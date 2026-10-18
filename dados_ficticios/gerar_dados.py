"""Gera dados inteiramente fictícios para desenvolvimento."""

import json
import random
from pathlib import Path

SEMENTE = 42
TOTAL_PARTICIPANTES = 60
ARQUIVO_SAIDA = Path(__file__).with_name("amostra.json")

TESTES = [
    ("Joelho", "Lachman"),
    ("Joelho", "Gaveta Anterior (LCA)"),
    ("Joelho", "Estresse em Valgo (LCM)"),
    ("Joelho", "Estresse em Varo (LCL)"),
    ("Tornozelo", "Thompson"),
    ("Tornozelo", "Inclinação Talar"),
    ("Tornozelo", "Sinal de Kleiger"),
    ("Ombro", "Neer"),
    ("Ombro", "Impacto de Yocum"),
    ("Ombro", "Jobe"),
    ("Punho", "Finkelstein"),
    ("Punho", "Tinel"),
    ("Punho", "Phalen"),
    ("Coluna", "Lasègue"),
    ("Coluna", "Patrick-FABERE"),
    ("Coluna", "Adams"),
]

RESULTADOS = ("Negativo", "Positivo", "Não realizado", "Inconclusivo")
LADOS = ("Direito", "Esquerdo", "Bilateral")


def gerar_participantes(gerador: random.Random) -> list[dict]:
    participantes = []

    for numero in range(1, TOTAL_PARTICIPANTES + 1):
        participantes.append(
            {
                "codigo": f"P-{numero:03d}",
                "idade": gerador.randint(18, 75),
                "peso_kg": round(gerador.uniform(45, 110), 1),
                "altura_m": round(gerador.uniform(1.45, 2.00), 2),
                "consentimento": True,
                "data_consentimento": "2026-10-17",
            }
        )

    return participantes


def gerar_avaliacoes_e_resultados(
    participantes: list[dict], gerador: random.Random
) -> tuple[list[dict], list[dict]]:
    avaliacoes = []
    resultados_testes = []

    for numero, participante in enumerate(participantes, start=1):
        avaliacao_id = f"A-{numero:03d}"
        avaliacoes.append(
            {
                "id": avaliacao_id,
                "participante_codigo": participante["codigo"],
                "data_avaliacao": "2026-10-18",
            }
        )

        # Algumas avaliações completas e outras ainda com testes pendentes.
        quantidade = (
            len(TESTES) if numero <= 12 else gerador.randint(5, len(TESTES) - 1)
        )

        for indice in gerador.sample(range(len(TESTES)), k=quantidade):
            resultado = gerador.choices(
                RESULTADOS, weights=(65, 15, 12, 8), k=1
            )[0]

            resultados_testes.append(
                {
                    "avaliacao_id": avaliacao_id,
                    "teste_id": f"T-{indice + 1:02d}",
                    "lado": gerador.choice(LADOS),
                    "resultado": resultado,
                    "dor_0_10": (
                        None
                        if resultado == "Não realizado"
                        else gerador.randint(0, 10)
                    ),
                    "valor_medido": None,
                    "observacoes": None,
                }
            )

    return avaliacoes, resultados_testes


def main() -> None:
    gerador = random.Random(SEMENTE)
    participantes = gerar_participantes(gerador)
    avaliacoes, resultados_testes = gerar_avaliacoes_e_resultados(
        participantes, gerador
    )

    catalogo = [
        {"id": f"T-{indice:02d}", "regiao": regiao, "nome": nome}
        for indice, (regiao, nome) in enumerate(TESTES, start=1)
    ]

    dados = {
        "metadados": {"ficticio": True, "semente": SEMENTE},
        "participantes": participantes,
        "testes_catalogo": catalogo,
        "avaliacoes": avaliacoes,
        "resultados_testes": resultados_testes,
    }

    ARQUIVO_SAIDA.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Gerados {len(participantes)} participantes fictícios.")
    print(f"Testes disponíveis: {len(catalogo)}.")
    print(f"Avaliações: {len(avaliacoes)}; resultados: {len(resultados_testes)}.")


if __name__ == "__main__":
    main()
