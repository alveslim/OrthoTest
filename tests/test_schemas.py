import pytest
from pydantic import ValidationError
from backend.schemas import ParticipanteEntrada, ResultadoTeste

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

def test_participante_valido_com_consentimento():
    participante = ParticipanteEntrada(
        codigo="P-001",
        idade=19,
        peso_kg=65,
        altura_m=1.70,
        consentimento=True,
        data_consentimento="2026-10-21T10:00:00-04:00",
    )

    assert participante.codigo == "P-001"
    assert participante.consentimento is True


def test_participante_com_idade_zero_e_rejeitado():
    with pytest.raises(ValidationError):
        ParticipanteEntrada(codigo="P-002", idade=0)


def test_consentimento_sem_data_e_rejeitado():
    with pytest.raises(ValidationError, match="exige data_consentimento"):
        ParticipanteEntrada(
            codigo="P-003",
            idade=20,
            consentimento=True,
        )