-- Migration 002: Create Support Sessions Table
-- Data: 2025-10-13
-- Descrição: Tabela para armazenar o progresso do formulário de suporte
--            Resolve o problema de perda de dados ao reiniciar o bot

CREATE TABLE IF NOT EXISTS support_sessions (
    -- Identificação
    user_id INTEGER PRIMARY KEY,        -- ID do Telegram (único por usuário)

    -- Estado do formulário (JSON)
    state_json TEXT NOT NULL,           -- Estado serializado do formulário {step, data, ...}

    -- Controle temporal
    created_at TEXT NOT NULL,           -- Quando iniciou o formulário
    updated_at TEXT NOT NULL,           -- Última atualização

    -- Metadados
    current_step TEXT NOT NULL,         -- Passo atual: 'categoria', 'descricao', 'severidade', etc.

    -- Dados estruturados (para queries rápidas)
    categoria TEXT,                     -- Categoria selecionada (se já tiver)
    severidade TEXT,                    -- Severidade selecionada (se já tiver)

    -- Controle de expiração
    expires_at TEXT                     -- Quando a sessão expira (24h após última atualização)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_support_sessions_updated
    ON support_sessions(updated_at);

CREATE INDEX IF NOT EXISTS idx_support_sessions_expires
    ON support_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_support_sessions_step
    ON support_sessions(current_step);

-- Comentários sobre a estrutura:
--
-- user_id: PRIMARY KEY garante que cada usuário só tem uma sessão ativa por vez
-- state_json: Armazena TODO o estado do formulário em formato JSON flexível
-- current_step: Facilita debugging e queries sobre em qual etapa os usuários estão
-- categoria/severidade: Cópias desnormalizadas para queries rápidas (opcional)
-- expires_at: Permite limpeza automática de sessões antigas (24h)
--
-- Exemplo de state_json:
-- {
--   "step": "descricao",
--   "data": {
--     "categoria": "conectividade",
--     "descricao": "Ping alto em jogos",
--     "severidade": "alta"
--   },
--   "images": [],
--   "started_at": "2025-10-13T10:30:00"
-- }
