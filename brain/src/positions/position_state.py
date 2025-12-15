"""
Position State - Stub
======================
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class StateType(Enum):
    """Tipos de estado."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PositionState:
    """Estado de uma posição."""
    ticket: int
    symbol: str
    state: StateType = StateType.HEALTHY
    
    # Tracking
    entry_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    
    # P&L tracking
    current_profit: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    
    # Events
    events: List[str] = field(default_factory=list)
    
    def update(self, profit: float) -> None:
        """Atualiza estado."""
        self.current_profit = profit
        self.max_profit = max(self.max_profit, profit)
        self.max_loss = min(self.max_loss, profit)
        self.last_update = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'ticket': self.ticket,
            'symbol': self.symbol,
            'state': self.state.value,
            'current_profit': self.current_profit,
            'max_profit': self.max_profit,
            'max_loss': self.max_loss,
        }
