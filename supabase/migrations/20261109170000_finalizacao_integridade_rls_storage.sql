-- Finalização do OrthoTest: schema compatível, RLS completo e Storage privado.
-- Idempotente: pode ser aplicada após as migrations ORT-09/ORT-10 sem apagar registros.
-- A aplicação usa a chave anon + access token do usuário; NÃO usa service_role no backend.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Tabelas-base (em instalações novas) e colunas ausentes (instalações existentes).
CREATE TABLE IF NOT EXISTS public.perfis (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  nome_exibicao TEXT NOT NULL DEFAULT 'Avaliador',
  papel TEXT NOT NULL DEFAULT 'aluno' CHECK (papel IN ('aluno', 'professor')),
  criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.participantes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE RESTRICT DEFAULT auth.uid(),
  codigo VARCHAR(20) NOT NULL,
  idade SMALLINT NOT NULL CHECK (idade > 0 AND idade < 120),
  peso_kg NUMERIC(5,2) CHECK (peso_kg > 0 AND peso_kg < 400),
  altura_m NUMERIC(3,2) CHECK (altura_m BETWEEN 0.5 AND 2.5),
  consentimento BOOLEAN NOT NULL DEFAULT FALSE,
  data_consentimento TIMESTAMPTZ,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
  excluido_em TIMESTAMPTZ,
  CONSTRAINT participante_consentimento_exige_data
    CHECK (consentimento = FALSE OR data_consentimento IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS public.testes_catalogo (
  id SMALLINT PRIMARY KEY,
  regiao VARCHAR(50) NOT NULL,
  nome VARCHAR(100) NOT NULL UNIQUE,
  estrutura VARCHAR(150),
  definicao TEXT NOT NULL,
  objetivo TEXT NOT NULL,
  como_fazer TEXT NOT NULL,
  positivo_se TEXT NOT NULL,
  referencia TEXT,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.avaliacoes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participante_id UUID NOT NULL REFERENCES public.participantes(id) ON DELETE RESTRICT,
  avaliador_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT DEFAULT auth.uid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE RESTRICT DEFAULT auth.uid(),
  data_avaliacao TIMESTAMPTZ NOT NULL DEFAULT now(),
  status VARCHAR(20) NOT NULL DEFAULT 'pendente',
  progresso_percentual NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (progresso_percentual BETWEEN 0 AND 100),
  flag_professor BOOLEAN NOT NULL DEFAULT FALSE,
  flag_motivo TEXT,
  excluido_em TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS public.resultados_testes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  avaliacao_id UUID NOT NULL REFERENCES public.avaliacoes(id) ON DELETE RESTRICT,
  teste_id SMALLINT NOT NULL REFERENCES public.testes_catalogo(id) ON DELETE RESTRICT,
  lado VARCHAR(10) NOT NULL CHECK (lado IN ('Direito', 'Esquerdo', 'Bilateral')),
  resultado VARCHAR(20) NOT NULL CHECK (resultado IN ('Positivo', 'Negativo', 'Não realizado', 'Inconclusivo')),
  valor_medido NUMERIC(5,1),
  dor_0_10 SMALLINT CHECK (dor_0_10 BETWEEN 0 AND 10),
  observacoes TEXT,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.ia_rascunhos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  avaliacao_id UUID NOT NULL REFERENCES public.avaliacoes(id) ON DELETE RESTRICT,
  texto TEXT NOT NULL,
  gerado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
  revisado_por UUID REFERENCES auth.users(id) ON DELETE RESTRICT,
  aprovado BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT ia_aprovado_exige_revisor
    CHECK (aprovado = FALSE OR revisado_por IS NOT NULL)
);

-- Garante as colunas esperadas mesmo em bancos criados parcialmente fora das migrations.
ALTER TABLE public.perfis ADD COLUMN IF NOT EXISTS nome_exibicao TEXT NOT NULL DEFAULT 'Avaliador';
ALTER TABLE public.perfis ADD COLUMN IF NOT EXISTS papel TEXT NOT NULL DEFAULT 'aluno';
ALTER TABLE public.participantes ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) DEFAULT auth.uid();
ALTER TABLE public.participantes ADD COLUMN IF NOT EXISTS excluido_em TIMESTAMPTZ;
ALTER TABLE public.testes_catalogo ADD COLUMN IF NOT EXISTS estrutura VARCHAR(150);
ALTER TABLE public.testes_catalogo ADD COLUMN IF NOT EXISTS referencia TEXT;
ALTER TABLE public.testes_catalogo ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE public.avaliacoes ADD COLUMN IF NOT EXISTS avaliador_id UUID REFERENCES auth.users(id) DEFAULT auth.uid();
ALTER TABLE public.avaliacoes ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) DEFAULT auth.uid();
ALTER TABLE public.avaliacoes ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pendente';
ALTER TABLE public.avaliacoes ADD COLUMN IF NOT EXISTS progresso_percentual NUMERIC(5,2) NOT NULL DEFAULT 0;
ALTER TABLE public.avaliacoes ADD COLUMN IF NOT EXISTS flag_professor BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE public.avaliacoes ADD COLUMN IF NOT EXISTS flag_motivo TEXT;
ALTER TABLE public.avaliacoes ADD COLUMN IF NOT EXISTS excluido_em TIMESTAMPTZ;
ALTER TABLE public.resultados_testes ADD COLUMN IF NOT EXISTS valor_medido NUMERIC(5,1);
ALTER TABLE public.resultados_testes ADD COLUMN IF NOT EXISTS dor_0_10 SMALLINT;
ALTER TABLE public.resultados_testes ADD COLUMN IF NOT EXISTS observacoes TEXT;
ALTER TABLE public.ia_rascunhos ADD COLUMN IF NOT EXISTS texto TEXT;
ALTER TABLE public.ia_rascunhos ADD COLUMN IF NOT EXISTS gerado_em TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.ia_rascunhos ADD COLUMN IF NOT EXISTS revisado_por UUID REFERENCES auth.users(id);
ALTER TABLE public.ia_rascunhos ADD COLUMN IF NOT EXISTS aprovado BOOLEAN NOT NULL DEFAULT FALSE;

-- Corrige a divergência histórica entre avaliador_id e user_id sem atribuir registros
-- órfãos arbitrariamente a quem executa a migration.
UPDATE public.avaliacoes
SET user_id = avaliador_id
WHERE user_id IS NULL AND avaliador_id IS NOT NULL;

UPDATE public.avaliacoes
SET avaliador_id = user_id
WHERE avaliador_id IS NULL AND user_id IS NOT NULL;

UPDATE public.participantes p
SET user_id = (
  SELECT a.avaliador_id
  FROM public.avaliacoes a
  WHERE a.participante_id = p.id
    AND a.avaliador_id IS NOT NULL
  ORDER BY a.data_avaliacao ASC
  LIMIT 1
)
WHERE p.user_id IS NULL
  AND EXISTS (
    SELECT 1 FROM public.avaliacoes a
    WHERE a.participante_id = p.id AND a.avaliador_id IS NOT NULL
  );

-- Restrições e índices idempotentes.
CREATE UNIQUE INDEX IF NOT EXISTS ux_participantes_user_codigo
  ON public.participantes(user_id, codigo) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_avaliacoes_avaliador
  ON public.avaliacoes(avaliador_id);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_participante
  ON public.avaliacoes(participante_id);
CREATE INDEX IF NOT EXISTS idx_resultados_avaliacao
  ON public.resultados_testes(avaliacao_id);
CREATE INDEX IF NOT EXISTS idx_resultados_teste
  ON public.resultados_testes(teste_id);
CREATE INDEX IF NOT EXISTS idx_ia_rascunhos_avaliacao
  ON public.ia_rascunhos(avaliacao_id);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'resultado_unico_por_lado'
      AND conrelid = 'public.resultados_testes'::regclass
  ) THEN
    ALTER TABLE public.resultados_testes
      ADD CONSTRAINT resultado_unico_por_lado
      UNIQUE (avaliacao_id, teste_id, lado);
  END IF;
END $$;

-- 2) RLS em todas as tabelas com dados.
ALTER TABLE public.perfis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.participantes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.testes_catalogo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.avaliacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resultados_testes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ia_rascunhos ENABLE ROW LEVEL SECURITY;

-- Apaga apenas as políticas com estes nomes para permitir reaplicar esta migration.
DROP POLICY IF EXISTS "perfil_proprio_ou_professor" ON public.perfis;
DROP POLICY IF EXISTS "catalogo_leitura_autenticada" ON public.testes_catalogo;
DROP POLICY IF EXISTS "participantes_select_owner" ON public.participantes;
DROP POLICY IF EXISTS "participantes_insert_owner" ON public.participantes;
DROP POLICY IF EXISTS "participantes_update_owner" ON public.participantes;
DROP POLICY IF EXISTS "participantes_delete_owner" ON public.participantes;
DROP POLICY IF EXISTS "avaliacoes_select_owner" ON public.avaliacoes;
DROP POLICY IF EXISTS "avaliacoes_insert_owner" ON public.avaliacoes;
DROP POLICY IF EXISTS "avaliacoes_update_owner" ON public.avaliacoes;
DROP POLICY IF EXISTS "resultados_select_owner" ON public.resultados_testes;
DROP POLICY IF EXISTS "resultados_insert_owner" ON public.resultados_testes;
DROP POLICY IF EXISTS "resultados_update_owner" ON public.resultados_testes;
DROP POLICY IF EXISTS "resultados_delete_owner" ON public.resultados_testes;
DROP POLICY IF EXISTS "ia_select_owner_professor" ON public.ia_rascunhos;
DROP POLICY IF EXISTS "ia_insert_owner" ON public.ia_rascunhos;
DROP POLICY IF EXISTS "ia_update_professor" ON public.ia_rascunhos;

CREATE POLICY "perfil_proprio_ou_professor"
ON public.perfis FOR SELECT TO authenticated
USING (user_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor');

CREATE POLICY "catalogo_leitura_autenticada"
ON public.testes_catalogo FOR SELECT TO authenticated
USING (ativo = TRUE OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor');

CREATE POLICY "participantes_select_owner"
ON public.participantes FOR SELECT TO authenticated
USING (user_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor');
CREATE POLICY "participantes_insert_owner"
ON public.participantes FOR INSERT TO authenticated
WITH CHECK (user_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor');
CREATE POLICY "participantes_update_owner"
ON public.participantes FOR UPDATE TO authenticated
USING (user_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
WITH CHECK (user_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor');
CREATE POLICY "participantes_delete_owner"
ON public.participantes FOR DELETE TO authenticated
USING (user_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor');

CREATE POLICY "avaliacoes_select_owner"
ON public.avaliacoes FOR SELECT TO authenticated
USING (avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor');
CREATE POLICY "avaliacoes_insert_owner"
ON public.avaliacoes FOR INSERT TO authenticated
WITH CHECK (
  avaliador_id = auth.uid()
  AND EXISTS (
    SELECT 1 FROM public.participantes p
    WHERE p.id = participante_id
      AND (p.user_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
  )
);
CREATE POLICY "avaliacoes_update_owner"
ON public.avaliacoes FOR UPDATE TO authenticated
USING (avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
WITH CHECK (avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor');

CREATE POLICY "resultados_select_owner"
ON public.resultados_testes FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.avaliacoes a
    WHERE a.id = avaliacao_id
      AND (a.avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
  )
);
CREATE POLICY "resultados_insert_owner"
ON public.resultados_testes FOR INSERT TO authenticated
WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.avaliacoes a
    WHERE a.id = avaliacao_id
      AND (a.avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
  )
);
CREATE POLICY "resultados_update_owner"
ON public.resultados_testes FOR UPDATE TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.avaliacoes a
    WHERE a.id = avaliacao_id
      AND (a.avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.avaliacoes a
    WHERE a.id = avaliacao_id
      AND (a.avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
  )
);
CREATE POLICY "resultados_delete_owner"
ON public.resultados_testes FOR DELETE TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.avaliacoes a
    WHERE a.id = avaliacao_id
      AND (a.avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
  )
);

CREATE POLICY "ia_select_owner_professor"
ON public.ia_rascunhos FOR SELECT TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM public.avaliacoes a
    WHERE a.id = avaliacao_id
      AND (a.avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
  )
);
CREATE POLICY "ia_insert_owner"
ON public.ia_rascunhos FOR INSERT TO authenticated
WITH CHECK (
  revisado_por = auth.uid()
  AND (
    aprovado = FALSE
    OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor'
  )
  AND EXISTS (
    SELECT 1 FROM public.avaliacoes a
    WHERE a.id = avaliacao_id
      AND (a.avaliador_id = auth.uid() OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
  )
);
CREATE POLICY "ia_update_professor"
ON public.ia_rascunhos FOR UPDATE TO authenticated
USING ((auth.jwt() -> 'app_metadata' ->> 'role') = 'professor')
WITH CHECK (
  (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor'
  AND revisado_por = auth.uid()
);

-- 3) Views seguras para consultas futuras (invoker mantém as regras RLS do usuário).
CREATE OR REPLACE VIEW public.vw_positivos_por_teste
WITH (security_invoker = true) AS
SELECT t.id AS teste_id, t.nome, t.regiao,
       COUNT(*) FILTER (WHERE r.resultado = 'Positivo') AS positivos,
       COUNT(*) FILTER (WHERE r.resultado <> 'Não realizado') AS total_valido
FROM public.resultados_testes r
JOIN public.testes_catalogo t ON t.id = r.teste_id
GROUP BY t.id, t.nome, t.regiao;

CREATE OR REPLACE VIEW public.vw_positivos_por_regiao
WITH (security_invoker = true) AS
SELECT t.regiao,
       COUNT(*) FILTER (WHERE r.resultado = 'Positivo') AS positivos,
       COUNT(*) FILTER (WHERE r.resultado <> 'Não realizado') AS total_valido
FROM public.resultados_testes r
JOIN public.testes_catalogo t ON t.id = r.teste_id
GROUP BY t.regiao;

CREATE OR REPLACE VIEW public.vw_participantes_faixa_etaria
WITH (security_invoker = true) AS
SELECT CASE
  WHEN p.idade < 18 THEN 'Menor de 18'
  WHEN p.idade < 30 THEN '18 a 29'
  WHEN p.idade < 45 THEN '30 a 44'
  ELSE '45 ou mais'
END AS faixa_etaria,
COUNT(DISTINCT p.id) AS total
FROM public.participantes p
GROUP BY 1;

-- 4) Bucket privado para relatórios CSV. Arquivos ficam separados por usuário.
INSERT INTO storage.buckets (id, name, public)
VALUES ('relatorios', 'relatorios', FALSE)
ON CONFLICT (id) DO UPDATE SET public = FALSE;

DROP POLICY IF EXISTS "relatorios_upload_proprio" ON storage.objects;
DROP POLICY IF EXISTS "relatorios_leitura_propria_ou_professor" ON storage.objects;

CREATE POLICY "relatorios_upload_proprio"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'relatorios'
  AND split_part(name, '/', 1) = auth.uid()::text
);

CREATE POLICY "relatorios_leitura_propria_ou_professor"
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'relatorios'
  AND (
    split_part(name, '/', 1) = auth.uid()::text
    OR (auth.jwt() -> 'app_metadata' ->> 'role') = 'professor'
  )
);
