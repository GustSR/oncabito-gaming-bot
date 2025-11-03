#!/usr/bin/env python3
"""
Script de Export de Dados Críticos
Exporta dados essenciais para arquivo JSON como backup adicional
"""

import sys
import os
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

# Adiciona o diretório raiz ao path
# IMPORTANTE: Sobe três níveis (.., .., ..) para chegar em /app
# __file__ = /app/scripts/tasks/export_critical_data.py -> /app
root_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, root_dir)

# Tenta importar config, se falhar usa caminho padrão
try:
    from src.sentinela.core.config import DATABASE_FILE
except ImportError:
    DATABASE_FILE = "data/database/sentinela.db"

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

logger = logging.getLogger(__name__)

class CriticalDataExporter:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.export_dir = Path('backups/critical_data')
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def get_db_connection(self):
        """Cria conexão com o banco de dados"""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def export_users_critical_data(self) -> list:
        """Exporta dados críticos dos usuários (CPF ↔ Telegram ID)"""
        users_data = []

        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        user_id,
                        username,
                        cpf,
                        client_name,
                        service_name,
                        service_status,
                        is_active,
                        created_at,
                        last_verification
                    FROM users
                    WHERE user_id IS NOT NULL
                    ORDER BY user_id
                """)

                for row in cursor.fetchall():
                    users_data.append({
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'cpf': row['cpf'],
                        'client_name': row['client_name'],
                        'service_name': row['service_name'],
                        'service_status': row['service_status'],
                        'is_active': bool(row['is_active']),
                        'created_at': row['created_at'],
                        'last_verification': row['last_verification']
                    })

        except Exception as e:
            logger.error(f"Erro ao exportar dados de usuários: {e}")
            return []

        return users_data

    def export_user_states(self) -> list:
        """Exporta estados de usuários"""
        states_data = []

        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        user_id,
                        has_interacted,
                        last_interaction
                    FROM user_states
                    ORDER BY user_id
                """)

                for row in cursor.fetchall():
                    states_data.append({
                        'user_id': row['user_id'],
                        'has_interacted': bool(row['has_interacted']),
                        'last_interaction': row['last_interaction']
                    })

        except Exception as e:
            logger.warning(f"Tabela user_states não encontrada ou erro: {e}")
            return []

        return states_data

    def export_user_rules(self) -> list:
        """Exporta dados de regras aceitas"""
        rules_data = []

        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        user_id,
                        username,
                        joined_at,
                        rules_accepted,
                        rules_accepted_at,
                        expires_at,
                        status
                    FROM user_rules
                    ORDER BY user_id
                """)

                for row in cursor.fetchall():
                    rules_data.append({
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'joined_at': row['joined_at'],
                        'rules_accepted': bool(row['rules_accepted']),
                        'rules_accepted_at': row['rules_accepted_at'],
                        'expires_at': row['expires_at'],
                        'status': row['status']
                    })

        except Exception as e:
            logger.warning(f"Tabela user_rules não encontrada ou erro: {e}")
            return []

        return rules_data

    def export_migration_history(self) -> list:
        """Exporta histórico de migrations aplicadas"""
        migrations_data = []

        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        version,
                        filename,
                        applied_at,
                        checksum
                    FROM schema_migrations
                    ORDER BY version
                """)

                for row in cursor.fetchall():
                    migrations_data.append({
                        'version': row['version'],
                        'filename': row['filename'],
                        'applied_at': row['applied_at'],
                        'checksum': row['checksum']
                    })

        except Exception as e:
            logger.warning(f"Tabela schema_migrations não encontrada ou erro: {e}")
            return []

        return migrations_data

    def export_support_tickets_summary(self) -> list:
        """Exporta resumo dos tickets de suporte (sem dados sensíveis)"""
        tickets_data = []

        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        id,
                        user_id,
                        username,
                        category,
                        affected_game,
                        urgency_level,
                        status,
                        created_at,
                        resolved_at
                    FROM support_tickets
                    ORDER BY id
                """)

                for row in cursor.fetchall():
                    tickets_data.append({
                        'id': row['id'],
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'category': row['category'],
                        'affected_game': row['affected_game'],
                        'urgency_level': row['urgency_level'],
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'resolved_at': row['resolved_at']
                    })

        except Exception as e:
            logger.warning(f"Tabela support_tickets não encontrada ou erro: {e}")
            return []

        return tickets_data

    def create_critical_export(self) -> dict:
        """Cria export completo dos dados críticos"""
        timestamp = datetime.now()

        logger.info("📦 Exportando dados críticos...")

        # Exporta cada tipo de dado
        users_data = self.export_users_critical_data()
        states_data = self.export_user_states()
        rules_data = self.export_user_rules()
        migrations_data = self.export_migration_history()
        tickets_summary = self.export_support_tickets_summary()

        # Monta export completo
        export_data = {
            'export_info': {
                'timestamp': timestamp.isoformat(),
                'database_file': self.database_path,
                'export_version': '1.0',
                'description': 'Export de dados críticos do OnCabito Bot'
            },
            'statistics': {
                'total_users': len(users_data),
                'users_with_cpf': len([u for u in users_data if u.get('cpf')]),
                'active_users': len([u for u in users_data if u.get('is_active')]),
                'user_states': len(states_data),
                'user_rules': len(rules_data),
                'applied_migrations': len(migrations_data),
                'support_tickets': len(tickets_summary)
            },
            'data': {
                'users': users_data,
                'user_states': states_data,
                'user_rules': rules_data,
                'schema_migrations': migrations_data,
                'support_tickets_summary': tickets_summary
            }
        }

        # Salva arquivo
        filename = f"critical_data_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.export_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

            file_size = filepath.stat().st_size
            logger.info(f"✅ Export salvo: {filepath} ({file_size:,} bytes)")

            # Limpa exports antigos (mantém últimos 30 dias)
            self.cleanup_old_exports()

            return {
                'success': True,
                'filepath': str(filepath),
                'file_size': file_size,
                'statistics': export_data['statistics']
            }

        except Exception as e:
            logger.error(f"❌ Erro ao salvar export: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def cleanup_old_exports(self):
        """Remove exports antigos (> 30 dias)"""
        try:
            import time
            cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30 dias

            removed_count = 0
            for file_path in self.export_dir.glob("critical_data_*.json"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    removed_count += 1

            if removed_count > 0:
                logger.info(f"🧹 Removidos {removed_count} export(s) antigo(s)")

        except Exception as e:
            logger.warning(f"Erro na limpeza de exports antigos: {e}")

    def list_exports(self) -> list:
        """Lista exports disponíveis"""
        exports = []

        for file_path in sorted(self.export_dir.glob("critical_data_*.json")):
            try:
                stat = file_path.stat()
                exports.append({
                    'filename': file_path.name,
                    'filepath': str(file_path),
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception as e:
                logger.warning(f"Erro ao ler arquivo {file_path}: {e}")

        return exports

def main():
    """Função principal"""

    # Verifica se o banco existe
    if not os.path.exists(DATABASE_FILE):
        logger.error(f"❌ Banco de dados não encontrado: {DATABASE_FILE}")
        sys.exit(1)

    # Executa export
    exporter = CriticalDataExporter(DATABASE_FILE)
    result = exporter.create_critical_export()

    # Mostra resultado
    print(f"\n📦 EXPORT DE DADOS CRÍTICOS")
    print(f"===========================")
    print(f"🕒 Horário: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")

    if result['success']:
        print(f"✅ Status: SUCESSO")
        print(f"📁 Arquivo: {result['filepath']}")
        print(f"📊 Tamanho: {result['file_size']:,} bytes")

        stats = result['statistics']
        print(f"\n📈 ESTATÍSTICAS:")
        print(f"👥 Total de usuários: {stats['total_users']}")
        print(f"🔗 Usuários com CPF: {stats['users_with_cpf']}")
        print(f"✅ Usuários ativos: {stats['active_users']}")
        print(f"📊 Estados de usuário: {stats['user_states']}")
        print(f"📋 Regras aceitas: {stats['user_rules']}")
        print(f"🔄 Migrations aplicadas: {stats['applied_migrations']}")
        print(f"🎫 Tickets de suporte: {stats['support_tickets']}")

        # Lista exports disponíveis
        exports = exporter.list_exports()
        print(f"\n📁 EXPORTS DISPONÍVEIS: {len(exports)}")
        for export in exports[-3:]:  # Mostra últimos 3
            created = datetime.fromisoformat(export['created']).strftime('%d/%m/%Y %H:%M')
            print(f"   • {export['filename']} ({export['size']:,} bytes) - {created}")

        print(f"\n📝 Logs: logs/")
        print(f"📂 Diretório: backups/critical_data/")

        sys.exit(0)
    else:
        print(f"❌ Status: ERRO")
        print(f"💥 Erro: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()