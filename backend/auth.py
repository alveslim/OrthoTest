"""Autenticação: valida o token no endpoint oficial do Supabase Auth.

Não valida JWT com segredo fixo: também funciona com chaves assimétricas (Signing Keys).
O papel (aluno/professor) vem da tabela `perfis`, lida com o próprio token do usuário.
"""
import os

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


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

    return {
        "sub": str(user_id),
        "email": user.get("email"),
        "app_metadata": user.get("app_metadata") or {},
        "access_token": token,
    }


def papel_do_usuario(payload: dict) -> str:
    """Lê o papel em `perfis` (RLS: cada um lê o próprio perfil). Sem perfil = aluno."""
    from backend.supabase_client import rest

    linhas = rest(
        "GET", "perfis", payload,
        params={"select": "papel", "user_id": f"eq.{payload['sub']}"},
    )
    return linhas[0]["papel"] if linhas else "aluno"


def requer_professor(payload: dict = Depends(validar)) -> dict:
    """Autoriza ações exclusivas do professor."""
    if papel_do_usuario(payload) != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação permitida somente para usuário com papel de professor.",
        )
    return payload
