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

    async def get_removal_no_cpf_message(self) -> str:
        """
        Retorna mensagem de remoção por não ter CPF vinculado.

        Returns:
            str: Mensagem formatada
        """
        return (
            "⚠️ **Você foi removido do Grupo Gaming OnCabo**\n\n"
            "🔒 **Motivo:** CPF não vinculado à sua conta\n\n"
            "Identificamos que você não possui CPF vinculado ao seu Telegram ID "
            "no sistema OnCabo Gaming.\n\n"
            "❓ **Por que isso aconteceu?**\n"
            "• O grupo Gaming é exclusivo para clientes verificados\n"
            "• Todos os membros devem ter CPF vinculado para segurança\n"
            "• Você não respondeu à nossa solicitação de CPF em 24 horas\n\n"
            "🔄 **Como retornar ao grupo:**\n\n"
            "1. Entre em contato comigo com /start\n"
            "2. Envie seu CPF (11 dígitos)\n"
            "3. Aguarde validação do plano Gaming OnCabo\n"
            "4. Receba link de acesso temporário (30 min)\n\n"
            "⚠️ **Requisitos:**\n"
            "• Possuir plano **Gaming OnCabo** ativo\n"
            "• CPF válido e cadastrado no HubSoft\n\n"
            "📞 **Precisa de ajuda?**\n"
            "🌐 Site: https://oncabo.net.br\n"
            "💬 WhatsApp: https://wa.me/5511999999999\n"
            "📧 Email: contato@oncabo.net.br\n\n"
            "🙏 **Agradecemos a compreensão!**"
        )

    async def get_removal_no_gaming_plan_message(self, client_name: str = "Cliente") -> str:
        """
        Retorna mensagem de remoção por não ter plano Gaming ativo.

        Args:
            client_name: Nome do cliente

        Returns:
            str: Mensagem formatada
        """
        return (
            f"⚠️ **Você foi removido do Grupo Gaming OnCabo**\n\n"
            f"Olá, {client_name}!\n\n"
            "🔒 **Motivo:** Plano Gaming não está ativo\n\n"
            "Identificamos que você não possui mais o **Plano Gaming OnCabo** ativo "
            "em seu contrato.\n\n"
            "❓ **Por que isso aconteceu?**\n"
            "• O grupo Gaming é exclusivo para clientes com plano Gaming ativo\n"
            "• Nosso sistema verifica periodicamente os contratos no HubSoft\n"
            "• Seu plano Gaming foi cancelado ou migrado para outro plano\n\n"
            "💡 **Quer voltar ao grupo?**\n\n"
            "Para retornar, você precisa contratar novamente o **Plano Gaming OnCabo**.\n\n"
            "🎮 **Benefícios do Plano Gaming:**\n"
            "✅ Latência ultra-baixa para jogos online\n"
            "✅ Prioridade de tráfego para gaming\n"
            "✅ Suporte técnico especializado 24/7\n"
            "✅ Acesso ao grupo exclusivo de gamers\n"
            "✅ Otimização de rota para servidores\n\n"
            "📞 **Entre em contato:**\n"
            "🌐 Site: https://oncabo.net.br\n"
            "💬 WhatsApp: https://wa.me/5511999999999\n"
            "📧 Email: contato@oncabo.net.br\n\n"
            "💼 **Nossa equipe comercial terá prazer em te ajudar!**\n\n"
            "🙏 **Obrigado por ter feito parte do grupo Gaming OnCabo!**"
        )

    async def get_removal_account_choice_message(self, chosen_account: str) -> str:
        """
        Retorna mensagem de remoção devido à escolha de outra conta.

        Args:
            chosen_account: Conta escolhida pelo usuário

        Returns:
            str: Mensagem formatada
        """
        return (
            "⚠️ **Você foi removido do Grupo Gaming OnCabo**\n\n"
            "🔒 **Motivo:** CPF vinculado a outra conta Telegram\n\n"
            "Identificamos que seu CPF está vinculado a múltiplas contas Telegram.\n\n"
            "❓ **O que aconteceu?**\n"
            f"• Você escolheu manter a conta: **{chosen_account}**\n"
            "• Por segurança, apenas 1 conta pode ter acesso ao grupo\n"
            "• Esta conta foi automaticamente removida\n\n"
            "🔄 **Como retornar ao grupo:**\n\n"
            f"**Use a conta escolhida:** {chosen_account}\n\n"
            "1. Entre em contato comigo com /start\n"
            "2. Seu CPF já está vinculado\n"
            "3. Receberá link de acesso automaticamente\n\n"
            "⚠️ **IMPORTANTE:**\n"
            "• Apenas 1 conta Telegram por CPF é permitida\n"
            "• Se precisar trocar de conta, entre em contato novamente\n"
            "• O sistema verificará e permitirá a escolha\n\n"
            "📞 **Precisa de ajuda?**\n"
            "🌐 Site: https://oncabo.net.br\n"
            "💬 WhatsApp: https://wa.me/5511999999999\n\n"
            "🙏 **Agradecemos a compreensão!**"
        )
