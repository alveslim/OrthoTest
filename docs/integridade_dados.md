# Estratégia de Integridade de Dados e Constraints (ORT-37)

Para garantir a consistência das informações clínicas da aplicação OrthoTest, foram adotadas as seguintes camadas de proteção:

## 1. Validação de Aplicação (Backend Python/Pydantic)
- **Escala de Dor Restrita:** A variável `dor_0_10` foi bloqueada com *constraints* `ge=0` e `le=10`. Qualquer requisição fora deste limite é abortada (Status 422 Unprocessable Entity), impedindo gravações parciais no banco.
- **Relacionamento Obrigatório:** A ausência de `avaliacao_id` gera erro de validação imediato, prevenindo resultados "órfãos".

## 2. Restrições do Banco de Dados (Supabase SQL / Constraints)
Para além da validação em código, o banco de dados foi configurado com:
- **Foreign Keys (Chaves Estrangeiras):** O campo `avaliacao_id` na tabela `resultados` possui uma constraint `REFERENCES avaliacoes(id) ON DELETE CASCADE`.
- **Unique Constraints (Restrição de Unicidade):** Criada uma chave composta `UNIQUE(avaliacao_id, teste_id, lado)`. Isto impede matematicamente que o banco aceite inserções duplicadas, mesmo que o frontend dispare dois requests simultâneos por falha de rede.