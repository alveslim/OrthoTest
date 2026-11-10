"""Gera database/seed_catalogo.sql a partir de database/catalogo_testes.json.

O JSON é a fonte única dos textos das fichas clínicas (docs/ dos grupos).
Uso: python scripts/gerar_seed_catalogo.py
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "database" / "catalogo_testes.json"
DESTINO = RAIZ / "database" / "seed_catalogo.sql"
CAMPOS = ("id", "regiao", "nome", "estrutura", "definicao", "objetivo",
          "como_fazer", "positivo_se", "unidade_medida", "referencia")


def literal(valor) -> str:
    if valor is None:
        return "NULL"
    if isinstance(valor, int):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def main() -> None:
    testes = json.loads(ORIGEM.read_text(encoding="utf-8"))
    linhas = [
        "-- GERADO por scripts/gerar_seed_catalogo.py a partir de database/catalogo_testes.json.",
        "-- Não edite à mão. Idempotente: pode ser executado mais de uma vez.",
        f"INSERT INTO testes_catalogo ({', '.join(CAMPOS)}) VALUES",
    ]
    valores = ["  (" + ", ".join(literal(t.get(c)) for c in CAMPOS) + ")" for t in testes]
    linhas.append(",\n".join(valores))
    atualiza = ", ".join(f"{c} = EXCLUDED.{c}" for c in CAMPOS if c != "id")
    linhas.append(f"ON CONFLICT (id) DO UPDATE SET {atualiza};")
    linhas.append("SELECT setval(pg_get_serial_sequence('testes_catalogo', 'id'), (SELECT max(id) FROM testes_catalogo));")
    DESTINO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"{len(testes)} testes gravados em {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
