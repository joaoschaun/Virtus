"""
VIRTUS Market Analysis Module
==============================

Análise de condições de mercado e multi-timeframe.
"""

from .mtf_analyzer import (
    MultiTimeframeAnalyzer,
    TimeframeBias,
    SignalStrength,
    TimeframeAnalysis,
    MTFConfluence,
    MTFAnalysisResult,
)

from .market_regime import (
    MarketRegimeDetector,
    MarketRegime,
    RegimeAnalysisResult,
    RegimeParameters,
)

from .session_analyzer import (
    SessionAnalyzer,
    TradingSession,
    SessionQuality,
    SessionAnalysisResult,
    SessionConfig,
)

from .macro_context_analyzer import (
    MacroContextAnalyzer,
    MacroRegime,
    DollarStrength,
    VIXLevel,
    MacroAnalysisResult,
    MacroData,
)

__all__ = [
    # MTF
    'MultiTimeframeAnalyzer',
    'TimeframeBias',
    'SignalStrength',
    'TimeframeAnalysis',
    'MTFConfluence',
    'MTFAnalysisResult',
    
    # Market Regime
    'MarketRegimeDetector',
    'MarketRegime',
    'RegimeAnalysisResult',
    'RegimeParameters',
    
    # Session
    'SessionAnalyzer',
    'TradingSession',
    'SessionQuality',
    'SessionAnalysisResult',
    'SessionConfig',
    
    # Macro Context
    'MacroContextAnalyzer',
    'MacroRegime',
    'DollarStrength',
    'VIXLevel',
    'MacroAnalysisResult',
    'MacroData',
]
