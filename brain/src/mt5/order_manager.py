"""
BRAIN - MT5 Order Manager
Gerenciador de ordens e execução
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from .mt5_manager import MT5Manager, get_mt5_manager
from ..core.types import OrderType, Position, SignalDirection
from ..core.logger import get_logger
from ..core.exceptions import MT5Error, RiskError

logger = get_logger("mt5.orders")


class OrderStatus(Enum):
    """Status de uma ordem"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class OrderRequest:
    """Requisição de ordem"""
    symbol: str
    order_type: OrderType
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    deviation: int = 20
    magic: int = 0
    comment: str = ""
    
    # Controle interno
    bot_id: Optional[str] = None
    signal_id: Optional[str] = None


@dataclass
class OrderResult:
    """Resultado de uma ordem"""
    success: bool
    ticket: int = 0
    deal: int = 0
    volume: float = 0.0
    price: float = 0.0
    message: str = ""
    request: Optional[OrderRequest] = None


class OrderManager:
    """
    Gerenciador de ordens
    
    Responsabilidades:
    - Validar ordens antes de enviar
    - Calcular SL/TP
    - Executar ordens via MT5
    - Rastrear ordens
    """
    
    def __init__(
        self,
        mt5_manager: Optional[MT5Manager] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self._mt5 = mt5_manager or get_mt5_manager()
        self._config = config or {}
        
        # Configurações padrão
        self._default_deviation = self._config.get("default_deviation", 20)
        self._max_slippage_pips = self._config.get("max_slippage_pips", 5)
        self._default_magic = self._config.get("default_magic", 123456)
        
        # Cache de símbolo info
        self._symbol_info_cache: Dict[str, Dict[str, Any]] = {}
        
        # Histórico de ordens
        self._order_history: List[OrderResult] = []
        
        # Lock para execução sequencial
        self._lock = asyncio.Lock()
    
    async def send_order(self, request: OrderRequest) -> OrderResult:
        """
        Envia uma ordem para o MT5
        
        Args:
            request: Requisição de ordem
            
        Returns:
            Resultado da ordem
        """
        async with self._lock:
            try:
                # Validar ordem
                await self._validate_order(request)
                
                # Normalizar volume
                request.volume = await self._normalize_volume(
                    request.symbol,
                    request.volume
                )
                
                # Normalizar preços
                if request.sl:
                    request.sl = await self._normalize_price(
                        request.symbol,
                        request.sl
                    )
                if request.tp:
                    request.tp = await self._normalize_price(
                        request.symbol,
                        request.tp
                    )
                
                # Definir magic se não especificado
                if request.magic == 0:
                    request.magic = self._default_magic
                
                # Enviar via MT5
                result = await self._mt5.send_order(
                    symbol=request.symbol,
                    order_type=request.order_type,
                    volume=request.volume,
                    price=request.price,
                    sl=request.sl,
                    tp=request.tp,
                    deviation=request.deviation or self._default_deviation,
                    magic=request.magic,
                    comment=request.comment
                )
                
                order_result = OrderResult(
                    success=True,
                    ticket=result["ticket"],
                    deal=result.get("deal", 0),
                    volume=result["volume"],
                    price=result["price"],
                    message=result.get("comment", "OK"),
                    request=request
                )
                
                self._order_history.append(order_result)
                
                logger.info(
                    f"Ordem executada: {request.symbol} {request.order_type.value} "
                    f"{result['volume']} @ {result['price']}"
                )
                
                return order_result
                
            except Exception as e:
                order_result = OrderResult(
                    success=False,
                    message=str(e),
                    request=request
                )
                self._order_history.append(order_result)
                
                logger.error(f"Falha ao enviar ordem: {e}")
                return order_result
    
    async def _validate_order(self, request: OrderRequest):
        """Valida uma ordem antes de enviar"""
        # Verificar conexão
        if not self._mt5.is_connected:
            raise MT5Error("MT5 não conectado")
        
        # Verificar símbolo
        symbol_info = await self._get_symbol_info(request.symbol)
        if not symbol_info:
            raise MT5Error(f"Símbolo inválido: {request.symbol}")
        
        # Verificar volume
        min_vol = symbol_info.get("volume_min", 0.01)
        max_vol = symbol_info.get("volume_max", 100)
        
        if request.volume < min_vol:
            raise RiskError(f"Volume {request.volume} abaixo do mínimo {min_vol}")
        if request.volume > max_vol:
            raise RiskError(f"Volume {request.volume} acima do máximo {max_vol}")
        
        # Verificar SL/TP lógico
        if request.sl and request.tp:
            if request.order_type == OrderType.BUY:
                if request.sl >= request.tp:
                    raise RiskError("SL deve ser menor que TP para ordem de compra")
            else:
                if request.sl <= request.tp:
                    raise RiskError("SL deve ser maior que TP para ordem de venda")
    
    async def _get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Obtém informações do símbolo com cache"""
        if symbol not in self._symbol_info_cache:
            self._symbol_info_cache[symbol] = await self._mt5.get_symbol_info(symbol)
        return self._symbol_info_cache[symbol]
    
    async def _normalize_volume(self, symbol: str, volume: float) -> float:
        """Normaliza volume para o step do símbolo"""
        info = await self._get_symbol_info(symbol)
        step = info.get("volume_step", 0.01)
        
        # Arredondar para o step
        normalized = round(volume / step) * step
        
        # Garantir mínimo
        min_vol = info.get("volume_min", 0.01)
        return max(normalized, min_vol)
    
    async def _normalize_price(self, symbol: str, price: float) -> float:
        """Normaliza preço para o digits do símbolo"""
        info = await self._get_symbol_info(symbol)
        digits = info.get("digits", 5)
        
        return round(price, digits)
    
    # ==========================================================================
    # CÁLCULO DE SL/TP
    # ==========================================================================
    
    async def calculate_sl(
        self,
        symbol: str,
        order_type: OrderType,
        entry_price: float,
        sl_pips: Optional[float] = None,
        sl_percent: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> float:
        """
        Calcula Stop Loss
        
        Args:
            symbol: Símbolo
            order_type: Tipo de ordem
            entry_price: Preço de entrada
            sl_pips: SL em pips
            sl_percent: SL em % do preço
            sl_price: Preço do SL direto
            
        Returns:
            Preço do SL
        """
        if sl_price:
            return await self._normalize_price(symbol, sl_price)
        
        info = await self._get_symbol_info(symbol)
        point = info.get("point", 0.00001)
        
        if sl_pips:
            pip_value = point * 10  # Para pares de 5 dígitos
            sl_distance = sl_pips * pip_value
        elif sl_percent:
            sl_distance = entry_price * (sl_percent / 100)
        else:
            raise ValueError("Deve especificar sl_pips, sl_percent ou sl_price")
        
        if order_type == OrderType.BUY:
            sl = entry_price - sl_distance
        else:
            sl = entry_price + sl_distance
        
        return await self._normalize_price(symbol, sl)
    
    async def calculate_tp(
        self,
        symbol: str,
        order_type: OrderType,
        entry_price: float,
        tp_pips: Optional[float] = None,
        tp_percent: Optional[float] = None,
        tp_price: Optional[float] = None,
        risk_reward: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> float:
        """
        Calcula Take Profit
        
        Args:
            symbol: Símbolo
            order_type: Tipo de ordem
            entry_price: Preço de entrada
            tp_pips: TP em pips
            tp_percent: TP em % do preço
            tp_price: Preço do TP direto
            risk_reward: Ratio risk/reward (requer sl_price)
            sl_price: Preço do SL (para risk_reward)
            
        Returns:
            Preço do TP
        """
        if tp_price:
            return await self._normalize_price(symbol, tp_price)
        
        info = await self._get_symbol_info(symbol)
        point = info.get("point", 0.00001)
        
        if risk_reward and sl_price:
            sl_distance = abs(entry_price - sl_price)
            tp_distance = sl_distance * risk_reward
        elif tp_pips:
            pip_value = point * 10
            tp_distance = tp_pips * pip_value
        elif tp_percent:
            tp_distance = entry_price * (tp_percent / 100)
        else:
            raise ValueError("Deve especificar tp_pips, tp_percent, tp_price ou risk_reward")
        
        if order_type == OrderType.BUY:
            tp = entry_price + tp_distance
        else:
            tp = entry_price - tp_distance
        
        return await self._normalize_price(symbol, tp)
    
    # ==========================================================================
    # GERENCIAMENTO DE POSIÇÕES
    # ==========================================================================
    
    async def modify_position(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None
    ) -> bool:
        """Modifica SL/TP de uma posição"""
        return await self._mt5.modify_position(ticket, sl, tp)
    
    async def close_position(
        self,
        ticket: int,
        volume: Optional[float] = None
    ) -> OrderResult:
        """
        Fecha uma posição
        
        Args:
            ticket: Ticket da posição
            volume: Volume a fechar (None = total)
            
        Returns:
            Resultado do fechamento
        """
        try:
            result = await self._mt5.close_position(ticket, volume)
            
            return OrderResult(
                success=True,
                ticket=result.get("ticket", ticket),
                volume=result.get("volume", 0),
                price=result.get("price", 0),
                message=f"Posição fechada com lucro/prejuízo de {result.get('profit', 0)}"
            )
        except Exception as e:
            return OrderResult(
                success=False,
                ticket=ticket,
                message=str(e)
            )
    
    async def close_partial(
        self,
        ticket: int,
        percent: float
    ) -> OrderResult:
        """
        Fecha percentual de uma posição
        
        Args:
            ticket: Ticket da posição
            percent: Percentual a fechar (0-100)
            
        Returns:
            Resultado
        """
        positions = await self._mt5.get_positions()
        position = next((p for p in positions if p.ticket == ticket), None)
        
        if not position:
            return OrderResult(
                success=False,
                ticket=ticket,
                message="Posição não encontrada"
            )
        
        close_volume = position.volume * (percent / 100)
        close_volume = await self._normalize_volume(position.symbol, close_volume)
        
        return await self.close_position(ticket, close_volume)
    
    # ==========================================================================
    # HELPERS
    # ==========================================================================
    
    async def calculate_position_size(
        self,
        symbol: str,
        risk_amount: float,
        sl_pips: float
    ) -> float:
        """
        Calcula tamanho da posição baseado no risco
        
        Args:
            symbol: Símbolo
            risk_amount: Valor em risco ($)
            sl_pips: Distância do SL em pips
            
        Returns:
            Volume/lots
        """
        info = await self._get_symbol_info(symbol)
        point = info.get("point", 0.00001)
        contract_size = info.get("trade_contract_size", 100000)
        
        # Pip value por lote
        pip_value = point * 10 * contract_size  # Simplificado, assumindo USD como conta
        
        # Volume
        volume = risk_amount / (sl_pips * pip_value)
        
        return await self._normalize_volume(symbol, volume)
    
    def get_order_history(
        self,
        limit: int = 100,
        symbol: Optional[str] = None
    ) -> List[OrderResult]:
        """Obtém histórico de ordens"""
        history = self._order_history[-limit:]
        
        if symbol:
            history = [
                o for o in history
                if o.request and o.request.symbol == symbol
            ]
        
        return history


# Factory
def create_order_manager(
    mt5_manager: Optional[MT5Manager] = None,
    config: Optional[Dict[str, Any]] = None
) -> OrderManager:
    """Cria nova instância do OrderManager"""
    return OrderManager(mt5_manager, config)
