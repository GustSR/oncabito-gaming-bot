"""
Configuração global de fixtures do pytest.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """
    Cria event loop para testes async.

    Necessário para testes que usam async/await.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_container():
    """
    Mock do DI Container.

    Retorna um container mockado com métodos .get() configuráveis.
    """
    container = MagicMock()
    container.get = MagicMock()
    return container


@pytest.fixture
def mock_telegram_update():
    """
    Mock de Update do python-telegram-bot.

    Simula uma mensagem/callback do Telegram.
    """
    update = MagicMock()

    # Mock do usuário
    user = MagicMock()
    user.id = 123456
    user.username = "test_user"
    user.first_name = "Test"
    user.mention_markdown.return_value = "[Test](tg://user?id=123456)"

    # Mock da mensagem
    message = MagicMock()
    message.reply_text = AsyncMock()
    message.text = "Test message"

    # Mock do chat
    chat = MagicMock()
    chat.id = 123456
    chat.type = "private"

    # Configura update
    update.effective_user = user
    update.message = message
    update.effective_chat = chat
    update.get_bot.return_value.create_chat_invite_link = AsyncMock()

    return update


@pytest.fixture
def mock_telegram_context():
    """
    Mock de ContextTypes.DEFAULT_TYPE.

    Simula o contexto do bot com user_data e job_queue.
    """
    context = MagicMock()
    context.user_data = {}
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()

    # Mock do job_queue
    job_queue = MagicMock()
    job_queue.run_once = MagicMock()
    job_queue.get_jobs_by_name = MagicMock(return_value=[])
    context.job_queue = job_queue

    return context


@pytest.fixture
def mock_user_repository():
    """
    Mock do UserRepository.

    Simula operações de repositório de usuários.
    """
    repo = AsyncMock()
    repo.find_by_telegram_id = AsyncMock()
    repo.save = AsyncMock()
    repo.exists = AsyncMock()
    return repo


@pytest.fixture
def mock_cpf_repository():
    """
    Mock do CPFVerificationRepository.

    Simula operações de repositório de verificações CPF.
    """
    repo = AsyncMock()
    repo.find_by_user_id = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def mock_cpf_use_case():
    """
    Mock do CPFVerificationUseCase.

    Simula operações de caso de uso de verificação CPF.
    """
    use_case = AsyncMock()
    use_case.start_verification = AsyncMock()
    use_case.submit_cpf = AsyncMock()
    use_case.check_user_active = AsyncMock()
    return use_case


@pytest.fixture
def mock_hubsoft_use_case():
    """
    Mock do HubSoftIntegrationUseCase.

    Simula operações de caso de uso de integração HubSoft.
    """
    use_case = AsyncMock()
    use_case.create_ticket = AsyncMock()
    use_case.get_user_active_tickets = AsyncMock()
    return use_case


@pytest.fixture
def mock_user_entity():
    """
    Mock de entidade User.

    Simula um usuário do domínio.
    """
    from src.sentinela.domain.entities.user import UserStatus

    user = MagicMock()
    user.id = MagicMock()
    user.id.value = 123456
    user.telegram_id = 123456
    user.username = "test_user"
    user.status = UserStatus.ACTIVE
    user.is_active.return_value = True
    user.can_create_ticket.return_value = True

    return user


@pytest.fixture
def mock_inactive_user_entity():
    """
    Mock de entidade User com status INACTIVE.

    Simula um usuário inativo (plano cancelado).
    """
    from src.sentinela.domain.entities.user import UserStatus

    user = MagicMock()
    user.id = MagicMock()
    user.id.value = 789012
    user.telegram_id = 789012
    user.username = "inactive_user"
    user.status = UserStatus.INACTIVE
    user.is_active.return_value = False
    user.can_create_ticket.return_value = False

    return user
