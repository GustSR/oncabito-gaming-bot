import logging
import sqlite3
from src.sentinela.core.config import DATABASE_FILE

logger = logging.getLogger(__name__)

def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados SQLite."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome
        return conn
    except sqlite3.Error as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        raise

def initialize_database():
    """
    Cria a tabela de usuários no banco de dados, se ela ainda não existir.
    Esta função é segura para ser chamada múltiplas vezes.
    """
    logger.info(f"Verificando e inicializando o banco de dados em '{DATABASE_FILE}'...")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    cpf TEXT,
                    client_name TEXT,
                    service_name TEXT,
                    service_status TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    last_verification TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabela para controlar estados de interação
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id INTEGER PRIMARY KEY,
                    has_interacted BOOLEAN NOT NULL DEFAULT 0,
                    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Tabela para controlar aceitação de regras
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_rules (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rules_accepted BOOLEAN NOT NULL DEFAULT 0,
                    rules_accepted_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            # Adicionar um gatilho para atualizar 'updated_at' automaticamente
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_users_updated_at
                AFTER UPDATE ON users
                FOR EACH ROW
                BEGIN
                    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = OLD.user_id;
                END;
            """)
            conn.commit()
        logger.info("Banco de dados inicializado com sucesso.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao inicializar o banco de dados: {e}")
        raise

def is_first_interaction(user_id: int) -> bool:
    """
    Verifica se é a primeira interação do usuário.

    Args:
        user_id: ID do usuário no Telegram

    Returns:
        bool: True se for primeira interação, False caso contrário
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT has_interacted FROM user_states WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()

            if result is None:
                # Usuário não existe, é primeira interação
                return True

            return not bool(result['has_interacted'])
    except sqlite3.Error as e:
        logger.error(f"Erro ao verificar primeira interação: {e}")
        return True  # Em caso de erro, trata como primeira interação

def mark_user_interacted(user_id: int):
    """
    Marca que o usuário já interagiu com o bot.

    Args:
        user_id: ID do usuário no Telegram
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_states (user_id, has_interacted, last_interaction)
                VALUES (?, 1, CURRENT_TIMESTAMP)
            """, (user_id,))
            conn.commit()
            logger.info(f"Usuário {user_id} marcado como tendo interagido.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao marcar interação do usuário {user_id}: {e}")

def save_user_data(user_id: int, username: str, cpf: str, client_data: dict) -> bool:
    """
    Salva ou atualiza dados do usuário no banco de dados.

    Args:
        user_id: ID do usuário no Telegram
        username: Nome de usuário do Telegram
        cpf: CPF do cliente
        client_data: Dados do cliente retornados pela API HubSoft

    Returns:
        bool: True se salvou com sucesso, False caso contrário
    """
    try:
        # Extrai dados do cliente
        client_name = client_data.get('nome_razaosocial', '')
        servicos = client_data.get('servicos', [])

        service_name = ''
        service_status = ''
        if servicos:
            servico = servicos[0]  # Pega o primeiro serviço
            service_name = servico.get('nome', '')
            service_status = servico.get('status', '')

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users
                (user_id, username, cpf, client_name, service_name, service_status,
                 is_active, last_verification, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id, username, cpf, client_name, service_name, service_status))
            conn.commit()

        logger.info(f"Dados salvos para usuário {user_id} - Cliente: {client_name}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Erro ao salvar dados do usuário {user_id}: {e}")
        return False

def get_user_data(user_id: int) -> dict | None:
    """
    Busca dados do usuário no banco.

    Args:
        user_id: ID do usuário no Telegram

    Returns:
        dict: Dados do usuário ou None se não encontrado
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()

            if result:
                return dict(result)
            return None

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar dados do usuário {user_id}: {e}")
        return None

def get_all_active_users() -> list:
    """
    Retorna todos os usuários ativos (para checkups diários futuros).

    Returns:
        list: Lista de usuários ativos
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users WHERE is_active = 1
            """)
            results = cursor.fetchall()

            return [dict(row) for row in results]

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar usuários ativos: {e}")
        return []

# Funções para checkups diários futuros
def mark_user_inactive(user_id: int) -> bool:
    """
    Marca usuário como inativo (para remoção do grupo).

    Args:
        user_id: ID do usuário no Telegram

    Returns:
        bool: True se marcou com sucesso
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

        logger.info(f"Usuário {user_id} marcado como inativo")
        return True

    except sqlite3.Error as e:
        logger.error(f"Erro ao marcar usuário {user_id} como inativo: {e}")
        return False

# Funções para controle de regras
def save_user_joining(user_id: int, username: str, expires_hours: int = 24) -> bool:
    """
    Salva informação de usuário que entrou no grupo e precisa aceitar regras.

    Args:
        user_id: ID do usuário
        username: Nome do usuário
        expires_hours: Horas até expirar (padrão 24h)

    Returns:
        bool: True se salvou com sucesso
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_rules
                (user_id, username, joined_at, expires_at, status)
                VALUES (?, ?, CURRENT_TIMESTAMP,
                        datetime('now', '+{} hours'), 'pending')
            """.format(expires_hours), (user_id, username))
            conn.commit()

        logger.info(f"Usuário {username} (ID: {user_id}) salvo como pendente de regras")
        return True

    except sqlite3.Error as e:
        logger.error(f"Erro ao salvar usuário pendente {user_id}: {e}")
        return False

def mark_rules_accepted(user_id: int) -> bool:
    """
    Marca que usuário aceitou as regras.

    Args:
        user_id: ID do usuário

    Returns:
        bool: True se marcou com sucesso
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_rules
                SET rules_accepted = 1,
                    rules_accepted_at = CURRENT_TIMESTAMP,
                    status = 'accepted'
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

        logger.info(f"Usuário {user_id} marcado como tendo aceitado as regras")
        return True

    except sqlite3.Error as e:
        logger.error(f"Erro ao marcar regras aceitas para {user_id}: {e}")
        return False

def get_pending_rules_users() -> list:
    """
    Retorna usuários pendentes de aceitar regras.

    Returns:
        list: Lista de usuários pendentes
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, joined_at, expires_at
                FROM user_rules
                WHERE status = 'pending' AND rules_accepted = 0
            """)
            results = cursor.fetchall()

            return [dict(row) for row in results]

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar usuários pendentes: {e}")
        return []

def get_expired_rules_users() -> list:
    """
    Retorna usuários que expiraram sem aceitar regras.

    Returns:
        list: Lista de usuários expirados
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, joined_at, expires_at
                FROM user_rules
                WHERE status = 'pending'
                AND rules_accepted = 0
                AND expires_at < CURRENT_TIMESTAMP
            """)
            results = cursor.fetchall()

            return [dict(row) for row in results]

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar usuários expirados: {e}")
        return []

def mark_user_expired(user_id: int) -> bool:
    """
    Marca usuário como expirado (não aceitou regras a tempo).

    Args:
        user_id: ID do usuário

    Returns:
        bool: True se marcou com sucesso
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_rules
                SET status = 'expired'
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

        logger.info(f"Usuário {user_id} marcado como expirado")
        return True

    except sqlite3.Error as e:
        logger.error(f"Erro ao marcar usuário {user_id} como expirado: {e}")
        return False
