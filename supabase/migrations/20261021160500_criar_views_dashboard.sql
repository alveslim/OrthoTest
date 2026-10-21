-- 1. Adicionar as colunas necessárias para as tarefas ORT-10 e ORT-14
ALTER TABLE avaliacoes ADD COLUMN status VARCHAR(20) DEFAULT 'pendente';
ALTER TABLE avaliacoes ADD COLUMN progresso_percentual DECIMAL(5,2) DEFAULT 0.0;

-- 2. Criar a View 1 (agora com a coluna existente)
CREATE OR REPLACE VIEW vw_dashboard_status_avaliacoes AS
SELECT 
  status, 
  COUNT(id) AS total
FROM avaliacoes
GROUP BY status;

-- View 2: Contagem de pacientes por professor
CREATE OR REPLACE VIEW vw_dashboard_pacientes_por_professor AS
SELECT 
  user_id, 
  COUNT(id) AS total_pacientes
FROM participantes
GROUP BY user_id;

-- View 3: Testes ortopédicos mais aplicados
CREATE OR REPLACE VIEW vw_dashboard_testes_comuns AS
SELECT 
  t.nome, 
  t.regiao, 
  COUNT(r.id) AS total_aplicacoes
FROM resultados_testes r
JOIN testes_catalogo t ON r.teste_id = t.id
GROUP BY t.nome, t.regiao
ORDER BY total_aplicacoes DESC;