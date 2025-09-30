import logging
import os
import asyncio

from src.sentinela.core.logging_config import setup_logging
from src.sentinela.bot.bot_instance import application
from src.sentinela.infrastructure.config.dependency_injection import configure_dependencies
from src.sentinela.presentation.telegram_bot_new import register_handlers

def run_migrations():
    """Executa migrations se disponíveis."""
    logger = logging.getLogger(__name__)
    migrations_dir = "migrations"
    if not os.path.exists(migrations_dir):
        logger.info("Diretório de migrations não encontrado, pulando...")
        return

    try:
        import sys
        sys.path.append('.')
        from migrations.migration_engine import MigrationEngine
        from src.sentinela.core.config import DATABASE_FILE

        logger.info("Verificando e aplicando migrations...")
        engine = MigrationEngine(DATABASE_FILE, migrations_dir)
        if engine.run_pending_migrations():
            logger.info("Migrations aplicadas com sucesso.")
        else:
            logger.info("Nenhuma migration pendente.")

    except Exception as e:
        logger.error(f"Erro ao executar migrations: {e}", exc_info=True)
        # Decide-se por não continuar se migrations falharem
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

        # 5. (Opcional) Inicia serviços de background
        # Esta parte pode ser migrada para dentro da nova arquitetura depois
        async def startup_services(app):
            logger.info("Serviços de background (startup) iniciados.")

        async def shutdown_services(app):
            logger.info("Serviços de background (shutdown) finalizados.")

        application.post_init = startup_services
        application.post_shutdown = shutdown_services

        # 6. Inicia o bot
        logger.info("--- Iniciando o bot Sentinela com a NOVA ARQUITETURA ---")
        application.run_polling()
        logger.info("--- Bot Sentinela foi encerrado ---")

    except Exception as e:
        logger.critical(f"Erro fatal na inicialização do bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()