"""
SQLite User Repository Implementation.

Implementa persistência de usuários usando SQLite.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from ...domain.entities.user import User, UserId
from ...domain.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class SQLiteUserRepository(UserRepository):
    """Implementação SQLite do repositório de usuários."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def _init_database(self):
        """Inicializa as tabelas do banco de dados."""
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    telegram_user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    roles TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_activity_at TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_telegram_id
                ON users(telegram_user_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username
                ON users(username)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_banned
                ON users(is_banned)
            """)

            await db.commit()

    async def save(self, user: User) -> None:
        """Salva um usuário."""
        import aiosqlite
        import json

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            # Verifica se existe
            cursor = await db.execute("""
                SELECT 1 FROM users WHERE id = ? LIMIT 1
            """, (user.id.value,))

            exists = await cursor.fetchone()

            if exists:
                # Update
                await db.execute("""
                    UPDATE users SET
                        telegram_user_id = ?,
                        username = ?,
                        first_name = ?,
                        last_name = ?,
                        is_banned = ?,
                        ban_reason = ?,
                        roles = ?,
                        updated_at = ?,
                        last_activity_at = ?,
                        metadata = ?
                    WHERE id = ?
                """, (
                    user.telegram_user_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.is_banned,
                    user.ban_reason,
                    json.dumps(user.roles),
                    datetime.now().isoformat(),
                    user.last_activity_at.isoformat() if user.last_activity_at else None,
                    self._serialize_metadata(user.metadata),
                    user.id.value
                ))
            else:
                # Insert
                await db.execute("""
                    INSERT INTO users (
                        id, telegram_user_id, username, first_name, last_name,
                        is_banned, ban_reason, roles, created_at, updated_at,
                        last_activity_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.id.value,
                    user.telegram_user_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.is_banned,
                    user.ban_reason,
                    json.dumps(user.roles),
                    user.created_at.isoformat(),
                    datetime.now().isoformat(),
                    user.last_activity_at.isoformat() if user.last_activity_at else None,
                    self._serialize_metadata(user.metadata)
                ))

            await db.commit()

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Busca usuário por ID."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM users WHERE id = ? LIMIT 1
            """, (user_id.value,))

            row = await cursor.fetchone()
            if row:
                return self._row_to_user(row)
            return None

    async def find_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Busca usuário por ID do Telegram."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM users WHERE telegram_user_id = ? LIMIT 1
            """, (telegram_id,))

            row = await cursor.fetchone()
            if row:
                return self._row_to_user(row)
            return None

    async def find_by_username(self, username: str) -> Optional[User]:
        """Busca usuário por username."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM users WHERE username = ? LIMIT 1
            """, (username,))

            row = await cursor.fetchone()
            if row:
                return self._row_to_user(row)
            return None

    async def find_active_users(self) -> List[User]:
        """Busca todos os usuários ativos."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM users WHERE is_banned = FALSE
                ORDER BY created_at DESC
            """)

            rows = await cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def find_banned_users(self) -> List[User]:
        """Busca usuários banidos."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM users WHERE is_banned = TRUE
                ORDER BY updated_at DESC
            """)

            rows = await cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def count_active_users(self) -> int:
        """Conta usuários ativos."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM users WHERE is_banned = FALSE
            """)

            result = await cursor.fetchone()
            return result[0] if result else 0

    async def find_users_by_role(self, role: str) -> List[User]:
        """Busca usuários por role."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM users WHERE roles LIKE ?
                ORDER BY created_at DESC
            """, (f'%"{role}"%',))

            rows = await cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def ban_user(self, user_id: UserId, reason: str) -> bool:
        """Bane um usuário."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE users SET
                    is_banned = TRUE,
                    ban_reason = ?,
                    updated_at = ?
                WHERE id = ?
            """, (reason, datetime.now().isoformat(), user_id.value))

            await db.commit()
            return cursor.rowcount > 0

    async def unban_user(self, user_id: UserId) -> bool:
        """Remove ban de um usuário."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE users SET
                    is_banned = FALSE,
                    ban_reason = NULL,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), user_id.value))

            await db.commit()
            return cursor.rowcount > 0

    async def update_last_activity(self, user_id: UserId) -> bool:
        """Atualiza última atividade do usuário."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE users SET
                    last_activity_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), datetime.now().isoformat(), user_id.value))

            await db.commit()
            return cursor.rowcount > 0

    async def get_user_statistics(self, user_id: UserId) -> dict:
        """Obtém estatísticas de um usuário."""
        import aiosqlite

        await self._init_database()

        # Por agora retorna estatísticas básicas, pode ser expandido
        user = await self.find_by_id(user_id)
        if not user:
            return {}

        return {
            "user_id": user.id.value,
            "telegram_id": user.telegram_user_id,
            "username": user.username,
            "is_banned": user.is_banned,
            "roles_count": len(user.roles),
            "created_at": user.created_at.isoformat(),
            "last_activity": user.last_activity_at.isoformat() if user.last_activity_at else None
        }

    async def delete(self, entity_id: UserId) -> bool:
        """Remove um usuário."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM users WHERE id = ?
            """, (entity_id.value,))

            await db.commit()
            return cursor.rowcount > 0

    async def exists(self, entity_id: UserId) -> bool:
        """Verifica se um usuário existe."""
        import aiosqlite

        await self._init_database()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 1 FROM users WHERE id = ? LIMIT 1
            """, (entity_id.value,))

            result = await cursor.fetchone()
            return result is not None

    def _row_to_user(self, row) -> User:
        """Converte linha do banco para User."""
        import json
        from datetime import datetime

        return User(
            id=UserId(row[0]),
            telegram_user_id=row[1],
            username=row[2],
            first_name=row[3],
            last_name=row[4],
            is_banned=bool(row[5]),
            ban_reason=row[6],
            roles=json.loads(row[7]) if row[7] else [],
            created_at=datetime.fromisoformat(row[8]),
            last_activity_at=datetime.fromisoformat(row[10]) if row[10] else None,
            metadata=self._deserialize_metadata(row[11])
        )

    def _serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """Serializa metadados para JSON."""
        import json
        return json.dumps(metadata) if metadata else "{}"

    def _deserialize_metadata(self, metadata_str: str) -> Dict[str, Any]:
        """Deserializa metadados do JSON."""
        import json
        try:
            return json.loads(metadata_str) if metadata_str else {}
        except:
            return {}