"""Cálculo dos KPIs do dashboard (ORT-26) com a regra de privacidade n < 3 (ORT-27).

Função pura: recebe linhas já filtradas pelo RLS (uma por resultado ativo) e devolve o dicionário
do dashboard. Grupos com menos de 3 PARTICIPANTES distintos nunca aparecem isolados; juntos, só
aparecem como "Outros" se o próprio grupo somado atingir 3 participantes.
"""
from collections import defaultdict

MIN_PARTICIPANTES = 3
ROTULO_OUTROS = "Outros (Privacidade < 3)"


def _pct(parte: int, total: int) -> float:
    return round(100.0 * parte / total, 1) if total else 0.0


def _agrupar(linhas: list[dict], chave: str) -> list[dict]:
    grupos: dict[str, dict] = defaultdict(lambda: {"total_valido": 0, "positivos": 0, "pessoas": set()})
    for linha in linhas:
        if linha.get("resultado") == "Não realizado":
            continue
        g = grupos[str(linha.get(chave) or "Desconhecido")]
        g["total_valido"] += 1
        g["positivos"] += linha.get("resultado") == "Positivo"
        g["pessoas"].add(linha.get("participante_id"))

    visiveis, ocultos = [], {"total_valido": 0, "positivos": 0, "pessoas": set()}
    for nome, g in sorted(grupos.items()):
        if len(g["pessoas"]) >= MIN_PARTICIPANTES:
            visiveis.append({
                chave: nome,
                "total_valido": g["total_valido"],
                "positivos": g["positivos"],
                "percentual_positivo": _pct(g["positivos"], g["total_valido"]),
                "participantes": len(g["pessoas"]),
            })
        else:
            ocultos["total_valido"] += g["total_valido"]
            ocultos["positivos"] += g["positivos"]
            ocultos["pessoas"] |= g["pessoas"]

    if len(ocultos["pessoas"]) >= MIN_PARTICIPANTES:
        visiveis.append({
            chave: ROTULO_OUTROS,
            "total_valido": ocultos["total_valido"],
            "positivos": ocultos["positivos"],
            "percentual_positivo": _pct(ocultos["positivos"], ocultos["total_valido"]),
            "participantes": len(ocultos["pessoas"]),
        })
    return visiveis


def _faixa_imc(imc) -> str | None:
    if imc is None:
        return None
    imc = float(imc)
    if imc < 18.5:
        return "Baixo peso"
    if imc < 25:
        return "Normal"
    if imc < 30:
        return "Sobrepeso"
    return "Obesidade"


def calcular_kpis(resultados: list[dict], avaliacoes: list[dict]) -> dict:
    """`avaliacoes`: linhas de public.avaliacoes visíveis ao usuário (status, participante_id)."""
    participantes = {a["participante_id"] for a in avaliacoes}
    n_part = len(participantes)
    completas = sum(1 for a in avaliacoes if a.get("status") == "concluido")

    dores = [
        r["dor_0_10"] for r in resultados
        if r.get("resultado") != "Não realizado" and r.get("dor_0_10") is not None
    ]
    pessoas_com_dor = {r["participante_id"] for r in resultados if r.get("dor_0_10") is not None}
    gerais_visiveis = n_part >= MIN_PARTICIPANTES

    com_imc = [dict(r, faixa_imc=_faixa_imc(r.get("imc"))) for r in resultados if r.get("imc") is not None]

    return {
        "participantes_avaliados": n_part,
        "percentual_avaliacoes_completas": _pct(completas, len(avaliacoes)) if gerais_visiveis else None,
        "dor_media_geral": (
            round(sum(dores) / len(dores), 1) if dores and len(pessoas_com_dor) >= MIN_PARTICIPANTES else None
        ),
        "gerais_ocultos": not gerais_visiveis,
        "positividade_por_regiao": _agrupar(resultados, "regiao"),
        "positividade_por_teste": _agrupar(resultados, "teste"),
        "positividade_por_faixa_etaria": _agrupar(resultados, "faixa_etaria"),
        "positividade_por_imc": _agrupar(com_imc, "faixa_imc"),
    }
