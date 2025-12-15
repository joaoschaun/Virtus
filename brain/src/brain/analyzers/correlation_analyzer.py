"""
VIRTUS Correlation Analyzer
============================

Analisa correlações entre ativos e identifica padrões.
Detecta divergências e convergências para oportunidades de trading.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
import numpy as np
from collections import defaultdict

try:
    from ...core import VirtusLogger
except ImportError:
    from core import VirtusLogger


class CorrelationType(Enum):
    """Tipo de correlação."""
    POSITIVE = "positive"      # > 0.5
    NEGATIVE = "negative"      # < -0.5
    NEUTRAL = "neutral"        # -0.5 a 0.5
    DIVERGENT = "divergent"    # Mudança recente significativa


class DivergenceType(Enum):
    """Tipo de divergência detectada."""
    PRICE_VS_HISTORICAL = "price_vs_historical"
    INTER_ASSET = "inter_asset"
    REGIME_CHANGE = "regime_change"


@dataclass
class CorrelationPair:
    """Par de correlação entre dois ativos."""
    symbol_a: str
    symbol_b: str
    
    # Correlações por período
    correlation_1d: float = 0.0
    correlation_1w: float = 0.0
    correlation_1m: float = 0.0
    correlation_3m: float = 0.0
    
    # Tipo atual
    type: CorrelationType = CorrelationType.NEUTRAL
    
    # Mudança
    change_1w: float = 0.0     # Mudança na correlação
    
    # Metadata
    last_update: datetime = field(default_factory=datetime.now)
    data_points: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pair': f"{self.symbol_a}/{self.symbol_b}",
            'correlation_1d': round(self.correlation_1d, 3),
            'correlation_1w': round(self.correlation_1w, 3),
            'correlation_1m': round(self.correlation_1m, 3),
            'correlation_3m': round(self.correlation_3m, 3),
            'type': self.type.value,
            'change_1w': round(self.change_1w, 3),
            'data_points': self.data_points,
        }
    
    @property
    def avg_correlation(self) -> float:
        """Correlação média ponderada."""
        weights = [0.1, 0.2, 0.3, 0.4]  # Mais peso para períodos mais longos
        values = [self.correlation_1d, self.correlation_1w, 
                  self.correlation_1m, self.correlation_3m]
        return sum(w * v for w, v in zip(weights, values))


@dataclass
class Divergence:
    """Divergência detectada."""
    id: str
    type: DivergenceType
    symbols: List[str]
    timestamp: datetime
    
    # Descrição
    description: str
    significance: float  # 0 a 1
    
    # Trading implication
    trading_bias: str = "neutral"  # bullish, bearish, neutral
    opportunity: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'symbols': self.symbols,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'significance': round(self.significance, 3),
            'trading_bias': self.trading_bias,
            'opportunity': self.opportunity,
        }


@dataclass
class CorrelationMatrix:
    """Matriz de correlação completa."""
    symbols: List[str]
    matrix: Dict[str, Dict[str, float]]
    period: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbols': self.symbols,
            'period': self.period,
            'timestamp': self.timestamp.isoformat(),
            'matrix': {
                s1: {s2: round(v, 3) for s2, v in row.items()}
                for s1, row in self.matrix.items()
            },
        }
    
    def get_correlation(self, symbol_a: str, symbol_b: str) -> float:
        """Obtém correlação entre dois símbolos."""
        if symbol_a in self.matrix and symbol_b in self.matrix[symbol_a]:
            return self.matrix[symbol_a][symbol_b]
        return 0.0


class CorrelationAnalyzer:
    """
    Analisador de correlações entre ativos.
    
    Funcionalidades:
    - Cálculo de correlação rolling
    - Detecção de divergências
    - Identificação de regime changes
    - Oportunidades de pairs trading
    """
    
    def __init__(self):
        self.logger = VirtusLogger.get_logger("correlation_analyzer")
        
        # Dados de preços por símbolo
        self._prices: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Pares de correlação calculados
        self._pairs: Dict[str, CorrelationPair] = {}
        
        # Divergências ativas
        self._divergences: List[Divergence] = []
        
        # Histórico de correlações para detectar mudanças
        self._correlation_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Correlações conhecidas (históricas)
        self._known_correlations = {
            ('XAUUSD', 'DXY'): -0.8,      # Ouro vs Dollar Index
            ('EURUSD', 'DXY'): -0.95,     # Euro vs Dollar Index
            ('XAUUSD', 'EURUSD'): 0.5,    # Ouro vs Euro (ambos vs USD)
            ('XAUUSD', 'US10Y'): -0.4,    # Ouro vs Treasury Yields
            ('GBPUSD', 'EURUSD'): 0.7,    # GBP vs EUR
        }
    
    # ========================================================================
    # DADOS DE PREÇOS
    # ========================================================================
    
    async def add_price_data(
        self,
        symbol: str,
        timestamp: datetime,
        price: float
    ) -> None:
        """
        Adiciona dado de preço para análise de correlação.
        
        Args:
            symbol: Símbolo do ativo
            timestamp: Timestamp do preço
            price: Preço
        """
        self._prices[symbol].append((timestamp, price))
        
        # Mantém apenas dados recentes (90 dias)
        cutoff = datetime.now() - timedelta(days=90)
        self._prices[symbol] = [
            (t, p) for t, p in self._prices[symbol]
            if t >= cutoff
        ]
    
    async def add_price_series(
        self,
        symbol: str,
        prices: List[Tuple[datetime, float]]
    ) -> None:
        """Adiciona série de preços."""
        for timestamp, price in prices:
            await self.add_price_data(symbol, timestamp, price)
    
    # ========================================================================
    # CÁLCULO DE CORRELAÇÕES
    # ========================================================================
    
    async def calculate_correlation(
        self,
        symbol_a: str,
        symbol_b: str,
        days: int = 30
    ) -> Optional[float]:
        """
        Calcula correlação entre dois ativos.
        
        Args:
            symbol_a: Primeiro símbolo
            symbol_b: Segundo símbolo
            days: Período em dias
            
        Returns:
            Coeficiente de correlação (-1 a 1)
        """
        prices_a = self._get_aligned_prices(symbol_a, days)
        prices_b = self._get_aligned_prices(symbol_b, days)
        
        if len(prices_a) < 10 or len(prices_b) < 10:
            return None
        
        # Alinha por data
        returns_a, returns_b = self._align_returns(prices_a, prices_b)
        
        if len(returns_a) < 10:
            return None
        
        # Calcula correlação de Pearson
        correlation = self._pearson_correlation(returns_a, returns_b)
        
        return correlation
    
    def _get_aligned_prices(
        self,
        symbol: str,
        days: int
    ) -> List[Tuple[datetime, float]]:
        """Obtém preços alinhados para um período."""
        cutoff = datetime.now() - timedelta(days=days)
        
        prices = [
            (t, p) for t, p in self._prices.get(symbol, [])
            if t >= cutoff
        ]
        
        return sorted(prices, key=lambda x: x[0])
    
    def _align_returns(
        self,
        prices_a: List[Tuple[datetime, float]],
        prices_b: List[Tuple[datetime, float]]
    ) -> Tuple[List[float], List[float]]:
        """Alinha retornos por data."""
        # Cria dicts por data
        dict_a = {t.date(): p for t, p in prices_a}
        dict_b = {t.date(): p for t, p in prices_b}
        
        # Datas em comum
        common_dates = sorted(set(dict_a.keys()) & set(dict_b.keys()))
        
        if len(common_dates) < 2:
            return [], []
        
        # Calcula retornos
        returns_a = []
        returns_b = []
        
        for i in range(1, len(common_dates)):
            prev_date = common_dates[i-1]
            curr_date = common_dates[i]
            
            ret_a = (dict_a[curr_date] - dict_a[prev_date]) / dict_a[prev_date]
            ret_b = (dict_b[curr_date] - dict_b[prev_date]) / dict_b[prev_date]
            
            returns_a.append(ret_a)
            returns_b.append(ret_b)
        
        return returns_a, returns_b
    
    def _pearson_correlation(
        self,
        x: List[float],
        y: List[float]
    ) -> float:
        """Calcula correlação de Pearson."""
        n = len(x)
        if n < 2:
            return 0.0
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        # Variâncias e covariância
        var_x = sum((xi - mean_x) ** 2 for xi in x)
        var_y = sum((yi - mean_y) ** 2 for yi in y)
        cov_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        
        denominator = (var_x * var_y) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return cov_xy / denominator
    
    # ========================================================================
    # ANÁLISE DE PARES
    # ========================================================================
    
    async def analyze_pair(
        self,
        symbol_a: str,
        symbol_b: str
    ) -> CorrelationPair:
        """
        Análise completa de correlação entre dois ativos.
        
        Args:
            symbol_a: Primeiro símbolo
            symbol_b: Segundo símbolo
            
        Returns:
            CorrelationPair com todas as métricas
        """
        pair_key = f"{symbol_a}_{symbol_b}"
        
        # Calcula correlações para diferentes períodos
        corr_1d = await self.calculate_correlation(symbol_a, symbol_b, days=1) or 0.0
        corr_1w = await self.calculate_correlation(symbol_a, symbol_b, days=7) or 0.0
        corr_1m = await self.calculate_correlation(symbol_a, symbol_b, days=30) or 0.0
        corr_3m = await self.calculate_correlation(symbol_a, symbol_b, days=90) or 0.0
        
        # Determina tipo
        avg_corr = (corr_1w + corr_1m) / 2
        if avg_corr > 0.5:
            corr_type = CorrelationType.POSITIVE
        elif avg_corr < -0.5:
            corr_type = CorrelationType.NEGATIVE
        else:
            corr_type = CorrelationType.NEUTRAL
        
        # Mudança
        history = self._correlation_history.get(pair_key, [])
        change_1w = 0.0
        if history:
            week_ago = datetime.now() - timedelta(days=7)
            old_corrs = [c for t, c in history if t <= week_ago]
            if old_corrs:
                change_1w = corr_1w - old_corrs[-1]
        
        # Verifica divergência (mudança significativa)
        if abs(change_1w) > 0.3:
            corr_type = CorrelationType.DIVERGENT
        
        pair = CorrelationPair(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            correlation_1d=corr_1d,
            correlation_1w=corr_1w,
            correlation_1m=corr_1m,
            correlation_3m=corr_3m,
            type=corr_type,
            change_1w=change_1w,
            data_points=len(self._prices.get(symbol_a, [])),
        )
        
        # Salva
        self._pairs[pair_key] = pair
        self._correlation_history[pair_key].append((datetime.now(), corr_1w))
        
        return pair
    
    async def build_correlation_matrix(
        self,
        symbols: Optional[List[str]] = None,
        period_days: int = 30
    ) -> CorrelationMatrix:
        """
        Constrói matriz de correlação completa.
        
        Args:
            symbols: Lista de símbolos
            period_days: Período para cálculo
            
        Returns:
            CorrelationMatrix
        """
        symbols = symbols or list(self._prices.keys())
        
        if len(symbols) < 2:
            return CorrelationMatrix(
                symbols=[],
                matrix={},
                period=f"{period_days}d",
                timestamp=datetime.now(),
            )
        
        matrix: Dict[str, Dict[str, float]] = {}
        
        for symbol_a in symbols:
            matrix[symbol_a] = {}
            for symbol_b in symbols:
                if symbol_a == symbol_b:
                    matrix[symbol_a][symbol_b] = 1.0
                else:
                    corr = await self.calculate_correlation(
                        symbol_a, symbol_b, period_days
                    )
                    matrix[symbol_a][symbol_b] = corr or 0.0
        
        return CorrelationMatrix(
            symbols=symbols,
            matrix=matrix,
            period=f"{period_days}d",
            timestamp=datetime.now(),
        )
    
    # ========================================================================
    # DETECÇÃO DE DIVERGÊNCIAS
    # ========================================================================
    
    async def detect_divergences(
        self,
        symbols: Optional[List[str]] = None
    ) -> List[Divergence]:
        """
        Detecta divergências entre ativos.
        
        Args:
            symbols: Símbolos para analisar
            
        Returns:
            Lista de divergências detectadas
        """
        symbols = symbols or list(self._prices.keys())
        divergences = []
        
        # Verifica pares conhecidos
        for (sym_a, sym_b), expected in self._known_correlations.items():
            if sym_a in symbols or sym_b in symbols:
                actual = await self.calculate_correlation(sym_a, sym_b, days=30)
                if actual is not None:
                    diff = abs(actual - expected)
                    
                    if diff > 0.3:  # Divergência significativa
                        div = Divergence(
                            id=f"div_{sym_a}_{sym_b}_{datetime.now().timestamp()}",
                            type=DivergenceType.PRICE_VS_HISTORICAL,
                            symbols=[sym_a, sym_b],
                            timestamp=datetime.now(),
                            description=(
                                f"Correlação atual ({actual:.2f}) difere da "
                                f"histórica ({expected:.2f})"
                            ),
                            significance=min(1.0, diff / 0.5),
                            trading_bias=self._infer_trading_bias(
                                sym_a, sym_b, actual, expected
                            ),
                        )
                        divergences.append(div)
        
        # Verifica regime changes
        for pair_key, history in self._correlation_history.items():
            if len(history) < 10:
                continue
            
            recent = [c for t, c in history[-5:]]
            older = [c for t, c in history[-20:-5]]
            
            if not older:
                continue
            
            avg_recent = sum(recent) / len(recent)
            avg_older = sum(older) / len(older)
            
            if abs(avg_recent - avg_older) > 0.4:
                symbols_in_pair = pair_key.split('_')
                div = Divergence(
                    id=f"regime_{pair_key}_{datetime.now().timestamp()}",
                    type=DivergenceType.REGIME_CHANGE,
                    symbols=symbols_in_pair,
                    timestamp=datetime.now(),
                    description=(
                        f"Mudança de regime detectada: "
                        f"correlação mudou de {avg_older:.2f} para {avg_recent:.2f}"
                    ),
                    significance=min(1.0, abs(avg_recent - avg_older) / 0.5),
                )
                divergences.append(div)
        
        self._divergences = divergences
        return divergences
    
    def _infer_trading_bias(
        self,
        symbol_a: str,
        symbol_b: str,
        actual: float,
        expected: float
    ) -> str:
        """Infere viés de trading baseado na divergência."""
        # Simplificação: divergência de correlação pode indicar reversão
        if abs(actual - expected) > 0.3:
            # Correlação está se normalizando ou divergindo?
            if abs(actual) < abs(expected):
                return "neutral"  # Correlação enfraquecendo
            else:
                return "neutral"  # Correlação fortalecendo
        return "neutral"
    
    # ========================================================================
    # OPORTUNIDADES
    # ========================================================================
    
    async def find_trading_opportunities(
        self,
        symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Identifica oportunidades de trading baseadas em correlação.
        
        Args:
            symbols: Símbolos para analisar
            
        Returns:
            Lista de oportunidades
        """
        opportunities = []
        symbols = symbols or list(self._prices.keys())
        
        # Detecta divergências primeiro
        divergences = await self.detect_divergences(symbols)
        
        for div in divergences:
            if div.significance > 0.6:
                opportunities.append({
                    'type': 'divergence',
                    'symbols': div.symbols,
                    'description': div.description,
                    'significance': div.significance,
                    'action': 'monitor',
                })
        
        # Verifica pares com correlação extrema para mean reversion
        for pair_key, pair in self._pairs.items():
            if pair.type == CorrelationType.DIVERGENT:
                opportunities.append({
                    'type': 'correlation_shift',
                    'symbols': [pair.symbol_a, pair.symbol_b],
                    'description': (
                        f"Correlação mudou {pair.change_1w:.2f} na última semana"
                    ),
                    'action': 'pairs_analysis',
                })
        
        return opportunities
    
    # ========================================================================
    # RELATÓRIOS
    # ========================================================================
    
    async def get_correlation_report(
        self,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Gera relatório completo de correlações.
        
        Args:
            symbols: Símbolos para incluir
            
        Returns:
            Relatório detalhado
        """
        symbols = symbols or list(self._prices.keys())[:5]  # Top 5
        
        # Matriz
        matrix = await self.build_correlation_matrix(symbols)
        
        # Divergências
        divergences = await self.detect_divergences(symbols)
        
        # Oportunidades
        opportunities = await self.find_trading_opportunities(symbols)
        
        # Pares mais correlacionados
        strongest_positive = []
        strongest_negative = []
        
        for pair in self._pairs.values():
            if pair.avg_correlation > 0.7:
                strongest_positive.append(pair.to_dict())
            elif pair.avg_correlation < -0.7:
                strongest_negative.append(pair.to_dict())
        
        return {
            'timestamp': datetime.now().isoformat(),
            'symbols_analyzed': symbols,
            'matrix': matrix.to_dict(),
            'strongest_positive': strongest_positive[:5],
            'strongest_negative': strongest_negative[:5],
            'divergences': [d.to_dict() for d in divergences],
            'opportunities': opportunities,
            'stats': self.get_stats(),
        }
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def get_pair(self, symbol_a: str, symbol_b: str) -> Optional[CorrelationPair]:
        """Obtém par de correlação existente."""
        key = f"{symbol_a}_{symbol_b}"
        if key in self._pairs:
            return self._pairs[key]
        
        key = f"{symbol_b}_{symbol_a}"
        return self._pairs.get(key)
    
    def clear_old_data(self, days: int = 90) -> int:
        """Limpa dados antigos."""
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        
        for symbol in list(self._prices.keys()):
            old_count = len(self._prices[symbol])
            self._prices[symbol] = [
                (t, p) for t, p in self._prices[symbol]
                if t >= cutoff
            ]
            count += old_count - len(self._prices[symbol])
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do analisador."""
        total_prices = sum(len(p) for p in self._prices.values())
        
        return {
            'symbols_tracked': len(self._prices),
            'total_price_points': total_prices,
            'pairs_analyzed': len(self._pairs),
            'active_divergences': len(self._divergences),
            'history_entries': sum(
                len(h) for h in self._correlation_history.values()
            ),
        }
