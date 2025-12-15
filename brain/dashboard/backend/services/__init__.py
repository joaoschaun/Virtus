"""
VIRTUS Dashboard - Backend Services
====================================
"""

from .news_service import (
    NewsService,
    TextToSpeechService,
    NewsItem,
    NewsCategory,
    NewsPriority,
    news_service,
)

__all__ = [
    'NewsService',
    'TextToSpeechService',
    'NewsItem',
    'NewsCategory',
    'NewsPriority',
    'news_service',
]
