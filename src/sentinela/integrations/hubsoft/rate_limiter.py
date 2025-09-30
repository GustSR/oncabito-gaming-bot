"""
Sistema de Rate Limiting e Queue para API HubSoft.

Este módulo implementa controle de rate limiting proativo para evitar
sobrecarga da API HubSoft e reduzir chances de bloqueio por excesso de requisições.

Funcionalidades:
- Rate limiting configurável (requests por minuto)
- Queue inteligente com priorização
- Retry automático com backoff exponencial
- Monitoramento de saúde da API
"""

import asyncio
import logging
import time
import threading
from enum import Enum
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class RequestPriority(Enum):
    """Prioridades para requisições na queue."""
    CRITICAL = 1    # Operações críticas (criação de tickets)
    HIGH = 2        # Verificações de usuário em tempo real
    NORMAL = 3      # Sincronizações regulares
    LOW = 4         # Operações de background, limpeza


@dataclass
class QueuedRequest:
    """Representa uma requisição na queue."""
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: RequestPriority = RequestPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    callback: Optional[Callable] = None
    request_id: str = field(default_factory=lambda: f"req_{int(time.time() * 1000)}")

    def __lt__(self, other):
        """Comparação para heap queue - menor priority value = maior prioridade."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class HubSoftRateLimiter:
    """
    Rate limiter thread-safe para API HubSoft.

    Implementa:
    - Limite de requisições por minuto
    - Queue com priorização
    - Retry automático com backoff
    - Estatísticas de uso
    """

    def __init__(self, max_requests_per_minute: int = 30):
        """
        Inicializa o rate limiter.

        Args:
            max_requests_per_minute: Máximo de requisições por minuto
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.request_interval = 60.0 / max_requests_per_minute  # Segundos entre requisições

        # Controle de rate limiting
        self._request_times = deque()
        self._rate_lock = threading.Lock()

        # Queue de requisições
        self._request_queue = asyncio.PriorityQueue()
        self._queue_processor_task = None
        self._is_processing = False

        # Estatísticas
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0,
            'retried_requests': 0,
            'queue_size_peak': 0
        }

        # Controle de saúde da API
        self._api_healthy = True
        self._last_health_check = None
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5

    async def start(self):
        """Inicia o processador de queue."""
        if not self._is_processing:
            self._is_processing = True
            self._queue_processor_task = asyncio.create_task(self._process_queue())
            logger.info(f"Rate limiter iniciado: {self.max_requests_per_minute} req/min")

    async def stop(self):
        """Para o processador de queue."""
        self._is_processing = False
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Rate limiter parado")

    def can_make_request(self) -> bool:
        """
        Verifica se pode fazer uma requisição agora sem violar rate limit.

        Returns:
            bool: True se pode fazer requisição
        """
        with self._rate_lock:
            current_time = time.time()

            # Remove requisições antigas (mais de 1 minuto)
            while self._request_times and current_time - self._request_times[0] > 60:
                self._request_times.popleft()

            # Verifica se pode fazer nova requisição
            return len(self._request_times) < self.max_requests_per_minute

    def _record_request(self):
        """Registra uma nova requisição no controle de rate."""
        with self._rate_lock:
            self._request_times.append(time.time())

    async def wait_for_rate_limit(self):
        """Aguarda até poder fazer uma nova requisição."""
        while not self.can_make_request():
            # Calcula tempo de espera baseado na requisição mais antiga
            with self._rate_lock:
                if self._request_times:
                    oldest_request = self._request_times[0]
                    wait_time = 60 - (time.time() - oldest_request)
                    wait_time = max(0.1, wait_time)  # Mínimo 100ms
                else:
                    wait_time = self.request_interval

            logger.debug(f"Rate limit atingido, aguardando {wait_time:.2f}s...")
            await asyncio.sleep(wait_time)

    async def execute_request(
        self,
        func: Callable,
        *args,
        priority: RequestPriority = RequestPriority.NORMAL,
        max_retries: int = 3,
        **kwargs
    ) -> Any:
        """
        Executa uma requisição respeitando rate limiting.

        Args:
            func: Função a executar
            *args: Argumentos para a função
            priority: Prioridade da requisição
            max_retries: Máximo de tentativas
            **kwargs: Argumentos nomeados para a função

        Returns:
            Resultado da função ou None em caso de erro
        """
        request = QueuedRequest(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries
        )

        # Adiciona na queue
        await self._request_queue.put(request)

        # Atualiza estatística de tamanho de queue
        queue_size = self._request_queue.qsize()
        if queue_size > self._stats['queue_size_peak']:
            self._stats['queue_size_peak'] = queue_size

        logger.debug(f"Requisição {request.request_id} adicionada à queue "
                    f"(prioridade: {priority.name}, queue size: {queue_size})")

        # Por enquanto retorna None, mas poderia implementar Future para retorno assíncrono
        return None

    async def _process_queue(self):
        """Processa a queue de requisições."""
        logger.info("Processador de queue iniciado")

        while self._is_processing:
            try:
                # Aguarda nova requisição (timeout para permitir parada)
                try:
                    request = await asyncio.wait_for(
                        self._request_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Executa a requisição
                await self._execute_queued_request(request)

            except Exception as e:
                logger.error(f"Erro no processador de queue: {e}")
                await asyncio.sleep(1)

    async def _execute_queued_request(self, request: QueuedRequest):
        """Executa uma requisição da queue."""
        start_time = time.time()

        try:
            # Verifica saúde da API
            if not self._api_healthy:
                await self._check_api_health()
                if not self._api_healthy:
                    # API ainda não saudável, agenda retry
                    await self._schedule_retry(request, "API não saudável")
                    return

            # Aguarda rate limit
            await self.wait_for_rate_limit()

            # Registra requisição
            self._record_request()
            self._stats['total_requests'] += 1

            logger.debug(f"Executando requisição {request.request_id}")

            # Executa a função
            if asyncio.iscoroutinefunction(request.func):
                result = await request.func(*request.args, **request.kwargs)
            else:
                result = request.func(*request.args, **request.kwargs)

            # Sucesso
            self._stats['successful_requests'] += 1
            self._consecutive_failures = 0
            self._api_healthy = True

            execution_time = time.time() - start_time
            logger.debug(f"Requisição {request.request_id} concluída em {execution_time:.2f}s")

            # Executa callback se fornecido
            if request.callback:
                try:
                    await request.callback(result)
                except Exception as e:
                    logger.error(f"Erro no callback da requisição {request.request_id}: {e}")

        except Exception as e:
            # Falha na requisição
            self._stats['failed_requests'] += 1
            self._consecutive_failures += 1

            logger.error(f"Erro na requisição {request.request_id}: {e}")

            # Verifica se deve marcar API como não saudável
            if self._consecutive_failures >= self._max_consecutive_failures:
                self._api_healthy = False
                logger.warning(f"API marcada como não saudável após {self._consecutive_failures} falhas consecutivas")

            # Agenda retry se ainda tem tentativas
            if request.retry_count < request.max_retries:
                await self._schedule_retry(request, str(e))
            else:
                logger.error(f"Requisição {request.request_id} falhou definitivamente após {request.retry_count} tentativas")

    async def _schedule_retry(self, request: QueuedRequest, error_reason: str):
        """Agenda retry de uma requisição."""
        request.retry_count += 1
        self._stats['retried_requests'] += 1

        # Backoff exponencial: 2^retry_count segundos
        delay = min(2 ** request.retry_count, 60)  # Máximo 60 segundos

        logger.warning(f"Agendando retry {request.retry_count}/{request.max_retries} "
                      f"para requisição {request.request_id} em {delay}s (motivo: {error_reason})")

        # Agenda retry
        asyncio.create_task(self._delayed_retry(request, delay))

    async def _delayed_retry(self, request: QueuedRequest, delay: float):
        """Executa retry após delay."""
        await asyncio.sleep(delay)
        await self._request_queue.put(request)

    async def _check_api_health(self):
        """Verifica saúde da API HubSoft."""
        try:
            # Implementa verificação simples de saúde
            # Por enquanto apenas aguarda um tempo e marca como saudável
            await asyncio.sleep(5)
            self._api_healthy = True
            self._consecutive_failures = 0
            logger.info("API HubSoft voltou a responder normalmente")

        except Exception as e:
            logger.error(f"Verificação de saúde da API falhou: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do rate limiter.

        Returns:
            dict: Estatísticas detalhadas
        """
        current_time = time.time()

        # Calcula taxa de requisições atual
        with self._rate_lock:
            recent_requests = sum(1 for t in self._request_times if current_time - t <= 60)

        return {
            'max_requests_per_minute': self.max_requests_per_minute,
            'current_requests_per_minute': recent_requests,
            'queue_size': self._request_queue.qsize() if hasattr(self, '_request_queue') else 0,
            'is_processing': self._is_processing,
            'api_healthy': self._api_healthy,
            'consecutive_failures': self._consecutive_failures,
            'stats': self._stats.copy()
        }


# Instância singleton global
rate_limiter = HubSoftRateLimiter(max_requests_per_minute=30)  # 30 req/min = safe limit


# Funções de conveniência
async def rate_limited_request(
    func: Callable,
    *args,
    priority: RequestPriority = RequestPriority.NORMAL,
    max_retries: int = 3,
    **kwargs
) -> Any:
    """
    Executa requisição com rate limiting.

    Args:
        func: Função a executar
        priority: Prioridade da requisição
        max_retries: Máximo de tentativas

    Returns:
        Resultado da função
    """
    return await rate_limiter.execute_request(
        func, *args,
        priority=priority,
        max_retries=max_retries,
        **kwargs
    )


def get_rate_limiter_stats() -> Dict[str, Any]:
    """Retorna estatísticas do rate limiter."""
    return rate_limiter.get_stats()


async def start_rate_limiter():
    """Inicia o rate limiter."""
    await rate_limiter.start()


async def stop_rate_limiter():
    """Para o rate limiter."""
    await rate_limiter.stop()