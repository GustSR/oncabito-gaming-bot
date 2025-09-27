#!/usr/bin/env python3
"""
Script de Teste para Sistema de Re-verificação de CPF
Testa todas as funcionalidades do sistema
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Adiciona o diretório raiz ao path
root_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'src'))

# Tenta importar config, se falhar usa fallback
try:
    from src.sentinela.core.config import DATABASE_FILE
except ImportError:
    DATABASE_FILE = "data/database/sentinela.db"

from src.sentinela.services.cpf_verification_service import CPFVerificationService
from src.sentinela.clients.db_client import get_db_connection

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

logger = logging.getLogger(__name__)

class CPFVerificationTester:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def test_database_structure(self) -> bool:
        """Testa se as tabelas necessárias existem"""
        try:
            logger.info("🔍 Testando estrutura do banco de dados...")

            with get_db_connection() as conn:
                # Verifica tabelas necessárias
                required_tables = [
                    'pending_cpf_verifications',
                    'cpf_verification_history',
                    'users'
                ]

                for table in required_tables:
                    cursor = conn.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name=?
                    """, (table,))

                    if not cursor.fetchone():
                        logger.error(f"❌ Tabela '{table}' não encontrada")
                        return False

                logger.info("✅ Todas as tabelas necessárias existem")
                return True

        except Exception as e:
            logger.error(f"❌ Erro ao testar estrutura: {e}")
            return False

    def test_verification_creation(self) -> bool:
        """Testa criação de verificações pendentes"""
        try:
            logger.info("🔍 Testando criação de verificações...")

            test_user_id = 999999999
            test_username = "test_user"
            test_mention = "@test_user"

            # Limpa dados de teste anteriores
            with get_db_connection() as conn:
                conn.execute("DELETE FROM pending_cpf_verifications WHERE user_id = ?", (test_user_id,))
                conn.execute("DELETE FROM cpf_verification_history WHERE user_id = ?", (test_user_id,))
                conn.commit()

            # Testa criação de verificação
            success = CPFVerificationService.create_pending_verification(
                user_id=test_user_id,
                username=test_username,
                user_mention=test_mention,
                verification_type="auto_checkup",
                source_action="test_script"
            )

            if not success:
                logger.error("❌ Falha ao criar verificação pendente")
                return False

            # Verifica se foi criada
            verification = CPFVerificationService.get_pending_verification(test_user_id)
            if not verification:
                logger.error("❌ Verificação criada mas não encontrada")
                return False

            logger.info("✅ Verificação criada e encontrada com sucesso")

            # Testa atualização de tentativas
            CPFVerificationService.update_verification_attempt(test_user_id)

            # Testa completar verificação
            CPFVerificationService.complete_verification(
                test_user_id, True, "12345678901"
            )

            logger.info("✅ Ciclo completo de verificação testado")

            # Limpa dados de teste
            with get_db_connection() as conn:
                conn.execute("DELETE FROM pending_cpf_verifications WHERE user_id = ?", (test_user_id,))
                conn.execute("DELETE FROM cpf_verification_history WHERE user_id = ?", (test_user_id,))
                conn.commit()

            return True

        except Exception as e:
            logger.error(f"❌ Erro no teste de criação: {e}")
            return False

    def test_statistics(self) -> bool:
        """Testa estatísticas de verificação"""
        try:
            logger.info("🔍 Testando estatísticas...")

            stats = CPFVerificationService.get_verification_stats()

            if not isinstance(stats, dict):
                logger.error("❌ Estatísticas não retornaram dict")
                return False

            required_keys = ['pending', 'expired', 'last_24h']
            for key in required_keys:
                if key not in stats:
                    logger.error(f"❌ Chave '{key}' ausente nas estatísticas")
                    return False

            logger.info(f"✅ Estatísticas válidas: {stats}")
            return True

        except Exception as e:
            logger.error(f"❌ Erro no teste de estatísticas: {e}")
            return False

    async def test_full_valid_cpf_flow(self) -> bool:
        """Testa o fluxo completo de verificação com um CPF válido."""
        try:
            logger.info("🔍 Testando o fluxo completo com CPF válido...")
            
            # --- Configuração do Teste ---
            test_user_id = 999999998
            test_username = "test_user_valid"
            # IMPORTANTE: Use um CPF que seja válido e tenha contrato no HubSoft para este teste
            valid_cpf_for_test = "61274037310" # Usando o CPF dos logs

            # --- Limpeza ---
            with get_db_connection() as conn:
                conn.execute("DELETE FROM pending_cpf_verifications WHERE user_id = ?", (test_user_id,))
                conn.execute("DELETE FROM cpf_verification_history WHERE user_id = ?", (test_user_id,))
                # Apaga o usuário se ele existir de um teste anterior
                conn.execute("DELETE FROM users WHERE cpf = ?", (valid_cpf_for_test,))
                conn.commit()
                logger.info("Ambiente de teste limpo.")

            # 1. Cria uma verificação pendente para o nosso usuário de teste
            CPFVerificationService.create_pending_verification(
                user_id=test_user_id,
                username=test_username,
                user_mention=f"@{test_username}",
                verification_type="test_flow"
            )
            logger.info(f"Verificação pendente criada para user_id {test_user_id}")

            # 2. Processa a verificação com o CPF válido
            logger.info(f"Processando verificação para o CPF {valid_cpf_for_test}...")
            result = await CPFVerificationService.process_cpf_verification(
                test_user_id, test_username, valid_cpf_for_test
            )

            # 3. Valida o resultado
            if not result['success']:
                logger.error(f"❌ FALHA: Ocorreu um erro ao processar um CPF válido.")
                logger.error(f"   - Motivo: {result.get('reason')}")
                logger.error(f"   - Mensagem: {result.get('message')}")
                return False
            
            logger.info("✅ SUCESSO: CPF válido processado e usuário salvo no banco.")
            
            # --- Limpeza Final ---
            with get_db_connection() as conn:
                conn.execute("DELETE FROM users WHERE user_id = ?", (test_user_id,))
                conn.commit()

            return True

        except Exception as e:
            logger.error(f"❌ ERRO CRÍTICO NO TESTE: {e}", exc_info=True)
            return False

    def test_expired_cleanup(self) -> bool:
        """Testa limpeza de verificações expiradas"""
        try:
            logger.info("🔍 Testando limpeza de expiradas...")

            # Cria verificação com data expirada manualmente
            test_user_id = 999999997

            with get_db_connection() as conn:
                # Limpa dados anteriores
                conn.execute("DELETE FROM pending_cpf_verifications WHERE user_id = ?", (test_user_id,))

                # Insere verificação expirada
                conn.execute("""
                    INSERT INTO pending_cpf_verifications (
                        user_id, username, user_mention, expires_at, status
                    ) VALUES (?, ?, ?, datetime('now', '-1 hour'), 'pending')
                """, (test_user_id, "expired_user", "@expired_user"))

                conn.commit()

            # Busca verificações expiradas
            expired = CPFVerificationService.get_expired_verifications()

            if not any(v['user_id'] == test_user_id for v in expired):
                logger.error("❌ Verificação expirada não foi detectada")
                return False

            logger.info("✅ Verificação expirada detectada corretamente")

            # Limpa dados de teste
            with get_db_connection() as conn:
                conn.execute("DELETE FROM pending_cpf_verifications WHERE user_id = ?", (test_user_id,))
                conn.commit()

            return True

        except Exception as e:
            logger.error(f"❌ Erro no teste de limpeza: {e}")
            return False

    async def run_all_tests(self) -> dict:
        """Executa todos os testes"""
        logger.info("🧪 Iniciando bateria completa de testes...")

        results = {
            'database_structure': False,
            'verification_creation': False,
            'statistics': False,
            'full_valid_cpf_flow': False,
            'expired_cleanup': False
        }

        # Executa cada teste
        results['database_structure'] = self.test_database_structure()
        results['verification_creation'] = self.test_verification_creation()
        results['statistics'] = self.test_statistics()
        results['full_valid_cpf_flow'] = await self.test_full_valid_cpf_flow()
        results['expired_cleanup'] = self.test_expired_cleanup()

        return results

def main():
    """Função principal"""

    # Verifica se o banco existe
    if not os.path.exists(DATABASE_FILE):
        logger.error(f"❌ Banco de dados não encontrado: {DATABASE_FILE}")
        print(f"\n❌ ERRO: Banco de dados não encontrado")
        print(f"📁 Procurado em: {DATABASE_FILE}")
        print(f"💡 Execute migrations primeiro: python3 migrations/migration_engine.py {DATABASE_FILE}")
        sys.exit(1)

    async def run_tests():
        # Executa testes
        tester = CPFVerificationTester(DATABASE_FILE)
        results = await tester.run_all_tests()

        # Mostra resultados
        print(f"\n🧪 RESULTADOS DOS TESTES")
        print(f"========================")
        print(f"🕒 Executado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
        print(f"📁 Banco testado: {DATABASE_FILE}")

        all_passed = True
        for test_name, passed in results.items():
            status = "✅ PASSOU" if passed else "❌ FALHOU"
            test_display = test_name.replace('_', ' ').title()
            print(f"  • {test_display}: {status}")

            if not passed:
                all_passed = False

        print(f"\n📊 RESUMO:")
        print(f"Total de testes: {len(results)}")
        print(f"Testes aprovados: {sum(results.values())}")
        print(f"Testes falharam: {len(results) - sum(results.values())}")

        if all_passed:
            print(f"\n🎉 TODOS OS TESTES PASSARAM!")
            print(f"✅ Sistema de re-verificação de CPF está funcionando corretamente")
            print(f"\n💡 Próximos passos:")
            print(f"  • Execute o daily checkup: python3 scripts/daily_checkup.py")
            print(f"  • Configure monitoramento: ./scripts/setup_monitoring.sh")
            print(f"  • Teste /suporte com usuário sem CPF no banco")
            sys.exit(0)
        else:
            print(f"\n💥 ALGUNS TESTES FALHARAM!")
            print(f"❌ Verifique os logs acima para detalhes dos erros")
            print(f"🔧 Corrija os problemas antes de usar o sistema")
            sys.exit(1)

    # Executa testes assíncronos
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()