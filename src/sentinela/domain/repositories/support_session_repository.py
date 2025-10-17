"""
Repository interface para Support Sessions.

Define as operações de persistência para sessões de formulário de suporte.
Permite que o progresso do formulário seja salvo e recuperado mesmo após
reinicializações do bot.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime


class SupportSessionRepository(ABC):
    """
    Repository para operações com sessões de suporte.

    Uma sessão de suporte representa o progresso de um usuário
    preenchendo o formulário de abertura de ticket. O repositório
    permite persistir esse progresso no banco de dados.
    """

    @abstractmethod
    async def save_session(
        self,
        user_id: int,
        state_json: Dict[str, Any],
        current_step: str
    ) -> bool:
        """
        Salva ou atualiza uma sessão de formulário.

        Args:
            user_id: ID do Telegram do usuário
            state_json: Estado completo do formulário em formato dict
            current_step: Passo atual do formulário ('categoria', 'descricao', etc.)

        Returns:
            bool: True se salvou com sucesso, False caso contrário

        Exemplo de state_json:
            {
                "step": "descricao",
                "data": {
                    "categoria": "conectividade",
                    "descricao": "Ping alto em jogos"
                },
                "images": [],
                "started_at": "2025-10-13T10:30:00"
            }
        """
        pass

    @abstractmethod
    async def find_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera a sessão de formulário de um usuário.

        Args:
            user_id: ID do Telegram do usuário

        Returns:
            Optional[Dict[str, Any]]: Dados da sessão ou None se não existir

        Retorno esperado:
            {
                "user_id": 123456789,
                "state_json": {...},
                "current_step": "descricao",
                "created_at": "2025-10-13T10:30:00",
                "updated_at": "2025-10-13T10:35:00",
                "expires_at": "2025-10-14T10:35:00"
            }
        """
        pass

    @abstractmethod
    async def delete_session(self, user_id: int) -> bool:
        """
        Remove a sessão de formulário de um usuário.

        Chamado quando o usuário completa o formulário ou cancela.

        Args:
            user_id: ID do Telegram do usuário

        Returns:
            bool: True se removeu com sucesso, False se não encontrou
        """
        pass

    @abstractmethod
    async def session_exists(self, user_id: int) -> bool:
        """
        Verifica se existe uma sessão ativa para o usuário.

        Args:
            user_id: ID do Telegram do usuário

        Returns:
            bool: True se existe, False caso contrário
        """
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """
        Remove sessões que expiraram (24h de inatividade).

        Returns:
            int: Número de sessões removidas
        """
        pass

    @abstractmethod
    async def get_active_sessions_count(self) -> int:
        """
        Conta quantas sessões ativas existem no momento.

        Returns:
            int: Número de sessões ativas
        """
        pass

    @abstractmethod
    async def had_recent_expired_session(self, user_id: int, within_minutes: int = 5) -> bool:
        """
        Verifica se o usuário teve uma sessão expirada recentemente.

        Útil para fornecer feedback quando usuário tenta continuar
        uma sessão que expirou.

        Args:
            user_id: ID do Telegram do usuário
            within_minutes: Janela de tempo em minutos para considerar "recente"

        Returns:
            bool: True se houve expiração recente, False caso contrário
        """
        pass
