"""Arquivos locais do aparelho: sessão salva, cache e fila de envios pendentes.

Onde guarda (primeiro que existir):
  1. ORTHOTEST_DATA_DIR        (testes / configuração manual)
  2. FLET_APP_STORAGE_DATA     (pasta própria do app no Android/iOS: o sistema não apaga sozinho)
  3. ~/.orthotest             (computador)
  4. localStorage do navegador (versão web/PWA, quando disponível; senão só na memória da aba)
Gravação atômica e, onde o sistema permite, só o dono lê (0600), porque a sessão salva guarda o token de
acesso. A senha NUNCA é salva.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

PREFIXO_WEB = "orthotest:"
_memoria: dict[str, str] = {}  # último recurso (web sem localStorage): vale só enquanto a aba estiver aberta


def _web() -> bool:
    return sys.platform == "emscripten"


def _local_storage():
    """localStorage do navegador, ou None (ex.: Python rodando em Web Worker, que não tem localStorage)."""
    try:
        import js  # type: ignore  # só existe dentro do Pyodide
        return js.localStorage if js.localStorage is not None else None
    except Exception:
        return None


def pasta_dados() -> Path:
    base = os.getenv("ORTHOTEST_DATA_DIR") or os.getenv("FLET_APP_STORAGE_DATA")
    pasta = Path(base) if base else Path.home() / ".orthotest"
    try:
        pasta.mkdir(parents=True, exist_ok=True)
    except OSError:  # aparelho sem pasta gravável
        pasta = Path(tempfile.gettempdir()) / "orthotest"
        pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def ler_json(nome: str, padrao):
    if _web():
        ls = _local_storage()
        bruto = ls.getItem(PREFIXO_WEB + nome) if ls is not None else _memoria.get(nome)
        try:
            return json.loads(bruto) if bruto else padrao
        except ValueError:
            return padrao
    caminho = pasta_dados() / nome
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def gravar_json(nome: str, dados) -> None:
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    if _web():
        ls = _local_storage()
        if ls is not None:
            ls.setItem(PREFIXO_WEB + nome, texto)
        else:
            _memoria[nome] = texto
        return
    caminho = pasta_dados() / nome
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(texto, encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, caminho)  # atômico: nunca deixa o arquivo pela metade


def apagar(nome: str) -> None:
    if _web():
        ls = _local_storage()
        if ls is not None:
            ls.removeItem(PREFIXO_WEB + nome)
        _memoria.pop(nome, None)
        return
    try:
        (pasta_dados() / nome).unlink()
    except OSError:
        pass
