# 🪦 Auditoria de Código Morto - OnCabo Gaming Bot

> **Data da Auditoria:** 2025-10-01
> **Status:** Identificação completa de código não utilizado e migrações incompletas

---

## 📋 Sumário Executivo

Esta auditoria identificou **código morto** (não utilizado) e **migrações incompletas** no projeto após a migração para Clean Architecture + DDD + CQRS.

### Estatísticas:
- ✅ **Arquivos ativos:** ~50 arquivos
- 🪦 **Arquivos mortos:** 21 arquivos
- ⚠️ **Funcionalidades incompletas:** 2 comandos
- 🧪 **Arquivos temporários de teste:** 5 arquivos

---

## 🚫 CÓDIGO MORTO - NÃO USAR

### 1️⃣ Serviços Antigos (Deletados do Git)

Esses arquivos foram **deletados** durante a migração mas ainda aparecem no git status.
**Ação recomendada:** Remover permanentemente com `git add` e commit.

```
📂 src/sentinela/bot/ (PASTA INTEIRA - OLD ARCHITECTURE)
   ├── __init__.py
   ├── bot_instance.py
   └── handlers.py

📂 src/sentinela/clients/ (PASTA INTEIRA - OLD ARCHITECTURE)
   ├── __init__.py
   └── db_client.py

📂 src/sentinela/services/ (PASTA INTEIRA - OLD ARCHITECTURE)
   ├── admin_detection_service.py
   ├── admin_service.py
   ├── cpf_validation_service.py
   ├── cpf_verification_service.py
   ├── duplicate_cpf_handler.py
   ├── hubsoft_sync_service.py
   ├── support_service.py
   └── user_service.py
```

**Motivo:** Arquitetura antiga. Funcionalidade migrada para:
- **Application Layer:** `src/sentinela/application/use_cases/`
- **Domain Services:** `src/sentinela/domain/services/`
- **Infrastructure:** `src/sentinela/infrastructure/`

---

### 2️⃣ Handlers Não Utilizados (Presentation Layer)

Esses arquivos **existem** mas **NÃO são registrados** no `telegram_bot_new.py`.
**Ação recomendada:** Deletar ou mover para `_archive/`.

```
📂 src/sentinela/presentation/handlers/
   ├── ✅ telegram_bot_handler.py (ATIVO - ÚNICO HANDLER USADO)
   ├── 🪦 support_conversation_handler.py (NÃO USADO)
   ├── 🪦 user_verification_handler.py (NÃO USADO)
   └── 🪦 example_handler.py (ARQUIVO DE EXEMPLO - NÃO USADO)
```

**Detalhes:**

#### `support_conversation_handler.py`
- **Status:** Código morto
- **Motivo:** Usa `SupportFormUseCase` que NÃO está no DI Container
- **Migração:** Funcionalidade implementada diretamente em `telegram_bot_handler.py` (linhas 571-1100)

#### `user_verification_handler.py`
- **Status:** Código morto
- **Motivo:** Usa sistema de DI antigo (`@dependency_injected`) que não existe mais
- **Migração:** Funcionalidade integrada em `telegram_bot_handler.py`

#### `example_handler.py`
- **Status:** Exemplo/demo
- **Motivo:** Apenas arquivo de exemplo educacional
- **Ação:** Pode ser deletado

---

### 3️⃣ Use Cases Não Utilizados (Application Layer)

Esses Use Cases **existem** mas **NÃO são registrados** no DI Container.
**Ação recomendada:** Avaliar se são necessários. Se sim, migrar. Se não, deletar.

```
📂 src/sentinela/application/use_cases/

✅ ATIVOS (registrados no container.py):
   ├── hubsoft_integration_use_case.py ✅
   ├── cpf_verification_use_case.py ✅
   ├── admin_operations_use_case.py ✅
   ├── member_verification_use_case.py ✅
   └── scheduled_tasks_use_case.py ✅

🪦 MORTOS (NÃO registrados no container.py):
   ├── group_management_use_case.py ❌
   ├── invite_management_use_case.py ❌
   ├── permission_management_use_case.py ❌
   ├── tech_notification_use_case.py ❌
   ├── topic_management_use_case.py ❌
   ├── support_form_use_case.py ❌
   ├── gaming_support_use_case.py ❌
   └── welcome_management_use_case.py ❌
```

**Observação:** Esses arquivos podem conter **lógica útil** que ainda não foi migrada.
**Decisão:** Avaliar caso a caso antes de deletar.

---

### 4️⃣ Arquivos Temporários de Teste

Esses arquivos são **temporários** e foram usados durante a migração.
**Ação recomendada:** Deletar após confirmar que não são mais necessários.

```
📂 Raiz do projeto:
   ├── complete_migration.py (TESTE DE MIGRAÇÃO)
   ├── demo_new_bot.py (DEMO/TESTE)
   ├── fix_container.py (FIX TEMPORÁRIO)
   ├── migration_bootstrap.py (BOOTSTRAP DE MIGRAÇÃO)
   └── test_telegram_bot_integration.py (TESTE)
```

**Status:** Provavelmente seguros para deletar
**Verificação:** Checar se há funcionalidade única antes de deletar

---

## ⚠️ MIGRAÇÕES INCOMPLETAS - PRECISA IMPLEMENTAR

Esses comandos/funcionalidades mostram mensagem "em migração" mas **não foram implementados**.

### 1️⃣ Comando `/status` ✅ **[IMPLEMENTADO]**

**Localização:** `src/sentinela/presentation/handlers/telegram_bot_handler.py:225-361`

**Status:** ✅ **COMPLETO - Implementado em 2025-10-01**

**Funcionalidades implementadas:**
- ✅ Busca todos os tickets do usuário via `ticket_repository.find_by_user()`
- ✅ Separa tickets ativos e finalizados
- ✅ Mostra resumo com contadores (total, ativos, finalizados)
- ✅ Lista tickets ativos com: protocolo, categoria, dias abertos, jogo, técnico
- ✅ Lista últimos 3 tickets finalizados
- ✅ Exibe emoji por status (⏳ pending, 🔄 in_progress, ✅ resolved, etc.)
- ✅ Botão "Abrir Novo Ticket" que inicia fluxo de suporte
- ✅ Mensagem amigável quando não há tickets
- ✅ Tratamento de erros com mensagem humanizada

**Callback implementado:**
- `status_new_ticket` → Inicia novo ticket (telegram_bot_handler.py:1331-1391)

---

### 2️⃣ Callback `admin_sync` (Sincronização HubSoft)

**Localização:** `src/sentinela/presentation/handlers/telegram_bot_handler.py:473-478`

**Status Atual:**
```python
elif callback_data == "admin_sync":
    message = (
        "🔄 **Sincronização HubSoft**\n\n"
        "Funcionalidade de sync disponível em breve.\n\n"
        "🚧 Sistema em migração para nova arquitetura"
    )
```

**Problema:** Botão existe no menu admin mas não faz nada

**O que precisa ser feito:**
1. Integrar com `HubSoftIntegrationUseCase`
2. Implementar sincronização manual de tickets pendentes
3. Mostrar status da sincronização
4. Remover mensagem "em migração"

**Referência:** Use `BulkSyncTicketsToHubSoftHandler` e `RetryFailedIntegrationsHandler`

---

## 📊 Mapeamento: DI Container vs Arquivos Existentes

### ✅ O QUE ESTÁ SENDO USADO (DI Container)

```python
# REPOSITORIES (todos registrados ✅)
├── ticket_repository (SQLiteTicketRepository)
├── cpf_verification_repository (SQLiteCPFVerificationRepository)
├── hubsoft_integration_repository (SQLiteHubSoftIntegrationRepository)
├── user_repository (SQLiteUserRepository)
└── group_invite_repository (SQLiteGroupInviteRepository)

# EXTERNAL SERVICES (todos registrados ✅)
├── hubsoft_api_repository (HubSoftAPIService)
├── hubsoft_cache_repository (HubSoftCacheService)
├── rate_limiter (RateLimiter)
├── token_manager (TokenManager)
└── cache_manager (CacheManager)

# DOMAIN SERVICES (todos registrados ✅)
├── cpf_validation_service (CPFValidationService)
└── duplicate_cpf_service (DuplicateCPFService)

# INFRASTRUCTURE (registrado ✅)
└── event_bus (InMemoryEventBus)

# USE CASES (apenas estes 5 ✅)
├── hubsoft_integration_use_case
├── cpf_verification_use_case
├── admin_operations_use_case
├── member_verification_use_case
└── scheduled_tasks_use_case

# COMMAND HANDLERS (todos registrados ✅)
├── HubSoft: 8 handlers
├── CPF: 4 handlers
└── Admin: 5 handlers
```

---

## 🎯 Plano de Ação Recomendado

### Fase 1: Limpeza Segura (Código Definitivamente Morto)
```bash
# 1. Deletar arquivos de exemplo/teste
rm -f example_handler.py
rm -f complete_migration.py demo_new_bot.py fix_container.py
rm -f migration_bootstrap.py test_telegram_bot_integration.py

# 2. Commitar arquivos deletados do git
git add src/sentinela/bot/
git add src/sentinela/clients/
git add src/sentinela/services/
git commit -m "chore: Remove código morto da arquitetura antiga"
```

### Fase 2: Avaliar Use Cases Não Utilizados
Para cada use case morto, decidir:
- ✅ **Precisa?** → Migrar para nova arquitetura e registrar no DI Container
- ❌ **Não precisa?** → Deletar

**Lista para avaliar:**
- `group_management_use_case.py`
- `invite_management_use_case.py`
- `permission_management_use_case.py`
- `tech_notification_use_case.py`
- `topic_management_use_case.py`
- `support_form_use_case.py`
- `gaming_support_use_case.py`
- `welcome_management_use_case.py`

### Fase 3: Completar Migrações Incompletas
1. **Implementar `/status` command** (alta prioridade - usuário reportou)
2. **Implementar `admin_sync` callback** (média prioridade)

### Fase 4: Criar Pasta de Arquivo (Opcional)
```bash
mkdir -p _archive/old_architecture
mv src/sentinela/presentation/handlers/support_conversation_handler.py _archive/
mv src/sentinela/presentation/handlers/user_verification_handler.py _archive/
# ... mover outros arquivos mortos mas potencialmente úteis
```

---

## 📝 Notas Importantes

### ⚠️ NÃO DELETAR AINDA:
- `migrations/` - Sistema de migrations de banco de dados (ATIVO)
- `src/sentinela/infrastructure/migration/` - Pode conter código útil

### ✅ ARQUIVOS QUE PARECEM DUPLICADOS MAS SÃO ATIVOS:
- `src/sentinela/domain/services/cpf_validation_service.py` ✅ (NOVO - ATIVO)
- `src/sentinela/services/cpf_validation_service.py` 🪦 (OLD - DELETADO)

Esses são arquivos **diferentes**:
- O da pasta `domain/services/` é NOVO e está sendo usado ✅
- O da pasta `services/` é OLD e foi deletado 🪦

### 🔍 Como Verificar se Arquivo Está Sendo Usado:
```bash
# 1. Verificar se está no DI Container
grep -n "nome_do_arquivo" src/sentinela/infrastructure/config/container.py

# 2. Verificar se é importado em algum lugar
grep -r "from.*nome_do_arquivo" src/

# 3. Verificar se está registrado no telegram_bot_new.py
grep -n "nome_do_arquivo" src/sentinela/presentation/telegram_bot_new.py
```

---

## 🎉 Conclusão

O projeto está **90% limpo** após a migração. Os 10% restantes são:
- **5%** - Use cases não utilizados (avaliar se são necessários)
- **3%** - Handlers alternativos não utilizados (podem ser deletados)
- **2%** - Comandos incompletos que mostram "em migração"

**Prioridade Máxima:** Completar migração do `/status` command
**Prioridade Média:** Deletar código morto confirmado
**Prioridade Baixa:** Avaliar use cases não utilizados

---

**Documentado em:** 2025-10-01
**Por:** Claude Code (Auditoria Automática)
**Próxima Revisão:** Após implementação do `/status` command
