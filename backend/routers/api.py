from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from backend.schemas import (
    ParticipanteEntrada, ParticipanteSaida,
    AvaliacaoEntrada, AvaliacaoSaida,
    ResultadoTeste, TesteCatalogo
)
from backend.auth import validar_token

router = APIRouter(prefix='/api/v1', tags=["OrthoTest"])

# ----------------
# catalogo 
# ----------------

@router.get('catalogo/testes', response_model=List[TesteCatalogo])
def listar_catalogo_testes(user_payload: dict = Depends(validar_token)):
    """Retorna a lista dos 16 testes ortopedicos do catalogo"""
    # TODO: logica de chamada ao supabase: supabase.table('testes_catalogo').select('*').execute()
    return[]

# ---------------
# participantes
# ---------------

@router.get("/participantes", response_model=ParticipanteSaida, status_code=status.HTTP_201_CREATED)
def criar_participante(participante: ParticipanteEntrada, user_payload: dict = Depends(validar_token)):
    """registra novo participante vinculado ao avaliador"""
    # extrair o ID do utiliador autenticado: user_id = payload.get("sub")
    pass

@router.get("/participantes", response_model=List[ParticipanteSaida])
def listar_participantes(user_payload: dict = Depends(validar_token)):
    """lista os participandtes, o rls do supabase garantira que o aluno vai ser apenas os seus"""
    pass

# ---------------
# avaliacoes e resultados
# ---------------


@router.post("/avaliacoes", response_model=AvaliacaoSaida, status_code=status.HTTP_201_CREATED)
def iniciar_avaliacao(avaliacao: AvaliacaoEntrada, user_payload: dict = Depends(validar_token)):
    """cria uma nova ficha de avaliação para um participante."""
    pass

@router.get("/avaliacoes", response_model=List[AvaliacaoSaida])
def listar_avaliacoes(user_payload: dict = Depends(validar_token)):
    """lista avaliações do utilizador atual."""
    pass

@router.post("/avaliacoes/{avaliacao_id}/resultados", status_code=status.HTTP_201_CREATED)
def registar_resultado_teste(
    avaliacao_id: UUID, 
    resultado: ResultadoTeste, 
    user_payload: dict = Depends(validar_token)
):
    """regista o resultado de um teste específico dentro de uma avaliação."""
    pass

# importar o novo schema no topo do ficheiro (OU ONDE TIVER OS RESTANTES IMPORTS)
from backend.schemas import AvaliacaoSinalizar

@router.post("/avaliacoes/{avaliacao_id}/sinalizar", status_code=status.HTTP_200_OK)
def sinalizar_avaliacao(
    avaliacao_id: UUID,
    sinalizacao: AvaliacaoSinalizar,
    user_payload: dict = Depends(validar_token)
):
    return {"mensagem": "Avaliação sinalizada com sucesso para o professor."}