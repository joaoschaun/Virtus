"""
VIRTUS Advisor Module
======================

Consultor de mercado - briefings, análises e alertas via Telegram.
"""

from .market_advisor import MarketAdvisor, get_advisor

__all__ = [
    'MarketAdvisor',
    'get_advisor',
]
