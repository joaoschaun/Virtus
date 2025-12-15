"""
VIRTUS Market Regime Detector
==============================

Detecta o regime atual do mercado para adaptação automática de estratégias.

Regimes detectados:
1. TRENDING_UP - Tendência de alta clara
2. TRENDING_DOWN - Tendência de baixa clara  
3. RANGING - Mercado lateral/consolidação
4. VOLATILE - Alta volatilidade
5. BREAKOUT - Rompimento em andamento
6. REVERSAL - Possível reversão
7. QUIET - Baixa volatilidade/mercado parado

Cada regime tem multiplicadores de risco e parâmetros otimizados.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
import logging


class MarketRegime(Enum):
    """Regimes de mercado."""
    TRENDING_UP = auto()      # Tendência de alta
    TRENDING_DOWN = auto()    # Tendência de baixa
    RANGING = auto()          # Consolidação lateral
    VOLATILE = auto()         # Alta volatilidade
    BREAKOUT = auto()         # Rompimento
    REVERSAL = auto()         # Reversão
    QUIET = auto()            # Baixa volatilidade
    UNKNOWN = auto()          # Indefinido


@dataclass
class RegimeParameters:
    """Parâmetros otimizados para cada regime."""
    
    # Trading
    risk_multiplier: float     # Multiplicador de risco (1.0 = normal)
    position_size_mult: float  # Multiplicador de tamanho
    max_trades: int            # Máx trades simultâneos
    
    # Stops
    sl_atr_mult: float        # SL em múltiplos de ATR
    tp_atr_mult: float        # TP em múltiplos de ATR
    trailing_enabled: bool    # Usar trailing stop
    trailing_activation: float # ATR para ativar trailing
    
    # Timeframes
    preferred_tf: str         # Timeframe preferido
    confirmation_tf: str      # TF para confirmação
    
    # Estratégias recomendadas
    strategies: List[str]     # Estratégias recomendadas
    avoid_strategies: List[str]  # Estratégias a evitar
    
    # Indicadores
    indicator_weights: Dict[str, float] = field(default_factory=dict)


# Parâmetros por regime
REGIME_PARAMS: Dict[MarketRegime, RegimeParameters] = {
    
    MarketRegime.TRENDING_UP: RegimeParameters(
        risk_multiplier=1.2,
        position_size_mult=1.1,
        max_trades=3,
        sl_atr_mult=1.5,
        tp_atr_mult=3.0,
        trailing_enabled=True,
        trailing_activation=1.0,
        preferred_tf='H1',
        confirmation_tf='H4',
        strategies=['trend_following', 'pullback_buy', 'breakout'],
        avoid_strategies=['counter_trend', 'scalping_sell'],
        indicator_weights={
            'moving_averages': 1.2,
            'trend_strength': 1.3,
            'momentum': 1.1,
            'reversal': 0.5,
        }
    ),
    
    MarketRegime.TRENDING_DOWN: RegimeParameters(
        risk_multiplier=1.2,
        position_size_mult=1.1,
        max_trades=3,
        sl_atr_mult=1.5,
        tp_atr_mult=3.0,
        trailing_enabled=True,
        trailing_activation=1.0,
        preferred_tf='H1',
        confirmation_tf='H4',
        strategies=['trend_following', 'pullback_sell', 'breakout'],
        avoid_strategies=['counter_trend', 'scalping_buy'],
        indicator_weights={
            'moving_averages': 1.2,
            'trend_strength': 1.3,
            'momentum': 1.1,
            'reversal': 0.5,
        }
    ),
    
    MarketRegime.RANGING: RegimeParameters(
        risk_multiplier=0.8,
        position_size_mult=0.8,
        max_trades=2,
        sl_atr_mult=1.2,
        tp_atr_mult=1.5,
        trailing_enabled=False,
        trailing_activation=0,
        preferred_tf='M15',
        confirmation_tf='H1',
        strategies=['mean_reversion', 'range_trading', 'scalping'],
        avoid_strategies=['trend_following', 'breakout'],
        indicator_weights={
            'support_resistance': 1.3,
            'oscillators': 1.2,
            'momentum': 0.8,
            'trend': 0.6,
        }
    ),
    
    MarketRegime.VOLATILE: RegimeParameters(
        risk_multiplier=0.5,
        position_size_mult=0.5,
        max_trades=1,
        sl_atr_mult=2.0,
        tp_atr_mult=2.5,
        trailing_enabled=True,
        trailing_activation=1.5,
        preferred_tf='M30',
        confirmation_tf='H1',
        strategies=['volatility_breakout', 'momentum'],
        avoid_strategies=['scalping', 'tight_stops'],
        indicator_weights={
            'volatility': 1.3,
            'momentum': 1.1,
            'volume': 1.2,
            'trend': 0.8,
        }
    ),
    
    MarketRegime.BREAKOUT: RegimeParameters(
        risk_multiplier=1.0,
        position_size_mult=1.0,
        max_trades=2,
        sl_atr_mult=1.3,
        tp_atr_mult=2.5,
        trailing_enabled=True,
        trailing_activation=1.0,
        preferred_tf='M15',
        confirmation_tf='H1',
        strategies=['breakout', 'momentum', 'follow_through'],
        avoid_strategies=['mean_reversion', 'counter_trend'],
        indicator_weights={
            'volume': 1.4,
            'momentum': 1.3,
            'volatility': 1.2,
            'support_resistance': 1.1,
        }
    ),
    
    MarketRegime.REVERSAL: RegimeParameters(
        risk_multiplier=0.7,
        position_size_mult=0.7,
        max_trades=1,
        sl_atr_mult=1.8,
        tp_atr_mult=3.0,
        trailing_enabled=False,
        trailing_activation=0,
        preferred_tf='H1',
        confirmation_tf='H4',
        strategies=['reversal', 'divergence', 'exhaustion'],
        avoid_strategies=['trend_following', 'breakout'],
        indicator_weights={
            'divergence': 1.4,
            'exhaustion': 1.3,
            'volume': 1.2,
            'support_resistance': 1.2,
        }
    ),
    
    MarketRegime.QUIET: RegimeParameters(
        risk_multiplier=0.6,
        position_size_mult=0.6,
        max_trades=1,
        sl_atr_mult=1.0,
        tp_atr_mult=1.2,
        trailing_enabled=False,
        trailing_activation=0,
        preferred_tf='M5',
        confirmation_tf='M15',
        strategies=['scalping', 'tight_range'],
        avoid_strategies=['trend_following', 'swing'],
        indicator_weights={
            'oscillators': 1.2,
            'micro_structure': 1.1,
            'spread': 1.3,
        }
    ),
    
    MarketRegime.UNKNOWN: RegimeParameters(
        risk_multiplier=0.3,
        position_size_mult=0.3,
        max_trades=1,
        sl_atr_mult=1.5,
        tp_atr_mult=1.5,
        trailing_enabled=False,
        trailing_activation=0,
        preferred_tf='M30',
        confirmation_tf='H1',
        strategies=['wait'],
        avoid_strategies=['all'],
        indicator_weights={},
    ),
}


@dataclass
class RegimeAnalysisResult:
    """Resultado da análise de regime."""
    current_regime: MarketRegime
    confidence: float  # 0 a 1
    parameters: RegimeParameters
    secondary_regime: Optional[MarketRegime]
    regime_strength: float  # Quão forte o regime está
    transition_probability: float  # Probabilidade de mudança
    recommended_bias: str  # 'LONG', 'SHORT', 'NEUTRAL'
    details: Dict[str, Any]


class MarketRegimeDetector:
    """
    Detecta o regime atual do mercado.
    
    Usa múltiplos indicadores para classificar o mercado
    e ajustar automaticamente os parâmetros de trading.
    """
    
    def __init__(
        self,
        logger: logging.Logger = None,
        # ADX
        adx_trend_threshold: float = 25,
        adx_strong_trend: float = 40,
        # ATR
        atr_period: int = 14,
        volatility_lookback: int = 50,
        high_volatility_mult: float = 1.5,
        low_volatility_mult: float = 0.7,
        # Range
        range_detection_bars: int = 30,
        range_threshold_pct: float = 0.015,  # 1.5%
        # Breakout
        breakout_volume_mult: float = 1.5,
        # RSI
        rsi_period: int = 14,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
    ):
        self.logger = logger or logging.getLogger(__name__)
        
        self.adx_trend_threshold = adx_trend_threshold
        self.adx_strong_trend = adx_strong_trend
        self.atr_period = atr_period
        self.volatility_lookback = volatility_lookback
        self.high_volatility_mult = high_volatility_mult
        self.low_volatility_mult = low_volatility_mult
        self.range_detection_bars = range_detection_bars
        self.range_threshold_pct = range_threshold_pct
        self.breakout_volume_mult = breakout_volume_mult
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        
        self.last_regime: Optional[MarketRegime] = None
        self.regime_history: List[Tuple[datetime, MarketRegime]] = []
    
    def analyze(self, df: pd.DataFrame) -> RegimeAnalysisResult:
        """
        Analisa e detecta o regime do mercado.
        
        Args:
            df: DataFrame OHLCV
            
        Returns:
            RegimeAnalysisResult
        """
        if df is None or len(df) < self.volatility_lookback:
            return self._unknown_result()
        
        # Calcula indicadores
        indicators = self._calculate_indicators(df)
        
        # Scores para cada regime
        scores = self._calculate_regime_scores(df, indicators)
        
        # Determina regime principal
        regime, confidence = self._determine_regime(scores)
        
        # Regime secundário
        secondary = self._get_secondary_regime(scores, regime)
        
        # Força do regime
        strength = self._calculate_regime_strength(df, indicators, regime)
        
        # Probabilidade de transição
        transition_prob = self._estimate_transition_probability(indicators, regime)
        
        # Bias recomendado
        bias = self._determine_bias(df, indicators, regime)
        
        # Atualiza histórico
        self.last_regime = regime
        self.regime_history.append((datetime.now(), regime))
        
        return RegimeAnalysisResult(
            current_regime=regime,
            confidence=confidence,
            parameters=REGIME_PARAMS[regime],
            secondary_regime=secondary,
            regime_strength=strength,
            transition_probability=transition_prob,
            recommended_bias=bias,
            details={
                'scores': {r.name: round(s, 2) for r, s in scores.items()},
                'indicators': indicators,
            }
        )
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcula indicadores para detecção."""
        indicators = {}
        
        # ATR e Volatilidade
        df_calc = df.copy()
        df_calc['tr'] = np.maximum(
            df_calc['high'] - df_calc['low'],
            np.maximum(
                abs(df_calc['high'] - df_calc['close'].shift(1)),
                abs(df_calc['low'] - df_calc['close'].shift(1))
            )
        )
        atr = df_calc['tr'].rolling(self.atr_period).mean().iloc[-1]
        avg_atr = df_calc['tr'].rolling(self.volatility_lookback).mean().iloc[-1]
        
        indicators['atr'] = atr
        indicators['volatility_ratio'] = atr / avg_atr if avg_atr > 0 else 1.0
        
        # ADX
        adx = self._calculate_adx(df)
        indicators['adx'] = adx
        
        # Direção da tendência
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        sma_50 = df['close'].rolling(50).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        indicators['trend_direction'] = 1 if sma_20 > sma_50 else -1
        indicators['price_vs_sma20'] = (current_price - sma_20) / sma_20
        indicators['price_vs_sma50'] = (current_price - sma_50) / sma_50 if len(df) >= 50 else 0
        
        # RSI
        rsi = self._calculate_rsi(df)
        indicators['rsi'] = rsi
        
        # Range
        recent = df.iloc[-self.range_detection_bars:]
        range_high = recent['high'].max()
        range_low = recent['low'].min()
        range_pct = (range_high - range_low) / range_low if range_low > 0 else 0
        
        indicators['range_pct'] = range_pct
        indicators['in_range'] = range_pct < self.range_threshold_pct
        
        # Volume
        vol_col = 'volume' if 'volume' in df.columns else 'tick_volume'
        current_vol = df[vol_col].iloc[-1]
        avg_vol = df[vol_col].rolling(20).mean().iloc[-1]
        
        indicators['volume_ratio'] = current_vol / avg_vol if avg_vol > 0 else 1.0
        
        # Breakout potencial
        lookback = 20
        recent_high = df['high'].iloc[-lookback:-1].max()
        recent_low = df['low'].iloc[-lookback:-1].min()
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        indicators['near_breakout_high'] = current_high >= recent_high * 0.998
        indicators['near_breakout_low'] = current_low <= recent_low * 1.002
        
        return indicators
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula ADX."""
        df_calc = df.copy()
        
        df_calc['plus_dm'] = df_calc['high'].diff()
        df_calc['minus_dm'] = -df_calc['low'].diff()
        
        df_calc['plus_dm'] = df_calc.apply(
            lambda x: x['plus_dm'] if x['plus_dm'] > x['minus_dm'] and x['plus_dm'] > 0 else 0, axis=1
        )
        df_calc['minus_dm'] = df_calc.apply(
            lambda x: x['minus_dm'] if x['minus_dm'] > x['plus_dm'] and x['minus_dm'] > 0 else 0, axis=1
        )
        
        df_calc['tr'] = np.maximum(
            df_calc['high'] - df_calc['low'],
            np.maximum(
                abs(df_calc['high'] - df_calc['close'].shift(1)),
                abs(df_calc['low'] - df_calc['close'].shift(1))
            )
        )
        
        smoothed_tr = df_calc['tr'].rolling(period).mean()
        smoothed_plus_dm = df_calc['plus_dm'].rolling(period).mean()
        smoothed_minus_dm = df_calc['minus_dm'].rolling(period).mean()
        
        plus_di = 100 * smoothed_plus_dm / smoothed_tr
        minus_di = 100 * smoothed_minus_dm / smoothed_tr
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.001)
        adx = dx.rolling(period).mean().iloc[-1]
        
        return float(adx) if not np.isnan(adx) else 0
    
    def _calculate_rsi(self, df: pd.DataFrame) -> float:
        """Calcula RSI."""
        delta = df['close'].diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        
        rs = avg_gain / (avg_loss + 0.001)
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50
    
    def _calculate_regime_scores(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, float]
    ) -> Dict[MarketRegime, float]:
        """Calcula scores para cada regime."""
        scores = {regime: 0.0 for regime in MarketRegime}
        
        adx = indicators['adx']
        vol_ratio = indicators['volatility_ratio']
        rsi = indicators['rsi']
        trend_dir = indicators['trend_direction']
        range_pct = indicators['range_pct']
        volume_ratio = indicators['volume_ratio']
        
        # TRENDING_UP
        if adx >= self.adx_trend_threshold and trend_dir > 0:
            scores[MarketRegime.TRENDING_UP] = min(adx / 50, 1.0) * 1.2
            if indicators['price_vs_sma20'] > 0:
                scores[MarketRegime.TRENDING_UP] *= 1.1
        
        # TRENDING_DOWN
        if adx >= self.adx_trend_threshold and trend_dir < 0:
            scores[MarketRegime.TRENDING_DOWN] = min(adx / 50, 1.0) * 1.2
            if indicators['price_vs_sma20'] < 0:
                scores[MarketRegime.TRENDING_DOWN] *= 1.1
        
        # RANGING
        if adx < self.adx_trend_threshold:
            scores[MarketRegime.RANGING] = (self.adx_trend_threshold - adx) / self.adx_trend_threshold
            if indicators['in_range']:
                scores[MarketRegime.RANGING] *= 1.3
            if vol_ratio < 1.0:
                scores[MarketRegime.RANGING] *= 1.2
        
        # VOLATILE
        if vol_ratio >= self.high_volatility_mult:
            scores[MarketRegime.VOLATILE] = min((vol_ratio - 1) / 0.5, 1.0)
            if volume_ratio > 1.5:
                scores[MarketRegime.VOLATILE] *= 1.2
        
        # BREAKOUT
        if indicators.get('near_breakout_high') or indicators.get('near_breakout_low'):
            scores[MarketRegime.BREAKOUT] = 0.8
            if volume_ratio > self.breakout_volume_mult:
                scores[MarketRegime.BREAKOUT] *= 1.3
        
        # REVERSAL
        if rsi >= self.rsi_overbought or rsi <= self.rsi_oversold:
            scores[MarketRegime.REVERSAL] = abs(rsi - 50) / 50
            
            # Reversão após tendência forte
            if adx > self.adx_strong_trend:
                if (rsi >= self.rsi_overbought and trend_dir > 0) or \
                   (rsi <= self.rsi_oversold and trend_dir < 0):
                    scores[MarketRegime.REVERSAL] *= 1.4
        
        # QUIET
        if vol_ratio <= self.low_volatility_mult:
            scores[MarketRegime.QUIET] = (self.low_volatility_mult - vol_ratio) / self.low_volatility_mult
            if adx < 20:
                scores[MarketRegime.QUIET] *= 1.2
        
        return scores
    
    def _determine_regime(
        self,
        scores: Dict[MarketRegime, float]
    ) -> Tuple[MarketRegime, float]:
        """Determina regime principal e confiança."""
        
        # Remove UNKNOWN dos scores
        active_scores = {k: v for k, v in scores.items() if k != MarketRegime.UNKNOWN}
        
        if not active_scores or max(active_scores.values()) < 0.3:
            return MarketRegime.UNKNOWN, 0.3
        
        # Regime com maior score
        regime = max(active_scores, key=active_scores.get)
        max_score = active_scores[regime]
        
        # Calcula confiança (baseada na diferença para o segundo)
        sorted_scores = sorted(active_scores.values(), reverse=True)
        if len(sorted_scores) >= 2:
            diff = sorted_scores[0] - sorted_scores[1]
            confidence = min(0.5 + diff * 0.5, 0.95)
        else:
            confidence = 0.7
        
        return regime, confidence
    
    def _get_secondary_regime(
        self,
        scores: Dict[MarketRegime, float],
        primary: MarketRegime
    ) -> Optional[MarketRegime]:
        """Obtém regime secundário."""
        active_scores = {
            k: v for k, v in scores.items()
            if k not in [MarketRegime.UNKNOWN, primary] and v > 0.3
        }
        
        if not active_scores:
            return None
        
        return max(active_scores, key=active_scores.get)
    
    def _calculate_regime_strength(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, float],
        regime: MarketRegime
    ) -> float:
        """Calcula força do regime."""
        if regime == MarketRegime.UNKNOWN:
            return 0.0
        
        strength = 0.5
        
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            # Força baseada em ADX
            adx = indicators['adx']
            if adx >= self.adx_strong_trend:
                strength = 0.9
            elif adx >= self.adx_trend_threshold:
                strength = 0.6 + (adx - self.adx_trend_threshold) / 30
        
        elif regime == MarketRegime.RANGING:
            # Força baseada em consistência do range
            if indicators['in_range']:
                strength = 0.8
        
        elif regime == MarketRegime.VOLATILE:
            vol_ratio = indicators['volatility_ratio']
            strength = min(vol_ratio / 2, 1.0)
        
        return min(max(strength, 0.0), 1.0)
    
    def _estimate_transition_probability(
        self,
        indicators: Dict[str, float],
        regime: MarketRegime
    ) -> float:
        """Estima probabilidade de mudança de regime."""
        prob = 0.2  # Base
        
        # Regime trending com ADX enfraquecendo
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if indicators['adx'] < self.adx_trend_threshold:
                prob += 0.3
            
            # RSI extremo indica possível reversão
            rsi = indicators['rsi']
            if rsi > 70 or rsi < 30:
                prob += 0.2
        
        # Ranging com volume aumentando
        elif regime == MarketRegime.RANGING:
            if indicators['volume_ratio'] > 1.5:
                prob += 0.3
            if indicators.get('near_breakout_high') or indicators.get('near_breakout_low'):
                prob += 0.2
        
        # Volatilidade tendendo a reverter à média
        elif regime == MarketRegime.VOLATILE:
            if indicators['volatility_ratio'] > 2.0:
                prob += 0.4  # Volatilidade extrema geralmente não dura
        
        return min(prob, 0.9)
    
    def _determine_bias(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, float],
        regime: MarketRegime
    ) -> str:
        """Determina bias recomendado."""
        
        if regime == MarketRegime.TRENDING_UP:
            return 'LONG'
        
        elif regime == MarketRegime.TRENDING_DOWN:
            return 'SHORT'
        
        elif regime == MarketRegime.REVERSAL:
            rsi = indicators['rsi']
            if rsi >= self.rsi_overbought:
                return 'SHORT'
            elif rsi <= self.rsi_oversold:
                return 'LONG'
        
        elif regime == MarketRegime.BREAKOUT:
            if indicators.get('near_breakout_high'):
                return 'LONG'
            elif indicators.get('near_breakout_low'):
                return 'SHORT'
        
        return 'NEUTRAL'
    
    def _unknown_result(self) -> RegimeAnalysisResult:
        """Retorna resultado desconhecido."""
        return RegimeAnalysisResult(
            current_regime=MarketRegime.UNKNOWN,
            confidence=0.3,
            parameters=REGIME_PARAMS[MarketRegime.UNKNOWN],
            secondary_regime=None,
            regime_strength=0.0,
            transition_probability=0.5,
            recommended_bias='NEUTRAL',
            details={},
        )
    
    def get_risk_multiplier(self, df: pd.DataFrame) -> float:
        """
        Obtém multiplicador de risco baseado no regime.
        
        Returns:
            Float entre 0 e 1.5
        """
        result = self.analyze(df)
        return result.parameters.risk_multiplier * result.confidence
    
    def should_trade(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Verifica se deve operar baseado no regime.
        
        Returns:
            (should_trade, reason)
        """
        result = self.analyze(df)
        
        if result.current_regime == MarketRegime.UNKNOWN:
            return False, "Regime desconhecido"
        
        if result.confidence < 0.5:
            return False, f"Baixa confiança no regime ({result.confidence:.0%})"
        
        if result.transition_probability > 0.7:
            return False, "Alta probabilidade de mudança de regime"
        
        if result.parameters.risk_multiplier < 0.4:
            return False, f"Regime {result.current_regime.name} não recomendado para trading"
        
        return True, f"OK - Regime {result.current_regime.name}"
    
    def to_dict(self, result: RegimeAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        return {
            'regime': result.current_regime.name,
            'confidence': round(result.confidence, 2),
            'strength': round(result.regime_strength, 2),
            'secondary_regime': result.secondary_regime.name if result.secondary_regime else None,
            'transition_probability': round(result.transition_probability, 2),
            'bias': result.recommended_bias,
            'parameters': {
                'risk_multiplier': result.parameters.risk_multiplier,
                'position_size_mult': result.parameters.position_size_mult,
                'max_trades': result.parameters.max_trades,
                'sl_atr_mult': result.parameters.sl_atr_mult,
                'tp_atr_mult': result.parameters.tp_atr_mult,
                'trailing_enabled': result.parameters.trailing_enabled,
                'preferred_tf': result.parameters.preferred_tf,
                'strategies': result.parameters.strategies,
                'avoid': result.parameters.avoid_strategies,
            },
            'details': result.details,
        }
