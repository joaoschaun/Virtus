"""
VIRTUS MT5 Module
==================

Interface com MetaTrader 5 para trading.
"""

from .mt5_connection import MT5Connection, get_mt5_connection
from .mt5_data import MT5DataService, get_mt5_data
from .mt5_orders import MT5OrderManager, get_mt5_orders

__all__ = [
    'MT5Connection',
    'get_mt5_connection',
    'MT5DataService',
    'get_mt5_data',
    'MT5OrderManager',
    'get_mt5_orders',
]
