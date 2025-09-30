#!/usr/bin/env python3
"""
Teste completo do sistema de eventos.

Valida Event Bus, Event Handlers e integração com domain entities.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Adiciona o path do projeto para imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from sentinela.infrastructure.events.event_bus import get_event_bus, publish_event
from sentinela.infrastructure.events.event_handler_registry import setup_event_handlers
from sentinela.domain.events.ticket_events import TicketCreated, TicketAssigned, TicketStatusChanged
from sentinela.domain.events.user_events import UserRegistered, CPFValidated
from sentinela.domain.events.conversation_events import ConversationStarted, ConversationCompleted
from sentinela.domain.value_objects.identifiers import TicketId, UserId, ConversationId, Protocol

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_event_system():
    """Testa o sistema completo de eventos."""

    print("🧪 INICIANDO TESTE DO SISTEMA DE EVENTOS")
    print("=" * 60)

    # 1. Configura o Event Bus e handlers
    print("\n1️⃣ Configurando Event Bus e Handlers...")
    event_bus = get_event_bus()
    registry = setup_event_handlers(event_bus)

    print(f"✅ Event Bus configurado com {registry.get_handler_count()} handlers")

    # 2. Testa eventos de usuário
    print("\n2️⃣ Testando eventos de usuário...")

    user_registered = UserRegistered(
        user_id=12345,
        username="TestGamer",
        registration_date=datetime.now()
    )
    await publish_event(user_registered)

    cpf_validated = CPFValidated(
        user_id=12345,
        username="TestGamer",
        cpf_number="11144477735",
        is_valid=True
    )
    await publish_event(cpf_validated)

    print("✅ Eventos de usuário processados")

    # 3. Testa eventos de conversa
    print("\n3️⃣ Testando eventos de conversa...")

    conversation_id = ConversationId.generate()
    conversation_started = ConversationStarted(
        conversation_id=conversation_id,
        user_id=12345,
        username="TestGamer",
        started_at=datetime.now()
    )
    await publish_event(conversation_started)

    # Simula conversa completada
    await asyncio.sleep(0.1)  # Simula duração da conversa

    ticket_id = TicketId.generate()
    conversation_completed = ConversationCompleted(
        conversation_id=conversation_id,
        user_id=12345,
        username="TestGamer",
        ticket_id=ticket_id,
        started_at=conversation_started.started_at,
        completed_at=datetime.now()
    )
    await publish_event(conversation_completed)

    print("✅ Eventos de conversa processados")

    # 4. Testa eventos de ticket
    print("\n4️⃣ Testando eventos de ticket...")

    ticket_created = TicketCreated(
        ticket_id=ticket_id,
        user_id=12345,
        username="TestGamer",
        category="🎮 Performance em Jogos",
        affected_game="⚡️ Valorant",
        problem_timing="🚨 Agora mesmo / Hoje",
        description="Lag intenso no Valorant durante partidas rankeadas",
        protocol=Protocol.local(ticket_id)
    )
    await publish_event(ticket_created)

    ticket_assigned = TicketAssigned(
        ticket_id=ticket_id,
        technician="TecnicoGaming01",
        status="IN_PROGRESS"
    )
    await publish_event(ticket_assigned)

    ticket_status_changed = TicketStatusChanged(
        ticket_id=ticket_id,
        user_id=12345,
        old_status="PENDING",
        new_status="RESOLVED"
    )
    await publish_event(ticket_status_changed)

    print("✅ Eventos de ticket processados")

    # 5. Testa publicação em lote
    print("\n5️⃣ Testando publicação em lote...")

    batch_events = [
        UserRegistered(user_id=54321, username="BatchUser1", registration_date=datetime.now()),
        UserRegistered(user_id=54322, username="BatchUser2", registration_date=datetime.now()),
        UserRegistered(user_id=54323, username="BatchUser3", registration_date=datetime.now())
    ]

    await event_bus.publish_many(batch_events)
    print("✅ Eventos em lote processados")

    # 6. Métricas finais
    print("\n6️⃣ Métricas do sistema...")

    total_event_types = len(event_bus.get_registered_event_types())
    total_handlers = event_bus.get_handler_count()

    print(f"📊 Tipos de eventos registrados: {total_event_types}")
    print(f"📊 Total de handlers ativos: {total_handlers}")

    # 7. Teste de performance
    print("\n7️⃣ Teste de performance...")

    start_time = datetime.now()

    # Simula 100 eventos em paralelo
    performance_events = [
        TicketCreated(
            ticket_id=TicketId.generate(),
            user_id=i,
            username=f"PerfUser{i}",
            category="🔧 Problema com Equipamento",
            affected_game="🌐 Todos os jogos",
            problem_timing="📅 Ontem",
            description=f"Teste de performance #{i}",
            protocol=Protocol.local(i)
        )
        for i in range(100)
    ]

    await event_bus.publish_many(performance_events)

    end_time = datetime.now()
    duration_ms = (end_time - start_time).total_seconds() * 1000

    print(f"⚡ 100 eventos processados em {duration_ms:.1f}ms")
    print(f"⚡ Performance: {100000/duration_ms:.0f} eventos/segundo")

    print("\n" + "=" * 60)
    print("🎉 TESTE DO SISTEMA DE EVENTOS COMPLETADO COM SUCESSO!")
    print("=" * 60)


async def test_event_error_handling():
    """Testa tratamento de erros nos event handlers."""

    print("\n🔥 TESTANDO TRATAMENTO DE ERROS...")

    # Cria um handler que sempre falha para teste
    from sentinela.infrastructure.events.event_bus import EventHandler
    from sentinela.domain.entities.base import DomainEvent
    from typing import Type

    class FailingHandler(EventHandler):
        @property
        def event_type(self) -> Type[DomainEvent]:
            return UserRegistered

        async def handle(self, event: DomainEvent) -> None:
            raise Exception("Handler de teste que sempre falha")

    # Registra handler que falha
    event_bus = get_event_bus()
    failing_handler = FailingHandler()
    event_bus.subscribe(UserRegistered, failing_handler)

    # Publica evento que causará erro
    error_event = UserRegistered(
        user_id=99999,
        username="ErrorUser",
        registration_date=datetime.now()
    )

    # O evento deve ser processado mesmo com erro no handler
    await publish_event(error_event)

    # Remove handler de teste
    event_bus.unsubscribe(UserRegistered, failing_handler)

    print("✅ Tratamento de erros funcionando corretamente")


if __name__ == "__main__":
    async def main():
        await test_event_system()
        await test_event_error_handling()

    asyncio.run(main())