"""
BRAIN - Rate Limiter
Controle de rate limiting por provider
"""

import time
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Dict, Optional

from ...core.logger import get_logger

logger = get_logger("brain.budget")


class RateLimiter:
    """
    Rate Limiter usando Sliding Window
    
    Controla requisições por minuto para cada provider.
    """
    
    def __init__(self):
        self._windows: Dict[str, deque] = {}
        self._limits: Dict[str, int] = {}
        self._lock = Lock()
    
    def set_limit(self, provider: str, requests_per_minute: int):
        """Define limite de requisições por minuto"""
        with self._lock:
            self._limits[provider] = requests_per_minute
            if provider not in self._windows:
                self._windows[provider] = deque()
    
    def can_proceed(self, provider: str) -> bool:
        """
        Verifica se pode fazer requisição
        
        Args:
            provider: Nome do provider
            
        Returns:
            True se pode prosseguir
        """
        with self._lock:
            if provider not in self._limits:
                return True
            
            limit = self._limits[provider]
            window = self._windows.get(provider, deque())
            
            # Remover timestamps antigos (> 60 segundos)
            current_time = time.time()
            while window and current_time - window[0] > 60:
                window.popleft()
            
            self._windows[provider] = window
            
            return len(window) < limit
    
    def record_request(self, provider: str):
        """Registra uma requisição"""
        with self._lock:
            if provider not in self._windows:
                self._windows[provider] = deque()
            
            self._windows[provider].append(time.time())
    
    def wait_time(self, provider: str) -> float:
        """
        Retorna tempo de espera necessário em segundos
        
        Returns:
            Tempo em segundos para poder fazer próxima requisição
        """
        with self._lock:
            if provider not in self._limits:
                return 0
            
            limit = self._limits[provider]
            window = self._windows.get(provider, deque())
            
            if len(window) < limit:
                return 0
            
            # Tempo até o request mais antigo expirar
            oldest = window[0]
            wait = 60 - (time.time() - oldest)
            
            return max(0, wait)
    
    def get_usage(self, provider: str) -> Dict[str, int]:
        """Retorna uso atual"""
        with self._lock:
            window = self._windows.get(provider, deque())
            limit = self._limits.get(provider, 0)
            
            # Limpar antigos
            current_time = time.time()
            while window and current_time - window[0] > 60:
                window.popleft()
            
            return {
                "current": len(window),
                "limit": limit,
                "remaining": max(0, limit - len(window))
            }
