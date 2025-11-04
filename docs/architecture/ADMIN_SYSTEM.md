# 👤 Sistema de Administradores

## 📋 Visão Geral

O OnCabo Gaming Bot possui um sistema automático de detecção e gerenciamento de administradores que:
- Sincroniza automaticamente administradores do Telegram
- Protege admins de verificações e remoções automáticas
- Mantém histórico de permissões no banco de dados
- Não requer configuração manual de IDs

---

## 🏗️ Arquitetura

### Tabela do Banco de Dados

```sql
CREATE TABLE IF NOT EXISTS administrators (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    status TEXT DEFAULT 'administrator',  -- administrator, owner, creator
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_administrators_active ON administrators(is_active);
```

### Repositório

**Interface**: `src/sentinela/domain/repositories/admin_repository.py`
**Implementação**: `src/sentinela/infrastructure/repositories/sqlite_admin_repository.py`

**Métodos Principais**:
```python
# Verificar se é admin
async def is_administrator(user_id: int) -> bool

# Buscar dados de um admin
async def get_administrator(user_id: int) -> Optional[dict]

# Listar todos os admins
async def list_administrators(active_only: bool = True) -> List[dict]

# Salvar/atualizar admin
async def save_administrator(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    status: str = "administrator",
    is_active: bool = True
) -> bool

# Desativar admin (não remove do banco)
async def deactivate_administrator(user_id: int) -> bool

# Sincronizar do Telegram
async def sync_from_telegram(admin_list: List[dict]) -> int
```

---

## ⏰ Sincronização Automática

### Como Funciona

A sincronização acontece na **Fase 1** do `daily_cpf_checkup.py`:

1. **Busca admins do Telegram**:
```python
admins = await bot.get_chat_administrators(group_id)
```

2. **Marca todos os atuais como inativos**:
```sql
UPDATE administrators SET is_active = 0
```

3. **Atualiza/Adiciona admins atuais**:
```python
for admin in admins:
    await admin_repo.save_administrator(
        user_id=admin.user.id,
        username=admin.user.username,
        first_name=admin.user.first_name,
        status=admin.status,  # creator, administrator, etc
        is_active=True
    )
```

### Frequência

- **Automática**: A cada 30 minutos (6:00-23:59) via cron
- **Manual**: Executando `daily_cpf_checkup.py`

```bash
# Manual no servidor
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/daily_cpf_checkup.py
```

---

## 🛡️ Proteções para Administradores

Os administradores são **automaticamente protegidos** nas seguintes situações:

### 1. Remoção por Falta de Contrato Ativo

**Local**: `scripts/tasks/daily_cpf_checkup.py:291-293`

```python
if await self.admin_repo.is_administrator(user_id):
    logger.info(f"⏭️ Pulando administrador: {user_id}")
    continue
```

### 2. Verificação de CPF Expirado

**Local**: `scripts/tasks/daily_cpf_checkup.py:353-355`

```python
if await self.admin_repo.is_administrator(user_id):
    logger.info(f"⏭️ Pulando verificação de CPF para o administrador {user.username}")
    continue
```

### 3. Verificação de Contrato HubSoft

**Local**: `scripts/tasks/daily_cpf_checkup.py:556-558`

```python
if await self.admin_repo.is_administrator(user_id):
    logger.info(f"⏭️ Pulando verificação de contrato para o administrador {user.username}")
    continue
```

### 4. Remoção por Não Aceitar Regras

**Local**: `src/sentinela/application/use_cases/welcome_management_use_case.py:256-258`

```python
if await self.admin_repository.is_administrator(member.telegram_id):
    logger.info(f"⏭️ Pulando verificação de regras para o administrador {member.username}")
    continue
```

---

## 🔍 Verificação de Permissões

### No Bot Handler

**Local**: `src/sentinela/presentation/handlers/telegram_bot_handler.py:1383`

```python
async def _is_admin(self, user_id: int) -> bool:
    """Verifica se usuário é administrador consultando o repositório."""
    return await self._admin_repo.is_administrator(user_id)
```

### No Sistema de Controle de Acesso

**Local**: `src/sentinela/core/access_control.py:57-59`

```python
# Verifica no banco de administradores
is_admin = asyncio.run(admin_repo.is_administrator(user_id))
if is_admin:
    return AccessLevel.ADMIN
```

---

## 📊 Monitoramento

### Ver Administradores no Banco

```bash
# Conectar ao banco
docker exec -it oncabo-gaming-bot sqlite3 /app/data/database/sentinela.db

# Listar admins ativos
SELECT user_id, username, first_name, status, detected_at, is_active
FROM administrators
WHERE is_active = 1;

# Ver histórico completo (incluindo inativos)
SELECT user_id, username, first_name, status, detected_at, last_updated, is_active
FROM administrators
ORDER BY last_updated DESC;
```

### Logs de Sincronização

```bash
# Ver logs do checkup (inclui sincronização de admins)
tail -f logs/checkup.log | grep -i "admin"

# Exemplo de output:
# 2025-11-04 18:30:00 - INFO - 👤 FASE 1: Sincronizando Administradores
# 2025-11-04 18:30:01 - INFO - Encontrados 3 administradores. Sincronizando...
# 2025-11-04 18:30:01 - INFO - ✅ Sincronização concluída. 3 administradores ativos.
```

---

## 🔧 Troubleshooting

### Admin não está sendo reconhecido

1. **Verificar se a sincronização rodou recentemente**:
```bash
tail -n 100 logs/checkup.log | grep "Sincronizando Administradores"
```

2. **Forçar sincronização manual**:
```bash
docker exec oncabo-gaming-bot python3 /app/scripts/tasks/daily_cpf_checkup.py
```

3. **Verificar no banco**:
```bash
docker exec oncabo-gaming-bot sqlite3 /app/data/database/sentinela.db \
  "SELECT * FROM administrators WHERE user_id = USER_ID_AQUI;"
```

### Admin foi removido do banco

Se um admin foi rebaixado no Telegram e depois promovido novamente, ele será re-adicionado na próxima sincronização (máximo 30 minutos de espera).

**Forçar re-sincronização imediata**:
```bash
./deployment/run_checkup.sh
```

### Permissões não estão funcionando

O sistema verifica permissões em **tempo real** consultando o banco. Se um admin foi recém-promovido:

1. Aguarde próxima sincronização (até 30 min)
2. OU force sincronização manual
3. Verifique se o `is_active = 1` no banco

---

## 🎯 Boas Práticas

### ✅ **DO**
- Confie na sincronização automática (roda a cada 30 min)
- Use `is_administrator()` para verificar permissões
- Verifique logs de checkup para debug
- Force sincronização manual se necessário urgentemente

### ❌ **DON'T**
- NÃO adicione IDs manualmente no banco
- NÃO modifique tabela `administrators` diretamente
- NÃO desabilite sincronização automática
- NÃO assuma que mudanças no Telegram refletem instantaneamente

---

## 📚 Referências

**Código Relacionado**:
- Repository Interface: `src/sentinela/domain/repositories/admin_repository.py`
- Repository Implementation: `src/sentinela/infrastructure/repositories/sqlite_admin_repository.py`
- Sincronização: `scripts/tasks/daily_cpf_checkup.py` (Fase 1)
- Proteções: Checkup + Welcome Use Case

**Documentação**:
- Checkup Diário: `scripts/README.md`
- Cron Jobs: `deployment/README.md`
- Arquitetura: `docs/architecture/OVERVIEW.md`
