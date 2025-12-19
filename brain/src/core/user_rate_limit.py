"""
VIRTUS - Rate Limiting por Usuário
===================================

Sistema de rate limiting baseado em usuário/token para o dashboard.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import logging
from functools import wraps

from fastapi import Request, HTTPException, status

logger = logging.getLogger("virtus.user_rate_limit")


@dataclass
class UserRateLimitConfig:
    """Configuração de rate limit por usuário."""
    # Limites padrão
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    
    # Limites por endpoint (opcional)
    endpoint_limits: Dict[str, int] = field(default_factory=lambda: {
        "/api/auth/login": 5,           # 5 tentativas por minuto
        "/api/trade": 30,               # 30 trades por minuto
        "/api/brain/trade": 30,
        "/api/positions": 120,          # 2 por segundo
        "/api/analysis": 60,            # 1 por segundo
    })
    
    # Burst
    burst_multiplier: float = 2.0
    
    # Whitelist
    whitelist_ips: list = field(default_factory=lambda: ["127.0.0.1", "localhost"])
    whitelist_users: list = field(default_factory=lambda: ["admin"])
    
    # Penalidades
    penalty_multiplier: float = 2.0
    penalty_duration_minutes: int = 5
    max_penalties: int = 3
    ban_duration_minutes: int = 60


@dataclass
class UserRateState:
    """Estado de rate limiting de um usuário."""
    user_id: str
    requests_minute: int = 0
    requests_hour: int = 0
    requests_day: int = 0
    minute_window_start: float = 0
    hour_window_start: float = 0
    day_window_start: float = 0
    penalties: int = 0
    penalty_until: Optional[float] = None
    banned_until: Optional[float] = None
    endpoint_counts: Dict[str, int] = field(default_factory=dict)
    endpoint_window_starts: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "requests_minute": self.requests_minute,
            "requests_hour": self.requests_hour,
            "requests_day": self.requests_day,
            "penalties": self.penalties,
            "is_penalized": self.penalty_until is not None and time.time() < self.penalty_until,
            "is_banned": self.banned_until is not None and time.time() < self.banned_until,
        }


class UserRateLimiter:
    """
    Rate limiter baseado em usuário.
    
    Uso:
        limiter = UserRateLimiter()
        
        # Como middleware
        @app.middleware("http")
        async def rate_limit(request, call_next):
            user = get_user(request)
            if not limiter.allow(user, request.url.path):
                raise HTTPException(429, "Rate limit exceeded")
            return await call_next(request)
    """
    
    def __init__(self, config: Optional[UserRateLimitConfig] = None):
        self.config = config or UserRateLimitConfig()
        self._states: Dict[str, UserRateState] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def _get_state(self, user_id: str) -> UserRateState:
        """Obtém ou cria estado do usuário."""
        if user_id not in self._states:
            self._states[user_id] = UserRateState(user_id=user_id)
        return self._states[user_id]
    
    def _reset_windows(self, state: UserRateState):
        """Reseta janelas de tempo se necessário."""
        now = time.time()
        
        # Reset minuto
        if now - state.minute_window_start >= 60:
            state.requests_minute = 0
            state.minute_window_start = now
            state.endpoint_counts.clear()
            state.endpoint_window_starts.clear()
        
        # Reset hora
        if now - state.hour_window_start >= 3600:
            state.requests_hour = 0
            state.hour_window_start = now
        
        # Reset dia
        if now - state.day_window_start >= 86400:
            state.requests_day = 0
            state.day_window_start = now
    
    def allow(
        self,
        user_id: str,
        endpoint: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Verifica se o request é permitido.
        
        Returns:
            True se permitido, False se deve bloquear
        """
        # Whitelist check
        if ip_address in self.config.whitelist_ips:
            return True
        if user_id in self.config.whitelist_users:
            return True
        
        state = self._get_state(user_id)
        self._reset_windows(state)
        now = time.time()
        
        # Verifica ban
        if state.banned_until and now < state.banned_until:
            logger.warning(f"User {user_id} is banned until {datetime.fromtimestamp(state.banned_until)}")
            return False
        
        # Verifica penalidade
        limit_multiplier = 1.0
        if state.penalty_until and now < state.penalty_until:
            limit_multiplier = 1.0 / self.config.penalty_multiplier
        
        # Calcula limites efetivos
        minute_limit = int(self.config.requests_per_minute * limit_multiplier)
        hour_limit = int(self.config.requests_per_hour * limit_multiplier)
        day_limit = int(self.config.requests_per_day * limit_multiplier)
        
        # Verifica limite por endpoint
        if endpoint and endpoint in self.config.endpoint_limits:
            endpoint_limit = int(self.config.endpoint_limits[endpoint] * limit_multiplier)
            
            # Reset window do endpoint
            if endpoint not in state.endpoint_window_starts:
                state.endpoint_window_starts[endpoint] = now
                state.endpoint_counts[endpoint] = 0
            elif now - state.endpoint_window_starts[endpoint] >= 60:
                state.endpoint_window_starts[endpoint] = now
                state.endpoint_counts[endpoint] = 0
            
            if state.endpoint_counts.get(endpoint, 0) >= endpoint_limit:
                self._apply_penalty(state, f"endpoint limit {endpoint}")
                return False
        
        # Verifica limites globais
        if state.requests_minute >= minute_limit:
            self._apply_penalty(state, "minute limit")
            return False
        
        if state.requests_hour >= hour_limit:
            self._apply_penalty(state, "hour limit")
            return False
        
        if state.requests_day >= day_limit:
            self._apply_penalty(state, "day limit")
            return False
        
        # Incrementa contadores
        state.requests_minute += 1
        state.requests_hour += 1
        state.requests_day += 1
        
        if endpoint:
            state.endpoint_counts[endpoint] = state.endpoint_counts.get(endpoint, 0) + 1
        
        return True
    
    def _apply_penalty(self, state: UserRateState, reason: str):
        """Aplica penalidade ao usuário."""
        state.penalties += 1
        logger.warning(f"Rate limit penalty for {state.user_id}: {reason} (penalty #{state.penalties})")
        
        if state.penalties >= self.config.max_penalties:
            # Ban
            state.banned_until = time.time() + (self.config.ban_duration_minutes * 60)
            logger.error(f"User {state.user_id} BANNED for {self.config.ban_duration_minutes} minutes")
        else:
            # Penalidade temporária
            state.penalty_until = time.time() + (self.config.penalty_duration_minutes * 60)
    
    def get_remaining(self, user_id: str) -> Dict[str, int]:
        """Retorna limites restantes."""
        state = self._get_state(user_id)
        self._reset_windows(state)
        
        return {
            "minute_remaining": max(0, self.config.requests_per_minute - state.requests_minute),
            "hour_remaining": max(0, self.config.requests_per_hour - state.requests_hour),
            "day_remaining": max(0, self.config.requests_per_day - state.requests_day),
        }
    
    def get_user_state(self, user_id: str) -> Dict[str, Any]:
        """Retorna estado do usuário."""
        state = self._get_state(user_id)
        return state.to_dict()
    
    def reset_user(self, user_id: str):
        """Reseta estado do usuário (admin only)."""
        if user_id in self._states:
            del self._states[user_id]
            logger.info(f"Reset rate limit state for {user_id}")
    
    def unban_user(self, user_id: str):
        """Remove ban do usuário (admin only)."""
        state = self._get_state(user_id)
        state.banned_until = None
        state.penalties = 0
        state.penalty_until = None
        logger.info(f"Unbanned user {user_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas globais."""
        now = time.time()
        
        active_users = len(self._states)
        penalized = sum(1 for s in self._states.values() if s.penalty_until and now < s.penalty_until)
        banned = sum(1 for s in self._states.values() if s.banned_until and now < s.banned_until)
        
        return {
            "active_users": active_users,
            "penalized_users": penalized,
            "banned_users": banned,
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_hour": self.config.requests_per_hour,
                "requests_per_day": self.config.requests_per_day,
            }
        }
    
    async def cleanup(self):
        """Remove estados inativos."""
        now = time.time()
        inactive_threshold = 3600  # 1 hora
        
        to_remove = []
        for user_id, state in self._states.items():
            if (now - state.minute_window_start > inactive_threshold and
                state.requests_minute == 0 and
                not state.banned_until):
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self._states[user_id]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} inactive rate limit states")


# Instância global
user_rate_limiter = UserRateLimiter()


# ============================================================================
# MIDDLEWARE E DECORADORES
# ============================================================================

async def rate_limit_middleware(request: Request, call_next):
    """Middleware FastAPI para rate limiting."""
    # Obtém usuário do request
    user_id = "anonymous"
    if hasattr(request.state, "user"):
        user_id = request.state.user
    elif "authorization" in request.headers:
        # Usa token como identificador
        user_id = request.headers["authorization"][:32]
    
    ip_address = request.client.host if request.client else None
    endpoint = request.url.path
    
    if not user_rate_limiter.allow(user_id, endpoint, ip_address):
        remaining = user_rate_limiter.get_remaining(user_id)
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "remaining": remaining,
                "retry_after": 60,  # segundos
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(user_rate_limiter.config.requests_per_minute),
                "X-RateLimit-Remaining": str(remaining["minute_remaining"]),
            }
        )
    
    response = await call_next(request)
    
    # Adiciona headers de rate limit
    remaining = user_rate_limiter.get_remaining(user_id)
    response.headers["X-RateLimit-Limit"] = str(user_rate_limiter.config.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(remaining["minute_remaining"])
    
    return response


def rate_limited(limit_per_minute: int = 60):
    """
    Decorador para rate limiting em endpoints específicos.
    
    Uso:
        @app.get("/api/data")
        @rate_limited(30)  # 30 requests por minuto
        async def get_data():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Encontra o request nos argumentos
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                user_id = getattr(request.state, "user", "anonymous")
                endpoint = request.url.path
                
                # Configura limite específico temporariamente
                original_limit = user_rate_limiter.config.endpoint_limits.get(endpoint)
                user_rate_limiter.config.endpoint_limits[endpoint] = limit_per_minute
                
                try:
                    if not user_rate_limiter.allow(user_id, endpoint):
                        raise HTTPException(
                            status_code=429,
                            detail="Rate limit exceeded for this endpoint"
                        )
                finally:
                    # Restaura limite original
                    if original_limit:
                        user_rate_limiter.config.endpoint_limits[endpoint] = original_limit
                    elif endpoint in user_rate_limiter.config.endpoint_limits:
                        del user_rate_limiter.config.endpoint_limits[endpoint]
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# ROUTES PARA ADMIN
# ============================================================================

from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/admin/rate-limit", tags=["Rate Limit Admin"])


@router.get("/stats")
async def get_rate_limit_stats():
    """Retorna estatísticas de rate limiting."""
    return user_rate_limiter.get_stats()


@router.get("/user/{user_id}")
async def get_user_rate_state(user_id: str):
    """Retorna estado de rate limit de um usuário."""
    return user_rate_limiter.get_user_state(user_id)


@router.post("/user/{user_id}/reset")
async def reset_user_rate_limit(user_id: str):
    """Reseta rate limit de um usuário."""
    user_rate_limiter.reset_user(user_id)
    return {"message": f"Rate limit reset for {user_id}"}


@router.post("/user/{user_id}/unban")
async def unban_user(user_id: str):
    """Remove ban de um usuário."""
    user_rate_limiter.unban_user(user_id)
    return {"message": f"User {user_id} unbanned"}


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        limiter = UserRateLimiter(UserRateLimitConfig(
            requests_per_minute=5,
        ))
        
        user = "test_user"
        
        # Simula requests
        for i in range(10):
            allowed = limiter.allow(user, "/api/test")
            remaining = limiter.get_remaining(user)
            print(f"Request {i+1}: {'✅' if allowed else '❌'} | Remaining: {remaining['minute_remaining']}")
            await asyncio.sleep(0.1)
        
        print("\nUser state:", limiter.get_user_state(user))
        print("Stats:", limiter.get_stats())
    
    asyncio.run(test())
