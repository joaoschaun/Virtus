"""
VIRTUS ML - Signal Generator
=============================

Gerador de sinais de trading baseado em predições ML.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from .predictor import UnifiedPredictor, Prediction, EnsemblePrediction, ModelType

logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    """Força do sinal."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NEUTRAL = "neutral"


class SignalType(Enum):
    """Tipo de sinal."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


@dataclass
class TradingSignal:
    """Sinal de trading gerado pelo ML."""
    symbol: str
    timestamp: datetime
    
    # Sinal
    signal_type: SignalType
    strength: SignalStrength
    confidence: float
    
    # Preços sugeridos
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Risk/Reward
    risk_reward_ratio: Optional[float] = None
    position_size_suggestion: Optional[float] = None
    
    # Metadados
    source_models: List[str] = field(default_factory=list)
    reasoning: str = ""
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'signal_type': self.signal_type.value,
            'strength': self.strength.value,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'risk_reward_ratio': self.risk_reward_ratio,
            'source_models': self.source_models,
            'reasoning': self.reasoning,
        }
    
    @property
    def is_actionable(self) -> bool:
        """Verifica se sinal é acionável."""
        return (
            self.signal_type in [SignalType.BUY, SignalType.SELL] and
            self.strength in [SignalStrength.STRONG, SignalStrength.MODERATE] and
            self.confidence >= 0.6
        )


@dataclass
class SignalConfig:
    """Configuração do gerador de sinais."""
    # Thresholds
    min_confidence: float = 0.6
    strong_confidence: float = 0.8
    min_agreement: float = 0.6
    
    # Risk Management
    default_stop_loss_pips: float = 30.0
    default_take_profit_pips: float = 60.0
    max_risk_per_trade: float = 0.02  # 2% do capital
    min_risk_reward: float = 1.5
    
    # Filtros
    require_volume_confirmation: bool = True
    require_trend_alignment: bool = True
    
    # Expiração
    signal_validity_minutes: int = 30


class MLSignalGenerator:
    """
    Gerador de sinais de trading baseado em predições ML.
    
    Responsável por:
    - Transformar predições em sinais acionáveis
    - Calcular níveis de entrada/saída
    - Aplicar filtros de qualidade
    - Gerenciar expiração de sinais
    """
    
    def __init__(
        self,
        predictor: UnifiedPredictor,
        config: Optional[SignalConfig] = None
    ):
        self.predictor = predictor
        self.config = config or SignalConfig()
        
        self.active_signals: Dict[str, TradingSignal] = {}
        self.signal_history: List[TradingSignal] = []
    
    def generate_signal(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        current_price: float,
        use_ensemble: bool = True
    ) -> Optional[TradingSignal]:
        """
        Gera sinal de trading para um símbolo.
        
        Args:
            symbol: Símbolo do ativo
            market_data: Dados de mercado recentes
            current_price: Preço atual
            use_ensemble: Se usa ensemble ou modelo individual
            
        Returns:
            TradingSignal ou None se sem sinal
        """
        try:
            # Obtém predição
            if use_ensemble:
                prediction = self.predictor.predict_ensemble(symbol, market_data)
                source_models = [p.model_type.value for p in prediction.predictions]
                confidence = prediction.weighted_confidence
                agreement = prediction.agreement_ratio
            else:
                # Usa LSTM por padrão
                prediction = self.predictor.predict(
                    symbol, market_data, ModelType.LSTM
                )
                source_models = [prediction.model_type.value]
                confidence = prediction.confidence
                agreement = 1.0
            
            # Verifica thresholds
            if confidence < self.config.min_confidence:
                logger.debug(f"{symbol}: Confidence {confidence:.2f} abaixo do mínimo")
                return None
            
            if agreement < self.config.min_agreement:
                logger.debug(f"{symbol}: Agreement {agreement:.2f} abaixo do mínimo")
                return None
            
            # Determina tipo e força do sinal
            direction = prediction.direction
            signal_type = self._direction_to_signal(direction)
            strength = self._calculate_strength(confidence, agreement)
            
            if signal_type == SignalType.HOLD:
                return None
            
            # Calcula níveis de preço
            entry_price, stop_loss, take_profit = self._calculate_levels(
                symbol, signal_type, current_price, market_data
            )
            
            # Calcula R/R
            if stop_loss and take_profit:
                risk = abs(entry_price - stop_loss)
                reward = abs(take_profit - entry_price)
                risk_reward = reward / risk if risk > 0 else 0
                
                # Verifica R/R mínimo
                if risk_reward < self.config.min_risk_reward:
                    logger.debug(f"{symbol}: R/R {risk_reward:.2f} abaixo do mínimo")
                    return None
            else:
                risk_reward = None
            
            # Gera reasoning
            reasoning = self._generate_reasoning(
                symbol, signal_type, confidence, agreement, source_models
            )
            
            # Cria sinal
            signal = TradingSignal(
                symbol=symbol,
                timestamp=datetime.now(),
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=risk_reward,
                source_models=source_models,
                reasoning=reasoning,
                expires_at=datetime.now() + pd.Timedelta(
                    minutes=self.config.signal_validity_minutes
                ),
            )
            
            # Armazena
            self.active_signals[symbol] = signal
            self.signal_history.append(signal)
            
            logger.info(f"Sinal gerado: {signal.to_dict()}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Erro ao gerar sinal para {symbol}: {e}")
            return None
    
    def _direction_to_signal(self, direction: str) -> SignalType:
        """Converte direção em tipo de sinal."""
        if direction == 'UP':
            return SignalType.BUY
        elif direction == 'DOWN':
            return SignalType.SELL
        else:
            return SignalType.HOLD
    
    def _calculate_strength(
        self,
        confidence: float,
        agreement: float
    ) -> SignalStrength:
        """Calcula força do sinal."""
        combined_score = (confidence + agreement) / 2
        
        if combined_score >= 0.8:
            return SignalStrength.STRONG
        elif combined_score >= 0.65:
            return SignalStrength.MODERATE
        elif combined_score >= 0.5:
            return SignalStrength.WEAK
        else:
            return SignalStrength.NEUTRAL
    
    def _calculate_levels(
        self,
        symbol: str,
        signal_type: SignalType,
        current_price: float,
        market_data: pd.DataFrame
    ) -> Tuple[float, float, float]:
        """Calcula níveis de entrada, stop e target."""
        
        # Calcula ATR para stops dinâmicos
        if 'high' in market_data.columns and 'low' in market_data.columns:
            highs = market_data['high'].values[-20:]
            lows = market_data['low'].values[-20:]
            closes = market_data['close'].values[-20:]
            
            tr = np.maximum(
                highs - lows,
                np.maximum(
                    np.abs(highs - np.roll(closes, 1)),
                    np.abs(lows - np.roll(closes, 1))
                )
            )
            atr = np.nanmean(tr[1:])  # Ignora primeiro (NaN do roll)
        else:
            # Fallback para pips fixos
            atr = self._pips_to_price(symbol, self.config.default_stop_loss_pips)
        
        entry_price = current_price
        
        if signal_type == SignalType.BUY:
            stop_loss = current_price - (atr * 1.5)
            take_profit = current_price + (atr * 3.0)
        elif signal_type == SignalType.SELL:
            stop_loss = current_price + (atr * 1.5)
            take_profit = current_price - (atr * 3.0)
        else:
            stop_loss = current_price
            take_profit = current_price
        
        return entry_price, stop_loss, take_profit
    
    def _pips_to_price(self, symbol: str, pips: float) -> float:
        """Converte pips para preço."""
        # Determina tamanho do pip baseado no símbolo
        if 'JPY' in symbol:
            pip_size = 0.01
        elif 'XAU' in symbol:
            pip_size = 0.1
        else:
            pip_size = 0.0001
        
        return pips * pip_size
    
    def _generate_reasoning(
        self,
        symbol: str,
        signal_type: SignalType,
        confidence: float,
        agreement: float,
        models: List[str]
    ) -> str:
        """Gera explicação do sinal."""
        
        action = "compra" if signal_type == SignalType.BUY else "venda"
        models_str = ", ".join(models)
        
        reasoning = (
            f"Sinal de {action} para {symbol} baseado em análise de {len(models)} "
            f"modelos ML ({models_str}). Confiança: {confidence:.1%}, "
            f"Concordância entre modelos: {agreement:.1%}."
        )
        
        return reasoning
    
    def get_active_signal(self, symbol: str) -> Optional[TradingSignal]:
        """Retorna sinal ativo para um símbolo."""
        signal = self.active_signals.get(symbol)
        
        if signal and signal.expires_at:
            if datetime.now() > signal.expires_at:
                del self.active_signals[symbol]
                return None
        
        return signal
    
    def invalidate_signal(self, symbol: str):
        """Invalida sinal para um símbolo."""
        if symbol in self.active_signals:
            del self.active_signals[symbol]
    
    def get_all_active_signals(self) -> List[TradingSignal]:
        """Retorna todos os sinais ativos válidos."""
        now = datetime.now()
        valid_signals = []
        
        for symbol, signal in list(self.active_signals.items()):
            if signal.expires_at and now > signal.expires_at:
                del self.active_signals[symbol]
            else:
                valid_signals.append(signal)
        
        return valid_signals
    
    def get_signal_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas dos sinais."""
        if not self.signal_history:
            return {'total_signals': 0}
        
        buy_signals = sum(1 for s in self.signal_history if s.signal_type == SignalType.BUY)
        sell_signals = sum(1 for s in self.signal_history if s.signal_type == SignalType.SELL)
        
        avg_confidence = np.mean([s.confidence for s in self.signal_history])
        strong_signals = sum(1 for s in self.signal_history if s.strength == SignalStrength.STRONG)
        
        return {
            'total_signals': len(self.signal_history),
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'avg_confidence': avg_confidence,
            'strong_signals_ratio': strong_signals / len(self.signal_history),
            'active_signals': len(self.active_signals),
        }
