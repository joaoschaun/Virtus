"""VIRTUS Position Exits Module
==============================

Gerenciamento completo de saídas com múltiplos tipos de trailing stop.

Tipos de Trailing Stop:
- FIXED_PIPS: Distância fixa em pips
- ATR_BASED: Baseado em ATR (adaptativo)
- PERCENTAGE: Percentual do preço
- CHANDELIER: Chandelier Exit
- PARABOLIC_SAR: Parabolic SAR
- SWING_BASED: Baseado em swing points
- STEP_TRAIL: Move em incrementos fixos
"""

from .trailing_stop import (
    TrailingStop,
    TrailingStopType,
    TrailingStopConfig,
    TrailingStopState,
)

try:
    from .breakeven import Breakeven
except ImportError:
    Breakeven = None

try:
    from .partial_close import PartialClose
except ImportError:
    PartialClose = None

from .exit_manager import (
    ExitManager,
    ExitSignal,
    TrailingStopType as TrailingType,  # Alias para compatibilidade
    ExitReason,
    TrailingStopConfig as TrailingConfig,  # Alias para compatibilidade
    PartialExitConfig,
)

__all__ = [
    # Trailing Stop Module
    'TrailingStop',
    'TrailingStopType',
    'TrailingStopConfig',
    'TrailingStopState',
    # Breakeven & Partial
    'Breakeven',
    'PartialClose',
    # Exit Manager
    'ExitManager',
    'ExitSignal',
    'TrailingType',
    'ExitReason',
    'TrailingConfig',
    'PartialExitConfig',
]
