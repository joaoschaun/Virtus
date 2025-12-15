"""
VIRTUS MT5 - Data Service
==========================

Serviço para obter dados de mercado do MT5.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

from ..core.logger import get_logger
from ..core.config import get_config
from ..core.types import Timeframe, OHLC
from ..core.exceptions import MT5DataError
from .mt5_connection import MT5Connection, get_mt5_connection

logger = get_logger("mt5_data")


# Mapeamento de Timeframes
TIMEFRAME_MAP = {
    Timeframe.M1: mt5.TIMEFRAME_M1,
    Timeframe.M5: mt5.TIMEFRAME_M5,
    Timeframe.M15: mt5.TIMEFRAME_M15,
    Timeframe.M30: mt5.TIMEFRAME_M30,
    Timeframe.H1: mt5.TIMEFRAME_H1,
    Timeframe.H4: mt5.TIMEFRAME_H4,
    Timeframe.D1: mt5.TIMEFRAME_D1,
    Timeframe.W1: mt5.TIMEFRAME_W1,
    Timeframe.MN1: mt5.TIMEFRAME_MN1,
}


class MT5DataService:
    """
    Serviço para obter dados de mercado do MT5.
    
    Fornece:
    - Preços em tempo real
    - Dados históricos (OHLCV)
    - Ticks
    - Informações de spread
    """
    
    _instance: Optional['MT5DataService'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._connection: Optional[MT5Connection] = None
    
    @classmethod
    async def get_instance(cls) -> 'MT5DataService':
        """Retorna instância singleton"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._instance._connection = await get_mt5_connection()
            return cls._instance
    
    async def _ensure_connected(self):
        """Garante conexão com MT5"""
        if not self._connection or not self._connection.is_connected:
            self._connection = await get_mt5_connection()
            if not await self._connection.ensure_connected():
                raise MT5DataError("Não foi possível conectar ao MT5")
    
    # ========================================================================
    # PREÇOS EM TEMPO REAL
    # ========================================================================
    
    async def get_price(self, symbol: str) -> Dict[str, Any]:
        """
        Obtém preço atual de um símbolo.
        
        Args:
            symbol: Símbolo
            
        Returns:
            Dict com bid, ask, last, spread
        """
        await self._ensure_connected()
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5DataError(f"Não foi possível obter preço de {symbol}")
        
        info = mt5.symbol_info(symbol)
        point = info.point if info else 0.00001
        
        return {
            'symbol': symbol,
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last,
            'volume': tick.volume,
            'time': datetime.fromtimestamp(tick.time),
            'spread': round((tick.ask - tick.bid) / point),
            'spread_points': tick.ask - tick.bid,
        }
    
    async def get_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Obtém preços de múltiplos símbolos.
        
        Args:
            symbols: Lista de símbolos
            
        Returns:
            Dict com preços por símbolo
        """
        prices = {}
        for symbol in symbols:
            try:
                prices[symbol] = await self.get_price(symbol)
            except Exception as e:
                logger.warning(f"Erro ao obter preço de {symbol}: {e}")
                prices[symbol] = None
        return prices
    
    # ========================================================================
    # DADOS HISTÓRICOS
    # ========================================================================
    
    async def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        count: int = 100,
        start_pos: int = 0
    ) -> pd.DataFrame:
        """
        Obtém candles históricos.
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            count: Número de candles
            start_pos: Posição inicial (0 = mais recente)
            
        Returns:
            DataFrame com OHLCV
        """
        await self._ensure_connected()
        
        mt5_timeframe = TIMEFRAME_MAP.get(timeframe, mt5.TIMEFRAME_H1)
        
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, start_pos, count)
        if rates is None or len(rates) == 0:
            raise MT5DataError(f"Não foi possível obter candles de {symbol}")
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # Renomeia colunas para padrão
        df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tick_volume': 'volume',
            'spread': 'spread',
            'real_volume': 'real_volume'
        }, inplace=True)
        
        return df
    
    async def get_candles_range(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Obtém candles em um período específico.
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            start_time: Data/hora inicial
            end_time: Data/hora final (default: agora)
            
        Returns:
            DataFrame com OHLCV
        """
        await self._ensure_connected()
        
        mt5_timeframe = TIMEFRAME_MAP.get(timeframe, mt5.TIMEFRAME_H1)
        end_time = end_time or datetime.now()
        
        rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_time, end_time)
        if rates is None or len(rates) == 0:
            raise MT5DataError(f"Não foi possível obter candles de {symbol}")
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        return df
    
    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: Timeframe
    ) -> Dict[str, Any]:
        """
        Obtém último candle formado.
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            
        Returns:
            Dict com OHLCV do último candle
        """
        df = await self.get_candles(symbol, timeframe, count=2)
        if len(df) < 2:
            raise MT5DataError(f"Dados insuficientes para {symbol}")
        
        # Retorna penúltimo (último completo)
        candle = df.iloc[-2]
        return {
            'time': candle.name,
            'open': candle['open'],
            'high': candle['high'],
            'low': candle['low'],
            'close': candle['close'],
            'volume': candle['volume'],
        }
    
    # ========================================================================
    # TICKS
    # ========================================================================
    
    async def get_ticks(
        self,
        symbol: str,
        count: int = 100
    ) -> pd.DataFrame:
        """
        Obtém últimos ticks.
        
        Args:
            symbol: Símbolo
            count: Número de ticks
            
        Returns:
            DataFrame com ticks
        """
        await self._ensure_connected()
        
        ticks = mt5.copy_ticks_from(symbol, datetime.now(), count, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            raise MT5DataError(f"Não foi possível obter ticks de {symbol}")
        
        df = pd.DataFrame(ticks)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        return df
    
    # ========================================================================
    # SPREAD E VOLATILIDADE
    # ========================================================================
    
    async def get_current_spread(self, symbol: str) -> int:
        """Obtém spread atual em points"""
        price = await self.get_price(symbol)
        return price.get('spread', 0)
    
    async def get_average_spread(
        self,
        symbol: str,
        period_minutes: int = 60
    ) -> float:
        """
        Calcula spread médio em um período.
        
        Args:
            symbol: Símbolo
            period_minutes: Período em minutos
            
        Returns:
            Spread médio
        """
        try:
            df = await self.get_candles(
                symbol,
                Timeframe.M1,
                count=period_minutes
            )
            return df['spread'].mean()
        except Exception as e:
            logger.warning(f"Erro ao calcular spread médio: {e}")
            return 0.0
    
    async def get_volatility(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.H1,
        periods: int = 14
    ) -> float:
        """
        Calcula volatilidade (ATR simplificado).
        
        Args:
            symbol: Símbolo
            timeframe: Timeframe
            periods: Períodos para cálculo
            
        Returns:
            ATR médio
        """
        try:
            df = await self.get_candles(symbol, timeframe, count=periods + 1)
            
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            # True Range
            tr1 = high[1:] - low[1:]
            tr2 = np.abs(high[1:] - close[:-1])
            tr3 = np.abs(low[1:] - close[:-1])
            
            tr = np.maximum(tr1, np.maximum(tr2, tr3))
            atr = np.mean(tr)
            
            return float(atr)
            
        except Exception as e:
            logger.warning(f"Erro ao calcular volatilidade: {e}")
            return 0.0
    
    # ========================================================================
    # INFORMAÇÕES DE SÍMBOLO
    # ========================================================================
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Obtém informações detalhadas de um símbolo.
        
        Args:
            symbol: Símbolo
            
        Returns:
            Dict com todas as informações
        """
        await self._ensure_connected()
        
        info = mt5.symbol_info(symbol)
        if info is None:
            raise MT5DataError(f"Símbolo {symbol} não encontrado")
        
        return {
            'name': info.name,
            'description': info.description,
            'path': info.path,
            'point': info.point,
            'digits': info.digits,
            'spread': info.spread,
            'spread_float': info.spread_float,
            'trade_contract_size': info.trade_contract_size,
            'trade_tick_value': info.trade_tick_value,
            'trade_tick_size': info.trade_tick_size,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
            'volume_step': info.volume_step,
            'margin_initial': info.margin_initial,
            'trade_mode': info.trade_mode,
            'bid': info.bid,
            'ask': info.ask,
        }
    
    async def get_pip_value(self, symbol: str, volume: float = 1.0) -> float:
        """
        Calcula valor do pip para um volume.
        
        Args:
            symbol: Símbolo
            volume: Volume em lotes
            
        Returns:
            Valor do pip na moeda da conta
        """
        await self._ensure_connected()
        
        info = mt5.symbol_info(symbol)
        if info is None:
            return 0.0
        
        # Pip value básico
        tick_value = info.trade_tick_value
        tick_size = info.trade_tick_size
        point = info.point
        
        # Para forex pairs
        pip_size = point * 10 if info.digits == 5 or info.digits == 3 else point
        pip_value = (pip_size / tick_size) * tick_value * volume
        
        return pip_value


# Helper
async def get_mt5_data() -> MT5DataService:
    """Retorna instância do serviço de dados"""
    return await MT5DataService.get_instance()
