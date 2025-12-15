"""
VIRTUS Volume Analysis
=======================

Análise avançada de volume:
- Volume Profile
- POC (Point of Control)
- Value Area (VA High/Low)
- Delta Volume
- Volume Spread Analysis (VSA)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from collections import defaultdict


class VolumeSignal(Enum):
    """Sinais de volume."""
    CLIMAX_BUY = auto()        # Volume muito alto com alta
    CLIMAX_SELL = auto()       # Volume muito alto com queda
    NO_DEMAND = auto()         # Tentativa de alta sem volume
    NO_SUPPLY = auto()         # Tentativa de queda sem volume
    STOPPING_VOLUME = auto()   # Volume alto parando movimento
    TEST = auto()              # Teste de oferta/demanda
    ACCUMULATION = auto()      # Acumulação
    DISTRIBUTION = auto()      # Distribuição


@dataclass
class VolumeProfileLevel:
    """Nível do Volume Profile."""
    price: float
    volume: float
    buy_volume: float
    sell_volume: float
    delta: float  # buy - sell
    
    @property
    def imbalance(self) -> float:
        """Razão de imbalance."""
        total = self.buy_volume + self.sell_volume
        if total == 0:
            return 0
        return (self.buy_volume - self.sell_volume) / total


@dataclass
class VolumeProfile:
    """Volume Profile calculado."""
    levels: List[VolumeProfileLevel]
    poc: float  # Point of Control
    vah: float  # Value Area High
    val: float  # Value Area Low
    total_volume: float
    buy_volume: float
    sell_volume: float
    delta: float
    
    @property
    def value_area(self) -> Tuple[float, float]:
        """Retorna Value Area (VAL, VAH)."""
        return (self.val, self.vah)


@dataclass
class VolumeAnalysisResult:
    """Resultado da análise de volume."""
    current_volume: float
    average_volume: float
    volume_ratio: float  # current / average
    profile: Optional[VolumeProfile]
    signals: List[VolumeSignal]
    trend_confirmation: bool
    divergence: bool
    accumulation_score: float  # -1 (distribuição) a +1 (acumulação)


class VolumeAnalyzer:
    """
    Analisador de volume avançado.
    
    Implementa:
    - Volume Profile com POC e Value Area
    - Delta Volume (compra vs venda estimada)
    - Volume Spread Analysis (VSA)
    - Detecção de acumulação/distribuição
    """
    
    def __init__(
        self,
        profile_levels: int = 24,  # Níveis no volume profile
        value_area_pct: float = 0.70,  # 70% do volume
        volume_ma_period: int = 20,
    ):
        self.profile_levels = profile_levels
        self.value_area_pct = value_area_pct
        self.volume_ma_period = volume_ma_period
    
    def analyze(self, df: pd.DataFrame) -> VolumeAnalysisResult:
        """
        Análise completa de volume.
        
        Args:
            df: DataFrame com OHLCV
            
        Returns:
            VolumeAnalysisResult com análise completa
        """
        if df is None or len(df) < self.volume_ma_period:
            return self._empty_result()
        
        # Verifica se tem coluna de volume
        if 'volume' not in df.columns and 'tick_volume' not in df.columns:
            return self._empty_result()
        
        volume_col = 'volume' if 'volume' in df.columns else 'tick_volume'
        volume = df[volume_col].values
        
        # Volume atual e médio
        current_volume = volume[-1]
        avg_volume = np.mean(volume[-self.volume_ma_period:])
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Calcula Volume Profile
        profile = self._calculate_volume_profile(df, volume_col)
        
        # Detecta sinais VSA
        signals = self._detect_vsa_signals(df, volume_col)
        
        # Verifica confirmação de tendência
        trend_confirmation = self._check_trend_confirmation(df, volume_col)
        
        # Verifica divergência
        divergence = self._check_volume_divergence(df, volume_col)
        
        # Score de acumulação/distribuição
        accum_score = self._calculate_accumulation_score(df, volume_col)
        
        return VolumeAnalysisResult(
            current_volume=current_volume,
            average_volume=avg_volume,
            volume_ratio=volume_ratio,
            profile=profile,
            signals=signals,
            trend_confirmation=trend_confirmation,
            divergence=divergence,
            accumulation_score=accum_score,
        )
    
    def _calculate_volume_profile(self, df: pd.DataFrame, volume_col: str) -> Optional[VolumeProfile]:
        """Calcula Volume Profile."""
        if len(df) < 10:
            return None
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        open_prices = df['open'].values
        volume = df[volume_col].values
        
        # Define range do profile
        profile_high = max(high)
        profile_low = min(low)
        step = (profile_high - profile_low) / self.profile_levels
        
        if step <= 0:
            return None
        
        # Inicializa níveis
        levels = []
        level_volumes = defaultdict(lambda: {'total': 0, 'buy': 0, 'sell': 0})
        
        # Distribui volume nos níveis
        for i in range(len(df)):
            candle_high = high[i]
            candle_low = low[i]
            candle_volume = volume[i]
            
            # Estima delta baseado na posição do close
            candle_range = candle_high - candle_low
            if candle_range > 0:
                close_position = (close[i] - candle_low) / candle_range
            else:
                close_position = 0.5
            
            # Candle bullish = mais compra, bearish = mais venda
            is_bullish = close[i] > open_prices[i]
            
            if is_bullish:
                buy_pct = 0.5 + (close_position * 0.3)
            else:
                buy_pct = 0.5 - ((1 - close_position) * 0.3)
            
            buy_volume = candle_volume * buy_pct
            sell_volume = candle_volume * (1 - buy_pct)
            
            # Distribui entre níveis que o candle tocou
            level_start = int((candle_low - profile_low) / step)
            level_end = int((candle_high - profile_low) / step)
            
            levels_touched = max(1, level_end - level_start + 1)
            vol_per_level = candle_volume / levels_touched
            buy_per_level = buy_volume / levels_touched
            sell_per_level = sell_volume / levels_touched
            
            for lvl in range(level_start, min(level_end + 1, self.profile_levels)):
                level_volumes[lvl]['total'] += vol_per_level
                level_volumes[lvl]['buy'] += buy_per_level
                level_volumes[lvl]['sell'] += sell_per_level
        
        # Converte para lista de VolumeProfileLevel
        for lvl in range(self.profile_levels):
            price = profile_low + (lvl + 0.5) * step
            vol_data = level_volumes[lvl]
            
            levels.append(VolumeProfileLevel(
                price=price,
                volume=vol_data['total'],
                buy_volume=vol_data['buy'],
                sell_volume=vol_data['sell'],
                delta=vol_data['buy'] - vol_data['sell'],
            ))
        
        # Encontra POC
        poc_level = max(levels, key=lambda x: x.volume)
        poc = poc_level.price
        
        # Calcula Value Area
        total_volume = sum(lvl.volume for lvl in levels)
        target_volume = total_volume * self.value_area_pct
        
        # Expande do POC
        poc_idx = levels.index(poc_level)
        accumulated = poc_level.volume
        low_idx = poc_idx
        high_idx = poc_idx
        
        while accumulated < target_volume:
            # Adiciona próximo nível com mais volume
            add_low = low_idx > 0
            add_high = high_idx < len(levels) - 1
            
            if add_low and add_high:
                if levels[low_idx - 1].volume >= levels[high_idx + 1].volume:
                    low_idx -= 1
                    accumulated += levels[low_idx].volume
                else:
                    high_idx += 1
                    accumulated += levels[high_idx].volume
            elif add_low:
                low_idx -= 1
                accumulated += levels[low_idx].volume
            elif add_high:
                high_idx += 1
                accumulated += levels[high_idx].volume
            else:
                break
        
        val = levels[low_idx].price - step/2
        vah = levels[high_idx].price + step/2
        
        total_buy = sum(lvl.buy_volume for lvl in levels)
        total_sell = sum(lvl.sell_volume for lvl in levels)
        
        return VolumeProfile(
            levels=levels,
            poc=poc,
            vah=vah,
            val=val,
            total_volume=total_volume,
            buy_volume=total_buy,
            sell_volume=total_sell,
            delta=total_buy - total_sell,
        )
    
    def _detect_vsa_signals(self, df: pd.DataFrame, volume_col: str) -> List[VolumeSignal]:
        """Detecta sinais de Volume Spread Analysis."""
        signals = []
        
        if len(df) < 5:
            return signals
        
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df[volume_col].values
        
        # Últimos candles
        last_close = close[-1]
        last_high = high[-1]
        last_low = low[-1]
        last_volume = volume[-1]
        last_spread = last_high - last_low
        
        prev_close = close[-2]
        
        avg_volume = np.mean(volume[-20:])
        avg_spread = np.mean(high[-20:] - low[-20:])
        
        # Volume muito acima da média
        high_volume = last_volume > avg_volume * 1.5
        very_high_volume = last_volume > avg_volume * 2.0
        low_volume = last_volume < avg_volume * 0.7
        
        # Spread
        wide_spread = last_spread > avg_spread * 1.3
        narrow_spread = last_spread < avg_spread * 0.7
        
        # Posição do close no range
        if last_spread > 0:
            close_position = (last_close - last_low) / last_spread
        else:
            close_position = 0.5
        
        is_up = last_close > prev_close
        is_down = last_close < prev_close
        
        # Climax Buy: Volume muito alto + spread largo + close alto + alta
        if very_high_volume and wide_spread and close_position > 0.6 and is_up:
            signals.append(VolumeSignal.CLIMAX_BUY)
        
        # Climax Sell: Volume muito alto + spread largo + close baixo + queda
        if very_high_volume and wide_spread and close_position < 0.4 and is_down:
            signals.append(VolumeSignal.CLIMAX_SELL)
        
        # No Demand: Tentativa de alta + volume baixo + spread estreito
        if is_up and low_volume and narrow_spread:
            signals.append(VolumeSignal.NO_DEMAND)
        
        # No Supply: Tentativa de queda + volume baixo + spread estreito
        if is_down and low_volume and narrow_spread:
            signals.append(VolumeSignal.NO_SUPPLY)
        
        # Stopping Volume: Volume muito alto que para o movimento
        if very_high_volume:
            # Verifica se parou tendência
            prev_trend_up = close[-3] < close[-2]
            prev_trend_down = close[-3] > close[-2]
            
            if prev_trend_up and is_down:
                signals.append(VolumeSignal.STOPPING_VOLUME)
            elif prev_trend_down and is_up:
                signals.append(VolumeSignal.STOPPING_VOLUME)
        
        # Test: Volume baixo testando área
        if low_volume and narrow_spread:
            signals.append(VolumeSignal.TEST)
        
        return signals
    
    def _check_trend_confirmation(self, df: pd.DataFrame, volume_col: str) -> bool:
        """Verifica se volume confirma a tendência."""
        if len(df) < 10:
            return False
        
        close = df['close'].values
        volume = df[volume_col].values
        
        # Tendência de preço (últimos 10 candles)
        price_trend = close[-1] - close[-10]
        
        # Tendência de volume
        vol_first_half = np.mean(volume[-10:-5])
        vol_second_half = np.mean(volume[-5:])
        vol_trend = vol_second_half - vol_first_half
        
        # Confirmação: volume aumentando na direção da tendência
        if price_trend > 0 and vol_trend > 0:
            return True
        elif price_trend < 0 and vol_trend > 0:
            return True
        
        return False
    
    def _check_volume_divergence(self, df: pd.DataFrame, volume_col: str) -> bool:
        """Verifica divergência entre preço e volume."""
        if len(df) < 20:
            return False
        
        close = df['close'].values
        volume = df[volume_col].values
        
        # Compara últimos dois movimentos
        # Movimento 1: candles -20 a -10
        # Movimento 2: candles -10 a atual
        
        price_move_1 = close[-10] - close[-20]
        price_move_2 = close[-1] - close[-10]
        
        vol_move_1 = np.mean(volume[-20:-10])
        vol_move_2 = np.mean(volume[-10:])
        
        # Divergência: preço faz novo high mas volume diminui
        if price_move_1 > 0 and price_move_2 > 0:
            if close[-1] > close[-10] > close[-20]:  # Novos highs
                if vol_move_2 < vol_move_1 * 0.8:  # Volume menor
                    return True
        
        # Divergência bearish: preço faz novo low mas volume diminui
        if price_move_1 < 0 and price_move_2 < 0:
            if close[-1] < close[-10] < close[-20]:  # Novos lows
                if vol_move_2 < vol_move_1 * 0.8:
                    return True
        
        return False
    
    def _calculate_accumulation_score(self, df: pd.DataFrame, volume_col: str) -> float:
        """
        Calcula score de acumulação/distribuição.
        
        Returns:
            -1 (forte distribuição) a +1 (forte acumulação)
        """
        if len(df) < 20:
            return 0.0
        
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df[volume_col].values
        
        # Accumulation/Distribution Line
        ad_values = []
        
        for i in range(len(df)):
            hl_range = high[i] - low[i]
            if hl_range > 0:
                clv = ((close[i] - low[i]) - (high[i] - close[i])) / hl_range
            else:
                clv = 0
            
            ad = clv * volume[i]
            ad_values.append(ad)
        
        # Tendência do A/D nos últimos 20 candles
        ad_array = np.array(ad_values[-20:])
        
        if len(ad_array) < 2:
            return 0.0
        
        # Regressão linear simples
        x = np.arange(len(ad_array))
        slope = np.polyfit(x, ad_array, 1)[0]
        
        # Normaliza para -1 a +1
        avg_volume = np.mean(volume[-20:])
        normalized_slope = slope / avg_volume if avg_volume > 0 else 0
        
        return max(-1, min(1, normalized_slope * 10))
    
    def _empty_result(self) -> VolumeAnalysisResult:
        """Retorna resultado vazio."""
        return VolumeAnalysisResult(
            current_volume=0,
            average_volume=0,
            volume_ratio=1.0,
            profile=None,
            signals=[],
            trend_confirmation=False,
            divergence=False,
            accumulation_score=0.0,
        )
    
    def to_dict(self, result: VolumeAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        profile_dict = None
        if result.profile:
            profile_dict = {
                'poc': round(result.profile.poc, 5),
                'vah': round(result.profile.vah, 5),
                'val': round(result.profile.val, 5),
                'delta': round(result.profile.delta, 2),
                'buy_volume': round(result.profile.buy_volume, 2),
                'sell_volume': round(result.profile.sell_volume, 2),
            }
        
        return {
            'current_volume': round(result.current_volume, 2),
            'average_volume': round(result.average_volume, 2),
            'volume_ratio': round(result.volume_ratio, 2),
            'profile': profile_dict,
            'signals': [s.name for s in result.signals],
            'trend_confirmation': result.trend_confirmation,
            'divergence': result.divergence,
            'accumulation_score': round(result.accumulation_score, 3),
        }
