-- OrtoCheck · RLS (ORT-09): aluno vê o que criou; professor vê tudo; anônimo não vê nada.

CREATE OR REPLACE FUNCTION public.eh_professor()
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM perfis WHERE user_id = (SELECT auth.uid()) AND papel = 'professor');
$$;
REVOKE EXECUTE ON FUNCTION public.eh_professor() FROM PUBLIC, anon;
GRANT  EXECUTE ON FUNCTION public.eh_professor() TO authenticated;

ALTER TABLE public.perfis             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.testes_catalogo    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.participantes      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.avaliacoes         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resultados_testes  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ia_rascunhos       ENABLE ROW LEVEL SECURITY;

-- Privilégios mínimos: anon não toca em nada; authenticated só o necessário.
REVOKE ALL ON public.perfis, public.testes_catalogo, public.participantes,
              public.avaliacoes, public.resultados_testes, public.ia_rascunhos FROM anon;
REVOKE ALL ON public.perfis, public.testes_catalogo, public.participantes,
              public.avaliacoes, public.resultados_testes, public.ia_rascunhos FROM authenticated;

GRANT SELECT ON public.perfis, public.testes_catalogo TO authenticated;
GRANT SELECT, INSERT ON public.participantes TO authenticated;
GRANT UPDATE (idade, peso_kg, altura_m, excluido_em) ON public.participantes TO authenticated;
GRANT SELECT, INSERT ON public.avaliacoes TO authenticated;
GRANT UPDATE (flag_professor, flag_motivo, excluido_em) ON public.avaliacoes TO authenticated;
-- Resultados: sem DELETE físico (exclusão é lógica).
GRANT SELECT, INSERT ON public.resultados_testes TO authenticated;
GRANT UPDATE (lado, resultado, valor_medido, dor_0_10, observacoes, excluido_em) ON public.resultados_testes TO authenticated;
GRANT SELECT, INSERT ON public.ia_rascunhos TO authenticated;
GRANT UPDATE (texto, revisado_por, aprovado) ON public.ia_rascunhos TO authenticated;
-- Catálogo: o professor edita pelo painel do Supabase/SQL (service_role); o app só lê.

-- perfis (papel só muda por SQL administrativo)
DROP POLICY IF EXISTS perfis_leitura ON public.perfis;
CREATE POLICY perfis_leitura ON public.perfis FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()) OR public.eh_professor());

-- catálogo
DROP POLICY IF EXISTS catalogo_leitura ON public.testes_catalogo;
CREATE POLICY catalogo_leitura ON public.testes_catalogo FOR SELECT TO authenticated USING (true);

-- participantes
DROP POLICY IF EXISTS participantes_select ON public.participantes;
DROP POLICY IF EXISTS participantes_insert ON public.participantes;
DROP POLICY IF EXISTS participantes_update ON public.participantes;
CREATE POLICY participantes_select ON public.participantes FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()) OR public.eh_professor());
CREATE POLICY participantes_insert ON public.participantes FOR INSERT TO authenticated
  WITH CHECK (user_id = (SELECT auth.uid()) AND consentimento IS TRUE);
CREATE POLICY participantes_update ON public.participantes FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()) OR public.eh_professor())
  WITH CHECK (user_id = (SELECT auth.uid()) OR public.eh_professor());

-- avaliações
DROP POLICY IF EXISTS avaliacoes_select ON public.avaliacoes;
DROP POLICY IF EXISTS avaliacoes_insert ON public.avaliacoes;
DROP POLICY IF EXISTS avaliacoes_update ON public.avaliacoes;
CREATE POLICY avaliacoes_select ON public.avaliacoes FOR SELECT TO authenticated
  USING (avaliador_id = (SELECT auth.uid()) OR public.eh_professor());
CREATE POLICY avaliacoes_insert ON public.avaliacoes FOR INSERT TO authenticated
  WITH CHECK (avaliador_id = (SELECT auth.uid())
              AND EXISTS (SELECT 1 FROM public.participantes p WHERE p.id = participante_id));
CREATE POLICY avaliacoes_update ON public.avaliacoes FOR UPDATE TO authenticated
  USING (avaliador_id = (SELECT auth.uid()) OR public.eh_professor())
  WITH CHECK (avaliador_id = (SELECT auth.uid()) OR public.eh_professor());

-- resultados (acesso herdado da avaliação; a subconsulta já respeita o RLS de avaliacoes)
DROP POLICY IF EXISTS resultados_select ON public.resultados_testes;
DROP POLICY IF EXISTS resultados_insert ON public.resultados_testes;
DROP POLICY IF EXISTS resultados_update ON public.resultados_testes;
CREATE POLICY resultados_select ON public.resultados_testes FOR SELECT TO authenticated
  USING (EXISTS (SELECT 1 FROM public.avaliacoes a WHERE a.id = avaliacao_id));
CREATE POLICY resultados_insert ON public.resultados_testes FOR INSERT TO authenticated
  WITH CHECK (EXISTS (SELECT 1 FROM public.avaliacoes a
                       WHERE a.id = avaliacao_id AND a.avaliador_id = (SELECT auth.uid())));
CREATE POLICY resultados_update ON public.resultados_testes FOR UPDATE TO authenticated
  USING (EXISTS (SELECT 1 FROM public.avaliacoes a
                  WHERE a.id = avaliacao_id AND a.avaliador_id = (SELECT auth.uid())))
  WITH CHECK (EXISTS (SELECT 1 FROM public.avaliacoes a
                       WHERE a.id = avaliacao_id AND a.avaliador_id = (SELECT auth.uid())));

-- rascunhos da IA: aluno salva rascunho (não aprovado); só professor aprova
DROP POLICY IF EXISTS rascunhos_select ON public.ia_rascunhos;
DROP POLICY IF EXISTS rascunhos_insert ON public.ia_rascunhos;
DROP POLICY IF EXISTS rascunhos_update ON public.ia_rascunhos;
CREATE POLICY rascunhos_select ON public.ia_rascunhos FOR SELECT TO authenticated
  USING (EXISTS (SELECT 1 FROM public.avaliacoes a WHERE a.id = avaliacao_id));
CREATE POLICY rascunhos_insert ON public.ia_rascunhos FOR INSERT TO authenticated
  WITH CHECK (EXISTS (SELECT 1 FROM public.avaliacoes a WHERE a.id = avaliacao_id)
              AND ((aprovado IS FALSE AND revisado_por IS NULL)
                   OR (public.eh_professor() AND revisado_por = (SELECT auth.uid()))));
CREATE POLICY rascunhos_update ON public.ia_rascunhos FOR UPDATE TO authenticated
  USING (public.eh_professor())
  WITH CHECK (public.eh_professor() AND (aprovado IS FALSE OR revisado_por = (SELECT auth.uid())));
