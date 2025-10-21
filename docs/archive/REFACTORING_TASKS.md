# 🔧 Plano de Refatoração - Sentinela Bot

**Branch:** `fix/critical-architecture-issues`
**Data de Criação:** 09/10/2025
**Baseado em:** Análise completa de arquitetura e código

---

## 📊 Contexto da Análise

Este documento detalha as tasks necessárias para corrigir problemas críticos identificados durante auditoria completa do código. O projeto está **funcional** mas apresenta **débito técnico** acumulado durante migração incompleta para Clean Architecture + DDD.

### Estatísticas da Análise:
- **Arquivos Python analisados:** ~140
- **Código morto identificado:** 43% dos Use Cases (6 de 14)
- **Problemas críticos:** 5
- **Problemas médios:** 3
- **Arquivo mais problemático:** `telegram_bot_handler.py` (2.284 linhas, 102KB)

---

## 🔴 FASE 1: CORREÇÕES CRÍTICAS (Urgente)

### TASK-001: Commitar Mudanças Pendentes da Refatoração

**Prioridade:** 🔴 **CRÍTICA** (Bloqueante)
**Estimativa:** 15 minutos
**Arquivo:** `.git/index`

#### O QUE FAZER:

Commitar arquivos deletados da refatoração anterior que ainda aparecem no `git status`:

```bash
git add src/sentinela/application/command_handlers/admin_command_handlers.py
git add src/sentinela/application/use_cases/admin_operations_use_case.py
git add src/sentinela/domain/entities/ticket.py
git add src/sentinela/domain/repositories/ticket_repository.py
git add src/sentinela/infrastructure/repositories/sqlite_ticket_repository.py
git add src/sentinela/application/commands/admin_commands.py
git add src/sentinela/infrastructure/config/dependency_injection.py
git add src/sentinela/infrastructure/repositories/sqlite_user_repository.py
git add src/sentinela/presentation/handlers/telegram_bot_handler.py
git add src/sentinela/presentation/telegram_bot_new.py

git commit -m "chore: Remove código morto da refatoração anterior

- Remove entidade Ticket (substituída por integração direta com HubSoft)
- Remove admin_command_handlers duplicado
- Remove admin_operations_use_case não utilizado
- Atualiza dependency_injection.py
- Atualiza sqlite_user_repository.py
- Atualiza telegram_bot_handler.py e telegram_bot_new.py"
```

#### POR QUE FAZER:

1. **Claridade:** Git status mostra mudanças pendentes que confundem o estado do repo
2. **Bloqueante:** Precisamos de um ponto de partida limpo para próximas correções
3. **Rastreabilidade:** Documenta a remoção de código morto
4. **Evita conflitos:** Previne merge conflicts futuros

#### ANÁLISE DETALHADA:

**Arquivos deletados identificados:**
- `ticket.py` e `ticket_repository.py` - Eram duplicados, funcionalidade agora está no HubSoft
- `admin_command_handlers.py` - Handlers foram consolidados em `telegram_bot_handler.py`
- `admin_operations_use_case.py` - Use case não estava registrado no DI Container

**Impacto da não-correção:**
- Confusão sobre o estado real do código
- Dificuldade em entender o que está ativo vs deletado
- Git history poluído

---

### TASK-002: Corrigir Bug Crítico de Verificação de Usuário

**Prioridade:** 🔴 **CRÍTICA** (Segurança)
**Estimativa:** 1 hora
**Arquivo:** `src/sentinela/presentation/handlers/telegram_bot_handler.py:1247-1259`

#### O QUE FAZER:

Substituir lógica incorreta de verificação de usuário:

**ANTES (❌ INCORRETO):**
```python
# Linha 1247-1259
status_info = await self._get_verification_status_message(user.id)
if not status_info["is_verified"]:
    # Se está aguardando CPF (PENDING ou IN_PROGRESS), seta flag
    from ...domain.entities.cpf_verification import VerificationStatus
    if status_info["status"] in [VerificationStatus.PENDING.value, VerificationStatus.IN_PROGRESS.value]:
        context.user_data['waiting_cpf'] = True
        logger.debug(f"Flag waiting_cpf setado para usuário {user.id}")

    await update.message.reply_text(
        status_info["message"],
        parse_mode='Markdown'
    )
    return
```

**DEPOIS (✅ CORRETO):**
```python
# Usar _check_user_verified() para decisão binária
is_verified = await self._check_user_verified(user.id)

if not is_verified:
    # Agora sim, pega a mensagem contextualizada
    status_info = await self._get_verification_status_message(user.id)

    # Se está aguardando CPF, seta flag
    from ...domain.entities.cpf_verification import VerificationStatus
    if status_info["status"] in [VerificationStatus.PENDING.value, VerificationStatus.IN_PROGRESS.value]:
        context.user_data['waiting_cpf'] = True
        logger.debug(f"Flag waiting_cpf setado para usuário {user.id}")

    await update.message.reply_text(
        status_info["message"],
        parse_mode='Markdown'
    )
    return

# Usuário ACTIVE → resposta padrão
message = (
    "💬 Mensagem recebida!\n\n"
    "Para criar um atendimento, use /suporte\n"
    "Para verificar status, use /status\n\n"
    "📋 Digite /ajuda para ver todos os comandos."
)
await update.message.reply_text(message)
```

#### POR QUE FAZER:

1. **Falha de Segurança:** Usuários com CPF `COMPLETED` mas sem plano `ACTIVE` conseguem acessar funcionalidades restritas
2. **Lógica Incorreta:** `_get_verification_status_message()` é para **mensagens**, não para **decisões de acesso**
3. **Violação de Regra de Negócio:** Um usuário pode ter:
   - CPF verificado (`COMPLETED`) ✅
   - Mas plano cancelado ou sincronização falhou ❌
   - Resultado: `status = ACTIVE` falso negativo

#### ANÁLISE DETALHADA:

**Diferença entre as funções:**

| Função | Propósito | Retorno | Quando Usar |
|--------|-----------|---------|-------------|
| `_check_user_verified()` | Decisão binária de acesso | `bool` (True/False) | Para **controle de acesso** |
| `_get_verification_status_message()` | Mensagem contextualizada | `dict` com mensagem | Para **feedback ao usuário** |

**Exemplo do problema:**

```python
# Cenário: Usuário com CPF verificado mas plano cancelado
user.cpf_verification.status = "COMPLETED"  # ✅
user.status = "INACTIVE"                     # ❌ Plano cancelado

# Função INCORRETA (_get_verification_status_message):
status_info["is_verified"] = True  # ✅ Retorna True (tem COMPLETED)
# BUG: Usuário SEM plano ativo passa pela validação!

# Função CORRETA (_check_user_verified):
is_verified = False  # ❌ Retorna False (verifica status ACTIVE no User)
# ✅ Corretamente bloqueia o acesso
```

**Impacto da não-correção:**
- Usuários sem plano ativo podem criar tickets
- Acesso indevido a funcionalidades pagas
- Violação de regras de negócio da OnCabo

**Testes necessários após correção:**
1. ✅ Usuário `COMPLETED` + `ACTIVE` → deve passar
2. ❌ Usuário `COMPLETED` + `INACTIVE` → deve bloquear
3. ❌ Usuário `PENDING` → deve bloquear
4. ❌ Usuário sem verificação → deve bloquear

---

### TASK-003: Resolver Referências Órfãs em `support_form_use_case.py`

**Prioridade:** 🔴 **CRÍTICA** (Crash em Runtime)
**Estimativa:** 30 minutos
**Arquivo:** `src/sentinela/application/use_cases/support_form_use_case.py`

#### O QUE FAZER:

**Opção A (Recomendada): DELETAR o arquivo**

```bash
git rm src/sentinela/application/use_cases/support_form_use_case.py
git commit -m "refactor: Remove support_form_use_case.py (código morto)

- Arquivo referencia entidades deletadas (Ticket, TicketRepository)
- Funcionalidade já implementada diretamente em telegram_bot_handler.py
- Use case não está registrado no DI Container
- Não há dependências ativas deste arquivo"
```

**Opção B (Se funcionalidade for necessária): MIGRAR**

1. Remover imports de entidades deletadas:
```python
# ❌ REMOVER
from ...domain.repositories.ticket_repository import TicketRepository
from ...domain.entities.ticket import Ticket, TicketAttachment
```

2. Atualizar para usar integração HubSoft direta:
```python
# ✅ ADICIONAR
from ...application.use_cases.hubsoft_integration_use_case import HubSoftIntegrationUseCase
```

3. Registrar no DI Container (`dependency_injection.py`)

#### POR QUE FAZER:

1. **Import Error:** Arquivo tenta importar entidades que **não existem mais**
2. **Crash Garantido:** Qualquer tentativa de usar `SupportFormUseCase` resulta em `ModuleNotFoundError`
3. **Código Morto Perigoso:** Arquivo existe mas não pode funcionar

#### ANÁLISE DETALHADA:

**Referências órfãs identificadas:**

```python
# Linha 15-17 (❌ ERRO)
from ...domain.repositories.ticket_repository import TicketRepository
from ...domain.entities.ticket import Ticket, TicketAttachment

# Status no Git:
# D src/sentinela/domain/entities/ticket.py
# D src/sentinela/domain/repositories/ticket_repository.py
# D src/sentinela/infrastructure/repositories/sqlite_ticket_repository.py
```

**Dependências deste arquivo:**

```bash
$ grep -r "SupportFormUseCase" src/
src/sentinela/application/use_cases/support_form_use_case.py:class SupportFormUseCase(UseCase):
src/sentinela/application/commands/start_support_conversation_handler.py:from ...application.use_cases.support_form_use_case import SupportFormUseCase
```

**Conclusão da análise:**
- ❌ **NÃO está registrado no DI Container**
- ❌ **NÃO é usado em `telegram_bot_handler.py`** (handler principal)
- ⚠️ É importado em `start_support_conversation_handler.py` (mas handler não é usado)

**Decisão recomendada:** **DELETAR** (Opção A)

**Razões:**
1. Funcionalidade de suporte já implementada em `telegram_bot_handler.py` (linhas 571-1100)
2. Use Case não está no DI Container = código morto
3. Entidades que ele depende foram deletadas na refatoração
4. Manter o arquivo requer reescrever toda lógica

**Impacto da não-correção:**
- Crash se alguém tentar usar `SupportFormUseCase`
- Confusão sobre qual código usar para formulário de suporte
- Imports quebrados poluem o código

---

### TASK-004: Dividir `telegram_bot_handler.py` - FASE 1 (Extrair Lógica de CPF)

**Prioridade:** 🔴 **CRÍTICA** (God Object)
**Estimativa:** 4-6 horas
**Arquivo:** `src/sentinela/presentation/handlers/telegram_bot_handler.py`

#### O QUE FAZER:

Criar novo handler especializado para verificação de CPF:

**1. Criar arquivo:** `src/sentinela/presentation/handlers/cpf_verification_handler.py`

```python
"""
Handler especializado para verificação de CPF via Telegram.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from ...application.use_cases.cpf_verification_use_case import CPFVerificationUseCase
from ...infrastructure.config.dependency_injection import get_container

logger = logging.getLogger(__name__)


class CPFVerificationHandler:
    """Handler para fluxo de verificação de CPF."""

    def __init__(self, container=None):
        self._container = container or get_container()
        self._cpf_use_case = None

    async def _ensure_initialized(self):
        """Garante que use cases estão inicializados."""
        if not self._cpf_use_case:
            self._cpf_use_case = self._container.get("cpf_verification_use_case")

    async def handle_cpf_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        cpf_text: str
    ) -> bool:
        """
        Processa entrada de CPF do usuário.

        Args:
            update: Update do Telegram
            context: Context do bot
            cpf_text: CPF digitado pelo usuário

        Returns:
            bool: True se CPF foi processado com sucesso
        """
        await self._ensure_initialized()
        user = update.effective_user

        # Delega para CPFVerificationUseCase
        # ... (extrair lógica das linhas 1045-1180 do telegram_bot_handler.py)

    async def start_verification_flow(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Inicia fluxo de verificação de CPF."""
        await self._ensure_initialized()

        # Delega para CPFVerificationUseCase
        # ... (extrair lógica de _start_welcome_flow)

    async def check_user_verified(self, user_id: int) -> bool:
        """
        Verifica se usuário está ativo e verificado.

        Args:
            user_id: ID do usuário Telegram

        Returns:
            bool: True se usuário está ativo
        """
        await self._ensure_initialized()

        # Delega para CPFVerificationUseCase
        # ... (extrair _check_user_verified)

    async def get_verification_status_message(self, user_id: int) -> dict:
        """
        Obtém mensagem contextualizada do status de verificação.

        Args:
            user_id: ID do usuário

        Returns:
            dict: {"is_verified": bool, "status": str, "message": str}
        """
        await self._ensure_initialized()

        # Delega para CPFVerificationUseCase
        # ... (extrair _get_verification_status_message)
```

**2. Atualizar `telegram_bot_handler.py`:**

```python
# Adicionar import
from .cpf_verification_handler import CPFVerificationHandler

class TelegramBotHandler:
    def __init__(self, container=None):
        # ...
        self._cpf_handler = CPFVerificationHandler(container)

    # Substituir chamadas diretas por delegação:
    async def _check_user_verified(self, user_id: int) -> bool:
        return await self._cpf_handler.check_user_verified(user_id)

    async def _get_verification_status_message(self, user_id: int) -> dict:
        return await self._cpf_handler.get_verification_status_message(user_id)

    # ... (manter assinatura dos métodos mas delegar implementação)
```

**3. Mover testes relacionados:**

```bash
# Se houver testes de CPF, mover para arquivo separado
mv tests/test_cpf_verification_in_handler.py tests/test_cpf_verification_handler.py
```

#### POR QUE FAZER:

1. **Complexidade Reduzida:** `telegram_bot_handler.py` tem 2.284 linhas (deve ter <500)
2. **Single Responsibility:** Handler deve **coordenar**, não **implementar**
3. **Testabilidade:** Handlers especializados são mais fáceis de testar
4. **Manutenibilidade:** Mudanças em CPF não afetam outras funcionalidades

#### ANÁLISE DETALHADA:

**Métodos a extrair do `telegram_bot_handler.py`:**

| Método | Linhas | Responsabilidade | Destino |
|--------|--------|------------------|---------|
| `_check_user_verified()` | 138-173 | Verifica se usuário está ACTIVE | `CPFVerificationHandler` |
| `_get_verification_status_message()` | 175-253 | Monta mensagem contextualizada | `CPFVerificationHandler` |
| `_start_welcome_flow()` | 255-419 | Inicia fluxo de boas-vindas + CPF | `CPFVerificationHandler` |
| `_handle_cpf_input()` | 1045-1180 | Processa CPF digitado | `CPFVerificationHandler` |
| `_user_already_interacted()` | (não encontrado) | Verifica primeira interação | `CPFVerificationHandler` |

**Total de linhas a extrair:** ~600 linhas

**Benefícios mensuráveis:**
- ✅ `telegram_bot_handler.py`: 2.284 → ~1.684 linhas (-26%)
- ✅ `CPFVerificationHandler`: novo arquivo com ~600 linhas
- ✅ Testabilidade: 1 arquivo testável vs método privado

**Padrão de extração:**

```
telegram_bot_handler.py (God Object)
         ↓
    [EXTRAIR]
         ↓
┌─────────────────────────────┐
│ telegram_bot_handler.py     │ ← Coordenador (thin wrapper)
│ - Recebe updates Telegram   │
│ - Delega para handlers      │
│ - Mantém assinatura pública │
└─────────────────────────────┘
         ↓ delega para
┌─────────────────────────────┐
│ CPFVerificationHandler      │ ← Especialista
│ - Lógica de verificação CPF │
│ - Usa CPFVerificationUseCase│
│ - Retorna resultados        │
└─────────────────────────────┘
```

**Impacto da não-correção:**
- Arquivo continua crescendo (já está em 2.284 linhas)
- Bugs em CPF podem afetar outras funcionalidades
- Impossível testar isoladamente
- Viola SOLID (Single Responsibility Principle)

**Riscos da refatoração:**
- ⚠️ **Médio:** Quebrar fluxo de verificação se não testar bem
- ⚠️ **Baixo:** Perder estado de conversação (mitigado por design stateless)

**Mitigação de riscos:**
1. ✅ Manter assinatura dos métodos públicos
2. ✅ Criar testes antes de extrair
3. ✅ Fazer extração incremental (um método por vez)
4. ✅ Testar fluxo completo após cada extração

---

### TASK-005: Dividir `telegram_bot_handler.py` - FASE 2 (Extrair Lógica de Suporte)

**Prioridade:** 🔴 **CRÍTICA** (God Object)
**Estimativa:** 6-8 horas
**Arquivo:** `src/sentinela/presentation/handlers/telegram_bot_handler.py`

#### O QUE FAZER:

Criar novo handler especializado para formulário de suporte:

**1. Criar arquivo:** `src/sentinela/presentation/handlers/support_form_handler.py`

```python
"""
Handler especializado para formulário de suporte via Telegram.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ...application.use_cases.hubsoft_integration_use_case import HubSoftIntegrationUseCase
from ...infrastructure.config.dependency_injection import get_container

logger = logging.getLogger(__name__)


class SupportFormHandler:
    """Handler para fluxo de criação de tickets de suporte."""

    def __init__(self, container=None):
        self._container = container or get_container()
        self._hubsoft_use_case = None

    async def _ensure_initialized(self):
        """Garante que use cases estão inicializados."""
        if not self._hubsoft_use_case:
            self._hubsoft_use_case = self._container.get("hubsoft_integration_use_case")

    async def handle_suporte_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Inicia fluxo de criação de ticket.

        Args:
            update: Update do Telegram
            context: Context do bot
        """
        await self._ensure_initialized()

        # Delega para HubSoftIntegrationUseCase
        # ... (extrair lógica das linhas 571-800 do telegram_bot_handler.py)

    async def handle_support_callback(
        self,
        query,
        callback_data: str,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Processa callbacks do formulário de suporte.

        Args:
            query: CallbackQuery do Telegram
            callback_data: Dados do callback
            context: Context do bot
        """
        await self._ensure_initialized()

        # Router de callbacks:
        # - sup_cat_* → Seleção de categoria
        # - sup_game_* → Seleção de jogo
        # - sup_timing_* → Seleção de timing
        # - sup_desc → Descrição
        # - sup_attach_* → Anexos
        # - sup_confirm → Confirmação
        # ... (extrair lógica das linhas 800-1100 do telegram_bot_handler.py)

    async def handle_description_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        description: str
    ):
        """Processa entrada de descrição do problema."""
        await self._ensure_initialized()
        # ...

    async def handle_photo_attachment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Processa anexo de foto."""
        await self._ensure_initialized()
        # ...
```

**2. Atualizar `telegram_bot_handler.py`:**

```python
from .support_form_handler import SupportFormHandler

class TelegramBotHandler:
    def __init__(self, container=None):
        # ...
        self._support_handler = SupportFormHandler(container)

    async def handle_suporte_command(self, update, context):
        """Delega para SupportFormHandler."""
        return await self._support_handler.handle_suporte_command(update, context)

    async def handle_callback_query(self, update, context):
        """Router de callbacks."""
        query = update.callback_query
        callback_data = query.data

        # Callbacks de suporte → delega
        if callback_data.startswith("sup_"):
            return await self._support_handler.handle_support_callback(
                query, callback_data, context
            )

        # Outros callbacks → mantém aqui
        # ...
```

#### POR QUE FAZER:

1. **Responsabilidade Única:** Formulário de suporte é domínio completo separado
2. **Redução Massiva:** Remove ~800 linhas do handler principal
3. **Isolamento de Bugs:** Bugs no formulário não afetam verificação/admin
4. **Reusabilidade:** Handler pode ser usado por outros bots

#### ANÁLISE DETALHADA:

**Métodos a extrair:**

| Método/Seção | Linhas | Responsabilidade | Complexidade |
|--------------|--------|------------------|--------------|
| `handle_suporte_command()` | 571-650 | Inicia formulário | Média |
| Callbacks `sup_cat_*` | 651-720 | Seleção de categoria | Baixa |
| Callbacks `sup_game_*` | 721-790 | Seleção de jogo | Baixa |
| Callbacks `sup_timing_*` | 791-850 | Seleção de timing | Baixa |
| Callbacks `sup_desc` | 851-920 | Entrada de descrição | Média |
| Callbacks `sup_attach_*` | 921-1000 | Gerenciamento de anexos | Alta |
| Callbacks `sup_confirm` | 1001-1080 | Confirmação e criação | Alta |
| `handle_photo_message()` | 1277-1310 | Processa foto durante form | Média |

**Total de linhas a extrair:** ~800 linhas

**Estado do formulário (context.user_data):**

```python
# Estado mantido no context.user_data durante formulário:
support_state = {
    'state': SupportState,          # Enum: CATEGORY, GAME, TIMING, etc
    'current_step': int,             # 1-6
    'category': str,                 # connectivity, performance, etc
    'game': str,                     # valorant, lol, etc
    'custom_game_name': str,         # Se "outro jogo"
    'timing': str,                   # now, hours_ago, etc
    'description': str,              # Descrição do problema
    'attachments': [                 # Lista de anexos
        {'file_id': str, 'type': str, 'size': int}
    ]
}
```

**Fluxo completo do formulário:**

```
┌────────────────┐
│ /suporte       │
│ (comando)      │
└───────┬────────┘
        │
        ▼
┌────────────────────┐
│ 1. Categoria       │ sup_cat_connectivity
│ (6 opções)         │ sup_cat_performance, etc
└───────┬────────────┘
        │
        ▼
┌────────────────────┐
│ 2. Jogo            │ sup_game_valorant
│ (10+ jogos)        │ sup_game_lol, etc
└───────┬────────────┘
        │
        ▼
┌────────────────────┐
│ 3. Timing          │ sup_timing_now
│ (quando começou)   │ sup_timing_hours_ago, etc
└───────┬────────────┘
        │
        ▼
┌────────────────────┐
│ 4. Descrição       │ (texto livre)
│ (texto do problema)│
└───────┬────────────┘
        │
        ▼
┌────────────────────┐
│ 5. Anexos          │ sup_attach_add
│ (0-3 fotos)        │ sup_attach_skip
└───────┬────────────┘
        │
        ▼
┌────────────────────┐
│ 6. Confirmação     │ sup_confirm_yes
│ (revisar dados)    │ sup_confirm_edit, sup_cancel
└───────┬────────────┘
        │
        ▼
┌────────────────────┐
│ Ticket Criado!     │
│ (protocolo: HS-XXX)│
└────────────────────┘
```

**Benefícios mensuráveis:**
- ✅ `telegram_bot_handler.py`: 1.684 → ~884 linhas (-47%)
- ✅ `SupportFormHandler`: novo arquivo com ~800 linhas
- ✅ Testabilidade: Formulário pode ser testado isoladamente
- ✅ Manutenção: Mudanças no form não afetam resto do bot

**Após TASK-004 e TASK-005:**

```
telegram_bot_handler.py (ANTES)
├── 2.284 linhas
├── 102KB
├── 38 métodos
└── Responsabilidades:
    ├── Verificação CPF (~600 linhas)
    ├── Formulário Suporte (~800 linhas)
    ├── Admin Commands (~400 linhas)
    └── Comandos gerais (~484 linhas)

            ↓ APÓS REFATORAÇÃO

telegram_bot_handler.py (DEPOIS)
├── ~884 linhas (-61%)
├── ~40KB
├── ~18 métodos
└── Responsabilidades:
    ├── Coordenação geral
    ├── Admin Commands (~400 linhas)
    └── Comandos gerais (~484 linhas)

cpf_verification_handler.py (NOVO)
├── ~600 linhas
└── Verificação CPF especializada

support_form_handler.py (NOVO)
├── ~800 linhas
└── Formulário de suporte especializado
```

**Impacto da não-correção:**
- Arquivo continua como "God Object" ingerenciável
- Bugs no formulário afetam todo o bot
- Testes complexos e frágeis
- Novos desenvolvedores levam dias para entender o arquivo

---

## 🟡 FASE 2: LIMPEZA E ORGANIZAÇÃO

### TASK-006: Implementar ou Deletar Repositórios Órfãos

**Prioridade:** 🟡 **MÉDIA**
**Estimativa:** 3-4 horas (se implementar) / 30 min (se deletar)
**Arquivos:**
- `src/sentinela/domain/repositories/support_conversation_repository.py`
- `src/sentinela/domain/repositories/group_topic_repository.py`

#### O QUE FAZER:

**Decisão 1: `SupportConversationRepository`**

Este repositório é usado por `support_form_use_case.py` (que é código morto - ver TASK-003).

**Opção A (Recomendada): DELETAR**
```bash
git rm src/sentinela/domain/repositories/support_conversation_repository.py
git rm src/sentinela/domain/entities/support_conversation.py  # se não usado
git commit -m "refactor: Remove SupportConversationRepository (não utilizado)"
```

**Opção B: IMPLEMENTAR (se funcionalidade for necessária)**

```python
# Criar: src/sentinela/infrastructure/repositories/sqlite_support_conversation_repository.py

from ...domain.repositories.support_conversation_repository import SupportConversationRepository
from ...domain.entities.support_conversation import SupportConversation
import aiosqlite
import logging

logger = logging.getLogger(__name__)


class SQLiteSupportConversationRepository(SupportConversationRepository):
    """Implementação SQLite do repositório de conversas de suporte."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._initialized = False

    async def _ensure_table(self):
        """Cria tabela se não existir."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS support_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    current_step TEXT,
                    form_data TEXT,  -- JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            await db.commit()
        self._initialized = True

    async def save(self, conversation: SupportConversation):
        """Salva ou atualiza conversa."""
        if not self._initialized:
            await self._ensure_table()

        async with aiosqlite.connect(self._db_path) as db:
            # ...implementação

    async def find_active_by_user(self, user_id):
        """Busca conversa ativa do usuário."""
        # ...implementação

    # ... outros métodos
```

**Decisão 2: `GroupTopicRepository`**

Este repositório é usado por `topic_management_use_case.py` (não está no DI Container).

**Análise de uso:**
```bash
$ grep -r "GroupTopicRepository" src/
src/sentinela/domain/repositories/group_topic_repository.py:class GroupTopicRepository(ABC):
src/sentinela/application/use_cases/topic_management_use_case.py:from ...domain.repositories.group_topic_repository import GroupTopicRepository
```

**Opção A (Recomendada): DELETAR**
```bash
# Apenas se TopicManagementUseCase não for necessário
git rm src/sentinela/domain/repositories/group_topic_repository.py
git rm src/sentinela/application/use_cases/topic_management_use_case.py
```

**Opção B: IMPLEMENTAR**
```python
# Criar: src/sentinela/infrastructure/repositories/sqlite_group_topic_repository.py
# Estrutura similar ao exemplo acima
```

#### POR QUE FAZER:

1. **Integridade Arquitetural:** Clean Architecture exige implementação para cada interface
2. **Evita Confusão:** Desenvolvedores tentam usar interface mas falha em runtime
3. **DRY (Don't Repeat Yourself):** Se não é usado, não deve existir

#### ANÁLISE DETALHADA:

**Repositórios no projeto:**

| Repository (Interface) | Implementação SQLite | Registrado no DI | Status |
|------------------------|---------------------|------------------|--------|
| `UserRepository` | ✅ `SQLiteUserRepository` | ✅ | 🟢 OK |
| `AdminRepository` | ✅ `SQLiteAdminRepository` | ✅ | 🟢 OK |
| `CPFVerificationRepository` | ✅ `SQLiteCPFVerificationRepository` | ✅ | 🟢 OK |
| `HubSoftIntegrationRepository` | ✅ `SQLiteHubSoftIntegrationRepository` | ✅ | 🟢 OK |
| `GroupMemberRepository` | ✅ `SQLiteGroupMemberRepository` | ✅ | 🟢 OK |
| `SupportConversationRepository` | ❌ **FALTANDO** | ❌ | 🔴 ÓRFÃO |
| `GroupTopicRepository` | ❌ **FALTANDO** | ❌ | 🔴 ÓRFÃO |

**Decisão recomendada:**

Para ambos: **DELETAR** (Opção A)

**Razões:**
1. `SupportConversationRepository`:
   - Usado apenas por `support_form_use_case.py` (código morto - TASK-003)
   - Funcionalidade de formulário já implementada diretamente em handler
   - Estado do formulário mantido em `context.user_data` (não precisa persistir)

2. `GroupTopicRepository`:
   - Usado apenas por `topic_management_use_case.py` (não registrado no DI)
   - Funcionalidade de tópicos não parece ser usada no bot
   - Nenhuma referência em `telegram_bot_handler.py`

**Se decidir IMPLEMENTAR:**
- Criar tabelas SQL correspondentes
- Registrar no DI Container
- Criar testes unitários
- Atualizar documentação

**Impacto da não-correção:**
- Interfaces órfãs confundem arquitetura
- Promessa não cumprida (interface existe mas não funciona)
- Violação dos princípios SOLID

---

### TASK-007: Avaliar e Decidir sobre Use Cases Não Utilizados

**Prioridade:** 🟡 **MÉDIA**
**Estimativa:** 2-3 horas (análise) + tempo de implementação (variável)
**Arquivos:** 6 Use Cases não registrados no DI Container

#### O QUE FAZER:

Para cada Use Case, seguir processo de decisão:

```
1. AVALIAR necessidade funcional
   ├─ Funcionalidade existe no bot? → IR PARA 2
   └─ Funcionalidade não existe? → IR PARA 3

2. FUNCIONALIDADE EXISTE
   ├─ Implementada em outro lugar? → DELETAR Use Case duplicado
   └─ Use Case está correto mas não registrado? → REGISTRAR no DI

3. FUNCIONALIDADE NÃO EXISTE
   ├─ É necessária para o negócio? → IMPLEMENTAR completamente
   └─ Não é necessária? → DELETAR (mover para _archive/ se houver valor histórico)
```

#### ANÁLISE DETALHADA:

**Use Case 1: `SupportFormUseCase`**

```python
# Arquivo: src/sentinela/application/use_cases/support_form_use_case.py
# Linhas: 547
# Última modificação: (checar git log)
```

**Status:** ❌ **DELETAR** (já decidido em TASK-003)

**Razões:**
- Referências órfãs (importa entidades deletadas)
- Funcionalidade já implementada em `telegram_bot_handler.py`
- Não registrado no DI Container

---

**Use Case 2: `GamingSupportUseCase`**

```python
# Arquivo: src/sentinela/application/use_cases/gaming_support_use_case.py
# Propósito: Diagnóstico de problemas de gaming (ping, FPS, etc)
```

**Análise:**
- ✅ **Domínio válido:** Diagnóstico é core business do bot
- ❓ **Implementação:** Verificar se está sendo usado indiretamente
- 🔍 **Buscar referências:**

```bash
$ grep -r "GamingSupportUseCase" src/
# Se retornar vazio → Não está sendo usado
```

**Decisão recomendada:**
- Se contém lógica de diagnóstico útil → **MIGRAR** para `HubSoftIntegrationUseCase`
- Se é duplicado → **DELETAR**
- Se é futuro → **MOVER** para `_future_features/`

---

**Use Case 3: `GroupManagementUseCase`**

```python
# Arquivo: src/sentinela/application/use_cases/group_management_use_case.py
# Propósito: Gerenciamento de membros do grupo Telegram
```

**Análise:**
- ✅ **Funcionalidade existe:** Bot adiciona membros verificados ao grupo
- ❓ **Onde está implementado:** Verificar em `telegram_bot_handler.py`

```bash
$ grep -n "group_id\|add.*member\|ban.*user" src/sentinela/presentation/handlers/telegram_bot_handler.py
```

**Decisão recomendada:**
- Se lógica está em handler → **REGISTRAR** Use Case e refatorar handler
- Se não está sendo usado → **AVALIAR** necessidade com time de produto

---

**Use Case 4: `InviteManagementUseCase`**

```python
# Arquivo: src/sentinela/application/use_cases/invite_management_use_case.py
# Propósito: Gerenciamento de links de convite
```

**Análise:**
- 🔍 **Verificar repositório:** `GroupInviteRepository` está registrado?

```bash
$ grep "GroupInviteRepository\|invite" src/sentinela/infrastructure/config/dependency_injection.py
```

**Decisão recomendada:**
- Se repositório existe e está registrado → **REGISTRAR** Use Case também
- Se não há repositório → **DELETAR** (funcionalidade incompleta)

---

**Use Case 5: `PermissionManagementUseCase`**

```python
# Arquivo: src/sentinela/application/use_cases/permission_management_use_case.py
# Propósito: Controle de permissões (admin, moderador, etc)
```

**Análise:**
- ❓ **Funcionalidade existe:** Bot tem comandos admin?
- 🔍 **Verificar:**

```bash
$ grep -n "admin\|permission\|is_admin" src/sentinela/presentation/handlers/telegram_bot_handler.py
```

**Decisão recomendada:**
- Se há lógica de admin no handler → **REGISTRAR** e refatorar
- Se não há controle de permissões → **AVALIAR** necessidade

---

**Use Case 6: `TechNotificationUseCase`**

```python
# Arquivo: src/sentinela/application/use_cases/tech_notification_use_case.py
# Propósito: Notificar técnicos sobre novos tickets
```

**Análise:**
- ✅ **Funcionalidade crítica:** Técnicos precisam ser notificados
- ❓ **Onde está implementado:** Provavelmente em event handlers

```bash
$ grep -r "notif.*tech\|técnico\|technician" src/sentinela/infrastructure/events/
```

**Decisão recomendada:**
- Se está em event handler → **OK**, manter separado
- Se Use Case tem lógica útil → **REGISTRAR** e integrar com events
- Se não está implementado → **IMPLEMENTAR** (funcionalidade crítica!)

---

**Use Case 7: `TopicManagementUseCase`**

```python
# Arquivo: src/sentinela/application/use_cases/topic_management_use_case.py
# Propósito: Gerenciamento de tópicos do grupo Telegram
```

**Análise:**
- ❓ **Bot usa tópicos:** Grupo Telegram tem tópicos configurados?
- 🔍 **Verificar:** `TELEGRAM_GROUP_ID`, `WELCOME_TOPIC_ID`, etc em config

**Decisão recomendada:**
- Se grupo usa tópicos → **IMPLEMENTAR** repositório e registrar
- Se não usa tópicos → **DELETAR** (funcionalidade não necessária)

---

#### TEMPLATE DE DECISÃO:

Para cada Use Case, preencher:

```markdown
## Use Case: [Nome]

**Funcionalidade:** [Descrição]

**Análise:**
- [ ] Funcionalidade existe no bot? (Sim/Não/Parcial)
- [ ] Está implementada em outro lugar? (Local)
- [ ] É necessária para o negócio? (Sim/Não)
- [ ] Dependências estão completas? (Repositórios, Services, etc)

**Decisão:** [REGISTRAR / DELETAR / IMPLEMENTAR / MIGRAR]

**Razão:** [Justificativa da decisão]

**Ação imediata:**
```bash
# Comandos para executar a decisão
```

**Estimativa:** [Tempo necessário]
```

#### POR QUE FAZER:

1. **Clareza Arquitetural:** Saber o que é código morto vs funcionalidade futura
2. **Redução de Débito Técnico:** Deletar código não usado
3. **Planejamento:** Se funcionalidade é necessária, planejar implementação
4. **Documentação:** Decisões documentadas evitam refazer análise

**Impacto da não-correção:**
- 43% de código morto (6 de 14 Use Cases)
- Confusão sobre o que está ativo
- Manutenção de código inútil
- Falsa impressão de funcionalidades implementadas

---

### TASK-008: Criar Testes para Handlers Críticos

**Prioridade:** 🟡 **MÉDIA** (mas importante para sustentabilidade)
**Estimativa:** 6-8 horas
**Arquivos:** Criar estrutura de testes

#### O QUE FAZER:

**1. Criar estrutura de testes:**

```bash
mkdir -p tests/unit/handlers
mkdir -p tests/integration
mkdir -p tests/fixtures
```

**2. Criar testes unitários para `CPFVerificationHandler`:**

```python
# tests/unit/handlers/test_cpf_verification_handler.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.sentinela.presentation.handlers.cpf_verification_handler import CPFVerificationHandler
from src.sentinela.domain.entities.user import UserStatus


@pytest.fixture
def mock_container():
    """Mock do DI Container."""
    container = MagicMock()
    cpf_use_case = AsyncMock()
    container.get.return_value = cpf_use_case
    return container


@pytest.fixture
def handler(mock_container):
    """Instância do handler com container mockado."""
    return CPFVerificationHandler(container=mock_container)


class TestCPFVerificationHandler:
    """Testes do CPFVerificationHandler."""

    @pytest.mark.asyncio
    async def test_check_user_verified_active_user_returns_true(self, handler, mock_container):
        """Usuário ACTIVE deve retornar True."""
        # Arrange
        user_id = 123456
        mock_use_case = mock_container.get.return_value
        mock_use_case.check_user_active.return_value = True

        # Act
        result = await handler.check_user_verified(user_id)

        # Assert
        assert result is True
        mock_use_case.check_user_active.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_check_user_verified_inactive_user_returns_false(self, handler, mock_container):
        """Usuário INACTIVE deve retornar False."""
        # Arrange
        user_id = 123456
        mock_use_case = mock_container.get.return_value
        mock_use_case.check_user_active.return_value = False

        # Act
        result = await handler.check_user_verified(user_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_user_verified_completed_cpf_but_inactive_returns_false(self, handler, mock_container):
        """
        TESTE CRÍTICO: Usuário com CPF COMPLETED mas status INACTIVE
        deve retornar False (não permitir acesso).

        Este é o bug identificado na TASK-002.
        """
        # Arrange
        user_id = 123456
        mock_use_case = mock_container.get.return_value

        # Simula usuário com CPF verificado mas plano cancelado
        mock_user = MagicMock()
        mock_user.cpf_verification.status = "COMPLETED"
        mock_user.status = UserStatus.INACTIVE

        mock_use_case.get_user.return_value = mock_user
        mock_use_case.check_user_active.return_value = False  # Deve verificar status ACTIVE

        # Act
        result = await handler.check_user_verified(user_id)

        # Assert
        assert result is False, "Usuário INACTIVE não deve ter acesso, mesmo com CPF COMPLETED"

    @pytest.mark.asyncio
    async def test_get_verification_status_message_pending_returns_correct_message(self, handler):
        """Status PENDING deve retornar mensagem de aguardando CPF."""
        # ...

    @pytest.mark.asyncio
    async def test_handle_cpf_input_valid_cpf_starts_verification(self, handler):
        """CPF válido deve iniciar processo de verificação."""
        # ...

    @pytest.mark.asyncio
    async def test_handle_cpf_input_invalid_cpf_returns_error(self, handler):
        """CPF inválido deve retornar mensagem de erro."""
        # ...
```

**3. Criar testes unitários para `SupportFormHandler`:**

```python
# tests/unit/handlers/test_support_form_handler.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.sentinela.presentation.handlers.support_form_handler import SupportFormHandler


@pytest.fixture
def handler(mock_container):
    return SupportFormHandler(container=mock_container)


class TestSupportFormHandler:
    """Testes do SupportFormHandler."""

    @pytest.mark.asyncio
    async def test_handle_suporte_command_unverified_user_denies_access(self, handler):
        """Usuário não verificado não deve criar ticket."""
        # ...

    @pytest.mark.asyncio
    async def test_handle_suporte_command_verified_user_starts_form(self, handler):
        """Usuário verificado deve iniciar formulário."""
        # ...

    @pytest.mark.asyncio
    async def test_handle_suporte_command_user_with_active_ticket_shows_existing(self, handler):
        """Usuário com ticket ativo deve ver ticket existente."""
        # ...

    @pytest.mark.asyncio
    async def test_support_callback_category_selection_advances_to_game(self, handler):
        """Seleção de categoria deve avançar para seleção de jogo."""
        # ...

    @pytest.mark.asyncio
    async def test_support_flow_complete_creates_ticket_in_hubsoft(self, handler):
        """Fluxo completo deve criar ticket no HubSoft."""
        # ...
```

**4. Criar testes de integração:**

```python
# tests/integration/test_cpf_verification_flow.py

import pytest
from src.sentinela.infrastructure.config.dependency_injection import configure_dependencies


@pytest.mark.integration
class TestCPFVerificationFlow:
    """Testes de integração do fluxo de verificação CPF."""

    @pytest.mark.asyncio
    async def test_complete_cpf_verification_flow(self):
        """Testa fluxo completo de verificação de CPF."""
        # Arrange
        configure_dependencies()  # DI Container real

        # Act & Assert
        # 1. Usuário inicia /start
        # 2. Bot solicita CPF
        # 3. Usuário envia CPF válido
        # 4. Bot consulta HubSoft (mock)
        # 5. Usuário é ativado
        # 6. Bot envia boas-vindas
        # ...
```

**5. Configurar pytest:**

```python
# tests/conftest.py

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop para testes async."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_telegram_update():
    """Mock de Update do python-telegram-bot."""
    # ...


@pytest.fixture
def mock_telegram_context():
    """Mock de ContextTypes.DEFAULT_TYPE."""
    # ...
```

**6. Configurar coverage:**

```bash
# .coveragerc
[run]
source = src/sentinela
omit =
    */tests/*
    */migrations/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

#### POR QUE FAZER:

1. **Prevenção de Regressões:** Mudanças futuras não quebram funcionalidade
2. **Documentação Viva:** Testes documentam comportamento esperado
3. **Confiança em Refatorações:** Podemos refatorar sabendo que testes vão alertar
4. **Bug do TASK-002:** Teste específico garante que bug não volta

#### ANÁLISE DETALHADA:

**Cobertura de testes recomendada:**

| Componente | Prioridade | Cobertura Alvo | Razão |
|------------|-----------|----------------|-------|
| `CPFVerificationHandler` | 🔴 ALTA | 90%+ | Lógica crítica de autenticação |
| `SupportFormHandler` | 🔴 ALTA | 80%+ | Fluxo principal do bot |
| `telegram_bot_handler.py` (router) | 🟡 MÉDIA | 70%+ | Coordenação entre handlers |
| Use Cases (Domain/Application) | 🟡 MÉDIA | 80%+ | Regras de negócio |
| Repositories (Infrastructure) | 🟢 BAIXA | 60%+ | Testes de integração cobrem |
| Value Objects (Domain) | 🔴 ALTA | 95%+ | Pequenos e críticos |

**Testes críticos para o bug TASK-002:**

```python
@pytest.mark.critical
@pytest.mark.asyncio
async def test_bug_task_002_user_completed_cpf_but_inactive_is_blocked():
    """
    TESTE CRÍTICO: Reproduz bug identificado na TASK-002.

    Cenário:
    - Usuário tem CPF COMPLETED
    - Mas status é INACTIVE (plano cancelado)

    Comportamento esperado:
    - _check_user_verified() deve retornar False
    - Usuário NÃO deve ter acesso

    Comportamento anterior (BUG):
    - _get_verification_status_message()["is_verified"] retornava True
    - Usuário passava pela validação indevidamente
    """
    # Arrange
    user_id = 999999

    # Cria usuário no banco com CPF COMPLETED mas INACTIVE
    async with aiosqlite.connect(TEST_DB) as db:
        await db.execute("""
            INSERT INTO users (id, username, status, cpf_verification_status)
            VALUES (?, ?, ?, ?)
        """, (user_id, "test_user", "INACTIVE", "COMPLETED"))
        await db.commit()

    handler = CPFVerificationHandler()

    # Act
    is_verified = await handler.check_user_verified(user_id)

    # Assert
    assert is_verified is False, (
        "BUG: Usuário com CPF COMPLETED mas status INACTIVE "
        "não deve ser considerado verificado!"
    )
```

**Benefícios mensuráveis:**
- ✅ **Confiança:** 80%+ de cobertura = deploy seguro
- ✅ **Velocidade:** Bugs detectados em segundos vs horas
- ✅ **Documentação:** Testes mostram como usar handlers
- ✅ **Qualidade:** Força design melhor (código testável é código limpo)

**Impacto da não-correção:**
- Bugs como TASK-002 podem voltar sem ser detectados
- Medo de refatorar (sem rede de segurança)
- Regressões em produção
- Tempo perdido debugando manualmente

---

## 📝 RESUMO DAS TASKS

| Task | Prioridade | Estimativa | Impacto | Bloqueante |
|------|-----------|-----------|---------|------------|
| TASK-001: Commitar mudanças pendentes | 🔴 CRÍTICA | 15 min | Limpeza | ✅ SIM |
| TASK-002: Bug verificação usuário | 🔴 CRÍTICA | 1h | Segurança | ❌ |
| TASK-003: Referências órfãs | 🔴 CRÍTICA | 30 min | Crash | ❌ |
| TASK-004: Extrair lógica CPF | 🔴 CRÍTICA | 4-6h | Arquitetura | ❌ |
| TASK-005: Extrair lógica Suporte | 🔴 CRÍTICA | 6-8h | Arquitetura | ❌ |
| TASK-006: Repositórios órfãos | 🟡 MÉDIA | 30 min - 4h | Arquitetura | ❌ |
| TASK-007: Use Cases não utilizados | 🟡 MÉDIA | 2-3h + variável | Limpeza | ❌ |
| TASK-008: Testes críticos | 🟡 MÉDIA | 6-8h | Qualidade | ❌ |

**Total estimado (críticas):** 12-16 horas
**Total estimado (completo):** 20-32 horas

---

## 🎯 ORDEM DE EXECUÇÃO RECOMENDADA

### Dia 1: Correções Urgentes (4-5h)
1. ✅ TASK-001: Commitar mudanças (15 min)
2. 🚨 TASK-002: Bug verificação (1h)
3. 🚨 TASK-003: Referências órfãs (30 min)
4. 📝 Testar mudanças em ambiente de staging

### Dia 2-3: Refatoração de Handlers (10-14h)
5. 🔥 TASK-004: Extrair CPF Handler (4-6h)
6. 🔥 TASK-005: Extrair Support Handler (6-8h)
7. 📝 Testes de integração dos handlers

### Dia 4: Limpeza e Organização (8-12h)
8. 🧹 TASK-006: Repositórios órfãos (30 min - 4h)
9. 🗑️ TASK-007: Use Cases não utilizados (2-3h + implementações)
10. 📝 Atualizar documentação

### Dia 5: Testes e Validação (6-8h)
11. 🧪 TASK-008: Criar testes críticos (6-8h)
12. 📝 Validação completa do sistema
13. 📊 Relatório de conclusão

---

## ✅ CRITÉRIOS DE SUCESSO

**FASE 1 (Críticas):**
- [ ] Git status limpo (sem arquivos deletados pendentes)
- [ ] Bug de verificação corrigido e testado
- [ ] Nenhuma referência órfã no código
- [ ] `telegram_bot_handler.py` reduzido para <1000 linhas
- [ ] 2 novos handlers criados e funcionais

**FASE 2 (Limpeza):**
- [ ] Todos repositórios com implementação OU deletados
- [ ] Todos Use Cases decididos (registrar/deletar/implementar)
- [ ] 80%+ de cobertura de testes em handlers críticos
- [ ] Documentação atualizada

**MÉTRICAS:**
- Linhas de código em handlers: ~~2.284~~ → <500 por handler
- Use Cases ativos: ~~57%~~ → 80%+
- Repositórios implementados: ~~78%~~ → 100%
- Cobertura de testes: ~~0%?~~ → 80%+
- Bugs críticos: ~~3~~ → 0

---

## 🚀 PRÓXIMOS PASSOS APÓS CONCLUSÃO

1. **Deploy Gradual:**
   - Deploy em staging
   - Testes manuais de fluxos críticos
   - Monitoramento de erros
   - Deploy em produção

2. **Documentação:**
   - Atualizar diagramas de arquitetura
   - Criar ADRs (Architecture Decision Records)
   - Atualizar README com novos handlers

3. **Melhoria Contínua:**
   - Implementar funcionalidades faltantes (admin_sync, etc)
   - Adicionar mais testes
   - Monitorar métricas de performance

---

**Criado em:** 09/10/2025
**Branch:** `fix/critical-architecture-issues`
**Responsável:** [Seu nome]
**Revisado por:** [A definir]
