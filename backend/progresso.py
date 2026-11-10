from collections.abc import Iterable, Mapping

from backend.schemas import ResultadoTeste


RESULTADOS_RESPONDIDOS = {
    "Positivo",
    "Negativo",
    "Não realizado",
    "Inconclusivo",
}


def calcular_progresso(
    avaliacao_id: str,
    ids_catalogo: Iterable[int],
    resultados: Iterable[ResultadoTeste],
) -> dict[str, str | int]:
    esperados = set(ids_catalogo)

    respondidos = {
        item.teste_id
        for item in resultados
        if item.avaliacao_id == avaliacao_id
        and item.teste_id in esperados
        and item.resultado is not None
    }

    total = len(esperados)
    quantidade = len(respondidos)

    return {
        "status": (
            "Completo" if total > 0 and quantidade == total else "Incompleto"
        ),
        "respondidos": quantidade,
        "total": total,
        "progresso": f"{quantidade} de {total} testes",
    }


def aplicar_progresso_em_memoria(
    avaliacoes: Iterable[Mapping],
    ids_catalogo: Iterable[int],
    resultados: Iterable[Mapping],
) -> list[dict]:
    """Recalcula status/progresso sem confiar em valores históricos do banco.

    Útil após atualização do catálogo: uma avaliação que estava completa com
    quatro testes ativos não deve continuar 100% completa quando o catálogo
    passa a exigir mais testes.
    """
    esperados = {int(item) for item in ids_catalogo}
    por_avaliacao: dict[str, set[int]] = {}

    for resultado in resultados:
        if resultado.get("resultado") not in RESULTADOS_RESPONDIDOS:
            continue
        try:
            avaliacao_id = str(resultado["avaliacao_id"])
            teste_id = int(resultado["teste_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if teste_id in esperados:
            por_avaliacao.setdefault(avaliacao_id, set()).add(teste_id)

    total = len(esperados)
    normalizadas = []
    for avaliacao in avaliacoes:
        item = dict(avaliacao)
        respondidos = len(por_avaliacao.get(str(item.get("id")), set()))
        percentual = round(respondidos / total * 100, 1) if total else 0.0
        item["status"] = (
            "concluido" if total > 0 and respondidos == total
            else "em_andamento" if respondidos > 0
            else "pendente"
        )
        item["progresso_percentual"] = percentual
        normalizadas.append(item)

    return normalizadas
