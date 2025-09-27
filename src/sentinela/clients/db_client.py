import logging
import sqlite3
from datetime import datetime
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

            # Tabela para atendimentos de suporte
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hubsoft_atendimento_id TEXT UNIQUE,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    user_mention TEXT,
                    client_id TEXT,
                    cpf TEXT,
                    client_name TEXT,
                    category TEXT NOT NULL,
                    affected_game TEXT,
                    problem_started TEXT,
                    description TEXT NOT NULL,
                    urgency_level TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'pending',
                    telegram_message_id INTEGER,
                    topic_thread_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Tabela para conversas de formulário (anti-spam e controle de estado)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS support_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    conversation_state TEXT DEFAULT 'idle',
                    current_step INTEGER DEFAULT 0,
                    form_data TEXT,
                    is_active BOOLEAN DEFAULT 0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Tabela para controle anti-spam
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS support_spam_control (
                    user_id INTEGER PRIMARY KEY,
                    active_tickets_count INTEGER DEFAULT 0,
                    daily_tickets_count INTEGER DEFAULT 0,
                    last_ticket_date DATE DEFAULT CURRENT_DATE,
                    last_ticket_time TIMESTAMP,
                    spam_score INTEGER DEFAULT 0,
                    blocked_until TIMESTAMP,
                    total_tickets INTEGER DEFAULT 0,
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

def get_user_by_cpf(cpf: str) -> dict | None:
    """
    Busca dados do usuário no banco pelo CPF.

    Args:
        cpf: CPF do usuário

    Returns:
        dict: Dados do usuário ou None se não encontrado
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users WHERE cpf = ?
            """, (cpf,))
            result = cursor.fetchone()

            if result:
                return dict(result)
            return None

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar dados do usuário pelo CPF {cpf}: {e}")
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

# ==================== FUNÇÕES DE SUPORTE ====================

def can_create_support_ticket(user_id: int) -> dict:
    """
    Verifica se usuário pode criar um novo ticket de suporte (anti-spam).

    Args:
        user_id: ID do usuário

    Returns:
        dict: Resultado da verificação
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Busca controle de spam
            cursor.execute("""
                SELECT active_tickets_count, daily_tickets_count, last_ticket_date,
                       last_ticket_time, spam_score, blocked_until
                FROM support_spam_control
                WHERE user_id = ?
            """, (user_id,))
            spam_data = cursor.fetchone()

            # Verifica tickets ativos
            cursor.execute("""
                SELECT COUNT(*) as active_count
                FROM support_tickets
                WHERE user_id = ? AND status IN ('pending', 'open', 'in_progress')
            """, (user_id,))
            active_tickets = cursor.fetchone()['active_count']

            # Verifica conversas ativas
            cursor.execute("""
                SELECT COUNT(*) as active_conversations
                FROM support_conversations
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            active_conversations = cursor.fetchone()['active_conversations']

            # Regras de validação
            if active_tickets > 0:
                return {
                    'can_create': False,
                    'reason': 'active_ticket',
                    'message': 'Você já possui um atendimento ativo'
                }

            if active_conversations > 0:
                return {
                    'can_create': False,
                    'reason': 'active_conversation',
                    'message': 'Você já está preenchendo um formulário de suporte'
                }

            # Verifica bloqueio por spam
            if spam_data and spam_data['blocked_until']:
                from datetime import datetime
                blocked_until = datetime.fromisoformat(spam_data['blocked_until'])
                if datetime.now() < blocked_until:
                    return {
                        'can_create': False,
                        'reason': 'blocked',
                        'message': 'Você está temporariamente bloqueado para criar novos chamados'
                    }

            # Verifica limite diário (3 por dia)
            if spam_data and spam_data['daily_tickets_count'] >= 3:
                from datetime import datetime, date
                last_date = datetime.fromisoformat(spam_data['last_ticket_date']).date()
                if last_date == date.today():
                    return {
                        'can_create': False,
                        'reason': 'daily_limit',
                        'message': 'Limite diário de 3 chamados atingido'
                    }

            return {'can_create': True, 'reason': 'approved', 'message': 'Pode criar ticket'}

    except sqlite3.Error as e:
        logger.error(f"Erro ao verificar permissão de ticket para usuário {user_id}: {e}")
        return {'can_create': False, 'reason': 'error', 'message': 'Erro interno'}

def start_support_conversation(user_id: int, username: str) -> bool:
    """
    Inicia uma conversa de formulário de suporte.

    Args:
        user_id: ID do usuário
        username: Nome do usuário

    Returns:
        bool: True se iniciou com sucesso
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Finaliza conversas antigas do usuário
            cursor.execute("""
                UPDATE support_conversations
                SET is_active = 0, completed_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))

            # Inicia nova conversa
            cursor.execute("""
                INSERT INTO support_conversations
                (user_id, conversation_state, current_step, is_active, form_data)
                VALUES (?, 'category_selection', 1, 1, '{}')
            """, (user_id,))

            conn.commit()
            logger.info(f"Conversa de suporte iniciada para usuário {username} (ID: {user_id})")
            return True

    except sqlite3.Error as e:
        logger.error(f"Erro ao iniciar conversa de suporte para {user_id}: {e}")
        return False

def get_support_conversation(user_id: int) -> dict:
    """
    Busca conversa ativa de suporte do usuário.

    Args:
        user_id: ID do usuário

    Returns:
        dict: Dados da conversa ou None
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM support_conversations
                WHERE user_id = ? AND is_active = 1
                ORDER BY started_at DESC LIMIT 1
            """, (user_id,))
            result = cursor.fetchone()

            if result:
                return dict(result)
            return None

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar conversa de suporte para {user_id}: {e}")
        return None

def update_support_conversation(user_id: int, step: int, state: str, form_data: str) -> bool:
    """
    Atualiza estado da conversa de suporte.

    Args:
        user_id: ID do usuário
        step: Passo atual
        state: Estado atual
        form_data: Dados do formulário (JSON)

    Returns:
        bool: True se atualizou com sucesso
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE support_conversations
                SET current_step = ?, conversation_state = ?, form_data = ?,
                    last_activity = CURRENT_TIMESTAMP
                WHERE user_id = ? AND is_active = 1
            """, (step, state, form_data, user_id))
            conn.commit()
            return True

    except sqlite3.Error as e:
        logger.error(f"Erro ao atualizar conversa de suporte para {user_id}: {e}")
        return False

def save_support_ticket(ticket_data: dict) -> int:
    """
    Salva ticket de suporte no banco.

    Args:
        ticket_data: Dados completos do ticket

    Returns:
        int: ID do ticket criado ou None se erro
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO support_tickets
                (hubsoft_atendimento_id, user_id, username, user_mention, client_id, cpf, client_name,
                 category, affected_game, problem_started, description,
                 urgency_level, telegram_message_id, topic_thread_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket_data.get('hubsoft_atendimento_id'),
                ticket_data['user_id'], ticket_data['username'], ticket_data['user_mention'],
                ticket_data.get('client_id', ticket_data['user_id']), ticket_data['cpf'], ticket_data['client_name'],
                ticket_data['category'], ticket_data['affected_game'], ticket_data['problem_started'],
                ticket_data['description'], ticket_data['urgency_level'],
                ticket_data.get('telegram_message_id'), ticket_data.get('topic_thread_id')
            ))

            ticket_id = cursor.lastrowid

            # Atualiza controle anti-spam
            update_spam_control(ticket_data['user_id'])

            # Finaliza conversa
            cursor.execute("""
                UPDATE support_conversations
                SET is_active = 0, completed_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND is_active = 1
            """, (ticket_data['user_id'],))

            conn.commit()
            logger.info(f"Ticket de suporte #{ticket_id} criado para usuário {ticket_data['username']}")
            return ticket_id

    except sqlite3.Error as e:
        logger.error(f"Erro ao salvar ticket de suporte: {e}")
        return None

def update_spam_control(user_id: int) -> bool:
    """
    Atualiza controles anti-spam para o usuário.

    Args:
        user_id: ID do usuário

    Returns:
        bool: True se atualizou com sucesso
    """
    try:
        from datetime import datetime, date

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Busca dados atuais
            cursor.execute("""
                SELECT daily_tickets_count, last_ticket_date, total_tickets
                FROM support_spam_control WHERE user_id = ?
            """, (user_id,))
            current_data = cursor.fetchone()

            today = date.today()
            daily_count = 1
            total_count = 1

            if current_data:
                last_date = datetime.fromisoformat(current_data['last_ticket_date']).date()
                total_count = current_data['total_tickets'] + 1

                if last_date == today:
                    daily_count = current_data['daily_tickets_count'] + 1
                else:
                    daily_count = 1

            # Conta tickets ativos
            cursor.execute("""
                SELECT COUNT(*) as active_count
                FROM support_tickets
                WHERE user_id = ? AND status IN ('pending', 'open', 'in_progress')
            """, (user_id,))
            active_count = cursor.fetchone()['active_count']

            # Atualiza/insere dados
            cursor.execute("""
                INSERT OR REPLACE INTO support_spam_control
                (user_id, active_tickets_count, daily_tickets_count, last_ticket_date,
                 last_ticket_time, total_tickets)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (user_id, active_count, daily_count, today.isoformat(), total_count))

            conn.commit()
            return True

    except sqlite3.Error as e:
        logger.error(f"Erro ao atualizar controle anti-spam para {user_id}: {e}")
        return False

def get_active_support_tickets(user_id: int) -> list:
    """
    Busca tickets ativos do usuário.

    Args:
        user_id: ID do usuário

    Returns:
        list: Lista de tickets ativos
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM support_tickets
                WHERE user_id = ? AND status IN ('pending', 'open', 'in_progress')
                ORDER BY created_at DESC
            """, (user_id,))
            results = cursor.fetchall()

            return [dict(row) for row in results]

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar tickets ativos para {user_id}: {e}")
        return []

def get_user_bot_created_hubsoft_ids(user_id: int) -> list:
    """
    Busca IDs do HubSoft de todos os atendimentos criados pelo bot para um usuário.

    Args:
        user_id: ID do usuário

    Returns:
        list: Lista de IDs do HubSoft de atendimentos criados pelo bot
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT hubsoft_atendimento_id
                FROM support_tickets
                WHERE user_id = ?
                AND hubsoft_atendimento_id IS NOT NULL
                AND hubsoft_atendimento_id != ''
                ORDER BY created_at DESC
            """, (user_id,))
            results = cursor.fetchall()

            # Retorna apenas os IDs, não os dicts completos
            return [row['hubsoft_atendimento_id'] for row in results]

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar IDs HubSoft para usuário {user_id}: {e}")
        return []

def update_user_id_for_cpf(cpf: str, new_user_id: int, new_username: str) -> bool:
    """
    Atualiza o user_id e username para um registro de usuário existente baseado no CPF.
    Usado para remapear um CPF para uma nova conta do Telegram.

    Args:
        cpf: O CPF do registro a ser atualizado.
        new_user_id: O novo ID de usuário do Telegram.
        new_username: O novo username do Telegram.

    Returns:
        bool: True se a atualização foi bem-sucedida, False caso contrário.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET user_id = ?, username = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cpf = ?
            """, (new_user_id, new_username, cpf))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Registro de usuário para CPF {cpf[:3]}*** remapeado para o novo user_id {new_user_id}")
                return True
            else:
                logger.warning(f"Nenhum usuário encontrado com o CPF {cpf[:3]}*** para remapear.")
                return False

    except sqlite3.Error as e:
        logger.error(f"Erro ao remapear CPF para o novo user_id {new_user_id}: {e}")
        return False

# === FUNÇÕES DE SINCRONIZAÇÃO HUBSOFT ===

def update_support_tickets_table_for_sync():
    """
    Atualiza a tabela support_tickets com campos necessários para sincronização.
    Esta função é segura para ser executada múltiplas vezes.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Adiciona campos de sincronização se não existirem
            cursor.execute("""
                SELECT name FROM pragma_table_info('support_tickets')
                WHERE name IN ('hubsoft_protocol', 'sync_status', 'synced_at', 'last_sync_attempt', 'sync_error')
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]

            if 'hubsoft_protocol' not in existing_columns:
                cursor.execute("""
                    ALTER TABLE support_tickets
                    ADD COLUMN hubsoft_protocol TEXT
                """)
                logger.info("Adicionada coluna 'hubsoft_protocol' à tabela support_tickets")

            if 'sync_status' not in existing_columns:
                cursor.execute("""
                    ALTER TABLE support_tickets
                    ADD COLUMN sync_status TEXT DEFAULT 'pending'
                """)
                logger.info("Adicionada coluna 'sync_status' à tabela support_tickets")

            if 'synced_at' not in existing_columns:
                cursor.execute("""
                    ALTER TABLE support_tickets
                    ADD COLUMN synced_at TIMESTAMP
                """)
                logger.info("Adicionada coluna 'synced_at' à tabela support_tickets")

            if 'last_sync_attempt' not in existing_columns:
                cursor.execute("""
                    ALTER TABLE support_tickets
                    ADD COLUMN last_sync_attempt TIMESTAMP
                """)
                logger.info("Adicionada coluna 'last_sync_attempt' à tabela support_tickets")

            if 'sync_error' not in existing_columns:
                cursor.execute("""
                    ALTER TABLE support_tickets
                    ADD COLUMN sync_error TEXT
                """)
                logger.info("Adicionada coluna 'sync_error' à tabela support_tickets")

            conn.commit()
            logger.info("Atualização da tabela support_tickets para sincronização concluída")

    except sqlite3.Error as e:
        logger.error(f"Erro ao atualizar tabela support_tickets para sincronização: {e}")
        raise

def create_administrators_table():
    """
    Cria tabela para armazenar administradores detectados automaticamente.
    Esta função é segura para ser executada múltiplas vezes.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS administrators (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    status TEXT,
                    detected_at TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            conn.commit()
            logger.info("Tabela administrators criada/verificada com sucesso")

    except sqlite3.Error as e:
        logger.error(f"Erro ao criar tabela administrators: {e}")
        raise

def get_offline_tickets() -> list:
    """
    Busca todos os tickets criados offline (sem hubsoft_atendimento_id).

    Returns:
        list: Lista de tickets offline
    """
    try:
        # Garante que a tabela está atualizada
        update_support_tickets_table_for_sync()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM support_tickets
                WHERE (hubsoft_atendimento_id IS NULL OR hubsoft_atendimento_id = '')
                AND status NOT IN ('resolved', 'closed', 'cancelled')
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar tickets offline: {e}")
        return []

def get_all_active_tickets_with_hubsoft_id() -> list:
    """
    Busca todos os tickets ativos que possuem ID do HubSoft.

    Returns:
        list: Lista de tickets ativos com HubSoft ID
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM support_tickets
                WHERE hubsoft_atendimento_id IS NOT NULL
                AND hubsoft_atendimento_id != ''
                AND status NOT IN ('resolved', 'closed', 'cancelled')
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar tickets ativos com HubSoft ID: {e}")
        return []

def get_ticket_by_hubsoft_id(hubsoft_id: str) -> dict:
    """
    Busca ticket por ID do HubSoft.

    Args:
        hubsoft_id: ID do atendimento no HubSoft

    Returns:
        dict: Dados do ticket ou None se não encontrado
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM support_tickets
                WHERE hubsoft_atendimento_id = ?
            """, (hubsoft_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar ticket por HubSoft ID {hubsoft_id}: {e}")
        return None

def get_ticket_by_id(ticket_id: int) -> dict:
    """
    Busca ticket por ID local.

    Args:
        ticket_id: ID do ticket local

    Returns:
        dict: Dados do ticket ou None se não encontrado
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM support_tickets
                WHERE id = ?
            """, (ticket_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar ticket por ID {ticket_id}: {e}")
        return None

def update_ticket_sync_status(ticket_id: int, sync_data: dict) -> bool:
    """
    Atualiza dados de sincronização de um ticket.

    Args:
        ticket_id: ID do ticket local
        sync_data: Dados de sincronização

    Returns:
        bool: True se sucesso, False caso contrário
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Monta query dinâmica baseada nos dados fornecidos
            set_clauses = []
            values = []

            if 'hubsoft_status' in sync_data:
                set_clauses.append("status = ?")
                # Se hubsoft_status é um dict, extrair o campo relevante
                status = sync_data['hubsoft_status']
                if isinstance(status, dict):
                    values.append(status.get('display', status.get('name', 'Em Andamento')))
                else:
                    values.append(str(status))

            if 'last_sync' in sync_data:
                set_clauses.append("last_sync_attempt = ?")
                values.append(sync_data['last_sync'])

            if 'is_synced' in sync_data:
                set_clauses.append("sync_status = ?")
                values.append('synced' if sync_data['is_synced'] else 'pending')

                if sync_data['is_synced']:
                    set_clauses.append("synced_at = ?")
                    values.append(sync_data.get('last_sync', datetime.now().isoformat()))

            if 'sync_error' in sync_data:
                set_clauses.append("sync_error = ?")
                values.append(sync_data['sync_error'])

            # Sempre atualiza timestamp
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(ticket_id)

            if set_clauses:
                query = f"""
                    UPDATE support_tickets
                    SET {', '.join(set_clauses)}
                    WHERE id = ?
                """
                cursor.execute(query, values)
                conn.commit()

                logger.info(f"Status de sincronização do ticket {ticket_id} atualizado")
                return cursor.rowcount > 0

            return False

    except sqlite3.Error as e:
        logger.error(f"Erro ao atualizar status de sincronização do ticket {ticket_id}: {e}")
        return False

def update_ticket_with_hubsoft_data(ticket_id: int, hubsoft_data: dict) -> bool:
    """
    Atualiza ticket local com dados do HubSoft após sincronização.

    Args:
        ticket_id: ID do ticket local
        hubsoft_data: Dados recebidos do HubSoft

    Returns:
        bool: True se sucesso, False caso contrário
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE support_tickets
                SET hubsoft_atendimento_id = ?,
                    hubsoft_protocol = ?,
                    sync_status = ?,
                    synced_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                hubsoft_data.get('hubsoft_atendimento_id'),
                hubsoft_data.get('hubsoft_protocol'),
                hubsoft_data.get('sync_status', 'synced'),
                hubsoft_data.get('synced_at'),
                ticket_id
            ))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Ticket {ticket_id} atualizado com dados do HubSoft")
                return True
            else:
                logger.warning(f"Nenhum ticket encontrado com ID {ticket_id}")
                return False

    except sqlite3.Error as e:
        logger.error(f"Erro ao atualizar ticket {ticket_id} com dados do HubSoft: {e}")
        return False

def get_sync_statistics() -> dict:
    """
    Retorna estatísticas de sincronização do sistema.

    Returns:
        dict: Estatísticas de sincronização
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Total de tickets
            cursor.execute("SELECT COUNT(*) FROM support_tickets")
            total_tickets = cursor.fetchone()[0]

            # Tickets sincronizados
            cursor.execute("""
                SELECT COUNT(*) FROM support_tickets
                WHERE hubsoft_atendimento_id IS NOT NULL
                AND hubsoft_atendimento_id != ''
            """)
            synced_tickets = cursor.fetchone()[0]

            # Tickets offline
            cursor.execute("""
                SELECT COUNT(*) FROM support_tickets
                WHERE (hubsoft_atendimento_id IS NULL OR hubsoft_atendimento_id = '')
                AND status NOT IN ('resolved', 'closed', 'cancelled')
            """)
            offline_tickets = cursor.fetchone()[0]

            # Tickets com erro de sincronização
            cursor.execute("""
                SELECT COUNT(*) FROM support_tickets
                WHERE sync_error IS NOT NULL AND sync_error != ''
            """)
            failed_sync_tickets = cursor.fetchone()[0]

            # Última sincronização
            cursor.execute("""
                SELECT MAX(synced_at) FROM support_tickets
                WHERE synced_at IS NOT NULL
            """)
            last_sync = cursor.fetchone()[0]

            return {
                "total_tickets": total_tickets,
                "synced_tickets": synced_tickets,
                "offline_tickets": offline_tickets,
                "failed_sync_tickets": failed_sync_tickets,
                "last_successful_sync": last_sync,
                "sync_percentage": round((synced_tickets / total_tickets * 100) if total_tickets > 0 else 0, 2)
            }

    except sqlite3.Error as e:
        logger.error(f"Erro ao obter estatísticas de sincronização: {e}")
        return {}

# === FUNÇÕES DE ADMINISTRADORES ===

def get_stored_administrators() -> list:
    """
    Busca todos os administradores armazenados no banco.

    Returns:
        list: Lista de administradores ativos
    """
    try:
        # Garante que a tabela existe
        create_administrators_table()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, last_name, status, detected_at, last_updated
                FROM administrators
                WHERE is_active = 1
                ORDER BY detected_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar administradores armazenados: {e}")
        return []

def update_administrators(admin_list: list) -> bool:
    """
    Atualiza lista completa de administradores no banco.

    Args:
        admin_list: Lista de dicionários com dados dos administradores

    Returns:
        bool: True se sucesso, False caso contrário
    """
    try:
        # Garante que a tabela existe
        create_administrators_table()

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Desativa todos os administradores atuais
            cursor.execute("""
                UPDATE administrators
                SET is_active = 0, last_updated = CURRENT_TIMESTAMP
            """)

            # Insere ou atualiza administradores atuais
            for admin in admin_list:
                cursor.execute("""
                    INSERT OR REPLACE INTO administrators
                    (user_id, username, first_name, last_name, status, detected_at, last_updated, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
                """, (
                    admin['user_id'],
                    admin.get('username'),
                    admin.get('first_name'),
                    admin.get('last_name'),
                    admin.get('status'),
                    admin.get('detected_at')
                ))

            conn.commit()
            logger.info(f"Lista de administradores atualizada: {len(admin_list)} administradores ativos")
            return True

    except sqlite3.Error as e:
        logger.error(f"Erro ao atualizar administradores: {e}")
        return False

def get_administrator_ids() -> list:
    """
    Retorna apenas os IDs dos administradores ativos.

    Returns:
        list: Lista de IDs de administradores
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id FROM administrators
                WHERE is_active = 1
            """)
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar IDs de administradores: {e}")
        return []

def is_stored_administrator(user_id: int) -> bool:
    """
    Verifica se um usuário é administrador baseado no banco.

    Args:
        user_id: ID do usuário

    Returns:
        bool: True se é administrador ativo, False caso contrário
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM administrators
                WHERE user_id = ? AND is_active = 1
            """, (user_id,))
            return cursor.fetchone() is not None

    except sqlite3.Error as e:
        logger.error(f"Erro ao verificar se usuário {user_id} é administrador: {e}")
        return False

def get_administrator_info(user_id: int) -> dict:
    """
    Obtém informações detalhadas de um administrador.

    Args:
        user_id: ID do administrador

    Returns:
        dict: Informações do administrador ou None se não encontrado
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, last_name, status,
                       detected_at, last_updated, is_active
                FROM administrators
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    except sqlite3.Error as e:
        logger.error(f"Erro ao buscar informações do administrador {user_id}: {e}")
        return None
