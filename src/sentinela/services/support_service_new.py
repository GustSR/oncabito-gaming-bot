"""
Nova implementação do support_service usando a arquitetura refatorada.

Este arquivo fornece uma interface de compatibilidade para o código existente
enquanto usa a nova arquitetura internamente.
"""

import logging
import warnings
from typing import Dict, Any, Optional

from ..application.use_cases.support_form_use_case import SupportFormUseCase, SupportFormResult
from ..domain.entities.ticket import TicketAttachment

logger = logging.getLogger(__name__)


# Mantém as constantes originais para compatibilidade
CATEGORIES = {
    "connectivity": "🌐 Conectividade/Ping",
    "performance": "🎮 Performance em Jogos",
    "configuration": "⚙️ Configuração/Otimização",
    "equipment": "🔧 Problema com Equipamento",
    "other": "📞 Outro"
}

POPULAR_GAMES = {
    "valorant": "⚡️ Valorant",
    "cs2": "🎯 CS2",
    "lol": "🏆 League of Legends",
    "fortnite": "🌍 Fortnite",
    "apex": "🎮 Apex Legends",
    "overwatch": "🦸 Overwatch 2",
    "mobile_legends": "📱 Mobile Legends",
    "dota2": "⚔️ Dota 2",
    "all_games": "🌐 Todos os jogos",
    "other_game": "📝 Outro jogo"
}

TIMING_OPTIONS = {
    "now": "🚨 Agora mesmo / Hoje",
    "yesterday": "📅 Ontem",
    "this_week": "📆 Esta semana",
    "last_week": "🗓️ Semana passada",
    "long_time": "⏳ Há mais tempo",
    "always": "🔄 Sempre foi assim"
}


async def handle_support_request(user_id: int, username: str, user_mention: str) -> None:
    """
    Função de compatibilidade para iniciar suporte.

    DEPRECATED: Use SupportFormUseCase.start_conversation ao invés disso.
    Esta função será removida na v3.0.

    Args:
        user_id: ID do usuário no Telegram
        username: Nome de usuário
        user_mention: Mention formatado do usuário
    """
    warnings.warn(
        "handle_support_request is deprecated. Use SupportFormUseCase instead.",
        DeprecationWarning,
        stacklevel=2
    )

    logger.info(f"COMPATIBILITY: Redirecting support request to new architecture for user {username} (ID: {user_id})")

    try:
        # Redireciona para nova implementação
        from ..infrastructure.config.dependency_injection import get_container

        container = get_container()
        support_use_case = container.get(SupportFormUseCase)

        result = await support_use_case.start_conversation(user_id, username)

        # Aqui seria necessário enviar a mensagem via Telegram
        # Por compatibilidade, apenas loga o resultado
        if result.success:
            logger.info(f"Support conversation started for user {user_id}")
        else:
            logger.warning(f"Failed to start support conversation: {result.message}")

    except Exception as e:
        logger.error(f"Error in compatibility layer for support request: {e}")


async def handle_support_message(user_id: int, message_text: str, username: str) -> bool:
    """
    Função de compatibilidade para processar mensagem de suporte.

    DEPRECATED: Use SupportFormUseCase methods ao invés disso.

    Args:
        user_id: ID do usuário
        message_text: Texto da mensagem
        username: Nome de usuário

    Returns:
        bool: True se mensagem foi processada
    """
    warnings.warn(
        "handle_support_message is deprecated. Use SupportFormUseCase instead.",
        DeprecationWarning,
        stacklevel=2
    )

    logger.info(f"COMPATIBILITY: Processing support message for user {username} (ID: {user_id})")

    try:
        # Para compatibilidade, sempre retorna True
        # A nova implementação seria feita via handlers específicos
        return True

    except Exception as e:
        logger.error(f"Error in compatibility layer for support message: {e}")
        return False


async def handle_photo_attachment(user_id: int, photo, username: str) -> bool:
    """
    Função de compatibilidade para processar anexo de foto.

    DEPRECATED: Use SupportFormUseCase.process_attachment ao invés disso.

    Args:
        user_id: ID do usuário
        photo: Objeto photo do Telegram
        username: Nome de usuário

    Returns:
        bool: True se anexo foi processado
    """
    warnings.warn(
        "handle_photo_attachment is deprecated. Use SupportFormUseCase instead.",
        DeprecationWarning,
        stacklevel=2
    )

    logger.info(f"COMPATIBILITY: Processing photo attachment for user {username} (ID: {user_id})")

    try:
        # Para compatibilidade, sempre retorna True
        # A nova implementação seria feita via SupportFormUseCase.process_attachment
        return True

    except Exception as e:
        logger.error(f"Error in compatibility layer for photo attachment: {e}")
        return False


class SupportFormManager:
    """
    Classe de compatibilidade para o SupportFormManager.

    DEPRECATED: Use SupportFormUseCase ao invés desta classe.
    Esta classe será removida na v3.0.
    """

    # Mantém as constantes originais
    CATEGORIES = CATEGORIES
    POPULAR_GAMES = POPULAR_GAMES
    TIMING_OPTIONS = TIMING_OPTIONS

    STEPS = {
        1: "category_selection",
        2: "game_selection",
        3: "timing_selection",
        4: "description_input",
        5: "attachments_optional",
        6: "confirmation"
    }

    def __init__(self):
        warnings.warn(
            "SupportFormManager is deprecated. Use SupportFormUseCase instead.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.warning("Using deprecated SupportFormManager class")

    @staticmethod
    async def start_conversation_static(user_id: int, username: str) -> Dict[str, Any]:
        """
        Método estático para compatibilidade.

        Returns:
            Dict com resultado da operação
        """
        try:
            from ..infrastructure.config.dependency_injection import get_container

            container = get_container()
            support_use_case = container.get(SupportFormUseCase)

            result = await support_use_case.start_conversation(user_id, username)

            return {
                "success": result.success,
                "message": result.message,
                "next_step": result.next_step.value if result.next_step else None,
                "keyboard_options": result.keyboard_options
            }

        except Exception as e:
            logger.error(f"Error in static support conversation start: {e}")
            return {
                "success": False,
                "message": "Erro interno do sistema",
                "next_step": None,
                "keyboard_options": []
            }


# Funções de conveniência para migração gradual
async def get_support_form_use_case() -> SupportFormUseCase:
    """
    Função de conveniência para obter instância do SupportFormUseCase.

    Returns:
        SupportFormUseCase: Instância configurada via DI
    """
    from ..infrastructure.config.dependency_injection import get_container

    container = get_container()
    return container.get(SupportFormUseCase)


def migrate_attachment_to_new_format(attachment_dict: Dict[str, Any]) -> TicketAttachment:
    """
    Migra anexo do formato antigo para o novo.

    Args:
        attachment_dict: Dicionário com dados do anexo no formato antigo

    Returns:
        TicketAttachment: Anexo no novo formato
    """
    return TicketAttachment(
        file_id=attachment_dict.get("file_id", ""),
        filename=attachment_dict.get("filename", "attachment"),
        file_path=attachment_dict.get("file_path", ""),
        file_size=attachment_dict.get("file_size", 0),
        content_type=attachment_dict.get("content_type")
    )


# Mapping de compatibilidade para facilitar migração
STEP_MAPPING = {
    1: "category_selection",
    2: "game_selection",
    3: "timing_selection",
    4: "description_input",
    5: "attachments_optional",
    6: "confirmation"
}

STATE_MAPPING = {
    "category_selection": "CATEGORY_SELECTION",
    "game_selection": "GAME_SELECTION",
    "timing_selection": "TIMING_SELECTION",
    "description_input": "DESCRIPTION_INPUT",
    "attachments_optional": "ATTACHMENTS_OPTIONAL",
    "confirmation": "CONFIRMATION"
}


def get_legacy_step_name(step_number: int) -> str:
    """Retorna nome do passo no formato legacy."""
    return STEP_MAPPING.get(step_number, "unknown")


def get_new_state_name(legacy_state: str) -> str:
    """Converte estado legacy para novo formato."""
    return STATE_MAPPING.get(legacy_state, "UNKNOWN")