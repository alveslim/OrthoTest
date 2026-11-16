"""Cache curto de sessão/papel: menos idas ao Supabase por chamada da API, sem guardar o token em claro."""
import importlib
import sys
import types

import pytest
from fake_fastapi import fastapi_falso


@pytest.fixture
def auth(monkeypatch):
    try:
        import fastapi  # noqa: F401
    except ImportError:
        fa, sec = fastapi_falso()
        monkeypatch.setitem(sys.modules, "fastapi", fa)
        monkeypatch.setitem(sys.modules, "fastapi.security", sec)
    monkeypatch.delitem(sys.modules, "backend.auth", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    modulo = importlib.import_module("backend.auth")
    yield modulo
    monkeypatch.delitem(sys.modules, "backend.auth", raising=False)


class _Resp:
    status_code = 200

    def json(self):
        return {"id": "11111111-1111-1111-1111-111111111111", "email": "a@b.com", "app_metadata": {}}


def _cred(token):
    return types.SimpleNamespace(scheme="Bearer", credentials=token)


def test_validar_consulta_o_supabase_uma_vez_por_token(auth, monkeypatch):
    chamadas = []
    monkeypatch.setattr(auth.requests, "get", lambda *a, **k: chamadas.append(1) or _Resp())
    r1 = auth.validar(_cred("tok-1"))
    r2 = auth.validar(_cred("tok-1"))
    assert r1 == r2 and r1["access_token"] == "tok-1" and len(chamadas) == 1
    auth.validar(_cred("tok-2"))  # outro token: consulta de novo
    assert len(chamadas) == 2
    assert all("tok-1" not in k for k in auth._cache_sessao)  # chave é hash, não o token


def test_cache_expira(auth, monkeypatch):
    chamadas = []
    monkeypatch.setattr(auth.requests, "get", lambda *a, **k: chamadas.append(1) or _Resp())
    relogio = [1000.0]
    monkeypatch.setattr(auth.time, "monotonic", lambda: relogio[0])
    auth.validar(_cred("t"))
    relogio[0] += auth.TTL_SESSAO + 1
    auth.validar(_cred("t"))
    assert len(chamadas) == 2


def test_token_invalido_nao_vai_para_o_cache(auth, monkeypatch):
    resp = _Resp()
    resp.status_code = 401
    monkeypatch.setattr(auth.requests, "get", lambda *a, **k: resp)
    with pytest.raises(Exception):
        auth.validar(_cred("ruim"))
    assert not auth._cache_sessao


def test_papel_em_cache(auth, monkeypatch):
    import backend.supabase_client as sc
    chamadas = []
    monkeypatch.setattr(sc, "rest", lambda *a, **k: chamadas.append(1) or [{"papel": "professor"}])
    p = {"sub": "u1", "access_token": "t"}
    assert auth.papel_do_usuario(p) == "professor" and auth.papel_do_usuario(p) == "professor"
    assert len(chamadas) == 1


def test_cache_tem_limite(auth):
    for i in range(auth._MAX_CACHE + 5):
        auth._guardar(auth._cache_papel, f"u{i}", "aluno", 60)
    assert len(auth._cache_papel) <= auth._MAX_CACHE
