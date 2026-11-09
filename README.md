# OrthoTest — Sistema Interativo de Avaliação Ortopédica

Aplicação acadêmica para registrar testes ortopédicos especiais, acompanhar avaliações e consultar indicadores agregados. O cliente é desenvolvido em **Python + Flet** e a API em **FastAPI**, com autenticação e persistência no **Supabase**.

> **Aviso:** projeto educacional; não é dispositivo médico. Os resultados não confirmam diagnósticos nem prescrevem tratamentos. A aplicação dos testes deve ser realizada por profissional capacitado, com consentimento do participante.

## Estado desta versão

A versão de finalização corrige a integração cliente/API, a validação da sessão Supabase, a persistência repetida de resultados, o isolamento por usuário e a tela de seleção do lado do teste. O catálogo é atualizado para refletir os três documentos ortopédicos enviados ao projeto em 09/11/2026.

O catálogo contém **19 testes ativos**. O antigo registro “Gaveta Anterior” permanece inativo no banco para preservar avaliações antigas que já apontavam para aquele ID.

| Região | Testes ativos |
|---|---|
| Joelho | Lachman, Estresse em Valgo, Estresse em Varo |
| Tornozelo | Thompson, Inclinação Talar |
| Quadril | Thomas, FADIR, Patrick-FABERE |
| Ombro | Neer, Jobe |
| Cotovelo | Cozen, Estresse em Valgo (Cotovelo) |
| Punho | Tinel, Phalen |
| Coluna lombar | Lasègue |
| Coluna cervical | Spurling, Distração Cervical |
| Tórax | Adams, Wright |

As referências bibliográficas do catálogo ficam vazias até o grupo validar edição e fonte. O sistema não inventa referências.

## Arquitetura

```
Cliente Flet (desktop / web / mobile)
          |
          | HTTPS + access token do Supabase
          v
API FastAPI  --------------------> regras clínicas locais / LLM opcional
          |
          | chave anon + sessão do usuário
          v
Supabase Auth + PostgREST + PostgreSQL (RLS) + Storage privado
```

- **Cliente:** telas de login/consentimento, participantes, seleção de testes, registro de resultados, dashboard e resumo para revisão.
- **API:** valida a sessão no endpoint oficial do Supabase Auth e executa consultas PostgREST com o access token do próprio usuário.
- **Banco:** políticas RLS separam dados de alunos; professor tem acesso de revisão conforme `app_metadata.role = professor`.
- **IA:** regras locais documentadas; provedor LLM é opcional. Sem provedor disponível, a aplicação retorna um resumo estruturado baseado nas regras, identificado como tal.

A aplicação não deve receber a chave `service_role`. Use apenas `SUPABASE_ANON_KEY` no cliente e no backend.

## Estrutura

```
OrthoTest/
├── app/                         # Cliente Flet
├── backend/                     # API FastAPI, autenticação e schemas
│   └── routers/api.py
├── ai/regras_clinicas.json      # Regras determinísticas e referências
├── supabase/migrations/         # Migrations do banco, RLS, views e Storage
├── database/seed_catalogo.sql   # Catálogo atualizado (19 ativos + legado)
├── dados_ficticios/             # Dados exclusivamente fictícios
├── tests/                       # Testes pytest
├── docs/                        # API, instalação, segurança e decisões
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Executar localmente (Windows / PowerShell)

1. Clone e instale:

```powershell
git clone https://github.com/alveslim/OrthoTest.git
cd OrthoTest
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

2. Preencha o arquivo `.env` com `SUPABASE_URL` e `SUPABASE_ANON_KEY`. Para execução local, mantenha `API_BASE_URL=http://127.0.0.1:8000/api/v1` e `MODO_OFFLINE=false`.

3. Inicie a API em um terminal:

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

4. Inicie o cliente em outro terminal:

```powershell
flet run app/main.py
```

Para abrir no navegador:

```powershell
flet run --web app/main.py
```

Quando o cliente web estiver hospedado em outro domínio, configure `API_BASE_URL` com a URL pública da API e inclua a origem em `CORS_ORIGINS`. O endereço `127.0.0.1` só funciona quando API e cliente estão na mesma máquina.

## Configurar o Supabase

1. No projeto Supabase correto, confira primeiro se as tabelas e migrations anteriores estão aplicadas.
2. Aplique `supabase/migrations/20261109170000_finalizacao_integridade_rls_storage.sql`. Ela cria tabelas que estiverem faltando, alinha colunas esperadas, ativa RLS, recria políticas específicas, prepara views e cria o bucket privado `relatorios`.
3. Execute `database/seed_catalogo.sql` para atualizar os testes ativos. Não apague registros históricos.
4. Crie usuários no Supabase Auth. Para um professor, o administrador deve definir `app_metadata.role = professor`; os demais usuários ficam como `aluno`.
5. Teste com dois usuários de aluno diferentes e um professor, confirmando que cada aluno só consegue ver seus próprios participantes e avaliações e que o professor consegue revisar os registros.

**Não execute migrations diretamente em produção sem backup e sem conferir o projeto selecionado.** A migration é idempotente quanto à criação/alinhamento de objetos, mas qualquer alteração de políticas deve ser validada no banco real.

## Dados e regras de negócio

- Durante desenvolvimento, utilize somente dados fictícios.
- Não registre nomes completos; use códigos como `P-001`.
- O consentimento deve estar marcado e acompanhado de data antes do cadastro.
- Um resultado positivo não é um diagnóstico; um negativo não garante ausência de condição.
- Valores permitidos para resultado: `Positivo`, `Negativo`, `Não realizado`, `Inconclusivo`.
- Valores permitidos para lado: `Direito`, `Esquerdo`, `Bilateral`.
- Dor: inteiro de 0 a 10.
- O progresso é calculado com base nos testes ativos do catálogo.
- A exclusão de participantes e avaliações deve ser lógica; resultados podem ser removidos da avaliação pelo endpoint próprio.
- Dashboard não exibe uma região isolada com menos de três participantes. Grupos ocultos só são agregados quando o próprio grupo agregado alcança o limite mínimo.
- A aprovação de resumo de IA é exclusiva de professor e registra o revisor.

## Modo de demonstração

`MODO_OFFLINE=true` habilita dados mock apenas para demonstrar a interface. Esses dados são temporários e não são enviados ao Supabase. Não utilize esse modo para registrar avaliações reais.

## Testes

Execute:

```powershell
python -m pytest -q
```

Os testes unitários não substituem o teste de integração com o Supabase. A validação real de RLS exige contas de teste distintas no projeto e requisições autenticadas com cada sessão.

## Documentação

- [Contrato da API](docs/api.md)
- [Instalação](docs/instalacao.md)
- [Segurança RLS](docs/seguranca_rls.md)
- [Integridade dos dados](docs/integridade_dados.md)
- [Decisões de produto](docs/decisoes.md)

## Ética e privacidade

A participação deve ser voluntária e consentida. O sistema coleta o mínimo necessário, evita identificação nominal e apresenta apenas indicadores agregados no dashboard. Não publique dados individuais, tokens, chaves do Supabase ou arquivos `.env` no repositório.
