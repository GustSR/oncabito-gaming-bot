import logging
import os
from src.sentinela.core.logging_config import setup_logging
from src.sentinela.clients.db_client import initialize_database
from src.sentinela.bot.bot_instance import application
from src.sentinela.bot.handlers import register_handlers

def run_migrations():
    """Executa migrations se disponíveis"""
    logger = logging.getLogger(__name__)

    try:
        # Verifica se o diretório de migrations existe
        migrations_dir = "migrations"
        if not os.path.exists(migrations_dir):
            logger.info("Diretório de migrations não encontrado, pulando...")
            return

        # Importa e executa o migration engine
        import sys
        sys.path.append('.')

        from migrations.migration_engine import MigrationEngine
        from src.sentinela.core.config import DATABASE_FILE

        logger.info("Verificando e aplicando migrations...")
        engine = MigrationEngine(DATABASE_FILE, migrations_dir)

        # Executa migrations pendentes
        if engine.run_pending_migrations():
            logger.info("Migrations aplicadas com sucesso")
        else:
            logger.warning("Algumas migrations falharam - sistema pode funcionar mesmo assim")

    except Exception as e:
        logger.warning(f"Erro ao executar migrations: {e}")
        logger.info("Sistema continuará sem migrations - pode funcionar normalmente")

def main() -> None:
    """
    Ponto de entrada principal para configurar e iniciar o bot Sentinela.
    """
    # 1. Configura o sistema de logging
    setup_logging()

    # 2. Executa migrations (antes da inicialização do DB)
    run_migrations()

    # 3. Garante que o banco de dados e suas tabelas estejam criados
    initialize_database()

    # 4. Registra os handlers (comandos /start, mensagens, etc.)
    register_handlers(application)

    # 5. Inicia o bot e o mantém rodando para receber atualizações
    logger = logging.getLogger(__name__)
    logger.info("--- Iniciando o bot Sentinela ---")
    application.run_polling()
    logger.info("--- Bot Sentinela foi encerrado ---")

if __name__ == "__main__":
    main()
