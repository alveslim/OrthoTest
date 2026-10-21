from collections.abc import Iterable

from backend.schemas import ResultadoTeste


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