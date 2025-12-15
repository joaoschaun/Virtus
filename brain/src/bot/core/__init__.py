"""
VIRTUS Bot Core Module
=======================

Componentes centrais do bot de trading.

Inclui:
- BotState: Gerenciamento de estado do bot
- TradingBot: Bot de trading por símbolo
- TradingEngine: Motor de trading integrado com todos os componentes avançados
"""

from .bot_state import (
    BotState,
    TradingPhase,
    BotStatistics,
    BotContext,
    BotStateManager,
)
from .trading_bot import TradingBot, create_bot
from .trading_engine import (
    TradingEngine,
    TradingMode,
    ExecutionMode,
    TradeDecision,
    EngineStatistics,
)

__all__ = [
    # Bot State
    'BotState',
    'TradingPhase',
    'BotStatistics',
    'BotContext',
    'BotStateManager',
    # Trading Bot
    'TradingBot',
    'create_bot',
    # Trading Engine
    'TradingEngine',
    'TradingMode',
    'ExecutionMode',
    'TradeDecision',
    'EngineStatistics',
]
