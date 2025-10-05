"""
Duplicate CPF Service.

Serviço de domínio para detectar e gerenciar CPFs duplicados.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..repositories.cpf_verification_repository import CPFVerificationRepository
from ..repositories.user_repository import UserRepository
from ..entities.cpf_verification import VerificationStatus

logger = logging.getLogger(__name__)


class DuplicateCPFService:
    """Serviço para detectar e gerenciar CPFs duplicados."""

    def __init__(
        self,
        verification_repository: CPFVerificationRepository,
        user_repository: UserRepository
    ):
        self.verification_repository = verification_repository
        self.user_repository = user_repository

    async def check_for_duplicates(
        self,
        cpf_hash: str,
        exclude_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verifica se existem duplicatas de CPF.

        Args:
            cpf_hash: Hash do CPF a ser verificado
            exclude_user_id: ID de usuário para excluir da busca

        Returns:
            Informações sobre duplicatas encontradas
        """
        try:
            # Busca verificações recentes com o mesmo CPF
            recent_verifications = await self._find_recent_verifications_by_cpf(
                cpf_hash, exclude_user_id
            )

            if not recent_verifications:
                return {
                    "has_duplicates": False,
                    "duplicate_count": 0,
                    "users": []
                }

            # Analisa duplicatas
            duplicate_users = []
            for verification in recent_verifications:
                duplicate_users.append({
                    "user_id": verification.user_id,
                    "username": verification.username,
                    "status": verification.status.value,
                    "created_at": verification.created_at.isoformat(),
                    "verification_id": verification.id.value
                })

            return {
                "has_duplicates": True,
                "duplicate_count": len(duplicate_users),
                "users": duplicate_users,
                "risk_level": self._calculate_risk_level(duplicate_users)
            }

        except Exception as e:
            logger.error(f"Erro ao verificar duplicatas: {e}")
            return {
                "has_duplicates": False,
                "error": str(e)
            }

    async def resolve_duplicate(
        self,
        primary_user_id: int,
        duplicate_user_ids: List[int],
        resolution_type: str = "merge"
    ) -> Dict[str, Any]:
        """
        Resolve conflito de CPF duplicado.

        Args:
            primary_user_id: ID do usuário principal
            duplicate_user_ids: IDs dos usuários duplicados
            resolution_type: Tipo de resolução (merge, block, manual)

        Returns:
            Resultado da resolução
        """
        try:
            if resolution_type == "merge":
                return await self._merge_duplicate_accounts(
                    primary_user_id, duplicate_user_ids
                )
            elif resolution_type == "block":
                return await self._block_duplicate_accounts(duplicate_user_ids)
            elif resolution_type == "manual":
                return await self._flag_for_manual_review(
                    primary_user_id, duplicate_user_ids
                )
            else:
                return {
                    "success": False,
                    "error": f"Tipo de resolução inválido: {resolution_type}"
                }

        except Exception as e:
            logger.error(f"Erro ao resolver duplicata: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_duplicate_statistics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Obtém estatísticas de duplicatas.

        Args:
            days: Período em dias para análise

        Returns:
            Estatísticas de duplicatas
        """
        try:
            since = datetime.now() - timedelta(days=days)

            # Busca todas as verificações do período
            all_verifications = []
            for status in VerificationStatus:
                verifications = await self.verification_repository.find_by_status(
                    status, limit=1000
                )
                all_verifications.extend([
                    v for v in verifications
                    if v.created_at >= since
                ])

            # Agrupa por CPF hash
            cpf_groups = {}
            for verification in all_verifications:
                cpf_hash = verification.cpf_hash
                if cpf_hash not in cpf_groups:
                    cpf_groups[cpf_hash] = []
                cpf_groups[cpf_hash].append(verification)

            # Identifica duplicatas
            duplicates = {
                cpf_hash: verifications
                for cpf_hash, verifications in cpf_groups.items()
                if len(verifications) > 1
            }

            return {
                "period_days": days,
                "total_verifications": len(all_verifications),
                "unique_cpfs": len(cpf_groups),
                "duplicate_cpfs": len(duplicates),
                "duplicate_rate": len(duplicates) / len(cpf_groups) * 100 if cpf_groups else 0,
                "most_duplicated": self._get_most_duplicated(duplicates)
            }

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {
                "error": str(e)
            }

    async def _find_recent_verifications_by_cpf(
        self,
        cpf_hash: str,
        exclude_user_id: Optional[int] = None,
        days: int = 30
    ) -> List:
        """Busca verificações recentes com o mesmo CPF."""
        since = datetime.now() - timedelta(days=days)

        # Como não temos busca por CPF hash implementada,
        # simula busca por todas as verificações e filtra
        all_verifications = []
        for status in VerificationStatus:
            verifications = await self.verification_repository.find_by_status(
                status, limit=1000
            )
            all_verifications.extend(verifications)

        # Filtra por CPF hash e usuário
        filtered_verifications = []
        for verification in all_verifications:
            if (verification.cpf_hash == cpf_hash and
                verification.created_at >= since and
                (exclude_user_id is None or verification.user_id != exclude_user_id)):
                filtered_verifications.append(verification)

        return filtered_verifications

    def _calculate_risk_level(self, duplicate_users: List[Dict[str, Any]]) -> str:
        """Calcula nível de risco baseado nas duplicatas."""
        count = len(duplicate_users)

        if count <= 1:
            return "low"
        elif count <= 3:
            return "medium"
        else:
            return "high"

    async def _merge_duplicate_accounts(
        self,
        primary_user_id: int,
        duplicate_user_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Desativa contas antigas e mantém a principal.

        A lógica de "merge" aqui é desativar os usuários antigos que tinham o CPF,
        permitindo que o novo usuário (primary_user_id) prossiga com a verificação.
        """
        from ...domain.value_objects.identifiers import UserId

        deactivated_count = 0
        errors = []

        logger.info(f"Iniciando merge de contas para CPF. Primária: {primary_user_id}, Duplicadas: {duplicate_user_ids}")

        for dup_id in duplicate_user_ids:
            try:
                user_to_deactivate = await self.user_repo.find_by_id(UserId(dup_id))
                if user_to_deactivate:
                    reason = f"CPF transferido para o usuário {primary_user_id}"
                    user_to_deactivate.deactivate(reason)
                    await self.user_repo.save(user_to_deactivate)
                    deactivated_count += 1
                    logger.info(f"Usuário {dup_id} desativado com sucesso.")
                else:
                    logger.warning(f"Usuário duplicado com ID {dup_id} não encontrado para desativação.")
            except Exception as e:
                error_msg = f"Erro ao desativar usuário duplicado {dup_id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        if errors:
            return {
                "success": False,
                "action": "merge",
                "primary_user_id": primary_user_id,
                "deactivated_accounts": deactivated_count,
                "error": "Ocorreram erros ao desativar as contas antigas.",
                "error_details": errors
            }

        return {
            "success": True,
            "action": "merge",
            "primary_user_id": primary_user_id,
            "deactivated_accounts": deactivated_count,
            "message": "Contas antigas desativadas com sucesso."
        }

    async def _block_duplicate_accounts(
        self,
        duplicate_user_ids: List[int]
    ) -> Dict[str, Any]:
        """Simula bloqueio de contas duplicadas."""
        # TODO: Implementar lógica real de bloqueio
        logger.warning(f"Blocking duplicate accounts: {duplicate_user_ids}")

        return {
            "success": True,
            "action": "block",
            "blocked_accounts": len(duplicate_user_ids),
            "message": "Contas bloqueadas com sucesso (simulado)"
        }

    async def _flag_for_manual_review(
        self,
        primary_user_id: int,
        duplicate_user_ids: List[int]
    ) -> Dict[str, Any]:
        """Simula marcação para revisão manual."""
        # TODO: Implementar sistema de flags
        logger.info(f"Flagging for manual review: primary={primary_user_id}, duplicates={duplicate_user_ids}")

        return {
            "success": True,
            "action": "manual_review",
            "flagged_accounts": len(duplicate_user_ids) + 1,
            "message": "Marcado para revisão manual (simulado)"
        }

    def _get_most_duplicated(self, duplicates: Dict[str, List]) -> Optional[Dict[str, Any]]:
        """Obtém o CPF com mais duplicatas."""
        if not duplicates:
            return None

        most_duplicated_cpf = max(duplicates.keys(), key=lambda k: len(duplicates[k]))
        verifications = duplicates[most_duplicated_cpf]

        return {
            "cpf_hash": most_duplicated_cpf,
            "duplicate_count": len(verifications),
            "user_ids": [v.user_id for v in verifications]
        }