"""
VIRTUS Brain Analyzers Module
==============================

Analisadores centrais do Brain:
- NewsAnalyzer: Processa e categoriza notícias de mercado
- SentimentAnalyzer: Agrega sentimento de múltiplas fontes
- MacroAnalyzer: Analisa indicadores macroeconômicos
- CorrelationAnalyzer: Detecta correlações e divergências
"""

from .news_analyzer import (
    NewsAnalyzer,
    NewsItem,
    NewsSummary,
    NewsImpact,
    NewsSentiment,
    NewsCategory,
)
from .sentiment_analyzer import (
    SentimentAnalyzer,
    SentimentReading,
    CompositeSentiment,
    SentimentConfig,
    SentimentSource,
    MarketMood,
)
from .macro_analyzer import (
    MacroAnalyzer,
    EconomicEvent,
    MacroSnapshot,
    MacroConfig,
    EventImpact,
    EventType,
    Currency,
)
from .correlation_analyzer import (
    CorrelationAnalyzer,
    CorrelationPair,
    CorrelationMatrix,
    Divergence,
    CorrelationType,
    DivergenceType,
)

__all__ = [
    # News
    'NewsAnalyzer',
    'NewsItem',
    'NewsSummary',
    'NewsImpact',
    'NewsSentiment',
    'NewsCategory',
    # Sentiment
    'SentimentAnalyzer',
    'SentimentReading',
    'CompositeSentiment',
    'SentimentConfig',
    'SentimentSource',
    'MarketMood',
    # Macro
    'MacroAnalyzer',
    'EconomicEvent',
    'MacroSnapshot',
    'MacroConfig',
    'EventImpact',
    'EventType',
    'Currency',
    # Correlation
    'CorrelationAnalyzer',
    'CorrelationPair',
    'CorrelationMatrix',
    'Divergence',
    'CorrelationType',
    'DivergenceType',
]
