import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SyncStatus:
    """Status de sincronização de um ticket"""
    is_synced: bool
    last_sync_attempt: Optional[datetime] = None
    last_successful_sync: Optional[datetime] = None
    sync_error: Optional[str] = None
    hubsoft_id: Optional[str] = None
    hubsoft_protocol: Optional[str] = None
    local_protocol: Optional[str] = None

class HubSoftSyncService:
    """
    Serviço responsável pela sincronização bidirecional entre o sistema local
    e o HubSoft, incluindo status de tickets, recovery de tickets offline
    e monitoramento de conectividade.
    """

    def __init__(self):
        self._is_hubsoft_online = None
        self._last_health_check = None
        self._sync_in_progress = False
        self._failed_syncs = {}  # ticket_id -> retry_count

    async def check_hubsoft_health(self) -> bool:
        """
        Verifica se o HubSoft está online e funcionando.

        Returns:
            bool: True se HubSoft está acessível, False caso contrário
        """
        try:
            from src.sentinela.core.config import HUBSOFT_ENABLED
            if not HUBSOFT_ENABLED:
                return False

            from src.sentinela.integrations.hubsoft.atendimento import hubsoft_atendimento_client

            # Faz uma requisição simples para testar conectividade
            # Usamos o endpoint de listagem com limite mínimo para não sobrecarregar
            test_result = await hubsoft_atendimento_client.get_atendimentos_paginado(
                pagina=0,
                itens_por_pagina=1
            )

            is_online = test_result.get('status') == 'success'
            self._is_hubsoft_online = is_online
            self._last_health_check = datetime.now()

            if is_online:
                logger.info("HubSoft health check: ONLINE")
                # Se acabou de voltar online, trigger de sincronização
                await self._on_hubsoft_back_online()
            else:
                logger.warning("HubSoft health check: OFFLINE")

            return is_online

        except Exception as e:
            logger.error(f"Erro ao verificar health do HubSoft: {e}")
            self._is_hubsoft_online = False
            self._last_health_check = datetime.now()
            return False

    async def _on_hubsoft_back_online(self):
        """Executa ações quando HubSoft volta online"""
        try:
            logger.info("HubSoft voltou online - iniciando processo de recovery automático")

            # Inicia sincronização de tickets offline em background
            asyncio.create_task(self.sync_offline_tickets_to_hubsoft())

            # Atualiza status de todos os tickets ativos
            asyncio.create_task(self.sync_all_active_tickets_status())

        except Exception as e:
            logger.error(f"Erro no processo de recovery automático: {e}")

    async def sync_ticket_status_from_hubsoft(self, hubsoft_id: str) -> Optional[Dict[str, Any]]:
        """
        Sincroniza status de um ticket específico do HubSoft.

        Args:
            hubsoft_id: ID do atendimento no HubSoft

        Returns:
            Dict com dados atualizados do ticket ou None se erro
        """
        try:
            if not await self.check_hubsoft_health():
                return None

            from src.sentinela.integrations.hubsoft.atendimento import hubsoft_atendimento_client
            from src.sentinela.clients.db_client import get_ticket_by_hubsoft_id, update_ticket_sync_status

            # Busca detalhes do atendimento no HubSoft
            # Como não temos endpoint específico, usamos o endpoint geral
            result = await hubsoft_atendimento_client.get_atendimentos_paginado(
                pagina=0,
                itens_por_pagina=50,  # Busca mais tickets para encontrar o específico
                relacoes="atendimento_mensagem,cliente_servico"
            )

            if result.get('status') != 'success':
                return None

            # Encontra o ticket específico
            target_ticket = None
            for atendimento in result.get('atendimentos', []):
                if str(atendimento.get('id', '')) == str(hubsoft_id):
                    target_ticket = atendimento
                    break

            if not target_ticket:
                logger.warning(f"Ticket {hubsoft_id} não encontrado no HubSoft")
                return None

            # Atualiza dados locais
            ticket_data = get_ticket_by_hubsoft_id(hubsoft_id)
            if ticket_data:
                sync_data = {
                    'hubsoft_status': target_ticket.get('status', {}),
                    'last_sync': datetime.now().isoformat(),
                    'is_synced': True
                }

                # Atualiza no banco local
                update_ticket_sync_status(ticket_data['id'], sync_data)

                logger.info(f"Status do ticket {hubsoft_id} sincronizado com sucesso")
                return target_ticket

            return target_ticket

        except Exception as e:
            logger.error(f"Erro ao sincronizar status do ticket {hubsoft_id}: {e}")
            return None

    async def sync_offline_tickets_to_hubsoft(self) -> Dict[str, Any]:
        """
        Envia tickets criados offline para o HubSoft quando ele volta online.

        Returns:
            Dict com resultado da sincronização
        """
        if self._sync_in_progress:
            return {"status": "already_running", "message": "Sincronização já em andamento"}

        try:
            self._sync_in_progress = True

            if not await self.check_hubsoft_health():
                return {"status": "error", "message": "HubSoft não está online"}

            from src.sentinela.clients.db_client import get_offline_tickets, update_ticket_with_hubsoft_data
            from src.sentinela.integrations.hubsoft.atendimento import hubsoft_atendimento_client

            # Busca tickets offline (sem hubsoft_atendimento_id)
            offline_tickets = get_offline_tickets()

            if not offline_tickets:
                return {"status": "success", "message": "Nenhum ticket offline para sincronizar"}

            results = {
                "total_tickets": len(offline_tickets),
                "success_count": 0,
                "failed_count": 0,
                "errors": []
            }

            logger.info(f"Iniciando sincronização de {len(offline_tickets)} tickets offline")

            for ticket in offline_tickets:
                try:
                    ticket_id = ticket['id']

                    # Reconstrói dados do ticket para HubSoft
                    ticket_data = {
                        'user_id': ticket['user_id'],
                        'username': ticket['username'],
                        'category': ticket['category'],
                        'affected_game': ticket['affected_game'],
                        'problem_started': ticket['problem_started'],
                        'description': ticket['description'],
                        'urgency_level': ticket['urgency_level']
                    }

                    # Tenta criar no HubSoft
                    hubsoft_response = await hubsoft_atendimento_client.create_atendimento(
                        client_cpf=ticket['cpf'],
                        ticket_data=ticket_data
                    )

                    if hubsoft_response and hubsoft_response.get('id_atendimento'):
                        hubsoft_id = hubsoft_response['id_atendimento']
                        hubsoft_protocol = hubsoft_response.get('protocolo')

                        # Atualiza ticket local com dados do HubSoft
                        update_data = {
                            'hubsoft_atendimento_id': hubsoft_id,
                            'hubsoft_protocol': hubsoft_protocol,
                            'sync_status': 'synced',
                            'synced_at': datetime.now().isoformat()
                        }

                        success = update_ticket_with_hubsoft_data(ticket_id, update_data)

                        if success:
                            # Adiciona contexto histórico no HubSoft
                            local_protocol = f"LOC{ticket_id:06d}"
                            await hubsoft_atendimento_client.add_message_to_atendimento(
                                str(hubsoft_id),
                                f"🔄 SINCRONIZAÇÃO AUTOMÁTICA:\n\n"
                                f"Este atendimento foi criado offline durante indisponibilidade do sistema.\n\n"
                                f"• Protocolo local original: {local_protocol}\n"
                                f"• Criado em: {ticket['created_at']}\n"
                                f"• Sincronizado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
                                f"📋 Dados preservados integralmente na sincronização."
                            )

                            results["success_count"] += 1
                            logger.info(f"Ticket {ticket_id} sincronizado: {local_protocol} → {hubsoft_protocol}")
                        else:
                            results["failed_count"] += 1
                            results["errors"].append(f"Ticket {ticket_id}: Erro ao atualizar dados locais")
                    else:
                        results["failed_count"] += 1
                        results["errors"].append(f"Ticket {ticket_id}: Falha na criação no HubSoft")

                        # Incrementa contador de falhas para retry posterior
                        self._failed_syncs[ticket_id] = self._failed_syncs.get(ticket_id, 0) + 1

                except Exception as e:
                    results["failed_count"] += 1
                    error_msg = f"Ticket {ticket.get('id', 'N/A')}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(f"Erro ao sincronizar ticket {ticket.get('id')}: {e}")

            logger.info(f"Sincronização concluída: {results['success_count']} sucessos, {results['failed_count']} falhas")
            return {"status": "completed", "results": results}

        except Exception as e:
            logger.error(f"Erro geral na sincronização de tickets offline: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            self._sync_in_progress = False

    async def sync_all_active_tickets_status(self) -> Dict[str, Any]:
        """
        Sincroniza status de todos os tickets ativos com o HubSoft.

        Returns:
            Dict com resultado da sincronização
        """
        try:
            if not await self.check_hubsoft_health():
                return {"status": "error", "message": "HubSoft não está online"}

            from src.sentinela.clients.db_client import get_all_active_tickets_with_hubsoft_id

            active_tickets = get_all_active_tickets_with_hubsoft_id()

            if not active_tickets:
                return {"status": "success", "message": "Nenhum ticket ativo para sincronizar"}

            results = {
                "total_tickets": len(active_tickets),
                "updated_count": 0,
                "unchanged_count": 0,
                "failed_count": 0
            }

            for ticket in active_tickets:
                hubsoft_id = ticket['hubsoft_atendimento_id']
                updated_data = await self.sync_ticket_status_from_hubsoft(hubsoft_id)

                if updated_data:
                    results["updated_count"] += 1
                else:
                    results["failed_count"] += 1

            logger.info(f"Sincronização de status concluída: {results['updated_count']} atualizados")
            return {"status": "completed", "results": results}

        except Exception as e:
            logger.error(f"Erro na sincronização de status: {e}")
            return {"status": "error", "message": str(e)}

    async def get_sync_status_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo do status de sincronização do sistema.

        Returns:
            Dict com informações de status
        """
        try:
            from src.sentinela.clients.db_client import get_sync_statistics

            stats = get_sync_statistics()
            health_status = await self.check_hubsoft_health()

            return {
                "hubsoft_online": health_status,
                "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
                "sync_in_progress": self._sync_in_progress,
                "failed_syncs": len(self._failed_syncs),
                "statistics": stats
            }

        except Exception as e:
            logger.error(f"Erro ao obter status de sincronização: {e}")
            return {"error": str(e)}

    async def force_ticket_sync(self, ticket_id: int) -> Dict[str, Any]:
        """
        Força sincronização de um ticket específico.

        Args:
            ticket_id: ID do ticket local

        Returns:
            Dict com resultado da operação
        """
        try:
            from src.sentinela.clients.db_client import get_ticket_by_id

            ticket = get_ticket_by_id(ticket_id)
            if not ticket:
                return {"status": "error", "message": "Ticket não encontrado"}

            hubsoft_id = ticket.get('hubsoft_atendimento_id')

            if hubsoft_id:
                # Ticket já tem ID do HubSoft - atualiza status
                updated_data = await self.sync_ticket_status_from_hubsoft(hubsoft_id)
                if updated_data:
                    return {"status": "success", "message": "Status sincronizado", "data": updated_data}
                else:
                    return {"status": "error", "message": "Falha na sincronização de status"}
            else:
                # Ticket offline - tenta sincronizar para HubSoft
                sync_result = await self.sync_offline_tickets_to_hubsoft()
                return sync_result

        except Exception as e:
            logger.error(f"Erro ao forçar sincronização do ticket {ticket_id}: {e}")
            return {"status": "error", "message": str(e)}

# Instância global do serviço
hubsoft_sync_service = HubSoftSyncService()