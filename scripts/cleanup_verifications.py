
import sqlite3
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = "data/database/sentinela.db"
USER_ID_TO_CLEAN = 1793240003

def cleanup_user_verifications():
    """Remove todos os registros de verificação para um usuário específico."""
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            logging.info(f"Conectado ao banco de dados: {DB_PATH}")
            
            # 1. Encontrar todos os verification_id para o usuário
            cursor.execute("SELECT id FROM cpf_verifications WHERE user_id = ?", (USER_ID_TO_CLEAN,))
            verification_ids_tuples = cursor.fetchall()
            verification_ids = [item[0] for item in verification_ids_tuples]
            
            if not verification_ids:
                logging.info(f"Nenhum registro de verificação encontrado para o usuário ID: {USER_ID_TO_CLEAN}. Nenhuma ação necessária.")
                return

            logging.info(f"Encontrados {len(verification_ids)} registros de verificação para o usuário ID: {USER_ID_TO_CLEAN}")

            # 2. Deletar registros da tabela filha 'cpf_verification_attempts'
            placeholders = ','.join('?' for _ in verification_ids)
            delete_attempts_query = f"DELETE FROM cpf_verification_attempts WHERE verification_id IN ({placeholders})"
            cursor.execute(delete_attempts_query, verification_ids)
            logging.info(f"{cursor.rowcount} tentativas de verificação removidas.")

            # 3. Deletar registros da tabela pai 'cpf_verifications'
            cursor.execute("DELETE FROM cpf_verifications WHERE user_id = ?", (USER_ID_TO_CLEAN,))
            logging.info(f"{cursor.rowcount} registros de verificação principais removidos.")
            
            conn.commit()
            logging.info("Limpeza concluída com sucesso!")

    except sqlite3.Error as e:
        logging.error(f"Erro de banco de dados durante a limpeza: {e}")
    except Exception as e:
        logging.error(f"Um erro inesperado ocorreu: {e}")

if __name__ == "__main__":
    cleanup_user_verifications()
