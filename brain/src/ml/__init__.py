"""VIRTUS Machine Learning Module
=================================

Framework completo de ML para trading:
- Config: Configurações YAML
- Data: Feature engineering, dataset builder
- Models: LSTM, k-NN, CNN, Ensemble
- Training: Trainer, hyperparameter tuning
- Inference: Predictor unificado, signal generator
- Evaluation: Backtester ML, métricas, comparador
- Utils: Checkpointing, monitoring
"""

from .model_factory import ModelFactory
from .models.model_base import (
    BaseModel,
    DirectionModel,
    ModelRegistry,
    ModelType,
    ModelStatus,
    ModelMetrics,
    Feature,
    Prediction,
)
from .models.prediction_engine import (
    PredictionEngine,
    PredictionService,
    EnsemblePrediction,
    FeatureCache,
)

# Config
from .config import (
    ConfigLoader,
    config_loader,
    load_model_config,
    load_training_config,
    LSTMConfig,
    KNNConfig,
    CNNConfig,
    TrainingConfig,
)

# Data
from .data import (
    TechnicalFeatureEngineer,
    FeatureConfig,
    CandlestickImageGenerator,
    ImageConfig,
    DatasetBuilder,
    DatasetConfig,
    Dataset,
    LabelType,
    SplitMethod,
)

# Inference
from .inference import (
    UnifiedPredictor,
    MLSignalGenerator,
    TradingSignal,
    SignalConfig,
    SignalType,
    SignalStrength,
)

# Evaluation
from .evaluation import (
    MLMetricsCalculator,
    ClassificationMetrics,
    TradingMetrics,
    ModelComparator,
    ModelResult,
    ComparisonResult,
    ComparisonMetric,
    MLBacktester,
    BacktestConfig,
    BacktestResult,
    BacktestMode,
)

# Utils
from .utils import (
    CheckpointManager,
    CheckpointMetadata,
    MLMonitor,
    ModelHealthChecker,
)

__all__ = [
    # Factory
    'ModelFactory',
    
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
    
    # Config
    'ConfigLoader',
    'config_loader',
    'load_model_config',
    'load_training_config',
    'LSTMConfig',
    'KNNConfig',
    'CNNConfig',
    'TrainingConfig',
    
    # Data
    'TechnicalFeatureEngineer',
    'FeatureConfig',
    'CandlestickImageGenerator',
    'ImageConfig',
    'DatasetBuilder',
    'DatasetConfig',
    'Dataset',
    'LabelType',
    'SplitMethod',
    
    # Inference
    'UnifiedPredictor',
    'MLSignalGenerator',
    'TradingSignal',
    'SignalConfig',
    'SignalType',
    'SignalStrength',
    
    # Evaluation
    'MLMetricsCalculator',
    'ClassificationMetrics',
    'TradingMetrics',
    'ModelComparator',
    'ModelResult',
    'ComparisonResult',
    'ComparisonMetric',
    'MLBacktester',
    'BacktestConfig',
    'BacktestResult',
    'BacktestMode',
    
    # Utils
    'CheckpointManager',
    'CheckpointMetadata',
    'MLMonitor',
    'ModelHealthChecker',
]
