from uuid import UUID
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Resultado(str, Enum):
    POSITIVO = "Positivo"
    NEGATIVO = "Negativo"
    NAO_REALIZADO = "Não realizado"
    INCONCLUSIVO = "Inconclusivo"

class Lado(str, Enum):
    DIREITO = "Direito"
    ESQUERDO = "Esquerdo"
    BILATERAL = "Bilateral"

class ResultadoTeste(BaseModel):
    model_config = ConfigDict(extra="forbid")
    avaliacao_id: str
    teste_id: int
    lado: Lado
    resultado: Resultado
    dor_0_10: int | None = Field(default=None, ge=0, le=10)
    valor_medido: float | None = None
    observacoes: str | None = Field(default=None, max_length=500)

class ParticipanteEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str = Field(min_length=1, max_length=20)
    idade: int = Field(gt=0, lt=120)
    peso_kg: float | None = Field(default=None, gt=0)
    altura_m: float | None = Field(default=None, gt=0)
    consentimento: bool = False
    data_consentimento: datetime | None = None

    @model_validator(mode="after")
    def validar_consentimento(self) -> "ParticipanteEntrada":
        if self.consentimento and self.data_consentimento is None:
            raise ValueError("Consentimento marcado exige data_consentimento")
        return self

class AvaliacaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participante_id: UUID

class Regiao(str, Enum):
    JOELHO = "Joelho"
    TORNOZELO = "Tornozelo"
    OMBRO = "Ombro"
    PUNHO = "Punho"
    COLUNA = "Coluna"

class TesteCatalogo(BaseModel):
    id: int = Field(gt=0)
    regiao: Regiao
    nome: str = Field(min_length=1, max_length=100)
    estrutura: str | None = Field(default=None, max_length=100)
    definicao: str = Field(min_length=1)
    objetivo: str = Field(min_length=1)
    como_fazer: str = Field(min_length=1)
    positivo_se: str = Field(min_length=1)
    referencia: str | None = None

class RascunhoIA(BaseModel):
    id: UUID
    avaliacao_id: UUID
    texto: str = Field(min_length=1)
    gerado_em: datetime
    revisado_por: UUID | None = None
    aprovado: bool = False

    @model_validator(mode="after")
    def validar_aprovacao(self) -> "RascunhoIA":
        if self.aprovado and self.revisado_por is None:
            raise ValueError("Rascunho aprovado exige revisado_por")
        return self

class Papel(str, Enum):
    ALUNO = "aluno"
    PROFESSOR = "professor"


class Perfil(BaseModel):
    user_id: UUID
    nome_exibicao: str = Field(min_length=1)
    papel: Papel