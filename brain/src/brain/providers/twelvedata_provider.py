"""
VIRTUS Brain - TwelveData Provider
===================================

Provider para API TwelveData - dados técnicos e de mercado.

API Docs: https://twelvedata.com/docs
Features:
- Dados de preço em tempo real
- Indicadores técnicos
- Dados históricos OHLCV
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base_provider import MarketDataProvider
from ...core.logger import get_logger
from ...core.types import Timeframe
from ..cache import CacheManager
from ..budget import BudgetManager

logger = get_logger("twelvedata")


class TwelveDataProvider(MarketDataProvider):
    """
    Provider para TwelveData API.
    
    Principal fonte para:
    - Preços em tempo real (forex)
    - Indicadores técnicos (RSI, MACD, EMA, etc.)
    - Dados históricos OHLCV
    """
    
    PROVIDER_NAME = "twelvedata"
    BASE_URL = "https://api.twelvedata.com"
    
    # Mapeamento de símbolos
    SYMBOL_MAP = {
        'XAUUSD': 'XAU/USD',
        'EURUSD': 'EUR/USD',
        'GBPUSD': 'GBP/USD',
        'USDJPY': 'USD/JPY',
    }
    
    # Mapeamento de timeframes
    TIMEFRAME_MAP = {
        Timeframe.M1: '1min',
        Timeframe.M5: '5min',
        Timeframe.M15: '15min',
        Timeframe.M30: '30min',
        Timeframe.H1: '1h',
        Timeframe.H4: '4h',
        Timeframe.D1: '1day',
        Timeframe.W1: '1week',
        Timeframe.MN1: '1month',
    }
    
    def __init__(
        self,
        api_key: str,
        cache_manager: Optional[CacheManager] = None,
        budget_manager: Optional[BudgetManager] = None
    ):
        super().__init__(
            api_key=api_key,
            cache_manager=cache_manager,
            budget_manager=budget_manager
        )
    
    def _format_symbol(self, symbol: str) -> str:
        """Converte símbolo para formato TwelveData"""
        return self.SYMBOL_MAP.get(symbol, symbol)
    
    def _get_params(self, symbol: str) -> Dict[str, str]:
        """Parâmetros base"""
        return {
            'apikey': self.api_key,
            'symbol': self._format_symbol(symbol),
        }
    
    # ========================================================================
    # MÉTODOS PÚBLICOS
    # ========================================================================
    
    async def health_check(self) -> bool:
        """Verifica se a API está disponível"""
        try:
            params = {'apikey': self.api_key}
            await self.get('api_usage', params=params)
            return True
        except Exception as e:
            logger.error(f"TwelveData health check falhou: {e}")
            return False
    
    async def get_supported_symbols(self) -> List[str]:
        """Retorna símbolos suportados"""
        return list(self.SYMBOL_MAP.keys())
    
    async def get_price(self, symbol: str) -> Dict[str, Any]:
        """
        Busca preço atual de um símbolo.
        
        Args:
            symbol: Símbolo (ex: 'XAUUSD')
            
        Returns:
            Dict com preço atual
        """
        params = self._get_params(symbol)
        
        try:
            response = await self.get('price', params=params)
            
            return {
                'symbol': symbol,
                'price': float(response.get('price', 0)),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar preço TwelveData: {e}")
            return {}
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Busca quote completo de um símbolo.
        
        Args:
            symbol: Símbolo
            
        Returns:
            Dict com quote (open, high, low, close, volume, etc.)
        """
        params = self._get_params(symbol)
        
        try:
            response = await self.get('quote', params=params)
            
            return {
                'symbol': symbol,
                'name': response.get('name', ''),
                'open': float(response.get('open', 0)),
                'high': float(response.get('high', 0)),
                'low': float(response.get('low', 0)),
                'close': float(response.get('close', 0)),
                'previous_close': float(response.get('previous_close', 0)),
                'change': float(response.get('change', 0)),
                'percent_change': float(response.get('percent_change', 0)),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar quote TwelveData: {e}")
            return {}
    
    async def get_historical(
        self,
        symbol: str,
        interval: str = '1h',
        limit: int = 100,
        timeframe: Optional[Timeframe] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca dados históricos OHLCV.
        
        Args:
            symbol: Símbolo
            interval: Intervalo (1min, 5min, 1h, 1day, etc.)
            limit: Número de candles
            timeframe: Enum Timeframe (alternativa a interval)
            
        Returns:
            Lista de candles
        """
        params = self._get_params(symbol)
        
        if timeframe:
            params['interval'] = self.TIMEFRAME_MAP.get(timeframe, '1h')
        else:
            params['interval'] = interval
        
        params['outputsize'] = str(limit)
        
        try:
            response = await self.get('time_series', params=params)
            
            candles = []
            for item in response.get('values', []):
                candles.append({
                    'timestamp': datetime.fromisoformat(item['datetime']),
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': float(item.get('volume', 0))
                })
            
            # Inverte para ordem cronológica
            candles.reverse()
            
            logger.debug(f"TwelveData: {len(candles)} candles de {symbol}")
            return candles
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico TwelveData: {e}")
            return []
    
    async def get_rsi(
        self,
        symbol: str,
        interval: str = '1h',
        period: int = 14,
        limit: int = 1
    ) -> Optional[float]:
        """
        Calcula RSI.
        
        Args:
            symbol: Símbolo
            interval: Intervalo
            period: Período do RSI
            limit: Número de valores (1 = apenas atual)
            
        Returns:
            Valor do RSI
        """
        params = self._get_params(symbol)
        params['interval'] = interval
        params['time_period'] = str(period)
        params['outputsize'] = str(limit)
        
        try:
            response = await self.get('rsi', params=params)
            
            values = response.get('values', [])
            if values:
                return float(values[0]['rsi'])
            return None
            
        except Exception as e:
            logger.error(f"Erro ao calcular RSI TwelveData: {e}")
            return None
    
    async def get_macd(
        self,
        symbol: str,
        interval: str = '1h',
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        limit: int = 1
    ) -> Optional[Dict[str, float]]:
        """
        Calcula MACD.
        
        Returns:
            Dict com macd, macd_signal, macd_hist
        """
        params = self._get_params(symbol)
        params['interval'] = interval
        params['fast_period'] = str(fast_period)
        params['slow_period'] = str(slow_period)
        params['signal_period'] = str(signal_period)
        params['outputsize'] = str(limit)
        
        try:
            response = await self.get('macd', params=params)
            
            values = response.get('values', [])
            if values:
                return {
                    'macd': float(values[0]['macd']),
                    'signal': float(values[0]['macd_signal']),
                    'histogram': float(values[0]['macd_hist'])
                }
            return None
            
        except Exception as e:
            logger.error(f"Erro ao calcular MACD TwelveData: {e}")
            return None
    
    async def get_ema(
        self,
        symbol: str,
        interval: str = '1h',
        period: int = 20,
        limit: int = 1
    ) -> Optional[float]:
        """
        Calcula EMA.
        
        Args:
            symbol: Símbolo
            interval: Intervalo
            period: Período da EMA
            
        Returns:
            Valor da EMA
        """
        params = self._get_params(symbol)
        params['interval'] = interval
        params['time_period'] = str(period)
        params['outputsize'] = str(limit)
        
        try:
            response = await self.get('ema', params=params)
            
            values = response.get('values', [])
            if values:
                return float(values[0]['ema'])
            return None
            
        except Exception as e:
            logger.error(f"Erro ao calcular EMA TwelveData: {e}")
            return None
    
    async def get_bollinger_bands(
        self,
        symbol: str,
        interval: str = '1h',
        period: int = 20,
        std_dev: float = 2.0,
        limit: int = 1
    ) -> Optional[Dict[str, float]]:
        """
        Calcula Bollinger Bands.
        
        Returns:
            Dict com upper_band, middle_band, lower_band
        """
        params = self._get_params(symbol)
        params['interval'] = interval
        params['time_period'] = str(period)
        params['sd'] = str(std_dev)
        params['outputsize'] = str(limit)
        
        try:
            response = await self.get('bbands', params=params)
            
            values = response.get('values', [])
            if values:
                return {
                    'upper': float(values[0]['upper_band']),
                    'middle': float(values[0]['middle_band']),
                    'lower': float(values[0]['lower_band'])
                }
            return None
            
        except Exception as e:
            logger.error(f"Erro ao calcular BB TwelveData: {e}")
            return None
    
    async def get_atr(
        self,
        symbol: str,
        interval: str = '1h',
        period: int = 14,
        limit: int = 1
    ) -> Optional[float]:
        """
        Calcula ATR.
        
        Returns:
            Valor do ATR
        """
        params = self._get_params(symbol)
        params['interval'] = interval
        params['time_period'] = str(period)
        params['outputsize'] = str(limit)
        
        try:
            response = await self.get('atr', params=params)
            
            values = response.get('values', [])
            if values:
                return float(values[0]['atr'])
            return None
            
        except Exception as e:
            logger.error(f"Erro ao calcular ATR TwelveData: {e}")
            return None
    
    async def get_all_indicators(
        self,
        symbol: str,
        interval: str = '1h'
    ) -> Dict[str, Any]:
        """
        Busca todos os indicadores principais de uma vez.
        
        Returns:
            Dict com RSI, MACD, EMA, BB, ATR
        """
        # Executa em paralelo
        results = await asyncio.gather(
            self.get_rsi(symbol, interval),
            self.get_macd(symbol, interval),
            self.get_ema(symbol, interval, period=20),
            self.get_ema(symbol, interval, period=50),
            self.get_bollinger_bands(symbol, interval),
            self.get_atr(symbol, interval),
            return_exceptions=True
        )
        
        return {
            'symbol': symbol,
            'interval': interval,
            'timestamp': datetime.now(),
            'rsi': results[0] if not isinstance(results[0], Exception) else None,
            'macd': results[1] if not isinstance(results[1], Exception) else None,
            'ema_20': results[2] if not isinstance(results[2], Exception) else None,
            'ema_50': results[3] if not isinstance(results[3], Exception) else None,
            'bollinger': results[4] if not isinstance(results[4], Exception) else None,
            'atr': results[5] if not isinstance(results[5], Exception) else None,
        }
