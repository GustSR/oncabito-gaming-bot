import sqlite3
import logging

logger = logging.getLogger(__name__)
db_path = "data/oncabo.db"

def inspect_full_schema():
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if not tables:
                print("No tables found.")
                return

            print("Database schema for 'oncabo.db':\n")

            for table_name_tuple in tables:
                table_name = table_name_tuple[0]
                print(f"--- TABLE: {table_name} ---")
                
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                for column in columns:
                    print(column)
                print("")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    inspect_full_schema()