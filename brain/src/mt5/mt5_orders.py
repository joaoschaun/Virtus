"""
VIRTUS MT5 - Order Manager
===========================

Gerenciador de ordens no MetaTrader 5.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import MetaTrader5 as mt5

from ..core.logger import get_logger
from ..core.config import get_config
from ..core.types import OrderType, Position, PositionStatus
from ..core.exceptions import MT5OrderError, MT5SymbolError
from .mt5_connection import MT5Connection, get_mt5_connection
from .mt5_data import MT5DataService, get_mt5_data

logger = get_logger("mt5_orders")


# Mapeamento de tipos de ordem
ORDER_TYPE_MAP = {
    OrderType.BUY: mt5.ORDER_TYPE_BUY,
    OrderType.SELL: mt5.ORDER_TYPE_SELL,
    OrderType.BUY_LIMIT: mt5.ORDER_TYPE_BUY_LIMIT,
    OrderType.SELL_LIMIT: mt5.ORDER_TYPE_SELL_LIMIT,
    OrderType.BUY_STOP: mt5.ORDER_TYPE_BUY_STOP,
    OrderType.SELL_STOP: mt5.ORDER_TYPE_SELL_STOP,
}


class MT5OrderManager:
    """
    Gerenciador de ordens MT5.
    
    Responsabilidades:
    - Enviar ordens (market, limit, stop)
    - Modificar posições
    - Fechar posições
    - Gerenciar trailing stops
    """
    
    _instance: Optional['MT5OrderManager'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._connection: Optional[MT5Connection] = None
        self._data_service: Optional[MT5DataService] = None
    
    @classmethod
    async def get_instance(cls) -> 'MT5OrderManager':
        """Retorna instância singleton"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._instance._connection = await get_mt5_connection()
                cls._instance._data_service = await get_mt5_data()
            return cls._instance
    
    async def _ensure_connected(self):
        """Garante conexão"""
        if not self._connection or not self._connection.is_connected:
            self._connection = await get_mt5_connection()
            if not await self._connection.ensure_connected():
                raise MT5OrderError("Não foi possível conectar ao MT5")
    
    # ========================================================================
    # ENVIO DE ORDENS
    # ========================================================================
    
    async def send_market_order(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        magic: int = 0,
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        Envia ordem a mercado.
        
        Args:
            symbol: Símbolo
            order_type: BUY ou SELL
            volume: Volume em lotes
            stop_loss: Preço do stop loss
            take_profit: Preço do take profit
            magic: Magic number para identificação
            comment: Comentário da ordem
            
        Returns:
            Dict com resultado da ordem
        """
        await self._ensure_connected()
        
        # Validações
        if order_type not in [OrderType.BUY, OrderType.SELL]:
            raise MT5OrderError("Ordem a mercado deve ser BUY ou SELL")
        
        # Seleciona símbolo
        if not self._connection.select_symbol(symbol):
            raise MT5SymbolError(f"Não foi possível selecionar {symbol}")
        
        # Obtém preço atual
        price_data = await self._data_service.get_price(symbol)
        price = price_data['ask'] if order_type == OrderType.BUY else price_data['bid']
        
        # Obtém info do símbolo
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise MT5SymbolError(f"Informações de {symbol} não disponíveis")
        
        # Prepara request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": ORDER_TYPE_MAP[order_type],
            "price": price,
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        if stop_loss:
            request["sl"] = stop_loss
        if take_profit:
            request["tp"] = take_profit
        
        # Envia ordem
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Falha ao enviar ordem: {result.comment} (code: {result.retcode})"
            logger.error(f"❌ {error_msg}")
            raise MT5OrderError(error_msg)
        
        logger.info(
            f"✅ Ordem executada: {order_type.value} {volume} {symbol} @ {result.price} "
            f"| Ticket: {result.order}"
        )
        
        return {
            'success': True,
            'ticket': result.order,
            'deal': result.deal,
            'volume': result.volume,
            'price': result.price,
            'symbol': symbol,
            'order_type': order_type.value,
            'comment': comment,
        }
    
    async def send_pending_order(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        magic: int = 0,
        comment: str = "",
        expiration: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Envia ordem pendente.
        
        Args:
            symbol: Símbolo
            order_type: BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP
            volume: Volume em lotes
            price: Preço de entrada
            stop_loss: Preço do stop loss
            take_profit: Preço do take profit
            magic: Magic number
            comment: Comentário
            expiration: Data de expiração
            
        Returns:
            Dict com resultado
        """
        await self._ensure_connected()
        
        if order_type in [OrderType.BUY, OrderType.SELL]:
            raise MT5OrderError("Use send_market_order para ordens a mercado")
        
        if not self._connection.select_symbol(symbol):
            raise MT5SymbolError(f"Não foi possível selecionar {symbol}")
        
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": ORDER_TYPE_MAP[order_type],
            "price": price,
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        
        if stop_loss:
            request["sl"] = stop_loss
        if take_profit:
            request["tp"] = take_profit
        if expiration:
            request["type_time"] = mt5.ORDER_TIME_SPECIFIED
            request["expiration"] = int(expiration.timestamp())
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Falha ao enviar ordem pendente: {result.comment}"
            logger.error(f"❌ {error_msg}")
            raise MT5OrderError(error_msg)
        
        logger.info(f"✅ Ordem pendente criada: {order_type.value} {volume} {symbol} @ {price}")
        
        return {
            'success': True,
            'ticket': result.order,
            'volume': result.volume,
            'price': price,
            'symbol': symbol,
            'order_type': order_type.value,
        }
    
    # ========================================================================
    # MODIFICAÇÃO DE POSIÇÕES
    # ========================================================================
    
    async def modify_position(
        self,
        ticket: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> bool:
        """
        Modifica SL/TP de uma posição.
        
        Args:
            ticket: Ticket da posição
            stop_loss: Novo stop loss
            take_profit: Novo take profit
            
        Returns:
            True se modificado com sucesso
        """
        await self._ensure_connected()
        
        # Obtém posição atual
        position = mt5.positions_get(ticket=ticket)
        if not position:
            raise MT5OrderError(f"Posição {ticket} não encontrada")
        
        position = position[0]
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": position.symbol,
            "sl": stop_loss if stop_loss else position.sl,
            "tp": take_profit if take_profit else position.tp,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Falha ao modificar posição: {result.comment}"
            logger.error(f"❌ {error_msg}")
            raise MT5OrderError(error_msg)
        
        logger.info(f"✅ Posição {ticket} modificada - SL: {stop_loss}, TP: {take_profit}")
        return True
    
    async def move_stop_to_breakeven(
        self,
        ticket: int,
        lock_pips: float = 0
    ) -> bool:
        """
        Move stop loss para breakeven + pips de lock.
        
        Args:
            ticket: Ticket da posição
            lock_pips: Pips de lucro a garantir
            
        Returns:
            True se modificado
        """
        await self._ensure_connected()
        
        position = mt5.positions_get(ticket=ticket)
        if not position:
            raise MT5OrderError(f"Posição {ticket} não encontrada")
        
        position = position[0]
        symbol_info = mt5.symbol_info(position.symbol)
        point = symbol_info.point
        
        # Calcula novo SL
        if position.type == mt5.ORDER_TYPE_BUY:
            new_sl = position.price_open + (lock_pips * point * 10)  # Assumindo 5 dígitos
        else:
            new_sl = position.price_open - (lock_pips * point * 10)
        
        return await self.modify_position(ticket, stop_loss=new_sl)
    
    async def apply_trailing_stop(
        self,
        ticket: int,
        distance_pips: float,
        step_pips: float = 1
    ) -> bool:
        """
        Aplica trailing stop a uma posição.
        
        Args:
            ticket: Ticket da posição
            distance_pips: Distância do trailing em pips
            step_pips: Step mínimo para mover
            
        Returns:
            True se trailing aplicado
        """
        await self._ensure_connected()
        
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False
        
        position = position[0]
        symbol_info = mt5.symbol_info(position.symbol)
        point = symbol_info.point
        
        # Obtém preço atual
        tick = mt5.symbol_info_tick(position.symbol)
        
        # Calcula novo SL
        if position.type == mt5.ORDER_TYPE_BUY:
            new_sl = tick.bid - (distance_pips * point * 10)
            # Só move se for maior que o SL atual
            if position.sl == 0 or new_sl > position.sl + (step_pips * point * 10):
                return await self.modify_position(ticket, stop_loss=new_sl)
        else:
            new_sl = tick.ask + (distance_pips * point * 10)
            # Só move se for menor que o SL atual
            if position.sl == 0 or new_sl < position.sl - (step_pips * point * 10):
                return await self.modify_position(ticket, stop_loss=new_sl)
        
        return False
    
    # ========================================================================
    # FECHAMENTO DE POSIÇÕES
    # ========================================================================
    
    async def close_position(
        self,
        ticket: int,
        volume: Optional[float] = None,
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        Fecha uma posição.
        
        Args:
            ticket: Ticket da posição
            volume: Volume a fechar (None = total)
            comment: Comentário
            
        Returns:
            Dict com resultado
        """
        await self._ensure_connected()
        
        position = mt5.positions_get(ticket=ticket)
        if not position:
            raise MT5OrderError(f"Posição {ticket} não encontrada")
        
        position = position[0]
        close_volume = volume if volume else position.volume
        
        # Tipo oposto para fechar
        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        # Preço para fechar
        tick = mt5.symbol_info_tick(position.symbol)
        price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": position.symbol,
            "volume": close_volume,
            "type": close_type,
            "price": price,
            "deviation": 20,
            "magic": position.magic,
            "comment": comment or "close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Falha ao fechar posição: {result.comment}"
            logger.error(f"❌ {error_msg}")
            raise MT5OrderError(error_msg)
        
        logger.info(f"✅ Posição {ticket} fechada @ {result.price} | Profit: {position.profit:.2f}")
        
        return {
            'success': True,
            'ticket': ticket,
            'close_price': result.price,
            'profit': position.profit,
            'volume_closed': close_volume,
        }
    
    async def close_all_positions(
        self,
        symbol: Optional[str] = None,
        magic: Optional[int] = None,
        comment: str = "close_all"
    ) -> List[Dict[str, Any]]:
        """
        Fecha todas as posições (opcionalmente filtradas).
        
        Args:
            symbol: Filtrar por símbolo
            magic: Filtrar por magic number
            comment: Comentário
            
        Returns:
            Lista de resultados
        """
        await self._ensure_connected()
        
        positions = mt5.positions_get()
        if not positions:
            return []
        
        results = []
        for pos in positions:
            # Aplica filtros
            if symbol and pos.symbol != symbol:
                continue
            if magic and pos.magic != magic:
                continue
            
            try:
                result = await self.close_position(pos.ticket, comment=comment)
                results.append(result)
            except Exception as e:
                logger.error(f"Erro ao fechar posição {pos.ticket}: {e}")
                results.append({'success': False, 'ticket': pos.ticket, 'error': str(e)})
        
        return results
    
    async def close_partial(
        self,
        ticket: int,
        percentage: float,
        comment: str = "partial_close"
    ) -> Dict[str, Any]:
        """
        Fecha parcialmente uma posição.
        
        Args:
            ticket: Ticket da posição
            percentage: Percentual a fechar (0-100)
            comment: Comentário
            
        Returns:
            Dict com resultado
        """
        position = mt5.positions_get(ticket=ticket)
        if not position:
            raise MT5OrderError(f"Posição {ticket} não encontrada")
        
        position = position[0]
        symbol_info = mt5.symbol_info(position.symbol)
        
        # Calcula volume a fechar
        close_volume = position.volume * (percentage / 100)
        # Arredonda para step do símbolo
        close_volume = round(close_volume / symbol_info.volume_step) * symbol_info.volume_step
        
        if close_volume < symbol_info.volume_min:
            raise MT5OrderError(f"Volume calculado ({close_volume}) menor que mínimo ({symbol_info.volume_min})")
        
        return await self.close_position(ticket, volume=close_volume, comment=comment)
    
    # ========================================================================
    # CONSULTAS
    # ========================================================================
    
    async def get_positions(
        self,
        symbol: Optional[str] = None,
        magic: Optional[int] = None
    ) -> List[Position]:
        """
        Obtém posições abertas.
        
        Args:
            symbol: Filtrar por símbolo
            magic: Filtrar por magic number
            
        Returns:
            Lista de Position
        """
        await self._ensure_connected()
        
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        if not positions:
            return []
        
        result = []
        for pos in positions:
            if magic and pos.magic != magic:
                continue
            
            # Determina tipo de ordem
            order_type = OrderType.BUY if pos.type == mt5.ORDER_TYPE_BUY else OrderType.SELL
            
            position = Position(
                ticket=pos.ticket,
                symbol=pos.symbol,
                order_type=order_type,
                volume=pos.volume,
                entry_price=pos.price_open,
                current_price=pos.price_current,
                stop_loss=pos.sl if pos.sl != 0 else None,
                take_profit=pos.tp if pos.tp != 0 else None,
                status=PositionStatus.OPEN,
                open_time=datetime.fromtimestamp(pos.time),
                profit=pos.profit,
                swap=pos.swap,
                commission=pos.commission if hasattr(pos, 'commission') else 0,
                magic_number=pos.magic,
                comment=pos.comment,
            )
            result.append(position)
        
        return result
    
    async def get_pending_orders(
        self,
        symbol: Optional[str] = None,
        magic: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Obtém ordens pendentes"""
        await self._ensure_connected()
        
        if symbol:
            orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()
        
        if not orders:
            return []
        
        result = []
        for order in orders:
            if magic and order.magic != magic:
                continue
            
            result.append({
                'ticket': order.ticket,
                'symbol': order.symbol,
                'type': order.type,
                'volume': order.volume_current,
                'price': order.price_open,
                'sl': order.sl,
                'tp': order.tp,
                'magic': order.magic,
                'comment': order.comment,
                'time_setup': datetime.fromtimestamp(order.time_setup),
            })
        
        return result
    
    async def cancel_pending_order(self, ticket: int) -> bool:
        """Cancela ordem pendente"""
        await self._ensure_connected()
        
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Falha ao cancelar ordem {ticket}: {result.comment}")
            return False
        
        logger.info(f"✅ Ordem {ticket} cancelada")
        return True


# Helper
async def get_mt5_orders() -> MT5OrderManager:
    """Retorna instância do gerenciador de ordens"""
    return await MT5OrderManager.get_instance()
