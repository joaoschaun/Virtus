"""
VIRTUS Dashboard - Daily Briefing Service
==========================================

Serviço completo de briefing diário com:
- Notícias relevantes do mercado
- Calendário econômico do dia
- Ações com limite de compra para dividendos
- Sentimento geral do mercado
- Geração de áudio em português (TTS)
"""

import asyncio
import aiohttp
import hashlib
import json
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging

try:
    import pytz
    BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')
except ImportError:
    BRAZIL_TZ = None

logger = logging.getLogger(__name__)

# Paths
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
DATA_PATH = BRAIN_PATH / "data"
AUDIO_CACHE_DIR = DATA_PATH / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# API Keys (lidas do ambiente - ver .env)
EODHD_API_KEY = os.getenv("EODHD_API_KEY", "")
BRAPI_API_KEY = os.getenv("BRAPI_API_KEY", "")


def get_brazil_now() -> datetime:
    """Retorna datetime atual no fuso horário do Brasil."""
    if BRAZIL_TZ:
        return datetime.now(BRAZIL_TZ)
    return datetime.utcnow() - timedelta(hours=3)


def format_brazil_date(dt: datetime = None) -> str:
    """Formata data no padrão brasileiro."""
    if dt is None:
        dt = get_brazil_now()
    return dt.strftime('%d/%m/%Y')


def get_weekday_name(dt: datetime = None) -> str:
    """Retorna nome do dia da semana em português."""
    if dt is None:
        dt = get_brazil_now()
    days = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 
            'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    return days[dt.weekday()]


class MarketSentiment(str, Enum):
    """Sentimento do mercado."""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


class EventImpact(str, Enum):
    """Impacto do evento."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class NewsItem:
    """Notícia do briefing."""
    title: str
    summary: str
    source: str
    category: str
    sentiment: str  # bullish, bearish, neutral
    impact: str  # high, medium, low
    url: Optional[str] = None
    published_at: Optional[str] = None


@dataclass
class EconomicEvent:
    """Evento do calendário econômico."""
    time: str
    country: str
    event: str
    impact: EventImpact
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


@dataclass
class DividendAlert:
    """Alerta de dividendo."""
    ticker: str
    company_name: str
    buy_limit_date: str
    ex_date: str
    payment_date: Optional[str]
    dividend_value: float
    dividend_yield: float
    days_remaining: int
    urgency: str  # urgent, today, soon


@dataclass
class MarketOverview:
    """Visão geral do mercado."""
    ibovespa: Dict[str, Any]
    dolar: Dict[str, Any]
    sp500: Dict[str, Any]
    sentiment: MarketSentiment
    sentiment_description: str


@dataclass
class DailyBriefing:
    """Briefing diário completo."""
    date: str
    weekday: str
    greeting: str
    market_overview: MarketOverview
    top_news: List[NewsItem]
    economic_calendar: List[EconomicEvent]
    dividend_alerts: List[DividendAlert]
    summary_text: str
    audio_text: str
    audio_url: Optional[str] = None
    generated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date,
            'weekday': self.weekday,
            'greeting': self.greeting,
            'market_overview': {
                'ibovespa': self.market_overview.ibovespa,
                'dolar': self.market_overview.dolar,
                'sp500': self.market_overview.sp500,
                'sentiment': self.market_overview.sentiment.value,
                'sentiment_description': self.market_overview.sentiment_description
            },
            'top_news': [
                {
                    'title': n.title,
                    'summary': n.summary,
                    'source': n.source,
                    'category': n.category,
                    'sentiment': n.sentiment,
                    'impact': n.impact,
                    'url': n.url,
                    'published_at': n.published_at
                } for n in self.top_news
            ],
            'economic_calendar': [
                {
                    'time': e.time,
                    'country': e.country,
                    'event': e.event,
                    'impact': e.impact.value,
                    'actual': e.actual,
                    'forecast': e.forecast,
                    'previous': e.previous
                } for e in self.economic_calendar
            ],
            'dividend_alerts': [
                {
                    'ticker': d.ticker,
                    'company_name': d.company_name,
                    'buy_limit_date': d.buy_limit_date,
                    'ex_date': d.ex_date,
                    'payment_date': d.payment_date,
                    'dividend_value': d.dividend_value,
                    'dividend_yield': d.dividend_yield,
                    'days_remaining': d.days_remaining,
                    'urgency': d.urgency
                } for d in self.dividend_alerts
            ],
            'summary_text': self.summary_text,
            'audio_text': self.audio_text,
            'audio_url': self.audio_url,
            'generated_at': self.generated_at
        }


class DailyBriefingService:
    """Serviço de briefing diário."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutos
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtém ou cria sessão HTTP."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'VIRTUS-Dashboard/1.0'}
            )
        return self.session
    
    async def close(self):
        """Fecha sessão HTTP."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def generate_briefing(self) -> DailyBriefing:
        """Gera briefing diário completo."""
        now = get_brazil_now()
        today_str = now.strftime('%Y-%m-%d')
        
        # Verifica cache
        cache_key = f"briefing_{today_str}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if (now.timestamp() - cached['timestamp']) < self._cache_ttl:
                return cached['data']
        
        # Busca dados em paralelo
        market_task = self._fetch_market_data()
        news_task = self._fetch_news()
        calendar_task = self._fetch_economic_calendar()
        dividends_task = self._fetch_dividend_alerts()
        
        market_data, news, calendar, dividends = await asyncio.gather(
            market_task, news_task, calendar_task, dividends_task,
            return_exceptions=True
        )
        
        # Trata exceções
        if isinstance(market_data, Exception):
            logger.error(f"Erro ao buscar dados de mercado: {market_data}")
            market_data = self._get_default_market_data()
        
        if isinstance(news, Exception):
            logger.error(f"Erro ao buscar notícias: {news}")
            news = []
        
        if isinstance(calendar, Exception):
            logger.error(f"Erro ao buscar calendário: {calendar}")
            calendar = []
        
        if isinstance(dividends, Exception):
            logger.error(f"Erro ao buscar dividendos: {dividends}")
            dividends = []
        
        # Determina saudação baseada na hora
        hour = now.hour
        if 5 <= hour < 12:
            greeting = "Bom dia"
        elif 12 <= hour < 18:
            greeting = "Boa tarde"
        else:
            greeting = "Boa noite"
        
        # Gera texto de resumo e áudio
        summary_text, audio_text = self._generate_summary_texts(
            market_data, news, calendar, dividends, greeting, now
        )
        
        # Cria briefing
        briefing = DailyBriefing(
            date=format_brazil_date(now),
            weekday=get_weekday_name(now),
            greeting=greeting,
            market_overview=market_data,
            top_news=news[:5],  # Top 5 notícias
            economic_calendar=calendar[:10],  # Top 10 eventos
            dividend_alerts=dividends,
            summary_text=summary_text,
            audio_text=audio_text,
            generated_at=now.isoformat()
        )
        
        # Cache
        self._cache[cache_key] = {
            'data': briefing,
            'timestamp': now.timestamp()
        }
        
        return briefing
    
    async def _fetch_market_data(self) -> MarketOverview:
        """Busca dados de mercado via Brapi API (Premium)."""
        session = await self._get_session()
        results = {}
        
        try:
            # 1. Busca índices (Ibovespa e S&P 500) via Brapi
            symbols = '%5EBVSP,%5EGSPC'  # URL encoded: ^BVSP,^GSPC
            url = f"https://brapi.dev/api/quote/{symbols}"
            params = {'token': BRAPI_API_KEY}
            
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for item in data.get('results', []):
                        symbol = item.get('symbol', '')
                        price = item.get('regularMarketPrice', 0)
                        change = item.get('regularMarketChange', 0)
                        change_pct = item.get('regularMarketChangePercent', 0)
                        
                        if symbol == '^BVSP':
                            results['ibovespa'] = {
                                'value': price,
                                'change': change,
                                'change_percent': change_pct,
                                'direction': 'up' if change >= 0 else 'down'
                            }
                        elif symbol == '^GSPC':
                            results['sp500'] = {
                                'value': price,
                                'change': change,
                                'change_percent': change_pct,
                                'direction': 'up' if change >= 0 else 'down'
                            }
                else:
                    logger.warning(f"Brapi índices retornou status {resp.status}")
            
            # 2. Busca moedas via Brapi
            await asyncio.sleep(1)  # Rate limit
            currency_url = "https://brapi.dev/api/v2/currency"
            currency_params = {'currency': 'USD-BRL', 'token': BRAPI_API_KEY}
            
            async with session.get(currency_url, params=currency_params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for curr in data.get('currency', []):
                        from_curr = curr.get('fromCurrency', '')
                        if from_curr == 'USD':
                            try:
                                bid_price = float(curr.get('bidPrice', 0) or 0)
                                pct_change = float(curr.get('percentageChange', 0) or 0)
                                bid_var = float(curr.get('bidVariation', 0) or 0)
                                
                                results['dolar'] = {
                                    'value': bid_price,
                                    'change': bid_var,
                                    'change_percent': pct_change,
                                    'direction': 'up' if bid_var >= 0 else 'down'
                                }
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Erro convertendo dados dolar: {e}")
                else:
                    logger.warning(f"Brapi moedas retornou status {resp.status}")
                    
        except Exception as e:
            logger.error(f"Erro ao buscar dados Brapi: {e}")
        
        # Aplica defaults para índices não encontrados
        if 'ibovespa' not in results:
            results['ibovespa'] = self._get_default_index()
        if 'sp500' not in results:
            results['sp500'] = self._get_default_index()
        if 'dolar' not in results:
            results['dolar'] = self._get_default_index()
        
        # Determina sentimento geral
        sentiment, description = self._analyze_market_sentiment(results)
        
        return MarketOverview(
            ibovespa=results.get('ibovespa', self._get_default_index()),
            dolar=results.get('dolar', self._get_default_index()),
            sp500=results.get('sp500', self._get_default_index()),
            sentiment=sentiment,
            sentiment_description=description
        )
    
    def _get_default_index(self) -> Dict:
        return {'value': 0, 'change': 0, 'change_percent': 0, 'direction': 'neutral'}
    
    def _get_default_market_data(self) -> MarketOverview:
        return MarketOverview(
            ibovespa=self._get_default_index(),
            dolar=self._get_default_index(),
            sp500=self._get_default_index(),
            sentiment=MarketSentiment.NEUTRAL,
            sentiment_description="Dados de mercado indisponíveis"
        )
    
    def _analyze_market_sentiment(self, data: Dict) -> tuple:
        """Analisa sentimento do mercado."""
        positive = 0
        negative = 0
        
        # Ibovespa
        if data.get('ibovespa', {}).get('change_percent', 0) > 0.5:
            positive += 2
        elif data.get('ibovespa', {}).get('change_percent', 0) < -0.5:
            negative += 2
        
        # Dólar (invertido - dólar caindo é bom para Brasil)
        if data.get('dolar', {}).get('change_percent', 0) < -0.3:
            positive += 1
        elif data.get('dolar', {}).get('change_percent', 0) > 0.3:
            negative += 1
        
        # S&P 500
        if data.get('sp500', {}).get('change_percent', 0) > 0.3:
            positive += 1
        elif data.get('sp500', {}).get('change_percent', 0) < -0.3:
            negative += 1
        
        score = positive - negative
        
        if score >= 3:
            return MarketSentiment.VERY_BULLISH, "Mercado muito otimista hoje. Tendência de alta generalizada."
        elif score >= 1:
            return MarketSentiment.BULLISH, "Mercado com viés positivo. Principais índices em alta."
        elif score <= -3:
            return MarketSentiment.VERY_BEARISH, "Mercado muito pessimista. Cautela recomendada."
        elif score <= -1:
            return MarketSentiment.BEARISH, "Mercado com viés negativo. Tendência de baixa."
        else:
            return MarketSentiment.NEUTRAL, "Mercado estável, sem tendência definida."
    
    async def _fetch_news(self) -> List[NewsItem]:
        """Busca notícias relevantes."""
        session = await self._get_session()
        news_list = []
        
        try:
            # EODHD News API
            url = "https://eodhd.com/api/news"
            params = {
                'api_token': EODHD_API_KEY,
                's': 'PETR4.SA,VALE3.SA,ITUB4.SA,BBDC4.SA,B3SA3.SA',
                'limit': 10,
                'offset': 0
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for item in data[:10]:
                        # Determina sentimento baseado em palavras-chave
                        title = item.get('title', '').lower()
                        sentiment = 'neutral'
                        if any(w in title for w in ['alta', 'sobe', 'recorde', 'lucro', 'crescimento']):
                            sentiment = 'bullish'
                        elif any(w in title for w in ['queda', 'cai', 'prejuízo', 'risco', 'crise']):
                            sentiment = 'bearish'
                        
                        news_list.append(NewsItem(
                            title=item.get('title', 'Sem título'),
                            summary=item.get('content', '')[:300] + '...' if len(item.get('content', '')) > 300 else item.get('content', ''),
                            source=item.get('source', 'EODHD'),
                            category='stocks',
                            sentiment=sentiment,
                            impact='medium',
                            url=item.get('link'),
                            published_at=item.get('date')
                        ))
        except Exception as e:
            logger.error(f"Erro ao buscar notícias EODHD: {e}")
        
        # Se não conseguiu notícias, adiciona algumas genéricas
        if not news_list:
            news_list = self._get_fallback_news()
        
        return news_list
    
    def _get_fallback_news(self) -> List[NewsItem]:
        """Retorna notícias de fallback."""
        now = get_brazil_now()
        return [
            NewsItem(
                title="Mercados globais operam com cautela",
                summary="Investidores aguardam dados econômicos importantes e decisões de política monetária.",
                source="VIRTUS",
                category="economy",
                sentiment="neutral",
                impact="medium",
                published_at=now.isoformat()
            ),
            NewsItem(
                title="Ibovespa acompanha mercados externos",
                summary="Bolsa brasileira segue tendência dos mercados internacionais nesta sessão.",
                source="VIRTUS",
                category="stocks",
                sentiment="neutral",
                impact="low",
                published_at=now.isoformat()
            )
        ]
    
    async def _fetch_economic_calendar(self) -> List[EconomicEvent]:
        """Busca calendário econômico."""
        session = await self._get_session()
        events = []
        
        # Mapeamento de tipos de eventos para português e impacto
        event_translations = {
            'Interest Rate Decision': ('Decisão de Taxa de Juros', EventImpact.HIGH),
            'Fed Interest Rate Decision': ('Decisão de Juros do FED', EventImpact.HIGH),
            'ECB Interest Rate Decision': ('Decisão de Juros do BCE', EventImpact.HIGH),
            'ECB Press Conference': ('Coletiva do BCE', EventImpact.HIGH),
            'Fed Press Conference': ('Coletiva do FED', EventImpact.HIGH),
            'FOMC Press Conference': ('Coletiva FOMC', EventImpact.HIGH),
            'FOMC Economic Projections': ('Projeções Econômicas FOMC', EventImpact.HIGH),
            'GDP Growth Rate': ('Taxa de Crescimento do PIB', EventImpact.HIGH),
            'Unemployment Rate': ('Taxa de Desemprego', EventImpact.HIGH),
            'Non Farm Payrolls': ('Payroll Não-Agrícola', EventImpact.HIGH),
            'Nonfarm Payrolls': ('Payroll Não-Agrícola', EventImpact.HIGH),
            'Inflation Rate': ('Taxa de Inflação', EventImpact.HIGH),
            'Core Inflation Rate': ('Inflação Núcleo', EventImpact.HIGH),
            'CPI': ('Índice de Preços ao Consumidor', EventImpact.HIGH),
            'Core CPI': ('CPI Núcleo', EventImpact.HIGH),
            'PPI': ('Índice de Preços ao Produtor', EventImpact.MEDIUM),
            'Producer Price Index': ('Índice de Preços ao Produtor', EventImpact.MEDIUM),
            'Retail Sales': ('Vendas no Varejo', EventImpact.HIGH),
            'Industrial Production': ('Produção Industrial', EventImpact.MEDIUM),
            'Consumer Confidence': ('Confiança do Consumidor', EventImpact.MEDIUM),
            'Balance of Trade': ('Balança Comercial', EventImpact.MEDIUM),
            'Jobless Claims': ('Pedidos de Seguro Desemprego', EventImpact.MEDIUM),
            'Initial Jobless Claims': ('Pedidos Iniciais Seguro Desemprego', EventImpact.MEDIUM),
            'Continuing Jobless Claims': ('Pedidos Contínuos Seguro Desemprego', EventImpact.MEDIUM),
            'Fed Balance Sheet': ('Balanço do FED', EventImpact.MEDIUM),
            'Leading Index': ('Índice Antecedente', EventImpact.MEDIUM),
            'PMI': ('PMI', EventImpact.HIGH),
            'Manufacturing PMI': ('PMI Manufatura', EventImpact.HIGH),
            'Services PMI': ('PMI Serviços', EventImpact.HIGH),
            'ISM Manufacturing PMI': ('PMI Manufatura ISM', EventImpact.HIGH),
            'ISM Services PMI': ('PMI Serviços ISM', EventImpact.HIGH),
            'Selic Rate': ('Taxa Selic', EventImpact.HIGH),
            'Copom Interest Rate Decision': ('Decisão Copom Taxa Selic', EventImpact.HIGH),
            'Kansas Fed Manufacturing Index': ('Índice Fed Kansas Manufatura', EventImpact.LOW),
            'EIA Natural Gas Stocks Change': ('Estoques Gás Natural EIA', EventImpact.LOW),
        }
        
        # Países importantes
        important_countries = ['US', 'BR', 'EU', 'GB', 'JP', 'CN']
        
        try:
            # EODHD Economic Calendar
            today = get_brazil_now().strftime('%Y-%m-%d')
            url = "https://eodhd.com/api/economic-events"
            params = {
                'api_token': EODHD_API_KEY,
                'from': today,
                'to': today,
                'fmt': 'json'
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Processa eventos
                    for item in data:
                        event_type = item.get('type', '')
                        country = item.get('country', 'N/A')
                        
                        # Traduz e determina impacto
                        if event_type in event_translations:
                            translated, impact = event_translations[event_type]
                        else:
                            translated = event_type
                            # Determina impacto por palavras-chave
                            if any(kw in event_type.lower() for kw in ['interest rate', 'gdp', 'inflation', 'employment', 'payroll']):
                                impact = EventImpact.HIGH
                            elif any(kw in event_type.lower() for kw in ['pmi', 'retail', 'production', 'confidence']):
                                impact = EventImpact.MEDIUM
                            else:
                                impact = EventImpact.LOW
                        
                        # Extrai hora do datetime e converte UTC para horário de Brasília (UTC-3)
                        date_str = item.get('date', '')
                        try:
                            if len(date_str) >= 16:
                                time_utc = date_str[11:16]  # "HH:MM" em UTC
                                hour_utc = int(time_utc[:2])
                                minute = time_utc[3:5]
                                # Converte UTC para Brasília (UTC-3)
                                hour_br = hour_utc - 3
                                if hour_br < 0:
                                    hour_br += 24  # Ajusta para o dia anterior
                                time_part = f"{hour_br:02d}:{minute}"
                            else:
                                time_part = 'N/A'
                        except:
                            time_part = 'N/A'
                        
                        # Adiciona comparação se houver (yoy, mom, etc)
                        comparison = item.get('comparison', '')
                        if comparison:
                            translated = f"{translated} ({comparison.upper()})"
                        
                        # Período
                        period = item.get('period', '')
                        if period:
                            translated = f"{translated} - {period}"
                        
                        events.append(EconomicEvent(
                            time=time_part,
                            country=country,
                            event=translated,
                            impact=impact,
                            actual=str(item.get('actual')) if item.get('actual') is not None else None,
                            forecast=str(item.get('estimate')) if item.get('estimate') is not None else None,
                            previous=str(item.get('previous')) if item.get('previous') is not None else None
                        ))
                    
                    # Ordena por impacto (alto primeiro) e depois por hora
                    impact_order = {EventImpact.HIGH: 0, EventImpact.MEDIUM: 1, EventImpact.LOW: 2}
                    events.sort(key=lambda x: (impact_order.get(x.impact, 3), x.time))
                    
                    # Prioriza países importantes
                    important_events = [e for e in events if e.country in important_countries]
                    other_events = [e for e in events if e.country not in important_countries]
                    events = important_events + other_events
                    
        except Exception as e:
            logger.error(f"Erro ao buscar calendário EODHD: {e}")
        
        # Se não conseguiu eventos, adiciona alguns padrão
        if not events:
            events = self._get_fallback_calendar()
        
        return events[:20]  # Limita a 20 eventos
    
    def _get_fallback_calendar(self) -> List[EconomicEvent]:
        """Retorna calendário de fallback."""
        return [
            EconomicEvent(
                time="10:00",
                country="BR",
                event="Abertura do mercado brasileiro",
                impact=EventImpact.MEDIUM
            ),
            EconomicEvent(
                time="11:30",
                country="US",
                event="Abertura do mercado americano",
                impact=EventImpact.MEDIUM
            )
        ]
    
    async def _fetch_dividend_alerts(self) -> List[DividendAlert]:
        """Busca alertas de dividendos usando DividendBrain."""
        alerts = []
        today = get_brazil_now().date()
        
        try:
            # Usa o DividendBrain real para buscar oportunidades
            from services.dividend_brain import get_dividend_brain
            brain = get_dividend_brain()
            signals = await brain.analyze_opportunities(capital=10000)
            
            for signal in signals:
                try:
                    # Converte ex_date para date
                    if signal.ex_date:
                        if isinstance(signal.ex_date, str):
                            ex_date = datetime.strptime(signal.ex_date, '%Y-%m-%d').date()
                        else:
                            ex_date = signal.ex_date
                        
                        # Buy limit date é 1 dia antes da ex_date
                        buy_limit = ex_date - timedelta(days=1)
                        days_remaining = (buy_limit - today).days
                        
                        # Só inclui se ainda dá tempo de comprar
                        if days_remaining >= 0:
                            if days_remaining == 0:
                                urgency = 'today'
                            elif days_remaining <= 2:
                                urgency = 'urgent'
                            else:
                                urgency = 'soon'
                            
                            # Suggested sell date como payment date (aproximação)
                            payment_date = signal.suggested_sell_date or ''
                            if payment_date and isinstance(payment_date, date):
                                payment_date = payment_date.strftime('%Y-%m-%d')
                            
                            alerts.append(DividendAlert(
                                ticker=signal.ticker,
                                company_name=signal.company_name,
                                buy_limit_date=buy_limit.strftime('%Y-%m-%d'),
                                ex_date=signal.ex_date if isinstance(signal.ex_date, str) else signal.ex_date.strftime('%Y-%m-%d'),
                                payment_date=payment_date,
                                dividend_value=signal.expected_dividend or 0,
                                dividend_yield=signal.dividend_yield or 0,
                                days_remaining=days_remaining,
                                urgency=urgency
                            ))
                except Exception as e:
                    logger.error(f"Erro ao processar sinal {signal.ticker}: {e}")
                    
        except ImportError as e:
            logger.warning(f"DividendBrain não disponível: {e}")
        except Exception as e:
            logger.error(f"Erro ao buscar dividendos do Brain: {e}")
        
        # Ordena por urgência
        urgency_order = {'today': 0, 'urgent': 1, 'soon': 2}
        alerts.sort(key=lambda x: urgency_order.get(x.urgency, 3))
        
        return alerts
    
    def _generate_summary_texts(
        self,
        market: MarketOverview,
        news: List[NewsItem],
        calendar: List[EconomicEvent],
        dividends: List[DividendAlert],
        greeting: str,
        now: datetime
    ) -> tuple:
        """Gera textos de resumo e áudio."""
        
        date_str = format_brazil_date(now)
        weekday = get_weekday_name(now)
        
        # Texto para exibição (mais detalhado)
        summary_parts = []
        summary_parts.append(f"📅 {weekday}, {date_str}")
        summary_parts.append("")
        
        # Mercado
        summary_parts.append("📊 MERCADO:")
        if market.ibovespa.get('value', 0) > 0:
            direction = "↑" if market.ibovespa.get('direction') == 'up' else "↓"
            summary_parts.append(f"• IBOV: {market.ibovespa['value']:,.0f} pts ({direction} {abs(market.ibovespa.get('change_percent', 0)):.2f}%)")
        if market.dolar.get('value', 0) > 0:
            direction = "↑" if market.dolar.get('direction') == 'up' else "↓"
            summary_parts.append(f"• Dólar: R$ {market.dolar['value']:.2f} ({direction} {abs(market.dolar.get('change_percent', 0)):.2f}%)")
        if market.sp500.get('value', 0) > 0:
            direction = "↑" if market.sp500.get('direction') == 'up' else "↓"
            summary_parts.append(f"• S&P 500: {market.sp500['value']:,.0f} pts ({direction} {abs(market.sp500.get('change_percent', 0)):.2f}%)")
        
        summary_parts.append(f"\n💡 {market.sentiment_description}")
        
        # Eventos de alto impacto
        high_impact_events = [e for e in calendar if e.impact == EventImpact.HIGH]
        if high_impact_events:
            summary_parts.append("\n🔴 EVENTOS DE ALTO IMPACTO HOJE:")
            for e in high_impact_events[:5]:
                summary_parts.append(f"• {e.time} ({e.country}) - {e.event}")
        
        # Dividendos urgentes
        urgent_divs = [d for d in dividends if d.urgency in ['today', 'urgent']]
        if urgent_divs:
            summary_parts.append("\n🚨 DIVIDENDOS URGENTES:")
            for d in urgent_divs[:3]:
                if d.urgency == 'today':
                    summary_parts.append(f"• {d.ticker}: ÚLTIMO DIA para comprar! DY: {d.dividend_yield}%")
                else:
                    summary_parts.append(f"• {d.ticker}: {d.days_remaining} dias restantes. DY: {d.dividend_yield}%")
        
        summary_text = "\n".join(summary_parts)
        
        # Texto para áudio (mais natural)
        audio_parts = []
        audio_parts.append(f"{greeting}! Aqui é o briefing diário da Virtus.")
        audio_parts.append(f"Hoje é {weekday}, dia {date_str}.")
        audio_parts.append("")
        
        # Mercado no áudio
        audio_parts.append("Vamos aos mercados:")
        if market.ibovespa.get('value', 0) > 0:
            direction = "em alta" if market.ibovespa.get('direction') == 'up' else "em baixa"
            audio_parts.append(f"O Ibovespa opera {direction} de {abs(market.ibovespa.get('change_percent', 0)):.1f} por cento.")
        if market.dolar.get('value', 0) > 0:
            direction = "subindo" if market.dolar.get('direction') == 'up' else "caindo"
            audio_parts.append(f"O dólar está {direction}, cotado a {market.dolar['value']:.2f} reais.")
        
        audio_parts.append(market.sentiment_description)
        
        # Eventos importantes no áudio
        if high_impact_events:
            audio_parts.append("")
            audio_parts.append("Atenção! Hoje temos eventos de alto impacto no calendário econômico:")
            for e in high_impact_events[:3]:
                country_name = {
                    'US': 'Estados Unidos',
                    'BR': 'Brasil',
                    'EU': 'Zona do Euro',
                    'GB': 'Reino Unido',
                    'JP': 'Japão',
                    'CN': 'China'
                }.get(e.country, e.country)
                audio_parts.append(f"Às {e.time}, {e.event}, de {country_name}.")
        
        # Dividendos no áudio
        if urgent_divs:
            audio_parts.append("")
            audio_parts.append("Atenção para os dividendos!")
            for d in urgent_divs[:2]:
                if d.urgency == 'today':
                    audio_parts.append(f"Hoje é o último dia para comprar {d.ticker} e garantir o dividendo de {d.dividend_yield} por cento.")
                else:
                    audio_parts.append(f"Faltam apenas {d.days_remaining} dias para comprar {d.ticker}. Dividend yield de {d.dividend_yield} por cento.")
        
        audio_parts.append("")
        audio_parts.append("Esse foi o briefing da Virtus. Bons investimentos!")
        
        audio_text = " ".join(audio_parts)
        
        return summary_text, audio_text


# Instância global
daily_briefing_service = DailyBriefingService()
