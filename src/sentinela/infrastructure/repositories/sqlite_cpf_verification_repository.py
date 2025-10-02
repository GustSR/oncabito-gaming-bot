"""
SQLite CPF Verification Repository Implementation.

Implementa persistência de verificações CPF usando SQLite.
"""

import logging
import sqlite3
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from ...domain.entities.cpf_verification import CPFVerificationRequest, VerificationId, VerificationStatus, VerificationAttempt, VerificationType
from ...domain.repositories.cpf_verification_repository import CPFVerificationRepository
from ...domain.value_objects.identifiers import UserId

logger = logging.getLogger(__name__)


class SQLiteCPFVerificationRepository(CPFVerificationRepository):
    """Implementação SQLite do repositório de verificações CPF."""

    def __init__(self, db_path: str = "data/oncabo.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self) -> None:
        """Inicializa tabelas do banco."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cpf_verifications (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    cpf_hash TEXT NOT NULL,
                    verification_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    completed_at TEXT,
                    verification_data TEXT,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cpf_verification_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    verification_id TEXT NOT NULL,
                    attempted_at TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    response_data TEXT,
                    error_message TEXT,
                    duration_ms INTEGER,
                    FOREIGN KEY (verification_id) REFERENCES cpf_verifications(id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cpf_verifications_user_id ON cpf_verifications(user_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cpf_verifications_status ON cpf_verifications(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cpf_verifications_cpf_hash ON cpf_verifications(cpf_hash)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cpf_verification_attempts_verification_id ON cpf_verification_attempts(verification_id)
            """)

            conn.commit()

    async def save(self, verification: CPFVerificationRequest) -> None:
        """Salva uma verificação CPF."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Verifica se já existe
                cursor.execute(
                    "SELECT id FROM cpf_verifications WHERE id = ?",
                    (verification.id.value,)
                )
                exists = cursor.fetchone()

                if exists:
                    # Update
                    cursor.execute("""
                        UPDATE cpf_verifications SET
                            user_id = ?,
                            username = ?,
                            cpf_hash = ?,
                            verification_type = ?,
                            status = ?,
                            max_attempts = ?,
                            expires_at = ?,
                            completed_at = ?,
                            verification_data = ?,
                            metadata = ?
                        WHERE id = ?
                    """, (
                        verification.user_id,
                        verification.username,
                        verification.cpf_hash,
                        verification.verification_type,
                        verification.status.value,
                        verification.max_attempts,
                        verification.expires_at.isoformat(),
                        verification.completed_at.isoformat() if verification.completed_at else None,
                        self._serialize_data(verification.verification_data),
                        self._serialize_data(verification.metadata),
                        verification.id.value
                    ))
                else:
                    # Insert
                    cursor.execute("""
                        INSERT INTO cpf_verifications (
                            id, user_id, username, cpf_hash, verification_type,
                            status, max_attempts, created_at, expires_at,
                            completed_at, verification_data, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        verification.id.value,
                        verification.user_id,
                        verification.username,
                        verification.cpf_hash,
                        verification.verification_type,
                        verification.status.value,
                        verification.max_attempts,
                        verification.created_at.isoformat(),
                        verification.expires_at.isoformat(),
                        verification.completed_at.isoformat() if verification.completed_at else None,
                        self._serialize_data(verification.verification_data),
                        self._serialize_data(verification.metadata)
                    ))

                # Salva tentativas
                await self._save_attempts(conn, verification)

                conn.commit()
                logger.debug(f"Verificação {verification.id.value} salva com sucesso")

        except Exception as e:
            logger.error(f"Erro ao salvar verificação {verification.id.value}: {e}")
            raise

    async def _save_attempts(self, conn: sqlite3.Connection, verification: CPFVerificationRequest) -> None:
        """Salva tentativas de verificação."""
        cursor = conn.cursor()

        # Remove tentativas existentes
        cursor.execute(
            "DELETE FROM cpf_verification_attempts WHERE verification_id = ?",
            (verification.id.value,)
        )

        # Insere tentativas atuais
        for attempt in verification.attempts:
            cursor.execute("""
                INSERT INTO cpf_verification_attempts (
                    verification_id, attempted_at, success, response_data,
                    error_message, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                verification.id.value,
                attempt.attempted_at.isoformat(),
                attempt.success,
                self._serialize_data(attempt.response_data),
                attempt.error_message,
                attempt.duration_ms
            ))

    async def find_by_id(self, verification_id: VerificationId) -> Optional[CPFVerificationRequest]:
        """Busca verificação por ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM cpf_verifications WHERE id = ?",
                    (verification_id.value,)
                )
                row = cursor.fetchone()

                if not row:
                    return None

                return await self._row_to_verification(conn, row)

        except Exception as e:
            logger.error(f"Erro ao buscar verificação {verification_id.value}: {e}")
            return None

    async def find_by_user_id(self, user_id: int, limit: int = 10) -> List[CPFVerificationRequest]:
        """Busca verificações por usuário."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM cpf_verifications
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id, limit))

                rows = cursor.fetchall()
                return [await self._row_to_verification(conn, row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar verificações do usuário {user_id}: {e}")
            return []

    async def find_pending_by_user(self, user_id: int) -> Optional[CPFVerificationRequest]:
        """Busca verificação pendente de um usuário."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM cpf_verifications
                    WHERE user_id = ? AND status IN ('pending', 'in_progress')
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user_id,))

                row = cursor.fetchone()

                if not row:
                    return None

                return await self._row_to_verification(conn, row)

        except Exception as e:
            logger.error(f"Erro ao buscar verificação pendente do usuário {user_id}: {e}")
            return None

    async def find_by_status(self, status: VerificationStatus, limit: int = 50) -> List[CPFVerificationRequest]:
        """Busca verificações por status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM cpf_verifications
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (status.value, limit))

                rows = cursor.fetchall()
                return [await self._row_to_verification(conn, row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar verificações com status {status.value}: {e}")
            return []

    async def find_expired(self, limit: int = 100) -> List[CPFVerificationRequest]:
        """Busca verificações expiradas."""
        try:
            now = datetime.now().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM cpf_verifications
                    WHERE expires_at < ? AND status NOT IN ('completed', 'failed', 'expired')
                    ORDER BY expires_at ASC
                    LIMIT ?
                """, (now, limit))

                rows = cursor.fetchall()
                return [await self._row_to_verification(conn, row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar verificações expiradas: {e}")
            return []

    async def get_verification_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtém estatísticas de verificação."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                where_clause = ""
                params = []

                if user_id:
                    where_clause = "WHERE user_id = ?"
                    params.append(user_id)

                # Contagem por status
                cursor.execute(f"""
                    SELECT status, COUNT(*) as count
                    FROM cpf_verifications
                    {where_clause}
                    GROUP BY status
                """, params)

                status_counts = {row[0]: row[1] for row in cursor.fetchall()}

                # Taxa de sucesso
                total = sum(status_counts.values())
                completed = status_counts.get('completed', 0)
                success_rate = (completed / total * 100) if total > 0 else 0

                return {
                    'total': total,
                    'pending': status_counts.get('pending', 0),
                    'in_progress': status_counts.get('in_progress', 0),
                    'completed': completed,
                    'failed': status_counts.get('failed', 0),
                    'expired': status_counts.get('expired', 0),
                    'success_rate': f"{success_rate:.1f}%"
                }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}

    async def cleanup_expired(self, older_than_days: int = 7) -> int:
        """Remove verificações expiradas antigas."""
        try:
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - older_than_days)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Remove tentativas primeiro (foreign key)
                cursor.execute("""
                    DELETE FROM cpf_verification_attempts
                    WHERE verification_id IN (
                        SELECT id FROM cpf_verifications
                        WHERE status = 'expired' AND expires_at < ?
                    )
                """, (cutoff_date.isoformat(),))

                # Remove verificações
                cursor.execute("""
                    DELETE FROM cpf_verifications
                    WHERE status = 'expired' AND expires_at < ?
                """, (cutoff_date.isoformat(),))

                removed_count = cursor.rowcount
                conn.commit()

                logger.info(f"Removidas {removed_count} verificações expiradas")
                return removed_count

        except Exception as e:
            logger.error(f"Erro ao limpar verificações expiradas: {e}")
            return 0

    async def _row_to_verification(self, conn: sqlite3.Connection, row: sqlite3.Row) -> CPFVerificationRequest:
        """Converte row do SQLite para entidade CPFVerificationRequest."""
        # Busca tentativas
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM cpf_verification_attempts
            WHERE verification_id = ?
            ORDER BY attempted_at ASC
        """, (row['id'],))

        attempt_rows = cursor.fetchall()
        attempts = []

        for attempt_row in attempt_rows:
            attempt = VerificationAttempt(
                attempted_at=datetime.fromisoformat(attempt_row[2]),  # attempted_at
                success=bool(attempt_row[3]),  # success
                response_data=self._deserialize_data(attempt_row[4]),  # response_data
                error_message=attempt_row[5],  # error_message
                duration_ms=attempt_row[6]  # duration_ms
            )
            attempts.append(attempt)

        # Cria verificação
        verification = CPFVerificationRequest(
            verification_id=VerificationId(row['id']),
            user_id=row['user_id'],
            username=row['username'],
            cpf_hash=row['cpf_hash'],
            verification_type=row['verification_type'],
            max_attempts=row['max_attempts'],
            expires_at=datetime.fromisoformat(row['expires_at'])
        )

        # Restaura estado
        verification._status = VerificationStatus(row['status'])
        verification._created_at = datetime.fromisoformat(row['created_at'])

        if row['completed_at']:
            verification._completed_at = datetime.fromisoformat(row['completed_at'])

        if row['verification_data']:
            verification._verification_data = self._deserialize_data(row['verification_data'])

        if row['metadata']:
            verification._metadata = self._deserialize_data(row['metadata'])

        verification._attempts = attempts

        return verification

    def _serialize_data(self, data: Dict[str, Any]) -> str:
        """Serializa dados para JSON."""
        import json
        return json.dumps(data) if data else "{}"

    def _deserialize_data(self, data_str: str) -> Dict[str, Any]:
        """Deserializa dados do JSON."""
        import json
        try:
            return json.loads(data_str) if data_str else {}
        except:
            return {}

    async def cleanup_old_verifications(self, days_old: int = 30) -> int:
        """Remove verificações antigas do sistema."""
        return await self.cleanup_expired(days_old)

    async def count_attempts_by_user(self, user_id: UserId, hours: int = 24) -> int:
        """Conta tentativas de verificação de um usuário em um período."""
        from datetime import datetime, timedelta

        cutoff_time = datetime.now() - timedelta(hours=hours)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM cpf_verifications
                WHERE user_id = ? AND created_at >= ?
            """, (user_id.value, cutoff_time.isoformat()))

            result = await cursor.fetchone()
            return result[0] if result else 0

    async def delete(self, entity_id: VerificationId) -> bool:
        """Remove uma verificação."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM cpf_verifications WHERE id = ?
            """, (entity_id.value,))

            await db.commit()
            return cursor.rowcount > 0

    async def exists(self, entity_id: VerificationId) -> bool:
        """Verifica se uma verificação existe."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 1 FROM cpf_verifications WHERE id = ? LIMIT 1
            """, (entity_id.value,))

            result = await cursor.fetchone()
            return result is not None

    async def find_by_cpf(self, cpf: str) -> List[CPFVerificationRequest]:
        """Busca verificações por CPF fornecido."""
        from ...domain.services.cpf_validation_service import CPFValidationService

        cpf_hash = CPFValidationService.hash_cpf(cpf)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM cpf_verifications
                WHERE cpf_hash = ?
                ORDER BY created_at DESC
            """, (cpf_hash,))

            rows = await cursor.fetchall()
            return [await self._row_to_verification(db, row) for row in rows]

    async def find_by_verification_type(self, verification_type: VerificationType) -> List[CPFVerificationRequest]:
        """Busca verificações por tipo."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM cpf_verifications
                WHERE verification_type = ?
                ORDER BY created_at DESC
            """, (verification_type.value,))

            rows = await cursor.fetchall()
            return [await self._row_to_verification(db, row) for row in rows]

    async def find_conflicting_verifications(self, cpf: str, user_id: UserId) -> List[CPFVerificationRequest]:
        """Busca verificações que podem gerar conflito de CPF."""
        from ...domain.services.cpf_validation_service import CPFValidationService

        cpf_hash = CPFValidationService.hash_cpf(cpf)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM cpf_verifications
                WHERE cpf_hash = ? AND user_id != ? AND status = ?
                ORDER BY created_at DESC
            """, (cpf_hash, user_id.value, VerificationStatus.VERIFIED.value))

            rows = await cursor.fetchall()
            return [await self._row_to_verification(db, row) for row in rows]

    async def find_expired_verifications(self) -> List[CPFVerificationRequest]:
        """Busca verificações expiradas."""
        return await self.find_expired()

    async def find_recent_verifications(self, hours: int = 24) -> List[CPFVerificationRequest]:
        """Busca verificações recentes."""
        from datetime import datetime, timedelta

        cutoff_time = datetime.now() - timedelta(hours=hours)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM cpf_verifications
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """, (cutoff_time.isoformat(),))

            rows = await cursor.fetchall()
            return [await self._row_to_verification(db, row) for row in rows]