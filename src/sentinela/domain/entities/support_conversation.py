"""
Support Conversation Entity - Conversa de formulário de suporte.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import json

from .base import AggregateRoot, DomainEvent
from .user import User
from .ticket import Ticket, TicketAttachment
from ..value_objects.identifiers import ConversationId, UserId, TicketId
from ..value_objects.ticket_category import TicketCategory, GameTitle, ProblemTiming


class ConversationState(Enum):
    """Estado da conversa de suporte."""
    IDLE = "idle"
    CATEGORY_SELECTION = "category_selection"
    GAME_SELECTION = "game_selection"
    TIMING_SELECTION = "timing_selection"
    DESCRIPTION_INPUT = "description_input"
    ATTACHMENTS_OPTIONAL = "attachments_optional"
    CONFIRMATION = "confirmation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ConversationStep(Enum):
    """Passo atual da conversa."""
    STEP_1 = 1  # Category selection
    STEP_2 = 2  # Game selection
    STEP_3 = 3  # Timing selection
    STEP_4 = 4  # Description input
    STEP_5 = 5  # Attachments optional
    STEP_6 = 6  # Confirmation


class ConversationStarted(DomainEvent):
    """Evento: conversa de suporte iniciada."""

    def __init__(self, conversation_id: ConversationId, user_id: UserId):
        super().__init__()
        self.conversation_id = conversation_id
        self.user_id = user_id


class ConversationCompleted(DomainEvent):
    """Evento: conversa concluída com sucesso."""

    def __init__(self, conversation_id: ConversationId, ticket_id: TicketId):
        super().__init__()
        self.conversation_id = conversation_id
        self.ticket_id = ticket_id


class ConversationCancelled(DomainEvent):
    """Evento: conversa cancelada."""

    def __init__(self, conversation_id: ConversationId, reason: str):
        super().__init__()
        self.conversation_id = conversation_id
        self.reason = reason


class ConversationBusinessRuleError(Exception):
    """Erro de regra de negócio da conversa."""
    pass


class SupportConversation(AggregateRoot[ConversationId]):
    """
    Entidade SupportConversation.

    Gerencia o estado de uma conversa de formulário de suporte,
    incluindo os dados coletados em cada passo.
    """

    def __init__(self, conversation_id: Optional[ConversationId], user: User):
        if conversation_id is None:
            conversation_id = ConversationId.generate()

        super().__init__(conversation_id)

        self._user = user
        self._state = ConversationState.CATEGORY_SELECTION
        self._current_step = ConversationStep.STEP_1
        self._form_data: Dict[str, Any] = {}
        self._is_active = True
        self._completed_at: Optional[datetime] = None
        self._ticket_id: Optional[TicketId] = None

        # Inicializa dados do formulário
        self._form_data = {
            "category": None,
            "game": None,
            "custom_game_name": None,
            "timing": None,
            "description": None,
            "attachments": [],
            "waiting_for_images": False
        }

        # Adiciona evento de início
        self._add_event(ConversationStarted(self.id, user.id))

    # Properties
    @property
    def user(self) -> User:
        """Usuário da conversa."""
        return self._user

    @property
    def state(self) -> ConversationState:
        """Estado atual da conversa."""
        return self._state

    @property
    def current_step(self) -> ConversationStep:
        """Passo atual da conversa."""
        return self._current_step

    @property
    def form_data(self) -> Dict[str, Any]:
        """Dados do formulário."""
        return self._form_data.copy()

    @property
    def is_active(self) -> bool:
        """Se a conversa está ativa."""
        return self._is_active

    @property
    def is_completed(self) -> bool:
        """Se a conversa foi concluída."""
        return self._state == ConversationState.COMPLETED

    @property
    def ticket_id(self) -> Optional[TicketId]:
        """ID do ticket gerado (se concluído)."""
        return self._ticket_id

    # Business operations

    def select_category(self, category_key: str) -> None:
        """
        Seleciona categoria do problema.

        Args:
            category_key: Chave da categoria

        Raises:
            ConversationBusinessRuleError: Se não é o passo correto
        """
        if self._current_step != ConversationStep.STEP_1:
            raise ConversationBusinessRuleError("Não é o momento de selecionar categoria")

        # Valida categoria
        category = TicketCategory.from_string(category_key)

        self._form_data["category"] = category_key
        self._advance_to_step(ConversationStep.STEP_2, ConversationState.GAME_SELECTION)

    def select_game(self, game_key: str, custom_name: str = "") -> None:
        """
        Seleciona jogo afetado.

        Args:
            game_key: Chave do jogo
            custom_name: Nome customizado (para "outro jogo")

        Raises:
            ConversationBusinessRuleError: Se não é o passo correto
        """
        if self._current_step != ConversationStep.STEP_2:
            raise ConversationBusinessRuleError("Não é o momento de selecionar jogo")

        # Valida jogo
        game = GameTitle.from_string(game_key, custom_name)

        self._form_data["game"] = game_key
        if custom_name:
            self._form_data["custom_game_name"] = custom_name

        self._advance_to_step(ConversationStep.STEP_3, ConversationState.TIMING_SELECTION)

    def select_timing(self, timing_key: str) -> None:
        """
        Seleciona quando o problema começou.

        Args:
            timing_key: Chave do timing

        Raises:
            ConversationBusinessRuleError: Se não é o passo correto
        """
        if self._current_step != ConversationStep.STEP_3:
            raise ConversationBusinessRuleError("Não é o momento de selecionar timing")

        # Valida timing
        timing = ProblemTiming.from_string(timing_key)

        self._form_data["timing"] = timing_key
        self._advance_to_step(ConversationStep.STEP_4, ConversationState.DESCRIPTION_INPUT)

    def set_description(self, description: str) -> None:
        """
        Define descrição detalhada do problema.

        Args:
            description: Descrição do problema

        Raises:
            ConversationBusinessRuleError: Se não é o passo correto ou descrição inválida
        """
        if self._current_step != ConversationStep.STEP_4:
            raise ConversationBusinessRuleError("Não é o momento de inserir descrição")

        if not description or len(description.strip()) < 10:
            raise ConversationBusinessRuleError("Descrição deve ter pelo menos 10 caracteres")

        self._form_data["description"] = description.strip()
        self._advance_to_step(ConversationStep.STEP_5, ConversationState.ATTACHMENTS_OPTIONAL)

        # Marca que está aguardando imagens (opcional)
        self._form_data["waiting_for_images"] = True

    def add_attachment(self, attachment: TicketAttachment) -> None:
        """
        Adiciona anexo à conversa.

        Args:
            attachment: Anexo a adicionar

        Raises:
            ConversationBusinessRuleError: Se não é o passo correto ou limite excedido
        """
        if self._current_step != ConversationStep.STEP_5:
            raise ConversationBusinessRuleError("Não é o momento de adicionar anexos")

        attachments = self._form_data.get("attachments", [])
        if len(attachments) >= 3:
            raise ConversationBusinessRuleError("Limite de 3 anexos por ticket")

        attachments.append({
            "file_id": attachment.file_id,
            "filename": attachment.filename,
            "file_path": attachment.file_path,
            "file_size": attachment.file_size
        })

        self._form_data["attachments"] = attachments
        self._touch()

    def skip_attachments(self) -> None:
        """Pula etapa de anexos."""
        if self._current_step != ConversationStep.STEP_5:
            raise ConversationBusinessRuleError("Não é o momento de pular anexos")

        self._form_data["waiting_for_images"] = False
        self._advance_to_step(ConversationStep.STEP_6, ConversationState.CONFIRMATION)

    def proceed_to_confirmation(self) -> None:
        """Prossegue para confirmação."""
        if self._current_step != ConversationStep.STEP_5:
            raise ConversationBusinessRuleError("Não é o momento de confirmar")

        self._form_data["waiting_for_images"] = False
        self._advance_to_step(ConversationStep.STEP_6, ConversationState.CONFIRMATION)

    def confirm_and_create_ticket(self) -> Ticket:
        """
        Confirma e cria ticket a partir dos dados coletados.

        Returns:
            Ticket: Ticket criado

        Raises:
            ConversationBusinessRuleError: Se dados incompletos ou não é o passo correto
        """
        if self._current_step != ConversationStep.STEP_6:
            raise ConversationBusinessRuleError("Não é o momento de confirmar")

        if not self._is_form_complete():
            raise ConversationBusinessRuleError("Formulário incompleto")

        # Cria value objects
        category = TicketCategory.from_string(self._form_data["category"])
        game = GameTitle.from_string(
            self._form_data["game"],
            self._form_data.get("custom_game_name", "")
        )
        timing = ProblemTiming.from_string(self._form_data["timing"])

        # Cria ticket
        from ..entities.ticket import UrgencyLevel
        ticket = Ticket(
            ticket_id=None,  # Será gerado automaticamente
            user=self._user,
            category=category,
            affected_game=game,
            problem_timing=timing,
            description=self._form_data["description"],
            urgency_level=self._determine_urgency_level()
        )

        # Adiciona anexos se houver
        for attachment_data in self._form_data.get("attachments", []):
            attachment = TicketAttachment(
                file_id=attachment_data["file_id"],
                filename=attachment_data["filename"],
                file_path=attachment_data["file_path"],
                file_size=attachment_data["file_size"]
            )
            ticket.add_attachment(attachment)

        # Finaliza conversa
        self._ticket_id = ticket.id
        self._state = ConversationState.COMPLETED
        self._is_active = False
        self._completed_at = datetime.now()

        self._add_event(ConversationCompleted(self.id, ticket.id))
        self._increment_version()

        return ticket

    def cancel(self, reason: str = "Usuário cancelou") -> None:
        """
        Cancela a conversa.

        Args:
            reason: Motivo do cancelamento
        """
        if not self._is_active:
            raise ConversationBusinessRuleError("Conversa já foi finalizada")

        self._state = ConversationState.CANCELLED
        self._is_active = False
        self._completed_at = datetime.now()

        self._add_event(ConversationCancelled(self.id, reason))
        self._increment_version()

    def timeout(self) -> None:
        """Marca conversa como expirada por timeout."""
        self.cancel("Timeout - sem atividade")

    def _advance_to_step(self, step: ConversationStep, state: ConversationState) -> None:
        """Avança para próximo passo."""
        self._current_step = step
        self._state = state
        self._touch()

    def _is_form_complete(self) -> bool:
        """Verifica se formulário está completo."""
        required_fields = ["category", "game", "timing", "description"]
        return all(
            field in self._form_data and self._form_data[field] is not None
            for field in required_fields
        )

    def _determine_urgency_level(self):
        """Determina nível de urgência baseado nos dados."""
        from ..entities.ticket import UrgencyLevel

        # Regras de negócio para urgência
        timing = self._form_data.get("timing", "")
        category = self._form_data.get("category", "")

        # Problemas recentes são mais urgentes
        if timing in ["now", "yesterday"]:
            if category == "connectivity":
                return UrgencyLevel.HIGH
            else:
                return UrgencyLevel.NORMAL

        # Problemas antigos são menos urgentes
        if timing in ["long_time", "always"]:
            return UrgencyLevel.LOW

        return UrgencyLevel.NORMAL

    def get_progress_percentage(self) -> int:
        """Retorna progresso da conversa em porcentagem."""
        step_progress = {
            ConversationStep.STEP_1: 16,  # 1/6
            ConversationStep.STEP_2: 33,  # 2/6
            ConversationStep.STEP_3: 50,  # 3/6
            ConversationStep.STEP_4: 66,  # 4/6
            ConversationStep.STEP_5: 83,  # 5/6
            ConversationStep.STEP_6: 100  # 6/6
        }

        return step_progress.get(self._current_step, 0)

    def get_next_expected_input(self) -> str:
        """Retorna descrição do próximo input esperado."""
        next_inputs = {
            ConversationStep.STEP_1: "Selecione a categoria do problema",
            ConversationStep.STEP_2: "Selecione o jogo afetado",
            ConversationStep.STEP_3: "Informe quando o problema começou",
            ConversationStep.STEP_4: "Descreva detalhadamente o problema",
            ConversationStep.STEP_5: "Adicione anexos (opcional) ou prossiga",
            ConversationStep.STEP_6: "Confirme as informações"
        }

        return next_inputs.get(self._current_step, "Ação desconhecida")

    def to_form_data_json(self) -> str:
        """Serializa dados do formulário para JSON."""
        return json.dumps(self._form_data)

    def __str__(self) -> str:
        return f"SupportConversation({self.id}, {self._state.value}, step {self._current_step.value})"