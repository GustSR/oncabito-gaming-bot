"""
SQLite HubSoft Integration Repository Implementation.

Implementa persistência de integrações HubSoft usando SQLite.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from ...domain.entities.hubsoft_integration import (
    HubSoftIntegrationRequest,
    IntegrationId,
    IntegrationType,
    IntegrationStatus,
    IntegrationPriority,
    IntegrationAttempt
)
from ...domain.repositories.hubsoft_repository import HubSoftIntegrationRepository

logger = logging.getLogger(__name__)


class SQLiteHubSoftIntegrationRepository(HubSoftIntegrationRepository):
    """Implementação SQLite do repositório de integrações HubSoft."""

    def __init__(self, db_path: str = "data/oncabo.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self) -> None:
        """Inicializa tabelas do banco."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hubsoft_integrations (
                    id TEXT PRIMARY KEY,
                    integration_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    metadata TEXT,
                    max_retries INTEGER NOT NULL,
                    timeout_seconds INTEGER NOT NULL,
                    scheduled_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    hubsoft_response TEXT,
                    error_details TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS hubsoft_integration_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    integration_id TEXT NOT NULL,
                    attempted_at TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    response_data TEXT,
                    duration_ms INTEGER,
                    FOREIGN KEY (integration_id) REFERENCES hubsoft_integrations(id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hubsoft_integrations_type ON hubsoft_integrations(integration_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hubsoft_integrations_status ON hubsoft_integrations(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hubsoft_integrations_priority ON hubsoft_integrations(priority)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hubsoft_integrations_scheduled_at ON hubsoft_integrations(scheduled_at)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hubsoft_integration_attempts_integration_id ON hubsoft_integration_attempts(integration_id)
            """)

            conn.commit()

    async def save(self, integration: HubSoftIntegrationRequest) -> None:
        """Salva uma integração."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Verifica se já existe
                cursor.execute(
                    "SELECT id FROM hubsoft_integrations WHERE id = ?",
                    (integration.id.value,)
                )
                exists = cursor.fetchone()

                if exists:
                    # Update
                    cursor.execute("""
                        UPDATE hubsoft_integrations SET
                            integration_type = ?,
                            priority = ?,
                            status = ?,
                            payload = ?,
                            metadata = ?,
                            max_retries = ?,
                            timeout_seconds = ?,
                            scheduled_at = ?,
                            started_at = ?,
                            completed_at = ?,
                            hubsoft_response = ?,
                            error_details = ?
                        WHERE id = ?
                    """, (
                        integration.integration_type.value,
                        integration.priority.value,
                        integration.status.value,
                        self._serialize_data(integration.payload),
                        self._serialize_data(integration.metadata),
                        integration.max_retries,
                        integration.timeout_seconds,
                        integration.scheduled_at.isoformat() if integration.scheduled_at else None,
                        integration.started_at.isoformat() if integration.started_at else None,
                        integration.completed_at.isoformat() if integration.completed_at else None,
                        self._serialize_data(integration.hubsoft_response),
                        self._serialize_data(integration.error_details),
                        integration.id.value
                    ))
                else:
                    # Insert
                    cursor.execute("""
                        INSERT INTO hubsoft_integrations (
                            id, integration_type, priority, status, payload, metadata,
                            max_retries, timeout_seconds, scheduled_at, started_at,
                            completed_at, hubsoft_response, error_details, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        integration.id.value,
                        integration.integration_type.value,
                        integration.priority.value,
                        integration.status.value,
                        self._serialize_data(integration.payload),
                        self._serialize_data(integration.metadata),
                        integration.max_retries,
                        integration.timeout_seconds,
                        integration.scheduled_at.isoformat() if integration.scheduled_at else None,
                        integration.started_at.isoformat() if integration.started_at else None,
                        integration.completed_at.isoformat() if integration.completed_at else None,
                        self._serialize_data(integration.hubsoft_response),
                        self._serialize_data(integration.error_details),
                        datetime.now().isoformat()
                    ))

                # Salva tentativas
                await self._save_attempts(conn, integration)

                conn.commit()
                logger.debug(f"Integração {integration.id.value} salva com sucesso")

        except Exception as e:
            logger.error(f"Erro ao salvar integração {integration.id.value}: {e}")
            raise

    async def _save_attempts(self, conn: sqlite3.Connection, integration: HubSoftIntegrationRequest) -> None:
        """Salva tentativas de integração."""
        cursor = conn.cursor()

        # Remove tentativas existentes
        cursor.execute(
            "DELETE FROM hubsoft_integration_attempts WHERE integration_id = ?",
            (integration.id.value,)
        )

        # Insere tentativas atuais
        for attempt in integration.attempts:
            cursor.execute("""
                INSERT INTO hubsoft_integration_attempts (
                    integration_id, attempted_at, success, error_message,
                    response_data, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                integration.id.value,
                attempt.attempted_at.isoformat(),
                attempt.success,
                attempt.error_message,
                self._serialize_data(attempt.response_data),
                attempt.duration_ms
            ))

    async def find_by_id(self, integration_id: IntegrationId) -> Optional[HubSoftIntegrationRequest]:
        """Busca integração por ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM hubsoft_integrations WHERE id = ?",
                    (integration_id.value,)
                )
                row = cursor.fetchone()

                if not row:
                    return None

                return await self._row_to_integration(conn, row)

        except Exception as e:
            logger.error(f"Erro ao buscar integração {integration_id.value}: {e}")
            return None

    async def find_pending_integrations(
        self,
        integration_type: Optional[IntegrationType] = None,
        limit: int = 50
    ) -> List[HubSoftIntegrationRequest]:
        """Busca integrações pendentes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                where_clause = "WHERE status = 'pending'"
                params = []

                if integration_type:
                    where_clause += " AND integration_type = ?"
                    params.append(integration_type.value)

                cursor.execute(f"""
                    SELECT * FROM hubsoft_integrations
                    {where_clause}
                    ORDER BY priority DESC, created_at ASC
                    LIMIT ?
                """, params + [limit])

                rows = cursor.fetchall()
                return [await self._row_to_integration(conn, row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar integrações pendentes: {e}")
            return []

    async def find_scheduled_integrations(
        self,
        until: datetime,
        limit: int = 50
    ) -> List[HubSoftIntegrationRequest]:
        """Busca integrações agendadas até uma data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM hubsoft_integrations
                    WHERE status = 'pending' AND scheduled_at IS NOT NULL AND scheduled_at <= ?
                    ORDER BY priority DESC, scheduled_at ASC
                    LIMIT ?
                """, (until.isoformat(), limit))

                rows = cursor.fetchall()
                return [await self._row_to_integration(conn, row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar integrações agendadas: {e}")
            return []

    async def find_active_integrations(
        self,
        integration_type: Optional[IntegrationType] = None
    ) -> List[HubSoftIntegrationRequest]:
        """Busca integrações ativas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                where_clause = "WHERE status = 'in_progress'"
                params = []

                if integration_type:
                    where_clause += " AND integration_type = ?"
                    params.append(integration_type.value)

                cursor.execute(f"""
                    SELECT * FROM hubsoft_integrations
                    {where_clause}
                    ORDER BY started_at ASC
                """, params)

                rows = cursor.fetchall()
                return [await self._row_to_integration(conn, row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar integrações ativas: {e}")
            return []

    async def find_failed_integrations(
        self,
        integration_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[HubSoftIntegrationRequest]:
        """Busca integrações falhadas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                where_clause = "WHERE status = 'failed'"
                params = []

                if integration_type:
                    where_clause += " AND integration_type = ?"
                    params.append(integration_type)

                if since:
                    where_clause += " AND completed_at >= ?"
                    params.append(since.isoformat())

                cursor.execute(f"""
                    SELECT * FROM hubsoft_integrations
                    {where_clause}
                    ORDER BY completed_at DESC
                    LIMIT ?
                """, params + [limit])

                rows = cursor.fetchall()
                return [await self._row_to_integration(conn, row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar integrações falhadas: {e}")
            return []

    async def find_completed_integrations(
        self,
        integration_type: Optional[IntegrationType] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[HubSoftIntegrationRequest]:
        """Busca integrações completadas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                where_clause = "WHERE status = 'completed'"
                params = []

                if integration_type:
                    where_clause += " AND integration_type = ?"
                    params.append(integration_type.value)

                if since:
                    where_clause += " AND completed_at >= ?"
                    params.append(since.isoformat())

                cursor.execute(f"""
                    SELECT * FROM hubsoft_integrations
                    {where_clause}
                    ORDER BY completed_at DESC
                    LIMIT ?
                """, params + [limit])

                rows = cursor.fetchall()
                return [await self._row_to_integration(conn, row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar integrações completadas: {e}")
            return []

    async def find_by_metadata(
        self,
        metadata_key: str,
        metadata_value: Any,
        status: Optional[IntegrationStatus] = None
    ) -> List[HubSoftIntegrationRequest]:
        """Busca integrações por metadados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                where_clause = "WHERE metadata LIKE ?"
                params = [f'%"{metadata_key}":"{metadata_value}"%']

                if status:
                    where_clause += " AND status = ?"
                    params.append(status.value)

                cursor.execute(f"""
                    SELECT * FROM hubsoft_integrations
                    {where_clause}
                    ORDER BY created_at DESC
                """, params)

                rows = cursor.fetchall()
                return [await self._row_to_integration(conn, row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar integrações por metadados: {e}")
            return []

    async def count_integrations_by_status(
        self,
        since: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Conta integrações por status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                where_clause = ""
                params = []

                if since:
                    where_clause = "WHERE created_at >= ?"
                    params.append(since.isoformat())

                cursor.execute(f"""
                    SELECT status, COUNT(*) as count
                    FROM hubsoft_integrations
                    {where_clause}
                    GROUP BY status
                """, params)

                return {row[0]: row[1] for row in cursor.fetchall()}

        except Exception as e:
            logger.error(f"Erro ao contar integrações por status: {e}")
            return {}

    async def cleanup_completed_integrations(
        self,
        older_than: datetime,
        batch_size: int = 100
    ) -> int:
        """Remove integrações completadas antigas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Remove tentativas primeiro (foreign key)
                cursor.execute("""
                    DELETE FROM hubsoft_integration_attempts
                    WHERE integration_id IN (
                        SELECT id FROM hubsoft_integrations
                        WHERE status = 'completed' AND completed_at < ?
                        LIMIT ?
                    )
                """, (older_than.isoformat(), batch_size))

                # Remove integrações
                cursor.execute("""
                    DELETE FROM hubsoft_integrations
                    WHERE status = 'completed' AND completed_at < ?
                    LIMIT ?
                """, (older_than.isoformat(), batch_size))

                removed_count = cursor.rowcount
                conn.commit()

                logger.info(f"Removidas {removed_count} integrações completadas")
                return removed_count

        except Exception as e:
            logger.error(f"Erro ao limpar integrações completadas: {e}")
            return 0

    async def get_integration_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        integration_type: Optional[IntegrationType] = None
    ) -> Dict[str, Any]:
        """Obtém métricas de integração."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                where_clause = "WHERE created_at BETWEEN ? AND ?"
                params = [start_date.isoformat(), end_date.isoformat()]

                if integration_type:
                    where_clause += " AND integration_type = ?"
                    params.append(integration_type.value)

                # Contagem total
                cursor.execute(f"""
                    SELECT COUNT(*) FROM hubsoft_integrations {where_clause}
                """, params)
                total = cursor.fetchone()[0]

                # Contagem por status
                cursor.execute(f"""
                    SELECT status, COUNT(*) as count
                    FROM hubsoft_integrations
                    {where_clause}
                    GROUP BY status
                """, params)
                status_counts = {row[0]: row[1] for row in cursor.fetchall()}

                # Duração média
                cursor.execute(f"""
                    SELECT AVG(
                        CASE
                            WHEN completed_at IS NOT NULL AND started_at IS NOT NULL
                            THEN (julianday(completed_at) - julianday(started_at)) * 86400
                            ELSE NULL
                        END
                    ) as avg_duration
                    FROM hubsoft_integrations
                    {where_clause} AND status = 'completed'
                """, params)
                avg_duration = cursor.fetchone()[0] or 0

                # Taxa de sucesso
                successful = status_counts.get('completed', 0)
                success_rate = (successful / total * 100) if total > 0 else 0

                return {
                    'total_integrations': total,
                    'successful': successful,
                    'failed': status_counts.get('failed', 0),
                    'pending': status_counts.get('pending', 0),
                    'in_progress': status_counts.get('in_progress', 0),
                    'avg_duration_seconds': round(avg_duration, 2),
                    'success_rate': round(success_rate, 2),
                    'period_days': (end_date - start_date).days
                }

        except Exception as e:
            logger.error(f"Erro ao obter métricas: {e}")
            return {}

    async def _row_to_integration(self, conn: sqlite3.Connection, row: sqlite3.Row) -> HubSoftIntegrationRequest:
        """Converte row do SQLite para entidade HubSoftIntegrationRequest."""
        # Busca tentativas
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM hubsoft_integration_attempts
            WHERE integration_id = ?
            ORDER BY attempted_at ASC
        """, (row['id'],))

        attempt_rows = cursor.fetchall()
        attempts = []

        for attempt_row in attempt_rows:
            attempt = IntegrationAttempt(
                attempted_at=datetime.fromisoformat(attempt_row[2]),  # attempted_at
                success=bool(attempt_row[3]),  # success
                error_message=attempt_row[4],  # error_message
                response_data=self._deserialize_data(attempt_row[5]),  # response_data
                duration_ms=attempt_row[6]  # duration_ms
            )
            attempts.append(attempt)

        # Cria integração
        integration = HubSoftIntegrationRequest(
            integration_id=IntegrationId(row['id']),
            integration_type=IntegrationType(row['integration_type']),
            priority=IntegrationPriority(row['priority']),
            payload=self._deserialize_data(row['payload']),
            metadata=self._deserialize_data(row['metadata']),
            max_retries=row['max_retries'],
            timeout_seconds=row['timeout_seconds']
        )

        # Restaura estado
        integration._status = IntegrationStatus(row['status'])

        if row['scheduled_at']:
            integration._scheduled_at = datetime.fromisoformat(row['scheduled_at'])

        if row['started_at']:
            integration._started_at = datetime.fromisoformat(row['started_at'])

        if row['completed_at']:
            integration._completed_at = datetime.fromisoformat(row['completed_at'])

        if row['hubsoft_response']:
            integration._hubsoft_response = self._deserialize_data(row['hubsoft_response'])

        if row['error_details']:
            integration._error_details = self._deserialize_data(row['error_details'])

        integration._attempts = attempts

        return integration

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