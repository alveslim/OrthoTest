# Estratégia de Row Level Security (RLS) - ORT-38

Para garantir o isolamento estrito de dados entre alunos e atestar que a segurança opera ao nível do banco de dados (não apenas na interface), as seguintes políticas SQL (Supabase RLS) foram desenhadas e homologadas por testes unitários:

## Políticas para a Tabela `avaliacoes` (e dependentes)

**1. Leitura de Dados (SELECT)**
Garante que um aluno nunca consegue descarregar fichas clínicas de colegas.
```sql
CREATE POLICY "Isolamento de Leitura (Alunos e Professores)"
ON avaliacoes FOR SELECT
USING (
  auth.uid() = avaliador_id 
  OR 
  (auth.jwt() ->> 'role' = 'professor')
);