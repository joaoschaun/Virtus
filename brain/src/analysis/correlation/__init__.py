"""
VIRTUS Correlation Analysis Module
===================================

Análise de correlações entre instrumentos.
"""

from .correlation_analyzer import (
    CorrelationAnalyzer,
    CorrelationStrength,
    CorrelationRegime,
    PairCorrelation,
    DXYCorrelation,
    CorrelationAnalysisResult,
)

__all__ = [
    'CorrelationAnalyzer',
    'CorrelationStrength',
    'CorrelationRegime',
    'PairCorrelation',
    'DXYCorrelation',
    'CorrelationAnalysisResult',
]
