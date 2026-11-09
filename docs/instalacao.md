# Instalação e execução — OrthoTest

## Requisitos

- Git;
- Python 3.11 ou superior;
- acesso ao projeto Supabase;
- usuário criado no Supabase Auth.

## Instalação no Windows

```powershell
git clone https://github.com/alveslim/OrthoTest.git
cd OrthoTest
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Preencha `.env`:

```env
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_ANON_KEY=SUA_CHAVE_PUBLICA
API_BASE_URL=http://127.0.0.1:8000/api/v1
CORS_ORIGINS=http://localhost:8550,http://127.0.0.1:8550
MODO_OFFLINE=false
```

Não coloque a chave `service_role` no cliente nem no backend da aplicação. O backend usa a sessão individual do usuário para que o RLS seja aplicado.

## Banco Supabase

1. Confira se está no projeto de desenvolvimento correto e faça backup se já houver dados.
2. Aplique a migration `supabase/migrations/20261109170000_finalizacao_integridade_rls_storage.sql`.
3. Execute `database/seed_catalogo.sql`.
4. Confirme se existem 19 testes ativos e o antigo registro Gaveta Anterior está inativo.
5. Crie usuários no Supabase Auth. O usuário professor precisa ter `app_metadata.role = professor`; os demais usuários ficam com papel `aluno`.
6. Valide as políticas RLS com pelo menos duas contas de aluno distintas e uma de professor antes de utilizar com participantes.

## Iniciar a API e o cliente

Terminal 1 — API:

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Verifique `http://127.0.0.1:8000/health`; a resposta esperada contém `"status": "ok"`.

Terminal 2 — aplicação desktop:

```powershell
flet run app/main.py
```

Ou navegador:

```powershell
flet run --web app/main.py
```

Quando o cliente web e a API estiverem hospedados em domínios diferentes, configure `API_BASE_URL` com a URL pública da API e adicione o domínio do cliente a `CORS_ORIGINS`. Não use `127.0.0.1` para um cliente hospedado fora da máquina local.

## Modo offline

`MODO_OFFLINE=true` é somente uma demonstração de interface com dados fictícios em memória. Não persiste no Supabase e perde os dados ao reiniciar o aplicativo. Para testes reais de integração, mantenha `MODO_OFFLINE=false`.

## Testes

```powershell
python -m pytest -q
```

Os testes automatizados unitários não substituem a validação das políticas RLS no banco. Para isso, execute os testes manuais descritos em `docs/validacao_supabase.md`.
