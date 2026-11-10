"""Gera docs/termo_consentimento.md (versão para imprimir, Plano B) a partir de app/termo.py."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "app"))

from termo import termo_markdown  # noqa: E402

destino = RAIZ / "docs" / "termo_consentimento.md"
destino.write_text(termo_markdown(), encoding="utf-8")
print(f"Gerado: {destino}")
