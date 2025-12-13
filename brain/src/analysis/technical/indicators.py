"""
BRAIN - Technical Indicators
Indicadores técnicos para análise
"""

from typing import List, Optional, Tuple
import numpy as np
from dataclasses import dataclass


@dataclass
class IndicatorResult:
    """Resultado de um indicador"""
    name: str
    values: np.ndarray
    signal: Optional[str] = None  # bullish, bearish, neutral
    strength: float = 0.0  # 0-1


class TechnicalIndicators:
    """
    Biblioteca de indicadores técnicos
    
    Todos os métodos são estáticos para facilitar uso
    """
    
    # ==========================================================================
    # MÉDIAS MÓVEIS
    # ==========================================================================
    
    @staticmethod
    def sma(data: np.ndarray, period: int) -> np.ndarray:
        """
        Simple Moving Average
        
        Args:
            data: Array de preços
            period: Período
            
        Returns:
            Array de SMA
        """
        result = np.full(len(data), np.nan)
        for i in range(period - 1, len(data)):
            result[i] = np.mean(data[i - period + 1:i + 1])
        return result
    
    @staticmethod
    def ema(data: np.ndarray, period: int) -> np.ndarray:
        """
        Exponential Moving Average
        
        Args:
            data: Array de preços
            period: Período
            
        Returns:
            Array de EMA
        """
        result = np.full(len(data), np.nan)
        multiplier = 2 / (period + 1)
        
        # Primeira EMA = SMA
        result[period - 1] = np.mean(data[:period])
        
        for i in range(period, len(data)):
            result[i] = (data[i] * multiplier) + (result[i - 1] * (1 - multiplier))
        
        return result
    
    @staticmethod
    def wma(data: np.ndarray, period: int) -> np.ndarray:
        """Weighted Moving Average"""
        result = np.full(len(data), np.nan)
        weights = np.arange(1, period + 1)
        
        for i in range(period - 1, len(data)):
            window = data[i - period + 1:i + 1]
            result[i] = np.sum(window * weights) / np.sum(weights)
        
        return result
    
    # ==========================================================================
    # MOMENTUM
    # ==========================================================================
    
    @staticmethod
    def rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Relative Strength Index
        
        Args:
            data: Array de preços de fechamento
            period: Período (default 14)
            
        Returns:
            Array de RSI (0-100)
        """
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        result = np.full(len(data), np.nan)
        
        avg_gain = np.zeros(len(data))
        avg_loss = np.zeros(len(data))
        
        # Primeiro cálculo
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])
        
        for i in range(period + 1, len(data)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
        
        rs = np.divide(
            avg_gain, avg_loss, 
            out=np.zeros_like(avg_gain), 
            where=avg_loss != 0
        )
        result[period:] = 100 - (100 / (1 + rs[period:]))
        
        return result
    
    @staticmethod
    def macd(
        data: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        MACD (Moving Average Convergence Divergence)
        
        Args:
            data: Array de preços
            fast: Período EMA rápida
            slow: Período EMA lenta
            signal: Período linha de sinal
            
        Returns:
            Tuple (macd_line, signal_line, histogram)
        """
        fast_ema = TechnicalIndicators.ema(data, fast)
        slow_ema = TechnicalIndicators.ema(data, slow)
        
        macd_line = fast_ema - slow_ema
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def stochastic(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Stochastic Oscillator
        
        Returns:
            Tuple (%K, %D)
        """
        k = np.full(len(closes), np.nan)
        
        for i in range(k_period - 1, len(closes)):
            high_max = np.max(highs[i - k_period + 1:i + 1])
            low_min = np.min(lows[i - k_period + 1:i + 1])
            
            if high_max != low_min:
                k[i] = ((closes[i] - low_min) / (high_max - low_min)) * 100
        
        d = TechnicalIndicators.sma(k, d_period)
        
        return k, d
    
    @staticmethod
    def cci(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int = 20
    ) -> np.ndarray:
        """Commodity Channel Index"""
        typical_price = (highs + lows + closes) / 3
        sma_tp = TechnicalIndicators.sma(typical_price, period)
        
        result = np.full(len(closes), np.nan)
        
        for i in range(period - 1, len(closes)):
            mean_deviation = np.mean(
                np.abs(typical_price[i - period + 1:i + 1] - sma_tp[i])
            )
            if mean_deviation != 0:
                result[i] = (typical_price[i] - sma_tp[i]) / (0.015 * mean_deviation)
        
        return result
    
    # ==========================================================================
    # VOLATILIDADE
    # ==========================================================================
    
    @staticmethod
    def atr(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """
        Average True Range
        
        Args:
            highs: Preços máximos
            lows: Preços mínimos
            closes: Preços de fechamento
            period: Período
            
        Returns:
            Array de ATR
        """
        tr = np.zeros(len(closes))
        
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            tr[i] = max(hl, hc, lc)
        
        result = np.full(len(closes), np.nan)
        result[period] = np.mean(tr[1:period + 1])
        
        for i in range(period + 1, len(closes)):
            result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
        
        return result
    
    @staticmethod
    def bollinger_bands(
        data: np.ndarray,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Bollinger Bands
        
        Returns:
            Tuple (upper, middle, lower)
        """
        middle = TechnicalIndicators.sma(data, period)
        
        std = np.full(len(data), np.nan)
        for i in range(period - 1, len(data)):
            std[i] = np.std(data[i - period + 1:i + 1])
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    @staticmethod
    def keltner_channels(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        ema_period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Keltner Channels"""
        middle = TechnicalIndicators.ema(closes, ema_period)
        atr = TechnicalIndicators.atr(highs, lows, closes, atr_period)
        
        upper = middle + (atr * multiplier)
        lower = middle - (atr * multiplier)
        
        return upper, middle, lower
    
    # ==========================================================================
    # VOLUME
    # ==========================================================================
    
    @staticmethod
    def obv(closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """On Balance Volume"""
        result = np.zeros(len(closes))
        result[0] = volumes[0]
        
        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                result[i] = result[i - 1] + volumes[i]
            elif closes[i] < closes[i - 1]:
                result[i] = result[i - 1] - volumes[i]
            else:
                result[i] = result[i - 1]
        
        return result
    
    @staticmethod
    def vwap(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray
    ) -> np.ndarray:
        """Volume Weighted Average Price"""
        typical_price = (highs + lows + closes) / 3
        cumulative_tpv = np.cumsum(typical_price * volumes)
        cumulative_vol = np.cumsum(volumes)
        
        return np.divide(
            cumulative_tpv, cumulative_vol,
            out=np.zeros_like(cumulative_tpv),
            where=cumulative_vol != 0
        )
    
    # ==========================================================================
    # TREND
    # ==========================================================================
    
    @staticmethod
    def adx(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int = 14
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Average Directional Index
        
        Returns:
            Tuple (ADX, +DI, -DI)
        """
        # Calcular +DM e -DM
        plus_dm = np.zeros(len(closes))
        minus_dm = np.zeros(len(closes))
        
        for i in range(1, len(closes)):
            up_move = highs[i] - highs[i - 1]
            down_move = lows[i - 1] - lows[i]
            
            if up_move > down_move and up_move > 0:
                plus_dm[i] = up_move
            if down_move > up_move and down_move > 0:
                minus_dm[i] = down_move
        
        # ATR
        atr = TechnicalIndicators.atr(highs, lows, closes, period)
        
        # Smoothed +DM e -DM
        smoothed_plus = TechnicalIndicators.ema(plus_dm, period)
        smoothed_minus = TechnicalIndicators.ema(minus_dm, period)
        
        # +DI e -DI
        plus_di = np.divide(
            smoothed_plus * 100, atr,
            out=np.zeros_like(smoothed_plus),
            where=atr != 0
        )
        minus_di = np.divide(
            smoothed_minus * 100, atr,
            out=np.zeros_like(smoothed_minus),
            where=atr != 0
        )
        
        # DX e ADX
        di_diff = np.abs(plus_di - minus_di)
        di_sum = plus_di + minus_di
        
        dx = np.divide(
            di_diff * 100, di_sum,
            out=np.zeros_like(di_diff),
            where=di_sum != 0
        )
        
        adx = TechnicalIndicators.ema(dx, period)
        
        return adx, plus_di, minus_di
    
    @staticmethod
    def supertrend(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int = 10,
        multiplier: float = 3.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        SuperTrend Indicator
        
        Returns:
            Tuple (supertrend, direction) onde direction: 1=up, -1=down
        """
        atr = TechnicalIndicators.atr(highs, lows, closes, period)
        hl2 = (highs + lows) / 2
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        supertrend = np.zeros(len(closes))
        direction = np.zeros(len(closes))
        
        supertrend[0] = upper_band[0]
        direction[0] = 1
        
        for i in range(1, len(closes)):
            if closes[i] > supertrend[i - 1]:
                supertrend[i] = lower_band[i]
                direction[i] = 1
            else:
                supertrend[i] = upper_band[i]
                direction[i] = -1
        
        return supertrend, direction
    
    # ==========================================================================
    # PIVOT POINTS
    # ==========================================================================
    
    @staticmethod
    def pivot_points(
        high: float,
        low: float,
        close: float
    ) -> dict:
        """
        Calcula Pivot Points clássicos
        
        Args:
            high: Máxima do período anterior
            low: Mínima do período anterior
            close: Fechamento do período anterior
            
        Returns:
            Dict com PP, R1, R2, R3, S1, S2, S3
        """
        pp = (high + low + close) / 3
        
        r1 = (2 * pp) - low
        s1 = (2 * pp) - high
        
        r2 = pp + (high - low)
        s2 = pp - (high - low)
        
        r3 = high + 2 * (pp - low)
        s3 = low - 2 * (high - pp)
        
        return {
            "PP": pp,
            "R1": r1, "R2": r2, "R3": r3,
            "S1": s1, "S2": s2, "S3": s3
        }
