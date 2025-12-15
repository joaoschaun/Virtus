"""
VIRTUS Technical Analysis Module
=================================

Análise técnica avançada com múltiplos componentes especializados.
"""

from .technical_analyzer import (
    TechnicalAnalyzer,
    TechnicalSignal,
    MarketStructure,
    TrendDirection,
    SignalStrength,
)

from .market_structure import (
    MarketStructureAnalyzer,
    SwingPoint,
    SwingType,
    StructureBreakEvent,
    MarketStructureState,
)

from .divergence_detector import (
    DivergenceDetector,
    Divergence,
    DivergenceType,
    DivergenceStrength,
    DivergenceAnalysisResult,
)

from .fibonacci_analyzer import (
    FibonacciAnalyzer,
    FibonacciLevel,
    FibonacciZone,
    FibonacciAnalysis,
    FibonacciResult,
)

from .harmonic_patterns import (
    HarmonicPatternDetector,
    HarmonicPattern,
    PatternType,
    PatternDirection,
    PatternStatus,
    HarmonicResult,
)

from .advanced_indicators import (
    AdvancedIndicators,
    IchimokuResult,
    VWAPResult,
    PivotPoints,
    SupertrendResult,
    AdvancedIndicatorsResult,
)

__all__ = [
    # Basic Technical
    'TechnicalAnalyzer',
    'TechnicalSignal',
    'MarketStructure',
    'TrendDirection',
    'SignalStrength',
    # Market Structure
    'MarketStructureAnalyzer',
    'SwingPoint',
    'SwingType',
    'StructureBreakEvent',
    'MarketStructureState',
    # Divergences
    'DivergenceDetector',
    'Divergence',
    'DivergenceType',
    'DivergenceStrength',
    'DivergenceAnalysisResult',
    # Fibonacci
    'FibonacciAnalyzer',
    'FibonacciLevel',
    'FibonacciZone',
    'FibonacciAnalysis',
    'FibonacciResult',
    # Harmonic Patterns
    'HarmonicPatternDetector',
    'HarmonicPattern',
    'PatternType',
    'PatternDirection',
    'PatternStatus',
    'HarmonicResult',
    # Advanced Indicators
    'AdvancedIndicators',
    'IchimokuResult',
    'VWAPResult',
    'PivotPoints',
    'SupertrendResult',
    'AdvancedIndicatorsResult',
]
