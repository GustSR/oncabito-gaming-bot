"""
Group Management Use Case.

Coordena operações de gerenciamento de membros do grupo,
incluindo adição, remoção e verificação de status.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from ..use_cases.base import UseCase, UseCaseResult
from ...domain.entities.group_member import GroupMember, MemberStatus, MemberRole
from ...domain.repositories.group_member_repository import GroupMemberRepository
from ...domain.repositories.user_repository import UserRepository
from ...domain.value_objects.identifiers import UserId
from ...infrastructure.events.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class MemberCheckResult:
    """Resultado de verificação de membro."""

    is_member: bool
    status: Optional[str] = None
    should_remove: bool = False
    reason: Optional[str] = None


@dataclass
class RemovalResult:
    """Resultado de remoção de membros."""

    success: bool
    removed_count: int
    failed_count: int
    removed_members: List[Dict[str, Any]]
    errors: List[str]


class GroupManagementUseCase(UseCase):
    """
    Use Case para gerenciamento de membros do grupo.

    Coordena verificações, adições e remoções de membros
    baseado em regras de negócio e contratos ativos.
    """

    def __init__(
        self,
        member_repository: GroupMemberRepository,
        user_repository: UserRepository,
        event_bus: EventBus,
        group_id: int
    ):
        """
        Inicializa o use case.

        Args:
            member_repository: Repositório de membros
            user_repository: Repositório de usuários
            event_bus: Event bus para publicar eventos
            group_id: ID do grupo no Telegram
        """
        self.member_repository = member_repository
        self.user_repository = user_repository
        self.event_bus = event_bus
        self.group_id = group_id

    async def check_member_status(
        self,
        telegram_id: int
    ) -> MemberCheckResult:
        """
        Verifica status de um membro no grupo.

        Args:
            telegram_id: ID do usuário no Telegram

        Returns:
            MemberCheckResult: Resultado da verificação
        """
        try:
            logger.info(f"Verificando status do membro {telegram_id}")

            # Busca membro no repositório
            member = await self.member_repository.find_by_telegram_id(telegram_id)

            if not member:
                logger.info(f"Membro {telegram_id} não encontrado no repositório")
                return MemberCheckResult(
                    is_member=False,
                    reason="not_in_database"
                )

            # Verifica se é membro ativo
            is_active = member.is_active_member()

            if not is_active:
                return MemberCheckResult(
                    is_member=False,
                    status=member.status.value,
                    reason="inactive_status"
                )

            # Verifica se tem contrato ativo
            if not member.is_active_contract:
                return MemberCheckResult(
                    is_member=True,
                    status=member.status.value,
                    should_remove=True,
                    reason="inactive_contract"
                )

            return MemberCheckResult(
                is_member=True,
                status=member.status.value,
                should_remove=False
            )

        except Exception as e:
            logger.error(f"Erro ao verificar status do membro {telegram_id}: {e}")
            return MemberCheckResult(
                is_member=False,
                reason="error"
            )

    async def register_new_member(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: str,
        last_name: Optional[str] = None
    ) -> UseCaseResult:
        """
        Registra novo membro no grupo.

        Args:
            telegram_id: ID no Telegram
            username: Nome de usuário
            first_name: Primeiro nome
            last_name: Sobrenome (opcional)

        Returns:
            UseCaseResult: Resultado do registro
        """
        try:
            logger.info(f"Registrando novo membro {telegram_id} (@{username})")

            # Verifica se já existe
            existing_member = await self.member_repository.find_by_telegram_id(telegram_id)

            if existing_member:
                # Atualiza status se estava inativo
                if existing_member.status in [MemberStatus.LEFT, MemberStatus.KICKED]:
                    existing_member.status = MemberStatus.MEMBER
                    existing_member.joined_at = datetime.now()
                    existing_member.left_at = None
                    existing_member.kick_reason = None
                    await self.member_repository.save(existing_member)

                    logger.info(f"Membro {telegram_id} reativado")

                    return UseCaseResult(
                        success=True,
                        message="Membro reativado com sucesso",
                        data={'member_id': existing_member.id.value}
                    )

                return UseCaseResult(
                    success=True,
                    message="Membro já está registrado",
                    data={'member_id': existing_member.id.value}
                )

            # Busca usuário correspondente
            user = await self.user_repository.find_by_telegram_id(telegram_id)

            # Cria novo membro
            user_id = user.id if user else UserId(telegram_id)

            member = GroupMember(
                id=UserId(telegram_id),  # Usando telegram_id como ID temporário
                user_id=user_id,
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                status=MemberStatus.MEMBER,
                role=MemberRole.NEW_MEMBER,
                is_verified=user.is_verified if user else False,
                is_active_contract=True  # Assume ativo inicialmente
            )

            # Salva membro
            saved_member = await self.member_repository.save(member)

            # Publica evento
            from ...domain.events.user_events import UserRegistered

            await self.event_bus.publish(
                UserRegistered(
                    aggregate_id=str(telegram_id),
                    user_id=telegram_id,
                    username=username or first_name,
                    registration_date=datetime.now()
                )
            )

            logger.info(f"Novo membro {telegram_id} registrado com sucesso")

            return UseCaseResult(
                success=True,
                message="Novo membro registrado",
                data={'member_id': saved_member.id.value}
            )

        except Exception as e:
            logger.error(f"Erro ao registrar novo membro {telegram_id}: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao registrar membro: {str(e)}"
            )

    async def remove_member(
        self,
        telegram_id: int,
        reason: str = "Contrato inativo"
    ) -> UseCaseResult:
        """
        Remove membro do grupo.

        Args:
            telegram_id: ID no Telegram
            reason: Motivo da remoção

        Returns:
            UseCaseResult: Resultado da remoção
        """
        try:
            logger.info(f"Removendo membro {telegram_id}. Motivo: {reason}")

            # Busca membro
            member = await self.member_repository.find_by_telegram_id(telegram_id)

            if not member:
                return UseCaseResult(
                    success=False,
                    message="Membro não encontrado"
                )

            # Verifica se pode ser removido
            if not member.can_be_removed():
                return UseCaseResult(
                    success=False,
                    message="Membro não pode ser removido (admin ou já removido)"
                )

            # Marca como removido
            member.mark_as_kicked(reason)

            # Salva alterações
            await self.member_repository.save(member)

            # Publica evento para remoção real no Telegram
            from ...domain.events.user_events import UserBanned

            await self.event_bus.publish(
                UserBanned(
                    aggregate_id=str(telegram_id),
                    user_id=telegram_id,
                    username=member.username or member.first_name,
                    reason=reason,
                    banned_by="system",
                    ban_date=datetime.now()
                )
            )

            logger.info(f"Membro {telegram_id} marcado para remoção")

            return UseCaseResult(
                success=True,
                message="Membro removido com sucesso",
                data={
                    'member_id': member.id.value,
                    'reason': reason
                }
            )

        except Exception as e:
            logger.error(f"Erro ao remover membro {telegram_id}: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao remover membro: {str(e)}"
            )

    async def cleanup_inactive_members(
        self,
        check_contract_status: bool = True
    ) -> RemovalResult:
        """
        Remove membros inativos ou sem contrato ativo.

        Args:
            check_contract_status: Se deve verificar status do contrato

        Returns:
            RemovalResult: Resultado da limpeza
        """
        try:
            logger.info("Iniciando cleanup de membros inativos")

            removed_members = []
            errors = []

            # Busca membros sem contrato ativo
            if check_contract_status:
                inactive_members = await self.member_repository.find_members_without_contract()

                logger.info(f"Encontrados {len(inactive_members)} membros sem contrato ativo")

                for member in inactive_members:
                    try:
                        if member.can_be_removed():
                            result = await self.remove_member(
                                member.telegram_id,
                                "Contrato inativo"
                            )

                            if result.success:
                                removed_members.append({
                                    'user_id': member.telegram_id,
                                    'username': member.username,
                                    'client_name': member.get_member_display_name(),
                                    'reason': 'Contrato inativo'
                                })
                            else:
                                errors.append(f"Falha ao remover {member.telegram_id}: {result.message}")

                    except Exception as e:
                        logger.error(f"Erro ao processar membro {member.telegram_id}: {e}")
                        errors.append(f"Erro ao remover {member.telegram_id}: {str(e)}")

            removed_count = len(removed_members)
            failed_count = len(errors)

            logger.info(f"Cleanup concluído: {removed_count} removidos, {failed_count} falhas")

            return RemovalResult(
                success=True,
                removed_count=removed_count,
                failed_count=failed_count,
                removed_members=removed_members,
                errors=errors
            )

        except Exception as e:
            logger.error(f"Erro no cleanup de membros: {e}")
            return RemovalResult(
                success=False,
                removed_count=0,
                failed_count=0,
                removed_members=[],
                errors=[str(e)]
            )

    async def get_group_statistics(self) -> UseCaseResult:
        """
        Obtém estatísticas do grupo.

        Returns:
            UseCaseResult: Estatísticas do grupo
        """
        try:
            logger.info("Obtendo estatísticas do grupo")

            # Conta membros ativos
            active_count = await self.member_repository.count_active_members()

            # Busca membros não verificados
            unverified = await self.member_repository.find_unverified_members()

            # Busca membros sem contrato
            no_contract = await self.member_repository.find_members_without_contract()

            # Busca membros inativos (30 dias)
            inactive = await self.member_repository.find_inactive_members(30)

            stats = {
                'total_active_members': active_count,
                'unverified_members': len(unverified),
                'members_without_contract': len(no_contract),
                'inactive_members_30d': len(inactive),
                'group_id': self.group_id,
                'generated_at': datetime.now().isoformat()
            }

            return UseCaseResult(
                success=True,
                message="Estatísticas obtidas com sucesso",
                data=stats
            )

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do grupo: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro ao obter estatísticas: {str(e)}"
            )