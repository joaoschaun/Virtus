"""
BRAIN - Scalping Strategy
Estratégia de scalping adaptativa
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np

from .base_strategy import (
    BaseStrategy, StrategyConfig, StrategyState,
    StrategyFactory
)
from ..core.types import Signal, SignalDirection, MarketRegime
from ..core.logger import get_logger

logger = get_logger("strategy.scalping")


class ScalpingStrategy(BaseStrategy):
    """
    Estratégia de Scalping
    
    Características:
    - Timeframes curtos (M1, M5)
    - Alvos pequenos (5-20 pips)
    - Alta frequência
    - Requer baixo spread
    
    Condições de entrada:
    - RSI extremo + reversão
    - Candle de rejeição em suporte/resistência
    - Volume acima da média
    """
    
    def __init__(self, config: StrategyConfig, symbol: str):
        super().__init__(config, symbol)
        
        # Parâmetros específicos
        self._rsi_period = config.parameters.get("rsi_period", 14)
        self._rsi_oversold = config.parameters.get("rsi_oversold", 30)
        self._rsi_overbought = config.parameters.get("rsi_overbought", 70)
        self._atr_period = config.parameters.get("atr_period", 14)
        self._volume_mult = config.parameters.get("volume_multiplier", 1.5)
        self._max_spread = config.parameters.get("max_spread_pips", 3)
    
    async def generate_signal(
        self,
        bars: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Signal]:
        """Gera sinal de scalping"""
        
        if not self.is_enabled:
            return None
        
        if len(bars) < 50:
            return None
        
        self._state = StrategyState.ANALYZING
        
        # Verificar sessão
        if not self._check_session():
            self._state = StrategyState.IDLE
            return None
        
        # Calcular indicadores
        closes = np.array([b["close"] for b in bars])
        highs = np.array([b["high"] for b in bars])
        lows = np.array([b["low"] for b in bars])
        volumes = np.array([b.get("tick_volume", 0) for b in bars])
        
        rsi = self._calculate_rsi(closes, self._rsi_period)
        atr = self._calculate_atr(highs, lows, closes, self._atr_period)
        avg_volume = np.mean(volumes[-20:])
        
        current_bar = bars[-1]
        current_rsi = rsi[-1]
        current_volume = volumes[-1]
        current_atr = atr[-1]
        
        # Verificar condições
        signal = None
        
        # Setup de compra: RSI oversold + candle de rejeição + volume
        if (current_rsi < self._rsi_oversold and
            self._is_bullish_rejection(bars[-3:]) and
            current_volume > avg_volume * self._volume_mult):
            
            entry = current_bar["close"]
            sl = entry - (current_atr * 1.5)
            tp = entry + (current_atr * 2)
            
            confidence = self._calculate_confidence(
                current_rsi, current_volume, avg_volume, "buy"
            )
            
            signal = self._create_signal(
                direction=SignalDirection.BUY,
                entry_price=entry,
                confidence=confidence,
                stop_loss=sl,
                take_profit=tp,
                reason=f"RSI oversold ({current_rsi:.1f}) + rejeição bullish + volume alto"
            )
        
        # Setup de venda: RSI overbought + candle de rejeição + volume
        elif (current_rsi > self._rsi_overbought and
              self._is_bearish_rejection(bars[-3:]) and
              current_volume > avg_volume * self._volume_mult):
            
            entry = current_bar["close"]
            sl = entry + (current_atr * 1.5)
            tp = entry - (current_atr * 2)
            
            confidence = self._calculate_confidence(
                current_rsi, current_volume, avg_volume, "sell"
            )
            
            signal = self._create_signal(
                direction=SignalDirection.SELL,
                entry_price=entry,
                confidence=confidence,
                stop_loss=sl,
                take_profit=tp,
                reason=f"RSI overbought ({current_rsi:.1f}) + rejeição bearish + volume alto"
            )
        
        if signal is None:
            self._state = StrategyState.IDLE
        
        return signal
    
    async def validate_signal(
        self,
        signal: Signal,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Valida sinal de scalping"""
        
        # Verificar se há eventos de alto impacto próximos
        if context:
            calendar = context.get("calendar", {})
            if not calendar.get("safe_to_trade", True):
                self._logger.debug("Sinal rejeitado: eventos de alto impacto")
                return False
        
        # Verificar confiança mínima
        min_confidence = self._config.parameters.get("min_confidence", 0.65)
        if signal.confidence < min_confidence:
            self._logger.debug(f"Sinal rejeitado: confiança {signal.confidence} < {min_confidence}")
            return False
        
        return True
    
    def _calculate_rsi(self, closes: np.ndarray, period: int) -> np.ndarray:
        """Calcula RSI"""
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.zeros(len(closes))
        avg_loss = np.zeros(len(closes))
        
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])
        
        for i in range(period + 1, len(closes)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
        
        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss!=0)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
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
    
    def _is_bullish_rejection(self, bars: List[Dict]) -> bool:
        """Verifica candle de rejeição bullish"""
        if len(bars) < 3:
            return False
        
        last = bars[-1]
        body = abs(last["close"] - last["open"])
        lower_wick = min(last["open"], last["close"]) - last["low"]
        upper_wick = last["high"] - max(last["open"], last["close"])
        
        # Pavio inferior maior que corpo e pavio superior
        return (lower_wick > body * 2 and 
                lower_wick > upper_wick * 2 and
                last["close"] > last["open"])
    
    def _is_bearish_rejection(self, bars: List[Dict]) -> bool:
        """Verifica candle de rejeição bearish"""
        if len(bars) < 3:
            return False
        
        last = bars[-1]
        body = abs(last["close"] - last["open"])
        lower_wick = min(last["open"], last["close"]) - last["low"]
        upper_wick = last["high"] - max(last["open"], last["close"])
        
        # Pavio superior maior que corpo e pavio inferior
        return (upper_wick > body * 2 and 
                upper_wick > lower_wick * 2 and
                last["close"] < last["open"])
    
    def _calculate_confidence(
        self,
        rsi: float,
        volume: float,
        avg_volume: float,
        direction: str
    ) -> float:
        """Calcula confiança do sinal"""
        confidence = 0.5
        
        # RSI extremo aumenta confiança
        if direction == "buy":
            if rsi < 20:
                confidence += 0.2
            elif rsi < 25:
                confidence += 0.15
            else:
                confidence += 0.1
        else:
            if rsi > 80:
                confidence += 0.2
            elif rsi > 75:
                confidence += 0.15
            else:
                confidence += 0.1
        
        # Volume acima da média
        vol_ratio = volume / avg_volume
        if vol_ratio > 2:
            confidence += 0.15
        elif vol_ratio > 1.5:
            confidence += 0.1
        
        return min(confidence, 0.95)


# Registrar no factory
StrategyFactory.register("scalping", ScalpingStrategy)
