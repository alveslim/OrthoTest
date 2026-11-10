"""Pontos que só aparecem no celular/navegador: onde guardar, de onde ler a configuração e o catálogo."""
import json
import sys
import types
from pathlib import Path

import armazenamento
import config
import estado

RAIZ = Path(__file__).resolve().parent.parent


def test_config_prioriza_ambiente_e_cai_no_arquivo_publico(monkeypatch, tmp_path):
    arq = tmp_path / "config_publica.json"
    arq.write_text(json.dumps({"API_BASE_URL": "https://api.exemplo.app/api/v1", "SUPABASE_URL": ""}), encoding="utf-8")
    monkeypatch.setattr(config, "ARQUIVO", arq)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    assert config.cfg("API_BASE_URL") == "https://api.exemplo.app/api/v1"
    monkeypatch.setenv("API_BASE_URL", "http://localhost:9000")
    assert config.cfg("API_BASE_URL") == "http://localhost:9000"
    assert config.cfg("SUPABASE_URL", "padrao") == "padrao"  # vazio no arquivo -> padrão
    monkeypatch.setattr(config, "ARQUIVO", tmp_path / "nao_existe.json")
    assert config.cfg("QUALQUER", "x") == "x"


def test_arquivo_publico_nao_tem_segredos():
    dados = json.loads((RAIZ / "app" / "config_publica.json").read_text(encoding="utf-8"))
    assert set(dados) == {"SUPABASE_URL", "SUPABASE_ANON_KEY", "API_BASE_URL", "TERMO_CONTATO"}
    chave = dados["SUPABASE_ANON_KEY"]
    assert chave.startswith("sb_publishable_") or (chave.startswith("eyJ") and '"role":"anon"' in
                                                    __import__("base64").urlsafe_b64decode(chave.split(".")[1] + "==").decode().replace(" ", ""))
    assert "service_role" not in json.dumps(dados)


def test_celular_usa_a_pasta_propria_do_app(monkeypatch, tmp_path):
    monkeypatch.delenv("ORTHOTEST_DATA_DIR", raising=False)
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path / "flet_data"))
    armazenamento.gravar_json("sessao.json", {"a": 1})
    assert (tmp_path / "flet_data" / "sessao.json").exists()
    assert armazenamento.ler_json("sessao.json", None) == {"a": 1}


def test_catalogo_local_fica_dentro_da_pasta_app():
    assert estado.CATALOGO_LOCAL.parent.name == "app" and estado.CATALOGO_LOCAL.exists()
    assert len(estado._catalogo_local()) == 19


class _LocalStorageFalso:
    def __init__(self):
        self.d = {}

    def getItem(self, k):
        return self.d.get(k)

    def setItem(self, k, v):
        self.d[k] = v

    def removeItem(self, k):
        self.d.pop(k, None)


def test_versao_web_guarda_no_localstorage_do_navegador(monkeypatch):
    ls = _LocalStorageFalso()
    monkeypatch.setitem(sys.modules, "js", types.SimpleNamespace(localStorage=ls))
    monkeypatch.setattr(sys, "platform", "emscripten")
    armazenamento.gravar_json("sessao.json", {"token": "x"})
    assert "orthotest:sessao.json" in ls.d
    assert armazenamento.ler_json("sessao.json", None) == {"token": "x"}
    armazenamento.apagar("sessao.json")
    assert armazenamento.ler_json("sessao.json", "vazio") == "vazio"


def test_versao_web_sem_localstorage_usa_memoria_da_aba(monkeypatch):
    monkeypatch.setitem(sys.modules, "js", types.SimpleNamespace(localStorage=None))  # ex.: Web Worker
    monkeypatch.setattr(sys, "platform", "emscripten")
    armazenamento.gravar_json("fila.json", [1, 2])
    assert armazenamento.ler_json("fila.json", None) == [1, 2]
    armazenamento.apagar("fila.json")


def test_arquivos_de_deploy_do_vercel_sao_validos():
    v = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))
    assert v["rewrites"][0]["destination"] == "/api/index" and v["functions"]["api/index.py"]["maxDuration"] == 60
    # O Vercel instala a partir do pyproject.toml (tem prioridade): precisa ter a API e não o Flet.
    py = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    deps = py.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert "fastapi" in deps and "flet" not in deps and "pandas" not in deps  # backend leve no serverless
    assert "flet==" in (RAIZ / "app" / "requirements.txt").read_text(encoding="utf-8")  # o app usa este arquivo (flet build)
    assert "backend.main" in (RAIZ / "api" / "index.py").read_text(encoding="utf-8")
