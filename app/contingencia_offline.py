"""Modo sem internet: fila de envios pendentes + cache do que já foi baixado.

A fila guarda, NA ORDEM em que aconteceram, três tipos de operação:
  participante  -> POST /participantes
  avaliacao     -> POST /avaliacoes            (depende do participante)
  resultado     -> POST /avaliacoes/{id}/resultados   (depende da avaliação)
Itens criados sem internet usam ids provisórios ("loc-..."); na sincronização cada id provisório é
trocado pelo id real devolvido pela API, e os itens seguintes usam o id real.

Nada é perdido em silêncio: o que a API recusar (dados inválidos) vai para `fila_rejeitados.json`.
"""
import re
import uuid
from datetime import datetime, timezone

from armazenamento import apagar, gravar_json, ler_json

ARQ_FILA = "fila_offline.json"
ARQ_REJEITADOS = "fila_rejeitados.json"
ARQ_CACHE = "cache_local.json"
PREFIXO_LOCAL = "loc-"


def novo_id_local() -> str:
    return PREFIXO_LOCAL + uuid.uuid4().hex[:10]


def eh_local(valor) -> bool:
    return str(valor).startswith(PREFIXO_LOCAL)


# ---------------------------------------------------------------- fila
def carregar_fila() -> list[dict]:
    fila = ler_json(ARQ_FILA, [])
    return fila if isinstance(fila, list) else []


def _gravar_fila(fila: list[dict]) -> None:
    if fila:
        gravar_json(ARQ_FILA, fila)
    else:
        apagar(ARQ_FILA)


def pendentes(user_id: str | None = None) -> list[dict]:
    fila = carregar_fila()
    return [i for i in fila if user_id is None or i.get("user_id") == user_id]


def _chave_resultado(item: dict) -> tuple:
    return (item.get("avaliacao_id"), int(item.get("teste_id", 0)), item.get("lado"))


def enfileirar_resultado(user_id: str, avaliacao_id: str, payload: dict) -> None:
    """Um resultado por (avaliação, teste, lado): salvar de novo substitui o pendente (idempotente)."""
    limpo = {k: v for k, v in payload.items() if k != "avaliacao_id"}
    novo = {"tipo": "resultado", "user_id": user_id, "avaliacao_id": avaliacao_id, "payload": limpo,
            "criado_em": datetime.now(timezone.utc).isoformat()}
    chave = _chave_resultado({"avaliacao_id": avaliacao_id, **novo["payload"]})
    fila = [i for i in carregar_fila() if not (
        i.get("tipo") == "resultado" and i.get("user_id") == user_id
        and _chave_resultado({"avaliacao_id": i["avaliacao_id"], **i["payload"]}) == chave)]
    fila.append(novo)
    _gravar_fila(fila)


def enfileirar_participante(user_id: str, local_id: str, payload: dict) -> None:
    fila = carregar_fila()
    fila.append({"tipo": "participante", "user_id": user_id, "local_id": local_id, "payload": payload,
                 "criado_em": datetime.now(timezone.utc).isoformat()})
    _gravar_fila(fila)


def enfileirar_avaliacao(user_id: str, local_id: str, participante_id: str) -> None:
    fila = carregar_fila()
    fila.append({"tipo": "avaliacao", "user_id": user_id, "local_id": local_id, "participante_id": participante_id,
                 "criado_em": datetime.now(timezone.utc).isoformat()})
    _gravar_fila(fila)


def avaliacao_pendente_do_participante(user_id: str, participante_id: str) -> dict | None:
    for i in carregar_fila():
        if i.get("tipo") == "avaliacao" and i.get("user_id") == user_id and i.get("participante_id") == participante_id:
            return i
    return None


def resultados_pendentes(user_id: str, avaliacao_id: str) -> list[dict]:
    return [dict(i["payload"], avaliacao_id=avaliacao_id, pendente=True) for i in carregar_fila()
            if i.get("tipo") == "resultado" and i.get("user_id") == user_id and i.get("avaliacao_id") == avaliacao_id]


def remover_resultado_pendente(user_id: str, avaliacao_id: str, teste_id: int, lado: str | None = None) -> bool:
    fila = carregar_fila()
    manter = [i for i in fila if not (
        i.get("tipo") == "resultado" and i.get("user_id") == user_id and i.get("avaliacao_id") == avaliacao_id
        and int(i["payload"].get("teste_id", 0)) == int(teste_id) and (lado is None or i["payload"].get("lado") == lado))]
    if len(manter) != len(fila):
        _gravar_fila(manter)
        return True
    return False


# ---------------------------------------------------------------- sincronização
def sincronizar(user_id: str, enviar) -> dict:
    """Envia a fila do usuário em ordem.

    `enviar(metodo, caminho, corpo)` devolve (status_http, json) ou levanta uma exceção de rede.
    Falha de rede/servidor/sessão: para e mantém o resto na fila. Recusa por dados inválidos (4xx): o
    item (e o que depende dele) vai para `fila_rejeitados.json`, com o motivo.
    """
    fila = carregar_fila()
    meus = [i for i in fila if i.get("user_id") == user_id]
    de_outros = [i for i in fila if i.get("user_id") != user_id]
    mapa: dict[str, str] = {}
    restantes: list[dict] = []
    rejeitados: list[dict] = []
    codigos_alterados: list[dict] = []
    enviados = 0
    parar = False
    erros: list[str] = []

    def resolver(i):
        return mapa.get(i, i)

    for item in meus:
        if parar:
            restantes.append(item)
            continue
        try:
            tipo = item["tipo"]
            if tipo == "participante":
                corpo_env = dict(item["payload"])
                status, corpo = enviar("POST", "/participantes", corpo_env)
                if status == 409 and corpo_env.get("codigo"):  # código já usado em outro aparelho
                    status, corpo = enviar("POST", "/participantes", {k: v for k, v in corpo_env.items() if k != "codigo"})
                    if status in (200, 201):
                        codigos_alterados.append({"antes": corpo_env["codigo"], "depois": corpo.get("codigo")})
            elif tipo == "avaliacao":
                pid = resolver(item["participante_id"])
                if eh_local(pid):  # o participante foi rejeitado
                    rejeitados.append(dict(item, motivo="O participante deste registro foi recusado pela API."))
                    mapa.setdefault(item["local_id"], item["local_id"])
                    continue
                status, corpo = enviar("POST", "/avaliacoes", {"participante_id": pid})
            elif tipo == "resultado":
                aid = resolver(item["avaliacao_id"])
                if eh_local(aid):
                    rejeitados.append(dict(item, motivo="A avaliação deste resultado foi recusada pela API."))
                    continue
                status, corpo = enviar("POST", f"/avaliacoes/{aid}/resultados", item["payload"])
            else:
                rejeitados.append(dict(item, motivo="Tipo de operação desconhecido."))
                continue
        except Exception as exc:  # sem rede: para aqui, mantém o resto
            erros.append(f"Sem conexão: {type(exc).__name__}")
            restantes.append(item)
            parar = True
            continue

        if status in (200, 201):
            enviados += 1
            if item["tipo"] in ("participante", "avaliacao"):
                mapa[item["local_id"]] = corpo["id"]
        elif status == 401 or status == 429 or status >= 500:
            erros.append("Sessão expirada. Entre novamente." if status == 401 else f"Servidor indisponível ({status}).")
            restantes.append(item)
            parar = True
        else:
            detalhe = corpo.get("detail") if isinstance(corpo, dict) else None
            rejeitados.append(dict(item, motivo=str(detalhe or f"Recusado ({status}).")))

    _gravar_fila(de_outros + restantes)
    if rejeitados:
        anteriores = ler_json(ARQ_REJEITADOS, [])
        gravar_json(ARQ_REJEITADOS, (anteriores if isinstance(anteriores, list) else []) + rejeitados)

    return {"sincronizados": enviados, "pendentes": len(restantes), "rejeitados": len(rejeitados),
            "codigos_alterados": codigos_alterados, "erros": erros, "mapa_ids": mapa}


# ---------------------------------------------------------------- cache do que já foi baixado
def carregar_cache(user_id: str) -> dict:
    c = ler_json(ARQ_CACHE, {})
    if not isinstance(c, dict) or c.get("user_id") != user_id:
        return {"user_id": user_id, "catalogo": [], "participantes": [], "avaliacoes": [], "resultados": {}}
    c.setdefault("catalogo", []); c.setdefault("participantes", []); c.setdefault("avaliacoes", []); c.setdefault("resultados", {})
    return c


def gravar_cache(cache: dict) -> None:
    gravar_json(ARQ_CACHE, cache)


def apagar_cache() -> None:
    apagar(ARQ_CACHE)


def proximo_codigo(codigos: list[str]) -> str:
    numeros = [int(m.group(1)) for c in codigos if (m := re.fullmatch(r"P-(\d+)", c or ""))]
    return f"P-{(max(numeros) if numeros else 0) + 1:03d}"
