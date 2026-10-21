# Guia de implementação — ORT-09 a ORT-16

Este documento descreve o que implementar, como testar e o que registrar no commit, no Pull Request (PR) e no merge de cada entrega.

## 0. Confira o repositório antes de começar

Na inspeção de 21/10/2026, encontrei estes pontos que afetam a execução:

- O README menciona **database/schema.sql**, mas esse caminho não foi localizado na branch **main** nem na branch **ort-06-schema-sql** consultada. Confira a PR #54 da ORT-06 e confirme qual arquivo SQL foi realmente entregue antes de escrever políticas RLS.
- O arquivo **.gitignore** contém os padrões **schema.sql** e **testes_schema.sql**, que podem ignorar arquivos com esses nomes em subpastas. Confira **git status --short --ignored** e ajuste o ignore caso o schema versionado esteja sendo ignorado.
- **backend/schemas.py** já existe com os enums de resultado/lado e um modelo ResultadoTeste. Amplie os modelos existentes, sem duplicar o mesmo propósito.
- **tests/test_schemas.py** já cobre a validação de dor, lado e resultado.
- **docs/decisoes.md** registra que a RLS deveria estar ativa e sem políticas até a ORT-09.
- A PR #56 já contém uma parte da ORT-14: cálculo de status/progresso e testes. A própria descrição informa que falta integrar o cálculo aos resultados persistidos e à resposta da API: https://github.com/alveslim/OrthoTest/pull/56
- **docs/api.md** ainda não foi localizado na branch main; a ORT-16 deve criá-lo.

Confirme se a PR #54 já foi integrada. Issue marcada no quadro ou branch existente não garante que o arquivo esteja na main.

## Fluxo de trabalho padrão

Faça uma branch por ORT, baseada na main atualizada. Não junte ORT-09 até ORT-16 em uma única PR.

~~~powershell
git status
git switch main
git pull origin main
git switch -c ort-09-rls-perfis
~~~

Antes de commitar:

~~~powershell
python -m pytest -q
git diff --check
git status
git diff
git add caminho/do/arquivo1 caminho/do/arquivo2
git diff --cached --check
git diff --cached
git commit -m "ORT-09: descreva a mudança"
git push -u origin ort-09-rls-perfis
~~~

Use **git add** com caminhos específicos depois de revisar o stage. Nunca versione .env, tokens, chave service_role, dados reais, caches ou arquivos temporários.

---

## ORT-09 — RLS, perfis e papéis no Supabase

**Objetivo:** o aluno acessa somente os dados que criou; o professor acessa os dados autorizados do grupo; todas as tabelas da aplicação ficam protegidas por Row Level Security.

### Implementação

1. Confirme o schema SQL real e os nomes/tipos das colunas antes de criar políticas.
2. Crie **public.perfis**, vinculada a **auth.users**, com user_id UUID como chave primária e FK, nome_exibicao e papel limitado a aluno/professor.
3. Cada linha precisa de uma relação verificável com seu proprietário. O dicionário do README não apresenta coluna de proprietário em participantes. Se o schema real também não tiver, adicione uma coluna como **criado_por UUID REFERENCES auth.users(id)** e atualize o SQL/migração. Confirme que **avaliacoes.avaliador_id** referencia o usuário autenticado.
4. Ative RLS em **perfis**, **participantes**, **avaliacoes**, **testes_catalogo**, **resultados_testes** e **ia_rascunhos**.
5. Crie políticas separadas por operação: SELECT, INSERT e UPDATE. A política de leitura não autoriza escrita. Evite exclusão física, pois o projeto prevê exclusão lógica.
6. Usuários autenticados podem ler o catálogo; alunos não podem alterá-lo.
7. Não permita que o cliente informe seu papel como professor ou edite o papel do próprio perfil. O provisionamento de papéis deve ocorrer por um processo administrativo confiável.
8. Registre as regras em **docs/decisoes.md**.

Uma função auxiliar para consultar o papel pode usar SECURITY DEFINER, search_path seguro e referências qualificadas. Adapte e teste o exemplo:

~~~sql
CREATE OR REPLACE FUNCTION public.usuario_eh_professor()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.perfis AS p
        WHERE p.user_id = (SELECT auth.uid())
          AND p.papel = 'professor'
    );
$$;

REVOKE ALL ON FUNCTION public.usuario_eh_professor() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.usuario_eh_professor() TO authenticated;
~~~

Exemplo de política para participantes, somente se a coluna **criado_por** existir:

~~~sql
ALTER TABLE public.participantes ENABLE ROW LEVEL SECURITY;

CREATE POLICY participantes_select_proprietario_ou_professor
ON public.participantes FOR SELECT TO authenticated
USING (
    criado_por = (SELECT auth.uid())
    OR (SELECT public.usuario_eh_professor())
);

CREATE POLICY participantes_insert_proprio
ON public.participantes FOR INSERT TO authenticated
WITH CHECK (criado_por = (SELECT auth.uid()));
~~~

Aplique o mesmo princípio às demais tabelas: avaliações pelo avaliador_id; resultados e rascunhos de IA pela avaliação relacionada; perfis pelo user_id; catálogo compartilhado e somente leitura. Defina quem pode revisar/aprovar rascunhos de IA.

### Testes de aceite

- Aluno A consulta os próprios registros; aluno B não pode ler nem modificar os registros de A.
- Professor consulta os dados autorizados.
- Usuário comum não se promove a professor.
- Catálogo é legível por autenticados e não editável por aluno.
- Usuário não autenticado não acessa dados individuais.
- Testes usam sessões autenticadas normais. A chave service_role ignora RLS e não comprova que as políticas funcionam.

**Commit sugerido:** ORT-09: ativa RLS e configura perfis por papel

**Título do PR:** ORT-09: aplica políticas RLS para alunos e professores

**Corpo do PR:**

~~~markdown
## O que foi feito
- Cria/vincula perfis ao Supabase Auth.
- Ativa RLS nas tabelas da aplicação.
- Define políticas por proprietário e papel.
- Documenta as regras de acesso.

## Validação
- [ ] Aluno A não acessa dados do Aluno B
- [ ] Professor acessa os dados autorizados
- [ ] Usuário comum não altera o próprio papel
- [ ] Catálogo não é editável por aluno
- [ ] Testes com sessão autenticada, sem service_role
- [ ] pytest e git diff --check passaram

Refs #9
~~~

Use **Closes #9** apenas quando todos os critérios da Issue estiverem cumpridos.

---

## ORT-10 — Views para o dashboard

**Objetivo:** criar consultas agregadas reutilizáveis para os indicadores do painel.

Implemente estas views no arquivo SQL/migração realmente usado pelo projeto:

1. **vw_positivos_por_teste** — região, teste, total de respostas, positivos, quantidade avaliável e percentual positivo.
2. **vw_positivos_por_regiao** — métricas agregadas por região anatômica.
3. **vw_participantes_faixa_etaria** — contagem por faixas etárias documentadas.

Registre em **docs/decisoes.md** a definição do percentual. Sugestão: Positivo e Negativo contam como resultados avaliáveis; Não realizado e Inconclusivo ficam fora do denominador, mas podem ter contagem própria. Use NULLIF para denominador zero e não invente percentual quando não há dados avaliáveis.

As views também precisam respeitar RLS. Em Supabase/PostgreSQL, uma view padrão pode usar privilégios de seu proprietário; quando a versão usada no projeto permitir, use **security_invoker = true** para que as políticas RLS das tabelas subjacentes sejam aplicadas. Conceda somente leitura às roles necessárias. Não inclua nome, e-mail ou observações. A regra que oculta grupos com menos de 3 participantes continua obrigatória no dashboard/relatório.

Exemplo da view por teste (ajuste nomes/colunas depois de conferir o schema):

~~~sql
CREATE OR REPLACE VIEW public.vw_positivos_por_teste
WITH (security_invoker = true)
AS
SELECT
    tc.regiao,
    tc.id AS teste_id,
    tc.nome AS teste,
    COUNT(rt.id) AS total_respostas,
    COUNT(rt.id) FILTER (WHERE rt.resultado = 'Positivo') AS positivos,
    COUNT(rt.id) FILTER (
        WHERE rt.resultado IN ('Positivo', 'Negativo')
    ) AS resultados_avaliaveis,
    ROUND(
        100.0 * COUNT(rt.id) FILTER (WHERE rt.resultado = 'Positivo')
        / NULLIF(
            COUNT(rt.id) FILTER (
                WHERE rt.resultado IN ('Positivo', 'Negativo')
            ),
            0
        ),
        1
    ) AS percentual_positivo
FROM public.testes_catalogo AS tc
LEFT JOIN public.resultados_testes AS rt
    ON rt.teste_id = tc.id
GROUP BY tc.regiao, tc.id, tc.nome;
~~~

### Testes

- Denominador zero sem divisão por zero.
- Percentuais conferidos manualmente com mistura conhecida de positivos e negativos.
- Casos só com Não realizado/Inconclusivo.
- Dados respeitam acesso de aluno/professor.
- Grupos pequenos não ficam expostos pelo dashboard.

**Commit:** ORT-10: cria views agregadas para o dashboard

**Título do PR:** ORT-10: adiciona views de positivos por teste, região e idade

No PR, liste as três views e a validação. Use **Refs #10** enquanto parcial e **Closes #10** somente após cumprir todos os critérios.

---

## ORT-11 — Schemas Pydantic

**Objetivo:** validar as entradas antes de acessar o banco.

Amplie **backend/schemas.py** e **tests/test_schemas.py**. Preserve os enums Resultado/Lado e o modelo ResultadoTeste atual.

Implemente modelos de entrada e resposta para participantes, avaliações, resultados, lote de resultados e sinalização ao professor. Use enums para resultado/lado, tipos adequados para IDs/datas e ConfigDict(extra="forbid") nos modelos de entrada.

Exemplo:

~~~python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ParticipanteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idade: int = Field(gt=0)
    peso_kg: float = Field(gt=0)
    altura_m: float = Field(ge=0.5, le=2.5)
    consentimento: bool
    data_consentimento: datetime | None = None
~~~

Regras importantes:
- O serviço deve consultar o banco para confirmar consentimento antes de criar avaliação; Pydantic sozinho não confirma o estado persistido.
- Use model_validator(mode="after") em lote para rejeitar duplicidades de (teste_id, lado), conforme a constraint do banco.
- Não deixe o cliente escolher avaliador_id arbitrário: use o usuário validado pelo middleware.
- Não confunda os limites usados em dados fictícios com as regras reais de negócio.

### Testes

- Dor -1 e 11 rejeitadas; 0 e 10 aceitas.
- Lado/resultado inválidos rejeitados.
- Campos inesperados e observações excessivas rejeitados.
- Idade, peso e altura fora dos limites rejeitados.
- Lote duplicado rejeitado; lote válido aceito.
- Testes atuais de ResultadoTeste continuam passando.

~~~powershell
python -m pytest -q tests/test_schemas.py
python -m pytest -q
~~~

**Commit:** ORT-11: amplia schemas Pydantic das entidades

**Título do PR:** ORT-11: valida entradas da API com Pydantic

No corpo, explique os modelos adicionados e os casos cobertos. Use **Refs #11** enquanto parcial.

---

## ORT-12 — JWT e papéis do usuário

**Objetivo:** proteger endpoints e aplicar autorização conforme o usuário autenticado.

### Implementação

1. Se ainda não existir, crie um ponto de entrada Flask (por exemplo, **backend/app.py**) e um módulo de autenticação (por exemplo, **backend/auth.py**).
2. Leia **Authorization: Bearer <access_token>**.
3. Valide o JWT com Supabase Auth. Não basta decodificar o token ou confiar em user_id enviado no JSON. O método Python **supabase.auth.get_user(jwt)** valida o access token no servidor.
4. Armazene o ID validado em flask.g durante a requisição.
5. Crie mecanismos reutilizáveis de autenticação e papel, por exemplo require_auth e require_role("professor").
6. Retorne 401 para token ausente/inválido e 403 para papel insuficiente.
7. Mantenha pública somente a rota de saúde e outras rotas explicitamente declaradas.
8. Não imprima token, senha ou chave nos logs.

### Atenção à service_role

A chave service_role ignora RLS. Se o backend a utilizar nas consultas, ele precisa checar explicitamente proprietário e permissões em cada operação. Prefira encaminhar o JWT do usuário nas operações que devem respeitar RLS ou implemente/teste filtros de proprietário. A chave administrativa fica somente no servidor, nunca no Flet, Git ou documentação.

### Testes

- Sem token, formato errado, token expirado/adulterado → 401.
- Token válido identifica o usuário correto.
- Aluno em rota exclusiva de professor → 403.
- Professor autenticado acessa a ação permitida.
- Rota pública funciona sem token.
- Nenhuma resposta/log revela segredo.

**Commit:** ORT-12: valida JWT e aplica papéis de acesso

**Título do PR:** ORT-12: protege a API com JWT do Supabase

Liste os testes de autenticação e autorização. Use **Refs #12** até cumprir os critérios.

---

## ORT-13 — Endpoints principais da API

**Objetivo:** permitir que o app Flet use catálogo, participantes, avaliações e resultados.

Use a organização que já existir no backend. O contrato mínimo sugerido é:

| Método/caminho | Finalidade |
|---|---|
| GET /health | Confirmar API ativa |
| GET /api/v1/catalogo | Listar os 16 testes |
| GET /api/v1/participantes | Listar os registros permitidos |
| POST /api/v1/participantes | Criar participante |
| GET /api/v1/participantes/<id> | Consultar participante autorizado |
| POST /api/v1/avaliacoes | Criar avaliação |
| GET /api/v1/avaliacoes/<id> | Consultar avaliação/resumo |
| GET /api/v1/avaliacoes/<id>/resultados | Listar resultados |
| POST /api/v1/avaliacoes/<id>/resultados | Validar e salvar lote |

Confirme as rotas existentes e a Issue antes de fixar os paths; não crie endpoints duplicados.

### Regras

- Valide JSON usando Pydantic.
- Use o usuário do middleware como avaliador.
- Confirme propriedade, existência e consentimento antes de criar avaliação.
- Valide o lote inteiro antes de gravar; um lote inválido não pode deixar metade dos resultados persistidos.
- Trate duplicidade de avaliação/teste/lado e erros do banco consistentemente.
- Não revele registros de outro aluno.
- Padronize erros: 400 payload inválido; 401 sem autenticação; 403 sem permissão; 404 recurso não encontrado/indisponível; 409 conflito; 500 falha inesperada sem detalhes internos.

### Testes

- Catálogo devolve os 16 testes.
- Criar/consultar participante e avaliação com payload válido.
- Payload inválido rejeitado.
- Aluno não acessa dados de outro aluno.
- Falta de consentimento bloqueia avaliação.
- Lote inválido não é parcialmente gravado.
- Duplicidade e erros HTTP são tratados.
- Respostas não incluem dados pessoais desnecessários.

**Commit:** ORT-13: implementa endpoints principais da API

**Título do PR:** ORT-13: adiciona endpoints de participantes, avaliações e resultados

Liste as rotas implementadas e os testes. Use **Refs #13** enquanto parcial.

---

## ORT-14 — Status e progresso calculados

**Objetivo:** calcular Completo/Incompleto e progresso a partir do catálogo e dos resultados persistidos. Não armazene uma coluna de status redundante que possa ficar desatualizada.

A PR **#56** já contém uma parte do cálculo. Revise-a e continue o código existente: a pendência declarada é conectar o cálculo aos resultados persistidos e à resposta da API.

### Integração

1. O serviço carrega IDs dos testes esperados e resultados da avaliação.
2. Conte testes esperados únicos, não linhas brutas: pode existir resultado por lado.
3. Resultado válido significa teste respondido. Não realizado e Inconclusivo contam como respondidos; linha ausente/vazia não conta.
4. Status só é Completo quando todos os testes esperados estiverem respondidos.
5. Progresso = respondidos/esperados, com proteção para total zero.
6. Inclua na resposta da API status, testes_respondidos, testes_esperados e progresso_percentual (ou os nomes combinados no contrato).
7. Documente a regra em **docs/decisoes.md** e **docs/api.md**.

### Testes

- Zero resultados → Incompleto e progresso zero.
- Avaliação parcial → contagem/percentual corretos.
- Todos respondidos → Completo.
- Não realizado e Inconclusivo contam como respondidos.
- Resultados por lados diferentes não duplicam a contagem.
- API e função de cálculo retornam o mesmo valor.

**Commit:** se a PR #56 estiver aberta, continue nela. Se já tiver sido integrada, use ORT-14: integra status e progresso à API.

**Título do PR:** atualize a PR #56 existente quando possível; não abra uma PR duplicada.

Corpo sugerido:

~~~markdown
## O que foi feito
- Conecta o cálculo de status aos resultados persistidos.
- Inclui status e progresso na resposta da API.
- Mantém o status calculado, sem coluna redundante.

## Validação
- [ ] Casos parcial/completo cobertos
- [ ] Não realizado/Inconclusivo contam como respondidos
- [ ] Resultado por lado não duplica progresso
- [ ] Testes passaram

Refs #14
~~~

---

## ORT-15 — Sinalizar ao professor

**Objetivo:** permitir que um aluno sinalize uma avaliação para atenção do professor, sem alterar automaticamente resultado clínico ou status.

### Implementação

1. Confirme os campos planejados em **avaliacoes**: flag_professor e flag_motivo. Use os nomes do schema que estiver integrado.
2. Crie endpoint autenticado, por exemplo **POST /api/v1/avaliacoes/<id>/sinalizar-professor**.
3. Receba motivo obrigatório, não vazio e limitado (por exemplo, 500 caracteres), validado com Pydantic.
4. Confirme que o usuário pode sinalizar aquela avaliação.
5. Grave flag_professor = true e o motivo.
6. Permita que professor filtre/lista avaliações sinalizadas, com verificação de papel.
7. Defina se uma nova sinalização atualiza o motivo anterior ou é rejeitada; evite duplicidade e registre a decisão.

### Testes

- Dono consegue sinalizar; outro aluno não.
- Avaliação ausente/indisponível retorna erro documentado.
- Motivo ausente, vazio ou longo demais é rejeitado.
- Professor consegue localizar sinalizações.
- Status e resultados não mudam após a sinalização.

**Commit:** ORT-15: adiciona sinalização de avaliação ao professor

**Título do PR:** ORT-15: permite sinalizar avaliações para revisão do professor

Liste a validação no corpo. Use **Refs #15** enquanto parcial.

---

## ORT-16 — Documentar contrato REST em docs/api.md

**Objetivo:** permitir que o Flet integre sem depender de detalhes internos do backend.

Crie **docs/api.md** e documente o comportamento real após ORT-11 a ORT-15. Não apresente rota pendente como pronta.

Inclua:
1. visão geral, versão e base path;
2. comando real para executar a API localmente e configuração sem credenciais reais;
3. autenticação Bearer e rotas públicas/protegidas;
4. permissões de aluno/professor e relação entre API e RLS;
5. formato de erros HTTP e exemplos JSON;
6. schemas de participante, avaliação, resultado, lote, progresso e sinalização;
7. para cada endpoint: método, caminho, papel permitido, corpo, resposta e erros;
8. consentimento, valores de lado/resultado, cálculo de progresso e propriedade;
9. exemplos de fluxo: consultar catálogo, criar participante, abrir avaliação, enviar resultados e consultar progresso;
10. regras de privacidade: apenas dados fictícios durante desenvolvimento, sem nome completo, segredo ou alegação de diagnóstico;
11. endpoints pendentes claramente marcados.

Compare cada rota documentada com a rota Flask real. Exemplos devem corresponder aos modelos Pydantic e aos testes. Atualize a documentação na mesma PR em que o contrato mudar.

**Commit:** ORT-16: documenta contrato da API

**Título do PR:** ORT-16: documenta endpoints, autenticação e exemplos da API

Corpo sugerido:

~~~markdown
## O que foi feito
- Cria docs/api.md com o contrato REST.
- Documenta autenticação, papéis, payloads, respostas e erros.
- Inclui exemplos alinhados aos endpoints implementados.

## Validação
- [ ] Rotas comparadas com a documentação
- [ ] Payloads correspondem aos schemas
- [ ] Exemplos conferidos com testes
- [ ] Nenhum segredo ou dado pessoal incluído
- [ ] git diff --check passou

Closes #16
~~~

Use **Closes #16** somente quando o contrato estiver revisado; antes disso, use **Refs #16**.

---

## Checklist de PR e merge

Antes da PR:
- [ ] Uma ORT por branch/PR, branch baseada na main atualizada.
- [ ] Descrição lista implementação e validação.
- [ ] Issue referenciada: **Refs #N** durante trabalho parcial; **Closes #N** quando os critérios forem atendidos.
- [ ] Testes relevantes e **python -m pytest -q** passaram.
- [ ] **git diff --check** passou.
- [ ] Nenhum segredo, dado real ou arquivo temporário no commit.
- [ ] RLS testada com sessão normal, não só com service_role.
- [ ] Documentação e decisões atualizadas.

Depois da PR:
1. Revise o diff no GitHub e compare com a Issue.
2. Corrija comentários e rode os testes novamente.
3. Faça merge somente com os critérios atendidos; use Squash and merge se for o padrão do projeto.
4. Exclua a branch remota após o merge, se permitido.
5. Atualize a main local antes de abrir a branch da próxima ORT.

Não mova a Issue para concluída só porque existe commit ou PR aberta: o merge representa entrega testada e revisada.

## Referências técnicas

- Supabase Python — validação de JWT com auth.get_user(jwt): https://supabase.com/docs/reference/python/auth-getuser
- Supabase — views e security_invoker para respeitar RLS: https://supabase.com/docs/guides/database/views
- Supabase Python — grants e políticas RLS: https://supabase.com/docs/reference/python/installing
- Flask — decorators para rotas protegidas: https://flask.palletsprojects.com/en/stable/patterns/viewdecorators/

Nomes finais de campos/rotas devem seguir o schema e o código realmente integrados à branch principal.
