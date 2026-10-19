from enum import Enum
from pydantic import BaseModel, Field

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
