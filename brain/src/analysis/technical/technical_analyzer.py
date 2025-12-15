"""
VIRTUS Technical Analysis - MAGISTRAL Edition
===============================================

Sistema avançado de análise técnica com:
- Multi-timeframe analysis (MTF)
- Detecção de divergências (RSI, MACD, Stochastic)
- Confluência de indicadores com scoring
- Thresholds adaptativos por volatilidade
- Cache inteligente para performance
- Qualidade de sinais com métricas
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import deque
import hashlib


class TrendDirection(Enum):
    """Direção da tendência com propriedades estendidas."""
    STRONG_UP = auto()
    UP = auto()
    NEUTRAL = auto()
    DOWN = auto()
    STRONG_DOWN = auto()
    
    @property
    def is_bullish(self) -> bool:
        return self in (TrendDirection.STRONG_UP, TrendDirection.UP)
    
    @property
    def is_bearish(self) -> bool:
        return self in (TrendDirection.STRONG_DOWN, TrendDirection.DOWN)
    
    @property
    def strength_value(self) -> int:
        """Valor numérico: -2 (STRONG_DOWN) a +2 (STRONG_UP)."""
        mapping = {
            TrendDirection.STRONG_UP: 2,
            TrendDirection.UP: 1,
            TrendDirection.NEUTRAL: 0,
            TrendDirection.DOWN: -1,
            TrendDirection.STRONG_DOWN: -2,
        }
        return mapping[self]


class SignalStrength(Enum):
    """Força do sinal com confiança associada."""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4
    
    @property
    def confidence(self) -> float:
        """Confiança associada à força (0.0-1.0)."""
        mapping = {
            SignalStrength.WEAK: 0.4,
            SignalStrength.MODERATE: 0.6,
            SignalStrength.STRONG: 0.8,
            SignalStrength.VERY_STRONG: 0.95,
        }
        return mapping[self]


class DivergenceType(Enum):
    """Tipos de divergência técnica."""
    REGULAR_BULLISH = "regular_bullish"   # Price lower low, indicator higher low
    REGULAR_BEARISH = "regular_bearish"   # Price higher high, indicator lower high
    HIDDEN_BULLISH = "hidden_bullish"     # Price higher low, indicator lower low
    HIDDEN_BEARISH = "hidden_bearish"     # Price lower high, indicator higher high
    NONE = "none"
    
    @property
    def is_bullish(self) -> bool:
        return self in (DivergenceType.REGULAR_BULLISH, DivergenceType.HIDDEN_BULLISH)
    
    @property
    def is_reversal(self) -> bool:
        """Regular divergences indicate reversal."""
        return self in (DivergenceType.REGULAR_BULLISH, DivergenceType.REGULAR_BEARISH)


class VolatilityState(Enum):
    """Estado de volatilidade do mercado."""
    COMPRESSION = "compression"   # Bollinger squeeze - breakout iminente
    EXPANSION = "expansion"       # Alta volatilidade
    NORMAL = "normal"


class MTFAlignment(Enum):
    """Alinhamento de múltiplos timeframes."""
    FULL_BULLISH = "full_bullish"
    PARTIAL_BULLISH = "partial_bullish"
    NEUTRAL = "neutral"
    PARTIAL_BEARISH = "partial_bearish"
    FULL_BEARISH = "full_bearish"
    
    @property
    def confluence_score(self) -> float:
        """Score de confluência MTF (0.0-1.0)."""
        mapping = {
            MTFAlignment.FULL_BULLISH: 1.0,
            MTFAlignment.PARTIAL_BULLISH: 0.7,
            MTFAlignment.NEUTRAL: 0.5,
            MTFAlignment.PARTIAL_BEARISH: 0.3,
            MTFAlignment.FULL_BEARISH: 0.0,
        }
        return mapping[self]


@dataclass
class TechnicalSignal:
    """Sinal técnico com metadados estendidos."""
    indicator: str
    signal_type: str  # buy, sell, neutral
    strength: SignalStrength
    value: float
    threshold: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_actionable(self) -> bool:
        """Sinal é acionável (não neutro e tem força mínima)."""
        return self.signal_type != 'neutral' and self.strength.value >= SignalStrength.MODERATE.value


@dataclass
class Divergence:
    """Divergência detectada entre preço e indicador."""
    type: DivergenceType
    indicator: str
    price_swing_1: Tuple[int, float]    # (index, value)
    price_swing_2: Tuple[int, float]
    indicator_swing_1: Tuple[int, float]
    indicator_swing_2: Tuple[int, float]
    strength: float  # 0.0-1.0 based on divergence magnitude
    
    @property
    def is_valid(self) -> bool:
        return self.type != DivergenceType.NONE and self.strength > 0.3


@dataclass
class ConfluenceResult:
    """Resultado de análise de confluência."""
    total_signals: int
    bullish_signals: int
    bearish_signals: int
    neutral_signals: int
    confluence_score: float  # -1.0 (full bearish) to +1.0 (full bullish)
    aligned_indicators: List[str]
    conflicting_indicators: List[str]
    quality: str  # 'high', 'medium', 'low'


@dataclass
class MarketStructure:
    """Estrutura de mercado com análise completa."""
    trend: TrendDirection
    support_levels: List[float]
    resistance_levels: List[float]
    key_levels: List[float]
    swing_highs: List[Tuple[int, float]]
    swing_lows: List[Tuple[int, float]]
    higher_highs: bool = False
    higher_lows: bool = False
    lower_highs: bool = False
    lower_lows: bool = False
    volatility_state: VolatilityState = VolatilityState.NORMAL
    divergences: List['Divergence'] = field(default_factory=list)


@dataclass
class AnalysisCache:
    """Cache para resultados de análise."""
    data_hash: str
    timestamp: datetime
    result: Dict[str, Any]
    ttl_seconds: int = 60


class TechnicalAnalyzer:
    """
    Analisador Técnico MAGISTRAL - Sistema avançado de análise técnica.
    
    Features:
    - Multi-timeframe analysis com alinhamento
    - Detecção de divergências (RSI, MACD, Stochastic)
    - Confluência de indicadores com scoring
    - Thresholds adaptativos baseados em volatilidade
    - Cache inteligente para performance
    - Histórico de análises para estatísticas
    """
    
    # Pesos dos indicadores por categoria
    INDICATOR_WEIGHTS = {
        'trend': {'ema': 0.3, 'macd': 0.4, 'adx': 0.3},
        'momentum': {'rsi': 0.35, 'stochastic': 0.25, 'cci': 0.2, 'williams': 0.2},
        'volatility': {'bb': 0.4, 'atr': 0.3, 'keltner': 0.3},
    }
    
    # Thresholds base (ajustados por volatilidade)
    BASE_THRESHOLDS = {
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'stoch_overbought': 80,
        'stoch_oversold': 20,
        'adx_trending': 25,
        'cci_overbought': 100,
        'cci_oversold': -100,
    }
    
    def __init__(self, enable_cache: bool = True, cache_ttl: int = 60):
        """
        Inicializa o analisador técnico.
        
        Args:
            enable_cache: Ativar cache de resultados
            cache_ttl: Time-to-live do cache em segundos
        """
        self._cache: Dict[str, AnalysisCache] = {}
        self._enable_cache = enable_cache
        self._cache_ttl = cache_ttl
        
        # Histórico de análises para estatísticas
        self._analysis_history: deque = deque(maxlen=100)
        
        # Thresholds adaptativos (podem ser ajustados por volatilidade)
        self._adaptive_thresholds = self.BASE_THRESHOLDS.copy()
        
        # Callbacks para eventos
        self._event_callbacks: List[Callable] = []
        
        # Estatísticas
        self._stats = {
            'total_analyses': 0,
            'cache_hits': 0,
            'divergences_detected': 0,
            'strong_signals_generated': 0,
        }
    
    def _get_data_hash(self, df: pd.DataFrame) -> str:
        """Gera hash único para o DataFrame."""
        key = f"{len(df)}_{df.iloc[-1]['close']}_{df.iloc[-1].name}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _get_cached_result(self, data_hash: str) -> Optional[Dict[str, Any]]:
        """Retorna resultado do cache se válido."""
        if not self._enable_cache or data_hash not in self._cache:
            return None
        
        cached = self._cache[data_hash]
        if (datetime.now() - cached.timestamp).total_seconds() < cached.ttl_seconds:
            self._stats['cache_hits'] += 1
            return cached.result
        
        del self._cache[data_hash]
        return None
    
    def _cache_result(self, data_hash: str, result: Dict[str, Any]) -> None:
        """Armazena resultado no cache."""
        if self._enable_cache:
            self._cache[data_hash] = AnalysisCache(
                data_hash=data_hash,
                timestamp=datetime.now(),
                result=result,
                ttl_seconds=self._cache_ttl,
            )
    
    def analyze(self, df: pd.DataFrame, use_cache: bool = True) -> Dict[str, Any]:
        """
        Análise técnica completa MAGISTRAL.
        
        Args:
            df: DataFrame com OHLCV (open, high, low, close, volume)
            use_cache: Usar cache de resultados
            
        Returns:
            Dicionário com todos os indicadores e sinais
        """
        if df is None or len(df) < 50:
            return {}
        
        # Verificar cache
        data_hash = self._get_data_hash(df)
        if use_cache:
            cached = self._get_cached_result(data_hash)
            if cached:
                return cached
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'candles': len(df),
        }
        
        # Garante que temos as colunas necessárias
        required = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required):
            return result
        
        # Adaptar thresholds baseado em volatilidade atual
        self._update_adaptive_thresholds(df)
        
        # Indicadores de tendência
        result['trend'] = self._analyze_trend(df)
        
        # Indicadores de momentum
        result['momentum'] = self._analyze_momentum(df)
        
        # Indicadores de volatilidade
        result['volatility'] = self._analyze_volatility(df)
        
        # Estrutura de mercado
        result['structure'] = self._analyze_structure(df)
        
        # === NOVAS ANÁLISES MAGISTRAIS ===
        
        # Detecção de divergências
        result['divergences'] = self._detect_all_divergences(df, result)
        
        # Confluência de indicadores
        result['confluence'] = self._analyze_confluence(result)
        
        # Sinais combinados
        result['signals'] = self._generate_signals(result)
        
        # Score geral (-100 a +100)
        result['score'] = self._calculate_score(result)
        
        # Qualidade do sinal
        result['signal_quality'] = self._assess_signal_quality(result)
        
        # Armazenar no cache e histórico
        self._cache_result(data_hash, result)
        self._analysis_history.append({
            'timestamp': datetime.now(),
            'score': result['score'],
            'quality': result['signal_quality'],
        })
        self._stats['total_analyses'] += 1
        
        return result
    
    def _update_adaptive_thresholds(self, df: pd.DataFrame) -> None:
        """Atualiza thresholds baseado na volatilidade atual."""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        atr = self._atr(high, low, close, 14)
        avg_price = close[-1]
        atr_percent = (atr / avg_price) * 100 if avg_price > 0 else 1
        
        # Em alta volatilidade, expandir thresholds
        if atr_percent > 2.0:  # High volatility
            vol_factor = 1.15
        elif atr_percent < 0.5:  # Low volatility
            vol_factor = 0.85
        else:
            vol_factor = 1.0
        
        # Ajustar thresholds de RSI
        self._adaptive_thresholds['rsi_overbought'] = min(85, int(70 * vol_factor))
        self._adaptive_thresholds['rsi_oversold'] = max(15, int(30 / vol_factor))
        
        # Ajustar thresholds de Stochastic
        self._adaptive_thresholds['stoch_overbought'] = min(90, int(80 * vol_factor))
        self._adaptive_thresholds['stoch_oversold'] = max(10, int(20 / vol_factor))
    
    def _analyze_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analisa indicadores de tendência."""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        result = {}
        
        # EMAs
        result['ema_20'] = self._ema(close, 20)
        result['ema_50'] = self._ema(close, 50)
        result['ema_200'] = self._ema(close, 200) if len(close) >= 200 else None
        
        # SMA
        result['sma_20'] = self._sma(close, 20)
        result['sma_50'] = self._sma(close, 50)
        
        # MACD
        macd, signal, hist = self._macd(close)
        result['macd'] = {
            'macd': macd,
            'signal': signal,
            'histogram': hist,
            'crossover': self._detect_crossover(macd, signal),
        }
        
        # ADX
        result['adx'] = self._adx(high, low, close, 14)
        
        # Direção da tendência
        result['direction'] = self._determine_trend_direction(result)
        
        return result
    
    def _analyze_momentum(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analisa indicadores de momentum."""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        result = {}
        
        # RSI
        result['rsi'] = self._rsi(close, 14)
        result['rsi_signal'] = self._rsi_signal(result['rsi'])
        
        # Stochastic
        k, d = self._stochastic(high, low, close, 14, 3)
        result['stochastic'] = {
            'k': k,
            'd': d,
            'signal': self._stochastic_signal(k, d),
        }
        
        # CCI
        result['cci'] = self._cci(high, low, close, 20)
        
        # Williams %R
        result['williams_r'] = self._williams_r(high, low, close, 14)
        
        return result
    
    def _analyze_volatility(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analisa indicadores de volatilidade."""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        result = {}
        
        # ATR
        result['atr'] = self._atr(high, low, close, 14)
        result['atr_percent'] = (result['atr'] / close[-1]) * 100 if close[-1] > 0 else 0
        
        # Bollinger Bands
        upper, middle, lower = self._bollinger_bands(close, 20, 2)
        result['bollinger'] = {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'width': (upper - lower) / middle * 100 if middle > 0 else 0,
            'position': self._bb_position(close[-1], upper, lower),
        }
        
        # Keltner Channels
        result['keltner'] = self._keltner_channels(high, low, close, 20, 2)
        
        return result
    
    def _analyze_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analisa estrutura de mercado (price action)."""
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        result = {}
        
        # Swing highs e lows
        swing_highs = self._find_swing_highs(high, 5)
        swing_lows = self._find_swing_lows(low, 5)
        
        result['swing_highs'] = swing_highs[-5:] if swing_highs else []
        result['swing_lows'] = swing_lows[-5:] if swing_lows else []
        
        # Suportes e resistências
        result['supports'] = self._find_support_levels(low, swing_lows)
        result['resistances'] = self._find_resistance_levels(high, swing_highs)
        
        # Estrutura HH/HL ou LH/LL
        result['higher_highs'] = self._check_higher_highs(swing_highs)
        result['higher_lows'] = self._check_higher_lows(swing_lows)
        result['lower_highs'] = self._check_lower_highs(swing_highs)
        result['lower_lows'] = self._check_lower_lows(swing_lows)
        
        # Padrões de candle
        result['patterns'] = self._identify_patterns(df)
        
        return result
    
    def _generate_signals(self, analysis: Dict[str, Any]) -> List[TechnicalSignal]:
        """Gera lista de sinais técnicos."""
        signals = []
        
        # RSI signals
        momentum = analysis.get('momentum', {})
        rsi = momentum.get('rsi')
        if rsi is not None:
            if rsi < 30:
                signals.append(TechnicalSignal(
                    indicator='RSI',
                    signal_type='buy',
                    strength=SignalStrength.STRONG if rsi < 20 else SignalStrength.MODERATE,
                    value=rsi,
                    threshold=30,
                ))
            elif rsi > 70:
                signals.append(TechnicalSignal(
                    indicator='RSI',
                    signal_type='sell',
                    strength=SignalStrength.STRONG if rsi > 80 else SignalStrength.MODERATE,
                    value=rsi,
                    threshold=70,
                ))
        
        # MACD signals
        trend = analysis.get('trend', {})
        macd_data = trend.get('macd', {})
        if macd_data.get('crossover') == 'bullish':
            signals.append(TechnicalSignal(
                indicator='MACD',
                signal_type='buy',
                strength=SignalStrength.MODERATE,
                value=macd_data.get('histogram', 0),
            ))
        elif macd_data.get('crossover') == 'bearish':
            signals.append(TechnicalSignal(
                indicator='MACD',
                signal_type='sell',
                strength=SignalStrength.MODERATE,
                value=macd_data.get('histogram', 0),
            ))
        
        # Stochastic signals
        stoch = momentum.get('stochastic', {})
        if stoch.get('signal') == 'oversold':
            signals.append(TechnicalSignal(
                indicator='Stochastic',
                signal_type='buy',
                strength=SignalStrength.MODERATE,
                value=stoch.get('k', 0),
                threshold=20,
            ))
        elif stoch.get('signal') == 'overbought':
            signals.append(TechnicalSignal(
                indicator='Stochastic',
                signal_type='sell',
                strength=SignalStrength.MODERATE,
                value=stoch.get('k', 0),
                threshold=80,
            ))
        
        # Bollinger Band signals
        volatility = analysis.get('volatility', {})
        bb_position = volatility.get('bollinger', {}).get('position')
        if bb_position == 'below_lower':
            signals.append(TechnicalSignal(
                indicator='Bollinger',
                signal_type='buy',
                strength=SignalStrength.WEAK,
                value=0,
            ))
        elif bb_position == 'above_upper':
            signals.append(TechnicalSignal(
                indicator='Bollinger',
                signal_type='sell',
                strength=SignalStrength.WEAK,
                value=0,
            ))
        
        return signals
    
    def _calculate_score(self, analysis: Dict[str, Any]) -> float:
        """
        Calcula score consolidado (-100 a +100).
        
        Positivo = bullish, Negativo = bearish
        """
        score = 0.0
        weights = {
            'trend': 40,
            'momentum': 35,
            'structure': 25,
        }
        
        # Score de tendência
        trend = analysis.get('trend', {})
        trend_direction = trend.get('direction')
        if trend_direction == TrendDirection.STRONG_UP:
            score += weights['trend']
        elif trend_direction == TrendDirection.UP:
            score += weights['trend'] * 0.5
        elif trend_direction == TrendDirection.STRONG_DOWN:
            score -= weights['trend']
        elif trend_direction == TrendDirection.DOWN:
            score -= weights['trend'] * 0.5
        
        # Score de momentum
        momentum = analysis.get('momentum', {})
        rsi = momentum.get('rsi', 50)
        rsi_score = (rsi - 50) / 50 * weights['momentum']
        score += rsi_score
        
        # Score de estrutura
        structure = analysis.get('structure', {})
        if structure.get('higher_highs') and structure.get('higher_lows'):
            score += weights['structure']
        elif structure.get('lower_highs') and structure.get('lower_lows'):
            score -= weights['structure']
        
        return max(-100, min(100, score))
    
    # === ANÁLISES MAGISTRAIS ===
    
    def _detect_all_divergences(
        self, 
        df: pd.DataFrame, 
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detecta todas as divergências entre preço e indicadores.
        
        Analisa:
        - RSI divergences (mais confiáveis)
        - MACD histogram divergences
        - Stochastic divergences
        """
        divergences = []
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        # RSI Divergences
        rsi_series = self._rsi_series(close, 14)
        rsi_divs = self._detect_divergence(low, high, rsi_series, 'RSI', lookback=20)
        divergences.extend(rsi_divs)
        
        # MACD Histogram Divergences
        _, _, histogram = self._macd_series(close, 12, 26, 9)
        if len(histogram) > 0:
            macd_divs = self._detect_divergence(low, high, histogram, 'MACD', lookback=20)
            divergences.extend(macd_divs)
        
        # Stochastic Divergences  
        k_series = self._stochastic_series(high, low, close, 14)
        stoch_divs = self._detect_divergence(low, high, k_series, 'Stochastic', lookback=20)
        divergences.extend(stoch_divs)
        
        # Atualizar estatísticas
        if divergences:
            self._stats['divergences_detected'] += len(divergences)
        
        return divergences
    
    def _detect_divergence(
        self,
        lows: np.ndarray,
        highs: np.ndarray,
        indicator: np.ndarray,
        indicator_name: str,
        lookback: int = 20
    ) -> List[Dict[str, Any]]:
        """Detecta divergências entre preço e indicador."""
        divergences = []
        
        if len(indicator) < lookback:
            return divergences
        
        # Últimos swings do preço
        price_swing_lows = self._find_swing_lows(lows[-lookback:], 3)
        price_swing_highs = self._find_swing_highs(highs[-lookback:], 3)
        
        # Swings do indicador
        ind_swing_lows = self._find_swing_lows(indicator[-lookback:], 3)
        ind_swing_highs = self._find_swing_highs(indicator[-lookback:], 3)
        
        # Regular Bullish: Price lower low, Indicator higher low
        if len(price_swing_lows) >= 2 and len(ind_swing_lows) >= 2:
            if (price_swing_lows[-1][1] < price_swing_lows[-2][1] and
                ind_swing_lows[-1][1] > ind_swing_lows[-2][1]):
                
                strength = abs(price_swing_lows[-2][1] - price_swing_lows[-1][1]) / lows[-1]
                divergences.append({
                    'type': DivergenceType.REGULAR_BULLISH.value,
                    'indicator': indicator_name,
                    'strength': min(1.0, strength * 100),
                    'signal': 'buy',
                })
        
        # Regular Bearish: Price higher high, Indicator lower high
        if len(price_swing_highs) >= 2 and len(ind_swing_highs) >= 2:
            if (price_swing_highs[-1][1] > price_swing_highs[-2][1] and
                ind_swing_highs[-1][1] < ind_swing_highs[-2][1]):
                
                strength = abs(price_swing_highs[-1][1] - price_swing_highs[-2][1]) / highs[-1]
                divergences.append({
                    'type': DivergenceType.REGULAR_BEARISH.value,
                    'indicator': indicator_name,
                    'strength': min(1.0, strength * 100),
                    'signal': 'sell',
                })
        
        # Hidden Bullish: Price higher low, Indicator lower low
        if len(price_swing_lows) >= 2 and len(ind_swing_lows) >= 2:
            if (price_swing_lows[-1][1] > price_swing_lows[-2][1] and
                ind_swing_lows[-1][1] < ind_swing_lows[-2][1]):
                
                divergences.append({
                    'type': DivergenceType.HIDDEN_BULLISH.value,
                    'indicator': indicator_name,
                    'strength': 0.6,  # Hidden divergences são menos fortes
                    'signal': 'buy',
                })
        
        # Hidden Bearish: Price lower high, Indicator higher high
        if len(price_swing_highs) >= 2 and len(ind_swing_highs) >= 2:
            if (price_swing_highs[-1][1] < price_swing_highs[-2][1] and
                ind_swing_highs[-1][1] > ind_swing_highs[-2][1]):
                
                divergences.append({
                    'type': DivergenceType.HIDDEN_BEARISH.value,
                    'indicator': indicator_name,
                    'strength': 0.6,
                    'signal': 'sell',
                })
        
        return divergences
    
    def _rsi_series(self, data: np.ndarray, period: int = 14) -> np.ndarray:
        """Calcula RSI como série temporal."""
        if len(data) < period + 1:
            return np.full(len(data), 50.0)
        
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        rsi = np.zeros(len(data))
        rsi[:period] = 50.0
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i + 1] = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _macd_series(
        self,
        data: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calcula MACD como série temporal."""
        if len(data) < slow:
            return np.array([]), np.array([]), np.array([])
        
        ema_fast = self._ema_series(data, fast)
        ema_slow = self._ema_series(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema_series(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _stochastic_series(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int = 14
    ) -> np.ndarray:
        """Calcula %K do Stochastic como série temporal."""
        k_series = np.zeros(len(close))
        
        for i in range(period, len(close)):
            highest = np.max(high[i-period:i])
            lowest = np.min(low[i-period:i])
            
            if highest == lowest:
                k_series[i] = 50.0
            else:
                k_series[i] = ((close[i] - lowest) / (highest - lowest)) * 100
        
        return k_series
    
    def _analyze_confluence(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa confluência de múltiplos indicadores.
        
        Quanto mais indicadores concordam, maior a confiança.
        """
        signals = analysis.get('signals', [])
        divergences = analysis.get('divergences', [])
        
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        bullish_indicators = []
        bearish_indicators = []
        
        # Contar sinais dos indicadores
        for signal in signals:
            if signal.signal_type == 'buy':
                bullish_count += 1
                bullish_indicators.append(signal.indicator)
            elif signal.signal_type == 'sell':
                bearish_count += 1
                bearish_indicators.append(signal.indicator)
            else:
                neutral_count += 1
        
        # Adicionar divergências ao count
        for div in divergences:
            if div.get('signal') == 'buy':
                bullish_count += 1
                bullish_indicators.append(f"{div['indicator']}_div")
            elif div.get('signal') == 'sell':
                bearish_count += 1
                bearish_indicators.append(f"{div['indicator']}_div")
        
        total = bullish_count + bearish_count + neutral_count
        
        # Calcular score de confluência (-1 a +1)
        if total > 0:
            confluence_score = (bullish_count - bearish_count) / total
        else:
            confluence_score = 0.0
        
        # Determinar indicadores em conflito
        conflicting = []
        if bullish_count > 0 and bearish_count > 0:
            conflicting = bullish_indicators[:2] + bearish_indicators[:2]
        
        # Determinar qualidade
        if total >= 4 and abs(confluence_score) > 0.6:
            quality = 'high'
        elif total >= 2 and abs(confluence_score) > 0.3:
            quality = 'medium'
        else:
            quality = 'low'
        
        return {
            'total_signals': total,
            'bullish_signals': bullish_count,
            'bearish_signals': bearish_count,
            'neutral_signals': neutral_count,
            'confluence_score': round(confluence_score, 3),
            'aligned_indicators': bullish_indicators if confluence_score > 0 else bearish_indicators,
            'conflicting_indicators': conflicting,
            'quality': quality,
        }
    
    def _assess_signal_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Avalia qualidade geral do sinal gerado.
        
        Considera:
        - Força da tendência
        - Confluência de indicadores
        - Presença de divergências
        - Volatilidade
        """
        confluence = analysis.get('confluence', {})
        divergences = analysis.get('divergences', [])
        volatility = analysis.get('volatility', {})
        trend = analysis.get('trend', {})
        
        quality_score = 50.0  # Base
        factors = []
        
        # Fator 1: Confluência (até +30)
        conf_score = abs(confluence.get('confluence_score', 0))
        quality_score += conf_score * 30
        if conf_score > 0.5:
            factors.append('high_confluence')
        
        # Fator 2: Divergências (até +20)
        if divergences:
            strong_divs = [d for d in divergences if d.get('strength', 0) > 0.5]
            if strong_divs:
                quality_score += len(strong_divs) * 10
                factors.append('divergence_present')
        
        # Fator 3: Tendência clara (até +15)
        direction = trend.get('direction')
        if direction in (TrendDirection.STRONG_UP, TrendDirection.STRONG_DOWN):
            quality_score += 15
            factors.append('strong_trend')
        elif direction in (TrendDirection.UP, TrendDirection.DOWN):
            quality_score += 8
        
        # Fator 4: Volatilidade adequada (até +15)
        bb = volatility.get('bollinger', {})
        bb_width = bb.get('width', 3)
        if 2 < bb_width < 5:
            quality_score += 15
            factors.append('optimal_volatility')
        elif bb_width < 1.5:
            quality_score -= 10  # Muito baixa - possível squeeze
            factors.append('low_volatility_warning')
        elif bb_width > 6:
            quality_score -= 5  # Muito alta
            factors.append('high_volatility_warning')
        
        # Limitar entre 0-100
        quality_score = max(0, min(100, quality_score))
        
        # Classificação
        if quality_score >= 80:
            grade = 'A'
        elif quality_score >= 60:
            grade = 'B'
        elif quality_score >= 40:
            grade = 'C'
        else:
            grade = 'D'
        
        return {
            'score': round(quality_score, 1),
            'grade': grade,
            'factors': factors,
            'actionable': quality_score >= 60 and confluence.get('quality') != 'low',
        }
    
    # === MÉTODOS MULTI-TIMEFRAME ===
    
    def analyze_mtf(
        self,
        dataframes: Dict[str, pd.DataFrame],
        primary_tf: str = 'H1'
    ) -> Dict[str, Any]:
        """
        Análise Multi-Timeframe.
        
        Args:
            dataframes: Dict com timeframe -> DataFrame
            primary_tf: Timeframe principal para decisões
            
        Returns:
            Análise combinada de múltiplos timeframes
        """
        analyses = {}
        
        # Analisar cada timeframe
        for tf, df in dataframes.items():
            if df is not None and len(df) >= 50:
                analyses[tf] = self.analyze(df, use_cache=True)
        
        if not analyses:
            return {'alignment': MTFAlignment.NEUTRAL.value, 'analyses': {}}
        
        # Determinar alinhamento
        scores = [a.get('score', 0) for a in analyses.values()]
        avg_score = np.mean(scores)
        
        bullish_tfs = sum(1 for s in scores if s > 20)
        bearish_tfs = sum(1 for s in scores if s < -20)
        total_tfs = len(scores)
        
        if bullish_tfs == total_tfs:
            alignment = MTFAlignment.FULL_BULLISH
        elif bullish_tfs > total_tfs / 2:
            alignment = MTFAlignment.PARTIAL_BULLISH
        elif bearish_tfs == total_tfs:
            alignment = MTFAlignment.FULL_BEARISH
        elif bearish_tfs > total_tfs / 2:
            alignment = MTFAlignment.PARTIAL_BEARISH
        else:
            alignment = MTFAlignment.NEUTRAL
        
        return {
            'alignment': alignment.value,
            'confluence_score': alignment.confluence_score,
            'average_score': round(avg_score, 2),
            'primary_analysis': analyses.get(primary_tf, {}),
            'timeframe_scores': {tf: a.get('score', 0) for tf, a in analyses.items()},
            'recommendation': self._mtf_recommendation(alignment, analyses.get(primary_tf, {})),
        }
    
    def _mtf_recommendation(
        self,
        alignment: MTFAlignment,
        primary_analysis: Dict[str, Any]
    ) -> str:
        """Gera recomendação baseada em MTF."""
        if alignment == MTFAlignment.FULL_BULLISH:
            return "STRONG BUY - All timeframes aligned bullish"
        elif alignment == MTFAlignment.FULL_BEARISH:
            return "STRONG SELL - All timeframes aligned bearish"
        elif alignment == MTFAlignment.PARTIAL_BULLISH:
            return "MODERATE BUY - Majority of timeframes bullish"
        elif alignment == MTFAlignment.PARTIAL_BEARISH:
            return "MODERATE SELL - Majority of timeframes bearish"
        else:
            return "HOLD - Mixed signals across timeframes"
    
    # === ESTATÍSTICAS E CONFIGURAÇÃO ===
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do analisador."""
        return {
            **self._stats,
            'cache_size': len(self._cache),
            'history_size': len(self._analysis_history),
            'adaptive_thresholds': self._adaptive_thresholds.copy(),
        }
    
    def clear_cache(self) -> None:
        """Limpa cache de análises."""
        self._cache.clear()
    
    def register_callback(self, callback: Callable) -> None:
        """Registra callback para eventos."""
        self._event_callbacks.append(callback)
    
    def get_recent_analyses(self, count: int = 10) -> List[Dict[str, Any]]:
        """Retorna análises recentes do histórico."""
        return list(self._analysis_history)[-count:]
    
    # === Indicadores ===
    
    def _sma(self, data: np.ndarray, period: int) -> float:
        """Simple Moving Average."""
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        return np.mean(data[-period:])
    
    def _ema(self, data: np.ndarray, period: int) -> float:
        """Exponential Moving Average."""
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        
        multiplier = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    def _rsi(self, data: np.ndarray, period: int = 14) -> float:
        """Relative Strength Index."""
        if len(data) < period + 1:
            return 50.0
        
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _rsi_signal(self, rsi: float) -> str:
        """Sinal baseado no RSI."""
        if rsi < 30:
            return 'oversold'
        elif rsi > 70:
            return 'overbought'
        return 'neutral'
    
    def _macd(
        self, 
        data: np.ndarray, 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> Tuple[float, float, float]:
        """MACD (Moving Average Convergence Divergence)."""
        if len(data) < slow:
            return 0, 0, 0
        
        ema_fast = self._ema_series(data, fast)
        ema_slow = self._ema_series(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema_series(macd_line, signal)[-1]
        histogram = macd_line[-1] - signal_line
        
        return macd_line[-1], signal_line, histogram
    
    def _ema_series(self, data: np.ndarray, period: int) -> np.ndarray:
        """EMA como série."""
        multiplier = 2 / (period + 1)
        ema = np.zeros(len(data))
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        return ema
    
    def _detect_crossover(self, macd: float, signal: float) -> str:
        """Detecta crossover do MACD."""
        # Simplificado - em produção verificar histórico
        if macd > signal and macd > 0:
            return 'bullish'
        elif macd < signal and macd < 0:
            return 'bearish'
        return 'none'
    
    def _stochastic(
        self, 
        high: np.ndarray, 
        low: np.ndarray, 
        close: np.ndarray, 
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[float, float]:
        """Stochastic Oscillator."""
        if len(close) < k_period:
            return 50.0, 50.0
        
        highest_high = np.max(high[-k_period:])
        lowest_low = np.min(low[-k_period:])
        
        if highest_high == lowest_low:
            k = 50.0
        else:
            k = ((close[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        
        # %D é a média de %K
        d = k  # Simplificado
        
        return k, d
    
    def _stochastic_signal(self, k: float, d: float) -> str:
        """Sinal do Stochastic."""
        if k < 20 and d < 20:
            return 'oversold'
        elif k > 80 and d > 80:
            return 'overbought'
        return 'neutral'
    
    def _cci(
        self, 
        high: np.ndarray, 
        low: np.ndarray, 
        close: np.ndarray, 
        period: int = 20
    ) -> float:
        """Commodity Channel Index."""
        if len(close) < period:
            return 0.0
        
        typical_price = (high + low + close) / 3
        sma = np.mean(typical_price[-period:])
        mean_deviation = np.mean(np.abs(typical_price[-period:] - sma))
        
        if mean_deviation == 0:
            return 0.0
        
        return (typical_price[-1] - sma) / (0.015 * mean_deviation)
    
    def _williams_r(
        self, 
        high: np.ndarray, 
        low: np.ndarray, 
        close: np.ndarray, 
        period: int = 14
    ) -> float:
        """Williams %R."""
        if len(close) < period:
            return -50.0
        
        highest_high = np.max(high[-period:])
        lowest_low = np.min(low[-period:])
        
        if highest_high == lowest_low:
            return -50.0
        
        return ((highest_high - close[-1]) / (highest_high - lowest_low)) * -100
    
    def _atr(
        self, 
        high: np.ndarray, 
        low: np.ndarray, 
        close: np.ndarray, 
        period: int = 14
    ) -> float:
        """Average True Range."""
        if len(close) < 2:
            return 0.0
        
        tr = np.zeros(len(close))
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(close)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        return np.mean(tr[-period:])
    
    def _bollinger_bands(
        self, 
        data: np.ndarray, 
        period: int = 20, 
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """Bollinger Bands."""
        if len(data) < period:
            return data[-1], data[-1], data[-1]
        
        middle = np.mean(data[-period:])
        std = np.std(data[-period:])
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def _bb_position(self, price: float, upper: float, lower: float) -> str:
        """Posição em relação às Bollinger Bands."""
        if price > upper:
            return 'above_upper'
        elif price < lower:
            return 'below_lower'
        return 'inside'
    
    def _keltner_channels(
        self, 
        high: np.ndarray, 
        low: np.ndarray, 
        close: np.ndarray, 
        period: int = 20,
        multiplier: float = 2.0
    ) -> Dict[str, float]:
        """Keltner Channels."""
        middle = self._ema(close, period)
        atr = self._atr(high, low, close, period)
        
        return {
            'upper': middle + (multiplier * atr),
            'middle': middle,
            'lower': middle - (multiplier * atr),
        }
    
    def _adx(
        self, 
        high: np.ndarray, 
        low: np.ndarray, 
        close: np.ndarray, 
        period: int = 14
    ) -> float:
        """Average Directional Index."""
        if len(close) < period + 1:
            return 25.0
        
        # Simplificado
        tr = self._atr(high, low, close, period)
        
        # +DM e -DM
        plus_dm = np.zeros(len(high))
        minus_dm = np.zeros(len(high))
        
        for i in range(1, len(high)):
            up_move = high[i] - high[i-1]
            down_move = low[i-1] - low[i]
            
            if up_move > down_move and up_move > 0:
                plus_dm[i] = up_move
            if down_move > up_move and down_move > 0:
                minus_dm[i] = down_move
        
        plus_di = 100 * np.mean(plus_dm[-period:]) / tr if tr > 0 else 0
        minus_di = 100 * np.mean(minus_dm[-period:]) / tr if tr > 0 else 0
        
        if plus_di + minus_di == 0:
            return 0.0
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx
    
    def _determine_trend_direction(self, trend_data: Dict[str, Any]) -> TrendDirection:
        """Determina direção da tendência."""
        ema_20 = trend_data.get('ema_20', 0)
        ema_50 = trend_data.get('ema_50', 0)
        ema_200 = trend_data.get('ema_200')
        adx = trend_data.get('adx', 25)
        macd = trend_data.get('macd', {})
        
        # Alinhamento de EMAs
        if ema_200:
            if ema_20 > ema_50 > ema_200:
                if adx > 25:
                    return TrendDirection.STRONG_UP
                return TrendDirection.UP
            elif ema_20 < ema_50 < ema_200:
                if adx > 25:
                    return TrendDirection.STRONG_DOWN
                return TrendDirection.DOWN
        else:
            if ema_20 > ema_50:
                return TrendDirection.UP
            elif ema_20 < ema_50:
                return TrendDirection.DOWN
        
        return TrendDirection.NEUTRAL
    
    def _find_swing_highs(self, data: np.ndarray, lookback: int = 5) -> List[Tuple[int, float]]:
        """Encontra swing highs."""
        swings = []
        for i in range(lookback, len(data) - lookback):
            if data[i] == max(data[i-lookback:i+lookback+1]):
                swings.append((i, data[i]))
        return swings
    
    def _find_swing_lows(self, data: np.ndarray, lookback: int = 5) -> List[Tuple[int, float]]:
        """Encontra swing lows."""
        swings = []
        for i in range(lookback, len(data) - lookback):
            if data[i] == min(data[i-lookback:i+lookback+1]):
                swings.append((i, data[i]))
        return swings
    
    def _find_support_levels(
        self, 
        low: np.ndarray, 
        swing_lows: List[Tuple[int, float]]
    ) -> List[float]:
        """Encontra níveis de suporte."""
        if not swing_lows:
            return []
        
        # Últimos 3 swing lows
        levels = [s[1] for s in swing_lows[-3:]]
        return sorted(levels)
    
    def _find_resistance_levels(
        self, 
        high: np.ndarray, 
        swing_highs: List[Tuple[int, float]]
    ) -> List[float]:
        """Encontra níveis de resistência."""
        if not swing_highs:
            return []
        
        # Últimos 3 swing highs
        levels = [s[1] for s in swing_highs[-3:]]
        return sorted(levels, reverse=True)
    
    def _check_higher_highs(self, swing_highs: List[Tuple[int, float]]) -> bool:
        """Verifica higher highs."""
        if len(swing_highs) < 2:
            return False
        return swing_highs[-1][1] > swing_highs[-2][1]
    
    def _check_higher_lows(self, swing_lows: List[Tuple[int, float]]) -> bool:
        """Verifica higher lows."""
        if len(swing_lows) < 2:
            return False
        return swing_lows[-1][1] > swing_lows[-2][1]
    
    def _check_lower_highs(self, swing_highs: List[Tuple[int, float]]) -> bool:
        """Verifica lower highs."""
        if len(swing_highs) < 2:
            return False
        return swing_highs[-1][1] < swing_highs[-2][1]
    
    def _check_lower_lows(self, swing_lows: List[Tuple[int, float]]) -> bool:
        """Verifica lower lows."""
        if len(swing_lows) < 2:
            return False
        return swing_lows[-1][1] < swing_lows[-2][1]
    
    def _identify_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identifica padrões de candle."""
        patterns = []
        
        if len(df) < 3:
            return patterns
        
        # Últimos 3 candles
        candles = df.iloc[-3:]
        
        # Doji
        last = candles.iloc[-1]
        body = abs(last['close'] - last['open'])
        range_hl = last['high'] - last['low']
        
        if range_hl > 0 and body / range_hl < 0.1:
            patterns.append({
                'name': 'Doji',
                'type': 'reversal',
                'position': len(df) - 1,
            })
        
        # Engulfing
        prev = candles.iloc[-2]
        if (last['close'] > last['open'] and 
            prev['close'] < prev['open'] and
            last['open'] < prev['close'] and
            last['close'] > prev['open']):
            patterns.append({
                'name': 'Bullish Engulfing',
                'type': 'bullish_reversal',
                'position': len(df) - 1,
            })
        elif (last['close'] < last['open'] and 
              prev['close'] > prev['open'] and
              last['open'] > prev['close'] and
              last['close'] < prev['open']):
            patterns.append({
                'name': 'Bearish Engulfing',
                'type': 'bearish_reversal',
                'position': len(df) - 1,
            })
        
        return patterns
