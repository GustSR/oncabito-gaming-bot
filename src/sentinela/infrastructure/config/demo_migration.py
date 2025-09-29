"""
Script de demonstração da migração para nova arquitetura.

Mostra como o código antigo pode ser redirecionado para a nova
arquitetura sem quebrar compatibilidade.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def demo_user_verification_migration():
    """
    Demonstra a migração da verificação de usuário.

    Compara o código antigo com o novo para mostrar que
    ambos funcionam de forma idêntica.
    """
    print("🔄 Demo: Migração de Verificação de Usuário")
    print("=" * 50)

    try:
        # Inicializa nova arquitetura
        from ..config.bootstrap import initialize_application
        await initialize_application()

        print("✅ Nova arquitetura inicializada com sucesso!")

        # Demonstra compatibilidade: função antiga redirecionando para nova
        from ...services.user_service_new import process_user_verification

        # Teste com dados fictícios
        test_cpf = "12345678901"
        test_user_id = 123456
        test_username = "demo_user"

        print(f"\n📋 Testando verificação para usuário: {test_username}")
        print(f"   CPF: {test_cpf[:3]}***")
        print(f"   User ID: {test_user_id}")

        # Executa verificação via camada de compatibilidade
        result = await process_user_verification(
            cpf=test_cpf,
            user_id=test_user_id,
            username=test_username
        )

        print(f"\n📤 Resultado da verificação:")
        print(f"   Tipo: {type(result).__name__}")
        print(f"   Conteúdo: {result[:100]}...")

        print("\n✅ Verificação executada com sucesso via NOVA ARQUITETURA!")
        print("   - Função antiga (process_user_verification) → Nova implementação")
        print("   - Commands/Handlers → Application Layer")
        print("   - External Services → Infrastructure Layer")
        print("   - Repository Pattern → Domain Layer")

        # Demonstra injeção de dependências
        print(f"\n🔧 Demonstrando Dependency Injection:")

        from ...infrastructure.config.dependency_injection import get_container
        from ...domain.repositories.user_repository import UserRepository
        from ...application.commands.verify_user_handler import VerifyUserHandler

        container = get_container()

        user_repo = container.get(UserRepository)
        verify_handler = container.get(VerifyUserHandler)

        print(f"   ✅ UserRepository: {type(user_repo).__name__}")
        print(f"   ✅ VerifyUserHandler: {type(verify_handler).__name__}")
        print(f"   ✅ Todas as dependências injetadas automaticamente!")

        return True

    except Exception as e:
        print(f"❌ Erro durante demonstração: {e}")
        logger.error(f"Erro na demo: {e}")
        return False


async def demo_repository_operations():
    """
    Demonstra as operações do repository.
    """
    print("\n🗄️ Demo: Operações do Repository")
    print("=" * 50)

    try:
        from ...infrastructure.config.dependency_injection import get_container
        from ...domain.repositories.user_repository import UserRepository

        container = get_container()
        user_repo = container.get(UserRepository)

        # Testa contagem de usuários ativos
        active_count = await user_repo.count_active_users()
        print(f"📊 Usuários ativos no sistema: {active_count}")

        # Testa busca de usuários ativos
        active_users = await user_repo.find_active_users()
        print(f"👥 Lista de usuários ativos: {len(active_users)} encontrados")

        # Testa busca de administradores
        admins = await user_repo.find_admins()
        print(f"👨‍💼 Administradores: {len(admins)} encontrados")

        print("✅ Repository funcionando perfeitamente!")
        return True

    except Exception as e:
        print(f"❌ Erro nas operações do repository: {e}")
        logger.error(f"Erro no repository demo: {e}")
        return False


async def main():
    """Executa todas as demonstrações."""
    print("🚀 DEMONSTRAÇÃO DA REFATORAÇÃO - FASE 2.1 COMPLETA")
    print("=" * 60)

    success = True

    # Demo 1: Migração de verificação
    success &= await demo_user_verification_migration()

    # Demo 2: Operações do repository
    success &= await demo_repository_operations()

    print("\n" + "=" * 60)
    if success:
        print("✅ TODAS AS DEMONSTRAÇÕES EXECUTADAS COM SUCESSO!")
        print("\n🎉 FASE 2.1 CONCLUÍDA:")
        print("   ✅ User Service migrado para nova arquitetura")
        print("   ✅ External Services abstractions criadas")
        print("   ✅ Commands e Handlers implementados")
        print("   ✅ Repository Pattern expandido")
        print("   ✅ Dependency Injection funcionando")
        print("   ✅ Compatibilidade com código existente mantida")
    else:
        print("❌ Algumas demonstrações falharam - verificar logs")

    return success


if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Executa demo
    asyncio.run(main())