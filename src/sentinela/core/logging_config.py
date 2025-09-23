import logging
import sys

def setup_logging():
    """
    Configura o sistema de logging para a aplicação.
    Define o formato das mensagens e para onde elas devem ser enviadas (console).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Em um ambiente de produção, é uma boa prática adicionar um FileHandler
            # para salvar os logs em um arquivo:
            # logging.FileHandler("sentinela.log", encoding='utf-8')
        ]
    )

    # Exemplo de como silenciar logs muito verbosos de bibliotecas de terceiros
    # logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Sistema de logging configurado com sucesso.")
