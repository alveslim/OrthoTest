-- Termo de consentimento por participante, nome/sobrenome OPCIONAIS e código automático.
-- Decisão registrada em docs/decisoes.md (ADR-049): nome e sobrenome são opcionais, ficam só na tabela
-- `participantes` (RLS: aluno vê os que criou, professor vê todos) e NUNCA entram em views, CSV ou IA.

ALTER TABLE public.participantes
  ADD COLUMN IF NOT EXISTS nome                      VARCHAR(60),
  ADD COLUMN IF NOT EXISTS sobrenome                 VARCHAR(80),
  ADD COLUMN IF NOT EXISTS termo_versao              VARCHAR(30),
  ADD COLUMN IF NOT EXISTS consentimento_responsavel BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.participantes
  DROP CONSTRAINT IF EXISTS consentimento_exige_termo,
  DROP CONSTRAINT IF EXISTS menor_exige_responsavel;
ALTER TABLE public.participantes
  ADD CONSTRAINT consentimento_exige_termo
    CHECK (consentimento = FALSE OR termo_versao IS NOT NULL),
  ADD CONSTRAINT menor_exige_responsavel
    CHECK (idade >= 18 OR consentimento = FALSE OR consentimento_responsavel);

-- Código P-001, P-002... gerado no banco quando o app não envia um (único por avaliador).
CREATE OR REPLACE FUNCTION public.gerar_codigo_participante()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  proximo INT;
BEGIN
  IF NEW.codigo IS NULL OR length(trim(NEW.codigo)) = 0 THEN
    PERFORM pg_advisory_xact_lock(hashtextextended(COALESCE(NEW.user_id::text, ''), 0));
    SELECT COALESCE(max(substring(codigo FROM '^P-([0-9]+)$')::INT), 0) + 1
      INTO proximo FROM participantes WHERE user_id = NEW.user_id;
    NEW.codigo := 'P-' || lpad(proximo::TEXT, 3, '0');
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS participantes_codigo ON public.participantes;
CREATE TRIGGER participantes_codigo
  BEFORE INSERT ON public.participantes
  FOR EACH ROW EXECUTE FUNCTION public.gerar_codigo_participante();

REVOKE EXECUTE ON FUNCTION public.gerar_codigo_participante() FROM PUBLIC, anon, authenticated;

GRANT UPDATE (nome, sobrenome) ON public.participantes TO authenticated;
