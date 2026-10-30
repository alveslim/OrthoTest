import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")

# Estado global da sessão no cliente Flet
sessao = {
    "access_token": None,
    "user_id": None,
    "email": None,
    "consentimento_aceito": False,
    "data_consentimento": None,
    "participante_atual": None,
    "avaliacao_atual": None,
    "teste_atual": None,
    "resultado_atual": None,
}

def _headers_autenticados() -> dict:
    return {
        "Authorization": f"Bearer {sessao['access_token']}",
        "Content-Type": "application/json",
    }

def autenticar_usuario(email: str, senha: str) -> tuple[bool, str]:
    """Autentica via API REST do Supabase Auth e guarda o JWT na sessão."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return False, "Configure SUPABASE_URL e SUPABASE_ANON_KEY no ficheiro .env"
    try:
        url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }
        resp = requests.post(
            url,
            headers=headers,
            json={"email": email.strip(), "password": senha},
            timeout=10,
        )
        if resp.status_code == 200:
            dados = resp.json()
            sessao["access_token"] = dados.get("access_token")
            usuario = dados.get("user") or {}
            sessao["user_id"] = str(usuario.get("id", ""))
            sessao["email"] = usuario.get("email", email.strip())
            return True, "Autenticado com sucesso."
        return False, "E-mail ou palavra-passe incorretos."
    except Exception:
        return False, "Erro ao conectar ao servidor de autenticação."

def registrar_consentimento_sessao():
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
        "teste_atual": None,
        "resultado_atual": None,
    })

def buscar_participantes_e_avaliacoes() -> tuple[bool, list | str]:
    try:
        resp_p = requests.get(f"{API_BASE_URL}/participantes", headers=_headers_autenticados(), timeout=10)
        resp_a = requests.get(f"{API_BASE_URL}/avaliacoes", headers=_headers_autenticados(), timeout=10)
        if resp_p.status_code != 200:
            return False, f"Erro ao carregar participantes ({resp_p.status_code})."
        
        participantes = resp_p.json()
        avaliacoes = resp_a.json() if resp_a.status_code == 200 else []
        mapa_aval = {str(a["participante_id"]): a for a in avaliacoes}
        
        for p in participantes:
            p["avaliacao"] = mapa_aval.get(str(p["id"]))
        return True, participantes
    except Exception:
        return False, "Não foi possível ligar à API FastAPI. Verifique se o servidor está em execução."

def criar_novo_participante(codigo: str, idade: int, peso_kg: float | None, altura_m: float | None) -> tuple[bool, dict | str]:
    payload = {
        "codigo": codigo.strip().upper(),
        "idade": idade,
        "peso_kg": peso_kg,
        "altura_m": altura_m,
        "consentimento": bool(sessao["consentimento_aceito"]),
        "data_consentimento": sessao["data_consentimento"],
    }
    try:
        resp = requests.post(f"{API_BASE_URL}/participantes", json=payload, headers=_headers_autenticados(), timeout=10)
        if resp.status_code in (200, 201):
            return True, resp.json()
        return False, str(resp.json().get("detail", "Erro ao validar os dados do participante."))
    except Exception:
        return False, "Falha de comunicação ao gravar participante na API."

def garantir_avaliacao_ativa(participante_id: str, avaliacao_existente: dict | None) -> tuple[bool, dict | str]:
    if avaliacao_existente:
        return True, avaliacao_existente
    try:
        resp = requests.post(f"{API_BASE_URL}/avaliacoes", json={"participante_id": str(participante_id)}, headers=_headers_autenticados(), timeout=10)
        if resp.status_code in (200, 201):
            return True, resp.json()
        return False, "Não foi possível iniciar a ficha de avaliação."
    except Exception:
        return False, "Erro de ligação ao iniciar avaliação."

def buscar_catalogo_e_resultados(avaliacao_id: str) -> tuple[bool, dict | str]:
    try:
        resp_cat = requests.get(f"{API_BASE_URL}/catalogo/testes", headers=_headers_autenticados(), timeout=10)
        if resp_cat.status_code != 200:
            return False, f"Erro ao carregar catálogo ({resp_cat.status_code})."
        
        resp_res = requests.get(f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/resultados", headers=_headers_autenticados(), timeout=10)
        catalogo = resp_cat.json()
        resultados = resp_res.json() if resp_res.status_code == 200 else []
        mapa_resultados = {int(r["teste_id"]): r for r in resultados if "teste_id" in r}
        
        return True, {"catalogo": catalogo, "mapa_resultados": mapa_resultados}
    except Exception:
        return False, "Falha de comunicação ao carregar catálogo e progresso da API."

def sinalizar_avaliacao_professor(avaliacao_id: str, motivo: str) -> tuple[bool, str]:
    try:
        resp = requests.post(f"{API_BASE_URL}/avaliacoes/{avaliacao_id}/sinalizar", json={"motivo": motivo.strip() or "Solicitação de revisão pelo aluno."}, headers=_headers_autenticados(), timeout=10)
        if resp.status_code == 200:
            return True, "Avaliação sinalizada ao professor com sucesso."
        return False, "Não foi possível sinalizar a avaliação."
    except Exception:
        return False, "Erro de conexão ao sinalizar avaliação."