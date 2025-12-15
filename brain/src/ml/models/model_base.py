"""
VIRTUS ML Model Base
=====================

Base para modelos de Machine Learning com:
- Feature engineering avançado
- Model registry
- Prediction engine
- Online learning
- Model validation
- A/B testing framework
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import deque
import numpy as np
import json
from pathlib import Path

from ...core import VirtusLogger


class ModelType(Enum):
    """Tipos de modelo."""
    DIRECTION = "direction"  # Prediz direção
    ENTRY_PROBABILITY = "entry_probability"  # Probabilidade de entry
    EXIT_TIMING = "exit_timing"  # Timing de saída
    VOLATILITY = "volatility"  # Previsão de volatilidade
    REGIME = "regime"  # Regime de mercado
    TREND_STRENGTH = "trend_strength"  # Força da tendência
    REVERSAL_PROBABILITY = "reversal_probability"  # Probabilidade de reversão


class ModelStatus(Enum):
    """Status do modelo."""
    TRAINING = "training"
    VALIDATING = "validating"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class ModelMetrics:
    """Métricas de performance do modelo."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_predictions: int = 0
    correct_predictions: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update(self, prediction: Any, actual: Any, profit: float = 0) -> None:
        """Atualiza métricas com nova predição."""
        self.total_predictions += 1
        
        if prediction == actual:
            self.correct_predictions += 1
        
        if self.total_predictions > 0:
            self.accuracy = self.correct_predictions / self.total_predictions
        
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'accuracy': round(self.accuracy, 4),
            'precision': round(self.precision, 4),
            'recall': round(self.recall, 4),
            'f1_score': round(self.f1_score, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'profit_factor': round(self.profit_factor, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'win_rate': round(self.win_rate, 4),
            'total_predictions': self.total_predictions,
            'correct_predictions': self.correct_predictions,
        }


@dataclass
class Feature:
    """Definição de feature."""
    name: str
    description: str
    calculator: Callable
    lookback: int = 0
    normalize: bool = True
    min_val: Optional[float] = None
    max_val: Optional[float] = None


@dataclass
class Prediction:
    """Resultado de uma predição."""
    model_name: str
    model_type: ModelType
    value: Any
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    features_used: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseModel(ABC):
    """
    Classe base abstrata para modelos de ML.
    
    Todos os modelos devem herdar desta classe e implementar
    os métodos abstratos.
    """
    
    def __init__(
        self,
        name: str,
        model_type: ModelType,
        features: List[Feature],
        min_samples: int = 100,
    ):
        self.name = name
        self.model_type = model_type
        self.features = features
        self.min_samples = min_samples
        
        self.status = ModelStatus.TRAINING
        self.metrics = ModelMetrics()
        self.created_at = datetime.now()
        self.last_trained = None
        
        self.logger = VirtusLogger.get_logger(f"model_{name}")
        
        # Training data
        self._training_data: List[Dict] = []
        self._feature_values: deque = deque(maxlen=10000)
        
        # Predictions history
        self._predictions: deque = deque(maxlen=1000)
    
    @abstractmethod
    async def train(self, data: List[Dict]) -> bool:
        """
        Treina o modelo com os dados fornecidos.
        
        Args:
            data: Lista de dicionários com features e labels
            
        Returns:
            True se treino foi bem sucedido
        """
        pass
    
    @abstractmethod
    async def predict(self, features: Dict[str, float]) -> Prediction:
        """
        Faz uma predição com as features fornecidas.
        
        Args:
            features: Dicionário de features
            
        Returns:
            Prediction com resultado
        """
        pass
    
    @abstractmethod
    async def update(self, features: Dict[str, float], actual: Any) -> None:
        """
        Atualiza modelo com novo dado (online learning).
        
        Args:
            features: Features usadas na predição
            actual: Valor real observado
        """
        pass
    
    def calculate_features(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calcula features a partir de dados de mercado."""
        result = {}
        
        for feature in self.features:
            try:
                value = feature.calculator(market_data)
                
                if feature.normalize and feature.min_val is not None and feature.max_val is not None:
                    # Normaliza para [0, 1]
                    range_val = feature.max_val - feature.min_val
                    if range_val > 0:
                        value = (value - feature.min_val) / range_val
                        value = max(0, min(1, value))
                
                result[feature.name] = value
            except Exception as e:
                self.logger.warning(f"Error calculating feature {feature.name}: {e}")
                result[feature.name] = 0.0
        
        return result
    
    def validate(self, validation_data: List[Dict]) -> Dict[str, float]:
        """Valida modelo com dados de validação."""
        if not validation_data:
            return {}
        
        correct = 0
        total = 0
        
        for sample in validation_data:
            features = sample.get('features', {})
            actual = sample.get('label')
            
            # Predição síncrona para validação
            prediction = asyncio.run(self.predict(features))
            
            if prediction.value == actual:
                correct += 1
            total += 1
        
        accuracy = correct / total if total > 0 else 0
        
        return {
            'accuracy': accuracy,
            'total_samples': total,
            'correct': correct,
        }
    
    def save(self, path: str) -> bool:
        """Salva modelo em arquivo."""
        try:
            model_data = {
                'name': self.name,
                'type': self.model_type.value,
                'status': self.status.value,
                'metrics': self.metrics.to_dict(),
                'created_at': self.created_at.isoformat(),
                'last_trained': self.last_trained.isoformat() if self.last_trained else None,
            }
            
            with open(path, 'w') as f:
                json.dump(model_data, f, indent=2)
            
            return True
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            return False
    
    def load(self, path: str) -> bool:
        """Carrega modelo de arquivo."""
        try:
            with open(path, 'r') as f:
                model_data = json.load(f)
            
            self.name = model_data['name']
            self.status = ModelStatus(model_data['status'])
            
            return True
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna informações do modelo."""
        return {
            'name': self.name,
            'type': self.model_type.value,
            'status': self.status.value,
            'metrics': self.metrics.to_dict(),
            'features': [f.name for f in self.features],
            'min_samples': self.min_samples,
            'created_at': self.created_at.isoformat(),
            'last_trained': self.last_trained.isoformat() if self.last_trained else None,
            'predictions_count': len(self._predictions),
        }


class DirectionModel(BaseModel):
    """
    Modelo para prever direção do mercado.
    
    Usa ensemble de técnicas simples para predizer
    se o preço vai subir ou descer.
    """
    
    def __init__(
        self,
        name: str = "direction_predictor",
        features: List[Feature] = None,
    ):
        if features is None:
            features = self._get_default_features()
        
        super().__init__(
            name=name,
            model_type=ModelType.DIRECTION,
            features=features,
            min_samples=200,
        )
        
        # Pesos das features (aprendidos durante treino)
        self._weights: Dict[str, float] = {}
        self._bias: float = 0.0
        self._threshold: float = 0.5
        
        # Learning rate para online learning
        self._learning_rate: float = 0.01
    
    def _get_default_features(self) -> List[Feature]:
        """Retorna features padrão para direção."""
        return [
            Feature(
                name="rsi_14",
                description="RSI de 14 períodos",
                calculator=lambda d: d.get('rsi', 50),
                normalize=True,
                min_val=0,
                max_val=100
            ),
            Feature(
                name="macd_hist",
                description="Histograma MACD normalizado",
                calculator=lambda d: d.get('macd_histogram', 0),
                normalize=True,
                min_val=-0.01,
                max_val=0.01
            ),
            Feature(
                name="trend_strength",
                description="Força da tendência (ADX)",
                calculator=lambda d: d.get('adx', 25),
                normalize=True,
                min_val=0,
                max_val=100
            ),
            Feature(
                name="price_vs_sma",
                description="Preço vs SMA 20",
                calculator=lambda d: 1 if d.get('close', 0) > d.get('sma_20', 0) else 0,
                normalize=False
            ),
            Feature(
                name="volume_ratio",
                description="Ratio de volume",
                calculator=lambda d: d.get('volume', 0) / max(d.get('avg_volume', 1), 1),
                normalize=True,
                min_val=0,
                max_val=5
            ),
            Feature(
                name="momentum",
                description="Momentum de preço",
                calculator=lambda d: d.get('momentum', 0),
                normalize=True,
                min_val=-0.02,
                max_val=0.02
            ),
        ]
    
    async def train(self, data: List[Dict]) -> bool:
        """Treina o modelo com regressão logística simples."""
        if len(data) < self.min_samples:
            self.logger.warning(
                f"Insufficient data for training: {len(data)} < {self.min_samples}"
            )
            return False
        
        self.status = ModelStatus.TRAINING
        
        try:
            # Inicializa pesos
            for feature in self.features:
                self._weights[feature.name] = np.random.randn() * 0.1
            self._bias = 0.0
            
            # Treina por múltiplas épocas
            epochs = 100
            batch_size = 32
            
            for epoch in range(epochs):
                np.random.shuffle(data)
                total_loss = 0
                
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    
                    for sample in batch:
                        features = sample.get('features', {})
                        label = sample.get('label', 0)  # 1 = up, 0 = down
                        
                        # Forward pass
                        z = self._bias
                        for fname, fval in features.items():
                            if fname in self._weights:
                                z += self._weights[fname] * fval
                        
                        # Sigmoid
                        prediction = 1 / (1 + np.exp(-z))
                        
                        # Loss (binary cross entropy)
                        loss = -label * np.log(prediction + 1e-10) - (1 - label) * np.log(1 - prediction + 1e-10)
                        total_loss += loss
                        
                        # Gradient descent
                        error = prediction - label
                        
                        for fname, fval in features.items():
                            if fname in self._weights:
                                self._weights[fname] -= self._learning_rate * error * fval
                        
                        self._bias -= self._learning_rate * error
                
                avg_loss = total_loss / len(data)
                
                if epoch % 20 == 0:
                    self.logger.debug(f"Epoch {epoch}: Loss = {avg_loss:.4f}")
            
            self.last_trained = datetime.now()
            self.status = ModelStatus.PRODUCTION
            
            self.logger.info(f"Model {self.name} trained successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            self.status = ModelStatus.FAILED
            return False
    
    async def predict(self, features: Dict[str, float]) -> Prediction:
        """Faz predição de direção."""
        # Forward pass
        z = self._bias
        for fname, fval in features.items():
            if fname in self._weights:
                z += self._weights[fname] * fval
        
        # Sigmoid
        probability = 1 / (1 + np.exp(-z))
        
        # Classificação
        direction = "up" if probability > self._threshold else "down"
        confidence = abs(probability - 0.5) * 2  # Normaliza confiança
        
        prediction = Prediction(
            model_name=self.name,
            model_type=self.model_type,
            value=direction,
            confidence=confidence,
            features_used=features,
            metadata={
                'raw_probability': probability,
                'threshold': self._threshold,
            }
        )
        
        self._predictions.append(prediction)
        
        return prediction
    
    async def update(self, features: Dict[str, float], actual: Any) -> None:
        """Online learning - atualiza com novo dado."""
        # Converte actual para label
        label = 1 if actual == "up" else 0
        
        # Forward pass
        z = self._bias
        for fname, fval in features.items():
            if fname in self._weights:
                z += self._weights[fname] * fval
        
        prediction = 1 / (1 + np.exp(-z))
        
        # Atualiza métricas
        predicted_label = 1 if prediction > self._threshold else 0
        self.metrics.update(predicted_label, label)
        
        # Gradient update
        error = prediction - label
        
        for fname, fval in features.items():
            if fname in self._weights:
                self._weights[fname] -= self._learning_rate * 0.1 * error * fval
        
        self._bias -= self._learning_rate * 0.1 * error


class ModelRegistry:
    """
    Registry central para gerenciamento de modelos.
    """
    
    def __init__(self, models_dir: str = "models"):
        self.logger = VirtusLogger.get_logger("model_registry")
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._models: Dict[str, BaseModel] = {}
        self._active_models: Dict[ModelType, str] = {}
    
    def register(self, model: BaseModel) -> bool:
        """Registra um modelo."""
        if model.name in self._models:
            self.logger.warning(f"Model {model.name} already registered")
            return False
        
        self._models[model.name] = model
        
        # Se não há modelo ativo para este tipo, ativa este
        if model.model_type not in self._active_models:
            self._active_models[model.model_type] = model.name
        
        self.logger.info(f"Model {model.name} registered")
        return True
    
    def get_model(self, name: str) -> Optional[BaseModel]:
        """Obtém modelo pelo nome."""
        return self._models.get(name)
    
    def get_active_model(self, model_type: ModelType) -> Optional[BaseModel]:
        """Obtém modelo ativo para um tipo."""
        name = self._active_models.get(model_type)
        if name:
            return self._models.get(name)
        return None
    
    def set_active(self, name: str) -> bool:
        """Define modelo como ativo para seu tipo."""
        model = self._models.get(name)
        if not model:
            return False
        
        self._active_models[model.model_type] = name
        self.logger.info(f"Model {name} set as active for {model.model_type.value}")
        return True
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Lista todos os modelos registrados."""
        return [model.get_info() for model in self._models.values()]
    
    async def train_model(self, name: str, data: List[Dict]) -> bool:
        """Treina um modelo específico."""
        model = self._models.get(name)
        if not model:
            return False
        
        return await model.train(data)
    
    async def predict(
        self,
        model_type: ModelType,
        features: Dict[str, float]
    ) -> Optional[Prediction]:
        """Faz predição usando modelo ativo do tipo especificado."""
        model = self.get_active_model(model_type)
        if not model:
            return None
        
        return await model.predict(features)
    
    def save_all(self) -> int:
        """Salva todos os modelos."""
        saved = 0
        for name, model in self._models.items():
            path = self.models_dir / f"{name}.json"
            if model.save(str(path)):
                saved += 1
        return saved
