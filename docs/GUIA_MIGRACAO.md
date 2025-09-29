# 🔄 Guia de Migração - Para Nova Arquitetura

## 🎯 **Como Migrar o Código Existente**

### **📋 Estratégia: Strangler Fig Pattern**

Migração gradual sem quebrar o sistema existente:

```
FASE 1: Criar nova estrutura (✅ CONCLUÍDO)
FASE 2: Migrar uma funcionalidade por vez
FASE 3: Deprecar código antigo
FASE 4: Remover código legacy
```

### **🔄 Processo de Migração por Funcionalidade**

#### **1. Identificar Funcionalidade**
```
Exemplo: "Criação de Usuário"

📍 Código atual:
- Handler: src/sentinela/bot/handlers.py (start_command)
- Service: src/sentinela/services/user_service.py
- DB: src/sentinela/clients/db_client.py (save_user_data)
```

#### **2. Criar Value Objects**
```python
# ANTES (primitivo)
def save_user_data(user_id: int, cpf: str, name: str):
    pass

# DEPOIS (value objects)
def save_user_data(user_id: UserId, cpf: CPF, name: str):
    pass
```

#### **3. Criar Entity**
```python
# ANTES (dict/dados primitivos)
user_data = {
    'user_id': 123,
    'cpf': '12345678901',
    'name': 'João'
}

# DEPOIS (entity rica)
user = User(
    user_id=UserId(123),
    cpf=CPF.from_raw('123.456.789-01'),
    client_name='João'
)
```

#### **4. Criar Repository**
```python
# ANTES (acesso direto ao DB)
def get_user_data(user_id):
    conn = sqlite3.connect(DATABASE_FILE)
    # SQL direto...

# DEPOIS (repository)
user_repo = container.get(UserRepository)
user = await user_repo.find_by_id(UserId(user_id))
```

#### **5. Criar Command/Query**
```python
# ANTES (lógica no handler)
async def start_command(update, context):
    user_id = update.effective_user.id
    # Lógica complexa aqui...

# DEPOIS (command)
command = CreateUserCommand(
    user_id=update.effective_user.id,
    cpf=cpf_input,
    # ...
)
result = await create_user_handler.handle(command)
```

---

## 📚 **Exemplos de Migração**

### **🔧 Migração: User Service**

#### **ANTES (Código Atual)**
```python
# src/sentinela/services/user_service.py
def save_user_to_database(user_id, username, cpf, client_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, cpf, client_name, is_active)
        VALUES (?, ?, ?, ?, 1)
    """, (user_id, username, cpf, client_name))
    conn.commit()
    conn.close()
```

#### **DEPOIS (Nova Arquitetura)**

**1. Value Objects**
```python
user_id = UserId(user_id)
cpf = CPF.from_raw(cpf)
```

**2. Entity**
```python
user = User(
    user_id=user_id,
    username=username,
    cpf=cpf,
    client_name=client_name
)
```

**3. Repository**
```python
user_repo = container.get(UserRepository)
await user_repo.save(user)
```

**4. Command**
```python
command = CreateUserCommand(
    user_id=user_id,
    username=username,
    cpf=cpf,
    client_name=client_name
)
handler = CreateUserHandler(user_repo)
result = await handler.handle(command)
```

---

### **🔧 Migração: Support Service**

#### **ANTES (Código Atual)**
```python
# src/sentinela/services/support_service.py
class SupportFormManager:
    CATEGORIES = {...}
    POPULAR_GAMES = {...}

    async def handle_support_request(user_id, username, user_mention):
        # 300+ linhas de código misturado
        pass
```

#### **DEPOIS (Nova Arquitetura)**

**1. Value Objects**
```python
@dataclass(frozen=True)
class TicketCategory(ValueObject):
    value: str
    display_name: str

    def __post_init__(self):
        if self.value not in VALID_CATEGORIES:
            raise ValidationError(f"Invalid category: {self.value}")

@dataclass(frozen=True)
class GameTitle(ValueObject):
    value: str
    display_name: str
```

**2. Entity**
```python
class Ticket(AggregateRoot[TicketId]):
    def __init__(self, user: User, category: TicketCategory):
        super().__init__(TicketId.generate())
        self.user = user
        self.category = category
        self.status = TicketStatus.OPEN
        self._messages = []

    def add_message(self, content: str, author: User):
        if self.status == TicketStatus.CLOSED:
            raise TicketClosedError()

        message = Message(content, author, datetime.now())
        self._messages.append(message)
        self._add_event(MessageAdded(self.id, message))
```

**3. Commands**
```python
@dataclass(frozen=True)
class CreateTicketCommand:
    user_id: int
    category: str
    game: str
    description: str

class CreateTicketHandler:
    async def handle(self, command: CreateTicketCommand) -> TicketId:
        # Lógica de negócio isolada
        pass
```

**4. Handler Simplificado**
```python
@dependency_injected
async def handle_support_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    create_ticket_handler: CreateTicketHandler
):
    # Apenas roteamento e formatação
    command = CreateTicketCommand(...)
    ticket_id = await create_ticket_handler.handle(command)
    await update.message.reply_text(f"Ticket {ticket_id} criado!")
```

---

## 🚦 **Plano de Migração Progressiva**

### **SEMANA 1-2: Setup Básico**
- ✅ Estrutura de camadas criada
- ✅ Repository pattern implementado
- ✅ DI Container funcionando
- ✅ Exemplos de Command/Query

### **SEMANA 3-4: Migração Core**
1. **User Management**
   - Migrar `user_service.py` → Commands/Queries
   - Migrar `db_client.py` (user operations) → UserRepository
   - Atualizar handlers de `/start`, `/status`

2. **CPF Verification**
   - Migrar `cpf_verification_service.py` → Domain Service
   - Criar VerificationRepository
   - Commands: StartVerification, CompleteVerification

### **SEMANA 5-6: Features Principais**
3. **Support System**
   - Ticket entity + repository
   - Support workflow commands
   - Form conversation state management

4. **Admin Operations**
   - Admin entity + permissions
   - Admin commands (sync, health check)
   - Notification system refactor

### **SEMANA 7-8: Integrations**
5. **HubSoft Integration**
   - Migrar para External Services layer
   - Criar abstrações para API calls
   - Event-driven sync

6. **Telegram Bot**
   - Migrar todos handlers para Presentation layer
   - Dependency injection everywhere
   - Clean separation

### **SEMANA 9-10: Legacy Cleanup**
7. **Deprecation**
   - Marcar código antigo como @deprecated
   - Mover para namespace legacy
   - Logging de uso de APIs antigas

8. **Migration Scripts**
   - Scripts para migrar dados existentes
   - Validação de integridade
   - Rollback procedures

---

## 🔧 **Ferramentas de Migração**

### **Migration Checker Script**
```python
#!/usr/bin/env python3
"""
Script para verificar progresso da migração.
"""

def check_migration_progress():
    """Verifica quais partes ainda precisam migrar."""

    # Verifica imports antigos
    old_imports = find_old_imports()

    # Verifica funções não migradas
    legacy_functions = find_legacy_functions()

    # Verifica coverage de testes
    test_coverage = check_test_coverage()

    print(f"Migration Progress:")
    print(f"  Legacy imports: {len(old_imports)}")
    print(f"  Legacy functions: {len(legacy_functions)}")
    print(f"  Test coverage: {test_coverage}%")
```

### **Backward Compatibility Layer**
```python
# src/sentinela/legacy/compatibility.py
"""
Camada de compatibilidade para transição gradual.
"""

import warnings
from ..application.commands.create_user_command import CreateUserCommand
from ..infrastructure.config.dependency_injection import get_container

def save_user_data(user_id, username, cpf, client_name):
    """
    DEPRECATED: Use CreateUserCommand instead.

    Esta função será removida na v3.0.
    """
    warnings.warn(
        "save_user_data is deprecated. Use CreateUserCommand instead.",
        DeprecationWarning,
        stacklevel=2
    )

    # Redireciona para nova implementação
    command = CreateUserCommand(
        user_id=user_id,
        username=username,
        cpf=cpf,
        client_name=client_name
    )

    container = get_container()
    handler = container.get(CreateUserHandler)

    # Converte async para sync para compatibilidade
    import asyncio
    return asyncio.run(handler.handle(command))
```

---

## 📊 **Métricas de Sucesso**

### **Indicadores de Progresso**
- [ ] 0% legacy imports em novos arquivos
- [ ] 80%+ test coverage em domain layer
- [ ] 0 acesso direto ao SQLite fora de repositories
- [ ] Todos handlers usam dependency injection
- [ ] Commands/Queries para todas operações

### **Performance Benchmarks**
- [ ] Tempo de resposta ≤ anterior
- [ ] Memory usage ≤ anterior
- [ ] Startup time ≤ anterior
- [ ] Error rate ≤ anterior

### **Quality Gates**
- [ ] mypy 100% type coverage
- [ ] 0 cyclic dependencies
- [ ] All business logic in domain layer
- [ ] All I/O async/await

---

## 🚨 **Troubleshooting**

### **Problemas Comuns na Migração**

#### **Import Errors**
```
# PROBLEMA
ModuleNotFoundError: No module named 'sentinela.domain'

# SOLUÇÃO
Verificar PYTHONPATH e structure dos __init__.py
```

#### **Circular Dependencies**
```
# PROBLEMA
ImportError: cannot import name 'UserRepository' from partially initialized module

# SOLUÇÃO
Usar dependency injection ao invés de imports diretos
```

#### **Type Hints Conflicts**
```
# PROBLEMA
TypeError: 'type' object is not subscriptable

# SOLUÇÃO
from __future__ import annotations
```

---

*Esta migração garante que o sistema evolui sem quebrar funcionalidades existentes, mantendo alta qualidade e testabilidade.*