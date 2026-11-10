"""Acesso ao Supabase (PostgREST + Storage) SEMPRE com o token do usuário.

Assim as políticas RLS valem em toda requisição: o aluno só enxerga o que criou e o
professor enxerga tudo. A chave `service_role` não é usada pelo backend.
"""
import os

import requests
from fastapi import HTTPException

TIMEOUT = 10


def base_url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


def _anon_key() -> str:
    return os.getenv("SUPABASE_ANON_KEY", "")


def headers(user: dict, prefer: str | None = None, content_type: str | None = "application/json") -> dict:
    if not base_url() or not _anon_key():
        raise HTTPException(503, "Supabase não configurado no backend (SUPABASE_URL / SUPABASE_ANON_KEY).")
    h = {"apikey": _anon_key(), "Authorization": f"Bearer {user['access_token']}"}
    if content_type:
        h["Content-Type"] = content_type
    if prefer:
        h["Prefer"] = prefer
    return h


def _detalhe(resp: requests.Response) -> str:
    try:
        corpo = resp.json()
        return str(corpo.get("message") or corpo.get("error") or corpo)
    except ValueError:
        return resp.text[:300] or f"Erro {resp.status_code} no banco de dados."


def _status_http(codigo: int) -> int:
    if codigo in (401, 403, 404, 409):
        return codigo
    if codigo == 429:
        return 429
    return 400 if 400 <= codigo < 500 else 502


def rest(
    metodo: str,
    tabela: str,
    user: dict,
    *,
    params: dict | None = None,
    json: object | None = None,
    prefer: str | None = None,
) -> list | dict | None:
    """Chama /rest/v1/<tabela>. Levanta HTTPException com a mensagem do banco se falhar."""
    try:
        resp = requests.request(
            metodo,
            f"{base_url()}/rest/v1/{tabela}",
            headers=headers(user, prefer),
            params=params,
            json=json,
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise HTTPException(503, "Banco de dados indisponível no momento.") from exc
    if resp.status_code >= 400:
        raise HTTPException(_status_http(resp.status_code), _detalhe(resp))
    return resp.json() if resp.content else None


def upload_storage(user: dict, bucket: str, caminho: str, conteudo: bytes, mime: str) -> None:
    try:
        resp = requests.post(
            f"{base_url()}/storage/v1/object/{bucket}/{caminho}",
            headers=headers(user, content_type=mime),
            data=conteudo,
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise HTTPException(503, "Storage indisponível no momento.") from exc
    if resp.status_code >= 400:
        raise HTTPException(_status_http(resp.status_code), _detalhe(resp))


def rest_todos(tabela: str, user: dict, params: dict | None = None, pagina: int = 1000) -> list:
    """GET paginado: o PostgREST limita cada resposta (padrão 1000 linhas)."""
    linhas: list = []
    inicio = 0
    while True:
        lote = rest("GET", tabela, user, params={**(params or {}), "limit": pagina, "offset": inicio}) or []
        linhas.extend(lote)
        if len(lote) < pagina:
            return linhas
        inicio += pagina
