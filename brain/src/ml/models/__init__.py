"""VIRTUS ML Models Module
========================

Framework de Machine Learning para trading.

Módulos:
- LSTM: Redes neurais recorrentes para séries temporais
- k-NN: Reconhecimento de padrões de candlestick
- Vision: CNN para análise visual de gráficos
- Ensemble: Combinação de modelos
- Transformer: Atenção para séries temporais
"""

from .model_base import (
    BaseModel,
    DirectionModel,
    ModelRegistry,
    ModelType,
    ModelStatus,
    ModelMetrics,
    Feature,
    Prediction,
)
from .prediction_engine import (
    PredictionEngine,
    PredictionService,
    EnsemblePrediction,
    FeatureCache,
)

# LSTM Models
from .lstm import (
    VirtusLSTMModel,
    LSTMConfig,
    LSTMArchitecture,
    PredictionTarget,
    LSTMPrediction,
)

# k-NN Pattern Recognition
from .knn import (
    KNNPatternRecognizer,
    PatternType,
    PatternSignal,
    PatternReliability,
    PatternMatch,
)

# Vision AI
from .vision import (
    VirtusVisionAnalyzer,
    ChartPatternType,
    PatternBias,
    PatternDetection,
    ChartRenderer,
)

__all__ = [
    # Model Base
    'BaseModel',
    'DirectionModel',
    'ModelRegistry',
    'ModelType',
    'ModelStatus',
    'ModelMetrics',
    'Feature',
    'Prediction',
    # Prediction Engine
    'PredictionEngine',
    'PredictionService',
    'EnsemblePrediction',
    'FeatureCache',
    # LSTM
    'VirtusLSTMModel',
    'LSTMConfig',
    'LSTMArchitecture',
    'PredictionTarget',
    'LSTMPrediction',
    # k-NN
    'KNNPatternRecognizer',
    'PatternType',
    'PatternSignal',
    'PatternReliability',
    'PatternMatch',
    # Vision
    'VirtusVisionAnalyzer',
    'ChartPatternType',
    'PatternBias',
    'PatternDetection',
    'ChartRenderer',
]
