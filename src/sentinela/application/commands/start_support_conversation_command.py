"""
Command para iniciar conversa de suporte.
"""

from dataclasses import dataclass

from .base import Command


@dataclass(frozen=True)
class StartSupportConversationCommand(Command):
    """
    Command para iniciar uma nova conversa de suporte.

    Attributes:
        user_id: ID do usuário no Telegram
        username: Username do usuário
        user_mention: Mention formatado do usuário
    """
    user_id: int
    username: str
    user_mention: str