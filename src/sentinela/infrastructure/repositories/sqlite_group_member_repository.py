"""
SQLite implementation of GroupMemberRepository.

Implementa persistência de membros do grupo usando SQLite.
Usa a tabela user_rules existente para controlar aceitação de regras.
"""

import logging
import aiosqlite
from typing import List, Optional
from datetime import datetime, timedelta

from ...domain.entities.group_member import GroupMember, MemberStatus, MemberRole
from ...domain.repositories.group_member_repository import GroupMemberRepository
from ...domain.value_objects.identifiers import UserId
from ...core.config import DATABASE_FILE

logger = logging.getLogger(__name__)


class SQLiteGroupMemberRepository(GroupMemberRepository):
    """
    Implementação SQLite do repositório de membros.

    Usa tabela user_rules para controlar estado de novos membros.
    """

    def __init__(self, db_path: str = DATABASE_FILE):
        """
        Inicializa repositório.

        Args:
            db_path: Caminho do arquivo SQLite
        """
        self.db_path = db_path

    async def save(self, member: GroupMember) -> GroupMember:
        """Salva ou atualiza membro."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Verifica se já existe
                cursor = await db.execute(
                    "SELECT user_id FROM user_rules WHERE user_id = ?",
                    (member.telegram_id,)
                )
                exists = await cursor.fetchone()

                if exists:
                    # Atualiza
                    await db.execute(
                        """
                        UPDATE user_rules
                        SET username = ?,
                            rules_accepted = ?,
                            rules_accepted_at = ?,
                            status = ?
                        WHERE user_id = ?
                        """,
                        (
                            member.username,
                            1 if member.is_verified else 0,
                            member.joined_at.isoformat() if member.is_verified else None,
                            'accepted' if member.is_verified else 'pending',
                            member.telegram_id
                        )
                    )
                else:
                    # Insere novo
                    expires_at = datetime.now() + timedelta(hours=24)
                    await db.execute(
                        """
                        INSERT INTO user_rules
                        (user_id, username, joined_at, rules_accepted, expires_at, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            member.telegram_id,
                            member.username,
                            member.joined_at.isoformat(),
                            0,
                            expires_at.isoformat(),
                            'pending'
                        )
                    )

                await db.commit()
                logger.info(f"Membro {member.telegram_id} salvo com sucesso")
                return member

        except Exception as e:
            logger.error(f"Erro ao salvar membro {member.telegram_id}: {e}")
            raise

    async def find_by_telegram_id(self, telegram_id: int) -> Optional[GroupMember]:
        """Busca membro por ID do Telegram."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT user_id, username, joined_at, rules_accepted,
                           rules_accepted_at, status
                    FROM user_rules
                    WHERE user_id = ?
                    """,
                    (telegram_id,)
                )
                row = await cursor.fetchone()

                if not row:
                    return None

                # Converte para GroupMember
                joined_at = datetime.fromisoformat(row[2]) if row[2] else datetime.now()
                is_verified = bool(row[3])

                return GroupMember(
                    id=None,  # Não usado neste contexto
                    user_id=UserId(row[0]),
                    telegram_id=row[0],
                    username=row[1],
                    first_name=row[1] or "Usuário",
                    joined_at=joined_at,
                    is_verified=is_verified,
                    role=MemberRole.GAMER_VERIFIED if is_verified else MemberRole.NEW_MEMBER,
                    status=MemberStatus.MEMBER
                )

        except Exception as e:
            logger.error(f"Erro ao buscar membro {telegram_id}: {e}")
            return None

    async def find_by_user_id(self, user_id: UserId) -> Optional[GroupMember]:
        """Busca membro por UserID."""
        return await self.find_by_telegram_id(user_id.value)

    async def find_all_active(self) -> List[GroupMember]:
        """Busca todos os membros ativos."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT user_id, username, joined_at, rules_accepted
                    FROM user_rules
                    WHERE status IN ('pending', 'accepted')
                    """
                )
                rows = await cursor.fetchall()

                members = []
                for row in rows:
                    joined_at = datetime.fromisoformat(row[2]) if row[2] else datetime.now()
                    is_verified = bool(row[3])

                    member = GroupMember(
                        id=None,
                        user_id=UserId(row[0]),
                        telegram_id=row[0],
                        username=row[1],
                        first_name=row[1] or "Usuário",
                        joined_at=joined_at,
                        is_verified=is_verified,
                        role=MemberRole.GAMER_VERIFIED if is_verified else MemberRole.NEW_MEMBER,
                        status=MemberStatus.MEMBER
                    )
                    members.append(member)

                return members

        except Exception as e:
            logger.error(f"Erro ao buscar membros ativos: {e}")
            return []

    async def find_by_status(self, status: MemberStatus) -> List[GroupMember]:
        """Busca membros por status."""
        # Implementação simplificada
        return await self.find_all_active()

    async def find_inactive_members(self, days: int) -> List[GroupMember]:
        """Busca membros inativos há X dias."""
        # Não implementado neste contexto simples
        return []

    async def find_unverified_members(self) -> List[GroupMember]:
        """Busca membros não verificados (não aceitaram regras)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT user_id, username, joined_at, expires_at
                    FROM user_rules
                    WHERE rules_accepted = 0
                    AND status = 'pending'
                    """
                )
                rows = await cursor.fetchall()

                members = []
                for row in rows:
                    joined_at = datetime.fromisoformat(row[2]) if row[2] else datetime.now()

                    member = GroupMember(
                        id=None,
                        user_id=UserId(row[0]),
                        telegram_id=row[0],
                        username=row[1],
                        first_name=row[1] or "Usuário",
                        joined_at=joined_at,
                        is_verified=False,
                        role=MemberRole.NEW_MEMBER,
                        status=MemberStatus.MEMBER
                    )
                    members.append(member)

                logger.info(f"Encontrados {len(members)} membros não verificados")
                return members

        except Exception as e:
            logger.error(f"Erro ao buscar membros não verificados: {e}")
            return []

    async def find_members_without_contract(self) -> List[GroupMember]:
        """Busca membros sem contrato ativo."""
        # Não implementado neste contexto
        return []

    async def count_active_members(self) -> int:
        """Conta membros ativos."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM user_rules WHERE status IN ('pending', 'accepted')"
                )
                count = await cursor.fetchone()
                return count[0] if count else 0

        except Exception as e:
            logger.error(f"Erro ao contar membros ativos: {e}")
            return 0

    async def delete(self, member_id: UserId) -> bool:
        """Remove membro do repositório."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE user_rules SET status = 'removed' WHERE user_id = ?",
                    (member_id.value,)
                )
                await db.commit()
                logger.info(f"Membro {member_id.value} removido")
                return True

        except Exception as e:
            logger.error(f"Erro ao remover membro {member_id.value}: {e}")
            return False

    async def exists(self, telegram_id: int) -> bool:
        """Verifica se membro existe."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT 1 FROM user_rules WHERE user_id = ?",
                    (telegram_id,)
                )
                exists = await cursor.fetchone()
                return exists is not None

        except Exception as e:
            logger.error(f"Erro ao verificar existência do membro {telegram_id}: {e}")
            return False
