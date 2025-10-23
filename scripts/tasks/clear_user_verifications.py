import sqlite3
import argparse
import os
import sys

# Adiciona a raiz do projeto ao sys.path para permitir importações de 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

try:
    from src.sentinela.core.config import DATABASE_FILE
except ImportError:
    print("Erro: Não foi possível importar a configuração. Verifique se o script está no local correto.")
    sys.exit(1)

def clear_verifications(user_id: int):
    """
    Deleta todos os registros de um user_id específico da tabela cpf_verifications.
    """
    db_path = os.path.join(project_root, DATABASE_FILE)
    
    if not os.path.exists(db_path):
        print(f"ERRO: O arquivo do banco de dados não foi encontrado em '{db_path}'")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cpf_verifications';")
        if cursor.fetchone() is None:
            print(f"ERRO: A tabela 'cpf_verifications' não existe no banco de dados '{db_path}'.")
            conn.close()
            return

        print(f"Conectado ao banco de dados: {db_path}")
        print(f"Tentando deletar registros da tabela 'cpf_verifications' para o user_id: {user_id}")

        # Executa o comando DELETE
        cursor.execute("DELETE FROM cpf_verifications WHERE user_id = ?", (user_id,))
        
        # Pega o número de linhas afetadas
        rows_deleted = cursor.rowcount
        
        conn.commit()
        
        print(f"Operação concluída. {rows_deleted} registro(s) foram deletados para o user_id {user_id}.")

    except sqlite3.Error as e:
        print(f"ERRO de banco de dados: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Limpa os registros de verificação de CPF para um usuário específico do Telegram.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("user_id", type=int, help="O ID do usuário do Telegram para o qual as tentativas serão limpas.")
    
    args = parser.parse_args()
    
    clear_verifications(args.user_id)
