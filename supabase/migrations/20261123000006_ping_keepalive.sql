-- Função pública e inofensiva (não lê nenhuma tabela): usada por um agendador do GitHub para manter o projeto
-- ativo (projetos gratuitos do Supabase pausam após ~7 dias sem atividade).
create or replace function public.ping()
returns integer
language sql
stable
security invoker
set search_path = ''
as $$ select 1 $$;

revoke all on function public.ping() from public;
grant execute on function public.ping() to anon, authenticated;
