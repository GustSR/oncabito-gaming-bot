import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Set
from telegram import Bot
from telegram.constants import ChatMemberStatus

logger = logging.getLogger(__name__)

class AdminDetectionService:
    """
    Serviço para detectar automaticamente administradores do grupo Telegram
    e sincronizar com o sistema de controle de acesso.
    """

    def __init__(self):
        self._last_sync = None
        self._cached_admins = set()
        self._sync_interval = timedelta(hours=6)  # Sincroniza a cada 6 horas

    async def detect_group_administrators(self) -> List[Dict]:
        """
        Detecta todos os administradores do grupo Telegram.

        Returns:
            List[Dict]: Lista de administradores com suas informações
        """
        try:
            from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID

            if not TELEGRAM_GROUP_ID:
                logger.error("TELEGRAM_GROUP_ID não configurado")
                return []

            bot = Bot(token=TELEGRAM_TOKEN)
            async with bot:
                # Obtém todos os administradores do grupo
                chat_administrators = await bot.get_chat_administrators(chat_id=TELEGRAM_GROUP_ID)

                admins = []
                for admin in chat_administrators:
                    user = admin.user

                    # Filtra apenas administradores reais (exclui o próprio bot e canais anônimos)
                    if (not user.is_bot and
                        admin.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and
                        user.id != bot.id):

                        admin_info = {
                            'user_id': user.id,
                            'username': user.username,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'status': admin.status,
                            'detected_at': datetime.now().isoformat()
                        }
                        admins.append(admin_info)

                logger.info(f"Detectados {len(admins)} administradores no grupo")
                return admins

        except Exception as e:
            logger.error(f"Erro ao detectar administradores do grupo: {e}")
            return []

    async def sync_administrators_to_database(self) -> Dict[str, any]:
        """
        Sincroniza administradores detectados com o banco de dados.

        Returns:
            Dict: Resultado da sincronização
        """
        try:
            # Detecta administradores atuais
            current_admins = await self.detect_group_administrators()

            if not current_admins:
                return {
                    "status": "error",
                    "message": "Nenhum administrador detectado ou erro na detecção"
                }

            # Obtém administradores armazenados
            from src.sentinela.clients.db_client import get_stored_administrators, update_administrators

            stored_admins = get_stored_administrators()
            stored_admin_ids = {admin['user_id'] for admin in stored_admins}
            current_admin_ids = {admin['user_id'] for admin in current_admins}

            # Calcula diferenças
            new_admins = [admin for admin in current_admins if admin['user_id'] not in stored_admin_ids]
            removed_admin_ids = stored_admin_ids - current_admin_ids
            unchanged_admin_ids = stored_admin_ids & current_admin_ids

            # Atualiza banco de dados
            update_result = update_administrators(current_admins)

            # Atualiza cache
            self._cached_admins = current_admin_ids
            self._last_sync = datetime.now()

            # Monta resultado
            result = {
                "status": "success",
                "sync_time": self._last_sync.isoformat(),
                "statistics": {
                    "total_current": len(current_admins),
                    "total_stored": len(stored_admins),
                    "new_admins": len(new_admins),
                    "removed_admins": len(removed_admin_ids),
                    "unchanged_admins": len(unchanged_admin_ids)
                },
                "new_admins": new_admins,
                "removed_admin_ids": list(removed_admin_ids),
                "database_updated": update_result
            }

            # Log das mudanças
            if new_admins:
                usernames = [admin.get('username', admin['first_name']) for admin in new_admins]
                logger.info(f"Novos administradores detectados: {', '.join(usernames)}")

            if removed_admin_ids:
                logger.info(f"Administradores removidos: {removed_admin_ids}")

            logger.info(f"Sincronização de administradores concluída: {len(current_admins)} admins ativos")
            return result

        except Exception as e:
            logger.error(f"Erro na sincronização de administradores: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def auto_sync_if_needed(self) -> bool:
        """
        Executa sincronização automática se necessário (baseado no intervalo).

        Returns:
            bool: True se sincronização foi executada, False caso contrário
        """
        try:
            if (self._last_sync is None or
                datetime.now() - self._last_sync > self._sync_interval):

                logger.info("Executando sincronização automática de administradores")
                result = await self.sync_administrators_to_database()
                return result.get("status") == "success"

            return False

        except Exception as e:
            logger.error(f"Erro na sincronização automática: {e}")
            return False

    def get_cached_admin_ids(self) -> Set[int]:
        """
        Retorna IDs dos administradores em cache.

        Returns:
            Set[int]: Conjunto de IDs de administradores
        """
        return self._cached_admins.copy()

    def is_cached_admin(self, user_id: int) -> bool:
        """
        Verifica se um usuário é administrador baseado no cache.

        Args:
            user_id: ID do usuário

        Returns:
            bool: True se é admin, False caso contrário
        """
        return user_id in self._cached_admins

    async def force_refresh_cache(self) -> Dict[str, any]:
        """
        Força atualização do cache de administradores.

        Returns:
            Dict: Resultado da atualização
        """
        logger.info("Forçando atualização do cache de administradores")
        return await self.sync_administrators_to_database()

    def get_last_sync_info(self) -> Dict[str, any]:
        """
        Retorna informações sobre a última sincronização.

        Returns:
            Dict: Informações de sincronização
        """
        return {
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "cached_admin_count": len(self._cached_admins),
            "cached_admin_ids": list(self._cached_admins),
            "sync_interval_hours": self._sync_interval.total_seconds() / 3600
        }

    async def validate_admin_permissions(self, user_id: int) -> Dict[str, any]:
        """
        Valida se um usuário específico ainda tem permissões de administrador.

        Args:
            user_id: ID do usuário para validar

        Returns:
            Dict: Resultado da validação
        """
        try:
            from src.sentinela.core.config import TELEGRAM_TOKEN, TELEGRAM_GROUP_ID

            bot = Bot(token=TELEGRAM_TOKEN)
            async with bot:
                # Verifica status atual do usuário no grupo
                member = await bot.get_chat_member(chat_id=TELEGRAM_GROUP_ID, user_id=user_id)

                is_admin = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

                return {
                    "user_id": user_id,
                    "is_admin": is_admin,
                    "current_status": member.status,
                    "validated_at": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Erro ao validar permissões do usuário {user_id}: {e}")
            return {
                "user_id": user_id,
                "is_admin": False,
                "error": str(e),
                "validated_at": datetime.now().isoformat()
            }

# Instância global do serviço
admin_detection_service = AdminDetectionService()