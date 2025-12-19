"""
VIRTUS Portal - Main Portal Service
====================================

Serviço principal do portal público com integração de múltiplas APIs:
- ForexNews API - Notícias de forex e commodities
- EODHD - Calendário econômico e dados de mercado
- Brapi - Cotações e dados de ações brasileiras
- Yahoo Finance - Índices globais
"""

import asyncio
import aiohttp
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib

# Carregar variáveis de ambiente do .env ANTES de ler as API keys
from dotenv import load_dotenv
_ENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
    logging.info(f"Loaded .env from: {_ENV_PATH}")
else:
    logging.warning(f".env not found at: {_ENV_PATH}")

# Tradução para português
try:
    from googletrans import Translator
    _translator = Translator()
    TRANSLATION_ENABLED = True
except ImportError:
    _translator = None
    TRANSLATION_ENABLED = False

try:
    import pytz
    BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')
except ImportError:
    BRAZIL_TZ = None

logger = logging.getLogger(__name__)

# API Keys (lidas do ambiente - ver .env)
FOREXNEWS_API_KEY = os.getenv("FOREXNEWS_API_KEY", "")
EODHD_API_KEY = os.getenv("EODHD_API_KEY", "")
BRAPI_API_KEY = os.getenv("BRAPI_API_KEY", "")

# Cache de traduções para evitar chamadas repetidas
_translation_cache: Dict[str, str] = {}
_MAX_CACHE_SIZE = 500


def get_brazil_now() -> datetime:
    """Retorna datetime atual no fuso horário do Brasil."""
    if BRAZIL_TZ:
        return datetime.now(BRAZIL_TZ)
    return datetime.utcnow() - timedelta(hours=3)


def utc_to_brazil(hour_utc: int) -> int:
    """Converte hora UTC para horário de Brasília."""
    hour_br = hour_utc - 3
    if hour_br < 0:
        hour_br += 24
    return hour_br


def _is_portuguese(text: str) -> bool:
    """Verifica se o texto já está em português."""
    # Palavras portuguesas comuns
    pt_words = ['de', 'da', 'do', 'em', 'na', 'no', 'para', 'com', 'por', 'sobre', 
                'que', 'uma', 'seu', 'sua', 'nos', 'mais', 'foi', 'são', 'está',
                'preço', 'mercado', 'ações', 'bolsa', 'real', 'economia', 'inflação',
                'juros', 'dólar', 'queda', 'alta', 'brasil', 'brasileiro']
    
    # Palavras inglesas comuns
    en_words = ['the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'is',
                'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                'price', 'market', 'stock', 'rise', 'fall', 'gold', 'dollar', 'amid']
    
    text_lower = text.lower()
    words = text_lower.split()
    
    pt_count = sum(1 for w in words if w in pt_words)
    en_count = sum(1 for w in words if w in en_words)
    
    return pt_count > en_count


def translate_to_portuguese(text: str, max_length: int = 500) -> str:
    """Traduz texto para português brasileiro com cache."""
    global _translation_cache
    
    if not text or len(text.strip()) < 3:
        return text
    
    # Se já está em português, retorna
    if _is_portuguese(text):
        return text
    
    # Verifica cache
    cache_key = hashlib.md5(text[:100].encode()).hexdigest()
    if cache_key in _translation_cache:
        return _translation_cache[cache_key]
    
    # Se não tem tradutor disponível
    if not TRANSLATION_ENABLED or not _translator:
        logger.warning("Tradutor não disponível - retornando texto original")
        return text
    
    try:
        # Limita o texto para evitar problemas com textos muito longos
        text_to_translate = text[:max_length] if len(text) > max_length else text
        result = _translator.translate(text_to_translate, dest='pt', src='en')
        translated = result.text if result else text
        
        # Salva no cache
        if len(_translation_cache) >= _MAX_CACHE_SIZE:
            # Remove metade do cache quando cheio
            keys = list(_translation_cache.keys())[:_MAX_CACHE_SIZE // 2]
            for k in keys:
                del _translation_cache[k]
        
        _translation_cache[cache_key] = translated
        logger.info(f"Traduzido: '{text[:50]}...' -> '{translated[:50]}...'")
        return translated
        
    except Exception as e:
        logger.warning(f"Erro na tradução: {e}")
        return text


class NewsCategory(str, Enum):
    """Categorias de notícias."""
    FOREX = "forex"
    STOCKS_BR = "stocks_br"
    STOCKS_US = "stocks_us"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    ECONOMY = "economy"
    POLITICS = "politics"


@dataclass
class PortalNews:
    """Notícia do portal."""
    id: str
    title: str
    summary: str
    content: Optional[str]
    source: str
    category: NewsCategory
    sentiment: str  # bullish, bearish, neutral
    published_at: str
    image_url: Optional[str] = None
    url: Optional[str] = None
    tickers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'content': self.content,
            'source': self.source,
            'category': self.category.value,
            'sentiment': self.sentiment,
            'published_at': self.published_at,
            'image_url': self.image_url,
            'url': self.url,
            'tickers': self.tickers
        }


@dataclass
class MarketQuote:
    """Cotação de mercado."""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: Optional[float] = None
    market_cap: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    previous_close: Optional[float] = None
    updated_at: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'price': self.price,
            'change': self.change,
            'change_percent': self.change_percent,
            'volume': self.volume,
            'market_cap': self.market_cap,
            'high': self.high,
            'low': self.low,
            'open': self.open,
            'previous_close': self.previous_close,
            'updated_at': self.updated_at
        }


@dataclass
class EconomicEvent:
    """Evento econômico."""
    time: str
    time_brazil: str
    country: str
    event: str
    impact: str  # high, medium, low
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'time': self.time,
            'time_brazil': self.time_brazil,
            'country': self.country,
            'event': self.event,
            'impact': self.impact,
            'actual': self.actual,
            'forecast': self.forecast,
            'previous': self.previous
        }


class PortalService:
    """Serviço principal do portal VIRTUS."""
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 600  # 10 minutos para economizar requisições
        self._brapi_cache_ttl = 900  # 15 minutos para Brapi (plano gratuito)
        self._last_brapi_call = 0
        self._brapi_rate_limit = 5  # segundos entre chamadas
        
        # Traduções de eventos
        self.event_translations = {
            'Interest Rate Decision': 'Decisão de Taxa de Juros',
            'Fed Interest Rate Decision': 'Decisão de Juros do FED',
            'ECB Interest Rate Decision': 'Decisão de Juros do BCE',
            'ECB Press Conference': 'Coletiva do BCE',
            'Fed Press Conference': 'Coletiva do FED',
            'FOMC Press Conference': 'Coletiva FOMC',
            'GDP Growth Rate': 'Taxa de Crescimento do PIB',
            'Unemployment Rate': 'Taxa de Desemprego',
            'Non Farm Payrolls': 'Payroll Não-Agrícola',
            'Nonfarm Payrolls': 'Payroll Não-Agrícola',
            'Inflation Rate': 'Taxa de Inflação',
            'Core Inflation Rate': 'Inflação Núcleo',
            'CPI': 'Índice de Preços ao Consumidor',
            'Core CPI': 'CPI Núcleo',
            'PPI': 'Índice de Preços ao Produtor',
            'Retail Sales': 'Vendas no Varejo',
            'Industrial Production': 'Produção Industrial',
            'Consumer Confidence': 'Confiança do Consumidor',
            'Balance of Trade': 'Balança Comercial',
            'Jobless Claims': 'Pedidos Seguro Desemprego',
            'Initial Jobless Claims': 'Pedidos Iniciais Seguro Desemprego',
            'PMI': 'PMI',
            'Manufacturing PMI': 'PMI Manufatura',
            'Services PMI': 'PMI Serviços',
            'Selic Rate': 'Taxa Selic',
            'Copom Interest Rate Decision': 'Decisão Copom Taxa Selic',
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna sessão HTTP."""
        if self._session is None or self._session.closed:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self._session
    
    async def close(self):
        """Fecha sessão."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Verifica se cache ainda é válido."""
        if key not in self._cache:
            return False
        cached = self._cache[key]
        return (datetime.now().timestamp() - cached['timestamp']) < self._cache_ttl
    
    # ========================================================================
    # FOREXNEWS API - Notícias de Forex e Commodities
    # ========================================================================
    
    async def get_forex_news(self, limit: int = 20, currencies: List[str] = None) -> List[PortalNews]:
        """Busca notícias de forex via ForexNews API."""
        cache_key = f"forex_news_{limit}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']
        
        session = await self._get_session()
        news_list = []
        
        if not currencies:
            currencies = ['EUR-USD', 'GBP-USD', 'XAU-USD', 'USD-JPY', 'USD-BRL']
        
        try:
            url = "https://forexnewsapi.com/api/v1"
            params = {
                'token': FOREXNEWS_API_KEY,
                'currencypair': ','.join(currencies[:3]),  # API aceita até 3
                'items': limit,
                'page': 1
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for i, item in enumerate(data.get('data', [])[:limit]):
                        # Determina sentimento
                        sentiment = 'neutral'
                        if item.get('sentiment'):
                            sent = item['sentiment'].lower()
                            if 'positive' in sent:
                                sentiment = 'bullish'
                            elif 'negative' in sent:
                                sentiment = 'bearish'
                        
                        # Traduz título e resumo para português
                        original_title = item.get('title', '') or ''
                        original_text = item.get('text', '') or ''
                        
                        translated_title = translate_to_portuguese(original_title, max_length=200)
                        translated_summary = translate_to_portuguese(original_text[:300], max_length=350)
                        if len(original_text) > 300:
                            translated_summary += '...'
                        
                        news_list.append(PortalNews(
                            id=f"forex_{i}_{datetime.now().timestamp()}",
                            title=translated_title,
                            summary=translated_summary,
                            content=original_text,
                            source=item.get('source_name', 'ForexNews'),
                            category=NewsCategory.FOREX,
                            sentiment=sentiment,
                            published_at=item.get('date', ''),
                            image_url=item.get('image_url'),
                            url=item.get('news_url'),
                            tickers=item.get('currency_pair', '').split(',')
                        ))
                else:
                    logger.warning(f"ForexNews API retornou status {resp.status}")
                    
        except Exception as e:
            logger.error(f"Erro ao buscar notícias ForexNews: {e}")
        
        # Cache
        self._cache[cache_key] = {'data': news_list, 'timestamp': datetime.now().timestamp()}
        return news_list
    
    # ========================================================================
    # EODHD API - Calendário Econômico e Notícias
    # ========================================================================
    
    async def get_economic_calendar(self, days: int = 0) -> List[EconomicEvent]:
        """Busca calendário econômico via EODHD."""
        cache_key = f"calendar_{days}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']
        
        session = await self._get_session()
        events = []
        
        try:
            today = get_brazil_now()
            target_date = today + timedelta(days=days)
            date_str = target_date.strftime('%Y-%m-%d')
            
            url = "https://eodhd.com/api/economic-events"
            params = {
                'api_token': EODHD_API_KEY,
                'from': date_str,
                'to': date_str,
                'fmt': 'json'
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Países importantes primeiro
                    important_countries = ['US', 'BR', 'EU', 'GB', 'JP', 'CN']
                    
                    for item in data:
                        event_type = item.get('type', '')
                        country = item.get('country', 'N/A')
                        
                        # Traduz evento
                        translated = self.event_translations.get(event_type, event_type)
                        
                        # Determina impacto
                        impact = 'low'
                        if any(kw in event_type.lower() for kw in ['interest rate', 'gdp', 'inflation', 'employment', 'payroll', 'fed', 'ecb', 'copom']):
                            impact = 'high'
                        elif any(kw in event_type.lower() for kw in ['pmi', 'retail', 'production', 'confidence']):
                            impact = 'medium'
                        
                        # Extrai hora UTC e converte para Brasília
                        date_str_item = item.get('date', '')
                        time_utc = 'N/A'
                        time_brazil = 'N/A'
                        try:
                            if len(date_str_item) >= 16:
                                time_utc = date_str_item[11:16]
                                hour_utc = int(time_utc[:2])
                                minute = time_utc[3:5]
                                hour_br = utc_to_brazil(hour_utc)
                                time_brazil = f"{hour_br:02d}:{minute}"
                        except:
                            pass
                        
                        # Adiciona comparação se houver
                        comparison = item.get('comparison', '')
                        if comparison:
                            translated = f"{translated} ({comparison.upper()})"
                        
                        period = item.get('period', '')
                        if period:
                            translated = f"{translated} - {period}"
                        
                        events.append(EconomicEvent(
                            time=time_utc,
                            time_brazil=time_brazil,
                            country=country,
                            event=translated,
                            impact=impact,
                            actual=str(item.get('actual')) if item.get('actual') is not None else None,
                            forecast=str(item.get('estimate')) if item.get('estimate') is not None else None,
                            previous=str(item.get('previous')) if item.get('previous') is not None else None
                        ))
                    
                    # Ordena por impacto e país
                    impact_order = {'high': 0, 'medium': 1, 'low': 2}
                    events.sort(key=lambda x: (
                        impact_order.get(x.impact, 3),
                        0 if x.country in important_countries else 1,
                        x.time_brazil
                    ))
                    
        except Exception as e:
            logger.error(f"Erro ao buscar calendário EODHD: {e}")
        
        self._cache[cache_key] = {'data': events, 'timestamp': datetime.now().timestamp()}
        return events
    
    async def get_eodhd_news(self, symbols: List[str] = None, limit: int = 20) -> List[PortalNews]:
        """Busca notícias de ações brasileiras via EODHD."""
        import json
        import ssl
        
        cache_key = f"eodhd_news_{limit}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']
            
        news_list = []
        
        if not symbols:
            symbols = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'B3SA3.SA']
        
        try:
            url = "https://eodhd.com/api/news"
            
            # A API EODHD aceita apenas um símbolo por vez, então buscamos por cada um
            # ou buscamos notícias gerais e filtramos
            params = {
                'api_token': EODHD_API_KEY,
                's': symbols[0],  # Usa apenas o primeiro símbolo
                'limit': limit * 2,  # Pega mais para compensar filtro
                'offset': 0,
                'fmt': 'json'
            }
            
            # Cria sessão dedicada para EODHD com headers adequados
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            logger.info(f"EODHD News: Buscando notícias para {symbols}")
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
                async with session.get(url, params=params) as resp:
                    logger.info(f"EODHD News: Status {resp.status}")
                    
                    if resp.status == 200:
                        # Usa read() + decode() para evitar problemas de encoding
                        raw_bytes = await resp.read()
                        text = raw_bytes.decode('utf-8')
                        logger.info(f"EODHD News: Recebido {len(text)} bytes")
                        
                        data = json.loads(text)
                        logger.info(f"EODHD News: Tipo de dados: {type(data)}, é lista: {isinstance(data, list)}")
                        
                        # EODHD retorna lista de objetos
                        items = data if isinstance(data, list) else data.get('data', []) if isinstance(data, dict) else []
                        logger.info(f"EODHD News: {len(items)} items encontrados")
                    
                        for i, item in enumerate(items[:limit]):
                            # Análise de sentimento
                            title = (item.get('title', '') or '').lower()
                            content = (item.get('content', '') or '').lower()
                            combined_text = title + ' ' + content
                            
                            sentiment = 'neutral'
                            bullish_words = ['alta', 'sobe', 'crescimento', 'lucro', 'recorde', 'positivo', 'otimismo', 'rally', 'surge', 'gains', 'profit', 'growth']
                            bearish_words = ['queda', 'baixa', 'prejuízo', 'negativo', 'pessimismo', 'risco', 'crise', 'falls', 'drop', 'decline', 'loss', 'warning']
                            
                            # Verifica sentimento da API se disponível
                            if item.get('sentiment'):
                                sent_data = item.get('sentiment', {})
                                if isinstance(sent_data, dict):
                                    pos = sent_data.get('pos', 0)
                                    neg = sent_data.get('neg', 0)
                                    if pos > neg and pos > 0.1:
                                        sentiment = 'bullish'
                                    elif neg > pos and neg > 0.1:
                                        sentiment = 'bearish'
                            else:
                                if any(w in combined_text for w in bullish_words):
                                    sentiment = 'bullish'
                                elif any(w in combined_text for w in bearish_words):
                                    sentiment = 'bearish'
                            
                            # Extrai símbolos relacionados
                            tickers = item.get('symbols', [])
                            if isinstance(tickers, str):
                                tickers = [t.strip() for t in tickers.split(',')]
                            
                            # Filtra apenas símbolos brasileiros
                            br_tickers = [t.replace('.SA', '') for t in tickers if '.SA' in t]
                            
                            # Traduz título e resumo para português
                            original_title = item.get('title', '') or 'Sem título'
                            original_content = item.get('content', '') or ''
                            
                            translated_title = translate_to_portuguese(original_title, max_length=200)
                            translated_summary = translate_to_portuguese(original_content[:300], max_length=350)
                            if len(original_content) > 300:
                                translated_summary += '...'
                            
                            news_list.append(PortalNews(
                                id=f"eodhd_{i}_{datetime.now().timestamp()}",
                                title=translated_title,
                                summary=translated_summary,
                                content=original_content,  # Conteúdo original (muito longo para traduzir)
                                source=item.get('source', 'EODHD') or 'Yahoo Finance',
                                category=NewsCategory.STOCKS_BR,
                                sentiment=sentiment,
                                published_at=item.get('date', '') or '',
                                url=item.get('link', ''),
                                tickers=br_tickers if br_tickers else tickers[:5]
                            ))
                    else:
                        logger.warning(f"EODHD News API retornou status {resp.status}")
                        
        except Exception as e:
            logger.error(f"Erro ao buscar notícias EODHD: {e}", exc_info=True)
        
        # Cache
        self._cache[cache_key] = {'data': news_list, 'timestamp': datetime.now().timestamp()}
        return news_list
    
    # ========================================================================
    # BRAPI - Cotações Brasil
    # ========================================================================
    
    async def get_brazil_quotes(self, symbols: List[str] = None) -> List[MarketQuote]:
        """Busca cotações brasileiras via Brapi."""
        cache_key = "brazil_quotes"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']
        
        if not BRAPI_API_KEY:
            logger.warning("BRAPI_API_KEY não configurada")
            return self._get_brazil_quotes_fallback_static()
        
        # Rate limiting para Brapi
        now = datetime.now().timestamp()
        if now - self._last_brapi_call < self._brapi_rate_limit:
            await asyncio.sleep(self._brapi_rate_limit)
        
        session = await self._get_session()
        quotes = []
        
        if not symbols:
            symbols = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'ABEV3', 'B3SA3', 'WEGE3', 'BBAS3']
        
        try:
            url = f"https://brapi.dev/api/quote/{','.join(symbols[:5])}"  # Limita para não exceder rate
            params = {'token': BRAPI_API_KEY}
            
            async with session.get(url, params=params) as resp:
                self._last_brapi_call = datetime.now().timestamp()
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    for item in data.get('results', []):
                        quotes.append(MarketQuote(
                            symbol=item.get('symbol', ''),
                            name=item.get('shortName', item.get('longName', '')),
                            price=item.get('regularMarketPrice', 0),
                            change=item.get('regularMarketChange', 0),
                            change_percent=item.get('regularMarketChangePercent', 0),
                            volume=item.get('regularMarketVolume'),
                            market_cap=item.get('marketCap'),
                            high=item.get('regularMarketDayHigh'),
                            low=item.get('regularMarketDayLow'),
                            open=item.get('regularMarketOpen'),
                            previous_close=item.get('regularMarketPreviousClose'),
                            updated_at=datetime.now().isoformat()
                        ))
                elif resp.status == 429:
                    logger.warning("Brapi rate limit, usando fallback")
                    return self._get_brazil_quotes_fallback_static()
                        
        except Exception as e:
            logger.error(f"Erro ao buscar cotações Brapi: {e}")
            return self._get_brazil_quotes_fallback_static()
        
        if quotes:
            self._cache[cache_key] = {'data': quotes, 'timestamp': datetime.now().timestamp()}
        
        return quotes if quotes else self._get_brazil_quotes_fallback_static()
    
    def _get_brazil_quotes_fallback_static(self) -> List[MarketQuote]:
        """Retorna cotações estáticas de fallback."""
        now = datetime.now().isoformat()
        return [
            MarketQuote(symbol='PETR4', name='Petrobras PN', price=31.08, change=0.34, change_percent=1.11, updated_at=now),
            MarketQuote(symbol='VALE3', name='Vale ON', price=54.20, change=-0.45, change_percent=-0.82, updated_at=now),
            MarketQuote(symbol='ITUB4', name='Itaú Unibanco PN', price=32.50, change=0.25, change_percent=0.77, updated_at=now),
            MarketQuote(symbol='BBDC4', name='Bradesco PN', price=11.85, change=0.12, change_percent=1.02, updated_at=now),
            MarketQuote(symbol='ABEV3', name='Ambev ON', price=11.20, change=-0.08, change_percent=-0.71, updated_at=now),
        ]
    
    # ========================================================================
    # ÍNDICES GLOBAIS - Brapi (principal) ou Yahoo Finance (fallback)
    # ========================================================================
    
    async def get_market_indices(self) -> Dict[str, MarketQuote]:
        """Busca principais índices de mercado via Brapi."""
        cache_key = "market_indices"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']
        
        # Rate limiting para Brapi
        now = datetime.now().timestamp()
        if now - self._last_brapi_call < self._brapi_rate_limit:
            await asyncio.sleep(self._brapi_rate_limit)
        
        session = await self._get_session()
        results = {}
        
        try:
            # 1. Busca índices (Ibovespa e S&P 500)
            symbols = '%5EBVSP,%5EGSPC'
            url = f"https://brapi.dev/api/quote/{symbols}"
            params = {'token': BRAPI_API_KEY}
            
            async with session.get(url, params=params) as resp:
                self._last_brapi_call = datetime.now().timestamp()
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    symbol_map = {
                        '^BVSP': ('ibovespa', 'Ibovespa'),
                        '^GSPC': ('sp500', 'S&P 500'),
                    }
                    
                    for item in data.get('results', []):
                        symbol = item.get('symbol', '')
                        if symbol in symbol_map:
                            key, name = symbol_map[symbol]
                            results[key] = MarketQuote(
                                symbol=symbol,
                                name=name,
                                price=item.get('regularMarketPrice', 0),
                                change=item.get('regularMarketChange', 0),
                                change_percent=item.get('regularMarketChangePercent', 0),
                                high=item.get('regularMarketDayHigh'),
                                low=item.get('regularMarketDayLow'),
                                volume=item.get('regularMarketVolume'),
                                previous_close=item.get('regularMarketPreviousClose'),
                                updated_at=datetime.now().isoformat()
                            )
            
            # 2. Busca moedas (endpoint específico)
            await asyncio.sleep(1)  # Rate limit
            currency_url = "https://brapi.dev/api/v2/currency"
            currency_params = {'currency': 'USD-BRL,EUR-BRL', 'token': BRAPI_API_KEY}
            
            async with session.get(currency_url, params=currency_params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for curr in data.get('currency', []):
                        from_curr = curr.get('fromCurrency', '')
                        bid_price = curr.get('bidPrice', 0)
                        pct_change = curr.get('percentageChange', 0)
                        
                        if from_curr == 'USD':
                            results['dolar'] = MarketQuote(
                                symbol='USDBRL',
                                name='Dólar',
                                price=bid_price,
                                change=curr.get('bidVariation', 0),
                                change_percent=pct_change,
                                high=curr.get('high'),
                                low=curr.get('low'),
                                updated_at=datetime.now().isoformat()
                            )
                        elif from_curr == 'EUR':
                            results['euro'] = MarketQuote(
                                symbol='EURBRL',
                                name='Euro',
                                price=bid_price,
                                change=curr.get('bidVariation', 0),
                                change_percent=pct_change,
                                high=curr.get('high'),
                                low=curr.get('low'),
                                updated_at=datetime.now().isoformat()
                            )
            
            # 3. Busca Bitcoin (endpoint crypto)
            await asyncio.sleep(1)  # Rate limit
            crypto_url = "https://brapi.dev/api/v2/crypto"
            crypto_params = {'coin': 'BTC', 'currency': 'USD', 'token': BRAPI_API_KEY}
            
            async with session.get(crypto_url, params=crypto_params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    coins = data.get('coins', [])
                    if coins:
                        btc = coins[0]
                        results['bitcoin'] = MarketQuote(
                            symbol='BTC',
                            name='Bitcoin',
                            price=btc.get('regularMarketPrice', 0),
                            change=btc.get('regularMarketChange', 0),
                            change_percent=btc.get('regularMarketChangePercent', 0),
                            high=btc.get('regularMarketDayHigh'),
                            low=btc.get('regularMarketDayLow'),
                            volume=btc.get('regularMarketVolume'),
                            updated_at=datetime.now().isoformat()
                        )
                            
        except Exception as e:
            logger.error(f"Erro ao buscar índices Brapi: {e}")
        
        # Se não conseguiu dados, usa fallback com dados estáticos
        if not results:
            results = self._get_fallback_indices()
        
        self._cache[cache_key] = {'data': results, 'timestamp': datetime.now().timestamp()}
        return results
    
    def _get_fallback_indices(self) -> Dict[str, MarketQuote]:
        """Retorna índices de fallback quando APIs falham."""
        now = datetime.now().isoformat()
        return {
            'ibovespa': MarketQuote(symbol='^BVSP', name='Ibovespa', price=124500, change=1250, change_percent=1.01, updated_at=now),
            'sp500': MarketQuote(symbol='^GSPC', name='S&P 500', price=6050, change=25, change_percent=0.41, updated_at=now),
            'dolar': MarketQuote(symbol='USDBRL', name='Dólar', price=6.15, change=0.03, change_percent=0.49, updated_at=now),
            'euro': MarketQuote(symbol='EURBRL', name='Euro', price=6.45, change=0.02, change_percent=0.31, updated_at=now),
            'bitcoin': MarketQuote(symbol='BTC', name='Bitcoin', price=106500, change=1200, change_percent=1.14, updated_at=now),
        }
    
    # ========================================================================
    # AGREGADORES
    # ========================================================================
    
    async def get_homepage_data(self) -> Dict[str, Any]:
        """Retorna todos os dados para a homepage do portal."""
        try:
            # Busca dados em paralelo (cuidado com rate limit da Brapi)
            indices_task = self.get_market_indices()
            calendar_task = self.get_economic_calendar(days=0)
            forex_news_task = self.get_forex_news(limit=10)
            br_news_task = self.get_eodhd_news(limit=10)
            
            # Brapi quotes separado para não sobrecarregar
            indices, calendar, forex_news, br_news = await asyncio.gather(
                indices_task, calendar_task, forex_news_task, br_news_task
            )
            
            # Busca cotações brasileiras com delay
            await asyncio.sleep(2)
            br_quotes = await self.get_brazil_quotes()
            
            # Combina notícias
            all_news = []
            for n in forex_news:
                all_news.append(n.to_dict())
            for n in br_news:
                all_news.append(n.to_dict())
            
            # Ordena por data
            all_news.sort(key=lambda x: x.get('published_at', ''), reverse=True)
            
            # Eventos de alto impacto
            high_impact_events = [e.to_dict() for e in calendar if e.impact == 'high'][:5]
            
            return {
                'success': True,
                'timestamp': get_brazil_now().isoformat(),
                'market': {
                    'indices': {k: v.to_dict() for k, v in indices.items()},
                    'brazil_stocks': [q.to_dict() for q in br_quotes[:10]],
                },
                'news': {
                    'latest': all_news[:15],
                    'forex': [n.to_dict() for n in forex_news[:5]],
                    'brazil': [n.to_dict() for n in br_news[:5]],
                },
                'calendar': {
                    'today': [e.to_dict() for e in calendar[:15]],
                    'high_impact': high_impact_events,
                },
                'summary': {
                    'market_status': self._get_market_status(indices),
                    'sentiment': self._analyze_news_sentiment(all_news),
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar dados da homepage: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_market_status(self, indices: Dict[str, MarketQuote]) -> str:
        """Retorna status geral do mercado."""
        if not indices:
            return "Dados indisponíveis"
        
        positive = 0
        negative = 0
        
        for key, quote in indices.items():
            if key in ['ibovespa', 'sp500', 'nasdaq']:
                if quote.change_percent > 0.3:
                    positive += 1
                elif quote.change_percent < -0.3:
                    negative += 1
        
        if positive > negative:
            return "Mercados em alta"
        elif negative > positive:
            return "Mercados em baixa"
        return "Mercados estáveis"
    
    def _analyze_news_sentiment(self, news: List[Dict]) -> Dict[str, Any]:
        """Analisa sentimento geral das notícias."""
        if not news:
            return {'overall': 'neutral', 'bullish': 0, 'bearish': 0, 'neutral': 0}
        
        counts = {'bullish': 0, 'bearish': 0, 'neutral': 0}
        for n in news:
            sent = n.get('sentiment', 'neutral')
            if sent in counts:
                counts[sent] += 1
        
        total = sum(counts.values())
        if total == 0:
            return {'overall': 'neutral', **counts}
        
        if counts['bullish'] > counts['bearish'] * 1.5:
            overall = 'bullish'
        elif counts['bearish'] > counts['bullish'] * 1.5:
            overall = 'bearish'
        else:
            overall = 'neutral'
        
        return {'overall': overall, **counts}


# Singleton
_portal_service: Optional[PortalService] = None


def get_portal_service() -> PortalService:
    """Retorna instância singleton do serviço."""
    global _portal_service
    if _portal_service is None:
        _portal_service = PortalService()
    return _portal_service
