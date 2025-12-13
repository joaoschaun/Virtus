# Strategies Module
from .base_strategy import BaseStrategy, StrategyConfig, StrategyState, StrategyFactory
from .scalping.scalping_strategy import ScalpingStrategy
from .trend.trend_strategy import TrendFollowingStrategy

__all__ = [
    'BaseStrategy',
    'StrategyConfig',
    'StrategyState',
    'StrategyFactory',
    'ScalpingStrategy',
    'TrendFollowingStrategy'
]
