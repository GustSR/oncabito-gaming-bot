"""
SQLite Duplicate Conflict Repository Implementation.

Implementa persistência de conflitos de duplicata usando SQLite.
"""

import logging
import sqlite3
import json
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from ...domain.entities.duplicate_conflict import DuplicateConflict, ConflictId, ConflictStatus, ResolutionAction
from ...domain.repositories.duplicate_conflict_repository import DuplicateConflictRepository

logger = logging.getLogger(__name__)


class SQLiteDuplicateConflictRepository(DuplicateConflictRepository):
    """Implementação SQLite do repositório de conflitos de duplicata."""

    def __init__(self, db_path: str = "data/database/sentinela.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def save(self, conflict: DuplicateConflict) -> None:
        """Salva um conflito de duplicata."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Verifica se já existe
                cursor = await db.execute(
                    "SELECT id FROM duplicate_conflicts WHERE id = ?",
                    (conflict.id.value,)
                )
                exists = await cursor.fetchone()

                if exists:
                    # Update
                    await db.execute("""
                        UPDATE duplicate_conflicts SET
                            cpf_hash = ?,
                            user_ids = ?,
                            notified_user_id = ?,
                            status = ?,
                            conflict_data = ?,
                            expires_at = ?,
                            resolved_at = ?,
                            resolved_by = ?,
                            resolution_choice = ?,
                            resolution_action = ?
                        WHERE id = ?
                    """, (
                        conflict.cpf_hash,
                        json.dumps(conflict.user_ids),
                        conflict.notified_user_id,
                        conflict.status.value,
                        json.dumps(conflict.conflict_data),
                        conflict.expires_at.isoformat(),
                        conflict.resolved_at.isoformat() if conflict.resolved_at else None,
                        conflict.resolved_by,
                        conflict.resolution_choice,
                        conflict.resolution_action.value if conflict.resolution_action else None,
                        conflict.id.value
                    ))
                else:
                    # Insert
                    await db.execute("""
                        INSERT INTO duplicate_conflicts (
                            id, cpf_hash, user_ids, notified_user_id, status,
                            conflict_data, created_at, expires_at, resolved_at,
                            resolved_by, resolution_choice, resolution_action
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        conflict.id.value,
                        conflict.cpf_hash,
                        json.dumps(conflict.user_ids),
                        conflict.notified_user_id,
                        conflict.status.value,
                        json.dumps(conflict.conflict_data),
                        conflict.created_at.isoformat(),
                        conflict.expires_at.isoformat(),
                        conflict.resolved_at.isoformat() if conflict.resolved_at else None,
                        conflict.resolved_by,
                        conflict.resolution_choice,
                        conflict.resolution_action.value if conflict.resolution_action else None
                    ))

                await db.commit()
                logger.debug(f"Conflito {conflict.id.value} salvo com sucesso")

        except Exception as e:
            logger.error(f"Erro ao salvar conflito {conflict.id.value}: {e}")
            raise

    async def find_by_id(self, conflict_id: ConflictId) -> Optional[DuplicateConflict]:
        """Busca conflito por ID."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM duplicate_conflicts WHERE id = ?",
                    (conflict_id.value,)
                )
                row = await cursor.fetchone()

                if not row:
                    return None

                return self._row_to_conflict(row)

        except Exception as e:
            logger.error(f"Erro ao buscar conflito {conflict_id.value}: {e}")
            return None

    async def find_by_cpf_hash(self, cpf_hash: str) -> List[DuplicateConflict]:
        """Busca conflitos por hash de CPF."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM duplicate_conflicts
                    WHERE cpf_hash = ?
                    ORDER BY created_at DESC
                """, (cpf_hash,))

                rows = await cursor.fetchall()
                return [self._row_to_conflict(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar conflitos por CPF hash: {e}")
            return []

    async def find_by_status(self, status: ConflictStatus) -> List[DuplicateConflict]:
        """Busca conflitos por status."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM duplicate_conflicts
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status.value,))

                rows = await cursor.fetchall()
                return [self._row_to_conflict(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar conflitos por status {status.value}: {e}")
            return []

    async def find_pending_conflicts(self) -> List[DuplicateConflict]:
        """Busca todos os conflitos pendentes."""
        return await self.find_by_status(ConflictStatus.PENDING)

    async def find_expired_pending_conflicts(self) -> List[DuplicateConflict]:
        """Busca conflitos pendentes que já expiraram."""
        try:
            now = datetime.now().isoformat()

            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM duplicate_conflicts
                    WHERE status = ? AND expires_at < ?
                    ORDER BY expires_at ASC
                """, (ConflictStatus.PENDING.value, now))

                rows = await cursor.fetchall()
                return [self._row_to_conflict(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar conflitos expirados: {e}")
            return []

    async def find_by_user_id(self, user_id: int) -> List[DuplicateConflict]:
        """Busca conflitos envolvendo um usuário específico."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM duplicate_conflicts
                    WHERE user_ids LIKE ?
                    ORDER BY created_at DESC
                """, (f'%{user_id}%',))

                rows = await cursor.fetchall()
                # Filtra apenas conflitos onde o user_id está realmente na lista
                conflicts = []
                for row in rows:
                    conflict = self._row_to_conflict(row)
                    if user_id in conflict.user_ids:
                        conflicts.append(conflict)

                return conflicts

        except Exception as e:
            logger.error(f"Erro ao buscar conflitos do usuário {user_id}: {e}")
            return []

    async def find_by_notified_user(self, user_id: int) -> List[DuplicateConflict]:
        """Busca conflitos onde um usuário foi notificado."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM duplicate_conflicts
                    WHERE notified_user_id = ?
                    ORDER BY created_at DESC
                """, (user_id,))

                rows = await cursor.fetchall()
                return [self._row_to_conflict(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar conflitos notificados para {user_id}: {e}")
            return []

    async def exists_pending_for_cpf(self, cpf_hash: str) -> bool:
        """Verifica se já existe um conflito pendente para um CPF."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT 1 FROM duplicate_conflicts
                    WHERE cpf_hash = ? AND status = ?
                    LIMIT 1
                """, (cpf_hash, ConflictStatus.PENDING.value))

                result = await cursor.fetchone()
                return result is not None

        except Exception as e:
            logger.error(f"Erro ao verificar conflito pendente para CPF: {e}")
            return False

    async def get_conflict_statistics(self, days: int = 30) -> dict:
        """Obtém estatísticas de conflitos."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            async with aiosqlite.connect(self.db_path) as db:
                # Contagem por status
                cursor = await db.execute("""
                    SELECT status, COUNT(*) as count
                    FROM duplicate_conflicts
                    WHERE created_at >= ?
                    GROUP BY status
                """, (cutoff_date,))

                status_counts = {row[0]: row[1] for row in await cursor.fetchall()}

                # Total
                total = sum(status_counts.values())

                # Taxa de resolução
                resolved = status_counts.get(ConflictStatus.RESOLVED.value, 0)
                resolution_rate = (resolved / total * 100) if total > 0 else 0

                return {
                    'period_days': days,
                    'total': total,
                    'pending': status_counts.get(ConflictStatus.PENDING.value, 0),
                    'resolved': resolved,
                    'expired_removed': status_counts.get(ConflictStatus.EXPIRED_REMOVED.value, 0),
                    'admin_resolved': status_counts.get(ConflictStatus.ADMIN_RESOLVED.value, 0),
                    'resolution_rate': f"{resolution_rate:.1f}%"
                }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de conflitos: {e}")
            return {}

    async def cleanup_old_resolved_conflicts(self, days_old: int = 90) -> int:
        """Remove conflitos resolvidos antigos do sistema."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM duplicate_conflicts
                    WHERE status IN (?, ?) AND resolved_at < ?
                """, (ConflictStatus.RESOLVED.value, ConflictStatus.ADMIN_RESOLVED.value, cutoff_date))

                await db.commit()
                removed_count = cursor.rowcount

                logger.info(f"Removidos {removed_count} conflitos resolvidos antigos")
                return removed_count

        except Exception as e:
            logger.error(f"Erro ao limpar conflitos antigos: {e}")
            return 0

    async def delete(self, entity_id: ConflictId) -> bool:
        """Remove um conflito."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    DELETE FROM duplicate_conflicts WHERE id = ?
                """, (entity_id.value,))

                await db.commit()
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Erro ao remover conflito {entity_id.value}: {e}")
            return False

    async def exists(self, entity_id: ConflictId) -> bool:
        """Verifica se um conflito existe."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT 1 FROM duplicate_conflicts WHERE id = ? LIMIT 1
                """, (entity_id.value,))

                result = await cursor.fetchone()
                return result is not None

        except Exception as e:
            logger.error(f"Erro ao verificar existência de conflito: {e}")
            return False

    def _row_to_conflict(self, row: aiosqlite.Row) -> DuplicateConflict:
        """Converte row do SQLite para entidade DuplicateConflict."""
        # Parse user_ids do JSON
        user_ids = json.loads(row['user_ids'])
        conflict_data = json.loads(row['conflict_data']) if row['conflict_data'] else {}

        # Cria conflito
        conflict = DuplicateConflict(
            conflict_id=ConflictId(row['id']),
            cpf_hash=row['cpf_hash'],
            user_ids=user_ids,
            notified_user_id=row['notified_user_id'],
            conflict_data=conflict_data,
            expires_at=datetime.fromisoformat(row['expires_at'])
        )

        # Restaura estado
        conflict._status = ConflictStatus(row['status'])
        conflict._created_at = datetime.fromisoformat(row['created_at'])

        if row['resolved_at']:
            conflict._resolved_at = datetime.fromisoformat(row['resolved_at'])

        if row['resolved_by']:
            conflict._resolved_by = row['resolved_by']

        if row['resolution_choice']:
            conflict._resolution_choice = row['resolution_choice']

        if row['resolution_action']:
            conflict._resolution_action = ResolutionAction(row['resolution_action'])

        return conflict
