"""
Welcome Message Value Object.

Representa mensagens de boas-vindas configuráveis
com templates e formatação.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class WelcomeMessageType(Enum):
    """Tipos de mensagem de boas-vindas."""

    INITIAL_WELCOME = "initial_welcome"      # Primeira mensagem ao entrar
    RULES_REMINDER = "rules_reminder"        # Lembrete de regras
    RULES_ACCEPTED = "rules_accepted"        # Confirmação de aceitação
    ACCESS_GRANTED = "access_granted"        # Acesso liberado
    WARNING_EXPIRING = "warning_expiring"    # Aviso de expiração próxima


@dataclass(frozen=True)
class WelcomeMessage:
    """
    Value Object representando mensagem de boas-vindas.

    Attributes:
        message_type: Tipo da mensagem
        text: Texto da mensagem (pode conter placeholders)
        parse_mode: Modo de parse (HTML, Markdown)
        topic_id: ID do tópico onde enviar (opcional)
        has_button: Se tem botão inline
        button_text: Texto do botão (se has_button=True)
        button_callback: Callback data do botão
    """

    message_type: WelcomeMessageType
    text: str
    parse_mode: str = "HTML"
    topic_id: Optional[int] = None
    has_button: bool = False
    button_text: Optional[str] = None
    button_callback: Optional[str] = None

    def format_for_user(
        self,
        user_mention: str,
        username: str,
        **kwargs
    ) -> str:
        """
        Formata mensagem para usuário específico.

        Args:
            user_mention: Menção HTML/Markdown do usuário
            username: Nome do usuário
            **kwargs: Outros placeholders opcionais

        Returns:
            str: Mensagem formatada
        """
        formatted = self.text

        # Substitui placeholders padrão
        formatted = formatted.replace("{user_mention}", user_mention)
        formatted = formatted.replace("{username}", username)

        # Substitui placeholders adicionais
        for key, value in kwargs.items():
            formatted = formatted.replace(f"{{{key}}}", str(value))

        return formatted

    @staticmethod
    def create_initial_welcome(
        welcome_topic_id: Optional[int] = None
    ) -> 'WelcomeMessage':
        """
        Cria mensagem de boas-vindas inicial.

        Args:
            welcome_topic_id: ID do tópico de boas-vindas

        Returns:
            WelcomeMessage: Mensagem configurada
        """
        text = (
            "🎮 <b>Olá, {user_mention}! Seja muito bem-vindo(a) à Comunidade OnCabo Gaming!</b> 🔥\n\n"
            "Que alegria ter você aqui com a gente! 🎉\n\n"
            "📋 <b>PRÓXIMO PASSO IMPORTANTE:</b>\n\n"
            "Por favor, vá até o tópico \"<b>📋 Regras da Comunidade</b>\" e:\n"
            "1️⃣ Leia nossas regras com atenção\n"
            "2️⃣ Clique no botão \"<b>✅ Li e aceito as regras</b>\"\n\n"
            "⏰ Você tem <b>24 horas</b> para aceitar\n"
            "⚠️ Sem aceitar, você será removido automaticamente\n\n"
            "🚀 <b>Aproveite a comunidade! Bons jogos!</b> 🎯"
        )

        return WelcomeMessage(
            message_type=WelcomeMessageType.INITIAL_WELCOME,
            text=text,
            parse_mode="HTML",
            topic_id=welcome_topic_id,
            has_button=False
        )

    @staticmethod
    def create_rules_reminder(
        rules_topic_id: int,
        user_id: int
    ) -> 'WelcomeMessage':
        """
        Cria mensagem de lembrete de regras.

        Args:
            rules_topic_id: ID do tópico de regras
            user_id: ID do usuário (para callback)

        Returns:
            WelcomeMessage: Mensagem configurada
        """
        text = (
            "📋 <b>{user_mention}, leia as regras acima com atenção!</b>\n\n"
            "Sua permanência no grupo depende da aceitação das regras.\n\n"
            "⏰ <b>Prazo:</b> 24 horas\n"
            "👇 <b>Após ler, clique no botão:</b>"
        )

        return WelcomeMessage(
            message_type=WelcomeMessageType.RULES_REMINDER,
            text=text,
            parse_mode="HTML",
            topic_id=rules_topic_id,
            has_button=True,
            button_text="✅ Li e aceito as regras da comunidade",
            button_callback=f"accept_rules_{user_id}"
        )

    @staticmethod
    def create_rules_accepted() -> 'WelcomeMessage':
        """
        Cria mensagem de confirmação de regras aceitas.

        Returns:
            WelcomeMessage: Mensagem configurada
        """
        text = (
            "✅ <b>{user_mention} aceitou as regras!</b>\n\n"
            "🎮 <b>Bem-vindo(a) oficial à Comunidade Gamer OnCabo!</b>\n"
            "🔥 <b>Aproveite e divirta-se com a galera!</b> 🎯"
        )

        return WelcomeMessage(
            message_type=WelcomeMessageType.RULES_ACCEPTED,
            text=text,
            parse_mode="HTML",
            has_button=False
        )

    @staticmethod
    def create_access_granted() -> str:
        """
        Cria texto de notificação de acesso liberado.

        Returns:
            str: Texto da notificação
        """
        return "✅ Regras aceitas! Acesso liberado aos tópicos de gaming!"

    @staticmethod
    def create_access_pending() -> str:
        """
        Cria texto de notificação de acesso pendente.

        Returns:
            str: Texto da notificação
        """
        return "✅ Regras aceitas! Aguarde liberação do acesso pelos administradores."

    @staticmethod
    def create_unauthorized_button() -> str:
        """
        Cria texto de erro para botão não autorizado.

        Returns:
            str: Texto de erro
        """
        return "❌ Este botão não é para você!"
