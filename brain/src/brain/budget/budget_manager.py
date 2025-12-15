"""
VIRTUS Brain - Budget Manager
==============================

Controle de orçamento de chamadas de API.
Implementa limites por período, alertas e fallbacks.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from ...core.logger import get_logger
from ...core.exceptions import BudgetExceededError

logger = get_logger("budget")


class BudgetPeriod(Enum):
    """Período de orçamento"""
    DAILY = "daily"
    MONTHLY = "monthly"
    MINUTE = "minute"


@dataclass
class ProviderBudget:
    """Orçamento de um provider"""
    provider: str
    
    # Limites
    daily_limit: int = 1000
    monthly_limit: int = 25000
    minute_limit: int = 60
    
    # Uso atual
    daily_usage: int = 0
    monthly_usage: int = 0
    minute_usage: int = 0
    
    # Timestamps
    daily_reset: datetime = field(default_factory=datetime.now)
    monthly_reset: datetime = field(default_factory=datetime.now)
    minute_reset: datetime = field(default_factory=datetime.now)
    
    # Status
    is_blocked: bool = False
    block_reason: str = ""
    
    @property
    def daily_remaining(self) -> int:
        return max(0, self.daily_limit - self.daily_usage)
    
    @property
    def monthly_remaining(self) -> int:
        return max(0, self.monthly_limit - self.monthly_usage)
    
    @property
    def minute_remaining(self) -> int:
        return max(0, self.minute_limit - self.minute_usage)
    
    @property
    def daily_usage_percent(self) -> float:
        return (self.daily_usage / self.daily_limit * 100) if self.daily_limit > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'provider': self.provider,
            'daily': {
                'limit': self.daily_limit,
                'used': self.daily_usage,
                'remaining': self.daily_remaining,
                'percent': f"{self.daily_usage_percent:.1f}%"
            },
            'monthly': {
                'limit': self.monthly_limit,
                'used': self.monthly_usage,
                'remaining': self.monthly_remaining,
            },
            'is_blocked': self.is_blocked,
            'block_reason': self.block_reason,
        }


class BudgetManager:
    """
    Gerenciador central de orçamento de APIs.
    
    Features:
    - Limites por minuto, dia e mês
    - Auto-reset de contadores
    - Alertas de uso
    - Fallback automático para providers alternativos
    """
    
    # Limites padrão por provider
    DEFAULT_LIMITS = {
        'forexnews': {'daily': 1000, 'monthly': 25000, 'minute': 60},
        'finnhub': {'daily': 60, 'monthly': 1500, 'minute': 30},
        'twelvedata': {'daily': 800, 'monthly': 20000, 'minute': 8},
        'fmp': {'daily': 250, 'monthly': 6000, 'minute': 10},
        'finazon': {'daily': 1000, 'monthly': 25000, 'minute': 60},
    }
    
    # Mapeamento de fallbacks
    FALLBACK_MAP = {
        'forexnews': ['finnhub', 'fmp'],
        'finnhub': ['forexnews', 'fmp'],
        'twelvedata': ['fmp', 'finazon'],
        'fmp': ['twelvedata', 'finazon'],
        'finazon': ['fmp', 'twelvedata'],
    }
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/brain")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._budgets: Dict[str, ProviderBudget] = {}
        self._lock = asyncio.Lock()
        
        # Callbacks de alerta
        self._alert_callbacks: List[callable] = []
        
        # Thresholds de alerta
        self.warning_threshold = 0.7  # 70%
        self.critical_threshold = 0.9  # 90%
        
        # Inicializa providers
        self._initialize_budgets()
        
        # Carrega estado salvo
        self._load_state()
    
    def _initialize_budgets(self):
        """Inicializa orçamentos para todos os providers"""
        for provider, limits in self.DEFAULT_LIMITS.items():
            self._budgets[provider] = ProviderBudget(
                provider=provider,
                daily_limit=limits['daily'],
                monthly_limit=limits['monthly'],
                minute_limit=limits['minute'],
            )
    
    def configure_budget(
        self,
        provider: str,
        daily_limit: Optional[int] = None,
        monthly_limit: Optional[int] = None,
        minute_limit: Optional[int] = None
    ):
        """Configura limites de um provider"""
        if provider not in self._budgets:
            self._budgets[provider] = ProviderBudget(provider=provider)
        
        budget = self._budgets[provider]
        if daily_limit is not None:
            budget.daily_limit = daily_limit
        if monthly_limit is not None:
            budget.monthly_limit = monthly_limit
        if minute_limit is not None:
            budget.minute_limit = minute_limit
        
        logger.info(f"Budget configurado: {provider} - D:{daily_limit} M:{monthly_limit} m:{minute_limit}")
    
    def _check_reset(self, budget: ProviderBudget):
        """Verifica e reseta contadores se necessário"""
        now = datetime.now()
        
        # Reset de minuto
        if (now - budget.minute_reset).total_seconds() >= 60:
            budget.minute_usage = 0
            budget.minute_reset = now
        
        # Reset diário
        if (now - budget.daily_reset).days >= 1:
            budget.daily_usage = 0
            budget.daily_reset = now.replace(hour=0, minute=0, second=0, microsecond=0)
            budget.is_blocked = False
            budget.block_reason = ""
        
        # Reset mensal
        if now.month != budget.monthly_reset.month:
            budget.monthly_usage = 0
            budget.monthly_reset = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    async def can_make_request(self, provider: str) -> bool:
        """Verifica se pode fazer request para um provider"""
        async with self._lock:
            if provider not in self._budgets:
                return True
            
            budget = self._budgets[provider]
            self._check_reset(budget)
            
            if budget.is_blocked:
                return False
            
            return (
                budget.minute_remaining > 0 and
                budget.daily_remaining > 0 and
                budget.monthly_remaining > 0
            )
    
    async def register_request(self, provider: str, count: int = 1):
        """Registra uma requisição feita"""
        async with self._lock:
            if provider not in self._budgets:
                return
            
            budget = self._budgets[provider]
            self._check_reset(budget)
            
            budget.minute_usage += count
            budget.daily_usage += count
            budget.monthly_usage += count
            
            # Verifica alertas
            await self._check_alerts(budget)
            
            # Salva estado
            self._save_state()
    
    async def _check_alerts(self, budget: ProviderBudget):
        """Verifica e dispara alertas se necessário"""
        usage_percent = budget.daily_usage_percent / 100
        
        if usage_percent >= self.critical_threshold:
            budget.is_blocked = True
            budget.block_reason = f"Limite crítico atingido ({usage_percent:.0%})"
            
            await self._trigger_alert(
                level="critical",
                provider=budget.provider,
                message=f"🚨 CRÍTICO: {budget.provider} em {usage_percent:.0%} do limite diário!"
            )
            
        elif usage_percent >= self.warning_threshold:
            await self._trigger_alert(
                level="warning",
                provider=budget.provider,
                message=f"⚠️ ALERTA: {budget.provider} em {usage_percent:.0%} do limite diário"
            )
    
    async def _trigger_alert(self, level: str, provider: str, message: str):
        """Dispara callbacks de alerta"""
        logger.warning(message)
        
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(level, provider, message)
                else:
                    callback(level, provider, message)
            except Exception as e:
                logger.error(f"Erro em callback de alerta: {e}")
    
    def add_alert_callback(self, callback: callable):
        """Adiciona callback para alertas de budget"""
        self._alert_callbacks.append(callback)
    
    async def get_fallback_provider(self, provider: str) -> Optional[str]:
        """Retorna provider alternativo disponível"""
        fallbacks = self.FALLBACK_MAP.get(provider, [])
        
        for fallback in fallbacks:
            if await self.can_make_request(fallback):
                logger.info(f"Usando fallback: {fallback} para {provider}")
                return fallback
        
        return None
    
    def get_budget_status(self, provider: str) -> Optional[Dict[str, Any]]:
        """Retorna status do budget de um provider"""
        if provider not in self._budgets:
            return None
        
        budget = self._budgets[provider]
        self._check_reset(budget)
        return budget.to_dict()
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Retorna status de todos os providers"""
        for budget in self._budgets.values():
            self._check_reset(budget)
        
        return {
            provider: budget.to_dict()
            for provider, budget in self._budgets.items()
        }
    
    # ========================================================================
    # PERSISTÊNCIA
    # ========================================================================
    
    def _save_state(self):
        """Salva estado em disco"""
        state_file = self.data_dir / "budget_state.json"
        
        state = {}
        for provider, budget in self._budgets.items():
            state[provider] = {
                'daily_usage': budget.daily_usage,
                'monthly_usage': budget.monthly_usage,
                'daily_reset': budget.daily_reset.isoformat(),
                'monthly_reset': budget.monthly_reset.isoformat(),
            }
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Erro ao salvar estado de budget: {e}")
    
    def _load_state(self):
        """Carrega estado do disco"""
        state_file = self.data_dir / "budget_state.json"
        
        if not state_file.exists():
            return
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            for provider, data in state.items():
                if provider in self._budgets:
                    budget = self._budgets[provider]
                    budget.daily_usage = data.get('daily_usage', 0)
                    budget.monthly_usage = data.get('monthly_usage', 0)
                    budget.daily_reset = datetime.fromisoformat(data.get('daily_reset', datetime.now().isoformat()))
                    budget.monthly_reset = datetime.fromisoformat(data.get('monthly_reset', datetime.now().isoformat()))
            
            logger.debug("Estado de budget carregado")
            
        except Exception as e:
            logger.warning(f"Erro ao carregar estado de budget: {e}")
    
    # ========================================================================
    # CONTEXT MANAGER
    # ========================================================================
    
    async def request(self, provider: str):
        """
        Context manager para fazer request controlada.
        
        Usage:
            async with budget_manager.request('forexnews') as allowed:
                if allowed:
                    # fazer request
        """
        return BudgetContext(self, provider)


class BudgetContext:
    """Context manager para requests com budget"""
    
    def __init__(self, manager: BudgetManager, provider: str):
        self.manager = manager
        self.provider = provider
        self.allowed = False
    
    async def __aenter__(self) -> bool:
        self.allowed = await self.manager.can_make_request(self.provider)
        if not self.allowed:
            logger.warning(f"Request bloqueada para {self.provider} - budget excedido")
        return self.allowed
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.allowed and exc_type is None:
            await self.manager.register_request(self.provider)
        return False


# Instância global
_budget_manager: Optional[BudgetManager] = None


def get_budget_manager(data_dir: Optional[Path] = None) -> BudgetManager:
    """Retorna instância global do budget manager"""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = BudgetManager(data_dir=data_dir)
    return _budget_manager
