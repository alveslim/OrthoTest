# Decisões do grupo

## Banco de dados (ORT-06)
- Datas em `TIMESTAMPTZ`.
- O status Completo/Incompleto é calculado a partir dos resultados; não é coluna.
- `ON DELETE RESTRICT`: nada some em cascata. A exclusão será lógica (ORT-07).
- RLS ligado em todas as tabelas, sem políticas até o ORT-09.

## Testes em duas posições (Estresse em Valgo e Estresse em Varo)
**Problema:** as fichas dizem que esses testes podem ser feitos em duas posições do joelho
(extensão e 20° a 30° de flexão), mas o banco guarda **um resultado por teste e por lado**
(`UNIQUE (avaliacao_id, teste_id, lado)`).

**Decisão (proposta, aguardando o grupo):** registrar um único resultado. O resultado é
**Positivo se qualquer uma das posições for positiva**. A posição em que o achado apareceu
é anotada em `observacoes` (ex.: "positivo a 30° de flexão; negativo em extensão").

**Por quê:** mantém o modelo simples e não exige nova tabela.
**Custo:** a posição fica em texto livre, então não dá para filtrar ou contar por posição no painel.
**Alternativa descartada por ora:** uma coluna `posicao` na tabela de resultados.
Só vale se o grupo precisar analisar por posição.

## Catálogo (ORT-05/08)
- Os textos do catálogo são copiados das fichas de Sabrina e Vinícius (`database/seed_catalogo.sql`).
- `referencia` fica `NULL` até o ORT-02 trazer a fonte bibliográfica verificada.

# Registo de Decisões Arquiteturais e de Governança (ADR)

## ADR-047: Política de Destino, Retenção e Descarte de Dados Pós-Projeto (ORT-47)

- **Data:** Novembro de 2026
- **Status:** Aprovado pelo Grupo e Orientação Académica
- **Responsável pela Execução:** Flávio Alves (Administrador do Banco / Backend)[cite: 22]
- **Momento de Execução:** Até 7 dias corridos após a apresentação final e consolidação das notas da disciplina (Data limite prevista: 12/11/2026)[cite: 22].

### 1. Decisão de Tratamento dos Dados
Em conformidade com o princípio da minimização e limitação de armazenamento:
1. **Preservação de Agregados Estatísticos:** Os relatórios CSV/PDF agregados (protegidos pela regra de K-Anonimato $n < 3$) serão exportados e mantidos no repositório académico como evidência estatística do estudo[cite: 22].
2. **Eliminação de Dados Individuais:** Todos os registos individuais nas tabelas `participantes`, `avaliacoes`, `resultados_testes` e `ia_rascunhos`, bem como os ficheiros brutos no bucket `relatorios` do Supabase Storage, serão permanentemente eliminados[cite: 22].
3. **Descarte de Formulários Físicos (Plano B):** Caso fichas impressas de contingência (ORT-43) tenham sido utilizadas, serão fragmentadas fisicamente logo após a validação da transcrição.

### 2. Procedimento Técnico de Expurgo (SQL)
No momento definido, o responsável executará a limpeza definitiva no Supabase SQL Editor:
```sql
TRUNCATE TABLE public.ia_rascunhos, public.resultados_testes, public.avaliacoes, public.participantes RESTART IDENTITY CASCADE;

## ADR-049: Nome opcional, código automático e termo de consentimento por participante

- **Data:** 10/11/2026
- **Decisão:** o cadastro passa a aceitar **nome e sobrenome opcionais** (`participantes.nome`, `participantes.sobrenome`) e o **código P-001, P-002… é gerado pelo banco** (gatilho `participantes_codigo`, único por avaliador). Antes o código era digitado e nome completo era proibido.
- **Por quê:** digitar o código atrapalhava e dava erro; o avaliador precisa achar a ficha de quem está na sua frente.
- **Salvaguardas:** nome e sobrenome ficam só na tabela `participantes` (RLS: aluno vê os que criou, professor vê todos). **Nunca** entram em views, no dashboard, no CSV nem no prompt da IA (a IA recebe só idade, peso, altura e resultados). Continuam valendo n < 3 e o expurgo do ADR-047 (a tabela inteira é apagada).
- **Termo de consentimento:** o participante lê o termo (texto em `app/termo.py`, versão impressa em `docs/termo_consentimento.md`) e o avaliador marca a confirmação no cadastro. O banco grava `consentimento`, `data_consentimento` e `termo_versao`, e recusa cadastro sem eles. Menor de 18 anos exige também `consentimento_responsavel`. Mudou o texto? Mude `TERMO_VERSAO`.
- **Sem internet:** participante criado offline recebe código provisório; se outro aparelho usar o mesmo código, o servidor atribui o próximo e o app avisa na sincronização.
