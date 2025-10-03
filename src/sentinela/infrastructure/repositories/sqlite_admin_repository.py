"""
SQLite Admin Repository Implementation.

Implementação concreta do repositório de administradores usando SQLite.
"""

import sqlite3
import logging
from typing import Optional, List
from datetime import datetime

from ...domain.repositories.admin_repository import AdminRepository

logger = logging.getLogger(__name__)


class SQLiteAdminRepository(AdminRepository):
    """
    Implementação SQLite do repositório de administradores.
    """

    def __init__(self, db_path: str):
        """
        Inicializa o repositório.

        Args:
            db_path: Caminho para o arquivo do banco SQLite
        """
        self.db_path = db_path
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """Garante que a tabela de administradores existe."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS administrators (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        status TEXT DEFAULT 'administrator',
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_administrators_active
                    ON administrators(is_active)
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Erro ao criar tabela administrators: {e}")

    async def is_administrator(self, user_id: int) -> bool:
        """Verifica se um usuário é administrador ativo."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 1 FROM administrators
                    WHERE user_id = ? AND is_active = 1
                    LIMIT 1
                """, (user_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Erro ao verificar administrador {user_id}: {e}")
            return False

    async def get_administrator(self, user_id: int) -> Optional[dict]:
        """Busca dados de um administrador."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT
                        user_id,
                        username,
                        first_name,
                        last_name,
                        status,
                        detected_at,
                        last_updated,
                        is_active
                    FROM administrators
                    WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Erro ao buscar administrador {user_id}: {e}")
            return None

    async def list_administrators(self, active_only: bool = True) -> List[dict]:
        """Lista todos os administradores."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                if active_only:
                    query = """
                        SELECT
                            user_id,
                            username,
                            first_name,
                            last_name,
                            status,
                            detected_at,
                            last_updated,
                            is_active
                        FROM administrators
                        WHERE is_active = 1
                        ORDER BY username
                    """
                    cursor = conn.execute(query)
                else:
                    query = """
                        SELECT
                            user_id,
                            username,
                            first_name,
                            last_name,
                            status,
                            detected_at,
                            last_updated,
                            is_active
                        FROM administrators
                        ORDER BY username
                    """
                    cursor = conn.execute(query)

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Erro ao listar administradores: {e}")
            return []

    async def save_administrator(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        status: str = "administrator",
        is_active: bool = True
    ) -> bool:
        """Salva ou atualiza um administrador."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verifica se já existe
                cursor = conn.execute(
                    "SELECT user_id FROM administrators WHERE user_id = ?",
                    (user_id,)
                )
                exists = cursor.fetchone()

                if exists:
                    # Update
                    conn.execute("""
                        UPDATE administrators SET
                            username = ?,
                            first_name = ?,
                            last_name = ?,
                            status = ?,
                            is_active = ?,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (
                        username,
                        first_name,
                        last_name,
                        status,
                        1 if is_active else 0,
                        user_id
                    ))
                else:
                    # Insert
                    conn.execute("""
                        INSERT INTO administrators (
                            user_id,
                            username,
                            first_name,
                            last_name,
                            status,
                            is_active
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        username,
                        first_name,
                        last_name,
                        status,
                        1 if is_active else 0
                    ))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Erro ao salvar administrador {user_id}: {e}")
            return False

    async def deactivate_administrator(self, user_id: int) -> bool:
        """Desativa um administrador."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE administrators SET
                        is_active = 0,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Erro ao desativar administrador {user_id}: {e}")
            return False

    async def sync_from_telegram(self, admin_list: List[dict]) -> int:
        """
        Sincroniza lista de administradores do Telegram.

        Args:
            admin_list: Lista de dicts com keys: user_id, username, first_name, last_name, status

        Returns:
            int: Número de administradores sincronizados
        """
        synced_count = 0

        try:
            # Marca todos como inativos primeiro
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE administrators SET is_active = 0")
                conn.commit()

            # Adiciona/atualiza os da lista atual
            for admin in admin_list:
                success = await self.save_administrator(
                    user_id=admin.get('user_id'),
                    username=admin.get('username'),
                    first_name=admin.get('first_name'),
                    last_name=admin.get('last_name'),
                    status=admin.get('status', 'administrator'),
                    is_active=True
                )
                if success:
                    synced_count += 1

            logger.info(f"Sincronizados {synced_count} administradores")
            return synced_count

        except Exception as e:
            logger.error(f"Erro ao sincronizar administradores: {e}")
            return synced_count
