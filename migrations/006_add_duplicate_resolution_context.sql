-- Migration: Add duplicate resolution context to cpf_verifications
-- Purpose: Persist duplicate resolution context to survive bot restarts
-- Related Issue: Inconsistência #2 - Contexto user_data Perdido em Reinicialização

-- Add column to store duplicate resolution context as JSON
ALTER TABLE cpf_verifications
ADD COLUMN duplicate_resolution_context TEXT DEFAULT NULL;

-- Add index for faster lookups of pending resolutions
CREATE INDEX IF NOT EXISTS idx_cpf_verifications_duplicate_context
ON cpf_verifications(duplicate_resolution_context)
WHERE duplicate_resolution_context IS NOT NULL;
