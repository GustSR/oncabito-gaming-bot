"""
Command para processar passo da conversa de suporte.
"""

from dataclasses import dataclass
from typing import Optional

from ..base import Command


@dataclass(frozen=True)
class ProcessSupportStepCommand(Command):
    """
    Command para processar um passo da conversa de suporte.

    Attributes:
        user_id: ID do usuário no Telegram
        step_data: Dados do passo (categoria, jogo, timing, etc.)
        step_type: Tipo do passo (category, game, timing, description, etc.)
        custom_input: Input customizado (para "outro jogo" ou descrição)
    """
    user_id: int
    step_data: str
    step_type: str
    custom_input: Optional[str] = None