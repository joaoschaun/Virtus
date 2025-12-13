"""
BRAIN - Trend Following Strategy
Estratégia de seguimento de tendência
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np

from ..base_strategy import (
    BaseStrategy, StrategyConfig, StrategyState,
    StrategyFactory
)
from ...core.types import Signal, SignalDirection, MarketRegime
from ...core.logger import get_logger

logger = get_logger("strategy.trend")


class TrendFollowingStrategy(BaseStrategy):
    """
    Estratégia de Seguimento de Tendência
    
    Características:
    - Timeframes médios (H1, H4)
    - Alvos maiores (50-200 pips)
    - Menor frequência, maior assertividade
    
    Condições de entrada:
    - Tendência definida (EMAs alinhadas)
    - Pullback para média
    - Rompimento de estrutura
    """
    
    def __init__(self, config: StrategyConfig, symbol: str):
        super().__init__(config, symbol)
        
        # Parâmetros
        self._fast_ema = config.parameters.get("fast_ema", 21)
        self._slow_ema = config.parameters.get("slow_ema", 50)
        self._trend_ema = config.parameters.get("trend_ema", 200)
        self._atr_period = config.parameters.get("atr_period", 14)
        self._atr_multiplier = config.parameters.get("atr_multiplier", 2.0)
    
    async def generate_signal(
        self,
        bars: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Signal]:
        """Gera sinal de tendência"""
        
        if not self.is_enabled:
            return None
        
        if len(bars) < self._trend_ema + 10:
            return None
        
        self._state = StrategyState.ANALYZING
        
        # Calcular indicadores
        closes = np.array([b["close"] for b in bars])
        highs = np.array([b["high"] for b in bars])
        lows = np.array([b["low"] for b in bars])
        
        fast_ema = self._calculate_ema(closes, self._fast_ema)
        slow_ema = self._calculate_ema(closes, self._slow_ema)
        trend_ema = self._calculate_ema(closes, self._trend_ema)
        atr = self._calculate_atr(highs, lows, closes, self._atr_period)
        
        current_bar = bars[-1]
        current_close = closes[-1]
        current_atr = atr[-1]
        
        # Determinar tendência
        trend = self._determine_trend(fast_ema, slow_ema, trend_ema)
        
        signal = None
        
        # Setup de compra em tendência de alta
        if trend == "bullish":
            # Procurar pullback para EMA rápida
            if self._is_pullback_to_ema(bars[-5:], fast_ema[-5:], "bullish"):
                entry = current_close
                sl = entry - (current_atr * self._atr_multiplier)
                tp = entry + (current_atr * self._atr_multiplier * 2)
                
                confidence = self._calculate_trend_confidence(
                    fast_ema[-1], slow_ema[-1], trend_ema[-1], current_close, "bullish"
                )
                
                signal = self._create_signal(
                    direction=SignalDirection.BUY,
                    entry_price=entry,
                    confidence=confidence,
                    stop_loss=sl,
                    take_profit=tp,
                    reason="Tendência de alta + pullback para EMA21"
                )
        
        # Setup de venda em tendência de baixa
        elif trend == "bearish":
            if self._is_pullback_to_ema(bars[-5:], fast_ema[-5:], "bearish"):
                entry = current_close
                sl = entry + (current_atr * self._atr_multiplier)
                tp = entry - (current_atr * self._atr_multiplier * 2)
                
                confidence = self._calculate_trend_confidence(
                    fast_ema[-1], slow_ema[-1], trend_ema[-1], current_close, "bearish"
                )
                
                signal = self._create_signal(
                    direction=SignalDirection.SELL,
                    entry_price=entry,
                    confidence=confidence,
                    stop_loss=sl,
                    take_profit=tp,
                    reason="Tendência de baixa + pullback para EMA21"
                )
        
        if signal is None:
            self._state = StrategyState.IDLE
        
        return signal
    
    async def validate_signal(
        self,
        signal: Signal,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Valida sinal de tendência"""
        
        # Verificar contexto macro
        if context:
            # Verificar alinhamento com sentimento
            sentiment = context.get("sentiment_score", 0)
            
            if signal.direction == SignalDirection.BUY and sentiment < -0.5:
                self._logger.debug("Sinal de compra contra sentimento muito negativo")
                return False
            
            if signal.direction == SignalDirection.SELL and sentiment > 0.5:
                self._logger.debug("Sinal de venda contra sentimento muito positivo")
                return False
        
        # Verificar confiança mínima
        min_confidence = self._config.parameters.get("min_confidence", 0.6)
        if signal.confidence < min_confidence:
            return False
        
        return True
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcula EMA"""
        ema = np.zeros(len(data))
        multiplier = 2 / (period + 1)
        
        ema[period-1] = np.mean(data[:period])
        
        for i in range(period, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        
        return ema
    
    def _calculate_atr(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int
    ) -> np.ndarray:
        """Calcula ATR"""
        tr = np.zeros(len(closes))
        
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr[i] = max(hl, hc, lc)
        
        atr = np.zeros(len(closes))
        atr[period] = np.mean(tr[1:period+1])
        
        for i in range(period + 1, len(closes)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        return atr
    
    def _determine_trend(
        self,
        fast_ema: np.ndarray,
        slow_ema: np.ndarray,
        trend_ema: np.ndarray
    ) -> str:
        """Determina tendência atual"""
        
        current_fast = fast_ema[-1]
        current_slow = slow_ema[-1]
        current_trend = trend_ema[-1]
        
        # Tendência de alta: fast > slow > trend
        if current_fast > current_slow > current_trend:
            return "bullish"
        
        # Tendência de baixa: fast < slow < trend
        if current_fast < current_slow < current_trend:
            return "bearish"
        
        return "ranging"
    
    def _is_pullback_to_ema(
        self,
        bars: List[Dict],
        ema: np.ndarray,
        trend: str
    ) -> bool:
        """Verifica se houve pullback para EMA"""
        
        if len(bars) < 3:
            return False
        
        last_bar = bars[-1]
        prev_bar = bars[-2]
        
        if trend == "bullish":
            # Preço tocou EMA e está subindo
            touched_ema = last_bar["low"] <= ema[-1] <= last_bar["high"]
            bullish_bar = last_bar["close"] > last_bar["open"]
            return touched_ema and bullish_bar
        
        else:  # bearish
            # Preço tocou EMA e está descendo
            touched_ema = last_bar["low"] <= ema[-1] <= last_bar["high"]
            bearish_bar = last_bar["close"] < last_bar["open"]
            return touched_ema and bearish_bar
    
    def _calculate_trend_confidence(
        self,
        fast: float,
        slow: float,
        trend: float,
        price: float,
        direction: str
    ) -> float:
        """Calcula confiança baseada na força da tendência"""
        confidence = 0.5
        
        # Distância entre EMAs
        fast_slow_dist = abs(fast - slow) / slow * 100
        slow_trend_dist = abs(slow - trend) / trend * 100
        
        # Maior separação = tendência mais forte
        if fast_slow_dist > 1:
            confidence += 0.1
        if slow_trend_dist > 2:
            confidence += 0.1
        
        # Preço acima/abaixo de todas as EMAs
        if direction == "bullish":
            if price > fast > slow > trend:
                confidence += 0.15
        else:
            if price < fast < slow < trend:
                confidence += 0.15
        
        return min(confidence, 0.9)


# Registrar no factory
StrategyFactory.register("trend_following", TrendFollowingStrategy)
