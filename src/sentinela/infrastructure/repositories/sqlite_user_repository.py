"""
SQLite implementation of UserRepository.

Implementação concreta do UserRepository usando SQLite.
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ...domain.repositories.user_repository import UserRepository
from ...domain.repositories.base import RepositoryError, EntityNotFoundError
from ...domain.entities.user import User, UserStatus, ServiceInfo
from ...domain.value_objects.identifiers import UserId
from ...domain.value_objects.cpf import CPF

logger = logging.getLogger(__name__)


class SQLiteUserRepository(UserRepository):
    """
    Implementação SQLite do UserRepository.

    Mapeia objetos de domínio User para/do banco SQLite.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """
        Cria conexão com banco SQLite.

        Returns:
            sqlite3.Connection: Conexão com o banco
        """
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao conectar ao banco: {e}", e)

    def _map_row_to_user(self, row: sqlite3.Row) -> User:
        """
        Mapeia row do banco para entidade User.

        Args:
            row: Row do SQLite

        Returns:
            User: Entidade User
        """
        try:
            user_id = UserId(row['user_id'])
            cpf = CPF(row['cpf'])

            # Mapeia service info se disponível
            service_info = None
            if row['service_name']:
                service_info = ServiceInfo(
                    name=row['service_name'],
                    status=row['service_status'] or 'unknown',
                    service_id=row.get('service_id')
                )

            # Cria usuário
            user = User(
                user_id=user_id,
                username=row['username'],
                cpf=cpf,
                client_name=row['client_name'],
                service_info=service_info
            )

            # Atualiza status
            status_str = row.get('status', 'pending_verification')
            if hasattr(UserStatus, status_str.upper()):
                user._status = UserStatus(status_str)

            # Atualiza timestamps
            if row['last_verification']:
                user._last_verification = datetime.fromisoformat(row['last_verification'])

            if row['created_at']:
                user._created_at = datetime.fromisoformat(row['created_at'])

            if row['updated_at']:
                user._updated_at = datetime.fromisoformat(row['updated_at'])

            # Admin flag
            user._is_admin = bool(row.get('is_admin', 0))

            # Limpa eventos (são do banco, não novos)
            user.clear_events()

            return user

        except Exception as e:
            raise RepositoryError(f"Erro ao mapear row para User: {e}", e)

    def _map_user_to_dict(self, user: User) -> Dict[str, Any]:
        """
        Mapeia entidade User para dict do banco.

        Args:
            user: Entidade User

        Returns:
            Dict: Dados para inserção/atualização
        """
        data = {
            'user_id': int(user.id),
            'username': user.username,
            'cpf': user.cpf.value,
            'client_name': user.client_name,
            'status': user.status.value,
            'is_admin': 1 if user.is_admin else 0,
            'last_verification': user.last_verification.isoformat() if user.last_verification else None,
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat(),
        }

        # Service info
        if user.service_info:
            data['service_name'] = user.service_info.name
            data['service_status'] = user.service_info.status
            data['service_id'] = user.service_info.service_id
        else:
            data['service_name'] = None
            data['service_status'] = None
            data['service_id'] = None

        return data

    async def save(self, user: User) -> None:
        """Salva usuário no banco."""
        try:
            with self._get_connection() as conn:
                data = self._map_user_to_dict(user)

                # Verifica se já existe
                existing = await self.exists(user.id)

                if existing:
                    # Update
                    placeholders = ', '.join(f"{key} = ?" for key in data.keys() if key != 'user_id')
                    values = [v for k, v in data.items() if k != 'user_id']
                    values.append(int(user.id))

                    conn.execute(
                        f"UPDATE users SET {placeholders} WHERE user_id = ?",
                        values
                    )
                else:
                    # Insert
                    placeholders = ', '.join('?' * len(data))
                    columns = ', '.join(data.keys())

                    conn.execute(
                        f"INSERT INTO users ({columns}) VALUES ({placeholders})",
                        list(data.values())
                    )

                conn.commit()
                logger.debug(f"User {user.id} saved successfully")

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao salvar usuário {user.id}: {e}", e)

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Busca usuário por ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (int(user_id),)
                )
                row = cursor.fetchone()

                if row:
                    return self._map_row_to_user(row)
                return None

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao buscar usuário {user_id}: {e}", e)

    async def find_by_cpf(self, cpf: CPF) -> Optional[User]:
        """Busca usuário por CPF."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM users WHERE cpf = ?",
                    (cpf.value,)
                )
                row = cursor.fetchone()

                if row:
                    return self._map_row_to_user(row)
                return None

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao buscar usuário por CPF: {e}", e)

    async def find_by_username(self, username: str) -> Optional[User]:
        """Busca usuário por username."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,)
                )
                row = cursor.fetchone()

                if row:
                    return self._map_row_to_user(row)
                return None

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao buscar usuário por username: {e}", e)

    async def find_active_users(self) -> List[User]:
        """Busca todos os usuários ativos."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM users WHERE status = ? ORDER BY created_at",
                    ('active',)
                )
                rows = cursor.fetchall()

                return [self._map_row_to_user(row) for row in rows]

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao buscar usuários ativos: {e}", e)

    async def find_pending_verification(self) -> List[User]:
        """Busca usuários pendentes de verificação."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM users WHERE status = ? ORDER BY created_at",
                    ('pending_verification',)
                )
                rows = cursor.fetchall()

                return [self._map_row_to_user(row) for row in rows]

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao buscar usuários pendentes: {e}", e)

    async def find_admins(self) -> List[User]:
        """Busca usuários administradores."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM users WHERE is_admin = 1 ORDER BY created_at"
                )
                rows = cursor.fetchall()

                return [self._map_row_to_user(row) for row in rows]

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao buscar administradores: {e}", e)

    async def count_active_users(self) -> int:
        """Conta usuários ativos."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM users WHERE status = ?",
                    ('active',)
                )
                return cursor.fetchone()[0]

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao contar usuários ativos: {e}", e)

    async def exists(self, user_id: UserId) -> bool:
        """Verifica se usuário existe."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM users WHERE user_id = ?",
                    (int(user_id),)
                )
                return cursor.fetchone() is not None

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao verificar existência do usuário {user_id}: {e}", e)

    async def exists_by_cpf(self, cpf: CPF) -> bool:
        """Verifica se existe usuário com o CPF."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM users WHERE cpf = ?",
                    (cpf.value,)
                )
                return cursor.fetchone() is not None

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao verificar CPF: {e}", e)

    async def delete(self, user_id: UserId) -> bool:
        """Remove usuário."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM users WHERE user_id = ?",
                    (int(user_id),)
                )
                conn.commit()
                return cursor.rowcount > 0

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao remover usuário {user_id}: {e}", e)

    async def mark_user_inactive(self, user_id: UserId) -> bool:
        """Marca usuário como inativo."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """UPDATE users
                       SET status = ?, updated_at = ?
                       WHERE user_id = ?""",
                    ('inactive', datetime.now().isoformat(), int(user_id))
                )
                conn.commit()
                success = cursor.rowcount > 0

                if success:
                    logger.info(f"Usuário {user_id} marcado como inativo")

                return success

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao marcar usuário {user_id} como inativo: {e}", e)

    async def update_user_id_for_cpf(self, cpf: CPF, new_user_id: UserId, new_username: str) -> bool:
        """Atualiza o user_id para um registro baseado no CPF."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """UPDATE users
                       SET user_id = ?, username = ?, updated_at = ?
                       WHERE cpf = ?""",
                    (int(new_user_id), new_username, datetime.now().isoformat(), cpf.value)
                )
                conn.commit()
                success = cursor.rowcount > 0

                if success:
                    logger.info(f"Registro de CPF {cpf.masked()} remapeado para usuário {new_user_id}")
                else:
                    logger.warning(f"Nenhum usuário encontrado com CPF {cpf.masked()}")

                return success

        except sqlite3.Error as e:
            raise RepositoryError(f"Erro ao remapear CPF para usuário {new_user_id}: {e}", e)