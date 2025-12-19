"""
VIRTUS - Retry com Backoff Exponencial
======================================

Sistema inteligente de retry com backoff exponencial e jitter.
"""

import asyncio
import random
import functools
from typing import Callable, TypeVar, Optional, Tuple, Type, Union, List
from datetime import datetime

from .logger import get_logger

logger = get_logger("retry")

T = TypeVar('T')


class RetryConfig:
    """Configuração de retry."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.1,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        non_retryable_exceptions: Tuple[Type[Exception], ...] = ()
    ):
        """
        Args:
            max_retries: Número máximo de tentativas
            base_delay: Delay base em segundos
            max_delay: Delay máximo em segundos
            exponential_base: Base do crescimento exponencial
            jitter: Adicionar variação aleatória ao delay
            jitter_factor: Fator de variação (0.1 = 10%)
            retryable_exceptions: Exceções que devem ser retentadas
            non_retryable_exceptions: Exceções que NÃO devem ser retentadas
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.retryable_exceptions = retryable_exceptions
        self.non_retryable_exceptions = non_retryable_exceptions


class RetryContext:
    """Contexto de uma execução com retry."""
    
    def __init__(self):
        self.attempt = 0
        self.total_time = 0.0
        self.last_exception: Optional[Exception] = None
        self.exceptions: List[Exception] = []
        self.started_at = datetime.now()


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[RetryContext], None]] = None,
    **kwargs
) -> T:
    """
    Executa função async com retry e backoff exponencial.
    
    Args:
        func: Função async a executar
        *args: Argumentos posicionais
        config: Configuração de retry
        on_retry: Callback chamado a cada retry
        **kwargs: Argumentos nomeados
        
    Returns:
        Resultado da função
        
    Raises:
        Exception: Última exceção após todas as tentativas
    """
    if config is None:
        config = RetryConfig()
    
    context = RetryContext()
    
    for attempt in range(config.max_retries + 1):
        context.attempt = attempt
        
        try:
            result = await func(*args, **kwargs)
            return result
            
        except config.non_retryable_exceptions as e:
            # Não retenta essas exceções
            logger.error(f"Exceção não retentável: {type(e).__name__}: {e}")
            raise
            
        except config.retryable_exceptions as e:
            context.last_exception = e
            context.exceptions.append(e)
            
            # Última tentativa - levanta exceção
            if attempt >= config.max_retries:
                logger.error(
                    f"Todas as {config.max_retries + 1} tentativas falharam. "
                    f"Última exceção: {type(e).__name__}: {e}"
                )
                raise
            
            # Calcula delay com backoff exponencial
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            
            # Adiciona jitter
            if config.jitter:
                jitter_range = delay * config.jitter_factor
                delay += random.uniform(-jitter_range, jitter_range)
                delay = max(0, delay)
            
            context.total_time += delay
            
            logger.warning(
                f"Tentativa {attempt + 1}/{config.max_retries + 1} falhou: "
                f"{type(e).__name__}: {e}. Aguardando {delay:.2f}s..."
            )
            
            # Callback de retry
            if on_retry:
                on_retry(context)
            
            await asyncio.sleep(delay)


def retry_sync(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """Versão síncrona do retry."""
    import time
    
    if config is None:
        config = RetryConfig()
    
    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
            
        except config.non_retryable_exceptions:
            raise
            
        except config.retryable_exceptions as e:
            if attempt >= config.max_retries:
                raise
            
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            
            if config.jitter:
                jitter_range = delay * config.jitter_factor
                delay += random.uniform(-jitter_range, jitter_range)
                delay = max(0, delay)
            
            logger.warning(
                f"Tentativa {attempt + 1}/{config.max_retries + 1} falhou: "
                f"{type(e).__name__}. Aguardando {delay:.2f}s..."
            )
            
            time.sleep(delay)


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator para adicionar retry com backoff a funções.
    
    Uso:
        @with_retry(max_retries=3, base_delay=1.0)
        async def call_api():
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        retryable_exceptions=retryable_exceptions
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await retry_async(func, *args, config=config, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return retry_sync(func, *args, config=config, **kwargs)
            return sync_wrapper
    
    return decorator


# ==================== CONFIGS PRÉ-DEFINIDAS ====================

# Para APIs que permitem muitas tentativas
API_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)

# Para operações críticas (MT5)
CRITICAL_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=0.5,
    max_delay=5.0,
    exponential_base=2.0,
    jitter=True
)

# Para operações de banco de dados
DB_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=0.1,
    max_delay=2.0,
    exponential_base=2.0,
    jitter=False
)

# Para requisições rápidas
FAST_RETRY_CONFIG = RetryConfig(
    max_retries=2,
    base_delay=0.2,
    max_delay=1.0,
    exponential_base=2.0,
    jitter=True
)
