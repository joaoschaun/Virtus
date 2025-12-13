"""
BRAIN - MT5 Data Feed
Streaming de dados do MetaTrader 5
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from .mt5_manager import MT5Manager, get_mt5_manager
from ..core.types import Timeframe
from ..core.logger import get_logger
from ..core.exceptions import MT5Error

logger = get_logger("mt5.datafeed")


@dataclass
class TickData:
    """Dados de tick"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    time: datetime
    spread: float


@dataclass
class BarData:
    """Dados de barra/candle"""
    symbol: str
    timeframe: Timeframe
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    real_volume: int = 0


class MT5DataFeed:
    """
    Feed de dados do MetaTrader 5
    
    Responsabilidades:
    - Streaming de ticks
    - Atualização de barras
    - Cache de dados
    - Callbacks para novos dados
    """
    
    def __init__(self, mt5_manager: Optional[MT5Manager] = None):
        self._mt5 = mt5_manager or get_mt5_manager()
        self._running = False
        
        # Símbolos subscritos
        self._subscribed_symbols: Set[str] = set()
        
        # Callbacks
        self._tick_callbacks: Dict[str, List[Callable]] = {}
        self._bar_callbacks: Dict[str, List[Callable]] = {}
        
        # Cache de últimos dados
        self._last_ticks: Dict[str, TickData] = {}
        self._last_bars: Dict[str, Dict[Timeframe, BarData]] = {}
        
        # Tasks de polling
        self._tick_task: Optional[asyncio.Task] = None
        self._bar_tasks: Dict[Timeframe, asyncio.Task] = {}
    
    async def start(self):
        """Inicia o feed de dados"""
        if self._running:
            return
        
        if not self._mt5.is_connected:
            raise MT5Error("MT5 não conectado")
        
        self._running = True
        
        # Iniciar polling de ticks
        self._tick_task = asyncio.create_task(self._tick_polling_loop())
        
        logger.info("MT5 DataFeed iniciado")
    
    async def stop(self):
        """Para o feed de dados"""
        self._running = False
        
        # Cancelar tasks
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        
        for task in self._bar_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._bar_tasks.clear()
        logger.info("MT5 DataFeed parado")
    
    def subscribe(
        self,
        symbol: str,
        on_tick: Optional[Callable[[TickData], None]] = None,
        on_bar: Optional[Callable[[BarData], None]] = None,
        timeframe: Timeframe = Timeframe.M1
    ):
        """
        Subscreve para receber dados de um símbolo
        
        Args:
            symbol: Símbolo
            on_tick: Callback para novos ticks
            on_bar: Callback para novas barras
            timeframe: Timeframe para barras
        """
        self._subscribed_symbols.add(symbol)
        
        if on_tick:
            if symbol not in self._tick_callbacks:
                self._tick_callbacks[symbol] = []
            self._tick_callbacks[symbol].append(on_tick)
        
        if on_bar:
            key = f"{symbol}_{timeframe.value}"
            if key not in self._bar_callbacks:
                self._bar_callbacks[key] = []
            self._bar_callbacks[key].append(on_bar)
            
            # Iniciar polling de barras se não existir
            if timeframe not in self._bar_tasks and self._running:
                self._bar_tasks[timeframe] = asyncio.create_task(
                    self._bar_polling_loop(timeframe)
                )
        
        logger.debug(f"Subscrito em {symbol}")
    
    def unsubscribe(self, symbol: str):
        """Remove subscrição de um símbolo"""
        self._subscribed_symbols.discard(symbol)
        self._tick_callbacks.pop(symbol, None)
        
        # Remover callbacks de barras
        keys_to_remove = [k for k in self._bar_callbacks if k.startswith(f"{symbol}_")]
        for key in keys_to_remove:
            del self._bar_callbacks[key]
        
        logger.debug(f"Unsubscribed de {symbol}")
    
    async def _tick_polling_loop(self):
        """Loop de polling de ticks"""
        while self._running:
            try:
                for symbol in list(self._subscribed_symbols):
                    await self._process_tick(symbol)
                
                # Intervalo entre polls
                await asyncio.sleep(0.1)  # 100ms
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no tick polling: {e}")
                await asyncio.sleep(1)
    
    async def _process_tick(self, symbol: str):
        """Processa tick de um símbolo"""
        try:
            tick_data = await self._mt5.get_tick(symbol)
            
            tick = TickData(
                symbol=symbol,
                bid=tick_data["bid"],
                ask=tick_data["ask"],
                last=tick_data["last"],
                volume=tick_data["volume"],
                time=tick_data["time"],
                spread=tick_data["spread"]
            )
            
            # Verificar se é novo tick
            last_tick = self._last_ticks.get(symbol)
            if last_tick is None or tick.time > last_tick.time:
                self._last_ticks[symbol] = tick
                
                # Notificar callbacks
                for callback in self._tick_callbacks.get(symbol, []):
                    try:
                        callback(tick)
                    except Exception as e:
                        logger.error(f"Erro em tick callback: {e}")
                        
        except Exception as e:
            logger.error(f"Erro ao processar tick de {symbol}: {e}")
    
    async def _bar_polling_loop(self, timeframe: Timeframe):
        """Loop de polling de barras"""
        # Intervalo baseado no timeframe
        intervals = {
            Timeframe.M1: 60,
            Timeframe.M5: 60,
            Timeframe.M15: 60,
            Timeframe.M30: 60,
            Timeframe.H1: 60,
            Timeframe.H4: 300,
            Timeframe.D1: 3600
        }
        
        interval = intervals.get(timeframe, 60)
        
        while self._running:
            try:
                for symbol in list(self._subscribed_symbols):
                    await self._process_bar(symbol, timeframe)
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no bar polling: {e}")
                await asyncio.sleep(interval)
    
    async def _process_bar(self, symbol: str, timeframe: Timeframe):
        """Processa nova barra"""
        try:
            rates = await self._mt5.get_rates(symbol, timeframe, count=2)
            
            if not rates:
                return
            
            # Última barra completa
            bar_data = rates[-2] if len(rates) >= 2 else rates[-1]
            
            bar = BarData(
                symbol=symbol,
                timeframe=timeframe,
                time=bar_data["time"],
                open=bar_data["open"],
                high=bar_data["high"],
                low=bar_data["low"],
                close=bar_data["close"],
                tick_volume=bar_data["tick_volume"],
                real_volume=bar_data.get("real_volume", 0)
            )
            
            # Cache
            if symbol not in self._last_bars:
                self._last_bars[symbol] = {}
            
            # Verificar se é nova barra
            last_bar = self._last_bars[symbol].get(timeframe)
            if last_bar is None or bar.time > last_bar.time:
                self._last_bars[symbol][timeframe] = bar
                
                # Notificar callbacks
                key = f"{symbol}_{timeframe.value}"
                for callback in self._bar_callbacks.get(key, []):
                    try:
                        callback(bar)
                    except Exception as e:
                        logger.error(f"Erro em bar callback: {e}")
                        
        except Exception as e:
            logger.error(f"Erro ao processar bar de {symbol}: {e}")
    
    # ==========================================================================
    # MÉTODOS DE ACESSO A DADOS
    # ==========================================================================
    
    def get_last_tick(self, symbol: str) -> Optional[TickData]:
        """Obtém último tick em cache"""
        return self._last_ticks.get(symbol)
    
    def get_last_bar(
        self,
        symbol: str,
        timeframe: Timeframe
    ) -> Optional[BarData]:
        """Obtém última barra em cache"""
        return self._last_bars.get(symbol, {}).get(timeframe)
    
    async def get_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        count: int = 100
    ) -> List[BarData]:
        """
        Obtém barras históricas
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            count: Número de barras
            
        Returns:
            Lista de BarData
        """
        rates = await self._mt5.get_rates(symbol, timeframe, count)
        
        return [
            BarData(
                symbol=symbol,
                timeframe=timeframe,
                time=r["time"],
                open=r["open"],
                high=r["high"],
                low=r["low"],
                close=r["close"],
                tick_volume=r["tick_volume"],
                real_volume=r.get("real_volume", 0)
            )
            for r in rates
        ]
    
    def get_spread(self, symbol: str) -> float:
        """Obtém spread atual"""
        tick = self._last_ticks.get(symbol)
        return tick.spread if tick else 0.0
    
    def get_mid_price(self, symbol: str) -> float:
        """Obtém preço mid"""
        tick = self._last_ticks.get(symbol)
        if tick:
            return (tick.bid + tick.ask) / 2
        return 0.0


# Factory
def create_datafeed(mt5_manager: Optional[MT5Manager] = None) -> MT5DataFeed:
    """Cria nova instância do DataFeed"""
    return MT5DataFeed(mt5_manager)
