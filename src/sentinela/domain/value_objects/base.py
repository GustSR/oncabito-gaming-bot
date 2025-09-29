"""
Base classes para Value Objects.

Value Objects são objetos imutáveis definidos pelos seus atributos.
Dois value objects são iguais se todos os seus atributos são iguais.
"""

from abc import ABC
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValueObject(ABC):
    """
    Classe base para todos os Value Objects.

    Características:
    - Imutável (frozen=True)
    - Igualdade baseada em valor
    - Sem identidade própria
    """

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))


class DomainError(Exception):
    """Classe base para todos os erros de domínio."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(DomainError):
    """Erro de validação de Value Object."""
    pass