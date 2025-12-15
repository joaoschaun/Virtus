"""VIRTUS Trend Strategy Module
=============================

Estratégia de trend following com 7 setups SMC/MTF.
"""

# Legacy
try:
    from .trend_following import TrendFollowingStrategy
    from .breakout import BreakoutStrategy
except ImportError:
    pass

# New advanced strategy
from .trend_strategy import (
    TrendStrategy,
    TrendSetup,
    TrendConfig,
)

__all__ = [
    'TrendStrategy',
    'TrendSetup',
    'TrendConfig',
]
