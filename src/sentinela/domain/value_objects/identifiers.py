"""
Identificadores únicos como Value Objects.

Representa IDs de entidades de forma type-safe.
"""

from dataclasses import dataclass
from typing import Union
from .base import ValueObject, ValidationError


@dataclass(frozen=True)
class UserId(ValueObject):
    """ID único de usuário (Telegram User ID)."""

    value: int

    def __post_init__(self):
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValidationError(
                f"UserId deve ser um inteiro positivo: {self.value}",
                {"user_id": self.value, "type": "invalid_id"}
            )

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True)
class TicketId(ValueObject):
    """ID único de ticket."""

    value: int

    def __post_init__(self):
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValidationError(
                f"TicketId deve ser um inteiro positivo: {self.value}",
                {"ticket_id": self.value, "type": "invalid_id"}
            )

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return self.value

    @classmethod
    def generate(cls) -> 'TicketId':
        """
        Gera um novo TicketId.

        Returns:
            TicketId: Novo ID gerado
        """
        import time
        # Por simplicidade, usa timestamp como ID
        # Em produção, usar UUID ou auto-increment do banco
        return cls(int(time.time() * 1000) % 2147483647)


@dataclass(frozen=True)
class HubSoftId(ValueObject):
    """ID de atendimento no HubSoft."""

    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValidationError(
                f"HubSoftId deve ser uma string não vazia: {self.value}",
                {"hubsoft_id": self.value, "type": "invalid_id"}
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Protocol(ValueObject):
    """
    Protocolo de atendimento.

    Pode ser local (LOC000001) ou do HubSoft (Atendimento - 20250926160819577001).
    """

    value: str
    source: str  # 'local' ou 'hubsoft'

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValidationError(
                f"Protocol deve ser uma string não vazia: {self.value}",
                {"protocol": self.value, "type": "invalid_protocol"}
            )

        if self.source not in ('local', 'hubsoft'):
            raise ValidationError(
                f"Protocol source deve ser 'local' ou 'hubsoft': {self.source}",
                {"source": self.source, "type": "invalid_source"}
            )

    @classmethod
    def local(cls, ticket_id: Union[int, TicketId]) -> "Protocol":
        """
        Cria protocolo local.

        Args:
            ticket_id: ID do ticket

        Returns:
            Protocol: Protocolo no formato LOC000001
        """
        if isinstance(ticket_id, TicketId):
            ticket_id = ticket_id.value

        return cls(f"LOC{ticket_id:06d}", "local")

    @classmethod
    def hubsoft(cls, hubsoft_protocol: str) -> "Protocol":
        """
        Cria protocolo do HubSoft.

        Args:
            hubsoft_protocol: Protocolo original do HubSoft

        Returns:
            Protocol: Protocolo no formato do HubSoft
        """
        if hubsoft_protocol.startswith("Atendimento - "):
            protocol_number = hubsoft_protocol.replace("Atendimento - ", "")
            return cls(f"Atendimento - {protocol_number}", "hubsoft")
        else:
            return cls(hubsoft_protocol, "hubsoft")

    def is_local(self) -> bool:
        """Verifica se é protocolo local."""
        return self.source == "local"

    def is_hubsoft(self) -> bool:
        """Verifica se é protocolo do HubSoft."""
        return self.source == "hubsoft"

    def display(self) -> str:
        """
        Retorna protocolo formatado para exibição.

        Returns:
            str: Protocolo formatado
        """
        return self.value

    def __str__(self) -> str:
        return self.display()


@dataclass(frozen=True)
class ConversationId(ValueObject):
    """
    Identificador único de conversa de suporte.

    Attributes:
        value: Valor numérico do ID
    """
    value: int

    def __post_init__(self):
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValidationError("ConversationId deve ser um número inteiro positivo")

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def generate(cls) -> 'ConversationId':
        """Gera um novo ConversationId."""
        import time
        return cls(int(time.time() * 1000) % 2147483647)