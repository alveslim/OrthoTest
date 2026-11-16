"""Substituto mínimo do FastAPI (só para importar os módulos do backend em ambientes sem o pacote real)."""
import types


def fastapi_falso():
    fa = types.ModuleType("fastapi")

    class APIRouter:
        def __init__(self, *a, **k):
            pass

        def _deco(self, *a, **k):
            return lambda f: f

        get = post = patch = delete = put = _deco

    class HTTPException(Exception):
        def __init__(self, status_code=500, detail=None, headers=None):
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
