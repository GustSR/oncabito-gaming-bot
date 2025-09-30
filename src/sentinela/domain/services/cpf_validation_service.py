"""
CPF Validation Service.

Serviço de domínio para validação de CPF.
"""

import logging
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)


class CPFValidationService:
    """Serviço para validação de CPF."""

    @staticmethod
    def validate_cpf(cpf: str) -> bool:
        """
        Valida um CPF usando o algoritmo oficial.

        Args:
            cpf: CPF a ser validado (apenas números)

        Returns:
            True se válido, False caso contrário
        """
        # Remove formatação
        cpf_clean = ''.join(filter(str.isdigit, cpf))

        # Verifica se tem 11 dígitos
        if len(cpf_clean) != 11:
            return False

        # Verifica se não são todos iguais
        if cpf_clean == cpf_clean[0] * 11:
            return False

        # Validação do primeiro dígito verificador
        sum1 = 0
        for i in range(9):
            sum1 += int(cpf_clean[i]) * (10 - i)

        remainder1 = sum1 % 11
        digit1 = 0 if remainder1 < 2 else 11 - remainder1

        if int(cpf_clean[9]) != digit1:
            return False

        # Validação do segundo dígito verificador
        sum2 = 0
        for i in range(10):
            sum2 += int(cpf_clean[i]) * (11 - i)

        remainder2 = sum2 % 11
        digit2 = 0 if remainder2 < 2 else 11 - remainder2

        if int(cpf_clean[10]) != digit2:
            return False

        return True

    @staticmethod
    def format_cpf(cpf: str) -> str:
        """
        Formata CPF para exibição.

        Args:
            cpf: CPF (apenas números)

        Returns:
            CPF formatado (XXX.XXX.XXX-XX)
        """
        cpf_clean = ''.join(filter(str.isdigit, cpf))

        if len(cpf_clean) != 11:
            return cpf

        return f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:]}"

    @staticmethod
    def mask_cpf(cpf: str, mask_middle: bool = True) -> str:
        """
        Mascara CPF para logs e exibição segura.

        Args:
            cpf: CPF a ser mascarado
            mask_middle: Se deve mascarar o meio (True) ou só o final (False)

        Returns:
            CPF mascarado
        """
        cpf_clean = ''.join(filter(str.isdigit, cpf))

        if len(cpf_clean) != 11:
            return "CPF_INVÁLIDO"

        if mask_middle:
            return f"{cpf_clean[:3]}***{cpf_clean[-2:]}"
        else:
            return f"{cpf_clean[:6]}***{cpf_clean[-2:]}"

    @staticmethod
    def hash_cpf(cpf: str, salt: Optional[str] = None) -> str:
        """
        Gera hash do CPF para armazenamento seguro.

        Args:
            cpf: CPF a ser hasheado
            salt: Salt opcional para o hash

        Returns:
            Hash SHA-256 do CPF
        """
        cpf_clean = ''.join(filter(str.isdigit, cpf))

        if salt:
            cpf_with_salt = f"{cpf_clean}{salt}"
        else:
            cpf_with_salt = cpf_clean

        return hashlib.sha256(cpf_with_salt.encode()).hexdigest()

    @staticmethod
    def verify_cpf_hash(cpf: str, cpf_hash: str, salt: Optional[str] = None) -> bool:
        """
        Verifica se um CPF corresponde a um hash.

        Args:
            cpf: CPF a ser verificado
            cpf_hash: Hash para comparação
            salt: Salt usado no hash original

        Returns:
            True se corresponde, False caso contrário
        """
        generated_hash = CPFValidationService.hash_cpf(cpf, salt)
        return generated_hash == cpf_hash

    @staticmethod
    def extract_info_from_cpf(cpf: str) -> dict:
        """
        Extrai informações básicas do CPF.

        Args:
            cpf: CPF a ser analisado

        Returns:
            Dicionário com informações extraídas
        """
        cpf_clean = ''.join(filter(str.isdigit, cpf))

        if len(cpf_clean) != 11:
            return {"valid": False, "error": "CPF deve ter 11 dígitos"}

        if not CPFValidationService.validate_cpf(cpf_clean):
            return {"valid": False, "error": "CPF inválido"}

        # Região fiscal baseada no 9º dígito
        region_digit = int(cpf_clean[8])
        regions = {
            0: "Rio Grande do Sul",
            1: "Distrito Federal, Goiás, Mato Grosso, Mato Grosso do Sul, Tocantins",
            2: "Pará, Amazonas, Acre, Amapá, Rondônia, Roraima",
            3: "Ceará, Maranhão, Piauí",
            4: "Pernambuco, Rio Grande do Norte, Paraíba, Alagoas",
            5: "Bahia, Sergipe",
            6: "Minas Gerais",
            7: "Rio de Janeiro, Espírito Santo",
            8: "São Paulo",
            9: "Paraná, Santa Catarina"
        }

        return {
            "valid": True,
            "cpf_clean": cpf_clean,
            "cpf_formatted": CPFValidationService.format_cpf(cpf_clean),
            "cpf_masked": CPFValidationService.mask_cpf(cpf_clean),
            "region_code": region_digit,
            "region_name": regions.get(region_digit, "Região desconhecida")
        }