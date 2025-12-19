"""
VIRTUS - Cache de Análises
==========================

Sistema de cache com TTL para evitar recálculo de análises.
"""

import asyncio
import time
import hashlib
import json
from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import OrderedDict
import functools

from .logger import get_logger

logger = get_logger("cache")

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Entrada do cache."""
    value: T
    created_at: float
    expires_at: float
    hits: int = 0
    last_accessed: float = 0
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at
    
    @property
    def ttl_remaining(self) -> float:
        return max(0, self.expires_at - time.time())


class AnalysisCache:
    """
    Cache de análises com TTL e LRU eviction.
    
    Features:
    - TTL configurável por tipo de análise
    - LRU eviction quando atinge capacidade máxima
    - Estatísticas de hit/miss
    - Thread-safe
    
    Uso:
        cache = AnalysisCache(default_ttl=60)
        
        # Set
        cache.set("XAUUSD_analysis", analysis_data)
        
        # Get
        data = cache.get("XAUUSD_analysis")
        
        # Com decorator
        @cache.cached(ttl=30)
        async def get_analysis(symbol: str):
            return await expensive_analysis(symbol)
    """
    
    def __init__(
        self,
        default_ttl: float = 60.0,
        max_size: int = 1000,
        cleanup_interval: float = 60.0
    ):
        """
        Args:
            default_ttl: TTL padrão em segundos
            max_size: Número máximo de entradas
            cleanup_interval: Intervalo de limpeza automática
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        
        # Estatísticas
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
        
        # TTLs específicos por tipo
        self._ttls: Dict[str, float] = {
            "market_data": 5,      # Dados de mercado: 5 segundos
            "analysis": 30,        # Análises: 30 segundos
            "indicators": 15,      # Indicadores: 15 segundos
            "signals": 10,         # Sinais: 10 segundos
            "news": 300,           # Notícias: 5 minutos
            "sentiment": 60,       # Sentimento: 1 minuto
            "account": 5,          # Dados da conta: 5 segundos
            "positions": 2,        # Posições: 2 segundos
        }
    
    def set_ttl(self, cache_type: str, ttl: float):
        """Define TTL para um tipo de cache."""
        self._ttls[cache_type] = ttl
    
    def _get_ttl(self, key: str) -> float:
        """Obtém TTL apropriado para uma chave."""
        for prefix, ttl in self._ttls.items():
            if key.startswith(prefix):
                return ttl
        return self.default_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Obtém valor do cache.
        
        Returns:
            Valor ou None se não existir/expirado
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None
            
            # Atualiza estatísticas e move para o final (LRU)
            entry.hits += 1
            entry.last_accessed = time.time()
            self._cache.move_to_end(key)
            
            self._stats["hits"] += 1
            return entry.value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ):
        """
        Armazena valor no cache.
        
        Args:
            key: Chave do cache
            value: Valor a armazenar
            ttl: TTL em segundos (usa default se não especificado)
        """
        if ttl is None:
            ttl = self._get_ttl(key)
        
        async with self._lock:
            # Eviction se necessário
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats["evictions"] += 1
            
            now = time.time()
            self._cache[key] = CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + ttl,
                last_accessed=now
            )
    
    async def delete(self, key: str) -> bool:
        """Remove entrada do cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self):
        """Limpa todo o cache."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache limpo")
    
    async def cleanup_expired(self) -> int:
        """Remove entradas expiradas."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self._stats["expirations"] += len(expired_keys)
                logger.debug(f"Cache cleanup: {len(expired_keys)} entradas expiradas removidas")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "evictions": self._stats["evictions"],
            "expirations": self._stats["expirations"],
        }
    
    def cached(
        self,
        ttl: Optional[float] = None,
        key_builder: Optional[Callable[..., str]] = None
    ):
        """
        Decorator para cachear resultados de funções.
        
        Uso:
            @cache.cached(ttl=30)
            async def get_analysis(symbol: str):
                return await expensive_operation()
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Constrói chave do cache
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Chave padrão baseada nos argumentos
                    key_parts = [func.__name__]
                    key_parts.extend(str(a) for a in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = "_".join(key_parts)
                
                # Tenta obter do cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Executa função e cacheia resultado
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator


# ==================== INSTÂNCIA GLOBAL ====================

_cache: Optional[AnalysisCache] = None


def get_analysis_cache() -> AnalysisCache:
    """Retorna cache global de análises."""
    global _cache
    if _cache is None:
        _cache = AnalysisCache(
            default_ttl=60,
            max_size=5000,
            cleanup_interval=60
        )
    return _cache


# ==================== DECORATORS UTILITÁRIOS ====================

def cached_analysis(ttl: float = 30):
    """Decorator para cachear análises."""
    cache = get_analysis_cache()
    return cache.cached(ttl=ttl)


def cached_market_data(ttl: float = 5):
    """Decorator para cachear dados de mercado."""
    cache = get_analysis_cache()
    return cache.cached(ttl=ttl)


def cached_news(ttl: float = 300):
    """Decorator para cachear notícias."""
    cache = get_analysis_cache()
    return cache.cached(ttl=ttl)
