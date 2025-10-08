#!/usr/bin/env python3
"""
Migration Engine para OnCabito Bot
Gerencia versões do schema do banco de dados SQLite
"""

import os
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

logger = logging.getLogger(__name__)

class MigrationEngine:
    def __init__(self, database_path: str, migrations_dir: str = "migrations"):
        self.database_path = database_path
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)

    def get_db_connection(self):
        """Cria conexão com o banco de dados"""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_migrations_table(self):
        """Cria tabela de controle de migrations se não existir"""
        with self.get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    filename TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT
                )
            """)
            conn.commit()
            logger.info("Tabela de migrations inicializada")

    def get_applied_migrations(self) -> List[int]:
        """Retorna lista de migrations já aplicadas"""
        with self.get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT version FROM schema_migrations ORDER BY version
            """)
            return [row[0] for row in cursor.fetchall()]

    def get_available_migrations(self) -> List[Tuple[int, str]]:
        """Retorna lista de migrations disponíveis (version, filename)"""
        migrations = []
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            filename = file_path.name
            # Extrai número da migration do formato: 001_description.sql
            try:
                version = int(filename[:3])
                migrations.append((version, filename))
            except ValueError:
                logger.warning(f"Arquivo de migration com formato inválido: {filename}")
        return migrations

    def get_pending_migrations(self) -> List[Tuple[int, str]]:
        """Retorna migrations que precisam ser executadas"""
        applied = set(self.get_applied_migrations())
        available = self.get_available_migrations()

        pending = [(v, f) for v, f in available if v not in applied]
        return sorted(pending)

    def count_critical_records(self) -> dict:
        """Conta registros críticos antes/depois de migrations"""
        counts = {}
        try:
            with self.get_db_connection() as conn:
                # Tenta contar usuários com CPF
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM users WHERE user_id IS NOT NULL AND cpf IS NOT NULL")
                    counts['users_with_cpf'] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    counts['users_with_cpf'] = 0

                # Tenta contar total de usuários
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM users")
                    counts['total_users'] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    counts['total_users'] = 0

                # Tenta contar tickets de suporte
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM support_tickets")
                    counts['support_tickets'] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    counts['support_tickets'] = 0

                # Tenta contar estados de usuários
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM user_states")
                    counts['user_states'] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    counts['user_states'] = 0

        except Exception as e:
            logger.warning(f"Erro geral ao contar registros: {e}")
            counts = {'error': str(e)}

        return counts

    def validate_migration_integrity(self, before: dict, after: dict, version: int):
        """Valida integridade dos dados após migration"""
        if 'error' in before or 'error' in after:
            logger.warning(f"Não foi possível validar integridade da migration {version}")
            return

        critical_tables = ['users_with_cpf', 'total_users']

        for table in critical_tables:
            before_count = before.get(table, 0)
            after_count = after.get(table, 0)

            # Permite crescimento, mas não perda > 5%
            if before_count > 0:
                loss_percentage = ((before_count - after_count) / before_count) * 100

                if loss_percentage > 5:  # Perda > 5% é suspeita
                    logger.error(
                        f"⚠️  ALERTA CRÍTICO: Migration {version} causou perda de {loss_percentage:.1f}% "
                        f"em {table} ({before_count} → {after_count})"
                    )
                elif loss_percentage > 0:
                    logger.warning(
                        f"Migration {version}: {table} reduziu {loss_percentage:.1f}% "
                        f"({before_count} → {after_count})"
                    )
                elif after_count > before_count:
                    growth = ((after_count - before_count) / before_count) * 100
                    logger.info(
                        f"✅ Migration {version}: {table} cresceu {growth:.1f}% "
                        f"({before_count} → {after_count})"
                    )
                else:
                    logger.info(f"✅ Migration {version}: {table} manteve {after_count} registros")
            elif after_count > 0:
                logger.info(f"✅ Migration {version}: {table} criado com {after_count} registros")

    def calculate_checksum(self, content: str) -> str:
        """Calcula checksum simples do conteúdo da migration"""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()

    def execute_migration(self, version: int, filename: str) -> bool:
        """Executa uma migration específica com verificação de integridade"""
        migration_path = self.migrations_dir / filename

        if not migration_path.exists():
            logger.error(f"Arquivo de migration não encontrado: {migration_path}")
            return False

        try:
            # Conta registros ANTES da migration
            before_counts = self.count_critical_records()
            logger.info(f"📊 Registros antes da migration {version}: {before_counts}")

            # Lê o conteúdo da migration
            with open(migration_path, 'r', encoding='utf-8') as f:
                content = f.read()

            checksum = self.calculate_checksum(content)

            # Executa a migration
            with self.get_db_connection() as conn:
                # Executa comandos SQL da migration
                conn.executescript(content)

                # Registra a migration como aplicada
                conn.execute("""
                    INSERT INTO schema_migrations (version, filename, checksum)
                    VALUES (?, ?, ?)
                """, (version, filename, checksum))

                conn.commit()

            # Conta registros DEPOIS da migration
            after_counts = self.count_critical_records()
            logger.info(f"📊 Registros depois da migration {version}: {after_counts}")

            # Verifica integridade
            self.validate_migration_integrity(before_counts, after_counts, version)

            logger.info(f"✅ Migration {version} ({filename}) aplicada com sucesso")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao executar migration {version}: {e}")
            return False

    def run_pending_migrations(self) -> bool:
        """Executa todas as migrations pendentes com verificação de integridade"""
        self.initialize_migrations_table()

        pending = self.get_pending_migrations()

        if not pending:
            logger.info("✅ Nenhuma migration pendente")
            return True

        # Conta registros totais antes de começar
        initial_counts = self.count_critical_records()
        logger.info(f"📊 Estado inicial do banco: {initial_counts}")

        logger.info(f"🔄 Executando {len(pending)} migration(s) pendente(s)")

        success_count = 0
        for version, filename in pending:
            logger.info(f"🔄 Aplicando migration {version}: {filename}")
            if self.execute_migration(version, filename):
                success_count += 1
            else:
                logger.error(f"❌ Falha na migration {version}, parando execução")
                return False

        # Verifica estado final
        final_counts = self.count_critical_records()
        logger.info(f"📊 Estado final do banco: {final_counts}")

        # Valida integridade geral
        if 'error' not in initial_counts and 'error' not in final_counts:
            logger.info("🔍 Validando integridade geral...")
            self.validate_migration_integrity(initial_counts, final_counts, -1)  # -1 = todas as migrations

        logger.info(f"✅ Todas as {success_count} migration(s) foram aplicadas com sucesso")
        return True

    def get_migration_status(self) -> dict:
        """Retorna status das migrations"""
        self.initialize_migrations_table()

        applied = self.get_applied_migrations()
        available = self.get_available_migrations()
        pending = self.get_pending_migrations()

        return {
            "applied_count": len(applied),
            "available_count": len(available),
            "pending_count": len(pending),
            "applied_versions": applied,
            "pending_migrations": pending,
            "last_applied": max(applied) if applied else None
        }

def main():
    """Função principal para execução standalone"""
    import sys

    # Configuração de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(levelname)s] - %(message)s'
    )

    # Caminho do banco (pode ser passado como argumento)
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/database/sentinela.db"

    if not os.path.exists(db_path):
        logger.error(f"Banco de dados não encontrado: {db_path}")
        sys.exit(1)

    # Cria engine e executa migrations
    engine = MigrationEngine(db_path)

    # Mostra status atual
    status = engine.get_migration_status()
    print(f"📊 Status das Migrations:")
    print(f"   • Aplicadas: {status['applied_count']}")
    print(f"   • Disponíveis: {status['available_count']}")
    print(f"   • Pendentes: {status['pending_count']}")

    if status['pending_count'] > 0:
        print(f"\n🔄 Executando migrations pendentes...")
        success = engine.run_pending_migrations()
        if success:
            print(f"✅ Todas as migrations foram aplicadas!")
        else:
            print(f"❌ Erro ao aplicar migrations")
            sys.exit(1)
    else:
        print(f"✅ Banco de dados está atualizado")

if __name__ == "__main__":
    main()