# 🏗️ Nova Arquitetura - Clean Architecture & DDD

## 📋 **Estrutura de Camadas**

```
src/sentinela/
├── 📱 presentation/           # Camada de Apresentação
│   ├── handlers/              # Telegram Bot handlers (só roteamento)
│   └── mappers/               # DTOs ↔ Domain objects
│
├── ⚙️ application/            # Camada de Aplicação
│   ├── commands/              # Commands (modificam estado)
│   ├── queries/               # Queries (consultas)
│   └── use_cases/             # Casos de uso
│
├── 🧠 domain/                 # Camada de Domínio
│   ├── entities/              # Entidades (User, Ticket, etc.)
│   ├── value_objects/         # CPF, Email, Protocol, etc.
│   ├── services/              # Domain Services
│   └── repositories/          # Interfaces de Repository
│
└── 💾 infrastructure/         # Camada de Infraestrutura
    ├── repositories/          # Implementações SQLite
    ├── external_services/     # HubSoft, Telegram clients
    └── config/                # Configurações técnicas
```

## 🎯 **Princípios da Arquitetura**

### **1. Dependency Rule**
```
Presentation → Application → Domain ← Infrastructure
```
- Domain não depende de nada
- Application depende apenas de Domain
- Infrastructure implementa interfaces do Domain
- Presentation usa Application layer

### **2. Separation of Concerns**
```
📱 Presentation: "Como mostrar/receber dados"
⚙️ Application: "O que fazer" (orchestration)
🧠 Domain: "Regras de negócio"
💾 Infrastructure: "Como persistir/acessar"
```

### **3. SOLID Principles**
- **S**ingle Responsibility: Cada classe tem uma razão para mudar
- **O**pen/Closed: Extensível sem modificar código existente
- **L**iskov Substitution: Implementações substituíveis
- **I**nterface Segregation: Interfaces focadas
- **D**ependency Inversion: Dependa de abstrações

## 🔄 **Fluxo de Dados**

### **Comando (Write Operation)**
```
1. Handler recebe input do Telegram
2. Mapeia para Command
3. Command Handler executa use case
4. Use case aplica regras de negócio
5. Repository persiste mudanças
6. Domain events são disparados
7. Response volta para Handler
```

### **Query (Read Operation)**
```
1. Handler recebe request
2. Mapeia para Query
3. Query Handler busca dados
4. Repository retorna dados
5. Mapeia para DTO
6. Handler formata resposta
```

## 📊 **Benefícios Esperados**

### **🧪 Testabilidade**
- Domain logic 100% testável (sem infraestrutura)
- Mocks simples via interfaces
- Testes de integração isolados

### **🔧 Manutenibilidade**
- Mudanças isoladas por camada
- Refatoração segura com tipos
- Debugging direcionado

### **🚀 Extensibilidade**
- Novos handlers = nova rota
- Novos providers = nova implementação
- Novos casos de uso = novo handler

### **📈 Performance**
- Repository pattern permite caching
- Command/Query separation otimiza leitura
- Async/await em toda I/O

## 🎭 **Exemplos de Uso**

### **Value Object**
```python
@dataclass(frozen=True)
class CPF:
    value: str

    def __post_init__(self):
        if not self._is_valid():
            raise InvalidCPFError(self.value)

    def _is_valid(self) -> bool:
        # Lógica de validação
        return len(self.value) == 11 and self.value.isdigit()

    def formatted(self) -> str:
        return f"{self.value[:3]}.{self.value[3:6]}.{self.value[6:9]}-{self.value[9:]}"
```

### **Entity**
```python
class Ticket(Entity):
    def __init__(self, id: TicketId, user: User, category: str):
        super().__init__(id)
        self.user = user
        self.category = category
        self.status = TicketStatus.OPEN
        self._messages: List[Message] = []
        self._events: List[DomainEvent] = []

    def add_message(self, content: str, author: User) -> None:
        if self.status == TicketStatus.CLOSED:
            raise TicketClosedError()

        message = Message(content, author, datetime.now())
        self._messages.append(message)
        self._events.append(MessageAdded(self.id, message))

    def close(self) -> None:
        if self.status != TicketStatus.OPEN:
            raise InvalidStatusTransitionError()

        self.status = TicketStatus.CLOSED
        self._events.append(TicketClosed(self.id))
```

### **Repository Interface**
```python
class TicketRepository(ABC):
    @abstractmethod
    async def save(self, ticket: Ticket) -> None:
        pass

    @abstractmethod
    async def find_by_id(self, id: TicketId) -> Optional[Ticket]:
        pass

    @abstractmethod
    async def find_by_user(self, user_id: UserId) -> List[Ticket]:
        pass
```

### **Command Handler**
```python
@dataclass
class CreateTicketCommand:
    user_id: int
    category: str
    description: str

class CreateTicketHandler:
    def __init__(
        self,
        user_repo: UserRepository,
        ticket_repo: TicketRepository,
        event_bus: EventBus
    ):
        self._user_repo = user_repo
        self._ticket_repo = ticket_repo
        self._event_bus = event_bus

    async def handle(self, command: CreateTicketCommand) -> TicketId:
        # 1. Busca usuário
        user = await self._user_repo.find_by_id(UserId(command.user_id))
        if not user:
            raise UserNotFoundError()

        # 2. Aplica regras de negócio
        if not user.can_create_ticket():
            raise TicketCreationNotAllowedError()

        # 3. Cria ticket
        ticket = Ticket.create(user, command.category, command.description)

        # 4. Persiste
        await self._ticket_repo.save(ticket)

        # 5. Publica eventos
        for event in ticket.events:
            await self._event_bus.publish(event)

        return ticket.id
```

## 🚧 **Status da Migração**

### ✅ **Fase 1: Estrutura (Concluída)**
- Criação das camadas
- Definição de responsabilidades
- Documentação

### 🔄 **Próximas Fases**
1. **Repository Pattern** - Abstrações e implementações
2. **DI Container** - Injeção de dependências
3. **CQRS** - Commands e Queries
4. **Domain Layer** - Entities e Value Objects
5. **Migration** - Migração gradual do código existente

---

*Esta arquitetura garante que o sistema seja:*
- ✅ **Testável** (domain logic isolado)
- ✅ **Manutenível** (mudanças isoladas)
- ✅ **Extensível** (novos recursos fáceis)
- ✅ **Performante** (async + caching)
- ✅ **Type-safe** (mypy compliance)