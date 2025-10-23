#!/usr/bin/env python3
"""
Script de Verificação Diária de Integridade de Dados
Monitora a saúde do banco de dados e detecta anomalias
"""

import sys
import os
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'src'))

# Tenta importar config, se falhar usa caminho padrão
try:
    from src.sentinela.core.config import DATABASE_FILE
except ImportError:
    DATABASE_FILE = "data/database/sentinela.db"

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/integrity_check.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class DataIntegrityChecker:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.history_file = Path('logs/integrity_history.json')
        self.history_file.parent.mkdir(exist_ok=True)

    def get_db_connection(self):
        """Cria conexão com o banco de dados"""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def count_critical_data(self) -> dict:
        """Conta dados críticos no banco"""
        counts = {}
        timestamp = datetime.now().isoformat()

        try:
            with self.get_db_connection() as conn:
                # Usuários com CPF (ligação crítica)
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM users
                    WHERE user_id IS NOT NULL AND cpf IS NOT NULL AND cpf != ''
                """)
                counts['users_with_cpf'] = cursor.fetchone()[0]

                # Total de usuários
                cursor = conn.execute("SELECT COUNT(*) FROM users")
                counts['total_users'] = cursor.fetchone()[0]

                # Usuários ativos
                cursor = conn.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                counts['active_users'] = cursor.fetchone()[0]

                # Tickets de suporte
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM support_tickets")
                    counts['support_tickets'] = cursor.fetchone()[0]
                except:
                    counts['support_tickets'] = 0

                # Estados de usuários
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM user_states")
                    counts['user_states'] = cursor.fetchone()[0]
                except:
                    counts['user_states'] = 0

                # Regras aceitas
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM user_rules WHERE rules_accepted = 1")
                    counts['rules_accepted'] = cursor.fetchone()[0]
                except:
                    counts['rules_accepted'] = 0

                # Última verificação
                try:
                    cursor = conn.execute("""
                        SELECT MAX(last_verification) FROM users
                        WHERE last_verification IS NOT NULL
                    """)
                    last_verification = cursor.fetchone()[0]
                    counts['last_verification'] = last_verification
                except:
                    counts['last_verification'] = None

        except Exception as e:
            logger.error(f"Erro ao contar dados: {e}")
            counts['error'] = str(e)

        counts['timestamp'] = timestamp
        return counts

    def load_history(self) -> list:
        """Carrega histórico de verificações"""
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar histórico: {e}")
            return []

    def save_history(self, history: list):
        """Salva histórico de verificações"""
        try:
            # Mantém apenas últimos 30 dias
            cutoff_date = datetime.now() - timedelta(days=30)
            filtered_history = [
                entry for entry in history
                if datetime.fromisoformat(entry['timestamp']) > cutoff_date
            ]

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(filtered_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")

    def detect_anomalies(self, current: dict, history: list) -> list:
        """Detecta anomalias comparando com histórico"""
        anomalies = []

        if not history or 'error' in current:
            return anomalies

        # Pega últimas 7 entradas para calcular média
        recent_history = history[-7:] if len(history) >= 7 else history

        for key in ['users_with_cpf', 'total_users', 'active_users']:
            if key not in current:
                continue

            current_value = current[key]

            # Calcula média dos últimos valores
            recent_values = [entry[key] for entry in recent_history if key in entry and 'error' not in entry]

            if not recent_values:
                continue

            avg_value = sum(recent_values) / len(recent_values)

            if avg_value > 0:
                # Verifica perda significativa (> 10%)
                loss_percentage = ((avg_value - current_value) / avg_value) * 100

                if loss_percentage > 10:
                    anomalies.append({
                        'type': 'data_loss',
                        'table': key,
                        'current': current_value,
                        'average': round(avg_value, 1),
                        'loss_percentage': round(loss_percentage, 1),
                        'severity': 'HIGH' if loss_percentage > 25 else 'MEDIUM'
                    })
                elif loss_percentage > 5:
                    anomalies.append({
                        'type': 'data_reduction',
                        'table': key,
                        'current': current_value,
                        'average': round(avg_value, 1),
                        'loss_percentage': round(loss_percentage, 1),
                        'severity': 'LOW'
                    })

        return anomalies

    def check_database_health(self) -> dict:
        """Verifica saúde geral do banco"""
        health = {'status': 'healthy', 'issues': []}

        try:
            with self.get_db_connection() as conn:
                # Verifica integridade do SQLite
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]

                if integrity_result != 'ok':
                    health['status'] = 'corrupted'
                    health['issues'].append({
                        'type': 'corruption',
                        'message': f'Falha na verificação de integridade: {integrity_result}',
                        'severity': 'CRITICAL'
                    })

                # Verifica se tabelas principais existem
                required_tables = ['users', 'schema_migrations']
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name IN ('users', 'schema_migrations')
                """)
                existing_tables = [row[0] for row in cursor.fetchall()]

                for table in required_tables:
                    if table not in existing_tables:
                        health['status'] = 'missing_tables'
                        health['issues'].append({
                            'type': 'missing_table',
                            'message': f'Tabela obrigatória ausente: {table}',
                            'severity': 'HIGH'
                        })

        except Exception as e:
            health['status'] = 'error'
            health['issues'].append({
                'type': 'connection_error',
                'message': str(e),
                'severity': 'CRITICAL'
            })

        return health

    def run_integrity_check(self) -> dict:
        """Executa verificação completa de integridade"""
        logger.info("🔍 Iniciando verificação de integridade de dados...")

        # Carrega histórico
        history = self.load_history()

        # Conta dados atuais
        current_counts = self.count_critical_data()
        logger.info(f"📊 Contagem atual: {current_counts}")

        # Verifica saúde do banco
        health = self.check_database_health()
        logger.info(f"🏥 Saúde do banco: {health['status']}")

        # Detecta anomalias
        anomalies = self.detect_anomalies(current_counts, history)

        # Prepara resultado
        result = {
            'timestamp': current_counts['timestamp'],
            'counts': current_counts,
            'health': health,
            'anomalies': anomalies,
            'status': 'ok' if not anomalies and health['status'] == 'healthy' else 'issues_detected'
        }

        # Log de anomalias
        if anomalies:
            logger.warning(f"⚠️ {len(anomalies)} anomalia(s) detectada(s):")
            for anomaly in anomalies:
                severity_emoji = '🚨' if anomaly['severity'] == 'HIGH' else '⚠️'
                logger.warning(f"{severity_emoji} {anomaly['type']}: {anomaly.get('message', '')}")

        # Log de problemas de saúde
        if health['issues']:
            logger.error(f"🏥 {len(health['issues'])} problema(s) de saúde detectado(s):")
            for issue in health['issues']:
                logger.error(f"🚨 {issue['type']}: {issue['message']}")

        # Salva no histórico
        history.append(current_counts)
        self.save_history(history)

        if result['status'] == 'ok':
            logger.info("✅ Verificação de integridade concluída - tudo OK")
        else:
            logger.warning("⚠️ Verificação de integridade concluída - problemas detectados")

        return result

def main():
    """Função principal"""

    # Verifica se o banco existe
    if not os.path.exists(DATABASE_FILE):
        logger.error(f"❌ Banco de dados não encontrado: {DATABASE_FILE}")
        sys.exit(1)

    # Cria diretório de logs
    os.makedirs('logs', exist_ok=True)

    # Executa verificação
    checker = DataIntegrityChecker(DATABASE_FILE)
    result = checker.run_integrity_check()

    # Resultado final
    print(f"\n📋 RELATÓRIO DE INTEGRIDADE")
    print(f"==========================")
    print(f"🕒 Horário: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
    print(f"📊 Status: {result['status'].upper()}")

    if 'error' not in result['counts']:
        counts = result['counts']
        print(f"👥 Usuários com CPF: {counts.get('users_with_cpf', 0)}")
        print(f"👥 Total de usuários: {counts.get('total_users', 0)}")
        print(f"✅ Usuários ativos: {counts.get('active_users', 0)}")
        print(f"🎫 Tickets de suporte: {counts.get('support_tickets', 0)}")

    if result['anomalies']:
        print(f"\n⚠️ ANOMALIAS DETECTADAS: {len(result['anomalies'])}")
        for anomaly in result['anomalies']:
            print(f"   • {anomaly['type']}: {anomaly.get('table', 'N/A')}")

    if result['health']['issues']:
        print(f"\n🏥 PROBLEMAS DE SAÚDE: {len(result['health']['issues'])}")
        for issue in result['health']['issues']:
            print(f"   • {issue['type']}: {issue['message']}")

    print(f"\n📝 Logs salvos em: logs/integrity_check.log")
    print(f"📈 Histórico salvo em: logs/integrity_history.json")

    # Exit code baseado no resultado
    if result['status'] == 'ok':
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()