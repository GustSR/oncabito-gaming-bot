import os
import logging
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env localizado na raiz do projeto
load_dotenv()

def get_env_var(key: str, default: str | None = None) -> str | None:
    """
    Obtém uma variável de ambiente, remove aspas extras e garante a barra no final de URLs.
    """
    value = os.getenv(key, default)
    if value:
        cleaned_value = value.strip('\'"')
        if key.endswith('_HOST') and cleaned_value and not cleaned_value.endswith('/'):
            cleaned_value += '/'
        return cleaned_value
    return value


# --- Configurações do Bot Telegram ---
TELEGRAM_TOKEN = get_env_var("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("A variável de ambiente TELEGRAM_TOKEN não foi definida no arquivo .env")

# --- Configurações do Grupo/Canal ---
TELEGRAM_GROUP_ID = get_env_var("TELEGRAM_GROUP_ID")
if not TELEGRAM_GROUP_ID:
    raise ValueError("A variável de ambiente TELEGRAM_GROUP_ID não foi definida no arquivo .env")

# --- Configurações de Tópicos ---
RULES_TOPIC_ID = get_env_var("RULES_TOPIC_ID")  # ID do tópico de regras (opcional)
WELCOME_TOPIC_ID = get_env_var("WELCOME_TOPIC_ID")  # ID do tópico de boas-vindas (opcional)
SUPPORT_TOPIC_ID = get_env_var("SUPPORT_TOPIC_ID", "148")  # ID do tópico de suporte (🆘 Suporte Gamer)

# --- Configurações de Notificações ---
TECH_NOTIFICATION_CHANNEL_ID = get_env_var("TECH_NOTIFICATION_CHANNEL_ID")  # Canal técnico

# Valida configuração do canal técnico
if not TECH_NOTIFICATION_CHANNEL_ID:
    logger = logging.getLogger(__name__)
    logger.warning("TECH_NOTIFICATION_CHANNEL_ID não configurado - notificações técnicas desabilitadas")

# --- Configurações do Link de Convite ---
INVITE_LINK_EXPIRE_TIME = int(get_env_var("INVITE_LINK_EXPIRE_TIME", "3600"))  # 1 hora por padrão
INVITE_LINK_MEMBER_LIMIT = int(get_env_var("INVITE_LINK_MEMBER_LIMIT", "1"))  # 1 uso por padrão

# --- Configurações da API Externa (ERP) ---
# Removido ERP_API_KEY - não é usado, pois a autenticação é via OAuth com HubSoft

# --- Configurações do Banco de Dados ---
DATABASE_FILE = get_env_var("DATABASE_FILE", "data/database/sentinela.db")

# --- Configurações da API Hubsoft ---
HUBSOFT_HOST = get_env_var("HUBSOFT_HOST")
HUBSOFT_CLIENT_ID = get_env_var("HUBSOFT_CLIENT_ID")
HUBSOFT_CLIENT_SECRET = get_env_var("HUBSOFT_CLIENT_SECRET")
HUBSOFT_USER = get_env_var("HUBSOFT_USER")
HUBSOFT_PASSWORD = get_env_var("HUBSOFT_PASSWORD")

# Determina se a integração HubSoft está habilitada
HUBSOFT_ENABLED = get_env_var("HUBSOFT_ENABLED", "true").lower() in ("true", "1", "yes", "on")

# Valida configuração HubSoft apenas se habilitado
if HUBSOFT_ENABLED:
    missing_vars = []
    required_vars = {
        "HUBSOFT_HOST": HUBSOFT_HOST,
        "HUBSOFT_CLIENT_ID": HUBSOFT_CLIENT_ID,
        "HUBSOFT_CLIENT_SECRET": HUBSOFT_CLIENT_SECRET,
        "HUBSOFT_USER": HUBSOFT_USER,
        "HUBSOFT_PASSWORD": HUBSOFT_PASSWORD
    }

    for var_name, var_value in required_vars.items():
        if not var_value:
            missing_vars.append(var_name)

    if missing_vars:
        logger = logging.getLogger(__name__)
        logger.warning(f"Integração HubSoft DESABILITADA - Variáveis ausentes: {', '.join(missing_vars)}")
        logger.warning("Bot funcionará apenas com tickets locais. Para habilitar HubSoft, configure todas as variáveis necessárias.")
        HUBSOFT_ENABLED = False
    else:
        logger = logging.getLogger(__name__)
        logger.info("Integração HubSoft HABILITADA - Todas as credenciais configuradas")
else:
    logger = logging.getLogger(__name__)
    logger.info("Integração HubSoft DESABILITADA via configuração (HUBSOFT_ENABLED=false)")

# --- Informações de Contato OnCabo ---
ONCABO_SITE_URL = get_env_var("ONCABO_SITE_URL", "https://www.oncabo.com.br")
ONCABO_WHATSAPP_URL = get_env_var("ONCABO_WHATSAPP_URL", "https://wa.me/5511999999999")
