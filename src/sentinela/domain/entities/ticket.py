"""
Ticket Entity - Entidade de ticket de suporte.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from .base import AggregateRoot, DomainEvent
from .user import User
from ..value_objects.identifiers import TicketId, UserId, HubSoftId, Protocol
from ..value_objects.ticket_category import TicketCategory, GameTitle, ProblemTiming


class TicketStatus(Enum):
    """Status do ticket de suporte."""
    PENDING = "pending"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class UrgencyLevel(Enum):
    """Nível de urgência do ticket."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCreated(DomainEvent):
    """Evento: ticket foi criado."""

    def __init__(self, ticket_id: TicketId, user_id: UserId, category: TicketCategory):
        super().__init__()
        self.ticket_id = ticket_id
        self.user_id = user_id
        self.category = category


class TicketAssigned(DomainEvent):
    """Evento: ticket foi atribuído a técnico."""

    def __init__(self, ticket_id: TicketId, assigned_to: str):
        super().__init__()
        self.ticket_id = ticket_id
        self.assigned_to = assigned_to


class TicketStatusChanged(DomainEvent):
    """Evento: status do ticket mudou."""

    def __init__(self, ticket_id: TicketId, old_status: TicketStatus, new_status: TicketStatus):
        super().__init__()
        self.ticket_id = ticket_id
        self.old_status = old_status
        self.new_status = new_status


class TicketSyncedWithHubSoft(DomainEvent):
    """Evento: ticket foi sincronizado com HubSoft."""

    def __init__(self, ticket_id: TicketId, hubsoft_id: HubSoftId, protocol: Protocol):
        super().__init__()
        self.ticket_id = ticket_id
        self.hubsoft_id = hubsoft_id
        self.protocol = protocol


@dataclass
class TicketAttachment:
    """Anexo do ticket."""
    file_id: str
    filename: str
    file_path: str
    file_size: int
    content_type: Optional[str] = None


@dataclass
class TicketMessage:
    """Mensagem do ticket."""
    author: str
    content: str
    timestamp: datetime
    is_internal: bool = False


class TicketBusinessRuleError(Exception):
    """Erro de regra de negócio do ticket."""
    pass


class Ticket(AggregateRoot[TicketId]):
    """
    Entidade Ticket.

    Representa um ticket de suporte com suas informações
    e regras de negócio associadas.
    """

    def __init__(
        self,
        ticket_id: Optional[TicketId],
        user: User,
        category: TicketCategory,
        affected_game: GameTitle,
        problem_timing: ProblemTiming,
        description: str,
        urgency_level: UrgencyLevel = UrgencyLevel.NORMAL
    ):
        if ticket_id is None:
            ticket_id = TicketId.generate()

        super().__init__(ticket_id)

        self._user = user
        self._category = category
        self._affected_game = affected_game
        self._problem_timing = problem_timing
        self._description = description
        self._urgency_level = urgency_level
        self._status = TicketStatus.PENDING

        # HubSoft integration
        self._hubsoft_id: Optional[HubSoftId] = None
        self._protocol: Optional[Protocol] = None
        self._sync_status = "pending"
        self._synced_at: Optional[datetime] = None
        self._sync_error: Optional[str] = None

        # Telegram integration
        self._telegram_message_id: Optional[int] = None
        self._topic_thread_id: Optional[int] = None

        # Assignment and resolution
        self._assigned_to: Optional[str] = None
        self._resolved_at: Optional[datetime] = None
        self._resolution_notes: Optional[str] = None

        # Attachments and messages
        self._attachments: List[TicketAttachment] = []
        self._messages: List[TicketMessage] = []

        # Generate initial event
        self._add_event(TicketCreated(self.id, user.id, category))

    # Properties
    @property
    def user(self) -> User:
        """Usuário que criou o ticket."""
        return self._user

    @property
    def category(self) -> TicketCategory:
        """Categoria do problema."""
        return self._category

    @property
    def affected_game(self) -> GameTitle:
        """Jogo afetado."""
        return self._affected_game

    @property
    def problem_timing(self) -> ProblemTiming:
        """Quando o problema começou."""
        return self._problem_timing

    @property
    def description(self) -> str:
        """Descrição detalhada do problema."""
        return self._description

    @property
    def urgency_level(self) -> UrgencyLevel:
        """Nível de urgência."""
        return self._urgency_level

    @property
    def status(self) -> TicketStatus:
        """Status atual do ticket."""
        return self._status

    @property
    def hubsoft_id(self) -> Optional[HubSoftId]:
        """ID no HubSoft."""
        return self._hubsoft_id

    @property
    def protocol(self) -> Optional[Protocol]:
        """Protocolo de atendimento."""
        return self._protocol

    @property
    def sync_status(self) -> str:
        """Status de sincronização."""
        return self._sync_status

    @property
    def assigned_to(self) -> Optional[str]:
        """Técnico responsável."""
        return self._assigned_to

    @property
    def attachments(self) -> List[TicketAttachment]:
        """Lista de anexos."""
        return self._attachments.copy()

    @property
    def messages(self) -> List[TicketMessage]:
        """Lista de mensagens."""
        return self._messages.copy()

    @property
    def telegram_message_id(self) -> Optional[int]:
        """ID da mensagem no Telegram."""
        return self._telegram_message_id

    @property
    def topic_thread_id(self) -> Optional[int]:
        """ID do tópico no Telegram."""
        return self._topic_thread_id

    # Business rules and operations

    def assign_to_technician(self, technician: str) -> None:
        """
        Atribui ticket a um técnico.

        Args:
            technician: Nome do técnico

        Raises:
            TicketBusinessRuleError: Se ticket já fechado
        """
        if self._status in (TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED):
            raise TicketBusinessRuleError("Não é possível atribuir ticket fechado")

        old_assigned = self._assigned_to
        self._assigned_to = technician

        if self._status == TicketStatus.PENDING:
            self._change_status(TicketStatus.IN_PROGRESS)

        self._add_event(TicketAssigned(self.id, technician))
        self._touch()

    def change_status(self, new_status: TicketStatus) -> None:
        """
        Muda status do ticket.

        Args:
            new_status: Novo status

        Raises:
            TicketBusinessRuleError: Se transição inválida
        """
        if not self._is_valid_status_transition(self._status, new_status):
            raise TicketBusinessRuleError(
                f"Transição inválida: {self._status.value} → {new_status.value}"
            )

        self._change_status(new_status)

    def _change_status(self, new_status: TicketStatus) -> None:
        """Muda status internamente."""
        old_status = self._status
        self._status = new_status

        if new_status == TicketStatus.RESOLVED:
            self._resolved_at = datetime.now()

        self._add_event(TicketStatusChanged(self.id, old_status, new_status))
        self._increment_version()

    def _is_valid_status_transition(self, current: TicketStatus, new: TicketStatus) -> bool:
        """Valida se transição de status é permitida."""
        allowed_transitions = {
            TicketStatus.PENDING: [TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.CANCELLED],
            TicketStatus.OPEN: [TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CANCELLED],
            TicketStatus.IN_PROGRESS: [TicketStatus.RESOLVED, TicketStatus.CANCELLED, TicketStatus.PENDING],
            TicketStatus.RESOLVED: [TicketStatus.CLOSED, TicketStatus.OPEN],  # Pode reabrir
            TicketStatus.CLOSED: [],  # Final
            TicketStatus.CANCELLED: []  # Final
        }

        return new in allowed_transitions.get(current, [])

    def add_attachment(self, attachment: TicketAttachment) -> None:
        """
        Adiciona anexo ao ticket.

        Args:
            attachment: Anexo a adicionar

        Raises:
            TicketBusinessRuleError: Se limite de anexos excedido
        """
        if len(self._attachments) >= 5:  # Limite de 5 anexos
            raise TicketBusinessRuleError("Limite de 5 anexos por ticket excedido")

        self._attachments.append(attachment)
        self._touch()

    def add_message(self, author: str, content: str, is_internal: bool = False) -> None:
        """
        Adiciona mensagem ao histórico.

        Args:
            author: Autor da mensagem
            content: Conteúdo da mensagem
            is_internal: Se é mensagem interna (não visível ao cliente)
        """
        message = TicketMessage(
            author=author,
            content=content,
            timestamp=datetime.now(),
            is_internal=is_internal
        )

        self._messages.append(message)
        self._touch()

    def sync_with_hubsoft(self, hubsoft_id: HubSoftId, protocol: Protocol) -> None:
        """
        Marca ticket como sincronizado com HubSoft.

        Args:
            hubsoft_id: ID no HubSoft
            protocol: Protocolo gerado
        """
        self._hubsoft_id = hubsoft_id
        self._protocol = protocol
        self._sync_status = "synced"
        self._synced_at = datetime.now()
        self._sync_error = None

        self._add_event(TicketSyncedWithHubSoft(self.id, hubsoft_id, protocol))
        self._touch()

    def mark_sync_failed(self, error: str) -> None:
        """
        Marca falha na sincronização.

        Args:
            error: Mensagem de erro
        """
        self._sync_status = "failed"
        self._sync_error = error
        self._touch()

    def set_telegram_info(self, message_id: int, topic_thread_id: Optional[int] = None) -> None:
        """
        Define informações do Telegram.

        Args:
            message_id: ID da mensagem no Telegram
            topic_thread_id: ID do tópico (se aplicável)
        """
        self._telegram_message_id = message_id
        self._topic_thread_id = topic_thread_id
        self._touch()

    def elevate_urgency(self) -> None:
        """Eleva nível de urgência do ticket."""
        urgency_levels = [UrgencyLevel.LOW, UrgencyLevel.NORMAL, UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]
        current_index = urgency_levels.index(self._urgency_level)

        if current_index < len(urgency_levels) - 1:
            self._urgency_level = urgency_levels[current_index + 1]
            self._touch()

    def close_with_resolution(self, resolution_notes: str) -> None:
        """
        Fecha ticket com nota de resolução.

        Args:
            resolution_notes: Notas sobre a resolução
        """
        if self._status != TicketStatus.RESOLVED:
            raise TicketBusinessRuleError("Ticket deve estar resolvido antes de ser fechado")

        self._resolution_notes = resolution_notes
        self._change_status(TicketStatus.CLOSED)

    def cancel(self, reason: str) -> None:
        """
        Cancela ticket.

        Args:
            reason: Motivo do cancelamento
        """
        if self._status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            raise TicketBusinessRuleError("Não é possível cancelar ticket já finalizado")

        self._resolution_notes = f"Cancelado: {reason}"
        self._change_status(TicketStatus.CANCELLED)

    def is_active(self) -> bool:
        """Verifica se ticket está ativo (não finalizado)."""
        return self._status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED)

    def is_synced_with_hubsoft(self) -> bool:
        """Verifica se está sincronizado com HubSoft."""
        return self._sync_status == "synced" and self._hubsoft_id is not None

    def needs_sync(self) -> bool:
        """Verifica se precisa ser sincronizado."""
        return self._sync_status in ("pending", "failed") and self._hubsoft_id is None

    def get_display_protocol(self) -> str:
        """Retorna protocolo para exibição."""
        if self._protocol:
            return self._protocol.display()
        else:
            # Protocolo local padrão
            return Protocol.local(self.id).display()

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dict (para serialização)."""
        return {
            "id": int(self.id),
            "user_id": int(self._user.id),
            "category": self._category.category_type.value,
            "affected_game": self._affected_game.game_type.value,
            "problem_timing": self._problem_timing.timing_type.value,
            "description": self._description,
            "urgency_level": self._urgency_level.value,
            "status": self._status.value,
            "hubsoft_id": str(self._hubsoft_id) if self._hubsoft_id else None,
            "protocol": str(self._protocol) if self._protocol else None,
            "sync_status": self._sync_status,
            "assigned_to": self._assigned_to,
            "telegram_message_id": self._telegram_message_id,
            "topic_thread_id": self._topic_thread_id,
            "attachments_count": len(self._attachments),
            "messages_count": len(self._messages),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self._resolved_at.isoformat() if self._resolved_at else None
        }

    def __str__(self) -> str:
        protocol = self.get_display_protocol()
        return f"Ticket({protocol}, {self._status.value}, {self._category.display_name})"