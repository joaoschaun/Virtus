"""
Breakeven - Stub
=================
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Breakeven:
    """Configuração de break-even."""
    trigger_pips: float = 20.0  # Ativar quando lucro >= X pips
    offset_pips: float = 2.0    # Mover SL para entry + offset
    
    def should_activate(
        self,
        entry_price: float,
        current_price: float,
        is_buy: bool
    ) -> bool:
        """Verifica se deve ativar break-even."""
        if is_buy:
            pips = (current_price - entry_price) * 10000
        else:
            pips = (entry_price - current_price) * 10000
        
        return pips >= self.trigger_pips
    
    def get_breakeven_level(
        self,
        entry_price: float,
        is_buy: bool
    ) -> float:
        """Calcula nível de break-even."""
        offset = self.offset_pips * 0.0001
        if is_buy:
            return entry_price + offset
        else:
            return entry_price - offset
