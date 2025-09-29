"""
Base classes para Entities.

Entities são objetos com identidade e ciclo de vida.
"""

from abc import ABC
from typing import Any, List, TypeVar, Generic
from datetime import datetime


EntityId = TypeVar('EntityId')


class DomainEvent:
    """
    Evento de domínio.

    Representa algo que aconteceu no domínio e é relevante
    para outros bounded contexts.
    """

    def __init__(self, occurred_at: datetime = None):
        self.occurred_at = occurred_at or datetime.now()
        self.event_id = f"{self.__class__.__name__}_{int(self.occurred_at.timestamp()*1000)}"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, DomainEvent):
            return False
        return self.event_id == other.event_id

    def __hash__(self) -> int:
        return hash(self.event_id)


class Entity(Generic[EntityId], ABC):
    """
    Classe base para todas as entidades.

    Características:
    - Tem identidade única
    - Pode mudar ao longo do tempo
    - Igualdade baseada em ID
    - Pode gerar domain events
    """

    def __init__(self, entity_id: EntityId):
        self._id = entity_id
        self._events: List[DomainEvent] = []
        self._created_at = datetime.now()
        self._updated_at = datetime.now()

    @property
    def id(self) -> EntityId:
        """ID único da entidade."""
        return self._id

    @property
    def created_at(self) -> datetime:
        """Data/hora de criação da entidade."""
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        """Data/hora da última atualização."""
        return self._updated_at

    @property
    def events(self) -> List[DomainEvent]:
        """Lista de eventos de domínio gerados."""
        return self._events.copy()

    def clear_events(self) -> None:
        """Limpa a lista de eventos."""
        self._events.clear()

    def _add_event(self, event: DomainEvent) -> None:
        """
        Adiciona um evento de domínio.

        Args:
            event: Evento a ser adicionado
        """
        self._events.append(event)

    def _touch(self) -> None:
        """Atualiza o timestamp de updated_at."""
        self._updated_at = datetime.now()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self._id})"


class AggregateRoot(Entity[EntityId]):
    """
    Aggregate Root.

    Ponto de entrada para um agregado no DDD.
    Controla consistência e invariantes do agregado.
    """

    def __init__(self, entity_id: EntityId):
        super().__init__(entity_id)
        self._version = 1

    @property
    def version(self) -> int:
        """Versão do agregado (para controle de concorrência)."""
        return self._version

    def _increment_version(self) -> None:
        """Incrementa a versão do agregado."""
        self._version += 1
        self._touch()