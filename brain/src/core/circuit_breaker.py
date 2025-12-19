"""
VIRTUS - Circuit Breaker
========================

Implementação do padrão Circuit Breaker para resiliência.
Protege contra cascata de falhas quando serviços externos falham.
"""

import asyncio
import time
from enum import Enum
from typing import Callable, Optional, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import functools

from ..core.logger import get_logger

logger = get_logger("circuit_breaker")


class CircuitState(Enum):
    """Estados do circuit breaker."""
    CLOSED = "closed"      # Normal - requisições passam
    OPEN = "open"          # Falhas - requisições bloqueadas
    HALF_OPEN = "half_open"  # Testando - algumas requisições passam


@dataclass
class CircuitBreakerConfig:
    """Configuração do circuit breaker."""
    failure_threshold: int = 5        # Falhas antes de abrir
    success_threshold: int = 3        # Sucessos para fechar
    timeout_seconds: float = 30.0     # Tempo no estado OPEN
    half_open_max_calls: int = 3      # Chamadas permitidas em HALF_OPEN


@dataclass
class CircuitStats:
    """Estatísticas do circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0


class CircuitBreaker:
    """
    Circuit Breaker para proteger chamadas a serviços externos.
    
    Estados:
    - CLOSED: Funcionamento normal
    - OPEN: Circuito aberto, todas as chamadas falham imediatamente
    - HALF_OPEN: Permite algumas chamadas para testar recuperação
    
    Uso:
        cb = CircuitBreaker("mt5_api")
        
        @cb
        async def call_mt5():
            ...
        
        # Ou manualmente:
        if cb.can_execute():
            try:
                result = await call_mt5()
                cb.record_success()
            except Exception:
                cb.record_failure()
    """
    
    def __init__(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        
        self.stats = CircuitStats()
        
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Retorna estado atual do circuit breaker."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN
    
    def can_execute(self) -> bool:
        """Verifica se uma chamada pode ser executada."""
        if self._state == CircuitState.CLOSED:
            return True
        
        if self._state == CircuitState.OPEN:
            # Verifica se timeout passou
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout_seconds:
                    self._transition_to(CircuitState.HALF_OPEN)
                    return True
            return False
        
        if self._state == CircuitState.HALF_OPEN:
            # Permite algumas chamadas para testar
            return self._half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Registra uma chamada bem-sucedida."""
        self.stats.total_calls += 1
        self.stats.successful_calls += 1
        self.stats.last_success_time = datetime.now()
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        
        # Reset failure count em sucesso
        self._failure_count = 0
    
    def record_failure(self, error: Optional[Exception] = None):
        """Registra uma chamada com falha."""
        self.stats.total_calls += 1
        self.stats.failed_calls += 1
        self.stats.last_failure_time = datetime.now()
        
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if error:
            logger.warning(f"[{self.name}] Falha registrada: {error}")
        
        if self._state == CircuitState.HALF_OPEN:
            # Qualquer falha em HALF_OPEN abre o circuito novamente
            self._transition_to(CircuitState.OPEN)
        
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)
    
    def record_rejected(self):
        """Registra uma chamada rejeitada (circuito aberto)."""
        self.stats.total_calls += 1
        self.stats.rejected_calls += 1
    
    def _transition_to(self, new_state: CircuitState):
        """Transição de estado."""
        old_state = self._state
        self._state = new_state
        self.stats.state_changes += 1
        
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            logger.info(f"[{self.name}] Circuit FECHADO - serviço recuperado")
        
        elif new_state == CircuitState.OPEN:
            self._success_count = 0
            logger.warning(f"[{self.name}] Circuit ABERTO - muitas falhas ({self._failure_count})")
        
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
            logger.info(f"[{self.name}] Circuit HALF_OPEN - testando recuperação")
    
    def reset(self):
        """Força reset do circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        logger.info(f"[{self.name}] Circuit resetado manualmente")
    
    def get_status(self) -> Dict:
        """Retorna status atual."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "stats": {
                "total_calls": self.stats.total_calls,
                "successful_calls": self.stats.successful_calls,
                "failed_calls": self.stats.failed_calls,
                "rejected_calls": self.stats.rejected_calls,
                "state_changes": self.stats.state_changes,
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "timeout_seconds": self.config.timeout_seconds,
            }
        }
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator para proteger funções."""
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.can_execute():
                    self.record_rejected()
                    raise CircuitOpenError(
                        f"Circuit breaker '{self.name}' está aberto"
                    )
                
                if self._state == CircuitState.HALF_OPEN:
                    self._half_open_calls += 1
                
                try:
                    result = await func(*args, **kwargs)
                    self.record_success()
                    return result
                except Exception as e:
                    self.record_failure(e)
                    raise
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.can_execute():
                    self.record_rejected()
                    raise CircuitOpenError(
                        f"Circuit breaker '{self.name}' está aberto"
                    )
                
                if self._state == CircuitState.HALF_OPEN:
                    self._half_open_calls += 1
                
                try:
                    result = func(*args, **kwargs)
                    self.record_success()
                    return result
                except Exception as e:
                    self.record_failure(e)
                    raise
            
            return sync_wrapper


class CircuitOpenError(Exception):
    """Exceção quando o circuit breaker está aberto."""
    pass


# ==================== GERENCIADOR GLOBAL ====================

class CircuitBreakerManager:
    """Gerenciador de múltiplos circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def get_or_create(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Obtém ou cria um circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Retorna status de todos os circuit breakers."""
        return {
            name: cb.get_status() 
            for name, cb in self._breakers.items()
        }
    
    def reset_all(self):
        """Reseta todos os circuit breakers."""
        for cb in self._breakers.values():
            cb.reset()


# Instância global
_manager = CircuitBreakerManager()


def get_circuit_breaker(
    name: str, 
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Obtém circuit breaker pelo nome."""
    return _manager.get_or_create(name, config)


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout_seconds: float = 30.0
):
    """
    Decorator para aplicar circuit breaker a uma função.
    
    Uso:
        @circuit_breaker("api_externa")
        async def call_api():
            ...
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        timeout_seconds=timeout_seconds
    )
    cb = get_circuit_breaker(name, config)
    return cb
