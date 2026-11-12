from uuid import UUID
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    # A avaliação já vem pela URL; opcional para manter compatibilidade com clientes antigos.
    avaliacao_id: str | None = None
    teste_id: int = Field(gt=0)
    lado: Lado
    resultado: Resultado
    dor_0_10: int | None = Field(default=None, ge=0, le=10)
    valor_medido: float | None = Field(default=None, ge=0, le=999)
    observacoes: str | None = Field(default=None, max_length=500)


class ParticipanteEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Sem código: o banco gera P-001, P-002... (único por avaliador).
    codigo: str | None = Field(default=None, min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    # Opcionais (ADR-049): ficam só em `participantes`; nunca vão para dashboard, CSV ou IA.
    nome: str | None = Field(default=None, max_length=60)
    sobrenome: str | None = Field(default=None, max_length=80)
    idade: int = Field(gt=0, lt=120)
    peso_kg: float | None = Field(default=None, gt=0, lt=400)
    altura_m: float | None = Field(default=None, ge=0.5, le=2.5)
    consentimento: bool = False
    data_consentimento: datetime | None = None
    termo_versao: str | None = Field(default=None, max_length=30)
    consentimento_responsavel: bool = False

    @field_validator("nome", "sobrenome", mode="before")
    @classmethod
    def _limpar_nome(cls, v):
        if isinstance(v, str):
            v = " ".join(v.split())
            return v or None
        return v

    @model_validator(mode="after")
    def validar_consentimento(self) -> "ParticipanteEntrada":
        if not self.consentimento:
            raise ValueError("O consentimento é obrigatório antes de cadastrar.")
        if self.data_consentimento is None:
            raise ValueError("Consentimento marcado exige data_consentimento.")
        if not self.termo_versao:
            raise ValueError("Consentimento marcado exige a versão do termo aceito.")
        if self.idade < 18 and not self.consentimento_responsavel:
            raise ValueError("Participante menor de 18 anos exige a ciência do responsável legal.")
        return self


class AvaliacaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    participante_id: UUID


class TesteCatalogo(BaseModel):
    """Linha de testes_catalogo. `regiao` é texto livre: novos testes entram só no banco (ORT-45)."""
    id: int = Field(gt=0)
    regiao: str = Field(min_length=1, max_length=50)
    nome: str = Field(min_length=1, max_length=100)
    estrutura: str | None = Field(default=None, max_length=150)
    definicao: str = Field(min_length=1)
    objetivo: str = Field(min_length=1)
    como_fazer: str = Field(min_length=1)
    positivo_se: str = Field(min_length=1)
    unidade_medida: str | None = Field(default=None, max_length=20)
    referencia: str | None = None
    ativo: bool = True


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
            raise ValueError("Rascunho aprovado exige revisado_por.")
        return self


class Papel(str, Enum):
    ALUNO = "aluno"
    PROFESSOR = "professor"


class Perfil(BaseModel):
    user_id: UUID
    nome_exibicao: str = Field(min_length=1)
    papel: Papel


class ParticipanteSaida(ParticipanteEntrada):
    codigo: str
    id: UUID
    user_id: UUID
    criado_em: datetime
    excluido_em: datetime | None = None  # o select * do banco traz a coluna; sem isso a resposta dava 500
    data_consentimento: datetime | None = None


class AvaliacaoSaida(AvaliacaoEntrada):
    id: UUID
    avaliador_id: UUID
    data_avaliacao: datetime
    flag_professor: bool = False
    flag_motivo: str | None = None
    status: str = "pendente"
    progresso_percentual: float = 0.0
    excluido_em: datetime | None = None


class ResultadoTesteSaida(ResultadoTeste):
    id: UUID
    criado_em: datetime | None = None
    excluido_em: datetime | None = None


class AvaliacaoSinalizar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motivo: str | None = Field(default=None, max_length=500)
