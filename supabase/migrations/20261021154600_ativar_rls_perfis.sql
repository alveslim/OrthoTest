-- 1. Adicionar a coluna user_id nas tabelas relacionando com auth.users
ALTER TABLE participantes ADD COLUMN user_id UUID REFERENCES auth.users(id) DEFAULT auth.uid();
ALTER TABLE avaliacoes ADD COLUMN user_id UUID REFERENCES auth.users(id) DEFAULT auth.uid();

-- 2. Ativar o Row Level Security (RLS)
ALTER TABLE participantes ENABLE ROW LEVEL SECURITY;
ALTER TABLE avaliacoes ENABLE ROW LEVEL SECURITY;

-- 3. Política para Participantes: Aluno acessa os seus registros; Professor acessa todos
CREATE POLICY "Leitura de participantes" 
ON participantes
FOR SELECT 
USING (
  auth.uid() = user_id 
  OR auth.jwt() -> 'app_metadata' ->> 'role' = 'professor'
);

-- 4. Política para Avaliações: Aluno acessa as suas; Professor acessa todas
CREATE POLICY "Leitura de avaliacoes" 
ON avaliacoes
FOR SELECT 
USING (
  auth.uid() = user_id 
  OR auth.jwt() -> 'app_metadata' ->> 'role' = 'professor'
);