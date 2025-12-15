"""
VIRTUS Dashboard Backend - Routes Module
========================================
"""

from .mt5_routes import router as mt5_router
from .news_routes import router as news_router
from .multi_bot_routes import router as multi_bot_router

__all__ = [
    "mt5_router",
    "news_router", 
    "multi_bot_router",
]
