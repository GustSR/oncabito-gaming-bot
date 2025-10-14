"""
SQLite Support Session Repository Implementation.

Implementação concreta do repositório de sessões de suporte usando aiosqlite.
Persiste o progresso do formulário de suporte no banco de dados de forma assíncrona.
"""

import aiosqlite
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ...domain.repositories.support_session_repository import SupportSessionRepository

logger = logging.getLogger(__name__)


class SQLiteSupportSessionRepository(SupportSessionRepository):
    """
    Implementação assíncrona com aiosqlite do repositório de sessões de suporte.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def save_session(
        self,
        user_id: int,
        state_json: Dict[str, Any],
        current_step: str
    ) -> bool:
        try:
            state_str = json.dumps(state_json, ensure_ascii=False)
            expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
            now = datetime.now().isoformat()
            data = state_json.get('data', {})
            categoria = data.get('categoria')
            severidade = data.get('severidade')

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT user_id FROM support_sessions WHERE user_id = ?",
                    (user_id,)
                )
                exists = await cursor.fetchone()

                if exists:
                    await db.execute("""
                        UPDATE support_sessions SET
                            state_json = ?, current_step = ?, updated_at = ?,
                            expires_at = ?, categoria = ?, severidade = ?
                        WHERE user_id = ?
                    """, (
                        state_str, current_step, now, expires_at,
                        categoria, severidade, user_id
                    ))
                    logger.debug(f"Sessão de suporte atualizada para usuário {user_id}")
                else:
                    await db.execute("""
                        INSERT INTO support_sessions (
                            user_id, state_json, current_step, created_at, updated_at,
                            expires_at, categoria, severidade
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id, state_str, current_step, now, now,
                        expires_at, categoria, severidade
                    ))
                    logger.info(f"Nova sessão de suporte criada para usuário {user_id}")

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Erro ao salvar sessão para {user_id}: {e}", exc_info=True)
            return False

    async def find_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM support_sessions WHERE user_id = ?", (user_id,)
                )
                row = await cursor.fetchone()

                if row:
                    session_data = dict(row)
                    session_data['state_json'] = json.loads(session_data['state_json'])
                    logger.debug(f"Sessão encontrada para usuário {user_id}")
                    return session_data

                return None

        except Exception as e:
            logger.error(f"Erro ao buscar sessão para {user_id}: {e}", exc_info=True)
            return None

    async def delete_session(self, user_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM support_sessions WHERE user_id = ?", (user_id,)
                )
                await db.commit()
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Erro ao remover sessão para {user_id}: {e}", exc_info=True)
            return False

    async def session_exists(self, user_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT 1 FROM support_sessions WHERE user_id = ? LIMIT 1", (user_id,)
                )
                return await cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"Erro ao verificar sessão para {user_id}: {e}", exc_info=True)
            return False

    async def cleanup_expired_sessions(self) -> int:
        try:
            now = datetime.now().isoformat()
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM support_sessions WHERE expires_at < ?", (now,)
                )
                await db.commit()
                removed_count = cursor.rowcount
                if removed_count > 0:
                    logger.info(f"Removidas {removed_count} sessões de suporte expiradas")
                return removed_count

        except Exception as e:
            logger.error(f"Erro ao limpar sessões expiradas: {e}", exc_info=True)
            return 0

    async def get_active_sessions_count(self) -> int:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM support_sessions")
                count = await cursor.fetchone()
                return count[0] if count else 0

        except Exception as e:
            logger.error(f"Erro ao contar sessões ativas: {e}", exc_info=True)
            return 0