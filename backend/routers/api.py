"""Rotas REST do OrthoTest.

Todas as chamadas ao PostgREST usam o access token do usuário autenticado (e a
chave anon). Assim, a autorização real é aplicada pelo RLS do PostgreSQL.
Nenhuma rota utiliza service_role para operações feitas em nome de um aluno.
"""
import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import requer_professor, validar as validar_auth
from backend.schemas import (
    AvaliacaoEntrada,
    AvaliacaoSinalizar,
    ParticipanteEntrada,
    ResultadoTeste,
)

load_dotenv = None
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
router = APIRouter(prefix="/api/v1", tags=["OrthoTest"])


def _headers(user_payload: dict, prefer: str = "return=representation") -> dict[str, str]:
    token = user_payload.get("access_token")
    if not SUPABASE_URL or not SUPABASE_ANON_KEY or not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase não configurado ou sessão ausente no backend.",
        )
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _request(
    method: str,
    table: str,
    user_payload: dict,
    *,
    params: dict | None = None,
    body: Any = None,
    raw_body: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
    expected: tuple[int, ...] = (200, 201, 204),
    prefer: str = "return=representation",
):
    if not SUPABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPABASE_URL não foi configurada.",
        )
    headers = _headers(user_payload, prefer=prefer)
    if extra_headers:
        headers.update(extra_headers)
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=body,
            data=raw_body,
            timeout=12,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha de comunicação com o Supabase.",
        ) from exc

    if response.status_code not in expected:
        # Evita devolver detalhes internos/SQL do Postgres para a interface.
        detail = "O Supabase recusou a operação."
        try:
            parsed = response.json()
            detail = parsed.get("message") or parsed.get("details") or detail
        except ValueError:
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)

    if response.status_code == 204 or not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


def _select(table: str, user_payload: dict, params: dict | None = None) -> list[dict]:
    result = _request("GET", table, user_payload, params=params or {"select": "*"})
    return result if isinstance(result, list) else []


def _insert(table: str, user_payload: dict, body: dict, params: dict | None = None, prefer: str = "return=representation") -> list[dict]:
    result = _request("POST", table, user_payload, params=params, body=body, prefer=prefer)
    return result if isinstance(result, list) else []


def _update(table: str, user_payload: dict, params: dict, body: dict) -> list[dict]:
    result = _request("PATCH", table, user_payload, params=params, body=body)
    return result if isinstance(result, list) else []


def _delete(table: str, user_payload: dict, params: dict):
    return _request("DELETE", table, user_payload, params=params, expected=(200, 204))


def _is_professor(user_payload: dict) -> bool:
    return (user_payload.get("app_metadata") or {}).get("role") == "professor"


def _owner_filter(user_payload: dict, field: str = "avaliador_id") -> dict:
    return {} if _is_professor(user_payload) else {field: f"eq.{user_payload['sub']}"}


def _get_assessment(avaliacao_id: UUID | str, user_payload: dict) -> dict:
    params = {
        "select": "id,participante_id,avaliador_id,status,progresso_percentual",
        "id": f"eq.{avaliacao_id}",
        **_owner_filter(user_payload),
    }
    rows = _select("avaliacoes", user_payload, params)
    if not rows:
        # Não revelar se a avaliação existe para outro usuário.
        raise HTTPException(status_code=404, detail="Avaliação não encontrada.")
    return rows[0]


def _catalogo(user_payload: dict) -> list[dict]:
    return _select(
        "testes_catalogo",
        user_payload,
        {"select": "*", "ativo": "eq.true", "order": "id.asc"},
    )


def _recalcular_progresso(avaliacao_id: str, user_payload: dict) -> dict:
    catalogo = _catalogo(user_payload)
    resultados = _select(
        "resultados_testes",
        user_payload,
        {"select": "teste_id,resultado,lado", "avaliacao_id": f"eq.{avaliacao_id}"},
    )
    ids_esperados = {int(item["id"]) for item in catalogo}
    ids_respondidos = {
        int(item["teste_id"])
        for item in resultados
        if item.get("resultado") in ("Positivo", "Negativo", "Não realizado", "Inconclusivo")
        and int(item["teste_id"]) in ids_esperados
    }
    total = len(ids_esperados)
    respondidos = len(ids_respondidos)
    percentual = round((respondidos / total) * 100, 1) if total else 0.0
    status_atual = (
        "concluido" if total > 0 and respondidos == total
        else "em_andamento" if respondidos
        else "pendente"
    )
    _update(
        "avaliacoes",
        user_payload,
        {"id": f"eq.{avaliacao_id}", **_owner_filter(user_payload)},
        {"status": status_atual, "progresso_percentual": percentual},
    )
    return {
        "status": status_atual,
        "respondidos": respondidos,
        "total": total,
        "progresso_percentual": percentual,
    }


@router.get("/health")
def api_health():
    return {"status": "ok"}


@router.get("/catalogo/testes")
def listar_catalogo_testes(user_payload: dict = Depends(validar_auth)):
    """Retorna somente os testes ativos do catálogo."""
    return _catalogo(user_payload)


@router.post(
    "/participantes",
    status_code=status.HTTP_201_CREATED,
)
def criar_participante(
    participante: ParticipanteEntrada,
    user_payload: dict = Depends(validar_auth),
):
    dados = participante.model_dump(mode="json", exclude_none=True)
    dados["codigo"] = dados["codigo"].strip().upper()
    dados["user_id"] = user_payload["sub"]
    rows = _insert("participantes", user_payload, dados)
    if not rows:
        raise HTTPException(status_code=500, detail="O participante não foi confirmado pelo banco.")
    return rows[0]


@router.get("/participantes")
def listar_participantes(user_payload: dict = Depends(validar_auth)):
    params = {
        "select": "*",
        "excluido_em": "is.null",
        "order": "criado_em.desc",
        **_owner_filter(user_payload, "user_id"),
    }
    return _select("participantes", user_payload, params)


@router.post(
    "/avaliacoes",
    status_code=status.HTTP_201_CREATED,
)
def iniciar_avaliacao(
    avaliacao: AvaliacaoEntrada,
    user_payload: dict = Depends(validar_auth),
):
    participante_params = {
        "select": "id,user_id",
        "id": f"eq.{avaliacao.participante_id}",
        "excluido_em": "is.null",
        **_owner_filter(user_payload, "user_id"),
    }
    participantes = _select("participantes", user_payload, participante_params)
    if not participantes:
        raise HTTPException(status_code=404, detail="Participante não encontrado.")

    user_id = user_payload["sub"]
    rows = _insert(
        "avaliacoes",
        user_payload,
        {
            "participante_id": str(avaliacao.participante_id),
            "avaliador_id": user_id,
            "user_id": user_id,
            "status": "pendente",
            "progresso_percentual": 0,
        },
    )
    if not rows:
        raise HTTPException(status_code=500, detail="A avaliação não foi confirmada pelo banco.")
    return rows[0]


@router.get("/avaliacoes")
def listar_avaliacoes(user_payload: dict = Depends(validar_auth)):
    params = {
        "select": "*",
        "excluido_em": "is.null",
        "order": "data_avaliacao.desc",
        **_owner_filter(user_payload),
    }
    avaliacoes = _select("avaliacoes", user_payload, params)
    if not avaliacoes:
        return []

    catalogo = _catalogo(user_payload)
    ids = [str(item["id"]) for item in avaliacoes]
    resultados = _select(
        "resultados_testes",
        user_payload,
        {
            "select": "avaliacao_id,teste_id,resultado",
            "avaliacao_id": f"in.({','.join(ids)})",
        },
    )
    return aplicar_progresso_em_memoria(
        avaliacoes,
        [item["id"] for item in catalogo],
        resultados,
    )


@router.post(
    "/avaliacoes/{avaliacao_id}/resultados",
    status_code=status.HTTP_201_CREATED,
)
def registar_resultado_teste(
    avaliacao_id: UUID,
    resultado: ResultadoTeste,
    user_payload: dict = Depends(validar_auth),
):
    _get_assessment(avaliacao_id, user_payload)
    catalogo_ids = {int(item["id"]) for item in _catalogo(user_payload)}
    if resultado.teste_id not in catalogo_ids:
        raise HTTPException(status_code=422, detail="O teste não existe ou está inativo no catálogo.")

    dados = resultado.model_dump(mode="json", exclude_none=True)
    dados.pop("avaliacao_id", None)
    dados["avaliacao_id"] = str(avaliacao_id)
    # Upsert respeita a chave única (avaliação, teste e lado) e evita duplicidade
    # quando o usuário salva novamente o mesmo resultado.
    rows = _insert(
        "resultados_testes",
        user_payload,
        dados,
        params={"on_conflict": "avaliacao_id,teste_id,lado"},
        prefer="resolution=merge-duplicates,return=representation",
    )
    progresso = _recalcular_progresso(str(avaliacao_id), user_payload)
    return {
        "mensagem": "Resultado salvo com sucesso.",
        "progresso_percentual": progresso["progresso_percentual"],
        "status": progresso["status"],
        "resultado": rows[0] if rows else None,
    }


@router.get("/avaliacoes/{avaliacao_id}/resultados")
def listar_resultados_avaliacao(
    avaliacao_id: UUID,
    user_payload: dict = Depends(validar_auth),
):
    _get_assessment(avaliacao_id, user_payload)
    return _select(
        "resultados_testes",
        user_payload,
        {
            "select": "*",
            "avaliacao_id": f"eq.{avaliacao_id}",
            "order": "teste_id.asc",
        },
    )


@router.post("/avaliacoes/{avaliacao_id}/sinalizar")
def sinalizar_avaliacao(
    avaliacao_id: UUID,
    sinalizacao: AvaliacaoSinalizar,
    user_payload: dict = Depends(validar_auth),
):
    _get_assessment(avaliacao_id, user_payload)
    rows = _update(
        "avaliacoes",
        user_payload,
        {"id": f"eq.{avaliacao_id}", **_owner_filter(user_payload)},
        {
            "flag_professor": True,
            "flag_motivo": (sinalizacao.motivo or "").strip() or "Solicitação de revisão.",
        },
    )
    if not rows and not _is_professor(user_payload):
        # Em RLS, uma linha bloqueada também pode resultar em retorno vazio.
        raise HTTPException(status_code=403, detail="Não foi possível sinalizar esta avaliação.")
    return {"mensagem": "Avaliação sinalizada para revisão do professor."}


@router.delete("/avaliacoes/{avaliacao_id}/resultados/{teste_id}")
def excluir_resultado_teste(
    avaliacao_id: UUID,
    teste_id: int,
    user_payload: dict = Depends(validar_auth),
):
    _get_assessment(avaliacao_id, user_payload)
    # Exclui todos os lados registrados para o teste desta avaliação.
    _delete(
        "resultados_testes",
        user_payload,
        {
            "avaliacao_id": f"eq.{avaliacao_id}",
            "teste_id": f"eq.{teste_id}",
        },
    )
    progresso = _recalcular_progresso(str(avaliacao_id), user_payload)
    return {
        "mensagem": "Resultado excluído com sucesso.",
        "progresso_percentual": progresso["progresso_percentual"],
        "status": progresso["status"],
    }


def _dados_dashboard(user_payload: dict) -> dict:
    params_aval = {
        "select": "id,participante_id,status",
        "excluido_em": "is.null",
        **_owner_filter(user_payload),
    }
    avaliacoes = _select("avaliacoes", user_payload, params_aval)
    ids_avaliacoes = [str(item["id"]) for item in avaliacoes]
    mapa_participantes = {
        str(item["id"]): str(item["participante_id"])
        for item in avaliacoes
    }
    participantes_unicos = set(mapa_participantes.values())

    if ids_avaliacoes:
        # UUIDs vêm do banco e são usados exclusivamente na cláusula IN.
        in_values = ",".join(ids_avaliacoes)
        resultados = _select(
            "resultados_testes",
            user_payload,
            {
                "select": "avaliacao_id,teste_id,resultado,dor_0_10",
                "avaliacao_id": f"in.({in_values})",
            },
        )
    else:
        resultados = []

    catalogo = _catalogo(user_payload)
    mapa_regiao = {int(item["id"]): item["regiao"] for item in catalogo}
    grupos: dict[str, dict] = {}
    dores = []

    for resultado in resultados:
        if resultado.get("resultado") == "Não realizado":
            continue
        avaliacao_ref = str(resultado.get("avaliacao_id"))
        participante_id = mapa_participantes.get(avaliacao_ref)
        regiao = mapa_regiao.get(int(resultado["teste_id"]))
        if not participante_id or not regiao:
            continue
        grupo = grupos.setdefault(
            regiao,
            {"participantes": set(), "positivos": 0, "total": 0},
        )
        grupo["participantes"].add(participante_id)
        grupo["total"] += 1
        if resultado.get("resultado") == "Positivo":
            grupo["positivos"] += 1
        if resultado.get("dor_0_10") is not None:
            dores.append(int(resultado["dor_0_10"]))

    # Recalcula o status com o catálogo ativo; não confia em progresso antigo
    # armazenado antes da ampliação das fichas.
    avaliacoes = aplicar_progresso_em_memoria(
        avaliacoes,
        [item["id"] for item in catalogo],
        resultados,
    )
    total_avaliacoes = len(avaliacoes)
    completas = sum(1 for item in avaliacoes if item.get("status") == "concluido")
    percentual_completas = (
        round(completas / total_avaliacoes * 100, 1)
        if total_avaliacoes else 0.0
    )
    dor_media = round(sum(dores) / len(dores), 1) if dores else 0.0

    # A privacidade é calculada pelo número de PARTICIPANTES distintos, não pela
    # quantidade de registros. Regiões pequenas só entram em "Outros" se o grupo
    # agregado também alcançar pelo menos três pessoas.
    exibidos = []
    participantes_ocultos = set()
    total_oculto = positivos_ocultos = 0
    for regiao, valores in grupos.items():
        total_pessoas = len(valores["participantes"])
        if total_pessoas < 3:
            participantes_ocultos.update(valores["participantes"])
            total_oculto += valores["total"]
            positivos_ocultos += valores["positivos"]
            continue
        exibidos.append({
            "regiao": regiao,
            "participantes": total_pessoas,
            "total_valido": valores["total"],
            "positivos": valores["positivos"],
            "percentual_positivo": round(
                valores["positivos"] / valores["total"] * 100, 1
            ) if valores["total"] else 0.0,
        })

    if len(participantes_ocultos) >= 3 and total_oculto:
        exibidos.append({
            "regiao": "Outros (privacidade)",
            "participantes": len(participantes_ocultos),
            "total_valido": total_oculto,
            "positivos": positivos_ocultos,
            "percentual_positivo": round(positivos_ocultos / total_oculto * 100, 1),
        })

    return {
        "participantes_avaliados": len(participantes_unicos),
        "avaliacoes_registradas": total_avaliacoes,
        "percentual_avaliacoes_completas": percentual_completas,
        "dor_media_geral": dor_media,
        "positividade_por_regiao": exibidos,
        "nota_privacidade": "Grupos com menos de 3 participantes não são exibidos isoladamente.",
    }


@router.get("/dashboard/kpis")
def calcular_kpis_agregados(user_payload: dict = Depends(validar_auth)):
    return _dados_dashboard(user_payload)


@router.post("/dashboard/exportar/csv")
def exportar_relatorio_csv(user_payload: dict = Depends(validar_auth)):
    """Gera CSV agregado e armazena em pasta exclusiva do usuário autenticado."""
    kpis = _dados_dashboard(user_payload)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["RELATÓRIO AGREGADO DE AVALIAÇÕES ORTOPÉDICAS"])
    writer.writerow(["Data de geração", datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")])
    writer.writerow(["Participantes avaliados", kpis["participantes_avaliados"]])
    writer.writerow(["Avaliações completas (%)", kpis["percentual_avaliacoes_completas"]])
    writer.writerow(["Dor média (0–10)", kpis["dor_media_geral"]])
    writer.writerow([])
    writer.writerow(["Região", "Participantes", "Testes válidos", "Positivos", "Positividade (%)"])
    for item in kpis["positividade_por_regiao"]:
        writer.writerow([
            item["regiao"], item["participantes"], item["total_valido"],
            item["positivos"], item["percentual_positivo"],
        ])

    uid = user_payload["sub"]
    filename = f"{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}_relatorio.csv"
    object_path = f"{uid}/{filename}"
    try:
        response = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/relatorios/{object_path}",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {user_payload['access_token']}",
                "Content-Type": "text/csv; charset=utf-8",
            },
            data=buffer.getvalue().encode("utf-8-sig"),
            timeout=15,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="Falha ao enviar o relatório para o Storage.") from exc
    if response.status_code not in (200, 201):
        return {
            "sucesso": False,
            "mensagem": "Não foi possível armazenar o relatório. Confira o bucket e as políticas de Storage.",
        }
    return {
        "sucesso": True,
        "mensagem": f"Relatório CSV armazenado no Supabase Storage ({filename}).",
        "caminho": object_path,
    }


def _carregar_regras() -> dict:
    caminho = Path(__file__).resolve().parents[2] / "ai" / "regras_clinicas.json"
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "regras": [],
            "ausencia_de_regra_confiavel": "Não há regra clínica documentada no sistema para este teste.",
            "_aviso_legal": "O sistema não confirma diagnósticos.",
        }


def _gerar_achados(avaliacao_id: str, user_payload: dict) -> dict:
    _get_assessment(avaliacao_id, user_payload)
    resultados = _select(
        "resultados_testes",
        user_payload,
        {"select": "teste_id,resultado,lado,dor_0_10", "avaliacao_id": f"eq.{avaliacao_id}"},
    )
    catalogo = _catalogo(user_payload)
    mapa_testes = {int(item["id"]): item for item in catalogo}
    base = _carregar_regras()
    regras = base.get("regras", [])
    fallback = base.get(
        "ausencia_de_regra_confiavel",
        "Não há regra clínica documentada no sistema para este teste.",
    )
    achados = []

    for item in resultados:
        if item.get("resultado") not in ("Positivo", "Inconclusivo"):
            continue
        teste = mapa_testes.get(int(item["teste_id"]))
        if not teste:
            continue
        nome = teste["nome"]
        regra = next(
            (
                rule for rule in regras
                if rule.get("resultado_gatilho") == item["resultado"]
                and rule.get("teste", "").lower().replace("teste de ", "") in nome.lower()
            ),
            None,
        )
        achados.append({
            "teste_origem": nome,
            "resultado": item["resultado"],
            "lado": item.get("lado"),
            "dor_0_10": item.get("dor_0_10"),
            "achado": regra.get("achado_sugerido") if regra else fallback,
            "referencia": regra.get("referencia_bibliografica", "Não informada") if regra else "Não informada",
            "status": "Regra aplicada" if regra else "Sem regra documentada",
        })
    return {
        "sucesso": True,
        "avaliacao_id": avaliacao_id,
        "aviso_legal": base.get("_aviso_legal", "Não constitui diagnóstico."),
        "achados": achados,
    }


@router.get("/avaliacoes/{avaliacao_id}/achados")
def gerar_achados_clinicos(
    avaliacao_id: UUID,
    user_payload: dict = Depends(validar_auth),
):
    return _gerar_achados(str(avaliacao_id), user_payload)


@router.post("/avaliacoes/{avaliacao_id}/resumo-ia")
def gerar_resumo_ia(
    avaliacao_id: UUID,
    user_payload: dict = Depends(validar_auth),
):
    dados = _gerar_achados(str(avaliacao_id), user_payload)
    achados = dados["achados"]
    if not achados:
        return {
            "sucesso": False,
            "resumo": "Ainda não existem resultados positivos ou inconclusivos suficientes para elaborar um resumo.",
            "aviso": "Sem achados para resumir.",
        }

    linhas = [
        f"- {item['teste_origem']} ({item['lado']}): {item['resultado']}. {item['achado']}"
        for item in achados
    ]
    prompt = (
        "Redija um resumo acadêmico descritivo, sem diagnóstico ou tratamento. "
        "Use somente os achados abaixo, não invente dados ou referências. "
        "Inclua ao final: 'Rascunho para revisão humana; não constitui diagnóstico clínico.'\n"
        + "\n".join(linhas)
    )
    texto = ""
    aviso = "Resumo estruturado pelas regras locais; serviço de LLM indisponível."
    llm_url = os.getenv("LLM_API_URL", "").strip()
    modelo = os.getenv("LLM_MODEL", "gemma")
    if llm_url:
        try:
            response = requests.post(
                llm_url,
                json={"model": modelo, "prompt": prompt, "stream": False},
                timeout=20,
            )
            if response.status_code == 200:
                texto = response.json().get("response", "").strip()
                if texto:
                    aviso = f"Resumo gerado pelo provedor configurado ({modelo}); aguardando revisão."
        except (requests.RequestException, ValueError):
            texto = ""

    if not texto:
        texto = (
            "Resumo descritivo dos achados registrados:\n"
            + "\n".join(linhas)
            + "\n\nRascunho para revisão humana; não constitui diagnóstico clínico."
        )
    elif "não constitui diagnóstico clínico" not in texto.lower():
        texto += "\n\nRascunho para revisão humana; não constitui diagnóstico clínico."

    return {"sucesso": True, "resumo": texto, "aviso": aviso}


@router.post("/avaliacoes/{avaliacao_id}/aprovar-resumo")
def aprovar_resumo_ia_auditoria(
    avaliacao_id: UUID,
    payload: dict,
    user_payload: dict = Depends(requer_professor),
):
    _get_assessment(avaliacao_id, user_payload)
    texto_final = str(payload.get("texto_final", "")).strip()
    if not texto_final:
        raise HTTPException(status_code=422, detail="O texto do resumo não pode estar vazio.")
    if len(texto_final) > 10000:
        raise HTTPException(status_code=422, detail="O resumo excede o limite de 10.000 caracteres.")

    rows = _insert(
        "ia_rascunhos",
        user_payload,
        {
            "avaliacao_id": str(avaliacao_id),
            "texto": texto_final,
            "revisado_por": user_payload["sub"],
            "aprovado": True,
            "gerado_em": datetime.now(timezone.utc).isoformat(),
        },
    )
    if not rows:
        raise HTTPException(status_code=500, detail="A aprovação não foi confirmada pelo banco.")
    return {"sucesso": True, "mensagem": "Resumo revisado e aprovado pelo professor."}
