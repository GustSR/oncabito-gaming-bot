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

            # OTIMIZAÇÃO: Busca detalhes do atendimento no HubSoft de forma mais eficiente
            # Tenta buscar com filtros mais específicos para reduzir dados transferidos
            result = await hubsoft_atendimento_client.get_atendimentos_paginado(
                pagina=0,
                itens_por_pagina=100,  # Aumentamos para reduzir chamadas múltiplas
                relacoes="atendimento_mensagem"  # Reduzimos relações desnecessárias
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

                    # Verifica se já existe um ticket similar no HubSoft para evitar duplicação
                    existing_ticket = await self._find_existing_hubsoft_ticket(
                        client_cpf=ticket['cpf'],
                        ticket_description=ticket['description'],
                        created_at=ticket['created_at']
                    )

                    if existing_ticket:
                        # Associa o ticket local com o existente no HubSoft
                        logger.info(f"Ticket local {ticket_id} correlacionado com ticket HubSoft existente {existing_ticket['id']}")

                        update_data = {
                            'hubsoft_atendimento_id': existing_ticket['id'],
                            'hubsoft_protocol': existing_ticket.get('protocolo'),
                            'sync_status': 'correlated',
                            'synced_at': datetime.now().isoformat()
                        }

                        success = update_ticket_with_hubsoft_data(ticket_id, update_data)

                        if success:
                            # Adiciona nota no HubSoft sobre a correlação
                            await hubsoft_atendimento_client.add_message_to_atendimento(
                                str(existing_ticket['id']),
                                f"🔗 CORRELAÇÃO AUTOMÁTICA:\n\n"
                                f"Este atendimento foi correlacionado com ticket local criado offline.\n\n"
                                f"• Protocolo local: LOC{ticket_id:06d}\n"
                                f"• Criado offline em: {ticket['created_at']}\n"
                                f"• Correlacionado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
                                f"📋 Dados do ticket local preservados."
                            )

                            results["success_count"] += 1
                        else:
                            results["failed_count"] += 1
                            results["errors"].append(f"Ticket {ticket_id}: Erro ao correlacionar com HubSoft")
                        continue

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
        Sincroniza status de todos os tickets ativos com o HubSoft de forma otimizada.

        OTIMIZAÇÃO: Busca todos os tickets em uma única chamada ao invés de
        uma chamada por ticket.

        Returns:
            Dict com resultado da sincronização
        """
        try:
            if not await self.check_hubsoft_health():
                return {"status": "error", "message": "HubSoft não está online"}

            from src.sentinela.clients.db_client import get_all_active_tickets_with_hubsoft_id
            from src.sentinela.integrations.hubsoft.atendimento import hubsoft_atendimento_client

            active_tickets = get_all_active_tickets_with_hubsoft_id()

            if not active_tickets:
                return {"status": "success", "message": "Nenhum ticket ativo para sincronizar"}

            # OTIMIZAÇÃO: Busca todos os atendimentos em lote ao invés de um por vez
            hubsoft_ids = [ticket['hubsoft_atendimento_id'] for ticket in active_tickets]
            logger.info(f"Sincronizando {len(active_tickets)} tickets ativos em lote...")

            results = {
                "total_tickets": len(active_tickets),
                "updated_count": 0,
                "unchanged_count": 0,
                "failed_count": 0,
                "api_calls_saved": len(active_tickets) - 1  # Economia de chamadas
            }

            # Busca todos os atendimentos em uma única chamada paginada
            all_hubsoft_tickets = {}
            page = 0
            while True:
                page_result = await hubsoft_atendimento_client.get_atendimentos_paginado(
                    pagina=page,
                    itens_por_pagina=100,  # Máximo por página
                    relacoes="atendimento_mensagem"
                )

                if page_result.get('status') != 'success':
                    break

                tickets_page = page_result.get('atendimentos', [])
                if not tickets_page:
                    break

                # Indexa tickets por ID para busca rápida
                for ticket in tickets_page:
                    ticket_id = str(ticket.get('id', ''))
                    if ticket_id in hubsoft_ids:
                        all_hubsoft_tickets[ticket_id] = ticket

                # Se encontrou todos os tickets necessários, para
                if len(all_hubsoft_tickets) >= len(hubsoft_ids):
                    break

                page += 1
                # Segurança: máximo 10 páginas para evitar loop infinito
                if page > 10:
                    break

            logger.info(f"Encontrados {len(all_hubsoft_tickets)} tickets no HubSoft de {len(hubsoft_ids)} buscados")

            # Atualiza tickets locais com dados do HubSoft
            from src.sentinela.clients.db_client import update_ticket_sync_status

            for ticket in active_tickets:
                hubsoft_id = str(ticket['hubsoft_atendimento_id'])

                if hubsoft_id in all_hubsoft_tickets:
                    hubsoft_ticket = all_hubsoft_tickets[hubsoft_id]

                    sync_data = {
                        'hubsoft_status': hubsoft_ticket.get('status', {}),
                        'last_sync': datetime.now().isoformat(),
                        'is_synced': True
                    }

                    success = update_ticket_sync_status(ticket['id'], sync_data)
                    if success:
                        results["updated_count"] += 1
                    else:
                        results["failed_count"] += 1
                else:
                    # Ticket não encontrado no HubSoft
                    results["failed_count"] += 1
                    logger.warning(f"Ticket {hubsoft_id} não encontrado no HubSoft durante sincronização em lote")

            logger.info(f"Sincronização em lote concluída: {results['updated_count']} atualizados, "
                       f"{results['api_calls_saved']} chamadas economizadas")
            return {"status": "completed", "results": results}

        except Exception as e:
            logger.error(f"Erro na sincronização de status em lote: {e}")
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

    async def _find_existing_hubsoft_ticket(self, client_cpf: str, ticket_description: str, created_at: str) -> Optional[Dict]:
        """
        Procura um ticket existente no HubSoft que possa corresponder ao ticket local.

        Args:
            client_cpf: CPF do cliente
            ticket_description: Descrição do ticket local
            created_at: Data de criação do ticket local

        Returns:
            Dict com dados do ticket HubSoft se encontrado, None caso contrário
        """
        try:
            from src.sentinela.integrations.hubsoft.atendimento import hubsoft_atendimento_client
            from datetime import datetime, timedelta

            # Busca atendimentos do cliente no HubSoft (últimos 7 dias)
            hubsoft_tickets = await hubsoft_atendimento_client.get_client_atendimentos(
                client_cpf=client_cpf,
                apenas_pendente=True
            )

            if not hubsoft_tickets:
                return None

            # Converte data de criação do ticket local para comparação
            try:
                local_created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                local_created = datetime.now()

            # Extrai palavras-chave da descrição para comparação
            local_keywords = set(ticket_description.lower().split())

            for hubsoft_ticket in hubsoft_tickets:
                try:
                    # Verifica se o ticket HubSoft foi criado em horário próximo (±24 horas)
                    hubsoft_created_str = hubsoft_ticket.get('data_cadastro', '')
                    if hubsoft_created_str:
                        hubsoft_created = datetime.fromisoformat(hubsoft_created_str.replace('Z', '+00:00'))
                        time_diff = abs((local_created - hubsoft_created).total_seconds())

                        # Se foram criados com mais de 24 horas de diferença, pula
                        if time_diff > 86400:  # 24 horas em segundos
                            continue

                    # Verifica similaridade do conteúdo
                    hubsoft_description = hubsoft_ticket.get('titulo', '') + ' ' + hubsoft_ticket.get('descricao', '')
                    hubsoft_keywords = set(hubsoft_description.lower().split())

                    # Calcula similaridade simples (palavras em comum)
                    common_keywords = local_keywords.intersection(hubsoft_keywords)
                    similarity = len(common_keywords) / max(len(local_keywords), 1)

                    # Se similaridade > 30% e criados no mesmo período, considera como correlação
                    if similarity > 0.3:
                        logger.info(f"Ticket correlacionado encontrado: HubSoft ID {hubsoft_ticket['id']}, similaridade: {similarity:.2%}")
                        return hubsoft_ticket

                except Exception as e:
                    logger.warning(f"Erro ao processar ticket HubSoft {hubsoft_ticket.get('id')}: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"Erro ao procurar ticket existente no HubSoft: {e}")
            return None

# Instância global do serviço
hubsoft_sync_service = HubSoftSyncService()