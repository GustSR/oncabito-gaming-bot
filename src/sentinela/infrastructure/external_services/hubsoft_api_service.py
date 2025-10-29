"""
HubSoft API Service Implementation.

Implementa comunicação real com a API do HubSoft,
incluindo autenticação, rate limiting e cache.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import aiohttp
import hashlib
import json

from ...domain.repositories.hubsoft_repository import (
    HubSoftAPIRepository,
    HubSoftCacheRepository,
    HubSoftAPIError
)
from ...integrations.hubsoft.rate_limiter import HubSoftRateLimiter
from ...integrations.hubsoft.token_manager import HubSoftTokenManager
from ...integrations.hubsoft.cache_manager import HubSoftCacheManager

logger = logging.getLogger(__name__)


class HubSoftAPIService(HubSoftAPIRepository):
    """Implementação do serviço de API HubSoft."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        rate_limiter: Optional[HubSoftRateLimiter] = None,
        token_manager: Optional[HubSoftTokenManager] = None,
        timeout_seconds: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds

        # Componentes auxiliares
        self.rate_limiter = rate_limiter or HubSoftRateLimiter()
        self.token_manager = token_manager or HubSoftTokenManager()

        # Session HTTP reutilizável
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtém session HTTP reutilizável."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'OnCabo-Sentinela/1.0'
                }
            )
        return self._session

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        authenticated: bool = True
    ) -> Dict[str, Any]:
        """Faz requisição para a API HubSoft."""

        # Rate limiting
        await self.rate_limiter.wait_for_rate_limit()

        try:
            session = await self._get_session()
            url = f"{self.base_url}/{endpoint.lstrip('/')}"

            # Headers da requisição
            headers = {}

            if authenticated:
                token = self.token_manager.get_access_token()
                if not token:
                    # Faz login se necessário
                    token = await self._authenticate()

                headers['Authorization'] = f'Bearer {token}'

            # Faz a requisição
            async with session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers
            ) as response:

                # Verifica rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    await self.rate_limiter.handle_rate_limit(retry_after)
                    raise HubSoftAPIError(
                        "Rate limit exceeded",
                        status_code=429,
                        error_code="rate_limit_exceeded"
                    )

                # Lê resposta
                try:
                    response_data = await response.json()
                except:
                    response_data = {"text": await response.text()}

                # Verifica se houve erro
                if not response.ok:
                    error_message = response_data.get('message', f'HTTP {response.status}')
                    error_code = response_data.get('error_code', 'api_error')

                    raise HubSoftAPIError(
                        error_message,
                        status_code=response.status,
                        error_code=error_code,
                        details=response_data
                    )

                return response_data

        except aiohttp.ClientError as e:
            raise HubSoftAPIError(
                f"Connection error: {str(e)}",
                error_code="connection_error"
            )
        except asyncio.TimeoutError:
            raise HubSoftAPIError(
                "Request timeout",
                error_code="timeout"
            )

    async def _authenticate(self) -> str:
        """Faz autenticação na API HubSoft."""
        try:
            auth_data = {
                "username": self.username,
                "password": self.password
            }

            response = await self._make_request(
                "POST",
                "/auth/login",
                data=auth_data,
                authenticated=False
            )

            token = response.get('access_token')
            if not token:
                raise HubSoftAPIError("No access token in response")

            # Armazena token
            expires_in = response.get('expires_in', 3600)
            await self.token_manager.store_token(token, expires_in)

            logger.info("Autenticação HubSoft realizada com sucesso")
            return token

        except Exception as e:
            logger.error(f"Erro na autenticação HubSoft: {e}")
            raise HubSoftAPIError(f"Authentication failed: {str(e)}")

    async def verify_client_by_cpf(
        self,
        cpf: str,
        include_contracts: bool = True
    ) -> Dict[str, Any]:
        """Verifica cliente no HubSoft por CPF."""
        try:
            params = {
                "busca": "cpf_cnpj",
                "termo_busca": cpf,
                "incluir_contrato": "sim" if include_contracts else "nao",  # API espera "sim"/"nao", não "true"/"false"
                "servico_status": "servico_habilitado"
            }

            response = await self._make_request(
                "GET",
                "/api/v1/integracao/cliente",
                params=params
            )

            logger.info(f"Cliente verificado: CPF={cpf[:3]}***{cpf[-2:]}")
            return response

        except Exception as e:
            logger.error(f"Erro ao verificar cliente: {e}")
            raise

    async def create_ticket(
        self,
        ticket_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cria atendimento no HubSoft via endpoint correto.

        Args:
            ticket_data: Dados do atendimento contendo:
                - id_cliente_servico (int): ID do serviço do cliente (obrigatório)
                - descricao (str): Descrição detalhada (obrigatório)
                - nome (str): Nome do solicitante (obrigatório)
                - telefone (str): Telefone no formato DDNNNNNNNNN (obrigatório)
                - email (str): Email do solicitante (opcional)
                - id_tipo_atendimento (int): Tipo de atendimento (opcional, padrão SAC)
                - id_atendimento_status (int): Status inicial (opcional)
                - parametros (dict): Parâmetros dinâmicos (opcional)

        Returns:
            Dict contendo response da API com protocolo e id_atendimento
        """
        try:
            response = await self._make_request(
                "POST",
                "/api/v1/integracao/atendimento",
                data=ticket_data
            )

            # Extrai protocolo e ID do atendimento criado
            atendimento = response.get('atendimento', {})
            protocolo = atendimento.get('protocolo')
            id_atendimento = atendimento.get('id_atendimento')

            logger.info(f"Atendimento criado no HubSoft: protocolo={protocolo}, id={id_atendimento}")
            return response

        except Exception as e:
            logger.error(f"Erro ao criar atendimento no HubSoft: {e}")
            raise

    async def get_user_tickets(
        self,
        cpf: str,
        include_closed: bool = True,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca atendimentos de um cliente por CPF.

        Args:
            cpf: CPF do cliente (formatado ou não)
            include_closed: Se True, inclui atendimentos fechados/resolvidos
            limit: Limite de resultados (padrão: 20)

        Returns:
            Lista de atendimentos do cliente
        """
        try:
            # Formata CPF (remove caracteres especiais)
            formatted_cpf = ''.join(filter(str.isdigit, cpf))

            # Monta parâmetros da requisição
            params = {
                "busca": "cpf_cnpj",
                "termo_busca": formatted_cpf,
                "apenas_pendente": "nao" if include_closed else "sim",
                "limit": limit or 20
            }

            logger.info(
                f"Buscando atendimentos para CPF {formatted_cpf[:3]}*** "
                f"(include_closed={include_closed}, limit={params['limit']})"
            )

            # Chama endpoint de consulta de atendimentos
            response = await self._make_request(
                "GET",
                "/api/v1/integracao/cliente/atendimento",
                params=params
            )

            # Processa resposta da API
            # A API retorna "success" (não "suscess" como estava na documentação antiga)
            if response.get('status') == 'success' and response.get('atendimentos'):
                atendimentos = response['atendimentos']
                logger.info(f"Encontrados {len(atendimentos)} atendimentos para CPF {formatted_cpf[:3]}***")

                # Mapeia campos da API HubSoft para campos esperados pelo bot
                mapped_tickets = []
                for atendimento in atendimentos:
                    mapped_ticket = self._map_hubsoft_ticket_to_internal(atendimento)
                    mapped_tickets.append(mapped_ticket)

                return mapped_tickets

            # Nenhum atendimento encontrado
            logger.info(f"Nenhum atendimento encontrado para CPF {formatted_cpf[:3]}***")
            return []

        except Exception as e:
            logger.error(f"Erro ao buscar atendimentos por CPF: {e}")
            raise HubSoftAPIError(f"Falha ao buscar atendimentos: {str(e)}")

    def _map_hubsoft_ticket_to_internal(self, hubsoft_ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapeia campos retornados pela API HubSoft para formato interno esperado pelo bot.

        Args:
            hubsoft_ticket: Dados do atendimento retornados pela API HubSoft

        Returns:
            Ticket mapeado para formato interno
        """
        # O campo 'status' vem como string na API HubSoft (ex: "Resolvido", "Aguardando Análise")
        status_value = hubsoft_ticket.get('status', 'Status Desconhecido')

        # Mapeia status em português para prefixo interno
        status_map = {
            'Aguardando Análise': 'aguardando_analise',
            'Em Andamento': 'em_andamento',
            'Resolvido': 'resolvido',
            'Cancelado': 'cancelado',
            'Pendente': 'pendente'
        }

        status_key = status_map.get(status_value, 'unknown')
        status_display = status_value

        # Tenta extrair categoria do tipo_atendimento
        # tipo_atendimento vem como string (ex: "SUPORTE - ONCABO GAMER")
        category = 'others'
        tipo_atendimento = hubsoft_ticket.get('tipo_atendimento', '')
        if tipo_atendimento and isinstance(tipo_atendimento, str):
            category = tipo_atendimento

        return {
            'id': hubsoft_ticket.get('id_atendimento'),
            'protocol': hubsoft_ticket.get('protocolo'),
            'status_key': status_key,          # Para lógica (ex: 'aguardando_analise')
            'status_display': status_display,    # Para exibição (ex: 'Aguardando Análise')
            'category': category,
            'created_at': hubsoft_ticket.get('data_cadastro'),
            'closed_at': hubsoft_ticket.get('data_fechamento'),
            'description': hubsoft_ticket.get('descricao_abertura', ''),
            'closure_description': hubsoft_ticket.get('descricao_fechamento', ''),
            'type': hubsoft_ticket.get('tipo_atendimento', ''),
            'affected_game': None,  # HubSoft não retorna esse campo diretamente
            # Dados originais da API HubSoft para referência
            '_hubsoft_data': hubsoft_ticket
        }

    async def add_attachment_to_ticket(
        self,
        id_atendimento: int,
        file_data: bytes,
        file_name: str,
        mime_type: str = 'image/png'
    ) -> Dict[str, Any]:
        """
        Adiciona anexo a um atendimento existente no HubSoft.

        Args:
            id_atendimento: ID do atendimento no HubSoft
            file_data: Dados binários do arquivo
            file_name: Nome do arquivo (ex: screenshot.png)
            mime_type: Tipo MIME do arquivo

        Returns:
            Dict contendo response da API

        Raises:
            HubSoftAPIError: Erro no upload do anexo
        """
        try:
            import aiohttp

            # Rate limiting
            await self.rate_limiter.wait_for_rate_limit()

            session = await self._get_session()
            url = f"{self.base_url}/api/v1/integracao/atendimento/adicionar_anexo/{id_atendimento}"

            # Obtém token de autenticação
            token = self.token_manager.get_access_token()
            if not token:
                token = await self._authenticate()

            # Cria FormData para enviar arquivo
            # Testando diferentes variações do nome do campo
            form_data = aiohttp.FormData()

            # Tenta enviar com diferentes nomes de campo
            # Baseado na doc que mostra: files[0]: None, files[1]: None
            form_data.add_field(
                'files[0]',
                file_data,
                filename=file_name,
                content_type=mime_type
            )

            # Headers (não incluir Content-Type, aiohttp define automaticamente)
            headers = {
                'Authorization': f'Bearer {token}'
            }

            logger.info(f"Enviando anexo: campo='files[0]', filename='{file_name}', size={len(file_data)} bytes, content_type='{mime_type}'")

            # Faz requisição multipart/form-data
            async with session.post(
                url=url,
                data=form_data,
                headers=headers
            ) as response:

                # Verifica rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    await self.rate_limiter.handle_rate_limit(retry_after)
                    raise HubSoftAPIError(
                        "Rate limit exceeded",
                        status_code=429,
                        error_code="rate_limit_exceeded"
                    )

                # Lê resposta
                try:
                    response_data = await response.json()
                except:
                    response_data = {"text": await response.text()}

                # Verifica se houve erro HTTP
                if not response.ok:
                    error_message = response_data.get('message', f'HTTP {response.status}')
                    error_code = response_data.get('error_code', 'upload_error')

                    raise HubSoftAPIError(
                        error_message,
                        status_code=response.status,
                        error_code=error_code,
                        details=response_data
                    )

                # Verifica se houve erro na resposta da API (status: "error")
                api_status = response_data.get('status', '')
                if api_status == 'error':
                    error_msg = response_data.get('msg', 'Erro desconhecido')
                    errors = response_data.get('errors', [])
                    exception = response_data.get('exception', '')

                    error_details = f"{error_msg}"
                    if errors:
                        error_details += f" - Erros: {', '.join(errors)}"
                    if exception:
                        error_details += f" - Exception: {exception}"

                    logger.error(f"Erro ao adicionar anexo '{file_name}' ao atendimento {id_atendimento}: {error_details}")
                    raise HubSoftAPIError(
                        error_details,
                        status_code=200,  # HTTP foi 200, mas API retornou erro
                        error_code="api_error",
                        details=response_data
                    )

                logger.info(f"Anexo '{file_name}' adicionado ao atendimento {id_atendimento} - Response: {response_data}")
                return response_data

        except aiohttp.ClientError as e:
            raise HubSoftAPIError(
                f"Connection error uploading attachment: {str(e)}",
                error_code="connection_error"
            )
        except asyncio.TimeoutError:
            raise HubSoftAPIError(
                "Timeout uploading attachment",
                error_code="timeout"
            )

    # REMOVIDOS: Métodos com endpoints inexistentes na API HubSoft
    # - update_ticket() - usava /tickets/{id} (não existe)
    # - get_ticket_status() - usava /tickets/{id}/status (não existe)
    # - search_tickets_by_cpf() - usava /tickets/search (não existe, usar get_user_tickets())
    # - get_client_contracts() - usava /clients/contracts (não existe, usar verify_client_by_cpf())

    async def check_api_health(self) -> Dict[str, Any]:
        """Verifica saúde da API HubSoft."""
        try:
            start_time = datetime.now()

            response = await self._make_request(
                "GET",
                "/health",
                authenticated=False
            )

            end_time = datetime.now()
            response_time = int((end_time - start_time).total_seconds() * 1000)

            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "timestamp": start_time.isoformat(),
                "details": response
            }

        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Obtém status do rate limiting."""
        return await self.rate_limiter.get_status()

    async def close(self) -> None:
        """Fecha recursos."""
        if self._session and not self._session.closed:
            await self._session.close()


class HubSoftCacheService(HubSoftCacheRepository):
    """Implementação do serviço de cache HubSoft."""

    def __init__(self, cache_manager: Optional[HubSoftCacheManager] = None):
        self.cache_manager = cache_manager or HubSoftCacheManager()

    async def get_cached_client_data(
        self,
        cpf: str
    ) -> Optional[Dict[str, Any]]:
        """Obtém dados de cliente do cache."""
        cache_key = f"client_data:{self._hash_cpf(cpf)}"
        return await self.cache_manager.get(cache_key)

    async def cache_client_data(
        self,
        cpf: str,
        client_data: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> None:
        """Armazena dados de cliente no cache."""
        cache_key = f"client_data:{self._hash_cpf(cpf)}"
        await self.cache_manager.set(cache_key, client_data, ttl_seconds)

    async def get_cached_ticket_data(
        self,
        ticket_id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtém dados de ticket do cache."""
        cache_key = f"ticket_data:{ticket_id}"
        return await self.cache_manager.get(cache_key)

    async def cache_ticket_data(
        self,
        ticket_id: str,
        ticket_data: Dict[str, Any],
        ttl_seconds: int = 1800
    ) -> None:
        """Armazena dados de ticket no cache."""
        cache_key = f"ticket_data:{ticket_id}"
        await self.cache_manager.set(cache_key, ticket_data, ttl_seconds)

    async def invalidate_client_cache(
        self,
        cpf: str
    ) -> None:
        """Invalida cache de cliente."""
        cache_key = f"client_data:{self._hash_cpf(cpf)}"
        await self.cache_manager.delete(cache_key)

    async def invalidate_ticket_cache(
        self,
        ticket_id: str
    ) -> None:
        """Invalida cache de ticket."""
        cache_key = f"ticket_data:{ticket_id}"
        await self.cache_manager.delete(cache_key)

    async def clear_expired_cache(self) -> int:
        """Remove entradas expiradas do cache."""
        return await self.cache_manager.cleanup_expired()

    def _hash_cpf(self, cpf: str) -> str:
        """Gera hash do CPF para usar como chave de cache."""
        return hashlib.sha256(cpf.encode()).hexdigest()[:16]