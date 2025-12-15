"""VIRTUS Reversal Strategy Module
================================

Estratégia de reversão com 8 setups.
"""

# Legacy
try:
    from .mean_reversion import MeanReversionStrategy
    from .range_trading import RangeTradingStrategy
except ImportError:
    pass

# New advanced strategy
from .reversal_strategy import (
    ReversalStrategy,
    ReversalSetup,
    ReversalConfig,
)

__all__ = [
    'ReversalStrategy',
    'ReversalSetup',
    'ReversalConfig',
]
