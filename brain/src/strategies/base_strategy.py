"""
Base Strategy - Stub
=====================
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from ..core import Signal, Timeframe
except ImportError:
    from core import Signal, Timeframe


@dataclass
class SetupResult:
    """Resultado de setup."""
    name: str
    direction: str  # "buy", "sell"
    score: float
    entry: float
    sl: float
    tp: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        self.metadata = self.metadata or {}


class BaseStrategy(ABC):
    """
    Classe base para todas as estratégias.
    
    Todas as estratégias devem herdar desta classe
    e implementar o método find_setups.
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def find_setups(
        self,
        market_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[SetupResult]:
        """
        Encontra setups válidos.
        
        Args:
            market_data: Dados de mercado atuais
            analysis: Resultado da análise
            
        Returns:
            Lista de setups encontrados
        """
        pass
    
    def validate_setup(self, setup: SetupResult) -> bool:
        """Valida um setup."""
        if not setup.entry or not setup.sl or not setup.tp:
            return False
        if setup.score < 0.5:
            return False
        return True
    
    def get_risk_reward(self, entry: float, sl: float, tp: float) -> float:
        """Calcula risk/reward."""
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        return reward / risk if risk > 0 else 0
