"""
BRAIN - Memory Cache
Cache em memória com TTL (fallback quando Redis não está disponível)
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional
from dataclasses import dataclass
from threading import Lock

from ...core.logger import get_logger

logger = get_logger("brain.cache")


@dataclass
class CacheEntry:
    """Entrada no cache"""
    key: str
    value: Any
    ttl: int  # segundos
    created_at: float
    
    @property
    def is_expired(self) -> bool:
        """Verifica se a entrada expirou"""
        return time.time() > (self.created_at + self.ttl)
    
    @property
    def remaining_ttl(self) -> int:
        """TTL restante em segundos"""
        remaining = (self.created_at + self.ttl) - time.time()
        return max(0, int(remaining))


class MemoryCache:
    """
    Cache em memória com TTL
    
    Características:
    - Thread-safe
    - TTL por entrada
    - Limpeza automática de entradas expiradas
    - Limite de tamanho (LRU)
    """
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = Lock()
        
        # Estatísticas
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém valor do cache
        
        Args:
            key: Chave do cache
            
        Returns:
            Valor ou None se não encontrado/expirado
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Armazena valor no cache
        
        Args:
            key: Chave do cache
            value: Valor a armazenar
            ttl: Tempo de vida em segundos (default: 5 min)
            
        Returns:
            True se armazenado com sucesso
        """
        with self._lock:
            # Limpar entradas expiradas se necessário
            if len(self._cache) >= self._max_size:
                self._cleanup_expired()
            
            # Se ainda cheio, remover entrada mais antiga
            if len(self._cache) >= self._max_size:
                self._evict_oldest()
            
            # Criar entrada
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl,
                created_at=time.time()
            )
            
            self._cache[key] = entry
            return True
    
    def delete(self, key: str) -> bool:
        """Remove entrada do cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """Verifica se chave existe e não expirou"""
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired:
                return True
            return False
    
    def clear(self):
        """Limpa todo o cache"""
        with self._lock:
            self._cache.clear()
            logger.info("🗑️ Cache limpo")
    
    def _cleanup_expired(self):
        """Remove entradas expiradas (chamado internamente)"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._evictions += 1
        
        if expired_keys:
            logger.debug(f"🧹 {len(expired_keys)} entradas expiradas removidas")
    
    def _evict_oldest(self):
        """Remove entrada mais antiga (LRU simplificado)"""
        if not self._cache:
            return
        
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        del self._cache[oldest_key]
        self._evictions += 1
        logger.debug(f"🗑️ Entrada evictada: {oldest_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "type": "memory",
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "evictions": self._evictions,
                "keys": list(self._cache.keys())[:20]  # Primeiras 20 chaves
            }
    
    def get_ttl(self, key: str) -> int:
        """Retorna TTL restante de uma chave"""
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                return entry.remaining_ttl
            return 0
