import logging
import os
import sys

from src.sentinela.core.logging_config import setup_logging
from src.sentinela.infrastructure.config.dependency_injection import configure_dependencies
from src.sentinela.presentation.telegram_bot_new import application, register_handlers
from migrations.migration_engine import MigrationEngine
from src.sentinela.core.config import DATABASE_FILE

from telegram.constants import UpdateType

def run_migrations():
    """Executa migrations se disponíveis."""
    logger = logging.getLogger(__name__)
    migrations_dir = "migrations"
    if not os.path.exists(migrations_dir):
        logger.info("Diretório de migrations não encontrado, pulando...")
        return

    try:
        # Adiciona o diretório raiz ao path para o motor de migração
        sys.path.append('.')
        
        logger.info("Verificando e aplicando migrations...")
        engine = MigrationEngine(DATABASE_FILE, migrations_dir)
        
        if not engine.run_pending_migrations():
            logger.error("Falha ao aplicar migrations. Abortando.")
            raise RuntimeError("Falha crítica nas migrations. Abortando.")
        
        if engine.get_pending_migrations():
            logger.warning("Ainda há migrations pendentes após a execução. Verifique os logs.")
        else:
            logger.info("Migrations aplicadas com sucesso.")

    except Exception as e:
        logger.error(f"Erro ao executar migrations: {e}", exc_info=True)
        raise RuntimeError("Falha crítica nas migrations. Abortando.") from e

def main() -> None:
    """
    Ponto de entrada principal para configurar e iniciar o bot Sentinela.
    """
    # 1. Configura o sistema de logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # 2. Executa migrations
        run_migrations()

        # 3. Configura a Injeção de Dependência (essencial para a nova arquitetura)
        configure_dependencies()
        logger.info("Injeção de dependência configurada.")

        # 4. Registra os handlers da nova arquitetura
        register_handlers(application)

        # 5. Inicia o bot
        logger.info("--- Iniciando o bot Sentinela com a NOVA ARQUITETURA ---")
        all_updates = [t for t in UpdateType]
        application.run_polling(allowed_updates=all_updates)
        logger.info("--- Bot Sentinela foi encerrado ---")

    except Exception as e:
        logger.critical(f"Erro fatal na inicialização do bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()