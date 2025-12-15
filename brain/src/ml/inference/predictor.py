"""
VIRTUS ML - Unified Predictor
==============================

Interface unificada para predições de todos os modelos ML.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Tipos de modelos disponíveis."""
    LSTM = "lstm"
    KNN = "knn"
    CNN = "cnn"
    ENSEMBLE = "ensemble"
    TRANSFORMER = "transformer"


@dataclass
class Prediction:
    """Resultado de uma predição."""
    model_type: ModelType
    symbol: str
    timestamp: datetime
    
    # Predição principal
    direction: str  # 'UP', 'DOWN', 'NEUTRAL'
    confidence: float  # 0.0 a 1.0
    probabilities: Dict[str, float]  # {class: prob}
    
    # Predição de preço (opcional)
    predicted_price: Optional[float] = None
    predicted_return: Optional[float] = None
    
    # Metadados
    features_used: int = 0
    inference_time_ms: float = 0.0
    model_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'model_type': self.model_type.value,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'direction': self.direction,
            'confidence': self.confidence,
            'probabilities': self.probabilities,
            'predicted_price': self.predicted_price,
            'predicted_return': self.predicted_return,
            'inference_time_ms': self.inference_time_ms,
        }


@dataclass
class EnsemblePrediction:
    """Predição combinada de múltiplos modelos."""
    symbol: str
    timestamp: datetime
    
    # Predição final
    direction: str
    confidence: float
    
    # Predições individuais
    predictions: List[Prediction]
    
    # Consenso
    agreement_ratio: float  # % de modelos concordando
    weighted_confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'direction': self.direction,
            'confidence': self.confidence,
            'agreement_ratio': self.agreement_ratio,
            'weighted_confidence': self.weighted_confidence,
            'individual_predictions': [p.to_dict() for p in self.predictions],
        }


class ModelWrapper:
    """Wrapper base para modelos."""
    
    def __init__(self, model: Any, model_type: ModelType):
        self.model = model
        self.model_type = model_type
        self.is_loaded = model is not None
        
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Faz predição. Retorna (classes, probabilidades)."""
        raise NotImplementedError


class LSTMWrapper(ModelWrapper):
    """Wrapper para modelo LSTM."""
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_loaded:
            raise RuntimeError("Modelo LSTM não carregado")
        
        # Predição
        probs = self.model.predict(X, verbose=0)
        
        # Classes
        classes = np.argmax(probs, axis=1)
        
        return classes, probs


class KNNWrapper(ModelWrapper):
    """Wrapper para modelo k-NN."""
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_loaded:
            raise RuntimeError("Modelo k-NN não carregado")
        
        # Para k-NN, X pode ser features de padrões
        classes = self.model.predict(X)
        probs = self.model.predict_proba(X)
        
        return classes, probs


class CNNWrapper(ModelWrapper):
    """Wrapper para modelo CNN."""
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.is_loaded:
            raise RuntimeError("Modelo CNN não carregado")
        
        # X deve ser batch de imagens
        with torch.no_grad():
            import torch
            import torch.nn.functional as F
            
            if isinstance(X, np.ndarray):
                X = torch.from_numpy(X).float()
            
            logits = self.model(X)
            probs = F.softmax(logits, dim=1).numpy()
            classes = np.argmax(probs, axis=1)
        
        return classes, probs


class UnifiedPredictor:
    """
    Preditor unificado que gerencia múltiplos modelos.
    
    Fornece interface consistente para:
    - Carregar modelos
    - Fazer predições individuais
    - Combinar predições (ensemble)
    """
    
    def __init__(
        self,
        model_dir: Optional[Path] = None,
        cache_enabled: bool = True
    ):
        self.model_dir = model_dir or Path("models")
        self.cache_enabled = cache_enabled
        
        self.models: Dict[str, Dict[ModelType, ModelWrapper]] = {}
        self.weights: Dict[ModelType, float] = {
            ModelType.LSTM: 0.4,
            ModelType.KNN: 0.2,
            ModelType.CNN: 0.4,
        }
        
        self._lock = threading.Lock()
        self._prediction_cache: Dict[str, Prediction] = {}
    
    def load_model(
        self,
        symbol: str,
        model_type: ModelType,
        model_path: Optional[Path] = None
    ) -> bool:
        """
        Carrega um modelo específico.
        
        Args:
            symbol: Símbolo do ativo
            model_type: Tipo do modelo
            model_path: Caminho do modelo (opcional)
            
        Returns:
            True se carregado com sucesso
        """
        with self._lock:
            if symbol not in self.models:
                self.models[symbol] = {}
            
            try:
                if model_type == ModelType.LSTM:
                    wrapper = self._load_lstm(symbol, model_path)
                elif model_type == ModelType.KNN:
                    wrapper = self._load_knn(symbol, model_path)
                elif model_type == ModelType.CNN:
                    wrapper = self._load_cnn(symbol, model_path)
                else:
                    logger.warning(f"Tipo de modelo não suportado: {model_type}")
                    return False
                
                self.models[symbol][model_type] = wrapper
                logger.info(f"Modelo {model_type.value} carregado para {symbol}")
                return True
                
            except Exception as e:
                logger.error(f"Erro ao carregar modelo {model_type.value} para {symbol}: {e}")
                return False
    
    def _load_lstm(self, symbol: str, path: Optional[Path]) -> ModelWrapper:
        """Carrega modelo LSTM."""
        try:
            from tensorflow import keras
            
            model_path = path or self.model_dir / f"lstm/{symbol}/model.h5"
            
            if model_path.exists():
                model = keras.models.load_model(str(model_path))
                return LSTMWrapper(model, ModelType.LSTM)
            else:
                logger.warning(f"Modelo LSTM não encontrado: {model_path}")
                return LSTMWrapper(None, ModelType.LSTM)
                
        except ImportError:
            logger.warning("TensorFlow não disponível")
            return LSTMWrapper(None, ModelType.LSTM)
    
    def _load_knn(self, symbol: str, path: Optional[Path]) -> ModelWrapper:
        """Carrega modelo k-NN."""
        import joblib
        
        model_path = path or self.model_dir / f"knn/{symbol}/model.joblib"
        
        if model_path.exists():
            model = joblib.load(str(model_path))
            return KNNWrapper(model, ModelType.KNN)
        else:
            logger.warning(f"Modelo k-NN não encontrado: {model_path}")
            return KNNWrapper(None, ModelType.KNN)
    
    def _load_cnn(self, symbol: str, path: Optional[Path]) -> ModelWrapper:
        """Carrega modelo CNN."""
        try:
            import torch
            
            model_path = path or self.model_dir / f"cnn/{symbol}/model.pt"
            
            if model_path.exists():
                model = torch.load(str(model_path), map_location='cpu')
                model.eval()
                return CNNWrapper(model, ModelType.CNN)
            else:
                logger.warning(f"Modelo CNN não encontrado: {model_path}")
                return CNNWrapper(None, ModelType.CNN)
                
        except ImportError:
            logger.warning("PyTorch não disponível")
            return CNNWrapper(None, ModelType.CNN)
    
    def predict(
        self,
        symbol: str,
        data: Union[pd.DataFrame, np.ndarray],
        model_type: ModelType,
        return_probabilities: bool = True
    ) -> Prediction:
        """
        Faz predição com um modelo específico.
        
        Args:
            symbol: Símbolo do ativo
            data: Dados para predição
            model_type: Tipo do modelo
            return_probabilities: Se retorna probabilidades
            
        Returns:
            Objeto Prediction
        """
        import time
        start_time = time.time()
        
        # Verifica se modelo está carregado
        if symbol not in self.models or model_type not in self.models[symbol]:
            raise ValueError(f"Modelo {model_type.value} não carregado para {symbol}")
        
        wrapper = self.models[symbol][model_type]
        
        # Prepara dados
        X = self._prepare_data(data, model_type)
        
        # Faz predição
        classes, probs = wrapper.predict(X)
        
        # Interpreta resultado
        class_idx = int(classes[-1])  # Última predição
        class_names = ['DOWN', 'NEUTRAL', 'UP']
        direction = class_names[class_idx] if class_idx < len(class_names) else 'NEUTRAL'
        
        confidence = float(probs[-1, class_idx]) if len(probs.shape) > 1 else 0.5
        
        probabilities = {
            name: float(probs[-1, i]) 
            for i, name in enumerate(class_names)
            if i < probs.shape[1]
        } if len(probs.shape) > 1 else {}
        
        inference_time = (time.time() - start_time) * 1000
        
        prediction = Prediction(
            model_type=model_type,
            symbol=symbol,
            timestamp=datetime.now(),
            direction=direction,
            confidence=confidence,
            probabilities=probabilities,
            features_used=X.shape[-1] if len(X.shape) > 1 else X.shape[0],
            inference_time_ms=inference_time,
        )
        
        return prediction
    
    def predict_ensemble(
        self,
        symbol: str,
        data: Union[pd.DataFrame, np.ndarray],
        model_types: Optional[List[ModelType]] = None
    ) -> EnsemblePrediction:
        """
        Faz predição combinando múltiplos modelos.
        
        Args:
            symbol: Símbolo do ativo
            data: Dados para predição
            model_types: Tipos de modelos a usar (default: todos disponíveis)
            
        Returns:
            EnsemblePrediction
        """
        if model_types is None:
            model_types = list(self.models.get(symbol, {}).keys())
        
        if not model_types:
            raise ValueError(f"Nenhum modelo disponível para {symbol}")
        
        predictions: List[Prediction] = []
        
        # Coleta predições
        for model_type in model_types:
            try:
                pred = self.predict(symbol, data, model_type)
                predictions.append(pred)
            except Exception as e:
                logger.warning(f"Erro na predição {model_type.value}: {e}")
        
        if not predictions:
            raise RuntimeError("Nenhuma predição bem-sucedida")
        
        # Combina predições
        ensemble_pred = self._combine_predictions(symbol, predictions)
        
        return ensemble_pred
    
    def _combine_predictions(
        self,
        symbol: str,
        predictions: List[Prediction]
    ) -> EnsemblePrediction:
        """Combina predições de múltiplos modelos."""
        
        # Votos ponderados
        direction_votes: Dict[str, float] = {'UP': 0, 'DOWN': 0, 'NEUTRAL': 0}
        
        total_weight = 0
        for pred in predictions:
            weight = self.weights.get(pred.model_type, 0.25)
            direction_votes[pred.direction] += weight * pred.confidence
            total_weight += weight
        
        # Normaliza
        for direction in direction_votes:
            direction_votes[direction] /= total_weight
        
        # Direção final
        final_direction = max(direction_votes, key=direction_votes.get)
        final_confidence = direction_votes[final_direction]
        
        # Agreement
        agreements = sum(1 for p in predictions if p.direction == final_direction)
        agreement_ratio = agreements / len(predictions)
        
        # Weighted confidence
        weighted_conf = sum(
            self.weights.get(p.model_type, 0.25) * p.confidence
            for p in predictions if p.direction == final_direction
        )
        
        return EnsemblePrediction(
            symbol=symbol,
            timestamp=datetime.now(),
            direction=final_direction,
            confidence=final_confidence,
            predictions=predictions,
            agreement_ratio=agreement_ratio,
            weighted_confidence=weighted_conf / total_weight,
        )
    
    def _prepare_data(
        self,
        data: Union[pd.DataFrame, np.ndarray],
        model_type: ModelType
    ) -> np.ndarray:
        """Prepara dados para o modelo específico."""
        
        if isinstance(data, pd.DataFrame):
            X = data.values.astype(np.float32)
        else:
            X = data.astype(np.float32)
        
        # Reshape específico por tipo
        if model_type == ModelType.LSTM:
            # LSTM espera (batch, seq_len, features)
            if len(X.shape) == 2:
                X = X.reshape(1, X.shape[0], X.shape[1])
        
        elif model_type == ModelType.CNN:
            # CNN espera (batch, channels, height, width)
            if len(X.shape) == 2:
                # Assume que é uma imagem achatada
                size = int(np.sqrt(X.shape[1]))
                X = X.reshape(-1, 1, size, size)
            elif len(X.shape) == 3:
                X = X.reshape(X.shape[0], 1, X.shape[1], X.shape[2])
        
        return X
    
    def set_model_weights(self, weights: Dict[ModelType, float]):
        """Define pesos para ensemble."""
        self.weights.update(weights)
    
    def get_loaded_models(self, symbol: str) -> List[ModelType]:
        """Retorna lista de modelos carregados para um símbolo."""
        return list(self.models.get(symbol, {}).keys())
    
    def is_model_loaded(self, symbol: str, model_type: ModelType) -> bool:
        """Verifica se modelo está carregado."""
        return (
            symbol in self.models and 
            model_type in self.models[symbol] and
            self.models[symbol][model_type].is_loaded
        )
