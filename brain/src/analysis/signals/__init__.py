"""
VIRTUS Signal Analysis Module
==============================

Geração e processamento de sinais de trading.
"""

from .signal_generator import SignalGenerator, SignalComponent, SignalSource
from .economic_calendar import EconomicCalendar, CalendarAnalysisResult, EconomicEvent, EventImpact
from .news_analyzer import NewsAnalyzer, NewsAnalysisResult, NewsItem, NewsImpact, NewsSentiment

__all__ = [
    'SignalGenerator',
    'SignalComponent',
    'SignalSource',
    
    # Economic Calendar
    'EconomicCalendar',
    'CalendarAnalysisResult',
    'EconomicEvent',
    'EventImpact',
    
    # News Analyzer
    'NewsAnalyzer',
    'NewsAnalysisResult',
    'NewsItem',
    'NewsImpact',
    'NewsSentiment',
]
