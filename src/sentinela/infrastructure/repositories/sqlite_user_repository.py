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

    async def save(self, user: User) -> None:
        """Salva um usuário."""
        import aiosqlite
        import json

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
                        metadata = ?,
                        expires_at = ?
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
                    user.expires_at.isoformat() if user.expires_at else None,
                    user.id.value
                ))
            else:
                # Insert
                await db.execute("""
                    INSERT INTO users (
                        id, telegram_user_id, username, first_name, last_name,
                        cpf, client_name, is_banned, ban_reason, roles, created_at, updated_at,
                        last_activity_at, metadata, status, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.id.value,
                    user.telegram_user_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.cpf.value,
                    user.client_name,
                    user.is_banned,
                    user.ban_reason,
                    json.dumps(user.roles),
                    user.created_at.isoformat(),
                    datetime.now().isoformat(),
                    user.last_activity_at.isoformat() if user.last_activity_at else None,
                    self._serialize_metadata(user.metadata),
                    user.status.value,
                    user.expires_at.isoformat() if user.expires_at else None
                ))

            await db.commit()

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Busca usuário por ID."""
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
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

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
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

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
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

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM users WHERE is_banned = FALSE
                ORDER BY created_at DESC
            """)

            rows = await cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def find_banned_users(self) -> List[User]:
        """Busca usuários banidos."""
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM users WHERE is_banned = TRUE
                ORDER BY updated_at DESC
            """)

            rows = await cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def count_active_users(self) -> int:
        """Conta usuários ativos."""
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM users WHERE is_banned = FALSE
            """)

            result = await cursor.fetchone()
            return result[0] if result else 0

    async def find_users_by_role(self, role: str) -> List[User]:
        """Busca usuários por role."""
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM users WHERE roles LIKE ?
                ORDER BY created_at DESC
            """, (f'%"{role}"%',))

            rows = await cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def ban_user(self, user_id: UserId, reason: str) -> bool:
        """Bane um usuário."""
        import aiosqlite

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

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE users SET
                    last_activity_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), datetime.now().isoformat(), user_id.value))

            await db.commit()
            return cursor.rowcount > 0

    async def find_by_cpf(self, cpf: str) -> Optional[User]:
        """
        Busca usuário por CPF.

        Args:
            cpf: CPF para buscar (apenas números)

        Returns:
            User encontrado ou None
        """
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM users WHERE cpf = ? LIMIT 1
            """, (cpf,))

            row = await cursor.fetchone()

            if row:
                return self._row_to_user(row)

            return None

    async def find_users_without_cpf(self) -> List[User]:
        """
        Busca todos os usuários que NÃO têm CPF vinculado.

        Returns:
            Lista de usuários sem CPF
        """
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM users
                WHERE cpf IS NULL OR cpf = ''
                ORDER BY created_at DESC
            """)

            rows = await cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    async def update_telegram_id(self, old_user_id: int, new_user_id: int, cpf: str) -> bool:
        """
        Atualiza vínculo de CPF para novo Telegram ID.

        Remove CPF do ID antigo e vincula ao novo ID.

        Args:
            old_user_id: Telegram ID antigo
            new_user_id: Telegram ID novo
            cpf: CPF a ser vinculado

        Returns:
            True se atualizado com sucesso
        """
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            # Remove CPF do usuário antigo
            await db.execute("""
                UPDATE users SET
                    cpf = NULL,
                    client_name = NULL,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), old_user_id))

            # Vincula CPF ao novo usuário
            cursor = await db.execute("""
                UPDATE users SET
                    cpf = ?,
                    updated_at = ?
                WHERE id = ?
            """, (cpf, datetime.now().isoformat(), new_user_id))

            await db.commit()

            return cursor.rowcount > 0

    async def get_user_statistics(self, user_id: UserId) -> dict:
        """Obtém estatísticas de um usuário."""
        import aiosqlite

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

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM users WHERE id = ?
            """, (entity_id.value,))

            await db.commit()
            return cursor.rowcount > 0

    async def exists(self, entity_id: UserId) -> bool:
        """Verifica se um usuário existe."""
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 1 FROM users WHERE id = ? LIMIT 1
            """, (entity_id.value,))

            result = await cursor.fetchone()
            return result is not None

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Converte linha do banco para User."""
        from ...domain.entities.user import ServiceInfo, UserStatus
        from ...domain.value_objects.cpf import CPF
        from datetime import datetime
        import json

        # Mapeia os dados da linha para os argumentos do construtor User
        user_id = UserId(int(row["id"]))
        username = row["username"]
        
        # O construtor do User espera um objeto CPF
        cpf_obj = CPF.from_raw(row["cpf"]) if row["cpf"] else None
        
        client_name = row["client_name"]
        
        # Cria ServiceInfo se houver dados de serviço
        service_info = None
        if row["service_name"] and row["service_status"]:
            service_info = ServiceInfo(
                name=row["service_name"],
                status=row["service_status"]
            )

        # Validação para garantir que campos obrigatórios não sejam nulos
        if not cpf_obj or not client_name:
            raise ValueError(f"Dados essenciais (CPF, client_name) ausentes para o usuário {user_id.value}")

        # Cria a instância do usuário
        user = User(
            user_id=user_id,
            telegram_user_id=row["telegram_user_id"],
            username=username,
            first_name=row["first_name"],
            last_name=row["last_name"],
            cpf=cpf_obj,
            client_name=client_name,
            service_info=service_info
        )

        # Recarrega o estado do usuário a partir do banco de dados
        user._status = UserStatus(row["status"]) if row["status"] else UserStatus.PENDING_VERIFICATION
        user._last_verification = datetime.fromisoformat(row["last_verification"]) if row["last_verification"] else None
        user._is_admin = True if row["roles"] and 'admin' in json.loads(row["roles"]) else False

        return user

    def _serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """Serializa metadados para JSON."""
        import json
        return json.dumps(metadata) if metadata else "{}"

    def _deserialize_metadata(self, metadata_str: str) -> Dict[str, Any]:
        """Deserializa metadados do JSON."""
        import json
        try:
            return json.loads(data_str) if data_str else {}
        except:
            return {}

    async def delete_expired_pending_users(self) -> int:
        """Deleta usuários pendentes cuja data de expiração já passou."""
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            now_iso = datetime.now().isoformat()
            
            cursor = await db.execute("""
                DELETE FROM users
                WHERE status = ? AND expires_at IS NOT NULL AND expires_at < ?
            """, ("pending_verification", now_iso))
            
            await db.commit()
            deleted_count = cursor.rowcount
            logger.info(f"{deleted_count} usuários pendentes expirados foram removidos.")
            return deleted_count
