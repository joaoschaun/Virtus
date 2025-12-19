"""
VIRTUS - Paper Trading (Simulação)
===================================

Modo de simulação para testar estratégias sem dinheiro real.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import uuid

logger = logging.getLogger("virtus.paper_trading")


class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"


class PositionState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"


@dataclass
class PaperPosition:
    """Posição simulada."""
    ticket: int
    symbol: str
    type: OrderType
    volume: float
    open_price: float
    open_time: datetime
    sl: Optional[float] = None
    tp: Optional[float] = None
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    profit: float = 0.0
    state: PositionState = PositionState.OPEN
    comment: str = ""
    magic: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket": self.ticket,
            "symbol": self.symbol,
            "type": self.type.value,
            "volume": self.volume,
            "open_price": self.open_price,
            "open_time": self.open_time.isoformat(),
            "sl": self.sl,
            "tp": self.tp,
            "close_price": self.close_price,
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "profit": round(self.profit, 2),
            "state": self.state.value,
            "comment": self.comment,
        }


@dataclass
class PaperAccount:
    """Conta simulada."""
    login: int = 99999999
    server: str = "Paper-Trading"
    balance: float = 10000.0
    equity: float = 10000.0
    margin: float = 0.0
    free_margin: float = 10000.0
    profit: float = 0.0
    leverage: int = 100
    currency: str = "USD"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "login": self.login,
            "server": self.server,
            "balance": round(self.balance, 2),
            "equity": round(self.equity, 2),
            "margin": round(self.margin, 2),
            "free_margin": round(self.free_margin, 2),
            "profit": round(self.profit, 2),
            "leverage": self.leverage,
            "currency": self.currency,
        }


@dataclass
class PaperConfig:
    """Configuração do paper trading."""
    # Conta inicial
    initial_balance: float = 10000.0
    leverage: int = 100
    currency: str = "USD"
    
    # Custos
    spread_pips: Dict[str, float] = field(default_factory=lambda: {
        "XAUUSD": 0.30,
        "EURUSD": 0.8,
        "GBPUSD": 1.2,
        "USDJPY": 0.9,
    })
    commission_per_lot: float = 0.0
    swap_long: float = -0.5
    swap_short: float = -0.5
    
    # Simulação de slippage
    slippage_enabled: bool = True
    max_slippage_pips: float = 1.0
    
    # Simulação de requotes
    requote_probability: float = 0.05
    
    # Execução
    execution_delay_ms: int = 100


@dataclass
class SymbolInfo:
    """Informações do símbolo."""
    name: str
    digits: int
    point: float
    pip_value: float  # Valor do pip para 1 lote
    lot_size: int
    min_volume: float
    max_volume: float
    volume_step: float


# Informações padrão dos símbolos
DEFAULT_SYMBOLS = {
    "XAUUSD": SymbolInfo(
        name="XAUUSD",
        digits=2,
        point=0.01,
        pip_value=1.0,
        lot_size=100,
        min_volume=0.01,
        max_volume=100.0,
        volume_step=0.01,
    ),
    "EURUSD": SymbolInfo(
        name="EURUSD",
        digits=5,
        point=0.00001,
        pip_value=10.0,
        lot_size=100000,
        min_volume=0.01,
        max_volume=100.0,
        volume_step=0.01,
    ),
    "GBPUSD": SymbolInfo(
        name="GBPUSD",
        digits=5,
        point=0.00001,
        pip_value=10.0,
        lot_size=100000,
        min_volume=0.01,
        max_volume=100.0,
        volume_step=0.01,
    ),
}


class PaperTradingEngine:
    """
    Engine de Paper Trading.
    
    Simula execução de trades sem usar dinheiro real.
    Conecta com MT5 apenas para obter preços em tempo real.
    
    Uso:
        engine = PaperTradingEngine()
        await engine.start()
        
        # Abre posição
        ticket = await engine.open_position(
            symbol="XAUUSD",
            order_type=OrderType.BUY,
            volume=0.01,
            sl=2040.0,
            tp=2060.0
        )
        
        # Fecha posição
        await engine.close_position(ticket)
    """
    
    def __init__(self, config: Optional[PaperConfig] = None):
        self.config = config or PaperConfig()
        
        # Estado
        self.account = PaperAccount(
            balance=self.config.initial_balance,
            equity=self.config.initial_balance,
            free_margin=self.config.initial_balance,
            leverage=self.config.leverage,
            currency=self.config.currency,
        )
        
        self.positions: Dict[int, PaperPosition] = {}
        self.history: List[PaperPosition] = []
        self.symbols = DEFAULT_SYMBOLS.copy()
        
        # Preços atuais (simulados ou do MT5)
        self._prices: Dict[str, Dict[str, float]] = {}
        
        # Control
        self._running = False
        self._update_task: Optional[asyncio.Task] = None
        self._ticket_counter = 100000000
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Inicia o engine de paper trading."""
        if self._running:
            return
        
        self._running = True
        
        # Inicializa preços
        await self._init_prices()
        
        # Inicia loop de atualização
        self._update_task = asyncio.create_task(self._update_loop())
        
        logger.info("📄 Paper Trading Engine iniciado")
        logger.info(f"   Balance: ${self.account.balance:,.2f}")
        logger.info(f"   Leverage: 1:{self.account.leverage}")
    
    async def stop(self):
        """Para o engine."""
        self._running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        logger.info("📄 Paper Trading Engine parado")
    
    async def _init_prices(self):
        """Inicializa preços dos símbolos."""
        # Tenta obter preços reais do MT5
        try:
            import MetaTrader5 as mt5
            
            for symbol in self.symbols:
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    self._prices[symbol] = {
                        "bid": tick.bid,
                        "ask": tick.ask,
                        "last": tick.last,
                        "time": datetime.now(),
                    }
        except Exception as e:
            logger.warning(f"Não foi possível obter preços do MT5: {e}")
        
        # Preços padrão se não conseguiu do MT5
        if not self._prices:
            self._prices = {
                "XAUUSD": {"bid": 2050.00, "ask": 2050.30, "last": 2050.15},
                "EURUSD": {"bid": 1.0850, "ask": 1.0851, "last": 1.08505},
                "GBPUSD": {"bid": 1.2650, "ask": 1.2652, "last": 1.2651},
            }
    
    async def _update_loop(self):
        """Loop de atualização de preços e posições."""
        while self._running:
            try:
                # Atualiza preços
                await self._update_prices()
                
                # Atualiza posições
                await self._update_positions()
                
                # Atualiza conta
                self._update_account()
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no update loop: {e}")
    
    async def _update_prices(self):
        """Atualiza preços dos símbolos."""
        try:
            import MetaTrader5 as mt5
            
            for symbol in self.symbols:
                tick = mt5.symbol_info_tick(symbol)
                if tick:
                    self._prices[symbol] = {
                        "bid": tick.bid,
                        "ask": tick.ask,
                        "last": tick.last,
                        "time": datetime.now(),
                    }
        except Exception:
            # Simula variação de preço se MT5 não disponível
            for symbol, prices in self._prices.items():
                variation = random.uniform(-0.0005, 0.0005)
                prices["bid"] *= (1 + variation)
                prices["ask"] = prices["bid"] + self.config.spread_pips.get(symbol, 1) * self.symbols[symbol].point
                prices["last"] = (prices["bid"] + prices["ask"]) / 2
    
    async def _update_positions(self):
        """Atualiza P/L das posições abertas."""
        async with self._lock:
            for position in list(self.positions.values()):
                if position.state != PositionState.OPEN:
                    continue
                
                prices = self._prices.get(position.symbol, {})
                if not prices:
                    continue
                
                # Calcula P/L
                symbol_info = self.symbols.get(position.symbol)
                if not symbol_info:
                    continue
                
                if position.type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]:
                    current_price = prices["bid"]
                    pips = (current_price - position.open_price) / symbol_info.point
                else:
                    current_price = prices["ask"]
                    pips = (position.open_price - current_price) / symbol_info.point
                
                position.profit = pips * symbol_info.pip_value * position.volume
                
                # Verifica SL/TP
                await self._check_sl_tp(position, current_price)
    
    async def _check_sl_tp(self, position: PaperPosition, current_price: float):
        """Verifica se SL ou TP foi atingido."""
        is_buy = position.type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]
        
        # Stop Loss
        if position.sl:
            if (is_buy and current_price <= position.sl) or \
               (not is_buy and current_price >= position.sl):
                await self._close_position_internal(position, current_price, "SL hit")
                return
        
        # Take Profit
        if position.tp:
            if (is_buy and current_price >= position.tp) or \
               (not is_buy and current_price <= position.tp):
                await self._close_position_internal(position, current_price, "TP hit")
                return
    
    def _update_account(self):
        """Atualiza métricas da conta."""
        total_profit = sum(p.profit for p in self.positions.values())
        total_margin = sum(
            (p.volume * self.symbols.get(p.symbol, DEFAULT_SYMBOLS["EURUSD"]).lot_size * 
             self._prices.get(p.symbol, {}).get("bid", 0)) / self.account.leverage
            for p in self.positions.values()
        )
        
        self.account.profit = total_profit
        self.account.equity = self.account.balance + total_profit
        self.account.margin = total_margin
        self.account.free_margin = self.account.equity - total_margin
    
    def _next_ticket(self) -> int:
        """Gera próximo ticket."""
        self._ticket_counter += 1
        return self._ticket_counter
    
    async def open_position(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "",
        magic: int = 0,
    ) -> Optional[int]:
        """
        Abre uma posição simulada.
        
        Returns:
            Ticket da posição ou None se falhou
        """
        async with self._lock:
            # Valida símbolo
            if symbol not in self.symbols:
                logger.error(f"Símbolo desconhecido: {symbol}")
                return None
            
            symbol_info = self.symbols[symbol]
            
            # Valida volume
            if volume < symbol_info.min_volume or volume > symbol_info.max_volume:
                logger.error(f"Volume inválido: {volume}")
                return None
            
            # Obtém preço
            prices = self._prices.get(symbol, {})
            if not prices:
                logger.error(f"Sem preço para {symbol}")
                return None
            
            # Determina preço de abertura
            if order_type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]:
                open_price = price or prices["ask"]
            else:
                open_price = price or prices["bid"]
            
            # Simula slippage
            if self.config.slippage_enabled:
                slippage = random.uniform(0, self.config.max_slippage_pips) * symbol_info.point
                if order_type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]:
                    open_price += slippage
                else:
                    open_price -= slippage
            
            # Simula requote
            if random.random() < self.config.requote_probability:
                logger.warning(f"Requote simulado para {symbol}")
                return None
            
            # Verifica margem
            required_margin = (volume * symbol_info.lot_size * open_price) / self.account.leverage
            if required_margin > self.account.free_margin:
                logger.error(f"Margem insuficiente: {required_margin} > {self.account.free_margin}")
                return None
            
            # Simula delay de execução
            await asyncio.sleep(self.config.execution_delay_ms / 1000)
            
            # Cria posição
            ticket = self._next_ticket()
            position = PaperPosition(
                ticket=ticket,
                symbol=symbol,
                type=order_type,
                volume=volume,
                open_price=round(open_price, symbol_info.digits),
                open_time=datetime.now(),
                sl=sl,
                tp=tp,
                comment=comment,
                magic=magic,
            )
            
            self.positions[ticket] = position
            
            logger.info(
                f"📄 Paper Trade OPEN: #{ticket} {order_type.value} {volume} {symbol} @ {open_price}"
            )
            
            return ticket
    
    async def close_position(
        self,
        ticket: int,
        price: Optional[float] = None,
    ) -> bool:
        """
        Fecha uma posição simulada.
        
        Returns:
            True se fechou, False se falhou
        """
        async with self._lock:
            position = self.positions.get(ticket)
            if not position:
                logger.error(f"Posição não encontrada: {ticket}")
                return False
            
            if position.state != PositionState.OPEN:
                logger.error(f"Posição já fechada: {ticket}")
                return False
            
            # Obtém preço de fechamento
            prices = self._prices.get(position.symbol, {})
            if position.type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]:
                close_price = price or prices.get("bid", position.open_price)
            else:
                close_price = price or prices.get("ask", position.open_price)
            
            return await self._close_position_internal(position, close_price, "Manual close")
    
    async def _close_position_internal(
        self,
        position: PaperPosition,
        close_price: float,
        reason: str = ""
    ) -> bool:
        """Fecha posição internamente."""
        symbol_info = self.symbols.get(position.symbol)
        
        # Calcula P/L final
        if position.type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]:
            pips = (close_price - position.open_price) / symbol_info.point
        else:
            pips = (position.open_price - close_price) / symbol_info.point
        
        position.profit = pips * symbol_info.pip_value * position.volume
        position.close_price = round(close_price, symbol_info.digits)
        position.close_time = datetime.now()
        position.state = PositionState.CLOSED
        position.comment = f"{position.comment} | {reason}".strip(" |")
        
        # Atualiza balance
        self.account.balance += position.profit
        
        # Move para histórico
        self.history.append(position)
        del self.positions[position.ticket]
        
        logger.info(
            f"📄 Paper Trade CLOSE: #{position.ticket} {position.symbol} "
            f"P/L: ${position.profit:,.2f} ({reason})"
        )
        
        return True
    
    async def modify_position(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> bool:
        """Modifica SL/TP de uma posição."""
        async with self._lock:
            position = self.positions.get(ticket)
            if not position:
                return False
            
            if sl is not None:
                position.sl = sl
            if tp is not None:
                position.tp = tp
            
            logger.info(f"📄 Paper Trade MODIFY: #{ticket} SL={sl} TP={tp}")
            return True
    
    def get_positions(self) -> List[Dict]:
        """Retorna posições abertas."""
        return [p.to_dict() for p in self.positions.values()]
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Retorna histórico de trades."""
        return [p.to_dict() for p in self.history[-limit:]]
    
    def get_account(self) -> Dict:
        """Retorna informações da conta."""
        return self.account.to_dict()
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """Retorna preço atual do símbolo."""
        return self._prices.get(symbol)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de trading."""
        if not self.history:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "total_profit": 0,
            }
        
        wins = [t for t in self.history if t.profit > 0]
        losses = [t for t in self.history if t.profit < 0]
        
        total_profit = sum(t.profit for t in wins)
        total_loss = abs(sum(t.profit for t in losses))
        
        return {
            "total_trades": len(self.history),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": (len(wins) / len(self.history) * 100) if self.history else 0,
            "profit_factor": (total_profit / total_loss) if total_loss > 0 else 0,
            "total_profit": sum(t.profit for t in self.history),
            "avg_profit": sum(t.profit for t in self.history) / len(self.history),
            "max_profit": max(t.profit for t in self.history) if self.history else 0,
            "max_loss": min(t.profit for t in self.history) if self.history else 0,
            "open_positions": len(self.positions),
        }


# Instância global
paper_trading = PaperTradingEngine()


# ============================================================================
# FASTAPI ROUTES
# ============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/paper", tags=["Paper Trading"])


class OpenPositionRequest(BaseModel):
    symbol: str
    type: str  # buy, sell
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: str = ""


@router.get("/account")
async def get_paper_account():
    """Retorna informações da conta paper."""
    return paper_trading.get_account()


@router.get("/positions")
async def get_paper_positions():
    """Retorna posições abertas."""
    return paper_trading.get_positions()


@router.get("/history")
async def get_paper_history(limit: int = 100):
    """Retorna histórico de trades."""
    return paper_trading.get_history(limit)


@router.get("/stats")
async def get_paper_stats():
    """Retorna estatísticas de trading."""
    return paper_trading.get_stats()


@router.post("/trade")
async def open_paper_trade(request: OpenPositionRequest):
    """Abre um trade paper."""
    order_type = OrderType.BUY if request.type.lower() == "buy" else OrderType.SELL
    
    ticket = await paper_trading.open_position(
        symbol=request.symbol,
        order_type=order_type,
        volume=request.volume,
        sl=request.sl,
        tp=request.tp,
        comment=request.comment,
    )
    
    if ticket is None:
        raise HTTPException(400, "Falha ao abrir posição")
    
    return {"ticket": ticket, "message": "Posição aberta com sucesso"}


@router.delete("/trade/{ticket}")
async def close_paper_trade(ticket: int):
    """Fecha um trade paper."""
    success = await paper_trading.close_position(ticket)
    
    if not success:
        raise HTTPException(400, "Falha ao fechar posição")
    
    return {"message": "Posição fechada com sucesso"}


@router.get("/price/{symbol}")
async def get_paper_price(symbol: str):
    """Retorna preço atual."""
    price = paper_trading.get_price(symbol)
    if not price:
        raise HTTPException(404, "Símbolo não encontrado")
    return price


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    async def test():
        engine = PaperTradingEngine(PaperConfig(
            initial_balance=10000.0,
            slippage_enabled=False,
        ))
        
        await engine.start()
        
        print("Account:", engine.get_account())
        
        # Abre posições
        ticket1 = await engine.open_position(
            symbol="XAUUSD",
            order_type=OrderType.BUY,
            volume=0.01,
            sl=2040.0,
            tp=2070.0,
            comment="Test trade"
        )
        print(f"Opened: #{ticket1}")
        
        ticket2 = await engine.open_position(
            symbol="EURUSD",
            order_type=OrderType.SELL,
            volume=0.02,
            comment="Test trade 2"
        )
        print(f"Opened: #{ticket2}")
        
        # Aguarda atualização
        await asyncio.sleep(2)
        
        print("\nPositions:", engine.get_positions())
        print("Account:", engine.get_account())
        
        # Fecha posição
        await engine.close_position(ticket1)
        
        print("\nStats:", engine.get_stats())
        print("History:", engine.get_history())
        
        await engine.stop()
    
    asyncio.run(test())
