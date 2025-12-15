"""
Partial Close - Stub
=====================
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PartialCloseLevel:
    """Nível de fechamento parcial."""
    profit_pips: float  # Lucro em pips para ativar
    close_percent: float  # % da posição para fechar
    move_sl_to: Optional[float] = None  # Novo SL (opcional)


@dataclass
class PartialClose:
    """Configuração de fechamento parcial."""
    levels: List[PartialCloseLevel] = None
    
    def __post_init__(self):
        if self.levels is None:
            self.levels = [
                PartialCloseLevel(profit_pips=30, close_percent=50),
                PartialCloseLevel(profit_pips=50, close_percent=25),
            ]
    
    def check_partial_close(
        self,
        entry_price: float,
        current_price: float,
        is_buy: bool,
        already_closed_levels: List[int]
    ) -> Optional[PartialCloseLevel]:
        """Verifica se deve fazer fechamento parcial."""
        if is_buy:
            pips = (current_price - entry_price) * 10000
        else:
            pips = (entry_price - current_price) * 10000
        
        for i, level in enumerate(self.levels):
            if i not in already_closed_levels and pips >= level.profit_pips:
                return level
        
        return None
