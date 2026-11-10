import pytest


@pytest.fixture(autouse=True)
def pasta_dados_isolada(monkeypatch, tmp_path):
    """Cada teste usa uma pasta de dados própria: nunca toca na sessão/fila reais do aparelho."""
    monkeypatch.setenv("ORTHOTEST_DATA_DIR", str(tmp_path / "dados"))
