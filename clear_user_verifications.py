#!/usr/bin/env python3
"""Script para limpar verificações de um usuário específico."""

import sqlite3
import sys

def clear_user_verifications(user_id: int):
    """Limpa todas as verificações de CPF de um usuário."""
    db_path = "data/database/sentinela.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"🗑️ Limpando dados do usuário {user_id}...")

        # Limpar verificações
        cursor.execute("DELETE FROM cpf_verifications WHERE user_id = ?", (user_id,))
        deleted_verifications = cursor.rowcount

        # Limpar estados
        cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        deleted_states = cursor.rowcount

        conn.commit()

        print(f"✅ {deleted_verifications} verificações removidas")
        print(f"✅ {deleted_states} estados removidos")
        print(f"✅ Usuário {user_id} pode tentar novamente!")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    user_id = 1793240003  # Seu ID
    clear_user_verifications(user_id)
