from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class BaseERPIntegration(ABC):
    """Interface base para integrações com sistemas ERP"""

    @abstractmethod
    async def get_client_data(self, cpf: str) -> Optional[Dict[str, Any]]:
        """Busca dados do cliente por CPF"""
        pass

    @abstractmethod
    async def create_atendimento(self, client_cpf: str, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um novo atendimento"""
        pass

    @abstractmethod
    async def get_client_atendimentos(self, client_cpf: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Consulta atendimentos do cliente"""
        pass

    @abstractmethod
    async def add_message_to_atendimento(self, atendimento_id: str, message: str) -> bool:
        """Adiciona mensagem ao atendimento"""
        pass

    @abstractmethod
    async def update_atendimento_status(self, atendimento_id: str, status: str) -> bool:
        """Atualiza status do atendimento"""
        pass