"""
VIRTUS LSTM Model - Deep Learning para Séries Temporais
========================================================

Implementação de Long Short-Term Memory (LSTM) para:
- Previsão de direção de preço
- Detecção de padrões temporais
- Forecasting de volatilidade
- Regime detection

Features:
- Stacked LSTM layers
- Bidirectional LSTM
- Attention mechanism
- Dropout regularization
- Early stopping
- Model checkpointing
- Online learning support
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from enum import Enum, auto
import json
from pathlib import Path

# Conditional imports for TensorFlow/PyTorch
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import (
        LSTM, Dense, Dropout, Bidirectional,
        Input, Attention, Concatenate, BatchNormalization,
        GRU, Conv1D, MaxPooling1D, Flatten
    )
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    # Dummy classes para type hints
    Model = object
    Sequential = object

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class LSTMArchitecture(Enum):
    """Tipos de arquitetura LSTM."""
    SIMPLE = "simple"                   # LSTM básico
    STACKED = "stacked"                 # Múltiplas camadas LSTM
    BIDIRECTIONAL = "bidirectional"     # LSTM bidirecional
    ATTENTION = "attention"             # LSTM com attention
    CNN_LSTM = "cnn_lstm"               # CNN + LSTM híbrido
    GRU = "gru"                         # GRU ao invés de LSTM


class PredictionTarget(Enum):
    """Alvos de predição."""
    DIRECTION = "direction"             # Up/Down/Neutral
    PRICE_CHANGE = "price_change"       # % de mudança
    VOLATILITY = "volatility"           # Volatilidade futura
    REGIME = "regime"                   # Regime de mercado
    PROBABILITY = "probability"         # Probabilidade de evento


@dataclass
class LSTMConfig:
    """Configuração do modelo LSTM."""
    # Arquitetura
    architecture: LSTMArchitecture = LSTMArchitecture.STACKED
    sequence_length: int = 60           # Candles de lookback
    hidden_units: List[int] = field(default_factory=lambda: [128, 64, 32])
    dropout_rate: float = 0.2
    recurrent_dropout: float = 0.1
    
    # Training
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    early_stopping_patience: int = 10
    reduce_lr_patience: int = 5
    
    # Features
    features: List[str] = field(default_factory=lambda: [
        'open', 'high', 'low', 'close', 'volume',
        'rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_lower',
        'atr', 'adx', 'ema_20', 'ema_50', 'ema_200'
    ])
    
    # Output
    target: PredictionTarget = PredictionTarget.DIRECTION
    num_classes: int = 3                # Up, Down, Neutral
    
    # Validation
    validation_split: float = 0.2
    test_split: float = 0.1


@dataclass
class LSTMPrediction:
    """Resultado de predição do LSTM."""
    direction: str                      # 'up', 'down', 'neutral'
    confidence: float                   # 0.0 - 1.0
    probabilities: Dict[str, float]     # Probabilidades por classe
    price_change_expected: float        # % esperado
    volatility_forecast: float          # Volatilidade esperada
    timestamp: datetime = field(default_factory=datetime.now)
    model_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'direction': self.direction,
            'confidence': round(self.confidence, 4),
            'probabilities': {k: round(v, 4) for k, v in self.probabilities.items()},
            'price_change_expected': round(self.price_change_expected, 4),
            'volatility_forecast': round(self.volatility_forecast, 4),
            'timestamp': self.timestamp.isoformat(),
            'model_version': self.model_version,
        }


class LSTMPreprocessor:
    """
    Preprocessador de dados para LSTM.
    
    Responsável por:
    - Normalização de features
    - Criação de sequências
    - Feature engineering
    - Data augmentation
    """
    
    def __init__(self, config: LSTMConfig):
        self.config = config
        self.scalers: Dict[str, Tuple[float, float]] = {}  # (min, max) por feature
        self.fitted = False
    
    def fit(self, data: np.ndarray, feature_names: List[str]) -> None:
        """Ajusta os scalers com os dados de treino."""
        for i, name in enumerate(feature_names):
            col = data[:, i]
            self.scalers[name] = (float(np.min(col)), float(np.max(col)))
        self.fitted = True
    
    def transform(self, data: np.ndarray, feature_names: List[str]) -> np.ndarray:
        """Normaliza os dados usando scalers ajustados."""
        if not self.fitted:
            raise ValueError("Preprocessor não foi ajustado. Chame fit() primeiro.")
        
        normalized = np.zeros_like(data, dtype=np.float32)
        
        for i, name in enumerate(feature_names):
            if name in self.scalers:
                min_val, max_val = self.scalers[name]
                if max_val - min_val > 0:
                    normalized[:, i] = (data[:, i] - min_val) / (max_val - min_val)
                else:
                    normalized[:, i] = 0.5
            else:
                normalized[:, i] = data[:, i]
        
        return normalized
    
    def create_sequences(
        self,
        data: np.ndarray,
        labels: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Cria sequências para LSTM.
        
        Args:
            data: Array (samples, features)
            labels: Labels opcionais
            
        Returns:
            X: (samples, sequence_length, features)
            y: (samples,) ou None
        """
        seq_len = self.config.sequence_length
        n_samples = len(data) - seq_len
        n_features = data.shape[1]
        
        X = np.zeros((n_samples, seq_len, n_features), dtype=np.float32)
        
        for i in range(n_samples):
            X[i] = data[i:i + seq_len]
        
        if labels is not None:
            y = labels[seq_len:]
            return X, y
        
        return X, None
    
    def inverse_transform(self, data: np.ndarray, feature_name: str) -> np.ndarray:
        """Reverte normalização para uma feature."""
        if feature_name not in self.scalers:
            return data
        
        min_val, max_val = self.scalers[feature_name]
        return data * (max_val - min_val) + min_val


class TensorFlowLSTM:
    """
    Implementação LSTM usando TensorFlow/Keras.
    """
    
    def __init__(self, config: LSTMConfig):
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow não está instalado. Execute: pip install tensorflow")
        
        self.config = config
        self.model: Optional[Model] = None
        self.history = None
    
    def build_model(self, input_shape: Tuple[int, int]) -> Model:
        """
        Constrói o modelo LSTM baseado na arquitetura configurada.
        
        Args:
            input_shape: (sequence_length, n_features)
        """
        if self.config.architecture == LSTMArchitecture.SIMPLE:
            return self._build_simple(input_shape)
        elif self.config.architecture == LSTMArchitecture.STACKED:
            return self._build_stacked(input_shape)
        elif self.config.architecture == LSTMArchitecture.BIDIRECTIONAL:
            return self._build_bidirectional(input_shape)
        elif self.config.architecture == LSTMArchitecture.ATTENTION:
            return self._build_attention(input_shape)
        elif self.config.architecture == LSTMArchitecture.CNN_LSTM:
            return self._build_cnn_lstm(input_shape)
        elif self.config.architecture == LSTMArchitecture.GRU:
            return self._build_gru(input_shape)
        else:
            return self._build_stacked(input_shape)
    
    def _build_simple(self, input_shape: Tuple[int, int]) -> Model:
        """LSTM simples de uma camada."""
        model = Sequential([
            LSTM(
                self.config.hidden_units[0],
                input_shape=input_shape,
                dropout=self.config.dropout_rate,
                recurrent_dropout=self.config.recurrent_dropout
            ),
            Dense(32, activation='relu'),
            Dropout(self.config.dropout_rate),
            Dense(self.config.num_classes, activation='softmax')
        ])
        return model
    
    def _build_stacked(self, input_shape: Tuple[int, int]) -> Model:
        """LSTM com múltiplas camadas empilhadas."""
        model = Sequential()
        
        # Primeira camada LSTM
        model.add(LSTM(
            self.config.hidden_units[0],
            input_shape=input_shape,
            return_sequences=True,
            dropout=self.config.dropout_rate,
            recurrent_dropout=self.config.recurrent_dropout
        ))
        model.add(BatchNormalization())
        
        # Camadas intermediárias
        for units in self.config.hidden_units[1:-1]:
            model.add(LSTM(
                units,
                return_sequences=True,
                dropout=self.config.dropout_rate,
                recurrent_dropout=self.config.recurrent_dropout
            ))
            model.add(BatchNormalization())
        
        # Última camada LSTM
        model.add(LSTM(
            self.config.hidden_units[-1],
            dropout=self.config.dropout_rate,
            recurrent_dropout=self.config.recurrent_dropout
        ))
        model.add(BatchNormalization())
        
        # Dense layers
        model.add(Dense(32, activation='relu'))
        model.add(Dropout(self.config.dropout_rate))
        model.add(Dense(self.config.num_classes, activation='softmax'))
        
        return model
    
    def _build_bidirectional(self, input_shape: Tuple[int, int]) -> Model:
        """LSTM bidirecional."""
        model = Sequential()
        
        model.add(Bidirectional(
            LSTM(
                self.config.hidden_units[0],
                return_sequences=True,
                dropout=self.config.dropout_rate,
                recurrent_dropout=self.config.recurrent_dropout
            ),
            input_shape=input_shape
        ))
        model.add(BatchNormalization())
        
        for units in self.config.hidden_units[1:]:
            model.add(Bidirectional(
                LSTM(
                    units,
                    return_sequences=False if units == self.config.hidden_units[-1] else True,
                    dropout=self.config.dropout_rate,
                    recurrent_dropout=self.config.recurrent_dropout
                )
            ))
            model.add(BatchNormalization())
        
        model.add(Dense(32, activation='relu'))
        model.add(Dropout(self.config.dropout_rate))
        model.add(Dense(self.config.num_classes, activation='softmax'))
        
        return model
    
    def _build_attention(self, input_shape: Tuple[int, int]) -> Model:
        """LSTM com mecanismo de atenção."""
        inputs = Input(shape=input_shape)
        
        # LSTM encoder
        lstm_out = LSTM(
            self.config.hidden_units[0],
            return_sequences=True,
            dropout=self.config.dropout_rate,
            recurrent_dropout=self.config.recurrent_dropout
        )(inputs)
        
        # Self-attention
        attention = Attention()([lstm_out, lstm_out])
        
        # Concatenar
        concat = Concatenate()([lstm_out, attention])
        
        # Segunda LSTM
        lstm_out2 = LSTM(
            self.config.hidden_units[-1],
            dropout=self.config.dropout_rate,
            recurrent_dropout=self.config.recurrent_dropout
        )(concat)
        
        # Dense layers
        dense = Dense(32, activation='relu')(lstm_out2)
        dense = Dropout(self.config.dropout_rate)(dense)
        outputs = Dense(self.config.num_classes, activation='softmax')(dense)
        
        return Model(inputs=inputs, outputs=outputs)
    
    def _build_cnn_lstm(self, input_shape: Tuple[int, int]) -> Model:
        """Híbrido CNN + LSTM."""
        model = Sequential()
        
        # CNN layers para extração de features
        model.add(Conv1D(
            64, kernel_size=3, activation='relu',
            input_shape=input_shape
        ))
        model.add(BatchNormalization())
        model.add(MaxPooling1D(pool_size=2))
        
        model.add(Conv1D(128, kernel_size=3, activation='relu'))
        model.add(BatchNormalization())
        model.add(MaxPooling1D(pool_size=2))
        
        # LSTM
        model.add(LSTM(
            self.config.hidden_units[0],
            dropout=self.config.dropout_rate,
            recurrent_dropout=self.config.recurrent_dropout
        ))
        model.add(BatchNormalization())
        
        # Dense
        model.add(Dense(32, activation='relu'))
        model.add(Dropout(self.config.dropout_rate))
        model.add(Dense(self.config.num_classes, activation='softmax'))
        
        return model
    
    def _build_gru(self, input_shape: Tuple[int, int]) -> Model:
        """GRU (alternativa mais leve ao LSTM)."""
        model = Sequential()
        
        model.add(GRU(
            self.config.hidden_units[0],
            input_shape=input_shape,
            return_sequences=True,
            dropout=self.config.dropout_rate,
            recurrent_dropout=self.config.recurrent_dropout
        ))
        model.add(BatchNormalization())
        
        model.add(GRU(
            self.config.hidden_units[-1],
            dropout=self.config.dropout_rate,
            recurrent_dropout=self.config.recurrent_dropout
        ))
        model.add(BatchNormalization())
        
        model.add(Dense(32, activation='relu'))
        model.add(Dropout(self.config.dropout_rate))
        model.add(Dense(self.config.num_classes, activation='softmax'))
        
        return model
    
    def compile_model(self) -> None:
        """Compila o modelo com otimizador e loss."""
        if self.model is None:
            raise ValueError("Modelo não foi construído. Chame build_model() primeiro.")
        
        optimizer = Adam(learning_rate=self.config.learning_rate)
        
        self.model.compile(
            optimizer=optimizer,
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        model_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Treina o modelo.
        
        Returns:
            Histórico de treinamento
        """
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=self.config.early_stopping_patience,
                restore_best_weights=True
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=self.config.reduce_lr_patience,
                min_lr=1e-6
            )
        ]
        
        if model_path:
            callbacks.append(ModelCheckpoint(
                model_path,
                monitor='val_loss',
                save_best_only=True
            ))
        
        validation_data = (X_val, y_val) if X_val is not None else None
        
        self.history = self.model.fit(
            X_train, y_train,
            batch_size=self.config.batch_size,
            epochs=self.config.epochs,
            validation_data=validation_data,
            validation_split=self.config.validation_split if validation_data is None else 0,
            callbacks=callbacks,
            verbose=1
        )
        
        return {
            'loss': self.history.history['loss'],
            'accuracy': self.history.history['accuracy'],
            'val_loss': self.history.history.get('val_loss', []),
            'val_accuracy': self.history.history.get('val_accuracy', []),
        }
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Faz predição."""
        if self.model is None:
            raise ValueError("Modelo não treinado.")
        return self.model.predict(X, verbose=0)
    
    def save(self, path: str) -> None:
        """Salva modelo."""
        if self.model:
            self.model.save(path)
    
    def load(self, path: str) -> None:
        """Carrega modelo."""
        self.model = keras.models.load_model(path)


class VirtusLSTMModel:
    """
    Modelo LSTM completo do VIRTUS para predição de mercado.
    
    Features:
    - Múltiplas arquiteturas LSTM
    - Preprocessamento automático
    - Feature engineering integrado
    - Online learning
    - Model versioning
    - Ensemble de múltiplos modelos
    """
    
    def __init__(
        self,
        config: Optional[LSTMConfig] = None,
        models_dir: str = "models/lstm"
    ):
        self.config = config or LSTMConfig()
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.preprocessor = LSTMPreprocessor(self.config)
        self.model: Optional[TensorFlowLSTM] = None
        
        # Histórico
        self.predictions_history: deque = deque(maxlen=1000)
        self.training_history: List[Dict] = []
        
        # Métricas
        self.metrics = {
            'accuracy': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1': 0.0,
            'total_predictions': 0,
            'correct_predictions': 0,
        }
        
        # Versão
        self.version = "1.0.0"
        self.trained = False
    
    def prepare_features(
        self,
        df,  # DataFrame com OHLCV
        include_indicators: bool = True
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Prepara features a partir de DataFrame OHLCV.
        
        Adiciona indicadores técnicos automaticamente.
        """
        import pandas as pd
        
        features = []
        feature_names = []
        
        # OHLCV básico
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                features.append(df[col].values)
                feature_names.append(col)
        
        # Volume
        vol_col = 'volume' if 'volume' in df.columns else 'tick_volume'
        if vol_col in df.columns:
            features.append(df[vol_col].values)
            feature_names.append('volume')
        
        if include_indicators:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            
            # RSI
            rsi = self._calculate_rsi(close, 14)
            features.append(rsi)
            feature_names.append('rsi')
            
            # MACD
            macd, signal, hist = self._calculate_macd(close)
            features.append(macd)
            features.append(signal)
            features.append(hist)
            feature_names.extend(['macd', 'macd_signal', 'macd_hist'])
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger(close)
            features.append(bb_upper)
            features.append(bb_lower)
            feature_names.extend(['bb_upper', 'bb_lower'])
            
            # ATR
            atr = self._calculate_atr(high, low, close)
            features.append(atr)
            feature_names.append('atr')
            
            # EMAs
            for period in [20, 50, 200]:
                ema = self._calculate_ema(close, period)
                features.append(ema)
                feature_names.append(f'ema_{period}')
            
            # Returns
            returns = np.zeros_like(close)
            returns[1:] = (close[1:] - close[:-1]) / close[:-1]
            features.append(returns)
            feature_names.append('returns')
        
        # Stack features
        data = np.column_stack(features)
        
        # Remove NaN
        data = np.nan_to_num(data, nan=0.0)
        
        return data, feature_names
    
    def prepare_labels(
        self,
        df,
        lookahead: int = 1,
        threshold: float = 0.0002
    ) -> np.ndarray:
        """
        Prepara labels para classificação.
        
        Args:
            df: DataFrame com preços
            lookahead: Períodos para frente
            threshold: Threshold para classificar Up/Down
            
        Returns:
            Labels: 0=Down, 1=Neutral, 2=Up
        """
        close = df['close'].values
        
        # Retorno futuro
        future_returns = np.zeros(len(close))
        future_returns[:-lookahead] = (close[lookahead:] - close[:-lookahead]) / close[:-lookahead]
        
        # Classificar
        labels = np.ones(len(close), dtype=np.int32)  # Default: Neutral
        labels[future_returns > threshold] = 2   # Up
        labels[future_returns < -threshold] = 0  # Down
        
        return labels
    
    def train(
        self,
        df,
        lookahead: int = 1,
        threshold: float = 0.0002,
        save_model: bool = True
    ) -> Dict[str, Any]:
        """
        Treina o modelo LSTM.
        
        Args:
            df: DataFrame com OHLCV
            lookahead: Períodos para predição
            threshold: Threshold para classificação
            save_model: Se deve salvar o modelo
            
        Returns:
            Histórico de treinamento
        """
        if not TF_AVAILABLE:
            return {'error': 'TensorFlow não disponível'}
        
        # Preparar dados
        data, feature_names = self.prepare_features(df)
        labels = self.prepare_labels(df, lookahead, threshold)
        
        # Fit preprocessor
        self.preprocessor.fit(data, feature_names)
        
        # Normalizar
        data_normalized = self.preprocessor.transform(data, feature_names)
        
        # Criar sequências
        X, y = self.preprocessor.create_sequences(data_normalized, labels)
        
        # Split train/val
        split_idx = int(len(X) * (1 - self.config.validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Construir modelo
        input_shape = (X_train.shape[1], X_train.shape[2])
        self.model = TensorFlowLSTM(self.config)
        self.model.model = self.model.build_model(input_shape)
        self.model.compile_model()
        
        # Treinar
        model_path = str(self.models_dir / f"lstm_v{self.version}.keras") if save_model else None
        history = self.model.train(X_train, y_train, X_val, y_val, model_path)
        
        # Avaliar
        y_pred = np.argmax(self.model.predict(X_val), axis=1)
        accuracy = np.mean(y_pred == y_val)
        
        self.metrics['accuracy'] = float(accuracy)
        self.trained = True
        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'samples': len(X_train),
            'accuracy': accuracy,
            'history': history,
        })
        
        return {
            'accuracy': accuracy,
            'samples_trained': len(X_train),
            'samples_val': len(X_val),
            'history': history,
        }
    
    def predict(self, df) -> LSTMPrediction:
        """
        Faz predição com o modelo treinado.
        
        Args:
            df: DataFrame com últimos N candles (N >= sequence_length)
            
        Returns:
            LSTMPrediction
        """
        if not self.trained or self.model is None:
            return LSTMPrediction(
                direction='neutral',
                confidence=0.0,
                probabilities={'down': 0.33, 'neutral': 0.34, 'up': 0.33},
                price_change_expected=0.0,
                volatility_forecast=0.0,
            )
        
        # Preparar features
        data, feature_names = self.prepare_features(df, include_indicators=True)
        
        # Normalizar
        data_normalized = self.preprocessor.transform(data, feature_names)
        
        # Criar sequência (última sequência disponível)
        seq_len = self.config.sequence_length
        if len(data_normalized) < seq_len:
            # Padding se necessário
            padded = np.zeros((seq_len, data_normalized.shape[1]))
            padded[-len(data_normalized):] = data_normalized
            X = padded.reshape(1, seq_len, -1)
        else:
            X = data_normalized[-seq_len:].reshape(1, seq_len, -1)
        
        # Predição
        probs = self.model.predict(X)[0]
        
        # Interpretar
        pred_class = np.argmax(probs)
        directions = ['down', 'neutral', 'up']
        direction = directions[pred_class]
        confidence = float(probs[pred_class])
        
        # Estimar mudança esperada
        price_change = (probs[2] - probs[0]) * 0.005  # Escala aproximada
        
        # Volatilidade (baseada na incerteza)
        entropy = -np.sum(probs * np.log(probs + 1e-10))
        volatility = float(entropy / np.log(3))  # Normalizado 0-1
        
        prediction = LSTMPrediction(
            direction=direction,
            confidence=confidence,
            probabilities={
                'down': float(probs[0]),
                'neutral': float(probs[1]),
                'up': float(probs[2]),
            },
            price_change_expected=price_change,
            volatility_forecast=volatility,
            model_version=self.version,
        )
        
        # Histórico
        self.predictions_history.append(prediction)
        self.metrics['total_predictions'] += 1
        
        return prediction
    
    def update_metrics(self, prediction: LSTMPrediction, actual_direction: str) -> None:
        """Atualiza métricas com resultado real."""
        if prediction.direction == actual_direction:
            self.metrics['correct_predictions'] += 1
        
        if self.metrics['total_predictions'] > 0:
            self.metrics['accuracy'] = (
                self.metrics['correct_predictions'] / 
                self.metrics['total_predictions']
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do modelo."""
        return {
            'trained': self.trained,
            'version': self.version,
            'architecture': self.config.architecture.value,
            'sequence_length': self.config.sequence_length,
            'metrics': self.metrics,
            'total_predictions': len(self.predictions_history),
            'training_sessions': len(self.training_history),
        }
    
    # === Indicadores Técnicos ===
    
    def _calculate_rsi(self, close: np.ndarray, period: int = 14) -> np.ndarray:
        """RSI."""
        deltas = np.diff(close, prepend=close[0])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.zeros_like(close)
        avg_loss = np.zeros_like(close)
        
        avg_gain[period] = np.mean(gains[1:period+1])
        avg_loss[period] = np.mean(losses[1:period+1])
        
        for i in range(period + 1, len(close)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i]) / period
        
        rs = np.divide(avg_gain, avg_loss, where=avg_loss != 0, out=np.ones_like(avg_gain) * 100)
        rsi = 100 - (100 / (1 + rs))
        rsi[:period] = 50
        
        return rsi
    
    def _calculate_macd(
        self,
        close: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """MACD."""
        ema_fast = self._calculate_ema(close, fast)
        ema_slow = self._calculate_ema(close, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger(
        self,
        close: np.ndarray,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bollinger Bands."""
        middle = np.zeros_like(close)
        upper = np.zeros_like(close)
        lower = np.zeros_like(close)
        
        for i in range(period, len(close)):
            window = close[i-period:i]
            middle[i] = np.mean(window)
            std = np.std(window)
            upper[i] = middle[i] + std_dev * std
            lower[i] = middle[i] - std_dev * std
        
        middle[:period] = close[:period]
        upper[:period] = close[:period]
        lower[:period] = close[:period]
        
        return upper, middle, lower
    
    def _calculate_atr(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """ATR."""
        tr = np.zeros_like(close)
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(close)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        atr = np.zeros_like(close)
        atr[period] = np.mean(tr[:period])
        
        for i in range(period + 1, len(close)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        return atr
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """EMA."""
        ema = np.zeros_like(data)
        multiplier = 2 / (period + 1)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        
        return ema
