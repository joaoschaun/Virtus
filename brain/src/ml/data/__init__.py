"""
VIRTUS ML - Data Module
========================

Módulo de preparação e transformação de dados para ML.
"""

from .feature_engineering import (
    TechnicalFeatureEngineer,
    FeatureConfig,
)

from .candlestick_transformer import (
    CandlestickImageGenerator,
    ImageConfig,
)

from .dataset_builder import (
    DatasetBuilder,
    DatasetConfig,
    Dataset,
    LabelType,
    SplitMethod,
)

__all__ = [
    # Feature Engineering
    'TechnicalFeatureEngineer',
    'FeatureConfig',
    
    # Image Generation
    'CandlestickImageGenerator',
    'ImageConfig',
    
    # Dataset Builder
    'DatasetBuilder',
    'DatasetConfig',
    'Dataset',
    'LabelType',
    'SplitMethod',
]
