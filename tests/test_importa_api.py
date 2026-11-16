"""Garante que a API importa por inteiro (era o que quebrava no Vercel: NameError ao importar as rotas).

O FastAPI real não precisa estar instalado: usamos um substituto mínimo só para executar o corpo do módulo,
onde os decoradores avaliam `response_model=...` (nomes não importados estouram aqui).
"""
import importlib
import sys

from fake_fastapi import fastapi_falso


def test_rotas_da_api_importam_sem_nameerror(monkeypatch):
    try:
        import fastapi  # noqa: F401  (se o real existir, usa o real)
    except ImportError:
        fa, sec = fastapi_falso()
        monkeypatch.setitem(sys.modules, "fastapi", fa)
        monkeypatch.setitem(sys.modules, "fastapi.security", sec)
    for nome in [n for n in sys.modules if n.startswith("backend.routers") or n in ("backend.auth", "backend.supabase_client")]:
        monkeypatch.delitem(sys.modules, nome, raising=False)
    modulo = importlib.import_module("backend.routers.api")
    assert hasattr(modulo, "router")
