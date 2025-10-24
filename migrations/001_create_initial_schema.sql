-- Migration 001: Cria o esquema inicial completo do banco de dados
-- Este arquivo consolida todas as definições de tabelas e índices
-- que estavam espalhadas pelos repositórios Python.

PRAGMA foreign_keys = ON;

-- Tabela: users
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    telegram_user_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    cpf TEXT UNIQUE,
    client_name TEXT,
    service_name TEXT,
    service_status TEXT,
    status TEXT NOT NULL,
    last_verification TEXT,
    is_banned BOOLEAN DEFAULT FALSE,
    ban_reason TEXT,
    roles TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_activity_at TEXT,
    metadata TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_cpf ON users(cpf);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

-- Tabela: group_invites
CREATE TABLE IF NOT EXISTS group_invites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    cpf TEXT NOT NULL,
    invite_link TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TEXT,
    client_name TEXT,
    plan_name TEXT,
    UNIQUE(invite_link)
);
CREATE INDEX IF NOT EXISTS idx_group_invites_user_id ON group_invites(user_id);
CREATE INDEX IF NOT EXISTS idx_group_invites_cpf ON group_invites(cpf);
CREATE INDEX IF NOT EXISTS idx_group_invites_expires_at ON group_invites(expires_at);

-- Tabela: hubsoft_integrations
CREATE TABLE IF NOT EXISTS hubsoft_integrations (
    id TEXT PRIMARY KEY,
    integration_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    metadata TEXT,
    max_retries INTEGER NOT NULL,
    timeout_seconds INTEGER NOT NULL,
    scheduled_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    hubsoft_response TEXT,
    error_details TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hubsoft_integration_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    integration_id TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    response_data TEXT,
    duration_ms INTEGER,
    FOREIGN KEY (integration_id) REFERENCES hubsoft_integrations(id)
);
CREATE INDEX IF NOT EXISTS idx_hubsoft_integrations_type ON hubsoft_integrations(integration_type);
CREATE INDEX IF NOT EXISTS idx_hubsoft_integrations_status ON hubsoft_integrations(status);
CREATE INDEX IF NOT EXISTS idx_hubsoft_integrations_priority ON hubsoft_integrations(priority);
CREATE INDEX IF NOT EXISTS idx_hubsoft_integrations_scheduled_at ON hubsoft_integrations(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_hubsoft_integration_attempts_integration_id ON hubsoft_integration_attempts(integration_id);

-- Tabela: administrators
CREATE TABLE IF NOT EXISTS administrators (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    status TEXT DEFAULT 'administrator',
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_administrators_active ON administrators(is_active);

-- Tabela: cpf_verifications
CREATE TABLE IF NOT EXISTS cpf_verifications (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    user_mention TEXT,
    cpf_hash TEXT NOT NULL,
    verification_type TEXT NOT NULL,
    status TEXT NOT NULL,
    max_attempts INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    completed_at TEXT,
    verification_data TEXT,
    metadata TEXT,
    client_data TEXT
);
CREATE TABLE IF NOT EXISTS cpf_verification_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verification_id TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    response_data TEXT,
    error_message TEXT,
    duration_ms INTEGER,
    cpf_provided_hash TEXT,
    FOREIGN KEY (verification_id) REFERENCES cpf_verifications(id)
);
CREATE INDEX IF NOT EXISTS idx_cpf_verifications_user_id ON cpf_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_cpf_verifications_status ON cpf_verifications(status);
CREATE INDEX IF NOT EXISTS idx_cpf_verifications_cpf_hash ON cpf_verifications(cpf_hash);
CREATE INDEX IF NOT EXISTS idx_cpf_verification_attempts_verification_id ON cpf_verification_attempts(verification_id);