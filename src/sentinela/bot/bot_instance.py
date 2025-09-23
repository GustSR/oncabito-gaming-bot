import logging
from telegram.ext import Application
from src.sentinela.core.config import TELEGRAM_TOKEN

logger = logging.getLogger(__name__)

def create_bot_application() -> Application:
    """
    Cria e configura a instância da aplicação do bot usando o token fornecido.
    """
    logger.info("Criando a instância da aplicação do bot...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    logger.info("Instância da aplicação do bot criada com sucesso.")
    return application

# Cria uma instância única da aplicação para ser importada em outros módulos
application = create_bot_application()
