import logging
from src.sentinela.clients import erp_client
from src.sentinela.clients.db_client import save_user_data
from src.sentinela.services.invite_service import create_temporary_invite_link
from src.sentinela.services.client_info_service import format_client_service_info
from src.sentinela.services.group_service import is_user_in_group

logger = logging.getLogger(__name__)

async def process_user_verification(cpf: str, user_id: int, username: str) -> str:
    """
    Orquestra o processo de verificação de um usuário.

    1. Verifica se já está no grupo
    2. Busca dados completos do cliente via API
    3. Salva dados no banco para checkups futuros
    4. Cria link temporário se necessário
    """
    logger.info(f"Iniciando processo de verificação para o usuário {username} (ID: {user_id}).")

    # Passo 1: Verificar se já está no grupo
    logger.info(f"Verificando se usuário {user_id} já está no grupo...")
    is_already_member = await is_user_in_group(user_id)

    if is_already_member:
        logger.info(f"Usuário {user_id} já está no grupo.")
        return (
            f"🎮 <b>VOCÊ JÁ ESTÁ NA COMUNIDADE!</b> 🎮\n\n"
            f"✅ Detectamos que você já faz parte do <b>Grupo Gamer OnCabo</b>!\n\n"
            f"🔥 <b>APROVEITE TODOS OS BENEFÍCIOS:</b>\n"
            f"• Dicas exclusivas de gaming\n"
            f"• Suporte prioritário\n"
            f"• Promoções especiais\n"
            f"• Comunidade de gamers\n\n"
            f"🚀 <b>Continue aproveitando sua experiência gamer com a OnCabo!</b>\n\n"
            f"💬 Caso tenha alguma dúvida, fale diretamente no grupo."
        )

    # Passo 2: Buscar dados completos do cliente
    logger.info(f"Buscando dados do cliente via API Hubsoft...")
    client_data = erp_client.get_client_data(cpf)

    if not client_data:
        logger.warning(f"Cliente não encontrado ou sem serviço ativo para o usuário {username} (ID: {user_id}).")
        return "❌ Não encontrei um contrato ativo para o CPF informado. Por favor, verifique os dados ou entre em contato com o suporte."

    logger.info(f"Cliente encontrado para o usuário {username} (ID: {user_id}).")

    # Passo 3: Salvar dados no banco para checkups futuros
    logger.info(f"Salvando dados do usuário no banco...")
    save_success = save_user_data(user_id, username or f"user_{user_id}", cpf, client_data)

    if save_success:
        logger.info(f"Dados salvos com sucesso para {username} (ID: {user_id})")
    else:
        logger.warning(f"Falha ao salvar dados para {username} (ID: {user_id})")

    # Passo 4: Tentar criar link temporário para o grupo da OnCabo
    logger.info(f"Criando link temporário para o grupo da OnCabo...")
    invite_link = await create_temporary_invite_link(user_id, username or f"user_{user_id}")

    if invite_link:
        # Sucesso - envia link
        logger.info(f"Link de convite criado com sucesso para {username} (ID: {user_id}).")

        return (
            f"🎮 <b>PARABÉNS, GAMER!</b> 🎮\n\n"
            f"✅ Seu contrato foi <b>verificado com sucesso</b>!\n\n"
            f"🔥 <b>ACESSO LIBERADO</b> para a Comunidade Gamer OnCabo!\n\n"
            f"🔗 <b>CLIQUE NO LINK ABAIXO:</b>\n{invite_link}\n\n"
            f"⚠️ <b>Importante:</b>\n"
            f"• Link temporário com validade limitada\n"
            f"• Use apenas uma vez\n"
            f"• Após entrar, você terá acesso permanente\n\n"
            f"🚀 <b>Bem-vindo à família OnCabo Gamer!</b>"
        )
    else:
        # Falha na criação do link - envia dados detalhados
        logger.warning(f"Falha ao criar link. Enviando dados detalhados para {username} (ID: {user_id}).")

        return format_client_service_info(client_data)
