"""
VIRTUS Divergence Detector
===========================

Detecção avançada de divergências:
- Regular Bullish/Bearish
- Hidden Bullish/Bearish
- Multi-indicador (RSI, MACD, Stochastic, OBV, CCI)
- Confluência de divergências
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class DivergenceType(Enum):
    """Tipo de divergência."""
    REGULAR_BULLISH = auto()   # Preço faz lower low, indicador faz higher low
    REGULAR_BEARISH = auto()   # Preço faz higher high, indicador faz lower high
    HIDDEN_BULLISH = auto()    # Preço faz higher low, indicador faz lower low (continuação)
    HIDDEN_BEARISH = auto()    # Preço faz lower high, indicador faz higher high (continuação)


class DivergenceStrength(Enum):
    """Força da divergência."""
    STRONG = auto()    # Múltiplos indicadores confirmam
    MODERATE = auto()  # 2 indicadores confirmam
    WEAK = auto()      # Apenas 1 indicador


@dataclass
class Divergence:
    """Uma divergência identificada."""
    type: DivergenceType
    indicator: str
    strength: DivergenceStrength
    price_point_1: Tuple[int, float]  # (índice, preço)
    price_point_2: Tuple[int, float]
    indicator_point_1: Tuple[int, float]  # (índice, valor)
    indicator_point_2: Tuple[int, float]
    bars_apart: int
    confirmation: bool  # Se já confirmou


@dataclass
class DivergenceAnalysisResult:
    """Resultado da análise de divergências."""
    divergences: List[Divergence]
    bullish_count: int
    bearish_count: int
    strongest: Optional[Divergence]
    confluence_score: float  # 0 a 1
    actionable: bool  # Se há divergência acionável
    bias: str  # 'bullish', 'bearish', 'neutral'


class DivergenceDetector:
    """
    Detector avançado de divergências.
    
    Analisa múltiplos indicadores para encontrar divergências
    e determinar confluência entre elas.
    """
    
    def __init__(
        self,
        lookback_bars: int = 50,
        min_bars_apart: int = 5,
        max_bars_apart: int = 30,
        swing_strength: int = 3,  # Candles para confirmar swing
    ):
        self.lookback_bars = lookback_bars
        self.min_bars_apart = min_bars_apart
        self.max_bars_apart = max_bars_apart
        self.swing_strength = swing_strength
    
    def analyze(self, df: pd.DataFrame) -> DivergenceAnalysisResult:
        """
        Analisa divergências em múltiplos indicadores.
        
        Args:
            df: DataFrame com OHLCV
            
        Returns:
            DivergenceAnalysisResult
        """
        if df is None or len(df) < self.lookback_bars:
            return self._empty_result()
        
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values if 'volume' in df.columns else df.get('tick_volume', np.zeros(len(df))).values
        
        all_divergences = []
        
        # Calcula indicadores
        rsi = self._calculate_rsi(close, 14)
        macd, macd_signal, macd_hist = self._calculate_macd(close)
        stoch_k, stoch_d = self._calculate_stochastic(high, low, close)
        obv = self._calculate_obv(close, volume)
        cci = self._calculate_cci(high, low, close)
        
        # Detecta divergências em cada indicador
        indicators = {
            'RSI': rsi,
            'MACD': macd_hist,
            'Stochastic': stoch_k,
            'OBV': obv,
            'CCI': cci,
        }
        
        for name, indicator_values in indicators.items():
            divs = self._find_divergences(close, high, low, indicator_values, name)
            all_divergences.extend(divs)
        
        # Conta divergências por tipo
        bullish_count = sum(1 for d in all_divergences 
                          if d.type in [DivergenceType.REGULAR_BULLISH, DivergenceType.HIDDEN_BULLISH])
        bearish_count = sum(1 for d in all_divergences 
                          if d.type in [DivergenceType.REGULAR_BEARISH, DivergenceType.HIDDEN_BEARISH])
        
        # Encontra a mais forte
        strongest = None
        if all_divergences:
            # Prioriza regular sobre hidden, e múltiplos indicadores
            regular_divs = [d for d in all_divergences 
                          if d.type in [DivergenceType.REGULAR_BULLISH, DivergenceType.REGULAR_BEARISH]]
            if regular_divs:
                strongest = max(regular_divs, key=lambda x: x.bars_apart)
            else:
                strongest = max(all_divergences, key=lambda x: x.bars_apart)
        
        # Calcula confluência
        confluence_score = self._calculate_confluence(all_divergences)
        
        # Determina se é acionável
        actionable = (
            len(all_divergences) >= 2 and
            confluence_score >= 0.4
        )
        
        # Determina viés
        if bullish_count > bearish_count and bullish_count >= 2:
            bias = 'bullish'
        elif bearish_count > bullish_count and bearish_count >= 2:
            bias = 'bearish'
        else:
            bias = 'neutral'
        
        # Atualiza força das divergências baseado em confluência
        self._update_strength(all_divergences)
        
        return DivergenceAnalysisResult(
            divergences=all_divergences,
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            strongest=strongest,
            confluence_score=confluence_score,
            actionable=actionable,
            bias=bias,
        )
    
    def _find_divergences(
        self,
        close: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        indicator: np.ndarray,
        indicator_name: str,
    ) -> List[Divergence]:
        """Encontra divergências entre preço e indicador."""
        divergences = []
        
        # Encontra swings no preço
        price_swing_highs = self._find_swing_highs(high, self.swing_strength)
        price_swing_lows = self._find_swing_lows(low, self.swing_strength)
        
        # Encontra swings no indicador
        ind_swing_highs = self._find_swing_highs(indicator, self.swing_strength)
        ind_swing_lows = self._find_swing_lows(indicator, self.swing_strength)
        
        # Procura divergências bearish (highs)
        for i in range(len(price_swing_highs) - 1):
            idx1, price1 = price_swing_highs[i]
            for j in range(i + 1, len(price_swing_highs)):
                idx2, price2 = price_swing_highs[j]
                
                bars_apart = idx2 - idx1
                if bars_apart < self.min_bars_apart or bars_apart > self.max_bars_apart:
                    continue
                
                # Encontra swings do indicador correspondentes
                ind1 = self._find_nearest_swing(ind_swing_highs, idx1)
                ind2 = self._find_nearest_swing(ind_swing_highs, idx2)
                
                if ind1 is None or ind2 is None:
                    continue
                
                # Regular Bearish: Preço HH, Indicador LH
                if price2 > price1 and ind2[1] < ind1[1]:
                    divergences.append(Divergence(
                        type=DivergenceType.REGULAR_BEARISH,
                        indicator=indicator_name,
                        strength=DivergenceStrength.WEAK,
                        price_point_1=(idx1, price1),
                        price_point_2=(idx2, price2),
                        indicator_point_1=ind1,
                        indicator_point_2=ind2,
                        bars_apart=bars_apart,
                        confirmation=True,
                    ))
                
                # Hidden Bearish: Preço LH, Indicador HH
                elif price2 < price1 and ind2[1] > ind1[1]:
                    divergences.append(Divergence(
                        type=DivergenceType.HIDDEN_BEARISH,
                        indicator=indicator_name,
                        strength=DivergenceStrength.WEAK,
                        price_point_1=(idx1, price1),
                        price_point_2=(idx2, price2),
                        indicator_point_1=ind1,
                        indicator_point_2=ind2,
                        bars_apart=bars_apart,
                        confirmation=True,
                    ))
        
        # Procura divergências bullish (lows)
        for i in range(len(price_swing_lows) - 1):
            idx1, price1 = price_swing_lows[i]
            for j in range(i + 1, len(price_swing_lows)):
                idx2, price2 = price_swing_lows[j]
                
                bars_apart = idx2 - idx1
                if bars_apart < self.min_bars_apart or bars_apart > self.max_bars_apart:
                    continue
                
                # Encontra swings do indicador correspondentes
                ind1 = self._find_nearest_swing(ind_swing_lows, idx1)
                ind2 = self._find_nearest_swing(ind_swing_lows, idx2)
                
                if ind1 is None or ind2 is None:
                    continue
                
                # Regular Bullish: Preço LL, Indicador HL
                if price2 < price1 and ind2[1] > ind1[1]:
                    divergences.append(Divergence(
                        type=DivergenceType.REGULAR_BULLISH,
                        indicator=indicator_name,
                        strength=DivergenceStrength.WEAK,
                        price_point_1=(idx1, price1),
                        price_point_2=(idx2, price2),
                        indicator_point_1=ind1,
                        indicator_point_2=ind2,
                        bars_apart=bars_apart,
                        confirmation=True,
                    ))
                
                # Hidden Bullish: Preço HL, Indicador LL
                elif price2 > price1 and ind2[1] < ind1[1]:
                    divergences.append(Divergence(
                        type=DivergenceType.HIDDEN_BULLISH,
                        indicator=indicator_name,
                        strength=DivergenceStrength.WEAK,
                        price_point_1=(idx1, price1),
                        price_point_2=(idx2, price2),
                        indicator_point_1=ind1,
                        indicator_point_2=ind2,
                        bars_apart=bars_apart,
                        confirmation=True,
                    ))
        
        return divergences
    
    def _find_swing_highs(
        self,
        data: np.ndarray,
        strength: int,
    ) -> List[Tuple[int, float]]:
        """Encontra swing highs."""
        swings = []
        
        for i in range(strength, len(data) - strength):
            is_swing = True
            for j in range(1, strength + 1):
                if data[i] <= data[i - j] or data[i] <= data[i + j]:
                    is_swing = False
                    break
            
            if is_swing:
                swings.append((i, data[i]))
        
        return swings
    
    def _find_swing_lows(
        self,
        data: np.ndarray,
        strength: int,
    ) -> List[Tuple[int, float]]:
        """Encontra swing lows."""
        swings = []
        
        for i in range(strength, len(data) - strength):
            is_swing = True
            for j in range(1, strength + 1):
                if data[i] >= data[i - j] or data[i] >= data[i + j]:
                    is_swing = False
                    break
            
            if is_swing:
                swings.append((i, data[i]))
        
        return swings
    
    def _find_nearest_swing(
        self,
        swings: List[Tuple[int, float]],
        target_idx: int,
        tolerance: int = 3,
    ) -> Optional[Tuple[int, float]]:
        """Encontra o swing mais próximo de um índice."""
        nearest = None
        min_dist = float('inf')
        
        for idx, value in swings:
            dist = abs(idx - target_idx)
            if dist <= tolerance and dist < min_dist:
                min_dist = dist
                nearest = (idx, value)
        
        return nearest
    
    def _calculate_confluence(self, divergences: List[Divergence]) -> float:
        """Calcula score de confluência."""
        if not divergences:
            return 0.0
        
        # Agrupa por tipo
        types_present = set(d.type for d in divergences)
        indicators_with_div = set(d.indicator for d in divergences)
        
        # Score baseado em:
        # 1. Número de indicadores com divergência
        # 2. Consistência do tipo (todos bullish ou todos bearish)
        
        indicator_score = len(indicators_with_div) / 5  # 5 indicadores
        
        # Consistência
        bullish_types = {DivergenceType.REGULAR_BULLISH, DivergenceType.HIDDEN_BULLISH}
        bearish_types = {DivergenceType.REGULAR_BEARISH, DivergenceType.HIDDEN_BEARISH}
        
        all_bullish = all(d.type in bullish_types for d in divergences)
        all_bearish = all(d.type in bearish_types for d in divergences)
        
        consistency_score = 1.0 if (all_bullish or all_bearish) else 0.5
        
        return (indicator_score * 0.6 + consistency_score * 0.4)
    
    def _update_strength(self, divergences: List[Divergence]) -> None:
        """Atualiza força das divergências baseado em confluência."""
        # Agrupa por tipo
        by_type = {}
        for d in divergences:
            if d.type not in by_type:
                by_type[d.type] = []
            by_type[d.type].append(d)
        
        # Atualiza força
        for div_type, divs in by_type.items():
            indicators = set(d.indicator for d in divs)
            
            if len(indicators) >= 3:
                strength = DivergenceStrength.STRONG
            elif len(indicators) >= 2:
                strength = DivergenceStrength.MODERATE
            else:
                strength = DivergenceStrength.WEAK
            
            for d in divs:
                # Cria novo objeto com força atualizada
                d.strength = strength
    
    def _calculate_rsi(self, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Calcula RSI."""
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        rsi = np.zeros(len(close))
        
        if len(close) <= period:
            return rsi
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        for i in range(period, len(close) - 1):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi[i + 1] = 100
            else:
                rs = avg_gain / avg_loss
                rsi[i + 1] = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(
        self,
        close: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calcula MACD."""
        ema_fast = self._ema(close, fast)
        ema_slow = self._ema(close, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_stochastic(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        k_period: int = 14,
        d_period: int = 3,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Calcula Stochastic."""
        k = np.zeros(len(close))
        
        for i in range(k_period, len(close)):
            highest = max(high[i-k_period:i+1])
            lowest = min(low[i-k_period:i+1])
            
            if highest != lowest:
                k[i] = 100 * (close[i] - lowest) / (highest - lowest)
        
        d = self._sma(k, d_period)
        
        return k, d
    
    def _calculate_obv(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Calcula OBV."""
        obv = np.zeros(len(close))
        
        for i in range(1, len(close)):
            if close[i] > close[i-1]:
                obv[i] = obv[i-1] + volume[i]
            elif close[i] < close[i-1]:
                obv[i] = obv[i-1] - volume[i]
            else:
                obv[i] = obv[i-1]
        
        return obv
    
    def _calculate_cci(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 20,
    ) -> np.ndarray:
        """Calcula CCI."""
        tp = (high + low + close) / 3
        cci = np.zeros(len(close))
        
        for i in range(period, len(close)):
            tp_slice = tp[i-period:i+1]
            sma = np.mean(tp_slice)
            mad = np.mean(np.abs(tp_slice - sma))
            
            if mad != 0:
                cci[i] = (tp[i] - sma) / (0.015 * mad)
        
        return cci
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcula EMA."""
        ema = np.zeros_like(data)
        multiplier = 2 / (period + 1)
        
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        
        return ema
    
    def _sma(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcula SMA."""
        sma = np.zeros_like(data)
        
        for i in range(period, len(data)):
            sma[i] = np.mean(data[i-period:i+1])
        
        return sma
    
    def _empty_result(self) -> DivergenceAnalysisResult:
        """Retorna resultado vazio."""
        return DivergenceAnalysisResult(
            divergences=[],
            bullish_count=0,
            bearish_count=0,
            strongest=None,
            confluence_score=0.0,
            actionable=False,
            bias='neutral',
        )
    
    def to_dict(self, result: DivergenceAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        divergences_list = []
        for d in result.divergences:
            divergences_list.append({
                'type': d.type.name,
                'indicator': d.indicator,
                'strength': d.strength.name,
                'bars_apart': d.bars_apart,
                'confirmed': d.confirmation,
            })
        
        strongest_dict = None
        if result.strongest:
            strongest_dict = {
                'type': result.strongest.type.name,
                'indicator': result.strongest.indicator,
                'strength': result.strongest.strength.name,
            }
        
        return {
            'divergences': divergences_list,
            'bullish_count': result.bullish_count,
            'bearish_count': result.bearish_count,
            'strongest': strongest_dict,
            'confluence_score': round(result.confluence_score, 3),
            'actionable': result.actionable,
            'bias': result.bias,
        }
