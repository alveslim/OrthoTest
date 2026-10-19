import pytest
from pydantic import ValidationError
from backend.schemas import ResultadoTeste

BASE = dict(avaliacao_id="a1", teste_id=1, lado="Direito", resultado="Positivo")

def test_dor_acima_de_10_e_rejeitada():
    with pytest.raises(ValidationError):
        ResultadoTeste(**BASE, dor_0_10=11)

def test_lado_invalido_e_rejeitado():
    with pytest.raises(ValidationError):
        ResultadoTeste(**{**BASE, "lado": "Frente"})

def test_nao_realizado_sem_dor_e_aceito():
    r = ResultadoTeste(**{**BASE, "resultado": "Não realizado"})
    assert r.dor_0_10 is None