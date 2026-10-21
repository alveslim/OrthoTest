import pytest
import backend.schemas as schemas
from pydantic import ValidationError
from backend.schemas import ParticipanteEntrada, ResultadoTeste, AvaliacaoEntrada, RascunhoIA, Perfil


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

PARTICIPANTE_ID = "123e4567-e89b-12d3-a456-426614174000"


def test_avaliacao_aceita_id_de_participante_valido():
    avaliacao = AvaliacaoEntrada(participante_id=PARTICIPANTE_ID)

    assert str(avaliacao.participante_id) == PARTICIPANTE_ID


def test_avaliacao_rejeita_id_de_participante_invalido():
    with pytest.raises(ValidationError):
        AvaliacaoEntrada(participante_id="id-invalido")


@pytest.mark.parametrize("campo", ["avaliador_id", "status"])
def test_avaliacao_rejeita_campos_definidos_pelo_backend(campo):
    with pytest.raises(ValidationError):
        AvaliacaoEntrada.model_validate(
            {"participante_id": PARTICIPANTE_ID, campo: "valor-enviado"}
        )

CATALOGO_BASE = {
    "id": 1,
    "regiao": "Joelho",
    "nome": "Teste fictício",
    "definicao": "Descrição de exemplo",
    "objetivo": "Objetivo de exemplo",
    "como_fazer": "Procedimento de exemplo",
    "positivo_se": "Critério de exemplo",
}


def test_catalogo_aceita_registro_valido():
    teste = schemas.TesteCatalogo.model_validate(CATALOGO_BASE)

    assert teste.regiao.value == "Joelho"
    assert teste.estrutura is None
    assert teste.referencia is None


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("id", 0),
        ("regiao", "Região inexistente"),
        ("definicao", ""),
    ],
)
def test_catalogo_rejeita_valor_invalido(campo, valor):
    with pytest.raises(ValidationError):
        schemas.TesteCatalogo.model_validate({**CATALOGO_BASE, campo: valor})

RASCUNHO_BASE = {
    "id": "123e4567-e89b-12d3-a456-426614174001",
    "avaliacao_id": "123e4567-e89b-12d3-a456-426614174002",
    "texto": "Resumo fictício para revisão.",
    "gerado_em": "2026-10-21T10:00:00-04:00",
}


def test_rascunho_pendente_e_aceito():
    rascunho = RascunhoIA.model_validate(RASCUNHO_BASE)

    assert rascunho.aprovado is False
    assert rascunho.revisado_por is None


def test_rascunho_aprovado_com_revisor_e_aceito():
    rascunho = RascunhoIA.model_validate(
        {
            **RASCUNHO_BASE,
            "aprovado": True,
            "revisado_por": "123e4567-e89b-12d3-a456-426614174003",
        }
    )

    assert rascunho.aprovado is True


def test_rascunho_aprovado_sem_revisor_e_rejeitado():
    with pytest.raises(ValidationError, match="exige revisado_por"):
        RascunhoIA.model_validate({**RASCUNHO_BASE, "aprovado": True})


def test_rascunho_sem_texto_e_rejeitado():
    with pytest.raises(ValidationError):
        RascunhoIA.model_validate({**RASCUNHO_BASE, "texto": ""})

PERFIL_BASE = {
    "user_id": "123e4567-e89b-12d3-a456-426614174004",
    "nome_exibicao": "Avaliador 01",
    "papel": "aluno",
}


@pytest.mark.parametrize("papel", ["aluno", "professor"])
def test_perfil_aceita_papel_valido(papel):
    perfil = Perfil.model_validate({**PERFIL_BASE, "papel": papel})

    assert perfil.papel.value == papel


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("papel", "admin"),
        ("nome_exibicao", ""),
        ("user_id", "id-invalido"),
    ],
)
def test_perfil_rejeita_valor_invalido(campo, valor):
    with pytest.raises(ValidationError):
        Perfil.model_validate({**PERFIL_BASE, campo: valor})

@pytest.mark.parametrize(
    "modelo, dados",
    [
        (
            ParticipanteEntrada,
            {"codigo": "P-001", "idade": 19, "nome": "Exemplo fictício"},
        ),
        (
            ResultadoTeste,
            {**BASE, "status": "Completo"},
        ),
    ],
)
def test_entradas_rejeitam_campos_extras(modelo, dados):
    with pytest.raises(ValidationError):
        modelo.model_validate(dados)