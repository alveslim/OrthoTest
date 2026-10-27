import os
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