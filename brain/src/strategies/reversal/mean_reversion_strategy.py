"""
BRAIN - Mean Reversion Strategy
Estratégia de reversão à média
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np

from ..base_strategy import BaseStrategy, StrategyConfig, StrategyState


class MeanReversionStrategy(BaseStrategy):
    """
    Estratégia de Reversão à Média
    
    Lógica:
    - Identifica desvios extremos da média (Bollinger Bands)
    - Entra em reversão quando preço atinge bandas externas
    - Usa RSI como confirmação de sobrecompra/sobrevenda
    - Exit na média móvel ou banda oposta
    
    Configurações recomendadas:
    - Timeframe: M15, M30, H1
    - Símbolos: Pares estáveis (EURUSD, GBPUSD)
    - Mercado: Range/Lateralizado
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Parâmetros específicos
        self._bb_period = config.parameters.get("bb_period", 20)
        self._bb_std = config.parameters.get("bb_std", 2.0)
        self._rsi_period = config.parameters.get("rsi_period", 14)
        self._rsi_oversold = config.parameters.get("rsi_oversold", 30)
        self._rsi_overbought = config.parameters.get("rsi_overbought", 70)
        self._atr_period = config.parameters.get("atr_period", 14)
        
        # Filtro de tendência
        self._use_trend_filter = config.parameters.get("use_trend_filter", True)
        self._trend_ema_period = config.parameters.get("trend_ema_period", 50)
        self._max_trend_slope = config.parameters.get("max_trend_slope", 0.0002)
    
    @property
    def name(self) -> str:
        return "mean_reversion"
    
    @property
    def description(self) -> str:
        return "Reversão à média com Bollinger Bands e RSI"
    
    # ==========================================================================
    # CÁLCULOS
    # ==========================================================================
    
    def _calculate_bollinger_bands(
        self,
        closes: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calcula Bollinger Bands"""
        # SMA
        sma = np.full(len(closes), np.nan)
        for i in range(self._bb_period - 1, len(closes)):
            sma[i] = np.mean(closes[i - self._bb_period + 1:i + 1])
        
        # Desvio padrão
        std = np.full(len(closes), np.nan)
        for i in range(self._bb_period - 1, len(closes)):
            std[i] = np.std(closes[i - self._bb_period + 1:i + 1])
        
        upper = sma + (std * self._bb_std)
        lower = sma - (std * self._bb_std)
        
        return upper, sma, lower
    
    def _calculate_rsi(self, closes: np.ndarray) -> np.ndarray:
        """Calcula RSI"""
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        result = np.full(len(closes), np.nan)
        
        avg_gain = np.zeros(len(closes))
        avg_loss = np.zeros(len(closes))
        
        period = self._rsi_period
        
        if len(gains) >= period:
            avg_gain[period] = np.mean(gains[:period])
            avg_loss[period] = np.mean(losses[:period])
            
            for i in range(period + 1, len(closes)):
                avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
                avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
            
            rs = np.divide(
                avg_gain, avg_loss,
                out=np.zeros_like(avg_gain),
                where=avg_loss != 0
            )
            result[period:] = 100 - (100 / (1 + rs[period:]))
        
        return result
    
    def _calculate_atr(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> np.ndarray:
        """Calcula ATR"""
        tr = np.zeros(len(closes))
        
        for i in range(1, len(closes)):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
        
        atr = np.full(len(closes), np.nan)
        period = self._atr_period
        
        if len(tr) > period:
            atr[period] = np.mean(tr[1:period + 1])
            for i in range(period + 1, len(closes)):
                atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        return atr
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcula EMA"""
        result = np.full(len(data), np.nan)
        multiplier = 2 / (period + 1)
        
        if len(data) >= period:
            result[period - 1] = np.mean(data[:period])
            for i in range(period, len(data)):
                result[i] = (data[i] * multiplier) + (result[i-1] * (1 - multiplier))
        
        return result
    
    def _is_ranging_market(
        self,
        closes: np.ndarray,
        ema: np.ndarray
    ) -> bool:
        """Verifica se mercado está lateralizado"""
        if not self._use_trend_filter:
            return True
        
        # Calcular slope da EMA
        if len(ema) < 10:
            return True
        
        recent_ema = ema[-10:]
        valid_ema = recent_ema[~np.isnan(recent_ema)]
        
        if len(valid_ema) < 5:
            return True
        
        # Slope = mudança percentual
        slope = (valid_ema[-1] - valid_ema[0]) / valid_ema[0]
        
        return abs(slope) < self._max_trend_slope
    
    def _get_bb_position(
        self,
        close: float,
        upper: float,
        middle: float,
        lower: float
    ) -> float:
        """Retorna posição do preço nas bandas (-1 a 1)"""
        if np.isnan(upper) or np.isnan(lower):
            return 0
        
        band_width = upper - lower
        if band_width == 0:
            return 0
        
        # Normaliza: -1 = banda inferior, 0 = média, 1 = banda superior
        position = 2 * (close - lower) / band_width - 1
        return np.clip(position, -1.5, 1.5)
    
    # ==========================================================================
    # SINAIS
    # ==========================================================================
    
    async def generate_signal(
        self,
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Gera sinal de mean reversion
        
        Condições BUY:
        - Preço toca/penetra banda inferior
        - RSI em sobrevenda (< 30)
        - Mercado lateralizado
        - Candle de reversão (opcional)
        
        Condições SELL:
        - Preço toca/penetra banda superior
        - RSI em sobrecompra (> 70)
        - Mercado lateralizado
        - Candle de reversão (opcional)
        """
        if self._state != StrategyState.ACTIVE:
            return None
        
        rates = market_data.get("rates", [])
        if len(rates) < self._bb_period + 10:
            return None
        
        # Extrair OHLC
        opens = np.array([r["open"] for r in rates])
        highs = np.array([r["high"] for r in rates])
        lows = np.array([r["low"] for r in rates])
        closes = np.array([r["close"] for r in rates])
        
        # Calcular indicadores
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes)
        rsi = self._calculate_rsi(closes)
        atr = self._calculate_atr(highs, lows, closes)
        trend_ema = self._calculate_ema(closes, self._trend_ema_period)
        
        # Valores atuais
        current_close = closes[-1]
        current_rsi = rsi[-1]
        current_atr = atr[-1]
        current_upper = bb_upper[-1]
        current_middle = bb_middle[-1]
        current_lower = bb_lower[-1]
        
        # Validações
        if np.isnan(current_rsi) or np.isnan(current_atr):
            return None
        
        # Verificar se mercado está lateralizado
        if not self._is_ranging_market(closes, trend_ema):
            return None
        
        # Posição nas bandas
        bb_position = self._get_bb_position(
            current_close, current_upper, current_middle, current_lower
        )
        
        signal = None
        
        # ===== SINAL DE COMPRA =====
        if (bb_position <= -0.9 and  # Na banda inferior
            current_rsi < self._rsi_oversold and
            self._is_reversal_candle(rates[-3:], "bullish")):
            
            entry = current_close
            sl = current_lower - current_atr
            tp = current_middle  # Target = média
            
            confidence = self._calculate_confidence(
                bb_position=abs(bb_position),
                rsi_extreme=(self._rsi_oversold - current_rsi) / self._rsi_oversold
            )
            
            signal = {
                "symbol": self._config.symbol,
                "direction": "buy",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "confidence": confidence,
                "strategy": self.name,
                "reason": f"Mean Reversion BUY - BB:{bb_position:.2f} RSI:{current_rsi:.0f}",
                "metadata": {
                    "bb_position": bb_position,
                    "rsi": current_rsi,
                    "atr": current_atr,
                    "bb_upper": current_upper,
                    "bb_lower": current_lower
                }
            }
        
        # ===== SINAL DE VENDA =====
        elif (bb_position >= 0.9 and  # Na banda superior
              current_rsi > self._rsi_overbought and
              self._is_reversal_candle(rates[-3:], "bearish")):
            
            entry = current_close
            sl = current_upper + current_atr
            tp = current_middle
            
            confidence = self._calculate_confidence(
                bb_position=abs(bb_position),
                rsi_extreme=(current_rsi - self._rsi_overbought) / (100 - self._rsi_overbought)
            )
            
            signal = {
                "symbol": self._config.symbol,
                "direction": "sell",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "confidence": confidence,
                "strategy": self.name,
                "reason": f"Mean Reversion SELL - BB:{bb_position:.2f} RSI:{current_rsi:.0f}",
                "metadata": {
                    "bb_position": bb_position,
                    "rsi": current_rsi,
                    "atr": current_atr,
                    "bb_upper": current_upper,
                    "bb_lower": current_lower
                }
            }
        
        if signal and self.validate_signal(signal):
            self._stats.signals_generated += 1
            return signal
        
        return None
    
    def _is_reversal_candle(
        self,
        rates: List[Dict],
        direction: str
    ) -> bool:
        """Verifica padrão de reversão"""
        if len(rates) < 2:
            return True  # Não filtrar se não há dados
        
        last = rates[-1]
        prev = rates[-2]
        
        body_last = last["close"] - last["open"]
        body_prev = prev["close"] - prev["open"]
        
        if direction == "bullish":
            # Último candle bullish após bearish
            return body_last > 0 and body_prev < 0
        else:
            # Último candle bearish após bullish
            return body_last < 0 and body_prev > 0
    
    def _calculate_confidence(
        self,
        bb_position: float,
        rsi_extreme: float
    ) -> float:
        """Calcula confiança do sinal"""
        # Mais extremo = mais confiança
        bb_score = min(bb_position, 1.0) * 0.5
        rsi_score = min(rsi_extreme, 1.0) * 0.5
        
        confidence = bb_score + rsi_score
        return round(min(confidence, 0.9), 2)
    
    # ==========================================================================
    # VALIDAÇÃO E SL/TP
    # ==========================================================================
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Valida sinal"""
        if not signal:
            return False
        
        entry = signal.get("entry_price", 0)
        sl = signal.get("stop_loss", 0)
        tp = signal.get("take_profit", 0)
        
        if not all([entry, sl, tp]):
            return False
        
        # R:R mínimo de 1:1
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        
        if risk == 0 or reward / risk < 1.0:
            return False
        
        # Confiança mínima
        if signal.get("confidence", 0) < self._config.min_confidence:
            return False
        
        return True
    
    def calculate_sl_tp(
        self,
        entry_price: float,
        direction: str,
        market_data: Dict[str, Any]
    ) -> tuple[float, float]:
        """Calcula SL/TP usando bandas de Bollinger"""
        rates = market_data.get("rates", [])
        
        if len(rates) < self._bb_period:
            # Fallback para ATR
            atr = market_data.get("atr", entry_price * 0.001)
            if direction == "buy":
                return entry_price - atr * 2, entry_price + atr * 2
            else:
                return entry_price + atr * 2, entry_price - atr * 2
        
        closes = np.array([r["close"] for r in rates])
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes)
        
        if direction == "buy":
            sl = bb_lower[-1]
            tp = bb_middle[-1]
        else:
            sl = bb_upper[-1]
            tp = bb_middle[-1]
        
        return sl, tp


# Registrar na factory
from ..base_strategy import StrategyFactory
StrategyFactory.register("mean_reversion", MeanReversionStrategy)
