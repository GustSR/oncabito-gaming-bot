-- Migration 004: Cria tabela duplicate_conflicts
-- Aplicada em: 2025-10-11
-- Descrição: Adiciona uma tabela para rastrear e gerenciar conflitos de CPF duplicado.
-- Quando o checkup diário detecta um CPF associado a múltiplas contas, cria um registro
-- aqui e notifica o usuário para escolher qual conta manter. Se não houver resposta no
-- prazo (expires_at), todas as contas são removidas automaticamente.

CREATE TABLE IF NOT EXISTS duplicate_conflicts (
    id TEXT PRIMARY KEY,
    cpf_hash TEXT NOT NULL,
    user_ids TEXT NOT NULL,  -- JSON array: [123, 456, 789]
    notified_user_id INTEGER NOT NULL,  -- ID do usuário que recebeu a notificação (mais recente)
    status TEXT NOT NULL,  -- PENDING, RESOLVED, EXPIRED_REMOVED
    conflict_data TEXT,  -- JSON com dados adicionais (usernames, first_names, etc)
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,  -- Prazo para resolução (geralmente 24h ou 48h)
    resolved_at TEXT,  -- Quando o conflito foi resolvido
    resolved_by INTEGER,  -- User ID que resolveu (pode ser o próprio ou admin)
    resolution_choice INTEGER,  -- User ID que foi escolhido para manter o CPF
    resolution_action TEXT  -- Ação tomada: USER_CHOICE, TIMEOUT_REMOVAL, ADMIN_INTERVENTION
);

-- Índices para otimizar buscas comuns
CREATE INDEX IF NOT EXISTS idx_duplicate_conflicts_status
    ON duplicate_conflicts(status);

CREATE INDEX IF NOT EXISTS idx_duplicate_conflicts_expires_at
    ON duplicate_conflicts(expires_at);

CREATE INDEX IF NOT EXISTS idx_duplicate_conflicts_cpf_hash
    ON duplicate_conflicts(cpf_hash);

CREATE INDEX IF NOT EXISTS idx_duplicate_conflicts_notified_user
    ON duplicate_conflicts(notified_user_id);

-- Índice composto para buscar conflitos pendentes que expiraram
CREATE INDEX IF NOT EXISTS idx_duplicate_conflicts_status_expires
    ON duplicate_conflicts(status, expires_at);
