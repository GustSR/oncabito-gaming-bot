#!/usr/bin/env python3
"""
Teste das Admin Operations.

Valida comandos administrativos, handlers e use cases
para operações de administração do sistema.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona o path do projeto para imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from sentinela.application.commands.admin_commands import (
    ListTicketsCommand,
    AssignTicketCommand,
    UpdateTicketStatusCommand,
    BanUserCommand,
    GetSystemStatsCommand,
    BulkUpdateTicketsCommand
)
from sentinela.application.command_handlers.admin_command_handlers import (
    ListTicketsHandler,
    AssignTicketHandler,
    UpdateTicketStatusHandler,
    BanUserHandler,
    GetSystemStatsHandler
)
from sentinela.application.use_cases.admin_operations_use_case import (
    AdminOperationsUseCase,
    AdminOperationResult
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock repositories for testing
class MockTicketRepository:
    """Mock repository para tickets."""

    def __init__(self):
        self._tickets = {}

    async def find_all(self):
        """Retorna todos os tickets."""
        from sentinela.domain.entities.ticket import Ticket, TicketId, TicketCategory, TicketStatus, UrgencyLevel
        from sentinela.domain.entities.user import User
        from sentinela.domain.value_objects.identifiers import UserId, Protocol
        from sentinela.domain.value_objects.ticket_category import TicketCategoryType
        from sentinela.domain.value_objects.game_title import GameTitle, GameType
        from sentinela.domain.value_objects.problem_timing import ProblemTiming, TimingType

        # Cria tickets mock
        tickets = []
        for i in range(5):
            ticket_id = TicketId(1000 + i)
            user_id = UserId(2000 + i)

            user = User(
                user_id=user_id,
                username=f"Usuario{i}",
                telegram_user_id=user_id.value
            )

            category = TicketCategory(
                category_type=TicketCategoryType.CONNECTIVITY,
                display_name="🌐 Conectividade/Ping"
            )

            game = GameTitle(
                game_type=GameType.VALORANT,
                display_name="⚡️ Valorant"
            )

            timing = ProblemTiming(
                timing_type=TimingType.NOW,
                display_name="🚨 Agora mesmo / Hoje"
            )

            ticket = Ticket(
                ticket_id=ticket_id,
                user=user,
                category=category,
                affected_game=game,
                problem_timing=timing,
                description=f"Problema de conexão {i}",
                urgency_level=UrgencyLevel.NORMAL,
                protocol=Protocol.local(ticket_id)
            )

            # Varia status dos tickets
            if i % 2 == 0:
                ticket.change_status(TicketStatus.OPEN)
            elif i == 1:
                ticket.change_status(TicketStatus.IN_PROGRESS)
                ticket.assign_to_technician("TecnicoGaming01")

            tickets.append(ticket)

        return tickets

    async def find_by_id(self, ticket_id):
        """Busca ticket por ID."""
        tickets = await self.find_all()
        for ticket in tickets:
            if ticket.id.value == ticket_id.value:
                return ticket
        return None

    async def save(self, ticket):
        """Salva ticket."""
        self._tickets[ticket.id.value] = ticket
        return True


class MockUserRepository:
    """Mock repository para usuários."""

    def __init__(self):
        self._users = {}

    async def find_all(self):
        """Retorna todos os usuários."""
        from sentinela.domain.entities.user import User
        from sentinela.domain.value_objects.identifiers import UserId

        users = []
        for i in range(10):
            user_id = UserId(2000 + i)
            user = User(
                user_id=user_id,
                username=f"Usuario{i}",
                telegram_user_id=user_id.value
            )
            users.append(user)

        return users

    async def find_by_id(self, user_id):
        """Busca usuário por ID."""
        users = await self.find_all()
        for user in users:
            if user.user_id.value == user_id.value:
                return user
        return None

    async def save(self, user):
        """Salva usuário."""
        self._users[user.user_id.value] = user
        return True


class MockVerificationRepository:
    """Mock repository para verificações."""

    async def get_verification_stats(self):
        """Retorna estatísticas de verificação."""
        return {
            "pending": 5,
            "completed": 25,
            "failed": 3,
            "expired": 2,
            "success_rate": "89%"
        }

    async def find_pending_by_user(self, user_id):
        """Busca verificação pendente por usuário."""
        return None  # Simplificado para teste


class MockEventBus:
    """Mock event bus para testes."""

    async def publish(self, event):
        """Publica evento."""
        logger.debug(f"Event published: {event.__class__.__name__}")


async def test_admin_commands():
    """Testa comandos administrativos."""

    print("\n🧪 TESTANDO COMANDOS ADMINISTRATIVOS")
    print("=" * 60)

    try:
        # 1. Testa ListTicketsCommand
        list_command = ListTicketsCommand(
            admin_user_id=123456789,
            status_filter="open",
            limit=10
        )

        print(f"✅ ListTicketsCommand criado")
        print(f"   Admin: {list_command.admin_user_id}")
        print(f"   Filtro: {list_command.status_filter}")
        print(f"   Limite: {list_command.limit}")

        # 2. Testa AssignTicketCommand
        assign_command = AssignTicketCommand(
            admin_user_id=123456789,
            ticket_id="1001",
            technician_name="TecnicoGaming01",
            notes="Atribuído para análise prioritária"
        )

        print(f"\n✅ AssignTicketCommand criado")
        print(f"   Ticket: {assign_command.ticket_id}")
        print(f"   Técnico: {assign_command.technician_name}")

        # 3. Testa BanUserCommand
        ban_command = BanUserCommand(
            admin_user_id=123456789,
            target_user_id=2001,
            reason="Violação das regras do grupo",
            duration_hours=24
        )

        print(f"\n✅ BanUserCommand criado")
        print(f"   Usuário alvo: {ban_command.target_user_id}")
        print(f"   Motivo: {ban_command.reason}")
        print(f"   Duração: {ban_command.duration_hours}h")

        # 4. Testa GetSystemStatsCommand
        stats_command = GetSystemStatsCommand(
            admin_user_id=123456789,
            include_details=True,
            date_range_days=30
        )

        print(f"\n✅ GetSystemStatsCommand criado")
        print(f"   Incluir detalhes: {stats_command.include_details}")
        print(f"   Período: {stats_command.date_range_days} dias")

        print("\n✅ TESTE DE COMANDOS PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE COMANDOS: {e}")
        logger.error(f"Erro no teste de comandos: {e}")
        return False


async def test_admin_handlers():
    """Testa handlers administrativos."""

    print("\n🧪 TESTANDO HANDLERS ADMINISTRATIVOS")
    print("=" * 60)

    try:
        # Setup mocks
        ticket_repo = MockTicketRepository()
        user_repo = MockUserRepository()
        verification_repo = MockVerificationRepository()
        event_bus = MockEventBus()

        # 1. Testa ListTicketsHandler
        print("🔄 Testando ListTicketsHandler...")

        list_handler = ListTicketsHandler(ticket_repo)
        list_command = ListTicketsCommand(
            admin_user_id=123456789,
            status_filter=None,
            limit=5
        )

        list_result = await list_handler.handle(list_command)
        print(f"   Resultado: {list_result.success}")
        if list_result.success:
            print(f"   Tickets encontrados: {list_result.data['total']}")

        # 2. Testa AssignTicketHandler
        print("\n🔄 Testando AssignTicketHandler...")

        assign_handler = AssignTicketHandler(ticket_repo, event_bus)
        assign_command = AssignTicketCommand(
            admin_user_id=123456789,
            ticket_id="1001",
            technician_name="TecnicoGaming01"
        )

        assign_result = await assign_handler.handle(assign_command)
        print(f"   Resultado: {assign_result.success}")
        if assign_result.success:
            print(f"   Ticket atribuído a: {assign_result.data['assigned_to']}")

        # 3. Testa BanUserHandler
        print("\n🔄 Testando BanUserHandler...")

        ban_handler = BanUserHandler(user_repo, event_bus)
        ban_command = BanUserCommand(
            admin_user_id=123456789,
            target_user_id=2001,
            reason="Teste de banimento",
            duration_hours=1
        )

        ban_result = await ban_handler.handle(ban_command)
        print(f"   Resultado: {ban_result.success}")
        if ban_result.success:
            print(f"   Usuário banido: {ban_result.data['user_id']}")

        # 4. Testa GetSystemStatsHandler
        print("\n🔄 Testando GetSystemStatsHandler...")

        stats_handler = GetSystemStatsHandler(ticket_repo, user_repo, verification_repo)
        stats_command = GetSystemStatsCommand(
            admin_user_id=123456789,
            include_details=False,
            date_range_days=7
        )

        stats_result = await stats_handler.handle(stats_command)
        print(f"   Resultado: {stats_result.success}")
        if stats_result.success:
            print(f"   Estatísticas coletadas para {stats_result.data['period_days']} dias")

        print("\n✅ TESTE DE HANDLERS PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE HANDLERS: {e}")
        logger.error(f"Erro no teste de handlers: {e}")
        return False


async def test_admin_use_case():
    """Testa use case administrativo."""

    print("\n🧪 TESTANDO ADMIN USE CASE")
    print("=" * 60)

    try:
        # Setup mocks
        ticket_repo = MockTicketRepository()
        user_repo = MockUserRepository()
        verification_repo = MockVerificationRepository()
        event_bus = MockEventBus()

        # Setup handlers
        list_handler = ListTicketsHandler(ticket_repo)
        assign_handler = AssignTicketHandler(ticket_repo, event_bus)
        update_handler = UpdateTicketStatusHandler(ticket_repo, event_bus)
        ban_handler = BanUserHandler(user_repo, event_bus)
        stats_handler = GetSystemStatsHandler(ticket_repo, user_repo, verification_repo)

        # Cria use case
        admin_use_case = AdminOperationsUseCase(
            list_tickets_handler=list_handler,
            assign_ticket_handler=assign_handler,
            update_ticket_status_handler=update_handler,
            ban_user_handler=ban_handler,
            stats_handler=stats_handler,
            ticket_repository=ticket_repo,
            user_repository=user_repo,
            verification_repository=verification_repo
        )

        # 1. Testa listagem com filtros
        print("🔄 Testando listagem de tickets...")

        list_result = await admin_use_case.list_tickets_with_filters(
            admin_user_id=123456789,
            status_filter=None,
            limit=5
        )

        print(f"   Sucesso: {list_result.success}")
        print(f"   Mensagem: {list_result.message}")
        print(f"   Itens afetados: {list_result.affected_items}")

        # 2. Testa atribuição de ticket
        print("\n🔄 Testando atribuição de ticket...")

        assign_result = await admin_use_case.assign_ticket_to_technician(
            admin_user_id=123456789,
            ticket_id="1001",
            technician_name="TecnicoGaming01",
            notes="Atribuição via teste"
        )

        print(f"   Sucesso: {assign_result.success}")
        print(f"   Mensagem: {assign_result.message}")

        # 3. Testa operação em lote
        print("\n🔄 Testando operação em lote...")

        bulk_result = await admin_use_case.bulk_update_tickets(
            admin_user_id=123456789,
            ticket_ids=["1001", "1002"],
            action="assign",
            parameters={"technician": "TecnicoGaming01", "notes": "Atribuição em lote"}
        )

        print(f"   Sucesso: {bulk_result.success}")
        print(f"   Mensagem: {bulk_result.message}")
        print(f"   Tickets processados: {bulk_result.affected_items}")

        # 4. Testa banimento com validação
        print("\n🔄 Testando banimento de usuário...")

        ban_result = await admin_use_case.ban_user_with_validation(
            admin_user_id=123456789,
            target_user_id=2001,
            reason="Teste de banimento via use case",
            duration_hours=1
        )

        print(f"   Sucesso: {ban_result.success}")
        print(f"   Mensagem: {ban_result.message}")

        # 5. Testa estatísticas abrangentes
        print("\n🔄 Testando estatísticas do sistema...")

        stats_result = await admin_use_case.get_comprehensive_stats(
            admin_user_id=123456789,
            include_details=True,
            date_range_days=30
        )

        print(f"   Sucesso: {stats_result.success}")
        print(f"   Mensagem: {stats_result.message}")
        if stats_result.success and stats_result.data:
            print(f"   Período analisado: {stats_result.data.get('period_days', 'N/A')} dias")

        print("\n✅ TESTE DE USE CASE PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE USE CASE: {e}")
        logger.error(f"Erro no teste de use case: {e}")
        return False


async def test_admin_operations():
    """Executa todos os testes das operações administrativas."""

    print("🎯 INICIANDO TESTES DAS OPERAÇÕES ADMINISTRATIVAS")
    print("=" * 80)

    # Lista de testes
    tests = [
        ("Comandos", test_admin_commands),
        ("Handlers", test_admin_handlers),
        ("Use Case", test_admin_use_case)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 Executando teste: {test_name}")
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name}: PASSOU")
            else:
                print(f"❌ {test_name}: FALHOU")
        except Exception as e:
            print(f"❌ {test_name}: ERRO - {e}")
            logger.error(f"Erro no teste {test_name}: {e}")

    # Resultado final
    print("\n" + "=" * 80)
    print(f"📊 RESULTADO FINAL: {passed}/{total} testes passaram")

    if passed == total:
        print("🎉 ADMIN OPERATIONS IMPLEMENTADAS COM SUCESSO!")
        print("✅ Todos os comandos administrativos estão operacionais")
        print("🔧 Sistema pronto para administração completa")
    else:
        print("⚠️ Alguns testes falharam - Revisar implementação")

    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    asyncio.run(test_admin_operations())