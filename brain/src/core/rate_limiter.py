"""
VIRTUS - Rate Limiter
=====================

Sistema de rate limiting centralizado para controlar chamadas a APIs.
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass
from collections import defaultdict

from .logger import get_logger

logger = get_logger("rate_limiter")


@dataclass
class RateLimitConfig:
    """Configuração de rate limit."""
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 5


class TokenBucket:
    """
    Implementação de Token Bucket para rate limiting.
    
    Permite burst inicial e depois limita taxa constante.
    """
    
    def __init__(
        self,
        rate: float,  # tokens por segundo
        capacity: int  # capacidade máxima (burst)
    ):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Tenta adquirir tokens.
        
        Returns:
            True se adquiriu, False se não há tokens disponíveis
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            
            # Adiciona tokens pelo tempo passado
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_and_acquire(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """
        Aguarda até conseguir adquirir tokens.
        
        Args:
            tokens: Quantidade de tokens necessários
            timeout: Tempo máximo de espera
            
        Returns:
            True se adquiriu, False se timeout
        """
        start = time.monotonic()
        
        while True:
            if await self.acquire(tokens):
                return True
            
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                return False
            
            # Calcula tempo de espera
            wait_time = min(
                (tokens - self.tokens) / self.rate,
                timeout - elapsed
            )
            await asyncio.sleep(max(0.01, wait_time))
    
    @property
    def available_tokens(self) -> float:
        """Tokens disponíveis atualmente."""
        return self.tokens


class RateLimiter:
    """
    Rate Limiter centralizado para múltiplas APIs.
    
    Uso:
        limiter = RateLimiter()
        limiter.configure("finnhub", requests_per_second=1)
        
        async with limiter.limit("finnhub"):
            await call_finnhub_api()
    """
    
    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._stats: Dict[str, Dict] = defaultdict(lambda: {
            "total_requests": 0,
            "throttled_requests": 0,
            "last_request": None
        })
        self._lock = asyncio.Lock()
    
    def configure(
        self,
        name: str,
        requests_per_second: float = 1.0,
        burst_size: int = 5
    ):
        """Configura rate limit para uma API."""
        self._configs[name] = RateLimitConfig(
            requests_per_second=requests_per_second,
            burst_size=burst_size
        )
        self._buckets[name] = TokenBucket(
            rate=requests_per_second,
            capacity=burst_size
        )
        logger.debug(f"Rate limit configurado: {name} ({requests_per_second}/s, burst={burst_size})")
    
    async def acquire(self, name: str, timeout: float = 30.0) -> bool:
        """
        Adquire permissão para fazer uma requisição.
        
        Args:
            name: Nome da API
            timeout: Tempo máximo de espera
            
        Returns:
            True se permitido, False se bloqueado
        """
        # Cria bucket com defaults se não existir
        if name not in self._buckets:
            self.configure(name)
        
        bucket = self._buckets[name]
        stats = self._stats[name]
        
        acquired = await bucket.wait_and_acquire(timeout=timeout)
        
        stats["total_requests"] += 1
        stats["last_request"] = time.time()
        
        if not acquired:
            stats["throttled_requests"] += 1
            logger.warning(f"Rate limit: {name} throttled (timeout={timeout}s)")
        
        return acquired
    
    def limit(self, name: str, timeout: float = 30.0):
        """
        Context manager para rate limiting.
        
        Uso:
            async with limiter.limit("api"):
                await call_api()
        """
        return RateLimitContext(self, name, timeout)
    
    def get_stats(self, name: Optional[str] = None) -> Dict:
        """Retorna estatísticas de rate limiting."""
        if name:
            return dict(self._stats.get(name, {}))
        return {n: dict(s) for n, s in self._stats.items()}
    
    def get_available(self, name: str) -> float:
        """Retorna tokens disponíveis para uma API."""
        if name in self._buckets:
            return self._buckets[name].available_tokens
        return 0.0


class RateLimitContext:
    """Context manager para rate limiting."""
    
    def __init__(self, limiter: RateLimiter, name: str, timeout: float):
        self.limiter = limiter
        self.name = name
        self.timeout = timeout
    
    async def __aenter__(self):
        acquired = await self.limiter.acquire(self.name, self.timeout)
        if not acquired:
            raise RateLimitExceeded(f"Rate limit excedido para {self.name}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class RateLimitExceeded(Exception):
    """Exceção quando rate limit é excedido."""
    pass


# ==================== INSTÂNCIA GLOBAL ====================

_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Retorna rate limiter global."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
        
        # Configurações padrão para APIs conhecidas
        _limiter.configure("finnhub", requests_per_second=1, burst_size=5)
        _limiter.configure("forexnews", requests_per_second=0.5, burst_size=3)
        _limiter.configure("twelvedata", requests_per_second=0.5, burst_size=3)
        _limiter.configure("fmp", requests_per_second=1, burst_size=5)
        _limiter.configure("eodhd", requests_per_second=1, burst_size=5)
        _limiter.configure("mt5", requests_per_second=10, burst_size=20)
        
    return _limiter


# Decorator para aplicar rate limiting
def rate_limited(api_name: str, timeout: float = 30.0):
    """
    Decorator para aplicar rate limiting a uma função.
    
    Uso:
        @rate_limited("finnhub")
        async def call_finnhub():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            async with limiter.limit(api_name, timeout):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
