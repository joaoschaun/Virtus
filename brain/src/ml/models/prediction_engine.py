"""
VIRTUS Prediction Engine
=========================

Motor de predição que:
- Combina múltiplos modelos
- Gera ensemble predictions
- Gerencia confidence aggregation
- Faz feature caching
- Implementa prediction logging
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import numpy as np

from ...core import VirtusLogger
from .model_base import (
    ModelRegistry, BaseModel, ModelType, Prediction,
    DirectionModel, ModelStatus
)


@dataclass
class EnsemblePrediction:
    """Predição combinada de múltiplos modelos."""
    direction: str  # "up", "down", "neutral"
    confidence: float
    probability_up: float
    probability_down: float
    
    contributing_models: List[str]
    model_predictions: Dict[str, Prediction]
    
    features_snapshot: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Tracking
    actual_outcome: Optional[str] = None
    was_correct: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'direction': self.direction,
            'confidence': round(self.confidence, 4),
            'probability_up': round(self.probability_up, 4),
            'probability_down': round(self.probability_down, 4),
            'contributing_models': self.contributing_models,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class FeatureCache:
    """Cache de features calculadas."""
    features: Dict[str, float]
    calculated_at: datetime
    market_data_hash: str
    
    def is_valid(self, max_age_seconds: float = 5.0) -> bool:
        """Verifica se cache ainda é válido."""
        age = (datetime.now() - self.calculated_at).total_seconds()
        return age < max_age_seconds


class PredictionEngine:
    """
    Motor de predição integrado.
    
    Combina múltiplos modelos de ML para gerar predições
    de alta qualidade com ensemble voting.
    
    Features:
    - Ensemble de modelos
    - Weighted voting
    - Confidence aggregation
    - Feature caching
    - Prediction logging
    - Performance tracking
    """
    
    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        min_confidence: float = 0.3,
        ensemble_threshold: float = 0.6,  # % de modelos que devem concordar
    ):
        self.logger = VirtusLogger.get_logger("prediction_engine")
        
        self.registry = registry or ModelRegistry()
        self.min_confidence = min_confidence
        self.ensemble_threshold = ensemble_threshold
        
        # Feature cache
        self._feature_cache: Dict[str, FeatureCache] = {}
        
        # Prediction history
        self._predictions: deque = deque(maxlen=10000)
        
        # Performance tracking
        self._correct_predictions = 0
        self._total_predictions = 0
        
        # Model weights para ensemble
        self._model_weights: Dict[str, float] = {}
    
    async def predict_direction(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        use_ensemble: bool = True,
    ) -> EnsemblePrediction:
        """
        Prediz direção do mercado.
        
        Args:
            symbol: Símbolo do ativo
            market_data: Dados de mercado atuais
            use_ensemble: Se deve usar ensemble de modelos
            
        Returns:
            EnsemblePrediction com resultado
        """
        # Calcula features
        features = await self._calculate_features(symbol, market_data)
        
        if not use_ensemble:
            # Usa apenas modelo ativo
            model = self.registry.get_active_model(ModelType.DIRECTION)
            if not model:
                return self._create_neutral_prediction(features)
            
            pred = await model.predict(features)
            
            return EnsemblePrediction(
                direction=pred.value,
                confidence=pred.confidence,
                probability_up=pred.metadata.get('raw_probability', 0.5),
                probability_down=1 - pred.metadata.get('raw_probability', 0.5),
                contributing_models=[model.name],
                model_predictions={model.name: pred},
                features_snapshot=features,
            )
        
        # Ensemble prediction
        return await self._ensemble_predict(ModelType.DIRECTION, features)
    
    async def _calculate_features(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calcula features com caching."""
        # Cria hash dos dados para cache
        data_hash = str(hash(frozenset(
            (k, v) for k, v in market_data.items()
            if isinstance(v, (int, float, str, bool))
        )))
        
        cache_key = f"{symbol}_{data_hash}"
        
        # Verifica cache
        if cache_key in self._feature_cache:
            cache = self._feature_cache[cache_key]
            if cache.is_valid():
                return cache.features
        
        # Calcula features
        features = {}
        
        # Features básicas
        features['rsi'] = market_data.get('rsi', 50) / 100
        features['macd_histogram'] = self._normalize(
            market_data.get('macd_histogram', 0), -0.01, 0.01
        )
        features['adx'] = market_data.get('adx', 25) / 100
        
        # Trend features
        close = market_data.get('close', 0)
        sma_20 = market_data.get('sma_20', close)
        sma_50 = market_data.get('sma_50', close)
        sma_200 = market_data.get('sma_200', close)
        
        features['price_vs_sma20'] = 1 if close > sma_20 else 0
        features['price_vs_sma50'] = 1 if close > sma_50 else 0
        features['sma20_vs_sma50'] = 1 if sma_20 > sma_50 else 0
        features['sma50_vs_sma200'] = 1 if sma_50 > sma_200 else 0
        
        # Volume features
        volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume', volume)
        features['volume_ratio'] = self._normalize(
            volume / max(avg_volume, 1), 0, 5
        )
        
        # Momentum features
        features['momentum'] = self._normalize(
            market_data.get('momentum', 0), -0.02, 0.02
        )
        features['roc'] = self._normalize(
            market_data.get('roc', 0), -5, 5
        )
        
        # Volatility features
        atr = market_data.get('atr', 0)
        features['atr_normalized'] = self._normalize(
            atr / close if close > 0 else 0, 0, 0.05
        )
        
        # SMC features
        features['in_premium'] = 1 if market_data.get('in_premium_zone', False) else 0
        features['in_discount'] = 1 if market_data.get('in_discount_zone', False) else 0
        features['near_ob'] = 1 if market_data.get('near_order_block', False) else 0
        features['near_fvg'] = 1 if market_data.get('near_fvg', False) else 0
        
        # Structure features
        features['bullish_bos'] = 1 if market_data.get('bullish_bos', False) else 0
        features['bearish_bos'] = 1 if market_data.get('bearish_bos', False) else 0
        features['choch'] = 1 if market_data.get('choch', False) else 0
        
        # Divergence features
        features['bullish_div'] = 1 if market_data.get('bullish_divergence', False) else 0
        features['bearish_div'] = 1 if market_data.get('bearish_divergence', False) else 0
        
        # Atualiza cache
        self._feature_cache[cache_key] = FeatureCache(
            features=features,
            calculated_at=datetime.now(),
            market_data_hash=data_hash
        )
        
        # Limpa cache antigo
        self._cleanup_cache()
        
        return features
    
    def _normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normaliza valor para [0, 1]."""
        if max_val == min_val:
            return 0.5
        normalized = (value - min_val) / (max_val - min_val)
        return max(0, min(1, normalized))
    
    def _cleanup_cache(self, max_entries: int = 100) -> None:
        """Remove entradas antigas do cache."""
        if len(self._feature_cache) > max_entries:
            # Remove entradas mais antigas
            sorted_keys = sorted(
                self._feature_cache.keys(),
                key=lambda k: self._feature_cache[k].calculated_at
            )
            
            for key in sorted_keys[:-max_entries]:
                del self._feature_cache[key]
    
    async def _ensemble_predict(
        self,
        model_type: ModelType,
        features: Dict[str, float]
    ) -> EnsemblePrediction:
        """
        Faz predição ensemble combinando múltiplos modelos.
        """
        # Obtém todos os modelos do tipo
        models = [
            m for m in self.registry._models.values()
            if m.model_type == model_type and m.status == ModelStatus.PRODUCTION
        ]
        
        if not models:
            return self._create_neutral_prediction(features)
        
        predictions: Dict[str, Prediction] = {}
        up_votes = 0.0
        down_votes = 0.0
        total_weight = 0.0
        
        for model in models:
            try:
                pred = await model.predict(features)
                predictions[model.name] = pred
                
                # Peso do modelo (baseado em performance histórica)
                weight = self._model_weights.get(model.name, 1.0)
                
                # Voto ponderado
                if pred.value == "up":
                    up_votes += weight * pred.confidence
                elif pred.value == "down":
                    down_votes += weight * pred.confidence
                
                total_weight += weight
                
            except Exception as e:
                self.logger.warning(f"Model {model.name} prediction failed: {e}")
        
        if total_weight == 0:
            return self._create_neutral_prediction(features)
        
        # Normaliza votos
        probability_up = up_votes / total_weight if total_weight > 0 else 0.5
        probability_down = down_votes / total_weight if total_weight > 0 else 0.5
        
        # Normaliza probabilidades
        total_prob = probability_up + probability_down
        if total_prob > 0:
            probability_up /= total_prob
            probability_down /= total_prob
        
        # Determina direção
        if probability_up > self.ensemble_threshold:
            direction = "up"
            confidence = probability_up
        elif probability_down > self.ensemble_threshold:
            direction = "down"
            confidence = probability_down
        else:
            direction = "neutral"
            confidence = 1 - abs(probability_up - probability_down)
        
        # Ajusta confiança mínima
        if confidence < self.min_confidence:
            direction = "neutral"
        
        ensemble_pred = EnsemblePrediction(
            direction=direction,
            confidence=confidence,
            probability_up=probability_up,
            probability_down=probability_down,
            contributing_models=list(predictions.keys()),
            model_predictions=predictions,
            features_snapshot=features,
        )
        
        self._predictions.append(ensemble_pred)
        self._total_predictions += 1
        
        return ensemble_pred
    
    def _create_neutral_prediction(
        self,
        features: Dict[str, float]
    ) -> EnsemblePrediction:
        """Cria predição neutra quando não há modelos disponíveis."""
        return EnsemblePrediction(
            direction="neutral",
            confidence=0.0,
            probability_up=0.5,
            probability_down=0.5,
            contributing_models=[],
            model_predictions={},
            features_snapshot=features,
        )
    
    async def record_outcome(
        self,
        prediction: EnsemblePrediction,
        actual_direction: str
    ) -> None:
        """Registra resultado real para atualizar modelos."""
        prediction.actual_outcome = actual_direction
        prediction.was_correct = (prediction.direction == actual_direction)
        
        if prediction.was_correct:
            self._correct_predictions += 1
        
        # Atualiza pesos dos modelos
        for model_name, model_pred in prediction.model_predictions.items():
            model_correct = (model_pred.value == actual_direction)
            
            current_weight = self._model_weights.get(model_name, 1.0)
            
            if model_correct:
                # Aumenta peso levemente
                self._model_weights[model_name] = min(2.0, current_weight * 1.01)
            else:
                # Diminui peso
                self._model_weights[model_name] = max(0.1, current_weight * 0.99)
        
        # Online learning nos modelos
        for model_name in prediction.contributing_models:
            model = self.registry.get_model(model_name)
            if model:
                await model.update(prediction.features_snapshot, actual_direction)
    
    def get_accuracy(self) -> float:
        """Retorna acurácia geral do engine."""
        if self._total_predictions == 0:
            return 0.0
        return self._correct_predictions / self._total_predictions
    
    def get_recent_predictions(self, count: int = 10) -> List[Dict[str, Any]]:
        """Retorna predições recentes."""
        predictions = list(self._predictions)[-count:]
        return [p.to_dict() for p in predictions]
    
    def get_model_weights(self) -> Dict[str, float]:
        """Retorna pesos atuais dos modelos."""
        return self._model_weights.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do engine."""
        return {
            'total_predictions': self._total_predictions,
            'correct_predictions': self._correct_predictions,
            'accuracy': round(self.get_accuracy(), 4),
            'model_weights': {k: round(v, 3) for k, v in self._model_weights.items()},
            'registered_models': len(self.registry._models),
            'cache_size': len(self._feature_cache),
        }


class PredictionService:
    """
    Serviço de predição para integração com o sistema de trading.
    
    Inclui:
    - Modelos de ML tradicionais (DirectionModel)
    - VirtusVisionAnalyzer para análise visual de padrões
    """
    
    _instance: Optional['PredictionService'] = None
    
    def __init__(self, models_dir: str = "models"):
        self.logger = VirtusLogger.get_logger("prediction_service")
        
        self.registry = ModelRegistry(models_dir)
        self.engine = PredictionEngine(self.registry)
        
        # Vision Analyzer (opcional - não bloqueia se não disponível)
        self.vision_analyzer = None
        self._vision_available = False
        
        self._initialized = False
        
        PredictionService._instance = self
    
    @classmethod
    def get_instance(cls) -> Optional['PredictionService']:
        """Obtém instância singleton."""
        return cls._instance
    
    async def initialize(self) -> bool:
        """Inicializa o serviço com modelos padrão."""
        try:
            # Registra modelo de direção padrão
            direction_model = DirectionModel()
            self.registry.register(direction_model)
            
            # Tenta inicializar Vision Analyzer (opcional)
            try:
                from .vision import VirtusVisionAnalyzer
                self.vision_analyzer = VirtusVisionAnalyzer(
                    use_tensorflow=False,  # Usa sklearn por padrão
                    use_pytorch=False
                )
                self._vision_available = True
                self.logger.info("✅ Vision Analyzer integrado ao PredictionService")
            except ImportError:
                self.logger.info("ℹ️ Vision Analyzer não disponível (dependências)")
            except Exception as e:
                self.logger.warning(f"⚠️ Vision Analyzer falhou: {e}")
            
            self._initialized = True
            self.logger.info("Prediction service initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
            return False
    
    async def predict(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        ohlcv_df: Any = None,  # DataFrame para Vision
    ) -> Optional[EnsemblePrediction]:
        """
        Obtém predição para um símbolo.
        
        Args:
            symbol: Símbolo do ativo
            market_data: Dados de mercado atuais
            ohlcv_df: DataFrame OHLCV para análise visual (opcional)
            
        Returns:
            EnsemblePrediction ou None se não disponível
        """
        if not self._initialized:
            return None
        
        try:
            # Predição do ensemble tradicional
            ensemble_pred = await self.engine.predict_direction(symbol, market_data)
            
            # Adiciona análise visual se disponível
            if self._vision_available and ohlcv_df is not None and len(ohlcv_df) >= 50:
                try:
                    vision_result = await self._get_vision_prediction(ohlcv_df)
                    if vision_result:
                        ensemble_pred = self._combine_with_vision(ensemble_pred, vision_result)
                except Exception as e:
                    self.logger.warning(f"Vision analysis failed: {e}")
            
            return ensemble_pred
            
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return None
    
    async def _get_vision_prediction(self, df) -> Optional[Dict[str, Any]]:
        """Obtém predição do Vision Analyzer."""
        if not self.vision_analyzer:
            return None
        
        try:
            # Análise visual do gráfico
            analysis = self.vision_analyzer.analyze(df)
            
            if analysis and 'overall_bias' in analysis:
                return {
                    'direction': analysis['overall_bias'],
                    'confidence': analysis.get('confidence', 0.5),
                    'patterns': analysis.get('patterns_detected', []),
                    'support_resistance': analysis.get('key_levels', {}),
                }
        except Exception as e:
            self.logger.debug(f"Vision analysis error: {e}")
        
        return None
    
    def _combine_with_vision(
        self,
        ensemble: EnsemblePrediction,
        vision: Dict[str, Any]
    ) -> EnsemblePrediction:
        """Combina predição ensemble com análise visual."""
        vision_dir = vision.get('direction', 'neutral')
        vision_conf = vision.get('confidence', 0.5)
        
        # Peso do vision: 20% da decisão final
        vision_weight = 0.2
        
        # Ajusta probabilidades baseado na visão
        if vision_dir == 'bullish':
            adj_up = ensemble.probability_up * (1 - vision_weight) + vision_conf * vision_weight
            adj_down = ensemble.probability_down * (1 - vision_weight) + (1 - vision_conf) * vision_weight * 0.5
        elif vision_dir == 'bearish':
            adj_up = ensemble.probability_up * (1 - vision_weight) + (1 - vision_conf) * vision_weight * 0.5
            adj_down = ensemble.probability_down * (1 - vision_weight) + vision_conf * vision_weight
        else:
            adj_up = ensemble.probability_up
            adj_down = ensemble.probability_down
        
        # Normaliza
        total = adj_up + adj_down
        if total > 0:
            adj_up /= total
            adj_down /= total
        
        # Recalcula direção
        if adj_up > 0.6:
            new_direction = "up"
            new_confidence = adj_up
        elif adj_down > 0.6:
            new_direction = "down"
            new_confidence = adj_down
        else:
            new_direction = "neutral"
            new_confidence = 1 - abs(adj_up - adj_down)
        
        # Adiciona vision aos contributing models
        contributing = list(ensemble.contributing_models) + ['VirtusVisionAnalyzer']
        
        return EnsemblePrediction(
            direction=new_direction,
            confidence=new_confidence,
            probability_up=adj_up,
            probability_down=adj_down,
            contributing_models=contributing,
            model_predictions=ensemble.model_predictions,
            features_snapshot=ensemble.features_snapshot,
        )
    
    async def train_models(self, training_data: List[Dict]) -> bool:
        """Treina todos os modelos registrados."""
        success = True
        
        for model in self.registry._models.values():
            try:
                result = await model.train(training_data)
                if not result:
                    success = False
            except Exception as e:
                self.logger.error(f"Training failed for {model.name}: {e}")
                success = False
        
        return success
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do serviço."""
        return {
            'initialized': self._initialized,
            'models': self.registry.list_models(),
            'engine_stats': self.engine.get_statistics(),
            'vision_available': self._vision_available,
        }
