-- Migration: Add expired sessions tracking
-- Purpose: Track recently expired sessions to provide user feedback
-- Related Issue: Inconsistência #5 - Sessão de Suporte Expirada mas Usuário Continua Preenchendo

-- Create table to track recently expired sessions
CREATE TABLE IF NOT EXISTS expired_support_sessions (
    user_id INTEGER PRIMARY KEY,           -- ID do Telegram do usuário
    expired_at TEXT NOT NULL,              -- Quando a sessão expirou
    session_data TEXT,                     -- Snapshot do estado da sessão (opcional, para debug)
    notified BOOLEAN DEFAULT 0             -- Se o usuário já foi notificado sobre a expiração
);

-- Index for fast cleanup of old expired sessions (> 1 hour)
CREATE INDEX IF NOT EXISTS idx_expired_support_sessions_expired_at
ON expired_support_sessions(expired_at);

-- Note: Expired sessions older than 1 hour can be safely deleted
-- during the periodic cleanup job
