"""
Nova implementação do user_service usando a arquitetura refatorada.

Este arquivo fornece uma interface de compatibilidade para o código existente
enquanto usa a nova arquitetura internamente.
"""

import logging
import warnings
from typing import Optional

from ..presentation.handlers.user_verification_handler import UserVerificationHandlers

logger = logging.getLogger(__name__)


async def process_user_verification(cpf: str, user_id: int, username: str) -> str:
    """
    Função de compatibilidade para processar verificação de usuário.

    DEPRECATED: Use UserVerificationHandlers.handle_user_verification ao invés disso.
    Esta função será removida na v3.0.

    Args:
        cpf: CPF do usuário
        user_id: ID do usuário no Telegram
        username: Username do usuário

    Returns:
        str: Mensagem de resposta

    Note:
        Esta função mantém a mesma interface da versão original
        mas usa a nova arquitetura internamente.
    """
    # Avisa sobre deprecação (pode ser removido depois)
    warnings.warn(
        "process_user_verification is deprecated. Use the new architecture handlers instead.",
        DeprecationWarning,
        stacklevel=2
    )

    logger.info(f"COMPATIBILITY: Redirecting user verification to new architecture for user {username} (ID: {user_id})")

    try:
        # Redireciona para nova implementação
        return await UserVerificationHandlers.handle_user_verification(
            cpf=cpf,
            user_id=user_id,
            username=username
        )

    except Exception as e:
        logger.error(f"Error in compatibility layer for user verification: {e}")
        return "❌ Erro interno durante verificação. Tente novamente mais tarde."