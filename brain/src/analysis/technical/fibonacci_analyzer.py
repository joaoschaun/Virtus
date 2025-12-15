"""
VIRTUS Fibonacci Analyzer
==========================

Análise completa de Fibonacci:
- Retracements
- Extensions
- Expansions
- Clusters (confluência de níveis)
- Auto-detecção de swings
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class FibonacciType(Enum):
    """Tipo de Fibonacci."""
    RETRACEMENT = auto()
    EXTENSION = auto()
    EXPANSION = auto()


class FibLevel(Enum):
    """Níveis de Fibonacci padrão."""
    FIB_0 = 0.0
    FIB_236 = 0.236
    FIB_382 = 0.382
    FIB_500 = 0.5
    FIB_618 = 0.618
    FIB_786 = 0.786
    FIB_100 = 1.0
    FIB_1272 = 1.272
    FIB_1618 = 1.618
    FIB_2000 = 2.0
    FIB_2618 = 2.618
    FIB_4236 = 4.236


@dataclass
class FibonacciLevel:
    """Um nível de Fibonacci calculado."""
    level_name: str  # Ex: "0.618"
    level_value: float  # 0.618
    price: float  # Preço no nível
    type: FibonacciType
    is_key_level: bool  # 0.382, 0.5, 0.618, 0.786
    touches: int  # Vezes que preço tocou
    strength: float  # 0 a 1


@dataclass
class FibonacciZone:
    """Zona de Fibonacci (cluster de níveis)."""
    price_low: float
    price_high: float
    center: float
    confluent_levels: List[str]
    strength: float  # Baseado no número de níveis confluentes


@dataclass
class FibonacciAnalysis:
    """Análise completa de Fibonacci."""
    type: FibonacciType
    swing_low: Tuple[int, float]  # (índice, preço)
    swing_high: Tuple[int, float]
    levels: List[FibonacciLevel]
    direction: str  # 'up' ou 'down'
    current_price_level: Optional[str]  # Nível atual do preço


@dataclass
class FibonacciResult:
    """Resultado completo da análise."""
    analyses: List[FibonacciAnalysis]
    clusters: List[FibonacciZone]
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]
    golden_zone: Optional[Tuple[float, float]]  # 0.618 - 0.786
    in_golden_zone: bool


class FibonacciAnalyzer:
    """
    Analisador de Fibonacci avançado.
    
    Características:
    - Auto-detecção de swings significativos
    - Retracements, Extensions, Expansions
    - Detecção de clusters (confluência)
    - Identificação de zonas douradas
    """
    
    # Níveis de retracement
    RETRACEMENT_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    
    # Níveis de extension
    EXTENSION_LEVELS = [1.0, 1.272, 1.618, 2.0, 2.618, 4.236]
    
    # Níveis chave (maior relevância)
    KEY_LEVELS = {0.382, 0.5, 0.618, 0.786, 1.618}
    
    def __init__(
        self,
        swing_strength: int = 5,
        max_swings: int = 3,
        cluster_tolerance: float = 0.001,  # 0.1%
    ):
        self.swing_strength = swing_strength
        self.max_swings = max_swings
        self.cluster_tolerance = cluster_tolerance
    
    def analyze(self, df: pd.DataFrame) -> FibonacciResult:
        """
        Análise completa de Fibonacci.
        
        Args:
            df: DataFrame com OHLCV
            
        Returns:
            FibonacciResult
        """
        if df is None or len(df) < 50:
            return self._empty_result()
        
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        current_price = close[-1]
        
        # Encontra swings significativos
        swing_highs = self._find_significant_swings(high, True)
        swing_lows = self._find_significant_swings(low, False)
        
        analyses = []
        all_levels = []
        
        # Gera análises para os últimos swings
        for i in range(min(self.max_swings, len(swing_highs), len(swing_lows))):
            # Retracement bullish (baixo para alto)
            if swing_lows and swing_highs:
                low_idx = len(low) - 1 - swing_lows[i][0] if i < len(swing_lows) else None
                high_idx = len(high) - 1 - swing_highs[i][0] if i < len(swing_highs) else None
                
                if low_idx is not None and high_idx is not None:
                    # Determina direção baseado na sequência
                    if low_idx < high_idx:
                        # Movimento de alta, retracement para baixo
                        analysis = self._calculate_retracement(
                            swing_low=(low_idx, low[low_idx]),
                            swing_high=(high_idx, high[high_idx]),
                            direction='up',
                            current_price=current_price,
                        )
                        analyses.append(analysis)
                        all_levels.extend(analysis.levels)
                    else:
                        # Movimento de baixa, retracement para cima
                        analysis = self._calculate_retracement(
                            swing_low=(low_idx, low[low_idx]),
                            swing_high=(high_idx, high[high_idx]),
                            direction='down',
                            current_price=current_price,
                        )
                        analyses.append(analysis)
                        all_levels.extend(analysis.levels)
        
        # Usa o swing mais recente para extension
        if len(swing_highs) >= 2 and len(swing_lows) >= 1:
            extension_analysis = self._calculate_extension(
                swing_high_1=(len(high) - 1 - swing_highs[1][0], swing_highs[1][1]),
                swing_low=(len(low) - 1 - swing_lows[0][0], swing_lows[0][1]),
                swing_high_2=(len(high) - 1 - swing_highs[0][0], swing_highs[0][1]),
                current_price=current_price,
            )
            if extension_analysis:
                analyses.append(extension_analysis)
                all_levels.extend(extension_analysis.levels)
        
        # Encontra clusters
        clusters = self._find_clusters(all_levels, current_price)
        
        # Encontra suporte e resistência mais próximos
        supports = [l.price for l in all_levels if l.price < current_price]
        resistances = [l.price for l in all_levels if l.price > current_price]
        
        nearest_support = max(supports) if supports else None
        nearest_resistance = min(resistances) if resistances else None
        
        # Identifica Golden Zone
        golden_zone = None
        in_golden_zone = False
        
        for analysis in analyses:
            if analysis.type == FibonacciType.RETRACEMENT:
                fib_618 = None
                fib_786 = None
                
                for level in analysis.levels:
                    if abs(level.level_value - 0.618) < 0.001:
                        fib_618 = level.price
                    elif abs(level.level_value - 0.786) < 0.001:
                        fib_786 = level.price
                
                if fib_618 and fib_786:
                    golden_zone = (min(fib_618, fib_786), max(fib_618, fib_786))
                    in_golden_zone = golden_zone[0] <= current_price <= golden_zone[1]
                    break
        
        return FibonacciResult(
            analyses=analyses,
            clusters=clusters,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            golden_zone=golden_zone,
            in_golden_zone=in_golden_zone,
        )
    
    def _find_significant_swings(
        self,
        data: np.ndarray,
        is_high: bool,
    ) -> List[Tuple[int, float]]:
        """
        Encontra swings significativos.
        
        Retorna lista de (índice_reverso, valor) ordenada por recência.
        """
        swings = []
        strength = self.swing_strength
        
        # Percorre de trás para frente
        for i in range(len(data) - strength - 1, strength, -1):
            is_swing = True
            
            if is_high:
                # Swing High
                for j in range(1, strength + 1):
                    if data[i] <= data[i - j] or data[i] <= data[i + j]:
                        is_swing = False
                        break
            else:
                # Swing Low
                for j in range(1, strength + 1):
                    if data[i] >= data[i - j] or data[i] >= data[i + j]:
                        is_swing = False
                        break
            
            if is_swing:
                # Índice reverso (0 = mais recente)
                reverse_idx = len(data) - 1 - i
                swings.append((reverse_idx, data[i]))
                
                if len(swings) >= self.max_swings * 2:
                    break
        
        return swings
    
    def _calculate_retracement(
        self,
        swing_low: Tuple[int, float],
        swing_high: Tuple[int, float],
        direction: str,
        current_price: float,
    ) -> FibonacciAnalysis:
        """Calcula níveis de retracement."""
        low_price = swing_low[1]
        high_price = swing_high[1]
        price_range = high_price - low_price
        
        levels = []
        current_level = None
        
        for level in self.RETRACEMENT_LEVELS:
            if direction == 'up':
                # Retração de um movimento de alta
                price = high_price - (price_range * level)
            else:
                # Retração de um movimento de baixa
                price = low_price + (price_range * level)
            
            is_key = level in self.KEY_LEVELS
            
            fib_level = FibonacciLevel(
                level_name=f"{level:.3f}",
                level_value=level,
                price=price,
                type=FibonacciType.RETRACEMENT,
                is_key_level=is_key,
                touches=0,
                strength=0.8 if is_key else 0.5,
            )
            levels.append(fib_level)
            
            # Verifica se preço atual está próximo deste nível
            tolerance = price_range * 0.01  # 1% do range
            if abs(current_price - price) < tolerance:
                current_level = f"{level:.3f}"
        
        return FibonacciAnalysis(
            type=FibonacciType.RETRACEMENT,
            swing_low=swing_low,
            swing_high=swing_high,
            levels=levels,
            direction=direction,
            current_price_level=current_level,
        )
    
    def _calculate_extension(
        self,
        swing_high_1: Tuple[int, float],
        swing_low: Tuple[int, float],
        swing_high_2: Tuple[int, float],
        current_price: float,
    ) -> Optional[FibonacciAnalysis]:
        """Calcula níveis de extension."""
        # Movimento inicial
        initial_move = swing_high_1[1] - swing_low[1]
        
        if abs(initial_move) < 0.00001:
            return None
        
        levels = []
        current_level = None
        
        for level in self.EXTENSION_LEVELS:
            # Extension projetada do swing low
            price = swing_low[1] + (initial_move * level)
            is_key = level in self.KEY_LEVELS
            
            fib_level = FibonacciLevel(
                level_name=f"{level:.3f}",
                level_value=level,
                price=price,
                type=FibonacciType.EXTENSION,
                is_key_level=is_key,
                touches=0,
                strength=0.8 if is_key else 0.5,
            )
            levels.append(fib_level)
            
            tolerance = abs(initial_move) * 0.01
            if abs(current_price - price) < tolerance:
                current_level = f"{level:.3f}"
        
        return FibonacciAnalysis(
            type=FibonacciType.EXTENSION,
            swing_low=swing_low,
            swing_high=swing_high_2,
            levels=levels,
            direction='up' if initial_move > 0 else 'down',
            current_price_level=current_level,
        )
    
    def _find_clusters(
        self,
        all_levels: List[FibonacciLevel],
        current_price: float,
    ) -> List[FibonacciZone]:
        """Encontra clusters de níveis Fibonacci."""
        if not all_levels:
            return []
        
        clusters = []
        prices = sorted([l.price for l in all_levels])
        
        if not prices:
            return []
        
        # Agrupa níveis próximos
        tolerance = current_price * self.cluster_tolerance
        
        i = 0
        while i < len(prices):
            cluster_prices = [prices[i]]
            cluster_levels = []
            
            # Encontra níveis no cluster
            j = i + 1
            while j < len(prices) and prices[j] - prices[i] < tolerance:
                cluster_prices.append(prices[j])
                j += 1
            
            # Se há confluência (2+ níveis)
            if len(cluster_prices) >= 2:
                # Encontra os nomes dos níveis
                for level in all_levels:
                    for cp in cluster_prices:
                        if abs(level.price - cp) < tolerance / 2:
                            cluster_levels.append(level.level_name)
                
                cluster = FibonacciZone(
                    price_low=min(cluster_prices),
                    price_high=max(cluster_prices),
                    center=np.mean(cluster_prices),
                    confluent_levels=list(set(cluster_levels)),
                    strength=min(1.0, len(cluster_prices) / 5),
                )
                clusters.append(cluster)
            
            i = j if j > i else i + 1
        
        return clusters
    
    def _empty_result(self) -> FibonacciResult:
        """Retorna resultado vazio."""
        return FibonacciResult(
            analyses=[],
            clusters=[],
            nearest_support=None,
            nearest_resistance=None,
            golden_zone=None,
            in_golden_zone=False,
        )
    
    def to_dict(self, result: FibonacciResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        analyses_list = []
        for analysis in result.analyses:
            levels_list = []
            for level in analysis.levels:
                levels_list.append({
                    'name': level.level_name,
                    'value': level.level_value,
                    'price': round(level.price, 5),
                    'is_key': level.is_key_level,
                    'strength': round(level.strength, 2),
                })
            
            analyses_list.append({
                'type': analysis.type.name,
                'direction': analysis.direction,
                'levels': levels_list,
                'current_level': analysis.current_price_level,
            })
        
        clusters_list = []
        for cluster in result.clusters:
            clusters_list.append({
                'low': round(cluster.price_low, 5),
                'high': round(cluster.price_high, 5),
                'center': round(cluster.center, 5),
                'levels': cluster.confluent_levels,
                'strength': round(cluster.strength, 2),
            })
        
        golden = None
        if result.golden_zone:
            golden = {
                'low': round(result.golden_zone[0], 5),
                'high': round(result.golden_zone[1], 5),
            }
        
        return {
            'analyses': analyses_list,
            'clusters': clusters_list,
            'nearest_support': round(result.nearest_support, 5) if result.nearest_support else None,
            'nearest_resistance': round(result.nearest_resistance, 5) if result.nearest_resistance else None,
            'golden_zone': golden,
            'in_golden_zone': result.in_golden_zone,
        }
