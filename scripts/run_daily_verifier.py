import os
import sys
import asyncio

# Adiciona o diretório raiz do projeto ao path do Python
# para permitir a importação dos módulos de 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.sentinela.core.logging_config import setup_logging
from src.sentinela.services.scheduler_service import verify_and_remove_inactive_users
from src.sentinela.clients.db_client import initialize_database

def main():
    """
    Ponto de entrada para o script agendado (Cron Job).
    
    1. Configura o logging para que possamos ver o que está acontecendo.
    2. Inicializa o banco de dados para garantir que as tabelas existam.
    3. Executa a função principal do serviço de agendamento.
    """
    setup_logging()
    initialize_database()
    
    # NOTA: A função `verify_and_remove_inactive_users` no serviço precisará
    # ser tornada assíncrona (`async def`) quando a lógica real de remoção
    # de usuário (que usa a biblioteca do bot) for implementada.
    # Quando isso acontecer, a chamada aqui deverá ser:
    # asyncio.run(verify_and_remove_inactive_users())
    verify_and_remove_inactive_users()

if __name__ == "__main__":
    print("Executando o script de verificação diária do Sentinela...")
    main()
    print("Script de verificação finalizado.")
