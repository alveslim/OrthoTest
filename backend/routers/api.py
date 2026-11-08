import os
import io
import csv
from typing import List
from uuid import UUID
import requests
from datetime import datetime, timezone
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
    
# ==========================================
# EXPORTAÇÃO E STORAGE (ORT-29)
# ==========================================
@router.post("/dashboard/exportar/csv")
def exportar_relatorio_csv(user_payload: dict = Depends(validar_auth)):
    """
    Gera um relatório CSV em memória e envia para o Supabase Storage.
    Garante a privacidade ao basear-se estritamente nos KPIs já agregados (ORT-27)[cite: 6].
    """
    
    # 1. AULA: Reutilizamos a lógica existente! Chamamos a função da ORT-26/27 
    # para garantir que os dados já vêm calculados e com os grupos pequenos ocultos.
    kpis = calcular_kpis_agregados(user_payload)
    
    # 2. Criação do CSV em Memória RAM (sem gravar no disco rígido do servidor)
    saida_memoria = io.StringIO()
    # Usamos ponto e vírgula para não haver conflitos com casas decimais no Excel europeu/brasileiro
    escritor_csv = csv.writer(saida_memoria, delimiter=';') 
    
    # Escrevemos o cabeçalho e os indicadores gerais
    escritor_csv.writerow(["RELATÓRIO AGREGADO DE AVALIAÇÕES ORTOPÉDICAS"])
    escritor_csv.writerow(["Data de Geração", datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")])
    escritor_csv.writerow([])
    escritor_csv.writerow(["MÉTRICAS GERAIS"])
    escritor_csv.writerow(["Total de Participantes", kpis["participantes_avaliados"]])
    escritor_csv.writerow(["Avaliações Concluídas (%)", kpis["percentual_avaliacoes_completas"]])
    escritor_csv.writerow(["Dor Média Geral (0-10)", kpis["dor_media_geral"]])
    escritor_csv.writerow([])
    
    # Escrevemos a tabela de resultados por região
    escritor_csv.writerow(["POSITIVIDADE POR REGIÃO"])
    escritor_csv.writerow(["Região", "Total de Testes Válidos", "Testes Positivos", "Taxa de Positividade (%)"])
    
    for regiao in kpis["positividade_por_regiao"]:
        escritor_csv.writerow([
            regiao["regiao"],
            regiao["total_valido"],
            regiao["positivos"],
            regiao["percentual_positivo"]
        ])
    
    conteudo_ficheiro = saida_memoria.getvalue()
    
    # 3. Envio para o Supabase Storage API
    user_id = user_payload.get("sub")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_ficheiro = f"relatorio_{user_id}_{timestamp}.csv"
    
    # A URL do storage exige limpar o "/rest/v1" da base de dados e apontar para "/storage/v1/object/"
    base_storage_url = SUPABASE_URL.replace("/rest/v1", "")
    url_upload = f"{base_storage_url}/storage/v1/object/relatorios/{nome_ficheiro}"
    
    headers_storage = _sb_headers()
    headers_storage["Content-Type"] = "text/csv"
    
    try:
        # AULA: O método POST no storage envia o ficheiro bruto no parâmetro 'data' em vez de 'json'
        resp = requests.post(url_upload, headers=headers_storage, data=conteudo_ficheiro.encode('utf-8'), timeout=10)
        
        if resp.status_code in (200, 201):
            return {"sucesso": True, "mensagem": "Relatório CSV gerado e armazenado com sucesso no Supabase!"}
        return {"sucesso": False, "mensagem": f"Erro do Storage: {resp.text}"}
    except Exception as e:
        return {"sucesso": False, "mensagem": "Falha de ligação ao exportar para o Storage."}
    
import json
import os

# ==========================================
# MOTOR DETERMINÍSTICO DE ACHADOS CLÍNICOS (ORT-31)
# ==========================================
@router.get("/avaliacoes/{avaliacao_id}/achados")
def gerar_achados_clinicos(avaliacao_id: str, user_payload: dict = Depends(validar_auth)):
    """
    AULA: Este é o nosso Motor de Regras. Ele lê os resultados do paciente
    e cruza com a base de conhecimento (JSON), garantindo reprodutibilidade e rastreabilidade[cite: 8].
    """
    
    # 1. Carregar a Base de Conhecimento (Ground Truth)
    # Procuramos o ficheiro JSON que criámos na ORT-30, assumindo que a API corre na raiz do projeto.
    caminho_json = "ai/regras_clinicas.json"
    try:
        with open(caminho_json, 'r', encoding='utf-8') as f:
            base_conhecimento = json.load(f)
    except FileNotFoundError:
        return {"sucesso": False, "mensagem": "Base de conhecimento (JSON) não encontrada."}

    regras_clinicas = base_conhecimento.get("regras", [])
    mensagem_fallback = base_conhecimento.get("ausencia_de_regra_confiavel", "Sem regra.")

    # 2. Buscar os Resultados do Paciente (O que aconteceu na clínica?)
    resp_res = requests.get(
        _sb_url("resultados_testes"),
        headers=_sb_headers(),
        params={"avaliacao_id": f"eq.{avaliacao_id}"},
        timeout=10
    )
    resultados_paciente = resp_res.json() if resp_res.status_code == 200 else []

    # 3. Buscar o Catálogo de Testes (Para sabermos o nome de cada teste pelo ID)
    resp_cat = requests.get(_sb_url("testes_catalogo"), headers=_sb_headers(), timeout=10)
    catalogo = {t["id"]: t["nome"] for t in (resp_cat.json() if resp_cat.status_code == 200 else [])}

    # 4. Motor de Cruzamento Lógico (Match Determinístico)
    achados_gerados = []

    for res in resultados_paciente:
        teste_nome = catalogo.get(res["teste_id"], "Desconhecido")
        resultado_atual = res.get("resultado")

        # AULA: Normalmente só geramos achados para testes Positivos ou Inconclusivos.
        # Testes 'Não realizados' ou 'Negativos' são ignorados nesta etapa para não poluir o relatório.
        if resultado_atual in ["Não realizado", "Negativo"]:
            continue

        # AULA: Aqui acontece a magia determinística. 
        # Procuramos na nossa lista de regras UMA regra em que o nome do teste E o resultado coincidam.
        regra_encontrada = next((r for r in regras_clinicas if r["teste"] == teste_nome and r["resultado_gatilho"] == resultado_atual), None)

        if regra_encontrada:
            # Caso 1: Encontrámos uma regra. Criamos um achado perfeitamente rastreável[cite: 8].
            achados_gerados.append({
                "teste_origem": teste_nome,
                "resultado": resultado_atual,
                "achado": regra_encontrada["achado_sugerido"],
                "referencia": regra_encontrada["referencia_bibliografica"],
                "status": "Regra Aplicada"
            })
        else:
            # Caso 2: O teste foi positivo, mas não está no JSON.
            # Cumprimos o critério: "casos sem regra são tratados sem gerar afirmações inventadas"[cite: 8].
            achados_gerados.append({
                "teste_origem": teste_nome,
                "resultado": resultado_atual,
                "achado": mensagem_fallback,
                "referencia": "N/A",
                "status": "Ausência de Regra"
            })

    # Retorna o pacote completo, incluindo sempre o aviso legal para proteção jurídica do software[cite: 8]
    return {
        "sucesso": True,
        "avaliacao_id": avaliacao_id,
        "aviso_legal": base_conhecimento.get("_aviso_legal"),
        "achados": achados_gerados
    }
    
# ==========================================
# INTEGRAÇÃO COM LLM (RESUMO DESIDENTIFICADO) - ORT-32
# ==========================================
@router.post("/avaliacoes/{avaliacao_id}/resumo-ia")
def gerar_resumo_ia(avaliacao_id: str, user_payload: dict = Depends(validar_auth)):
    """
    AULA: Esta rota consome os achados da ORT-31, junta os dados desidentificados 
    do paciente e envia para um modelo de linguagem (LLM) redigir um rascunho.
    """
    
    # 1. OBTER DADOS DESIDENTIFICADOS (Apenas Idade e Peso/Altura, NUNCA nomes)
    resp_aval = requests.get(_sb_url("avaliacoes"), headers=_sb_headers(), params={"id": f"eq.{avaliacao_id}"}, timeout=10)
    avaliacao_dados = resp_aval.json()[0] if resp_aval.status_code == 200 and resp_aval.json() else {}
    participante_id = avaliacao_dados.get("participante_id")
    
    idade, peso, altura = "N/A", "N/A", "N/A"
    if participante_id:
        resp_part = requests.get(_sb_url("participantes"), headers=_sb_headers(), params={"id": f"eq.{participante_id}"}, timeout=10)
        part_dados = resp_part.json()[0] if resp_part.status_code == 200 and resp_part.json() else {}
        idade = part_dados.get("idade", "N/A")
        peso = part_dados.get("peso_kg", "N/A")
        altura = part_dados.get("altura_m", "N/A")

    # 2. OBTER ACHADOS DA ORT-31
    # Chamamos a nossa própria função para garantir rastreabilidade determinística
    achados_paciente = gerar_achados_clinicos(avaliacao_id, user_payload).get("achados", [])
    
    if not achados_paciente:
        return {"sucesso": False, "resumo": "Não há testes suficientes com gatilhos positivos para a IA analisar."}

    lista_formatada = "\n".join([f"- {a['teste_origem']} ({a['resultado']}): {a['achado']}" for a in achados_paciente])

    # ---------------------------------------------------------
    # 3. ENGENHARIA DE PROMPT (O Segredo da Segurança)
    # ---------------------------------------------------------
    prompt_sistema = """Você é um assistente acadêmico de fisioterapia. 
    Sua ÚNICA função é redigir um parágrafo de resumo estruturado com base nos achados fornecidos.
    REGRAS ABSOLUTAS:
    1. NÃO confirme diagnósticos médicos.
    2. NÃO prescreva tratamentos, exercícios, exames ou medicações.
    3. Use linguagem descritiva e impessoal.
    4. O seu texto final DEVE incluir obrigatoriamente a seguinte frase exata no final: 'NOTA: Este é um rascunho gerado por IA para revisão humana e não constitui diagnóstico clínico.'"""
        
    dados_entrada = f"Dados do Paciente: Idade {idade}, Peso {peso}kg, Altura {altura}m.\nAchados Clínicos:\n{lista_formatada}"
    prompt_completo = f"{prompt_sistema}\n\nAnalise e resuma o seguinte:\n{dados_entrada}"

    # ---------------------------------------------------------
    # 4. ESTRATÉGIA DE FALLBACK EM CASCATA (Gemma Local -> Nemotron Nuvem -> Falha Segura)
    # ---------------------------------------------------------
    texto_resumo = ""
    aviso_geracao = ""

    # TENTATIVA 1: OLLAMA LOCAL (Gemma)
    try:
        url_local = os.getenv("LLM_API_URL", "http://127.0.0.1:11434/api/generate")
        modelo_local = os.getenv("LLM_MODEL", "gemma")
        
        resp_local = requests.post(
            url_local, 
            json={"model": modelo_local, "prompt": prompt_completo, "stream": False}, 
            timeout=10 # Timeout curto para desistir rápido se o Ollama estiver desligado
        )
        
        if resp_local.status_code == 200:
            texto_resumo = resp_local.json().get("response", "")
            aviso_geracao = "Gerado via IA Local (Gemma)."
        else:
            raise ValueError("Ollama respondeu com erro.")
            
    except Exception as e_local:
        print(f"[Aviso] IA Local falhou ({e_local}). A tentar NVIDIA Nemotron...")
        
        # TENTATIVA 2: NVIDIA (Nemotron)
        try:
            url_nvidia = os.getenv("NVIDIA_API_URL")
            chave_nvidia = os.getenv("NVIDIA_API_KEY")
            modelo_nvidia = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-4-340b-instruct")
            
            # A API da Nvidia (formato OpenAI) usa uma lista de "messages"
            payload_nvidia = {
                "model": modelo_nvidia,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": dados_entrada}
                ],
                "max_tokens": 400
            }
            headers_nvidia = {
                "Authorization": f"Bearer {chave_nvidia}",
                "Content-Type": "application/json"
            }
            
            resp_nvidia = requests.post(url_nvidia, headers=headers_nvidia, json=payload_nvidia, timeout=20)
            
            if resp_nvidia.status_code == 200:
                # O formato de resposta da Nvidia/OpenAI guarda o texto dentro de choices[0].message.content
                texto_resumo = resp_nvidia.json()["choices"][0]["message"]["content"]
                aviso_geracao = "Gerado via IA Nuvem (Nemotron)."
            else:
                raise ValueError(f"Nvidia respondeu com erro: {resp_nvidia.text}")
                
        except Exception as e_nvidia:
            print(f"[Erro] NVIDIA também falhou ({e_nvidia}). Disparando Falha Segura.")
            
            # TENTATIVA 3: FALHA SEGURA (Safe Fallback)
            return {
                "sucesso": False, 
                "resumo": "SERVIÇO DE IA INDISPONÍVEL: Os motores de IA Local e em Nuvem não estão a responder. Reveja os achados estruturados manualmente."
            }

    # Se chegar aqui, alguma IA (Gemma ou Nemotron) funcionou com sucesso!
    return {"sucesso": True, "resumo": texto_resumo, "aviso": aviso_geracao}

# ==========================================
# AUDITORIA E APROVAÇÃO DE RASCUNHOS IA (ORT-34)
# ==========================================
@router.post("/avaliacoes/{avaliacao_id}/aprovar-resumo")
def aprovar_resumo_ia_auditoria(avaliacao_id: str, payload: dict, user_payload: dict = Depends(validar_auth)):
    """
    AULA: Esta rota recebe o texto final que o humano editou e guardá-o na tabela ia_rascunhos.
    A garantia de auditoria faz-se extraindo o ID do utilizador do token de segurança (user_payload).
    """
    texto_final = payload.get("texto_final", "").strip()
    
    if not texto_final:
        return {"sucesso": False, "mensagem": "O texto do resumo não pode estar vazio."}
        
    # Extraímos a identidade do profissional que está a fazer a requisição (o 'revisor')
    revisor_id = user_payload.get("sub")
    
    # Preparamos o pacote de dados exigido pela ORT-34
    dados_auditoria = {
        "avaliacao_id": avaliacao_id,
        "texto_gerado": texto_final,
        "revisado_por": revisor_id, # Vinculação ao utilizador autorizado exigida pelo critério de aceite
        "aprovado": True,           # Estado persistido de aprovação
        "data_aprovacao": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Fazemos o POST para a tabela 'ia_rascunhos' no Supabase
        resp = requests.post(
            _sb_url("ia_rascunhos"),
            headers=_sb_headers(),
            json=dados_auditoria,
            timeout=10
        )
        
        if resp.status_code in (200, 201):
            return {"sucesso": True, "mensagem": "Resumo aprovado e registado com sucesso na ficha do paciente."}
        else:
            return {"sucesso": False, "mensagem": f"Erro ao guardar na base de dados: {resp.text}"}
            
    except Exception as e:
        return {"sucesso": False, "mensagem": "Falha de comunicação ao tentar auditar o registo."}