# 📁 Estrutura do Projeto

## Visão Geral

```
sentinela/
├── src/sentinela/           # Código-fonte
│   ├── domain/              # 🔵 Domain Layer
│   ├── application/         # 🟢 Application Layer
│   ├── infrastructure/      # 🟡 Infrastructure Layer
│   └── presentation/        # 🔴 Presentation Layer
├── docs/                    # Documentação
├── data/                    # Dados persistentes
├── logs/                    # Logs do sistema
└── tests/                   # Testes (futuro)
```

## 🔵 Domain Layer

**Localização:** `src/sentinela/domain/`

**Responsabilidade:** Núcleo do negócio

```
domain/
├── entities/                # Entidades de domínio
│   ├── base.py             # Entity base + DomainEvent
│   ├── user.py             # Usuário
│   ├── cpf_verification.py # Verificação de CPF
│   ├── ticket.py           # Chamado de suporte
│   ├── group_member.py     # Membro do grupo
│   ├── group_topic.py      # Tópico do grupo
│   └── invite_link.py      # Link de convite
│
├── value_objects/          # Value Objects imutáveis
│   ├── identifiers.py      # UserId, TicketId, CPF
│   ├── cpf.py             # CPF
│   ├── problem_category.py # Categorias
│   ├── game_title.py      # Jogos
│   ├── permission_level.py # Permissões
│   ├── notification_priority.py  # Prioridades
│   ├── welcome_message.py # Templates mensagens
│   └── scheduled_task.py  # Tarefas agendadas
│
├── repositories/           # Interfaces (contratos)
│   ├── user_repository.py
│   ├── cpf_verification_repository.py
│   ├── ticket_repository.py
│   ├── group_member_repository.py
│   ├── group_topic_repository.py
│   ├── admin_repository.py          # 👤 Administradores
│   ├── duplicate_conflict_repository.py  # Conflitos de CPF
│   └── hubsoft_api_repository.py
│
├── services/              # Domain Services
│   ├── cpf_validation_service.py     # Validação CPF
│   ├── duplicate_cpf_service.py      # Detecção duplicatas
│   ├── permission_service.py         # Lógica de permissões
│   ├── notification_formatter_service.py  # Formatação notificações
│   └── gaming_diagnostic_service.py  # Diagnóstico gaming
│
└── events/               # Domain Events
    ├── user_events.py    # 20+ eventos de usuário
    ├── ticket_events.py  # Eventos de tickets
    ├── group_events.py   # Eventos de grupo
    └── system_events.py  # Eventos de sistema
```

### Convenções Domain Layer

```python
# ✅ BOM - Entity imutável onde possível
@dataclass(frozen=True)
class CPF:
    value: str

    def __post_init__(self):
        if not self._is_valid():
            raise ValueError("CPF inválido")

# ✅ BOM - Entity com comportamento
@dataclass
class User(Entity):
    telegram_id: int
    cpf: Optional[CPF]

    def verify_cpf(self, cpf: CPF) -> None:
        # Lógica de negócio aqui
        self.cpf = cpf
        self.is_verified = True

# ❌ RUIM - Entity anêmica (apenas getters/setters)
class User:
    def set_cpf(self, cpf): self.cpf = cpf
    def get_cpf(self): return self.cpf
```

## 🟢 Application Layer

**Localização:** `src/sentinela/application/`

**Responsabilidade:** Orquestração de operações

```
application/
├── use_cases/             # Use Cases (orquestradores)
│   ├── base.py           # UseCase base + UseCaseResult
│   ├── cpf_verification_use_case.py
│   ├── hubsoft_integration_use_case.py
│   ├── admin_operations_use_case.py
│   ├── support_form_use_case.py
│   ├── permission_management_use_case.py
│   ├── tech_notification_use_case.py
│   ├── group_management_use_case.py
│   ├── invite_management_use_case.py
│   ├── welcome_management_use_case.py
│   ├── topic_management_use_case.py
│   ├── scheduled_tasks_use_case.py
│   └── gaming_support_use_case.py
│
├── commands/             # CQRS Commands (escrita)
│   ├── cpf_verification_commands.py
│   ├── admin_commands.py
│   └── ticket_commands.py
│
├── command_handlers/     # Handlers de Commands
│   └── process_expired_verifications_handler.py
│
└── queries/              # CQRS Queries (leitura)
    └── user_queries.py
```

### Convenções Application Layer

```python
# ✅ BOM - Use Case com responsabilidade única
class CPFVerificationUseCase(UseCase):
    async def start_verification(
        self, user_id: int, cpf: str
    ) -> UseCaseResult:
        # Orquestra: valida, persiste, publica evento
        pass

# ✅ BOM - Command explícito
@dataclass
class StartCPFVerificationCommand:
    user_id: int
    cpf: str
    requested_by: int

# ❌ RUIM - Use Case fazendo muitas coisas
class EverythingUseCase:
    def do_everything(...): # Evite isso!
```

## 🟡 Infrastructure Layer

**Localização:** `src/sentinela/infrastructure/`

**Responsabilidade:** Detalhes de implementação

```
infrastructure/
├── config/               # Configuração e DI
│   └── container.py     # Dependency Injection Container
│
├── repositories/         # Implementações de repositórios
│   ├── sqlite_user_repository.py
│   ├── sqlite_cpf_verification_repository.py
│   ├── sqlite_ticket_repository.py
│   ├── sqlite_group_member_repository.py
│   ├── sqlite_group_topic_repository.py
│   └── sqlite_hubsoft_integration_repository.py
│
├── external_services/    # Serviços externos
│   ├── hubsoft_api_service.py          # Implementação real
│   └── mock_hubsoft_api_service.py     # Mock para testes
│
├── events/              # Sistema de eventos
│   ├── event_bus.py    # Event Bus (InMemoryEventBus)
│   └── handlers/
│       └── user_event_handlers.py      # Event Handlers
│
└── migration/          # Sistema de migração (temporário)
    ├── manager.py
    └── legacy_adapter.py
```

### Convenções Infrastructure Layer

```python
# ✅ BOM - Repository implementa interface do Domain
class SQLiteUserRepository(UserRepository):
    async def find_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        # Implementação SQLite específica
        pass

# ✅ BOM - External Service com tratamento de erros
class HubSoftAPIService(HubSoftAPIRepository):
    async def check_contract_status(self, cpf: str) -> bool:
        try:
            response = await self._make_request(...)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"HubSoft API error: {e}")
            raise ExternalServiceError()

# ❌ RUIM - Lógica de negócio no Repository
class BadRepository(UserRepository):
    async def find_and_verify_user(...):  # Evite lógica aqui!
```

## 🔴 Presentation Layer

**Localização:** `src/sentinela/presentation/`

**Responsabilidade:** Interface com usuário

```
presentation/
├── handlers/             # Handlers de interface
│   ├── telegram_bot_handler.py         # Handler principal Telegram
│   └── support_conversation_handler.py # Formulário conversacional
│
└── mappers/             # Mapeadores DTO ↔ Entity
    └── (futuros mappers)
```

### Convenções Presentation Layer

```python
# ✅ BOM - Handler delega para Use Case
class TelegramBotHandler:
    async def handle_verificar_cpf(self, update, context):
        user_id = update.effective_user.id
        cpf = context.args[0]

        # Delega para Use Case
        result = await self.cpf_use_case.start_verification(user_id, cpf)

        # Formata resposta
        await update.message.reply_text(result.message)

# ❌ RUIM - Handler com lógica de negócio
class BadHandler:
    async def handle_verificar_cpf(...):
        # Não faça validações complexas aqui!
        # Não acesse banco diretamente!
        # Sempre delegue para Use Case!
```

## 📦 Outros Diretórios

### data/
Dados persistentes (gitignored)
```
data/
└── database/
    └── sentinela.db  # SQLite database
```

### logs/
Arquivos de log (gitignored)
```
logs/
├── app.log
├── error.log
└── access.log
```

### docs/
Documentação do projeto
```
docs/
├── README.md           # Índice da documentação
├── architecture/       # Documentação de arquitetura
├── api/               # Documentação de APIs
├── guides/            # Guias práticos
└── migration/         # Documentação de migração
```

## 🎯 Convenções Gerais

### Nomenclatura

```python
# Classes
User              # PascalCase para classes
CPFVerification   # PascalCase com acrônimos

# Métodos e funções
def start_verification()  # snake_case
async def get_user()      # snake_case

# Constantes
MAX_RETRIES = 3          # UPPER_SNAKE_CASE
DEFAULT_TIMEOUT = 300

# Variáveis
user_id = 123            # snake_case
cpf_number = "123..."
```

### Estrutura de Arquivos

```python
# ✅ 1 classe por arquivo
# user.py
class User(Entity):
    pass

# ✅ Nome do arquivo = nome da classe (snake_case)
cpf_verification_use_case.py  # contém CPFVerificationUseCase

# ✅ __init__.py em todos os pacotes
domain/
├── __init__.py
├── entities/
│   └── __init__.py
```

### Imports

```python
# ✅ Imports organizados
# 1. Standard library
import logging
from datetime import datetime

# 2. Third-party
from telegram import Update

# 3. Local - Absolutos do src
from sentinela.domain.entities.user import User
from sentinela.application.use_cases.cpf_verification_use_case import CPFVerificationUseCase

# ❌ Evite imports relativos complexos
from ....domain.entities.user import User  # Não faça isso!
```

## 📦 Scripts e Ferramentas

**Localização:** `scripts/`

**Responsabilidade:** Automação, manutenção e ferramentas operacionais

```
scripts/
├── dev/                    # Ferramentas de desenvolvimento
│   └── dev.sh             # Helper principal (./dev.sh start/stop/logs)
│
├── tasks/                 # Tarefas automatizadas (via cron)
│   ├── daily_cpf_checkup.py       # Checkup diário completo (6 fases)
│   │                              # - Sincroniza administradores
│   │                              # - Detecta CPFs duplicados
│   │                              # - Verifica contratos cancelados
│   ├── verify_data_integrity.py   # Verificação de integridade
│   └── export_critical_data.py    # Export de backup JSON
│
└── tools/                 # Ferramentas manuais
    └── clear_group_messages.py    # Limpeza de mensagens (preserva fixadas)
```

### Cron Jobs Configurados

```bash
# deployment/setup-cron.sh instala 4 cron jobs:

# 1. Auto-Update (00:00-05:00, cada 10 min)
*/10 0-5 * * * ./deployment/auto-update.sh

# 2. Daily Checkup (6:00-23:59, cada 30 min)
*/30 6-23 * * * ./deployment/run_checkup.sh

# 3. Integrity Check (diário às 6:00)
0 6 * * * ./deployment/run_integrity_check.sh

# 4. Data Export (diário às 6:30)
30 6 * * * ./deployment/run_data_export.sh
```

**Documentação**: Ver [Scripts README](../../scripts/README.md)

---

## 🔗 Próximos Passos

- [Visão Geral da Arquitetura](./OVERVIEW.md)
- [Sistema de Administradores](./ADMIN_SYSTEM.md)
- [Documentação Principal](../../README.md)
