# Instalação para desenvolvimento no Windows

Procedimento verificado com Python 3.14.7 e PowerShell.

É necessário ter Git e Python 3.14 instalados. Em um terminal:

```powershell
git clone https://github.com/alveslim/OrthoTest.git
cd OrthoTest
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
Copy-Item .env.example .env
```

O arquivo `.env` é local e não deve ser enviado ao Git. Preencha as configurações do Supabase quando estiverem disponíveis. A chave `SUPABASE_SERVICE_KEY` deve ser usada somente no backend.

A instalação das dependências foi verificada. As telas e a API ainda serão implementadas em outras issues.