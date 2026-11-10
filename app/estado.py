"""Estado da sessão e acesso à API do OrthoTest (online) ou aos dados de exemplo (modo offline).

MODO_OFFLINE=true roda o app inteiro sem internet, com o catálogo real de 19 testes e dados
em memória (perdidos ao fechar). Serve para ensaio e demonstração; não grava no banco.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from contingencia_offline import carregar_fila_local, salvar_rascunho_local, sincronizar_rascunhos

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
MODO_OFFLINE = os.getenv("MODO_OFFLINE", "false").lower() in ("true", "1", "yes")

CATALOGO_LOCAL = Path(__file__).resolve().parent.parent / "database" / "catalogo_testes.json"
TIMEOUT = 10

sessao = {
    "access_token": None,
    "user_id": None,
    "email": None,
    "papel": "aluno",
    "consentimento_aceito": False,
    "data_consentimento": None,
    "participante_atual": None,
    "avaliacao_atual": None,
    "teste_atual": None,
    "resultados_teste": [],
}


def _headers_autenticados() -> dict:
    return {"Authorization": f"Bearer {sessao['access_token']}", "Content-Type": "application/json"}


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


MSG_SEM_API = "Não foi possível falar com o servidor. Verifique a conexão e se a API está em execução."


# ---------------------------------------------------------------- sessão
def autenticar_usuario(email: str, senha: str) -> tuple[bool, str]:
    if MODO_OFFLINE:
        sessao.update(access_token="offline", user_id="offline", email=email, papel="professor")
        return True, "Modo offline: dados de exemplo, nada é gravado no banco."
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return False, "Configure SUPABASE_URL e SUPABASE_ANON_KEY no arquivo .env"
    try:
        resp = requests.post(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": email.strip(), "password": senha},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return False, "Erro ao conectar ao servidor de autenticação."
    if resp.status_code != 200:
        return False, "E-mail ou senha incorretos."
    dados = resp.json()
    sessao["access_token"] = dados.get("access_token")
    sessao["user_id"] = str(dados.get("user", {}).get("id", ""))
    sessao["email"] = email.strip()
    sessao["papel"] = "aluno"
    try:  # o papel só habilita botões; quem decide de verdade é o backend/RLS
        r = requests.get(f"{API_BASE_URL}/me", headers=_headers_autenticados(), timeout=TIMEOUT)
        if r.status_code == 200:
            sessao["papel"] = r.json().get("papel", "aluno")
    except requests.RequestException:
        pass
    return True, "Autenticado com sucesso."


def registrar_consentimento_sessao():
    sessao["consentimento_aceito"] = True
    sessao["data_consentimento"] = datetime.now(timezone.utc).isoformat()


def limpar_sessao():
    sessao.update(
        access_token=None, user_id=None, email=None, papel="aluno",
        consentimento_aceito=False, data_consentimento=None,
        participante_atual=None, avaliacao_atual=None, teste_atual=None, resultados_teste=[],
    )


# ---------------------------------------------------------------- dados de exemplo (offline)
def _catalogo_local() -> list[dict]:
    return json.loads(CATALOGO_LOCAL.read_text(encoding="utf-8"))


_off: dict = {"participantes": [], "avaliacoes": {}, "resultados": []}


def _off_inicializar():
    if _off["participantes"]:
        return
    for i, (cod, idade, peso, altura) in enumerate([("P-MOCK1", 22, 70.0, 1.75), ("P-MOCK2", 30, 82.0, 1.80)], 1):
        _off["participantes"].append({"id": f"p{i}", "codigo": cod, "idade": idade, "peso_kg": peso, "altura_m": altura})


def _off_atualizar_progresso(avaliacao_id: str):
    total = len(_catalogo_local())
    feitos = len({r["teste_id"] for r in _off["resultados"] if r["avaliacao_id"] == avaliacao_id})
    av = _off["avaliacoes"][avaliacao_id]
    av["progresso_percentual"] = round(100 * feitos / total, 2) if total else 0.0
    av["status"] = "pendente" if feitos == 0 else ("concluido" if feitos >= total else "em_andamento")


# ---------------------------------------------------------------- participantes e avaliações
def buscar_participantes_e_avaliacoes() -> tuple[bool, list | str]:
    if MODO_OFFLINE:
        _off_inicializar()
        avs = {a["participante_id"]: a for a in _off["avaliacoes"].values()}
        return True, [dict(p, avaliacao=avs.get(p["id"])) for p in _off["participantes"]]
    try:
        resp_p = requests.get(f"{API_BASE_URL}/participantes", headers=_headers_autenticados(), timeout=TIMEOUT)
        if resp_p.status_code != 200:
            return False, _erro_api(resp_p, f"Erro ao carregar participantes ({resp_p.status_code}).")
        resp_a = requests.get(f"{API_BASE_URL}/avaliacoes", headers=_headers_autenticados(), timeout=TIMEOUT)
        avaliacoes = resp_a.json() if resp_a.status_code == 200 else []
        mapa = {str(a["participante_id"]): a for a in avaliacoes}
        return True, [dict(p, avaliacao=mapa.get(str(p["id"]))) for p in resp_p.json()]
    except requests.RequestException:
        return False, MSG_SEM_API


def criar_novo_participante(codigo: str, idade: int, peso_kg: float | None, altura_m: float | None) -> tuple[bool, dict | str]:
    codigo = codigo.strip().upper()
    if MODO_OFFLINE:
        _off_inicializar()
        if any(p["codigo"] == codigo for p in _off["participantes"]):
            return False, "Já existe um registro com esse código. Use outro código."
        novo = {"id": f"p{uuid.uuid4().hex[:6]}", "codigo": codigo, "idade": idade, "peso_kg": peso_kg, "altura_m": altura_m}
        _off["participantes"].append(novo)
        return True, novo
    payload = {
        "codigo": codigo, "idade": idade, "peso_kg": peso_kg, "altura_m": altura_m,
        "consentimento": bool(sessao["consentimento_aceito"]),
        "data_consentimento": sessao["data_consentimento"],
    }
    try:
        resp = requests.post(f"{API_BASE_URL}/participantes", json=payload, headers=_headers_autenticados(), timeout=TIMEOUT)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code in (200, 201):
        return True, resp.json()
    return False, _erro_api(resp, "Erro ao validar os dados do participante.")


def garantir_avaliacao_ativa(participante_id: str, avaliacao_existente: dict | None) -> tuple[bool, dict | str]:
    if avaliacao_existente:
        return True, avaliacao_existente
    if MODO_OFFLINE:
        av = {"id": f"a{uuid.uuid4().hex[:6]}", "participante_id": participante_id, "status": "pendente", "progresso_percentual": 0.0}
        _off["avaliacoes"][av["id"]] = av
        return True, av
    try:
        resp = requests.post(f"{API_BASE_URL}/avaliacoes", json={"participante_id": str(participante_id)},
                             headers=_headers_autenticados(), timeout=TIMEOUT)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code in (200, 201):
        return True, resp.json()
    return False, _erro_api(resp, "Não foi possível iniciar a ficha de avaliação.")


# ---------------------------------------------------------------- catálogo e resultados
def _agrupar_por_teste(resultados: list[dict]) -> dict[int, list[dict]]:
    mapa: dict[int, list[dict]] = {}
    for r in resultados:
        mapa.setdefault(int(r["teste_id"]), []).append(r)
    return mapa


def buscar_catalogo_e_resultados(avaliacao_id: str) -> tuple[bool, dict | str]:
    """`mapa_resultados`: {teste_id: [linhas]} (um teste pode ter Direito e Esquerdo)."""
    if MODO_OFFLINE:
        res = [r for r in _off["resultados"] if r["avaliacao_id"] == avaliacao_id]
        return True, {"catalogo": _catalogo_local(), "mapa_resultados": _agrupar_por_teste(res)}
    try:
        resp_cat = requests.get(f"{API_BASE_URL}/catalogo/testes", headers=_headers_autenticados(), timeout=TIMEOUT)
        if resp_cat.status_code != 200:
            return False, _erro_api(resp_cat, f"Erro ao carregar catálogo ({resp_cat.status_code}).")
        resp_res = requests.get(f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/resultados", headers=_headers_autenticados(), timeout=TIMEOUT)
        if resp_res.status_code != 200:
            return False, _erro_api(resp_res, "Erro ao carregar os resultados da avaliação.")
        return True, {"catalogo": resp_cat.json(), "mapa_resultados": _agrupar_por_teste(resp_res.json())}
    except requests.RequestException:
        return False, MSG_SEM_API


def salvar_resultado_teste(avaliacao_id: str, payload: dict) -> tuple[bool, str]:
    """Grava na API. Sem internet, guarda na fila local e sincroniza depois."""
    if MODO_OFFLINE:
        _off["resultados"] = [r for r in _off["resultados"] if not (
            r["avaliacao_id"] == avaliacao_id and r["teste_id"] == payload["teste_id"] and r["lado"] == payload["lado"])]
        _off["resultados"].append(dict(payload, avaliacao_id=avaliacao_id))
        _off_atualizar_progresso(avaliacao_id)
        return True, "Resultado salvo (modo offline)."
    try:
        resp = requests.post(f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/resultados", json=payload,
                             headers=_headers_autenticados(), timeout=TIMEOUT)
    except requests.RequestException:
        salvar_rascunho_local(dict(payload, avaliacao_id=avaliacao_id))
        return True, "Sem conexão: resultado guardado neste aparelho e será enviado quando a internet voltar."
    if resp.status_code in (200, 201):
        return True, "Resultado salvo."
    return False, _erro_api(resp, "Erro ao salvar o resultado.")


def sincronizar_fila_offline() -> dict:
    """Reenvia rascunhos guardados sem internet. Devolve o resumo do contingencia_offline."""
    if MODO_OFFLINE or not carregar_fila_local():
        return {"sincronizados": 0, "pendentes": len(carregar_fila_local()), "conflitos": 0, "erros": []}
    return sincronizar_rascunhos(API_BASE_URL, _headers_autenticados())


def excluir_resultado_teste_api(avaliacao_id: str, teste_id: int, lado: str | None = None) -> tuple[bool, str]:
    if MODO_OFFLINE:
        _off["resultados"] = [r for r in _off["resultados"] if not (
            r["avaliacao_id"] == avaliacao_id and r["teste_id"] == teste_id and (lado is None or r["lado"] == lado))]
        _off_atualizar_progresso(avaliacao_id)
        return True, "Resultado excluído."
    try:
        resp = requests.delete(f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/resultados/{teste_id}",
                               params={"lado": lado} if lado else None, headers=_headers_autenticados(), timeout=TIMEOUT)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, "Resultado excluído."
    return False, _erro_api(resp, "Não foi possível excluir o resultado.")


def sinalizar_avaliacao_professor(avaliacao_id: str, motivo: str) -> tuple[bool, str]:
    if MODO_OFFLINE:
        return True, "Avaliação sinalizada (modo offline)."
    try:
        resp = requests.post(f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/sinalizar",
                             json={"motivo": motivo.strip() or "Solicitação de revisão pelo aluno."},
                             headers=_headers_autenticados(), timeout=TIMEOUT)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, "Avaliação sinalizada ao professor."
    return False, _erro_api(resp, "Não foi possível sinalizar a avaliação.")


# ---------------------------------------------------------------- dashboard
def buscar_kpis_dashboard() -> tuple[bool, dict | str]:
    if MODO_OFFLINE:
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
        resp = requests.get(f"{API_BASE_URL}/dashboard/kpis", headers=_headers_autenticados(), timeout=20)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, resp.json()
    return False, _erro_api(resp, "Não foi possível carregar os dados do dashboard.")


def exportar_relatorio_dashboard() -> tuple[bool, str]:
    if MODO_OFFLINE:
        return True, "Exportação simulada (modo offline)."
    try:
        resp = requests.post(f"{API_BASE_URL}/dashboard/exportar/csv", headers=_headers_autenticados(), timeout=20)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code in (200, 201):
        return True, resp.json().get("mensagem", "Relatório exportado.")
    return False, _erro_api(resp, "Erro ao exportar o relatório.")


# ---------------------------------------------------------------- IA de apoio
def solicitar_resumo_ia(avaliacao_id: str) -> tuple[bool, str, str]:
    if MODO_OFFLINE:
        nota = "NOTA: Este é um rascunho gerado por IA para revisão humana e não constitui diagnóstico clínico."
        return True, f"- Lachman (Joelho), lado Direito, Positivo: Possível frouxidão, indicando suspeita de lesão do LCA.\n\n{nota}", "Exemplo (modo offline)."
    try:
        resp = requests.post(f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/resumo-ia", headers=_headers_autenticados(), timeout=40)
    except requests.RequestException:
        return False, MSG_SEM_API, ""
    if resp.status_code == 200:
        d = resp.json()
        return bool(d.get("sucesso")), d.get("resumo", ""), d.get("aviso", "")
    return False, _erro_api(resp, "Erro ao contactar o motor de IA."), ""


def salvar_rascunho_ia_api(avaliacao_id: str, texto: str) -> tuple[bool, str]:
    if MODO_OFFLINE:
        return True, "Rascunho salvo (modo offline)."
    try:
        resp = requests.post(f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/rascunho", json={"texto_final": texto},
                             headers=_headers_autenticados(), timeout=TIMEOUT)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, resp.json().get("mensagem", "Rascunho salvo.")
    return False, _erro_api(resp, "Erro ao salvar o rascunho.")


def aprovar_resumo_ia_api(avaliacao_id: str, texto_final: str) -> tuple[bool, str]:
    if MODO_OFFLINE:
        return True, "Resumo aprovado (modo offline)."
    try:
        resp = requests.post(f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/aprovar-resumo", json={"texto_final": texto_final},
                             headers=_headers_autenticados(), timeout=TIMEOUT)
    except requests.RequestException:
        return False, MSG_SEM_API
    if resp.status_code == 200:
        return True, resp.json().get("mensagem", "Resumo aprovado.")
    return False, _erro_api(resp, "Erro ao aprovar o resumo.")
