"""
VIRTUS - EODHD Data Service
============================

Serviço dedicado para dados da API EODHD.
Fornece dados de mercado, fundamentais, calendário e notícias
para o dashboard e módulos de análise.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.logger import get_logger
from ..core.exceptions import NoDataError, ProviderUnavailableError
from .providers import EODHDProvider, get_eodhd_provider

logger = get_logger("eodhd_service")


class DataInterval(str, Enum):
    """Intervalos de dados"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    HOUR_1 = "1h"
    DAILY = "d"
    WEEKLY = "w"
    MONTHLY = "m"


@dataclass
class MarketOverview:
    """Visão geral do mercado"""
    timestamp: datetime
    forex: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    indices: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    crypto: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    commodities: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass 
class EconomicOverview:
    """Visão geral econômica"""
    timestamp: datetime
    events_today: List[Dict[str, Any]] = field(default_factory=list)
    events_week: List[Dict[str, Any]] = field(default_factory=list)
    earnings_today: List[Dict[str, Any]] = field(default_factory=list)
    ipos_upcoming: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SentimentOverview:
    """Visão geral de sentimento"""
    timestamp: datetime
    market_sentiment: float = 0.0
    news_count: int = 0
    top_news: List[Dict[str, Any]] = field(default_factory=list)
    sector_sentiments: Dict[str, float] = field(default_factory=dict)


class EODHDDataService:
    """
    Serviço centralizado para dados EODHD.
    
    Fornece métodos de alto nível para obter:
    - Market Overview (Forex, Índices, Crypto)
    - Economic Calendar
    - News & Sentiment
    - Technical Analysis
    - Fundamental Data
    
    Uso:
        service = EODHDDataService(api_key)
        await service.initialize()
        
        overview = await service.get_market_overview()
        calendar = await service.get_economic_overview()
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._provider: Optional[EODHDProvider] = None
        self._initialized = False
        
        # Cache interno para dados frequentes
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def initialize(self) -> bool:
        """Inicializa o serviço"""
        try:
            self._provider = EODHDProvider(api_key=self.api_key)
            
            # Verifica conexão
            health = await self._provider.health_check()
            if health['status'] != 'healthy':
                logger.warning(f"EODHD health check failed: {health}")
                return False
            
            self._initialized = True
            logger.info("✅ EODHD Data Service inicializado")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar EODHD Service: {e}")
            return False
    
    def _is_cache_valid(self, key: str, max_age_seconds: int = 60) -> bool:
        """Verifica se cache ainda é válido"""
        if key not in self._cache_timestamps:
            return False
        
        age = (datetime.now() - self._cache_timestamps[key]).total_seconds()
        return age < max_age_seconds
    
    def _set_cache(self, key: str, data: Any):
        """Salva dados no cache"""
        self._cache[key] = data
        self._cache_timestamps[key] = datetime.now()
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Obtém dados do cache"""
        return self._cache.get(key)
    
    # =========================================================================
    # MARKET OVERVIEW
    # =========================================================================
    
    async def get_market_overview(self) -> MarketOverview:
        """
        Obtém visão geral completa do mercado.
        
        Inclui:
        - Principais pares Forex
        - Índices globais
        - Criptomoedas principais
        - Commodities
        """
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        cache_key = "market_overview"
        if self._is_cache_valid(cache_key, 60):
            return self._get_cache(cache_key)
        
        overview = MarketOverview(timestamp=datetime.now())
        
        # Forex
        forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'XAGUSD', 'AUDUSD']
        for pair in forex_pairs:
            try:
                data = await self._provider.get_forex_rate(pair)
                overview.forex[pair] = data
            except Exception as e:
                logger.debug(f"Erro ao obter {pair}: {e}")
        
        # Índices (via bulk ou individual)
        indices = [
            ('SPX', 'GSPC.INDX'),
            ('DJI', 'DJI.INDX'),
            ('NASDAQ', 'IXIC.INDX'),
            ('VIX', 'VIX.INDX'),
        ]
        for name, symbol in indices:
            try:
                data = await self._provider.get_live_price(symbol)
                overview.indices[name] = data
            except Exception as e:
                logger.debug(f"Erro ao obter {name}: {e}")
        
        # Crypto
        cryptos = ['BTC-USD', 'ETH-USD', 'XRP-USD']
        for crypto in cryptos:
            try:
                data = await self._provider.get_crypto_price(crypto)
                overview.crypto[crypto] = data
            except Exception as e:
                logger.debug(f"Erro ao obter {crypto}: {e}")
        
        self._set_cache(cache_key, overview)
        return overview
    
    async def get_forex_detailed(
        self,
        pair: str,
        include_technicals: bool = True
    ) -> Dict[str, Any]:
        """
        Obtém dados detalhados de um par forex.
        
        Inclui:
        - Preço atual
        - Dados históricos (últimos 30 dias)
        - Indicadores técnicos (opcional)
        """
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        result = {
            'pair': pair,
            'timestamp': datetime.now().isoformat(),
            'current': None,
            'historical': [],
            'technicals': {}
        }
        
        # Preço atual
        try:
            result['current'] = await self._provider.get_forex_rate(pair)
        except Exception as e:
            logger.warning(f"Erro ao obter preço {pair}: {e}")
        
        # Histórico (30 dias)
        try:
            from_date = datetime.now() - timedelta(days=30)
            result['historical'] = await self._provider.get_forex_eod(
                pair, from_date
            )
        except Exception as e:
            logger.warning(f"Erro ao obter histórico {pair}: {e}")
        
        # Indicadores técnicos
        if include_technicals:
            try:
                symbol = f"{pair}.FOREX"
                result['technicals'] = {
                    'rsi': await self._provider.get_rsi(symbol),
                    'macd': await self._provider.get_macd(symbol),
                    'bbands': await self._provider.get_bbands(symbol),
                    'sma_20': await self._provider.get_sma(symbol, 20),
                    'sma_50': await self._provider.get_sma(symbol, 50),
                }
            except Exception as e:
                logger.warning(f"Erro ao obter técnicos {pair}: {e}")
        
        return result
    
    # =========================================================================
    # ECONOMIC CALENDAR
    # =========================================================================
    
    async def get_economic_overview(
        self,
        countries: List[str] = None
    ) -> EconomicOverview:
        """
        Obtém visão geral do calendário econômico.
        
        Inclui:
        - Eventos de hoje
        - Eventos da semana
        - Earnings de hoje
        - IPOs próximos
        """
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        countries = countries or ['US', 'GB', 'EU', 'JP']
        
        cache_key = f"economic_overview:{':'.join(countries)}"
        if self._is_cache_valid(cache_key, 3600):  # 1 hora
            return self._get_cache(cache_key)
        
        overview = EconomicOverview(timestamp=datetime.now())
        
        today = datetime.now()
        week_end = today + timedelta(days=7)
        
        # Eventos econômicos
        try:
            for country in countries:
                events = await self._provider.get_economic_events(
                    today, week_end, country
                )
                
                for event in events:
                    event_date = datetime.fromisoformat(event.get('date', ''))
                    
                    if event_date.date() == today.date():
                        overview.events_today.append(event)
                    
                    overview.events_week.append(event)
        except Exception as e:
            logger.warning(f"Erro ao obter eventos econômicos: {e}")
        
        # Earnings
        try:
            earnings = await self._provider.get_earnings_calendar(today, week_end)
            for earning in earnings:
                earning_date = datetime.fromisoformat(earning.get('date', ''))
                if earning_date.date() == today.date():
                    overview.earnings_today.append(earning)
        except Exception as e:
            logger.warning(f"Erro ao obter earnings: {e}")
        
        # IPOs
        try:
            overview.ipos_upcoming = await self._provider.get_ipos_calendar(
                today, week_end
            )
        except Exception as e:
            logger.warning(f"Erro ao obter IPOs: {e}")
        
        # Ordena eventos por data/hora
        overview.events_today.sort(key=lambda x: x.get('date', ''))
        overview.events_week.sort(key=lambda x: x.get('date', ''))
        
        self._set_cache(cache_key, overview)
        return overview
    
    # =========================================================================
    # NEWS & SENTIMENT
    # =========================================================================
    
    async def get_sentiment_overview(
        self,
        symbols: List[str] = None,
        limit: int = 20
    ) -> SentimentOverview:
        """
        Obtém visão geral de sentimento do mercado.
        
        Inclui:
        - Sentimento geral do mercado
        - Principais notícias
        - Sentimento por setor
        """
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        overview = SentimentOverview(timestamp=datetime.now())
        
        # Notícias gerais
        try:
            news = await self._provider.get_news(
                symbols=symbols,
                limit=limit
            )
            overview.top_news = news
            overview.news_count = len(news)
            
            # Calcula sentimento médio das notícias
            sentiments = []
            for article in news:
                if 'sentiment' in article:
                    sentiments.append(article['sentiment'].get('polarity', 0))
            
            if sentiments:
                overview.market_sentiment = sum(sentiments) / len(sentiments)
        except Exception as e:
            logger.warning(f"Erro ao obter notícias: {e}")
        
        # Sentimento por símbolos específicos
        if symbols:
            for symbol in symbols[:5]:  # Limita a 5 símbolos
                try:
                    eodhd_symbol = f"{symbol}.FOREX" if symbol in ['XAUUSD', 'EURUSD', 'GBPUSD'] else f"{symbol}.US"
                    sent = await self._provider.get_sentiment(eodhd_symbol)
                    if sent:
                        # Calcula média do sentimento
                        scores = [item.get('normalized', 0) for item in sent if 'normalized' in item]
                        if scores:
                            overview.sector_sentiments[symbol] = sum(scores) / len(scores)
                except Exception as e:
                    logger.debug(f"Erro ao obter sentimento {symbol}: {e}")
        
        return overview
    
    async def get_news_by_topic(
        self,
        topic: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Obtém notícias por tópico/tag.
        
        Topics disponíveis:
        - fed, inflation, rates, crypto, earnings, etc
        """
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        return await self._provider.get_news(tag=topic, limit=limit)
    
    # =========================================================================
    # TECHNICAL ANALYSIS
    # =========================================================================
    
    async def get_technical_analysis(
        self,
        symbol: str,
        exchange: str = "FOREX"
    ) -> Dict[str, Any]:
        """
        Obtém análise técnica completa de um símbolo.
        
        Inclui:
        - Tendência (SMA/EMA)
        - Momentum (RSI, MACD)
        - Volatilidade (Bollinger, ATR)
        - Força (ADX)
        """
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        eodhd_symbol = f"{symbol}.{exchange}"
        
        analysis = {
            'symbol': symbol,
            'exchange': exchange,
            'timestamp': datetime.now().isoformat(),
            'trend': {},
            'momentum': {},
            'volatility': {},
            'strength': {}
        }
        
        # Tendência
        try:
            analysis['trend']['sma_20'] = await self._provider.get_sma(eodhd_symbol, 20)
            analysis['trend']['sma_50'] = await self._provider.get_sma(eodhd_symbol, 50)
            analysis['trend']['ema_20'] = await self._provider.get_ema(eodhd_symbol, 20)
        except Exception as e:
            logger.debug(f"Erro trend: {e}")
        
        # Momentum
        try:
            analysis['momentum']['rsi'] = await self._provider.get_rsi(eodhd_symbol)
            analysis['momentum']['macd'] = await self._provider.get_macd(eodhd_symbol)
            analysis['momentum']['stoch'] = await self._provider.get_stochastic(eodhd_symbol)
        except Exception as e:
            logger.debug(f"Erro momentum: {e}")
        
        # Volatilidade
        try:
            analysis['volatility']['bbands'] = await self._provider.get_bbands(eodhd_symbol)
            analysis['volatility']['atr'] = await self._provider.get_atr(eodhd_symbol)
        except Exception as e:
            logger.debug(f"Erro volatility: {e}")
        
        # Força
        try:
            analysis['strength']['adx'] = await self._provider.get_adx(eodhd_symbol)
        except Exception as e:
            logger.debug(f"Erro strength: {e}")
        
        return analysis
    
    # =========================================================================
    # FUNDAMENTAL DATA
    # =========================================================================
    
    async def get_stock_fundamentals(
        self,
        symbol: str,
        exchange: str = "US"
    ) -> Dict[str, Any]:
        """
        Obtém dados fundamentalistas de uma ação.
        """
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        eodhd_symbol = f"{symbol}.{exchange}"
        
        return await self._provider.get_fundamentals(eodhd_symbol)
    
    async def get_company_profile(
        self,
        symbol: str,
        exchange: str = "US"
    ) -> Dict[str, Any]:
        """Obtém perfil da empresa"""
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        eodhd_symbol = f"{symbol}.{exchange}"
        return await self._provider.get_company_profile(eodhd_symbol)
    
    # =========================================================================
    # MACRO DATA
    # =========================================================================
    
    async def get_macro_overview(
        self,
        countries: List[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Obtém visão geral de dados macroeconômicos.
        """
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        countries = countries or ['USA', 'GBR', 'EUR', 'BRA']
        
        result = {}
        
        for country in countries:
            result[country] = {
                'gdp_growth': await self._safe_fetch(
                    self._provider.get_gdp_growth, country
                ),
                'inflation': await self._safe_fetch(
                    self._provider.get_inflation, country
                ),
                'unemployment': await self._safe_fetch(
                    self._provider.get_unemployment, country
                ),
                'interest_rate': await self._safe_fetch(
                    self._provider.get_interest_rate, country
                )
            }
        
        return result
    
    async def _safe_fetch(self, func, *args, **kwargs) -> Any:
        """Executa função com tratamento de erro"""
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.debug(f"Erro em {func.__name__}: {e}")
            return None
    
    # =========================================================================
    # SEARCH & DISCOVERY
    # =========================================================================
    
    async def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """Busca símbolos por nome ou código"""
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        return await self._provider.search_symbol(query)
    
    async def get_exchange_symbols(self, exchange: str) -> List[Dict[str, Any]]:
        """Lista símbolos de uma exchange"""
        if not self._initialized:
            raise ProviderUnavailableError("Service not initialized")
        
        return await self._provider.get_exchange_symbols(exchange)
    
    # =========================================================================
    # HEALTH & STATUS
    # =========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do serviço"""
        if not self._provider:
            return {
                'status': 'not_initialized',
                'timestamp': datetime.now().isoformat()
            }
        
        return await self._provider.health_check()
    
    async def close(self):
        """Fecha conexões"""
        if self._provider:
            await self._provider.close()
        self._initialized = False
        logger.info("EODHD Data Service encerrado")


# ============================================================================
# SINGLETON
# ============================================================================

_eodhd_service: Optional[EODHDDataService] = None


async def get_eodhd_service(api_key: Optional[str] = None) -> EODHDDataService:
    """
    Obtém instância singleton do serviço EODHD.
    
    Args:
        api_key: Chave de API (obrigatório na primeira chamada)
        
    Returns:
        Instância do serviço
    """
    global _eodhd_service
    
    if _eodhd_service is None:
        if api_key is None:
            raise ValueError("API key required for first initialization")
        
        _eodhd_service = EODHDDataService(api_key)
        await _eodhd_service.initialize()
    
    return _eodhd_service
