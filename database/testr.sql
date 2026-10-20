Planejando as etapas para implementar os testes de joelho.
Planejando as etapas para implementar os testes de joelho.

Antes de montar as instruções, vou ler o texto completo dos 4 testes do joelho na ficha, para o catálogo ficar fiel ao que o grupo escreveu.
Executou 4 comandos

Plano para fazer primeiro os 4 testes do joelho (Lachman, Gaveta Anterior, Estresse em Valgo e Estresse em Varo), na ordem de trabalho. Cada passo é um commit. O código dos passos 3 e 4 eu rodei aqui com Pydantic 2. O pytest não instalou neste ambiente, então rodei a mesma lógica em Python puro, e o SQL foi testado no SQLite.
0. Branch
bash

git switch main && git pull
git switch -c feat/joelho-testes

Mude o Status das Issues ORT-08, ORT-11 e ORT-21 no Project para “Em andamento”. Elas serão feitas só em parte nesta branch.
1. Catálogo dos 4 testes (parte do ORT-08)

Crie database/seed_catalogo.sql. Primeiro a tabela:
sql

CREATE TABLE testes_catalogo (
  id          SMALLINT PRIMARY KEY,
  regiao      VARCHAR(50)  NOT NULL,
  nome        VARCHAR(100) NOT NULL UNIQUE,
  estrutura   VARCHAR(100),
  definicao   TEXT NOT NULL,
  objetivo    TEXT NOT NULL,
  como_fazer  TEXT NOT NULL,
  positivo_se TEXT NOT NULL,
  referencia  TEXT          -- fica NULL até o ORT-02 trazer a fonte verificada
);

Depois um INSERT por teste, copiando fielmente as fichas de Sabrina e Vinícius. Resumo do que cada um deve conter:
id	Teste	Estrutura	Posição do joelho	Positivo se
1	Lachman	LCA	20° a 30° de flexão	aumento da translação anterior da tíbia, ponto final amolecido ou instabilidade
2	Gaveta Anterior	LCA	90° de flexão	translação anterior excessiva, maior que no lado oposto
3	Estresse em Valgo	LCM	extensão e 20° a 30°	dor medial e/ou abertura excessiva do espaço medial
4	Estresse em Varo	LCL	extensão e 20° a 30°	dor lateral e/ou abertura excessiva do espaço lateral

Não invente a referencia: deixe NULL.
2. Decisão do grupo antes de seguir

O Valgo e o Varo são feitos em duas posições (extensão e 20° a 30°), mas o banco guarda um resultado por teste e lado. Sugiro registrar um só resultado (positivo se alguma posição for positiva) e anotar a posição em observacoes. Registre isso em docs/decisoes.md.
3. Modelo de validação (parte do ORT-11)

backend/schemas.py (crie também backend/__init__.py vazio):
python

from enum import Enum
from pydantic import BaseModel, Field

class Resultado(str, Enum):
    POSITIVO = "Positivo"
    NEGATIVO = "Negativo"
    NAO_REALIZADO = "Não realizado"
    INCONCLUSIVO = "Inconclusivo"

class Lado(str, Enum):
    DIREITO = "Direito"
    ESQUERDO = "Esquerdo"
    BILATERAL = "Bilateral"

class ResultadoTeste(BaseModel):
    avaliacao_id: str
    teste_id: int
    lado: Lado
    resultado: Resultado
    dor_0_10: int | None = Field(default=None, ge=0, le=10)
    valor_medido: float | None = None
    observacoes: str | None = Field(default=None, max_length=500)

4. Testes automáticos

tests/test_schemas.py:
python

import pytest
from pydantic import ValidationError
from backend.schemas import ResultadoTeste

BASE = dict(avaliacao_id="a1", teste_id=1, lado="Direito", resultado="Positivo")

def test_dor_acima_de_10_e_rejeitada():
    with pytest.raises(ValidationError):
        ResultadoTeste(**BASE, dor_0_10=11)

def test_lado_invalido_e_rejeitado():
    with pytest.raises(ValidationError):
        ResultadoTeste(**{**BASE, "lado": "Frente"})

def test_nao_realizado_sem_dor_e_aceito():
    r = ResultadoTeste(**{**BASE, "resultado": "Não realizado"})
    assert r.dor_0_10 is None

Rode com pytest -q.
5. Tela do teste (parte do ORT-21)

Faça a tela de acordo com o design: título “Teste de Lachman”, um bloco “Como fazer” (lido do catálogo), seletor de lado (Direito, Esquerdo, Bilateral), 4 botões de resultado, dor de 0 a 10 (slider com 10 divisões), campo de observações e o botão “Salvar e próximo”. Comece com o Lachman e reaproveite a mesma tela para os outros três, trocando só o teste_id. Lembre que a ficha manda comparar com o lado oposto, então coloque essa dica na tela. Os nomes dos componentes do Flet mudam entre versões, então fixe a versão no requirements.txt antes. Para popular a tela, use os dados do ORT-05 filtrando teste_id de 1 a 4.
6. Fechamento
bash

git add .
git commit -m "ORT-08: catálogo dos testes do joelho"
git push -u origin feat/joelho-testes

Abra o Pull Request com Refs #8 #11 #21 (não Closes, porque são entregas parciais). Peça revisão de um colega, que deve conferir principalmente o texto clínico do catálogo contra a ficha.

Pronto quando: os 4 testes estão no catálogo, o modelo rejeita dor fora de 0 a 10 e lado inválido, e a tela salva um resultado de Lachman e de Varo.

Quer que eu escreva o seed_catalogo.sql completo dos 4 testes, copiando as fichas, e a tela em Flet para a versão que você fixar?

beleza, mas so trabalhando a ort-5
Adaptando o script para filtrar testes por região.

Entendi: vamos ficar só no ORT-05 e usar o joelho como foco. Vou fazer o gerador aceitar uma região (--regioes Joelho), de modo que ele gere dados fictícios só para os 4 testes do joelho.
Editou um arquivo
Gerar dados
PY 

me mostre como fzr a issue 6, me diga os passo a passo, oq escrever e como eu posso ir subindo? e voce acha interessante ficar fzd uma branch pra cada issue nova? ou uma branch para cada etapa? ou um fork? oq seria mais organizado.
Traduzindo o esquema para SQLite e planejando a estratégia de branches no Git.

Antes de responder, vou conferir duas coisas: se a alteração que deixei no gerador do ORT-05 ficou correta, e a Issue #6 como está hoje no GitHub.
Criou um arquivo, compartilhou 2 arquivos, executou 7 comandos
Branches: uma por Issue

Use uma branch curta por Issue. Não use uma por etapa, e não use fork.

    Uma por etapa vira uma branch de semanas, cheia de coisas misturadas. Os conflitos aparecem tarde e fica difícil revisar.
    Fork serve para quem não tem permissão no repositório. Você e seu amigo são colaboradores do alveslim/OrthoTest, então um fork só duplicaria o trabalho.
    Uma por Issue gera um PR pequeno, fácil de revisar, e o Closes #6 fecha a tarefa sozinho. Se duas Issues forem muito pequenas e do mesmo assunto (ORT-06 e ORT-07, por exemplo), pode juntar as duas numa branch.
    A etapa fica organizada pelo Milestone e pelo Project, não pelo Git.

Fluxo: main sempre funcionando, branch nova a partir da main atualizada, PR com squash merge, e apagar a branch depois.
ORT-06: passo a passo

1. Criar a branch
bash

git checkout main && git pull
git checkout -b feat/ort-06-schema-sql
mkdir -p database

2. Escrever database/schema.sql em 3 partes, com um commit em cada

O arquivo completo está no schema.sql que enviei. Cole por partes para o histórico ficar legível:
Commit	O que colar	Mensagem
1	Seções 1 e 3: participantes e avaliacoes	feat(db): tabelas participantes e avaliacoes (Refs #6)
2	Seções 2 e 4: testes_catalogo e resultados_testes	feat(db): catalogo de testes e resultados (Refs #6)
3	Seções 5, 6 e 7: ia_rascunhos, índices e RLS	feat(db): rascunhos da IA, indices e RLS (Refs #6)

Pela ordem dos commits, a seção 2 (testes_catalogo) vem antes da 3 só no arquivo final. Se preferir que cada commit rode sozinho, comece pelo commit 1 com participantes e testes_catalogo. O importante é que as tabelas referenciadas existam antes das que apontam para elas.

Depois de cada parte:
bash

git add database/schema.sql
git commit -m "feat(db): ... (Refs #6)"
git push -u origin feat/ort-06-schema-sql   # só no primeiro push; depois, git push

Abra o Draft PR logo depois do primeiro push. Use Refs #6 nos commits e deixe o Closes #6 só no PR.

3. Aplicar num projeto Supabase de desenvolvimento

Antes, crie pelo menos 1 usuário em Authentication > Users (o schema referencia auth.users). Depois cole o schema.sql no SQL Editor e rode. Não rode duas vezes: o script não é idempotente e a segunda execução dá erro.

4. Provar que as regras funcionam

Rode o testes_schema.sql no mesmo SQL Editor. Ele tenta inserir 16 valores inválidos, como idade 0, dor 11, resultado duplicado e consentimento sem data. Também insere 2 válidos. No fim ele desfaz tudo (ROLLBACK). O esperado é a mensagem ok em todas as linhas. Coloque um print dessa saída no PR como evidência.

5. Documentar

Crie docs/decisoes.md com poucas linhas:

    a data é guardada em TIMESTAMPTZ;
    o status Completo/Incompleto é calculado e não é coluna;
    ON DELETE RESTRICT evita apagar em cascata;
    RLS ligado e sem políticas até o ORT-09.

6. Fechar

Marque o PR como Ready, escreva Closes #6 na descrição e mova o card para Em revisão. Seu amigo revisa, vocês fazem squash merge e o card vai para Done.
O que testei e o que não testei

Testei o schema num PostgreSQL 16 local, não no Supabase. Lá ele aplica sem erro, bloqueia as 16 entradas inválidas, aceita as 2 válidas, e os CSVs do ORT-05 carregam sem violar nenhuma regra. Em Supabase não rodei. A diferença provável é só a tabela auth.users, que lá já existe.

Dois cuidados:

    Os avaliador_id dos dados fictícios são inventados. Para carregá-los no Supabase, troque-os pelos IDs de usuários reais do Auth.
    excluido_em entra no ORT-07, e as tabelas perfis e as políticas entram no ORT-09. Não precisa antecipar.

Se você me autorizar a escrever no repositório, posso criar a branch, os 3 commits e o Draft PR. Sem essa autorização, não envio nada ao GitHub. O PostgreSQL temporário que usei já foi desligado e apagado.
Schema
Código·SQL 
Testes schema
Código·SQL 
Conversa compactada
Conversa compactada
O Claude trabalha diretamente com sua base de código


Schema · SQL
-- OrtoCheck: schema do banco (ORT-06)
-- Como aplicar: Supabase > SQL Editor > cole este arquivo > Run.
-- Use um projeto de DESENVOLVIMENTO. O script não é idempotente: rodar duas vezes dá erro.
-- Datas ficam em TIMESTAMPTZ. A exclusão lógica (excluido_em) entra no ORT-07.
-- As políticas de acesso (RLS) entram no ORT-09; até lá as tabelas ficam fechadas (ver o fim).
 
-- ============================================================ 1. participantes
-- Sem nome completo: o participante é identificado só por um código (ex.: P-001).
CREATE TABLE participantes (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo             VARCHAR(20)  NOT NULL UNIQUE,
  idade              SMALLINT     NOT NULL CHECK (idade > 0 AND idade < 120),
  peso_kg            NUMERIC(5,2) CHECK (peso_kg > 0 AND peso_kg < 400),
  altura_m           NUMERIC(3,2) CHECK (altura_m BETWEEN 0.5 AND 2.5),
  consentimento      BOOLEAN      NOT NULL DEFAULT FALSE,
  data_consentimento TIMESTAMPTZ,
  criado_em          TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CONSTRAINT consentimento_exige_data
    CHECK (consentimento = FALSE OR data_consentimento IS NOT NULL)
);
 
-- ============================================================ 2. testes_catalogo
-- Os dados dos 16 testes entram no ORT-08. A tabela precisa existir antes por causa da FK.
CREATE TABLE testes_catalogo (
  id          SMALLINT     PRIMARY KEY,
  regiao      VARCHAR(50)  NOT NULL
              CHECK (regiao IN ('Joelho', 'Tornozelo', 'Ombro', 'Punho', 'Coluna')),
  nome        VARCHAR(100) NOT NULL UNIQUE,
  definicao   TEXT         NOT NULL,
  objetivo    TEXT         NOT NULL,
  como_fazer  TEXT         NOT NULL,
  positivo_se TEXT         NOT NULL,
  referencia  TEXT                     -- fica NULL até haver fonte bibliográfica verificada
);
 
-- ============================================================ 3. avaliacoes
-- avaliador_id aponta para o usuário do Supabase Auth (quem aplicou os testes).
-- ON DELETE RESTRICT: nada some em cascata; a exclusão será lógica (ORT-07).
CREATE TABLE avaliacoes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participante_id UUID        NOT NULL REFERENCES participantes (id) ON DELETE RESTRICT,
  avaliador_id    UUID        NOT NULL REFERENCES auth.users (id)    ON DELETE RESTRICT,
  data_avaliacao  TIMESTAMPTZ NOT NULL DEFAULT now(),
  flag_professor  BOOLEAN     NOT NULL DEFAULT FALSE,
  flag_motivo     TEXT
);
-- O status (Completo/Incompleto) NÃO é coluna: é calculado a partir dos resultados.
 
-- ============================================================ 4. resultados_testes
-- Um registro por teste e lado em cada avaliação.
CREATE TABLE resultados_testes (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  avaliacao_id UUID        NOT NULL REFERENCES avaliacoes (id)      ON DELETE RESTRICT,
  teste_id     SMALLINT    NOT NULL REFERENCES testes_catalogo (id) ON DELETE RESTRICT,
  lado         VARCHAR(10) NOT NULL
               CHECK (lado IN ('Direito', 'Esquerdo', 'Bilateral')),
  resultado    VARCHAR(15) NOT NULL
               CHECK (resultado IN ('Positivo', 'Negativo', 'Não realizado', 'Inconclusivo')),
  valor_medido NUMERIC(5,1),                       -- ângulo em graus, quando existir (ex.: Lasègue)
  dor_0_10     SMALLINT    CHECK (dor_0_10 BETWEEN 0 AND 10),
  observacoes  TEXT,
  CONSTRAINT resultado_unico_por_lado UNIQUE (avaliacao_id, teste_id, lado)
);
 
-- ============================================================ 5. ia_rascunhos
-- Resumos gerados pela IA. São RASCUNHO: só valem depois de revisados por uma pessoa.
CREATE TABLE ia_rascunhos (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  avaliacao_id UUID        NOT NULL REFERENCES avaliacoes (id) ON DELETE RESTRICT,
  texto        TEXT        NOT NULL,
  gerado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
  revisado_por UUID        REFERENCES auth.users (id) ON DELETE RESTRICT,
  aprovado     BOOLEAN     NOT NULL DEFAULT FALSE,
  CONSTRAINT aprovado_exige_revisor CHECK (aprovado = FALSE OR revisado_por IS NOT NULL)
);
 
-- ============================================================ 6. índices das chaves estrangeiras
-- O Postgres não cria índice sozinho em FK. O UNIQUE de resultados_testes já cobre avaliacao_id.
CREATE INDEX idx_avaliacoes_participante ON avaliacoes (participante_id);
CREATE INDEX idx_avaliacoes_avaliador    ON avaliacoes (avaliador_id);
CREATE INDEX idx_resultados_teste        ON resultados_testes (teste_id);
CREATE INDEX idx_ia_rascunhos_avaliacao  ON ia_rascunhos (avaliacao_id);
 
-- ============================================================ 7. segurança provisória
-- No Supabase, tabela sem RLS fica legível pela chave pública (anon). Ligar o RLS sem criar
-- políticas bloqueia o acesso direto; o backend (chave service_role) continua funcionando.
-- As políticas reais (aluno vê o que criou, professor vê tudo) entram no ORT-09.
ALTER TABLE participantes     ENABLE ROW LEVEL SECURITY;
ALTER TABLE testes_catalogo   ENABLE ROW LEVEL SECURITY;
ALTER TABLE avaliacoes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE resultados_testes ENABLE ROW LEVEL SECURITY;
ALTER TABLE ia_rascunhos      ENABLE ROW LEVEL SECURITY;
 
Claude terminou a resposta
