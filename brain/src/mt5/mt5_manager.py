"""
BRAIN - MT5 Connection Manager
Gerenciador de conexão com MetaTrader 5
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import os

from ..core.logger import get_logger
from ..core.types import (
    OrderType, SignalDirection, Position, Trade,
    Timeframe, Signal
)
from ..core.exceptions import MT5Error, ConnectionError

logger = get_logger("mt5")


class MT5ConnectionState(Enum):
    """Estado da conexão MT5"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MT5Manager:
    """
    Gerenciador de conexão com MetaTrader 5
    
    Singleton que gerencia:
    - Conexão com terminal MT5
    - Execução de ordens
    - Consulta de posições
    - Dados de mercado
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if MT5Manager._initialized:
            return
        
        self._state = MT5ConnectionState.DISCONNECTED
        self._account_info: Dict[str, Any] = {}
        self._connected_at: Optional[datetime] = None
        self._mt5 = None  # Módulo MetaTrader5
        self._lock = asyncio.Lock()
        
        MT5Manager._initialized = True
    
    @property
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self._state == MT5ConnectionState.CONNECTED
    
    @property
    def state(self) -> MT5ConnectionState:
        """Estado atual da conexão"""
        return self._state
    
    async def connect(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        path: Optional[str] = None,
        timeout: int = 60000
    ) -> bool:
        """
        Conecta ao terminal MetaTrader 5
        
        Args:
            login: Número da conta
            password: Senha
            server: Servidor
            path: Caminho do terminal
            timeout: Timeout em ms
            
        Returns:
            True se conectado com sucesso
        """
        async with self._lock:
            if self._state == MT5ConnectionState.CONNECTED:
                logger.info("Já conectado ao MT5")
                return True
            
            self._state = MT5ConnectionState.CONNECTING
            
            try:
                # Importar MT5 aqui para evitar erro se não instalado
                import MetaTrader5 as mt5
                self._mt5 = mt5
                
                # Parâmetros de conexão
                init_params = {}
                
                if path:
                    init_params["path"] = path
                if login:
                    init_params["login"] = login
                if password:
                    init_params["password"] = password
                if server:
                    init_params["server"] = server
                if timeout:
                    init_params["timeout"] = timeout
                
                # Inicializar MT5
                if not mt5.initialize(**init_params):
                    error = mt5.last_error()
                    self._state = MT5ConnectionState.ERROR
                    raise MT5Error(f"Falha ao inicializar MT5: {error}")
                
                # Login se credenciais fornecidas
                if login and password and server:
                    if not mt5.login(login, password, server):
                        error = mt5.last_error()
                        mt5.shutdown()
                        self._state = MT5ConnectionState.ERROR
                        raise MT5Error(f"Falha no login MT5: {error}")
                
                # Obter info da conta
                account = mt5.account_info()
                if account:
                    self._account_info = {
                        "login": account.login,
                        "server": account.server,
                        "balance": account.balance,
                        "equity": account.equity,
                        "profit": account.profit,
                        "margin": account.margin,
                        "margin_free": account.margin_free,
                        "margin_level": account.margin_level,
                        "leverage": account.leverage,
                        "currency": account.currency
                    }
                
                self._state = MT5ConnectionState.CONNECTED
                self._connected_at = datetime.now()
                
                logger.info(f"Conectado ao MT5 - Conta: {self._account_info.get('login')}")
                return True
                
            except ImportError:
                self._state = MT5ConnectionState.ERROR
                raise MT5Error("Módulo MetaTrader5 não instalado")
            except Exception as e:
                self._state = MT5ConnectionState.ERROR
                raise MT5Error(f"Erro ao conectar MT5: {e}", e)
    
    async def disconnect(self):
        """Desconecta do MetaTrader 5"""
        async with self._lock:
            if self._mt5 and self._state == MT5ConnectionState.CONNECTED:
                self._mt5.shutdown()
            
            self._state = MT5ConnectionState.DISCONNECTED
            self._account_info = {}
            self._connected_at = None
            logger.info("Desconectado do MT5")
    
    def _ensure_connected(self):
        """Garante que está conectado"""
        if self._state != MT5ConnectionState.CONNECTED:
            raise MT5Error("Não conectado ao MT5")
    
    # ==========================================================================
    # DADOS DE MERCADO
    # ==========================================================================
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Obtém informações do símbolo
        
        Args:
            symbol: Nome do símbolo
            
        Returns:
            Dict com informações
        """
        self._ensure_connected()
        
        info = self._mt5.symbol_info(symbol)
        if info is None:
            raise MT5Error(f"Símbolo não encontrado: {symbol}")
        
        return {
            "name": info.name,
            "description": info.description,
            "path": info.path,
            "point": info.point,
            "digits": info.digits,
            "spread": info.spread,
            "spread_float": info.spread_float,
            "trade_contract_size": info.trade_contract_size,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "bid": info.bid,
            "ask": info.ask,
            "last": info.last,
            "trade_mode": info.trade_mode,
            "swap_long": info.swap_long,
            "swap_short": info.swap_short
        }
    
    async def get_tick(self, symbol: str) -> Dict[str, Any]:
        """
        Obtém último tick do símbolo
        
        Args:
            symbol: Nome do símbolo
            
        Returns:
            Dict com tick atual
        """
        self._ensure_connected()
        
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5Error(f"Não foi possível obter tick de {symbol}")
        
        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "volume": tick.volume,
            "time": datetime.fromtimestamp(tick.time),
            "spread": round((tick.ask - tick.bid) / self._mt5.symbol_info(symbol).point)
        }
    
    async def get_rates(
        self,
        symbol: str,
        timeframe: Timeframe,
        count: int = 100,
        from_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém dados OHLCV
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            count: Número de candles
            from_date: Data inicial (opcional)
            
        Returns:
            Lista de candles
        """
        self._ensure_connected()
        
        # Mapear timeframe
        tf_map = {
            Timeframe.M1: self._mt5.TIMEFRAME_M1,
            Timeframe.M5: self._mt5.TIMEFRAME_M5,
            Timeframe.M15: self._mt5.TIMEFRAME_M15,
            Timeframe.M30: self._mt5.TIMEFRAME_M30,
            Timeframe.H1: self._mt5.TIMEFRAME_H1,
            Timeframe.H4: self._mt5.TIMEFRAME_H4,
            Timeframe.D1: self._mt5.TIMEFRAME_D1,
            Timeframe.W1: self._mt5.TIMEFRAME_W1,
            Timeframe.MN1: self._mt5.TIMEFRAME_MN1
        }
        
        mt5_tf = tf_map.get(timeframe, self._mt5.TIMEFRAME_H1)
        
        if from_date:
            rates = self._mt5.copy_rates_from(symbol, mt5_tf, from_date, count)
        else:
            rates = self._mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)
        
        if rates is None:
            raise MT5Error(f"Não foi possível obter rates de {symbol}")
        
        return [
            {
                "time": datetime.fromtimestamp(r[0]),
                "open": r[1],
                "high": r[2],
                "low": r[3],
                "close": r[4],
                "tick_volume": r[5],
                "spread": r[6],
                "real_volume": r[7]
            }
            for r in rates
        ]
    
    # ==========================================================================
    # CONTA E POSIÇÕES
    # ==========================================================================
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Obtém informações atualizadas da conta"""
        self._ensure_connected()
        
        account = self._mt5.account_info()
        if account is None:
            raise MT5Error("Não foi possível obter informações da conta")
        
        self._account_info = {
            "login": account.login,
            "server": account.server,
            "balance": account.balance,
            "equity": account.equity,
            "profit": account.profit,
            "margin": account.margin,
            "margin_free": account.margin_free,
            "margin_level": account.margin_level,
            "leverage": account.leverage,
            "currency": account.currency
        }
        
        return self._account_info
    
    async def get_positions(
        self,
        symbol: Optional[str] = None
    ) -> List[Position]:
        """
        Obtém posições abertas
        
        Args:
            symbol: Filtrar por símbolo (opcional)
            
        Returns:
            Lista de Position
        """
        self._ensure_connected()
        
        if symbol:
            positions = self._mt5.positions_get(symbol=symbol)
        else:
            positions = self._mt5.positions_get()
        
        if positions is None:
            return []
        
        result = []
        for pos in positions:
            position = Position(
                ticket=pos.ticket,
                symbol=pos.symbol,
                order_type=OrderType.BUY if pos.type == 0 else OrderType.SELL,
                volume=pos.volume,
                price_open=pos.price_open,
                sl=pos.sl,
                tp=pos.tp,
                price_current=pos.price_current,
                profit=pos.profit,
                time_open=datetime.fromtimestamp(pos.time),
                magic=pos.magic,
                comment=pos.comment
            )
            result.append(position)
        
        return result
    
    async def get_orders(
        self,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém ordens pendentes
        
        Args:
            symbol: Filtrar por símbolo (opcional)
            
        Returns:
            Lista de ordens
        """
        self._ensure_connected()
        
        if symbol:
            orders = self._mt5.orders_get(symbol=symbol)
        else:
            orders = self._mt5.orders_get()
        
        if orders is None:
            return []
        
        return [
            {
                "ticket": o.ticket,
                "symbol": o.symbol,
                "type": o.type,
                "volume": o.volume_current,
                "price_open": o.price_open,
                "sl": o.sl,
                "tp": o.tp,
                "time_setup": datetime.fromtimestamp(o.time_setup),
                "magic": o.magic,
                "comment": o.comment
            }
            for o in orders
        ]
    
    # ==========================================================================
    # EXECUÇÃO DE ORDENS
    # ==========================================================================
    
    async def send_order(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        deviation: int = 20,
        magic: int = 0,
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        Envia ordem de mercado
        
        Args:
            symbol: Símbolo
            order_type: Tipo de ordem (BUY/SELL)
            volume: Volume/lots
            price: Preço (None para mercado)
            sl: Stop Loss
            tp: Take Profit
            deviation: Desvio máximo em pontos
            magic: Magic number
            comment: Comentário
            
        Returns:
            Resultado da ordem
        """
        self._ensure_connected()
        
        # Obter preço atual se não especificado
        if price is None:
            tick = self._mt5.symbol_info_tick(symbol)
            if tick is None:
                raise MT5Error(f"Não foi possível obter preço de {symbol}")
            
            price = tick.ask if order_type == OrderType.BUY else tick.bid
        
        # Mapear tipo de ordem
        mt5_type = self._mt5.ORDER_TYPE_BUY if order_type == OrderType.BUY else self._mt5.ORDER_TYPE_SELL
        
        # Preparar request
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5_type,
            "price": price,
            "deviation": deviation,
            "magic": magic,
            "comment": comment,
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC
        }
        
        if sl:
            request["sl"] = sl
        if tp:
            request["tp"] = tp
        
        # Enviar ordem
        result = self._mt5.order_send(request)
        
        if result is None:
            raise MT5Error("Falha ao enviar ordem - resultado nulo")
        
        if result.retcode != self._mt5.TRADE_RETCODE_DONE:
            raise MT5Error(f"Ordem rejeitada: {result.retcode} - {result.comment}")
        
        logger.info(
            f"Ordem executada: {symbol} {order_type.value} {volume} @ {result.price}"
        )
        
        return {
            "ticket": result.order,
            "deal": result.deal,
            "volume": result.volume,
            "price": result.price,
            "comment": result.comment,
            "retcode": result.retcode
        }
    
    async def modify_position(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None
    ) -> bool:
        """
        Modifica SL/TP de uma posição
        
        Args:
            ticket: Ticket da posição
            sl: Novo Stop Loss
            tp: Novo Take Profit
            
        Returns:
            True se sucesso
        """
        self._ensure_connected()
        
        # Obter posição atual
        position = self._mt5.positions_get(ticket=ticket)
        if not position:
            raise MT5Error(f"Posição não encontrada: {ticket}")
        
        pos = position[0]
        
        request = {
            "action": self._mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": sl if sl else pos.sl,
            "tp": tp if tp else pos.tp
        }
        
        result = self._mt5.order_send(request)
        
        if result is None or result.retcode != self._mt5.TRADE_RETCODE_DONE:
            raise MT5Error(f"Falha ao modificar posição: {result.comment if result else 'erro desconhecido'}")
        
        logger.info(f"Posição {ticket} modificada: SL={sl}, TP={tp}")
        return True
    
    async def close_position(
        self,
        ticket: int,
        volume: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Fecha uma posição
        
        Args:
            ticket: Ticket da posição
            volume: Volume a fechar (None = total)
            
        Returns:
            Resultado do fechamento
        """
        self._ensure_connected()
        
        # Obter posição
        position = self._mt5.positions_get(ticket=ticket)
        if not position:
            raise MT5Error(f"Posição não encontrada: {ticket}")
        
        pos = position[0]
        
        # Volume a fechar
        close_volume = volume if volume else pos.volume
        
        # Tipo oposto
        close_type = self._mt5.ORDER_TYPE_SELL if pos.type == 0 else self._mt5.ORDER_TYPE_BUY
        
        # Preço de fechamento
        tick = self._mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if pos.type == 0 else tick.ask
        
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": close_volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": pos.magic,
            "comment": "Close by BRAIN",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC
        }
        
        result = self._mt5.order_send(request)
        
        if result is None or result.retcode != self._mt5.TRADE_RETCODE_DONE:
            raise MT5Error(f"Falha ao fechar posição: {result.comment if result else 'erro desconhecido'}")
        
        logger.info(f"Posição {ticket} fechada: {close_volume} lots @ {result.price}")
        
        return {
            "ticket": result.order,
            "volume": result.volume,
            "price": result.price,
            "profit": pos.profit
        }
    
    async def close_all_positions(
        self,
        symbol: Optional[str] = None
    ) -> int:
        """
        Fecha todas as posições
        
        Args:
            symbol: Filtrar por símbolo (opcional)
            
        Returns:
            Número de posições fechadas
        """
        positions = await self.get_positions(symbol)
        
        closed = 0
        for pos in positions:
            try:
                await self.close_position(pos.ticket)
                closed += 1
            except MT5Error as e:
                logger.error(f"Falha ao fechar posição {pos.ticket}: {e}")
        
        return closed


# Singleton global
_mt5_manager: Optional[MT5Manager] = None


def get_mt5_manager() -> MT5Manager:
    """Obtém instância global do MT5Manager"""
    global _mt5_manager
    if _mt5_manager is None:
        _mt5_manager = MT5Manager()
    return _mt5_manager
