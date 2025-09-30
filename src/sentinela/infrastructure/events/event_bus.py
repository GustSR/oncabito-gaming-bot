"""
Event Bus implementation.

Sistema central de distribuição de eventos para comunicação
assíncrona entre componentes da aplicação.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Type, Callable, Any, Optional
from collections import defaultdict

from ...domain.entities.base import DomainEvent

logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """
    Interface base para handlers de eventos.
    """

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """
        Processa um evento de domínio.

        Args:
            event: Evento a ser processado
        """
        pass

    @property
    @abstractmethod
    def event_type(self) -> Type[DomainEvent]:
        """Tipo de evento que este handler processa."""
        pass


class EventBus(ABC):
    """
    Interface abstrata para Event Bus.
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """
        Publica um evento no bus.

        Args:
            event: Evento a ser publicado
        """
        pass

    @abstractmethod
    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        Inscreve um handler para um tipo de evento.

        Args:
            event_type: Tipo de evento
            handler: Handler para processar o evento
        """
        pass

    @abstractmethod
    def unsubscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        Remove inscrição de um handler.

        Args:
            event_type: Tipo de evento
            handler: Handler a ser removido
        """
        pass


class InMemoryEventBus(EventBus):
    """
    Implementação em memória do Event Bus.

    Para produção, considerar usar Redis, RabbitMQ ou AWS EventBridge.
    """

    def __init__(self, max_concurrent_handlers: int = 10, handler_timeout: int = 30):
        self._handlers: Dict[Type[DomainEvent], List[EventHandler]] = defaultdict(list)
        self._global_handlers: List[EventHandler] = []
        self._processing_events = False
        self._max_concurrent_handlers = max_concurrent_handlers
        self._handler_timeout = handler_timeout

    async def publish(self, event: DomainEvent) -> None:
        """
        Publica evento para todos os handlers inscritos.

        Args:
            event: Evento a ser publicado
        """
        event_type = type(event)

        logger.debug(f"Publishing event: {event_type.__name__}")

        # Coleta todos os handlers para este tipo de evento
        handlers = self._handlers.get(event_type, []).copy()
        handlers.extend(self._global_handlers)

        if not handlers:
            logger.debug(f"No handlers registered for event: {event_type.__name__}")
            return

        # Processa handlers em paralelo
        await self._process_handlers_concurrently(event, handlers)

    async def _process_handlers_concurrently(self, event: DomainEvent, handlers: List[EventHandler]) -> None:
        """
        Processa handlers de forma concorrente.

        Args:
            event: Evento a ser processado
            handlers: Lista de handlers a executar
        """
        tasks = []

        for handler in handlers:
            task = asyncio.create_task(
                self._safe_handle_event(handler, event),
                name=f"{handler.__class__.__name__}-{type(event).__name__}"
            )
            tasks.append(task)

        if tasks:
            # Aguarda todos os handlers, mas não falha se algum der erro
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log de erros sem interromper o fluxo
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    handler_name = handlers[i].__class__.__name__
                    logger.error(f"Error in event handler {handler_name}: {result}")

    async def _safe_handle_event(self, handler: EventHandler, event: DomainEvent) -> None:
        """
        Executa handler de forma segura com tratamento de erro.

        Args:
            handler: Handler a executar
            event: Evento a processar
        """
        try:
            await handler.handle(event)
            logger.debug(f"Event handled successfully by {handler.__class__.__name__}")
        except Exception as e:
            logger.error(
                f"Error in event handler {handler.__class__.__name__} "
                f"for event {type(event).__name__}: {e}"
            )
            # Em produção, poderia enviar para dead letter queue
            raise

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        Inscreve handler para tipo de evento específico.

        Args:
            event_type: Tipo de evento
            handler: Handler a inscrever
        """
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(f"Subscribed {handler.__class__.__name__} to {event_type.__name__}")

    def unsubscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        Remove inscrição de handler.

        Args:
            event_type: Tipo de evento
            handler: Handler a remover
        """
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"Unsubscribed {handler.__class__.__name__} from {event_type.__name__}")

    def subscribe_to_all(self, handler: EventHandler) -> None:
        """
        Inscreve handler para todos os tipos de eventos.

        Args:
            handler: Handler global
        """
        if handler not in self._global_handlers:
            self._global_handlers.append(handler)
            logger.debug(f"Subscribed {handler.__class__.__name__} to all events")

    def unsubscribe_from_all(self, handler: EventHandler) -> None:
        """
        Remove handler global.

        Args:
            handler: Handler a remover
        """
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)
            logger.debug(f"Unsubscribed {handler.__class__.__name__} from all events")

    def get_handler_count(self, event_type: Optional[Type[DomainEvent]] = None) -> int:
        """
        Retorna número de handlers registrados.

        Args:
            event_type: Tipo específico ou None para total

        Returns:
            int: Número de handlers
        """
        if event_type:
            return len(self._handlers.get(event_type, []))
        else:
            total = sum(len(handlers) for handlers in self._handlers.values())
            total += len(self._global_handlers)
            return total

    def get_registered_event_types(self) -> List[Type[DomainEvent]]:
        """
        Retorna lista de tipos de eventos registrados.

        Returns:
            List[Type[DomainEvent]]: Tipos de eventos com handlers
        """
        return list(self._handlers.keys())

    async def publish_many(self, events: List[DomainEvent]) -> None:
        """
        Publica múltiplos eventos em lote.

        Args:
            events: Lista de eventos a publicar
        """
        if not events:
            return

        logger.debug(f"Publishing {len(events)} events in batch")

        # Publica todos os eventos de forma concorrente
        tasks = [self.publish(event) for event in events]
        await asyncio.gather(*tasks, return_exceptions=True)

    def clear_all_handlers(self) -> None:
        """Remove todos os handlers registrados."""
        self._handlers.clear()
        self._global_handlers.clear()
        logger.debug("Cleared all event handlers")


    async def shutdown(self) -> None:
        """Encerra o event bus e limpa recursos."""
        logger.info("Event bus sendo encerrado...")
        self._handlers.clear()
        self._global_handlers.clear()
        self._processing_events = False
        logger.info("Event bus encerrado com sucesso")


class EventBusDecorator:
    """
    Decorator para registrar handlers automaticamente.
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def handles(self, event_type: Type[DomainEvent]):
        """
        Decorator para marcar métodos como handlers de eventos.

        Args:
            event_type: Tipo de evento a processar

        Returns:
            Decorator function
        """
        def decorator(handler_class):
            # Registra automaticamente quando a classe é importada
            if hasattr(handler_class, 'handle'):
                handler_instance = handler_class()
                self.event_bus.subscribe(event_type, handler_instance)
            return handler_class
        return decorator


# Singleton global para facilitar uso
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Retorna instância global do event bus.

    Returns:
        EventBus: Instância global
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = InMemoryEventBus()
    return _global_event_bus


def set_event_bus(event_bus: EventBus) -> None:
    """
    Define instância global do event bus.

    Args:
        event_bus: Nova instância do event bus
    """
    global _global_event_bus
    _global_event_bus = event_bus


# Helper para publicar eventos facilmente
async def publish_event(event: DomainEvent) -> None:
    """
    Função de conveniência para publicar eventos.

    Args:
        event: Evento a publicar
    """
    event_bus = get_event_bus()
    await event_bus.publish(event)