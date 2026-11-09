import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

def verificar_ambiente():
    """AULA: Script de diagnóstico rápido para rodar na rede da universidade na véspera."""
    print("=== INICIANDO DIAGNÓSTICO DE VÉSPERA (ORT-44) ===")
    sb_url = os.getenv("SUPABASE_URL", "")
    sb_key = os.getenv("SUPABASE_KEY", "")

    if not sb_url or not sb_key:
        print("[ERRO] Variáveis SUPABASE_URL ou SUPABASE_KEY ausentes no .env!")
        return False

    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    inicio = time.time()
    try:
        # Testa leitura do catálogo para provar que o projeto Supabase está acordado (Ativo)
        url_teste = f"{sb_url.rstrip('/')}/rest/v1/testes_catalogo?select=id&limit=1" if "/rest/v1" not in sb_url else f"{sb_url}/testes_catalogo?select=id&limit=1"
        resp = requests.get(url_teste, headers=headers, timeout=10)
        latencia = round((time.time() - inicio) * 1000, 2)
        if resp.status_code == 200:
            print(f"[OK] Supabase ATIVO e acessível! Latência na rede atual: {latencia}ms")
            return True
        else:
            print(f"[ALERTA] Supabase respondeu com status {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[FALHA CRÍTICA] Sem conectividade com o Supabase na rede atual: {e}")
        return False

if __name__ == "__main__":
    verificar_ambiente()