"""
Permission Domain Service.

Serviço de domínio que implementa as regras de negócio
relacionadas a permissões e acessos.
"""

import logging
from typing import Set, Optional
from dataclasses import dataclass

from ..value_objects.permission_level import (
    PermissionLevel,
    UserPermissions,
    TopicAccess
)
from ..entities.user import User

logger = logging.getLogger(__name__)


@dataclass
class TopicConfiguration:
    """Configuração de tópicos do grupo."""

    welcome_topic_id: int
    rules_topic_id: int
    support_topic_id: int
    gaming_topic_ids: Set[int]  # Todos os tópicos de gaming


class PermissionDomainService:
    """
    Serviço de domínio para lógica de permissões.

    Implementa as regras de negócio relacionadas a concessão,
    revogação e validação de permissões.
    """

    def __init__(self, topic_config: TopicConfiguration):
        """
        Inicializa o serviço de permissões.

        Args:
            topic_config: Configuração dos tópicos do grupo
        """
        self.topic_config = topic_config

    def can_grant_gaming_access(self, user: User) -> bool:
        """
        Verifica se usuário pode receber acesso aos tópicos de gaming.

        Regras:
        - Usuário deve estar verificado via CPF
        - Usuário não deve estar banido
        - Usuário deve ter aceito as regras

        Args:
            user: Entidade do usuário

        Returns:
            bool: True se pode conceder acesso
        """
        if user.is_banned:
            logger.warning(f"Usuário {user.username} está banido - acesso negado")
            return False

        if not user.is_verified:
            logger.warning(f"Usuário {user.username} não está verificado - acesso negado")
            return False

        # Aqui poderíamos adicionar mais validações:
        # - Verificar se aceitou regras
        # - Verificar tempo mínimo no grupo
        # - Verificar histórico de comportamento

        return True

    def calculate_gaming_topics(self) -> Set[int]:
        """
        Calcula quais tópicos de gaming o usuário deve acessar.

        Returns:
            Set[int]: IDs dos tópicos de gaming
        """
        # Por padrão, concede acesso a todos os tópicos de gaming
        return self.topic_config.gaming_topic_ids

    def create_permissions_for_new_member(self) -> UserPermissions:
        """
        Cria permissões para novo membro do grupo.

        Novos membros começam restritos e só têm acesso
        ao tópico de regras.

        Returns:
            UserPermissions: Permissões do novo membro
        """
        return UserPermissions.create_restricted()

    def create_permissions_after_verification(
        self,
        user: User
    ) -> Optional[UserPermissions]:
        """
        Cria permissões após verificação do usuário.

        Args:
            user: Usuário verificado

        Returns:
            UserPermissions: Novas permissões ou None se não pode conceder
        """
        if not self.can_grant_gaming_access(user):
            return None

        # Calcula tópicos que usuário terá acesso
        gaming_topics = self.calculate_gaming_topics()

        # Adiciona tópico de suporte
        accessible_topics = gaming_topics.union({self.topic_config.support_topic_id})

        # Cria permissões de gamer verificado
        return UserPermissions.create_gamer(topic_access=accessible_topics)

    def should_notify_admins(self, user: User) -> bool:
        """
        Verifica se deve notificar administradores sobre usuário.

        Casos que requerem notificação:
        - Usuário verificado mas bot não conseguiu promover
        - Usuário com comportamento suspeito
        - Primeira verificação do usuário

        Args:
            user: Usuário a verificar

        Returns:
            bool: True se deve notificar
        """
        # Se é a primeira verificação, notifica
        if user.is_verified and not user.verification_count:
            return True

        # Aqui poderíamos adicionar mais lógica:
        # - Detectar comportamento suspeito
        # - Verificar tentativas múltiplas de verificação
        # - Alertar sobre usuários problemáticos

        return False

    def validate_permission_change(
        self,
        current_permissions: UserPermissions,
        new_permissions: UserPermissions,
        requesting_user_level: PermissionLevel
    ) -> bool:
        """
        Valida se uma mudança de permissão é permitida.

        Regras:
        - Apenas admins podem promover para moderador
        - Apenas owner pode promover para admin
        - Não pode rebaixar usuário de nível superior

        Args:
            current_permissions: Permissões atuais
            new_permissions: Permissões desejadas
            requesting_user_level: Nível do usuário solicitante

        Returns:
            bool: True se mudança é permitida
        """
        # Owner pode fazer qualquer mudança
        if requesting_user_level == PermissionLevel.OWNER:
            return True

        # Admin não pode promover para Admin
        if (requesting_user_level == PermissionLevel.ADMIN and
            new_permissions.level == PermissionLevel.ADMIN):
            return False

        # Não pode rebaixar usuário de nível igual ou superior
        level_hierarchy = {
            PermissionLevel.RESTRICTED: 0,
            PermissionLevel.VERIFIED: 1,
            PermissionLevel.GAMER: 2,
            PermissionLevel.MODERATOR: 3,
            PermissionLevel.ADMIN: 4,
            PermissionLevel.OWNER: 5
        }

        current_level_value = level_hierarchy[current_permissions.level]
        requesting_level_value = level_hierarchy[requesting_user_level]

        # Não pode modificar usuário de nível igual ou superior
        if current_level_value >= requesting_level_value:
            return False

        return True

    def get_permission_grant_message(
        self,
        user: User,
        permissions: UserPermissions
    ) -> str:
        """
        Gera mensagem de confirmação de concessão de permissões.

        Args:
            user: Usuário que recebeu permissões
            permissions: Permissões concedidas

        Returns:
            str: Mensagem formatada
        """
        message = f"✅ **Acesso Liberado!**\n\n"
        message += f"👤 **Usuário:** {user.username}\n"
        message += f"🎮 **Nível:** {permissions.level.value.title()}\n\n"

        if permissions.has_gaming_access():
            message += f"🎯 **Você agora tem acesso a:**\n"
            message += f"• 🎮 Tópicos de Gaming\n"
            message += f"• 🎫 Suporte Técnico\n"
            message += f"• 🎧 Setup & Periféricos\n\n"

        message += f"📋 **Suas permissões:**\n"
        message += f"• {'✅' if permissions.can_send_messages else '❌'} Enviar mensagens\n"
        message += f"• {'✅' if permissions.can_send_media else '❌'} Enviar mídias\n"
        message += f"• {'✅' if permissions.can_send_polls else '❌'} Criar enquetes\n\n"

        message += f"🎉 **Bem-vindo à comunidade OnCabo Gaming!**"

        return message

    def get_admin_notification_message(
        self,
        user: User,
        permissions: UserPermissions
    ) -> str:
        """
        Gera mensagem de notificação para administradores.

        Args:
            user: Usuário verificado
            permissions: Permissões concedidas

        Returns:
            str: Mensagem formatada para admins
        """
        message = f"✅ **USUÁRIO VERIFICADO - LIBERAR ACESSO**\n\n"
        message += f"👤 **Usuário:** {user.username}\n"
        message += f"🆔 **ID:** {user.telegram_id}\n"
        message += f"📋 **Status:** Verificado via CPF\n"
        message += f"🎮 **Nível:** {permissions.level.value.title()}\n\n"

        message += f"🔧 **Ação necessária:**\n"
        message += f"• Adicione ao cargo 'Gamer Verificado'\n"
        message += f"• Ou libere acesso aos tópicos manualmente\n\n"

        message += f"🎮 **Tópicos para liberar:**\n"
        message += f"• 🎮 Jogos FPS & Battle Royale\n"
        message += f"• 🧙 RPG & MMORPG\n"
        message += f"• ⚽️ Esportes & Corrida\n"
        message += f"• 🕹 Retro & Indie\n"
        message += f"• 🎧 Setup & Periféricos\n\n"

        message += f"🤖 **Sistema Sentinela - OnCabo**"

        return message