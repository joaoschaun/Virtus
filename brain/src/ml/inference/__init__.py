"""
VIRTUS ML - Inference Module
=============================

Módulo de inferência e predição para modelos ML.
"""

from .predictor import (
    UnifiedPredictor,
    Prediction,
    EnsemblePrediction,
    ModelType,
    ModelWrapper,
    LSTMWrapper,
    KNNWrapper,
    CNNWrapper,
)

from .signal_generator import (
    MLSignalGenerator,
    TradingSignal,
    SignalConfig,
    SignalType,
    SignalStrength,
)

__all__ = [
    # Predictor
    'UnifiedPredictor',
    'Prediction',
    'EnsemblePrediction',
    'ModelType',
    'ModelWrapper',
    'LSTMWrapper',
    'KNNWrapper',
    'CNNWrapper',
    
    # Signal Generator
    'MLSignalGenerator',
    'TradingSignal',
    'SignalConfig',
    'SignalType',
    'SignalStrength',
]
