# 🔄 Sistema de Migrations - OnCabito Bot

## 📋 **O que são Migrations?**

Migrations são scripts que gerenciam mudanças na estrutura do banco de dados de forma controlada e versionada. Elas garantem que:

- ✅ **Dados não sejam perdidos** durante atualizações
- ✅ **Schema seja atualizado** automaticamente
- ✅ **Histórico de mudanças** seja mantido
- ✅ **Rollback seja possível** se necessário

## 🛠️ **Como Funciona**

### **1. Estrutura de Arquivos:**
```
migrations/
├── migration_engine.py       # Engine que executa as migrations
├── 001_create_initial_schema.sql  # Migration inicial
├── 002_add_missing_columns.sql    # Correções de estrutura
└── README.md                # Este arquivo
```

### **2. Convenção de Nomenclatura:**
- **Formato**: `XXX_description.sql`
- **XXX**: Número sequencial (001, 002, 003...)
- **description**: Descrição breve da mudança

### **3. Execução Automática:**
- **Na inicialização**: Bot executa migrations pendentes automaticamente
- **Durante deploy**: Script de deploy executa migrations antes de subir nova versão
- **Manual**: Pode ser executado manualmente quando necessário

## 🚀 **Comandos Disponíveis**

### **Execução Manual:**
```bash
# Via container (recomendado)
docker exec oncabito-bot python3 /app/migrations/migration_engine.py /app/data/database/sentinela.db

# Localmente (se tiver permissões)
python3 migrations/migration_engine.py data/database/sentinela.db
```

### **Verificar Status:**
```bash
# Mostra quais migrations foram aplicadas
docker exec oncabito-bot python3 -c "
from migrations.migration_engine import MigrationEngine
engine = MigrationEngine('/app/data/database/sentinela.db')
status = engine.get_migration_status()
print(f'Aplicadas: {status[\"applied_count\"]}')
print(f'Pendentes: {status[\"pending_count\"]}')
"
```

## 📝 **Criando Nova Migration**

### **1. Criar Arquivo:**
```bash
# Próximo número sequencial
touch migrations/003_add_new_feature.sql
```

### **2. Estrutura Recomendada:**
```sql
-- Migration 003: Adiciona funcionalidade X
-- Aplicada em: 2025-09-26
-- Descrição: Detalhada do que a migration faz

-- Criar nova tabela
CREATE TABLE IF NOT EXISTS nova_tabela (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL
);

-- Adicionar coluna (cuidado: SQLite não suporta IF NOT EXISTS)
ALTER TABLE users ADD COLUMN nova_coluna TEXT;

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_nova_tabela_nome ON nova_tabela(nome);

-- Atualizar dados existentes se necessário
UPDATE users SET nova_coluna = 'valor_padrao' WHERE nova_coluna IS NULL;
```

### **3. Testar Migration:**
```bash
# Backup antes do teste
./scripts/db/backup_database.sh manual

# Executar migration
docker exec oncabito-bot python3 /app/migrations/migration_engine.py /app/data/database/sentinela.db

# Se der erro, restaurar backup
./scripts/restore_database.sh backups/manual/backup_file.db
```

## ⚠️ **Cuidados Importantes**

### **SQLite Limitações:**
- ❌ `ALTER TABLE IF NOT EXISTS` não existe
- ❌ `DROP COLUMN` não suportado
- ❌ Renomear colunas é complexo
- ✅ Usar apenas `ADD COLUMN` para novas colunas

### **Boas Práticas:**
1. **Sempre fazer backup** antes de aplicar migrations
2. **Testar localmente** antes de aplicar em produção
3. **Migrations devem ser idempotentes** (podem ser executadas múltiplas vezes)
4. **Nunca editar** migrations já aplicadas
5. **Usar transações** quando possível

### **Se Migration Falhar:**
```bash
# 1. Verificar logs
docker-compose logs oncabito-bot

# 2. Restaurar backup de segurança
./scripts/restore_database.sh backups/auto/auto_backup_YYYYMMDD_HHMMSS.db

# 3. Corrigir migration e tentar novamente
# (editar arquivo .sql)

# 4. Aplicar migration corrigida
docker exec oncabito-bot python3 /app/migrations/migration_engine.py /app/data/database/sentinela.db
```

## 🔧 **Integração com Deploy**

O sistema está integrado com os scripts de deploy:

### **Deploy Seguro:**
```bash
./scripts/deploy/deploy_safe.sh
```

### **Fluxo do Deploy Seguro:**
1. 💾 **Backup automático** do banco atual
2. 📥 **Git pull** do código novo
3. 🔄 **Executa migrations** pendentes
4. 🔨 **Build da imagem** Docker
5. 🆙 **Deploy da nova versão**
6. ✅ **Verifica funcionamento**

## 📊 **Tabela de Controle**

O sistema mantém uma tabela `schema_migrations` que registra:

```sql
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,      -- Número da migration
    filename TEXT NOT NULL,           -- Nome do arquivo
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Quando foi aplicada
    checksum TEXT                     -- Hash do conteúdo (verificação)
);
```

## 🆘 **Troubleshooting**

### **Erro: "attempt to write a readonly database"**
```bash
# Verificar permissões
ls -la data/database/
# Executar via container onde há permissões corretas
docker exec oncabito-bot python3 /app/migrations/migration_engine.py /app/data/database/sentinela.db
```

### **Erro: "duplicate column name"**
- ✅ **Normal** se coluna já existe
- ❌ **Problema** se migration deveria ser idempotente
- **Solução**: Corrigir migration para ser mais robusta

### **Migration "perdida"**
```bash
# Registrar migration manualmente se necessário
docker exec oncabito-bot python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/database/sentinela.db')
conn.execute('INSERT INTO schema_migrations (version, filename) VALUES (1, \"001_create_initial_schema.sql\")')
conn.commit()
"
```

---

**💡 Dica**: Use sempre o script `./scripts/deploy/deploy_safe.sh` para deploys em produção. Ele cuida de tudo automaticamente!