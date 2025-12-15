"""
VIRTUS Exit Manager
====================

Sistema avançado de gestão de saídas com:
- Trailing Stop dinâmico (ATR-based, Chandelier, Parabolic)
- Partial Exits (escalonamento de saídas)
- Time-based Exits
- Volatility Exits
- Break-even automático
- Target-based Exits (R-multiples)
- Market Structure Exits
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np

from ...core import VirtusLogger


class TrailingStopType(Enum):
    """Tipos de trailing stop."""
    FIXED_PIPS = "fixed_pips"
    ATR_BASED = "atr_based"
    CHANDELIER = "chandelier"
    PARABOLIC_SAR = "parabolic_sar"
    SWING_BASED = "swing_based"
    BREAKEVEN_TRAIL = "breakeven_trail"
    STEP_TRAIL = "step_trail"
    PERCENTAGE = "percentage"


class ExitReason(Enum):
    """Motivos de saída."""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    PARTIAL_EXIT = "partial_exit"
    TIME_EXIT = "time_exit"
    VOLATILITY_EXIT = "volatility_exit"
    BREAKEVEN = "breakeven"
    STRUCTURE_EXIT = "structure_exit"
    MANUAL = "manual"
    SIGNAL_REVERSAL = "signal_reversal"
    RISK_LIMIT = "risk_limit"


@dataclass
class TrailingStopConfig:
    """Configuração de trailing stop."""
    type: TrailingStopType = TrailingStopType.ATR_BASED
    atr_multiplier: float = 2.0
    fixed_pips: float = 20.0
    activation_pips: float = 10.0  # Pips em lucro para ativar
    step_pips: float = 5.0  # Para step trail
    percentage: float = 1.0  # Para percentage trail
    
    # Chandelier
    chandelier_period: int = 22
    chandelier_multiplier: float = 3.0
    
    # Parabolic SAR
    sar_acceleration: float = 0.02
    sar_maximum: float = 0.2


@dataclass
class PartialExitConfig:
    """Configuração de saídas parciais."""
    enabled: bool = True
    levels: List[Dict] = field(default_factory=lambda: [
        {'r_multiple': 1.0, 'exit_percent': 30},
        {'r_multiple': 2.0, 'exit_percent': 30},
        {'r_multiple': 3.0, 'exit_percent': 40},
    ])
    move_sl_to_be_after_first: bool = True
    
    
@dataclass
class TimeExitConfig:
    """Configuração de saídas por tempo."""
    enabled: bool = True
    max_bars: int = 50  # Máximo de barras
    max_hours: int = 24  # Máximo de horas
    friday_close_hour: int = 20  # Fechar antes do fim de semana
    no_overnight: bool = False  # Fechar antes da noite


@dataclass
class ExitSignal:
    """Sinal de saída."""
    should_exit: bool
    reason: ExitReason
    exit_price: float
    exit_percent: float = 100  # Porcentagem para sair
    new_sl: Optional[float] = None
    new_tp: Optional[float] = None
    confidence: float = 0.0
    message: str = ""


@dataclass
class PositionState:
    """Estado de uma posição para gerenciamento de saída."""
    symbol: str
    direction: str  # "buy" ou "sell"
    entry_price: float
    current_price: float
    initial_sl: float
    current_sl: float
    initial_tp: Optional[float]
    current_tp: Optional[float]
    volume: float
    remaining_volume: float
    entry_time: datetime
    
    # Métricas
    highest_price: float = 0.0
    lowest_price: float = 0.0
    current_profit_pips: float = 0.0
    current_r_multiple: float = 0.0
    bars_in_trade: int = 0
    
    # Trailing
    trailing_active: bool = False
    trailing_level: float = 0.0
    
    # Parciais
    partial_exits_done: int = 0
    total_partial_profit: float = 0.0


class ExitManager:
    """
    Gerenciador avançado de saídas.
    
    Features:
    - Trailing stop dinâmico com múltiplos métodos
    - Saídas parciais escalonadas
    - Saídas por tempo
    - Saídas por volatilidade
    - Break-even automático
    - Saídas por estrutura de mercado
    """
    
    def __init__(
        self,
        trailing_config: Optional[TrailingStopConfig] = None,
        partial_config: Optional[PartialExitConfig] = None,
        time_config: Optional[TimeExitConfig] = None,
    ):
        self.logger = VirtusLogger.get_logger("exit_manager")
        
        self.trailing_config = trailing_config or TrailingStopConfig()
        self.partial_config = partial_config or PartialExitConfig()
        self.time_config = time_config or TimeExitConfig()
        
        # Estado das posições
        self.positions: Dict[str, PositionState] = {}
        
        # Parabolic SAR state
        self._sar_state: Dict[str, Dict] = {}
        
        # Lock
        self._lock = asyncio.Lock()
    
    async def evaluate_exit(
        self,
        position_id: str,
        current_price: float,
        atr: Optional[float] = None,
        high: Optional[float] = None,
        low: Optional[float] = None,
        market_structure: Optional[Dict] = None,
    ) -> ExitSignal:
        """
        Avalia se deve sair de uma posição.
        
        Args:
            position_id: ID da posição
            current_price: Preço atual
            atr: ATR atual
            high: High do período
            low: Low do período
            market_structure: Dados de estrutura de mercado
            
        Returns:
            ExitSignal com recomendação
        """
        async with self._lock:
            if position_id not in self.positions:
                return ExitSignal(
                    should_exit=False,
                    reason=ExitReason.MANUAL,
                    exit_price=current_price,
                    message="Position not found"
                )
            
            state = self.positions[position_id]
            state.current_price = current_price
            
            # Atualiza máxima/mínima
            if state.highest_price == 0:
                state.highest_price = current_price
            if state.lowest_price == 0:
                state.lowest_price = current_price
            
            state.highest_price = max(state.highest_price, current_price)
            state.lowest_price = min(state.lowest_price, current_price)
            
            # Calcula profit em pips
            state.current_profit_pips = self._calculate_profit_pips(state)
            
            # Calcula R-multiple
            initial_risk = abs(state.entry_price - state.initial_sl)
            if initial_risk > 0:
                current_profit = abs(current_price - state.entry_price)
                if state.direction == "buy":
                    current_profit = current_price - state.entry_price
                else:
                    current_profit = state.entry_price - current_price
                state.current_r_multiple = current_profit / initial_risk
            
            # Incrementa bars
            state.bars_in_trade += 1
            
            # === VERIFICA STOP LOSS ===
            if self._check_stop_loss(state, current_price):
                return ExitSignal(
                    should_exit=True,
                    reason=ExitReason.STOP_LOSS,
                    exit_price=state.current_sl,
                    exit_percent=100,
                    confidence=1.0,
                    message="Stop loss atingido"
                )
            
            # === VERIFICA TAKE PROFIT ===
            if state.current_tp and self._check_take_profit(state, current_price):
                return ExitSignal(
                    should_exit=True,
                    reason=ExitReason.TAKE_PROFIT,
                    exit_price=state.current_tp,
                    exit_percent=100,
                    confidence=1.0,
                    message="Take profit atingido"
                )
            
            # === VERIFICA SAÍDAS PARCIAIS ===
            partial_signal = self._check_partial_exits(state)
            if partial_signal.should_exit:
                return partial_signal
            
            # === VERIFICA TRAILING STOP ===
            trailing_signal = await self._check_trailing_stop(
                state, current_price, atr, high, low
            )
            if trailing_signal.should_exit:
                return trailing_signal
            elif trailing_signal.new_sl:
                # Atualiza SL sem sair
                state.current_sl = trailing_signal.new_sl
            
            # === VERIFICA SAÍDA POR TEMPO ===
            time_signal = self._check_time_exit(state)
            if time_signal.should_exit:
                return time_signal
            
            # === VERIFICA SAÍDA POR ESTRUTURA ===
            if market_structure:
                structure_signal = self._check_structure_exit(state, market_structure)
                if structure_signal.should_exit:
                    return structure_signal
            
            # === SEM SAÍDA ===
            return ExitSignal(
                should_exit=False,
                reason=ExitReason.MANUAL,
                exit_price=current_price,
                new_sl=state.current_sl,
                message="No exit signal"
            )
    
    def _calculate_profit_pips(self, state: PositionState) -> float:
        """Calcula lucro em pips."""
        if state.direction == "buy":
            diff = state.current_price - state.entry_price
        else:
            diff = state.entry_price - state.current_price
        
        # Converte para pips
        if 'JPY' in state.symbol:
            return diff * 100
        elif 'XAU' in state.symbol:
            return diff * 10
        else:
            return diff * 10000
    
    def _check_stop_loss(self, state: PositionState, current_price: float) -> bool:
        """Verifica se stop loss foi atingido."""
        if state.direction == "buy":
            return current_price <= state.current_sl
        else:
            return current_price >= state.current_sl
    
    def _check_take_profit(self, state: PositionState, current_price: float) -> bool:
        """Verifica se take profit foi atingido."""
        if not state.current_tp:
            return False
        
        if state.direction == "buy":
            return current_price >= state.current_tp
        else:
            return current_price <= state.current_tp
    
    def _check_partial_exits(self, state: PositionState) -> ExitSignal:
        """Verifica saídas parciais por R-multiple."""
        if not self.partial_config.enabled:
            return ExitSignal(
                should_exit=False,
                reason=ExitReason.PARTIAL_EXIT,
                exit_price=state.current_price
            )
        
        levels = self.partial_config.levels
        
        # Verifica cada nível
        for i, level in enumerate(levels):
            if i < state.partial_exits_done:
                continue  # Já executou este nível
            
            r_target = level['r_multiple']
            exit_percent = level['exit_percent']
            
            if state.current_r_multiple >= r_target:
                # Marca como executado
                state.partial_exits_done = i + 1
                
                # Move SL para BE após primeira saída
                new_sl = state.current_sl
                if i == 0 and self.partial_config.move_sl_to_be_after_first:
                    new_sl = state.entry_price
                
                return ExitSignal(
                    should_exit=True,
                    reason=ExitReason.PARTIAL_EXIT,
                    exit_price=state.current_price,
                    exit_percent=exit_percent,
                    new_sl=new_sl,
                    confidence=0.9,
                    message=f"Partial exit at {r_target}R ({exit_percent}%)"
                )
        
        return ExitSignal(
            should_exit=False,
            reason=ExitReason.PARTIAL_EXIT,
            exit_price=state.current_price
        )
    
    async def _check_trailing_stop(
        self,
        state: PositionState,
        current_price: float,
        atr: Optional[float],
        high: Optional[float],
        low: Optional[float],
    ) -> ExitSignal:
        """Verifica e atualiza trailing stop."""
        config = self.trailing_config
        
        # Verifica se deve ativar trailing
        if not state.trailing_active:
            if state.current_profit_pips >= config.activation_pips:
                state.trailing_active = True
                self.logger.debug(f"Trailing activated at {state.current_profit_pips:.1f} pips")
        
        if not state.trailing_active:
            return ExitSignal(
                should_exit=False,
                reason=ExitReason.TRAILING_STOP,
                exit_price=current_price
            )
        
        # Calcula novo SL baseado no tipo
        new_sl = state.current_sl
        
        if config.type == TrailingStopType.FIXED_PIPS:
            new_sl = self._calculate_fixed_trailing(state, config.fixed_pips)
        
        elif config.type == TrailingStopType.ATR_BASED:
            if atr:
                new_sl = self._calculate_atr_trailing(state, atr, config.atr_multiplier)
        
        elif config.type == TrailingStopType.CHANDELIER:
            if atr and high and low:
                new_sl = self._calculate_chandelier_trailing(
                    state, high, low, atr, config.chandelier_multiplier
                )
        
        elif config.type == TrailingStopType.PARABOLIC_SAR:
            new_sl = self._calculate_parabolic_sar(state, high, low)
        
        elif config.type == TrailingStopType.SWING_BASED:
            if high and low:
                new_sl = self._calculate_swing_trailing(state, high, low)
        
        elif config.type == TrailingStopType.STEP_TRAIL:
            new_sl = self._calculate_step_trailing(state, config.step_pips)
        
        elif config.type == TrailingStopType.PERCENTAGE:
            new_sl = self._calculate_percentage_trailing(state, config.percentage)
        
        # Verifica se novo SL é melhor que o atual
        if self._is_better_sl(state, new_sl, state.current_sl):
            # Verifica se foi atingido
            if self._check_stop_loss(state, current_price):
                return ExitSignal(
                    should_exit=True,
                    reason=ExitReason.TRAILING_STOP,
                    exit_price=new_sl,
                    exit_percent=100,
                    confidence=1.0,
                    message=f"Trailing stop hit at {new_sl:.5f}"
                )
            
            return ExitSignal(
                should_exit=False,
                reason=ExitReason.TRAILING_STOP,
                exit_price=current_price,
                new_sl=new_sl,
                message=f"Trailing updated to {new_sl:.5f}"
            )
        
        return ExitSignal(
            should_exit=False,
            reason=ExitReason.TRAILING_STOP,
            exit_price=current_price
        )
    
    def _calculate_fixed_trailing(
        self, 
        state: PositionState, 
        trail_pips: float
    ) -> float:
        """Calcula trailing stop fixo."""
        # Converte pips para preço
        if 'JPY' in state.symbol:
            trail_distance = trail_pips / 100
        elif 'XAU' in state.symbol:
            trail_distance = trail_pips / 10
        else:
            trail_distance = trail_pips / 10000
        
        if state.direction == "buy":
            return state.highest_price - trail_distance
        else:
            return state.lowest_price + trail_distance
    
    def _calculate_atr_trailing(
        self,
        state: PositionState,
        atr: float,
        multiplier: float
    ) -> float:
        """Calcula trailing stop baseado em ATR."""
        trail_distance = atr * multiplier
        
        if state.direction == "buy":
            return state.highest_price - trail_distance
        else:
            return state.lowest_price + trail_distance
    
    def _calculate_chandelier_trailing(
        self,
        state: PositionState,
        high: float,
        low: float,
        atr: float,
        multiplier: float
    ) -> float:
        """
        Calcula Chandelier Exit.
        
        Long: Highest High - ATR * multiplier
        Short: Lowest Low + ATR * multiplier
        """
        if state.direction == "buy":
            return state.highest_price - (atr * multiplier)
        else:
            return state.lowest_price + (atr * multiplier)
    
    def _calculate_parabolic_sar(
        self,
        state: PositionState,
        high: Optional[float],
        low: Optional[float]
    ) -> float:
        """
        Calcula Parabolic SAR.
        """
        config = self.trailing_config
        position_id = f"{state.symbol}_{state.entry_time.timestamp()}"
        
        # Inicializa estado se necessário
        if position_id not in self._sar_state:
            self._sar_state[position_id] = {
                'sar': state.entry_price,
                'ep': state.highest_price if state.direction == "buy" else state.lowest_price,
                'af': config.sar_acceleration,
            }
        
        sar_info = self._sar_state[position_id]
        sar = sar_info['sar']
        ep = sar_info['ep']
        af = sar_info['af']
        
        if state.direction == "buy":
            # Atualiza EP (extreme point)
            if high and high > ep:
                ep = high
                af = min(af + config.sar_acceleration, config.sar_maximum)
            
            # Calcula novo SAR
            new_sar = sar + af * (ep - sar)
            new_sar = min(new_sar, low if low else state.current_price)
        else:
            # Short
            if low and low < ep:
                ep = low
                af = min(af + config.sar_acceleration, config.sar_maximum)
            
            new_sar = sar - af * (sar - ep)
            new_sar = max(new_sar, high if high else state.current_price)
        
        # Atualiza estado
        self._sar_state[position_id] = {'sar': new_sar, 'ep': ep, 'af': af}
        
        return new_sar
    
    def _calculate_swing_trailing(
        self,
        state: PositionState,
        high: float,
        low: float
    ) -> float:
        """Trailing baseado em swing points."""
        if state.direction == "buy":
            # Usa low como referência para longs
            return low - (high - low) * 0.2  # 20% buffer
        else:
            return high + (high - low) * 0.2
    
    def _calculate_step_trailing(
        self,
        state: PositionState,
        step_pips: float
    ) -> float:
        """
        Step trailing - move SL em incrementos fixos.
        """
        if 'JPY' in state.symbol:
            step_price = step_pips / 100
        elif 'XAU' in state.symbol:
            step_price = step_pips / 10
        else:
            step_price = step_pips / 10000
        
        profit_from_entry = abs(state.current_price - state.entry_price)
        steps = int(profit_from_entry / step_price)
        
        if steps <= 0:
            return state.current_sl
        
        if state.direction == "buy":
            new_sl = state.entry_price + (steps - 1) * step_price
            return max(new_sl, state.current_sl)
        else:
            new_sl = state.entry_price - (steps - 1) * step_price
            return min(new_sl, state.current_sl)
    
    def _calculate_percentage_trailing(
        self,
        state: PositionState,
        percentage: float
    ) -> float:
        """Trailing baseado em porcentagem do preço."""
        trail_distance = state.current_price * (percentage / 100)
        
        if state.direction == "buy":
            return state.highest_price - trail_distance
        else:
            return state.lowest_price + trail_distance
    
    def _is_better_sl(
        self,
        state: PositionState,
        new_sl: float,
        current_sl: float
    ) -> bool:
        """Verifica se novo SL é melhor (mais favorável) que o atual."""
        if state.direction == "buy":
            return new_sl > current_sl
        else:
            return new_sl < current_sl
    
    def _check_time_exit(self, state: PositionState) -> ExitSignal:
        """Verifica saída por tempo."""
        if not self.time_config.enabled:
            return ExitSignal(
                should_exit=False,
                reason=ExitReason.TIME_EXIT,
                exit_price=state.current_price
            )
        
        now = datetime.now()
        
        # Verifica máximo de barras
        if state.bars_in_trade >= self.time_config.max_bars:
            return ExitSignal(
                should_exit=True,
                reason=ExitReason.TIME_EXIT,
                exit_price=state.current_price,
                exit_percent=100,
                confidence=0.7,
                message=f"Max bars ({self.time_config.max_bars}) reached"
            )
        
        # Verifica máximo de horas
        hours_in_trade = (now - state.entry_time).total_seconds() / 3600
        if hours_in_trade >= self.time_config.max_hours:
            return ExitSignal(
                should_exit=True,
                reason=ExitReason.TIME_EXIT,
                exit_price=state.current_price,
                exit_percent=100,
                confidence=0.7,
                message=f"Max hours ({self.time_config.max_hours}) reached"
            )
        
        # Verifica fechamento de sexta
        if now.weekday() == 4:  # Friday
            if now.hour >= self.time_config.friday_close_hour:
                return ExitSignal(
                    should_exit=True,
                    reason=ExitReason.TIME_EXIT,
                    exit_price=state.current_price,
                    exit_percent=100,
                    confidence=0.9,
                    message="Friday close before weekend"
                )
        
        return ExitSignal(
            should_exit=False,
            reason=ExitReason.TIME_EXIT,
            exit_price=state.current_price
        )
    
    def _check_structure_exit(
        self,
        state: PositionState,
        market_structure: Dict
    ) -> ExitSignal:
        """
        Verifica saída baseada em estrutura de mercado.
        
        Sai se:
        - Break of Structure contra a posição
        - CHoCH detectado
        - Entrada em zona de premium/discount desfavorável
        """
        trend = market_structure.get('trend', 'neutral')
        bos_detected = market_structure.get('bos_detected', False)
        choch_detected = market_structure.get('choch_detected', False)
        zone = market_structure.get('zone', 'equilibrium')
        
        # CHoCH sempre indica saída
        if choch_detected:
            return ExitSignal(
                should_exit=True,
                reason=ExitReason.STRUCTURE_EXIT,
                exit_price=state.current_price,
                exit_percent=100,
                confidence=0.85,
                message="Change of Character detected"
            )
        
        # BOS contra a posição
        if bos_detected:
            if state.direction == "buy" and trend == "bearish":
                return ExitSignal(
                    should_exit=True,
                    reason=ExitReason.STRUCTURE_EXIT,
                    exit_price=state.current_price,
                    exit_percent=100,
                    confidence=0.80,
                    message="Bearish BOS against long"
                )
            elif state.direction == "sell" and trend == "bullish":
                return ExitSignal(
                    should_exit=True,
                    reason=ExitReason.STRUCTURE_EXIT,
                    exit_price=state.current_price,
                    exit_percent=100,
                    confidence=0.80,
                    message="Bullish BOS against short"
                )
        
        # Zona desfavorável
        if state.direction == "buy" and zone == "premium":
            # Comprado em zona de premium é ruim
            if state.current_r_multiple >= 1.5:
                return ExitSignal(
                    should_exit=True,
                    reason=ExitReason.STRUCTURE_EXIT,
                    exit_price=state.current_price,
                    exit_percent=50,  # Saída parcial
                    confidence=0.6,
                    message="Long in premium zone"
                )
        elif state.direction == "sell" and zone == "discount":
            if state.current_r_multiple >= 1.5:
                return ExitSignal(
                    should_exit=True,
                    reason=ExitReason.STRUCTURE_EXIT,
                    exit_price=state.current_price,
                    exit_percent=50,
                    confidence=0.6,
                    message="Short in discount zone"
                )
        
        return ExitSignal(
            should_exit=False,
            reason=ExitReason.STRUCTURE_EXIT,
            exit_price=state.current_price
        )
    
    async def register_position(
        self,
        position_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float],
        volume: float,
    ) -> None:
        """Registra nova posição para gerenciamento."""
        async with self._lock:
            self.positions[position_id] = PositionState(
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                current_price=entry_price,
                initial_sl=stop_loss,
                current_sl=stop_loss,
                initial_tp=take_profit,
                current_tp=take_profit,
                volume=volume,
                remaining_volume=volume,
                entry_time=datetime.now(),
                highest_price=entry_price,
                lowest_price=entry_price,
            )
            
            self.logger.info(
                f"Position registered: {position_id} | "
                f"{direction.upper()} {symbol} @ {entry_price:.5f}"
            )
    
    async def update_position_volume(
        self,
        position_id: str,
        closed_volume: float,
        profit: float
    ) -> None:
        """Atualiza volume após saída parcial."""
        async with self._lock:
            if position_id in self.positions:
                state = self.positions[position_id]
                state.remaining_volume -= closed_volume
                state.total_partial_profit += profit
                
                if state.remaining_volume <= 0:
                    del self.positions[position_id]
    
    async def close_position(self, position_id: str) -> None:
        """Remove posição do gerenciamento."""
        async with self._lock:
            if position_id in self.positions:
                del self.positions[position_id]
            
            # Limpa estado do SAR
            for key in list(self._sar_state.keys()):
                if key.startswith(position_id):
                    del self._sar_state[key]
    
    def get_position_state(self, position_id: str) -> Optional[PositionState]:
        """Retorna estado atual de uma posição."""
        return self.positions.get(position_id)
    
    def get_all_positions(self) -> Dict[str, PositionState]:
        """Retorna todas as posições sendo gerenciadas."""
        return self.positions.copy()
