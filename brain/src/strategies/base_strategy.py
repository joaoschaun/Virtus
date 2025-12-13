"""
BRAIN - Base Strategy
Interface base para todas as estratégias de trading
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.types import Signal, SignalDirection, MarketRegime, Timeframe
from ..core.logger import get_logger

logger = get_logger("strategy")


class StrategyState(Enum):
    """Estado da estratégia"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    SIGNAL_GENERATED = "signal_generated"
    IN_TRADE = "in_trade"
    DISABLED = "disabled"


@dataclass
class StrategyConfig:
    """Configuração de uma estratégia"""
    name: str
    enabled: bool = True
    timeframes: List[Timeframe] = field(default_factory=lambda: [Timeframe.H1])
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_per_trade: float = 1.0
    max_positions: int = 1
    allowed_sessions: List[str] = field(default_factory=lambda: ["london", "newyork"])


class BaseStrategy(ABC):
    """
    Classe base abstrata para estratégias de trading
    
    Toda estratégia deve:
    1. Implementar generate_signal()
    2. Implementar validate_signal()
    3. Opcionalmente implementar calculate_sl_tp()
    """
    
    def __init__(
        self,
        config: StrategyConfig,
        symbol: str
    ):
        self._config = config
        self._symbol = symbol
        self._state = StrategyState.IDLE
        self._last_signal: Optional[Signal] = None
        self._signals_count = 0
        self._wins = 0
        self._losses = 0
        
        self._logger = get_logger(f"strategy.{config.name}")
    
    @property
    def name(self) -> str:
        """Nome da estratégia"""
        return self._config.name
    
    @property
    def symbol(self) -> str:
        """Símbolo associado"""
        return self._symbol
    
    @property
    def state(self) -> StrategyState:
        """Estado atual"""
        return self._state
    
    @property
    def is_enabled(self) -> bool:
        """Verifica se estratégia está habilitada"""
        return self._config.enabled and self._state != StrategyState.DISABLED
    
    @property
    def win_rate(self) -> float:
        """Taxa de acerto"""
        total = self._wins + self._losses
        return (self._wins / total * 100) if total > 0 else 0.0
    
    @abstractmethod
    async def generate_signal(
        self,
        bars: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Signal]:
        """
        Gera sinal de trading
        
        Args:
            bars: Lista de candles
            context: Contexto do Brain (notícias, sentimento, etc.)
            
        Returns:
            Signal se condições atendidas, None caso contrário
        """
        pass
    
    @abstractmethod
    async def validate_signal(
        self,
        signal: Signal,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Valida um sinal gerado
        
        Args:
            signal: Sinal a validar
            context: Contexto adicional
            
        Returns:
            True se sinal é válido
        """
        pass
    
    def calculate_sl_tp(
        self,
        direction: SignalDirection,
        entry_price: float,
        atr: Optional[float] = None
    ) -> tuple[float, float]:
        """
        Calcula Stop Loss e Take Profit
        
        Args:
            direction: Direção do trade
            entry_price: Preço de entrada
            atr: ATR atual (opcional)
            
        Returns:
            Tuple (stop_loss, take_profit)
        """
        # Implementação padrão - pode ser sobrescrita
        sl_pips = self._config.parameters.get("default_sl_pips", 50)
        tp_pips = self._config.parameters.get("default_tp_pips", 100)
        
        pip_value = 0.0001 if "JPY" not in self._symbol else 0.01
        
        if direction == SignalDirection.BUY:
            sl = entry_price - (sl_pips * pip_value)
            tp = entry_price + (tp_pips * pip_value)
        else:
            sl = entry_price + (sl_pips * pip_value)
            tp = entry_price - (tp_pips * pip_value)
        
        return sl, tp
    
    def on_trade_result(self, profit: float):
        """
        Callback quando trade é fechado
        
        Args:
            profit: Resultado do trade
        """
        if profit > 0:
            self._wins += 1
        else:
            self._losses += 1
    
    def enable(self):
        """Habilita a estratégia"""
        self._state = StrategyState.IDLE
        self._config.enabled = True
    
    def disable(self):
        """Desabilita a estratégia"""
        self._state = StrategyState.DISABLED
        self._config.enabled = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da estratégia"""
        return {
            "name": self.name,
            "symbol": self._symbol,
            "state": self._state.value,
            "enabled": self._config.enabled,
            "signals_count": self._signals_count,
            "wins": self._wins,
            "losses": self._losses,
            "win_rate": self.win_rate
        }
    
    def _create_signal(
        self,
        direction: SignalDirection,
        entry_price: float,
        confidence: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        reason: str = ""
    ) -> Signal:
        """
        Cria um novo sinal
        
        Helper para subclasses criarem sinais padronizados
        """
        # Calcular SL/TP se não fornecidos
        if stop_loss is None or take_profit is None:
            sl, tp = self.calculate_sl_tp(direction, entry_price)
            stop_loss = stop_loss or sl
            take_profit = take_profit or tp
        
        self._signals_count += 1
        
        signal = Signal(
            id=f"{self.name}_{self._symbol}_{self._signals_count}",
            symbol=self._symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            strategy=self.name,
            timeframe=self._config.timeframes[0],
            timestamp=datetime.now(),
            reason=reason
        )
        
        self._last_signal = signal
        self._state = StrategyState.SIGNAL_GENERATED
        
        return signal
    
    def _check_session(self) -> bool:
        """Verifica se está em sessão permitida"""
        hour = datetime.now().hour
        
        session_hours = {
            "asia": (0, 8),
            "london": (8, 12),
            "newyork": (13, 21),
            "late": (21, 24)
        }
        
        for session in self._config.allowed_sessions:
            if session in session_hours:
                start, end = session_hours[session]
                if start <= hour < end:
                    return True
        
        return False


class StrategyFactory:
    """Factory para criar estratégias"""
    
    _registry: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: type):
        """Registra uma estratégia"""
        cls._registry[name] = strategy_class
    
    @classmethod
    def create(
        cls,
        name: str,
        config: StrategyConfig,
        symbol: str
    ) -> Optional[BaseStrategy]:
        """
        Cria uma instância de estratégia
        
        Args:
            name: Nome da estratégia
            config: Configuração
            symbol: Símbolo
            
        Returns:
            Instância da estratégia ou None
        """
        strategy_class = cls._registry.get(name)
        if strategy_class:
            return strategy_class(config, symbol)
        return None
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """Lista estratégias registradas"""
        return list(cls._registry.keys())
