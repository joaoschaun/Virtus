"""
BRAIN - Pattern Recognition
Reconhecimento de padrões de preço
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np


class PatternType(Enum):
    """Tipos de padrões"""
    # Candlestick
    DOJI = "doji"
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    ENGULFING = "engulfing"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    HARAMI = "harami"
    PIERCING = "piercing"
    DARK_CLOUD = "dark_cloud"
    SPINNING_TOP = "spinning_top"
    MARUBOZU = "marubozu"
    SHOOTING_STAR = "shooting_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    
    # Chart Patterns
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_SHOULDERS = "head_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_shoulders"
    TRIANGLE_ASC = "triangle_ascending"
    TRIANGLE_DESC = "triangle_descending"
    TRIANGLE_SYM = "triangle_symmetrical"
    WEDGE_RISING = "wedge_rising"
    WEDGE_FALLING = "wedge_falling"
    FLAG = "flag"
    PENNANT = "pennant"
    CHANNEL = "channel"


class PatternDirection(Enum):
    """Direção do padrão"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class Pattern:
    """Representa um padrão detectado"""
    type: PatternType
    direction: PatternDirection
    strength: float  # 0-1
    start_index: int
    end_index: int
    confirmation_level: Optional[float] = None
    target: Optional[float] = None
    stop_loss: Optional[float] = None
    metadata: Dict[str, Any] = None


class PatternRecognizer:
    """
    Reconhecedor de Padrões
    
    Detecta padrões de candlestick e gráficos
    """
    
    def __init__(self, tolerance: float = 0.001):
        """
        Args:
            tolerance: Tolerância para comparações de preço
        """
        self._tolerance = tolerance
    
    def detect_all(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> List[Pattern]:
        """
        Detecta todos os padrões
        
        Returns:
            Lista de padrões detectados
        """
        patterns = []
        
        # Candlestick patterns (últimas velas)
        patterns.extend(self._detect_candlestick_patterns(opens, highs, lows, closes))
        
        # Chart patterns
        patterns.extend(self._detect_chart_patterns(opens, highs, lows, closes))
        
        return patterns
    
    # ==========================================================================
    # CANDLESTICK PATTERNS
    # ==========================================================================
    
    def _detect_candlestick_patterns(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> List[Pattern]:
        """Detecta padrões de candlestick"""
        patterns = []
        n = len(closes)
        
        if n < 3:
            return patterns
        
        # Verificar última vela
        i = n - 1
        
        # Doji
        if self._is_doji(opens[i], highs[i], lows[i], closes[i]):
            patterns.append(Pattern(
                type=PatternType.DOJI,
                direction=PatternDirection.NEUTRAL,
                strength=0.5,
                start_index=i,
                end_index=i
            ))
        
        # Hammer / Inverted Hammer
        hammer = self._detect_hammer(opens[i], highs[i], lows[i], closes[i])
        if hammer:
            patterns.append(hammer)
        
        # Marubozu
        if self._is_marubozu(opens[i], highs[i], lows[i], closes[i]):
            direction = PatternDirection.BULLISH if closes[i] > opens[i] else PatternDirection.BEARISH
            patterns.append(Pattern(
                type=PatternType.MARUBOZU,
                direction=direction,
                strength=0.8,
                start_index=i,
                end_index=i
            ))
        
        # Verificar padrões de 2 velas
        if n >= 2:
            # Engulfing
            engulfing = self._detect_engulfing(
                opens[i-1], highs[i-1], lows[i-1], closes[i-1],
                opens[i], highs[i], lows[i], closes[i]
            )
            if engulfing:
                patterns.append(engulfing)
            
            # Harami
            harami = self._detect_harami(
                opens[i-1], highs[i-1], lows[i-1], closes[i-1],
                opens[i], highs[i], lows[i], closes[i]
            )
            if harami:
                patterns.append(harami)
        
        # Verificar padrões de 3 velas
        if n >= 3:
            # Morning Star
            if self._is_morning_star(
                opens[i-2:i+1], highs[i-2:i+1], 
                lows[i-2:i+1], closes[i-2:i+1]
            ):
                patterns.append(Pattern(
                    type=PatternType.MORNING_STAR,
                    direction=PatternDirection.BULLISH,
                    strength=0.85,
                    start_index=i-2,
                    end_index=i
                ))
            
            # Evening Star
            if self._is_evening_star(
                opens[i-2:i+1], highs[i-2:i+1], 
                lows[i-2:i+1], closes[i-2:i+1]
            ):
                patterns.append(Pattern(
                    type=PatternType.EVENING_STAR,
                    direction=PatternDirection.BEARISH,
                    strength=0.85,
                    start_index=i-2,
                    end_index=i
                ))
            
            # Three White Soldiers
            if self._is_three_white_soldiers(
                opens[i-2:i+1], closes[i-2:i+1]
            ):
                patterns.append(Pattern(
                    type=PatternType.THREE_WHITE_SOLDIERS,
                    direction=PatternDirection.BULLISH,
                    strength=0.9,
                    start_index=i-2,
                    end_index=i
                ))
            
            # Three Black Crows
            if self._is_three_black_crows(
                opens[i-2:i+1], closes[i-2:i+1]
            ):
                patterns.append(Pattern(
                    type=PatternType.THREE_BLACK_CROWS,
                    direction=PatternDirection.BEARISH,
                    strength=0.9,
                    start_index=i-2,
                    end_index=i
                ))
        
        return patterns
    
    def _is_doji(self, o: float, h: float, l: float, c: float) -> bool:
        """Verifica se é doji"""
        body = abs(c - o)
        range_total = h - l
        
        if range_total == 0:
            return False
        
        return body / range_total < 0.1
    
    def _detect_hammer(
        self,
        o: float, h: float, l: float, c: float
    ) -> Optional[Pattern]:
        """Detecta hammer ou inverted hammer"""
        body = abs(c - o)
        range_total = h - l
        
        if range_total == 0:
            return None
        
        body_position = (min(o, c) - l) / range_total
        
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        
        # Hammer: corpo pequeno no topo, sombra inferior longa
        if (body / range_total < 0.3 and
            lower_shadow > body * 2 and
            upper_shadow < body * 0.5):
            return Pattern(
                type=PatternType.HAMMER,
                direction=PatternDirection.BULLISH,
                strength=0.7,
                start_index=-1,
                end_index=-1
            )
        
        # Inverted Hammer: corpo pequeno na base, sombra superior longa
        if (body / range_total < 0.3 and
            upper_shadow > body * 2 and
            lower_shadow < body * 0.5):
            return Pattern(
                type=PatternType.INVERTED_HAMMER,
                direction=PatternDirection.BULLISH,
                strength=0.6,
                start_index=-1,
                end_index=-1
            )
        
        return None
    
    def _is_marubozu(self, o: float, h: float, l: float, c: float) -> bool:
        """Verifica se é marubozu (sem sombras)"""
        body = abs(c - o)
        range_total = h - l
        
        if range_total == 0:
            return False
        
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        
        return (upper_shadow / range_total < 0.05 and 
                lower_shadow / range_total < 0.05 and
                body / range_total > 0.9)
    
    def _detect_engulfing(
        self,
        o1: float, h1: float, l1: float, c1: float,
        o2: float, h2: float, l2: float, c2: float
    ) -> Optional[Pattern]:
        """Detecta engulfing"""
        # Bullish Engulfing
        if (c1 < o1 and  # Primeira bearish
            c2 > o2 and  # Segunda bullish
            o2 < c1 and  # Abre abaixo do fechamento
            c2 > o1):    # Fecha acima da abertura
            return Pattern(
                type=PatternType.ENGULFING,
                direction=PatternDirection.BULLISH,
                strength=0.8,
                start_index=-2,
                end_index=-1
            )
        
        # Bearish Engulfing
        if (c1 > o1 and  # Primeira bullish
            c2 < o2 and  # Segunda bearish
            o2 > c1 and  # Abre acima do fechamento
            c2 < o1):    # Fecha abaixo da abertura
            return Pattern(
                type=PatternType.ENGULFING,
                direction=PatternDirection.BEARISH,
                strength=0.8,
                start_index=-2,
                end_index=-1
            )
        
        return None
    
    def _detect_harami(
        self,
        o1: float, h1: float, l1: float, c1: float,
        o2: float, h2: float, l2: float, c2: float
    ) -> Optional[Pattern]:
        """Detecta harami"""
        # Bullish Harami
        if (c1 < o1 and  # Primeira bearish
            abs(c2 - o2) < abs(c1 - o1) * 0.5 and  # Segunda menor
            o2 > c1 and c2 < o1 and  # Contido
            o2 < o1 and c2 > c1):
            return Pattern(
                type=PatternType.HARAMI,
                direction=PatternDirection.BULLISH,
                strength=0.65,
                start_index=-2,
                end_index=-1
            )
        
        # Bearish Harami
        if (c1 > o1 and  # Primeira bullish
            abs(c2 - o2) < abs(c1 - o1) * 0.5 and
            o2 < c1 and c2 > o1 and
            o2 > o1 and c2 < c1):
            return Pattern(
                type=PatternType.HARAMI,
                direction=PatternDirection.BEARISH,
                strength=0.65,
                start_index=-2,
                end_index=-1
            )
        
        return None
    
    def _is_morning_star(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> bool:
        """Verifica Morning Star"""
        if len(opens) < 3:
            return False
        
        # Primeira: bearish longa
        first_bearish = closes[0] < opens[0]
        first_body = abs(closes[0] - opens[0])
        
        # Segunda: corpo pequeno (doji ou spinning top)
        second_small = abs(closes[1] - opens[1]) < first_body * 0.3
        
        # Terceira: bullish longa
        third_bullish = closes[2] > opens[2]
        third_body = abs(closes[2] - opens[2])
        
        # Gap down na segunda
        gap_down = max(opens[1], closes[1]) < closes[0]
        
        # Terceira fecha acima do meio da primeira
        closes_above = closes[2] > (opens[0] + closes[0]) / 2
        
        return (first_bearish and second_small and 
                third_bullish and third_body > first_body * 0.5 and
                closes_above)
    
    def _is_evening_star(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> bool:
        """Verifica Evening Star"""
        if len(opens) < 3:
            return False
        
        # Primeira: bullish longa
        first_bullish = closes[0] > opens[0]
        first_body = abs(closes[0] - opens[0])
        
        # Segunda: corpo pequeno
        second_small = abs(closes[1] - opens[1]) < first_body * 0.3
        
        # Terceira: bearish longa
        third_bearish = closes[2] < opens[2]
        third_body = abs(closes[2] - opens[2])
        
        # Gap up na segunda
        gap_up = min(opens[1], closes[1]) > closes[0]
        
        # Terceira fecha abaixo do meio da primeira
        closes_below = closes[2] < (opens[0] + closes[0]) / 2
        
        return (first_bullish and second_small and 
                third_bearish and third_body > first_body * 0.5 and
                closes_below)
    
    def _is_three_white_soldiers(
        self,
        opens: np.ndarray,
        closes: np.ndarray
    ) -> bool:
        """Verifica Three White Soldiers"""
        if len(opens) < 3:
            return False
        
        for i in range(3):
            # Todas bullish
            if closes[i] <= opens[i]:
                return False
            
            # Cada uma fecha mais alto
            if i > 0 and closes[i] <= closes[i-1]:
                return False
            
            # Cada uma abre dentro do corpo anterior
            if i > 0 and not (opens[i-1] < opens[i] < closes[i-1]):
                return False
        
        return True
    
    def _is_three_black_crows(
        self,
        opens: np.ndarray,
        closes: np.ndarray
    ) -> bool:
        """Verifica Three Black Crows"""
        if len(opens) < 3:
            return False
        
        for i in range(3):
            # Todas bearish
            if closes[i] >= opens[i]:
                return False
            
            # Cada uma fecha mais baixo
            if i > 0 and closes[i] >= closes[i-1]:
                return False
            
            # Cada uma abre dentro do corpo anterior
            if i > 0 and not (closes[i-1] < opens[i] < opens[i-1]):
                return False
        
        return True
    
    # ==========================================================================
    # CHART PATTERNS
    # ==========================================================================
    
    def _detect_chart_patterns(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> List[Pattern]:
        """Detecta padrões gráficos maiores"""
        patterns = []
        
        if len(closes) < 20:
            return patterns
        
        # Detectar pivots
        pivot_highs, pivot_lows = self._find_pivots(highs, lows, 5)
        
        # Double Top
        double_top = self._detect_double_top(highs, pivot_highs)
        if double_top:
            patterns.append(double_top)
        
        # Double Bottom
        double_bottom = self._detect_double_bottom(lows, pivot_lows)
        if double_bottom:
            patterns.append(double_bottom)
        
        return patterns
    
    def _find_pivots(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        lookback: int = 5
    ) -> tuple[List[tuple], List[tuple]]:
        """Encontra pivots (máximas e mínimas locais)"""
        pivot_highs = []
        pivot_lows = []
        
        for i in range(lookback, len(highs) - lookback):
            # Pivot High
            is_pivot_high = True
            for j in range(-lookback, lookback + 1):
                if j != 0 and highs[i] <= highs[i + j]:
                    is_pivot_high = False
                    break
            
            if is_pivot_high:
                pivot_highs.append((i, highs[i]))
            
            # Pivot Low
            is_pivot_low = True
            for j in range(-lookback, lookback + 1):
                if j != 0 and lows[i] >= lows[i + j]:
                    is_pivot_low = False
                    break
            
            if is_pivot_low:
                pivot_lows.append((i, lows[i]))
        
        return pivot_highs, pivot_lows
    
    def _detect_double_top(
        self,
        highs: np.ndarray,
        pivot_highs: List[tuple]
    ) -> Optional[Pattern]:
        """Detecta Double Top"""
        if len(pivot_highs) < 2:
            return None
        
        # Últimos 2 pivot highs
        for i in range(len(pivot_highs) - 1):
            idx1, high1 = pivot_highs[i]
            idx2, high2 = pivot_highs[i + 1]
            
            # Verificar se são similares (tolerância)
            diff = abs(high1 - high2) / high1
            
            if diff < 0.02:  # 2% tolerância
                # Verificar se há vale entre eles
                valley_idx = idx1 + np.argmin(highs[idx1:idx2])
                
                if valley_idx != idx1 and valley_idx != idx2:
                    return Pattern(
                        type=PatternType.DOUBLE_TOP,
                        direction=PatternDirection.BEARISH,
                        strength=0.75,
                        start_index=idx1,
                        end_index=idx2,
                        confirmation_level=highs[valley_idx],
                        target=highs[valley_idx] - (high1 - highs[valley_idx]),
                        metadata={"neckline": highs[valley_idx]}
                    )
        
        return None
    
    def _detect_double_bottom(
        self,
        lows: np.ndarray,
        pivot_lows: List[tuple]
    ) -> Optional[Pattern]:
        """Detecta Double Bottom"""
        if len(pivot_lows) < 2:
            return None
        
        for i in range(len(pivot_lows) - 1):
            idx1, low1 = pivot_lows[i]
            idx2, low2 = pivot_lows[i + 1]
            
            diff = abs(low1 - low2) / low1
            
            if diff < 0.02:
                peak_idx = idx1 + np.argmax(lows[idx1:idx2])
                
                if peak_idx != idx1 and peak_idx != idx2:
                    return Pattern(
                        type=PatternType.DOUBLE_BOTTOM,
                        direction=PatternDirection.BULLISH,
                        strength=0.75,
                        start_index=idx1,
                        end_index=idx2,
                        confirmation_level=lows[peak_idx],
                        target=lows[peak_idx] + (lows[peak_idx] - low1),
                        metadata={"neckline": lows[peak_idx]}
                    )
        
        return None
