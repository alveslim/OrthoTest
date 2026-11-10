-- OrtoCheck · views do dashboard (ORT-10) e Storage de relatórios (ORT-29).
-- Todas as views usam security_invoker: respeitam o RLS (aluno vê só o seu; professor vê tudo).
-- Grupos com menos de 3 participantes não aparecem nas views agregadas (regra n < 3).

-- Base: um registro por resultado ativo, sem nenhum identificador do participante além de um id opaco.
CREATE OR REPLACE VIEW public.vw_resultados_dashboard WITH (security_invoker = true) AS
SELECT r.id                AS resultado_id,
       r.avaliacao_id,
       a.participante_id,
       r.teste_id,
       t.regiao,
       t.nome              AS teste,
       r.lado,
       r.resultado,
       r.dor_0_10,
       p.idade,
       CASE WHEN p.idade < 18 THEN '< 18'
            WHEN p.idade < 25 THEN '18-24'
            WHEN p.idade < 35 THEN '25-34'
            WHEN p.idade < 45 THEN '35-44'
            WHEN p.idade < 60 THEN '45-59'
            ELSE '60+' END AS faixa_etaria,
       CASE WHEN p.peso_kg IS NULL OR p.altura_m IS NULL THEN NULL
            ELSE round((p.peso_kg / (p.altura_m * p.altura_m))::numeric, 1) END AS imc,
       a.status            AS status_avaliacao
  FROM public.resultados_testes r
  JOIN public.avaliacoes   a ON a.id = r.avaliacao_id   AND a.excluido_em IS NULL
  JOIN public.participantes p ON p.id = a.participante_id AND p.excluido_em IS NULL
  JOIN public.testes_catalogo t ON t.id = r.teste_id
 WHERE r.excluido_em IS NULL;

CREATE OR REPLACE VIEW public.vw_positivos_por_teste WITH (security_invoker = true) AS
SELECT regiao, teste,
       count(*) FILTER (WHERE resultado <> 'Não realizado')                      AS total_valido,
       count(*) FILTER (WHERE resultado = 'Positivo')                            AS positivos,
       round(100.0 * count(*) FILTER (WHERE resultado = 'Positivo')
             / NULLIF(count(*) FILTER (WHERE resultado <> 'Não realizado'), 0), 1) AS percentual_positivo,
       count(DISTINCT participante_id)                                            AS participantes
  FROM public.vw_resultados_dashboard
 GROUP BY regiao, teste
HAVING count(DISTINCT participante_id) >= 3;

CREATE OR REPLACE VIEW public.vw_positivos_por_regiao WITH (security_invoker = true) AS
SELECT regiao,
       count(*) FILTER (WHERE resultado <> 'Não realizado')                      AS total_valido,
       count(*) FILTER (WHERE resultado = 'Positivo')                            AS positivos,
       round(100.0 * count(*) FILTER (WHERE resultado = 'Positivo')
             / NULLIF(count(*) FILTER (WHERE resultado <> 'Não realizado'), 0), 1) AS percentual_positivo,
       count(DISTINCT participante_id)                                            AS participantes
  FROM public.vw_resultados_dashboard
 GROUP BY regiao
HAVING count(DISTINCT participante_id) >= 3;

CREATE OR REPLACE VIEW public.vw_participantes_faixa_etaria WITH (security_invoker = true) AS
SELECT CASE WHEN idade < 18 THEN '< 18' WHEN idade < 25 THEN '18-24' WHEN idade < 35 THEN '25-34'
            WHEN idade < 45 THEN '35-44' WHEN idade < 60 THEN '45-59' ELSE '60+' END AS faixa_etaria,
       count(*) AS participantes
  FROM public.participantes
 WHERE excluido_em IS NULL
 GROUP BY 1
HAVING count(*) >= 3;

REVOKE ALL ON public.vw_resultados_dashboard, public.vw_positivos_por_teste,
              public.vw_positivos_por_regiao, public.vw_participantes_faixa_etaria FROM anon, authenticated;
GRANT SELECT ON public.vw_resultados_dashboard, public.vw_positivos_por_teste,
                public.vw_positivos_por_regiao, public.vw_participantes_faixa_etaria TO authenticated;

-- Storage: bucket privado; cada usuário grava/lê só dentro da própria pasta (<user_id>/...). Professor lê tudo.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('relatorios', 'relatorios', false, 5242880, ARRAY['text/csv', 'application/pdf'])
ON CONFLICT (id) DO UPDATE SET public = false, file_size_limit = 5242880,
                               allowed_mime_types = ARRAY['text/csv', 'application/pdf'];

DROP POLICY IF EXISTS relatorios_insert ON storage.objects;
DROP POLICY IF EXISTS relatorios_select ON storage.objects;
CREATE POLICY relatorios_insert ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'relatorios' AND (storage.foldername(name))[1] = (SELECT auth.uid())::text);
CREATE POLICY relatorios_select ON storage.objects FOR SELECT TO authenticated
  USING (bucket_id = 'relatorios'
         AND ((storage.foldername(name))[1] = (SELECT auth.uid())::text OR public.eh_professor()));
