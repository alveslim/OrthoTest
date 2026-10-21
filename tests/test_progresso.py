from backend.progresso import calcular_progresso
from backend.schemas import ResultadoTeste


def registro(
    teste_id: int,
    resultado: str,
    avaliacao_id: str = "a1",
    lado: str = "Direito",
) -> ResultadoTeste:
    return ResultadoTeste(
        avaliacao_id=avaliacao_id,
        teste_id=teste_id,
        lado=lado,
        resultado=resultado,
    )


def test_avaliacao_parcial():
    resultados = [
        registro(1, "Não realizado"),
        registro(2, "Inconclusivo"),
        registro(2, "Positivo", lado="Esquerdo"),
        registro(3, "Negativo", avaliacao_id="outra"),
    ]

    assert calcular_progresso("a1", [1, 2, 3, 4], resultados) == {
        "status": "Incompleto",
        "respondidos": 2,
        "total": 4,
        "progresso": "2 de 4 testes",
    }


def test_avaliacao_completa():
    resultados = [
        registro(1, "Negativo"),
        registro(2, "Positivo"),
        registro(3, "Não realizado"),
        registro(4, "Inconclusivo"),
    ]

    assert calcular_progresso("a1", [1, 2, 3, 4], resultados) == {
        "status": "Completo",
        "respondidos": 4,
        "total": 4,
        "progresso": "4 de 4 testes",
    }


def test_catalogo_vazio_nao_conclui_avaliacao():
    assert calcular_progresso("a1", [], [registro(99, "Positivo")]) == {
        "status": "Incompleto",
        "respondidos": 0,
        "total": 0,
        "progresso": "0 de 0 testes",
    }