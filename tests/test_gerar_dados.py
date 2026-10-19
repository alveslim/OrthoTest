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
    
def test_idade_e_imc_estao_dentro_dos_limites():
    participantes, _, _ = gerar_amostra()

    for participante in participantes:
        assert 18 <= participante["idade"] <= 60

        imc = participante["peso_kg"] / participante["altura_m"] ** 2

        assert 17 <= imc <= 35, (
            f"IMC fora dos limites para {participante['codigo']}: {imc:.2f}"
        )


def test_quantidades_e_ligacoes_sao_validas():
    participantes, avaliacoes, resultados = gerar_amostra()

    assert len(participantes) == TOTAL_PARTICIPANTES == 60
    assert len(TESTES) == 16
    assert len(avaliacoes) == len(participantes)

    # Identificadores dos registros.
    ids_participantes = {p["id"] for p in participantes}
    codigos = {p["codigo"] for p in participantes}
    ids_avaliacao = {a["id"] for a in avaliacoes}
    ids_teste = {
        f"T-{numero:02d}"
        for numero in range(1, len(TESTES) + 1)
    }

    # Os identificadores devem ser únicos.
    assert len(ids_participantes) == len(participantes)
    assert len(codigos) == len(participantes)
    assert len(ids_avaliacao) == len(avaliacoes)

    # Nenhum nome ou e-mail real deve ser incluído.
    assert all(
        "nome" not in p and "email" not in p
        for p in participantes
    )

    # Toda avaliação deve apontar para um participante existente.
    assert all(
        a["participante_id"] in ids_participantes
        for a in avaliacoes
    )

    # Todas as avaliações devem ter exatamente 16 registros.
    quantidades = Counter(
        r["avaliacao_id"] for r in resultados
    )

    assert len(quantidades) == len(avaliacoes)
    assert all(
        total == len(TESTES)
        for total in quantidades.values()
    )

    # Confere os vínculos e os valores de cada resultado.
    combinacoes = set()

    for registro in resultados:
        chave = (
            registro["avaliacao_id"],
            registro["teste_id"],
        )

        # Um teste só pode aparecer uma vez por avaliação.
        assert chave not in combinacoes
        combinacoes.add(chave)

        assert registro["avaliacao_id"] in ids_avaliacao
        assert registro["teste_id"] in ids_teste
        assert registro["lado"] in LADOS
        assert registro["resultado"] in RESULTADOS
        assert registro["ficticio"] is True

        dor = registro["dor_0_10"]

        if registro["resultado"] == "Positivo":
            assert isinstance(dor, int) and 3 <= dor <= 8
        else:
            assert isinstance(dor, int) and 0 <= dor <= 2