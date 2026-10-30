# Validação de Builds e Plataformas (ORT-25)

Este documento regista os resultados dos testes de execução e *build* da aplicação OrthoTest nas diferentes plataformas suportadas pelo Flet, detalhando limitações e pré-requisitos.

## 1. Desktop (Windows/Linux/macOS)
- **Comando:** `flet run app/main.py`
- **Estado:** ✅ Estável e totalmente funcional.
- **Observações:** A interface adapta-se corretamente ao formato janela. A comunicação HTTP com a API FastAPI via `requests` ocorre sem bloqueios. O redimensionamento mantém os alvos de toque acessíveis.

## 2. Web (Navegador)
- **Comando:** `flet run --web app/main.py`
- **Estado:** ⚠️ Funcional com limitações.
- **Limitações:** 
  - A navegação web pode sofrer bloqueios de CORS (Cross-Origin Resource Sharing) se a API FastAPI não tiver o `CORSMiddleware` configurado para aceitar a origem do Flet Web.
  - A persistência de sessão (tokens JWT) necessita de adaptações para usar o `page.client_storage` de forma a sobreviver a atualizações de página (F5).

## 3. Android (APK)
- **Comando:** `flet build apk`
- **Estado:** ⏳ Pendente / Requer configuração de ambiente.
- **Pré-requisitos e Falhas:**
  - A geração do pacote necessita da instalação prévia do **Flutter SDK** e do **Android toolchain** (Android Studio).
  - Sem este ambiente configurado, o comando `flet build` falha.
  - **Limitação de rede:** Num dispositivo físico ou emulador, as chamadas HTTP à API não podem usar `http://127.0.0.1:8000`, sendo necessário alterar a variável `API_BASE_URL` no `.env` para o IP local da máquina na rede (ex: `http://192.168.1.X:8000`) ou usar um túnel (ex: Ngrok).