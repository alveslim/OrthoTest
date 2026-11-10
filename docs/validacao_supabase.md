# Validação do Supabase antes do uso

Esta validação precisa ser executada no projeto Supabase correto, com dados fictícios e contas de teste. Não utilize participantes reais para testar isolamento.

## Preparação

1. Confirme o identificador do projeto e faça backup caso já existam registros.
2. Aplique a migration `20261109170000_finalizacao_integridade_rls_storage.sql`.
3. Execute `database/seed_catalogo.sql` e confirme que há 19 testes ativos.
4. Crie três contas no Auth: `aluno_a`, `aluno_b` e `professor`. Defina `app_metadata.role = professor` somente na conta professor.
5. Faça login na aplicação com `MODO_OFFLINE=false`.

## Casos de teste

| Caso | Ação | Resultado esperado |
|---|---|---|
| Autenticação válida | Entrar com usuário ativo | Login concluído |
| Token inválido/expirado | Enviar sessão inválida | API retorna 401 |
| Isolamento de participantes | Criar P-A com aluno A e P-B com aluno B | A não lista P-B; B não lista P-A |
| Isolamento de avaliações | A abre avaliação e B tenta consultar o ID de A | B recebe 404/sem acesso |
| Isolamento de resultados | B tenta listar ou gravar resultado na avaliação de A | Operação recusada pelo RLS/API |
| Upsert de resultado | Salvar duas vezes o mesmo teste e lado | Um registro atualizado; sem duplicidade |
| Lados diferentes | Registrar lado Direito e depois Esquerdo | Registros distintos permitidos |
| Validação da dor | Enviar -1 ou 11 | API rejeita com 422 / banco rejeita |
| Exclusão de resultado | Excluir resultado do teste | Resultado removido e progresso recalculado |
| Professor | Consultar avaliação de A e B | Professor consegue revisar ambas |
| Aprovação de resumo | Aluno tenta aprovar | 403; botão fica desabilitado |
| CSV | Exportar relatório | Arquivo no bucket privado em pasta do usuário |
| Catálogo | Consultar catálogo | 19 testes ativos; Gaveta Anterior não aparece |

## Diagnóstico SQL

Execute `database/validacao_supabase.sql` no SQL Editor. As consultas são somente leitura e verificam catálogo, duplicidades, integridade referencial, limites de campos, RLS, políticas e bucket de relatórios.

## Limitações

Os testes unitários simulados em `tests/test_seguranca_rls.py` não comprovam o RLS real. Só marque a validação de segurança como concluída depois de testar com tokens de duas contas distintas e uma conta professor no projeto Supabase efetivo.
