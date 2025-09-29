# 🎯 Como Usar a Nova Arquitetura

## 🚀 **Inicialização**

### **1. Bootstrap da Aplicação**
```python
# main.py
from src.sentinela.infrastructure.config.bootstrap import initialize_application

async def main():
    # Inicializa nova arquitetura
    await initialize_application()

    # Resto da inicialização...
```

### **2. Usando Dependency Injection**
```python
from src.sentinela.infrastructure.config.dependency_injection import dependency_injected

@dependency_injected
async def my_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_repository: UserRepository  # ✨ Injetado automaticamente
):
    # user_repository está pronto para uso
    pass
```

---

## 🏗️ **Criando Novas Funcionalidades**

### **📝 Passo 1: Value Objects**
```python
# src/sentinela/domain/value_objects/email.py
@dataclass(frozen=True)
class Email(ValueObject):
    value: str

    def __post_init__(self):
        if '@' not in self.value:
            raise ValidationError("Invalid email format")

    def domain(self) -> str:
        return self.value.split('@')[1]
```

### **🎭 Passo 2: Entities**
```python
# src/sentinela/domain/entities/ticket.py
class Ticket(AggregateRoot[TicketId]):
    def __init__(self, user: User, category: str):
        super().__init__(TicketId.generate())
        self.user = user
        self.category = category
        self.status = TicketStatus.OPEN
        self._add_event(TicketCreated(self.id, user.id))

    def close(self, reason: str) -> None:
        if self.status != TicketStatus.OPEN:
            raise InvalidStatusTransitionError()

        self.status = TicketStatus.CLOSED
        self._add_event(TicketClosed(self.id, reason))
        self._increment_version()
```

### **📦 Passo 3: Repository Interface**
```python
# src/sentinela/domain/repositories/ticket_repository.py
class TicketRepository(Repository[Ticket, TicketId]):
    @abstractmethod
    async def find_by_user(self, user_id: UserId) -> List[Ticket]:
        pass

    @abstractmethod
    async def find_open_tickets(self) -> List[Ticket]:
        pass
```

### **⚙️ Passo 4: Repository Implementation**
```python
# src/sentinela/infrastructure/repositories/sqlite_ticket_repository.py
class SQLiteTicketRepository(TicketRepository):
    async def save(self, ticket: Ticket) -> None:
        # Implementação SQLite específica
        pass

    async def find_by_id(self, ticket_id: TicketId) -> Optional[Ticket]:
        # Implementação específica
        pass
```

### **🎯 Passo 5: Commands & Queries**
```python
# src/sentinela/application/commands/create_ticket_command.py
@dataclass(frozen=True)
class CreateTicketCommand:
    user_id: int
    category: str
    description: str

# src/sentinela/application/commands/create_ticket_handler.py
class CreateTicketHandler:
    def __init__(
        self,
        user_repo: UserRepository,
        ticket_repo: TicketRepository
    ):
        self._user_repo = user_repo
        self._ticket_repo = ticket_repo

    async def handle(self, command: CreateTicketCommand) -> TicketId:
        # 1. Valida usuário
        user = await self._user_repo.find_by_id(UserId(command.user_id))
        if not user or not user.can_create_ticket():
            raise UserCannotCreateTicketError()

        # 2. Cria ticket
        ticket = Ticket(user, command.category)
        ticket.add_description(command.description)

        # 3. Persiste
        await self._ticket_repo.save(ticket)

        return ticket.id
```

### **📱 Passo 6: Handler (Presentation)**
```python
# src/sentinela/presentation/handlers/ticket_handlers.py
@dependency_injected
async def handle_create_ticket(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    create_ticket_handler: CreateTicketHandler  # ✨ Injetado
):
    user = update.effective_user

    try:
        # 1. Valida input
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("❌ Uso: /ticket <categoria> <descrição>")
            return

        # 2. Cria command
        command = CreateTicketCommand(
            user_id=user.id,
            category=context.args[0],
            description=' '.join(context.args[1:])
        )

        # 3. Executa
        ticket_id = await create_ticket_handler.handle(command)

        # 4. Resposta
        await update.message.reply_text(
            f"✅ Ticket criado: #{ticket_id}\n"
            f"Aguarde atendimento!"
        )

    except UserCannotCreateTicketError:
        await update.message.reply_text("❌ Você não pode criar tickets no momento.")

    except ValidationError as e:
        await update.message.reply_text(f"❌ Dados inválidos: {e.message}")
```

### **⚙️ Passo 7: Registrar Dependências**
```python
# src/sentinela/infrastructure/config/dependency_injection.py
def configure_dependencies():
    container = get_container()

    # Repositories
    container.register_singleton(TicketRepository, SQLiteTicketRepository)

    # Command Handlers
    container.register_singleton(CreateTicketHandler, CreateTicketHandler)

    # Query Handlers
    container.register_singleton(GetTicketHandler, GetTicketHandler)
```

---

## 🧪 **Testando**

### **🎯 Testes de Domain**
```python
# tests/domain/entities/test_ticket.py
def test_ticket_creation():
    # Arrange
    user = User(UserId(123), "test", CPF.from_raw("12345678901"), "Test User")

    # Act
    ticket = Ticket(user, "bug")

    # Assert
    assert ticket.user == user
    assert ticket.status == TicketStatus.OPEN
    assert len(ticket.events) == 1
    assert isinstance(ticket.events[0], TicketCreated)

def test_ticket_close():
    # Arrange
    user = User(UserId(123), "test", CPF.from_raw("12345678901"), "Test User")
    ticket = Ticket(user, "bug")
    ticket.clear_events()  # Limpa eventos de criação

    # Act
    ticket.close("resolved")

    # Assert
    assert ticket.status == TicketStatus.CLOSED
    assert len(ticket.events) == 1
    assert isinstance(ticket.events[0], TicketClosed)
```

### **⚙️ Testes de Application**
```python
# tests/application/commands/test_create_ticket_handler.py
@pytest.fixture
def mock_user_repo():
    return Mock(spec=UserRepository)

@pytest.fixture
def mock_ticket_repo():
    return Mock(spec=TicketRepository)

async def test_create_ticket_success(mock_user_repo, mock_ticket_repo):
    # Arrange
    user = User(UserId(123), "test", CPF.from_raw("12345678901"), "Test User")
    user.activate()  # Usuário pode criar tickets

    mock_user_repo.find_by_id.return_value = user
    mock_ticket_repo.save.return_value = None

    handler = CreateTicketHandler(mock_user_repo, mock_ticket_repo)
    command = CreateTicketCommand(
        user_id=123,
        category="bug",
        description="Test description"
    )

    # Act
    ticket_id = await handler.handle(command)

    # Assert
    assert ticket_id is not None
    mock_user_repo.find_by_id.assert_called_once_with(UserId(123))
    mock_ticket_repo.save.assert_called_once()
```

### **📱 Testes de Integration**
```python
# tests/integration/test_user_repository.py
async def test_sqlite_user_repository():
    # Arrange
    repo = SQLiteUserRepository(":memory:")  # In-memory database

    user = User(
        UserId(123),
        "testuser",
        CPF.from_raw("12345678901"),
        "Test User"
    )

    # Act
    await repo.save(user)
    found_user = await repo.find_by_id(UserId(123))

    # Assert
    assert found_user is not None
    assert found_user.username == "testuser"
    assert found_user.cpf.value == "12345678901"
```

---

## 🔧 **Patterns Úteis**

### **🎭 Domain Events**
```python
# Produzir eventos
class User(AggregateRoot):
    def activate(self):
        self._status = UserStatus.ACTIVE
        self._add_event(UserActivated(self.id))

# Consumir eventos
class UserActivatedHandler:
    async def handle(self, event: UserActivated):
        # Envia email de boas-vindas
        # Notifica admins
        # Etc.
```

### **🔍 Specifications**
```python
# src/sentinela/domain/specifications/user_specifications.py
class CanCreateTicketSpecification:
    def is_satisfied_by(self, user: User) -> bool:
        return (
            user.is_active() and
            user.service_info is not None and
            user.service_info.status == "active"
        )

# Uso
spec = CanCreateTicketSpecification()
if spec.is_satisfied_by(user):
    # Pode criar ticket
```

### **🏭 Factories**
```python
# src/sentinela/domain/factories/ticket_factory.py
class TicketFactory:
    @staticmethod
    def create_support_ticket(user: User, description: str) -> Ticket:
        ticket = Ticket(user, "support")
        ticket.add_description(description)
        ticket.set_priority(Priority.NORMAL)
        return ticket

    @staticmethod
    def create_urgent_ticket(user: User, description: str) -> Ticket:
        ticket = Ticket(user, "urgent")
        ticket.add_description(description)
        ticket.set_priority(Priority.HIGH)
        return ticket
```

---

## 📊 **Monitoramento e Logs**

### **📝 Structured Logging**
```python
import structlog

logger = structlog.get_logger()

async def handle_command(command: CreateTicketCommand):
    logger.info(
        "Creating ticket",
        user_id=command.user_id,
        category=command.category,
        command_type="CreateTicket"
    )

    try:
        result = await self._process_command(command)
        logger.info(
            "Ticket created successfully",
            user_id=command.user_id,
            ticket_id=result.ticket_id,
            command_type="CreateTicket"
        )
        return result

    except Exception as e:
        logger.error(
            "Failed to create ticket",
            user_id=command.user_id,
            error=str(e),
            command_type="CreateTicket"
        )
        raise
```

### **📈 Métricas**
```python
from prometheus_client import Counter, Histogram

COMMANDS_TOTAL = Counter('commands_total', 'Total commands processed', ['command_type', 'status'])
COMMAND_DURATION = Histogram('command_duration_seconds', 'Command processing time', ['command_type'])

async def handle_command(command):
    with COMMAND_DURATION.labels(command_type=type(command).__name__).time():
        try:
            result = await self._process_command(command)
            COMMANDS_TOTAL.labels(command_type=type(command).__name__, status='success').inc()
            return result
        except Exception:
            COMMANDS_TOTAL.labels(command_type=type(command).__name__, status='error').inc()
            raise
```

---

## 🚀 **Performance Tips**

### **⚡ Async Everywhere**
```python
# ✅ BOM
async def handle_command(self, command):
    user = await self._user_repo.find_by_id(command.user_id)
    await self._ticket_repo.save(ticket)

# ❌ RUIM
def handle_command(self, command):
    user = self._user_repo.find_by_id(command.user_id)  # Blocking
    self._ticket_repo.save(ticket)  # Blocking
```

### **🎯 Repository Patterns**
```python
# ✅ BOM - Operações em lote
async def create_multiple_tickets(commands: List[CreateTicketCommand]):
    tickets = []
    for command in commands:
        # Cria entidades em memória
        ticket = self._create_ticket_from_command(command)
        tickets.append(ticket)

    # Salva em lote
    await self._ticket_repo.save_batch(tickets)

# ❌ RUIM - Uma operação por vez
async def create_multiple_tickets(commands: List[CreateTicketCommand]):
    for command in commands:
        ticket = self._create_ticket_from_command(command)
        await self._ticket_repo.save(ticket)  # N+1 problem
```

---

*Esta arquitetura garante código limpo, testável e manutenível! 🎉*