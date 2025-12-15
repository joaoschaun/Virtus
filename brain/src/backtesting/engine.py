"""
VIRTUS Backtesting Engine
==========================

Motor de backtesting para simulação e validação de estratégias.

Features:
- Simulação realista de ordens
- Spread e slippage
- Comissões e swap
- Múltiplos timeframes
- Métricas detalhadas
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import numpy as np
import pandas as pd
from collections import defaultdict

try:
    from ..core import VirtusLogger
    logger = VirtusLogger.get_logger("backtest_engine")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("backtest_engine")


class OrderType(Enum):
    """Tipo de ordem."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Status da ordem."""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class BacktestConfig:
    """Configuração do backtest."""
    # Capital
    initial_balance: float = 10000.0
    currency: str = "USD"
    
    # Custos
    spread_pips: float = 2.0  # Spread fixo em pips
    commission_per_lot: float = 7.0  # Comissão por lote
    swap_long: float = -2.5  # Swap para posições long
    swap_short: float = 1.5  # Swap para posições short
    slippage_pips: float = 0.5  # Slippage máximo
    
    # Execução
    fill_ratio: float = 1.0  # Taxa de preenchimento (1.0 = 100%)
    partial_fills: bool = False
    
    # Risco
    max_positions: int = 10
    max_daily_loss: float = 0.05  # 5% do capital
    max_drawdown: float = 0.20  # 20% do capital
    
    # Dados
    use_tick_data: bool = False
    price_type: str = "close"  # open, high, low, close, typical, weighted
    
    # Simulação
    realistic_fills: bool = True
    market_hours_only: bool = True


@dataclass
class Order:
    """Ordem de trading."""
    id: int
    symbol: str
    order_type: OrderType
    volume: float
    
    # Preços
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    fill_price: Optional[float] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Metadados
    strategy: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class Position:
    """Posição aberta."""
    id: int
    symbol: str
    direction: OrderType
    volume: float
    entry_price: float
    entry_time: datetime
    
    # SL/TP
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Custos
    commission: float = 0.0
    swap: float = 0.0
    
    # Estado atual
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    
    # Métricas
    mae: float = 0.0  # Maximum Adverse Excursion
    mfe: float = 0.0  # Maximum Favorable Excursion
    
    # Metadados
    strategy: Optional[str] = None
    
    def update_price(self, bid: float, ask: float, point_value: float = 1.0):
        """Atualiza preço e P&L."""
        if self.direction == OrderType.BUY:
            self.current_price = bid
            pips = (bid - self.entry_price) / point_value
        else:
            self.current_price = ask
            pips = (self.entry_price - ask) / point_value
        
        self.unrealized_pnl = pips * self.volume * 10  # Simplificado
        
        # Atualiza MAE/MFE
        if self.unrealized_pnl < 0:
            self.mae = min(self.mae, self.unrealized_pnl)
        else:
            self.mfe = max(self.mfe, self.unrealized_pnl)


@dataclass
class Trade:
    """Trade fechado."""
    id: int
    symbol: str
    direction: OrderType
    volume: float
    
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    
    profit: float
    profit_pips: float
    commission: float
    swap: float
    
    mae: float = 0.0
    mfe: float = 0.0
    
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_reason: str = "signal"
    strategy: Optional[str] = None
    
    @property
    def net_profit(self) -> float:
        return self.profit - self.commission - abs(self.swap)
    
    @property
    def is_winner(self) -> bool:
        return self.net_profit > 0
    
    @property
    def duration_minutes(self) -> int:
        return int((self.exit_time - self.entry_time).total_seconds() / 60)
    
    @property
    def risk_reward(self) -> float:
        if self.stop_loss and self.entry_price:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.exit_price - self.entry_price)
            return reward / risk if risk > 0 else 0
        return 0


@dataclass
class BacktestState:
    """Estado do backtest."""
    timestamp: datetime
    balance: float
    equity: float
    margin: float
    free_margin: float
    
    open_positions: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    
    drawdown: float = 0.0
    peak_equity: float = 0.0


class BacktestEngine:
    """
    Motor principal de backtesting.
    
    Simula execução de estratégias em dados históricos
    com custos realistas e métricas detalhadas.
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        
        # Logger - usa o global definido no topo do arquivo
        try:
            self.logger = VirtusLogger.get_logger("backtest_engine")
        except:
            self.logger = logger
        
        # Estado
        self._balance = self.config.initial_balance
        self._equity = self.config.initial_balance
        self._peak_equity = self.config.initial_balance
        
        # Tracking
        self._positions: Dict[int, Position] = {}
        self._trades: List[Trade] = []
        self._orders: List[Order] = []
        self._equity_curve: List[Tuple[datetime, float]] = []
        self._state_history: List[BacktestState] = []
        
        # Contadores
        self._order_id = 0
        self._position_id = 0
        self._trade_id = 0
        
        # Dados
        self._data: Optional[pd.DataFrame] = None
        self._current_bar: int = 0
        self._current_time: Optional[datetime] = None
        
        # Controle
        self._daily_pnl = 0.0
        self._last_day: Optional[datetime] = None
        
        # Callbacks
        self._on_bar_callbacks: List[Callable] = []
        self._on_trade_callbacks: List[Callable] = []
    
    # ============================================================
    # PROPRIEDADES
    # ============================================================
    
    @property
    def balance(self) -> float:
        return self._balance
    
    @property
    def equity(self) -> float:
        return self._equity
    
    @property
    def positions(self) -> Dict[int, Position]:
        return self._positions
    
    @property
    def trades(self) -> List[Trade]:
        return self._trades
    
    @property
    def current_time(self) -> Optional[datetime]:
        return self._current_time
    
    @property
    def drawdown(self) -> float:
        if self._peak_equity == 0:
            return 0
        return (self._peak_equity - self._equity) / self._peak_equity
    
    # ============================================================
    # DADOS
    # ============================================================
    
    def load_data(self, data: pd.DataFrame) -> None:
        """
        Carrega dados históricos.
        
        DataFrame deve ter colunas: open, high, low, close, volume
        e index datetime.
        """
        required_cols = ['open', 'high', 'low', 'close']
        missing = [c for c in required_cols if c not in data.columns]
        if missing:
            raise ValueError(f"Colunas faltando: {missing}")
        
        self._data = data.copy()
        
        # Garante index datetime
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'time' in data.columns:
                self._data.set_index('time', inplace=True)
            elif 'datetime' in data.columns:
                self._data.set_index('datetime', inplace=True)
        
        self._data = self._data.sort_index()
        self.logger.info(f"Data loaded: {len(self._data)} bars")
    
    def get_price(self, price_type: str = None) -> float:
        """Retorna preço atual baseado no tipo."""
        if self._data is None or self._current_bar >= len(self._data):
            return 0.0
        
        bar = self._data.iloc[self._current_bar]
        ptype = price_type or self.config.price_type
        
        if ptype == 'open':
            return bar['open']
        elif ptype == 'high':
            return bar['high']
        elif ptype == 'low':
            return bar['low']
        elif ptype == 'close':
            return bar['close']
        elif ptype == 'typical':
            return (bar['high'] + bar['low'] + bar['close']) / 3
        elif ptype == 'weighted':
            return (bar['high'] + bar['low'] + 2 * bar['close']) / 4
        
        return bar['close']
    
    def get_bar(self, offset: int = 0) -> Optional[pd.Series]:
        """Retorna barra com offset do índice atual."""
        idx = self._current_bar - offset
        if 0 <= idx < len(self._data):
            return self._data.iloc[idx]
        return None
    
    def get_bars(self, count: int) -> pd.DataFrame:
        """Retorna últimas N barras."""
        end = self._current_bar + 1
        start = max(0, end - count)
        return self._data.iloc[start:end].copy()
    
    # ============================================================
    # ORDENS
    # ============================================================
    
    def buy(
        self,
        symbol: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Optional[int]:
        """Abre posição de compra."""
        return self._open_position(
            symbol=symbol,
            direction=OrderType.BUY,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=strategy,
            comment=comment,
        )
    
    def sell(
        self,
        symbol: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Optional[int]:
        """Abre posição de venda."""
        return self._open_position(
            symbol=symbol,
            direction=OrderType.SELL,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=strategy,
            comment=comment,
        )
    
    def close_position(
        self,
        position_id: int,
        reason: str = "signal",
    ) -> Optional[Trade]:
        """Fecha uma posição."""
        if position_id not in self._positions:
            return None
        
        position = self._positions[position_id]
        return self._close_position(position, reason)
    
    def close_all(self, symbol: Optional[str] = None) -> List[Trade]:
        """Fecha todas as posições (ou de um símbolo)."""
        closed = []
        positions = list(self._positions.values())
        
        for position in positions:
            if symbol is None or position.symbol == symbol:
                trade = self._close_position(position, "close_all")
                if trade:
                    closed.append(trade)
        
        return closed
    
    def modify_position(
        self,
        position_id: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> bool:
        """Modifica SL/TP de uma posição."""
        if position_id not in self._positions:
            return False
        
        position = self._positions[position_id]
        
        if stop_loss is not None:
            position.stop_loss = stop_loss
        if take_profit is not None:
            position.take_profit = take_profit
        
        return True
    
    # ============================================================
    # EXECUÇÃO INTERNA
    # ============================================================
    
    def _open_position(
        self,
        symbol: str,
        direction: OrderType,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Optional[int]:
        """Abre posição internamente."""
        # Verifica limites
        if len(self._positions) >= self.config.max_positions:
            self.logger.warning("Max positions reached")
            return None
        
        # Verifica daily loss
        if self._daily_pnl < -self.config.max_daily_loss * self.config.initial_balance:
            self.logger.warning("Daily loss limit reached")
            return None
        
        # Calcula preço com spread e slippage
        price = self.get_price()
        spread = self.config.spread_pips * 0.0001  # Para forex
        slippage = self.config.slippage_pips * 0.0001
        
        if direction == OrderType.BUY:
            fill_price = price + spread / 2 + slippage
        else:
            fill_price = price - spread / 2 - slippage
        
        # Calcula comissão
        commission = self.config.commission_per_lot * volume
        
        # Cria posição
        self._position_id += 1
        position = Position(
            id=self._position_id,
            symbol=symbol,
            direction=direction,
            volume=volume,
            entry_price=fill_price,
            entry_time=self._current_time,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission=commission,
            strategy=strategy,
        )
        
        self._positions[position.id] = position
        self._balance -= commission
        
        self.logger.debug(
            f"Position opened: {direction.value} {volume} {symbol} @ {fill_price:.5f}"
        )
        
        return position.id
    
    def _close_position(
        self,
        position: Position,
        reason: str = "signal",
    ) -> Optional[Trade]:
        """Fecha posição internamente."""
        if position.id not in self._positions:
            return None
        
        # Calcula preço de saída
        price = self.get_price()
        spread = self.config.spread_pips * 0.0001
        slippage = self.config.slippage_pips * 0.0001
        
        if position.direction == OrderType.BUY:
            exit_price = price - spread / 2 - slippage
        else:
            exit_price = price + spread / 2 + slippage
        
        # Calcula P&L
        if position.direction == OrderType.BUY:
            profit_pips = (exit_price - position.entry_price) / 0.0001
        else:
            profit_pips = (position.entry_price - exit_price) / 0.0001
        
        profit = profit_pips * position.volume * 10  # Simplificado para forex
        
        # Cria trade
        self._trade_id += 1
        trade = Trade(
            id=self._trade_id,
            symbol=position.symbol,
            direction=position.direction,
            volume=position.volume,
            entry_price=position.entry_price,
            exit_price=exit_price,
            entry_time=position.entry_time,
            exit_time=self._current_time,
            profit=profit,
            profit_pips=profit_pips,
            commission=position.commission,
            swap=position.swap,
            mae=position.mae,
            mfe=position.mfe,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            exit_reason=reason,
            strategy=position.strategy,
        )
        
        # Atualiza estado
        self._trades.append(trade)
        self._balance += profit
        self._daily_pnl += trade.net_profit
        
        del self._positions[position.id]
        
        # Callbacks
        for callback in self._on_trade_callbacks:
            callback(trade)
        
        self.logger.debug(
            f"Position closed: {trade.direction.value} {trade.symbol} | "
            f"P&L: ${trade.net_profit:.2f} | Reason: {reason}"
        )
        
        return trade
    
    def _check_stops(self) -> None:
        """Verifica SL/TP das posições."""
        if self._data is None:
            return
        
        bar = self._data.iloc[self._current_bar]
        high = bar['high']
        low = bar['low']
        
        positions = list(self._positions.values())
        
        for position in positions:
            # Verifica Stop Loss
            if position.stop_loss:
                if position.direction == OrderType.BUY and low <= position.stop_loss:
                    self._close_position(position, "stop_loss")
                    continue
                elif position.direction == OrderType.SELL and high >= position.stop_loss:
                    self._close_position(position, "stop_loss")
                    continue
            
            # Verifica Take Profit
            if position.take_profit:
                if position.direction == OrderType.BUY and high >= position.take_profit:
                    self._close_position(position, "take_profit")
                    continue
                elif position.direction == OrderType.SELL and low <= position.take_profit:
                    self._close_position(position, "take_profit")
                    continue
    
    def _update_positions(self) -> None:
        """Atualiza preços e P&L das posições."""
        price = self.get_price()
        spread = self.config.spread_pips * 0.0001
        
        bid = price - spread / 2
        ask = price + spread / 2
        
        unrealized = 0.0
        for position in self._positions.values():
            position.update_price(bid, ask)
            unrealized += position.unrealized_pnl
        
        self._equity = self._balance + unrealized
        self._peak_equity = max(self._peak_equity, self._equity)
    
    def _update_daily_tracking(self) -> None:
        """Atualiza tracking diário."""
        if self._current_time is None:
            return
        
        current_day = self._current_time.date()
        
        if self._last_day is None:
            self._last_day = current_day
        elif current_day != self._last_day:
            self._daily_pnl = 0.0
            self._last_day = current_day
    
    def _record_state(self) -> None:
        """Registra estado atual."""
        if self._current_time is None:
            return
        
        winners = sum(1 for t in self._trades if t.is_winner)
        
        state = BacktestState(
            timestamp=self._current_time,
            balance=self._balance,
            equity=self._equity,
            margin=0.0,  # Simplificado
            free_margin=self._equity,
            open_positions=len(self._positions),
            total_trades=len(self._trades),
            winning_trades=winners,
            drawdown=self.drawdown,
            peak_equity=self._peak_equity,
        )
        
        self._state_history.append(state)
        self._equity_curve.append((self._current_time, self._equity))
    
    # ============================================================
    # EXECUÇÃO DO BACKTEST
    # ============================================================
    
    def run(
        self,
        strategy_func: Callable[['BacktestEngine', pd.Series], None],
        warmup_bars: int = 50,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> 'BacktestResult':
        """
        Executa o backtest.
        
        Args:
            strategy_func: Função (engine, bar) -> None que implementa a estratégia
            warmup_bars: Barras iniciais para warm-up (sem trading)
            progress_callback: Callback para progresso (current, total)
        
        Returns:
            BacktestResult com métricas e trades
        """
        if self._data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        self.logger.info(f"Starting backtest: {len(self._data)} bars, warmup={warmup_bars}")
        
        total_bars = len(self._data)
        
        for i in range(total_bars):
            self._current_bar = i
            self._current_time = self._data.index[i]
            
            # Atualiza tracking diário
            self._update_daily_tracking()
            
            # Verifica stops
            self._check_stops()
            
            # Atualiza posições
            self._update_positions()
            
            # Executa estratégia (após warmup)
            if i >= warmup_bars:
                bar = self._data.iloc[i]
                try:
                    strategy_func(self, bar)
                except Exception as e:
                    self.logger.error(f"Strategy error at bar {i}: {e}")
            
            # Callbacks de barra
            for callback in self._on_bar_callbacks:
                callback(self, self._data.iloc[i])
            
            # Registra estado
            self._record_state()
            
            # Progress callback
            if progress_callback and i % 100 == 0:
                progress_callback(i, total_bars)
            
            # Verifica max drawdown
            if self.drawdown >= self.config.max_drawdown:
                self.logger.warning(f"Max drawdown reached: {self.drawdown:.2%}")
                break
        
        # Fecha posições abertas
        self.close_all()
        
        self.logger.info(
            f"Backtest completed: {len(self._trades)} trades, "
            f"Final balance: ${self._balance:,.2f}"
        )
        
        return self._generate_result()
    
    def _generate_result(self) -> 'BacktestResult':
        """Gera resultado do backtest."""
        return BacktestResult(
            trades=self._trades.copy(),
            equity_curve=self._equity_curve.copy(),
            state_history=self._state_history.copy(),
            config=self.config,
            initial_balance=self.config.initial_balance,
            final_balance=self._balance,
        )
    
    # ============================================================
    # CALLBACKS
    # ============================================================
    
    def on_bar(self, callback: Callable) -> None:
        """Registra callback para cada barra."""
        self._on_bar_callbacks.append(callback)
    
    def on_trade(self, callback: Callable) -> None:
        """Registra callback para cada trade."""
        self._on_trade_callbacks.append(callback)
    
    # ============================================================
    # RESET
    # ============================================================
    
    def reset(self) -> None:
        """Reseta o engine para novo backtest."""
        self._balance = self.config.initial_balance
        self._equity = self.config.initial_balance
        self._peak_equity = self.config.initial_balance
        
        self._positions.clear()
        self._trades.clear()
        self._orders.clear()
        self._equity_curve.clear()
        self._state_history.clear()
        
        self._order_id = 0
        self._position_id = 0
        self._trade_id = 0
        
        self._current_bar = 0
        self._current_time = None
        
        self._daily_pnl = 0.0
        self._last_day = None


@dataclass
class BacktestResult:
    """Resultado do backtest."""
    trades: List[Trade]
    equity_curve: List[Tuple[datetime, float]]
    state_history: List[BacktestState]
    config: BacktestConfig
    initial_balance: float
    final_balance: float
    
    def __post_init__(self):
        self._metrics: Optional[Dict[str, Any]] = None
    
    @property
    def metrics(self) -> Dict[str, Any]:
        """Calcula métricas de performance."""
        if self._metrics is not None:
            return self._metrics
        
        from .metrics import calculate_metrics
        self._metrics = calculate_metrics(self)
        return self._metrics
    
    @property
    def total_return(self) -> float:
        """Retorno total."""
        return (self.final_balance - self.initial_balance) / self.initial_balance
    
    @property
    def total_trades(self) -> int:
        return len(self.trades)
    
    @property
    def winning_trades(self) -> int:
        return sum(1 for t in self.trades if t.is_winner)
    
    @property
    def losing_trades(self) -> int:
        return sum(1 for t in self.trades if not t.is_winner)
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0
        return self.winning_trades / self.total_trades
    
    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.net_profit for t in self.trades if t.net_profit > 0)
        gross_loss = abs(sum(t.net_profit for t in self.trades if t.net_profit < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    @property
    def max_drawdown(self) -> float:
        if not self.state_history:
            return 0
        return max(s.drawdown for s in self.state_history)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate * 100, 2),
            'profit_factor': round(self.profit_factor, 2),
            'total_return': round(self.total_return * 100, 2),
            'initial_balance': round(self.initial_balance, 2),
            'final_balance': round(self.final_balance, 2),
            'max_drawdown': round(self.max_drawdown * 100, 2),
            **self.metrics,
        }
    
    def summary(self) -> str:
        """Retorna resumo formatado."""
        m = self.metrics
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                          ║
╠══════════════════════════════════════════════════════════════╣
║  📊 PERFORMANCE                                              ║
║  ────────────────────────────────────────────────────────── ║
║  Total Return:     {self.total_return:>10.2%}                            ║
║  Final Balance:    ${self.final_balance:>10,.2f}                        ║
║  Max Drawdown:     {self.max_drawdown:>10.2%}                            ║
║                                                              ║
║  📈 TRADES                                                   ║
║  ────────────────────────────────────────────────────────── ║
║  Total Trades:     {self.total_trades:>10}                               ║
║  Win Rate:         {self.win_rate:>10.1%}                            ║
║  Profit Factor:    {self.profit_factor:>10.2f}                            ║
║                                                              ║
║  📉 RISK METRICS                                             ║
║  ────────────────────────────────────────────────────────── ║
║  Sharpe Ratio:     {m.get('sharpe_ratio', 0):>10.2f}                            ║
║  Sortino Ratio:    {m.get('sortino_ratio', 0):>10.2f}                            ║
║  Calmar Ratio:     {m.get('calmar_ratio', 0):>10.2f}                            ║
╚══════════════════════════════════════════════════════════════╝
"""
