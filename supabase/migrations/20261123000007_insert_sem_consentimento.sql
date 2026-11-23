-- O termo de consentimento saiu do app (ADR-050): o cadastro não exige mais consentimento = true.
DROP POLICY IF EXISTS participantes_insert ON public.participantes;
CREATE POLICY participantes_insert ON public.participantes FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()));
