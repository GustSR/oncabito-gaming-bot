#!/usr/bin/env python3
"""
Script de Teste para Serviços Refatorados

Testa todos os novos serviços criados durante a refatoração:
- AdminService
- CPFValidationService
- DuplicateCPFHandler
- CPFVerificationService (refatorado)
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

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

logger = logging.getLogger(__name__)

class RefactoredServicesTest:
    def __init__(self):
        self.test_results = {}

    def test_cpf_validation_service(self) -> bool:
        """Testa o CPFValidationService"""
        try:
            logger.info("🔍 Testando CPFValidationService...")

            from src.sentinela.services.cpf_validation_service import CPFValidationService

            # Teste 1: CPF válido
            result = CPFValidationService.validate_cpf_format("123.456.789-09")
            if not result.is_valid:
                logger.error("❌ CPF válido foi rejeitado")
                return False

            # Teste 2: CPF inválido
            result = CPFValidationService.validate_cpf_format("123.456.789-00")
            if result.is_valid:
                logger.error("❌ CPF inválido foi aceito")
                return False

            # Teste 3: Formatação
            formatted = CPFValidationService.format_cpf("12345678909")
            if formatted != "123.456.789-09":
                logger.error("❌ Formatação de CPF incorreta")
                return False

            # Teste 4: Limpeza
            clean = CPFValidationService.clean_cpf("123.456.789-09")
            if clean != "12345678909":
                logger.error("❌ Limpeza de CPF incorreta")
                return False

            # Teste 5: Máscara
            masked = CPFValidationService.mask_cpf("12345678909", 2)
            if not masked.endswith("09"):
                logger.error("❌ Máscara de CPF incorreta")
                return False

            logger.info("✅ CPFValidationService passou em todos os testes")
            return True

        except Exception as e:
            logger.error(f"❌ Erro no teste CPFValidationService: {e}")
            return False

    async def test_admin_service(self) -> bool:
        """Testa o AdminService"""
        try:
            logger.info("🔍 Testando AdminService...")

            from src.sentinela.services.admin_service import AdminService

            admin_service = AdminService()

            # Teste 1: Inicialização
            if not hasattr(admin_service, '_admin_cache'):
                logger.error("❌ AdminService não inicializou corretamente")
                return False

            # Teste 2: Cache vazio inicial
            if admin_service._admin_cache:
                logger.error("❌ Cache deveria estar vazio inicialmente")
                return False

            # Teste 3: Limpeza de cache
            admin_service.clear_cache()

            # Teste 4: Estatísticas
            stats = await admin_service.get_admin_stats()
            if not isinstance(stats, dict):
                logger.error("❌ Estatísticas deveriam retornar dict")
                return False

            # Teste 5: Verificação de isenção (deve funcionar mesmo sem dados)
            should_exempt = await admin_service.should_exempt_from_verification(999999999)
            if not isinstance(should_exempt, bool):
                logger.error("❌ should_exempt_from_verification deve retornar bool")
                return False

            logger.info("✅ AdminService passou em todos os testes")
            return True

        except Exception as e:
            logger.error(f"❌ Erro no teste AdminService: {e}")
            return False

    def test_duplicate_cpf_handler(self) -> bool:
        """Testa o DuplicateCPFHandler"""
        try:
            logger.info("🔍 Testando DuplicateCPFHandler...")

            from src.sentinela.services.duplicate_cpf_handler import DuplicateCPFHandler

            handler = DuplicateCPFHandler()

            # Teste 1: Inicialização
            if not hasattr(handler, '_pending_confirmations'):
                logger.error("❌ DuplicateCPFHandler não inicializou corretamente")
                return False

            # Teste 2: Confirmações pendentes vazio
            if handler._pending_confirmations:
                logger.error("❌ Confirmações pendentes deveriam estar vazias")
                return False

            # Teste 3: Limpeza de expiradas (não deveria dar erro)
            handler.cleanup_expired_confirmations()

            # Teste 4: Estatísticas
            stats = handler.get_stats()
            if not isinstance(stats, dict):
                logger.error("❌ Estatísticas deveriam retornar dict")
                return False

            # Teste 5: Busca de confirmação inexistente
            confirmation = handler.get_pending_confirmation("fake_id")
            if confirmation is not None:
                logger.error("❌ Deveria retornar None para confirmação inexistente")
                return False

            logger.info("✅ DuplicateCPFHandler passou em todos os testes")
            return True

        except Exception as e:
            logger.error(f"❌ Erro no teste DuplicateCPFHandler: {e}")
            return False

    def test_imports_and_dependencies(self) -> bool:
        """Testa se todos os imports funcionam"""
        try:
            logger.info("🔍 Testando imports e dependências...")

            # Teste de imports
            from src.sentinela.services.admin_service import admin_service
            from src.sentinela.services.cpf_validation_service import CPFValidationService
            from src.sentinela.services.duplicate_cpf_handler import duplicate_cpf_handler
            from src.sentinela.services.cpf_verification_service import CPFVerificationService

            # Verifica se instâncias globais estão disponíveis
            if admin_service is None:
                logger.error("❌ admin_service global não está disponível")
                return False

            if duplicate_cpf_handler is None:
                logger.error("❌ duplicate_cpf_handler global não está disponível")
                return False

            # Verifica se classes estão disponíveis
            if CPFValidationService is None:
                logger.error("❌ CPFValidationService não está disponível")
                return False

            if CPFVerificationService is None:
                logger.error("❌ CPFVerificationService não está disponível")
                return False

            logger.info("✅ Todos os imports funcionaram corretamente")
            return True

        except Exception as e:
            logger.error(f"❌ Erro nos imports: {e}")
            return False

    def test_backward_compatibility(self) -> bool:
        """Testa se funções de compatibilidade funcionam"""
        try:
            logger.info("🔍 Testando compatibilidade retroativa...")

            # Teste funções de conveniência do CPFValidationService
            from src.sentinela.services.cpf_validation_service import (
                validate_cpf_format, clean_cpf, format_cpf
            )

            # Teste 1: validate_cpf_format
            if not callable(validate_cpf_format):
                logger.error("❌ validate_cpf_format não é callable")
                return False

            # Teste 2: clean_cpf
            if clean_cpf("123.456.789-09") != "12345678909":
                logger.error("❌ clean_cpf não funciona")
                return False

            # Teste 3: format_cpf
            if format_cpf("12345678909") != "123.456.789-09":
                logger.error("❌ format_cpf não funciona")
                return False

            # Teste funções de conveniência do AdminService
            from src.sentinela.services.admin_service import (
                get_group_administrators, is_user_admin
            )

            if not callable(get_group_administrators):
                logger.error("❌ get_group_administrators não é callable")
                return False

            if not callable(is_user_admin):
                logger.error("❌ is_user_admin não é callable")
                return False

            logger.info("✅ Compatibilidade retroativa funcionando")
            return True

        except Exception as e:
            logger.error(f"❌ Erro na compatibilidade: {e}")
            return False

    async def run_all_tests(self) -> dict:
        """Executa todos os testes"""
        logger.info("🧪 Iniciando testes dos serviços refatorados...")

        tests = {
            'imports_and_dependencies': self.test_imports_and_dependencies(),
            'cpf_validation_service': self.test_cpf_validation_service(),
            'admin_service': await self.test_admin_service(),
            'duplicate_cpf_handler': self.test_duplicate_cpf_handler(),
            'backward_compatibility': self.test_backward_compatibility()
        }

        return tests

def main():
    """Função principal"""

    async def run_tests():
        tester = RefactoredServicesTest()
        results = await tester.run_all_tests()

        # Mostra resultados
        print(f"\n🧪 RESULTADOS DOS TESTES DE REFATORAÇÃO")
        print(f"=========================================")
        print(f"🕒 Executado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")

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
            print(f"\n🎉 TODOS OS TESTES DE REFATORAÇÃO PASSARAM!")
            print(f"✅ Serviços refatorados estão funcionando corretamente")
            print(f"\n💡 Benefícios alcançados:")
            print(f"  • Código mais modular e reutilizável")
            print(f"  • Redução de duplicação de código")
            print(f"  • Melhor separação de responsabilidades")
            print(f"  • Facilidade para testes unitários")
            print(f"  • Manutenibilidade aprimorada")
            sys.exit(0)
        else:
            print(f"\n💥 ALGUNS TESTES FALHARAM!")
            print(f"❌ Verifique os logs acima para detalhes dos erros")
            print(f"🔧 Corrija os problemas antes de usar os novos serviços")
            sys.exit(1)

    # Executa testes assíncronos
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()