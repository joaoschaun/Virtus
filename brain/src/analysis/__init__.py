"""
VIRTUS Analysis Module
=======================

Módulo central de análise técnica avançada.
Integra múltiplos componentes especializados em uma análise unificada.

Componentes:
- Technical: Indicadores clássicos e avançados
- Market Structure: BOS, CHoCH, Swing Points
- Smart Money: Order Blocks, FVG, Liquidity
- Volume: Profile, VSA, Delta
- Multi-Timeframe: Confluência entre períodos
- Divergences: Multi-indicador
- Fibonacci: Retracements, Extensions, Clusters
- Harmonic Patterns: Gartley, Bat, Butterfly, Crab, ABCD
- Correlation: DXY, cross-pair
- Master Analyzer: Integração de todos os módulos
"""

# Master Analyzer (integrador central)
from .master_analyzer import (
    MasterTechnicalAnalyzer,
    MasterAnalysisResult,
    MarketBias,
    SignalQuality,
    TradeDirection,
    KeyLevel,
    TradeSetup,
)

# Technical Analysis
from .technical import (
    TechnicalAnalyzer,
    TechnicalSignal,
    TrendDirection,
    SignalStrength,
    MarketStructureAnalyzer,
    SwingPoint,
    SwingType,
    DivergenceDetector,
    DivergenceType,
    FibonacciAnalyzer,
    FibonacciResult,
    HarmonicPatternDetector,
    HarmonicResult,
    PatternType,
    AdvancedIndicators,
    IchimokuResult,
    VWAPResult,
    PivotPoints,
    SupertrendResult,
)

# Institutional/Smart Money
from .institutional import (
    SmartMoneyAnalyzer,
    OrderBlock,
    FairValueGap,
    LiquidityPool,
    SmartMoneyResult,
)

# Volume Analysis
from .volume import (
    VolumeAnalyzer,
    VolumeProfile,
    VolumeSignal,
    VolumeAnalysisResult,
)

# Market/MTF Analysis
from .market import (
    MultiTimeframeAnalyzer,
    TimeframeBias,
    MTFConfluence,
    MTFAnalysisResult,
)

# Correlation Analysis
from .correlation import (
    CorrelationAnalyzer,
    CorrelationStrength,
    CorrelationRegime,
    CorrelationAnalysisResult,
)

# Signals
from .signals import SignalGenerator, SignalComponent, SignalSource

__all__ = [
    # Master Analyzer
    'MasterTechnicalAnalyzer',
    'MasterAnalysisResult',
    'MarketBias',
    'SignalQuality',
    'TradeDirection',
    'KeyLevel',
    'TradeSetup',
    # Technical
    'TechnicalAnalyzer',
    'TechnicalSignal',
    'TrendDirection',
    'SignalStrength',
    'MarketStructureAnalyzer',
    'SwingPoint',
    'SwingType',
    'DivergenceDetector',
    'DivergenceType',
    'FibonacciAnalyzer',
    'FibonacciResult',
    'HarmonicPatternDetector',
    'HarmonicResult',
    'PatternType',
    'AdvancedIndicators',
    'IchimokuResult',
    'VWAPResult',
    'PivotPoints',
    'SupertrendResult',
    # Smart Money
    'SmartMoneyAnalyzer',
    'OrderBlock',
    'FairValueGap',
    'LiquidityPool',
    'SmartMoneyResult',
    # Volume
    'VolumeAnalyzer',
    'VolumeProfile',
    'VolumeSignal',
    'VolumeAnalysisResult',
    # MTF
    'MultiTimeframeAnalyzer',
    'TimeframeBias',
    'MTFConfluence',
    'MTFAnalysisResult',
    # Correlation
    'CorrelationAnalyzer',
    'CorrelationStrength',
    'CorrelationRegime',
    'CorrelationAnalysisResult',
    # Signals
    'SignalGenerator',
    'SignalComponent',
    'SignalSource',
]
