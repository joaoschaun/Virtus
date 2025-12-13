"""
BRAIN - Position Supervisor
Gerenciamento de posições abertas
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.types import Position, OrderType
from ..core.logger import get_logger
from ..mt5.mt5_manager import MT5Manager

logger = get_logger("positions")


class TrailingMethod(Enum):
    """Método de trailing stop"""
    FIXED = "fixed"          # Distância fixa
    ATR = "atr"              # Baseado em ATR
    PERCENT = "percent"      # Percentual
    BREAKEVEN = "breakeven"  # Move para breakeven apenas


@dataclass
class TrailingConfig:
    """Configuração de trailing stop"""
    method: TrailingMethod = TrailingMethod.ATR
    activation_profit: float = 1.0  # R:R mínimo para ativar
    trailing_distance: float = 1.5  # Em ATR ou % ou pips
    step_pips: float = 5.0  # Mínimo de movimento
    breakeven_offset: float = 5.0  # Pips acima do breakeven


@dataclass
class PositionStats:
    """Estatísticas de uma posição"""
    ticket: int
    symbol: str
    direction: str
    
    # Preços
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    
    # P&L
    profit_pips: float = 0.0
    profit_money: float = 0.0
    profit_percent: float = 0.0
    
    # Risco
    risk_reward: float = 0.0
    max_profit: float = 0.0
    max_drawdown: float = 0.0
    
    # Tempo
    duration: timedelta = field(default_factory=timedelta)
    opened_at: datetime = field(default_factory=datetime.now)


class PositionSupervisor:
    """
    Supervisor de Posições
    
    Responsabilidades:
    - Monitorar posições abertas
    - Gerenciar trailing stop
    - Mover para breakeven
    - Parcial close
    - Exit rules
    """
    
    def __init__(
        self,
        mt5_manager: MT5Manager,
        trailing_config: TrailingConfig = None
    ):
        self._mt5 = mt5_manager
        self._trailing_config = trailing_config or TrailingConfig()
        
        # Estado
        self._positions: Dict[int, PositionStats] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_position_closed: Optional[Callable] = None
        self._on_breakeven: Optional[Callable] = None
        self._on_trailing_update: Optional[Callable] = None
    
    async def start(self, interval: float = 1.0):
        """
        Inicia monitoramento
        
        Args:
            interval: Intervalo em segundos
        """
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop(interval))
        logger.info("PositionSupervisor iniciado")
    
    async def stop(self):
        """Para monitoramento"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PositionSupervisor parado")
    
    async def _monitoring_loop(self, interval: float):
        """Loop principal de monitoramento"""
        while self._running:
            try:
                await self._update_positions()
            except Exception as e:
                logger.error(f"Erro no monitoramento: {e}")
            
            await asyncio.sleep(interval)
    
    async def _update_positions(self):
        """Atualiza todas as posições"""
        positions = await self._mt5.get_positions()
        current_tickets = set()
        
        for pos in positions:
            current_tickets.add(pos.ticket)
            
            # Nova posição ou atualizar
            if pos.ticket not in self._positions:
                self._positions[pos.ticket] = self._create_stats(pos)
                logger.info(f"Nova posição detectada: {pos.ticket} {pos.symbol}")
            else:
                await self._update_position_stats(pos)
        
        # Detectar posições fechadas
        closed_tickets = set(self._positions.keys()) - current_tickets
        for ticket in closed_tickets:
            stats = self._positions.pop(ticket)
            logger.info(f"Posição fechada: {ticket}")
            if self._on_position_closed:
                await self._on_position_closed(stats)
    
    def _create_stats(self, pos: Position) -> PositionStats:
        """Cria stats para nova posição"""
        direction = "buy" if pos.type == OrderType.BUY else "sell"
        
        return PositionStats(
            ticket=pos.ticket,
            symbol=pos.symbol,
            direction=direction,
            entry_price=pos.price_open,
            current_price=pos.price_current,
            stop_loss=pos.stop_loss or 0,
            take_profit=pos.take_profit or 0,
            profit_money=pos.profit,
            opened_at=pos.time
        )
    
    async def _update_position_stats(self, pos: Position):
        """Atualiza stats de posição existente"""
        stats = self._positions[pos.ticket]
        
        stats.current_price = pos.price_current
        stats.profit_money = pos.profit
        
        # Calcular pips
        if "JPY" in pos.symbol:
            pip_size = 0.01
        elif "XAU" in pos.symbol:
            pip_size = 0.1
        else:
            pip_size = 0.0001
        
        if stats.direction == "buy":
            stats.profit_pips = (pos.price_current - stats.entry_price) / pip_size
        else:
            stats.profit_pips = (stats.entry_price - pos.price_current) / pip_size
        
        # Tracking máximos
        stats.max_profit = max(stats.max_profit, pos.profit)
        stats.max_drawdown = min(stats.max_drawdown, pos.profit)
        
        # Duração
        stats.duration = datetime.now() - stats.opened_at
        
        # Aplicar trailing stop se configurado
        await self._check_trailing(stats, pos)
    
    # ==========================================================================
    # TRAILING STOP
    # ==========================================================================
    
    async def _check_trailing(self, stats: PositionStats, pos: Position):
        """Verifica e aplica trailing stop"""
        if not pos.stop_loss:
            return
        
        # Calcular R:R atual
        if stats.direction == "buy":
            risk = stats.entry_price - pos.stop_loss
            reward = stats.current_price - stats.entry_price
        else:
            risk = pos.stop_loss - stats.entry_price
            reward = stats.entry_price - stats.current_price
        
        if risk <= 0:
            return
        
        rr = reward / risk
        stats.risk_reward = rr
        
        # Verificar ativação
        if rr < self._trailing_config.activation_profit:
            return
        
        # Calcular novo SL
        new_sl = await self._calculate_new_sl(stats, pos)
        
        if new_sl is None:
            return
        
        # Verificar se é melhor que atual
        if stats.direction == "buy":
            if new_sl <= pos.stop_loss:
                return
        else:
            if new_sl >= pos.stop_loss:
                return
        
        # Verificar step mínimo
        sl_diff = abs(new_sl - pos.stop_loss)
        pip_size = 0.01 if "JPY" in pos.symbol else 0.0001
        if "XAU" in pos.symbol:
            pip_size = 0.1
        
        if sl_diff < self._trailing_config.step_pips * pip_size:
            return
        
        # Modificar posição
        result = await self._mt5.modify_position(
            pos.ticket,
            sl=new_sl,
            tp=pos.take_profit
        )
        
        if result:
            logger.info(f"Trailing aplicado: {pos.ticket} SL {pos.stop_loss:.5f} -> {new_sl:.5f}")
            stats.stop_loss = new_sl
            
            if self._on_trailing_update:
                await self._on_trailing_update(stats)
    
    async def _calculate_new_sl(
        self,
        stats: PositionStats,
        pos: Position
    ) -> Optional[float]:
        """Calcula novo SL baseado no método"""
        method = self._trailing_config.method
        
        if method == TrailingMethod.BREAKEVEN:
            return await self._breakeven_sl(stats, pos)
        
        elif method == TrailingMethod.FIXED:
            return self._fixed_trailing_sl(stats, pos)
        
        elif method == TrailingMethod.ATR:
            return await self._atr_trailing_sl(stats, pos)
        
        elif method == TrailingMethod.PERCENT:
            return self._percent_trailing_sl(stats, pos)
        
        return None
    
    async def _breakeven_sl(
        self,
        stats: PositionStats,
        pos: Position
    ) -> Optional[float]:
        """Move para breakeven apenas"""
        pip_size = 0.01 if "JPY" in pos.symbol else 0.0001
        if "XAU" in pos.symbol:
            pip_size = 0.1
        
        offset = self._trailing_config.breakeven_offset * pip_size
        
        if stats.direction == "buy":
            new_sl = stats.entry_price + offset
            # Só move se ainda não está em breakeven
            if pos.stop_loss < stats.entry_price:
                return new_sl
        else:
            new_sl = stats.entry_price - offset
            if pos.stop_loss > stats.entry_price:
                return new_sl
        
        return None
    
    def _fixed_trailing_sl(
        self,
        stats: PositionStats,
        pos: Position
    ) -> float:
        """Trailing com distância fixa em pips"""
        pip_size = 0.01 if "JPY" in pos.symbol else 0.0001
        if "XAU" in pos.symbol:
            pip_size = 0.1
        
        distance = self._trailing_config.trailing_distance * pip_size
        
        if stats.direction == "buy":
            return stats.current_price - distance
        else:
            return stats.current_price + distance
    
    async def _atr_trailing_sl(
        self,
        stats: PositionStats,
        pos: Position
    ) -> float:
        """Trailing baseado em ATR"""
        # Obter ATR (simplificado - idealmente viria do data feed)
        rates = await self._mt5.get_rates(pos.symbol, "H1", 20)
        
        if not rates:
            return self._fixed_trailing_sl(stats, pos)
        
        # Calcular ATR
        tr_list = []
        for i in range(1, len(rates)):
            high = rates[i]["high"]
            low = rates[i]["low"]
            prev_close = rates[i-1]["close"]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_list.append(tr)
        
        atr = sum(tr_list) / len(tr_list) if tr_list else 0.001
        
        distance = atr * self._trailing_config.trailing_distance
        
        if stats.direction == "buy":
            return stats.current_price - distance
        else:
            return stats.current_price + distance
    
    def _percent_trailing_sl(
        self,
        stats: PositionStats,
        pos: Position
    ) -> float:
        """Trailing percentual"""
        distance = stats.current_price * (self._trailing_config.trailing_distance / 100)
        
        if stats.direction == "buy":
            return stats.current_price - distance
        else:
            return stats.current_price + distance
    
    # ==========================================================================
    # AÇÕES MANUAIS
    # ==========================================================================
    
    async def move_to_breakeven(self, ticket: int, offset_pips: float = 5.0):
        """
        Move posição para breakeven
        
        Args:
            ticket: Ticket da posição
            offset_pips: Pips acima do BE
        """
        if ticket not in self._positions:
            return False
        
        stats = self._positions[ticket]
        pos = await self._mt5.get_position(ticket)
        
        if not pos:
            return False
        
        pip_size = 0.01 if "JPY" in pos.symbol else 0.0001
        if "XAU" in pos.symbol:
            pip_size = 0.1
        
        offset = offset_pips * pip_size
        
        if stats.direction == "buy":
            new_sl = stats.entry_price + offset
        else:
            new_sl = stats.entry_price - offset
        
        result = await self._mt5.modify_position(ticket, sl=new_sl, tp=pos.take_profit)
        
        if result:
            stats.stop_loss = new_sl
            logger.info(f"Breakeven: {ticket} SL -> {new_sl:.5f}")
            
            if self._on_breakeven:
                await self._on_breakeven(stats)
        
        return result
    
    async def close_partial(
        self,
        ticket: int,
        percent: float = 50.0
    ) -> bool:
        """
        Fecha parcialmente uma posição
        
        Args:
            ticket: Ticket
            percent: Percentual a fechar
            
        Returns:
            Sucesso
        """
        pos = await self._mt5.get_position(ticket)
        if not pos:
            return False
        
        close_volume = pos.volume * (percent / 100)
        close_volume = round(close_volume, 2)
        close_volume = max(0.01, close_volume)
        
        result = await self._mt5.close_position(ticket, volume=close_volume)
        
        if result:
            logger.info(f"Fechamento parcial: {ticket} {close_volume} lots")
        
        return result
    
    async def close_all(self, symbol: str = None) -> int:
        """
        Fecha todas as posições
        
        Args:
            symbol: Filtrar por símbolo (None = todas)
            
        Returns:
            Número de posições fechadas
        """
        closed = 0
        positions = await self._mt5.get_positions()
        
        for pos in positions:
            if symbol and pos.symbol != symbol:
                continue
            
            if await self._mt5.close_position(pos.ticket):
                closed += 1
        
        logger.info(f"Fechadas {closed} posições")
        return closed
    
    # ==========================================================================
    # REPORTS
    # ==========================================================================
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """Retorna resumo das posições"""
        positions = []
        total_profit = 0.0
        
        for stats in self._positions.values():
            positions.append({
                "ticket": stats.ticket,
                "symbol": stats.symbol,
                "direction": stats.direction,
                "profit_pips": round(stats.profit_pips, 1),
                "profit": round(stats.profit_money, 2),
                "rr": round(stats.risk_reward, 2),
                "duration": str(stats.duration).split(".")[0]
            })
            total_profit += stats.profit_money
        
        return {
            "count": len(positions),
            "total_profit": round(total_profit, 2),
            "positions": positions
        }
    
    def set_callbacks(
        self,
        on_closed: Callable = None,
        on_breakeven: Callable = None,
        on_trailing: Callable = None
    ):
        """Define callbacks para eventos"""
        self._on_position_closed = on_closed
        self._on_breakeven = on_breakeven
        self._on_trailing_update = on_trailing
