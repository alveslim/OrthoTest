"""Configuração do app: variável de ambiente (.env) tem prioridade; senão vale app/config_publica.json.

O celular não tem .env. Por isso os valores PÚBLICOS (URL do Supabase, chave publishable/anon e a URL da
API) vão em `app/config_publica.json`, que entra dentro do app. NUNCA coloque ali a chave service_role
nem senhas: tudo que está dentro de um app instalado pode ser extraído por quem o tiver.
"""
import json
import os
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "config_publica.json"


def _do_arquivo() -> dict:
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def cfg(nome: str, padrao: str = "") -> str:
    valor = os.getenv(nome)
    if valor not in (None, ""):
        return valor
    return str(_do_arquivo().get(nome) or padrao)
