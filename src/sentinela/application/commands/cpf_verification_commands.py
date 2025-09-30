"""
Commands para operações de verificação de CPF.

Define os comandos que podem ser executados
no contexto de verificação de CPF.
"""

from dataclasses import dataclass
from typing import Optional

from .base import Command


@dataclass(frozen=True)
class StartCPFVerificationCommand(Command):
    """
    Comando para iniciar uma verificação de CPF.

    Attributes:
        user_id: ID do usuário no Telegram
        username: Nome de usuário
        user_mention: Mention formatado do usuário
        verification_type: Tipo de verificação (auto_checkup, support_request)
        source_action: Ação que originou a verificação
    """
    user_id: int
    username: str
    user_mention: str
    verification_type: str = "auto_checkup"
    source_action: Optional[str] = None


@dataclass(frozen=True)
class SubmitCPFForVerificationCommand(Command):
    """
    Comando para submeter um CPF para verificação.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        cpf: CPF fornecido pelo usuário
    """
    user_id: int
    username: str
    cpf: str


@dataclass(frozen=True)
class CancelCPFVerificationCommand(Command):
    """
    Comando para cancelar uma verificação de CPF.

    Attributes:
        user_id: ID do usuário
        username: Nome de usuário
        reason: Motivo do cancelamento
    """
    user_id: int
    username: str
    reason: str = "Cancelado pelo usuário"


@dataclass(frozen=True)
class ProcessExpiredVerificationsCommand(Command):
    """
    Comando para processar verificações expiradas.

    Este comando é executado por job/scheduler para
    limpar verificações que expiraram.
    """
    pass


@dataclass(frozen=True)
class ResolveCPFDuplicateCommand(Command):
    """
    Comando para resolver conflito de CPF duplicado.

    Attributes:
        cpf: CPF em conflito
        current_user_id: ID do usuário atual
        existing_user_id: ID do usuário que já possui o CPF
        current_username: Nome do usuário atual
        existing_username: Nome do usuário existente
        resolution_action: Ação para resolver (remap, deny, manual_review)
    """
    cpf: str
    current_user_id: int
    existing_user_id: int
    current_username: str
    existing_username: str
    resolution_action: str  # "remap", "deny", "manual_review"


@dataclass(frozen=True)
class RemapCPFToNewUserCommand(Command):
    """
    Comando para remapear um CPF para um novo usuário.

    Attributes:
        cpf: CPF a ser remapeado
        old_user_id: ID do usuário anterior
        new_user_id: ID do novo usuário
        old_username: Nome do usuário anterior
        new_username: Nome do novo usuário
        reason: Motivo do remapeamento
    """
    cpf: str
    old_user_id: int
    new_user_id: int
    old_username: str
    new_username: str
    reason: str


@dataclass(frozen=True)
class GetVerificationStatsCommand(Command):
    """
    Comando para obter estatísticas de verificação.

    Attributes:
        admin_user_id: ID do usuário admin solicitante
        include_details: Se deve incluir detalhes granulares
    """
    admin_user_id: int
    include_details: bool = False