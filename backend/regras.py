"""Motor determinístico de achados (ORT-31) e resumo estruturado sem LLM.

Só afirma o que está em ai/regras_clinicas.json. Teste sem regra => mensagem de ausência.
"""
import json
from pathlib import Path

ARQUIVO_REGRAS = Path(__file__).resolve().parent.parent / "ai" / "regras_clinicas.json"
NOTA_RASCUNHO = "NOTA: Este é um rascunho gerado por IA para revisão humana e não constitui diagnóstico clínico."


def carregar_regras(caminho: Path = ARQUIVO_REGRAS) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def gerar_achados(resultados: list[dict], base: dict | None = None) -> list[dict]:
    """`resultados`: linhas de resultados_testes com `regiao` e `nome` do teste já resolvidos."""
    base = base or carregar_regras()
    regras = {(r["regiao"], r["teste"], r["resultado_gatilho"]): r for r in base.get("regras", [])}
    fallback = base.get("ausencia_de_regra_confiavel", "Sem regra.")
    achados = []
    for res in resultados:
        if res.get("resultado") in ("Não realizado", "Negativo"):
            continue
        regiao, nome = res.get("regiao"), res.get("nome")
        regra = regras.get((regiao, nome, res.get("resultado")))
        achados.append({
            "teste_origem": f"{nome} ({regiao})",
            "lado": res.get("lado"),
            "resultado": res.get("resultado"),
            "achado": regra["achado_sugerido"] if regra else fallback,
            "referencia": regra["referencia_bibliografica"] if regra else "N/A",
            "referencia_verificada": bool(regra and regra.get("referencia_verificada")),
            "status": "Regra Aplicada" if regra else "Ausência de Regra",
        })
    return achados


def resumo_estruturado(achados: list[dict], idade, peso, altura) -> str:
    """Rascunho sem LLM: lista os achados das regras, sem interpretação adicional."""
    linhas = [f"Participante: {idade} anos, {peso} kg, {altura} m (dados desidentificados)."]
    if not achados:
        linhas.append("Nenhum teste positivo ou inconclusivo registrado até o momento.")
    for a in achados:
        linhas.append(f"- {a['teste_origem']}, lado {a['lado']}, {a['resultado']}: {a['achado']}")
    linhas += ["", NOTA_RASCUNHO]
    return "\n".join(linhas)
