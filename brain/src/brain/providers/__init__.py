"""
VIRTUS Brain - Providers Module
================================

Providers para APIs externas de dados.
"""

from .base_provider import (
    BaseProvider,
    NewsProvider,
    SentimentProvider,
    CalendarProvider,
    MarketDataProvider
)
from .forexnews_provider import ForexNewsProvider
from .finnhub_provider import FinnhubProvider
from .twelvedata_provider import TwelveDataProvider
from .fmp_provider import FMPProvider
from .cftc_provider import CFTCProvider

__all__ = [
    # Base
    'BaseProvider',
    'NewsProvider',
    'SentimentProvider',
    'CalendarProvider',
    'MarketDataProvider',
    
    # Providers
    'ForexNewsProvider',
    'FinnhubProvider',
    'TwelveDataProvider',
    'FMPProvider',
    'CFTCProvider',
]
