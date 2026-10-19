"""Gera dados inteiramente fictícios para desenvolvimento."""

import argparse
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

# Probabilidade de resultado positivo, em porcentagem,
# seguindo a mesma ordem dos testes definidos em TESTES.
TAXAS_POSITIVO = (
    12, 18, 25, 30,
    15, 22, 28, 20,
    32, 14, 24, 35,
    17, 27, 11, 21,
)

def gerar_participantes(
    gerador: random.Random, 
    total: int = TOTAL_PARTICIPANTES
    ) -> list[dict]:
    participantes = []

    for numero in range(1, total + 1):
        idade = gerador.randint(18, 60)
        altura = round(gerador.uniform(1.45, 2.00), 2)

        # Usamos uma margem para evitar que o arredondamento
        # do peso faça o IMC ultrapassar os limites.
        imc_alvo = gerador.uniform(17.2, 34.8)
        peso = round(imc_alvo * altura**2, 1)

        participantes.append(
            {
                "id": f"PART-{numero:03d}",
                "codigo": f"P-{numero:03d}",
                "idade": idade,
                "peso_kg": peso,
                "altura_m": altura,
                "consentimento": True,
                "data_consentimento": "2026-10-17",
                "criado_em": "2026-10-17T09:00:00",
                "ficticio": True,
            }
        )

    return participantes


def gerar_avaliacoes_e_resultados(
    participantes: list[dict],
    gerador: random.Random,
) -> tuple[list[dict], list[dict]]:
    avaliacoes = []
    resultados_testes = []

    for numero, participante in enumerate(participantes, start=1):
        avaliacao_id = f"A-{numero:03d}"

        # Cria uma avaliação relacionada ao participante.
        avaliacoes.append(
            {
                "id": avaliacao_id,
                "participante_id": participante["id"],
                "avaliador_id": "AV-001",
                "data_avaliacao": "2026-10-18",
                "flag_professor": False,
                "flag_motivo": None,
                "ficticio": True,
            }
        )

        # Registra todos os testes para cada avaliação.
        for indice in range(len(TESTES)):
            taxa_positiva = TAXAS_POSITIVO[indice]

            resultado = gerador.choices(
                RESULTADOS,
                weights=(
                    85 - taxa_positiva,
                    taxa_positiva,
                    8,
                    7,
                ),
                k=1,
            )[0]

            # A dor depende do resultado sorteado.
            if resultado == "Positivo":
                dor = gerador.randint(3, 8)
            else:
                dor = gerador.randint(0, 2)

            resultados_testes.append(
                {
                    "avaliacao_id": avaliacao_id,
                    "teste_id": f"T-{indice + 1:02d}",
                    "lado": gerador.choice(LADOS),
                    "resultado": resultado,
                    "dor_0_10": dor,
                    "valor_medido": None,
                    "observacoes": None,
                    "ficticio": True,
                }
            )

    return avaliacoes, resultados_testes

def ler_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera dados fictícios para o OrthoCheck."
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semente para reproduzir os mesmos dados.",
    )

    parser.add_argument(
        "--n",
        type=int,
        default=60,
        help="Quantidade de participantes.",
    )

    args = parser.parse_args()

    if args.n < 1:
        parser.error("--n deve ser maior que zero.")

    return args

def main() -> None:
    args = ler_argumentos()
    gerador = random.Random(args.seed)
    participantes = gerar_participantes(gerador, total=args.n)
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
