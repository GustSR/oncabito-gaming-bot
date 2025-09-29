"""
Handler para comando de verificação de usuário.
"""

import logging
from typing import Optional

from .verify_user_command import VerifyUserCommand
from ...domain.repositories.user_repository import UserRepository
from ...domain.value_objects.cpf import CPF
from ...domain.value_objects.user_id import UserId
from ...domain.entities.user import User
from ...infrastructure.external_services.hubsoft_client import HubSoftClient
from ...infrastructure.external_services.group_client import GroupClient
from ...infrastructure.external_services.invite_client import InviteClient

logger = logging.getLogger(__name__)


class UserVerificationResult:
    """
    Resultado da verificação de usuário.
    """
    def __init__(self, success: bool, message: str, user: Optional[User] = None):
        self.success = success
        self.message = message
        self.user = user


class VerifyUserHandler:
    """
    Handler para processar verificação de usuário.

    Implementa a lógica de negócio para:
    1. Verificar se usuário já está no grupo
    2. Buscar dados via HubSoft API
    3. Criar/atualizar usuário
    4. Gerar convite se necessário
    """

    def __init__(
        self,
        user_repository: UserRepository,
        hubsoft_client: HubSoftClient,
        group_client: GroupClient,
        invite_client: InviteClient
    ):
        self._user_repository = user_repository
        self._hubsoft_client = hubsoft_client
        self._group_client = group_client
        self._invite_client = invite_client

    async def handle(self, command: VerifyUserCommand) -> UserVerificationResult:
        """
        Processa a verificação do usuário.

        Args:
            command: Comando com dados de verificação

        Returns:
            UserVerificationResult: Resultado da verificação
        """
        logger.info(f"Iniciando verificação para usuário {command.username} (ID: {command.user_id})")

        try:
            # Criar value objects
            user_id = UserId(command.user_id)
            cpf = CPF.from_raw(command.cpf)

            # Passo 1: Verificar se já está no grupo
            logger.info(f"Verificando se usuário {command.user_id} já está no grupo...")
            is_already_member = await self._group_client.is_user_in_group(command.user_id)

            if is_already_member:
                logger.info(f"Usuário {command.user_id} já está no grupo.")
                return UserVerificationResult(
                    success=True,
                    message=self._format_already_member_message()
                )

            # Passo 2: Buscar dados via HubSoft
            logger.info(f"Buscando dados do cliente via API HubSoft...")
            client_data = await self._hubsoft_client.get_client_data(cpf.value)

            if not client_data:
                logger.warning(f"Cliente não encontrado ou sem serviço ativo para {command.username} (ID: {command.user_id})")
                return UserVerificationResult(
                    success=False,
                    message="❌ Não encontrei um contrato ativo para o CPF informado. Por favor, verifique os dados ou entre em contato com o suporte."
                )

            logger.info(f"Cliente encontrado para {command.username} (ID: {command.user_id})")

            # Passo 3: Criar/atualizar usuário no sistema
            user = await self._create_or_update_user(user_id, command.username, cpf, client_data)

            if not user:
                logger.error(f"Falha ao criar/atualizar usuário {command.username} (ID: {command.user_id})")
                return UserVerificationResult(
                    success=False,
                    message="❌ Erro interno ao processar dados. Tente novamente mais tarde."
                )

            # Passo 4: Tentar criar convite
            logger.info(f"Criando link temporário para o grupo...")
            invite_link = await self._invite_client.create_temporary_invite_link(
                command.user_id,
                command.username or f"user_{command.user_id}"
            )

            if invite_link:
                # Sucesso - envia link
                logger.info(f"Link de convite criado com sucesso para {command.username} (ID: {command.user_id})")
                return UserVerificationResult(
                    success=True,
                    message=self._format_success_with_link_message(invite_link),
                    user=user
                )
            else:
                # Falha na criação do link - envia dados detalhados
                logger.warning(f"Falha ao criar link. Enviando dados detalhados para {command.username} (ID: {command.user_id})")
                return UserVerificationResult(
                    success=True,
                    message=self._format_client_info_message(client_data),
                    user=user
                )

        except Exception as e:
            logger.error(f"Erro durante verificação de usuário: {e}")
            return UserVerificationResult(
                success=False,
                message="❌ Erro interno durante verificação. Tente novamente mais tarde."
            )

    async def _create_or_update_user(
        self,
        user_id: UserId,
        username: str,
        cpf: CPF,
        client_data: dict
    ) -> Optional[User]:
        """
        Cria ou atualiza usuário no repositório.

        Args:
            user_id: ID do usuário
            username: Username do Telegram
            cpf: CPF validado
            client_data: Dados do cliente do HubSoft

        Returns:
            User: Usuário criado/atualizado ou None se erro
        """
        try:
            # Verifica se usuário já existe
            existing_user = await self._user_repository.find_by_id(user_id)

            if existing_user:
                # Atualiza dados existentes
                existing_user.update_client_data(client_data)
                await self._user_repository.save(existing_user)
                logger.info(f"Usuário {user_id} atualizado com sucesso")
                return existing_user
            else:
                # Cria novo usuário
                client_name = client_data.get('nome_razaosocial', '')
                user = User(
                    user_id=user_id,
                    username=username,
                    cpf=cpf,
                    client_name=client_name
                )

                # Adiciona informações de serviço
                user.update_client_data(client_data)

                await self._user_repository.save(user)
                logger.info(f"Usuário {user_id} criado com sucesso")
                return user

        except Exception as e:
            logger.error(f"Erro ao criar/atualizar usuário: {e}")
            return None

    def _format_already_member_message(self) -> str:
        """Formata mensagem para usuário que já é membro."""
        return (
            f"🎮 <b>VOCÊ JÁ ESTÁ NA COMUNIDADE!</b> 🎮\n\n"
            f"✅ Detectamos que você já faz parte do <b>Grupo Gamer OnCabo</b>!\n\n"
            f"🔥 <b>APROVEITE TODOS OS BENEFÍCIOS:</b>\n"
            f"• Dicas exclusivas de gaming\n"
            f"• Suporte prioritário\n"
            f"• Promoções especiais\n"
            f"• Comunidade de gamers\n\n"
            f"🚀 <b>Continue aproveitando sua experiência gamer com a OnCabo!</b>\n\n"
            f"💬 Caso tenha alguma dúvida, fale diretamente no grupo."
        )

    def _format_success_with_link_message(self, invite_link: str) -> str:
        """Formata mensagem de sucesso com link de convite."""
        return (
            f"🎮 <b>PARABÉNS, GAMER!</b> 🎮\n\n"
            f"✅ Seu contrato foi <b>verificado com sucesso</b>!\n\n"
            f"🔥 <b>ACESSO LIBERADO</b> para a Comunidade Gamer OnCabo!\n\n"
            f"🔗 <b>CLIQUE NO LINK ABAIXO:</b>\n{invite_link}\n\n"
            f"⚠️ <b>Importante:</b>\n"
            f"• Link temporário com validade limitada\n"
            f"• Use apenas uma vez\n"
            f"• Após entrar, você terá acesso permanente\n\n"
            f"🚀 <b>Bem-vindo à família OnCabo Gamer!</b>"
        )

    def _format_client_info_message(self, client_data: dict) -> str:
        """Formata mensagem com informações do cliente."""
        # Esta seria a lógica do client_info_service.format_client_service_info
        # Por enquanto, retorna mensagem básica
        client_name = client_data.get('nome_razaosocial', 'Cliente')
        return (
            f"✅ <b>Verificação concluída!</b>\n\n"
            f"👤 <b>Cliente:</b> {client_name}\n"
            f"📋 Entre em contato com o suporte para mais informações."
        )