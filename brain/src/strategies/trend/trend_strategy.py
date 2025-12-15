"""
VIRTUS Trend Following Strategy
================================

Estratégia de trend following avançada usando:
- Smart Money Concepts (SMC)
- Multi-Timeframe Analysis (MTF)
- Market Structure
- Order Blocks + FVG
- Fibonacci confluência
- Volume confirmation
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np

try:
    from ...core import VirtusLogger
    from ...core.types import Signal, SignalDirection, SignalStrength
except ImportError:
    from core import VirtusLogger
    from core.types import Signal, SignalDirection, SignalStrength


class TrendSetup(Enum):
    """Tipos de setup de trend following."""
    BOS_CONTINUATION = "bos_continuation"
    ORDER_BLOCK_PULLBACK = "order_block_pullback"
    FVG_RETEST = "fvg_retest"
    FIBONACCI_PULLBACK = "fibonacci_pullback"
    MTF_ALIGNMENT = "mtf_alignment"
    STRUCTURE_SHIFT = "structure_shift"
    LIQUIDITY_SWEEP_CONTINUATION = "liquidity_sweep_continuation"


class TrendStrength(Enum):
    """Força da tendência."""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4


@dataclass
class TrendSignal:
    """Sinal de trend following."""
    setup: TrendSetup
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    confidence: float
    trend_strength: TrendStrength
    risk_reward: float
    mtf_alignment: Dict[str, str]  # {timeframe: trend}
    confluences: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendConfig:
    """Configuração da estratégia de trend."""
    # Timeframes
    entry_tf: str = "M15"
    structure_tf: str = "H1"
    bias_tf: str = "H4"
    
    # Risk
    risk_per_trade: float = 1.0
    min_risk_reward: float = 2.0
    max_sl_atr: float = 2.5
    
    # Entry filters
    min_confluences: int = 3
    min_mtf_alignment: int = 2  # Mínimo de TFs alinhados
    require_bos: bool = True
    require_volume_confirmation: bool = True
    
    # Targets (R-multiples)
    tp1_r: float = 1.5
    tp2_r: float = 2.5
    tp3_r: float = 4.0
    
    # Partial exits
    tp1_percent: float = 40
    tp2_percent: float = 30
    tp3_percent: float = 30


class TrendStrategy:
    """
    Estratégia de Trend Following SMC.
    
    Lógica:
    1. Identifica bias (direção) no TF maior (H4/D1)
    2. Confirma estrutura no TF médio (H1)
    3. Entry no TF menor (M15) em pontos de interesse
    
    Setups:
    1. BOS Continuation - Após break of structure, entry no pullback
    2. Order Block Pullback - Pullback para OB em tendência
    3. FVG Retest - Reteste de Fair Value Gap
    4. Fibonacci Pullback - Pullback para zona dourada (61.8-78.6%)
    5. MTF Alignment - Todos os TFs alinhados
    6. Structure Shift - Entry após mudança de estrutura
    7. Liquidity Sweep Continuation - Após sweep, continuação do trend
    """
    
    def __init__(self, config: Optional[TrendConfig] = None):
        self.config = config or TrendConfig()
        self.logger = VirtusLogger.get_logger("trend_strategy")
        self.name = "Trend Strategy"
    
    async def evaluate(
        self,
        symbol: str,
        current_price: float,
        atr: float,
        # Market Structure
        market_structure: Dict[str, Any] = None,
        swing_high: float = 0,
        swing_low: float = 0,
        bos_detected: bool = False,
        bos_direction: str = "",
        choch_detected: bool = False,
        # SMC Data
        order_blocks: List[Dict] = None,
        fvg_zones: List[Dict] = None,
        liquidity_pools: List[Dict] = None,
        premium_zone: Tuple[float, float] = None,
        discount_zone: Tuple[float, float] = None,
        # Fibonacci
        fib_levels: Dict[str, float] = None,
        in_golden_zone: bool = False,
        # MTF Analysis
        mtf_analysis: Dict[str, Dict] = None,  # {tf: {trend, strength, bias}}
        # Volume
        volume_confirmation: bool = False,
        volume_trend: str = "neutral",
    ) -> Optional[TrendSignal]:
        """
        Avalia setups de trend following.
        """
        confluences = []
        
        # === DETERMINA BIAS ===
        bias = self._determine_bias(mtf_analysis, market_structure)
        
        if bias == "neutral":
            return None
        
        direction = SignalDirection.BUY if bias == "bullish" else SignalDirection.SELL
        
        # === VERIFICA ALINHAMENTO MTF ===
        mtf_alignment = self._check_mtf_alignment(mtf_analysis, bias)
        aligned_count = sum(1 for v in mtf_alignment.values() if v == bias)
        
        if aligned_count >= self.config.min_mtf_alignment:
            confluences.append(f"mtf_aligned_{aligned_count}")
        else:
            # Não atende requisito mínimo de alinhamento
            if self.config.min_mtf_alignment > 0:
                return None
        
        # === VERIFICA BOS ===
        if self.config.require_bos:
            if bos_detected and bos_direction == bias:
                confluences.append("bos_confirmed")
            else:
                return None  # BOS é obrigatório
        
        # === VERIFICA VOLUME ===
        if self.config.require_volume_confirmation:
            if volume_confirmation and volume_trend == bias:
                confluences.append("volume_confirmed")
            elif volume_confirmation:
                confluences.append("volume_present")
        
        # === AVALIA SETUPS ===
        signals: List[TrendSignal] = []
        
        # 1. BOS Continuation
        if bos_detected and bos_direction == bias:
            signal = self._evaluate_bos_continuation(
                current_price, direction, atr, swing_high, swing_low,
                mtf_alignment, confluences.copy()
            )
            if signal:
                signals.append(signal)
        
        # 2. Order Block Pullback
        if order_blocks:
            signal = self._evaluate_ob_pullback(
                current_price, direction, atr, order_blocks,
                premium_zone, discount_zone, mtf_alignment, confluences.copy()
            )
            if signal:
                signals.append(signal)
        
        # 3. FVG Retest
        if fvg_zones:
            signal = self._evaluate_fvg_retest(
                current_price, direction, atr, fvg_zones,
                mtf_alignment, confluences.copy()
            )
            if signal:
                signals.append(signal)
        
        # 4. Fibonacci Pullback
        if fib_levels and in_golden_zone:
            signal = self._evaluate_fib_pullback(
                current_price, direction, atr, fib_levels,
                swing_high, swing_low, mtf_alignment, confluences.copy()
            )
            if signal:
                signals.append(signal)
        
        # 5. MTF Alignment
        if aligned_count >= 3:
            signal = self._evaluate_mtf_alignment_entry(
                current_price, direction, atr,
                swing_high, swing_low, mtf_alignment, confluences.copy()
            )
            if signal:
                signals.append(signal)
        
        # 6. Liquidity Sweep Continuation
        if liquidity_pools:
            signal = self._evaluate_liquidity_sweep(
                current_price, direction, atr, liquidity_pools,
                mtf_alignment, confluences.copy()
            )
            if signal:
                signals.append(signal)
        
        # === SELECIONA MELHOR SINAL ===
        if not signals:
            return None
        
        # Filtra por confluências mínimas
        valid_signals = [
            s for s in signals 
            if len(s.confluences) >= self.config.min_confluences
        ]
        
        if not valid_signals:
            return None
        
        # Seleciona por confiança
        best_signal = max(valid_signals, key=lambda s: s.confidence)
        
        self.logger.info(
            f"🎯 Trend signal: {best_signal.setup.value} "
            f"{best_signal.direction.value} @ {best_signal.entry_price:.5f} "
            f"SL: {best_signal.stop_loss:.5f} "
            f"TP1: {best_signal.take_profit_1:.5f} "
            f"Confluences: {len(best_signal.confluences)}"
        )
        
        return best_signal
    
    def _determine_bias(
        self,
        mtf_analysis: Optional[Dict],
        market_structure: Optional[Dict]
    ) -> str:
        """Determina bias geral."""
        if not mtf_analysis and not market_structure:
            return "neutral"
        
        votes = {"bullish": 0, "bearish": 0}
        
        # MTF votes
        if mtf_analysis:
            for tf, data in mtf_analysis.items():
                trend = data.get('trend', 'neutral')
                weight = 1
                if tf in ['H4', 'D1']:
                    weight = 2  # TFs maiores têm mais peso
                
                if trend == 'bullish':
                    votes['bullish'] += weight
                elif trend == 'bearish':
                    votes['bearish'] += weight
        
        # Structure vote
        if market_structure:
            trend = market_structure.get('trend', 'neutral')
            if trend == 'bullish':
                votes['bullish'] += 2
            elif trend == 'bearish':
                votes['bearish'] += 2
        
        if votes['bullish'] > votes['bearish'] + 1:
            return "bullish"
        elif votes['bearish'] > votes['bullish'] + 1:
            return "bearish"
        
        return "neutral"
    
    def _check_mtf_alignment(
        self,
        mtf_analysis: Optional[Dict],
        bias: str
    ) -> Dict[str, str]:
        """Verifica alinhamento de timeframes."""
        alignment = {}
        
        if not mtf_analysis:
            return alignment
        
        for tf, data in mtf_analysis.items():
            trend = data.get('trend', 'neutral')
            alignment[tf] = trend
        
        return alignment
    
    def _evaluate_bos_continuation(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        swing_high: float,
        swing_low: float,
        mtf_alignment: Dict,
        confluences: List[str]
    ) -> Optional[TrendSignal]:
        """
        BOS Continuation Setup.
        
        Após um break of structure, espera pullback e entra na continuação.
        """
        confluences.append("bos_continuation")
        
        if direction == SignalDirection.BUY:
            # BOS bullish: espera pullback acima do swing low
            sl = swing_low - atr * 0.2
            
            # Verifica se preço está em zona de desconto
            range_size = swing_high - swing_low
            discount_level = swing_low + range_size * 0.382
            
            if price > discount_level:
                return None  # Preço não está em desconto
            
            confluences.append("in_discount")
            
        else:
            # BOS bearish: espera pullback abaixo do swing high
            sl = swing_high + atr * 0.2
            
            range_size = swing_high - swing_low
            premium_level = swing_high - range_size * 0.382
            
            if price < premium_level:
                return None
            
            confluences.append("in_premium")
        
        # Calcula targets
        sl_distance = abs(price - sl)
        tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
        tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
        tp3 = price + sl_distance * self.config.tp3_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp3_r
        
        rr = self.config.tp2_r  # Usa TP2 como referência de RR
        
        trend_strength = self._calculate_trend_strength(mtf_alignment)
        
        return TrendSignal(
            setup=TrendSetup.BOS_CONTINUATION,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confidence=0.75 + len(confluences) * 0.03,
            trend_strength=trend_strength,
            risk_reward=rr,
            mtf_alignment=mtf_alignment,
            confluences=confluences,
            metadata={
                'swing_high': swing_high,
                'swing_low': swing_low,
            }
        )
    
    def _evaluate_ob_pullback(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        order_blocks: List[Dict],
        premium_zone: Optional[Tuple[float, float]],
        discount_zone: Optional[Tuple[float, float]],
        mtf_alignment: Dict,
        confluences: List[str]
    ) -> Optional[TrendSignal]:
        """
        Order Block Pullback Setup.
        
        Entry quando preço retorna a um Order Block válido.
        """
        # Filtra OBs pela direção
        valid_obs = [
            ob for ob in order_blocks
            if (direction == SignalDirection.BUY and ob.get('type') == 'bullish') or
               (direction == SignalDirection.SELL and ob.get('type') == 'bearish')
        ]
        
        if not valid_obs:
            return None
        
        # Procura OB que o preço está tocando
        for ob in valid_obs:
            ob_high = ob.get('high', 0)
            ob_low = ob.get('low', 0)
            
            if ob_low <= price <= ob_high:
                confluences.append("order_block_tap")
                
                # Verifica zona premium/discount
                if direction == SignalDirection.BUY and discount_zone:
                    if discount_zone[0] <= price <= discount_zone[1]:
                        confluences.append("in_discount")
                elif direction == SignalDirection.SELL and premium_zone:
                    if premium_zone[0] <= price <= premium_zone[1]:
                        confluences.append("in_premium")
                
                # Stop abaixo/acima do OB
                if direction == SignalDirection.BUY:
                    sl = ob_low - atr * 0.2
                else:
                    sl = ob_high + atr * 0.2
                
                sl_distance = abs(price - sl)
                tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
                tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
                tp3 = price + sl_distance * self.config.tp3_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp3_r
                
                trend_strength = self._calculate_trend_strength(mtf_alignment)
                
                return TrendSignal(
                    setup=TrendSetup.ORDER_BLOCK_PULLBACK,
                    direction=direction,
                    entry_price=price,
                    stop_loss=sl,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    take_profit_3=tp3,
                    confidence=0.78 + len(confluences) * 0.03,
                    trend_strength=trend_strength,
                    risk_reward=self.config.tp2_r,
                    mtf_alignment=mtf_alignment,
                    confluences=confluences,
                    metadata={
                        'ob_high': ob_high,
                        'ob_low': ob_low,
                    }
                )
        
        return None
    
    def _evaluate_fvg_retest(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        fvg_zones: List[Dict],
        mtf_alignment: Dict,
        confluences: List[str]
    ) -> Optional[TrendSignal]:
        """
        FVG Retest Setup.
        
        Entry quando preço retesta um Fair Value Gap.
        """
        valid_fvgs = [
            fvg for fvg in fvg_zones
            if (direction == SignalDirection.BUY and fvg.get('type') == 'bullish') or
               (direction == SignalDirection.SELL and fvg.get('type') == 'bearish')
        ]
        
        if not valid_fvgs:
            return None
        
        for fvg in valid_fvgs:
            fvg_high = fvg.get('high', 0)
            fvg_low = fvg.get('low', 0)
            
            if fvg_low <= price <= fvg_high:
                confluences.append("fvg_retest")
                
                if direction == SignalDirection.BUY:
                    sl = fvg_low - atr * 0.3
                else:
                    sl = fvg_high + atr * 0.3
                
                sl_distance = abs(price - sl)
                tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
                tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
                tp3 = price + sl_distance * self.config.tp3_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp3_r
                
                trend_strength = self._calculate_trend_strength(mtf_alignment)
                
                return TrendSignal(
                    setup=TrendSetup.FVG_RETEST,
                    direction=direction,
                    entry_price=price,
                    stop_loss=sl,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    take_profit_3=tp3,
                    confidence=0.72 + len(confluences) * 0.03,
                    trend_strength=trend_strength,
                    risk_reward=self.config.tp2_r,
                    mtf_alignment=mtf_alignment,
                    confluences=confluences,
                    metadata={
                        'fvg_high': fvg_high,
                        'fvg_low': fvg_low,
                    }
                )
        
        return None
    
    def _evaluate_fib_pullback(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        fib_levels: Dict[str, float],
        swing_high: float,
        swing_low: float,
        mtf_alignment: Dict,
        confluences: List[str]
    ) -> Optional[TrendSignal]:
        """
        Fibonacci Pullback Setup.
        
        Entry na zona dourada (61.8%-78.6%).
        """
        confluences.append("fibonacci_pullback")
        confluences.append("golden_zone")
        
        fib_618 = fib_levels.get('0.618', 0)
        fib_786 = fib_levels.get('0.786', 0)
        
        if direction == SignalDirection.BUY:
            # Pullback em tendência de alta
            sl = min(fib_786, swing_low) - atr * 0.2
        else:
            sl = max(fib_786, swing_high) + atr * 0.2
        
        sl_distance = abs(price - sl)
        tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
        tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
        tp3 = price + sl_distance * self.config.tp3_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp3_r
        
        trend_strength = self._calculate_trend_strength(mtf_alignment)
        
        return TrendSignal(
            setup=TrendSetup.FIBONACCI_PULLBACK,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confidence=0.73 + len(confluences) * 0.03,
            trend_strength=trend_strength,
            risk_reward=self.config.tp2_r,
            mtf_alignment=mtf_alignment,
            confluences=confluences,
            metadata={
                'fib_618': fib_618,
                'fib_786': fib_786,
            }
        )
    
    def _evaluate_mtf_alignment_entry(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        swing_high: float,
        swing_low: float,
        mtf_alignment: Dict,
        confluences: List[str]
    ) -> Optional[TrendSignal]:
        """
        MTF Alignment Entry.
        
        Entry quando todos os TFs estão alinhados.
        """
        confluences.append("mtf_full_alignment")
        
        if direction == SignalDirection.BUY:
            sl = swing_low - atr * 0.3
        else:
            sl = swing_high + atr * 0.3
        
        sl_distance = abs(price - sl)
        
        # Limita SL por ATR máximo
        if sl_distance > atr * self.config.max_sl_atr:
            return None
        
        tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
        tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
        tp3 = price + sl_distance * self.config.tp3_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp3_r
        
        trend_strength = self._calculate_trend_strength(mtf_alignment)
        
        return TrendSignal(
            setup=TrendSetup.MTF_ALIGNMENT,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confidence=0.80 + len(confluences) * 0.02,
            trend_strength=trend_strength,
            risk_reward=self.config.tp2_r,
            mtf_alignment=mtf_alignment,
            confluences=confluences,
        )
    
    def _evaluate_liquidity_sweep(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        liquidity_pools: List[Dict],
        mtf_alignment: Dict,
        confluences: List[str]
    ) -> Optional[TrendSignal]:
        """
        Liquidity Sweep Continuation.
        
        Após sweep de liquidez, entra na continuação do trend.
        """
        # Procura sweep recente na direção oposta
        for pool in liquidity_pools:
            swept = pool.get('swept', False)
            pool_type = pool.get('type', '')
            
            if not swept:
                continue
            
            # Buy setup: sweep de lows (stop hunt de longs)
            # Sell setup: sweep de highs (stop hunt de shorts)
            if direction == SignalDirection.BUY and pool_type == 'low':
                confluences.append("liquidity_sweep")
                sl = pool.get('level', price) - atr * 0.3
            elif direction == SignalDirection.SELL and pool_type == 'high':
                confluences.append("liquidity_sweep")
                sl = pool.get('level', price) + atr * 0.3
            else:
                continue
            
            sl_distance = abs(price - sl)
            tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
            tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
            tp3 = price + sl_distance * self.config.tp3_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp3_r
            
            trend_strength = self._calculate_trend_strength(mtf_alignment)
            
            return TrendSignal(
                setup=TrendSetup.LIQUIDITY_SWEEP_CONTINUATION,
                direction=direction,
                entry_price=price,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                confidence=0.77 + len(confluences) * 0.03,
                trend_strength=trend_strength,
                risk_reward=self.config.tp2_r,
                mtf_alignment=mtf_alignment,
                confluences=confluences,
                metadata={
                    'pool_level': pool.get('level'),
                    'pool_type': pool_type,
                }
            )
        
        return None
    
    def _calculate_trend_strength(self, mtf_alignment: Dict) -> TrendStrength:
        """Calcula força da tendência baseado no alinhamento MTF."""
        aligned = sum(1 for v in mtf_alignment.values() if v in ['bullish', 'bearish'])
        total = len(mtf_alignment)
        
        if total == 0:
            return TrendStrength.WEAK
        
        ratio = aligned / total
        
        if ratio >= 0.9:
            return TrendStrength.VERY_STRONG
        elif ratio >= 0.7:
            return TrendStrength.STRONG
        elif ratio >= 0.5:
            return TrendStrength.MODERATE
        else:
            return TrendStrength.WEAK
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna informações da estratégia."""
        return {
            'name': 'VIRTUS Trend Following Strategy',
            'type': 'trend',
            'timeframes': {
                'entry': self.config.entry_tf,
                'structure': self.config.structure_tf,
                'bias': self.config.bias_tf,
            },
            'setups': [s.value for s in TrendSetup],
            'config': {
                'min_rr': self.config.min_risk_reward,
                'min_confluences': self.config.min_confluences,
                'tp_levels': {
                    'tp1': f"{self.config.tp1_r}R ({self.config.tp1_percent}%)",
                    'tp2': f"{self.config.tp2_r}R ({self.config.tp2_percent}%)",
                    'tp3': f"{self.config.tp3_r}R ({self.config.tp3_percent}%)",
                },
            },
        }
