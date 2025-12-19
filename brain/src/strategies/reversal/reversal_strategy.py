"""
VIRTUS Reversal Strategy
=========================

Estratégia de reversão avançada baseada em:
- Change of Character (CHoCH)
- Divergências (RSI, MACD, Hidden)
- Smart Money reversals
- Exhaustion patterns
- Supply/Demand zones
- Fibonacci extensions
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


class ReversalSetup(Enum):
    """Tipos de setup de reversão."""
    CHOCH_REVERSAL = "choch_reversal"
    DIVERGENCE_REVERSAL = "divergence_reversal"
    EXHAUSTION_PATTERN = "exhaustion_pattern"
    SUPPLY_DEMAND_REJECTION = "supply_demand_rejection"
    FIBONACCI_EXTENSION = "fibonacci_extension"
    LIQUIDITY_TRAP = "liquidity_trap"
    WYCKOFF_SPRING_UPTHRUST = "wyckoff_spring_upthrust"
    DOUBLE_TOP_BOTTOM = "double_top_bottom"


class DivergenceType(Enum):
    """Tipos de divergência."""
    REGULAR_BULLISH = "regular_bullish"
    REGULAR_BEARISH = "regular_bearish"
    HIDDEN_BULLISH = "hidden_bullish"
    HIDDEN_BEARISH = "hidden_bearish"


@dataclass
class ReversalSignal:
    """Sinal de reversão."""
    setup: ReversalSetup
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    confidence: float
    risk_reward: float
    reversal_confirmations: List[str]
    invalidation_level: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReversalConfig:
    """Configuração da estratégia de reversão."""
    # Timeframes
    signal_tf: str = "M15"
    confirmation_tf: str = "H1"
    
    # Divergence
    min_divergence_strength: float = 0.6
    require_multiple_divergence: bool = False
    
    # Risk
    min_risk_reward: float = 2.5
    max_sl_atr: float = 3.0
    
    # Confirmation
    min_confirmations: int = 2
    require_choch: bool = True
    require_volume_spike: bool = True
    
    # Targets
    tp1_r: float = 2.0
    tp2_r: float = 4.0
    
    # Exhaustion
    exhaustion_volume_multiplier: float = 2.0
    exhaustion_atr_multiplier: float = 1.5


class ReversalStrategy:
    """
    Estratégia de Reversão SMC.
    
    Lógica:
    1. Identifica exaustão do trend atual
    2. Confirma com CHoCH ou divergência
    3. Entry em ponto de interesse (OB, FVG)
    4. SL acima/abaixo da estrutura
    
    Setups:
    1. CHoCH Reversal - Mudança de caráter confirma reversão
    2. Divergence Reversal - Divergência + rejeição de nível
    3. Exhaustion Pattern - Volume e momentum extremos
    4. Supply/Demand Rejection - Rejeição forte em S/D zone
    5. Fibonacci Extension - Reversão em extensão (1.272, 1.618)
    6. Liquidity Trap - Armadilha de liquidez institucional
    7. Wyckoff Spring/Upthrust - Padrões clássicos Wyckoff
    8. Double Top/Bottom - Padrões clássicos com confirmação SMC
    """
    
    def __init__(self, config: Optional[ReversalConfig] = None):
        self.config = config or ReversalConfig()
        self.logger = VirtusLogger.get_logger("reversal_strategy")
    
    async def find_setups(
        self,
        market_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Interface para TradingEngine - encontra setups de reversão.
        
        Args:
            market_data: Dados de mercado
            analysis: Análise técnica completa
            
        Returns:
            Lista de setups encontrados
        """
        setups = []
        
        try:
            # Extrai dados
            symbol = market_data.get('symbol', '')
            tick = analysis.get('tick', {})
            current_price = tick.get('bid') or tick.get('last') or analysis.get('price', 0)
            
            if not current_price:
                return setups
            
            # Indicadores
            indicators = analysis.get('indicators', {})
            volatility = analysis.get('volatility', {})
            atr = volatility.get('atr', 0) or indicators.get('atr', 0)
            
            # RSI para divergências simples
            rsi = indicators.get('rsi', 50)
            
            # Bollinger para extremos
            bb = indicators.get('bollinger', {})
            bb_lower = bb.get('lower', 0)
            bb_upper = bb.get('upper', 0)
            
            # Reversão simples: RSI extremo + preço em banda
            if rsi and bb_lower and bb_upper:
                # Oversold extremo
                if rsi < 25 and current_price <= bb_lower:
                    sl_distance = atr * 2 if atr else current_price * 0.005
                    tp_distance = atr * 5 if atr else current_price * 0.012
                    
                    setups.append({
                        'name': 'reversal_oversold_extreme',
                        'direction': 'buy',
                        'entry': current_price,
                        'sl': current_price - sl_distance,
                        'tp': current_price + tp_distance,
                        'score': 0.7,
                        'risk_reward': tp_distance / sl_distance if sl_distance else 2.5,
                    })
                    
                # Overbought extremo
                elif rsi > 75 and current_price >= bb_upper:
                    sl_distance = atr * 2 if atr else current_price * 0.005
                    tp_distance = atr * 5 if atr else current_price * 0.012
                    
                    setups.append({
                        'name': 'reversal_overbought_extreme',
                        'direction': 'sell',
                        'entry': current_price,
                        'sl': current_price + sl_distance,
                        'tp': current_price - tp_distance,
                        'score': 0.7,
                        'risk_reward': tp_distance / sl_distance if sl_distance else 2.5,
                    })
                    
        except Exception as e:
            self.logger.error(f"Erro em find_setups: {e}")
        
        return setups
    
    async def evaluate(
        self,
        symbol: str,
        current_price: float,
        atr: float,
        # Structure
        choch_detected: bool = False,
        choch_direction: str = "",
        trend: str = "neutral",
        swing_high: float = 0,
        swing_low: float = 0,
        # Divergences
        divergences: List[Dict] = None,
        # Volume
        volume: float = 0,
        avg_volume: float = 0,
        volume_spike: bool = False,
        # SMC
        supply_zones: List[Dict] = None,
        demand_zones: List[Dict] = None,
        order_blocks: List[Dict] = None,
        # Fibonacci
        fib_extensions: Dict[str, float] = None,
        at_fib_extension: bool = False,
        extension_level: str = "",
        # Wyckoff
        wyckoff_pattern: Optional[str] = None,  # 'spring', 'upthrust'
        # Patterns
        double_top: bool = False,
        double_bottom: bool = False,
        pattern_neckline: float = 0,
    ) -> Optional[ReversalSignal]:
        """
        Avalia setups de reversão.
        """
        confirmations = []
        
        # === VERIFICA CONDIÇÕES BÁSICAS ===
        
        # Precisa estar em tendência para reverter
        if trend == "neutral":
            return None
        
        # Direção da reversão
        if trend == "bullish":
            reversal_direction = SignalDirection.SELL
        else:
            reversal_direction = SignalDirection.BUY
        
        # CHoCH é forte confirmação
        if choch_detected:
            if (choch_direction == "bearish" and reversal_direction == SignalDirection.SELL) or \
               (choch_direction == "bullish" and reversal_direction == SignalDirection.BUY):
                confirmations.append("choch_confirmed")
        
        # Volume spike
        if volume_spike:
            confirmations.append("volume_spike")
        elif volume > avg_volume * 1.5:
            confirmations.append("above_avg_volume")
        
        # === AVALIA SETUPS ===
        signals: List[ReversalSignal] = []
        
        # 1. CHoCH Reversal
        if choch_detected and "choch_confirmed" in confirmations:
            signal = self._evaluate_choch_reversal(
                current_price, reversal_direction, atr,
                swing_high, swing_low, confirmations.copy()
            )
            if signal:
                signals.append(signal)
        
        # 2. Divergence Reversal
        if divergences:
            signal = self._evaluate_divergence_reversal(
                current_price, reversal_direction, atr,
                divergences, swing_high, swing_low, confirmations.copy()
            )
            if signal:
                signals.append(signal)
        
        # 3. Exhaustion Pattern
        if volume_spike and volume > avg_volume * self.config.exhaustion_volume_multiplier:
            signal = self._evaluate_exhaustion(
                current_price, reversal_direction, atr,
                swing_high, swing_low, confirmations.copy()
            )
            if signal:
                signals.append(signal)
        
        # 4. Supply/Demand Rejection
        if (supply_zones and reversal_direction == SignalDirection.SELL) or \
           (demand_zones and reversal_direction == SignalDirection.BUY):
            signal = self._evaluate_sd_rejection(
                current_price, reversal_direction, atr,
                supply_zones or [], demand_zones or [],
                confirmations.copy()
            )
            if signal:
                signals.append(signal)
        
        # 5. Fibonacci Extension
        if at_fib_extension and fib_extensions:
            signal = self._evaluate_fib_extension(
                current_price, reversal_direction, atr,
                fib_extensions, extension_level,
                swing_high, swing_low, confirmations.copy()
            )
            if signal:
                signals.append(signal)
        
        # 6. Liquidity Trap
        signal = self._evaluate_liquidity_trap(
            current_price, reversal_direction, atr,
            swing_high, swing_low, volume_spike, confirmations.copy()
        )
        if signal:
            signals.append(signal)
        
        # 7. Wyckoff Spring/Upthrust
        if wyckoff_pattern:
            signal = self._evaluate_wyckoff(
                current_price, reversal_direction, atr,
                wyckoff_pattern, swing_high, swing_low, confirmations.copy()
            )
            if signal:
                signals.append(signal)
        
        # 8. Double Top/Bottom
        if (double_top and reversal_direction == SignalDirection.SELL) or \
           (double_bottom and reversal_direction == SignalDirection.BUY):
            signal = self._evaluate_double_pattern(
                current_price, reversal_direction, atr,
                double_top, double_bottom, pattern_neckline,
                swing_high, swing_low, confirmations.copy()
            )
            if signal:
                signals.append(signal)
        
        # === FILTRA E SELECIONA ===
        if not signals:
            return None
        
        # Filtra por confirmações mínimas
        valid_signals = [
            s for s in signals
            if len(s.reversal_confirmations) >= self.config.min_confirmations
        ]
        
        # Verifica CHoCH obrigatório
        if self.config.require_choch:
            valid_signals = [
                s for s in valid_signals
                if "choch_confirmed" in s.reversal_confirmations
            ]
        
        if not valid_signals:
            return None
        
        # Seleciona melhor
        best_signal = max(valid_signals, key=lambda s: s.confidence * s.risk_reward)
        
        if best_signal.risk_reward < self.config.min_risk_reward:
            return None
        
        self.logger.info(
            f"🔄 Reversal signal: {best_signal.setup.value} "
            f"{best_signal.direction.value} @ {best_signal.entry_price:.5f} "
            f"SL: {best_signal.stop_loss:.5f} "
            f"Confirmations: {len(best_signal.reversal_confirmations)}"
        )
        
        return best_signal
    
    def _evaluate_choch_reversal(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        swing_high: float,
        swing_low: float,
        confirmations: List[str]
    ) -> Optional[ReversalSignal]:
        """CHoCH Reversal Setup."""
        confirmations.append("choch_reversal")
        
        if direction == SignalDirection.BUY:
            # Reversão bullish após CHoCH
            sl = swing_low - atr * 0.3
            invalidation = swing_low - atr * 0.5
        else:
            # Reversão bearish
            sl = swing_high + atr * 0.3
            invalidation = swing_high + atr * 0.5
        
        sl_distance = abs(price - sl)
        tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
        tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
        
        return ReversalSignal(
            setup=ReversalSetup.CHOCH_REVERSAL,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            confidence=0.80 + len(confirmations) * 0.03,
            risk_reward=self.config.tp2_r,
            reversal_confirmations=confirmations,
            invalidation_level=invalidation,
        )
    
    def _evaluate_divergence_reversal(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        divergences: List[Dict],
        swing_high: float,
        swing_low: float,
        confirmations: List[str]
    ) -> Optional[ReversalSignal]:
        """Divergence Reversal Setup."""
        # Filtra divergências relevantes
        valid_divs = []
        
        for div in divergences:
            div_type = div.get('type', '')
            strength = div.get('strength', 0)
            
            if strength < self.config.min_divergence_strength:
                continue
            
            # Regular bullish = buy, Regular bearish = sell
            if direction == SignalDirection.BUY and div_type in ['regular_bullish', 'hidden_bullish']:
                valid_divs.append(div)
            elif direction == SignalDirection.SELL and div_type in ['regular_bearish', 'hidden_bearish']:
                valid_divs.append(div)
        
        if not valid_divs:
            return None
        
        # Adiciona confirmações
        for div in valid_divs:
            confirmations.append(f"divergence_{div.get('indicator', 'unknown')}")
        
        if len(valid_divs) >= 2:
            confirmations.append("multiple_divergence")
        
        if direction == SignalDirection.BUY:
            sl = swing_low - atr * 0.4
            invalidation = swing_low - atr * 0.6
        else:
            sl = swing_high + atr * 0.4
            invalidation = swing_high + atr * 0.6
        
        sl_distance = abs(price - sl)
        tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
        tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
        
        # Boost de confiança por múltiplas divergências
        confidence = 0.70 + len(valid_divs) * 0.05 + len(confirmations) * 0.02
        
        return ReversalSignal(
            setup=ReversalSetup.DIVERGENCE_REVERSAL,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            confidence=min(confidence, 0.95),
            risk_reward=self.config.tp2_r,
            reversal_confirmations=confirmations,
            invalidation_level=invalidation,
            metadata={
                'divergences': [d.get('type') for d in valid_divs],
            }
        )
    
    def _evaluate_exhaustion(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        swing_high: float,
        swing_low: float,
        confirmations: List[str]
    ) -> Optional[ReversalSignal]:
        """Exhaustion Pattern Setup."""
        confirmations.append("exhaustion_volume")
        
        if direction == SignalDirection.BUY:
            # Exaustão vendedora
            sl = swing_low - atr * 0.5
            invalidation = swing_low - atr * 0.7
        else:
            # Exaustão compradora
            sl = swing_high + atr * 0.5
            invalidation = swing_high + atr * 0.7
        
        sl_distance = abs(price - sl)
        tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
        tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
        
        return ReversalSignal(
            setup=ReversalSetup.EXHAUSTION_PATTERN,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            confidence=0.65 + len(confirmations) * 0.04,
            risk_reward=self.config.tp2_r,
            reversal_confirmations=confirmations,
            invalidation_level=invalidation,
        )
    
    def _evaluate_sd_rejection(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        supply_zones: List[Dict],
        demand_zones: List[Dict],
        confirmations: List[str]
    ) -> Optional[ReversalSignal]:
        """Supply/Demand Rejection Setup."""
        zones = supply_zones if direction == SignalDirection.SELL else demand_zones
        
        for zone in zones:
            zone_high = zone.get('high', 0)
            zone_low = zone.get('low', 0)
            strength = zone.get('strength', 0.5)
            
            # Verifica se preço está na zona
            if zone_low <= price <= zone_high:
                confirmations.append(f"{'supply' if direction == SignalDirection.SELL else 'demand'}_zone")
                
                if direction == SignalDirection.SELL:
                    sl = zone_high + atr * 0.3
                    invalidation = zone_high + atr * 0.5
                else:
                    sl = zone_low - atr * 0.3
                    invalidation = zone_low - atr * 0.5
                
                sl_distance = abs(price - sl)
                tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
                tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
                
                return ReversalSignal(
                    setup=ReversalSetup.SUPPLY_DEMAND_REJECTION,
                    direction=direction,
                    entry_price=price,
                    stop_loss=sl,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    confidence=0.70 + strength * 0.1 + len(confirmations) * 0.03,
                    risk_reward=self.config.tp2_r,
                    reversal_confirmations=confirmations,
                    invalidation_level=invalidation,
                    metadata={
                        'zone_high': zone_high,
                        'zone_low': zone_low,
                    }
                )
        
        return None
    
    def _evaluate_fib_extension(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        fib_extensions: Dict[str, float],
        extension_level: str,
        swing_high: float,
        swing_low: float,
        confirmations: List[str]
    ) -> Optional[ReversalSignal]:
        """Fibonacci Extension Reversal."""
        confirmations.append(f"fib_extension_{extension_level}")
        
        # Níveis de extensão mais fortes para reversão
        strong_levels = ['1.272', '1.618', '2.0', '2.618']
        
        if extension_level in strong_levels:
            confirmations.append("strong_extension")
        
        if direction == SignalDirection.BUY:
            sl = swing_low - atr * 0.4
            invalidation = swing_low - atr * 0.6
        else:
            sl = swing_high + atr * 0.4
            invalidation = swing_high + atr * 0.6
        
        sl_distance = abs(price - sl)
        tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
        tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
        
        return ReversalSignal(
            setup=ReversalSetup.FIBONACCI_EXTENSION,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            confidence=0.68 + len(confirmations) * 0.04,
            risk_reward=self.config.tp2_r,
            reversal_confirmations=confirmations,
            invalidation_level=invalidation,
            metadata={
                'extension_level': extension_level,
            }
        )
    
    def _evaluate_liquidity_trap(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        swing_high: float,
        swing_low: float,
        volume_spike: bool,
        confirmations: List[str]
    ) -> Optional[ReversalSignal]:
        """Liquidity Trap Setup."""
        if not volume_spike:
            return None
        
        # Verifica se preço fez novo extremo e voltou rapidamente
        range_size = swing_high - swing_low
        
        if direction == SignalDirection.BUY:
            # Trap de lows - preço varrru lows e voltou
            distance_from_low = price - swing_low
            if distance_from_low > range_size * 0.3:
                return None  # Já subiu muito
            
            confirmations.append("liquidity_trap_lows")
            sl = swing_low - atr * 0.3
            invalidation = swing_low - atr * 0.5
        else:
            # Trap de highs
            distance_from_high = swing_high - price
            if distance_from_high > range_size * 0.3:
                return None
            
            confirmations.append("liquidity_trap_highs")
            sl = swing_high + atr * 0.3
            invalidation = swing_high + atr * 0.5
        
        sl_distance = abs(price - sl)
        tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
        tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
        
        return ReversalSignal(
            setup=ReversalSetup.LIQUIDITY_TRAP,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            confidence=0.72 + len(confirmations) * 0.04,
            risk_reward=self.config.tp2_r,
            reversal_confirmations=confirmations,
            invalidation_level=invalidation,
        )
    
    def _evaluate_wyckoff(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        pattern: str,
        swing_high: float,
        swing_low: float,
        confirmations: List[str]
    ) -> Optional[ReversalSignal]:
        """Wyckoff Spring/Upthrust Setup."""
        # Spring = bullish (compra após sweep de lows)
        # Upthrust = bearish (venda após sweep de highs)
        
        if pattern == 'spring' and direction != SignalDirection.BUY:
            return None
        if pattern == 'upthrust' and direction != SignalDirection.SELL:
            return None
        
        confirmations.append(f"wyckoff_{pattern}")
        
        if direction == SignalDirection.BUY:
            sl = swing_low - atr * 0.3
            invalidation = swing_low - atr * 0.5
        else:
            sl = swing_high + atr * 0.3
            invalidation = swing_high + atr * 0.5
        
        sl_distance = abs(price - sl)
        tp1 = price + sl_distance * self.config.tp1_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp1_r
        tp2 = price + sl_distance * self.config.tp2_r if direction == SignalDirection.BUY else price - sl_distance * self.config.tp2_r
        
        return ReversalSignal(
            setup=ReversalSetup.WYCKOFF_SPRING_UPTHRUST,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            confidence=0.78 + len(confirmations) * 0.03,
            risk_reward=self.config.tp2_r,
            reversal_confirmations=confirmations,
            invalidation_level=invalidation,
            metadata={
                'pattern': pattern,
            }
        )
    
    def _evaluate_double_pattern(
        self,
        price: float,
        direction: SignalDirection,
        atr: float,
        double_top: bool,
        double_bottom: bool,
        neckline: float,
        swing_high: float,
        swing_low: float,
        confirmations: List[str]
    ) -> Optional[ReversalSignal]:
        """Double Top/Bottom Setup."""
        if double_top:
            confirmations.append("double_top")
            sl = swing_high + atr * 0.3
            invalidation = swing_high + atr * 0.5
            # Target = distância do topo ao neckline
            pattern_height = swing_high - neckline
            tp1 = neckline - pattern_height * 0.618
            tp2 = neckline - pattern_height
        else:
            confirmations.append("double_bottom")
            sl = swing_low - atr * 0.3
            invalidation = swing_low - atr * 0.5
            pattern_height = neckline - swing_low
            tp1 = neckline + pattern_height * 0.618
            tp2 = neckline + pattern_height
        
        sl_distance = abs(price - sl)
        rr = abs(tp2 - price) / sl_distance if sl_distance > 0 else 0
        
        return ReversalSignal(
            setup=ReversalSetup.DOUBLE_TOP_BOTTOM,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            confidence=0.75 + len(confirmations) * 0.03,
            risk_reward=rr,
            reversal_confirmations=confirmations,
            invalidation_level=invalidation,
            metadata={
                'pattern': 'double_top' if double_top else 'double_bottom',
                'neckline': neckline,
            }
        )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna informações da estratégia."""
        return {
            'name': 'VIRTUS Reversal Strategy',
            'type': 'reversal',
            'setups': [s.value for s in ReversalSetup],
            'config': {
                'min_rr': self.config.min_risk_reward,
                'min_confirmations': self.config.min_confirmations,
                'require_choch': self.config.require_choch,
            },
        }
