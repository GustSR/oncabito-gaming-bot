# 🏗️ Visão Geral da Arquitetura

## Introdução

O **Sentinela Bot** é construído utilizando **Clean Architecture** combinada com **Domain-Driven Design (DDD)**, garantindo:

- 🔄 **Manutenibilidade** - Código fácil de modificar e estender
- 🧪 **Testabilidade** - Camadas isoladas facilitam testes
- 🔌 **Flexibilidade** - Troca de frameworks sem afetar o núcleo
- 📊 **Escalabilidade** - Preparado para crescimento

## Arquitetura em Camadas

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│   (Telegram Handlers, CLI, API)         │
└────────────┬────────────────────────────┘
             │ Usa ↓
┌─────────────────────────────────────────┐
│        Application Layer                │
│  (Use Cases, Commands, Queries)         │
└────────────┬────────────────────────────┘
             │ Usa ↓
┌─────────────────────────────────────────┐
│          Domain Layer                   │
│  (Entities, Value Objects, Services)    │
│      ** NÚCLEO DO SISTEMA **            │
└────────────┬────────────────────────────┘
             ↑ Implementa
┌─────────────────────────────────────────┐
│      Infrastructure Layer               │
│  (DB, External APIs, Event Bus)         │
└─────────────────────────────────────────┘
```

## Camadas Detalhadas

### 1. Domain Layer (Núcleo de Negócio)

**Responsabilidade:** Regras de negócio puras

**Componentes:**
- **Entities:** Objetos com identidade (User, Ticket, CPFVerification)
- **Value Objects:** Objetos imutáveis (CPF, UserId, PermissionLevel)
- **Domain Services:** Lógica complexa de domínio (CPFValidationService)
- **Domain Events:** Eventos que acontecem no domínio (UserRegistered)
- **Repositories (interfaces):** Contratos de persistência

**Regras:**
- ❌ NÃO depende de NADA externo
- ❌ NÃO sabe de frameworks (Telegram, Django, etc)
- ✅ Contém apenas lógica de negócio
- ✅ 100% testável sem mocks complexos

**Exemplo:**
```python
# domain/entities/user.py
@dataclass
class User(Entity):
    telegram_id: int
    cpf: Optional[CPF]
    is_verified: bool

    def verify_cpf(self, cpf: CPF) -> None:
        """Regra de negócio pura"""
        if self.is_banned:
            raise DomainError("Banned users cannot verify")
        self.cpf = cpf
        self.is_verified = True
```

### 2. Application Layer (Casos de Uso)

**Responsabilidade:** Orquestração de operações

**Componentes:**
- **Use Cases:** Orquestradores (CPFVerificationUseCase)
- **Commands:** Comandos CQRS (StartCPFVerificationCommand)
- **Queries:** Consultas CQRS (GetUserByCPFQuery)
- **DTOs:** Objetos de transferência de dados

**Regras:**
- ✅ Usa Domain Layer
- ✅ Define interfaces que Infrastructure implementa
- ❌ NÃO conhece detalhes de implementação (Telegram, SQLite)
- ✅ Coordena fluxo de operações

**Exemplo:**
```python
# application/use_cases/cpf_verification_use_case.py
class CPFVerificationUseCase(UseCase):
    async def start_verification(
        self, user_id: int, cpf: str
    ) -> UseCaseResult:
        # 1. Busca usuário
        user = await self.user_repository.find_by_telegram_id(user_id)

        # 2. Valida CPF (Domain Service)
        if not self.cpf_service.is_valid(cpf):
            return UseCaseResult(success=False, message="CPF inválido")

        # 3. Verifica duplicatas (Domain Service)
        if await self.duplicate_service.has_duplicate(cpf):
            return UseCaseResult(success=False, message="CPF já cadastrado")

        # 4. Cria verificação (Entity)
        verification = CPFVerification.create(user.id, CPF(cpf))

        # 5. Persiste
        await self.verification_repository.save(verification)

        # 6. Publica evento
        await self.event_bus.publish(CPFVerificationStartedEvent(...))

        return UseCaseResult(success=True)
```

### 3. Infrastructure Layer (Implementação)

**Responsabilidade:** Detalhes técnicos

**Componentes:**
- **Repositories:** Implementações SQLite (SQLiteUserRepository)
- **External Services:** APIs externas (HubSoftAPIService)
- **Event Bus:** Sistema de eventos (InMemoryEventBus)
- **Dependency Injection:** Container de DI

**Regras:**
- ✅ Implementa interfaces do Domain/Application
- ✅ Conhece frameworks específicos
- ✅ Lida com I/O (banco, rede, arquivos)

**Exemplo:**
```python
# infrastructure/repositories/sqlite_user_repository.py
class SQLiteUserRepository(UserRepository):
    async def find_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        query = "SELECT * FROM users WHERE telegram_id = ?"
        # ... implementação SQLite específica
        return User.from_dict(row)
```

### 4. Presentation Layer (Interface)

**Responsabilidade:** Interação com usuário

**Componentes:**
- **Handlers:** Telegram handlers (TelegramBotHandler)
- **Controllers:** Controladores HTTP (se existir API)
- **CLI:** Interface de linha de comando

**Regras:**
- ✅ Usa Application Layer (Use Cases)
- ✅ Traduz comandos externos para Use Cases
- ✅ Formata respostas para o usuário

**Exemplo:**
```python
# presentation/handlers/telegram_bot_handler.py
class TelegramBotHandler:
    async def handle_verificar_cpf(self, update, context):
        # 1. Extrai dados do Telegram
        user_id = update.effective_user.id
        cpf = context.args[0]

        # 2. Chama Use Case
        result = await self.cpf_use_case.start_verification(user_id, cpf)

        # 3. Formata resposta
        if result.success:
            await update.message.reply_text("✅ CPF em verificação!")
        else:
            await update.message.reply_text(f"❌ {result.message}")
```

## Fluxo de Dados Típico

```
┌──────────┐
│ Telegram │  1. /verificar_cpf 123.456.789-00
└────┬─────┘
     │
     ↓
┌────────────────────┐
│ TelegramBotHandler │  2. Extrai dados do comando
└────┬───────────────┘
     │
     ↓
┌────────────────────────┐
│ CPFVerificationUseCase │  3. Orquestra operação
└────┬───────────────────┘
     │
     ├──→ CPFValidationService (Domain)
     ├──→ DuplicateCPFService (Domain)
     ├──→ SQLiteUserRepository (Infrastructure)
     ├──→ SQLiteCPFVerificationRepository (Infrastructure)
     └──→ EventBus (Infrastructure)

     ↓
┌─────────────┐
│ EventBus    │  4. Publica CPFVerificationStartedEvent
└─────┬───────┘
      │
      ↓
┌──────────────────┐
│ EventHandlers    │  5. Processa evento (notificações, integrações)
└──────────────────┘
```

## Padrões Implementados

### 1. Repository Pattern
Abstração de persistência de dados.

```python
# Interface (Domain)
class UserRepository(ABC):
    @abstractmethod
    async def find_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        pass

# Implementação (Infrastructure)
class SQLiteUserRepository(UserRepository):
    async def find_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        # Implementação específica SQLite
```

### 2. Event-Driven Architecture
Comunicação assíncrona entre componentes.

```python
# Use Case publica evento
await self.event_bus.publish(
    UserRegistered(user_id=123, username="john")
)

# Handler processa evento
class UserEventHandler:
    async def handle_user_registered(self, event: UserRegistered):
        # Envia notificação
        # Cria invite
        # etc
```

### 3. CQRS (Command Query Responsibility Segregation)
Separação de comandos (escrita) e queries (leitura).

```python
# Command - Altera estado
class StartCPFVerificationCommand:
    user_id: int
    cpf: str

# Query - Apenas leitura
class GetUserByCPFQuery:
    cpf: str
```

### 4. Dependency Injection
Gerenciamento de dependências centralizado.

```python
# Container registra dependências
container.register("user_repository", SQLiteUserRepository)
container.register("cpf_use_case", CPFVerificationUseCase)

# Use Case recebe dependências
use_case = container.get("cpf_use_case")
```

## Benefícios da Arquitetura

### ✅ Testabilidade
- Domain Layer 100% testável sem mocks
- Use Cases testáveis com mocks simples
- Testes de integração isolados

### ✅ Manutenibilidade
- Código organizado por responsabilidade
- Fácil localizar onde fazer mudanças
- Refatorações seguras

### ✅ Flexibilidade
- Trocar SQLite por PostgreSQL: só muda Infrastructure
- Trocar Telegram por Discord: só muda Presentation
- Adicionar API REST: nova Presentation Layer

### ✅ Escalabilidade
- Componentes independentes
- Fácil adicionar novos Use Cases
- Event Bus permite processamento assíncrono

## 🎯 Decisões Arquiteturais Importantes

### Tickets de Suporte - Single Source of Truth
- **📋 Fonte Única de Dados:** HubSoft API
- **❌ Persistência Local:** NÃO utilizada para tickets
- **✅ Motivo:** Evitar dessincronização e complexidade
- **📚 Detalhes:** Ver [ADR-001 em ARCHITECTURAL_DECISIONS.md](./ARCHITECTURAL_DECISIONS.md#adr-001-hubsoft-como-single-source-of-truth-para-tickets)

**Implementação:**
```python
# ✅ Criar ticket - Apenas no HubSoft
result = await hubsoft_use_case.sync_ticket_to_hubsoft(...)

# ✅ Consultar tickets - Apenas do HubSoft
tickets = await hubsoft_use_case.get_user_tickets(user_id)
```

**Benefícios:**
- Sem risco de dados dessincronizados
- Código mais simples e manutenível
- Dados sempre refletem estado atual do HubSoft
- Clean Architecture respeitada (presentation não acessa DB)

---

## Próximos Passos

- [Estrutura do Projeto](./PROJECT_STRUCTURE.md) - Organização de arquivos
- [Decisões Arquiteturais](./ARCHITECTURAL_DECISIONS.md) - ADRs documentados
- [Fluxo de Dados](./DATA_FLOW.md) - Exemplos detalhados
- [Padrões Implementados](./PATTERNS.md) - Design patterns em detalhes
