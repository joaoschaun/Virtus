"""
VIRTUS Market Structure Analysis
=================================

Análise avançada de estrutura de mercado:
- Swing Points (HH, HL, LH, LL)
- Break of Structure (BOS)
- Change of Character (CHoCH)
- Trend Identification
- Range Detection
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class StructureType(Enum):
    """Tipo de estrutura de mercado."""
    BULLISH_TREND = auto()      # HH + HL
    BEARISH_TREND = auto()      # LH + LL
    RANGING = auto()            # Sem direção clara
    CONSOLIDATION = auto()      # Range apertado
    BREAKOUT = auto()           # Saindo de range


class SwingType(Enum):
    """Tipo de swing point."""
    HIGHER_HIGH = "HH"
    HIGHER_LOW = "HL"
    LOWER_HIGH = "LH"
    LOWER_LOW = "LL"
    EQUAL_HIGH = "EH"
    EQUAL_LOW = "EL"


class StructureBreak(Enum):
    """Tipo de quebra de estrutura."""
    BOS_BULLISH = auto()        # Break of Structure bullish
    BOS_BEARISH = auto()        # Break of Structure bearish
    CHOCH_BULLISH = auto()      # Change of Character bullish
    CHOCH_BEARISH = auto()      # Change of Character bearish


@dataclass
class SwingPoint:
    """Ponto de swing identificado."""
    index: int
    price: float
    timestamp: datetime
    swing_type: SwingType
    strength: float  # 0-1, baseado em quantos candles confirmam
    broken: bool = False
    broken_at: Optional[int] = None


@dataclass
class StructureBreakEvent:
    """Evento de quebra de estrutura."""
    break_type: StructureBreak
    break_index: int
    break_price: float
    swing_broken: SwingPoint
    timestamp: datetime
    significance: float  # 0-1


@dataclass
class MarketStructureState:
    """Estado atual da estrutura de mercado."""
    structure_type: StructureType
    trend_strength: float  # 0-1
    swing_highs: List[SwingPoint]
    swing_lows: List[SwingPoint]
    last_hh: Optional[SwingPoint] = None
    last_hl: Optional[SwingPoint] = None
    last_lh: Optional[SwingPoint] = None
    last_ll: Optional[SwingPoint] = None
    recent_breaks: List[StructureBreakEvent] = field(default_factory=list)
    bias: str = "neutral"  # bullish, bearish, neutral


class MarketStructureAnalyzer:
    """
    Analisador de estrutura de mercado.
    
    Identifica:
    - Swing points com múltiplos métodos
    - Estrutura de tendência (HH/HL ou LH/LL)
    - Quebras de estrutura (BOS/CHoCH)
    - Zonas de premium/discount
    """
    
    def __init__(self, swing_strength: int = 5):
        """
        Args:
            swing_strength: Número de candles para confirmar swing (default 5)
        """
        self.swing_strength = swing_strength
        self._swing_highs: List[SwingPoint] = []
        self._swing_lows: List[SwingPoint] = []
        self._structure_breaks: List[StructureBreakEvent] = []
    
    def analyze(self, df: pd.DataFrame) -> MarketStructureState:
        """
        Análise completa de estrutura de mercado.
        
        Args:
            df: DataFrame com OHLCV
            
        Returns:
            MarketStructureState com análise completa
        """
        if df is None or len(df) < self.swing_strength * 3:
            return self._empty_state()
        
        # 1. Identifica swing points
        self._identify_swings(df)
        
        # 2. Classifica swings (HH, HL, LH, LL)
        self._classify_swings()
        
        # 3. Detecta quebras de estrutura
        self._detect_structure_breaks(df)
        
        # 4. Determina tipo de estrutura
        structure_type, trend_strength = self._determine_structure()
        
        # 5. Calcula bias
        bias = self._calculate_bias(df)
        
        return MarketStructureState(
            structure_type=structure_type,
            trend_strength=trend_strength,
            swing_highs=self._swing_highs[-10:],  # Últimos 10
            swing_lows=self._swing_lows[-10:],
            last_hh=self._get_last_swing(SwingType.HIGHER_HIGH),
            last_hl=self._get_last_swing(SwingType.HIGHER_LOW),
            last_lh=self._get_last_swing(SwingType.LOWER_HIGH),
            last_ll=self._get_last_swing(SwingType.LOWER_LOW),
            recent_breaks=self._structure_breaks[-5:],
            bias=bias,
        )
    
    def _identify_swings(self, df: pd.DataFrame) -> None:
        """Identifica swing highs e lows usando múltiplos métodos."""
        high = df['high'].values
        low = df['low'].values
        timestamps = df.index if isinstance(df.index, pd.DatetimeIndex) else range(len(df))
        
        self._swing_highs = []
        self._swing_lows = []
        
        n = self.swing_strength
        
        for i in range(n, len(df) - n):
            # Swing High: maior high em janela de 2n+1
            left_highs = high[i-n:i]
            right_highs = high[i+1:i+n+1]
            
            if high[i] > max(left_highs) and high[i] > max(right_highs):
                # Calcula força baseado em quantos candles são menores
                left_count = sum(1 for h in left_highs if h < high[i])
                right_count = sum(1 for h in right_highs if h < high[i])
                strength = (left_count + right_count) / (2 * n)
                
                self._swing_highs.append(SwingPoint(
                    index=i,
                    price=high[i],
                    timestamp=timestamps[i] if hasattr(timestamps[i], 'timestamp') else datetime.now(),
                    swing_type=SwingType.HIGHER_HIGH,  # Será reclassificado
                    strength=strength,
                ))
            
            # Swing Low: menor low em janela de 2n+1
            left_lows = low[i-n:i]
            right_lows = low[i+1:i+n+1]
            
            if low[i] < min(left_lows) and low[i] < min(right_lows):
                left_count = sum(1 for l in left_lows if l > low[i])
                right_count = sum(1 for l in right_lows if l > low[i])
                strength = (left_count + right_count) / (2 * n)
                
                self._swing_lows.append(SwingPoint(
                    index=i,
                    price=low[i],
                    timestamp=timestamps[i] if hasattr(timestamps[i], 'timestamp') else datetime.now(),
                    swing_type=SwingType.HIGHER_LOW,  # Será reclassificado
                    strength=strength,
                ))
    
    def _classify_swings(self) -> None:
        """Classifica swings como HH, HL, LH, LL."""
        # Classifica Swing Highs
        for i, swing in enumerate(self._swing_highs):
            if i == 0:
                swing.swing_type = SwingType.HIGHER_HIGH
                continue
            
            prev = self._swing_highs[i-1]
            tolerance = 0.0001  # Para evitar ruído
            
            if swing.price > prev.price * (1 + tolerance):
                swing.swing_type = SwingType.HIGHER_HIGH
            elif swing.price < prev.price * (1 - tolerance):
                swing.swing_type = SwingType.LOWER_HIGH
            else:
                swing.swing_type = SwingType.EQUAL_HIGH
        
        # Classifica Swing Lows
        for i, swing in enumerate(self._swing_lows):
            if i == 0:
                swing.swing_type = SwingType.HIGHER_LOW
                continue
            
            prev = self._swing_lows[i-1]
            tolerance = 0.0001
            
            if swing.price > prev.price * (1 + tolerance):
                swing.swing_type = SwingType.HIGHER_LOW
            elif swing.price < prev.price * (1 - tolerance):
                swing.swing_type = SwingType.LOWER_LOW
            else:
                swing.swing_type = SwingType.EQUAL_LOW
    
    def _detect_structure_breaks(self, df: pd.DataFrame) -> None:
        """Detecta BOS e CHoCH."""
        self._structure_breaks = []
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        # Verifica quebra de swing highs
        for swing in self._swing_highs:
            if swing.broken:
                continue
            
            # Procura candle que quebrou o swing high
            for i in range(swing.index + 1, len(df)):
                if close[i] > swing.price:
                    swing.broken = True
                    swing.broken_at = i
                    
                    # Determina se é BOS ou CHoCH
                    if swing.swing_type == SwingType.LOWER_HIGH:
                        # Quebrar LH = CHoCH bullish
                        break_type = StructureBreak.CHOCH_BULLISH
                        significance = 0.8
                    else:
                        # Quebrar HH = BOS bullish (continuação)
                        break_type = StructureBreak.BOS_BULLISH
                        significance = 0.6
                    
                    self._structure_breaks.append(StructureBreakEvent(
                        break_type=break_type,
                        break_index=i,
                        break_price=close[i],
                        swing_broken=swing,
                        timestamp=datetime.now(),
                        significance=significance * swing.strength,
                    ))
                    break
        
        # Verifica quebra de swing lows
        for swing in self._swing_lows:
            if swing.broken:
                continue
            
            for i in range(swing.index + 1, len(df)):
                if close[i] < swing.price:
                    swing.broken = True
                    swing.broken_at = i
                    
                    if swing.swing_type == SwingType.HIGHER_LOW:
                        # Quebrar HL = CHoCH bearish
                        break_type = StructureBreak.CHOCH_BEARISH
                        significance = 0.8
                    else:
                        # Quebrar LL = BOS bearish (continuação)
                        break_type = StructureBreak.BOS_BEARISH
                        significance = 0.6
                    
                    self._structure_breaks.append(StructureBreakEvent(
                        break_type=break_type,
                        break_index=i,
                        break_price=close[i],
                        swing_broken=swing,
                        timestamp=datetime.now(),
                        significance=significance * swing.strength,
                    ))
                    break
    
    def _determine_structure(self) -> Tuple[StructureType, float]:
        """Determina tipo de estrutura e força da tendência."""
        if len(self._swing_highs) < 2 or len(self._swing_lows) < 2:
            return StructureType.RANGING, 0.0
        
        # Conta tipos de swings recentes (últimos 6)
        recent_highs = self._swing_highs[-6:]
        recent_lows = self._swing_lows[-6:]
        
        hh_count = sum(1 for s in recent_highs if s.swing_type == SwingType.HIGHER_HIGH)
        lh_count = sum(1 for s in recent_highs if s.swing_type == SwingType.LOWER_HIGH)
        hl_count = sum(1 for s in recent_lows if s.swing_type == SwingType.HIGHER_LOW)
        ll_count = sum(1 for s in recent_lows if s.swing_type == SwingType.LOWER_LOW)
        
        total_highs = len(recent_highs)
        total_lows = len(recent_lows)
        
        # Tendência de alta: HH + HL
        bullish_score = (hh_count / total_highs + hl_count / total_lows) / 2
        
        # Tendência de baixa: LH + LL
        bearish_score = (lh_count / total_highs + ll_count / total_lows) / 2
        
        if bullish_score > 0.6:
            return StructureType.BULLISH_TREND, bullish_score
        elif bearish_score > 0.6:
            return StructureType.BEARISH_TREND, bearish_score
        elif abs(bullish_score - bearish_score) < 0.2:
            return StructureType.CONSOLIDATION, 1 - abs(bullish_score - bearish_score)
        else:
            return StructureType.RANGING, 0.3
    
    def _calculate_bias(self, df: pd.DataFrame) -> str:
        """Calcula bias baseado em estrutura e breaks recentes."""
        if not self._structure_breaks:
            # Sem breaks, usa estrutura
            structure_type, _ = self._determine_structure()
            if structure_type == StructureType.BULLISH_TREND:
                return "bullish"
            elif structure_type == StructureType.BEARISH_TREND:
                return "bearish"
            return "neutral"
        
        # Último break determina bias
        last_break = self._structure_breaks[-1]
        
        if last_break.break_type in [StructureBreak.CHOCH_BULLISH, StructureBreak.BOS_BULLISH]:
            return "bullish"
        elif last_break.break_type in [StructureBreak.CHOCH_BEARISH, StructureBreak.BOS_BEARISH]:
            return "bearish"
        
        return "neutral"
    
    def _get_last_swing(self, swing_type: SwingType) -> Optional[SwingPoint]:
        """Obtém último swing de um tipo específico."""
        swings = self._swing_highs if swing_type in [SwingType.HIGHER_HIGH, SwingType.LOWER_HIGH] else self._swing_lows
        
        for swing in reversed(swings):
            if swing.swing_type == swing_type:
                return swing
        return None
    
    def _empty_state(self) -> MarketStructureState:
        """Retorna estado vazio."""
        return MarketStructureState(
            structure_type=StructureType.RANGING,
            trend_strength=0.0,
            swing_highs=[],
            swing_lows=[],
            bias="neutral",
        )
    
    def get_premium_discount_zones(self, df: pd.DataFrame) -> Dict[str, Tuple[float, float]]:
        """
        Calcula zonas de premium e discount.
        
        Premium: Acima de 50% do range (vender)
        Discount: Abaixo de 50% do range (comprar)
        """
        if len(self._swing_highs) < 1 or len(self._swing_lows) < 1:
            return {}
        
        # Usa último swing high e low significativos
        recent_high = max(s.price for s in self._swing_highs[-3:])
        recent_low = min(s.price for s in self._swing_lows[-3:])
        
        range_size = recent_high - recent_low
        equilibrium = recent_low + (range_size * 0.5)
        
        return {
            'premium': (equilibrium, recent_high),
            'discount': (recent_low, equilibrium),
            'equilibrium': equilibrium,
            'range_high': recent_high,
            'range_low': recent_low,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte análise para dicionário."""
        structure_type, trend_strength = self._determine_structure()
        
        return {
            'structure_type': structure_type.name,
            'trend_strength': round(trend_strength, 3),
            'bias': self._calculate_bias(None) if self._structure_breaks else "neutral",
            'swing_highs': [
                {
                    'index': s.index,
                    'price': s.price,
                    'type': s.swing_type.value,
                    'strength': round(s.strength, 3),
                    'broken': s.broken,
                }
                for s in self._swing_highs[-5:]
            ],
            'swing_lows': [
                {
                    'index': s.index,
                    'price': s.price,
                    'type': s.swing_type.value,
                    'strength': round(s.strength, 3),
                    'broken': s.broken,
                }
                for s in self._swing_lows[-5:]
            ],
            'recent_breaks': [
                {
                    'type': b.break_type.name,
                    'index': b.break_index,
                    'price': b.break_price,
                    'significance': round(b.significance, 3),
                }
                for b in self._structure_breaks[-3:]
            ],
        }
