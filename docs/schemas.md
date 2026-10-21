# Schemas Pydantic

Os modelos em `backend/schemas.py` validam dados usados pelo backend.

| Modelo | Uso |
| --- | --- |
| `ParticipanteEntrada` | Dados para criar participante; exige data quando há consentimento. |
| `AvaliacaoEntrada` | Entrada para criar avaliação; recebe o ID do participante. |
| `ResultadoTeste` | Resultado, lado, dor de 0 a 10 e campos opcionais do teste. |
| `TesteCatalogo` | Item do catálogo lido pelo backend; referência pode estar ausente. |
| `RascunhoIA` | Rascunho lido pelo backend; aprovação exige revisor registrado. |
| `Perfil` | Perfil lido pelo backend; papel limitado a aluno ou professor. |

`ParticipanteEntrada`, `AvaliacaoEntrada` e `ResultadoTeste` rejeitam campos desconhecidos. O cliente não define o status calculado da avaliação. Validar o valor de um papel ou de uma aprovação não substitui a verificação das permissões do usuário.

## Identificadores e dados fictícios

O gerador de dados fictícios usa IDs de avaliação como `A-001`. Atualmente, `ResultadoTeste.avaliacao_id` aceita texto, enquanto `AvaliacaoEntrada.participante_id` e os IDs de `RascunhoIA` são UUIDs.

Antes de integrar esses modelos aos endpoints da ORT-13, a equipe precisa definir os tipos de ID da API e como os IDs da amostra fictícia serão convertidos quando necessário. Os dados fictícios servem para desenvolvimento; não representam registros já persistidos no Supabase.