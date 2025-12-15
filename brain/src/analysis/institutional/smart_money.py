"""
VIRTUS Smart Money Concepts (SMC) Analysis
===========================================

Análise baseada em conceitos institucionais:
- Order Blocks (OB)
- Fair Value Gaps (FVG/Imbalance)
- Liquidity Pools
- Breaker Blocks
- Mitigation Blocks
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class OrderBlockType(Enum):
    """Tipo de Order Block."""
    BULLISH = auto()    # Último candle bearish antes de movimento bullish
    BEARISH = auto()    # Último candle bullish antes de movimento bearish


class FVGType(Enum):
    """Tipo de Fair Value Gap."""
    BULLISH = auto()    # Gap para cima (comprar no reteste)
    BEARISH = auto()    # Gap para baixo (vender no reteste)


class LiquidityType(Enum):
    """Tipo de liquidez."""
    BUY_SIDE = auto()   # Acima de swing highs (stop losses de shorts)
    SELL_SIDE = auto()  # Abaixo de swing lows (stop losses de longs)
    EQUAL_HIGHS = auto()
    EQUAL_LOWS = auto()


@dataclass
class OrderBlock:
    """Order Block identificado."""
    ob_type: OrderBlockType
    index: int
    high: float
    low: float
    open_price: float
    close: float
    timestamp: datetime
    strength: float  # 0-1, baseado no movimento subsequente
    mitigated: bool = False
    mitigated_at: Optional[int] = None
    times_tested: int = 0
    
    @property
    def zone(self) -> Tuple[float, float]:
        """Retorna zona do OB (low, high)."""
        return (self.low, self.high)
    
    @property
    def midpoint(self) -> float:
        """Ponto médio do OB."""
        return (self.high + self.low) / 2


@dataclass
class FairValueGap:
    """Fair Value Gap (Imbalance) identificado."""
    fvg_type: FVGType
    index: int
    high: float  # Limite superior do gap
    low: float   # Limite inferior do gap
    timestamp: datetime
    size: float  # Tamanho em pips
    filled: bool = False
    filled_percentage: float = 0.0
    
    @property
    def zone(self) -> Tuple[float, float]:
        """Retorna zona do FVG."""
        return (self.low, self.high)
    
    @property
    def midpoint(self) -> float:
        """Ponto médio do FVG."""
        return (self.high + self.low) / 2


@dataclass
class LiquidityPool:
    """Pool de liquidez identificado."""
    liq_type: LiquidityType
    price: float
    strength: float  # 0-1, baseado em quantos toques
    touch_count: int
    indices: List[int]  # Índices dos toques
    swept: bool = False
    swept_at: Optional[int] = None


class SmartMoneyAnalyzer:
    """
    Analisador de Smart Money Concepts.
    
    Identifica:
    - Order Blocks (zonas de entrada institucional)
    - Fair Value Gaps (imbalances no preço)
    - Pools de liquidez (stop hunts)
    - Breaker Blocks (OB que foram quebrados)
    """
    
    def __init__(
        self,
        ob_min_move: float = 0.001,  # Movimento mínimo após OB (0.1%)
        fvg_min_size: float = 0.0003,  # Tamanho mínimo FVG
        liquidity_tolerance: float = 0.0001,  # Tolerância para equal highs/lows
    ):
        self.ob_min_move = ob_min_move
        self.fvg_min_size = fvg_min_size
        self.liquidity_tolerance = liquidity_tolerance
        
        self.order_blocks: List[OrderBlock] = []
        self.fair_value_gaps: List[FairValueGap] = []
        self.liquidity_pools: List[LiquidityPool] = []
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Análise completa de SMC.
        
        Args:
            df: DataFrame com OHLCV
            
        Returns:
            Dicionário com todos os elementos SMC
        """
        if df is None or len(df) < 20:
            return {}
        
        # 1. Identifica Order Blocks
        self._find_order_blocks(df)
        
        # 2. Identifica Fair Value Gaps
        self._find_fair_value_gaps(df)
        
        # 3. Identifica Pools de Liquidez
        self._find_liquidity_pools(df)
        
        # 4. Atualiza status (mitigação, preenchimento)
        self._update_status(df)
        
        return self.to_dict()
    
    def _find_order_blocks(self, df: pd.DataFrame) -> None:
        """Encontra Order Blocks."""
        self.order_blocks = []
        
        open_prices = df['open'].values
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        for i in range(1, len(df) - 2):
            # Candle atual
            is_bullish = close[i] > open_prices[i]
            is_bearish = close[i] < open_prices[i]
            
            # Movimento subsequente
            future_high = max(high[i+1:min(i+6, len(df))])
            future_low = min(low[i+1:min(i+6, len(df))])
            
            # Bullish OB: Último candle bearish antes de movimento bullish forte
            if is_bearish:
                move_up = (future_high - high[i]) / high[i]
                if move_up >= self.ob_min_move:
                    # Verifica se realmente é o último bearish
                    if i > 0 and close[i-1] <= open_prices[i-1]:
                        strength = min(move_up / self.ob_min_move / 3, 1.0)
                        
                        self.order_blocks.append(OrderBlock(
                            ob_type=OrderBlockType.BULLISH,
                            index=i,
                            high=high[i],
                            low=low[i],
                            open_price=open_prices[i],
                            close=close[i],
                            timestamp=df.index[i] if isinstance(df.index, pd.DatetimeIndex) else datetime.now(),
                            strength=strength,
                        ))
            
            # Bearish OB: Último candle bullish antes de movimento bearish forte
            if is_bullish:
                move_down = (low[i] - future_low) / low[i]
                if move_down >= self.ob_min_move:
                    if i > 0 and close[i-1] >= open_prices[i-1]:
                        strength = min(move_down / self.ob_min_move / 3, 1.0)
                        
                        self.order_blocks.append(OrderBlock(
                            ob_type=OrderBlockType.BEARISH,
                            index=i,
                            high=high[i],
                            low=low[i],
                            open_price=open_prices[i],
                            close=close[i],
                            timestamp=df.index[i] if isinstance(df.index, pd.DatetimeIndex) else datetime.now(),
                            strength=strength,
                        ))
    
    def _find_fair_value_gaps(self, df: pd.DataFrame) -> None:
        """Encontra Fair Value Gaps (Imbalances)."""
        self.fair_value_gaps = []
        
        high = df['high'].values
        low = df['low'].values
        
        for i in range(1, len(df) - 1):
            # FVG Bullish: Low do candle 3 > High do candle 1
            # (gap entre candle 1 e 3, candle 2 é o impulso)
            if i >= 1:
                gap_low = high[i-1]  # High do candle anterior
                gap_high = low[i+1]  # Low do próximo candle
                
                # Bullish FVG
                if gap_high > gap_low:
                    size = gap_high - gap_low
                    if size >= self.fvg_min_size * high[i]:
                        self.fair_value_gaps.append(FairValueGap(
                            fvg_type=FVGType.BULLISH,
                            index=i,
                            high=gap_high,
                            low=gap_low,
                            timestamp=df.index[i] if isinstance(df.index, pd.DatetimeIndex) else datetime.now(),
                            size=size,
                        ))
                
                # Bearish FVG: High do candle 3 < Low do candle 1
                gap_high_bear = low[i-1]  # Low do candle anterior
                gap_low_bear = high[i+1]  # High do próximo candle
                
                if gap_high_bear > gap_low_bear:
                    size = gap_high_bear - gap_low_bear
                    if size >= self.fvg_min_size * high[i]:
                        self.fair_value_gaps.append(FairValueGap(
                            fvg_type=FVGType.BEARISH,
                            index=i,
                            high=gap_high_bear,
                            low=gap_low_bear,
                            timestamp=df.index[i] if isinstance(df.index, pd.DatetimeIndex) else datetime.now(),
                            size=size,
                        ))
    
    def _find_liquidity_pools(self, df: pd.DataFrame) -> None:
        """Encontra pools de liquidez."""
        self.liquidity_pools = []
        
        high = df['high'].values
        low = df['low'].values
        
        # Encontra swing highs e lows
        swing_highs = self._find_swing_points(high, is_high=True)
        swing_lows = self._find_swing_points(low, is_high=False)
        
        # Agrupa highs próximos (equal highs = liquidez)
        self._group_equal_levels(swing_highs, LiquidityType.BUY_SIDE, LiquidityType.EQUAL_HIGHS)
        self._group_equal_levels(swing_lows, LiquidityType.SELL_SIDE, LiquidityType.EQUAL_LOWS)
    
    def _find_swing_points(self, data: np.ndarray, is_high: bool, lookback: int = 3) -> List[Tuple[int, float]]:
        """Encontra swing points."""
        points = []
        
        for i in range(lookback, len(data) - lookback):
            if is_high:
                if data[i] == max(data[i-lookback:i+lookback+1]):
                    points.append((i, data[i]))
            else:
                if data[i] == min(data[i-lookback:i+lookback+1]):
                    points.append((i, data[i]))
        
        return points
    
    def _group_equal_levels(
        self, 
        points: List[Tuple[int, float]], 
        single_type: LiquidityType,
        equal_type: LiquidityType
    ) -> None:
        """Agrupa níveis iguais em pools de liquidez."""
        if not points:
            return
        
        used = set()
        
        for i, (idx1, price1) in enumerate(points):
            if i in used:
                continue
            
            equal_points = [(idx1, price1)]
            
            for j, (idx2, price2) in enumerate(points[i+1:], i+1):
                if j in used:
                    continue
                
                # Verifica se preços são "iguais" dentro da tolerância
                if abs(price1 - price2) / price1 <= self.liquidity_tolerance:
                    equal_points.append((idx2, price2))
                    used.add(j)
            
            used.add(i)
            
            # Cria pool de liquidez
            avg_price = sum(p[1] for p in equal_points) / len(equal_points)
            
            if len(equal_points) >= 2:
                # Equal highs/lows = mais significativo
                liq_type = equal_type
                strength = min(len(equal_points) / 3, 1.0)
            else:
                liq_type = single_type
                strength = 0.5
            
            self.liquidity_pools.append(LiquidityPool(
                liq_type=liq_type,
                price=avg_price,
                strength=strength,
                touch_count=len(equal_points),
                indices=[p[0] for p in equal_points],
            ))
    
    def _update_status(self, df: pd.DataFrame) -> None:
        """Atualiza status de mitigação e preenchimento."""
        high = df['high'].values
        low = df['low'].values
        
        # Atualiza Order Blocks
        for ob in self.order_blocks:
            if ob.mitigated:
                continue
            
            for i in range(ob.index + 1, len(df)):
                if ob.ob_type == OrderBlockType.BULLISH:
                    # OB bullish mitigado quando preço entra na zona
                    if low[i] <= ob.high:
                        ob.times_tested += 1
                        if low[i] <= ob.midpoint:
                            ob.mitigated = True
                            ob.mitigated_at = i
                            break
                else:
                    # OB bearish mitigado quando preço entra na zona
                    if high[i] >= ob.low:
                        ob.times_tested += 1
                        if high[i] >= ob.midpoint:
                            ob.mitigated = True
                            ob.mitigated_at = i
                            break
        
        # Atualiza Fair Value Gaps
        for fvg in self.fair_value_gaps:
            if fvg.filled:
                continue
            
            for i in range(fvg.index + 1, len(df)):
                if fvg.fvg_type == FVGType.BULLISH:
                    # FVG bullish preenchido quando preço desce até ele
                    if low[i] <= fvg.high:
                        penetration = (fvg.high - max(low[i], fvg.low)) / (fvg.high - fvg.low)
                        fvg.filled_percentage = max(fvg.filled_percentage, penetration)
                        if low[i] <= fvg.low:
                            fvg.filled = True
                            break
                else:
                    # FVG bearish preenchido quando preço sobe até ele
                    if high[i] >= fvg.low:
                        penetration = (min(high[i], fvg.high) - fvg.low) / (fvg.high - fvg.low)
                        fvg.filled_percentage = max(fvg.filled_percentage, penetration)
                        if high[i] >= fvg.high:
                            fvg.filled = True
                            break
        
        # Atualiza Liquidity Pools
        for pool in self.liquidity_pools:
            if pool.swept:
                continue
            
            last_idx = max(pool.indices)
            for i in range(last_idx + 1, len(df)):
                if pool.liq_type in [LiquidityType.BUY_SIDE, LiquidityType.EQUAL_HIGHS]:
                    if high[i] > pool.price:
                        pool.swept = True
                        pool.swept_at = i
                        break
                else:
                    if low[i] < pool.price:
                        pool.swept = True
                        pool.swept_at = i
                        break
    
    def get_active_order_blocks(self) -> List[OrderBlock]:
        """Retorna OBs ativos (não mitigados)."""
        return [ob for ob in self.order_blocks if not ob.mitigated]
    
    def get_unfilled_fvgs(self) -> List[FairValueGap]:
        """Retorna FVGs não preenchidos."""
        return [fvg for fvg in self.fair_value_gaps if not fvg.filled]
    
    def get_unswept_liquidity(self) -> List[LiquidityPool]:
        """Retorna pools de liquidez não varridos."""
        return [pool for pool in self.liquidity_pools if not pool.swept]
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte análise para dicionário."""
        return {
            'order_blocks': {
                'bullish': [
                    {
                        'index': ob.index,
                        'zone': ob.zone,
                        'strength': round(ob.strength, 3),
                        'mitigated': ob.mitigated,
                        'times_tested': ob.times_tested,
                    }
                    for ob in self.order_blocks 
                    if ob.ob_type == OrderBlockType.BULLISH
                ][-5:],
                'bearish': [
                    {
                        'index': ob.index,
                        'zone': ob.zone,
                        'strength': round(ob.strength, 3),
                        'mitigated': ob.mitigated,
                        'times_tested': ob.times_tested,
                    }
                    for ob in self.order_blocks 
                    if ob.ob_type == OrderBlockType.BEARISH
                ][-5:],
            },
            'fair_value_gaps': {
                'bullish': [
                    {
                        'index': fvg.index,
                        'zone': fvg.zone,
                        'size': round(fvg.size, 6),
                        'filled': fvg.filled,
                        'filled_pct': round(fvg.filled_percentage, 2),
                    }
                    for fvg in self.fair_value_gaps 
                    if fvg.fvg_type == FVGType.BULLISH
                ][-5:],
                'bearish': [
                    {
                        'index': fvg.index,
                        'zone': fvg.zone,
                        'size': round(fvg.size, 6),
                        'filled': fvg.filled,
                        'filled_pct': round(fvg.filled_percentage, 2),
                    }
                    for fvg in self.fair_value_gaps 
                    if fvg.fvg_type == FVGType.BEARISH
                ][-5:],
            },
            'liquidity_pools': {
                'buy_side': [
                    {
                        'price': round(pool.price, 5),
                        'strength': round(pool.strength, 3),
                        'touches': pool.touch_count,
                        'swept': pool.swept,
                    }
                    for pool in self.liquidity_pools 
                    if pool.liq_type in [LiquidityType.BUY_SIDE, LiquidityType.EQUAL_HIGHS]
                ][-3:],
                'sell_side': [
                    {
                        'price': round(pool.price, 5),
                        'strength': round(pool.strength, 3),
                        'touches': pool.touch_count,
                        'swept': pool.swept,
                    }
                    for pool in self.liquidity_pools 
                    if pool.liq_type in [LiquidityType.SELL_SIDE, LiquidityType.EQUAL_LOWS]
                ][-3:],
            },
            'active_obs_count': len(self.get_active_order_blocks()),
            'unfilled_fvgs_count': len(self.get_unfilled_fvgs()),
            'unswept_liq_count': len(self.get_unswept_liquidity()),
        }


@dataclass
class SmartMoneyResult:
    """
    Resultado consolidado da análise Smart Money.
    
    Usado para comunicação entre módulos.
    """
    order_blocks: List[OrderBlock]
    fair_value_gaps: List[FairValueGap]
    liquidity_pools: List[LiquidityPool]
    bias: str  # 'bullish', 'bearish', 'neutral'
    confidence: float  # 0-1
    key_levels: List[float]
    summary: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_analyzer(cls, analyzer: SmartMoneyAnalyzer) -> "SmartMoneyResult":
        """Cria resultado a partir do analisador."""
        active_obs = analyzer.get_active_order_blocks()
        unfilled_fvgs = analyzer.get_unfilled_fvgs()
        
        # Determina bias
        bullish_obs = sum(1 for ob in active_obs if ob.ob_type == OrderBlockType.BULLISH)
        bearish_obs = sum(1 for ob in active_obs if ob.ob_type == OrderBlockType.BEARISH)
        bullish_fvgs = sum(1 for fvg in unfilled_fvgs if fvg.fvg_type == FVGType.BULLISH)
        bearish_fvgs = sum(1 for fvg in unfilled_fvgs if fvg.fvg_type == FVGType.BEARISH)
        
        bullish_score = bullish_obs + bullish_fvgs
        bearish_score = bearish_obs + bearish_fvgs
        
        if bullish_score > bearish_score + 1:
            bias = 'bullish'
        elif bearish_score > bullish_score + 1:
            bias = 'bearish'
        else:
            bias = 'neutral'
        
        # Confiança baseada na quantidade de elementos
        total = bullish_score + bearish_score
        confidence = min(total / 10, 1.0) if total > 0 else 0.0
        
        # Key levels (OBs e FVGs importantes)
        key_levels = []
        for ob in active_obs[:3]:
            key_levels.append(ob.midpoint)
        for fvg in unfilled_fvgs[:3]:
            key_levels.append(fvg.midpoint)
        
        return cls(
            order_blocks=analyzer.order_blocks,
            fair_value_gaps=analyzer.fair_value_gaps,
            liquidity_pools=analyzer.liquidity_pools,
            bias=bias,
            confidence=confidence,
            key_levels=sorted(set(key_levels)),
            summary=analyzer.to_dict(),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'bias': self.bias,
            'confidence': round(self.confidence, 3),
            'key_levels': [round(l, 5) for l in self.key_levels],
            'active_order_blocks': len([ob for ob in self.order_blocks if not ob.mitigated]),
            'unfilled_fvgs': len([fvg for fvg in self.fair_value_gaps if not fvg.filled]),
            'unswept_liquidity': len([lp for lp in self.liquidity_pools if not lp.swept]),
            'timestamp': self.timestamp.isoformat(),
        }
