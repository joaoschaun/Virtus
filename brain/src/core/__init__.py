"""
VIRTUS Core Module
==================

Módulo central com utilitários fundamentais do sistema.
"""

from .config import Config, get_config, BotConfig
from .logger import VirtusLogger, get_logger
from .types import (
    OrderType, PositionStatus, SignalType, SignalDirection, SignalStrength,
    Timeframe, MarketRegime, SentimentLevel, NewsImpact, BotStatus,
    Signal, Position, TechnicalAnalysis, SmartMoneyAnalysis,
    NewsItem, MarketSentiment, EconomicEvent,
    DailyPerformance, GlobalPerformance, DailyBriefing,
    RiskConfig
)
from .exceptions import (
    VirtusError, ConfigurationError, ConfigNotFoundError, InvalidConfigError,
    MT5Error, MT5ConnectionError, MT5AuthenticationError, MT5OrderError,
    APIError, APIConnectionError, APIRateLimitError, APIAuthenticationError,
    BrainError, CacheError, BudgetExceededError, ProviderUnavailableError,
    BotError, BotStartupError, BotNotFoundError,
    StrategyError, InvalidSignalError,
    PositionError, PositionNotFoundError, MaxPositionsExceededError,
    RiskError, RiskLimitExceededError, DrawdownLimitError,
    AnalysisError, InsufficientDataError,
    MLError, ModelNotFoundError, PredictionError,
    TelegramError, TelegramConnectionError,
    DatabaseError, DatabaseConnectionError,
    OrchestratorError
)
from .scheduler import Scheduler, get_scheduler, periodic, daily

__all__ = [
    # Config
    'Config', 'get_config', 'BotConfig',
    
    # Logger
    'VirtusLogger', 'get_logger',
    
    # Types - Enums
    'OrderType', 'PositionStatus', 'SignalType', 'SignalDirection', 'SignalStrength',
    'Timeframe', 'MarketRegime', 'SentimentLevel', 'NewsImpact', 'BotStatus',
    
    # Types - Data Classes
    'Signal', 'Position', 'TechnicalAnalysis', 'SmartMoneyAnalysis',
    'NewsItem', 'MarketSentiment', 'EconomicEvent',
    'DailyPerformance', 'GlobalPerformance', 'DailyBriefing',
    'RiskConfig',
    
    # Exceptions
    'VirtusError', 'ConfigurationError', 'ConfigNotFoundError', 'InvalidConfigError',
    'MT5Error', 'MT5ConnectionError', 'MT5AuthenticationError', 'MT5OrderError',
    'APIError', 'APIConnectionError', 'APIRateLimitError', 'APIAuthenticationError',
    'BrainError', 'CacheError', 'BudgetExceededError', 'ProviderUnavailableError',
    'BotError', 'BotStartupError', 'BotNotFoundError',
    'StrategyError', 'InvalidSignalError',
    'PositionError', 'PositionNotFoundError', 'MaxPositionsExceededError',
    'RiskError', 'RiskLimitExceededError', 'DrawdownLimitError',
    'AnalysisError', 'InsufficientDataError',
    'MLError', 'ModelNotFoundError', 'PredictionError',
    'TelegramError', 'TelegramConnectionError',
    'DatabaseError', 'DatabaseConnectionError',
    'OrchestratorError',
    
    # Scheduler
    'Scheduler', 'get_scheduler', 'periodic', 'daily',
]
