"""
VIRTUS Risk Module
===================

Gerenciamento centralizado de risco para múltiplos bots.

Inclui:
- RiskManager: Gerenciamento básico de risco
- AdvancedRiskManager: Kelly Criterion, Monte Carlo VaR, Anti-Martingale
- GlobalRiskManager: Coordenação de risco entre bots
- CorrelationRiskManager: Gestão de risco de correlação
- ExposureManager: Controle de alocação e exposição
"""

from .risk_manager import (
    RiskManager,
    RiskLevel,
    RiskMetrics,
    PositionSizing,
    get_risk_manager,
)
from .advanced_risk import (
    AdvancedRiskManager,
    KellyResult,
    VaRResult,
    SizingMethod,
    DrawdownState,
    TradeStatistics,
    EquityCurveState,
)
from .global_risk import (
    GlobalRiskManager,
    GlobalRiskState,
    TradingMode,
    BotRiskStatus,
    GlobalRiskMetrics,
    GlobalRiskConfig,
)
from .correlation_risk import (
    CorrelationRiskManager,
    CorrelationLevel,
    CorrelationEntry,
    PositionExposure,
    CorrelationRiskMetrics,
    CorrelationRiskConfig,
)
from .exposure_manager import (
    ExposureManager,
    AssetClass,
    ExposureType,
    SymbolExposure,
    ClassExposure,
    ExposureMetrics,
    ExposureConfig,
)

__all__ = [
    # Basic Risk Manager
    'RiskManager',
    'RiskLevel',
    'RiskMetrics',
    'PositionSizing',
    'get_risk_manager',
    # Advanced Risk Manager
    'AdvancedRiskManager',
    'KellyResult',
    'VaRResult',
    'SizingMethod',
    'DrawdownState',
    'TradeStatistics',
    'EquityCurveState',
    # Global Risk Manager
    'GlobalRiskManager',
    'GlobalRiskState',
    'TradingMode',
    'BotRiskStatus',
    'GlobalRiskMetrics',
    'GlobalRiskConfig',
    # Correlation Risk Manager
    'CorrelationRiskManager',
    'CorrelationLevel',
    'CorrelationEntry',
    'PositionExposure',
    'CorrelationRiskMetrics',
    'CorrelationRiskConfig',
    # Exposure Manager
    'ExposureManager',
    'AssetClass',
    'ExposureType',
    'SymbolExposure',
    'ClassExposure',
    'ExposureMetrics',
    'ExposureConfig',
]
