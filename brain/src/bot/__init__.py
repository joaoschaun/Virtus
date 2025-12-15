"""
VIRTUS Bot Module
==================

Sistema de bots de trading multi-mercado.
Suporta: Forex, Arbitragem, Crypto, Stocks, etc.
"""

from .core import (
    BotState,
    TradingPhase,
    BotStatistics,
    BotContext,
    BotStateManager,
    TradingBot,
    create_bot,
)
from .health import BotHealthMonitor, BotHealth, HealthStatus

# Novo sistema multi-bot
from .base import (
    BaseBot,
    BotConfig,
    BotType,
    BotStatus,
    BotMetrics,
    MarketType,
)
from .registry import BotRegistry, bot_registry, AggregatedMetrics
from .types import (
    ForexBot,
    ArbitrageBot,
    CryptoBot,
    StocksBot,
    register_all_bot_types,
)

__all__ = [
    # Core (legado)
    'BotState',
    'TradingPhase',
    'BotStatistics',
    'BotContext',
    'BotStateManager',
    'TradingBot',
    'create_bot',
    # Health
    'BotHealthMonitor',
    'BotHealth',
    'HealthStatus',
    # Base Multi-Bot
    'BaseBot',
    'BotConfig',
    'BotType',
    'BotStatus',
    'BotMetrics',
    'MarketType',
    # Registry
    'BotRegistry',
    'bot_registry',
    'AggregatedMetrics',
    # Bot Types
    'ForexBot',
    'ArbitrageBot',
    'CryptoBot',
    'StocksBot',
    'register_all_bot_types',]