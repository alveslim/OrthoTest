import os
from typing import List
from uuid import UUID
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import create_client, Client

from backend.schemas import (
    ParticipanteEntrada,
    ParticipanteSaida,
    AvaliacaoEntrada,
    AvaliacaoSaida,
    AvaliacaoSinalizar,
    ResultadoTeste,
    TesteCatalogo,
)
# Importa validar e cria um alias caso seu auth.py use um dos dois nomes
try:
    from backend.auth import validar as validar_auth
except ImportError:
    from backend.auth import validar_token as validar_auth

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# Usa a chave disponivel no backend (.env) para comunicar com o Supabase
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

def obter_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Variáveis SUPABASE_URL e SUPABASE_KEY não configuradas no .env",
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter(prefix="/api/v1", tags=["OrthoTest"])


# ----------------
# CATÁLOGO
# ----------------
@router.get("/catalogo/testes", response_model=List[TesteCatalogo])
def listar_catalogo_testes(user_payload: dict = Depends(validar_auth)):
    """Retorna a lista dos testes ortopédicos do catálogo."""
    sb = obter_supabase()
    resposta = sb.table("testes_catalogo").select("*").order("id").execute()
    return resposta.data


# ----------------
# PARTICIPANTES
# ----------------
@router.post("/participantes", response_model=ParticipanteSaida, status_code=status.HTTP_201_CREATED)
def criar_participante(
    participante: ParticipanteEntrada,
    user_payload: dict = Depends(validar_auth),
):
    """Registra novo participante vinculado ao avaliador autenticado."""
    sb = obter_supabase()
    user_id = user_payload.get("sub")
    dados = participante.model_dump(mode="json", exclude_none=True)
    dados["user_id"] = user_id

    resposta = sb.table("participantes").insert(dados).execute()
    if not resposta.data:
        raise HTTPException(status_code=400, detail="Não foi possível criar o participante.")
    return resposta.data[0]


@router.get("/participantes", response_model=List[ParticipanteSaida])
def listar_participantes(user_payload: dict = Depends(validar_auth)):
    """Lista os participantes do avaliador autenticado."""
    sb = obter_supabase()
    user_id = user_payload.get("sub")
    resposta = (
        sb.table("participantes")
        .select("*")
        .eq("user_id", user_id)
        .order("criado_em", desc=True)
        .execute()
    )
    return resposta.data


# ----------------
# AVALIAÇÕES E RESULTADOS
# ----------------
@router.post("/avaliacoes", response_model=AvaliacaoSaida, status_code=status.HTTP_201_CREATED)
def iniciar_avaliacao(
    avaliacao: AvaliacaoEntrada,
    user_payload: dict = Depends(validar_auth),
):
    """Cria uma nova ficha de avaliação para um participante."""
    sb = obter_supabase()
    user_id = user_payload.get("sub")
    dados = {
        "participante_id": str(avaliacao.participante_id),
        "avaliador_id": user_id,
        "status": "pendente",
        "progresso_percentual": 0.0,
    }
    resposta = sb.table("avaliacoes").insert(dados).execute()
    if not resposta.data:
        raise HTTPException(status_code=400, detail="Erro ao iniciar avaliação.")
    return resposta.data[0]


@router.get("/avaliacoes", response_model=List[AvaliacaoSaida])
def listar_avaliacoes(user_payload: dict = Depends(validar_auth)):
    """Lista avaliações do utilizador atual."""
    sb = obter_supabase()
    user_id = user_payload.get("sub")
    resposta = (
        sb.table("avaliacoes")
        .select("*")
        .eq("avaliador_id", user_id)
        .execute()
    )
    return resposta.data


@router.post("/avaliacoes/{avaliacao_id}/resultados", status_code=status.HTTP_201_CREATED)
def registar_resultado_teste(
    avaliacao_id: UUID,
    resultado: ResultadoTeste,
    user_payload: dict = Depends(validar_auth),
):
    """Regista ou atualiza o resultado de um teste específico e recalcula o progresso."""
    sb = obter_supabase()
    dados = resultado.model_dump(mode="json", exclude_none=True)
    dados["avaliacao_id"] = str(avaliacao_id)

    # Verifica se já existe resultado para este teste nesta avaliação
    existente = (
        sb.table("resultados_testes")
        .select("id")
        .eq("avaliacao_id", str(avaliacao_id))
        .eq("teste_id", resultado.teste_id)
        .execute()
    )

    if existente.data:
        sb.table("resultados_testes").update(dados).eq("id", existente.data[0]["id"]).execute()
    else:
        sb.table("resultados_testes").insert(dados).execute()

    # Atualiza o progresso da avaliação
    total_cat = sb.table("testes_catalogo").select("id", count="exact").execute()
    total_res = (
        sb.table("resultados_testes")
        .select("id", count="exact")
        .eq("avaliacao_id", str(avaliacao_id))
        .execute()
    )
    n_cat = total_cat.count or len(total_cat.data) or 16
    n_res = total_res.count or len(total_res.data) or 0
    perc = round((n_res / n_cat) * 100, 1) if n_cat > 0 else 0.0
    novo_status = "concluido" if n_res >= n_cat else ("em_andamento" if n_res > 0 else "pendente")

    sb.table("avaliacoes").update({
        "progresso_percentual": perc,
        "status": novo_status,
    }).eq("id", str(avaliacao_id)).execute()

    return {
        "mensagem": "Resultado salvo com sucesso.",
        "progresso_percentual": perc,
        "status": novo_status,
    }


@router.get("/avaliacoes/{avaliacao_id}/resultados")
def listar_resultados_avaliacao(
    avaliacao_id: UUID,
    user_payload: dict = Depends(validar_auth),
):
    """Retorna os resultados já gravados para uma avaliação específica."""
    sb = obter_supabase()
    resposta = (
        sb.table("resultados_testes")
        .select("*")
        .eq("avaliacao_id", str(avaliacao_id))
        .execute()
    )
    return resposta.data


@router.post("/avaliacoes/{avaliacao_id}/sinalizar", status_code=status.HTTP_200_OK)
def sinalizar_avaliacao(
    avaliacao_id: UUID,
    sinalizacao: AvaliacaoSinalizar,
    user_payload: dict = Depends(validar_auth),
):
    """Sinaliza uma avaliação para revisão do professor."""
    sb = obter_supabase()
    sb.table("avaliacoes").update({
        "flag_professor": True,
        "flag_motivo": sinalizacao.motivo,
    }).eq("id", str(avaliacao_id)).execute()

    return {"mensagem": "Avaliação sinalizada com sucesso para o professor."}