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

CREATE TABLE IF NOT EXISTS testes_catalogo (
  id          SMALLINT     PRIMARY KEY,
  regiao      VARCHAR(50)  NOT NULL
              CHECK (regiao IN ('Joelho', 'Tornozelo', 'Ombro', 'Punho', 'Coluna')),
  nome        VARCHAR(100) NOT NULL UNIQUE,
  estrutura   VARCHAR(100),            -- ligamento/estrutura avaliada (ex.: LCA)
  definicao   TEXT         NOT NULL,
  objetivo    TEXT         NOT NULL,
  como_fazer  TEXT         NOT NULL,
  positivo_se TEXT         NOT NULL,
  referencia  TEXT                     -- fica NULL até haver fonte bibliográfica verificada
);

CREATE TABLE avaliacoes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participante_id UUID        NOT NULL REFERENCES participantes (id) ON DELETE RESTRICT,
  avaliador_id    UUID        NOT NULL REFERENCES auth.users (id)    ON DELETE RESTRICT,
  data_avaliacao  TIMESTAMPTZ NOT NULL DEFAULT now(),
  flag_professor  BOOLEAN     NOT NULL DEFAULT FALSE,
  flag_motivo     TEXT
);

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

CREATE TABLE ia_rascunhos (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  avaliacao_id UUID        NOT NULL REFERENCES avaliacoes (id) ON DELETE RESTRICT,
  texto        TEXT        NOT NULL,
  gerado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
  revisado_por UUID        REFERENCES auth.users (id) ON DELETE RESTRICT,
  aprovado     BOOLEAN     NOT NULL DEFAULT FALSE,
  CONSTRAINT aprovado_exige_revisor CHECK (aprovado = FALSE OR revisado_por IS NOT NULL)
);

-- O Postgres não cria índice sozinho em FK. O UNIQUE de resultados_testes já cobre avaliacao_id.
CREATE INDEX idx_avaliacoes_participante ON avaliacoes (participante_id);
CREATE INDEX idx_avaliacoes_avaliador    ON avaliacoes (avaliador_id);
CREATE INDEX idx_resultados_teste        ON resultados_testes (teste_id);
CREATE INDEX idx_ia_rascunhos_avaliacao  ON ia_rascunhos (avaliacao_id);

-- ============================================================ segurança provisória
-- No Supabase, tabela sem RLS fica legível pela chave pública (anon). Ligar o RLS sem criar
-- políticas bloqueia o acesso direto; o backend (chave service_role) continua funcionando.
-- As políticas reais (aluno vê o que criou, professor vê tudo) entram no ORT-09.
ALTER TABLE participantes     ENABLE ROW LEVEL SECURITY;
ALTER TABLE testes_catalogo   ENABLE ROW LEVEL SECURITY;
ALTER TABLE avaliacoes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE resultados_testes ENABLE ROW LEVEL SECURITY;
ALTER TABLE ia_rascunhos      ENABLE ROW LEVEL SECURITY;