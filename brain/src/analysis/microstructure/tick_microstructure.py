"""
VIRTUS Tick Microstructure Analyzer
=====================================

Análise de microestrutura baseada em ticks e spreads.

Funcionalidades:
- Tick Analysis
- Spread Analysis
- Bid-Ask Dynamics
- Price Impact Estimation
- Liquidity Assessment
- Market Quality Metrics
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import deque
import logging


class SpreadCondition(Enum):
    """Condição do spread."""
    TIGHT = auto()       # Spread apertado, boa liquidez
    NORMAL = auto()      # Spread normal
    WIDE = auto()        # Spread alargado
    VERY_WIDE = auto()   # Spread muito largo, evitar
    EXTREME = auto()     # Spread extremo, não operar


class LiquidityLevel(Enum):
    """Nível de liquidez."""
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    VERY_LOW = auto()


class MarketQuality(Enum):
    """Qualidade do mercado."""
    EXCELLENT = auto()
    GOOD = auto()
    FAIR = auto()
    POOR = auto()
    AVOID = auto()


@dataclass
class TickMetrics:
    """Métricas de tick."""
    tick_count: int
    avg_tick_size: float
    tick_frequency: float  # ticks por segundo
    up_ticks: int
    down_ticks: int
    unchanged_ticks: int
    tick_direction_ratio: float  # up_ticks / total


@dataclass
class SpreadMetrics:
    """Métricas de spread."""
    current_spread: float
    current_spread_pips: float
    avg_spread: float
    avg_spread_pips: float
    min_spread: float
    max_spread: float
    spread_volatility: float
    spread_condition: SpreadCondition
    spread_percentile: float  # vs histórico


@dataclass
class MicrostructureAnalysisResult:
    """Resultado da análise de microestrutura."""
    # Spread
    spread_metrics: SpreadMetrics
    spread_acceptable: bool
    
    # Liquidez
    liquidity_level: LiquidityLevel
    liquidity_score: float  # 0 a 1
    
    # Qualidade
    market_quality: MarketQuality
    quality_score: float
    
    # Ticks
    tick_metrics: Optional[TickMetrics]
    
    # Trading
    recommended_slippage: float  # Slippage esperado em pips
    position_size_adjustment: float  # 1.0 = normal, <1 = reduzir
    
    # Alertas
    warnings: List[str]
    
    recommendation: str
    details: Dict[str, Any]


class TickMicrostructureAnalyzer:
    """
    Analisador de microestrutura de mercado.
    
    Analisa spreads, ticks e liquidez para otimizar
    execução e evitar condições adversas.
    """
    
    # Spreads típicos por par (em pips)
    TYPICAL_SPREADS = {
        'EURUSD': 0.8,
        'GBPUSD': 1.2,
        'USDJPY': 0.9,
        'AUDUSD': 1.0,
        'USDCAD': 1.2,
        'USDCHF': 1.1,
        'NZDUSD': 1.3,
        'EURGBP': 1.0,
        'EURJPY': 1.3,
        'GBPJPY': 2.0,
        'XAUUSD': 2.5,
        'XAGUSD': 3.0,
    }
    
    # Multiplicadores de spread
    SPREAD_TIGHT = 0.8      # < 80% do típico
    SPREAD_NORMAL = 1.5     # < 150% do típico
    SPREAD_WIDE = 2.5       # < 250% do típico
    SPREAD_VERY_WIDE = 4.0  # < 400% do típico
    
    def __init__(
        self,
        logger: logging.Logger = None,
        spread_history_size: int = 100,
        tick_history_size: int = 500,
    ):
        self.logger = logger or logging.getLogger(__name__)
        
        # Históricos
        self.spread_history: Dict[str, deque] = {}
        self.tick_history: Dict[str, deque] = {}
        
        self.spread_history_size = spread_history_size
        self.tick_history_size = tick_history_size
    
    def analyze(
        self,
        symbol: str,
        current_bid: float,
        current_ask: float,
        point_value: float = 0.0001,  # Valor do ponto/pip
        ticks: List[Dict] = None,  # Histórico de ticks opcional
    ) -> MicrostructureAnalysisResult:
        """
        Analisa microestrutura do mercado.
        
        Args:
            symbol: Símbolo
            current_bid: Preço bid atual
            current_ask: Preço ask atual
            point_value: Valor do ponto (0.0001 para majors, 0.01 para JPY)
            ticks: Lista de ticks recentes [{price, time, volume}]
            
        Returns:
            MicrostructureAnalysisResult
        """
        # Normaliza símbolo
        symbol = symbol.upper()
        
        # Inicializa histórico se necessário
        if symbol not in self.spread_history:
            self.spread_history[symbol] = deque(maxlen=self.spread_history_size)
        if symbol not in self.tick_history:
            self.tick_history[symbol] = deque(maxlen=self.tick_history_size)
        
        # Calcula spread
        current_spread = current_ask - current_bid
        current_spread_pips = current_spread / point_value
        
        # Adiciona ao histórico
        self.spread_history[symbol].append({
            'spread': current_spread,
            'spread_pips': current_spread_pips,
            'time': datetime.now(),
        })
        
        # Análise de spread
        spread_metrics = self._analyze_spread(symbol, current_spread, current_spread_pips, point_value)
        
        # Processa ticks se disponíveis
        tick_metrics = None
        if ticks:
            for tick in ticks:
                self.tick_history[symbol].append(tick)
            tick_metrics = self._analyze_ticks(symbol)
        
        # Avalia liquidez
        liquidity_level, liquidity_score = self._assess_liquidity(
            spread_metrics, tick_metrics
        )
        
        # Qualidade do mercado
        market_quality, quality_score = self._assess_market_quality(
            spread_metrics, liquidity_level, tick_metrics
        )
        
        # Spread aceitável?
        spread_acceptable = spread_metrics.spread_condition not in [
            SpreadCondition.VERY_WIDE,
            SpreadCondition.EXTREME
        ]
        
        # Slippage esperado
        slippage = self._estimate_slippage(spread_metrics, liquidity_level)
        
        # Ajuste de posição
        position_adj = self._calculate_position_adjustment(
            spread_metrics, liquidity_level, market_quality
        )
        
        # Warnings
        warnings = self._generate_warnings(
            spread_metrics, liquidity_level, market_quality
        )
        
        # Recomendação
        recommendation = self._generate_recommendation(
            spread_acceptable, market_quality, liquidity_level, spread_metrics
        )
        
        return MicrostructureAnalysisResult(
            spread_metrics=spread_metrics,
            spread_acceptable=spread_acceptable,
            liquidity_level=liquidity_level,
            liquidity_score=liquidity_score,
            market_quality=market_quality,
            quality_score=quality_score,
            tick_metrics=tick_metrics,
            recommended_slippage=slippage,
            position_size_adjustment=position_adj,
            warnings=warnings,
            recommendation=recommendation,
            details={
                'symbol': symbol,
                'bid': current_bid,
                'ask': current_ask,
            }
        )
    
    def _analyze_spread(
        self,
        symbol: str,
        current_spread: float,
        current_spread_pips: float,
        point_value: float
    ) -> SpreadMetrics:
        """Analisa spread."""
        
        history = list(self.spread_history[symbol])
        
        # Médias
        if len(history) >= 10:
            spreads = [h['spread'] for h in history]
            spreads_pips = [h['spread_pips'] for h in history]
            
            avg_spread = np.mean(spreads)
            avg_spread_pips = np.mean(spreads_pips)
            min_spread = np.min(spreads)
            max_spread = np.max(spreads)
            spread_vol = np.std(spreads) / avg_spread if avg_spread > 0 else 0
            
            # Percentil
            percentile = (np.searchsorted(sorted(spreads_pips), current_spread_pips) / len(spreads_pips)) * 100
        else:
            avg_spread = current_spread
            avg_spread_pips = current_spread_pips
            min_spread = current_spread
            max_spread = current_spread
            spread_vol = 0
            percentile = 50
        
        # Spread típico do par
        typical = self.TYPICAL_SPREADS.get(symbol, 1.5)
        ratio = current_spread_pips / typical if typical > 0 else 1
        
        # Condição do spread
        if ratio < self.SPREAD_TIGHT:
            condition = SpreadCondition.TIGHT
        elif ratio < self.SPREAD_NORMAL:
            condition = SpreadCondition.NORMAL
        elif ratio < self.SPREAD_WIDE:
            condition = SpreadCondition.WIDE
        elif ratio < self.SPREAD_VERY_WIDE:
            condition = SpreadCondition.VERY_WIDE
        else:
            condition = SpreadCondition.EXTREME
        
        return SpreadMetrics(
            current_spread=current_spread,
            current_spread_pips=current_spread_pips,
            avg_spread=avg_spread,
            avg_spread_pips=avg_spread_pips,
            min_spread=min_spread,
            max_spread=max_spread,
            spread_volatility=spread_vol,
            spread_condition=condition,
            spread_percentile=percentile,
        )
    
    def _analyze_ticks(self, symbol: str) -> Optional[TickMetrics]:
        """Analisa ticks."""
        
        history = list(self.tick_history[symbol])
        
        if len(history) < 10:
            return None
        
        # Contagem de ticks
        tick_count = len(history)
        
        # Tamanho médio do tick
        prices = [t.get('price', 0) for t in history]
        price_changes = np.diff(prices)
        avg_tick = np.mean(np.abs(price_changes)) if len(price_changes) > 0 else 0
        
        # Frequência
        if len(history) >= 2:
            first_time = history[0].get('time', datetime.now())
            last_time = history[-1].get('time', datetime.now())
            
            if isinstance(first_time, str):
                first_time = datetime.fromisoformat(first_time)
            if isinstance(last_time, str):
                last_time = datetime.fromisoformat(last_time)
            
            duration = (last_time - first_time).total_seconds()
            frequency = tick_count / duration if duration > 0 else 0
        else:
            frequency = 0
        
        # Direção
        up_ticks = np.sum(price_changes > 0)
        down_ticks = np.sum(price_changes < 0)
        unchanged = np.sum(price_changes == 0)
        
        total = up_ticks + down_ticks + unchanged
        direction_ratio = up_ticks / total if total > 0 else 0.5
        
        return TickMetrics(
            tick_count=tick_count,
            avg_tick_size=avg_tick,
            tick_frequency=frequency,
            up_ticks=int(up_ticks),
            down_ticks=int(down_ticks),
            unchanged_ticks=int(unchanged),
            tick_direction_ratio=direction_ratio,
        )
    
    def _assess_liquidity(
        self,
        spread: SpreadMetrics,
        ticks: Optional[TickMetrics]
    ) -> Tuple[LiquidityLevel, float]:
        """Avalia liquidez."""
        
        score = 0.5
        
        # Baseado em spread
        if spread.spread_condition == SpreadCondition.TIGHT:
            score += 0.3
        elif spread.spread_condition == SpreadCondition.NORMAL:
            score += 0.1
        elif spread.spread_condition == SpreadCondition.WIDE:
            score -= 0.1
        elif spread.spread_condition == SpreadCondition.VERY_WIDE:
            score -= 0.25
        else:
            score -= 0.4
        
        # Baseado em ticks
        if ticks:
            if ticks.tick_frequency > 10:  # > 10 ticks/seg
                score += 0.2
            elif ticks.tick_frequency > 1:
                score += 0.1
            elif ticks.tick_frequency < 0.1:
                score -= 0.2
        
        score = max(0, min(1, score))
        
        if score >= 0.7:
            level = LiquidityLevel.HIGH
        elif score >= 0.5:
            level = LiquidityLevel.MEDIUM
        elif score >= 0.3:
            level = LiquidityLevel.LOW
        else:
            level = LiquidityLevel.VERY_LOW
        
        return level, score
    
    def _assess_market_quality(
        self,
        spread: SpreadMetrics,
        liquidity: LiquidityLevel,
        ticks: Optional[TickMetrics]
    ) -> Tuple[MarketQuality, float]:
        """Avalia qualidade do mercado."""
        
        score = 0.5
        
        # Spread
        if spread.spread_condition == SpreadCondition.TIGHT:
            score += 0.25
        elif spread.spread_condition == SpreadCondition.EXTREME:
            score -= 0.35
        elif spread.spread_condition == SpreadCondition.VERY_WIDE:
            score -= 0.2
        
        # Volatilidade do spread (estabilidade)
        if spread.spread_volatility < 0.1:
            score += 0.1
        elif spread.spread_volatility > 0.5:
            score -= 0.15
        
        # Liquidez
        if liquidity == LiquidityLevel.HIGH:
            score += 0.2
        elif liquidity == LiquidityLevel.VERY_LOW:
            score -= 0.25
        
        score = max(0, min(1, score))
        
        if score >= 0.8:
            quality = MarketQuality.EXCELLENT
        elif score >= 0.6:
            quality = MarketQuality.GOOD
        elif score >= 0.4:
            quality = MarketQuality.FAIR
        elif score >= 0.2:
            quality = MarketQuality.POOR
        else:
            quality = MarketQuality.AVOID
        
        return quality, score
    
    def _estimate_slippage(
        self,
        spread: SpreadMetrics,
        liquidity: LiquidityLevel
    ) -> float:
        """Estima slippage esperado em pips."""
        
        base_slippage = spread.current_spread_pips * 0.5
        
        # Ajusta por liquidez
        liquidity_mult = {
            LiquidityLevel.HIGH: 0.8,
            LiquidityLevel.MEDIUM: 1.0,
            LiquidityLevel.LOW: 1.5,
            LiquidityLevel.VERY_LOW: 2.5,
        }
        
        mult = liquidity_mult.get(liquidity, 1.0)
        
        return round(base_slippage * mult, 2)
    
    def _calculate_position_adjustment(
        self,
        spread: SpreadMetrics,
        liquidity: LiquidityLevel,
        quality: MarketQuality
    ) -> float:
        """Calcula ajuste de tamanho de posição."""
        
        adjustment = 1.0
        
        # Por spread
        if spread.spread_condition == SpreadCondition.WIDE:
            adjustment *= 0.8
        elif spread.spread_condition == SpreadCondition.VERY_WIDE:
            adjustment *= 0.5
        elif spread.spread_condition == SpreadCondition.EXTREME:
            adjustment *= 0.0  # Não operar
        
        # Por liquidez
        if liquidity == LiquidityLevel.LOW:
            adjustment *= 0.8
        elif liquidity == LiquidityLevel.VERY_LOW:
            adjustment *= 0.5
        
        # Por qualidade
        if quality == MarketQuality.POOR:
            adjustment *= 0.7
        elif quality == MarketQuality.AVOID:
            adjustment *= 0.0
        
        return round(adjustment, 2)
    
    def _generate_warnings(
        self,
        spread: SpreadMetrics,
        liquidity: LiquidityLevel,
        quality: MarketQuality
    ) -> List[str]:
        """Gera avisos."""
        
        warnings = []
        
        if spread.spread_condition == SpreadCondition.EXTREME:
            warnings.append("🚫 Spread extremo - NÃO OPERAR")
        elif spread.spread_condition == SpreadCondition.VERY_WIDE:
            warnings.append("⚠️ Spread muito alargado")
        elif spread.spread_condition == SpreadCondition.WIDE:
            warnings.append("⚠️ Spread acima do normal")
        
        if spread.spread_volatility > 0.5:
            warnings.append("⚠️ Spread instável")
        
        if liquidity == LiquidityLevel.VERY_LOW:
            warnings.append("⚠️ Liquidez muito baixa")
        elif liquidity == LiquidityLevel.LOW:
            warnings.append("⚠️ Liquidez reduzida")
        
        if quality == MarketQuality.AVOID:
            warnings.append("🚫 Qualidade do mercado inadequada")
        elif quality == MarketQuality.POOR:
            warnings.append("⚠️ Qualidade do mercado ruim")
        
        return warnings
    
    def _generate_recommendation(
        self,
        spread_ok: bool,
        quality: MarketQuality,
        liquidity: LiquidityLevel,
        spread: SpreadMetrics
    ) -> str:
        """Gera recomendação."""
        
        if not spread_ok:
            return f"🚫 NÃO OPERAR - Spread {spread.current_spread_pips:.1f} pips"
        
        if quality == MarketQuality.AVOID:
            return "🚫 NÃO OPERAR - Qualidade do mercado inadequada"
        
        if quality == MarketQuality.EXCELLENT:
            return f"✅ EXCELENTE - Spread {spread.current_spread_pips:.1f} pips, liquidez {liquidity.name}"
        
        if quality == MarketQuality.GOOD:
            return f"✅ BOM - Spread {spread.current_spread_pips:.1f} pips"
        
        if quality == MarketQuality.FAIR:
            return f"⚠️ ACEITÁVEL - Spread {spread.current_spread_pips:.1f} pips, cuidado com slippage"
        
        return f"⚠️ CAUTELA - Spread {spread.current_spread_pips:.1f} pips, reduzir exposição"
    
    def is_good_to_trade(
        self,
        symbol: str,
        bid: float,
        ask: float,
        point_value: float = 0.0001
    ) -> Tuple[bool, str]:
        """
        Verifica rapidamente se é bom momento para operar.
        
        Returns:
            (is_good, reason)
        """
        result = self.analyze(symbol, bid, ask, point_value)
        
        if not result.spread_acceptable:
            return False, f"Spread alto: {result.spread_metrics.current_spread_pips:.1f} pips"
        
        if result.market_quality == MarketQuality.AVOID:
            return False, "Qualidade do mercado inadequada"
        
        if result.position_size_adjustment < 0.5:
            return False, "Condições de mercado ruins"
        
        return True, f"OK - Spread: {result.spread_metrics.current_spread_pips:.1f} pips"
    
    def to_dict(self, result: MicrostructureAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        tick_dict = None
        if result.tick_metrics:
            t = result.tick_metrics
            tick_dict = {
                'count': t.tick_count,
                'avg_size': round(t.avg_tick_size, 6),
                'frequency': round(t.tick_frequency, 2),
                'up_ticks': t.up_ticks,
                'down_ticks': t.down_ticks,
                'direction_ratio': round(t.tick_direction_ratio, 2),
            }
        
        s = result.spread_metrics
        spread_dict = {
            'current_pips': round(s.current_spread_pips, 2),
            'avg_pips': round(s.avg_spread_pips, 2),
            'condition': s.spread_condition.name,
            'percentile': round(s.spread_percentile, 1),
            'volatility': round(s.spread_volatility, 3),
        }
        
        return {
            'spread': spread_dict,
            'spread_acceptable': result.spread_acceptable,
            'liquidity': {
                'level': result.liquidity_level.name,
                'score': round(result.liquidity_score, 2),
            },
            'quality': {
                'level': result.market_quality.name,
                'score': round(result.quality_score, 2),
            },
            'ticks': tick_dict,
            'recommended_slippage_pips': result.recommended_slippage,
            'position_adjustment': result.position_size_adjustment,
            'warnings': result.warnings,
            'recommendation': result.recommendation,
        }
