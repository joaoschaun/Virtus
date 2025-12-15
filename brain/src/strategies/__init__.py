"""VIRTUS Strategies Module
==========================

Estratégias de trading:
- Scalping: 9 setups de microestrutura
- Trend: 7 setups SMC/MTF
- Reversal: 8 setups de reversão
- Event: 5 setups de eventos

Factory com auto-registro e combinador de sinais.
"""

from .base_strategy import BaseStrategy, SetupResult
from .strategy_factory import (
    StrategyFactory,
    StrategyRegistry,
    StrategyConfig,
    StrategyInfo,
    StrategyCategory,
    StrategyStatus,
    StrategyCombiner,
    register_strategy,
)
from .scalping.scalping_strategy import (
    ScalpingStrategy,
    ScalpingSetup,
    ScalpingConfig,
)
from .trend.trend_strategy import (
    TrendStrategy,
    TrendSetup,
    TrendConfig,
)
from .reversal.reversal_strategy import (
    ReversalStrategy,
    ReversalSetup,
    ReversalConfig,
)
from .event.event_strategy import (
    EventStrategy,
    EventSetup,
    EventConfig,
)

__all__ = [
    # Base
    'BaseStrategy',
    'SetupResult',
    # Factory & Registry
    'StrategyFactory',
    'StrategyRegistry',
    'StrategyConfig',
    'StrategyInfo',
    'StrategyCategory',
    'StrategyStatus',
    'StrategyCombiner',
    'register_strategy',
    # Scalping
    'ScalpingStrategy',
    'ScalpingSetup',
    'ScalpingConfig',
    # Trend
    'TrendStrategy',
    'TrendSetup',
    'TrendConfig',
    # Reversal
    'ReversalStrategy',
    'ReversalSetup',
    'ReversalConfig',
    # Event
    'EventStrategy',
    'EventSetup',
    'EventConfig',
]
