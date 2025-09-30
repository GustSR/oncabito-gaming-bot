"""
SQLite Ticket Repository Implementation.

Implementa persistência de tickets usando SQLite,
mantendo compatibilidade com o sistema atual.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from ...domain.entities.ticket import Ticket, TicketId, TicketStatus, UrgencyLevel
from ...domain.entities.user import User
from ...domain.repositories.ticket_repository import TicketRepository
from ...domain.value_objects.identifiers import UserId, Protocol, HubSoftId
from ...domain.value_objects.ticket_category import TicketCategory, TicketCategoryType
from ...domain.value_objects.game_title import GameTitle, GameType
from ...domain.value_objects.problem_timing import ProblemTiming, TimingType

logger = logging.getLogger(__name__)


class SQLiteTicketRepository(TicketRepository):
    """Implementação SQLite do repositório de tickets."""

    def __init__(self, db_path: str = "data/oncabo.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self) -> None:
        """Inicializa tabelas do banco."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    telegram_user_id INTEGER NOT NULL,
                    category_type TEXT NOT NULL,
                    category_display_name TEXT NOT NULL,
                    game_type TEXT NOT NULL,
                    game_display_name TEXT NOT NULL,
                    timing_type TEXT NOT NULL,
                    timing_display_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    urgency_level TEXT NOT NULL,
                    status TEXT NOT NULL,
                    protocol_local TEXT NOT NULL,
                    protocol_hubsoft TEXT,
                    assigned_technician TEXT,
                    resolution_notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    closed_at TEXT,
                    hubsoft_synced BOOLEAN DEFAULT FALSE,
                    hubsoft_sync_at TEXT,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tickets_protocol_local ON tickets(protocol_local)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tickets_protocol_hubsoft ON tickets(protocol_hubsoft)
            """)

            conn.commit()

    async def save(self, ticket: Ticket) -> None:
        """Salva um ticket."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Verifica se já existe
                cursor.execute(
                    "SELECT id FROM tickets WHERE id = ?",
                    (ticket.id.value,)
                )
                exists = cursor.fetchone()

                if exists:
                    # Update
                    cursor.execute("""
                        UPDATE tickets SET
                            user_id = ?,
                            username = ?,
                            telegram_user_id = ?,
                            category_type = ?,
                            category_display_name = ?,
                            game_type = ?,
                            game_display_name = ?,
                            timing_type = ?,
                            timing_display_name = ?,
                            description = ?,
                            urgency_level = ?,
                            status = ?,
                            protocol_local = ?,
                            protocol_hubsoft = ?,
                            assigned_technician = ?,
                            resolution_notes = ?,
                            updated_at = ?,
                            closed_at = ?,
                            hubsoft_synced = ?,
                            hubsoft_sync_at = ?,
                            metadata = ?
                        WHERE id = ?
                    """, (
                        ticket.user.user_id.value,
                        ticket.user.username,
                        ticket.user.telegram_user_id,
                        ticket.category.category_type.value,
                        ticket.category.display_name,
                        ticket.affected_game.game_type.value,
                        ticket.affected_game.display_name,
                        ticket.problem_timing.timing_type.value,
                        ticket.problem_timing.display_name,
                        ticket.description,
                        ticket.urgency_level.value,
                        ticket.status.value,
                        ticket.protocol.local_id,
                        ticket.protocol.hubsoft_id,
                        ticket.assigned_technician,
                        ticket.resolution_notes,
                        ticket.updated_at.isoformat(),
                        ticket.closed_at.isoformat() if ticket.closed_at else None,
                        ticket.hubsoft_synced,
                        ticket.hubsoft_sync_at.isoformat() if ticket.hubsoft_sync_at else None,
                        self._serialize_metadata(ticket.metadata),
                        ticket.id.value
                    ))
                else:
                    # Insert
                    cursor.execute("""
                        INSERT INTO tickets (
                            id, user_id, username, telegram_user_id,
                            category_type, category_display_name,
                            game_type, game_display_name,
                            timing_type, timing_display_name,
                            description, urgency_level, status,
                            protocol_local, protocol_hubsoft,
                            assigned_technician, resolution_notes,
                            created_at, updated_at, closed_at,
                            hubsoft_synced, hubsoft_sync_at, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ticket.id.value,
                        ticket.user.user_id.value,
                        ticket.user.username,
                        ticket.user.telegram_user_id,
                        ticket.category.category_type.value,
                        ticket.category.display_name,
                        ticket.affected_game.game_type.value,
                        ticket.affected_game.display_name,
                        ticket.problem_timing.timing_type.value,
                        ticket.problem_timing.display_name,
                        ticket.description,
                        ticket.urgency_level.value,
                        ticket.status.value,
                        ticket.protocol.local_id,
                        ticket.protocol.hubsoft_id,
                        ticket.assigned_technician,
                        ticket.resolution_notes,
                        ticket.created_at.isoformat(),
                        ticket.updated_at.isoformat(),
                        ticket.closed_at.isoformat() if ticket.closed_at else None,
                        ticket.hubsoft_synced,
                        ticket.hubsoft_sync_at.isoformat() if ticket.hubsoft_sync_at else None,
                        self._serialize_metadata(ticket.metadata)
                    ))

                conn.commit()
                logger.debug(f"Ticket {ticket.id.value} salvo com sucesso")

        except Exception as e:
            logger.error(f"Erro ao salvar ticket {ticket.id.value}: {e}")
            raise

    async def find_by_id(self, ticket_id: TicketId) -> Optional[Ticket]:
        """Busca ticket por ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM tickets WHERE id = ?",
                    (ticket_id.value,)
                )
                row = cursor.fetchone()

                if not row:
                    return None

                return self._row_to_ticket(row)

        except Exception as e:
            logger.error(f"Erro ao buscar ticket {ticket_id.value}: {e}")
            return None

    async def find_by_user_id(self, user_id: UserId, limit: int = 50) -> List[Ticket]:
        """Busca tickets por usuário."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM tickets
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id.value, limit))

                rows = cursor.fetchall()
                return [self._row_to_ticket(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar tickets do usuário {user_id.value}: {e}")
            return []

    async def find_by_status(self, status: TicketStatus, limit: int = 100) -> List[Ticket]:
        """Busca tickets por status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM tickets
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (status.value, limit))

                rows = cursor.fetchall()
                return [self._row_to_ticket(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar tickets com status {status.value}: {e}")
            return []

    async def find_by_protocol(self, protocol: str) -> Optional[Ticket]:
        """Busca ticket por protocolo (local ou HubSoft)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Busca primeiro por protocolo local
                cursor.execute(
                    "SELECT * FROM tickets WHERE protocol_local = ?",
                    (protocol,)
                )
                row = cursor.fetchone()

                if not row:
                    # Busca por protocolo HubSoft
                    cursor.execute(
                        "SELECT * FROM tickets WHERE protocol_hubsoft = ?",
                        (protocol,)
                    )
                    row = cursor.fetchone()

                if not row:
                    return None

                return self._row_to_ticket(row)

        except Exception as e:
            logger.error(f"Erro ao buscar ticket por protocolo {protocol}: {e}")
            return None

    async def find_pending_sync(self, limit: int = 50) -> List[Ticket]:
        """Busca tickets pendentes de sincronização."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM tickets
                    WHERE hubsoft_synced = FALSE
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (limit,))

                rows = cursor.fetchall()
                return [self._row_to_ticket(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar tickets pendentes de sync: {e}")
            return []

    async def find_by_assignee(self, technician_name: str, limit: int = 50) -> List[Ticket]:
        """Busca tickets atribuídos a um técnico."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM tickets
                    WHERE assigned_technician = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (technician_name, limit))

                rows = cursor.fetchall()
                return [self._row_to_ticket(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar tickets do técnico {technician_name}: {e}")
            return []

    async def find_all(self, limit: int = 100, offset: int = 0) -> List[Ticket]:
        """Busca todos os tickets com paginação."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM tickets
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))

                rows = cursor.fetchall()
                return [self._row_to_ticket(row) for row in rows]

        except Exception as e:
            logger.error(f"Erro ao buscar todos os tickets: {e}")
            return []

    async def count_by_status(self) -> Dict[str, int]:
        """Conta tickets por status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM tickets
                    GROUP BY status
                """)

                rows = cursor.fetchall()
                return {row[0]: row[1] for row in rows}

        except Exception as e:
            logger.error(f"Erro ao contar tickets por status: {e}")
            return {}

    async def get_user_ticket_count(self, user_id: UserId) -> int:
        """Obtém número de tickets de um usuário."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT COUNT(*) FROM tickets WHERE user_id = ?",
                    (user_id.value,)
                )

                return cursor.fetchone()[0]

        except Exception as e:
            logger.error(f"Erro ao contar tickets do usuário {user_id.value}: {e}")
            return 0

    def _row_to_ticket(self, row: sqlite3.Row) -> Ticket:
        """Converte row do SQLite para entidade Ticket."""
        user = User(
            user_id=UserId(row['user_id']),
            username=row['username'],
            telegram_user_id=row['telegram_user_id']
        )

        category = TicketCategory(
            category_type=TicketCategoryType(row['category_type']),
            display_name=row['category_display_name']
        )

        game = GameTitle(
            game_type=GameType(row['game_type']),
            display_name=row['game_display_name']
        )

        timing = ProblemTiming(
            timing_type=TimingType(row['timing_type']),
            display_name=row['timing_display_name']
        )

        protocol = Protocol(
            local_id=row['protocol_local'],
            hubsoft_id=row['protocol_hubsoft']
        )

        # Cria ticket básico
        ticket = Ticket(
            ticket_id=TicketId(row['id']),
            user=user,
            category=category,
            affected_game=game,
            problem_timing=timing,
            description=row['description'],
            urgency_level=UrgencyLevel(row['urgency_level']),
            protocol=protocol
        )

        # Restaura estado
        ticket._status = TicketStatus(row['status'])
        ticket._assigned_technician = row['assigned_technician']
        ticket._resolution_notes = row['resolution_notes']
        ticket._created_at = datetime.fromisoformat(row['created_at'])
        ticket._updated_at = datetime.fromisoformat(row['updated_at'])

        if row['closed_at']:
            ticket._closed_at = datetime.fromisoformat(row['closed_at'])

        ticket._hubsoft_synced = bool(row['hubsoft_synced'])

        if row['hubsoft_sync_at']:
            ticket._hubsoft_sync_at = datetime.fromisoformat(row['hubsoft_sync_at'])

        if row['metadata']:
            ticket._metadata = self._deserialize_metadata(row['metadata'])

        return ticket

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

    async def find_by_user(self, user_id: UserId) -> List[Ticket]:
        """Busca tickets por usuário."""
        return await self.find_by_user_id(user_id)

    async def find_active_tickets(self) -> List[Ticket]:
        """Busca todos os tickets ativos (não finalizados)."""
        active_statuses = [TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.ASSIGNED]
        tickets = []
        for status in active_statuses:
            tickets.extend(await self.find_by_status(status))
        return tickets

    async def find_by_hubsoft_id(self, hubsoft_id: HubSoftId) -> Optional[Ticket]:
        """Busca ticket por ID do HubSoft."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM tickets WHERE protocol_hubsoft = ?
                LIMIT 1
            """, (hubsoft_id.value,))

            row = await cursor.fetchone()
            if row:
                return self._row_to_ticket(row)
            return None

    async def find_active_by_user(self, user_id: UserId) -> List[Ticket]:
        """Busca tickets ativos de um usuário."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM tickets
                WHERE user_id = ? AND status IN (?, ?, ?)
                ORDER BY created_at DESC
            """, (user_id.value, TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value, TicketStatus.ASSIGNED.value))

            rows = await cursor.fetchall()
            return [self._row_to_ticket(row) for row in rows]

    async def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Ticket]:
        """Busca tickets criados em um período."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM tickets
                WHERE created_at BETWEEN ? AND ?
                ORDER BY created_at DESC
            """, (start_date.isoformat(), end_date.isoformat()))

            rows = await cursor.fetchall()
            return [self._row_to_ticket(row) for row in rows]

    async def count_active_by_user(self, user_id: UserId) -> int:
        """Conta tickets ativos de um usuário."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM tickets
                WHERE user_id = ? AND status IN (?, ?, ?)
            """, (user_id.value, TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value, TicketStatus.ASSIGNED.value))

            result = await cursor.fetchone()
            return result[0] if result else 0

    async def count_by_status(self, status: TicketStatus) -> int:
        """Conta tickets por status."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM tickets WHERE status = ?
            """, (status.value,))

            result = await cursor.fetchone()
            return result[0] if result else 0

    async def get_user_ticket_statistics(self, user_id: UserId) -> dict:
        """Obtém estatísticas de tickets de um usuário."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT
                    status,
                    COUNT(*) as count
                FROM tickets
                WHERE user_id = ?
                GROUP BY status
            """, (user_id.value,))

            rows = await cursor.fetchall()
            stats = {"total": 0}

            for row in rows:
                status, count = row
                stats[status] = count
                stats["total"] += count

            return stats

    async def find_tickets_with_attachments(self) -> List[Ticket]:
        """Busca tickets que possuem anexos."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM tickets
                WHERE metadata LIKE '%attachment%' OR metadata LIKE '%file%'
                ORDER BY created_at DESC
            """)

            rows = await cursor.fetchall()
            return [self._row_to_ticket(row) for row in rows]

    async def update_sync_status(
        self,
        ticket_id: TicketId,
        sync_status: str,
        hubsoft_id: Optional[HubSoftId] = None,
        sync_error: Optional[str] = None
    ) -> bool:
        """Atualiza status de sincronização de um ticket."""
        async with aiosqlite.connect(self.db_path) as db:
            sync_at = datetime.now().isoformat()

            if hubsoft_id:
                await db.execute("""
                    UPDATE tickets
                    SET hubsoft_synced = ?, hubsoft_sync_at = ?, protocol_hubsoft = ?
                    WHERE id = ?
                """, (sync_status == "success", sync_at, hubsoft_id.value, ticket_id.value))
            else:
                await db.execute("""
                    UPDATE tickets
                    SET hubsoft_synced = ?, hubsoft_sync_at = ?
                    WHERE id = ?
                """, (sync_status == "success", sync_at, ticket_id.value))

            await db.commit()
            return True

    async def delete(self, entity_id: TicketId) -> bool:
        """Remove um ticket."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM tickets WHERE id = ?
            """, (entity_id.value,))

            await db.commit()
            return cursor.rowcount > 0

    async def exists(self, entity_id: TicketId) -> bool:
        """Verifica se um ticket existe."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 1 FROM tickets WHERE id = ? LIMIT 1
            """, (entity_id.value,))

            result = await cursor.fetchone()
            return result is not None