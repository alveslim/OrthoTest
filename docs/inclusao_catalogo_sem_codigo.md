# Procedimento: Inclusão Dinâmica de Teste no Catálogo sem Alterar Código (ORT-45)

## 1. Arquitetura Data-Driven
O aplicativo Flet e o motor de KPIs consomem a tabela `testes_catalogo` dinamicamente via endpoint `GET /api/v1/catalogo`. Nenhuma região ou nome de teste está fixo (*hardcoded*) nos componentes visuais de coleta.

## 2. Passo a Passo para Cadastrar Novo Teste pelo Banco
Para adicionar um novo teste ortopédico (ex: *Teste de Phalen* na região *Punho*), execute o seguinte comando no **SQL Editor** do Supabase (ou insira via *Table Editor*):

```sql
INSERT INTO public.testes_catalogo (nome, regiao, descricao, ativo)
VALUES (
    'Teste de Phalen',
    'Punho',
    'Flexão máxima dos punhos por 60 segundos para avaliar compressão do nervo mediano.',
    true
);