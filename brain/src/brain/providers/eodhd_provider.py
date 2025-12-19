"""
VIRTUS Brain - EODHD Provider
==============================

Provider completo para EODHD Financial APIs.
Integração com dados de mercado, fundamentais, calendário econômico e notícias.

API: https://eodhd.com/financial-apis/
Documentação: https://eodhd.com/financial-apis/api-for-historical-data-and-volumes/

Recursos disponíveis:
- Market Data (EOD, Intraday, Live, Websockets)
- Fundamental Data (Stocks, ETFs, Crypto)
- Economic Calendar & Earnings
- Financial News & Sentiment
- Technical Indicators
- Macro Indicators
- Exchange & Instruments Info
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

from .base_provider import BaseProvider
from ...core.logger import get_logger
from ...core.types import (
    NewsItem, NewsImpact, SentimentLevel,
    EconomicEvent, MarketSentiment
)
from ...core.exceptions import (
    APIError, APIResponseError, NoDataError
)

logger = get_logger("eodhd")


class EODHDInterval(str, Enum):
    """Intervalos suportados pelo EODHD"""
    MIN_1 = "1m"
    MIN_5 = "5m"
    HOUR_1 = "1h"
    DAILY = "d"
    WEEKLY = "w"
    MONTHLY = "m"


class EODHDExchange(str, Enum):
    """Principais exchanges suportadas"""
    US = "US"           # USA Stocks
    FOREX = "FOREX"     # Forex pairs
    CC = "CC"           # Cryptocurrencies
    INDX = "INDX"       # Indices
    COMM = "COMM"       # Commodities
    LSE = "LSE"         # London
    TSE = "TSE"         # Tokyo
    XETRA = "XETRA"     # Germany
    AS = "AS"           # Amsterdam
    PA = "PA"           # Paris
    MI = "MI"           # Milan
    SA = "SA"           # Brazil (B3)
    SN = "SN"           # Chile
    MX = "MX"           # Mexico


class EODHDProvider(BaseProvider):
    """
    Provider completo para EODHD Financial APIs.
    
    Implementa todos os recursos disponíveis:
    - Market Data (EOD, Intraday, Live)
    - Fundamental Data
    - Economic Calendar
    - News & Sentiment
    - Technical Indicators
    - Macro Data
    
    Uso:
        provider = EODHDProvider(api_key="your_key")
        
        # Dados históricos
        candles = await provider.get_eod_data("AAPL.US")
        
        # Intraday
        intraday = await provider.get_intraday_data("EURUSD.FOREX", "5m")
        
        # Calendário econômico
        events = await provider.get_economic_calendar()
        
        # Notícias
        news = await provider.get_news(["AAPL", "GOOGL"])
    """
    
    PROVIDER_NAME = "eodhd"
    BASE_URL = "https://eodhd.com/api"
    
    # Endpoints disponíveis
    ENDPOINTS = {
        # Market Data
        'eod': '/eod/{symbol}',
        'intraday': '/intraday/{symbol}',
        'real_time': '/real-time/{symbol}',
        'live': '/live/{symbol}',
        'options': '/options/{symbol}',
        
        # Historical Data
        'historical': '/eod/{symbol}',
        'splits': '/splits/{symbol}',
        'dividends': '/div/{symbol}',
        
        # Fundamental Data
        'fundamentals': '/fundamentals/{symbol}',
        'bulk_fundamentals': '/bulk-fundamentals/{exchange}',
        'insider_transactions': '/insider-transactions',
        
        # Exchanges & Symbols
        'exchanges': '/exchanges-list/',
        'exchange_symbols': '/exchange-symbol-list/{exchange}',
        'search': '/search/{query}',
        
        # Calendar
        'earnings': '/calendar/earnings',
        'ipos': '/calendar/ipos',
        'trends': '/calendar/trends',
        'economic_events': '/economic-events',
        
        # News & Sentiment
        'news': '/news',
        'sentiment': '/sentiments',
        'tweets': '/tweets',
        
        # Technical Indicators
        'technical': '/technical/{symbol}',
        
        # Macro Data
        'macro': '/macro-indicator/{country}',
        
        # Bonds
        'bonds': '/bond-fundamentals/{isin}',
    }
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self._symbol_cache: Dict[str, List[str]] = {}
    
    def _build_url(self, endpoint: str, **kwargs) -> str:
        """Constrói URL com parâmetros de path"""
        formatted_endpoint = endpoint.format(**kwargs) if kwargs else endpoint
        return f"{self.BASE_URL}{formatted_endpoint}"
    
    def _add_auth(self, params: Dict) -> Dict:
        """Adiciona autenticação aos parâmetros"""
        params['api_token'] = self.api_key
        params['fmt'] = 'json'
        return params
    
    async def _fetch(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        cache_key: Optional[str] = None,
        cache_ttl: int = 300,
        **path_params
    ) -> Any:
        """
        Faz requisição à API com cache e tratamento de erros.
        
        Args:
            endpoint: Endpoint da API
            params: Query parameters
            cache_key: Chave para cache
            cache_ttl: TTL do cache em segundos
            **path_params: Parâmetros para formatação do endpoint
        """
        # Verifica cache
        if cache_key and self.cache_manager:
            cached = await self.cache_manager.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached
        
        # Prepara request - endpoint é passado diretamente para _make_request
        # que vai chamar _build_url internamente
        formatted_endpoint = endpoint.format(**path_params) if path_params else endpoint
        params = self._add_auth(params or {})
        
        try:
            response = await self._make_request('GET', formatted_endpoint, params=params)
            
            # Salva no cache
            if cache_key and self.cache_manager:
                await self.cache_manager.set(cache_key, response, ttl_override=cache_ttl)
            
            return response
            
        except Exception as e:
            logger.error(f"EODHD API error: {e}")
            raise
    
    # =========================================================================
    # MARKET DATA - EOD (End of Day)
    # =========================================================================
    
    async def get_eod_data(
        self,
        symbol: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        period: str = 'd'
    ) -> List[Dict[str, Any]]:
        """
        Obtém dados históricos End-of-Day.
        
        Args:
            symbol: Símbolo com exchange (ex: AAPL.US, EURUSD.FOREX)
            from_date: Data inicial
            to_date: Data final
            period: 'd' (daily), 'w' (weekly), 'm' (monthly)
            
        Returns:
            Lista de candles com open, high, low, close, volume
        """
        params = {'period': period}
        
        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%d')
        
        cache_key = f"eodhd:eod:{symbol}:{period}"
        
        data = await self._fetch(
            self.ENDPOINTS['eod'],
            params=params,
            cache_key=cache_key,
            cache_ttl=3600,  # 1 hora
            symbol=symbol
        )
        
        return data if isinstance(data, list) else []
    
    async def get_live_price(self, symbol: str) -> Dict[str, Any]:
        """
        Obtém preço em tempo real (delayed 15-20min para free tier).
        
        Args:
            symbol: Símbolo com exchange
            
        Returns:
            Dict com preço atual, open, high, low, volume
        """
        cache_key = f"eodhd:live:{symbol}"
        
        return await self._fetch(
            self.ENDPOINTS['real_time'],
            cache_key=cache_key,
            cache_ttl=60,  # 1 minuto
            symbol=symbol
        )
    
    async def get_bulk_live_prices(
        self,
        symbols: List[str],
        exchange: str = "US"
    ) -> List[Dict[str, Any]]:
        """
        Obtém preços em tempo real para múltiplos símbolos.
        
        Args:
            symbols: Lista de símbolos
            exchange: Exchange code
            
        Returns:
            Lista de preços
        """
        params = {'s': ','.join(symbols)}
        cache_key = f"eodhd:bulk_live:{exchange}:{len(symbols)}"
        
        return await self._fetch(
            f'/real-time/{exchange}',
            params=params,
            cache_key=cache_key,
            cache_ttl=60
        )
    
    # =========================================================================
    # MARKET DATA - INTRADAY
    # =========================================================================
    
    async def get_intraday_data(
        self,
        symbol: str,
        interval: str = "5m",
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém dados intraday.
        
        Args:
            symbol: Símbolo com exchange
            interval: '1m', '5m', '1h'
            from_timestamp: Unix timestamp inicial
            to_timestamp: Unix timestamp final
            
        Returns:
            Lista de candles intraday
        """
        params = {'interval': interval}
        
        if from_timestamp:
            params['from'] = from_timestamp
        if to_timestamp:
            params['to'] = to_timestamp
        
        cache_key = f"eodhd:intraday:{symbol}:{interval}"
        
        return await self._fetch(
            self.ENDPOINTS['intraday'],
            params=params,
            cache_key=cache_key,
            cache_ttl=300,  # 5 minutos
            symbol=symbol
        )
    
    # =========================================================================
    # FUNDAMENTAL DATA
    # =========================================================================
    
    async def get_fundamentals(
        self,
        symbol: str,
        filter_field: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtém dados fundamentalistas completos.
        
        Args:
            symbol: Símbolo com exchange
            filter_field: Campo específico (General, Highlights, Valuation, etc)
            
        Returns:
            Dict com dados fundamentalistas
        """
        params = {}
        if filter_field:
            params['filter'] = filter_field
        
        cache_key = f"eodhd:fundamentals:{symbol}"
        
        return await self._fetch(
            self.ENDPOINTS['fundamentals'],
            params=params,
            cache_key=cache_key,
            cache_ttl=86400,  # 24 horas
            symbol=symbol
        )
    
    async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Obtém perfil da empresa"""
        return await self.get_fundamentals(symbol, filter_field='General')
    
    async def get_financials(self, symbol: str) -> Dict[str, Any]:
        """Obtém dados financeiros (balanço, DRE, fluxo de caixa)"""
        return await self.get_fundamentals(symbol, filter_field='Financials')
    
    async def get_valuation(self, symbol: str) -> Dict[str, Any]:
        """Obtém métricas de valuation (P/E, P/B, EV/EBITDA)"""
        return await self.get_fundamentals(symbol, filter_field='Valuation')
    
    async def get_dividends(
        self,
        symbol: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém histórico de dividendos.
        
        Args:
            symbol: Símbolo com exchange
            from_date: Data inicial
            to_date: Data final
            
        Returns:
            Lista de dividendos
        """
        params = {}
        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%d')
        
        cache_key = f"eodhd:dividends:{symbol}"
        
        return await self._fetch(
            self.ENDPOINTS['dividends'],
            params=params,
            cache_key=cache_key,
            cache_ttl=86400,
            symbol=symbol
        )
    
    async def get_splits(self, symbol: str) -> List[Dict[str, Any]]:
        """Obtém histórico de splits"""
        cache_key = f"eodhd:splits:{symbol}"
        
        return await self._fetch(
            self.ENDPOINTS['splits'],
            cache_key=cache_key,
            cache_ttl=86400,
            symbol=symbol
        )
    
    # =========================================================================
    # ECONOMIC CALENDAR
    # =========================================================================
    
    async def get_economic_events(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        country: Optional[str] = None,
        comparison: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém eventos econômicos do calendário.
        
        Args:
            from_date: Data inicial
            to_date: Data final
            country: Código do país (US, GB, EU, etc)
            comparison: 'mom' (month over month) ou 'yoy' (year over year)
            
        Returns:
            Lista de eventos econômicos
        """
        params = {}
        
        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%d')
        if country:
            params['country'] = country
        if comparison:
            params['comparison'] = comparison
        
        cache_key = f"eodhd:economic_events:{country or 'all'}"
        
        data = await self._fetch(
            self.ENDPOINTS['economic_events'],
            params=params,
            cache_key=cache_key,
            cache_ttl=3600
        )
        
        return data if isinstance(data, list) else []
    
    async def get_economic_calendar(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        symbols: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """
        Interface padrão para calendário econômico.
        Implementa CalendarProvider.
        
        Returns:
            Lista de EconomicEvent formatados
        """
        events = await self.get_economic_events(from_date, to_date)
        
        result = []
        for event in events:
            try:
                # Determina impacto baseado na mudança
                actual = event.get('actual')
                previous = event.get('previous')
                estimate = event.get('estimate')
                
                impact = self._calculate_event_impact(actual, previous, estimate)
                
                result.append(EconomicEvent(
                    title=event.get('event', 'Unknown Event'),
                    country=event.get('country', 'Unknown'),
                    datetime=datetime.fromisoformat(event.get('date', '')),
                    impact=impact,
                    actual=actual,
                    forecast=estimate,
                    previous=previous,
                    source='eodhd'
                ))
            except Exception as e:
                logger.warning(f"Error parsing event: {e}")
                continue
        
        return result
    
    def _calculate_event_impact(
        self,
        actual: Optional[float],
        previous: Optional[float],
        estimate: Optional[float]
    ) -> NewsImpact:
        """Calcula impacto do evento baseado nos valores"""
        if actual is None:
            return NewsImpact.LOW
        
        try:
            if estimate is not None:
                diff = abs(float(actual) - float(estimate))
                if diff > 0.5:
                    return NewsImpact.HIGH
                elif diff > 0.2:
                    return NewsImpact.MEDIUM
            return NewsImpact.LOW
        except:
            return NewsImpact.LOW
    
    async def get_earnings_calendar(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém calendário de earnings.
        
        Args:
            from_date: Data inicial
            to_date: Data final
            symbols: Lista de símbolos para filtrar
            
        Returns:
            Lista de earnings events
        """
        params = {}
        
        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%d')
        if symbols:
            params['symbols'] = ','.join(symbols)
        
        cache_key = f"eodhd:earnings:{symbols or 'all'}"
        
        return await self._fetch(
            self.ENDPOINTS['earnings'],
            params=params,
            cache_key=cache_key,
            cache_ttl=3600
        )
    
    async def get_ipos_calendar(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Obtém calendário de IPOs"""
        params = {}
        
        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%d')
        
        cache_key = "eodhd:ipos"
        
        return await self._fetch(
            self.ENDPOINTS['ipos'],
            params=params,
            cache_key=cache_key,
            cache_ttl=3600
        )
    
    # =========================================================================
    # NEWS & SENTIMENT
    # =========================================================================
    
    async def get_news(
        self,
        symbols: Optional[List[str]] = None,
        tag: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtém notícias financeiras.
        
        Args:
            symbols: Lista de símbolos (ex: ['AAPL.US', 'MSFT.US'])
            tag: Tag para filtrar (ex: 'fed', 'crypto')
            from_date: Data inicial
            to_date: Data final
            limit: Máximo de resultados
            offset: Offset para paginação
            
        Returns:
            Lista de notícias
        """
        params = {
            'limit': limit,
            'offset': offset
        }
        
        if symbols:
            params['s'] = ','.join(symbols)
        if tag:
            params['t'] = tag
        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%d')
        
        cache_key = f"eodhd:news:{symbols or tag or 'all'}:{offset}"
        
        return await self._fetch(
            self.ENDPOINTS['news'],
            params=params,
            cache_key=cache_key,
            cache_ttl=900  # 15 minutos
        )
    
    async def get_formatted_news(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[NewsItem]:
        """
        Obtém notícias formatadas como NewsItem.
        Implementa NewsProvider.
        
        Returns:
            Lista de NewsItem
        """
        news_data = await self.get_news(symbols=symbols, limit=limit)
        
        result = []
        for article in news_data:
            try:
                # Determina impacto baseado em keywords
                title = article.get('title', '')
                impact = self._determine_news_impact(title)
                
                result.append(NewsItem(
                    title=title,
                    content=article.get('content', ''),
                    source=article.get('link', 'eodhd'),
                    published_at=datetime.fromisoformat(
                        article.get('date', datetime.now().isoformat())
                    ),
                    symbols=article.get('symbols', []),
                    sentiment_score=article.get('sentiment', {}).get('polarity', 0),
                    impact=impact,
                    url=article.get('link', '')
                ))
            except Exception as e:
                logger.warning(f"Error parsing news: {e}")
                continue
        
        return result
    
    def _determine_news_impact(self, title: str) -> NewsImpact:
        """Determina impacto da notícia baseado em keywords"""
        title_lower = title.lower()
        
        high_impact_keywords = [
            'fed', 'fomc', 'rate', 'inflation', 'crash', 'surge',
            'war', 'crisis', 'emergency', 'recession', 'default'
        ]
        
        medium_impact_keywords = [
            'earnings', 'profit', 'revenue', 'gdp', 'employment',
            'trade', 'tariff', 'deal', 'merger', 'acquisition'
        ]
        
        for keyword in high_impact_keywords:
            if keyword in title_lower:
                return NewsImpact.HIGH
        
        for keyword in medium_impact_keywords:
            if keyword in title_lower:
                return NewsImpact.MEDIUM
        
        return NewsImpact.LOW
    
    async def get_sentiment(
        self,
        symbol: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Obtém análise de sentimento para um símbolo.
        
        Args:
            symbol: Símbolo (ex: AAPL.US)
            from_date: Data inicial
            to_date: Data final
            
        Returns:
            Dict com dados de sentimento
        """
        params = {'s': symbol}
        
        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%d')
        
        cache_key = f"eodhd:sentiment:{symbol}"
        
        return await self._fetch(
            self.ENDPOINTS['sentiment'],
            params=params,
            cache_key=cache_key,
            cache_ttl=600  # 10 minutos
        )
    
    async def get_market_sentiment(self, symbol: str) -> MarketSentiment:
        """
        Obtém sentimento formatado como MarketSentiment.
        
        Returns:
            MarketSentiment com score e nível
        """
        data = await self.get_sentiment(symbol)
        
        if not data:
            return MarketSentiment(
                symbol=symbol,
                score=0,
                level=SentimentLevel.NEUTRAL,
                source='eodhd'
            )
        
        # Calcula score médio
        scores = [item.get('normalized', 0) for item in data if 'normalized' in item]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Determina nível
        if avg_score > 0.3:
            level = SentimentLevel.BULLISH
        elif avg_score > 0.1:
            level = SentimentLevel.SLIGHTLY_BULLISH
        elif avg_score < -0.3:
            level = SentimentLevel.BEARISH
        elif avg_score < -0.1:
            level = SentimentLevel.SLIGHTLY_BEARISH
        else:
            level = SentimentLevel.NEUTRAL
        
        return MarketSentiment(
            symbol=symbol,
            score=avg_score,
            level=level,
            source='eodhd'
        )
    
    # =========================================================================
    # TECHNICAL INDICATORS
    # =========================================================================
    
    async def get_technical_indicator(
        self,
        symbol: str,
        function: str,
        period: int = 14,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Obtém indicador técnico calculado pela API.
        
        Args:
            symbol: Símbolo com exchange
            function: Nome do indicador (sma, ema, rsi, macd, bbands, etc)
            period: Período do indicador
            from_date: Data inicial
            to_date: Data final
            **kwargs: Parâmetros adicionais do indicador
            
        Returns:
            Lista de valores do indicador
        
        Indicadores disponíveis:
            - sma, ema, wma: Médias móveis
            - rsi: Relative Strength Index
            - macd: Moving Average Convergence Divergence
            - bbands: Bollinger Bands
            - stoch: Stochastic Oscillator
            - atr: Average True Range
            - adx: Average Directional Index
            - cci: Commodity Channel Index
            - obv: On Balance Volume
            - sar: Parabolic SAR
            - williams: Williams %R
        """
        params = {
            'function': function.lower(),
            'period': period
        }
        params.update(kwargs)
        
        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')
        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%d')
        
        cache_key = f"eodhd:technical:{symbol}:{function}:{period}"
        
        return await self._fetch(
            self.ENDPOINTS['technical'],
            params=params,
            cache_key=cache_key,
            cache_ttl=300,  # 5 minutos
            symbol=symbol
        )
    
    async def get_sma(
        self,
        symbol: str,
        period: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Simple Moving Average"""
        return await self.get_technical_indicator(symbol, 'sma', period, **kwargs)
    
    async def get_ema(
        self,
        symbol: str,
        period: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Exponential Moving Average"""
        return await self.get_technical_indicator(symbol, 'ema', period, **kwargs)
    
    async def get_rsi(
        self,
        symbol: str,
        period: int = 14,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Relative Strength Index"""
        return await self.get_technical_indicator(symbol, 'rsi', period, **kwargs)
    
    async def get_macd(
        self,
        symbol: str,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Moving Average Convergence Divergence"""
        return await self.get_technical_indicator(
            symbol, 'macd', 
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
            **kwargs
        )
    
    async def get_bbands(
        self,
        symbol: str,
        period: int = 20,
        stddev: float = 2.0,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Bollinger Bands"""
        return await self.get_technical_indicator(
            symbol, 'bbands',
            period=period,
            stddev=stddev,
            **kwargs
        )
    
    async def get_atr(
        self,
        symbol: str,
        period: int = 14,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Average True Range"""
        return await self.get_technical_indicator(symbol, 'atr', period, **kwargs)
    
    async def get_stochastic(
        self,
        symbol: str,
        fast_k: int = 14,
        slow_k: int = 3,
        slow_d: int = 3,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Stochastic Oscillator"""
        return await self.get_technical_indicator(
            symbol, 'stoch',
            fast_k=fast_k,
            slow_k=slow_k,
            slow_d=slow_d,
            **kwargs
        )
    
    async def get_adx(
        self,
        symbol: str,
        period: int = 14,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Average Directional Index"""
        return await self.get_technical_indicator(symbol, 'adx', period, **kwargs)
    
    # =========================================================================
    # MACRO INDICATORS
    # =========================================================================
    
    async def get_macro_indicator(
        self,
        country: str,
        indicator: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém indicadores macroeconômicos de um país.
        
        Args:
            country: Código do país (USA, BRA, GBR, DEU, etc)
            indicator: Indicador específico (gdp, inflation, unemployment, etc)
            
        Returns:
            Lista de valores do indicador
        
        Indicadores disponíveis:
            - gdp_growth_annual: Crescimento anual do PIB
            - inflation_consumer_prices_annual: Inflação anual
            - real_interest_rate: Taxa de juros real
            - unemployment_rate: Taxa de desemprego
            - current_account_balance: Saldo em conta corrente
            - government_debt_to_gdp: Dívida pública / PIB
        """
        params = {}
        if indicator:
            params['indicator'] = indicator
        
        cache_key = f"eodhd:macro:{country}:{indicator or 'all'}"
        
        return await self._fetch(
            self.ENDPOINTS['macro'],
            params=params,
            cache_key=cache_key,
            cache_ttl=86400,  # 24 horas
            country=country
        )
    
    async def get_gdp_growth(self, country: str = "USA") -> List[Dict[str, Any]]:
        """Crescimento do PIB"""
        return await self.get_macro_indicator(country, 'gdp_growth_annual')
    
    async def get_inflation(self, country: str = "USA") -> List[Dict[str, Any]]:
        """Taxa de inflação"""
        return await self.get_macro_indicator(country, 'inflation_consumer_prices_annual')
    
    async def get_unemployment(self, country: str = "USA") -> List[Dict[str, Any]]:
        """Taxa de desemprego"""
        return await self.get_macro_indicator(country, 'unemployment_rate')
    
    async def get_interest_rate(self, country: str = "USA") -> List[Dict[str, Any]]:
        """Taxa de juros real"""
        return await self.get_macro_indicator(country, 'real_interest_rate')
    
    # =========================================================================
    # FOREX ESPECÍFICO
    # =========================================================================
    
    async def get_forex_pairs(self) -> List[Dict[str, Any]]:
        """Lista todos os pares forex disponíveis"""
        cache_key = "eodhd:forex_pairs"
        
        return await self._fetch(
            '/exchange-symbol-list/FOREX',
            cache_key=cache_key,
            cache_ttl=86400
        )
    
    async def get_forex_rate(self, pair: str) -> Dict[str, Any]:
        """
        Obtém cotação forex.
        
        Args:
            pair: Par forex (ex: EURUSD, GBPUSD)
            
        Returns:
            Dict com preço atual
        """
        symbol = f"{pair}.FOREX"
        return await self.get_live_price(symbol)
    
    async def get_forex_eod(
        self,
        pair: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Obtém dados históricos forex"""
        symbol = f"{pair}.FOREX"
        return await self.get_eod_data(symbol, from_date, to_date)
    
    async def get_forex_intraday(
        self,
        pair: str,
        interval: str = "5m"
    ) -> List[Dict[str, Any]]:
        """Obtém dados intraday forex"""
        symbol = f"{pair}.FOREX"
        return await self.get_intraday_data(symbol, interval)
    
    # =========================================================================
    # CRYPTO
    # =========================================================================
    
    async def get_crypto_list(self) -> List[Dict[str, Any]]:
        """Lista todas as criptomoedas disponíveis"""
        cache_key = "eodhd:crypto_list"
        
        return await self._fetch(
            '/exchange-symbol-list/CC',
            cache_key=cache_key,
            cache_ttl=86400
        )
    
    async def get_crypto_price(self, symbol: str) -> Dict[str, Any]:
        """
        Obtém preço de criptomoeda.
        
        Args:
            symbol: Símbolo da cripto (ex: BTC-USD, ETH-USD)
            
        Returns:
            Dict com preço atual
        """
        crypto_symbol = f"{symbol}.CC"
        return await self.get_live_price(crypto_symbol)
    
    async def get_crypto_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Obtém dados fundamentais de criptomoeda"""
        crypto_symbol = f"{symbol}.CC"
        return await self.get_fundamentals(crypto_symbol)
    
    # =========================================================================
    # EXCHANGES & SEARCH
    # =========================================================================
    
    async def get_exchanges(self) -> List[Dict[str, Any]]:
        """Lista todas as exchanges disponíveis"""
        cache_key = "eodhd:exchanges"
        
        return await self._fetch(
            self.ENDPOINTS['exchanges'],
            cache_key=cache_key,
            cache_ttl=86400
        )
    
    async def get_exchange_symbols(self, exchange: str) -> List[Dict[str, Any]]:
        """
        Lista todos os símbolos de uma exchange.
        
        Args:
            exchange: Código da exchange (US, LSE, FOREX, CC, etc)
            
        Returns:
            Lista de símbolos
        """
        cache_key = f"eodhd:symbols:{exchange}"
        
        return await self._fetch(
            self.ENDPOINTS['exchange_symbols'],
            cache_key=cache_key,
            cache_ttl=86400,
            exchange=exchange
        )
    
    async def search_symbol(self, query: str) -> List[Dict[str, Any]]:
        """
        Busca símbolos por nome ou código.
        
        Args:
            query: Termo de busca
            
        Returns:
            Lista de símbolos encontrados
        """
        cache_key = f"eodhd:search:{query}"
        
        return await self._fetch(
            self.ENDPOINTS['search'],
            cache_key=cache_key,
            cache_ttl=3600,
            query=query
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def health_check(self) -> bool:
        """Verifica saúde da conexão com a API"""
        try:
            # Tenta buscar notícias (endpoint gratuito)
            result = await self.get_news(limit=1)
            return result is not None and len(result) > 0
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_health_details(self) -> Dict[str, Any]:
        """Retorna detalhes do health check"""
        try:
            result = await self.get_news(limit=1)
            return {
                'status': 'healthy' if result else 'degraded',
                'provider': self.PROVIDER_NAME,
                'timestamp': datetime.now().isoformat(),
                'sample_data': result is not None
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': self.PROVIDER_NAME,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    async def get_supported_symbols(self) -> List[str]:
        """Retorna lista de símbolos/exchanges suportados"""
        return [
            "FOREX", "US", "CC", "INDX", "COMM",
            "LSE", "TSE", "XETRA", "PA", "SA"
        ]
    
    def format_symbol(
        self,
        symbol: str,
        exchange: str = "US"
    ) -> str:
        """
        Formata símbolo para API EODHD.
        
        Args:
            symbol: Símbolo base (ex: AAPL)
            exchange: Exchange code (US, FOREX, CC, etc)
            
        Returns:
            Símbolo formatado (ex: AAPL.US)
        """
        if '.' in symbol:
            return symbol
        return f"{symbol}.{exchange}"
    
    async def get_multi_symbol_data(
        self,
        symbols: List[str],
        data_type: str = "eod"
    ) -> Dict[str, Any]:
        """
        Obtém dados para múltiplos símbolos em paralelo.
        
        Args:
            symbols: Lista de símbolos
            data_type: Tipo de dados ('eod', 'live', 'intraday')
            
        Returns:
            Dict com dados de cada símbolo
        """
        async def fetch_symbol(symbol: str):
            try:
                if data_type == "eod":
                    return await self.get_eod_data(symbol)
                elif data_type == "live":
                    return await self.get_live_price(symbol)
                elif data_type == "intraday":
                    return await self.get_intraday_data(symbol)
                else:
                    return None
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                return None
        
        tasks = [fetch_symbol(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        
        return {
            symbol: data 
            for symbol, data in zip(symbols, results)
            if data is not None
        }


# ============================================================================
# SINGLETON
# ============================================================================

_eodhd_provider: Optional[EODHDProvider] = None


def get_eodhd_provider(api_key: Optional[str] = None) -> EODHDProvider:
    """
    Obtém instância singleton do EODHDProvider.
    
    Args:
        api_key: Chave de API EODHD
        
    Returns:
        Instância do provider
    """
    global _eodhd_provider
    
    if _eodhd_provider is None:
        if api_key is None:
            raise ValueError("API key required for first initialization")
        _eodhd_provider = EODHDProvider(api_key=api_key)
    
    return _eodhd_provider


async def init_eodhd_provider(api_key: str) -> EODHDProvider:
    """
    Inicializa o provider EODHD.
    
    Args:
        api_key: Chave de API
        
    Returns:
        Provider inicializado
    """
    provider = get_eodhd_provider(api_key)
    
    # Verifica saúde
    health = await provider.health_check()
    if health['status'] != 'healthy':
        logger.warning(f"EODHD provider health check failed: {health}")
    else:
        logger.info("✅ EODHD provider initialized successfully")
    
    return provider
