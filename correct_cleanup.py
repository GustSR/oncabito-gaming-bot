import sqlite3
import logging

logger = logging.getLogger(__name__)
db_path = "data/database/sentinela.db"
user_id_to_clear = 1793240003

def cleanup_verifications():
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM cpf_verifications WHERE user_id = ?",
                (user_id_to_clear,)
            )
            verification_ids = [row[0] for row in cursor.fetchall()]

            if not verification_ids:
                print(f"Nenhuma verificação encontrada para o usuário ID: {user_id_to_clear} no banco de dados {db_path}")
                return

            cursor.execute(
                f"DELETE FROM cpf_verification_attempts WHERE verification_id IN ({','.join('?' for _ in verification_ids)})",
                verification_ids
            )
            attempts_deleted = cursor.rowcount
            print(f"{attempts_deleted} tentativas de verificação removidas de {db_path}.")

            cursor.execute(
                "DELETE FROM cpf_verifications WHERE user_id = ?",
                (user_id_to_clear,)
            )
            verifications_deleted = cursor.rowcount
            print(f"{verifications_deleted} registros de verificação removidos para o usuário ID: {user_id_to_clear} de {db_path}")

            conn.commit()
            print("Limpeza concluída com sucesso.")

    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}")

if __name__ == "__main__":
    cleanup_verifications()