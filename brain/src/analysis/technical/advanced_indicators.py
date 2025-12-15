"""
VIRTUS Advanced Indicators
===========================

Indicadores avançados:
- Ichimoku Cloud completo
- VWAP com bandas
- Pivot Points (múltiplos tipos)
- Supertrend
- Chandelier Exit
- Keltner Channels
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


@dataclass
class IchimokuResult:
    """Resultado do Ichimoku."""
    tenkan_sen: float       # Conversion Line (9)
    kijun_sen: float        # Base Line (26)
    senkou_span_a: float    # Leading Span A
    senkou_span_b: float    # Leading Span B
    chikou_span: float      # Lagging Span
    cloud_top: float
    cloud_bottom: float
    cloud_color: str        # 'green' ou 'red'
    price_vs_cloud: str     # 'above', 'below', 'inside'
    tk_cross: str           # 'bullish', 'bearish', 'none'
    momentum: str           # 'bullish', 'bearish', 'neutral'
    signal_strength: float  # 0 a 1


@dataclass
class VWAPResult:
    """Resultado do VWAP."""
    vwap: float
    upper_band_1: float    # +1 desvio
    lower_band_1: float    # -1 desvio
    upper_band_2: float    # +2 desvios
    lower_band_2: float    # -2 desvios
    price_position: str    # 'above_vwap', 'below_vwap', 'at_vwap'
    distance_pct: float    # Distância em % do preço ao VWAP


@dataclass
class PivotPoints:
    """Pivot Points."""
    pivot: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float
    type: str  # 'standard', 'fibonacci', 'camarilla', 'woodie'


@dataclass
class SupertrendResult:
    """Resultado do Supertrend."""
    value: float
    direction: str  # 'up' ou 'down'
    signal: str     # 'buy', 'sell', 'hold'
    trend_changed: bool


@dataclass 
class AdvancedIndicatorsResult:
    """Resultado completo dos indicadores avançados."""
    ichimoku: IchimokuResult
    vwap: VWAPResult
    pivots: Dict[str, PivotPoints]  # Diferentes tipos
    supertrend: SupertrendResult
    atr: float
    atr_percent: float


class AdvancedIndicators:
    """
    Calculador de indicadores técnicos avançados.
    
    Fornece indicadores sofisticados para análise profissional.
    """
    
    def __init__(
        self,
        # Ichimoku
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
        displacement: int = 26,
        # Supertrend
        supertrend_period: int = 10,
        supertrend_multiplier: float = 3.0,
    ):
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        self.displacement = displacement
        self.supertrend_period = supertrend_period
        self.supertrend_multiplier = supertrend_multiplier
    
    def analyze(self, df: pd.DataFrame) -> AdvancedIndicatorsResult:
        """
        Calcula todos os indicadores avançados.
        
        Args:
            df: DataFrame com OHLCV
            
        Returns:
            AdvancedIndicatorsResult
        """
        if df is None or len(df) < 60:
            return self._empty_result()
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        volume = df['volume'].values if 'volume' in df.columns else df.get('tick_volume', np.ones(len(df))).values
        
        # Calcula cada indicador
        ichimoku = self._calculate_ichimoku(high, low, close)
        vwap = self._calculate_vwap(high, low, close, volume)
        pivots = self._calculate_all_pivots(high, low, close)
        supertrend = self._calculate_supertrend(high, low, close)
        atr, atr_pct = self._calculate_atr(high, low, close)
        
        return AdvancedIndicatorsResult(
            ichimoku=ichimoku,
            vwap=vwap,
            pivots=pivots,
            supertrend=supertrend,
            atr=atr,
            atr_percent=atr_pct,
        )
    
    def _calculate_ichimoku(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> IchimokuResult:
        """Calcula Ichimoku Cloud."""
        # Tenkan-sen (Conversion Line)
        tenkan = (self._highest(high, self.tenkan_period) + 
                  self._lowest(low, self.tenkan_period)) / 2
        
        # Kijun-sen (Base Line)
        kijun = (self._highest(high, self.kijun_period) + 
                 self._lowest(low, self.kijun_period)) / 2
        
        # Senkou Span A (Leading Span A)
        senkou_a = (tenkan[-1] + kijun[-1]) / 2
        
        # Senkou Span B (Leading Span B)
        senkou_b = (self._highest(high, self.senkou_b_period)[-1] + 
                    self._lowest(low, self.senkou_b_period)[-1]) / 2
        
        # Chikou Span (Lagging Span)
        chikou = close[-self.displacement] if len(close) > self.displacement else close[-1]
        
        # Cloud
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        cloud_color = 'green' if senkou_a > senkou_b else 'red'
        
        # Posição do preço em relação à nuvem
        current_price = close[-1]
        if current_price > cloud_top:
            price_vs_cloud = 'above'
        elif current_price < cloud_bottom:
            price_vs_cloud = 'below'
        else:
            price_vs_cloud = 'inside'
        
        # TK Cross
        current_tenkan = tenkan[-1]
        current_kijun = kijun[-1]
        prev_tenkan = tenkan[-2] if len(tenkan) > 1 else tenkan[-1]
        prev_kijun = kijun[-2] if len(kijun) > 1 else kijun[-1]
        
        if prev_tenkan <= prev_kijun and current_tenkan > current_kijun:
            tk_cross = 'bullish'
        elif prev_tenkan >= prev_kijun and current_tenkan < current_kijun:
            tk_cross = 'bearish'
        else:
            tk_cross = 'none'
        
        # Momentum
        bullish_signals = 0
        bearish_signals = 0
        
        if current_price > cloud_top:
            bullish_signals += 2
        elif current_price < cloud_bottom:
            bearish_signals += 2
        
        if current_tenkan > current_kijun:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if chikou > close[-self.displacement - 1]:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if cloud_color == 'green':
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if bullish_signals > bearish_signals + 2:
            momentum = 'bullish'
            signal_strength = bullish_signals / 5
        elif bearish_signals > bullish_signals + 2:
            momentum = 'bearish'
            signal_strength = bearish_signals / 5
        else:
            momentum = 'neutral'
            signal_strength = 0.5
        
        return IchimokuResult(
            tenkan_sen=current_tenkan,
            kijun_sen=current_kijun,
            senkou_span_a=senkou_a,
            senkou_span_b=senkou_b,
            chikou_span=chikou,
            cloud_top=cloud_top,
            cloud_bottom=cloud_bottom,
            cloud_color=cloud_color,
            price_vs_cloud=price_vs_cloud,
            tk_cross=tk_cross,
            momentum=momentum,
            signal_strength=min(1.0, signal_strength),
        )
    
    def _calculate_vwap(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
    ) -> VWAPResult:
        """Calcula VWAP com bandas."""
        # Typical Price
        tp = (high + low + close) / 3
        
        # VWAP cumulativo
        cum_tp_vol = np.cumsum(tp * volume)
        cum_vol = np.cumsum(volume)
        
        vwap_values = cum_tp_vol / np.where(cum_vol == 0, 1, cum_vol)
        current_vwap = vwap_values[-1]
        
        # Desvio padrão para bandas
        # Calcula variância ponderada por volume
        squared_diff = (tp - current_vwap) ** 2
        weighted_var = np.sum(squared_diff * volume) / np.sum(volume)
        std_dev = np.sqrt(weighted_var)
        
        upper_1 = current_vwap + std_dev
        lower_1 = current_vwap - std_dev
        upper_2 = current_vwap + (2 * std_dev)
        lower_2 = current_vwap - (2 * std_dev)
        
        # Posição do preço
        current_price = close[-1]
        if current_price > current_vwap:
            position = 'above_vwap'
        elif current_price < current_vwap:
            position = 'below_vwap'
        else:
            position = 'at_vwap'
        
        distance_pct = ((current_price - current_vwap) / current_vwap) * 100
        
        return VWAPResult(
            vwap=current_vwap,
            upper_band_1=upper_1,
            lower_band_1=lower_1,
            upper_band_2=upper_2,
            lower_band_2=lower_2,
            price_position=position,
            distance_pct=distance_pct,
        )
    
    def _calculate_all_pivots(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> Dict[str, PivotPoints]:
        """Calcula diferentes tipos de Pivot Points."""
        # Usa os valores do período anterior
        h = high[-2] if len(high) > 1 else high[-1]
        l = low[-2] if len(low) > 1 else low[-1]
        c = close[-2] if len(close) > 1 else close[-1]
        
        pivots = {}
        
        # Standard (Floor)
        pivot = (h + l + c) / 3
        pivots['standard'] = PivotPoints(
            pivot=pivot,
            r1=2 * pivot - l,
            r2=pivot + (h - l),
            r3=h + 2 * (pivot - l),
            s1=2 * pivot - h,
            s2=pivot - (h - l),
            s3=l - 2 * (h - pivot),
            type='standard',
        )
        
        # Fibonacci
        range_hl = h - l
        pivots['fibonacci'] = PivotPoints(
            pivot=pivot,
            r1=pivot + 0.382 * range_hl,
            r2=pivot + 0.618 * range_hl,
            r3=pivot + 1.0 * range_hl,
            s1=pivot - 0.382 * range_hl,
            s2=pivot - 0.618 * range_hl,
            s3=pivot - 1.0 * range_hl,
            type='fibonacci',
        )
        
        # Camarilla
        pivots['camarilla'] = PivotPoints(
            pivot=pivot,
            r1=c + range_hl * 1.1 / 12,
            r2=c + range_hl * 1.1 / 6,
            r3=c + range_hl * 1.1 / 4,
            s1=c - range_hl * 1.1 / 12,
            s2=c - range_hl * 1.1 / 6,
            s3=c - range_hl * 1.1 / 4,
            type='camarilla',
        )
        
        # Woodie
        woodie_pivot = (h + l + 2 * c) / 4
        pivots['woodie'] = PivotPoints(
            pivot=woodie_pivot,
            r1=2 * woodie_pivot - l,
            r2=woodie_pivot + range_hl,
            r3=h + 2 * (woodie_pivot - l),
            s1=2 * woodie_pivot - h,
            s2=woodie_pivot - range_hl,
            s3=l - 2 * (h - woodie_pivot),
            type='woodie',
        )
        
        return pivots
    
    def _calculate_supertrend(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> SupertrendResult:
        """Calcula Supertrend."""
        period = self.supertrend_period
        multiplier = self.supertrend_multiplier
        
        # ATR
        atr = self._atr(high, low, close, period)
        
        # Bandas básicas
        hl2 = (high + low) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        # Supertrend
        supertrend = np.zeros(len(close))
        direction = np.ones(len(close))
        
        for i in range(period, len(close)):
            if close[i] > upper_band[i-1]:
                direction[i] = 1
            elif close[i] < lower_band[i-1]:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
                
                if direction[i] == 1 and lower_band[i] < lower_band[i-1]:
                    lower_band[i] = lower_band[i-1]
                elif direction[i] == -1 and upper_band[i] > upper_band[i-1]:
                    upper_band[i] = upper_band[i-1]
            
            supertrend[i] = lower_band[i] if direction[i] == 1 else upper_band[i]
        
        current_direction = 'up' if direction[-1] == 1 else 'down'
        
        # Sinal
        trend_changed = direction[-1] != direction[-2] if len(direction) > 1 else False
        
        if trend_changed:
            signal = 'buy' if current_direction == 'up' else 'sell'
        else:
            signal = 'hold'
        
        return SupertrendResult(
            value=supertrend[-1],
            direction=current_direction,
            signal=signal,
            trend_changed=trend_changed,
        )
    
    def _calculate_atr(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14,
    ) -> Tuple[float, float]:
        """Calcula ATR e ATR percentual."""
        atr_values = self._atr(high, low, close, period)
        current_atr = atr_values[-1]
        atr_percent = (current_atr / close[-1]) * 100
        
        return current_atr, atr_percent
    
    def _atr(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int,
    ) -> np.ndarray:
        """Calcula ATR."""
        tr = np.zeros(len(close))
        
        for i in range(1, len(close)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        atr = np.zeros(len(close))
        atr[period] = np.mean(tr[:period])
        
        for i in range(period + 1, len(close)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        return atr
    
    def _highest(self, data: np.ndarray, period: int) -> np.ndarray:
        """Maior valor dos últimos n períodos."""
        result = np.zeros(len(data))
        for i in range(period, len(data)):
            result[i] = max(data[i-period:i+1])
        return result
    
    def _lowest(self, data: np.ndarray, period: int) -> np.ndarray:
        """Menor valor dos últimos n períodos."""
        result = np.zeros(len(data))
        result[:period] = np.inf
        for i in range(period, len(data)):
            result[i] = min(data[i-period:i+1])
        return result
    
    def _empty_result(self) -> AdvancedIndicatorsResult:
        """Retorna resultado vazio."""
        empty_ichimoku = IchimokuResult(
            tenkan_sen=0, kijun_sen=0, senkou_span_a=0, senkou_span_b=0,
            chikou_span=0, cloud_top=0, cloud_bottom=0, cloud_color='neutral',
            price_vs_cloud='unknown', tk_cross='none', momentum='neutral',
            signal_strength=0,
        )
        
        empty_vwap = VWAPResult(
            vwap=0, upper_band_1=0, lower_band_1=0, upper_band_2=0,
            lower_band_2=0, price_position='unknown', distance_pct=0,
        )
        
        empty_supertrend = SupertrendResult(
            value=0, direction='none', signal='hold', trend_changed=False,
        )
        
        return AdvancedIndicatorsResult(
            ichimoku=empty_ichimoku,
            vwap=empty_vwap,
            pivots={},
            supertrend=empty_supertrend,
            atr=0,
            atr_percent=0,
        )
    
    def to_dict(self, result: AdvancedIndicatorsResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        pivots_dict = {}
        for ptype, pdata in result.pivots.items():
            pivots_dict[ptype] = {
                'pivot': round(pdata.pivot, 5),
                'r1': round(pdata.r1, 5),
                'r2': round(pdata.r2, 5),
                'r3': round(pdata.r3, 5),
                's1': round(pdata.s1, 5),
                's2': round(pdata.s2, 5),
                's3': round(pdata.s3, 5),
            }
        
        return {
            'ichimoku': {
                'tenkan_sen': round(result.ichimoku.tenkan_sen, 5),
                'kijun_sen': round(result.ichimoku.kijun_sen, 5),
                'senkou_span_a': round(result.ichimoku.senkou_span_a, 5),
                'senkou_span_b': round(result.ichimoku.senkou_span_b, 5),
                'cloud_color': result.ichimoku.cloud_color,
                'price_vs_cloud': result.ichimoku.price_vs_cloud,
                'tk_cross': result.ichimoku.tk_cross,
                'momentum': result.ichimoku.momentum,
                'signal_strength': round(result.ichimoku.signal_strength, 3),
            },
            'vwap': {
                'value': round(result.vwap.vwap, 5),
                'upper_1': round(result.vwap.upper_band_1, 5),
                'lower_1': round(result.vwap.lower_band_1, 5),
                'upper_2': round(result.vwap.upper_band_2, 5),
                'lower_2': round(result.vwap.lower_band_2, 5),
                'position': result.vwap.price_position,
                'distance_pct': round(result.vwap.distance_pct, 3),
            },
            'pivots': pivots_dict,
            'supertrend': {
                'value': round(result.supertrend.value, 5),
                'direction': result.supertrend.direction,
                'signal': result.supertrend.signal,
                'trend_changed': result.supertrend.trend_changed,
            },
            'atr': round(result.atr, 5),
            'atr_percent': round(result.atr_percent, 4),
        }
