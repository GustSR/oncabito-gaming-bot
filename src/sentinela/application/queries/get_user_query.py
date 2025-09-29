"""
Get User Query.

Query para buscar usuário por ID.
"""

from dataclasses import dataclass
from ...domain.value_objects.identifiers import UserId


@dataclass(frozen=True)
class GetUserQuery:
    """
    Query para buscar usuário por ID.

    Args:
        user_id: ID do usuário a buscar
    """

    user_id: int

    def to_domain_id(self) -> UserId:
        """
        Converte para objeto de domínio.

        Returns:
            UserId: ID validado

        Raises:
            ValidationError: Se ID inválido
        """
        return UserId(self.user_id)