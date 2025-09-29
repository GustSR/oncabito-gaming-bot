"""
CPF Value Object.

Representa um CPF válido com validações de domínio.
"""

import re
from dataclasses import dataclass
from .base import ValueObject, ValidationError


@dataclass(frozen=True)
class CPF(ValueObject):
    """
    Value Object para CPF.

    Garante que o CPF está no formato correto e é válido.
    """

    value: str

    def __post_init__(self):
        if not self._is_valid():
            raise ValidationError(
                f"CPF inválido: {self.value}",
                {"cpf": self.value, "type": "invalid_format_or_checksum"}
            )

    @classmethod
    def from_raw(cls, raw_cpf: str) -> "CPF":
        """
        Cria CPF a partir de string bruta (remove formatação).

        Args:
            raw_cpf: CPF com ou sem formatação

        Returns:
            CPF: Instance válida

        Raises:
            ValidationError: Se CPF inválido
        """
        clean_cpf = cls._clean(raw_cpf)
        return cls(clean_cpf)

    @staticmethod
    def _clean(cpf: str) -> str:
        """Remove formatação do CPF, mantendo apenas dígitos."""
        return re.sub(r'[^0-9]', '', cpf)

    def _is_valid(self) -> bool:
        """
        Valida CPF usando algoritmo oficial.

        Returns:
            bool: True se CPF válido
        """
        # Remove formatação
        cpf = self._clean(self.value)

        # Verifica se tem 11 dígitos
        if len(cpf) != 11 or not cpf.isdigit():
            return False

        # Verifica se não é sequência repetida
        if cpf == cpf[0] * 11:
            return False

        # Calcula primeiro dígito verificador
        sum_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digit_1 = 11 - (sum_1 % 11)
        if digit_1 >= 10:
            digit_1 = 0

        # Calcula segundo dígito verificador
        sum_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digit_2 = 11 - (sum_2 % 11)
        if digit_2 >= 10:
            digit_2 = 0

        # Verifica se os dígitos são válidos
        return cpf[9:11] == f"{digit_1}{digit_2}"

    def formatted(self) -> str:
        """
        Retorna CPF formatado (000.000.000-00).

        Returns:
            str: CPF formatado
        """
        cpf = self.value
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    def masked(self) -> str:
        """
        Retorna CPF mascarado para logs (000.000.***-**).

        Returns:
            str: CPF mascarado
        """
        cpf = self.value
        return f"{cpf[:3]}.{cpf[3:6]}.***-**"

    def __str__(self) -> str:
        return self.formatted()

    def __repr__(self) -> str:
        return f"CPF({self.masked()})"