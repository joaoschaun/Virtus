"""
VIRTUS ML - Dataset Builder
============================

Construção de datasets para treinamento de modelos ML.
Integra feature engineering, labels e split temporal.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

from .feature_engineering import TechnicalFeatureEngineer, FeatureConfig
from .candlestick_transformer import CandlestickImageGenerator, ImageConfig

logger = logging.getLogger(__name__)


class LabelType(Enum):
    """Tipos de label."""
    DIRECTION = "direction"          # Up/Down/Neutral
    BINARY = "binary"                # Up/Down
    REGRESSION = "regression"        # Preço futuro
    MULTI_HORIZON = "multi_horizon"  # Múltiplos horizontes


class SplitMethod(Enum):
    """Métodos de split de dados."""
    TEMPORAL = "temporal"
    RANDOM = "random"
    WALK_FORWARD = "walk_forward"
    PURGED_KFOLD = "purged_kfold"


@dataclass
class DatasetConfig:
    """Configuração do dataset."""
    # Dados
    symbol: str = "EURUSD"
    timeframe: str = "H1"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Labels
    label_type: LabelType = LabelType.DIRECTION
    prediction_horizon: int = 1  # Candles à frente
    direction_threshold: float = 0.0002  # Threshold para Up/Down
    
    # Features
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)
    sequence_length: int = 60
    
    # Split
    split_method: SplitMethod = SplitMethod.TEMPORAL
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    
    # Preprocessing
    normalize: bool = True
    remove_na: bool = True
    remove_outliers: bool = False
    outlier_std: float = 3.0


@dataclass 
class Dataset:
    """Dataset para ML."""
    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    
    feature_names: List[str]
    label_names: List[str]
    
    # Metadados
    config: DatasetConfig
    created_at: datetime = field(default_factory=datetime.now)
    
    # Estatísticas
    train_samples: int = 0
    val_samples: int = 0
    test_samples: int = 0
    
    def __post_init__(self):
        self.train_samples = len(self.X_train)
        self.val_samples = len(self.X_val)
        self.test_samples = len(self.X_test)
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo do dataset."""
        return {
            'train_samples': self.train_samples,
            'val_samples': self.val_samples,
            'test_samples': self.test_samples,
            'total_samples': self.train_samples + self.val_samples + self.test_samples,
            'n_features': len(self.feature_names),
            'n_classes': len(self.label_names),
            'class_distribution': self._get_class_distribution(),
            'feature_names': self.feature_names[:10],  # Primeiras 10
        }
    
    def _get_class_distribution(self) -> Dict[str, float]:
        """Calcula distribuição de classes."""
        all_y = np.concatenate([self.y_train, self.y_val, self.y_test])
        
        if len(all_y.shape) > 1:
            all_y = np.argmax(all_y, axis=1)
        
        unique, counts = np.unique(all_y, return_counts=True)
        total = len(all_y)
        
        return {
            self.label_names[int(u)] if int(u) < len(self.label_names) else str(u): c/total 
            for u, c in zip(unique, counts)
        }


class DatasetBuilder:
    """
    Constrói datasets para treinamento de modelos ML.
    
    Responsável por:
    - Carregar e preprocessar dados
    - Criar features via feature engineering
    - Gerar labels
    - Criar splits temporais
    - Normalização
    """
    
    def __init__(self, config: DatasetConfig):
        self.config = config
        self.feature_engineer = TechnicalFeatureEngineer(config.feature_config)
        self.scalers: Dict[str, Tuple[float, float]] = {}
    
    def build_from_dataframe(
        self,
        df: pd.DataFrame,
        include_sequences: bool = True
    ) -> Dataset:
        """
        Constrói dataset a partir de DataFrame.
        
        Args:
            df: DataFrame com OHLCV
            include_sequences: Se deve criar sequências para LSTM
            
        Returns:
            Dataset pronto para treinamento
        """
        logger.info(f"Building dataset with {len(df)} samples")
        
        # 1. Feature Engineering
        df_features = self.feature_engineer.create_features(df)
        feature_names = self.feature_engineer.get_feature_names()
        
        # 2. Cria Labels
        labels, label_names = self._create_labels(df_features)
        
        # 3. Remove NaN
        if self.config.remove_na:
            df_features, labels = self._remove_na(df_features, labels, feature_names)
        
        # 4. Remove Outliers
        if self.config.remove_outliers:
            df_features = self._remove_outliers(df_features, feature_names)
        
        # 5. Extrai features como array
        X = df_features[feature_names].values.astype(np.float32)
        y = labels
        
        # 6. Cria sequências se necessário
        if include_sequences:
            X, y = self._create_sequences(X, y)
        
        # 7. Split
        X_train, y_train, X_val, y_val, X_test, y_test = self._split_data(X, y)
        
        # 8. Normalização
        if self.config.normalize:
            X_train, X_val, X_test = self._normalize(X_train, X_val, X_test)
        
        # 9. Cria Dataset
        dataset = Dataset(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            y_test=y_test,
            feature_names=feature_names,
            label_names=label_names,
            config=self.config,
        )
        
        logger.info(f"Dataset built: {dataset.get_summary()}")
        
        return dataset
    
    def build_image_dataset(
        self,
        df: pd.DataFrame,
        image_config: Optional[ImageConfig] = None
    ) -> Dataset:
        """
        Constrói dataset de imagens para CNN.
        
        Args:
            df: DataFrame com OHLCV
            image_config: Configuração de imagens
            
        Returns:
            Dataset com imagens
        """
        img_config = image_config or ImageConfig()
        generator = CandlestickImageGenerator(img_config)
        
        # Gera imagens
        images = generator.generate_batch(df, stride=1)
        
        # Cria labels alinhados com as imagens
        labels, label_names = self._create_labels(df)
        
        # Alinha labels com imagens (offset pelo lookback)
        labels = labels[img_config.lookback:]
        labels = labels[:len(images)]
        
        # Normaliza imagens
        X = images.astype(np.float32) / 255.0
        y = labels
        
        # Split
        X_train, y_train, X_val, y_val, X_test, y_test = self._split_data(X, y)
        
        return Dataset(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            y_test=y_test,
            feature_names=['image'],
            label_names=label_names,
            config=self.config,
        )
    
    def _create_labels(
        self,
        df: pd.DataFrame
    ) -> Tuple[np.ndarray, List[str]]:
        """Cria labels baseado no tipo configurado."""
        
        close = df['close'].values
        horizon = self.config.prediction_horizon
        
        if self.config.label_type == LabelType.DIRECTION:
            # 3 classes: Down, Neutral, Up
            future_returns = np.zeros(len(close))
            future_returns[:-horizon] = (close[horizon:] - close[:-horizon]) / close[:-horizon]
            
            labels = np.ones(len(close), dtype=np.int32)  # Default: Neutral
            labels[future_returns > self.config.direction_threshold] = 2   # Up
            labels[future_returns < -self.config.direction_threshold] = 0  # Down
            
            label_names = ['Down', 'Neutral', 'Up']
            
        elif self.config.label_type == LabelType.BINARY:
            # 2 classes: Down, Up
            future_returns = np.zeros(len(close))
            future_returns[:-horizon] = (close[horizon:] - close[:-horizon]) / close[:-horizon]
            
            labels = (future_returns > 0).astype(np.int32)
            label_names = ['Down', 'Up']
            
        elif self.config.label_type == LabelType.REGRESSION:
            # Valor contínuo: retorno futuro
            labels = np.zeros(len(close), dtype=np.float32)
            labels[:-horizon] = (close[horizon:] - close[:-horizon]) / close[:-horizon]
            label_names = ['return']
            
        elif self.config.label_type == LabelType.MULTI_HORIZON:
            # Múltiplos horizontes
            horizons = [1, 3, 5, 10]
            labels = np.zeros((len(close), len(horizons)), dtype=np.float32)
            
            for i, h in enumerate(horizons):
                labels[:-h, i] = (close[h:] - close[:-h]) / close[:-h]
            
            label_names = [f'return_{h}' for h in horizons]
        
        else:
            raise ValueError(f"Label type {self.config.label_type} não suportado")
        
        return labels, label_names
    
    def _remove_na(
        self,
        df: pd.DataFrame,
        labels: np.ndarray,
        feature_names: List[str]
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """Remove linhas com NaN."""
        
        # Mask de válidos
        valid_mask = ~df[feature_names].isna().any(axis=1)
        
        # Aplica mask
        df_clean = df[valid_mask].copy()
        labels_clean = labels[valid_mask.values]
        
        logger.info(f"Removed {(~valid_mask).sum()} NaN rows")
        
        return df_clean, labels_clean
    
    def _remove_outliers(
        self,
        df: pd.DataFrame,
        feature_names: List[str]
    ) -> pd.DataFrame:
        """Remove outliers usando z-score."""
        
        df_clean = df.copy()
        
        for col in feature_names:
            if col not in df_clean.columns:
                continue
            
            mean = df_clean[col].mean()
            std = df_clean[col].std()
            
            if std > 0:
                z_scores = np.abs((df_clean[col] - mean) / std)
                df_clean = df_clean[z_scores < self.config.outlier_std]
        
        return df_clean
    
    def _create_sequences(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Cria sequências para modelos recorrentes."""
        
        seq_len = self.config.sequence_length
        
        X_seq = []
        y_seq = []
        
        for i in range(seq_len, len(X)):
            X_seq.append(X[i-seq_len:i])
            y_seq.append(y[i])
        
        return np.array(X_seq), np.array(y_seq)
    
    def _split_data(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Divide dados em treino/validação/teste."""
        
        n = len(X)
        
        if self.config.split_method == SplitMethod.TEMPORAL:
            # Split temporal (mantém ordem)
            train_end = int(n * self.config.train_ratio)
            val_end = int(n * (self.config.train_ratio + self.config.val_ratio))
            
            X_train = X[:train_end]
            y_train = y[:train_end]
            X_val = X[train_end:val_end]
            y_val = y[train_end:val_end]
            X_test = X[val_end:]
            y_test = y[val_end:]
            
        elif self.config.split_method == SplitMethod.RANDOM:
            # Split aleatório (não recomendado para séries temporais)
            indices = np.random.permutation(n)
            
            train_end = int(n * self.config.train_ratio)
            val_end = int(n * (self.config.train_ratio + self.config.val_ratio))
            
            X_train = X[indices[:train_end]]
            y_train = y[indices[:train_end]]
            X_val = X[indices[train_end:val_end]]
            y_val = y[indices[train_end:val_end]]
            X_test = X[indices[val_end:]]
            y_test = y[indices[val_end:]]
            
        else:
            # Default: temporal
            return self._split_data(X, y)
        
        return X_train, y_train, X_val, y_val, X_test, y_test
    
    def _normalize(
        self,
        X_train: np.ndarray,
        X_val: np.ndarray,
        X_test: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Normaliza features usando estatísticas do treino."""
        
        # Flatten se necessário (para sequências)
        original_shape_train = X_train.shape
        original_shape_val = X_val.shape
        original_shape_test = X_test.shape
        
        if len(X_train.shape) == 3:
            # (samples, seq_len, features) -> (samples*seq_len, features)
            n_features = X_train.shape[-1]
            X_train_flat = X_train.reshape(-1, n_features)
            X_val_flat = X_val.reshape(-1, n_features)
            X_test_flat = X_test.reshape(-1, n_features)
        else:
            X_train_flat = X_train
            X_val_flat = X_val
            X_test_flat = X_test
        
        # Calcula estatísticas no treino
        for i in range(X_train_flat.shape[1]):
            min_val = np.nanmin(X_train_flat[:, i])
            max_val = np.nanmax(X_train_flat[:, i])
            
            range_val = max_val - min_val
            if range_val == 0:
                range_val = 1
            
            self.scalers[i] = (min_val, max_val)
            
            # Aplica normalização
            X_train_flat[:, i] = (X_train_flat[:, i] - min_val) / range_val
            X_val_flat[:, i] = (X_val_flat[:, i] - min_val) / range_val
            X_test_flat[:, i] = (X_test_flat[:, i] - min_val) / range_val
        
        # Reshape de volta
        if len(original_shape_train) == 3:
            X_train = X_train_flat.reshape(original_shape_train)
            X_val = X_val_flat.reshape(original_shape_val)
            X_test = X_test_flat.reshape(original_shape_test)
        else:
            X_train = X_train_flat
            X_val = X_val_flat
            X_test = X_test_flat
        
        return X_train, X_val, X_test
    
    def create_walk_forward_splits(
        self,
        df: pd.DataFrame,
        train_window: int = 252,
        test_window: int = 63,
        step_size: int = 21
    ) -> List[Dataset]:
        """
        Cria múltiplos splits walk-forward.
        
        Args:
            df: DataFrame completo
            train_window: Tamanho da janela de treino
            test_window: Tamanho da janela de teste
            step_size: Passo entre splits
            
        Returns:
            Lista de Datasets
        """
        datasets = []
        
        for start in range(0, len(df) - train_window - test_window, step_size):
            train_end = start + train_window
            test_end = train_end + test_window
            
            df_fold = df.iloc[start:test_end].copy()
            
            # Modifica config para este fold
            fold_config = DatasetConfig(
                **{**self.config.__dict__, 
                   'train_ratio': train_window / (train_window + test_window),
                   'val_ratio': 0.0,
                   'test_ratio': test_window / (train_window + test_window)}
            )
            
            builder = DatasetBuilder(fold_config)
            dataset = builder.build_from_dataframe(df_fold)
            datasets.append(dataset)
        
        return datasets
