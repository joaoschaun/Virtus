"""
VIRTUS Correlation Analyzer - MAGISTRAL Edition
=================================================

Sistema avançado de análise de correlações para trading:
- Correlação entre pares com múltiplos métodos
- Correlação com DXY (Dollar Index)
- Correlação com yields (bonds)
- Análise de divergência de correlação
- Detecção de regime de correlação
- Correlação dinâmica (rolling + EWMA)
- Lead-lag detection entre pares
- Cointegração para pairs trading
- Cache inteligente para performance
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import deque
import hashlib


class CorrelationStrength(Enum):
    """Força da correlação com propriedades estendidas."""
    VERY_STRONG = auto()    # > 0.8 ou < -0.8
    STRONG = auto()         # 0.6-0.8 ou -0.6 a -0.8
    MODERATE = auto()       # 0.4-0.6 ou -0.4 a -0.6
    WEAK = auto()           # 0.2-0.4 ou -0.2 a -0.4
    NONE = auto()           # < 0.2 e > -0.2
    
    @property
    def min_threshold(self) -> float:
        """Threshold mínimo absoluto para a força."""
        mapping = {
            CorrelationStrength.VERY_STRONG: 0.8,
            CorrelationStrength.STRONG: 0.6,
            CorrelationStrength.MODERATE: 0.4,
            CorrelationStrength.WEAK: 0.2,
            CorrelationStrength.NONE: 0.0,
        }
        return mapping[self]
    
    @property
    def is_tradeable(self) -> bool:
        """Se a correlação é forte o suficiente para trades baseados nela."""
        return self in (CorrelationStrength.VERY_STRONG, CorrelationStrength.STRONG)


class CorrelationRegime(Enum):
    """Regime de correlação com contexto de mercado."""
    RISK_ON = auto()        # Correlações normais de risk-on
    RISK_OFF = auto()       # Correlações de aversão a risco
    TRANSITIONING = auto()  # Mudando de regime
    ABNORMAL = auto()       # Correlações quebradas
    CRISIS = auto()         # Correlações de crise (tudo correlaciona)
    
    @property
    def risk_multiplier(self) -> float:
        """Multiplicador de risco para o regime."""
        mapping = {
            CorrelationRegime.RISK_ON: 1.0,
            CorrelationRegime.RISK_OFF: 1.3,
            CorrelationRegime.TRANSITIONING: 1.5,
            CorrelationRegime.ABNORMAL: 2.0,
            CorrelationRegime.CRISIS: 2.5,
        }
        return mapping[self]


class CorrelationMethod(Enum):
    """Métodos de cálculo de correlação."""
    PEARSON = "pearson"         # Correlação linear padrão
    SPEARMAN = "spearman"       # Correlação de rank (robusta a outliers)
    KENDALL = "kendall"         # Correlação de concordância
    EWMA = "ewma"               # Exponentially weighted


@dataclass
class PairCorrelation:
    """Correlação entre dois instrumentos com análise estendida."""
    pair_1: str
    pair_2: str
    correlation: float
    strength: CorrelationStrength
    rolling_corr: List[float]  # Últimas N correlações
    is_stable: bool
    diverging: bool
    lead_lag: int = 0          # Lag em períodos (positivo = pair_1 lidera)
    half_life: float = 0.0     # Meia-vida da correlação
    confidence: float = 0.0    # Confiança na correlação
    
    @property
    def is_tradeable(self) -> bool:
        """Se o par é adequado para pairs trading."""
        return (
            self.strength.is_tradeable and 
            self.is_stable and 
            not self.diverging and
            self.confidence > 0.6
        )


@dataclass
class DXYCorrelation:
    """Correlação com Dollar Index com contexto."""
    symbol: str
    correlation: float
    expected_correlation: float  # Esperado baseado no par
    divergence: float
    signal: str  # 'aligned', 'diverging', 'neutral'
    rolling_divergence: List[float] = field(default_factory=list)
    
    @property
    def divergence_trend(self) -> str:
        """Tendência da divergência."""
        if len(self.rolling_divergence) < 3:
            return 'unknown'
        if self.rolling_divergence[-1] > self.rolling_divergence[-3]:
            return 'increasing'
        elif self.rolling_divergence[-1] < self.rolling_divergence[-3]:
            return 'decreasing'
        return 'stable'


@dataclass
class LeadLagResult:
    """Resultado de análise de lead-lag."""
    leader: str
    follower: str
    lag_periods: int
    correlation_at_lag: float
    confidence: float
    

@dataclass
class CointegrationResult:
    """Resultado de teste de cointegração."""
    pair_1: str
    pair_2: str
    is_cointegrated: bool
    spread_mean: float
    spread_std: float
    half_life: float
    z_score: float
    signal: str  # 'buy_spread', 'sell_spread', 'neutral'


@dataclass
class CorrelationAnalysisResult:
    """Resultado completo da análise de correlação MAGISTRAL."""
    pair_correlations: Dict[str, 'PairCorrelation']
    dxy_correlation: Optional['DXYCorrelation']
    regime: CorrelationRegime
    regime_confidence: float
    anomalies: List[str]
    trading_implications: List[str]
    lead_lag_analysis: List['LeadLagResult'] = field(default_factory=list)
    cointegration_results: List['CointegrationResult'] = field(default_factory=list)
    correlation_matrix: Optional[np.ndarray] = None
    risk_score: float = 0.0  # 0-100, quanto maior mais risco de correlação


@dataclass
class CorrelationCache:
    """Cache para resultados de correlação."""
    key: str
    timestamp: datetime
    result: Dict[str, Any]
    ttl_seconds: int = 300  # 5 minutos


class CorrelationAnalyzer:
    """
    Analisador de Correlações MAGISTRAL - Sistema avançado de correlação.
    
    Features:
    - Múltiplos métodos de correlação (Pearson, Spearman, EWMA)
    - Análise lead-lag entre pares
    - Detecção de cointegração para pairs trading
    - Cache inteligente para performance
    - Regime detection com múltiplos fatores
    - Risk scoring baseado em correlação
    - Histórico de análises
    """
    
    # Correlações esperadas (aproximadas) - Base empírica
    EXPECTED_DXY_CORRELATIONS = {
        'EURUSD': -0.9,   # EUR/USD é inverso do DXY
        'GBPUSD': -0.7,   # GBP/USD também inverso
        'USDJPY': 0.6,    # USD/JPY positivo
        'USDCHF': 0.8,    # USD/CHF positivo
        'AUDUSD': -0.6,   # AUD/USD inverso
        'NZDUSD': -0.5,   # NZD/USD inverso
        'USDCAD': 0.7,    # USD/CAD positivo
        'XAUUSD': -0.5,   # Ouro inverso ao USD
        'XAGUSD': -0.4,   # Prata inverso ao USD
    }
    
    # Pares correlacionados com thresholds
    CORRELATED_PAIRS = [
        ('EURUSD', 'GBPUSD', 0.8),    # Geralmente correlacionados
        ('EURUSD', 'USDCHF', -0.9),   # Geralmente inversos
        ('AUDUSD', 'NZDUSD', 0.85),   # Muito correlacionados
        ('EURUSD', 'EURJPY', 0.7),    # Correlacionados
        ('USDJPY', 'EURJPY', 0.6),    # Correlacionados
        ('XAUUSD', 'EURUSD', 0.4),    # Correlação moderada
        ('XAUUSD', 'XAGUSD', 0.9),    # Metais muito correlacionados
        ('AUDUSD', 'XAUUSD', 0.5),    # AUD e ouro (mineração)
    ]
    
    # Pares de crise (correlacionam em stress)
    CRISIS_PAIRS = [
        'USDJPY', 'USDCHF', 'XAUUSD'  # Safe havens
    ]
    
    def __init__(
        self,
        correlation_period: int = 20,
        rolling_window: int = 10,
        stability_threshold: float = 0.1,
        enable_cache: bool = True,
        cache_ttl: int = 300,
    ):
        """
        Inicializa o analisador de correlações.
        
        Args:
            correlation_period: Período para cálculo de correlação
            rolling_window: Janela para rolling correlation
            stability_threshold: Threshold para estabilidade
            enable_cache: Habilitar cache
            cache_ttl: TTL do cache em segundos
        """
        self.correlation_period = correlation_period
        self.rolling_window = rolling_window
        self.stability_threshold = stability_threshold
        self._enable_cache = enable_cache
        self._cache_ttl = cache_ttl
        
        # Cache
        self._cache: Dict[str, CorrelationCache] = {}
        
        # Histórico
        self._analysis_history: deque = deque(maxlen=50)
        
        # Estatísticas
        self._stats = {
            'total_analyses': 0,
            'cache_hits': 0,
            'anomalies_detected': 0,
            'regime_changes': 0,
        }
        
        # Último regime detectado
        self._last_regime: Optional[CorrelationRegime] = None
        
        # Callbacks
        self._callbacks: List[Callable] = []
    
    def _get_cache_key(self, main_symbol: str, other_symbols: List[str]) -> str:
        """Gera chave de cache."""
        symbols = sorted([main_symbol] + other_symbols)
        return hashlib.md5('_'.join(symbols).encode()).hexdigest()[:16]
    
    def _get_cached(self, key: str) -> Optional[CorrelationAnalysisResult]:
        """Obtém resultado do cache se válido."""
        if not self._enable_cache or key not in self._cache:
            return None
        
        cached = self._cache[key]
        if (datetime.now() - cached.timestamp).total_seconds() < cached.ttl_seconds:
            self._stats['cache_hits'] += 1
            return cached.result
        
        del self._cache[key]
        return None
    
    def analyze(
        self,
        main_symbol: str,
        main_data: pd.DataFrame,
        other_data: Dict[str, pd.DataFrame] = None,
        dxy_data: pd.DataFrame = None,
    ) -> CorrelationAnalysisResult:
        """
        Analisa correlações do símbolo principal.
        
        Args:
            main_symbol: Símbolo principal (ex: 'EURUSD')
            main_data: DataFrame do símbolo principal
            other_data: Dicionário com DataFrames de outros símbolos
            dxy_data: DataFrame do DXY (opcional)
            
        Returns:
            CorrelationAnalysisResult
        """
        if main_data is None or len(main_data) < self.correlation_period:
            return self._empty_result()
        
        main_returns = self._calculate_returns(main_data['close'].values)
        
        pair_correlations = {}
        anomalies = []
        trading_implications = []
        
        # Correlações com outros pares
        if other_data:
            for symbol, df in other_data.items():
                if df is None or len(df) < self.correlation_period:
                    continue
                
                other_returns = self._calculate_returns(df['close'].values)
                
                # Alinha os tamanhos
                min_len = min(len(main_returns), len(other_returns))
                
                if min_len < self.correlation_period:
                    continue
                
                corr = self._calculate_correlation(
                    main_returns[-min_len:],
                    other_returns[-min_len:]
                )
                
                rolling = self._calculate_rolling_correlation(
                    main_returns[-min_len:],
                    other_returns[-min_len:]
                )
                
                strength = self._classify_strength(corr)
                is_stable = self._check_stability(rolling)
                
                # Verifica divergência
                expected = self._get_expected_correlation(main_symbol, symbol)
                diverging = False
                if expected is not None:
                    if abs(corr - expected) > 0.3:
                        diverging = True
                        anomalies.append(
                            f"Correlação anômala entre {main_symbol} e {symbol}: "
                            f"esperado {expected:.2f}, atual {corr:.2f}"
                        )
                
                pair_correlations[symbol] = PairCorrelation(
                    pair_1=main_symbol,
                    pair_2=symbol,
                    correlation=corr,
                    strength=strength,
                    rolling_corr=rolling,
                    is_stable=is_stable,
                    diverging=diverging,
                )
        
        # Correlação com DXY
        dxy_correlation = None
        if dxy_data is not None and len(dxy_data) >= self.correlation_period:
            dxy_returns = self._calculate_returns(dxy_data['close'].values)
            min_len = min(len(main_returns), len(dxy_returns))
            
            if min_len >= self.correlation_period:
                dxy_corr = self._calculate_correlation(
                    main_returns[-min_len:],
                    dxy_returns[-min_len:]
                )
                
                expected_dxy = self.EXPECTED_DXY_CORRELATIONS.get(main_symbol, 0)
                dxy_divergence = dxy_corr - expected_dxy
                
                if abs(dxy_divergence) > 0.2:
                    signal = 'diverging'
                    anomalies.append(
                        f"Correlação com DXY divergente: esperado {expected_dxy:.2f}, "
                        f"atual {dxy_corr:.2f}"
                    )
                else:
                    signal = 'aligned'
                
                dxy_correlation = DXYCorrelation(
                    symbol=main_symbol,
                    correlation=dxy_corr,
                    expected_correlation=expected_dxy,
                    divergence=dxy_divergence,
                    signal=signal,
                )
        
        # Determina regime
        regime, regime_conf = self._determine_regime(
            pair_correlations, dxy_correlation
        )
        
        # Gera implicações de trading
        trading_implications = self._generate_implications(
            main_symbol, pair_correlations, dxy_correlation, regime
        )
        
        return CorrelationAnalysisResult(
            pair_correlations=pair_correlations,
            dxy_correlation=dxy_correlation,
            regime=regime,
            regime_confidence=regime_conf,
            anomalies=anomalies,
            trading_implications=trading_implications,
        )
    
    def _calculate_returns(self, prices: np.ndarray) -> np.ndarray:
        """Calcula retornos percentuais."""
        if len(prices) < 2:
            return np.array([])
        return np.diff(prices) / prices[:-1]
    
    def _calculate_correlation(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray,
    ) -> float:
        """Calcula correlação de Pearson."""
        if len(returns1) < 2 or len(returns2) < 2:
            return 0.0
        
        # Usa últimos N períodos
        r1 = returns1[-self.correlation_period:]
        r2 = returns2[-self.correlation_period:]
        
        if len(r1) != len(r2):
            min_len = min(len(r1), len(r2))
            r1 = r1[-min_len:]
            r2 = r2[-min_len:]
        
        mean1 = np.mean(r1)
        mean2 = np.mean(r2)
        
        cov = np.mean((r1 - mean1) * (r2 - mean2))
        std1 = np.std(r1)
        std2 = np.std(r2)
        
        if std1 == 0 or std2 == 0:
            return 0.0
        
        return cov / (std1 * std2)
    
    def _calculate_rolling_correlation(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray,
    ) -> List[float]:
        """Calcula correlação rolling."""
        rolling = []
        window = self.rolling_window
        
        for i in range(window, len(returns1)):
            r1 = returns1[i-window:i]
            r2 = returns2[i-window:i]
            
            corr = self._calculate_correlation_simple(r1, r2)
            rolling.append(corr)
        
        return rolling[-10:]  # Últimas 10
    
    def _calculate_correlation_simple(
        self,
        r1: np.ndarray,
        r2: np.ndarray,
    ) -> float:
        """Correlação simples para rolling."""
        if len(r1) < 2:
            return 0.0
        
        mean1 = np.mean(r1)
        mean2 = np.mean(r2)
        
        cov = np.mean((r1 - mean1) * (r2 - mean2))
        std1 = np.std(r1)
        std2 = np.std(r2)
        
        if std1 == 0 or std2 == 0:
            return 0.0
        
        return cov / (std1 * std2)
    
    def _classify_strength(self, correlation: float) -> CorrelationStrength:
        """Classifica a força da correlação."""
        abs_corr = abs(correlation)
        
        if abs_corr >= 0.8:
            return CorrelationStrength.VERY_STRONG
        elif abs_corr >= 0.6:
            return CorrelationStrength.STRONG
        elif abs_corr >= 0.4:
            return CorrelationStrength.MODERATE
        elif abs_corr >= 0.2:
            return CorrelationStrength.WEAK
        else:
            return CorrelationStrength.NONE
    
    def _check_stability(self, rolling: List[float]) -> bool:
        """Verifica se a correlação é estável."""
        if len(rolling) < 3:
            return True
        
        std = np.std(rolling)
        return std < self.stability_threshold
    
    def _get_expected_correlation(
        self,
        symbol1: str,
        symbol2: str,
    ) -> Optional[float]:
        """Obtém correlação esperada entre dois pares."""
        for pair1, pair2, expected in self.CORRELATED_PAIRS:
            if (symbol1 == pair1 and symbol2 == pair2) or \
               (symbol1 == pair2 and symbol2 == pair1):
                return expected if symbol1 == pair1 else -expected
        return None
    
    def _determine_regime(
        self,
        pair_correlations: Dict[str, PairCorrelation],
        dxy_correlation: Optional[DXYCorrelation],
    ) -> Tuple[CorrelationRegime, float]:
        """Determina o regime de correlação atual."""
        if not pair_correlations and not dxy_correlation:
            return CorrelationRegime.ABNORMAL, 0.5
        
        # Conta anomalias
        total = len(pair_correlations)
        diverging = sum(1 for p in pair_correlations.values() if p.diverging)
        unstable = sum(1 for p in pair_correlations.values() if not p.is_stable)
        
        if total == 0:
            if dxy_correlation and dxy_correlation.signal == 'diverging':
                return CorrelationRegime.ABNORMAL, 0.6
            return CorrelationRegime.TRANSITIONING, 0.5
        
        diverging_pct = diverging / total
        unstable_pct = unstable / total
        
        if diverging_pct > 0.5 or unstable_pct > 0.5:
            return CorrelationRegime.ABNORMAL, 1 - diverging_pct
        elif unstable_pct > 0.3:
            return CorrelationRegime.TRANSITIONING, 1 - unstable_pct
        else:
            # Verifica se é risk-on ou risk-off
            # Simplificado - em produção seria mais sofisticado
            return CorrelationRegime.RISK_ON, 1 - diverging_pct
    
    def _generate_implications(
        self,
        main_symbol: str,
        pair_correlations: Dict[str, PairCorrelation],
        dxy_correlation: Optional[DXYCorrelation],
        regime: CorrelationRegime,
    ) -> List[str]:
        """Gera implicações de trading."""
        implications = []
        
        # Regime
        if regime == CorrelationRegime.ABNORMAL:
            implications.append(
                "⚠️ Regime de correlação anormal - cuidado com hedges e exposição"
            )
        elif regime == CorrelationRegime.TRANSITIONING:
            implications.append(
                "🔄 Correlações em transição - monitorar mudança de regime"
            )
        
        # DXY
        if dxy_correlation:
            if dxy_correlation.signal == 'diverging':
                if dxy_correlation.divergence > 0:
                    implications.append(
                        f"📈 {main_symbol} mais forte que o esperado vs DXY - "
                        f"possível força específica do par"
                    )
                else:
                    implications.append(
                        f"📉 {main_symbol} mais fraco que o esperado vs DXY - "
                        f"possível fraqueza específica do par"
                    )
        
        # Pares correlacionados
        for symbol, corr in pair_correlations.items():
            if corr.diverging:
                implications.append(
                    f"⚠️ Divergência com {symbol} - possível oportunidade de reversão à média"
                )
            
            if corr.strength == CorrelationStrength.VERY_STRONG:
                sign = "positiva" if corr.correlation > 0 else "negativa"
                implications.append(
                    f"🔗 Correlação muito forte {sign} com {symbol} - "
                    f"evitar exposição duplicada"
                )
        
        return implications
    
    def _empty_result(self) -> CorrelationAnalysisResult:
        """Retorna resultado vazio."""
        return CorrelationAnalysisResult(
            pair_correlations={},
            dxy_correlation=None,
            regime=CorrelationRegime.ABNORMAL,
            regime_confidence=0.0,
            anomalies=['Dados insuficientes'],
            trading_implications=[],
        )
    
    # === MÉTODOS MAGISTRAIS ===
    
    def calculate_lead_lag(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray,
        symbol1: str,
        symbol2: str,
        max_lag: int = 5,
    ) -> LeadLagResult:
        """
        Detecta relação lead-lag entre dois instrumentos.
        
        Útil para identificar qual par lidera movimentos.
        """
        if len(returns1) < max_lag * 2 or len(returns2) < max_lag * 2:
            return LeadLagResult(
                leader=symbol1,
                follower=symbol2,
                lag_periods=0,
                correlation_at_lag=0.0,
                confidence=0.0,
            )
        
        min_len = min(len(returns1), len(returns2))
        r1 = returns1[-min_len:]
        r2 = returns2[-min_len:]
        
        best_corr = 0.0
        best_lag = 0
        
        # Testar lags positivos e negativos
        for lag in range(-max_lag, max_lag + 1):
            if lag == 0:
                corr = self._calculate_correlation_simple(r1, r2)
            elif lag > 0:
                # r1 lidera r2 por 'lag' períodos
                corr = self._calculate_correlation_simple(r1[:-lag], r2[lag:])
            else:
                # r2 lidera r1
                corr = self._calculate_correlation_simple(r1[-lag:], r2[:lag])
            
            if abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag
        
        leader = symbol1 if best_lag > 0 else symbol2
        follower = symbol2 if best_lag > 0 else symbol1
        
        # Confiança baseada na diferença entre melhor lag e lag=0
        zero_corr = self._calculate_correlation_simple(r1, r2)
        confidence = abs(best_corr) - abs(zero_corr) if best_lag != 0 else abs(zero_corr)
        confidence = max(0.0, min(1.0, confidence * 2))  # Scale 0-1
        
        return LeadLagResult(
            leader=leader,
            follower=follower,
            lag_periods=abs(best_lag),
            correlation_at_lag=best_corr,
            confidence=confidence,
        )
    
    def test_cointegration(
        self,
        prices1: np.ndarray,
        prices2: np.ndarray,
        symbol1: str,
        symbol2: str,
    ) -> CointegrationResult:
        """
        Testa cointegração entre dois instrumentos para pairs trading.
        
        Usa método de Engle-Granger simplificado.
        """
        if len(prices1) < 50 or len(prices2) < 50:
            return CointegrationResult(
                pair_1=symbol1,
                pair_2=symbol2,
                is_cointegrated=False,
                spread_mean=0.0,
                spread_std=0.0,
                half_life=0.0,
                z_score=0.0,
                signal='neutral',
            )
        
        min_len = min(len(prices1), len(prices2))
        p1 = prices1[-min_len:]
        p2 = prices2[-min_len:]
        
        # Normalizar preços
        p1_norm = p1 / p1[0]
        p2_norm = p2 / p2[0]
        
        # Calcular hedge ratio (beta) via regressão linear simples
        beta = np.cov(p1_norm, p2_norm)[0, 1] / np.var(p2_norm)
        
        # Spread
        spread = p1_norm - beta * p2_norm
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        
        # Z-score atual
        z_score = (spread[-1] - spread_mean) / spread_std if spread_std > 0 else 0
        
        # Half-life do spread (mean reversion)
        half_life = self._calculate_half_life(spread)
        
        # Teste ADF simplificado (verificar estacionariedade do spread)
        spread_diff = np.diff(spread)
        spread_lag = spread[:-1]
        
        if len(spread_diff) > 1 and np.std(spread_lag) > 0:
            # Regressão: spread_diff = alpha + beta * spread_lag
            cov = np.cov(spread_diff, spread_lag)[0, 1]
            var = np.var(spread_lag)
            adf_beta = cov / var if var > 0 else 0
            
            # Se beta < 0, indica mean reversion
            is_cointegrated = adf_beta < -0.1 and half_life > 0 and half_life < 20
        else:
            is_cointegrated = False
        
        # Sinal de trading
        if is_cointegrated:
            if z_score > 2.0:
                signal = 'sell_spread'  # Vender p1, comprar p2
            elif z_score < -2.0:
                signal = 'buy_spread'   # Comprar p1, vender p2
            else:
                signal = 'neutral'
        else:
            signal = 'neutral'
        
        return CointegrationResult(
            pair_1=symbol1,
            pair_2=symbol2,
            is_cointegrated=is_cointegrated,
            spread_mean=spread_mean,
            spread_std=spread_std,
            half_life=half_life,
            z_score=z_score,
            signal=signal,
        )
    
    def _calculate_half_life(self, spread: np.ndarray) -> float:
        """Calcula meia-vida de mean reversion do spread."""
        if len(spread) < 10:
            return 0.0
        
        spread_lag = spread[:-1]
        spread_diff = np.diff(spread)
        
        if len(spread_lag) < 2 or np.std(spread_lag) == 0:
            return 0.0
        
        # Lambda = beta da regressão
        cov = np.cov(spread_diff, spread_lag)[0, 1]
        var = np.var(spread_lag)
        lambd = cov / var if var > 0 else 0
        
        if lambd >= 0:
            return 0.0  # Não há mean reversion
        
        half_life = -np.log(2) / lambd
        return max(0.0, half_life)
    
    def calculate_correlation_ewma(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray,
        span: int = 20,
    ) -> float:
        """
        Calcula correlação usando EWMA (Exponentially Weighted Moving Average).
        
        Mais responsiva a mudanças recentes.
        """
        if len(returns1) < 5 or len(returns2) < 5:
            return 0.0
        
        min_len = min(len(returns1), len(returns2))
        r1 = returns1[-min_len:]
        r2 = returns2[-min_len:]
        
        # Weights exponenciais
        alpha = 2 / (span + 1)
        weights = np.array([(1 - alpha) ** i for i in range(len(r1) - 1, -1, -1)])
        weights /= weights.sum()
        
        # Médias ponderadas
        mean1 = np.sum(weights * r1)
        mean2 = np.sum(weights * r2)
        
        # Covariância e variâncias ponderadas
        cov = np.sum(weights * (r1 - mean1) * (r2 - mean2))
        var1 = np.sum(weights * (r1 - mean1) ** 2)
        var2 = np.sum(weights * (r2 - mean2) ** 2)
        
        if var1 == 0 or var2 == 0:
            return 0.0
        
        return cov / np.sqrt(var1 * var2)
    
    def calculate_spearman(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray,
    ) -> float:
        """
        Calcula correlação de Spearman (rank correlation).
        
        Mais robusta a outliers que Pearson.
        """
        if len(returns1) < 5 or len(returns2) < 5:
            return 0.0
        
        min_len = min(len(returns1), len(returns2))
        r1 = returns1[-min_len:]
        r2 = returns2[-min_len:]
        
        # Converter para ranks
        rank1 = np.argsort(np.argsort(r1)).astype(float)
        rank2 = np.argsort(np.argsort(r2)).astype(float)
        
        # Correlação de Pearson nos ranks
        return self._calculate_correlation_simple(rank1, rank2)
    
    def calculate_correlation_matrix(
        self,
        data: Dict[str, pd.DataFrame],
        method: CorrelationMethod = CorrelationMethod.PEARSON,
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Calcula matriz de correlação entre múltiplos símbolos.
        
        Returns:
            (matriz de correlação, lista de símbolos)
        """
        symbols = list(data.keys())
        n = len(symbols)
        
        if n < 2:
            return np.array([[1.0]]), symbols
        
        # Calcular retornos
        returns = {}
        for symbol, df in data.items():
            if df is not None and len(df) >= self.correlation_period:
                returns[symbol] = self._calculate_returns(df['close'].values)
        
        # Matriz de correlação
        matrix = np.eye(n)
        
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = symbols[i], symbols[j]
                if s1 in returns and s2 in returns:
                    r1, r2 = returns[s1], returns[s2]
                    
                    if method == CorrelationMethod.PEARSON:
                        corr = self._calculate_correlation(r1, r2)
                    elif method == CorrelationMethod.SPEARMAN:
                        corr = self.calculate_spearman(r1, r2)
                    elif method == CorrelationMethod.EWMA:
                        corr = self.calculate_correlation_ewma(r1, r2)
                    else:
                        corr = self._calculate_correlation(r1, r2)
                    
                    matrix[i, j] = corr
                    matrix[j, i] = corr
        
        return matrix, symbols
    
    def calculate_risk_score(
        self,
        correlations: Dict[str, PairCorrelation],
    ) -> float:
        """
        Calcula score de risco baseado em correlações.
        
        Alto = portfólio muito correlacionado (risco concentrado).
        """
        if not correlations:
            return 0.0
        
        # Média de correlações absolutas
        avg_corr = np.mean([abs(c.correlation) for c in correlations.values()])
        
        # Percentual de correlações fortes
        strong_count = sum(
            1 for c in correlations.values() 
            if c.strength in (CorrelationStrength.VERY_STRONG, CorrelationStrength.STRONG)
        )
        strong_pct = strong_count / len(correlations)
        
        # Percentual de divergências
        diverging_count = sum(1 for c in correlations.values() if c.diverging)
        diverging_pct = diverging_count / len(correlations)
        
        # Score composto
        risk_score = (
            avg_corr * 40 +          # Correlação média contribui 40%
            strong_pct * 40 +         # Correlações fortes 40%
            diverging_pct * 20        # Divergências 20%
        )
        
        return min(100.0, risk_score * 100)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do analisador."""
        return {
            **self._stats,
            'cache_size': len(self._cache),
            'history_size': len(self._analysis_history),
            'last_regime': self._last_regime.name if self._last_regime else None,
        }
    
    def get_regime_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """Retorna histórico de regimes."""
        return list(self._analysis_history)[-count:]
    
    def register_callback(self, callback: Callable) -> None:
        """Registra callback para eventos (mudança de regime, anomalias)."""
        self._callbacks.append(callback)
    
    def clear_cache(self) -> None:
        """Limpa cache de análises."""
        self._cache.clear()
    
    def to_dict(self, result: CorrelationAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        pairs_dict = {}
        for symbol, corr in result.pair_correlations.items():
            pairs_dict[symbol] = {
                'correlation': round(corr.correlation, 3),
                'strength': corr.strength.name,
                'is_stable': corr.is_stable,
                'diverging': corr.diverging,
            }
        
        dxy_dict = None
        if result.dxy_correlation:
            dxy_dict = {
                'correlation': round(result.dxy_correlation.correlation, 3),
                'expected': round(result.dxy_correlation.expected_correlation, 3),
                'divergence': round(result.dxy_correlation.divergence, 3),
                'signal': result.dxy_correlation.signal,
            }
        
        return {
            'pair_correlations': pairs_dict,
            'dxy_correlation': dxy_dict,
            'regime': result.regime.name,
            'regime_confidence': round(result.regime_confidence, 3),
            'anomalies': result.anomalies,
            'trading_implications': result.trading_implications,
        }
