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

@router.delete("/avaliacoes/{avaliacao_id}/resultados/{teste_id}", status_code=status.HTTP_200_OK)
def excluir_resultado_teste(
    avaliacao_id: UUID,
    teste_id: int,
    user_payload: dict = Depends(validar_auth),
):

    """exclusao do resultado e recalculo do progresso ORT-22"""
    requests.delete(
        _sb_url("resultados_testes"),
        headers=_sb_headers(),
        params={
            "avaliacao_id": f"eq.{avaliacao_id}",
            "teste_id": f"aq.{teste_id}",
        },
    timeout=10
    )

    # recalcula o progresso
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
    return {"mensagem": "Resultado excluído com sucesso."}

# ==========================================
# DASHBOARD E KPIs (ORT-26)
# ==========================================
@router.get("/dashboard/kpis")
def calcular_kpis_agregados(user_payload: dict = Depends(validar_auth)):
    """
    Calcula os KPIs agregados da clínica.
    Nesta rota, simulamos o comportamento de agregação de bibliotecas como o Pandas ou agrupamentos SQL,
    mas utilizando dicionários nativos do Python para máxima compatibilidade e rapidez.
    """
    
    # ---------------------------------------------------------
    # PARTE 1: EXTRAÇÃO DE DADOS (O equivalente a SELECTs no SQL)
    # ---------------------------------------------------------
    # Buscamos todas as avaliações feitas pelo utilizador atual
    user_id = user_payload.get("sub")
    resp_aval = requests.get(
        _sb_url("avaliacoes"),
        headers=_sb_headers(),
        params={"select": "*", "avaliador_id": f"eq.{user_id}"},
        timeout=10
    )
    avaliacoes = resp_aval.json() if resp_aval.status_code == 200 else []

    # Buscamos todos os resultados de testes já registados
    resp_res = requests.get(_sb_url("resultados_testes"), headers=_sb_headers(), timeout=10)
    resultados = resp_res.json() if resp_res.status_code == 200 else []

    # Buscamos o catálogo para saber a que "Região" pertence cada teste
    resp_cat = requests.get(_sb_url("testes_catalogo"), headers=_sb_headers(), timeout=10)
    catalogo = resp_cat.json() if resp_cat.status_code == 200 else []

    # Criamos um "dicionário de mapeamento" (Equivalente a um JOIN em SQL ou merge no Pandas)
    # Exemplo: mapa_regioes[1] = "Joelho"
    mapa_regioes = {t["id"]: t["regiao"] for t in catalogo}


    # ---------------------------------------------------------
    # PARTE 2: CÁLCULO DE KPIs GERAIS (Avaliações e Dor)
    # ---------------------------------------------------------
    total_avaliacoes = len(avaliacoes)
    
    # List Comprehension: Filtra apenas as avaliações que têm o status exato "concluido"
    avaliacoes_completas = len([a for a in avaliacoes if a.get("status") == "concluido"])
    
    # Evita a temida "Divisão por Zero". Se não houver avaliações, o percentual é 0.
    perc_completas = round((avaliacoes_completas / total_avaliacoes) * 100, 1) if total_avaliacoes > 0 else 0.0

    # Variáveis acumuladoras para a Dor Média
    soma_dor = 0
    testes_com_dor_avaliada = 0

    # ---------------------------------------------------------
    # PARTE 3: CÁLCULO DE POSITIVIDADE POR REGIÃO
    # ---------------------------------------------------------
    # Vamos criar um dicionário para contar o total de testes válidos e positivos por região.
    # Estrutura esperada: {"Joelho": {"positivos": 5, "total_valido": 10}, ...}
    agrupamento_regioes = {}

    for res in resultados:
        resultado_texto = res.get("resultado")
        
        # REGRA DE NEGÓCIO DA ORT-26: "Não realizado" é ignorado dos percentuais!
        if resultado_texto == "Não realizado":
            continue  # O comando 'continue' salta para o próximo item do loop ignorando o resto.

        # Se passou pelo if acima, o teste foi realizado (Positivo, Negativo ou Inconclusivo)
        testes_com_dor_avaliada += 1
        soma_dor += int(res.get("dor_0_10", 0))

        # Descobrimos a região deste teste usando o nosso mapa criado na Parte 1
        teste_id = int(res.get("teste_id"))
        regiao = mapa_regioes.get(teste_id, "Desconhecida")

        # Inicializa a região no dicionário se ela ainda não existir
        if regiao not in agrupamento_regioes:
            agrupamento_regioes[regiao] = {"positivos": 0, "total_valido": 0}

        # Incrementamos o denominador (Total válido)
        agrupamento_regioes[regiao]["total_valido"] += 1

        # Incrementamos o numerador apenas se o resultado for estritamente "Positivo"
        if resultado_texto == "Positivo":
            agrupamento_regioes[regiao]["positivos"] += 1

    # Calcula a dor média (Novamente, protegendo contra divisão por zero)
    dor_media = round(soma_dor / testes_com_dor_avaliada, 1) if testes_com_dor_avaliada > 0 else 0.0

# ---------------------------------------------------------
    # PARTE 4: FORMATAÇÃO FINAL E REGRA DE PRIVACIDADE (ORT-27)
    # ---------------------------------------------------------
    positivos_por_regiao = []
    
    # Variáveis acumuladoras para o grupo de segurança (Outros)
    ocultos_positivos = 0
    ocultos_total = 0

    for regiao, contadores in agrupamento_regioes.items():
        total_valido = contadores["total_valido"]
        positivos = contadores["positivos"]
        
        # AULA DE PRIVACIDADE (K-Anonimato): 
        # Se o grupo tiver menos de 3 testes válidos, é perigoso exibi-lo isoladamente.
        if total_valido < 3:
            # Em vez de adicionar à lista principal, guardamos os dados no nosso "saco" de ocultos.
            ocultos_total += total_valido
            ocultos_positivos += positivos
            # O comando 'continue' faz o loop saltar para a próxima região sem ler as linhas abaixo.
            continue 
            
        # Se chegou aqui, o grupo tem 3 ou mais pessoas (é seguro exibir!)
        perc_positivo = round((positivos / total_valido) * 100, 1)
        positivos_por_regiao.append({
            "regiao": regiao,
            "total_valido": total_valido,
            "positivos": positivos,
            "percentual_positivo": perc_positivo
        })

    # No final do loop, verificamos se sobrou algo no nosso "saco" de segurança.
    # Se sim, criamos a barra agregada "Outros (Privacidade)" para não perdermos a estatística geral.
    if ocultos_total > 0:
        perc_ocultos = round((ocultos_positivos / ocultos_total) * 100, 1) if ocultos_total > 0 else 0.0
        positivos_por_regiao.append({
            "regiao": "Outros (Privacidade < 3)",
            "total_valido": ocultos_total,
            "positivos": ocultos_positivos,
            "percentual_positivo": perc_ocultos
        })

    # Retorna o JSON estruturado e seguro
    return {
        "participantes_avaliados": total_avaliacoes,
        "percentual_avaliacoes_completas": perc_completas,
        "dor_media_geral": dor_media,
        "positividade_por_regiao": positivos_por_regiao
    }