import re
import logging

logger = logging.getLogger(__name__)

def is_valid_cpf_format(cpf: str) -> bool:
    """
    Verifica se a string tem formato válido de CPF.

    Args:
        cpf: String a ser validada

    Returns:
        bool: True se for formato válido de CPF
    """
    if not cpf:
        return False

    # Remove caracteres não numéricos
    cpf_clean = re.sub(r'[^0-9]', '', cpf)

    # Verifica se tem 11 dígitos
    if len(cpf_clean) != 11:
        return False

    # Verifica se não são todos números iguais
    if cpf_clean == cpf_clean[0] * 11:
        return False

    return True

def extract_cpf_from_message(message: str) -> str | None:
    """
    Extrai CPF de uma mensagem de texto.

    Args:
        message: Mensagem do usuário

    Returns:
        str: CPF limpo (apenas números) ou None se não encontrado
    """
    if not message:
        return None

    # Padrões de CPF
    patterns = [
        r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b',  # 123.456.789-01 ou 12345678901
        r'\b\d{11}\b'  # 12345678901
    ]

    for pattern in patterns:
        matches = re.findall(pattern, message)
        for match in matches:
            cpf_clean = re.sub(r'[^0-9]', '', match)
            if is_valid_cpf_format(cpf_clean):
                logger.info(f"CPF válido encontrado na mensagem.")
                return cpf_clean

    logger.warning("Nenhum CPF válido encontrado na mensagem.")
    return None

def is_message_cpf_only(message: str) -> bool:
    """
    Verifica se a mensagem contém apenas um CPF.

    Args:
        message: Mensagem do usuário

    Returns:
        bool: True se a mensagem for apenas um CPF
    """
    cpf = extract_cpf_from_message(message)
    if not cpf:
        return False

    # Remove o CPF da mensagem e verifica se sobra algo relevante
    message_clean = re.sub(r'[^a-zA-Z0-9]', '', message)
    cpf_clean = re.sub(r'[^0-9]', '', cpf)

    return message_clean == cpf_clean