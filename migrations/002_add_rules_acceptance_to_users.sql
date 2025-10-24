-- Migration 002: Adiciona colunas de aceitação de regras na tabela users
-- Descrição: Adiciona as colunas 'rules_accepted' e 'rules_accepted_at' para
-- centralizar a lógica de aceitação de regras na entidade principal do usuário.

ALTER TABLE users ADD COLUMN rules_accepted BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN rules_accepted_at TEXT;

-- Adiciona um índice para buscas futuras
CREATE INDEX IF NOT EXISTS idx_users_rules_accepted ON users(rules_accepted);
