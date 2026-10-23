# Contrato da API - OrthoTest

Este documento descreve os endpoints da API REST do OrthoTest (FastAPI). 
Todas as requisições requerem autenticação via JWT gerado pelo Supabase.

## 1. Autenticação e Autorização
O controlo de acessos é gerido através de um Bearer Token no cabeçalho das requisições.
- **Header Obrigatório:** `Authorization: Bearer <TOKEN_SUPABASE>`
- **Papéis (Roles):** A claim `app_metadata.role` define se o utilizador é `aluno` ou `professor`. A validação é feita via middlewares (Dependências FastAPI).

---

## 2. Catálogo de Testes

### `GET /api/v1/catalogo/testes`
Lista todos os testes ortopédicos disponíveis no sistema.
- **Acesso:** Autenticado (Aluno e Professor).
- **Resposta Sucesso (200 OK):**
  ```json
  [
    {
      "id": 1,
      "nome": "Lachman",
      "regiao": "Joelho",
      "estrutura": "LCA",
      "definicao": "...",
      "objetivo": "...",
      "como_fazer": "...",
      "positivo_se": "..."
    }
  ]

### 3. Participantes (Pacientes)

### POST/api/v1/participantes
Cria um novo registro de participante.
**Acesso:** Autenticado
**Body Request:**
```json
{
  "codigo": "PAC-001",
  "idade": 25,
  "peso_kg": 70.5,
  "altura_m": 1.75,
  "consentimento": true,
  "data_consentimento": "2026-10-23T14:30:00Z"
}

```
Resposta Sucesso (201 Created): Retorna o objeto criado incluindo o id (UUID), user_id e criado_em

### GET /api/v1/participantes

Lista os participantes. O Row Level Security (RLS) garante que o aluno apenas vê os seus próprios participantes.

***Acesso:*** Autenticado.

## 4. Avaliações Clínicas
### POST /api/v1/avaliacoes

Inicia uma nova ficha de avaliação clínica.
**Acesso:** Autenticado.
Body Request:

```json
{
  "participante_id": "uuid-do-participante"
}
```
Resposta Sucesso (201 Created):
```json
{
  "id": "uuid-da-avaliacao",
  "participante_id": "uuid-do-participante",
  "avaliador_id": "uuid-do-aluno",
  "status": "pendente",
  "progresso_percentual": 0.0,
  "data_avaliacao": "2026-10-23T14:30:00Z",
  "flag_professor": false,
  "flag_motivo": null
}
```

### POST /api/v1/avaliacoes/{avaliacao_id}/sinalizar

Sinaliza uma avaliação para análise e revisão do professor (dúvida ou conclusão).

**Acesso:** Autenticado (dono da avaliação).

    Body Request:
```json
{
  "motivo": "Dificuldade em interpretar o estresse em varo, solicito revisão."
}
```
Resposta Sucesso (200 OK):
```json
{
  "mensagem": "Avaliação sinalizada com sucesso para o professor."
}
```