import logging
from src.sentinela.core.logging_config import setup_logging
from src.sentinela.clients.db_client import initialize_database
from src.sentinela.bot.bot_instance import application
from src.sentinela.bot.handlers import register_handlers

def main() -> None:
    """
    Ponto de entrada principal para configurar e iniciar o bot Sentinela.
    """
    # 1. Configura o sistema de logging
    setup_logging()
    
    # 2. Garante que o banco de dados e suas tabelas estejam criados
    initialize_database()

    # 3. Registra os handlers (comandos /start, mensagens, etc.)
    register_handlers(application)

    # 4. Inicia o bot e o mantém rodando para receber atualizações
    logger = logging.getLogger(__name__)
    logger.info("--- Iniciando o bot Sentinela ---")
    application.run_polling()
    logger.info("--- Bot Sentinela foi encerrado ---")

if __name__ == "__main__":
    main()
