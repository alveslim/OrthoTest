"""Estado da sessão e acesso à API do OrthoTest.

Três situações:
  * online      : tudo vai para a API/Supabase.
  * sem internet: o app continua funcionando com o que já foi baixado (cache) e guarda o que você
                  registrar na fila do aparelho; envia sozinho quando a conexão volta.
  * demonstração (MODO_DEMO=true): dados de exemplo em memória, login aceita qualquer coisa, nada é
                  gravado. Só para ensaio; a tela de login avisa.
"""
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

import contingencia_offline as fila_local
from armazenamento import apagar, gravar_json, ler_json
from config import cfg
from termo import TERMO_VERSAO

load_dotenv()  # só ajuda no computador; no celular os valores vêm de app/config_publica.json

if sys.platform == "emscripten":  # versão web (Pyodide): faz o `requests` usar o fetch do navegador
    try:
        import pyodide_http  # type: ignore
        pyodide_http.patch_all()
    except Exception:
        pass

SUPABASE_URL = cfg("SUPABASE_URL")
SUPABASE_ANON_KEY = cfg("SUPABASE_ANON_KEY")
API_BASE_URL = cfg("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")


def _flag(*nomes: str) -> bool:
    return any(cfg(n, "false").lower() in ("true", "1", "yes") for n in nomes)


MODO_DEMO = _flag("MODO_DEMO", "MODO_OFFLINE")  # MODO_OFFLINE: nome antigo, ainda aceito

CATALOGO_LOCAL = Path(__file__).resolve().parent / "catalogo_testes.json"
TIMEOUT = 10
ARQ_SESSAO = "sessao.json"

sessao = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": 0,
    "user_id": None,
    "email": None,
    "papel": "aluno",
    "offline": False,
    "participante_atual": None,
    "avaliacao_atual": None,
    "teste_atual": None,
    "resultados_teste": [],
}

MSG_SEM_API = "Sem conexão com o servidor. Esta ação precisa de internet."


class _Indisponivel(Exception):
    """Servidor respondeu 502/503/504: tratado como falta de conexão."""


# ---------------------------------------------------------------- HTTP com renovação de sessão
def _headers_autenticados() -> dict:
    return {"Authorization": f"Bearer {sessao['access_token']}", "Content-Type": "application/json"}


def _req(metodo: str, caminho: str, *, params=None, json=None, timeout: int = TIMEOUT, renovar: bool = True):
    """Chama a API com o token. Se vier 401, renova o token uma vez e repete. Levanta RequestException sem rede."""
    url = f"{API_BASE_URL}{caminho}"
    try:
        resp = requests.request(metodo, url, headers=_headers_autenticados(), params=params, json=json, timeout=timeout)
        if resp.status_code == 401 and renovar and sessao.get("refresh_token") and _renovar_sessao() is True:
            resp = requests.request(metodo, url, headers=_headers_autenticados(), params=params, json=json, timeout=timeout)
    except requests.RequestException:
        sessao["offline"] = True
        raise
    sessao["offline"] = resp.status_code in (502, 503, 504)
    return resp


def _erro_api(resp: requests.Response, padrao: str) -> str:
    """Mensagem em português a partir da resposta de erro da API."""
    if resp.status_code == 401:
        return "Sessão expirada. Saia e entre novamente."
    try:
        detalhe = resp.json().get("detail")
    except ValueError:
        detalhe = None
    if isinstance(detalhe, list) and detalhe:  # erro de validação do Pydantic
        detalhe = "; ".join(str(d.get("msg", d)) for d in detalhe)
    if resp.status_code == 409 or (detalhe and "duplicate key" in str(detalhe)):
        return "Já existe um registro com esse código. Use outro código."
    return str(detalhe) if detalhe else padrao


# ---------------------------------------------------------------- sessão (login, lembrar, renovar)
def _aplicar_tokens(dados: dict) -> None:
    sessao["access_token"] = dados.get("access_token")
    if dados.get("refresh_token"):
        sessao["refresh_token"] = dados["refresh_token"]
    sessao["expires_at"] = int(dados.get("expires_at") or (time.time() + int(dados.get("expires_in", 3600))))
    if dados.get("user"):
        sessao["user_id"] = str(dados["user"].get("id", sessao.get("user_id") or ""))


def _salvar_sessao_local() -> None:
    if MODO_DEMO or not sessao.get("refresh_token"):
        return
    gravar_json(ARQ_SESSAO, {k: sessao.get(k) for k in
                             ("access_token", "refresh_token", "expires_at", "user_id", "email", "papel")})


def _renovar_sessao() -> bool | None:
    """True = renovada; False = o servidor recusou (precisa entrar de novo); None = sem rede (tenta depois)."""
    if not sessao.get("refresh_token") or not SUPABASE_URL:
        return False
    try:
        resp = requests.post(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=refresh_token",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"refresh_token": sessao["refresh_token"]}, timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code == 200:
        _aplicar_tokens(resp.json())
        _salvar_sessao_local()
        return True
    if resp.status_code in (400, 401, 403):
        return False
    return None


def autenticar_usuario(email: str, senha: str) -> tuple[bool, str]:
    if MODO_DEMO:
        sessao.update(access_token="demo", user_id="demo", email=email, papel="professor")
        return True, "Modo demonstração: dados de exemplo, nada é gravado no banco."
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return False, "Configure SUPABASE_URL e SUPABASE_ANON_KEY no arquivo .env"
    try:
        resp = requests.post(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": email.strip(), "password": senha}, timeout=TIMEOUT)
    except requests.RequestException:
        return False, "Sem internet. O primeiro acesso precisa de conexão; depois o app lembra do seu login."
    if resp.status_code != 200:
        try:
            codigo = resp.json().get("error_code", "")
        except ValueError:
            codigo = ""
        if codigo == "email_not_confirmed":
            return False, "E-mail ainda não confirmado. Abra o link que o Supabase enviou ao seu e-mail."
        if resp.status_code >= 500:
            return False, "Servidor de autenticação indisponível. Tente de novo em instantes."
        return False, "E-mail ou senha incorretos."
    _aplicar_tokens(resp.json())
    sessao["email"] = email.strip()
    sessao["papel"] = "aluno"
    sessao["offline"] = False
    try:  # o papel só habilita botões; quem decide de verdade é o backend/RLS
        r = _req("GET", "/me")
        if r.status_code == 200:
            sessao["papel"] = r.json().get("papel", "aluno")
    except requests.RequestException:
        pass
    _salvar_sessao_local()
    return True, "Autenticado com sucesso."


def tentar_restaurar_sessao() -> bool:
    """Reabre o app já logado, se houver sessão salva. Funciona sem internet (a sessão é renovada depois)."""
    if MODO_DEMO:
        return False
    salva = ler_json(ARQ_SESSAO, None)
    if not isinstance(salva, dict) or not salva.get("refresh_token") or not salva.get("user_id"):
        return False
    sessao.update({k: salva.get(k) for k in ("access_token", "refresh_token", "expires_at", "user_id", "email")})
    sessao["papel"] = salva.get("papel") or "aluno"
    if (salva.get("expires_at") or 0) - time.time() > 60:
        return True
    resultado = _renovar_sessao()
    if resultado is False:  # sessão revogada ou vencida de vez
        limpar_sessao()
        return False
    sessao["offline"] = resultado is None  # None = sem rede: segue com o que está no aparelho
    return True


def limpar_sessao():
    sessao.update(
        access_token=None, refresh_token=None, expires_at=0, user_id=None, email=None, papel="aluno", offline=False,
        participante_atual=None, avaliacao_atual=None, teste_atual=None, resultados_teste=[],
    )
    apagar(ARQ_SESSAO)  # sair = esquecer o login neste aparelho (a fila de envios pendentes é mantida)


def situacao_rede() -> dict:
    return {"offline": bool(sessao.get("offline")), "demo": MODO_DEMO,
            "pendentes": 0 if MODO_DEMO else len(fila_local.pendentes(sessao.get("user_id")))}


# ---------------------------------------------------------------- demonstração (em memória)
def _catalogo_local() -> list[dict]:
    return json.loads(CATALOGO_LOCAL.read_text(encoding="utf-8"))


_off: dict = {"participantes": [], "avaliacoes": {}, "resultados": []}
_DEMO_PESSOAS = [("P-001", "Ana", "Lima", 22, 70.0, 1.75), ("P-002", None, None, 30, 82.0, 1.80)]


def _off_inicializar():
    if _off["participantes"]:
        return
    for i, (cod, nome, sob, idade, peso, altura) in enumerate(_DEMO_PESSOAS, 1):
        _off["participantes"].append({"id": f"p{i}", "codigo": cod, "nome": nome, "sobrenome": sob,
                                      "idade": idade, "peso_kg": peso, "altura_m": altura})


def _off_atualizar_progresso(avaliacao_id: str):
    total = len(_catalogo_local())
    feitos = len({r["teste_id"] for r in _off["resultados"] if r["avaliacao_id"] == avaliacao_id})
    av = _off["avaliacoes"][avaliacao_id]
    av["progresso_percentual"] = round(100 * feitos / total, 2) if total else 0.0
    av["status"] = "pendente" if feitos == 0 else ("concluido" if feitos >= total else "em_andamento")


# ---------------------------------------------------------------- cache e fila (visão local)
def _user() -> str:
    return str(sessao.get("user_id") or "")


def _cache() -> dict:
    return fila_local.carregar_cache(_user())


def _catalogo_base() -> list[dict]:
    return _cache()["catalogo"] or _catalogo_local()


def _indisponivel(resp) -> bool:
    return resp.status_code in (502, 503, 504)


def _agrupar_por_teste(resultados: list[dict]) -> dict[int, list[dict]]:
    mapa: dict[int, list[dict]] = {}
    for r in resultados:
        mapa.setdefault(int(r["teste_id"]), []).append(r)
    return mapa


def _resultados_visiveis(avaliacao_id: str, do_servidor: list[dict] | None = None) -> list[dict]:
    """Resultados já enviados (servidor ou cache) + os pendentes de envio (que prevalecem)."""
    base = do_servidor if do_servidor is not None else _cache()["resultados"].get(str(avaliacao_id), [])
    pend = fila_local.resultados_pendentes(_user(), str(avaliacao_id))
    chaves = {(int(p["teste_id"]), p["lado"]) for p in pend}
    return [r for r in base if (int(r["teste_id"]), r["lado"]) not in chaves] + pend


def _progresso_visivel(av: dict) -> dict:
    """Recalcula o progresso mostrando também o que ainda está só no aparelho."""
    pend = {int(p["teste_id"]) for p in fila_local.resultados_pendentes(_user(), str(av["id"]))}
    if not pend:
        return av
    total = len(_catalogo_base())
    ja = {int(r["teste_id"]) for r in _cache()["resultados"].get(str(av["id"]), [])}
    base = round(float(av.get("progresso_percentual") or 0) * total / 100)
    feitos = min(total, base + len(pend - ja)) if total else 0
    return dict(av, progresso_percentual=round(100 * feitos / total, 2) if total else 0.0,
                status="concluido" if total and feitos >= total else "em_andamento")


def _montar_lista(participantes: list[dict], avaliacoes: list[dict]) -> list[dict]:
    """Junta servidor/cache com o que foi criado sem internet e ainda não foi enviado."""
    user = _user()
    ps = list(participantes)
    avs = {str(a["participante_id"]): a for a in avaliacoes}
    for item in fila_local.pendentes(user):
        if item["tipo"] == "participante":
            ps.insert(0, dict(item["payload"], id=item["local_id"], pendente=True))
        elif item["tipo"] == "avaliacao":
            avs[str(item["participante_id"])] = {"id": item["local_id"], "participante_id": item["participante_id"],
                                                 "status": "pendente", "progresso_percentual": 0.0, "pendente": True}
    return [dict(p, avaliacao=_progresso_visivel(avs[str(p["id"])]) if str(p["id"]) in avs else None) for p in ps]


def codigo_sugerido() -> str:
    """Próximo código P-00N (o banco gera o definitivo; sem internet este fica provisório)."""
    if MODO_DEMO:
        _off_inicializar()
        return fila_local.proximo_codigo([p["codigo"] for p in _off["participantes"]])
    c = _cache()
    codigos = [p.get("codigo", "") for p in c["participantes"]]
    codigos += [i["payload"].get("codigo", "") for i in fila_local.pendentes(_user()) if i["tipo"] == "participante"]
    return fila_local.proximo_codigo(codigos)


# ---------------------------------------------------------------- participantes e avaliações
def buscar_participantes_e_avaliacoes() -> tuple[bool, list | str]:
    if MODO_DEMO:
        _off_inicializar()
        avs = {a["participante_id"]: a for a in _off["avaliacoes"].values()}
        return True, [dict(p, avaliacao=avs.get(p["id"])) for p in _off["participantes"]]
    sincronizar_fila_offline()
    cache = _cache()
    try:
        resp_p = _req("GET", "/participantes")
        if resp_p.status_code == 200:
            resp_a = _req("GET", "/avaliacoes")
            avaliacoes = resp_a.json() if resp_a.status_code == 200 else cache["avaliacoes"]
            cache.update(participantes=resp_p.json(), avaliacoes=avaliacoes)
            fila_local.gravar_cache(cache)
            return True, _montar_lista(cache["participantes"], cache["avaliacoes"])
        if not _indisponivel(resp_p):
            return False, _erro_api(resp_p, f"Erro ao carregar participantes ({resp_p.status_code}).")
        sessao["offline"] = True
    except requests.RequestException:
        pass
    return True, _montar_lista(cache["participantes"], cache["avaliacoes"])  # sem internet: usa o aparelho


def criar_novo_participante(idade: int, peso_kg: float | None, altura_m: float | None, nome: str | None = None,
                            sobrenome: str | None = None, responsavel_ciente: bool = False) -> tuple[bool, dict | str]:
    """O consentimento já foi aceito na tela (termo lido e marcado); aqui só registramos data e versão."""
    nome = " ".join((nome or "").split()) or None
    sobrenome = " ".join((sobrenome or "").split()) or None
    if MODO_DEMO:
        _off_inicializar()
        codigo = fila_local.proximo_codigo([p["codigo"] for p in _off["participantes"]])
        novo = {"id": f"p{uuid.uuid4().hex[:6]}", "codigo": codigo, "nome": nome, "sobrenome": sobrenome,
                "idade": idade, "peso_kg": peso_kg, "altura_m": altura_m}
        _off["participantes"].append(novo)
        return True, novo
    payload = {"nome": nome, "sobrenome": sobrenome, "idade": idade, "peso_kg": peso_kg, "altura_m": altura_m,
               "consentimento": True, "data_consentimento": datetime.now(timezone.utc).isoformat(),
               "termo_versao": TERMO_VERSAO, "consentimento_responsavel": bool(responsavel_ciente)}
    payload = {k: v for k, v in payload.items() if v is not None}
    try:
        resp = _req("POST", "/participantes", json=payload)
        if resp.status_code in (200, 201):
            novo = resp.json()
            c = _cache()
            c["participantes"].insert(0, novo)
            fila_local.gravar_cache(c)
            return True, novo
        if not _indisponivel(resp):
            return False, _erro_api(resp, "Erro ao validar os dados do participante.")
    except requests.RequestException:
        pass
    # Sem internet: guarda no aparelho com um código provisório.
    local_id = fila_local.novo_id_local()
    codigo = codigo_sugerido()
    payload["codigo"] = codigo
    fila_local.enfileirar_participante(_user(), local_id, payload)
    return True, dict(payload, id=local_id, pendente=True)


def garantir_avaliacao_ativa(participante_id: str, avaliacao_existente: dict | None) -> tuple[bool, dict | str]:
    if avaliacao_existente:
        return True, avaliacao_existente
    if MODO_DEMO:
        av = {"id": f"a{uuid.uuid4().hex[:6]}", "participante_id": participante_id, "status": "pendente", "progresso_percentual": 0.0}
        _off["avaliacoes"][av["id"]] = av
        return True, av
    pendente = fila_local.avaliacao_pendente_do_participante(_user(), str(participante_id))
    if pendente:
        return True, {"id": pendente["local_id"], "participante_id": participante_id, "status": "pendente",
                      "progresso_percentual": 0.0, "pendente": True}
    if not fila_local.eh_local(participante_id):
        try:
            resp = _req("POST", "/avaliacoes", json={"participante_id": str(participante_id)})
            if resp.status_code in (200, 201):
                av = resp.json()
                c = _cache()
                c["avaliacoes"] = [a for a in c["avaliacoes"] if a["id"] != av["id"]] + [av]
                fila_local.gravar_cache(c)
                return True, av
            if not _indisponivel(resp):
                return False, _erro_api(resp, "Não foi possível iniciar a ficha de avaliação.")
        except requests.RequestException:
            pass
    local_id = fila_local.novo_id_local()
    fila_local.enfileirar_avaliacao(_user(), local_id, str(participante_id))
    return True, {"id": local_id, "participante_id": participante_id, "status": "pendente",
                  "progresso_percentual": 0.0, "pendente": True}


# ---------------------------------------------------------------- catálogo e resultados
def buscar_catalogo_e_resultados(avaliacao_id: str) -> tuple[bool, dict | str]:
    """`mapa_resultados`: {teste_id: [linhas]} (um teste pode ter Direito e Esquerdo)."""
    if MODO_DEMO:
        res = [r for r in _off["resultados"] if r["avaliacao_id"] == avaliacao_id]
        return True, {"catalogo": _catalogo_local(), "mapa_resultados": _agrupar_por_teste(res)}
    avaliacao_id = str(avaliacao_id)
    cache = _cache()
    do_servidor = None
    if not fila_local.eh_local(avaliacao_id):
        try:
            resp_cat = _req("GET", "/catalogo/testes")
            if resp_cat.status_code == 200:
                resp_res = _req("GET", f"/avaliacoes/{avaliacao_id}/resultados")
                if resp_res.status_code == 200:
                    cache["catalogo"] = resp_cat.json()
                    do_servidor = resp_res.json()
                    cache["resultados"][avaliacao_id] = do_servidor
                    fila_local.gravar_cache(cache)
                elif not _indisponivel(resp_res):
                    return False, _erro_api(resp_res, "Erro ao carregar os resultados da avaliação.")
            elif not _indisponivel(resp_cat):
                return False, _erro_api(resp_cat, f"Erro ao carregar catálogo ({resp_cat.status_code}).")
        except requests.RequestException:
            pass
    catalogo = cache["catalogo"] or _catalogo_local()
    return True, {"catalogo": catalogo, "mapa_resultados": _agrupar_por_teste(_resultados_visiveis(avaliacao_id, do_servidor))}


def _cache_gravar_resultado(avaliacao_id: str, payload: dict) -> None:
    c = _cache()
    linhas = [r for r in c["resultados"].get(avaliacao_id, [])
              if not (int(r["teste_id"]) == int(payload["teste_id"]) and r["lado"] == payload["lado"])]
    linhas.append(dict(payload, avaliacao_id=avaliacao_id))
    c["resultados"][avaliacao_id] = linhas
    fila_local.gravar_cache(c)


def salvar_resultado_teste(avaliacao_id: str, payload: dict) -> tuple[bool, str]:
    """Grava na API. Sem internet, guarda no aparelho e envia quando a conexão voltar."""
    if MODO_DEMO:
        _off["resultados"] = [r for r in _off["resultados"] if not (
            r["avaliacao_id"] == avaliacao_id and r["teste_id"] == payload["teste_id"] and r["lado"] == payload["lado"])]
        _off["resultados"].append(dict(payload, avaliacao_id=avaliacao_id))
        _off_atualizar_progresso(avaliacao_id)
        return True, "Resultado salvo (modo demonstração)."
    avaliacao_id = str(avaliacao_id)
    if not fila_local.eh_local(avaliacao_id):
        try:
            resp = _req("POST", f"/avaliacoes/{avaliacao_id}/resultados", json=payload)
            if resp.status_code in (200, 201):
                fila_local.remover_resultado_pendente(_user(), avaliacao_id, payload["teste_id"], payload["lado"])
                _cache_gravar_resultado(avaliacao_id, payload)
                sincronizar_fila_offline()  # a conexão voltou: aproveita para esvaziar a fila
                return True, "Resultado salvo."
            if not _indisponivel(resp):
                return False, _erro_api(resp, "Erro ao salvar o resultado.")
        except requests.RequestException:
            pass
    fila_local.enfileirar_resultado(_user(), avaliacao_id, payload)
    return True, "Sem conexão: resultado guardado neste aparelho. Será enviado quando a internet voltar."


def _enviar_para_fila(metodo: str, caminho: str, corpo: dict):
    resp = _req(metodo, caminho, json=corpo)
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, {}


def sincronizar_fila_offline() -> dict:
    """Envia o que foi guardado sem internet. Seguro chamar sempre: sem pendência, não faz nada."""
    vazio = {"sincronizados": 0, "pendentes": 0, "rejeitados": 0, "codigos_alterados": [], "erros": [], "mapa_ids": {}}
    if MODO_DEMO or not sessao.get("access_token"):
        return vazio
    n = len(fila_local.pendentes(_user()))
    if not n:
        return vazio
    res = fila_local.sincronizar(_user(), _enviar_para_fila)
    for chave in ("participante_atual", "avaliacao_atual"):  # a tela aberta passa a usar o id real
        atual = sessao.get(chave)
        if atual and atual.get("id") in res["mapa_ids"]:
            sessao[chave] = dict(atual, id=res["mapa_ids"][atual["id"]], pendente=False)
    if res["sincronizados"] and not res["erros"]:
        sessao["offline"] = False
    return res


def excluir_resultado_teste_api(avaliacao_id: str, teste_id: int, lado: str | None = None) -> tuple[bool, str]:
    if MODO_DEMO:
        _off["resultados"] = [r for r in _off["resultados"] if not (
            r["avaliacao_id"] == avaliacao_id and r["teste_id"] == teste_id and (lado is None or r["lado"] == lado))]
        _off_atualizar_progresso(avaliacao_id)
        return True, "Resultado excluído."
    avaliacao_id = str(avaliacao_id)
    descartou = fila_local.remover_resultado_pendente(_user(), avaliacao_id, teste_id, lado)
    if fila_local.eh_local(avaliacao_id):
        return True, "Resultado excluído."
    try:
        resp = _req("DELETE", f"/avaliacoes/{avaliacao_id}/resultados/{teste_id}", params={"lado": lado} if lado else None)
    except requests.RequestException:
        return descartou, ("Resultado pendente descartado. Excluir o que já foi enviado precisa de internet."
                           if descartou else MSG_SEM_API)
    if resp.status_code == 200:
        c = _cache()
        c["resultados"][avaliacao_id] = [r for r in c["resultados"].get(avaliacao_id, []) if not (
            int(r["teste_id"]) == int(teste_id) and (lado is None or r["lado"] == lado))]
        fila_local.gravar_cache(c)
        return True, "Resultado excluído."
    if resp.status_code == 404 and descartou:
        return True, "Resultado excluído."
    return False, _erro_api(resp, "Não foi possível excluir o resultado.")


def sinalizar_avaliacao_professor(avaliacao_id: str, motivo: str) -> tuple[bool, str]:
    if MODO_DEMO:
        return True, "Avaliação sinalizada (modo demonstração)."
    if fila_local.eh_local(avaliacao_id):
        return False, "Esta ficha ainda não foi enviada. Aguarde a internet voltar para sinalizar."
    try:
        resp = _req("POST", f"/avaliacoes/{avaliacao_id}/sinalizar",
                    json={"motivo": motivo.strip() or "Solicitação de revisão pelo aluno."})
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, "Avaliação sinalizada ao professor."
    return False, _erro_api(resp, "Não foi possível sinalizar a avaliação.")


def marcar_revisada_api(avaliacao_id: str) -> tuple[bool, str]:
    """Professor: tira a marca de revisão pedida."""
    if MODO_DEMO:
        return True, "Marcada como revisada (modo demonstração)."
    try:
        resp = _req("POST", f"/avaliacoes/{avaliacao_id}/revisar")
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, "Avaliação marcada como revisada."
    return False, _erro_api(resp, "Não foi possível marcar como revisada.")


# ---------------------------------------------------------------- dashboard
def buscar_kpis_dashboard() -> tuple[bool, dict | str]:
    if MODO_DEMO:
        def grupo(nome, pct, n=5, campo="regiao"):
            return {campo: nome, "total_valido": n * 4, "positivos": round(n * 4 * pct / 100),
                    "percentual_positivo": pct, "participantes": n}
        return True, {
            "participantes_avaliados": 12, "percentual_avaliacoes_completas": 75.0, "dor_media_geral": 4.2,
            "gerais_ocultos": False,
            "positividade_por_regiao": [grupo("Joelho", 35.0), grupo("Ombro", 20.0), grupo("Coluna lombar", 15.0)],
            "positividade_por_teste": [grupo("Lachman", 30.0, campo="teste"), grupo("Neer", 20.0, campo="teste")],
            "positividade_por_faixa_etaria": [grupo("18-24", 28.0, campo="faixa_etaria")],
            "positividade_por_imc": [grupo("Normal", 22.0, campo="faixa_imc")],
        }
    try:
        resp = _req("GET", "/dashboard/kpis", timeout=20)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, resp.json()
    return False, _erro_api(resp, "Não foi possível carregar os dados do dashboard.")


def exportar_relatorio_dashboard() -> tuple[bool, str]:
    if MODO_DEMO:
        return True, "Exportação simulada (modo demonstração)."
    try:
        resp = _req("POST", "/dashboard/exportar/csv", timeout=20)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code in (200, 201):
        return True, resp.json().get("mensagem", "Relatório exportado.")
    return False, _erro_api(resp, "Erro ao exportar o relatório.")


# ---------------------------------------------------------------- IA de apoio
MSG_FICHA_LOCAL = "Esta ficha ainda não foi enviada ao servidor. Aguarde a internet voltar e sincronize."


def solicitar_resumo_ia(avaliacao_id: str) -> tuple[bool, str, str]:
    if not MODO_DEMO and fila_local.eh_local(avaliacao_id):
        return False, MSG_FICHA_LOCAL, ""
    if MODO_DEMO:
        nota = "NOTA: Este é um rascunho gerado por IA para revisão humana e não constitui diagnóstico clínico."
        return True, f"- Lachman (Joelho), lado Direito, Positivo: Possível frouxidão, indicando suspeita de lesão do LCA.\n\n{nota}", "Exemplo (modo demonstração)."
    try:
        resp = _req("POST", f"/avaliacoes/{avaliacao_id}/resumo-ia", timeout=40)
    except requests.RequestException:
        return False, MSG_SEM_API, ""
    if resp.status_code == 200:
        d = resp.json()
        return bool(d.get("sucesso")), d.get("resumo", ""), d.get("aviso", "")
    return False, _erro_api(resp, "Erro ao contactar o motor de IA."), ""


def salvar_rascunho_ia_api(avaliacao_id: str, texto: str) -> tuple[bool, str]:
    if not MODO_DEMO and fila_local.eh_local(avaliacao_id):
        return False, MSG_FICHA_LOCAL
    if MODO_DEMO:
        return True, "Rascunho salvo (modo demonstração)."
    try:
        resp = _req("POST", f"/avaliacoes/{avaliacao_id}/rascunho", json={"texto_final": texto})
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, resp.json().get("mensagem", "Rascunho salvo.")
    return False, _erro_api(resp, "Erro ao salvar o rascunho.")


def aprovar_resumo_ia_api(avaliacao_id: str, texto_final: str) -> tuple[bool, str]:
    if not MODO_DEMO and fila_local.eh_local(avaliacao_id):
        return False, MSG_FICHA_LOCAL
    if MODO_DEMO:
        return True, "Resumo aprovado (modo demonstração)."
    try:
        resp = _req("POST", f"/avaliacoes/{avaliacao_id}/aprovar-resumo", json={"texto_final": texto_final})
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, resp.json().get("mensagem", "Resumo aprovado.")
    return False, _erro_api(resp, "Erro ao aprovar o resumo.")
