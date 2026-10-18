import random
from collections import Counter

from dados_ficticios.gerar_dados import (
    LADOS,
    RESULTADOS,
    SEMENTE,
    TESTES,
    TOTAL_PARTICIPANTES,
    gerar_avaliacoes_e_resultados,
    gerar_participantes,
)


def gerar_amostra():
    gerador = random.Random(SEMENTE)
    participantes = gerar_participantes(gerador)
    avaliacoes, resultados = gerar_avaliacoes_e_resultados(
        participantes, gerador
    )
    return participantes, avaliacoes, resultados


def test_mesma_semente_produz_mesmos_dados():
    assert gerar_amostra() == gerar_amostra()


def test_quantidades_e_ligacoes_sao_validas():
    participantes, avaliacoes, resultados = gerar_amostra()

    assert len(participantes) == TOTAL_PARTICIPANTES == 60
    assert len(TESTES) == 16
    assert len(avaliacoes) == 60

    codigos = {p["codigo"] for p in participantes}
    ids_avaliacao = {a["id"] for a in avaliacoes}
    ids_teste = {f"T-{numero:02d}" for numero in range(1, len(TESTES) + 1)}

    assert len(codigos) == len(participantes)
    assert len(ids_avaliacao) == len(avaliacoes)
    assert all(a["participante_codigo"] in codigos for a in avaliacoes)
    assert all("nome" not in p and "email" not in p for p in participantes)

    quantidades = Counter(r["avaliacao_id"] for r in resultados)
    assert any(total == len(TESTES) for total in quantidades.values())
    assert any(total < len(TESTES) for total in quantidades.values())

    combinacoes = set()
    for registro in resultados:
        chave = (
            registro["avaliacao_id"],
            registro["teste_id"],
            registro["lado"],
        )
        assert chave not in combinacoes
        combinacoes.add(chave)

        assert registro["avaliacao_id"] in ids_avaliacao
        assert registro["teste_id"] in ids_teste
        assert registro["lado"] in LADOS
        assert registro["resultado"] in RESULTADOS

        dor = registro["dor_0_10"]
        if registro["resultado"] == "Não realizado":
            assert dor is None
        else:
            assert isinstance(dor, int) and 0 <= dor <= 10
