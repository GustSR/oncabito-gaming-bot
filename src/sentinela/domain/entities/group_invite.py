"""
Group Invite Entity.

Representa um convite gerado para acesso ao grupo Gaming.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class GroupInvite:
    """
    Entidade que representa um convite de acesso ao grupo.

    Attributes:
        invite_id: ID único do convite
        user_id: ID do usuário no Telegram
        cpf: CPF do cliente
        invite_link: URL do link de convite
        created_at: Data/hora de criação
        expires_at: Data/hora de expiração
        used: Se o convite foi usado
        used_at: Data/hora que foi usado
        client_name: Nome do cliente
        plan_name: Nome do plano Gaming
    """

    invite_id: Optional[int]
    user_id: int
    cpf: str
    invite_link: str
    created_at: datetime
    expires_at: datetime
    used: bool = False
    used_at: Optional[datetime] = None
    client_name: Optional[str] = None
    plan_name: Optional[str] = None

    @classmethod
    def create(
        cls,
        user_id: int,
        cpf: str,
        invite_link: str,
        client_name: str,
        plan_name: str,
        duration_minutes: int = 30
    ) -> 'GroupInvite':
        """
        Cria um novo convite de grupo.

        Args:
            user_id: ID do usuário Telegram
            cpf: CPF do cliente
            invite_link: URL do convite gerado
            client_name: Nome do cliente
            plan_name: Nome do plano
            duration_minutes: Duração do convite em minutos (padrão 30)

        Returns:
            GroupInvite: Nova instância de convite
        """
        now = datetime.now()
        expires_at = now + timedelta(minutes=duration_minutes)

        return cls(
            invite_id=None,  # Será definido pelo banco
            user_id=user_id,
            cpf=cpf,
            invite_link=invite_link,
            created_at=now,
            expires_at=expires_at,
            used=False,
            used_at=None,
            client_name=client_name,
            plan_name=plan_name
        )

    def mark_as_used(self) -> None:
        """Marca o convite como usado."""
        self.used = True
        self.used_at = datetime.now()

    def is_expired(self) -> bool:
        """Verifica se o convite expirou."""
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Verifica se o convite ainda é válido (não usado e não expirado)."""
        return not self.used and not self.is_expired()

    def get_remaining_time(self) -> str:
        """Retorna tempo restante formatado."""
        if self.is_expired():
            return "Expirado"

        remaining = self.expires_at - datetime.now()
        minutes = int(remaining.total_seconds() / 60)

        if minutes < 1:
            return "Menos de 1 minuto"
        elif minutes == 1:
            return "1 minuto"
        else:
            return f"{minutes} minutos"
