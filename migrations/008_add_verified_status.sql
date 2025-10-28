-- Migration 008: Adiciona novo status 'verified' para usuários
--
-- Este status representa usuários que validaram seu CPF mas ainda não entraram no grupo.
-- Fluxo: pending_verification → verified (após CPF) → active (após entrar no grupo)
--
-- Executado em: [data será preenchida automaticamente]

PRAGMA foreign_keys = ON;

-- Não há necessidade de alterar a tabela, pois o campo 'status' já é TEXT
-- O SQLite permite qualquer valor TEXT na coluna 'status'
-- A constraint de valores válidos é feita na camada de aplicação (UserStatus enum)

-- Documentação do novo status:
-- 'pending_verification': Usuário criado mas ainda não verificou CPF
-- 'verified': CPF verificado, aguardando entrada no grupo  [NOVO]
-- 'active': Entrou no grupo e está ativo
-- 'inactive': Saiu do grupo ou foi removido
-- 'suspended': Temporariamente suspenso

-- Nenhuma alteração de schema necessária.
-- Esta migration serve apenas como documentação e versionamento.
