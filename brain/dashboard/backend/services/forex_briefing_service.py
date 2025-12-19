"""
VIRTUS Dashboard - Forex Briefing Service
==========================================

Serviço completo de briefing para operações Forex:
- Agregação de notícias de múltiplas fontes (EODHD, ForexNews)
- Calendário econômico focado em forex
- Análise de sentimento com TESS AI
- Geração de áudio em português
- Sinais indicativos por símbolo
"""

import asyncio
import aiohttp
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
import logging
import hashlib
import json
import sys

try:
    import pytz
    BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')
except ImportError:
    BRAZIL_TZ = None

def get_brazil_now() -> datetime:
    """Retorna datetime atual no fuso horário do Brasil."""
    if BRAZIL_TZ:
        return datetime.now(BRAZIL_TZ)
    # Fallback: UTC-3 manual
    return datetime.utcnow() - timedelta(hours=3)

def format_brazil_date(dt: datetime = None) -> str:
    """Formata data no padrão brasileiro."""
    if dt is None:
        dt = get_brazil_now()
    return dt.strftime('%d/%m/%Y')

logger = logging.getLogger(__name__)

# Paths para imports do Brain
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

# Constantes
FOREX_SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY']
FOREX_CURRENCIES = {
    'XAUUSD': ['XAU', 'USD', 'gold', 'ouro'],
    'EURUSD': ['EUR', 'USD', 'euro'],
    'GBPUSD': ['GBP', 'USD', 'libra', 'pound', 'cable'],
    'USDJPY': ['USD', 'JPY', 'iene', 'yen'],
}
FOREX_COUNTRIES = ['US', 'EU', 'GB', 'JP', 'CH']  # Países relevantes para forex

# API Keys (carregadas do ambiente ou config)
EODHD_API_KEY = os.getenv("EODHD_API_KEY", "")
FOREXNEWS_API_KEY = ""  # Será carregado do config


class MarketDirection(str, Enum):
    """Direção do mercado"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class ImpactLevel(str, Enum):
    """Nível de impacto"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ForexNews:
    """Notícia relevante para forex"""
    id: str
    title: str
    summary: str
    content: str
    source: str
    provider: str  # 'eodhd', 'forexnews'
    published_at: datetime
    url: Optional[str] = None
    
    # Relevância para forex
    symbols: List[str] = field(default_factory=list)
    currencies: List[str] = field(default_factory=list)
    
    # Análise
    sentiment: MarketDirection = MarketDirection.NEUTRAL
    sentiment_score: float = 0.0
    impact: ImpactLevel = ImpactLevel.MEDIUM
    
    # Áudio
    audio_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'content': self.content,
            'source': self.source,
            'provider': self.provider,
            'published_at': self.published_at.isoformat(),
            'url': self.url,
            'symbols': self.symbols,
            'currencies': self.currencies,
            'sentiment': self.sentiment.value,
            'sentiment_score': self.sentiment_score,
            'impact': self.impact.value,
            'audio_url': self.audio_url,
        }


@dataclass
class EconomicEvent:
    """Evento do calendário econômico"""
    id: str
    name: str
    country: str
    date: datetime
    
    # Valores
    actual: Optional[str] = None
    previous: Optional[str] = None
    forecast: Optional[str] = None
    
    # Impacto
    impact: ImpactLevel = ImpactLevel.MEDIUM
    
    # Moedas afetadas
    currencies_affected: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'country': self.country,
            'date': self.date.isoformat(),
            'actual': self.actual,
            'previous': self.previous,
            'forecast': self.forecast,
            'impact': self.impact.value,
            'currencies_affected': self.currencies_affected,
        }


@dataclass
class SymbolSignal:
    """Sinal indicativo para um símbolo"""
    symbol: str
    direction: MarketDirection
    strength: float  # 0 a 1
    
    # Fatores
    news_sentiment: MarketDirection
    calendar_impact: str
    technical_bias: Optional[str] = None
    
    # Resumo
    summary: str = ""
    key_events: List[str] = field(default_factory=list)
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'direction': self.direction.value,
            'strength': self.strength,
            'news_sentiment': self.news_sentiment.value,
            'calendar_impact': self.calendar_impact,
            'technical_bias': self.technical_bias,
            'summary': self.summary,
            'key_events': self.key_events,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class DailyBriefing:
    """Briefing diário completo"""
    date: datetime
    
    # Resumo geral
    market_mood: MarketDirection
    headline: str
    summary: str
    
    # Detalhes por símbolo
    signals: Dict[str, SymbolSignal] = field(default_factory=dict)
    
    # Notícias principais
    top_news: List[ForexNews] = field(default_factory=list)
    
    # Calendário do dia
    key_events: List[EconomicEvent] = field(default_factory=list)
    
    # Para redes sociais
    social_post: str = ""
    
    # Áudio
    audio_url: Optional[str] = None
    audio_text: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date.isoformat(),
            'market_mood': self.market_mood.value,
            'headline': self.headline,
            'summary': self.summary,
            'signals': {k: v.to_dict() for k, v in self.signals.items()},
            'top_news': [n.to_dict() for n in self.top_news],
            'key_events': [e.to_dict() for e in self.key_events],
            'social_post': self.social_post,
            'audio_url': self.audio_url,
            'audio_text': self.audio_text,
        }


class ForexBriefingService:
    """
    Serviço de briefing Forex integrado.
    
    Fontes de dados:
    - EODHD: Notícias, calendário, dados macro
    - ForexNews API: Notícias em tempo real, sentimento
    - TESS AI: Análise e resumos em português
    
    Funcionalidades:
    - Agregação de notícias relevantes
    - Calendário econômico filtrado
    - Sinais indicativos por símbolo
    - Briefing diário com áudio
    """
    
    def __init__(self):
        self.logger = logging.getLogger("forex_briefing")
        
        # APIs
        self._eodhd_key = EODHD_API_KEY
        self._forexnews_key = self._load_forexnews_key()
        
        # TESS (opcional)
        self._tess_analyzer = None
        self._tess_available = False
        
        # TTS
        self._tts = None
        
        # Cache
        self._news_cache: Dict[str, ForexNews] = {}
        self._events_cache: List[EconomicEvent] = []
        self._briefing_cache: Optional[DailyBriefing] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=15)
        
        # Inicialização assíncrona
        self._initialized = False
    
    def _load_forexnews_key(self) -> str:
        """Carrega chave da ForexNews API do config"""
        try:
            config_path = BRAIN_PATH / "config" / "config.yaml"
            if config_path.exists():
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config.get('api_keys', {}).get('forexnews', '')
        except Exception as e:
            self.logger.warning(f"Não foi possível carregar ForexNews key: {e}")
        return ""
    
    async def initialize(self):
        """Inicializa o serviço"""
        if self._initialized:
            return
        
        # Tenta inicializar TESS
        try:
            from src.integrations.tess.market_analyzer import TessMarketAnalyzer
            self._tess_analyzer = TessMarketAnalyzer()
            await self._tess_analyzer.initialize()
            self._tess_available = True
            self.logger.info("✅ TESS AI disponível para análise")
        except Exception as e:
            self.logger.warning(f"TESS não disponível: {e}")
        
        # Inicializa TTS
        try:
            from services.news_service import TextToSpeechService
            self._tts = TextToSpeechService()
            self.logger.info("✅ TTS disponível para áudio")
        except Exception as e:
            self.logger.warning(f"TTS não disponível: {e}")
        
        self._initialized = True
    
    # ========================================================================
    # NOTÍCIAS
    # ========================================================================
    
    async def get_forex_news(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 20,
        hours_back: int = 24
    ) -> List[ForexNews]:
        """
        Busca notícias relevantes para forex de múltiplas fontes.
        
        Args:
            symbols: Símbolos específicos ou None para todos
            limit: Número máximo de notícias
            hours_back: Horas no passado
            
        Returns:
            Lista de ForexNews ordenada por relevância
        """
        await self.initialize()
        
        symbols = symbols or FOREX_SYMBOLS
        all_news: List[ForexNews] = []
        
        # Busca paralela de múltiplas fontes
        tasks = [
            self._fetch_eodhd_news(symbols, limit),
            self._fetch_forexnews(symbols, limit) if self._forexnews_key else asyncio.sleep(0),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # EODHD news
        if isinstance(results[0], list):
            all_news.extend(results[0])
        
        # ForexNews
        if len(results) > 1 and isinstance(results[1], list):
            all_news.extend(results[1])
        
        # Remove duplicatas (por título similar)
        unique_news = self._deduplicate_news(all_news)
        
        # Ordena por relevância (impacto + recência)
        unique_news.sort(
            key=lambda n: (
                n.impact == ImpactLevel.HIGH,
                n.published_at
            ),
            reverse=True
        )
        
        # Análise com TESS se disponível
        if self._tess_available and unique_news:
            unique_news = await self._analyze_news_with_tess(unique_news[:10])
        
        return unique_news[:limit]
    
    async def _fetch_eodhd_news(
        self,
        symbols: List[str],
        limit: int
    ) -> List[ForexNews]:
        """Busca notícias do EODHD"""
        news = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Busca notícias gerais de forex
                url = "https://eodhd.com/api/news"
                params = {
                    'api_token': self._eodhd_key,
                    'fmt': 'json',
                    's': 'EURUSD.FOREX,GBPUSD.FOREX',
                    'limit': limit,
                }
                
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        for item in data:
                            # Filtra por relevância forex
                            title = item.get('title', '').lower()
                            content = item.get('content', '').lower()
                            
                            # Verifica se é relevante para forex
                            relevant_symbols = self._identify_symbols(title + " " + content)
                            if not relevant_symbols:
                                continue
                            
                            # Parse sentimento da API
                            sentiment_data = item.get('sentiment', {})
                            polarity = sentiment_data.get('polarity', 0)
                            
                            if polarity > 0.3:
                                sentiment = MarketDirection.BULLISH
                            elif polarity < -0.3:
                                sentiment = MarketDirection.BEARISH
                            else:
                                sentiment = MarketDirection.NEUTRAL
                            
                            news_item = ForexNews(
                                id=hashlib.md5(item.get('title', '').encode()).hexdigest()[:12],
                                title=item.get('title', ''),
                                summary=item.get('content', '')[:300] + '...' if len(item.get('content', '')) > 300 else item.get('content', ''),
                                content=item.get('content', ''),
                                source=item.get('source', 'EODHD'),
                                provider='eodhd',
                                published_at=datetime.fromisoformat(item.get('date', '').replace('Z', '+00:00')) if item.get('date') else datetime.now(),
                                url=item.get('link'),
                                symbols=relevant_symbols,
                                currencies=self._get_currencies_from_symbols(relevant_symbols),
                                sentiment=sentiment,
                                sentiment_score=polarity,
                                impact=self._determine_impact(title, content),
                            )
                            news.append(news_item)
                            
        except Exception as e:
            self.logger.error(f"Erro ao buscar notícias EODHD: {e}")
        
        return news
    
    async def _fetch_forexnews(
        self,
        symbols: List[str],
        limit: int
    ) -> List[ForexNews]:
        """Busca notícias do ForexNews API"""
        news = []
        
        if not self._forexnews_key:
            return news
        
        try:
            async with aiohttp.ClientSession() as session:
                for symbol in symbols[:3]:  # Top 3 símbolos
                    currency_pair = self._symbol_to_forexnews_format(symbol)
                    
                    url = "https://forexnewsapi.com/api/v1"
                    params = {
                        'token': self._forexnews_key,
                        'currencypair': currency_pair,
                        'items': limit // 3,
                    }
                    
                    async with session.get(url, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            for item in data.get('data', []):
                                news_item = ForexNews(
                                    id=hashlib.md5(item.get('title', '').encode()).hexdigest()[:12],
                                    title=item.get('title', ''),
                                    summary=item.get('description', ''),
                                    content=item.get('content', ''),
                                    source=item.get('source', 'ForexNews'),
                                    provider='forexnews',
                                    published_at=datetime.fromisoformat(item.get('date', '').replace('Z', '+00:00')) if item.get('date') else datetime.now(),
                                    url=item.get('url'),
                                    symbols=[symbol],
                                    currencies=self._get_currencies_from_symbols([symbol]),
                                    sentiment=self._parse_forexnews_sentiment(item),
                                    impact=ImpactLevel.MEDIUM,
                                )
                                news.append(news_item)
                                
        except Exception as e:
            self.logger.error(f"Erro ao buscar ForexNews: {e}")
        
        return news
    
    def _symbol_to_forexnews_format(self, symbol: str) -> str:
        """Converte símbolo para formato ForexNews (EUR-USD)"""
        mapping = {
            'XAUUSD': 'XAU-USD',
            'EURUSD': 'EUR-USD',
            'GBPUSD': 'GBP-USD',
            'USDJPY': 'USD-JPY',
        }
        return mapping.get(symbol, symbol)
    
    def _identify_symbols(self, text: str) -> List[str]:
        """Identifica símbolos forex mencionados no texto"""
        text_lower = text.lower()
        found = []
        
        for symbol, keywords in FOREX_CURRENCIES.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if symbol not in found:
                        found.append(symbol)
                    break
        
        return found
    
    def _get_currencies_from_symbols(self, symbols: List[str]) -> List[str]:
        """Obtém moedas dos símbolos"""
        currencies = set()
        for symbol in symbols:
            if symbol in FOREX_CURRENCIES:
                currencies.update(FOREX_CURRENCIES[symbol][:2])  # Só as moedas, não keywords
        return list(currencies)
    
    def _determine_impact(self, title: str, content: str) -> ImpactLevel:
        """Determina impacto da notícia"""
        high_impact_keywords = [
            'fed', 'fomc', 'rate decision', 'interest rate', 'inflation',
            'cpi', 'nfp', 'payroll', 'gdp', 'recession', 'crash',
            'breaking', 'urgent', 'surprise', 'shock',
        ]
        
        medium_impact_keywords = [
            'pmi', 'manufacturing', 'employment', 'jobs', 'retail',
            'housing', 'trade', 'balance', 'sentiment',
        ]
        
        text = (title + " " + content).lower()
        
        for keyword in high_impact_keywords:
            if keyword in text:
                return ImpactLevel.HIGH
        
        for keyword in medium_impact_keywords:
            if keyword in text:
                return ImpactLevel.MEDIUM
        
        return ImpactLevel.LOW
    
    def _parse_forexnews_sentiment(self, item: Dict) -> MarketDirection:
        """Parse sentimento do ForexNews"""
        sentiment = item.get('sentiment', 'neutral')
        if sentiment in ['positive', 'very_positive', 'bullish']:
            return MarketDirection.BULLISH
        elif sentiment in ['negative', 'very_negative', 'bearish']:
            return MarketDirection.BEARISH
        return MarketDirection.NEUTRAL
    
    def _deduplicate_news(self, news: List[ForexNews]) -> List[ForexNews]:
        """Remove notícias duplicadas"""
        seen_titles = set()
        unique = []
        
        for item in news:
            # Normaliza título para comparação
            normalized = item.title.lower()[:50]
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(item)
        
        return unique
    
    async def _analyze_news_with_tess(
        self,
        news: List[ForexNews]
    ) -> List[ForexNews]:
        """Analisa notícias com TESS AI"""
        if not self._tess_analyzer:
            return news
        
        try:
            news_items = [
                {'title': n.title, 'content': n.content, 'source': n.source}
                for n in news
            ]
            
            result = await self._tess_analyzer.analyze_news_sentiment(news_items)
            
            if result:
                # Aplica sentimento geral às notícias
                if result.sentiment == 'bullish':
                    direction = MarketDirection.BULLISH
                elif result.sentiment == 'bearish':
                    direction = MarketDirection.BEARISH
                else:
                    direction = MarketDirection.NEUTRAL
                
                for n in news:
                    if n.sentiment == MarketDirection.NEUTRAL:
                        n.sentiment = direction
                        n.sentiment_score = result.confidence
                        
        except Exception as e:
            self.logger.warning(f"Erro na análise TESS: {e}")
        
        return news
    
    # ========================================================================
    # CALENDÁRIO ECONÔMICO
    # ========================================================================
    
    async def get_forex_calendar(
        self,
        days_ahead: int = 7,
        countries: Optional[List[str]] = None,
        min_impact: str = "medium"
    ) -> List[EconomicEvent]:
        """
        Obtém calendário econômico filtrado para forex.
        
        Args:
            days_ahead: Dias à frente para buscar
            countries: Países para filtrar (default: US, EU, GB, JP, CH)
            min_impact: Impacto mínimo ('low', 'medium', 'high')
            
        Returns:
            Lista de eventos ordenados por data
        """
        await self.initialize()
        
        countries = countries or FOREX_COUNTRIES
        events: List[EconomicEvent] = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # EODHD Calendar
                from_date = datetime.now()
                to_date = from_date + timedelta(days=days_ahead)
                
                url = "https://eodhd.com/api/economic-events"
                params = {
                    'api_token': self._eodhd_key,
                    'fmt': 'json',
                    'from': from_date.strftime('%Y-%m-%d'),
                    'to': to_date.strftime('%Y-%m-%d'),
                }
                
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        for item in data:
                            country = item.get('country', '')
                            
                            # Filtra por países relevantes
                            if country not in countries:
                                continue
                            
                            # Determina impacto
                            impact = self._determine_event_impact(item.get('type', ''))
                            
                            # Filtra por impacto mínimo
                            impact_order = {'low': 0, 'medium': 1, 'high': 2}
                            if impact_order.get(impact.value, 0) < impact_order.get(min_impact, 0):
                                continue
                            
                            event = EconomicEvent(
                                id=hashlib.md5(f"{item.get('type')}{item.get('date')}".encode()).hexdigest()[:12],
                                name=item.get('type', ''),
                                country=country,
                                date=datetime.strptime(item.get('date', ''), '%Y-%m-%d %H:%M:%S') if item.get('date') else datetime.now(),
                                actual=str(item.get('actual')) if item.get('actual') is not None else None,
                                previous=str(item.get('previous')) if item.get('previous') is not None else None,
                                forecast=str(item.get('estimate')) if item.get('estimate') is not None else None,
                                impact=impact,
                                currencies_affected=self._country_to_currencies(country),
                            )
                            events.append(event)
                            
        except Exception as e:
            self.logger.error(f"Erro ao buscar calendário: {e}")
        
        # Ordena por data
        events.sort(key=lambda e: e.date)
        
        return events
    
    def _determine_event_impact(self, event_type: str) -> ImpactLevel:
        """Determina impacto de um evento econômico"""
        event_lower = event_type.lower()
        
        high_impact = [
            'interest rate', 'rate decision', 'fomc', 'ecb', 'boe', 'boj',
            'nfp', 'non-farm', 'payroll', 'cpi', 'inflation', 'gdp',
            'pce', 'retail sales',
        ]
        
        medium_impact = [
            'pmi', 'manufacturing', 'services', 'employment', 'jobless',
            'trade balance', 'industrial', 'housing', 'consumer confidence',
        ]
        
        for keyword in high_impact:
            if keyword in event_lower:
                return ImpactLevel.HIGH
        
        for keyword in medium_impact:
            if keyword in event_lower:
                return ImpactLevel.MEDIUM
        
        return ImpactLevel.LOW
    
    def _country_to_currencies(self, country: str) -> List[str]:
        """Converte país para moedas afetadas"""
        mapping = {
            'US': ['USD'],
            'EU': ['EUR'],
            'GB': ['GBP'],
            'JP': ['JPY'],
            'CH': ['CHF'],
            'AU': ['AUD'],
            'CA': ['CAD'],
            'NZ': ['NZD'],
        }
        return mapping.get(country, [])
    
    # ========================================================================
    # SINAIS POR SÍMBOLO
    # ========================================================================
    
    async def get_symbol_signal(
        self,
        symbol: str
    ) -> SymbolSignal:
        """
        Gera sinal indicativo para um símbolo.
        
        Considera:
        - Sentimento das notícias
        - Eventos do calendário
        - Análise TESS (se disponível)
        
        Args:
            symbol: Símbolo forex (ex: XAUUSD)
            
        Returns:
            SymbolSignal com direção e resumo
        """
        await self.initialize()
        
        # Busca notícias do símbolo
        news = await self.get_forex_news(symbols=[symbol], limit=10, hours_back=24)
        
        # Busca eventos relevantes
        events = await self.get_forex_calendar(days_ahead=1, min_impact="medium")
        relevant_events = [
            e for e in events
            if any(c in e.currencies_affected for c in self._get_currencies_from_symbols([symbol]))
        ]
        
        # Analisa sentimento das notícias
        bullish_count = sum(1 for n in news if n.sentiment == MarketDirection.BULLISH)
        bearish_count = sum(1 for n in news if n.sentiment == MarketDirection.BEARISH)
        
        if bullish_count > bearish_count * 1.5:
            news_sentiment = MarketDirection.BULLISH
        elif bearish_count > bullish_count * 1.5:
            news_sentiment = MarketDirection.BEARISH
        elif bullish_count > 0 and bearish_count > 0:
            news_sentiment = MarketDirection.MIXED
        else:
            news_sentiment = MarketDirection.NEUTRAL
        
        # Impacto do calendário
        high_impact_events = [e for e in relevant_events if e.impact == ImpactLevel.HIGH]
        calendar_impact = "alto" if high_impact_events else "moderado" if relevant_events else "baixo"
        
        # Direção geral
        if news_sentiment in [MarketDirection.BULLISH, MarketDirection.BEARISH]:
            direction = news_sentiment
            strength = min(0.8, (abs(bullish_count - bearish_count) / max(len(news), 1)))
        else:
            direction = MarketDirection.NEUTRAL
            strength = 0.3
        
        # Gera resumo
        key_events = [e.name for e in relevant_events[:3]]
        top_news_titles = [n.title for n in news[:3]]
        
        summary = self._generate_symbol_summary(
            symbol, direction, news_sentiment, calendar_impact, key_events, top_news_titles
        )
        
        return SymbolSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            news_sentiment=news_sentiment,
            calendar_impact=calendar_impact,
            summary=summary,
            key_events=key_events,
        )
    
    def _generate_symbol_summary(
        self,
        symbol: str,
        direction: MarketDirection,
        news_sentiment: MarketDirection,
        calendar_impact: str,
        key_events: List[str],
        top_news: List[str]
    ) -> str:
        """Gera resumo textual do sinal"""
        symbol_names = {
            'XAUUSD': 'Ouro',
            'EURUSD': 'Euro/Dólar',
            'GBPUSD': 'Libra/Dólar',
            'USDJPY': 'Dólar/Iene',
        }
        
        name = symbol_names.get(symbol, symbol)
        
        direction_text = {
            MarketDirection.BULLISH: 'alta',
            MarketDirection.BEARISH: 'baixa',
            MarketDirection.NEUTRAL: 'lateral',
            MarketDirection.MIXED: 'indefinido',
        }
        
        summary = f"{name} com viés de {direction_text.get(direction, 'indefinido')}. "
        summary += f"Sentimento das notícias {direction_text.get(news_sentiment, 'neutro')}. "
        summary += f"Impacto do calendário {calendar_impact}."
        
        if key_events:
            summary += f" Eventos relevantes: {', '.join(key_events[:2])}."
        
        return summary
    
    # ========================================================================
    # BRIEFING DIÁRIO
    # ========================================================================
    
    async def get_daily_briefing(
        self,
        symbols: Optional[List[str]] = None,
        generate_audio: bool = True
    ) -> DailyBriefing:
        """
        Gera briefing diário completo.
        
        Inclui:
        - Humor geral do mercado
        - Sinais por símbolo
        - Top notícias
        - Eventos do dia
        - Texto para áudio
        - Post para redes sociais
        
        Args:
            symbols: Símbolos para incluir (default: todos)
            generate_audio: Se deve gerar áudio
            
        Returns:
            DailyBriefing completo
        """
        await self.initialize()
        
        # Verifica cache
        if self._briefing_cache and self._cache_time:
            if datetime.now() - self._cache_time < self._cache_ttl:
                return self._briefing_cache
        
        symbols = symbols or FOREX_SYMBOLS
        
        # Busca dados em paralelo
        news_task = self.get_forex_news(symbols=symbols, limit=10)
        events_task = self.get_forex_calendar(days_ahead=1, min_impact="medium")
        signals_tasks = [self.get_symbol_signal(s) for s in symbols]
        
        all_results = await asyncio.gather(
            news_task,
            events_task,
            *signals_tasks,
            return_exceptions=True
        )
        
        news = all_results[0] if isinstance(all_results[0], list) else []
        events = all_results[1] if isinstance(all_results[1], list) else []
        signals = {
            symbols[i]: all_results[2 + i]
            for i in range(len(symbols))
            if isinstance(all_results[2 + i], SymbolSignal)
        }
        
        # Determina humor geral
        bullish = sum(1 for s in signals.values() if s.direction == MarketDirection.BULLISH)
        bearish = sum(1 for s in signals.values() if s.direction == MarketDirection.BEARISH)
        
        if bullish > bearish:
            market_mood = MarketDirection.BULLISH
            mood_text = "otimista"
        elif bearish > bullish:
            market_mood = MarketDirection.BEARISH
            mood_text = "cauteloso"
        else:
            market_mood = MarketDirection.NEUTRAL
            mood_text = "misto"
        
        # Headline
        today = datetime.now()
        headline = f"Mercado {mood_text} nesta {today.strftime('%A')}"
        
        # Resumo geral
        summary = self._generate_briefing_summary(news, events, signals, market_mood)
        
        # Texto para áudio
        audio_text = self._generate_audio_text(news, events, signals, market_mood, today)
        
        # Post para redes sociais
        social_post = self._generate_social_post(news, events, market_mood, today)
        
        briefing = DailyBriefing(
            date=today,
            market_mood=market_mood,
            headline=headline,
            summary=summary,
            signals=signals,
            top_news=news[:5],
            key_events=[e for e in events if e.impact == ImpactLevel.HIGH][:5],
            social_post=social_post,
            audio_text=audio_text,
        )
        
        # Gera áudio se solicitado
        if generate_audio and self._tts and audio_text:
            try:
                audio_path = await self._tts.text_to_speech(audio_text)
                if audio_path:
                    briefing.audio_url = f"/api/forex/briefing/audio/{audio_path.name}"
            except Exception as e:
                self.logger.warning(f"Erro ao gerar áudio: {e}")
        
        # Atualiza cache
        self._briefing_cache = briefing
        self._cache_time = datetime.now()
        
        return briefing
    
    def _generate_briefing_summary(
        self,
        news: List[ForexNews],
        events: List[EconomicEvent],
        signals: Dict[str, SymbolSignal],
        market_mood: MarketDirection
    ) -> str:
        """Gera resumo do briefing"""
        mood_text = {
            MarketDirection.BULLISH: "otimista com viés de alta",
            MarketDirection.BEARISH: "cauteloso com viés de baixa",
            MarketDirection.NEUTRAL: "misto aguardando direção",
            MarketDirection.MIXED: "dividido entre otimismo e cautela",
        }
        
        summary = f"O mercado forex está {mood_text.get(market_mood, 'indefinido')} hoje. "
        
        high_impact = [e for e in events if e.impact == ImpactLevel.HIGH]
        if high_impact:
            summary += f"Atenção para {len(high_impact)} evento(s) de alto impacto: "
            summary += ", ".join([e.name for e in high_impact[:3]])
            summary += ". "
        
        if news:
            bullish_news = sum(1 for n in news if n.sentiment == MarketDirection.BULLISH)
            bearish_news = sum(1 for n in news if n.sentiment == MarketDirection.BEARISH)
            summary += f"Das {len(news)} notícias principais, {bullish_news} são positivas e {bearish_news} negativas."
        
        return summary
    
    def _generate_audio_text(
        self,
        news: List[ForexNews],
        events: List[EconomicEvent],
        signals: Dict[str, SymbolSignal],
        market_mood: MarketDirection,
        date: datetime
    ) -> str:
        """Gera texto para áudio do briefing"""
        weekday_names = {
            0: 'segunda-feira', 1: 'terça-feira', 2: 'quarta-feira',
            3: 'quinta-feira', 4: 'sexta-feira', 5: 'sábado', 6: 'domingo'
        }
        
        mood_text = {
            MarketDirection.BULLISH: "otimista",
            MarketDirection.BEARISH: "cauteloso",
            MarketDirection.NEUTRAL: "neutro",
            MarketDirection.MIXED: "misto",
        }
        
        text = f"Bom dia, trader! Hoje é {weekday_names.get(date.weekday(), '')}, "
        text += f"dia {date.day} de {date.strftime('%B')} de {date.year}. "
        text += f"O mercado forex está com sentimento {mood_text.get(market_mood, 'indefinido')}. "
        
        # Sinais por símbolo
        symbol_names = {
            'XAUUSD': 'Ouro',
            'EURUSD': 'Euro dólar',
            'GBPUSD': 'Libra dólar',
            'USDJPY': 'Dólar iene',
        }
        
        for symbol, signal in signals.items():
            name = symbol_names.get(symbol, symbol)
            direction = 'alta' if signal.direction == MarketDirection.BULLISH else 'baixa' if signal.direction == MarketDirection.BEARISH else 'indefinida'
            text += f"{name} com viés de {direction}. "
        
        # Eventos importantes
        high_impact = [e for e in events if e.impact == ImpactLevel.HIGH]
        if high_impact:
            text += "Eventos de alto impacto hoje: "
            for event in high_impact[:3]:
                text += f"{event.name} às {event.date.strftime('%H:%M')}. "
        
        # Top notícias
        if news:
            text += "Principais notícias: "
            for n in news[:3]:
                text += f"{n.title}. "
        
        text += "Opere com sabedoria e bons trades!"
        
        return text
    
    def _generate_social_post(
        self,
        news: List[ForexNews],
        events: List[EconomicEvent],
        market_mood: MarketDirection,
        date: datetime
    ) -> str:
        """Gera post para redes sociais"""
        mood_emoji = {
            MarketDirection.BULLISH: "📈",
            MarketDirection.BEARISH: "📉",
            MarketDirection.NEUTRAL: "➡️",
            MarketDirection.MIXED: "🔄",
        }
        
        emoji = mood_emoji.get(market_mood, "📊")
        
        post = f"{emoji} BRIEFING FOREX - {date.strftime('%d/%m/%Y')}\n\n"
        
        mood_text = {
            MarketDirection.BULLISH: "Mercado otimista",
            MarketDirection.BEARISH: "Mercado cauteloso",
            MarketDirection.NEUTRAL: "Mercado neutro",
            MarketDirection.MIXED: "Mercado misto",
        }
        
        post += f"🎯 {mood_text.get(market_mood, 'Mercado indefinido')}\n\n"
        
        # Eventos
        high_impact = [e for e in events if e.impact == ImpactLevel.HIGH]
        if high_impact:
            post += "⚠️ EVENTOS IMPORTANTES:\n"
            for event in high_impact[:3]:
                post += f"• {event.name} ({event.country}) - {event.date.strftime('%H:%M')}\n"
            post += "\n"
        
        # Top notícias
        if news:
            post += "📰 DESTAQUES:\n"
            for n in news[:2]:
                sentiment_emoji = "🟢" if n.sentiment == MarketDirection.BULLISH else "🔴" if n.sentiment == MarketDirection.BEARISH else "⚪"
                post += f"{sentiment_emoji} {n.title[:60]}...\n"
        
        post += "\n#Forex #Trading #XAUUSD #EURUSD #MercadoFinanceiro"
        
        return post


# Instância global
forex_briefing_service = ForexBriefingService()
