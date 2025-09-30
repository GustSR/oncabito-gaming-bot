"""
Sistema de cache inteligente para API HubSoft.

Este módulo implementa cache em memória para dados da API HubSoft visando:
- Reduzir requisições desnecessárias para dados que mudam pouco
- Melhorar performance das operações frequentes
- Implementar TTL (Time To Live) adequado para cada tipo de dado

Cache Categories:
- Client Data: Dados básicos do cliente (TTL: 30 minutos)
- Contract Status: Status de contrato ativo (TTL: 4 horas)
- Service Data: Dados de serviço (TTL: 1 hora)
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Representa uma entrada no cache com metadados."""
    data: Any
    created_at: float = field(default_factory=time.time)
    ttl_seconds: int = 1800  # 30 minutos default
    access_count: int = 0
    last_access: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Verifica se a entrada expirou."""
        return time.time() > (self.created_at + self.ttl_seconds)

    def is_fresh(self) -> bool:
        """Verifica se a entrada ainda está fresca (não expirou)."""
        return not self.is_expired()

    def touch(self):
        """Atualiza timestamp de último acesso e incrementa contador."""
        self.last_access = time.time()
        self.access_count += 1


class HubSoftCacheManager:
    """
    Gerenciador de cache thread-safe para dados da API HubSoft.

    Categorias de cache com TTL diferenciados:
    - CLIENT_DATA: Dados básicos do cliente (30 min)
    - CONTRACT_STATUS: Status do contrato (4 horas)
    - SERVICE_DATA: Dados de serviço (1 hora)
    """

    # TTL por categoria (em segundos)
    TTL_CLIENT_DATA = 30 * 60      # 30 minutos
    TTL_CONTRACT_STATUS = 4 * 60 * 60  # 4 horas
    TTL_SERVICE_DATA = 60 * 60     # 1 hora

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0
        }
        self._max_entries = 1000  # Limite máximo de entradas

    def _generate_key(self, category: str, identifier: str) -> str:
        """
        Gera chave única para o cache.

        Args:
            category: Categoria do cache (CLIENT_DATA, CONTRACT_STATUS, etc.)
            identifier: Identificador único (CPF, ID, etc.)

        Returns:
            str: Chave única para o cache
        """
        # Normaliza CPF removendo formatação
        if category in ['CLIENT_DATA', 'CONTRACT_STATUS']:
            clean_identifier = "".join(filter(str.isdigit, identifier))
            return f"{category}:{clean_identifier}"
        return f"{category}:{identifier}"

    def get(self, category: str, identifier: str) -> Optional[Any]:
        """
        Recupera dados do cache se válidos.

        Args:
            category: Categoria do cache
            identifier: Identificador único

        Returns:
            Dados armazenados ou None se não encontrado/expirado
        """
        key = self._generate_key(category, identifier)

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats['misses'] += 1
                logger.debug(f"Cache MISS: {key}")
                return None

            if entry.is_expired():
                # Remove entrada expirada
                del self._cache[key]
                self._stats['misses'] += 1
                self._stats['evictions'] += 1
                logger.debug(f"Cache EXPIRED: {key} (age: {time.time() - entry.created_at:.1f}s)")
                return None

            # Cache hit - atualiza metadados
            entry.touch()
            self._stats['hits'] += 1
            logger.debug(f"Cache HIT: {key} (age: {time.time() - entry.created_at:.1f}s, "
                        f"access count: {entry.access_count})")
            return entry.data

    def set(self, category: str, identifier: str, data: Any, ttl_override: Optional[int] = None) -> bool:
        """
        Armazena dados no cache.

        Args:
            category: Categoria do cache
            identifier: Identificador único
            data: Dados a armazenar
            ttl_override: TTL customizado em segundos (opcional)

        Returns:
            bool: True se armazenado com sucesso
        """
        if data is None:
            return False

        key = self._generate_key(category, identifier)

        # Determina TTL baseado na categoria
        if ttl_override:
            ttl = ttl_override
        elif category == 'CLIENT_DATA':
            ttl = self.TTL_CLIENT_DATA
        elif category == 'CONTRACT_STATUS':
            ttl = self.TTL_CONTRACT_STATUS
        elif category == 'SERVICE_DATA':
            ttl = self.TTL_SERVICE_DATA
        else:
            ttl = self.TTL_CLIENT_DATA  # Default

        with self._lock:
            # Verifica limite de entradas
            if len(self._cache) >= self._max_entries:
                self._evict_lru()

            # Cria entrada
            entry = CacheEntry(data=data, ttl_seconds=ttl)
            self._cache[key] = entry
            self._stats['sets'] += 1

            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True

    def invalidate(self, category: str, identifier: str) -> bool:
        """
        Remove entrada específica do cache.

        Args:
            category: Categoria do cache
            identifier: Identificador único

        Returns:
            bool: True se removido, False se não encontrado
        """
        key = self._generate_key(category, identifier)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache INVALIDATED: {key}")
                return True
            return False

    def invalidate_category(self, category: str) -> int:
        """
        Remove todas as entradas de uma categoria.

        Args:
            category: Categoria a invalidar

        Returns:
            int: Número de entradas removidas
        """
        with self._lock:
            keys_to_remove = [key for key in self._cache.keys() if key.startswith(f"{category}:")]

            for key in keys_to_remove:
                del self._cache[key]

            logger.info(f"Cache invalidated category {category}: {len(keys_to_remove)} entries removed")
            return len(keys_to_remove)

    def clear(self) -> int:
        """
        Limpa todo o cache.

        Returns:
            int: Número de entradas removidas
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries removed")
            return count

    def cleanup_expired(self) -> int:
        """
        Remove todas as entradas expiradas.

        Returns:
            int: Número de entradas removidas
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                self._stats['evictions'] += len(expired_keys)
                logger.debug(f"Cache cleanup: {len(expired_keys)} expired entries removed")

            return len(expired_keys)

    def _evict_lru(self):
        """Remove a entrada menos recentemente usada (LRU)."""
        if not self._cache:
            return

        # Encontra entrada com último acesso mais antigo
        lru_key = min(self._cache.keys(),
                     key=lambda k: self._cache[k].last_access)

        del self._cache[lru_key]
        self._stats['evictions'] += 1
        logger.debug(f"Cache LRU eviction: {lru_key}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache.

        Returns:
            dict: Estatísticas detalhadas
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0

            # Análise por categoria
            categories = {}
            for key, entry in self._cache.items():
                category = key.split(':', 1)[0]
                if category not in categories:
                    categories[category] = {'count': 0, 'total_accesses': 0}
                categories[category]['count'] += 1
                categories[category]['total_accesses'] += entry.access_count

            return {
                'total_entries': len(self._cache),
                'max_entries': self._max_entries,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self._stats['evictions'],
                'sets': self._stats['sets'],
                'categories': categories,
                'memory_usage_estimate': self._estimate_memory_usage()
            }

    def _estimate_memory_usage(self) -> str:
        """Estima uso de memória do cache."""
        # Estimativa simples baseada no número de entradas
        estimated_bytes = len(self._cache) * 1024  # ~1KB por entrada (estimativa)
        if estimated_bytes < 1024:
            return f"{estimated_bytes} bytes"
        elif estimated_bytes < 1024 * 1024:
            return f"{estimated_bytes / 1024:.1f} KB"
        else:
            return f"{estimated_bytes / (1024 * 1024):.1f} MB"


# Instância singleton global
cache_manager = HubSoftCacheManager()


# Funções de conveniência
def cache_client_data(cpf: str, data: Dict[str, Any], ttl_override: Optional[int] = None) -> bool:
    """Cache dados de cliente."""
    return cache_manager.set('CLIENT_DATA', cpf, data, ttl_override)


def get_cached_client_data(cpf: str) -> Optional[Dict[str, Any]]:
    """Recupera dados de cliente do cache."""
    return cache_manager.get('CLIENT_DATA', cpf)


def cache_contract_status(cpf: str, status: bool, ttl_override: Optional[int] = None) -> bool:
    """Cache status de contrato."""
    return cache_manager.set('CONTRACT_STATUS', cpf, status, ttl_override)


def get_cached_contract_status(cpf: str) -> Optional[bool]:
    """Recupera status de contrato do cache."""
    return cache_manager.get('CONTRACT_STATUS', cpf)


def invalidate_client_cache(cpf: str):
    """Invalida cache para um cliente específico."""
    cache_manager.invalidate('CLIENT_DATA', cpf)
    cache_manager.invalidate('CONTRACT_STATUS', cpf)


def get_cache_stats() -> Dict[str, Any]:
    """Retorna estatísticas do cache."""
    return cache_manager.get_stats()


def cleanup_cache():
    """Limpa entradas expiradas do cache."""
    return cache_manager.cleanup_expired()