
import asyncio
import logging
import os
import sys

# Adiciona o diretório raiz ao path para encontrar os módulos da aplicação
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sentinela.core.logging_config import setup_logging
from src.sentinela.infrastructure.config.dependency_injection import configure_dependencies, get_container

async def run_cleanup():
    """Função principal para executar a limpeza."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("--- Iniciando script de limpeza de usuários expirados ---")

    try:
        # Configura a injeção de dependência para ter acesso aos repositórios
        configure_dependencies()
        container = get_container()
        user_repo = container.get("user_repository")

        if not user_repo:
            logger.error("Falha ao obter UserRepository do container.")
            return

        # Executa a função de limpeza
        deleted_count = await user_repo.delete_expired_pending_users()
        
        if deleted_count > 0:
            logger.info(f"{deleted_count} usuários pendentes expirados foram removidos com sucesso.")
        else:
            logger.info("Nenhum usuário pendente expirado encontrado para remover.")

    except Exception as e:
        logger.critical(f"Erro fatal durante a execução do script de limpeza: {e}", exc_info=True)
    finally:
        logger.info("--- Script de limpeza finalizado ---")

if __name__ == "__main__":
    # O script precisa ser executado em um loop de eventos asyncio
    asyncio.run(run_cleanup())
