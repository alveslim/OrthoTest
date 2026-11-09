-- Consultas de diagnóstico somente leitura para executar no SQL Editor do Supabase.
-- Não altera dados. Não retorna códigos de participantes nem resultados individuais.

-- 1) Contagem do catálogo ativo e legado.
SELECT ativo, COUNT(*) AS quantidade
FROM public.testes_catalogo
GROUP BY ativo
ORDER BY ativo DESC;

-- 2) Esperado: 19 testes ativos.
SELECT COUNT(*) AS testes_ativos
FROM public.testes_catalogo
WHERE ativo = TRUE;

-- 3) Esperado: zero linhas (não pode haver duplicidade por avaliação/teste/lado).
SELECT avaliacao_id, teste_id, lado, COUNT(*) AS duplicados
FROM public.resultados_testes
GROUP BY avaliacao_id, teste_id, lado
HAVING COUNT(*) > 1;

-- 4) Esperado: zero linhas (nenhum resultado órfão).
SELECT COUNT(*) AS resultados_sem_avaliacao
FROM public.resultados_testes r
LEFT JOIN public.avaliacoes a ON a.id = r.avaliacao_id
WHERE a.id IS NULL;

-- 5) Esperado: zero linhas (dor, lado e resultado dentro dos limites).
SELECT COUNT(*) AS resultados_fora_dos_limites
FROM public.resultados_testes
WHERE (dor_0_10 IS NOT NULL AND dor_0_10 NOT BETWEEN 0 AND 10)
   OR lado NOT IN ('Direito', 'Esquerdo', 'Bilateral')
   OR resultado NOT IN ('Positivo', 'Negativo', 'Não realizado', 'Inconclusivo');

-- 6) Esperado: relrowsecurity = true para todas as tabelas.
SELECT c.relname AS tabela, c.relrowsecurity AS rls_ativo
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
  AND c.relname IN (
    'perfis', 'participantes', 'testes_catalogo',
    'avaliacoes', 'resultados_testes', 'ia_rascunhos'
  )
ORDER BY c.relname;

-- 7) Inspeciona os nomes e escopos das políticas instaladas.
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'perfis', 'participantes', 'testes_catalogo',
    'avaliacoes', 'resultados_testes', 'ia_rascunhos'
  )
ORDER BY tablename, policyname;

-- 8) Esperado: bucket relatorios existe e não é público.
SELECT id, name, public
FROM storage.buckets
WHERE id = 'relatorios';
