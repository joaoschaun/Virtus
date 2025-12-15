"""
VIRTUS Bot State Management
============================

Gerenciamento de estado do bot de trading.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import asyncio


class BotState(Enum):
    """Estados possíveis do bot."""
    INITIALIZING = auto()
    CONNECTING = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()
    ERROR = auto()
    MAINTENANCE = auto()


class TradingPhase(Enum):
    """Fases de trading do bot."""
    WAITING = auto()          # Aguardando condições
    ANALYZING = auto()        # Analisando mercado
    SIGNAL_DETECTED = auto()  # Sinal detectado
    CONFIRMING = auto()       # Confirmando entrada
    ENTERING = auto()         # Executando entrada
    MANAGING = auto()         # Gerenciando posição
    EXITING = auto()          # Executando saída


@dataclass
class BotStatistics:
    """Estatísticas do bot."""
    start_time: datetime = field(default_factory=datetime.now)
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    signals_generated: int = 0
    signals_executed: int = 0
    signals_filtered: int = 0
    last_trade_time: Optional[datetime] = None
    best_trade: float = 0.0
    worst_trade: float = 0.0
    
    @property
    def win_rate(self) -> float:
        """Taxa de acerto."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def profit_factor(self) -> float:
        """Fator de lucro."""
        if self.total_loss == 0:
            return float('inf') if self.total_profit > 0 else 0.0
        return abs(self.total_profit / self.total_loss)
    
    @property
    def average_win(self) -> float:
        """Lucro médio por trade vencedor."""
        if self.winning_trades == 0:
            return 0.0
        return self.total_profit / self.winning_trades
    
    @property
    def average_loss(self) -> float:
        """Perda média por trade perdedor."""
        if self.losing_trades == 0:
            return 0.0
        return abs(self.total_loss) / self.losing_trades
    
    @property
    def expectancy(self) -> float:
        """Expectativa matemática."""
        if self.total_trades == 0:
            return 0.0
        win_rate = self.winning_trades / self.total_trades
        loss_rate = self.losing_trades / self.total_trades
        return (win_rate * self.average_win) - (loss_rate * self.average_loss)
    
    @property
    def net_profit(self) -> float:
        """Lucro líquido."""
        return self.total_profit + self.total_loss
    
    @property
    def uptime_hours(self) -> float:
        """Tempo de execução em horas."""
        return (datetime.now() - self.start_time).total_seconds() / 3600
    
    def record_trade(self, profit: float) -> None:
        """Registra resultado de um trade."""
        self.total_trades += 1
        self.last_trade_time = datetime.now()
        
        if profit > 0:
            self.winning_trades += 1
            self.total_profit += profit
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            
            if profit > self.best_trade:
                self.best_trade = profit
            if self.consecutive_wins > self.max_consecutive_wins:
                self.max_consecutive_wins = self.consecutive_wins
        else:
            self.losing_trades += 1
            self.total_loss += profit  # profit é negativo
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            
            if profit < self.worst_trade:
                self.worst_trade = profit
            if self.consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.consecutive_losses
        
        # Atualiza drawdown
        self._update_drawdown()
    
    def _update_drawdown(self) -> None:
        """Atualiza cálculo de drawdown."""
        # Simplificado - em produção usar equity curve
        if self.net_profit < 0:
            self.current_drawdown = abs(self.net_profit)
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown
        else:
            self.current_drawdown = 0.0
    
    def record_signal(self, executed: bool = False, filtered: bool = False) -> None:
        """Registra sinal gerado."""
        self.signals_generated += 1
        if executed:
            self.signals_executed += 1
        if filtered:
            self.signals_filtered += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte estatísticas para dicionário."""
        return {
            'start_time': self.start_time.isoformat(),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 2),
            'total_profit': round(self.total_profit, 2),
            'total_loss': round(self.total_loss, 2),
            'net_profit': round(self.net_profit, 2),
            'profit_factor': round(self.profit_factor, 2) if self.profit_factor != float('inf') else 'inf',
            'expectancy': round(self.expectancy, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'current_drawdown': round(self.current_drawdown, 2),
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_wins': self.max_consecutive_wins,
            'max_consecutive_losses': self.max_consecutive_losses,
            'signals_generated': self.signals_generated,
            'signals_executed': self.signals_executed,
            'signals_filtered': self.signals_filtered,
            'best_trade': round(self.best_trade, 2),
            'worst_trade': round(self.worst_trade, 2),
            'uptime_hours': round(self.uptime_hours, 2),
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
        }
    
    def reset(self) -> None:
        """Reseta estatísticas."""
        self.__init__()


@dataclass
class BotContext:
    """Contexto atual do bot."""
    state: BotState = BotState.INITIALIZING
    trading_phase: TradingPhase = TradingPhase.WAITING
    symbol: str = ""
    current_price: float = 0.0
    spread: float = 0.0
    volatility: float = 0.0
    trend_direction: str = "neutral"
    market_session: str = ""
    has_position: bool = False
    position_profit: float = 0.0
    last_signal_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte contexto para dicionário."""
        return {
            'state': self.state.name,
            'trading_phase': self.trading_phase.name,
            'symbol': self.symbol,
            'current_price': self.current_price,
            'spread': self.spread,
            'volatility': self.volatility,
            'trend_direction': self.trend_direction,
            'market_session': self.market_session,
            'has_position': self.has_position,
            'position_profit': self.position_profit,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'last_error': self.last_error,
            'error_count': self.error_count,
        }


class BotStateManager:
    """Gerenciador de estado do bot."""
    
    def __init__(self, bot_id: str, symbol: str):
        self.bot_id = bot_id
        self.symbol = symbol
        self.context = BotContext(symbol=symbol)
        self.statistics = BotStatistics()
        self._state_history: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._callbacks: Dict[str, List[callable]] = {
            'state_change': [],
            'phase_change': [],
            'error': [],
            'trade': [],
        }
    
    async def set_state(self, state: BotState, reason: str = "") -> None:
        """Define novo estado do bot."""
        async with self._lock:
            old_state = self.context.state
            self.context.state = state
            
            # Registra histórico
            self._state_history.append({
                'timestamp': datetime.now().isoformat(),
                'from_state': old_state.name,
                'to_state': state.name,
                'reason': reason,
            })
            
            # Mantém histórico limitado
            if len(self._state_history) > 100:
                self._state_history = self._state_history[-100:]
            
            # Notifica callbacks
            for callback in self._callbacks['state_change']:
                try:
                    await callback(old_state, state, reason)
                except Exception:
                    pass
    
    async def set_phase(self, phase: TradingPhase) -> None:
        """Define nova fase de trading."""
        async with self._lock:
            old_phase = self.context.trading_phase
            self.context.trading_phase = phase
            
            # Notifica callbacks
            for callback in self._callbacks['phase_change']:
                try:
                    await callback(old_phase, phase)
                except Exception:
                    pass
    
    async def record_error(self, error: str) -> None:
        """Registra erro."""
        async with self._lock:
            self.context.last_error = error
            self.context.last_error_time = datetime.now()
            self.context.error_count += 1
            
            # Notifica callbacks
            for callback in self._callbacks['error']:
                try:
                    await callback(error)
                except Exception:
                    pass
    
    async def clear_error(self) -> None:
        """Limpa estado de erro."""
        async with self._lock:
            self.context.last_error = None
    
    async def record_trade(self, profit: float) -> None:
        """Registra trade."""
        async with self._lock:
            self.statistics.record_trade(profit)
            
            # Notifica callbacks
            for callback in self._callbacks['trade']:
                try:
                    await callback(profit, self.statistics)
                except Exception:
                    pass
    
    async def update_context(
        self,
        price: Optional[float] = None,
        spread: Optional[float] = None,
        volatility: Optional[float] = None,
        trend: Optional[str] = None,
        session: Optional[str] = None,
        has_position: Optional[bool] = None,
        position_profit: Optional[float] = None,
    ) -> None:
        """Atualiza contexto de mercado."""
        async with self._lock:
            if price is not None:
                self.context.current_price = price
            if spread is not None:
                self.context.spread = spread
            if volatility is not None:
                self.context.volatility = volatility
            if trend is not None:
                self.context.trend_direction = trend
            if session is not None:
                self.context.market_session = session
            if has_position is not None:
                self.context.has_position = has_position
            if position_profit is not None:
                self.context.position_profit = position_profit
    
    def on_state_change(self, callback: callable) -> None:
        """Registra callback para mudança de estado."""
        self._callbacks['state_change'].append(callback)
    
    def on_phase_change(self, callback: callable) -> None:
        """Registra callback para mudança de fase."""
        self._callbacks['phase_change'].append(callback)
    
    def on_error(self, callback: callable) -> None:
        """Registra callback para erro."""
        self._callbacks['error'].append(callback)
    
    def on_trade(self, callback: callable) -> None:
        """Registra callback para trade."""
        self._callbacks['trade'].append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do bot."""
        return {
            'bot_id': self.bot_id,
            'symbol': self.symbol,
            'context': self.context.to_dict(),
            'statistics': self.statistics.to_dict(),
            'state_history': self._state_history[-10:],  # Últimos 10 estados
        }
    
    def is_running(self) -> bool:
        """Verifica se bot está rodando."""
        return self.context.state == BotState.RUNNING
    
    def is_ready(self) -> bool:
        """Verifica se bot está pronto."""
        return self.context.state in [BotState.READY, BotState.RUNNING]
    
    def can_trade(self) -> bool:
        """Verifica se bot pode operar."""
        return (
            self.context.state == BotState.RUNNING and
            self.context.trading_phase in [TradingPhase.WAITING, TradingPhase.ANALYZING]
        )
    
    def has_error(self) -> bool:
        """Verifica se bot está em erro."""
        return self.context.state == BotState.ERROR
    
    async def save_state(self, filepath: str) -> None:
        """Salva estado em arquivo."""
        async with self._lock:
            state_data = {
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'saved_at': datetime.now().isoformat(),
                'statistics': self.statistics.to_dict(),
                'context': self.context.to_dict(),
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
    
    async def load_state(self, filepath: str) -> bool:
        """Carrega estado de arquivo."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # Restaura estatísticas (parcial)
            stats = state_data.get('statistics', {})
            self.statistics.total_trades = stats.get('total_trades', 0)
            self.statistics.winning_trades = stats.get('winning_trades', 0)
            self.statistics.losing_trades = stats.get('losing_trades', 0)
            self.statistics.total_profit = stats.get('total_profit', 0.0)
            self.statistics.total_loss = stats.get('total_loss', 0.0)
            self.statistics.max_drawdown = stats.get('max_drawdown', 0.0)
            self.statistics.max_consecutive_wins = stats.get('max_consecutive_wins', 0)
            self.statistics.max_consecutive_losses = stats.get('max_consecutive_losses', 0)
            
            return True
        except Exception:
            return False
