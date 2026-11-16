"""Autenticação: valida o token no endpoint oficial do Supabase Auth.

Não valida JWT com segredo fixo: também funciona com chaves assimétricas (Signing Keys).
O papel (aluno/professor) vem da tabela `perfis`, lida com o próprio token do usuário.
"""
import hashlib
import os
import time

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)

# Cache curto em memória (por instância): evita ir ao Supabase Auth/perfis a CADA chamada da API; uma tela do app
# faz várias chamadas seguidas. Token revogado ou papel alterado passam a valer em até TTL segundos.
TTL_SESSAO = 30
TTL_PAPEL = 60
_MAX_CACHE = 512
_cache_sessao: dict[str, tuple[float, dict]] = {}
_cache_papel: dict[str, tuple[float, str]] = {}


def limpar_caches() -> None:
    _cache_sessao.clear()
    _cache_papel.clear()


def _guardar(cache: dict, chave: str, valor, ttl: int) -> None:
    agora = time.monotonic()
    if len(cache) >= _MAX_CACHE:  # nunca cresce sem limite: descarta o que expirou (ou tudo, se ainda estiver cheio)
        for k in [k for k, (exp, _) in cache.items() if exp <= agora]:
            cache.pop(k, None)
        if len(cache) >= _MAX_CACHE:
            cache.clear()
    cache[chave] = (agora + ttl, valor)


def validar(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação obrigatória.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    base_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not base_url or not anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase não configurado no backend.",
        )

    token = credentials.credentials
    chave = hashlib.sha256(token.encode()).hexdigest()  # o token em si nunca fica guardado
    em_cache = _cache_sessao.get(chave)
    if em_cache and em_cache[0] > time.monotonic():
        return dict(em_cache[1])
    try:
        response = requests.get(
            f"{base_url}/auth/v1/user",
            headers={"apikey": anon_key, "Authorization": f"Bearer {token}"},
            timeout=8,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível validar a sessão no Supabase Auth.",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada. Entre novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = response.json()
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="O Supabase não retornou uma identidade válida.",
        )

    resultado = {
        "sub": str(user_id),
        "email": user.get("email"),
        "app_metadata": user.get("app_metadata") or {},
        "access_token": token,
    }
    _guardar(_cache_sessao, chave, resultado, TTL_SESSAO)
    return dict(resultado)


def papel_do_usuario(payload: dict) -> str:
    """Lê o papel em `perfis` (RLS: cada um lê o próprio perfil). Sem perfil = aluno."""
    from backend.supabase_client import rest

    em_cache = _cache_papel.get(payload["sub"])
    if em_cache and em_cache[0] > time.monotonic():
        return em_cache[1]
    linhas = rest(
        "GET", "perfis", payload,
        params={"select": "papel", "user_id": f"eq.{payload['sub']}"},
    )
    papel = linhas[0]["papel"] if linhas else "aluno"
    _guardar(_cache_papel, payload["sub"], papel, TTL_PAPEL)
    return papel


def requer_professor(payload: dict = Depends(validar)) -> dict:
    """Autoriza ações exclusivas do professor."""
    if papel_do_usuario(payload) != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação permitida somente para usuário com papel de professor.",
        )
    return payload
