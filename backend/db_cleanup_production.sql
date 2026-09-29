-- Migration: cleanup fake processos + add 3 ferramentas
-- Date: 2026-08-18
-- Removed 13 fake processos
-- Added auto-laudo-pro, forensic, calculator ferramentas

DELETE FROM processo WHERE numero_cnj LIKE '%test%' OR numero_cnj LIKE '%fake%' OR empresa_id IS NULL;
INSERT INTO tools (name, title, description, url, icon, access_level, is_active, created_at, updated_at) 
VALUES 
  ('auto-laudo-pro', 'Laudo Automático', 'Geração de laudos via Qwen', '/api/v1/laudos/gerar', '📝', 'user', true, NOW(), NOW()),
  ('forensic', 'Análise Forense', 'Análise de mídia', '/api/v1/ferramentas/analisar-midia', '🔬', 'user', true, NOW(), NOW()),
  ('calculator', 'Calculadora', 'Cálculos periciais', '/api/v1/deslocamento', '🧮', 'user', true, NOW(), NOW())
ON CONFLICT (name) DO NOTHING;
