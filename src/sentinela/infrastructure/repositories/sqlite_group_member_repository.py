"""
SQLite implementation of GroupMemberRepository.

Implementa a visão de "Membro do Grupo" lendo da tabela principal 'users'.
"""

import logging
import aiosqlite
from typing import List, Optional
from datetime import datetime, timedelta

from ...domain.entities.group_member import GroupMember, MemberStatus, MemberRole
from ...domain.repositories.group_member_repository import GroupMemberRepository
from ...domain.repositories.user_repository import UserRepository
from ...domain.value_objects.identifiers import UserId
from ...core.config import DATABASE_FILE

logger = logging.getLogger(__name__)


class SQLiteGroupMemberRepository(GroupMemberRepository):
    """
    Implementação SQLite do repositório de membros.

    Este repositório atua como uma "view" sobre a tabela 'users',
    adaptando os dados da entidade User para a entidade GroupMember.
    """

    def __init__(self, user_repository: UserRepository):
        """
        Inicializa o repositório.

        Args:
            user_repository: O repositório de usuário principal, usado como fonte de dados.
        """
        self.user_repository = user_repository

    async def save(self, member: GroupMember) -> GroupMember:
        """Salva ou atualiza membro através do UserRepository."""
        # A lógica de salvar um membro agora é tratada pelo fluxo normal do UserRepository.
        # Esta implementação previne a escrita em tabelas defasadas.
        logger.warning("SQLiteGroupMemberRepository.save() não deve ser usado diretamente. Use UserRepository.")
        user = await self.user_repository.find_by_telegram_id(member.telegram_id)
        if not user:
            # A criação de usuário deve ser feita pelo fluxo de use case apropriado.
            raise NotImplementedError("A criação de novos usuários deve passar pelo UserRepository.")
        
        # Apenas retorna o membro, assumindo que a modificação foi feita na entidade User e salva pelo UserRepository
        return member

    async def find_by_telegram_id(self, telegram_id: int) -> Optional[GroupMember]:
        """Busca membro por ID do Telegram usando o UserRepository."""
        user = await self.user_repository.find_by_telegram_id(telegram_id)
        if user:
            return self._user_to_group_member(user)
        return None

    async def find_by_user_id(self, user_id: UserId) -> Optional[GroupMember]:
        """Busca membro por UserID delegando para o UserRepository."""
        user = await self.user_repository.find_by_id(user_id)
        if user:
            return self._user_to_group_member(user)
        return None

    async def find_all_active(self) -> List[GroupMember]:
        """Busca todos os membros ativos delegando para o UserRepository."""
        active_users = await self.user_repository.find_active_users()
        return [self._user_to_group_member(user) for user in active_users]

    async def find_by_status(self, status: MemberStatus) -> List[GroupMember]:
        """Busca membros por status (não implementado, retorna lista vazia)."""
        logger.warning("find_by_status não implementado completamente no SQLiteGroupMemberRepository.")
        # Esta lógica precisaria de um mapeamento de MemberStatus para UserStatus
        return []

    async def find_inactive_members(self, days: int) -> List[GroupMember]:
        """Busca membros inativos (não implementado, retorna lista vazia)."""
        logger.warning("find_inactive_members não implementado no SQLiteGroupMemberRepository.")
        return []

    async def find_unverified_members(self) -> List[GroupMember]:
        """Busca membros não verificados (não aceitaram regras) a partir da tabela users."""
        import aiosqlite
        from ...core.config import DATABASE_FILE # Import local para evitar problemas de import circular

        members = []
        try:
            async with aiosqlite.connect(DATABASE_FILE) as db:
                db.row_factory = aiosqlite.Row
                # Busca usuários que não aceitaram as regras e não estão banidos
                cursor = await db.execute(
                    """
                    SELECT telegram_user_id, username, first_name, created_at 
                    FROM users 
                    WHERE rules_accepted = FALSE AND is_banned = FALSE
                    """,
                )
                rows = await cursor.fetchall()

                for row in rows:
                    # Converte a linha para um objeto GroupMember simplificado, pois não temos todos os dados de User aqui
                    joined_at = datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
                    member = GroupMember(
                        id=None,
                        user_id=UserId(row["telegram_user_id"]),
                        telegram_id=row["telegram_user_id"],
                        username=row["username"],
                        first_name=row["first_name"],
                        joined_at=joined_at,
                        is_verified=False, # Por definição, se não aceitou as regras, não é verificado
                        role=MemberRole.NEW_MEMBER,
                        status=MemberStatus.MEMBER
                    )
                    members.append(member)
                
                logger.info(f"Encontrados {len(members)} membros que não aceitaram as regras.")

        except Exception as e:
            logger.error(f"Erro ao buscar membros não verificados: {e}", exc_info=True)
        
        return members

    async def find_members_without_contract(self) -> List[GroupMember]:
        """Busca membros sem contrato (não implementado, retorna lista vazia)."""
        logger.warning("find_members_without_contract não implementado no SQLiteGroupMemberRepository.")
        return []

    async def count_active_members(self) -> int:
        """Conta membros ativos delegando para o UserRepository."""
        return await self.user_repository.count_active_users()

    async def delete(self, member_id: UserId) -> bool:
        """Remove membro delegando para o UserRepository."""
        return await self.user_repository.delete(member_id)

    async def exists(self, telegram_id: int) -> bool:
        """Verifica se membro existe usando o UserRepository."""
        user = await self.user_repository.find_by_telegram_id(telegram_id)
        return user is not None

    def _user_to_group_member(self, user) -> GroupMember:
        """Converte uma entidade User para uma entidade GroupMember."""
        return GroupMember(
            id=user.id,
            user_id=user.id,
            telegram_id=user.telegram_user_id,
            username=user.username,
            first_name=user.first_name,
            joined_at=user.created_at, # Aproximação, idealmente teríamos um campo joined_at em User
            is_verified=user.is_active(), # Considera verificado se o usuário está ativo
            role=MemberRole.GAMER_VERIFIED if user.is_active() else MemberRole.NEW_MEMBER,
            status=MemberStatus.MEMBER if user.is_active() else MemberStatus.PENDING
        )
