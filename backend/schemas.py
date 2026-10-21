from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, model_validator

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
    avaliacao_id: str
    teste_id: int
    lado: Lado
    resultado: Resultado
    dor_0_10: int | None = Field(default=None, ge=0, le=10)
    valor_medido: float | None = None
    observacoes: str | None = Field(default=None, max_length=500)

class ParticipanteEntrada(BaseModel):
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