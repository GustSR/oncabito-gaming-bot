"""
CPFValidationService - Serviço centralizado para validação de CPF

Este serviço centraliza toda a lógica de validação, formatação e verificação de CPF,
incluindo validação de formato, dígitos verificadores e integração com APIs externas.
"""

import re
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CPFValidationResult:
    """Resultado da validação de CPF"""
    is_valid: bool
    formatted_cpf: str
    clean_cpf: str
    error_message: Optional[str] = None
    validation_details: Optional[Dict] = None

class CPFValidationService:
    """Serviço centralizado para validação de CPF"""

    # CPFs inválidos conhecidos (sequências, etc.)
    INVALID_CPFS = {
        '00000000000', '11111111111', '22222222222', '33333333333',
        '44444444444', '55555555555', '66666666666', '77777777777',
        '88888888888', '99999999999'
    }

    @staticmethod
    def clean_cpf(cpf: str) -> str:
        """
        Remove formatação do CPF (pontos, hífens, espaços)

        Args:
            cpf: CPF com ou sem formatação

        Returns:
            str: CPF apenas com números
        """
        if not cpf:
            return ""
        return re.sub(r'[^\d]', '', str(cpf))

    @staticmethod
    def format_cpf(cpf: str) -> str:
        """
        Formata CPF no padrão XXX.XXX.XXX-XX

        Args:
            cpf: CPF limpo (apenas números)

        Returns:
            str: CPF formatado
        """
        clean = CPFValidationService.clean_cpf(cpf)
        if len(clean) != 11:
            return cpf  # Retorna original se não tiver 11 dígitos

        return f"{clean[:3]}.{clean[3:6]}.{clean[6:9]}-{clean[9:]}"

    @staticmethod
    def validate_cpf_format(cpf: str) -> CPFValidationResult:
        """
        Valida formato e dígitos verificadores do CPF

        Args:
            cpf: CPF a ser validado

        Returns:
            CPFValidationResult: Resultado da validação
        """
        if not cpf:
            return CPFValidationResult(
                is_valid=False,
                formatted_cpf="",
                clean_cpf="",
                error_message="CPF não informado"
            )

        # Limpa o CPF
        clean_cpf = CPFValidationService.clean_cpf(cpf)

        # Verifica se tem 11 dígitos
        if len(clean_cpf) != 11:
            return CPFValidationResult(
                is_valid=False,
                formatted_cpf=cpf,
                clean_cpf=clean_cpf,
                error_message="CPF deve ter 11 dígitos"
            )

        # Verifica se não é uma sequência inválida
        if clean_cpf in CPFValidationService.INVALID_CPFS:
            return CPFValidationResult(
                is_valid=False,
                formatted_cpf=CPFValidationService.format_cpf(clean_cpf),
                clean_cpf=clean_cpf,
                error_message="CPF inválido (sequência não permitida)"
            )

        # Valida dígitos verificadores
        is_valid_digits = CPFValidationService._validate_cpf_digits(clean_cpf)

        if not is_valid_digits:
            return CPFValidationResult(
                is_valid=False,
                formatted_cpf=CPFValidationService.format_cpf(clean_cpf),
                clean_cpf=clean_cpf,
                error_message="CPF inválido (dígitos verificadores incorretos)"
            )

        # CPF válido
        return CPFValidationResult(
            is_valid=True,
            formatted_cpf=CPFValidationService.format_cpf(clean_cpf),
            clean_cpf=clean_cpf,
            validation_details={
                'original_input': cpf,
                'was_formatted': cpf != clean_cpf,
                'validation_method': 'format_and_digits'
            }
        )

    @staticmethod
    def _validate_cpf_digits(cpf: str) -> bool:
        """
        Valida os dígitos verificadores do CPF

        Args:
            cpf: CPF limpo (11 dígitos)

        Returns:
            bool: True se dígitos estão corretos
        """
        if len(cpf) != 11:
            return False

        # Calcula primeiro dígito verificador
        sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digit1 = 11 - (sum1 % 11)
        if digit1 >= 10:
            digit1 = 0

        # Verifica primeiro dígito
        if int(cpf[9]) != digit1:
            return False

        # Calcula segundo dígito verificador
        sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digit2 = 11 - (sum2 % 11)
        if digit2 >= 10:
            digit2 = 0

        # Verifica segundo dígito
        return int(cpf[10]) == digit2

    @staticmethod
    def validate_and_normalize(cpf: str) -> Tuple[bool, str, str]:
        """
        Conveniência para validar e normalizar CPF

        Args:
            cpf: CPF a ser validado

        Returns:
            Tuple[bool, str, str]: (is_valid, clean_cpf, formatted_cpf)
        """
        result = CPFValidationService.validate_cpf_format(cpf)
        return result.is_valid, result.clean_cpf, result.formatted_cpf

    @staticmethod
    def get_validation_error_message(cpf: str) -> Optional[str]:
        """
        Retorna mensagem de erro específica para CPF inválido

        Args:
            cpf: CPF a ser validado

        Returns:
            Optional[str]: Mensagem de erro ou None se válido
        """
        result = CPFValidationService.validate_cpf_format(cpf)
        return result.error_message

    @staticmethod
    def is_valid_cpf(cpf: str) -> bool:
        """
        Verifica rapidamente se CPF é válido

        Args:
            cpf: CPF a ser validado

        Returns:
            bool: True se CPF é válido
        """
        result = CPFValidationService.validate_cpf_format(cpf)
        return result.is_valid

    @staticmethod
    def get_user_friendly_error(cpf: str) -> str:
        """
        Retorna mensagem de erro amigável para o usuário

        Args:
            cpf: CPF que falhou na validação

        Returns:
            str: Mensagem amigável
        """
        result = CPFValidationService.validate_cpf_format(cpf)

        if result.is_valid:
            return "CPF válido"

        error_messages = {
            "CPF não informado": "❌ Por favor, informe seu CPF.",
            "CPF deve ter 11 dígitos": "❌ CPF deve ter 11 dígitos. Exemplo: 123.456.789-00",
            "CPF inválido (sequência não permitida)": "❌ CPF inválido. Sequências como 111.111.111-11 não são aceitas.",
            "CPF inválido (dígitos verificadores incorretos)": "❌ CPF inválido. Verifique se digitou corretamente."
        }

        return error_messages.get(
            result.error_message,
            f"❌ CPF inválido: {result.error_message}"
        )

    @staticmethod
    def compare_cpfs(cpf1: str, cpf2: str) -> bool:
        """
        Compara dois CPFs ignorando formatação

        Args:
            cpf1: Primeiro CPF
            cpf2: Segundo CPF

        Returns:
            bool: True se são o mesmo CPF
        """
        clean1 = CPFValidationService.clean_cpf(cpf1)
        clean2 = CPFValidationService.clean_cpf(cpf2)
        return clean1 == clean2 and len(clean1) == 11

    @staticmethod
    def mask_cpf(cpf: str, show_last_digits: int = 2) -> str:
        """
        Mascara CPF para exibição (XXX.XXX.XXX-XX -> XXX.XXX.XXX-XX)

        Args:
            cpf: CPF a ser mascarado
            show_last_digits: Quantos dígitos finais mostrar

        Returns:
            str: CPF mascarado
        """
        clean = CPFValidationService.clean_cpf(cpf)
        if len(clean) != 11:
            return "CPF inválido"

        # Máscara padrão
        if show_last_digits <= 0:
            return "XXX.XXX.XXX-XX"
        elif show_last_digits >= 11:
            return CPFValidationService.format_cpf(clean)
        else:
            masked = "X" * (11 - show_last_digits) + clean[-show_last_digits:]
            return CPFValidationService.format_cpf(masked)


# Funções de conveniência para manter compatibilidade
def validate_cpf_format(cpf: str) -> bool:
    """Função de conveniência para manter compatibilidade"""
    return CPFValidationService.is_valid_cpf(cpf)

def clean_cpf(cpf: str) -> str:
    """Função de conveniência para manter compatibilidade"""
    return CPFValidationService.clean_cpf(cpf)

def format_cpf(cpf: str) -> str:
    """Função de conveniência para manter compatibilidade"""
    return CPFValidationService.format_cpf(cpf)