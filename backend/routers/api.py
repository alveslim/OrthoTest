import os
from typing import List
from uuid import UUID
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status

from backend.schemas import (
    ParticipanteEntrada,
    ParticipanteSaida,
    AvaliacaoEntrada,
    AvaliacaoSaida,
    AvaliacaoSinalizar,
    ResultadoTeste,
    TesteCatalogo,
)

try:
    from backend.auth import validar as validar_auth
except ImportError:
    from backend.auth import validar_token as validar_auth

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")


def _sb_headers(prefer: str = "return=representation") -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configure SUPABASE_URL e SUPABASE_ANON_KEY (ou SUPABASE_SERVICE_ROLE_KEY) no .env",
        )
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_url(tabela: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{tabela}"


router = APIRouter(prefix="/api/v1", tags=["OrthoTest"])


# ----------------
# CATÁLOGO
# ----------------
@router.get("/catalogo/testes", response_model=List[TesteCatalogo])
def listar_catalogo_testes(user_payload: dict = Depends(validar_auth)):
    """Retorna a lista dos testes ortopédicos do catálogo."""
    resp = requests.get(
        _sb_url("testes_catalogo"),
        headers=_sb_headers(),
        params={"select": "*", "order": "id.asc"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ----------------
# PARTICIPANTES
# ----------------
@router.post("/participantes", response_model=ParticipanteSaida, status_code=status.HTTP_201_CREATED)
def criar_participante(
    participante: ParticipanteEntrada,
    user_payload: dict = Depends(validar_auth),
):
    """Registra novo participante vinculado ao avaliador autenticado."""
    user_id = user_payload.get("sub")
    dados = participante.model_dump(mode="json", exclude_none=True)
    dados["user_id"] = user_id

    resp = requests.post(
        _sb_url("participantes"),
        headers=_sb_headers(),
        json=dados,
        timeout=10,
    )
    if resp.status_code not in (200, 201) or not resp.json():
        raise HTTPException(status_code=400, detail=f"Erro ao criar participante: {resp.text}")
    return resp.json()[0]


@router.get("/participantes", response_model=List[ParticipanteSaida])
def listar_participantes(user_payload: dict = Depends(validar_auth)):
    """Lista os participantes do avaliador autenticado."""
    user_id = user_payload.get("sub")
    resp = requests.get(
        _sb_url("participantes"),
        headers=_sb_headers(),
        params={"select": "*", "user_id": f"eq.{user_id}", "order": "criado_em.desc"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


# ----------------
# AVALIAÇÕES E RESULTADOS
# ----------------
@router.post("/avaliacoes", response_model=AvaliacaoSaida, status_code=status.HTTP_201_CREATED)
def iniciar_avaliacao(
    avaliacao: AvaliacaoEntrada,
    user_payload: dict = Depends(validar_auth),
):
    """Cria uma nova ficha de avaliação para um participante."""
    user_id = user_payload.get("sub")
    dados = {
        "participante_id": str(avaliacao.participante_id),
        "avaliador_id": user_id,
        "status": "pendente",
        "progresso_percentual": 0.0,
    }
    resp = requests.post(
        _sb_url("avaliacoes"),
        headers=_sb_headers(),
        json=dados,
        timeout=10,
    )
    if resp.status_code not in (200, 201) or not resp.json():
        raise HTTPException(status_code=400, detail=f"Erro ao iniciar avaliação: {resp.text}")
    return resp.json()[0]


@router.get("/avaliacoes", response_model=List[AvaliacaoSaida])
def listar_avaliacoes(user_payload: dict = Depends(validar_auth)):
    """Lista avaliações do utilizador atual."""
    user_id = user_payload.get("sub")
    resp = requests.get(
        _sb_url("avaliacoes"),
        headers=_sb_headers(),
        params={"select": "*", "avaliador_id": f"eq.{user_id}"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/avaliacoes/{avaliacao_id}/resultados", status_code=status.HTTP_201_CREATED)
def registar_resultado_teste(
    avaliacao_id: UUID,
    resultado: ResultadoTeste,
    user_payload: dict = Depends(validar_auth),
):
    """Regista ou atualiza o resultado de um teste específico e recalcula o progresso."""
    dados = resultado.model_dump(mode="json", exclude_none=True)
    dados["avaliacao_id"] = str(avaliacao_id)

    # Verifica se já existe resultado para este teste nesta avaliação
    check = requests.get(
        _sb_url("resultados_testes"),
        headers=_sb_headers(),
        params={
            "select": "id",
            "avaliacao_id": f"eq.{avaliacao_id}",
            "teste_id": f"eq.{resultado.teste_id}",
        },
        timeout=10,
    )
    existentes = check.json() if check.status_code == 200 else []

    if existentes:
        res_id = existentes[0]["id"]
        requests.patch(
            _sb_url("resultados_testes"),
            headers=_sb_headers(),
            params={"id": f"eq.{res_id}"},
            json=dados,
            timeout=10,
        )
    else:
        requests.post(
            _sb_url("resultados_testes"),
            headers=_sb_headers(),
            json=dados,
            timeout=10,
        )

    # Recalcula o progresso da avaliação
    cat_resp = requests.get(_sb_url("testes_catalogo"), headers=_sb_headers(), params={"select": "id"}, timeout=10)
    res_resp = requests.get(
        _sb_url("resultados_testes"),
        headers=_sb_headers(),
        params={"select": "id", "avaliacao_id": f"eq.{avaliacao_id}"},
        timeout=10,
    )
    n_cat = len(cat_resp.json()) if cat_resp.status_code == 200 and cat_resp.json() else 16
    n_res = len(res_resp.json()) if res_resp.status_code == 200 else 0

    perc = round((n_res / n_cat) * 100, 1) if n_cat > 0 else 0.0
    novo_status = "concluido" if n_res >= n_cat else ("em_andamento" if n_res > 0 else "pendente")

    requests.patch(
        _sb_url("avaliacoes"),
        headers=_sb_headers(),
        params={"id": f"eq.{avaliacao_id}"},
        json={"progresso_percentual": perc, "status": novo_status},
        timeout=10,
    )

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
    resp = requests.get(
        _sb_url("resultados_testes"),
        headers=_sb_headers(),
        params={"select": "*", "avaliacao_id": f"eq.{avaliacao_id}"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/avaliacoes/{avaliacao_id}/sinalizar", status_code=status.HTTP_200_OK)
def sinalizar_avaliacao(
    avaliacao_id: UUID,
    sinalizacao: AvaliacaoSinalizar,
    user_payload: dict = Depends(validar_auth),
):
    """Sinaliza uma avaliação para revisão do professor."""
    requests.patch(
        _sb_url("avaliacoes"),
        headers=_sb_headers(),
        params={"id": f"eq.{avaliacao_id}"},
        json={"flag_professor": True, "flag_motivo": sinalizacao.motivo},
        timeout=10,
    )
    return {"mensagem": "Avaliação sinalizada com sucesso para o professor."}