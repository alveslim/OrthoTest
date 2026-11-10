"""Arquivos locais do aparelho: sessão salva, cache e fila de envios pendentes.

Pasta padrão: ~/.orthotest (ou a definida em ORTHOTEST_DATA_DIR). Gravação atômica e, onde o sistema
permite, só o dono lê (0600), porque a sessão salva guarda o token de acesso. A senha NUNCA é salva.
"""
import json
import os
import tempfile
from pathlib import Path


def pasta_dados() -> Path:
    base = os.getenv("ORTHOTEST_DATA_DIR")
    pasta = Path(base) if base else Path.home() / ".orthotest"
    try:
        pasta.mkdir(parents=True, exist_ok=True)
    except OSError:  # aparelho sem home gravável (ex.: alguns builds móveis)
        pasta = Path(tempfile.gettempdir()) / "orthotest"
        pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def ler_json(nome: str, padrao):
    caminho = pasta_dados() / nome
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def gravar_json(nome: str, dados) -> None:
    caminho = pasta_dados() / nome
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, caminho)  # atômico: nunca deixa o arquivo pela metade


def apagar(nome: str) -> None:
    try:
        (pasta_dados() / nome).unlink()
    except OSError:
        pass
