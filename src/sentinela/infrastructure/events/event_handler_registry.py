"""
Event Handler Registry.

Sistema para registrar automaticamente todos os event handlers
no Event Bus durante a inicialização da aplicação.
"""

import logging
from typing import Type, List

from .event_bus import EventBus, EventHandler
from .handlers.ticket_event_handlers import (
    TicketCreatedHandler,
    TicketAssignedHandler,
    TicketStatusChangedHandler,
    TicketSyncedHandler,
    TicketAuditHandler
)
from .handlers.user_event_handlers import (
    UserRegisteredHandler,
    UserBannedHandler,
    UserUnbannedHandler,
    CPFValidatedHandler,
    UserActivityAuditHandler
)
from .handlers.conversation_event_handlers import (
    ConversationStartedHandler,
    ConversationCompletedHandler,
    ConversationCancelledHandler,
    ConversationFlowAnalyticsHandler
)
from .handlers.cpf_verification_event_handlers import (
    VerificationStartedHandler,
    VerificationCompletedHandler,
    VerificationFailedHandler,
    VerificationExpiredHandler,
    CPFDuplicateDetectedHandler,
    CPFRemappedHandler
)

logger = logging.getLogger(__name__)


class EventHandlerRegistry:
    """
    Registry para registrar automaticamente event handlers.

    Centraliza o registro de todos os handlers disponíveis
    e permite ativação/desativação de grupos de handlers.
    """

    def __init__(self, event_bus: EventBus):
        """
        Inicializa o registry.

        Args:
            event_bus: Instância do event bus para registrar handlers
        """
        self.event_bus = event_bus
        self._registered_handlers: List[EventHandler] = []

    def register_all_handlers(self) -> None:
        """
        Registra todos os event handlers disponíveis.

        Registra handlers específicos por tipo de evento
        e handlers globais para auditoria e analytics.
        """
        logger.info("🔧 Registrando todos os event handlers...")

        # Handlers específicos para eventos de ticket
        self._register_ticket_handlers()

        # Handlers específicos para eventos de usuário
        self._register_user_handlers()

        # Handlers específicos para eventos de conversa
        self._register_conversation_handlers()

        # Handlers específicos para eventos de verificação de CPF
        self._register_cpf_verification_handlers()

        # Handlers globais para auditoria
        self._register_global_handlers()

        logger.info(f"✅ {len(self._registered_handlers)} event handlers registrados com sucesso!")

    def _register_ticket_handlers(self) -> None:
        """Registra handlers para eventos de ticket."""
        ticket_handlers = [
            TicketCreatedHandler(),
            TicketAssignedHandler(),
            TicketStatusChangedHandler(),
            TicketSyncedHandler()
        ]

        for handler in ticket_handlers:
            self.event_bus.subscribe(handler.event_type, handler)
            self._registered_handlers.append(handler)
            logger.debug(f"📝 Registrado: {handler.__class__.__name__}")

    def _register_user_handlers(self) -> None:
        """Registra handlers para eventos de usuário."""
        user_handlers = [
            UserRegisteredHandler(),
            UserBannedHandler(),
            UserUnbannedHandler(),
            CPFValidatedHandler()
        ]

        for handler in user_handlers:
            self.event_bus.subscribe(handler.event_type, handler)
            self._registered_handlers.append(handler)
            logger.debug(f"👤 Registrado: {handler.__class__.__name__}")

    def _register_conversation_handlers(self) -> None:
        """Registra handlers para eventos de conversa."""
        conversation_handlers = [
            ConversationStartedHandler(),
            ConversationCompletedHandler(),
            ConversationCancelledHandler()
        ]

        for handler in conversation_handlers:
            self.event_bus.subscribe(handler.event_type, handler)
            self._registered_handlers.append(handler)
            logger.debug(f"💬 Registrado: {handler.__class__.__name__}")

    def _register_cpf_verification_handlers(self) -> None:
        """Registra handlers para eventos de verificação de CPF."""
        cpf_handlers = [
            VerificationStartedHandler(),
            VerificationCompletedHandler(),
            VerificationFailedHandler(),
            VerificationExpiredHandler(),
            CPFDuplicateDetectedHandler(),
            CPFRemappedHandler()
        ]

        for handler in cpf_handlers:
            self.event_bus.subscribe(handler.event_type, handler)
            self._registered_handlers.append(handler)
            logger.debug(f"🔍 Registrado: {handler.__class__.__name__}")

    def _register_global_handlers(self) -> None:
        """Registra handlers globais para auditoria e analytics."""
        global_handlers = [
            TicketAuditHandler(),
            UserActivityAuditHandler(),
            ConversationFlowAnalyticsHandler()
        ]

        for handler in global_handlers:
            # Handlers globais se inscrevem para todos os eventos
            self.event_bus.subscribe_to_all(handler)
            self._registered_handlers.append(handler)
            logger.debug(f"🌐 Global Handler: {handler.__class__.__name__}")

    def register_custom_handler(self, handler: EventHandler) -> None:
        """
        Registra um handler customizado.

        Args:
            handler: Handler customizado a ser registrado
        """
        self.event_bus.subscribe(handler.event_type, handler)
        self._registered_handlers.append(handler)
        logger.info(f"🔧 Handler customizado registrado: {handler.__class__.__name__}")

    def unregister_handler(self, handler: EventHandler) -> None:
        """
        Remove registro de um handler.

        Args:
            handler: Handler a ser removido
        """
        self.event_bus.unsubscribe(handler.event_type, handler)
        if handler in self._registered_handlers:
            self._registered_handlers.remove(handler)
        logger.info(f"❌ Handler removido: {handler.__class__.__name__}")

    def get_registered_handlers(self) -> List[EventHandler]:
        """
        Retorna lista de handlers registrados.

        Returns:
            List[EventHandler]: Handlers atualmente registrados
        """
        return self._registered_handlers.copy()

    def get_handler_count(self) -> int:
        """
        Retorna número de handlers registrados.

        Returns:
            int: Número total de handlers
        """
        return len(self._registered_handlers)

    def clear_all_handlers(self) -> None:
        """Remove todos os handlers registrados."""
        self.event_bus.clear_all_handlers()
        self._registered_handlers.clear()
        logger.warning("🧹 Todos os event handlers foram removidos")

    def get_handlers_by_event_type(self, event_type: Type) -> List[EventHandler]:
        """
        Retorna handlers registrados para um tipo específico de evento.

        Args:
            event_type: Tipo de evento

        Returns:
            List[EventHandler]: Handlers para o tipo especificado
        """
        return [
            handler for handler in self._registered_handlers
            if handler.event_type == event_type
        ]

    def diagnose_handlers(self) -> None:
        """
        Diagnóstica o estado atual dos handlers.

        Útil para debugging e monitoramento.
        """
        logger.info("🔍 DIAGNÓSTICO DE EVENT HANDLERS:")
        logger.info(f"  📊 Total de handlers: {len(self._registered_handlers)}")

        # Agrupa handlers por categoria
        ticket_handlers = [h for h in self._registered_handlers if "Ticket" in h.__class__.__name__]
        user_handlers = [h for h in self._registered_handlers if "User" in h.__class__.__name__]
        conversation_handlers = [h for h in self._registered_handlers if "Conversation" in h.__class__.__name__]
        global_handlers = [h for h in self._registered_handlers if "Audit" in h.__class__.__name__ or "Analytics" in h.__class__.__name__]

        logger.info(f"  📝 Ticket handlers: {len(ticket_handlers)}")
        logger.info(f"  👤 User handlers: {len(user_handlers)}")
        logger.info(f"  💬 Conversation handlers: {len(conversation_handlers)}")
        logger.info(f"  🌐 Global handlers: {len(global_handlers)}")

        # Lista handlers registrados no event bus
        event_types = self.event_bus.get_registered_event_types()
        logger.info(f"  🎯 Tipos de eventos com handlers: {len(event_types)}")

        total_subscriptions = self.event_bus.get_handler_count()
        logger.info(f"  🔗 Total de subscrições: {total_subscriptions}")


def setup_event_handlers(event_bus: EventBus) -> EventHandlerRegistry:
    """
    Função de conveniência para configurar todos os event handlers.

    Args:
        event_bus: Instância do event bus

    Returns:
        EventHandlerRegistry: Registry configurado com todos os handlers
    """
    registry = EventHandlerRegistry(event_bus)
    registry.register_all_handlers()
    registry.diagnose_handlers()

    return registry