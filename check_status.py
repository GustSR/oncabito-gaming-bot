
import sqlite3
import logging
import asyncio
import sys
import os

# Adiciona o diretório raiz ao path para encontrar os módulos da aplicação
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sentinela.core.logging_config import setup_logging

DB_PATH = "data/database/sentinela.db"
USER_ID_TO_CHECK = 1793240003

def check_user_status():
    """Verifica e imprime o status de um usuário específico."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            logger.info(f"Conectado ao banco de dados: {DB_PATH}")
            
            cursor.execute("SELECT status, expires_at FROM users WHERE telegram_user_id = ?", (USER_ID_TO_CHECK,))
            row = cursor.fetchone()
            
            if row:
                logger.info(f"Status encontrado para o usuário {USER_ID_TO_CHECK}: status='{row['status']}', expires_at='{row['expires_at']}'")
                print(f"Status: {row['status']}")
                print(f"Expires At: {row['expires_at']}")
            else:
                logger.warning(f"Nenhum usuário encontrado com o telegram_user_id: {USER_ID_TO_CHECK}")
                print("Usuário não encontrado.")

    except sqlite3.Error as e:
        logger.error(f"Erro de banco de dados: {e}")
    except Exception as e:
        logger.error(f"Um erro inesperado ocorreu: {e}")

if __name__ == "__main__":
    check_user_status()
