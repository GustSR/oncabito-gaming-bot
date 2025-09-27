"""
AdminService - Serviço centralizado para gestão de administradores do grupo

Este serviço centraliza toda a lógica relacionada aos administradores do grupo Telegram,
incluindo busca, cache, verificação de permissões e isenções automáticas.
"""

import logging
from typing import Set, Dict, Optional
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError

from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID

logger = logging.getLogger(__name__)

class AdminService:
    """Serviço centralizado para gestão de administradores"""

    def __init__(self):
        self._admin_cache: Dict[str, Set[int]] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = timedelta(hours=1)  # Cache por 1 hora

    async def get_group_administrators(self, group_id: Optional[str] = None) -> Set[int]:
        """
        Busca lista de administradores do grupo com cache inteligente

        Args:
            group_id: ID do grupo (usa TELEGRAM_GROUP_ID se não especificado)

        Returns:
            Set[int]: Set com IDs dos administradores
        """
        target_group_id = group_id or TELEGRAM_GROUP_ID

        # Verifica se o cache ainda é válido
        if self._is_cache_valid(target_group_id):
            logger.debug(f"Usando cache de administradores para grupo {target_group_id}")
            return self._admin_cache[target_group_id]

        try:
            logger.info(f"Buscando administradores do grupo {target_group_id}")
            bot = Bot(token=TELEGRAM_TOKEN)

            administrators = await bot.get_chat_administrators(target_group_id)
            admin_ids = {admin.user.id for admin in administrators if not admin.user.is_bot}

            # Atualiza o cache
            self._admin_cache[target_group_id] = admin_ids
            self._cache_timestamp = datetime.now()

            logger.info(f"Encontrados {len(admin_ids)} administradores no grupo {target_group_id}")
            return admin_ids

        except TelegramError as e:
            logger.error(f"Erro do Telegram ao buscar administradores: {e}")
            # Retorna cache antigo se disponível, senão set vazio
            return self._admin_cache.get(target_group_id, set())
        except Exception as e:
            logger.error(f"Erro ao buscar administradores do grupo: {e}")
            return self._admin_cache.get(target_group_id, set())

    def _is_cache_valid(self, group_id: str) -> bool:
        """Verifica se o cache ainda é válido"""
        return (
            group_id in self._admin_cache and
            self._cache_timestamp and
            datetime.now() - self._cache_timestamp < self._cache_duration
        )

    async def is_user_admin(self, user_id: int, group_id: Optional[str] = None) -> bool:
        """
        Verifica se um usuário é administrador do grupo

        Args:
            user_id: ID do usuário
            group_id: ID do grupo (usa TELEGRAM_GROUP_ID se não especificado)

        Returns:
            bool: True se o usuário é administrador
        """
        admin_ids = await self.get_group_administrators(group_id)
        return user_id in admin_ids

    async def filter_non_admins(self, user_ids: Set[int], group_id: Optional[str] = None) -> Set[int]:
        """
        Filtra uma lista de usuários retornando apenas os não-administradores

        Args:
            user_ids: Set de IDs de usuários
            group_id: ID do grupo (usa TELEGRAM_GROUP_ID se não especificado)

        Returns:
            Set[int]: Set com IDs dos usuários não-administradores
        """
        admin_ids = await self.get_group_administrators(group_id)
        return user_ids - admin_ids

    async def should_exempt_from_verification(self, user_id: int, group_id: Optional[str] = None) -> bool:
        """
        Verifica se um usuário deve ser isento de verificações automáticas

        Args:
            user_id: ID do usuário
            group_id: ID do grupo (usa TELEGRAM_GROUP_ID se não especificado)

        Returns:
            bool: True se deve ser isento (é administrador)
        """
        return await self.is_user_admin(user_id, group_id)

    def clear_cache(self, group_id: Optional[str] = None):
        """
        Limpa o cache de administradores

        Args:
            group_id: ID do grupo específico ou None para limpar todo cache
        """
        if group_id:
            self._admin_cache.pop(group_id, None)
            logger.debug(f"Cache limpo para grupo {group_id}")
        else:
            self._admin_cache.clear()
            self._cache_timestamp = None
            logger.debug("Cache de administradores completamente limpo")

    async def get_admin_stats(self, group_id: Optional[str] = None) -> Dict[str, any]:
        """
        Retorna estatísticas dos administradores

        Args:
            group_id: ID do grupo (usa TELEGRAM_GROUP_ID se não especificado)

        Returns:
            Dict: Estatísticas dos administradores
        """
        target_group_id = group_id or TELEGRAM_GROUP_ID
        admin_ids = await self.get_group_administrators(target_group_id)

        return {
            'total_admins': len(admin_ids),
            'admin_ids': list(admin_ids),
            'cache_valid': self._is_cache_valid(target_group_id),
            'last_updated': self._cache_timestamp.isoformat() if self._cache_timestamp else None
        }


# Instância global do serviço
admin_service = AdminService()


# Funções de conveniência para manter compatibilidade
async def get_group_administrators(group_id: Optional[str] = None) -> Set[int]:
    """Função de conveniência para manter compatibilidade"""
    return await admin_service.get_group_administrators(group_id)

async def is_user_admin(user_id: int, group_id: Optional[str] = None) -> bool:
    """Função de conveniência para manter compatibilidade"""
    return await admin_service.is_user_admin(user_id, group_id)