import pytest


@pytest.fixture(autouse=True)
def pasta_dados_isolada(monkeypatch, tmp_path):
    """Cada teste usa uma pasta de dados própria: nunca toca na sessão/fila reais do aparelho."""
    monkeypatch.setenv("ORTHOTEST_DATA_DIR", str(tmp_path / "dados"))


@pytest.fixture(autouse=True)
def limpar_caches_do_backend():
    """O backend guarda sessão/papel em cache curto na memória; cada teste começa sem cache."""
    import sys
    yield
    auth = sys.modules.get("backend.auth")
    if auth is not None and hasattr(auth, "limpar_caches"):
        auth.limpar_caches()
