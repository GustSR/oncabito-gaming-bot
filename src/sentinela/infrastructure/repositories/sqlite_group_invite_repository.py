"""
SQLite Group Invite Repository Implementation.

Implementa persistência de convites de grupo usando SQLite.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from ...domain.entities.group_invite import GroupInvite

logger = logging.getLogger(__name__)


class SQLiteGroupInviteRepository:
    """Implementação SQLite do repositório de convites de grupo."""

    def __init__(self, db_path: str = "data/database/sentinela.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self) -> None:
        """Inicializa tabelas do banco."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS group_invites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    cpf TEXT NOT NULL,
                    invite_link TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    used_at TEXT,
                    client_name TEXT,
                    plan_name TEXT,
                    UNIQUE(invite_link)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_group_invites_user_id
                ON group_invites(user_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_group_invites_cpf
                ON group_invites(cpf)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_group_invites_expires_at
                ON group_invites(expires_at)
            """)

            conn.commit()

    async def save(self, invite: GroupInvite) -> GroupInvite:
        """
        Salva um convite no banco.

        Args:
            invite: Convite a ser salvo

        Returns:
            GroupInvite: Convite salvo com ID atualizado
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if invite.invite_id:
                    # Update
                    cursor.execute("""
                        UPDATE group_invites SET
                            user_id = ?,
                            cpf = ?,
                            invite_link = ?,
                            created_at = ?,
                            expires_at = ?,
                            used = ?,
                            used_at = ?,
                            client_name = ?,
                            plan_name = ?
                        WHERE id = ?
                    """, (
                        invite.user_id,
                        invite.cpf,
                        invite.invite_link,
                        invite.created_at.isoformat(),
                        invite.expires_at.isoformat(),
                        invite.used,
                        invite.used_at.isoformat() if invite.used_at else None,
                        invite.client_name,
                        invite.plan_name,
                        invite.invite_id
                    ))
                else:
                    # Insert
                    cursor.execute("""
                        INSERT INTO group_invites (
                            user_id, cpf, invite_link, created_at, expires_at,
                            used, used_at, client_name, plan_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        invite.user_id,
                        invite.cpf,
                        invite.invite_link,
                        invite.created_at.isoformat(),
                        invite.expires_at.isoformat(),
                        invite.used,
                        invite.used_at.isoformat() if invite.used_at else None,
                        invite.client_name,
                        invite.plan_name
                    ))

                    invite.invite_id = cursor.lastrowid

                conn.commit()

            logger.info(f"Convite salvo: ID={invite.invite_id}, User={invite.user_id}")
            return invite

        except Exception as e:
            logger.error(f"Erro ao salvar convite: {e}")
            raise

    async def find_by_id(self, invite_id: int) -> Optional[GroupInvite]:
        """Busca convite por ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM group_invites WHERE id = ?
                """, (invite_id,))

                row = cursor.fetchone()

                if row:
                    return self._row_to_entity(row)

                return None

        except Exception as e:
            logger.error(f"Erro ao buscar convite por ID: {e}")
            return None

    async def find_by_user_id(self, user_id: int) -> List[GroupInvite]:
        """Busca todos os convites de um usuário."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM group_invites
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """, (user_id,))

                rows = cursor.fetchall()

                return [self._row_to_entity(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar convites por usuário: {e}")
            return []

    async def find_by_link(self, invite_link: str) -> Optional[GroupInvite]:
        """Busca convite por link."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM group_invites WHERE invite_link = ?
                """, (invite_link,))

                row = cursor.fetchone()

                if row:
                    return self._row_to_entity(row)

                return None

        except Exception as e:
            logger.error(f"Erro ao buscar convite por link: {e}")
            return None

    async def mark_as_used(self, invite_id: int) -> bool:
        """Marca um convite como usado."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE group_invites
                    SET used = TRUE, used_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), invite_id))

                conn.commit()

                logger.info(f"Convite {invite_id} marcado como usado")
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Erro ao marcar convite como usado: {e}")
            return False

    async def find_expired(self) -> List[GroupInvite]:
        """Busca convites expirados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                now = datetime.now().isoformat()

                cursor.execute("""
                    SELECT * FROM group_invites
                    WHERE expires_at < ? AND used = FALSE
                    ORDER BY expires_at DESC
                """, (now,))

                rows = cursor.fetchall()

                return [self._row_to_entity(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar convites expirados: {e}")
            return []

    async def cleanup_old_invites(self, days: int = 30) -> int:
        """Remove convites antigos do banco."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cutoff_date = datetime.now()
                from datetime import timedelta
                cutoff_date = cutoff_date - timedelta(days=days)

                cursor.execute("""
                    DELETE FROM group_invites
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))

                deleted = cursor.rowcount
                conn.commit()

                logger.info(f"Removidos {deleted} convites antigos (>{days} dias)")
                return deleted

        except Exception as e:
            logger.error(f"Erro ao limpar convites antigos: {e}")
            return 0

    def _row_to_entity(self, row: sqlite3.Row) -> GroupInvite:
        """Converte linha do banco para entidade."""
        return GroupInvite(
            invite_id=row['id'],
            user_id=row['user_id'],
            cpf=row['cpf'],
            invite_link=row['invite_link'],
            created_at=datetime.fromisoformat(row['created_at']),
            expires_at=datetime.fromisoformat(row['expires_at']),
            used=bool(row['used']),
            used_at=datetime.fromisoformat(row['used_at']) if row['used_at'] else None,
            client_name=row['client_name'],
            plan_name=row['plan_name']
        )
