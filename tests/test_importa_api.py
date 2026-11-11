"""Garante que a API importa por inteiro (era o que quebrava no Vercel: NameError ao importar as rotas).

O FastAPI real não precisa estar instalado: usamos um substituto mínimo só para executar o corpo do módulo,
onde os decoradores avaliam `response_model=...` (nomes não importados estouram aqui).
"""
import importlib
import sys
import types


def _fastapi_falso():
    fa = types.ModuleType("fastapi")

    class APIRouter:
        def __init__(self, *a, **k):
            pass

        def _deco(self, *a, **k):
            return lambda f: f

        get = post = patch = delete = put = _deco

    class HTTPException(Exception):
        def __init__(self, status_code=500, detail=None):
            super().__init__(detail)

    fa.APIRouter, fa.HTTPException = APIRouter, HTTPException
    fa.Depends = lambda *a, **k: None
    fa.Query = lambda *a, **k: None
    fa.status = types.SimpleNamespace(**{n: 0 for n in (
        "HTTP_200_OK", "HTTP_201_CREATED", "HTTP_400_BAD_REQUEST", "HTTP_401_UNAUTHORIZED",
        "HTTP_403_FORBIDDEN", "HTTP_404_NOT_FOUND", "HTTP_409_CONFLICT", "HTTP_422_UNPROCESSABLE_ENTITY",
        "HTTP_502_BAD_GATEWAY", "HTTP_503_SERVICE_UNAVAILABLE", "HTTP_204_NO_CONTENT")})
    sec = types.ModuleType("fastapi.security")
    sec.HTTPBearer = lambda *a, **k: (lambda *x, **y: None)
    sec.HTTPAuthorizationCredentials = type("HTTPAuthorizationCredentials", (), {})
    return fa, sec


def test_rotas_da_api_importam_sem_nameerror(monkeypatch):
    try:
        import fastapi  # noqa: F401  (se o real existir, usa o real)
    except ImportError:
        fa, sec = _fastapi_falso()
        monkeypatch.setitem(sys.modules, "fastapi", fa)
        monkeypatch.setitem(sys.modules, "fastapi.security", sec)
    for nome in [n for n in sys.modules if n.startswith("backend.routers") or n in ("backend.auth", "backend.supabase_client")]:
        monkeypatch.delitem(sys.modules, nome, raising=False)
    modulo = importlib.import_module("backend.routers.api")
    assert hasattr(modulo, "router")
