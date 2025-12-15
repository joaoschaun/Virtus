"""
VIRTUS ML - Evaluation Module
==============================

Módulo de avaliação e comparação de modelos ML.
"""

from .ml_metrics import (
    MLMetricsCalculator,
    ClassificationMetrics,
    TradingMetrics,
    calculate_information_coefficient,
    calculate_hit_rate,
)

from .model_comparator import (
    ModelComparator,
    ModelResult,
    ComparisonResult,
    ComparisonMetric,
)

from .ml_backtester import (
    MLBacktester,
    BacktestConfig,
    BacktestResult,
    BacktestMode,
    Trade,
)

__all__ = [
    # Metrics
    'MLMetricsCalculator',
    'ClassificationMetrics',
    'TradingMetrics',
    'calculate_information_coefficient',
    'calculate_hit_rate',
    
    # Comparator
    'ModelComparator',
    'ModelResult',
    'ComparisonResult',
    'ComparisonMetric',
    
    # Backtester
    'MLBacktester',
    'BacktestConfig',
    'BacktestResult',
    'BacktestMode',
    'Trade',
]
