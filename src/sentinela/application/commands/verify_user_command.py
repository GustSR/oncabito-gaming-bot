"""
Command para processar verificação de usuário.

Usado quando um usuário fornece CPF para verificação de conta.
"""

from dataclasses import dataclass

from .base import Command


@dataclass(frozen=True)
class VerifyUserCommand(Command):
    """
    Command para verificar e processar usuário via CPF.

    Attributes:
        cpf: CPF do usuário (já validado)
        user_id: ID do usuário no Telegram
        username: Username do usuário no Telegram
    """
    cpf: str
    user_id: int
    username: str