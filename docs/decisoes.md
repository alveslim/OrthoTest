# Decisões do grupo

## Banco de dados (ORT-06)
- Datas em `TIMESTAMPTZ`.
- O status Completo/Incompleto é calculado a partir dos resultados; não é coluna.
- `ON DELETE RESTRICT`: nada some em cascata. A exclusão será lógica (ORT-07).
- RLS ligado em todas as tabelas, sem políticas até o ORT-09.

## Testes em duas posições (Estresse em Valgo e Estresse em Varo)
**Problema:** as fichas dizem que esses testes podem ser feitos em duas posições do joelho
(extensão e 20° a 30° de flexão), mas o banco guarda **um resultado por teste e por lado**
(`UNIQUE (avaliacao_id, teste_id, lado)`).

**Decisão (proposta, aguardando o grupo):** registrar um único resultado. O resultado é
**Positivo se qualquer uma das posições for positiva**. A posição em que o achado apareceu
é anotada em `observacoes` (ex.: "positivo a 30° de flexão; negativo em extensão").

**Por quê:** mantém o modelo simples e não exige nova tabela.
**Custo:** a posição fica em texto livre, então não dá para filtrar ou contar por posição no painel.
**Alternativa descartada por ora:** uma coluna `posicao` na tabela de resultados.
Só vale se o grupo precisar analisar por posição.

## Catálogo (ORT-05/08)
- Os textos do catálogo são copiados das fichas de Sabrina e Vinícius (`database/seed_catalogo.sql`).
- `referencia` fica `NULL` até o ORT-02 trazer a fonte bibliográfica verificada.