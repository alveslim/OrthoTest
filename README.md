# 🩺 OrtoCheck: Sistema Interativo de Avaliação Ortopédica (kickoff)

Projeto de Extensão da disciplina de **Semiologia e Diagnóstico Cinesiológico-Funcional** (Universidade Nilton Lins). O OrtoCheck é um app (web, desktop e mobile, em Python + Flet) para **registrar testes ortopédicos especiais**, acompanhar os resultados em um painel e usar IA apenas como **apoio supervisionado** ao raciocínio clínico.

> **Status:** em desenvolvimento. Projeto acadêmico, não é dispositivo médico. A ferramenta não confirma diagnósticos nem prescreve tratamento.

## Conteúdo desta pasta

```
ortocheck/
├── app/                    # Cliente Flet (telas, componentes, tema)
├── backend/                # API Flask, schemas Pydantic, serviços
├── ai/                     # regras_clinicas.json e integração com o LLM
├── database/
│   ├── schema.sql          # tabelas, constraints, RLS
│   └── seed_catalogo.sql   # os 16 testes (vindos das fichas do grupo)
├── dados_ficticios/
│   └── gerar_dados.py      # participantes FICTÍCIOS (semente fixa) para desenvolver
├── tests/                  # pytest
├── docs/                   # fichas dos testes, mockups, croqui, decisões, referências
├── relatorios/             # CSV/PDF gerados
├── requirements.txt
├── .env.example
└── README.md
```

> Durante o desenvolvimento use **somente dados fictícios**. Dados reais entram apenas no dia da atividade, já com consentimento.

## Arquitetura

```
Cliente (Flet: web / desktop / mobile)
        │  HTTPS + token (JWT do Supabase Auth)
        ▼
Backend (Flask + Pydantic + Pandas) ──► Módulo de IA (só dados desidentificados)
        │
        ▼
Supabase (PostgreSQL + Auth + Storage, com RLS)
```

| Camada | Tecnologia | Responsabilidade |
|---|---|---|
| Apresentação | Flet | Check-up, lista de participantes, dashboard |
| Backend | Flask, Pydantic, Pandas | Validar token e dados, regras de negócio, agregações, relatórios |
| Dados | Supabase (PostgreSQL) | Tabelas, Auth, Storage, Row Level Security |
| IA | Regras + LLM (a definir) | Rascunho de resumo para discussão |

O app **não contém** senhas nem chaves do banco. A `service_role` fica só no backend.

## Testes ortopédicos (16)

| Região | Testes |
|---|---|
| Joelho | Lachman, Gaveta Anterior (LCA); Estresse em Valgo (LCM); Estresse em Varo (LCL) |
| Tornozelo | Thompson; Inclinação Talar; Sinal de Kleiger |
| Ombro | Neer; Impacto de Yocum; Jobe |
| Punho | Finkelstein; Tinel; Phalen |
| Coluna | Lasègue; Patrick-FABERE; Adams |

Fichas por: Sabrina e Vinícius (MMII), Carolaine e Sophia (ombros e punhos), Eduarda e Sophia (coluna). Cada ficha tem definição, objetivo, como fazer e critério de resultado positivo.

## Dicionário de dados

| Tabela | Colunas |
|---|---|
| participantes | id, codigo, idade, peso_kg, altura_m, consentimento, data_consentimento, criado_em |
| avaliacoes | id, participante_id, avaliador_id, data_avaliacao, flag_professor, flag_motivo |
| testes_catalogo | id, regiao, nome, definicao, objetivo, como_fazer, positivo_se, referencia |
| resultados_testes | id, avaliacao_id, teste_id, lado, resultado, valor_medido, dor_0_10, observacoes |
| ia_rascunhos | id, avaliacao_id, texto, gerado_em, revisado_por, aprovado |
| perfis | user_id, nome_exibicao, papel (aluno ou professor) |

Relacionamentos: `avaliacoes.participante_id → participantes`, `resultados_testes.avaliacao_id → avaliacoes`, `resultados_testes.teste_id → testes_catalogo`, `ia_rascunhos.avaliacao_id → avaliacoes`.

Valores fixos: `lado` ∈ {Direito, Esquerdo, Bilateral}; `resultado` ∈ {Positivo, Negativo, Não realizado, Inconclusivo}.

### Regras de negócio (decididas pelo grupo, mudar só com registro em `docs/decisoes.md`)

- **Sem nome completo.** O participante é identificado por código (P-001). Idade, peso e altura são os únicos dados pessoais.
- **Consentimento obrigatório** antes de abrir o primeiro teste.
- **Positivo não é lesão e negativo não é "saudável".** Positivo = sinal compatível com a hipótese em investigação.
- `status` da avaliação é **calculado**: Completo = todos os testes esperados com resultado diferente de vazio (Não realizado e Inconclusivo contam como respondidos).
- IMC = `peso_kg / altura_m²`.
- `dor_0_10` é inteiro de 0 a 10. `valor_medido` guarda o ângulo quando existir (ex.: Lasègue).
- **Dashboard oculta qualquer grupo com menos de 3 participantes.**
- **IA nunca diagnostica.** Toda saída é rascunho, com revisor registrado e aprovação do professor.
- Exclusão é **lógica**, com confirmação.

## 1. Preparar o ambiente

```bash
git clone https://github.com/seu-usuario/ortocheck.git && cd ortocheck
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install flet flask pydantic pandas supabase python-dotenv pytest
pip freeze > requirements.txt    # fixe as versões, principalmente a do Flet

cp .env.example .env             # preencha SUPABASE_URL e SUPABASE_ANON_KEY
printf ".venv/\n__pycache__/\n.env\n*.db\n" > .gitignore
git add . && git commit -m "kickoff: estrutura do projeto"
```

`SUPABASE_SERVICE_KEY` só entra no `.env` do backend, nunca no app.

Rodar:

```bash
flask --app backend.app run        # terminal 1
flet run app/main.py               # terminal 2 (desktop)
flet run --web app/main.py         # alternativa: navegador
```

## 2. Chamados (tickets) para resolver, em ordem

Etiquetas: **[A]** dados/backend/IA, **[B]** app/design, **[G]** grupo inteiro (clínico).

**Etapa A: Fundamentos**
- [x] **ORT-00** Revisão inicial do projeto, mockups e arquitetura (ver `docs/revisao.md`).
- [x] **ORT-01** [G] Confirmar as regras de negócio acima e registrar em `docs/decisoes.md`. Definir datas reais: pré-projeto, dia da comunidade, entrega final.
- [x] **ORT-02** [G] Corrigir os .docx (colagem do Lasègue/Patrick; Adams: tórax ou coluna) e incluir referências bibliográficas em cada ficha.
- [x] **ORT-03** [A] Criar o repositório, `.env.example` e `requirements.txt` com versões fixas.
- [x] **ORT-04** [B] Definir paleta, tipografia e tema Flet (Material 3 com cor-semente). Validar contraste mínimo de 4,5:1.
- [x] **ORT-05** [A] Escrever `dados_ficticios/gerar_dados.py` (semente fixa, ~60 participantes com resultados plausíveis) para alimentar o desenvolvimento.

**Etapa B: Banco de dados (Supabase)**
- [x] **ORT-06** [A] Escrever `database/schema.sql` com PK, FK, `NOT NULL` e `CHECK` (dor entre 0 e 10, `lado` e `resultado` válidos, idade > 0, altura entre 0,5 e 2,5).
- [x] **ORT-07** [A] Usar `TIMESTAMPTZ` e exclusão lógica (`excluido_em`).
- [x] **ORT-08** [A] Carregar `seed_catalogo.sql` com os 16 testes a partir das fichas.
- [x] **ORT-09** [A] Ativar **RLS** em todas as tabelas: aluno vê o que criou, professor vê tudo. Criar `perfis` e papéis no Supabase Auth.
- [x] **ORT-10** [A] Criar views: `vw_positivos_por_teste`, `vw_positivos_por_regiao`, `vw_participantes_faixa_etaria`.

**Etapa C: Backend**
- [x] **ORT-11** [A] Schemas Pydantic de todas as entidades (valida resultado, lado, dor).
- [x] **ORT-12** [A] Middleware que valida o JWT do Supabase e o papel do usuário.
- [x] **ORT-13** [A] Endpoints: participantes, avaliações, resultados (salvar vários de uma vez), catálogo.
- [x] **ORT-14** [A] Calcular `status` e progresso ("2 de 6 testes") no backend.
- [x] **ORT-15** [A] Endpoint "sinalizar ao professor".
- [x] **ORT-16** [A] Documentar a API (lista de endpoints em `docs/api.md`) para o app consumir sem esperar o backend.

**Etapa D: App (Flet)**
- [x] **ORT-17** [B] Desenhar as telas **em formato celular** (check-up, teste, lista, dashboard) e só depois adaptar ao desktop.
- [x] **ORT-18** [B] Login e consentimento (checkbox + data) antes do primeiro teste.
- [x] **ORT-19** [B] Lista de participantes por código, com status e botão claro "Novo participante".
- [x] **ORT-20** [B] Tela de seleção de testes com progresso e separação visual entre "feito" e "resultado".
- [x] **ORT-21** [B] Tela do teste: seletor Positivo/Negativo/Não realizado, D/E/Bilateral, slider de dor 0–10, observações e botão "?" com a ficha. Alvos de toque de 44–48 px.
- [x] **ORT-22** [B] Ações destrutivas (Excluir) separadas do Salvar, com confirmação.
- [x] **ORT-23** [B] Traduzir toda a interface para português (sem "Search", "Hello", "Passed/Unpassed").
- [x] **ORT-24** [B] Rodar com dados fictícios em JSON e depois trocar pela API.
- [X] **ORT-25** [B] Testar o build web, desktop e APK (`flet build apk`). Anotar o que não funciona.

**Etapa E: Dashboard e relatórios**
- [ ] **ORT-26** [A] Calcular KPIs com Pandas ou SQL: participantes avaliados, % de avaliações completas, % positivo por teste e por região, dor média.
- [ ] **ORT-27** [A] Aplicar a regra de n < 3 (ocultar ou agrupar).
- [ ] **ORT-28** [B] Gráficos: cartões de KPI, barras horizontais por teste, positivos por região, faixa etária e IMC, filtros (região, lado, faixa etária). Remover o template financeiro.
- [ ] **ORT-29** [A] Gerar relatório CSV/PDF **sem identificação individual** e guardar no Supabase Storage.

**Etapa F: IA de apoio**
- [ ] **ORT-30** [G] Escrever `ai/regras_clinicas.json`: teste positivo → estrutura sugerida, **com referência** (nunca inventada).
- [ ] **ORT-31** [A] Motor de regras em Python que lê as regras e gera os "achados" de uma avaliação.
- [ ] **ORT-32** [A] LLM só para redigir o resumo a partir dos achados e dos dados **desidentificados**. Prompt proíbe diagnóstico. Testar com modelo local (Ollama) ou API gratuita.
- [ ] **ORT-33** [B] Painel "Assistente de IA": mostra o rascunho, o aviso "rascunho para revisão" e botões Revisar/Aprovar. Renomear "Sugerir Diagnóstico" para "Gerar resumo para discussão".
- [ ] **ORT-34** [A] Registrar `revisado_por` e `aprovado` em `ia_rascunhos`.
- [ ] **ORT-35** [A] Se usar Colab + ngrok: endpoint protegido por chave. Nunca enviar nome ou contato.

**Etapa G: Testes**
- [ ] **ORT-36** [A] `pytest` das regras (status, IMC, n < 3, validações Pydantic), incluindo casos de borda.
- [ ] **ORT-37** [A] Testes de dados: nenhum resultado sem avaliação, sem duplicidade de (avaliação, teste, lado), dor dentro de 0–10.
- [ ] **ORT-38** [A] **Teste de RLS:** um aluno não consegue ler dados de outro aluno.
- [ ] **ORT-39** [A] Reconciliação: total de resultados no banco = no dashboard = no relatório (diferença zero).
- [ ] **ORT-40** [G] Teste de usabilidade com colegas (o PDF exige). Cronometrar uma avaliação completa e registrar os erros encontrados.
- [ ] **ORT-41** [G] Teste de regressão: refazer o fluxo inteiro com os dados fictícios e confirmar que os números não mudam.

**Etapa H: Como no dia real**
- [ ] **ORT-42** [A] Modo de contingência: salvar rascunho local e sincronizar quando voltar a internet.
- [ ] **ORT-43** [G] Plano B impresso: planilha ou formulário, caso o sistema caia.
- [ ] **ORT-44** [A] Acessar o projeto Supabase na véspera (projetos inativos são pausados) e testar com a rede da universidade.
- [ ] **ORT-45** [G] Mudança de requisito: "adicionar um novo teste ao catálogo". Fazer sem mexer em código, só no banco, e documentar.
- [ ] **ORT-46** [A] Simular 5 avaliadores salvando ao mesmo tempo e medir o tempo de resposta.
- [ ] **ORT-47** [G] Definir o que acontece com os dados depois do projeto (exportar agregados, apagar os individuais) e registrar em `docs/decisoes.md`.
- [ ] **ORT-48** [G] Escrever o resumo de 1 página: o que foi encontrado, limitações e o que a IA fez e não fez.

## 3. Dicas

- **Nunca use dados reais para desenvolver.** Gere fictícios com semente fixa.
- Faça commits pequenos, um por chamado: `ORT-21: tela do teste com seletor de resultado`.
- Combinem o **contrato primeiro** (schemas Pydantic e `docs/api.md`). Assim [A] e [B] trabalham em paralelo.
- Antes de corrigir, **conte**: "o dashboard mostra 12 positivos de Neer; o banco tem 12". Esse número vira teste.
- Fixe a versão do Flet; a API muda entre versões.
- Toda decisão clínica ou de privacidade fica em `docs/decisoes.md`, mesmo quando foi tomada rápido.
- A IA só entra depois de o check-up e o dashboard funcionarem.

## 4. Para pesquisar

- Flet: `ft.Page`, `NavigationBar`, `ft.Theme(color_scheme_seed=...)`, `flet build apk`
- Supabase: Auth (JWT), Row Level Security, Storage, `supabase-py`
- Flask: blueprints, validação com Pydantic, CORS
- Pandas: `groupby`, `pivot_table`, `cut` (faixas etárias), `to_csv`
- PostgreSQL: `CHECK`, `TIMESTAMPTZ`, views, políticas RLS
- LGPD: dado pessoal sensível, consentimento, minimização, retenção
- Acessibilidade: contraste WCAG (4,5:1), alvos de toque
- IA: prompts com restrições, RAG simples sobre as fichas, Ollama
- Referências dos testes: Magee (Avaliação Musculoesquelética), Cipriano (Manual de Testes Especiais Ortopédicos). Confirmar títulos e edições.

## 5. Erros de partida já identificados (gabarito)

Só leia depois de fazer a sua própria revisão.

<details>
<summary>Abrir gabarito</summary>

- **Ética e PDF do professor:** botão "Sugerir Diagnóstico"; `nome_completo` na tabela; nomes completos nos mockups; ausência de consentimento; dashboard sem proteção contra n pequeno.
- **Linguagem clínica:** "Passed/Unpassed", "Falhou/Com Lesão", `sinal_positivo BOOLEAN NOT NULL` sem opção "Não realizado"; ✓ verde em teste positivo.
- **Escopo:** telas de Pescoço, Braço e Musculatura sem ficha científica; menu "Pesquisa" sem função.
- **Fichas (.docx):** texto colado no Lasègue/Patrick; Adams como "Tórax" vs "Coluna"; sem referências.
- **Banco:** `status` e `avaliador` digitados em vez de calculado e FK; `TIMESTAMP` sem fuso; `ON DELETE CASCADE` com botão Excluir; sem RLS; sem tabela de perfis.
- **Arquitetura:** Prisma (JavaScript) com backend Python; treinar um modelo sem base rotulada; Colab + ngrok em produção; IA ligada direto ao banco e ao Drive no croqui; tudo depende de internet.
- **Visual:** dashboard de template financeiro em inglês; seis donuts iguais; contraste baixo (texto laranja em laranja, branco em cinza); logos diferentes entre as telas; Salvar e Excluir lado a lado; círculos de ~20 px; só mockups de notebook.

</details>

## Ética e LGPD

- Participação **voluntária**, com consentimento registrado.
- Coleta mínima, sem nome completo e sem imagens sem autorização.
- Nenhum dado individual é exibido em apresentações ou no painel.
- Dados usados apenas para triagem educativa e análise descritiva. A atividade não substitui avaliação fisioterapêutica ou médica.

## Equipe

Estudantes de Fisioterapia da Universidade Nilton Lins. Desenvolvimento: [A] backend/dados/IA e [B] app/design (preencher nomes). Fichas clínicas: veja a seção "Testes ortopédicos".

## Referências

_Adicionar aqui as referências das fichas (obrigatório pelas orientações do projeto)._
