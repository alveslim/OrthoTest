# Segurança e Row Level Security (RLS)

## Princípios de implementação

- O backend valida access tokens usando o endpoint oficial do Supabase Auth (`/auth/v1/user`).
- As consultas PostgREST usam a chave pública `SUPABASE_ANON_KEY` e o access token do usuário. Não usam `service_role`.
- `participantes.user_id` identifica quem criou o participante.
- `avaliacoes.avaliador_id` identifica quem abriu a avaliação.
- `resultados_testes` e `ia_rascunhos` são autorizados por meio da avaliação relacionada.
- O papel de professor é obtido de `app_metadata.role = professor`; não se confia em um papel enviado pelo cliente.
- A bucket `relatorios` é privada e guarda cada CSV em uma pasta com o UUID do usuário.

## Políticas

A migration `supabase/migrations/20261109170000_finalizacao_integridade_rls_storage.sql`:
- ativa RLS em perfis, participantes, catálogo, avaliações, resultados e rascunhos;
- permite que alunos leiam e alterem seus próprios registros;
- permite revisão por professores;
- permite leitura autenticada do catálogo ativo;
- impede que a aprovação do resumo seja feita por aluno;
- aplica isolamento de arquivos no Storage.

## Limites dos testes atuais

`tests/test_seguranca_rls.py` é um simulador unitário da regra de autorização. Ele não prova que o RLS do Supabase remoto está ativo. A validação real exige duas contas de aluno distintas e uma conta professor, usando os access tokens reais e dados fictícios.

Siga `docs/validacao_supabase.md` antes de usar o sistema com participantes. Nunca envie access tokens, chaves ou dados identificáveis para issues ou logs públicos.
