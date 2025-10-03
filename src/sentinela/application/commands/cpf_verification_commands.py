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


# NOTE: ResolveCPFDuplicateCommand e RemapCPFToNewUserCommand foram removidos
# pois não possuem handlers implementados. Funcionalidade será implementada
# futuramente quando houver necessidade de negócio.
# Por enquanto, conflitos de CPF são tratados pelo DuplicateCPFService via eventos.

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


@dataclass(frozen=True)
class ProcessExpiredVerificationsCommand(Command):
    """
    Comando para processar verificações expiradas.

    Attributes:
        cleanup_days_old: Dias para considerar verificações muito antigas para limpeza
    """
    cleanup_days_old: int = 30