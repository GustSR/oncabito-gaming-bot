import sqlite3
import argparse
import os
import sys
import json

# Adiciona a raiz do projeto ao sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

try:
    from src.sentinela.core.config import DATABASE_FILE
except ImportError:
    print("Erro: Não foi possível importar a configuração.")
    sys.exit(1)

def inspect_verifications(user_id: int):
    """
    Lê e exibe todos os registros de um user_id da tabela cpf_verifications.
    """
    db_path = os.path.join(project_root, DATABASE_FILE)
    
    if not os.path.exists(db_path):
        print(f"ERRO: O arquivo do banco de dados não foi encontrado em '{db_path}'")
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print(f"Conectado ao banco de dados: {db_path}")
        print(f"Buscando registros na tabela 'cpf_verifications' para o user_id: {user_id}")

        cursor.execute("SELECT * FROM cpf_verifications WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        rows = cursor.fetchall()
        
        if not rows:
            print(f"Nenhum registro encontrado para o user_id {user_id}.")
        else:
            print(f"Encontrados {len(rows)} registro(s) para o user_id {user_id}:")
            for row in rows:
                # Converte a linha do sqlite para um dicionário e imprime como JSON
                row_dict = dict(row)
                print(json.dumps(row_dict, indent=2))

    except sqlite3.Error as e:
        print(f"ERRO de banco de dados: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspeciona os registros de verificação de CPF para um usuário.")
    parser.add_argument("user_id", type=int, help="O ID do usuário do Telegram a ser inspecionado.")
    
    args = parser.parse_args()
    
    inspect_verifications(args.user_id)
