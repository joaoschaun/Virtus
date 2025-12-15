"""
VIRTUS Database Module
======================

Sistema de persistência para o trading system.
"""

from .models import (
    Base,
    Trade,
    PartialExit,
    Signal,
    DailyPerformance,
    AccountSnapshot,
    BotSession,
    Alert,
    MarketData,
    TradeDirection,
    TradeStatus,
    ExitReason,
    SignalType,
    create_all_tables,
    drop_all_tables,
)

from .manager import (
    DatabaseConfig,
    DatabaseManager,
    get_database,
)

from .repositories import (
    TradeRepository,
    SignalRepository,
)

__all__ = [
    # Models
    'Base',
    'Trade',
    'PartialExit',
    'Signal',
    'DailyPerformance',
    'AccountSnapshot',
    'BotSession',
    'Alert',
    'MarketData',
    
    # Enums
    'TradeDirection',
    'TradeStatus',
    'ExitReason',
    'SignalType',
    
    # Manager
    'DatabaseConfig',
    'DatabaseManager',
    'get_database',
    
    # Repositories
    'TradeRepository',
    'SignalRepository',
    
    # Helpers
    'create_all_tables',
    'drop_all_tables',
]
