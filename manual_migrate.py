
import sqlite3
import logging

logger = logging.getLogger(__name__)
db_path = "data/database/sentinela.db"
migration_file = "migrations/001_create_initial_schema.sql"

def run_manual_migration():
    try:
        with open(migration_file, 'r') as f:
            sql_script = f.read()
        
        with sqlite3.connect(db_path) as conn:
            print(f"Conectado ao banco de dados {db_path}")
            print("Executando script de migração...")
            conn.executescript(sql_script)
            conn.commit()
            print("Script de migração executado com sucesso.")

    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
    except FileNotFoundError:
        print(f"Arquivo de migração não encontrado: {migration_file}")
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}")

if __name__ == "__main__":
    run_manual_migration()
