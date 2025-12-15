"""
VIRTUS Multi-Timeframe Analysis
================================

Análise de múltiplos timeframes para confluência de sinais.
Combina análises de diferentes períodos para aumentar assertividade.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class TimeframeBias(Enum):
    """Viés do timeframe."""
    STRONG_BULLISH = auto()
    BULLISH = auto()
    NEUTRAL = auto()
    BEARISH = auto()
    STRONG_BEARISH = auto()


class SignalStrength(Enum):
    """Força do sinal."""
    VERY_STRONG = auto()
    STRONG = auto()
    MODERATE = auto()
    WEAK = auto()
    NONE = auto()


@dataclass
class TimeframeAnalysis:
    """Análise de um timeframe específico."""
    timeframe: str
    bias: TimeframeBias
    trend: str  # 'up', 'down', 'sideways'
    momentum: float  # -1 a +1
    volatility: float  # normalizada
    key_levels: List[float]
    ema_alignment: bool  # EMAs alinhadas na direção
    rsi: float
    macd_signal: str  # 'bullish', 'bearish', 'neutral'


@dataclass
class MTFConfluence:
    """Confluência entre múltiplos timeframes."""
    overall_bias: TimeframeBias
    signal_strength: SignalStrength
    confluence_score: float  # 0 a 1
    aligned_timeframes: List[str]
    conflicting_timeframes: List[str]
    dominant_trend: str
    entry_permission: bool  # Se pode entrar na direção
    optimal_direction: str  # 'long', 'short', 'none'
    notes: List[str]


@dataclass
class MTFAnalysisResult:
    """Resultado completo da análise MTF."""
    analyses: Dict[str, TimeframeAnalysis]
    confluence: MTFConfluence
    timestamp: datetime = field(default_factory=datetime.now)


class MultiTimeframeAnalyzer:
    """
    Analisador Multi-Timeframe (MTF).
    
    Combina análises de diferentes timeframes para:
    - Identificar tendência dominante
    - Encontrar confluência de sinais
    - Determinar força do setup
    - Validar entradas
    """
    
    # Hierarquia de timeframes (menor para maior)
    TIMEFRAME_HIERARCHY = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']
    
    # Pesos por timeframe (maior = mais influência)
    TIMEFRAME_WEIGHTS = {
        'M1': 0.05,
        'M5': 0.10,
        'M15': 0.15,
        'M30': 0.15,
        'H1': 0.20,
        'H4': 0.15,
        'D1': 0.15,
        'W1': 0.05,
    }
    
    def __init__(
        self,
        ema_fast: int = 21,
        ema_slow: int = 50,
        ema_trend: int = 200,
        rsi_period: int = 14,
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.ema_trend = ema_trend
        self.rsi_period = rsi_period
    
    def analyze(
        self,
        data_by_timeframe: Dict[str, pd.DataFrame],
    ) -> MTFAnalysisResult:
        """
        Análise completa de múltiplos timeframes.
        
        Args:
            data_by_timeframe: Dicionário {timeframe: DataFrame}
            
        Returns:
            MTFAnalysisResult com análise completa
        """
        analyses = {}
        
        # Analisa cada timeframe
        for tf, df in data_by_timeframe.items():
            if df is not None and len(df) >= self.ema_trend:
                analyses[tf] = self._analyze_timeframe(df, tf)
        
        # Calcula confluência
        confluence = self._calculate_confluence(analyses)
        
        return MTFAnalysisResult(
            analyses=analyses,
            confluence=confluence,
        )
    
    def _analyze_timeframe(self, df: pd.DataFrame, timeframe: str) -> TimeframeAnalysis:
        """Analisa um timeframe específico."""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        # EMAs
        ema_fast = self._ema(close, self.ema_fast)
        ema_slow = self._ema(close, self.ema_slow)
        ema_trend = self._ema(close, self.ema_trend)
        
        # Tendência
        trend = self._determine_trend(close, ema_fast, ema_slow, ema_trend)
        
        # Bias
        bias = self._determine_bias(close, ema_fast, ema_slow, ema_trend)
        
        # Momentum (-1 a +1)
        momentum = self._calculate_momentum(close, ema_fast, ema_slow)
        
        # Volatilidade
        volatility = self._calculate_volatility(high, low, close)
        
        # Níveis chave
        key_levels = self._find_key_levels(high, low, close)
        
        # Alinhamento de EMAs
        ema_alignment = self._check_ema_alignment(
            close[-1], ema_fast[-1], ema_slow[-1], ema_trend[-1], trend
        )
        
        # RSI
        rsi = self._calculate_rsi(close, self.rsi_period)
        
        # MACD Signal
        macd_signal = self._calculate_macd_signal(close)
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            bias=bias,
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            key_levels=key_levels,
            ema_alignment=ema_alignment,
            rsi=rsi,
            macd_signal=macd_signal,
        )
    
    def _determine_trend(
        self,
        close: np.ndarray,
        ema_fast: np.ndarray,
        ema_slow: np.ndarray,
        ema_trend: np.ndarray,
    ) -> str:
        """Determina a tendência."""
        current_close = close[-1]
        
        # Verifica posição em relação às EMAs
        above_fast = current_close > ema_fast[-1]
        above_slow = current_close > ema_slow[-1]
        above_trend = current_close > ema_trend[-1]
        
        # Verifica ordenação das EMAs
        emas_bullish = ema_fast[-1] > ema_slow[-1] > ema_trend[-1]
        emas_bearish = ema_fast[-1] < ema_slow[-1] < ema_trend[-1]
        
        if emas_bullish and above_fast:
            return 'up'
        elif emas_bearish and not above_fast:
            return 'down'
        else:
            return 'sideways'
    
    def _determine_bias(
        self,
        close: np.ndarray,
        ema_fast: np.ndarray,
        ema_slow: np.ndarray,
        ema_trend: np.ndarray,
    ) -> TimeframeBias:
        """Determina o viés do timeframe."""
        current_close = close[-1]
        
        # Scores
        score = 0
        
        # Posição relativa às EMAs
        if current_close > ema_fast[-1]:
            score += 1
        elif current_close < ema_fast[-1]:
            score -= 1
        
        if current_close > ema_slow[-1]:
            score += 1
        elif current_close < ema_slow[-1]:
            score -= 1
        
        if current_close > ema_trend[-1]:
            score += 1
        elif current_close < ema_trend[-1]:
            score -= 1
        
        # Ordenação das EMAs
        if ema_fast[-1] > ema_slow[-1] > ema_trend[-1]:
            score += 2
        elif ema_fast[-1] < ema_slow[-1] < ema_trend[-1]:
            score -= 2
        
        # Momentum das EMAs
        if ema_fast[-1] > ema_fast[-5]:
            score += 1
        elif ema_fast[-1] < ema_fast[-5]:
            score -= 1
        
        # Converte score para bias
        if score >= 5:
            return TimeframeBias.STRONG_BULLISH
        elif score >= 2:
            return TimeframeBias.BULLISH
        elif score <= -5:
            return TimeframeBias.STRONG_BEARISH
        elif score <= -2:
            return TimeframeBias.BEARISH
        else:
            return TimeframeBias.NEUTRAL
    
    def _calculate_momentum(
        self,
        close: np.ndarray,
        ema_fast: np.ndarray,
        ema_slow: np.ndarray,
    ) -> float:
        """Calcula momentum normalizado (-1 a +1)."""
        # Distância do preço à EMA rápida
        price_ema_dist = (close[-1] - ema_fast[-1]) / ema_fast[-1] * 100
        
        # Distância entre EMAs
        ema_dist = (ema_fast[-1] - ema_slow[-1]) / ema_slow[-1] * 100
        
        # Rate of change
        roc = (close[-1] - close[-10]) / close[-10] * 100 if len(close) >= 10 else 0
        
        # Combina
        momentum = (price_ema_dist * 0.3 + ema_dist * 0.4 + roc * 0.3)
        
        # Normaliza para -1 a +1
        return max(-1, min(1, momentum / 5))
    
    def _calculate_volatility(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> float:
        """Calcula volatilidade normalizada."""
        # ATR
        tr_values = []
        for i in range(1, len(close)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
            tr_values.append(tr)
        
        atr = np.mean(tr_values[-14:]) if len(tr_values) >= 14 else 0
        
        # Normaliza em relação ao preço
        return atr / close[-1] * 100 if close[-1] > 0 else 0
    
    def _find_key_levels(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> List[float]:
        """Encontra níveis chave."""
        levels = []
        
        # Recent high/low
        levels.append(max(high[-20:]))
        levels.append(min(low[-20:]))
        
        # Pivot points
        typical_price = (high[-1] + low[-1] + close[-1]) / 3
        levels.append(typical_price)
        
        # Suporte e resistência baseados em toques
        # (Simplificado - em produção seria mais sofisticado)
        return sorted(set(levels))
    
    def _check_ema_alignment(
        self,
        price: float,
        ema_fast: float,
        ema_slow: float,
        ema_trend: float,
        trend: str,
    ) -> bool:
        """Verifica se EMAs estão alinhadas."""
        if trend == 'up':
            return price > ema_fast > ema_slow > ema_trend
        elif trend == 'down':
            return price < ema_fast < ema_slow < ema_trend
        return False
    
    def _calculate_rsi(self, close: np.ndarray, period: int) -> float:
        """Calcula RSI."""
        if len(close) < period + 1:
            return 50.0
        
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd_signal(self, close: np.ndarray) -> str:
        """Calcula sinal do MACD."""
        ema_12 = self._ema(close, 12)
        ema_26 = self._ema(close, 26)
        
        macd_line = ema_12 - ema_26
        signal_line = self._ema(macd_line, 9)
        
        if macd_line[-1] > signal_line[-1]:
            if macd_line[-2] <= signal_line[-2]:
                return 'bullish_cross'
            return 'bullish'
        elif macd_line[-1] < signal_line[-1]:
            if macd_line[-2] >= signal_line[-2]:
                return 'bearish_cross'
            return 'bearish'
        return 'neutral'
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calcula EMA."""
        ema = np.zeros_like(data)
        multiplier = 2 / (period + 1)
        
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        
        return ema
    
    def _calculate_confluence(
        self,
        analyses: Dict[str, TimeframeAnalysis],
    ) -> MTFConfluence:
        """Calcula confluência entre timeframes."""
        if not analyses:
            return self._empty_confluence()
        
        # Conta vieses
        bullish_count = 0
        bearish_count = 0
        aligned = []
        conflicting = []
        
        weighted_score = 0
        total_weight = 0
        
        for tf, analysis in analyses.items():
            weight = self.TIMEFRAME_WEIGHTS.get(tf, 0.1)
            total_weight += weight
            
            if analysis.bias in [TimeframeBias.STRONG_BULLISH, TimeframeBias.BULLISH]:
                bullish_count += 1
                weighted_score += weight
            elif analysis.bias in [TimeframeBias.STRONG_BEARISH, TimeframeBias.BEARISH]:
                bearish_count += 1
                weighted_score -= weight
        
        # Normaliza score
        if total_weight > 0:
            weighted_score /= total_weight
        
        # Determina viés geral
        if weighted_score >= 0.6:
            overall_bias = TimeframeBias.STRONG_BULLISH
            dominant_trend = 'up'
        elif weighted_score >= 0.3:
            overall_bias = TimeframeBias.BULLISH
            dominant_trend = 'up'
        elif weighted_score <= -0.6:
            overall_bias = TimeframeBias.STRONG_BEARISH
            dominant_trend = 'down'
        elif weighted_score <= -0.3:
            overall_bias = TimeframeBias.BEARISH
            dominant_trend = 'down'
        else:
            overall_bias = TimeframeBias.NEUTRAL
            dominant_trend = 'sideways'
        
        # Identifica TFs alinhados e conflitantes
        for tf, analysis in analyses.items():
            if dominant_trend == 'up' and analysis.trend == 'up':
                aligned.append(tf)
            elif dominant_trend == 'down' and analysis.trend == 'down':
                aligned.append(tf)
            elif dominant_trend == 'sideways' and analysis.trend == 'sideways':
                aligned.append(tf)
            else:
                conflicting.append(tf)
        
        # Calcula confluência score
        total_tf = len(analyses)
        confluence_score = len(aligned) / total_tf if total_tf > 0 else 0
        
        # Determina força do sinal
        if confluence_score >= 0.8:
            signal_strength = SignalStrength.VERY_STRONG
        elif confluence_score >= 0.6:
            signal_strength = SignalStrength.STRONG
        elif confluence_score >= 0.4:
            signal_strength = SignalStrength.MODERATE
        elif confluence_score >= 0.2:
            signal_strength = SignalStrength.WEAK
        else:
            signal_strength = SignalStrength.NONE
        
        # Permissão de entrada
        entry_permission = (
            confluence_score >= 0.5 and
            overall_bias != TimeframeBias.NEUTRAL and
            signal_strength in [SignalStrength.VERY_STRONG, SignalStrength.STRONG]
        )
        
        # Direção ótima
        if entry_permission:
            if overall_bias in [TimeframeBias.STRONG_BULLISH, TimeframeBias.BULLISH]:
                optimal_direction = 'long'
            elif overall_bias in [TimeframeBias.STRONG_BEARISH, TimeframeBias.BEARISH]:
                optimal_direction = 'short'
            else:
                optimal_direction = 'none'
        else:
            optimal_direction = 'none'
        
        # Notas
        notes = []
        if confluence_score >= 0.8:
            notes.append("Alta confluência entre timeframes")
        if len(conflicting) > len(aligned):
            notes.append("Atenção: Timeframes conflitantes")
        if 'H4' in aligned and 'D1' in aligned:
            notes.append("Timeframes superiores alinhados - setup mais confiável")
        if 'M5' in conflicting or 'M15' in conflicting:
            notes.append("Timeframes inferiores divergentes - aguardar alinhamento")
        
        return MTFConfluence(
            overall_bias=overall_bias,
            signal_strength=signal_strength,
            confluence_score=confluence_score,
            aligned_timeframes=aligned,
            conflicting_timeframes=conflicting,
            dominant_trend=dominant_trend,
            entry_permission=entry_permission,
            optimal_direction=optimal_direction,
            notes=notes,
        )
    
    def _empty_confluence(self) -> MTFConfluence:
        """Retorna confluência vazia."""
        return MTFConfluence(
            overall_bias=TimeframeBias.NEUTRAL,
            signal_strength=SignalStrength.NONE,
            confluence_score=0.0,
            aligned_timeframes=[],
            conflicting_timeframes=[],
            dominant_trend='sideways',
            entry_permission=False,
            optimal_direction='none',
            notes=['Dados insuficientes para análise'],
        )
    
    def to_dict(self, result: MTFAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        analyses_dict = {}
        for tf, analysis in result.analyses.items():
            analyses_dict[tf] = {
                'bias': analysis.bias.name,
                'trend': analysis.trend,
                'momentum': round(analysis.momentum, 3),
                'volatility': round(analysis.volatility, 4),
                'ema_alignment': analysis.ema_alignment,
                'rsi': round(analysis.rsi, 2),
                'macd_signal': analysis.macd_signal,
            }
        
        return {
            'analyses': analyses_dict,
            'confluence': {
                'overall_bias': result.confluence.overall_bias.name,
                'signal_strength': result.confluence.signal_strength.name,
                'confluence_score': round(result.confluence.confluence_score, 3),
                'aligned_timeframes': result.confluence.aligned_timeframes,
                'conflicting_timeframes': result.confluence.conflicting_timeframes,
                'dominant_trend': result.confluence.dominant_trend,
                'entry_permission': result.confluence.entry_permission,
                'optimal_direction': result.confluence.optimal_direction,
                'notes': result.confluence.notes,
            },
            'timestamp': result.timestamp.isoformat(),
        }
