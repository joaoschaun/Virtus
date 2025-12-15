"""
VIRTUS Position Manager
========================

Gerenciador completo de posições por bot.
Cada bot tem seu próprio PositionManager para isolamento.

Features:
- Gestão de múltiplas posições por símbolo
- Sincronização com MT5
- Tracking de P&L em tempo real
- Histórico de posições
- Integração com ExitManager
- Eventos e callbacks
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import json
from pathlib import Path

from ..core import VirtusLogger, Position, PositionStatus, OrderType
from ..core.exceptions import PositionError
from .position_state import PositionState, StateType
from .exits import ExitManager, ExitSignal, ExitReason


class PositionEvent(Enum):
    """Eventos de posição."""
    OPENED = "opened"
    CLOSED = "closed"
    MODIFIED = "modified"
    SL_HIT = "sl_hit"
    TP_HIT = "tp_hit"
    TRAILING_UPDATED = "trailing_updated"
    BREAKEVEN_SET = "breakeven_set"
    PARTIAL_CLOSED = "partial_closed"
    ERROR = "error"


@dataclass
class PositionMetrics:
    """Métricas de uma posição."""
    ticket: int
    symbol: str
    
    # Preços
    entry_price: float = 0.0
    current_price: float = 0.0
    
    # P&L
    current_pnl: float = 0.0
    current_pnl_pips: float = 0.0
    max_profit: float = 0.0
    max_profit_pips: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pips: float = 0.0
    
    # R-Multiple
    initial_risk: float = 0.0
    r_multiple: float = 0.0
    
    # Tempo
    duration_seconds: int = 0
    duration_bars: int = 0
    
    # Saídas parciais
    partial_closes: int = 0
    volume_remaining: float = 0.0
    total_realized_pnl: float = 0.0
    
    # Trailing
    trailing_active: bool = False
    trailing_distance: float = 0.0
    
    # Breakeven
    breakeven_active: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'ticket': self.ticket,
            'symbol': self.symbol,
            'entry_price': round(self.entry_price, 5),
            'current_price': round(self.current_price, 5),
            'current_pnl': round(self.current_pnl, 2),
            'current_pnl_pips': round(self.current_pnl_pips, 1),
            'max_profit': round(self.max_profit, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'r_multiple': round(self.r_multiple, 2),
            'duration_seconds': self.duration_seconds,
            'partial_closes': self.partial_closes,
            'trailing_active': self.trailing_active,
            'breakeven_active': self.breakeven_active,
        }


@dataclass
class PositionRecord:
    """Registro completo de uma posição (aberta ou fechada)."""
    ticket: int
    symbol: str
    order_type: OrderType
    volume: float
    
    # Preços de entrada
    entry_price: float
    entry_time: datetime
    
    # SL/TP
    initial_sl: float
    initial_tp: float
    current_sl: float
    current_tp: float
    
    # Saída (quando fechada)
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    
    # P&L
    pnl: float = 0.0
    pnl_pips: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    
    # Métricas
    max_profit: float = 0.0
    max_drawdown: float = 0.0
    r_multiple: float = 0.0
    
    # Metadados
    strategy: Optional[str] = None
    signal_confidence: float = 0.0
    
    # Histórico de modificações
    modifications: List[Dict] = field(default_factory=list)
    partial_closes: List[Dict] = field(default_factory=list)
    
    @property
    def is_closed(self) -> bool:
        return self.exit_time is not None
    
    @property
    def duration(self) -> timedelta:
        end = self.exit_time or datetime.now()
        return end - self.entry_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'ticket': self.ticket,
            'symbol': self.symbol,
            'type': self.order_type.value,
            'volume': self.volume,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_reason': self.exit_reason.value if self.exit_reason else None,
            'pnl': round(self.pnl, 2),
            'pnl_pips': round(self.pnl_pips, 1),
            'r_multiple': round(self.r_multiple, 2),
            'duration_seconds': int(self.duration.total_seconds()),
            'strategy': self.strategy,
        }


class PositionManager:
    """
    Gerenciador de posições para um bot específico.
    
    Cada bot/símbolo tem sua própria instância de PositionManager
    para garantir isolamento e tracking independente.
    
    Responsabilidades:
    - Adicionar/remover posições
    - Tracking de P&L em tempo real
    - Sincronização com MT5
    - Gestão de trailing stop e breakeven
    - Histórico de trades
    - Eventos e callbacks
    """
    
    def __init__(
        self,
        bot_id: str,
        symbol: str,
        mt5_orders: Any = None,  # MT5OrderManager
        config: Optional[Dict] = None,
        data_dir: Optional[Path] = None
    ):
        self.bot_id = bot_id
        self.symbol = symbol
        self.mt5_orders = mt5_orders
        self.config = config or {}
        
        self.logger = VirtusLogger.get_logger(f"positions.{symbol.lower()}")
        
        # Diretório de dados
        self.data_dir = data_dir or Path(f"data/bots/{symbol.lower()}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Posições ativas (ticket -> PositionRecord)
        self._positions: Dict[int, PositionRecord] = {}
        
        # Estados das posições (ticket -> PositionState)
        self._states: Dict[int, PositionState] = {}
        
        # Métricas em tempo real (ticket -> PositionMetrics)
        self._metrics: Dict[int, PositionMetrics] = {}
        
        # Histórico de posições fechadas
        self._history: List[PositionRecord] = []
        
        # Exit manager
        self._exit_manager: Optional[ExitManager] = None
        
        # Callbacks de eventos
        self._event_callbacks: Dict[PositionEvent, List[Callable]] = defaultdict(list)
        
        # Configurações de limites
        self._max_positions = self.config.get('max_positions', 2)
        self._max_volume = self.config.get('max_volume', 1.0)
        
        # Lock para operações thread-safe
        self._lock = asyncio.Lock()
        
        # Pip value para o símbolo
        self._pip_value = self._get_pip_value()
    
    def _get_pip_value(self) -> float:
        """Retorna o valor do pip para o símbolo."""
        pip_values = {
            'XAUUSD': 0.01,
            'EURUSD': 0.0001,
            'GBPUSD': 0.0001,
            'USDJPY': 0.01,
        }
        return pip_values.get(self.symbol, 0.0001)
    
    # ========================================================================
    # GESTÃO DE POSIÇÕES
    # ========================================================================
    
    async def add_position(
        self,
        ticket: int,
        order_type: OrderType,
        volume: float,
        entry_price: float,
        sl: float,
        tp: float,
        strategy: Optional[str] = None,
        signal_confidence: float = 0.0
    ) -> PositionRecord:
        """
        Adiciona uma nova posição ao gerenciador.
        
        Args:
            ticket: Ticket da ordem no MT5
            order_type: Tipo da ordem (BUY/SELL)
            volume: Volume da posição
            entry_price: Preço de entrada
            sl: Stop Loss
            tp: Take Profit
            strategy: Nome da estratégia
            signal_confidence: Confiança do sinal
            
        Returns:
            PositionRecord criado
        """
        async with self._lock:
            if ticket in self._positions:
                raise PositionError(f"Posição {ticket} já existe")
            
            if len(self._positions) >= self._max_positions:
                raise PositionError(f"Limite de posições atingido ({self._max_positions})")
            
            # Cria registro da posição
            position = PositionRecord(
                ticket=ticket,
                symbol=self.symbol,
                order_type=order_type,
                volume=volume,
                entry_price=entry_price,
                entry_time=datetime.now(),
                initial_sl=sl,
                initial_tp=tp,
                current_sl=sl,
                current_tp=tp,
                strategy=strategy,
                signal_confidence=signal_confidence
            )
            
            # Calcula risco inicial
            risk_pips = abs(entry_price - sl) / self._pip_value
            
            # Cria estado
            state = PositionState(
                ticket=ticket,
                symbol=self.symbol,
                state=StateType.HEALTHY
            )
            
            # Cria métricas
            metrics = PositionMetrics(
                ticket=ticket,
                symbol=self.symbol,
                entry_price=entry_price,
                current_price=entry_price,
                initial_risk=risk_pips * volume * 10,  # Aproximação
                volume_remaining=volume
            )
            
            # Armazena
            self._positions[ticket] = position
            self._states[ticket] = state
            self._metrics[ticket] = metrics
            
            self.logger.info(
                f"📈 Posição adicionada: #{ticket} {order_type.value} "
                f"{volume} @ {entry_price:.5f} | SL: {sl:.5f} | TP: {tp:.5f}"
            )
            
            # Dispara evento
            await self._emit_event(PositionEvent.OPENED, position)
            
            # Salva estado
            await self._save_state()
            
            return position
    
    async def remove_position(
        self,
        ticket: int,
        exit_price: float,
        exit_reason: ExitReason = ExitReason.MANUAL,
        pnl: Optional[float] = None
    ) -> PositionRecord:
        """
        Remove uma posição (fecha).
        
        Args:
            ticket: Ticket da posição
            exit_price: Preço de saída
            exit_reason: Motivo da saída
            pnl: P&L da posição (se não fornecido, será calculado)
            
        Returns:
            PositionRecord fechado
        """
        async with self._lock:
            if ticket not in self._positions:
                raise PositionError(f"Posição {ticket} não encontrada")
            
            position = self._positions[ticket]
            metrics = self._metrics[ticket]
            
            # Marca como fechada
            position.exit_price = exit_price
            position.exit_time = datetime.now()
            position.exit_reason = exit_reason
            
            # Calcula P&L se não fornecido
            if pnl is not None:
                position.pnl = pnl
            else:
                position.pnl = self._calculate_pnl(
                    position.order_type,
                    position.entry_price,
                    exit_price,
                    position.volume
                )
            
            # Calcula P&L em pips
            position.pnl_pips = self._calculate_pnl_pips(
                position.order_type,
                position.entry_price,
                exit_price
            )
            
            # Copia métricas finais
            position.max_profit = metrics.max_profit
            position.max_drawdown = metrics.max_drawdown
            position.r_multiple = metrics.r_multiple
            
            # Move para histórico
            self._history.append(position)
            
            # Remove dos dicionários ativos
            del self._positions[ticket]
            del self._states[ticket]
            del self._metrics[ticket]
            
            self.logger.info(
                f"📉 Posição fechada: #{ticket} | "
                f"P&L: {position.pnl:+.2f} ({position.pnl_pips:+.1f} pips) | "
                f"Motivo: {exit_reason.value}"
            )
            
            # Dispara evento baseado no motivo
            if exit_reason == ExitReason.STOP_LOSS:
                await self._emit_event(PositionEvent.SL_HIT, position)
            elif exit_reason == ExitReason.TAKE_PROFIT:
                await self._emit_event(PositionEvent.TP_HIT, position)
            else:
                await self._emit_event(PositionEvent.CLOSED, position)
            
            # Salva estado
            await self._save_state()
            
            return position
    
    async def update_position(
        self,
        ticket: int,
        current_price: float,
        current_sl: Optional[float] = None,
        current_tp: Optional[float] = None
    ) -> PositionMetrics:
        """
        Atualiza dados de uma posição.
        
        Args:
            ticket: Ticket da posição
            current_price: Preço atual
            current_sl: Novo SL (se modificado)
            current_tp: Novo TP (se modificado)
            
        Returns:
            PositionMetrics atualizado
        """
        async with self._lock:
            if ticket not in self._positions:
                raise PositionError(f"Posição {ticket} não encontrada")
            
            position = self._positions[ticket]
            state = self._states[ticket]
            metrics = self._metrics[ticket]
            
            # Atualiza SL/TP se fornecidos
            if current_sl is not None and current_sl != position.current_sl:
                old_sl = position.current_sl
                position.current_sl = current_sl
                position.modifications.append({
                    'time': datetime.now().isoformat(),
                    'type': 'sl_change',
                    'old': old_sl,
                    'new': current_sl
                })
                await self._emit_event(PositionEvent.MODIFIED, position)
            
            if current_tp is not None and current_tp != position.current_tp:
                old_tp = position.current_tp
                position.current_tp = current_tp
                position.modifications.append({
                    'time': datetime.now().isoformat(),
                    'type': 'tp_change',
                    'old': old_tp,
                    'new': current_tp
                })
            
            # Calcula P&L atual
            current_pnl = self._calculate_pnl(
                position.order_type,
                position.entry_price,
                current_price,
                position.volume
            )
            current_pnl_pips = self._calculate_pnl_pips(
                position.order_type,
                position.entry_price,
                current_price
            )
            
            # Atualiza métricas
            metrics.current_price = current_price
            metrics.current_pnl = current_pnl
            metrics.current_pnl_pips = current_pnl_pips
            
            # Atualiza máximos/mínimos
            if current_pnl > metrics.max_profit:
                metrics.max_profit = current_pnl
                metrics.max_profit_pips = current_pnl_pips
            
            if current_pnl < metrics.max_drawdown:
                metrics.max_drawdown = current_pnl
                metrics.max_drawdown_pips = current_pnl_pips
            
            # Calcula R-Multiple
            if metrics.initial_risk > 0:
                metrics.r_multiple = current_pnl / metrics.initial_risk
            
            # Atualiza duração
            metrics.duration_seconds = int((datetime.now() - position.entry_time).total_seconds())
            
            # Atualiza estado
            state.update(current_pnl)
            
            return metrics
    
    async def partial_close(
        self,
        ticket: int,
        close_percent: float,
        exit_price: float
    ) -> Dict[str, Any]:
        """
        Fecha parcialmente uma posição.
        
        Args:
            ticket: Ticket da posição
            close_percent: Percentual a fechar (0-100)
            exit_price: Preço de saída
            
        Returns:
            Dicionário com resultado da operação
        """
        async with self._lock:
            if ticket not in self._positions:
                raise PositionError(f"Posição {ticket} não encontrada")
            
            position = self._positions[ticket]
            metrics = self._metrics[ticket]
            
            # Calcula volume a fechar
            close_volume = position.volume * (close_percent / 100)
            remaining_volume = position.volume - close_volume
            
            if remaining_volume < 0.01:  # Volume mínimo
                raise PositionError("Volume restante muito pequeno")
            
            # Calcula P&L parcial
            partial_pnl = self._calculate_pnl(
                position.order_type,
                position.entry_price,
                exit_price,
                close_volume
            )
            
            # Registra fechamento parcial
            position.partial_closes.append({
                'time': datetime.now().isoformat(),
                'volume_closed': close_volume,
                'volume_remaining': remaining_volume,
                'exit_price': exit_price,
                'pnl': partial_pnl
            })
            
            # Atualiza volume
            position.volume = remaining_volume
            metrics.volume_remaining = remaining_volume
            metrics.partial_closes += 1
            metrics.total_realized_pnl += partial_pnl
            
            self.logger.info(
                f"🔀 Fechamento parcial #{ticket}: {close_percent}% @ {exit_price:.5f} | "
                f"P&L: {partial_pnl:+.2f} | Volume restante: {remaining_volume:.2f}"
            )
            
            await self._emit_event(PositionEvent.PARTIAL_CLOSED, position)
            
            return {
                'volume_closed': close_volume,
                'volume_remaining': remaining_volume,
                'partial_pnl': partial_pnl,
                'total_realized_pnl': metrics.total_realized_pnl
            }
    
    # ========================================================================
    # TRAILING STOP E BREAKEVEN
    # ========================================================================
    
    async def update_trailing_stop(
        self,
        ticket: int,
        new_sl: float,
        distance_pips: float
    ) -> bool:
        """
        Atualiza trailing stop de uma posição.
        
        Args:
            ticket: Ticket da posição
            new_sl: Novo valor do SL
            distance_pips: Distância do trailing em pips
            
        Returns:
            True se atualizado com sucesso
        """
        async with self._lock:
            if ticket not in self._positions:
                return False
            
            position = self._positions[ticket]
            metrics = self._metrics[ticket]
            
            # Verifica se o novo SL é melhor
            is_buy = position.order_type == OrderType.BUY
            
            if is_buy and new_sl <= position.current_sl:
                return False
            if not is_buy and new_sl >= position.current_sl:
                return False
            
            old_sl = position.current_sl
            position.current_sl = new_sl
            
            # Atualiza métricas
            metrics.trailing_active = True
            metrics.trailing_distance = distance_pips
            
            # Registra modificação
            position.modifications.append({
                'time': datetime.now().isoformat(),
                'type': 'trailing_stop',
                'old': old_sl,
                'new': new_sl
            })
            
            self.logger.info(
                f"📊 Trailing Stop #{ticket}: {old_sl:.5f} → {new_sl:.5f} "
                f"(distância: {distance_pips:.1f} pips)"
            )
            
            await self._emit_event(PositionEvent.TRAILING_UPDATED, position)
            
            # Atualiza no MT5
            if self.mt5_orders:
                await self._update_sl_mt5(ticket, new_sl)
            
            return True
    
    async def set_breakeven(
        self,
        ticket: int,
        lock_pips: float = 1.0
    ) -> bool:
        """
        Move SL para breakeven + lock_pips.
        
        Args:
            ticket: Ticket da posição
            lock_pips: Pips de lucro a garantir
            
        Returns:
            True se movido com sucesso
        """
        async with self._lock:
            if ticket not in self._positions:
                return False
            
            position = self._positions[ticket]
            metrics = self._metrics[ticket]
            
            is_buy = position.order_type == OrderType.BUY
            
            # Calcula novo SL no breakeven + lock
            if is_buy:
                new_sl = position.entry_price + (lock_pips * self._pip_value)
                if new_sl <= position.current_sl:
                    return False  # Já está em breakeven ou melhor
            else:
                new_sl = position.entry_price - (lock_pips * self._pip_value)
                if new_sl >= position.current_sl:
                    return False
            
            old_sl = position.current_sl
            position.current_sl = new_sl
            
            # Atualiza métricas
            metrics.breakeven_active = True
            
            # Registra modificação
            position.modifications.append({
                'time': datetime.now().isoformat(),
                'type': 'breakeven',
                'old': old_sl,
                'new': new_sl,
                'lock_pips': lock_pips
            })
            
            self.logger.info(
                f"🔒 Breakeven #{ticket}: SL movido para {new_sl:.5f} "
                f"(lock: {lock_pips} pips)"
            )
            
            await self._emit_event(PositionEvent.BREAKEVEN_SET, position)
            
            # Atualiza no MT5
            if self.mt5_orders:
                await self._update_sl_mt5(ticket, new_sl)
            
            return True
    
    # ========================================================================
    # SINCRONIZAÇÃO MT5
    # ========================================================================
    
    async def sync_with_mt5(self) -> Dict[str, int]:
        """
        Sincroniza posições com MT5.
        
        Returns:
            Dicionário com contagem de operações
        """
        if not self.mt5_orders:
            return {'synced': 0, 'added': 0, 'removed': 0}
        
        stats = {'synced': 0, 'added': 0, 'removed': 0}
        
        try:
            # Obtém posições do MT5
            mt5_positions = self.mt5_orders.get_positions(self.symbol)
            mt5_tickets = {p.ticket for p in mt5_positions}
            local_tickets = set(self._positions.keys())
            
            # Posições novas no MT5 (não temos localmente)
            new_tickets = mt5_tickets - local_tickets
            for pos in mt5_positions:
                if pos.ticket in new_tickets:
                    order_type = OrderType.BUY if pos.type == 0 else OrderType.SELL
                    await self.add_position(
                        ticket=pos.ticket,
                        order_type=order_type,
                        volume=pos.volume,
                        entry_price=pos.price_open,
                        sl=pos.sl,
                        tp=pos.tp,
                        strategy='synced'
                    )
                    stats['added'] += 1
            
            # Posições fechadas no MT5 (ainda temos localmente)
            closed_tickets = local_tickets - mt5_tickets
            for ticket in closed_tickets:
                # Busca preço de fechamento no histórico MT5
                exit_price = self._positions[ticket].entry_price  # Fallback
                history = self.mt5_orders.get_history_deals(ticket)
                if history:
                    exit_price = history[-1].price
                
                await self.remove_position(
                    ticket=ticket,
                    exit_price=exit_price,
                    exit_reason=ExitReason.MANUAL
                )
                stats['removed'] += 1
            
            # Atualiza posições existentes
            for pos in mt5_positions:
                if pos.ticket in self._positions:
                    await self.update_position(
                        ticket=pos.ticket,
                        current_price=pos.price_current,
                        current_sl=pos.sl,
                        current_tp=pos.tp
                    )
                    stats['synced'] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Erro na sincronização MT5: {e}")
            return stats
    
    async def _update_sl_mt5(self, ticket: int, new_sl: float) -> bool:
        """Atualiza SL no MT5."""
        if not self.mt5_orders:
            return False
        
        try:
            return self.mt5_orders.modify_position(ticket, sl=new_sl)
        except Exception as e:
            self.logger.error(f"Erro ao atualizar SL no MT5: {e}")
            return False
    
    # ========================================================================
    # CÁLCULOS
    # ========================================================================
    
    def _calculate_pnl(
        self,
        order_type: OrderType,
        entry_price: float,
        exit_price: float,
        volume: float
    ) -> float:
        """Calcula P&L em dinheiro."""
        if order_type == OrderType.BUY:
            pips = (exit_price - entry_price) / self._pip_value
        else:
            pips = (entry_price - exit_price) / self._pip_value
        
        # Aproximação: 10 USD por pip por lote padrão
        pip_value_usd = 10.0
        if self.symbol == 'XAUUSD':
            pip_value_usd = 1.0
        elif 'JPY' in self.symbol:
            pip_value_usd = 9.0
        
        return pips * volume * pip_value_usd
    
    def _calculate_pnl_pips(
        self,
        order_type: OrderType,
        entry_price: float,
        exit_price: float
    ) -> float:
        """Calcula P&L em pips."""
        if order_type == OrderType.BUY:
            return (exit_price - entry_price) / self._pip_value
        else:
            return (entry_price - exit_price) / self._pip_value
    
    # ========================================================================
    # CONSULTAS
    # ========================================================================
    
    def get_position(self, ticket: int) -> Optional[PositionRecord]:
        """Obtém posição por ticket."""
        return self._positions.get(ticket)
    
    def get_metrics(self, ticket: int) -> Optional[PositionMetrics]:
        """Obtém métricas de uma posição."""
        return self._metrics.get(ticket)
    
    def get_state(self, ticket: int) -> Optional[PositionState]:
        """Obtém estado de uma posição."""
        return self._states.get(ticket)
    
    def get_all_positions(self) -> List[PositionRecord]:
        """Retorna todas as posições ativas."""
        return list(self._positions.values())
    
    def get_all_metrics(self) -> List[PositionMetrics]:
        """Retorna métricas de todas as posições."""
        return list(self._metrics.values())
    
    def count_positions(self) -> int:
        """Conta posições ativas."""
        return len(self._positions)
    
    def get_total_pnl(self) -> float:
        """Retorna P&L total de posições ativas."""
        return sum(m.current_pnl for m in self._metrics.values())
    
    def get_total_volume(self) -> float:
        """Retorna volume total de posições ativas."""
        return sum(p.volume for p in self._positions.values())
    
    def has_position(self, ticket: int) -> bool:
        """Verifica se existe posição."""
        return ticket in self._positions
    
    def can_open_position(self) -> bool:
        """Verifica se pode abrir nova posição."""
        return len(self._positions) < self._max_positions
    
    # ========================================================================
    # HISTÓRICO
    # ========================================================================
    
    def get_history(
        self,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PositionRecord]:
        """
        Obtém histórico de posições fechadas.
        
        Args:
            limit: Máximo de registros
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Lista de PositionRecord fechados
        """
        history = self._history
        
        if start_date:
            history = [p for p in history if p.exit_time >= start_date]
        if end_date:
            history = [p for p in history if p.exit_time <= end_date]
        
        # Ordena por data de saída (mais recente primeiro)
        history = sorted(history, key=lambda p: p.exit_time, reverse=True)
        
        return history[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do histórico."""
        if not self._history:
            return {}
        
        trades = self._history
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in trades)
        total_pips = sum(t.pnl_pips for t in trades)
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': len(winning) / len(trades) * 100 if trades else 0,
            'total_pnl': round(total_pnl, 2),
            'total_pips': round(total_pips, 1),
            'average_pnl': round(total_pnl / len(trades), 2) if trades else 0,
            'average_pips': round(total_pips / len(trades), 1) if trades else 0,
            'best_trade': round(max(t.pnl for t in trades), 2) if trades else 0,
            'worst_trade': round(min(t.pnl for t in trades), 2) if trades else 0,
            'average_duration': sum(t.duration.total_seconds() for t in trades) / len(trades) / 60 if trades else 0,
        }
    
    # ========================================================================
    # EVENTOS E CALLBACKS
    # ========================================================================
    
    def on_event(self, event: PositionEvent, callback: Callable) -> None:
        """Registra callback para evento."""
        self._event_callbacks[event].append(callback)
    
    async def _emit_event(self, event: PositionEvent, position: PositionRecord) -> None:
        """Emite evento para callbacks."""
        for callback in self._event_callbacks[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, position)
                else:
                    callback(event, position)
            except Exception as e:
                self.logger.error(f"Erro no callback de {event.value}: {e}")
    
    # ========================================================================
    # PERSISTÊNCIA
    # ========================================================================
    
    async def _save_state(self) -> None:
        """Salva estado em disco."""
        try:
            state_file = self.data_dir / "positions.json"
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'positions': [p.to_dict() for p in self._positions.values()],
                'history': [p.to_dict() for p in self._history[-100:]],  # Últimos 100
            }
            
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar estado: {e}")
    
    async def load_state(self) -> bool:
        """Carrega estado de disco."""
        try:
            state_file = self.data_dir / "positions.json"
            
            if not state_file.exists():
                return False
            
            with open(state_file, 'r') as f:
                data = json.load(f)
            
            # Carrega histórico
            for record in data.get('history', []):
                position = PositionRecord(
                    ticket=record['ticket'],
                    symbol=record['symbol'],
                    order_type=OrderType(record['type']),
                    volume=record.get('volume', 0),
                    entry_price=record.get('entry_price', 0),
                    entry_time=datetime.fromisoformat(record['entry_time']),
                    initial_sl=record.get('initial_sl', 0),
                    initial_tp=record.get('initial_tp', 0),
                    current_sl=record.get('current_sl', 0),
                    current_tp=record.get('current_tp', 0),
                    exit_price=record.get('exit_price'),
                    exit_time=datetime.fromisoformat(record['exit_time']) if record.get('exit_time') else None,
                    pnl=record.get('pnl', 0),
                    pnl_pips=record.get('pnl_pips', 0),
                    strategy=record.get('strategy')
                )
                self._history.append(position)
            
            self.logger.info(f"Estado carregado: {len(self._history)} trades no histórico")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar estado: {e}")
            return False
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    async def close(self) -> None:
        """Fecha o gerenciador."""
        await self._save_state()
        self.logger.info(f"PositionManager {self.symbol} fechado")


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_position_manager(
    bot_id: str,
    symbol: str,
    mt5_orders: Any = None,
    config: Optional[Dict] = None
) -> PositionManager:
    """
    Factory para criar PositionManager.
    
    Args:
        bot_id: ID do bot
        symbol: Símbolo do ativo
        mt5_orders: MT5OrderManager (opcional)
        config: Configuração adicional
        
    Returns:
        PositionManager configurado
    """
    return PositionManager(
        bot_id=bot_id,
        symbol=symbol,
        mt5_orders=mt5_orders,
        config=config
    )
