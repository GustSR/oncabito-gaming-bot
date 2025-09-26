import logging

# Em breve, estes módulos serão importados para uso real
# from src.sentinela.clients import db_client
# from src.sentinela.integrations.hubsoft import cliente as hubsoft_cliente
# from src.sentinela.core.config import TELEGRAM_GROUP_ID
# from src.sentinela.bot.bot_instance import application

logger = logging.getLogger(__name__)

def verify_and_remove_inactive_users():
    """
    Orquestra a rotina de verificação de usuários inativos.

    1. Busca todos os usuários ativos no banco de dados.
    2. Para cada usuário, verifica o status do contrato no ERP.
    3. Se o contrato estiver inativo, remove o usuário do grupo e o desativa no DB.
    """
    logger.info("--- INICIANDO ROTINA DE VERIFICAÇÃO DE USUÁRIOS INATIVOS ---")

    # Passo 1: Buscar usuários ativos no banco de dados (simulação)
    # active_users = db_client.get_active_users()
    active_users = []  # SIMULAÇÃO: Nenhum usuário no DB por enquanto
    logger.info(f"Encontrados {len(active_users)} usuários ativos para verificação.")

    if not active_users:
        logger.info("Nenhum usuário ativo para verificar. Rotina encerrada.")
        return

    for user in active_users:
        user_id = user['user_id']
        cpf = user['cpf']
        logger.info(f"Verificando usuário ID: {user_id}...")

        # Passo 2: Verificar status do contrato no ERP (simulação)
        # is_contract_active = erp_client.check_contract_status(cpf)
        is_contract_active = False  # SIMULAÇÃO: Contrato se tornou inativo

        if is_contract_active:
            logger.info(f"Usuário ID: {user_id} continua com contrato ativo.")
            continue
        
        logger.warning(f"Contrato INATIVO para o usuário ID: {user_id}. Iniciando processo de remoção.")
        
        # Passo 3a: Remover usuário do grupo (simulação)
        try:
            # await application.bot.kick_chat_member(chat_id=TELEGRAM_GROUP_ID, user_id=user_id)
            logger.info(f"(Simulação) Usuário ID: {user_id} removido do grupo do Telegram.")
        except Exception as e:
            logger.error(f"Falha ao remover usuário ID: {user_id} do grupo. Erro: {e}")
            continue  # Pula para o próximo usuário se a remoção falhar
        
        # Passo 3b: Marcar como inativo no banco de dados (simulação)
        # db_client.deactivate_user(user_id)
        logger.info(f"(Simulação) Usuário ID: {user_id} marcado como inativo no banco de dados.")

    logger.info("--- ROTINA DE VERIFICAÇÃO DE USUÁRIOS INATIVOS CONCLUÍDA ---")
