"""
Command para criar ticket de suporte.
"""

from dataclasses import dataclass
from typing import List, Optional

from ..base import Command


@dataclass(frozen=True)
class TicketAttachmentData:
    """Dados de anexo do ticket."""
    file_id: str
    filename: str
    file_path: str
    file_size: int
    content_type: Optional[str] = None


@dataclass(frozen=True)
class CreateTicketCommand(Command):
    """
    Command para criar um novo ticket de suporte.

    Attributes:
        user_id: ID do usuário no Telegram
        category: Categoria do problema
        affected_game: Jogo afetado
        custom_game_name: Nome do jogo customizado (se "outro jogo")
        problem_timing: Quando o problema começou
        description: Descrição detalhada do problema
        attachments: Lista de anexos
        urgency_level: Nível de urgência (opcional)
        telegram_message_id: ID da mensagem no Telegram (opcional)
        topic_thread_id: ID do tópico (opcional)
    """
    user_id: int
    category: str
    affected_game: str
    problem_timing: str
    description: str
    custom_game_name: Optional[str] = None
    attachments: List[TicketAttachmentData] = None
    urgency_level: str = "normal"
    telegram_message_id: Optional[int] = None
    topic_thread_id: Optional[int] = None

    def __post_init__(self):
        # Inicializa lista vazia se None
        if self.attachments is None:
            object.__setattr__(self, 'attachments', [])