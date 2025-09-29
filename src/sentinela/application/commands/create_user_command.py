"""
Create User Command.

Comando para criação de novos usuários no sistema.
"""

from dataclasses import dataclass
from typing import Optional
from ...domain.value_objects.identifiers import UserId
from ...domain.value_objects.cpf import CPF


@dataclass(frozen=True)
class CreateUserCommand:
    """
    Comando para criar novo usuário.

    Args:
        user_id: ID do usuário (Telegram ID)
        username: Username do Telegram
        cpf: CPF do usuário
        client_name: Nome do cliente
        service_name: Nome do serviço (opcional)
        service_status: Status do serviço (opcional)
    """

    user_id: int
    username: str
    cpf: str
    client_name: str
    service_name: Optional[str] = None
    service_status: Optional[str] = None

    def to_domain_objects(self) -> tuple[UserId, CPF]:
        """
        Converte dados primitivos para objetos de domínio.

        Returns:
            tuple: (UserId, CPF) validados

        Raises:
            ValidationError: Se dados inválidos
        """
        user_id = UserId(self.user_id)
        cpf = CPF.from_raw(self.cpf)
        return user_id, cpf