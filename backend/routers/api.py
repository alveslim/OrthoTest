"""Rotas da API OrthoTest.

Todas as chamadas ao banco usam o token do usuário (RLS aplicado). Erros do banco viram
HTTPException com a mensagem original, nunca são engolidos.
"""
import csv
import io
import os
from datetime import datetime, timezone
from typing import List
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend import regras
from backend.auth import papel_do_usuario, requer_professor
from backend.auth import validar as validar_auth
from backend.kpis import calcular_kpis
from backend.schemas import (
    AvaliacaoEntrada,
    AvaliacaoSaida,
    AvaliacaoSinalizar,
    ParticipanteEntrada,
    ParticipanteSaida,
    ResultadoTeste,
    TesteCatalogo,
)
from backend.supabase_client import rest, rest_todos, upload_storage

router = APIRouter(prefix="/api/v1", tags=["OrthoTest"])


class TextoResumo(BaseModel):
    texto_final: str = Field(min_length=1, max_length=5000)


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _avaliacao_visivel(avaliacao_id: UUID, user: dict) -> dict:
    """Garante que a avaliação existe e é visível ao usuário (RLS). Senão: 404."""
    linhas = rest("GET", "avaliacoes", user, params={"select": "*", "id": f"eq.{avaliacao_id}", "excluido_em": "is.null"})
    if not linhas:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avaliação não encontrada.")
    return linhas[0]


# ---------------- PERFIL ----------------
@router.get("/me")
def quem_sou_eu(user: dict = Depends(validar_auth)):
    return {"user_id": user["sub"], "email": user.get("email"), "papel": papel_do_usuario(user)}


# ---------------- CATÁLOGO ----------------
@router.get("/catalogo/testes", response_model=List[TesteCatalogo])
def listar_catalogo_testes(user: dict = Depends(validar_auth)):
    return rest("GET", "testes_catalogo", user, params={"select": "*", "ativo": "eq.true", "order": "id.asc"})


# ---------------- PARTICIPANTES ----------------
@router.post("/participantes", response_model=ParticipanteSaida, status_code=status.HTTP_201_CREATED)
def criar_participante(participante: ParticipanteEntrada, user: dict = Depends(validar_auth)):
    dados = participante.model_dump(mode="json", exclude_none=True)
    dados["user_id"] = user["sub"]
    linhas = rest("POST", "participantes", user, json=dados, prefer="return=representation")
    if not linhas:
        raise HTTPException(400, "Não foi possível criar o participante.")
    return linhas[0]


@router.get("/participantes", response_model=List[ParticipanteSaida])
def listar_participantes(user: dict = Depends(validar_auth)):
    return rest_todos("participantes", user, {"select": "*", "excluido_em": "is.null", "order": "criado_em.desc"})


@router.delete("/participantes/{participante_id}")
def excluir_participante(participante_id: UUID, user: dict = Depends(validar_auth)):
    """Exclusão LÓGICA (some das listas e do dashboard; o dado permanece para auditoria)."""
    feito = rest("PATCH", "participantes", user, params={"id": f"eq.{participante_id}", "excluido_em": "is.null"},
                 json={"excluido_em": _agora()}, prefer="return=representation")
    if not feito:
        raise HTTPException(404, "Participante não encontrado.")
    return {"mensagem": "Participante excluído."}


# ---------------- AVALIAÇÕES ----------------
@router.post("/avaliacoes", response_model=AvaliacaoSaida, status_code=status.HTTP_201_CREATED)
def iniciar_avaliacao(avaliacao: AvaliacaoEntrada, user: dict = Depends(validar_auth)):
    """Cria a ficha do participante, ou devolve a que já existe (uma ativa por participante)."""
    existente = rest("GET", "avaliacoes", user, params={
        "select": "*", "participante_id": f"eq.{avaliacao.participante_id}", "excluido_em": "is.null"})
    if existente:
        return existente[0]
    linhas = rest("POST", "avaliacoes", user,
                  json={"participante_id": str(avaliacao.participante_id), "avaliador_id": user["sub"]},
                  prefer="return=representation")
    return linhas[0]


@router.get("/avaliacoes", response_model=List[AvaliacaoSaida])
def listar_avaliacoes(user: dict = Depends(validar_auth)):
    return rest_todos("avaliacoes", user, {"select": "*", "excluido_em": "is.null"})


@router.post("/avaliacoes/{avaliacao_id}/resultados", status_code=status.HTTP_201_CREATED)
def registrar_resultado_teste(avaliacao_id: UUID, resultado: ResultadoTeste, user: dict = Depends(validar_auth)):
    """Salva (ou atualiza) o resultado de um teste/lado. O progresso é recalculado pelo banco."""
    _avaliacao_visivel(avaliacao_id, user)
    dados = resultado.model_dump(mode="json")
    dados["avaliacao_id"] = str(avaliacao_id)
    dados["excluido_em"] = None  # regravar um resultado excluído o reativa
    rest("POST", "resultados_testes", user, params={"on_conflict": "avaliacao_id,teste_id,lado"},
         json=dados, prefer="resolution=merge-duplicates,return=representation")
    atual = _avaliacao_visivel(avaliacao_id, user)
    return {
        "mensagem": "Resultado salvo com sucesso.",
        "progresso_percentual": float(atual["progresso_percentual"]),
        "status": atual["status"],
    }


@router.get("/avaliacoes/{avaliacao_id}/resultados")
def listar_resultados_avaliacao(avaliacao_id: UUID, user: dict = Depends(validar_auth)):
    return rest_todos("resultados_testes", user, {
        "select": "*", "avaliacao_id": f"eq.{avaliacao_id}", "excluido_em": "is.null"})


@router.delete("/avaliacoes/{avaliacao_id}/resultados/{teste_id}")
def excluir_resultado_teste(
    avaliacao_id: UUID,
    teste_id: int,
    lado: str | None = Query(default=None, pattern="^(Direito|Esquerdo|Bilateral)$"),
    user: dict = Depends(validar_auth),
):
    """Exclusão LÓGICA do resultado (todos os lados, ou só `lado`). O banco recalcula o progresso."""
    params = {"avaliacao_id": f"eq.{avaliacao_id}", "teste_id": f"eq.{teste_id}", "excluido_em": "is.null"}
    if lado:
        params["lado"] = f"eq.{lado}"
    feito = rest("PATCH", "resultados_testes", user, params=params,
                 json={"excluido_em": _agora()}, prefer="return=representation")
    if not feito:
        raise HTTPException(404, "Resultado não encontrado.")
    atual = _avaliacao_visivel(avaliacao_id, user)
    return {"mensagem": "Resultado excluído com sucesso.",
            "progresso_percentual": float(atual["progresso_percentual"]), "status": atual["status"]}


@router.post("/avaliacoes/{avaliacao_id}/sinalizar")
def sinalizar_avaliacao(avaliacao_id: UUID, sinalizacao: AvaliacaoSinalizar, user: dict = Depends(validar_auth)):
    feito = rest("PATCH", "avaliacoes", user, params={"id": f"eq.{avaliacao_id}"},
                 json={"flag_professor": True, "flag_motivo": sinalizacao.motivo}, prefer="return=representation")
    if not feito:
        raise HTTPException(404, "Avaliação não encontrada.")
    return {"mensagem": "Avaliação sinalizada com sucesso para o professor."}


# ---------------- DASHBOARD ----------------
def _kpis_do_usuario(user: dict) -> dict:
    resultados = rest_todos("vw_resultados_dashboard", user, {"select": "*"})
    avaliacoes = rest_todos("avaliacoes", user, {"select": "participante_id,status", "excluido_em": "is.null"})
    return calcular_kpis(resultados, avaliacoes)


@router.get("/dashboard/kpis")
def calcular_kpis_agregados(user: dict = Depends(validar_auth)):
    """Aluno vê os próprios dados; professor vê o grupo todo. Grupos com < 3 participantes ficam ocultos."""
    return _kpis_do_usuario(user)


def _linhas_csv(kpis: dict) -> str:
    saida = io.StringIO()
    w = csv.writer(saida, delimiter=";")
    w.writerow(["RELATÓRIO AGREGADO DE AVALIAÇÕES ORTOPÉDICAS (sem identificação individual)"])
    w.writerow(["Gerado em (UTC)", datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")])
    w.writerow([])
    w.writerow(["Participantes avaliados", kpis["participantes_avaliados"]])
    w.writerow(["Avaliações completas (%)", "oculto (n < 3)" if kpis["percentual_avaliacoes_completas"] is None else kpis["percentual_avaliacoes_completas"]])
    w.writerow(["Dor média (0-10)", "oculto (n < 3)" if kpis["dor_media_geral"] is None else kpis["dor_media_geral"]])
    for titulo, chave, campo in (
        ("POSITIVIDADE POR REGIÃO", "positividade_por_regiao", "regiao"),
        ("POSITIVIDADE POR TESTE", "positividade_por_teste", "teste"),
        ("POSITIVIDADE POR FAIXA ETÁRIA", "positividade_por_faixa_etaria", "faixa_etaria"),
        ("POSITIVIDADE POR FAIXA DE IMC", "positividade_por_imc", "faixa_imc"),
    ):
        w.writerow([])
        w.writerow([titulo])
        w.writerow(["Grupo", "Resultados válidos", "Positivos", "Positividade (%)", "Participantes"])
        for g in kpis[chave]:
            w.writerow([g[campo], g["total_valido"], g["positivos"], g["percentual_positivo"], g["participantes"]])
    return saida.getvalue()


@router.post("/dashboard/exportar/csv")
def exportar_relatorio_csv(user: dict = Depends(validar_auth)):
    """Gera o CSV agregado e guarda no Storage, na pasta do próprio usuário."""
    conteudo = "﻿" + _linhas_csv(_kpis_do_usuario(user))  # BOM: o Excel abre com acentos corretos
    caminho = f"{user['sub']}/relatorio_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.csv"
    upload_storage(user, "relatorios", caminho, conteudo.encode("utf-8"), "text/csv")
    return {"sucesso": True, "mensagem": "Relatório CSV agregado salvo no Storage.", "arquivo": caminho}


# ---------------- ACHADOS E IA ----------------
def _resultados_com_teste(avaliacao_id: UUID, user: dict) -> list[dict]:
    linhas = rest_todos("resultados_testes", user, {
        "select": "lado,resultado,testes_catalogo(regiao,nome)",
        "avaliacao_id": f"eq.{avaliacao_id}", "excluido_em": "is.null"})
    return [{"lado": l["lado"], "resultado": l["resultado"],
             "regiao": l["testes_catalogo"]["regiao"], "nome": l["testes_catalogo"]["nome"]} for l in linhas]


@router.get("/avaliacoes/{avaliacao_id}/achados")
def gerar_achados_clinicos(avaliacao_id: UUID, user: dict = Depends(validar_auth)):
    _avaliacao_visivel(avaliacao_id, user)
    base = regras.carregar_regras()
    return {
        "sucesso": True,
        "avaliacao_id": str(avaliacao_id),
        "aviso_legal": base.get("_aviso_legal"),
        "achados": regras.gerar_achados(_resultados_com_teste(avaliacao_id, user), base),
    }


PROMPT_SISTEMA = (
    "Você é um assistente acadêmico de fisioterapia. Sua ÚNICA função é redigir um parágrafo de resumo "
    "com base nos achados fornecidos. REGRAS ABSOLUTAS: 1. NÃO confirme diagnósticos. 2. NÃO prescreva "
    "tratamentos, exercícios, exames ou medicações. 3. Use linguagem descritiva e impessoal. 4. Termine "
    f"obrigatoriamente com a frase exata: '{regras.NOTA_RASCUNHO}'"
)


def _chamar_llm(dados_entrada: str) -> tuple[str, str] | None:
    """Ollama local, depois NVIDIA. Devolve (texto, aviso) ou None se nenhum respondeu."""
    try:
        r = requests.post(
            os.getenv("LLM_API_URL", "http://127.0.0.1:11434/api/generate"),
            json={"model": os.getenv("LLM_MODEL", "gemma"), "stream": False,
                  "prompt": f"{PROMPT_SISTEMA}\n\nAnalise e resuma o seguinte:\n{dados_entrada}"},
            timeout=10,
        )
        if r.status_code == 200 and r.json().get("response"):
            return r.json()["response"], "Gerado via IA local (Ollama)."
    except Exception:
        pass
    url, chave = os.getenv("NVIDIA_API_URL"), os.getenv("NVIDIA_API_KEY")
    if url and chave:
        try:
            r = requests.post(
                url, headers={"Authorization": f"Bearer {chave}"}, timeout=20,
                json={"model": os.getenv("NVIDIA_MODEL", "nvidia/nemotron-4-340b-instruct"), "max_tokens": 400,
                      "messages": [{"role": "system", "content": PROMPT_SISTEMA},
                                   {"role": "user", "content": dados_entrada}]},
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"], "Gerado via IA em nuvem (NVIDIA)."
        except Exception:
            pass
    return None


@router.post("/avaliacoes/{avaliacao_id}/resumo-ia")
def gerar_resumo_ia(avaliacao_id: UUID, user: dict = Depends(validar_auth)):
    """Rascunho para discussão. Só dados desidentificados (idade, peso, altura) saem do sistema."""
    avaliacao = _avaliacao_visivel(avaliacao_id, user)
    part = rest("GET", "participantes", user, params={"select": "idade,peso_kg,altura_m", "id": f"eq.{avaliacao['participante_id']}"})
    p = part[0] if part else {}
    idade, peso, altura = p.get("idade", "N/A"), p.get("peso_kg", "N/A"), p.get("altura_m", "N/A")

    achados = regras.gerar_achados(_resultados_com_teste(avaliacao_id, user))
    if not achados:
        return {"sucesso": False, "resumo": "Ainda não há teste positivo ou inconclusivo para resumir."}

    lista = "\n".join(f"- {a['teste_origem']} ({a['resultado']}): {a['achado']}" for a in achados)
    dados = f"Dados do participante: idade {idade}, peso {peso} kg, altura {altura} m.\nAchados:\n{lista}"
    gerado = _chamar_llm(dados)
    if gerado:
        texto, aviso = gerado
        if regras.NOTA_RASCUNHO not in texto:
            texto = f"{texto.rstrip()}\n\n{regras.NOTA_RASCUNHO}"
        return {"sucesso": True, "resumo": texto, "aviso": aviso}
    return {"sucesso": True, "resumo": regras.resumo_estruturado(achados, idade, peso, altura),
            "aviso": "IA indisponível: resumo estruturado gerado só pelas regras clínicas locais."}


@router.post("/avaliacoes/{avaliacao_id}/rascunho")
def salvar_rascunho_ia(avaliacao_id: UUID, corpo: TextoResumo, user: dict = Depends(validar_auth)):
    """Qualquer avaliador guarda o texto como rascunho NÃO aprovado."""
    _avaliacao_visivel(avaliacao_id, user)
    rest("POST", "ia_rascunhos", user, prefer="return=minimal",
         json={"avaliacao_id": str(avaliacao_id), "texto": corpo.texto_final.strip(), "aprovado": False})
    return {"sucesso": True, "mensagem": "Rascunho salvo para revisão do professor."}


@router.post("/avaliacoes/{avaliacao_id}/aprovar-resumo")
def aprovar_resumo_ia(avaliacao_id: UUID, corpo: TextoResumo, user: dict = Depends(requer_professor)):
    """Somente professor aprova; o revisor vem do token, nunca do corpo da requisição."""
    _avaliacao_visivel(avaliacao_id, user)
    rest("POST", "ia_rascunhos", user, prefer="return=minimal",
         json={"avaliacao_id": str(avaliacao_id), "texto": corpo.texto_final.strip(),
               "revisado_por": user["sub"], "aprovado": True})
    return {"sucesso": True, "mensagem": "Resumo aprovado e registrado com revisor identificado."}
