import pytest
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

def test_progresso_antigo_e_recalculado_apos_ampliacao_do_catalogo():
    from backend.progresso import aplicar_progresso_em_memoria

    avaliacao_antiga = {
        "id": "a1",
        "status": "concluido",
        "progresso_percentual": 100.0,
    }
    catalogo_atual = list(range(1, 20))
    resultados_antigos = [
        {
            "avaliacao_id": "a1",
            "teste_id": teste_id,
            "resultado": "Positivo",
        }
        for teste_id in range(1, 5)
    ]

    atualizada = aplicar_progresso_em_memoria(
        [avaliacao_antiga], catalogo_atual, resultados_antigos
    )[0]

    assert atualizada["status"] == "em_andamento"
    assert atualizada["progresso_percentual"] == 21.1


def test_nao_realizado_conta_como_teste_respondido_no_progresso_atual():
    from backend.progresso import aplicar_progresso_em_memoria

    avaliacoes = [{"id": "a1", "status": "pendente"}]
    catalogo = [1, 2, 3]
    resultados = [
        {
            "avaliacao_id": "a1",
            "teste_id": 1,
            "resultado": "Não realizado",
        },
        {
            "avaliacao_id": "a1",
            "teste_id": 2,
            "resultado": "Inconclusivo",
        },
    ]

    atualizada = aplicar_progresso_em_memoria(avaliacoes, catalogo, resultados)[0]

    assert atualizada["status"] == "em_andamento"
    assert atualizada["progresso_percentual"] == 66.7


def test_resultado_fora_do_catalogo_ativo_nao_aumenta_progresso():
    from backend.progresso import aplicar_progresso_em_memoria

    avaliacoes = [{"id": "a1", "status": "concluido", "progresso_percentual": 100}]
    resultados = [
        {"avaliacao_id": "a1", "teste_id": 99, "resultado": "Positivo"}
    ]

    atualizada = aplicar_progresso_em_memoria(avaliacoes, [1, 2], resultados)[0]

    assert atualizada["status"] == "pendente"
    assert atualizada["progresso_percentual"] == 0.0
