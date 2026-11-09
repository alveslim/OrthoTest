# Contrato da API — OrthoTest

API em FastAPI. Todas as rotas abaixo exigem o cabeçalho:

```http
Authorization: Bearer <access_token_do_supabase>
```

A API valida o token em `/auth/v1/user` e usa a chave pública `SUPABASE_ANON_KEY` junto do access token do usuário nas chamadas ao PostgREST. As políticas RLS do banco são aplicadas em cada requisição. Não configure nem utilize `service_role` nesta aplicação.

Prefixo: `/api/v1`.

## Saúde

- `GET /health` — status da API (sem prefixo).
- `GET /api/v1/health` — status da API (prefixado).

## Catálogo

- `GET /catalogo/testes` — lista apenas testes ativos do catálogo.
- O catálogo contém 19 testes ativos; o registro legado de Gaveta Anterior é mantido inativo para preservar IDs históricos.

## Participantes

- `POST /participantes` — cria participante pertencente ao usuário autenticado.
- `GET /participantes` — lista participantes do usuário; papel de professor pode consultar o conjunto de registros autorizado por RLS.

Exemplo de corpo:

```json
{
  "codigo": "P-001",
  "idade": 25,
  "peso_kg": 70.5,
  "altura_m": 1.75,
  "consentimento": true,
  "data_consentimento": "2026-11-09T15:00:00-04:00"
}
```

Consentimento e data são obrigatórios. O sistema não recebe nome completo.

## Avaliações

- `POST /avaliacoes` — abre avaliação para participante do usuário.
- `GET /avaliacoes` — lista avaliações próprias; professor pode consultar para revisão.
- `POST /avaliacoes/{avaliacao_id}/sinalizar` — sinaliza para revisão.
- `GET /avaliacoes/{avaliacao_id}/resultados` — lista resultados da avaliação autorizada.
- `POST /avaliacoes/{avaliacao_id}/resultados` — insere ou atualiza resultado por avaliação, teste e lado.
- `DELETE /avaliacoes/{avaliacao_id}/resultados/{teste_id}` — remove todos os lados registrados para o teste naquela avaliação.

Exemplo de resultado:

```json
{
  "teste_id": 1,
  "lado": "Direito",
  "resultado": "Positivo",
  "dor_0_10": 4,
  "valor_medido": null,
  "observacoes": "Observação descritiva"
}
```

Valores de `lado`: `Direito`, `Esquerdo`, `Bilateral`.
Valores de `resultado`: `Positivo`, `Negativo`, `Não realizado`, `Inconclusivo`.
A dor, quando informada, deve ser um inteiro entre 0 e 10. O progresso é recalculado a partir dos testes ativos do catálogo.

## Dashboard e relatórios

- `GET /dashboard/kpis` — retorna contagens e indicadores agregados.
- `POST /dashboard/exportar/csv` — gera CSV agregado e salva no bucket privado `relatorios`, em pasta identificada pelo UUID do usuário.

A regra de privacidade usa participantes distintos por região. Regiões com menos de três pessoas não são exibidas individualmente; o grupo agregado também precisa ter pelo menos três participantes.

## Assistente de revisão

- `GET /avaliacoes/{avaliacao_id}/achados` — aplica regras clínicas locais documentadas.
- `POST /avaliacoes/{avaliacao_id}/resumo-ia` — gera resumo descritivo; LLM é opcional e há fallback determinístico.
- `POST /avaliacoes/{avaliacao_id}/aprovar-resumo` — registra aprovação, exclusivo para `app_metadata.role = professor`.

A IA não confirma diagnósticos nem recomenda tratamentos. Todo texto deve ser revisado por professor antes de ser tratado como resumo aprovado.

## Códigos de resposta

- `200/201`: operação concluída.
- `401`: sessão ausente, inválida ou expirada.
- `403`: usuário autenticado sem autorização para a ação.
- `404`: recurso não encontrado ou não pertence ao usuário.
- `422`: payload inválido.
- `503`: Supabase/API indisponível ou configuração ausente.

## Execução local

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
