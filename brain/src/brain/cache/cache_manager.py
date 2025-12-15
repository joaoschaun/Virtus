"""
VIRTUS Brain - Cache Manager
============================

Gerenciador de cache inteligente para dados de APIs.
Implementa TTL, invalidação e persistência.
"""

import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from collections import OrderedDict
import pickle

from ...core.logger import get_logger
from ...core.exceptions import CacheError

logger = get_logger("cache")

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Entrada individual no cache"""
    key: str
    value: T
    created_at: datetime
    expires_at: datetime
    provider: str = ""
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    @property
    def ttl_remaining(self) -> float:
        """Segundos restantes até expiração"""
        remaining = (self.expires_at - datetime.now()).total_seconds()
        return max(0, remaining)


class CacheManager:
    """
    Gerenciador de cache central para o Brain.
    
    Features:
    - TTL configurável por tipo de dado
    - LRU eviction
    - Persistência em disco
    - Métricas de hit/miss
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_memory_items: int = 1000,
        default_ttl: int = 300,
        persist_to_disk: bool = True
    ):
        self.cache_dir = cache_dir or Path("data/brain/cache")
        self.max_memory_items = max_memory_items
        self.default_ttl = default_ttl
        self.persist_to_disk = persist_to_disk
        
        # Cache em memória (LRU)
        self._memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # TTLs específicos por tipo
        self._ttl_config: Dict[str, int] = {
            'news': 900,           # 15 min
            'sentiment': 600,      # 10 min
            'calendar': 3600,      # 1 hora
            'cot': 86400,          # 24 horas
            'price': 60,           # 1 min
            'indicator': 300,      # 5 min
            'market_data': 120,    # 2 min
            'analysis': 300,       # 5 min
        }
        
        # Métricas
        self._hits = 0
        self._misses = 0
        
        # Lock para operações thread-safe
        self._lock = asyncio.Lock()
        
        # Garante diretório existe
        if self.persist_to_disk:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def configure_ttl(self, data_type: str, ttl_seconds: int):
        """Configura TTL para um tipo de dado"""
        self._ttl_config[data_type] = ttl_seconds
        logger.debug(f"TTL configurado: {data_type} = {ttl_seconds}s")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Gera chave única para cache"""
        key_parts = [prefix] + [str(a) for a in args]
        if kwargs:
            key_parts.append(json.dumps(kwargs, sort_keys=True))
        
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    def _get_ttl(self, data_type: str) -> int:
        """Retorna TTL para um tipo de dado"""
        return self._ttl_config.get(data_type, self.default_ttl)
    
    async def get(
        self,
        key: str,
        data_type: str = "default"
    ) -> Optional[Any]:
        """
        Recupera valor do cache.
        
        Args:
            key: Chave do cache
            data_type: Tipo de dado para TTL
            
        Returns:
            Valor cacheado ou None se não encontrado/expirado
        """
        async with self._lock:
            # Tenta memória primeiro
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                
                if entry.is_expired:
                    del self._memory_cache[key]
                    self._misses += 1
                    return None
                
                # Move para final (LRU)
                self._memory_cache.move_to_end(key)
                entry.hits += 1
                self._hits += 1
                
                logger.debug(f"Cache HIT (memória): {key}")
                return entry.value
            
            # Tenta disco
            if self.persist_to_disk:
                disk_value = await self._get_from_disk(key, data_type)
                if disk_value is not None:
                    self._hits += 1
                    return disk_value
            
            self._misses += 1
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        data_type: str = "default",
        provider: str = "",
        ttl_override: Optional[int] = None
    ):
        """
        Armazena valor no cache.
        
        Args:
            key: Chave do cache
            value: Valor a armazenar
            data_type: Tipo de dado para TTL
            provider: Provider de origem
            ttl_override: TTL personalizado (sobrescreve config)
        """
        ttl = ttl_override if ttl_override else self._get_ttl(data_type)
        
        async with self._lock:
            now = datetime.now()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl),
                provider=provider
            )
            
            # Eviction se necessário
            while len(self._memory_cache) >= self.max_memory_items:
                self._memory_cache.popitem(last=False)
            
            self._memory_cache[key] = entry
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            
            # Persiste em disco
            if self.persist_to_disk:
                await self._save_to_disk(key, entry)
    
    async def delete(self, key: str):
        """Remove entrada do cache"""
        async with self._lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
            
            if self.persist_to_disk:
                await self._delete_from_disk(key)
    
    async def invalidate_by_provider(self, provider: str):
        """Invalida todas as entradas de um provider"""
        async with self._lock:
            keys_to_delete = [
                k for k, v in self._memory_cache.items()
                if v.provider == provider
            ]
            for key in keys_to_delete:
                del self._memory_cache[key]
            
            logger.info(f"Invalidadas {len(keys_to_delete)} entradas do provider {provider}")
    
    async def invalidate_by_type(self, data_type: str):
        """Invalida todas as entradas de um tipo"""
        async with self._lock:
            # Por ora, limpa tudo (poderia ser melhorado com prefixos)
            self._memory_cache.clear()
            logger.info(f"Cache do tipo {data_type} invalidado")
    
    async def clear(self):
        """Limpa todo o cache"""
        async with self._lock:
            self._memory_cache.clear()
            self._hits = 0
            self._misses = 0
            
            if self.persist_to_disk:
                for f in self.cache_dir.glob("*.cache"):
                    f.unlink()
            
            logger.info("Cache completamente limpo")
    
    async def cleanup_expired(self):
        """Remove entradas expiradas"""
        async with self._lock:
            expired_keys = [
                k for k, v in self._memory_cache.items()
                if v.is_expired
            ]
            for key in expired_keys:
                del self._memory_cache[key]
            
            if expired_keys:
                logger.debug(f"Removidas {len(expired_keys)} entradas expiradas")
    
    # ========================================================================
    # MÉTODOS DE DISCO
    # ========================================================================
    
    def _sanitize_key_for_filename(self, key: str) -> str:
        """Sanitiza key para uso como nome de arquivo (Windows compatibility)"""
        # Caracteres inválidos no Windows: \ / : * ? " < > |
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        safe_key = key
        for char in invalid_chars:
            safe_key = safe_key.replace(char, '_')
        return safe_key
    
    async def _get_from_disk(self, key: str, data_type: str) -> Optional[Any]:
        """Recupera valor do disco"""
        try:
            safe_key = self._sanitize_key_for_filename(key)
            cache_file = self.cache_dir / f"{safe_key}.cache"
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'rb') as f:
                entry: CacheEntry = pickle.load(f)
            
            if entry.is_expired:
                cache_file.unlink()
                return None
            
            # Carrega na memória
            self._memory_cache[key] = entry
            logger.debug(f"Cache HIT (disco): {key}")
            
            return entry.value
            
        except Exception as e:
            logger.warning(f"Erro ao ler cache do disco: {e}")
            return None
    
    async def _save_to_disk(self, key: str, entry: CacheEntry):
        """Salva valor em disco"""
        try:
            safe_key = self._sanitize_key_for_filename(key)
            cache_file = self.cache_dir / f"{safe_key}.cache"
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache em disco: {e}")
    
    async def _delete_from_disk(self, key: str):
        """Remove arquivo de cache"""
        try:
            safe_key = self._sanitize_key_for_filename(key)
            cache_file = self.cache_dir / f"{safe_key}.cache"
            if cache_file.exists():
                cache_file.unlink()
        except Exception as e:
            logger.warning(f"Erro ao deletar cache do disco: {e}")
    
    # ========================================================================
    # MÉTRICAS
    # ========================================================================
    
    @property
    def hit_rate(self) -> float:
        """Taxa de acerto do cache"""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        return {
            'memory_entries': len(self._memory_cache),
            'max_entries': self.max_memory_items,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{self.hit_rate:.1%}",
            'ttl_config': self._ttl_config,
        }


# Decorador para cache
def cached(data_type: str = "default", ttl: Optional[int] = None):
    """
    Decorador para cachear resultado de função.
    
    Usage:
        @cached(data_type='news', ttl=900)
        async def get_news(symbol: str) -> List[dict]:
            ...
    """
    def decorator(func: Callable):
        async def wrapper(self, *args, **kwargs):
            # Precisa ter acesso ao cache_manager
            if not hasattr(self, 'cache_manager'):
                return await func(self, *args, **kwargs)
            
            cache_manager: CacheManager = self.cache_manager
            key = cache_manager._generate_key(func.__name__, *args, **kwargs)
            
            # Tenta cache
            cached_value = await cache_manager.get(key, data_type)
            if cached_value is not None:
                return cached_value
            
            # Executa função
            result = await func(self, *args, **kwargs)
            
            # Salva no cache
            await cache_manager.set(key, result, data_type, ttl_override=ttl)
            
            return result
        
        return wrapper
    return decorator


# Instância global
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(cache_dir: Optional[Path] = None) -> CacheManager:
    """Retorna instância global do cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(cache_dir=cache_dir)
    return _cache_manager
