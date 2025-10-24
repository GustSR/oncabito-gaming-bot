-- Migration 003: Adiciona a coluna expires_at na tabela users
-- Aplicada em: 2025-10-07
-- Descrição: Adiciona uma coluna para rastrear a expiração de usuários com status 'pending_verification',
-- permitindo que uma tarefa de limpeza remova registros órfãos.

ALTER TABLE users ADD COLUMN expires_at TEXT;
