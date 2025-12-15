"""
VIRTUS Trailing Stop
=====================

Implementação completa de diferentes tipos de Trailing Stop.
Cada tipo tem sua própria lógica de cálculo baseada em:
- Pips fixos
- ATR dinâmico
- Percentual
- Chandelier Exit
- Parabolic SAR
- Swing-based
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np

from ...core import VirtusLogger


class TrailingStopType(Enum):
    """Tipos de trailing stop disponíveis."""
    FIXED_PIPS = "fixed_pips"           # Distância fixa em pips
    ATR_BASED = "atr_based"             # Baseado em ATR
    PERCENTAGE = "percentage"            # Percentual do preço
    CHANDELIER = "chandelier"           # Chandelier Exit
    PARABOLIC_SAR = "parabolic_sar"     # Parabolic SAR
    SWING_BASED = "swing_based"         # Baseado em swings
    STEP_TRAIL = "step_trail"           # Move em steps fixos
    BREAKEVEN_TRAIL = "breakeven_trail" # Após breakeven


@dataclass
class TrailingStopConfig:
    """Configuração do trailing stop."""
    type: TrailingStopType = TrailingStopType.ATR_BASED
    
    # Ativação
    activation_pips: float = 10.0      # Pips em lucro para ativar
    
    # Fixed Pips
    fixed_distance: float = 20.0       # Distância em pips
    step_pips: float = 5.0             # Movimento mínimo
    
    # ATR Based
    atr_period: int = 14
    atr_multiplier: float = 2.0
    
    # Percentage
    percentage: float = 1.0            # % do preço
    
    # Chandelier
    chandelier_period: int = 22
    chandelier_multiplier: float = 3.0
    
    # Parabolic SAR
    sar_acceleration: float = 0.02
    sar_maximum: float = 0.2
    
    # Swing Based
    swing_lookback: int = 5
    swing_buffer_pips: float = 2.0


@dataclass
class TrailingStopState:
    """Estado atual do trailing stop."""
    active: bool = False
    type: Optional[TrailingStopType] = None
    current_stop: float = 0.0
    initial_stop: float = 0.0
    activation_price: Optional[float] = None
    last_update: datetime = field(default_factory=datetime.now)
    
    # Para tipos específicos
    sar_af: float = 0.02              # Acceleration factor atual
    sar_ep: float = 0.0               # Extreme point
    swing_highs: List[float] = field(default_factory=list)
    swing_lows: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'active': self.active,
            'type': self.type.value if self.type else None,
            'current_stop': round(self.current_stop, 5),
            'initial_stop': round(self.initial_stop, 5),
            'last_update': self.last_update.isoformat(),
        }


class TrailingStop:
    """
    Implementação de Trailing Stop com múltiplos tipos.
    
    Uso:
        trailing = TrailingStop(config)
        
        # A cada tick
        new_sl = trailing.calculate(
            is_buy=True,
            current_price=1850.50,
            current_sl=1845.00,
            atr=2.50,
            highs=[...],
            lows=[...]
        )
        
        if new_sl:
            # Atualiza SL
    """
    
    def __init__(self, config: Optional[TrailingStopConfig] = None):
        self.config = config or TrailingStopConfig()
        self.logger = VirtusLogger.get_logger("trailing_stop")
        
        # Estado
        self.state = TrailingStopState()
        
        # Pip value (será configurado externamente)
        self._pip_value = 0.0001
    
    def set_pip_value(self, pip_value: float) -> None:
        """Configura valor do pip para o símbolo."""
        self._pip_value = pip_value
    
    def initialize(
        self,
        initial_sl: float,
        entry_price: float,
        is_buy: bool
    ) -> None:
        """
        Inicializa o trailing stop.
        
        Args:
            initial_sl: SL inicial da posição
            entry_price: Preço de entrada
            is_buy: Se é posição de compra
        """
        self.state = TrailingStopState(
            active=False,
            type=self.config.type,
            current_stop=initial_sl,
            initial_stop=initial_sl,
            sar_af=self.config.sar_acceleration,
            sar_ep=entry_price
        )
    
    def calculate(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float,
        atr: Optional[float] = None,
        highs: Optional[List[float]] = None,
        lows: Optional[List[float]] = None
    ) -> Optional[float]:
        """
        Calcula novo valor de SL.
        
        Args:
            is_buy: Se é posição de compra
            current_price: Preço atual
            current_sl: SL atual
            atr: Valor ATR (para ATR_BASED)
            highs: Lista de máximas (para CHANDELIER, SWING)
            lows: Lista de mínimas (para CHANDELIER, SWING)
            
        Returns:
            Novo SL se deve ser atualizado, None se não
        """
        # Verifica ativação
        if not self.state.active:
            if self._check_activation(is_buy, current_price, current_sl):
                self.state.active = True
                self.state.activation_price = current_price
                self.logger.debug(f"Trailing ativado @ {current_price}")
            else:
                return None
        
        # Calcula novo SL baseado no tipo
        new_sl = self._calculate_by_type(
            is_buy=is_buy,
            current_price=current_price,
            current_sl=current_sl,
            atr=atr,
            highs=highs,
            lows=lows
        )
        
        if new_sl is None:
            return None
        
        # Verifica se é uma melhoria
        if is_buy:
            if new_sl > current_sl:
                self.state.current_stop = new_sl
                self.state.last_update = datetime.now()
                return new_sl
        else:
            if new_sl < current_sl:
                self.state.current_stop = new_sl
                self.state.last_update = datetime.now()
                return new_sl
        
        return None
    
    def _check_activation(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float
    ) -> bool:
        """Verifica se trailing deve ser ativado."""
        if is_buy:
            profit_pips = (current_price - current_sl) / self._pip_value - \
                         (current_sl - self.state.initial_stop) / self._pip_value
        else:
            profit_pips = (current_sl - current_price) / self._pip_value - \
                         (self.state.initial_stop - current_sl) / self._pip_value
        
        # Simplificação: calcula lucro em pips desde entrada aproximada
        entry_approx = self.state.initial_stop + (20 * self._pip_value) if is_buy else \
                      self.state.initial_stop - (20 * self._pip_value)
        
        if is_buy:
            profit_pips = (current_price - entry_approx) / self._pip_value
        else:
            profit_pips = (entry_approx - current_price) / self._pip_value
        
        return profit_pips >= self.config.activation_pips
    
    def _calculate_by_type(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float,
        atr: Optional[float],
        highs: Optional[List[float]],
        lows: Optional[List[float]]
    ) -> Optional[float]:
        """Calcula SL baseado no tipo configurado."""
        
        if self.config.type == TrailingStopType.FIXED_PIPS:
            return self._calc_fixed_pips(is_buy, current_price, current_sl)
        
        elif self.config.type == TrailingStopType.ATR_BASED:
            if atr is None:
                return self._calc_fixed_pips(is_buy, current_price, current_sl)
            return self._calc_atr_based(is_buy, current_price, current_sl, atr)
        
        elif self.config.type == TrailingStopType.PERCENTAGE:
            return self._calc_percentage(is_buy, current_price, current_sl)
        
        elif self.config.type == TrailingStopType.CHANDELIER:
            if highs is None or lows is None:
                return self._calc_fixed_pips(is_buy, current_price, current_sl)
            return self._calc_chandelier(is_buy, current_price, current_sl, highs, lows, atr)
        
        elif self.config.type == TrailingStopType.PARABOLIC_SAR:
            return self._calc_parabolic_sar(is_buy, current_price, current_sl)
        
        elif self.config.type == TrailingStopType.SWING_BASED:
            if highs is None or lows is None:
                return self._calc_fixed_pips(is_buy, current_price, current_sl)
            return self._calc_swing_based(is_buy, current_price, current_sl, highs, lows)
        
        elif self.config.type == TrailingStopType.STEP_TRAIL:
            return self._calc_step_trail(is_buy, current_price, current_sl)
        
        else:
            return self._calc_fixed_pips(is_buy, current_price, current_sl)
    
    # ========================================================================
    # TIPOS DE TRAILING
    # ========================================================================
    
    def _calc_fixed_pips(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float
    ) -> Optional[float]:
        """
        Trailing de distância fixa em pips.
        
        Mantém SL a X pips do preço atual.
        """
        distance = self.config.fixed_distance * self._pip_value
        step = self.config.step_pips * self._pip_value
        
        if is_buy:
            new_sl = current_price - distance
            if new_sl > current_sl + step:
                return round(new_sl, 5)
        else:
            new_sl = current_price + distance
            if new_sl < current_sl - step:
                return round(new_sl, 5)
        
        return None
    
    def _calc_atr_based(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float,
        atr: float
    ) -> Optional[float]:
        """
        Trailing baseado em ATR.
        
        Distância = ATR * multiplicador
        Mais adaptativo a volatilidade.
        """
        distance = atr * self.config.atr_multiplier
        step = self.config.step_pips * self._pip_value
        
        if is_buy:
            new_sl = current_price - distance
            if new_sl > current_sl + step:
                return round(new_sl, 5)
        else:
            new_sl = current_price + distance
            if new_sl < current_sl - step:
                return round(new_sl, 5)
        
        return None
    
    def _calc_percentage(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float
    ) -> Optional[float]:
        """
        Trailing percentual.
        
        SL a X% do preço atual.
        """
        distance = current_price * (self.config.percentage / 100)
        step = self.config.step_pips * self._pip_value
        
        if is_buy:
            new_sl = current_price - distance
            if new_sl > current_sl + step:
                return round(new_sl, 5)
        else:
            new_sl = current_price + distance
            if new_sl < current_sl - step:
                return round(new_sl, 5)
        
        return None
    
    def _calc_chandelier(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float,
        highs: List[float],
        lows: List[float],
        atr: Optional[float]
    ) -> Optional[float]:
        """
        Chandelier Exit.
        
        Para LONG: Highest High - ATR * mult
        Para SHORT: Lowest Low + ATR * mult
        """
        period = min(self.config.chandelier_period, len(highs), len(lows))
        
        if period < 2:
            return self._calc_fixed_pips(is_buy, current_price, current_sl)
        
        # Calcula ATR se não fornecido
        if atr is None:
            true_ranges = []
            for i in range(1, period):
                tr = max(
                    highs[-i] - lows[-i],
                    abs(highs[-i] - lows[-i-1]) if i < len(lows)-1 else 0,
                    abs(lows[-i] - highs[-i-1]) if i < len(highs)-1 else 0
                )
                true_ranges.append(tr)
            atr = np.mean(true_ranges) if true_ranges else 0.001
        
        mult = self.config.chandelier_multiplier
        step = self.config.step_pips * self._pip_value
        
        if is_buy:
            highest = max(highs[-period:])
            new_sl = highest - (atr * mult)
            if new_sl > current_sl + step:
                return round(new_sl, 5)
        else:
            lowest = min(lows[-period:])
            new_sl = lowest + (atr * mult)
            if new_sl < current_sl - step:
                return round(new_sl, 5)
        
        return None
    
    def _calc_parabolic_sar(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float
    ) -> Optional[float]:
        """
        Parabolic SAR trailing.
        
        Acelera conforme lucro aumenta.
        """
        af = self.state.sar_af
        ep = self.state.sar_ep
        
        # Atualiza extreme point
        if is_buy:
            if current_price > ep:
                ep = current_price
                af = min(af + self.config.sar_acceleration, self.config.sar_maximum)
        else:
            if current_price < ep:
                ep = current_price
                af = min(af + self.config.sar_acceleration, self.config.sar_maximum)
        
        # Calcula novo SAR
        new_sl = current_sl + af * (ep - current_sl)
        
        # Salva estado
        self.state.sar_af = af
        self.state.sar_ep = ep
        
        step = self.config.step_pips * self._pip_value
        
        if is_buy:
            if new_sl > current_sl + step and new_sl < current_price:
                return round(new_sl, 5)
        else:
            if new_sl < current_sl - step and new_sl > current_price:
                return round(new_sl, 5)
        
        return None
    
    def _calc_swing_based(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float,
        highs: List[float],
        lows: List[float]
    ) -> Optional[float]:
        """
        Trailing baseado em swing points.
        
        Usa mínimas/máximas locais como referência.
        """
        lookback = min(self.config.swing_lookback, len(lows) - 2, len(highs) - 2)
        
        if lookback < 2:
            return self._calc_fixed_pips(is_buy, current_price, current_sl)
        
        buffer = self.config.swing_buffer_pips * self._pip_value
        step = self.config.step_pips * self._pip_value
        
        if is_buy:
            # Encontra swing low mais recente
            recent_lows = lows[-lookback:]
            swing_low = min(recent_lows)
            new_sl = swing_low - buffer
            
            if new_sl > current_sl + step:
                return round(new_sl, 5)
        else:
            # Encontra swing high mais recente
            recent_highs = highs[-lookback:]
            swing_high = max(recent_highs)
            new_sl = swing_high + buffer
            
            if new_sl < current_sl - step:
                return round(new_sl, 5)
        
        return None
    
    def _calc_step_trail(
        self,
        is_buy: bool,
        current_price: float,
        current_sl: float
    ) -> Optional[float]:
        """
        Step trailing - move em incrementos fixos.
        
        Só move quando o preço avançou X pips desde último movimento.
        """
        distance = self.config.fixed_distance * self._pip_value
        step = self.config.step_pips * self._pip_value
        
        if is_buy:
            # Calcula quantos steps de distância
            price_from_sl = current_price - current_sl
            expected_distance = distance
            
            if price_from_sl > expected_distance + step:
                new_sl = current_price - expected_distance
                return round(new_sl, 5)
        else:
            price_from_sl = current_sl - current_price
            expected_distance = distance
            
            if price_from_sl > expected_distance + step:
                new_sl = current_price + expected_distance
                return round(new_sl, 5)
        
        return None
    
    # ========================================================================
    # STATUS
    # ========================================================================
    
    def get_state(self) -> TrailingStopState:
        """Retorna estado atual."""
        return self.state
    
    def is_active(self) -> bool:
        """Verifica se trailing está ativo."""
        return self.state.active
    
    def reset(self) -> None:
        """Reseta o trailing stop."""
        self.state = TrailingStopState()


# ============================================================================
# FACTORY
# ============================================================================

def create_trailing_stop(
    trailing_type: str = "atr_based",
    **kwargs
) -> TrailingStop:
    """
    Factory para criar TrailingStop configurado.
    
    Args:
        trailing_type: Tipo do trailing ('fixed_pips', 'atr_based', etc)
        **kwargs: Parâmetros de configuração
        
    Returns:
        TrailingStop configurado
    """
    type_map = {
        'fixed_pips': TrailingStopType.FIXED_PIPS,
        'fixed': TrailingStopType.FIXED_PIPS,
        'atr_based': TrailingStopType.ATR_BASED,
        'atr': TrailingStopType.ATR_BASED,
        'percentage': TrailingStopType.PERCENTAGE,
        'percent': TrailingStopType.PERCENTAGE,
        'chandelier': TrailingStopType.CHANDELIER,
        'parabolic_sar': TrailingStopType.PARABOLIC_SAR,
        'sar': TrailingStopType.PARABOLIC_SAR,
        'swing_based': TrailingStopType.SWING_BASED,
        'swing': TrailingStopType.SWING_BASED,
        'step_trail': TrailingStopType.STEP_TRAIL,
        'step': TrailingStopType.STEP_TRAIL,
    }
    
    ts_type = type_map.get(trailing_type.lower(), TrailingStopType.ATR_BASED)
    
    config = TrailingStopConfig(
        type=ts_type,
        activation_pips=kwargs.get('activation_pips', 10.0),
        fixed_distance=kwargs.get('distance_pips', 20.0),
        step_pips=kwargs.get('step_pips', 5.0),
        atr_period=kwargs.get('atr_period', 14),
        atr_multiplier=kwargs.get('atr_multiplier', 2.0),
        percentage=kwargs.get('percentage', 1.0),
        chandelier_period=kwargs.get('chandelier_period', 22),
        chandelier_multiplier=kwargs.get('chandelier_multiplier', 3.0),
        sar_acceleration=kwargs.get('sar_acceleration', 0.02),
        sar_maximum=kwargs.get('sar_maximum', 0.2),
        swing_lookback=kwargs.get('swing_lookback', 5),
        swing_buffer_pips=kwargs.get('swing_buffer_pips', 2.0),
    )
    
    return TrailingStop(config)
