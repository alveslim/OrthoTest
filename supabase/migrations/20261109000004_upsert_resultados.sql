-- Correção: a API grava resultados com UPSERT (INSERT ... ON CONFLICT DO UPDATE). O PostgREST
-- inclui TODAS as colunas do corpo no UPDATE, então o papel authenticated precisa de UPDATE também
-- em avaliacao_id e teste_id. A política resultados_update (USING + WITH CHECK) continua exigindo que
-- a avaliação pertença ao usuário, então ninguém move um resultado para a avaliação de outro.
GRANT UPDATE (avaliacao_id, teste_id) ON public.resultados_testes TO authenticated;
