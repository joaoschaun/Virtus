"""
VIRTUS Harmonic Patterns
=========================

Detecção de padrões harmônicos:
- Gartley
- Bat
- Butterfly
- Crab
- Shark
- Cypher
- ABCD
- Three Drives
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class PatternType(Enum):
    """Tipos de padrões harmônicos."""
    GARTLEY = auto()
    BAT = auto()
    BUTTERFLY = auto()
    CRAB = auto()
    SHARK = auto()
    CYPHER = auto()
    ABCD = auto()
    THREE_DRIVES = auto()


class PatternDirection(Enum):
    """Direção do padrão."""
    BULLISH = auto()
    BEARISH = auto()


class PatternStatus(Enum):
    """Status do padrão."""
    FORMING = auto()     # Em formação
    COMPLETE = auto()    # Completo, aguardando entrada
    TRIGGERED = auto()   # Ativado
    INVALIDATED = auto() # Invalidado


@dataclass
class PatternPoint:
    """Um ponto do padrão (X, A, B, C, D)."""
    name: str  # 'X', 'A', 'B', 'C', 'D'
    index: int
    price: float
    timestamp: Optional[datetime] = None


@dataclass
class FibRatio:
    """Razão Fibonacci esperada."""
    leg: str  # Ex: 'AB/XA'
    expected: float  # Razão esperada
    actual: float  # Razão real
    tolerance: float  # Tolerância
    is_valid: bool


@dataclass
class HarmonicPattern:
    """Um padrão harmônico identificado."""
    type: PatternType
    direction: PatternDirection
    status: PatternStatus
    points: Dict[str, PatternPoint]  # X, A, B, C, D
    ratios: List[FibRatio]
    prz_low: float  # Potential Reversal Zone
    prz_high: float
    stop_loss: float
    target_1: float  # 0.382 de AD
    target_2: float  # 0.618 de AD
    target_3: float  # Ponto A
    confidence: float  # 0 a 1
    score: float  # Qualidade do padrão


@dataclass
class HarmonicResult:
    """Resultado da análise harmônica."""
    patterns: List[HarmonicPattern]
    best_pattern: Optional[HarmonicPattern]
    actionable_patterns: List[HarmonicPattern]
    forming_patterns: List[HarmonicPattern]


class HarmonicPatternDetector:
    """
    Detector de padrões harmônicos.
    
    Identifica padrões baseados em razões Fibonacci
    com alta precisão e cálculo de zonas de reversão.
    """
    
    # Definição das razões Fibonacci para cada padrão
    PATTERNS = {
        PatternType.GARTLEY: {
            'AB_XA': (0.618, 0.01),  # (valor esperado, tolerância)
            'BC_AB': ((0.382, 0.886), 0.02),  # Range
            'CD_BC': ((1.272, 1.618), 0.02),
            'AD_XA': (0.786, 0.02),
        },
        PatternType.BAT: {
            'AB_XA': ((0.382, 0.5), 0.02),
            'BC_AB': ((0.382, 0.886), 0.02),
            'CD_BC': ((1.618, 2.618), 0.03),
            'AD_XA': (0.886, 0.02),
        },
        PatternType.BUTTERFLY: {
            'AB_XA': (0.786, 0.02),
            'BC_AB': ((0.382, 0.886), 0.02),
            'CD_BC': ((1.618, 2.618), 0.03),
            'AD_XA': ((1.272, 1.618), 0.03),
        },
        PatternType.CRAB: {
            'AB_XA': ((0.382, 0.618), 0.02),
            'BC_AB': ((0.382, 0.886), 0.02),
            'CD_BC': ((2.618, 3.618), 0.05),
            'AD_XA': (1.618, 0.03),
        },
        PatternType.SHARK: {
            'AB_XA': ((1.13, 1.618), 0.03),
            'BC_AB': ((1.13, 1.618), 0.03),
            'CD_BC': ((1.618, 2.236), 0.03),
            'AD_XA': ((0.886, 1.13), 0.03),
        },
        PatternType.CYPHER: {
            'AB_XA': ((0.382, 0.618), 0.02),
            'BC_AB': ((1.13, 1.414), 0.03),
            'CD_XC': (0.786, 0.02),
        },
    }
    
    def __init__(
        self,
        swing_strength: int = 5,
        min_pattern_bars: int = 15,
        max_pattern_bars: int = 150,
    ):
        self.swing_strength = swing_strength
        self.min_pattern_bars = min_pattern_bars
        self.max_pattern_bars = max_pattern_bars
    
    def analyze(self, df: pd.DataFrame) -> HarmonicResult:
        """
        Analisa padrões harmônicos.
        
        Args:
            df: DataFrame com OHLCV
            
        Returns:
            HarmonicResult
        """
        if df is None or len(df) < 50:
            return self._empty_result()
        
        high = df['high'].values
        low = df['low'].values
        
        # Encontra todos os swings
        swing_highs = self._find_swings(high, is_high=True)
        swing_lows = self._find_swings(low, is_high=False)
        
        # Combina e ordena swings
        all_swings = []
        for idx, price in swing_highs:
            all_swings.append((idx, price, 'high'))
        for idx, price in swing_lows:
            all_swings.append((idx, price, 'low'))
        
        all_swings.sort(key=lambda x: x[0])
        
        patterns = []
        
        # Procura padrões XABCD
        patterns.extend(self._find_xabcd_patterns(all_swings, df))
        
        # Procura padrões ABCD simples
        patterns.extend(self._find_abcd_patterns(all_swings, df))
        
        # Ordena por score
        patterns.sort(key=lambda x: x.score, reverse=True)
        
        # Separa padrões
        actionable = [p for p in patterns if p.status == PatternStatus.COMPLETE]
        forming = [p for p in patterns if p.status == PatternStatus.FORMING]
        
        best = patterns[0] if patterns else None
        
        return HarmonicResult(
            patterns=patterns,
            best_pattern=best,
            actionable_patterns=actionable,
            forming_patterns=forming,
        )
    
    def _find_swings(
        self,
        data: np.ndarray,
        is_high: bool,
    ) -> List[Tuple[int, float]]:
        """Encontra swing points."""
        swings = []
        strength = self.swing_strength
        
        for i in range(strength, len(data) - strength):
            is_swing = True
            
            for j in range(1, strength + 1):
                if is_high:
                    if data[i] <= data[i - j] or data[i] <= data[i + j]:
                        is_swing = False
                        break
                else:
                    if data[i] >= data[i - j] or data[i] >= data[i + j]:
                        is_swing = False
                        break
            
            if is_swing:
                swings.append((i, data[i]))
        
        return swings
    
    def _find_xabcd_patterns(
        self,
        swings: List[Tuple[int, float, str]],
        df: pd.DataFrame,
    ) -> List[HarmonicPattern]:
        """Encontra padrões XABCD (Gartley, Bat, Butterfly, Crab, Shark)."""
        patterns = []
        
        if len(swings) < 5:
            return patterns
        
        # Tenta diferentes combinações de 5 pontos
        for i in range(len(swings) - 4):
            x = swings[i]
            a = swings[i + 1]
            b = swings[i + 2]
            c = swings[i + 3]
            d = swings[i + 4]
            
            # Verifica se respeita tempo mínimo/máximo
            bars = d[0] - x[0]
            if bars < self.min_pattern_bars or bars > self.max_pattern_bars:
                continue
            
            # Verifica alternância de highs e lows
            if not self._verify_alternation([x, a, b, c, d]):
                continue
            
            # Determina direção
            if x[2] == 'low' and a[2] == 'high':
                direction = PatternDirection.BULLISH
            elif x[2] == 'high' and a[2] == 'low':
                direction = PatternDirection.BEARISH
            else:
                continue
            
            # Tenta identificar qual padrão
            for pattern_type, ratios_def in self.PATTERNS.items():
                if pattern_type in [PatternType.CYPHER]:
                    continue  # Cypher tem lógica diferente
                
                pattern = self._validate_pattern(
                    pattern_type=pattern_type,
                    direction=direction,
                    points=[x, a, b, c, d],
                    ratios_def=ratios_def,
                    df=df,
                )
                
                if pattern:
                    patterns.append(pattern)
        
        return patterns
    
    def _verify_alternation(
        self,
        swings: List[Tuple[int, float, str]],
    ) -> bool:
        """Verifica se os swings alternam entre high e low."""
        for i in range(len(swings) - 1):
            if swings[i][2] == swings[i + 1][2]:
                return False
        return True
    
    def _validate_pattern(
        self,
        pattern_type: PatternType,
        direction: PatternDirection,
        points: List[Tuple[int, float, str]],
        ratios_def: Dict,
        df: pd.DataFrame,
    ) -> Optional[HarmonicPattern]:
        """Valida um padrão específico."""
        x, a, b, c, d = points
        
        # Calcula as legs
        xa = abs(a[1] - x[1])
        ab = abs(b[1] - a[1])
        bc = abs(c[1] - b[1])
        cd = abs(d[1] - c[1])
        ad = abs(d[1] - a[1])
        
        if xa == 0:
            return None
        
        # Calcula razões
        ratios = []
        all_valid = True
        
        # AB/XA
        if 'AB_XA' in ratios_def:
            expected, tol = ratios_def['AB_XA']
            actual = ab / xa
            is_valid = self._check_ratio(actual, expected, tol)
            ratios.append(FibRatio('AB/XA', expected if isinstance(expected, float) else np.mean(expected), actual, tol, is_valid))
            if not is_valid:
                all_valid = False
        
        # BC/AB
        if 'BC_AB' in ratios_def and ab != 0:
            expected, tol = ratios_def['BC_AB']
            actual = bc / ab
            is_valid = self._check_ratio(actual, expected, tol)
            ratios.append(FibRatio('BC/AB', expected if isinstance(expected, float) else np.mean(expected), actual, tol, is_valid))
            if not is_valid:
                all_valid = False
        
        # CD/BC
        if 'CD_BC' in ratios_def and bc != 0:
            expected, tol = ratios_def['CD_BC']
            actual = cd / bc
            is_valid = self._check_ratio(actual, expected, tol)
            ratios.append(FibRatio('CD/BC', expected if isinstance(expected, float) else np.mean(expected), actual, tol, is_valid))
            if not is_valid:
                all_valid = False
        
        # AD/XA
        if 'AD_XA' in ratios_def:
            expected, tol = ratios_def['AD_XA']
            actual = ad / xa
            is_valid = self._check_ratio(actual, expected, tol)
            ratios.append(FibRatio('AD/XA', expected if isinstance(expected, float) else np.mean(expected), actual, tol, is_valid))
            if not is_valid:
                all_valid = False
        
        if not all_valid:
            return None
        
        # Calcula PRZ e targets
        if direction == PatternDirection.BULLISH:
            prz_low = min(d[1], x[1])
            prz_high = d[1] + (xa * 0.05)
            stop_loss = prz_low - (xa * 0.1)
            target_1 = d[1] + (ad * 0.382)
            target_2 = d[1] + (ad * 0.618)
            target_3 = a[1]
        else:
            prz_low = d[1] - (xa * 0.05)
            prz_high = max(d[1], x[1])
            stop_loss = prz_high + (xa * 0.1)
            target_1 = d[1] - (ad * 0.382)
            target_2 = d[1] - (ad * 0.618)
            target_3 = a[1]
        
        # Calcula confidence e score
        confidence = sum(1 for r in ratios if r.is_valid) / len(ratios) if ratios else 0
        
        # Score baseado em múltiplos fatores
        ratio_score = sum(1 - min(abs(r.actual - r.expected) / 0.1, 1) for r in ratios) / len(ratios) if ratios else 0
        
        # Determina status
        current_price = df['close'].values[-1]
        
        if direction == PatternDirection.BULLISH:
            if current_price < prz_high:
                status = PatternStatus.COMPLETE
            elif current_price > target_1:
                status = PatternStatus.TRIGGERED
            else:
                status = PatternStatus.FORMING
        else:
            if current_price > prz_low:
                status = PatternStatus.COMPLETE
            elif current_price < target_1:
                status = PatternStatus.TRIGGERED
            else:
                status = PatternStatus.FORMING
        
        # Cria pontos do padrão
        pattern_points = {
            'X': PatternPoint('X', x[0], x[1]),
            'A': PatternPoint('A', a[0], a[1]),
            'B': PatternPoint('B', b[0], b[1]),
            'C': PatternPoint('C', c[0], c[1]),
            'D': PatternPoint('D', d[0], d[1]),
        }
        
        return HarmonicPattern(
            type=pattern_type,
            direction=direction,
            status=status,
            points=pattern_points,
            ratios=ratios,
            prz_low=prz_low,
            prz_high=prz_high,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            confidence=confidence,
            score=ratio_score * confidence,
        )
    
    def _check_ratio(
        self,
        actual: float,
        expected: float | Tuple[float, float],
        tolerance: float,
    ) -> bool:
        """Verifica se a razão está dentro da tolerância."""
        if isinstance(expected, tuple):
            # Range
            return expected[0] - tolerance <= actual <= expected[1] + tolerance
        else:
            # Valor único
            return abs(actual - expected) <= tolerance
    
    def _find_abcd_patterns(
        self,
        swings: List[Tuple[int, float, str]],
        df: pd.DataFrame,
    ) -> List[HarmonicPattern]:
        """Encontra padrões ABCD simples."""
        patterns = []
        
        if len(swings) < 4:
            return patterns
        
        for i in range(len(swings) - 3):
            a = swings[i]
            b = swings[i + 1]
            c = swings[i + 2]
            d = swings[i + 3]
            
            # Verifica alternância
            if not self._verify_alternation([a, b, c, d]):
                continue
            
            # Determina direção
            if a[2] == 'low':
                direction = PatternDirection.BULLISH
            else:
                direction = PatternDirection.BEARISH
            
            # Calcula legs
            ab = abs(b[1] - a[1])
            bc = abs(c[1] - b[1])
            cd = abs(d[1] - c[1])
            
            if ab == 0 or bc == 0:
                continue
            
            # ABCD: AB = CD, BC é retração de AB
            bc_ab = bc / ab
            cd_ab = cd / ab
            
            # Verifica se BC é retração válida (0.382 - 0.886)
            if not (0.382 - 0.05 <= bc_ab <= 0.886 + 0.05):
                continue
            
            # Verifica se CD é igual a AB (tolerância de 20%)
            if not (0.8 <= cd_ab <= 1.2):
                continue
            
            ratios = [
                FibRatio('BC/AB', 0.618, bc_ab, 0.15, 0.382 <= bc_ab <= 0.886),
                FibRatio('CD/AB', 1.0, cd_ab, 0.2, 0.8 <= cd_ab <= 1.2),
            ]
            
            # Calcula targets
            if direction == PatternDirection.BULLISH:
                stop_loss = d[1] - (ab * 0.2)
                target_1 = d[1] + (ab * 0.382)
                target_2 = d[1] + (ab * 0.618)
                target_3 = d[1] + ab
                prz_low = d[1] - (ab * 0.05)
                prz_high = d[1] + (ab * 0.05)
            else:
                stop_loss = d[1] + (ab * 0.2)
                target_1 = d[1] - (ab * 0.382)
                target_2 = d[1] - (ab * 0.618)
                target_3 = d[1] - ab
                prz_low = d[1] - (ab * 0.05)
                prz_high = d[1] + (ab * 0.05)
            
            confidence = 0.8  # ABCD é mais simples, confiança fixa
            score = (1 - abs(cd_ab - 1)) * confidence
            
            pattern_points = {
                'A': PatternPoint('A', a[0], a[1]),
                'B': PatternPoint('B', b[0], b[1]),
                'C': PatternPoint('C', c[0], c[1]),
                'D': PatternPoint('D', d[0], d[1]),
            }
            
            patterns.append(HarmonicPattern(
                type=PatternType.ABCD,
                direction=direction,
                status=PatternStatus.COMPLETE,
                points=pattern_points,
                ratios=ratios,
                prz_low=prz_low,
                prz_high=prz_high,
                stop_loss=stop_loss,
                target_1=target_1,
                target_2=target_2,
                target_3=target_3,
                confidence=confidence,
                score=score,
            ))
        
        return patterns
    
    def _empty_result(self) -> HarmonicResult:
        """Retorna resultado vazio."""
        return HarmonicResult(
            patterns=[],
            best_pattern=None,
            actionable_patterns=[],
            forming_patterns=[],
        )
    
    def to_dict(self, result: HarmonicResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        patterns_list = []
        for p in result.patterns:
            points_dict = {
                name: {'index': pt.index, 'price': round(pt.price, 5)}
                for name, pt in p.points.items()
            }
            
            ratios_list = [
                {
                    'leg': r.leg,
                    'expected': round(r.expected, 3),
                    'actual': round(r.actual, 3),
                    'valid': r.is_valid,
                }
                for r in p.ratios
            ]
            
            patterns_list.append({
                'type': p.type.name,
                'direction': p.direction.name,
                'status': p.status.name,
                'points': points_dict,
                'ratios': ratios_list,
                'prz': {'low': round(p.prz_low, 5), 'high': round(p.prz_high, 5)},
                'stop_loss': round(p.stop_loss, 5),
                'targets': {
                    'target_1': round(p.target_1, 5),
                    'target_2': round(p.target_2, 5),
                    'target_3': round(p.target_3, 5),
                },
                'confidence': round(p.confidence, 3),
                'score': round(p.score, 3),
            })
        
        best = None
        if result.best_pattern:
            best = {
                'type': result.best_pattern.type.name,
                'direction': result.best_pattern.direction.name,
                'score': round(result.best_pattern.score, 3),
            }
        
        return {
            'patterns': patterns_list,
            'best_pattern': best,
            'actionable_count': len(result.actionable_patterns),
            'forming_count': len(result.forming_patterns),
        }
