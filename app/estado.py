import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Estado global da sessão no cliente Flet
sessao = {
    "access_token": None,
    "user_id": None,
    "email": None,
    "consentimento_aceito": False,
    "data_consentimento": None,
    "participante_atual": None,
    "avaliacao_atual": None,
}

def obter_cliente_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Configure SUPABASE_URL e SUPABASE_ANON_KEY no ficheiro .env")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def autenticar_usuario(email: str, senha: str) -> tuple[bool, str]:
    """Autentica no Supabase Auth e guarda o JWT na sessão."""
    try:
        sb = obter_cliente_supabase()
        resposta = sb.auth.sign_in_with_password({"email": email.strip(), "password": senha})
        if resposta.session:
            sessao["access_token"] = resposta.session.access_token
            sessao["user_id"] = str(resposta.user.id)
            sessao["email"] = resposta.user.email
            return True, "Autenticado com sucesso."
        return False, "Sessão não iniciada. Verifique as credenciais."
    except Exception as erro:
        msg = str(erro)
        if "Invalid login credentials" in msg:
            return False, "E-mail ou palavra-passe incorretos."
        return False, "Erro ao conectar ao servidor de autenticação."

def registrar_consentimento_sessao():
    """Regista o consentimento e o timestamp UTC atual."""
    sessao["consentimento_aceito"] = True
    sessao["data_consentimento"] = datetime.now(timezone.utc).isoformat()

def limpar_sessao():
    sessao.update({
        "access_token": None,
        "user_id": None,
        "email": None,
        "consentimento_aceito": False,
        "data_consentimento": None,
        "participante_atual": None,
        "avaliacao_atual": None,
    })

def _headers_autenticados() -> dict:
    return {
        "Authorization": f"Bearer {sessao['access_token']}",
        "Content-Type": "application/json",
    }

def buscar_participantes_e_avaliacoes() -> tuple[bool, list | str]:
    """Busca participantes e cruza com as avaliações do utilizador na API."""
    try:
        resp_p = requests.get(f"{API_BASE_URL}/participantes", headers=_headers_autenticados(), timeout=10)
        resp_a = requests.get(f"{API_BASE_URL}/avaliacoes", headers=_headers_autenticados(), timeout=10)

        if resp_p.status_code != 200:
            return False, f"Erro ao carregar participantes ({resp_p.status_code})."

        participantes = resp_p.json()
        avaliacoes = resp_a.json() if resp_a.status_code == 200 else []

        # Mapeia a avaliação mais recente por participante_id
        mapa_aval = {str(a["participante_id"]): a for a in avaliacoes}

        for p in participantes:
            aval = mapa_aval.get(str(p["id"]))
            p["avaliacao"] = aval

        return True, participantes
    except Exception:
        return False, "Não foi possível ligar à API FastAPI. Verifique se o servidor está em execução."

def criar_novo_participante(codigo: str, idade: int, peso_kg: float | None, altura_m: float | None) -> tuple[bool, dict | str]:
    """Envia POST para registar o participante com o consentimento da sessão."""
    payload = {
        "codigo": codigo.strip().upper(),
        "idade": idade,
        "peso_kg": peso_kg,
        "altura_m": altura_m,
        "consentimento": bool(sessao["consentimento_aceito"]),
        "data_consentimento": sessao["data_consentimento"],
    }
    try:
        resp = requests.post(
            f"{API_BASE_URL}/participantes",
            json=payload,
            headers=_headers_autenticados(),
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True, resp.json()
        detalhe = resp.json().get("detail", "Erro ao validar os dados do participante.")
        return False, str(detalhe)
    except Exception:
        return False, "Falha de comunicação ao gravar participante na API."

def garantir_avaliacao_ativa(participante_id: str, avaliacao_existente: dict | None) -> tuple[bool, dict | str]:
    """Retorna a avaliação existente ou inicia uma nova ficha via POST /avaliacoes."""
    if avaliacao_existente:
        return True, avaliacao_existente
    try:
        resp = requests.post(
            f"{API_BASE_URL}/avaliacoes",
            json={"participante_id": str(participante_id)},
            headers=_headers_autenticados(),
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True, resp.json()
        return False, "Não foi possível iniciar a ficha de avaliação."
    except Exception:
        return False, "Erro de ligação ao iniciar avaliação."

def buscar_catalogo_e_resultados(avaliacao_id: str) -> tuple[bool, dict | str]:
    """Busca o catálogo completo de testes e os resultados já registrados na avaliação."""
    try:
        resp_cat = requests.get(f"{API_BASE_URL}/catalogo/testes", headers=_headers_autenticados(), timeout=10)
        if resp_cat.status_code != 200:
            return False, f"Erro ao carregar catálogo ({resp_cat.status_code})."

        resp_res = requests.get(
            f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/resultados",
            headers=_headers_autenticados(),
            timeout=10,
        )
        catalogo = resp_cat.json()
        resultados = resp_res.json() if resp_res.status_code == 200 else []

        # Mapeia teste_id -> último resultado registrado
        mapa_resultados = {int(r["teste_id"]): r for r in resultados if "teste_id" in r}

        return True, {
            "catalogo": catalogo,
            "mapa_resultados": mapa_resultados,
        }
    except Exception:
        return False, "Falha de comunicação ao carregar catálogo e progresso da API."


def sinalizar_avaliacao_professor(avaliacao_id: str, motivo: str) -> tuple[bool, str]:
    """Envia POST para sinalizar a avaliação ao professor (ORT-15 / Tela de Seleção)."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/sinalizar",
            json={"motivo": motivo.strip() or "Solicitação de revisão pelo aluno."},
            headers=_headers_autenticados(),
            timeout=10,
        )
        if resp.status_code == 200:
            return True, "Avaliação sinalizada ao professor com sucesso."
        return False, "Não foi possível sinalizar a avaliação."
    except Exception:
        return False, "Erro de conexão ao sinalizar avaliação."