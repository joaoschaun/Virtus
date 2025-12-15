"""
VIRTUS Institutional Analysis Module (Smart Money Concepts)
============================================================

Análise institucional com conceitos de Smart Money / ICT.
"""

from .smart_money import (
    SmartMoneyAnalyzer,
    OrderBlock,
    FairValueGap,
    LiquidityPool,
    SmartMoneyResult,
)

from .manipulation_detector import (
    ManipulationDetector,
    ManipulationEvent,
    ManipulationType,
    ManipulationSeverity,
    ManipulationAnalysisResult,
)

from .institutional_sentiment import (
    InstitutionalSentimentAnalyzer,
    SentimentAnalysisResult,
    SentimentBias,
    COTData,
    TraderType,
)

__all__ = [
    # Smart Money
    'SmartMoneyAnalyzer',
    'OrderBlock',
    'FairValueGap',
    'LiquidityPool',
    'SmartMoneyResult',
    
    # Manipulation Detection
    'ManipulationDetector',
    'ManipulationEvent',
    'ManipulationType',
    'ManipulationSeverity',
    'ManipulationAnalysisResult',
    
    # Institutional Sentiment
    'InstitutionalSentimentAnalyzer',
    'SentimentAnalysisResult',
    'SentimentBias',
    'COTData',
    'TraderType',
]
