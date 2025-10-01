"""
Member Verification Use Case.

Coordena verificação automática de membros do grupo Gaming.
Garante que todos os membros (exceto admins) têm CPF vinculado.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .base import UseCase, UseCaseResult
from ...domain.repositories.user_repository import UserRepository
from ...domain.value_objects.identifiers import UserId
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class MemberVerificationUseCase(UseCase):
    """
    Use Case para verificação automática de membros do grupo.

    Responsabilidades:
    - Verificar se membros têm CPF vinculado
    - Solicitar CPF de membros sem vínculo
    - Remover membros que não completarem verificação
    - Validar plano Gaming no HubSoft
    """

    def __init__(
        self,
        user_repository: UserRepository,
        event_bus: EventBus
    ):
        """
        Inicializa o use case.

        Args:
            user_repository: Repositório de usuários
            event_bus: Event bus para publicar eventos
        """
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def check_all_members_cpf(
        self,
        group_members: List[Dict[str, Any]],
        admin_ids: List[int]
    ) -> UseCaseResult:
        """
        Verifica CPF de todos os membros do grupo.

        Args:
            group_members: Lista de membros do grupo (do Telegram API)
            admin_ids: Lista de IDs de administradores (não verificar)

        Returns:
            UseCaseResult: Resultado da verificação
        """
        try:
            logger.info(f"Iniciando verificação de CPF de {len(group_members)} membros")

            members_without_cpf = []
            members_to_remove = []
            members_validated = []

            for member in group_members:
                user_id = member.get('user', {}).get('id')
                username = member.get('user', {}).get('username', 'Usuário')

                # Pula administradores
                if user_id in admin_ids:
                    logger.debug(f"Pulando admin: {username} ({user_id})")
                    continue

                # Busca usuário no banco
                user_id_vo = UserId(user_id)
                existing_user = await self.user_repository.find_by_id(user_id_vo)

                if not existing_user or not existing_user.cpf:
                    # Usuário SEM CPF vinculado
                    logger.warning(f"Membro sem CPF: {username} ({user_id})")
                    members_without_cpf.append({
                        'user_id': user_id,
                        'username': username
                    })
                else:
                    # Usuário TEM CPF - valida no HubSoft
                    logger.debug(f"Membro com CPF: {username} ({user_id}) - CPF: {existing_user.cpf.masked_value}")
                    members_validated.append({
                        'user_id': user_id,
                        'username': username,
                        'cpf': existing_user.cpf.value
                    })

            logger.info(
                f"Verificação concluída: "
                f"{len(members_validated)} validados, "
                f"{len(members_without_cpf)} sem CPF"
            )

            return UseCaseResult(
                success=True,
                message="Verificação de membros concluída",
                data={
                    'total_members': len(group_members),
                    'validated': len(members_validated),
                    'without_cpf': len(members_without_cpf),
                    'members_without_cpf': members_without_cpf,
                    'members_validated': members_validated
                }
            )

        except Exception as e:
            logger.error(f"Erro ao verificar membros: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro na verificação: {str(e)}"
            )

    async def validate_member_gaming_plan(
        self,
        cpf: str
    ) -> UseCaseResult:
        """
        Valida se membro ainda possui plano Gaming ativo no HubSoft.

        Args:
            cpf: CPF do membro

        Returns:
            UseCaseResult: Resultado da validação
        """
        try:
            from ...integrations.hubsoft.cliente import check_gaming_plan_by_cpf

            logger.info(f"Validando plano Gaming para CPF {cpf[:3]}***")

            gaming_info = check_gaming_plan_by_cpf(cpf)

            if gaming_info['has_gaming']:
                logger.info(f"CPF {cpf[:3]}*** possui plano Gaming ativo: {gaming_info['plan_name']}")
                return UseCaseResult(
                    success=True,
                    message="Plano Gaming ativo",
                    data=gaming_info
                )
            else:
                logger.warning(f"CPF {cpf[:3]}*** NÃO possui plano Gaming ativo")
                return UseCaseResult(
                    success=False,
                    message="Plano Gaming não encontrado",
                    data=gaming_info
                )

        except Exception as e:
            logger.error(f"Erro ao validar plano Gaming: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro na validação HubSoft: {str(e)}"
            )

    async def get_cpf_verification_message(self) -> str:
        """
        Retorna mensagem padrão para solicitação de CPF.

        Returns:
            str: Mensagem formatada
        """
        return (
            "🔐 **Verificação de Acesso - OnCabo Gaming**\n\n"
            "Olá! Identificamos que você ainda não tem CPF vinculado "
            "à sua conta no grupo Gaming.\n\n"
            "⏰ **Você tem 24 horas para enviar seu CPF.**\n\n"
            "📱 **Como fazer:**\n"
            "Envie apenas números (11 dígitos).\n"
            "Exemplo: 12345678901\n\n"
            "⚠️ **IMPORTANTE:** Se não verificarmos seu CPF em 24 horas, "
            "você será removido do grupo automaticamente por medidas "
            "de segurança.\n\n"
            "🔒 **Seus dados estão seguros e protegidos.**"
        )

    async def get_removal_message(self, reason: str = "sem CPF vinculado") -> str:
        """
        Retorna mensagem de remoção do grupo.

        Args:
            reason: Motivo da remoção

        Returns:
            str: Mensagem formatada
        """
        return (
            f"⚠️ **Remoção do Grupo Gaming**\n\n"
            f"Você foi removido do grupo OnCabo Gaming.\n\n"
            f"**Motivo:** {reason}\n\n"
            "🔄 **Como retornar:**\n"
            "1. Entre em contato comigo pelo comando /start\n"
            "2. Envie seu CPF para verificação\n"
            "3. Aguarde validação do seu plano Gaming\n"
            "4. Receba novo link de acesso\n\n"
            "📞 **Dúvidas?** Entre em contato:\n"
            "🌐 Site: https://oncabo.net.br\n"
            "💬 WhatsApp: https://wa.me/5511999999999"
        )
