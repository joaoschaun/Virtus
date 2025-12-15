"""
VIRTUS News Analyzer
=====================

Analisa impacto de notícias no mercado.

Funcionalidades:
- Integração com ForexNews API
- Análise de sentimento de notícias
- Classificação de impacto
- Headlines em tempo real
- Filtro por moeda/símbolo
"""

import aiohttp
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta, timezone
import logging


class NewsImpact(Enum):
    """Impacto da notícia."""
    VERY_HIGH = auto()   # Market-moving
    HIGH = auto()        # Significativo
    MEDIUM = auto()      # Moderado
    LOW = auto()         # Baixo
    NONE = auto()        # Irrelevante


class NewsSentiment(Enum):
    """Sentimento da notícia."""
    VERY_BULLISH = auto()
    BULLISH = auto()
    NEUTRAL = auto()
    BEARISH = auto()
    VERY_BEARISH = auto()


@dataclass
class NewsItem:
    """Uma notícia."""
    id: str
    title: str
    summary: str
    source: str
    published_at: datetime
    url: str
    
    # Análise
    currencies: List[str]
    impact: NewsImpact
    sentiment: NewsSentiment
    sentiment_score: float  # -1 a 1
    
    # Keywords
    keywords: List[str] = field(default_factory=list)
    
    # Relevância
    relevance_score: float = 0.0


@dataclass
class NewsAnalysisResult:
    """Resultado da análise de notícias."""
    has_breaking_news: bool
    overall_sentiment: NewsSentiment
    sentiment_score: float  # -1 a 1
    
    news_items: List[NewsItem]
    high_impact_news: List[NewsItem]
    
    affected_currencies: List[str]
    risk_level: str  # 'low', 'medium', 'high'
    
    recommendation: str
    details: Dict[str, Any]


# Palavras-chave para análise de sentimento
BULLISH_KEYWORDS = [
    'surge', 'rally', 'gain', 'rise', 'jump', 'soar', 'climb',
    'bullish', 'upbeat', 'optimistic', 'growth', 'expand',
    'beat', 'exceed', 'strong', 'robust', 'recover', 'rebound',
    'hawkish', 'rate hike', 'inflation', 'employment',
    'alta', 'subir', 'crescer', 'otimista', 'forte',
]

BEARISH_KEYWORDS = [
    'fall', 'drop', 'decline', 'plunge', 'crash', 'tumble',
    'bearish', 'pessimistic', 'concern', 'worry', 'fear',
    'miss', 'disappoint', 'weak', 'slowdown', 'recession',
    'dovish', 'rate cut', 'unemployment', 'crisis',
    'queda', 'cair', 'pessimista', 'fraco', 'recessão',
]

HIGH_IMPACT_KEYWORDS = [
    'breaking', 'urgent', 'alert', 'fed', 'fomc', 'ecb', 'boe',
    'nfp', 'payroll', 'gdp', 'cpi', 'inflation', 'rate decision',
    'emergency', 'intervention', 'crisis', 'war', 'election',
    'powell', 'lagarde', 'bailey', 'kuroda',
]


class NewsAnalyzer:
    """
    Analisador de notícias para trading.
    
    Busca e analisa notícias relevantes para
    ajustar estratégias de trading.
    """
    
    def __init__(
        self,
        logger: logging.Logger = None,
        # API Keys
        forexnews_api_key: str = None,
        finnhub_api_key: str = None,
        # Configurações
        cache_ttl_minutes: int = 5,
        lookback_hours: int = 24,
    ):
        self.logger = logger or logging.getLogger(__name__)
        
        self.forexnews_api_key = forexnews_api_key
        self.finnhub_api_key = finnhub_api_key
        
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.lookback_hours = lookback_hours
        
        # Cache
        self._news_cache: List[NewsItem] = []
        self._cache_time: Optional[datetime] = None
    
    async def analyze(
        self,
        symbol: str = None,
        currencies: List[str] = None,
        force_refresh: bool = False,
    ) -> NewsAnalysisResult:
        """
        Analisa notícias relevantes.
        
        Args:
            symbol: Par de moedas (opcional)
            currencies: Lista de moedas para filtrar
            force_refresh: Força atualização
            
        Returns:
            NewsAnalysisResult
        """
        # Extrai moedas do símbolo
        if symbol and not currencies:
            currencies = self._extract_currencies(symbol)
        
        # Obtém notícias
        news = await self._get_news(force_refresh)
        
        # Filtra por moedas
        if currencies:
            filtered = [
                n for n in news
                if any(c in n.currencies for c in currencies)
            ]
        else:
            filtered = news
        
        # Ordena por relevância e data
        filtered.sort(key=lambda n: (-n.relevance_score, -n.published_at.timestamp()))
        
        # Análise
        high_impact = [n for n in filtered if n.impact in [NewsImpact.VERY_HIGH, NewsImpact.HIGH]]
        has_breaking = any(n.impact == NewsImpact.VERY_HIGH for n in filtered[:5])
        
        # Sentimento geral
        sentiment_score = self._calculate_overall_sentiment(filtered)
        overall_sentiment = self._score_to_sentiment(sentiment_score)
        
        # Risk level
        risk_level = self._assess_risk_level(filtered, has_breaking)
        
        # Moedas afetadas
        affected = list(set(c for n in high_impact for c in n.currencies))
        
        # Recomendação
        recommendation = self._generate_recommendation(
            overall_sentiment, has_breaking, high_impact, currencies
        )
        
        return NewsAnalysisResult(
            has_breaking_news=has_breaking,
            overall_sentiment=overall_sentiment,
            sentiment_score=sentiment_score,
            news_items=filtered[:20],  # Top 20
            high_impact_news=high_impact[:10],
            affected_currencies=affected,
            risk_level=risk_level,
            recommendation=recommendation,
            details={
                'total_news': len(filtered),
                'high_impact_count': len(high_impact),
                'filter_currencies': currencies,
            }
        )
    
    async def _get_news(self, force_refresh: bool = False) -> List[NewsItem]:
        """Obtém notícias."""
        
        # Verifica cache
        if not force_refresh and self._cache_valid():
            return self._news_cache
        
        news = []
        
        # ForexNews API
        if self.forexnews_api_key:
            try:
                fn_news = await self._fetch_forexnews()
                news.extend(fn_news)
            except Exception as e:
                self.logger.warning(f"Erro ForexNews: {e}")
        
        # Finnhub
        if self.finnhub_api_key:
            try:
                fh_news = await self._fetch_finnhub()
                news.extend(fh_news)
            except Exception as e:
                self.logger.warning(f"Erro Finnhub: {e}")
        
        # Remove duplicatas
        seen = set()
        unique_news = []
        for n in news:
            key = n.title[:50].lower()
            if key not in seen:
                seen.add(key)
                unique_news.append(n)
        
        # Atualiza cache
        self._news_cache = unique_news
        self._cache_time = datetime.now(timezone.utc)
        
        return unique_news
    
    def _cache_valid(self) -> bool:
        """Verifica cache."""
        if not self._cache_time or not self._news_cache:
            return False
        
        age = datetime.now(timezone.utc) - self._cache_time
        return age < self.cache_ttl
    
    async def _fetch_forexnews(self) -> List[NewsItem]:
        """Busca notícias do ForexNews API."""
        news = []
        
        url = 'https://forexnewsapi.com/api/v1/news'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params={
                    'token': self.forexnews_api_key,
                    'items': 50,
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get('data', []):
                        try:
                            news_item = self._parse_forexnews_item(item)
                            if news_item:
                                news.append(news_item)
                        except Exception as e:
                            self.logger.debug(f"Erro parsing news: {e}")
        
        return news
    
    def _parse_forexnews_item(self, item: Dict) -> Optional[NewsItem]:
        """Parse item do ForexNews."""
        title = item.get('title', '')
        summary = item.get('text', '')[:500]
        
        # Extrai moedas mencionadas
        currencies = self._extract_currencies_from_text(title + ' ' + summary)
        
        # Análise de sentimento
        sentiment_score = self._analyze_text_sentiment(title + ' ' + summary)
        sentiment = self._score_to_sentiment(sentiment_score)
        
        # Impacto
        impact = self._assess_news_impact(title, summary)
        
        # Relevância
        relevance = self._calculate_relevance(item, currencies, impact)
        
        # Parse date
        try:
            pub_date = datetime.fromisoformat(
                item.get('date', '').replace('Z', '+00:00')
            )
        except:
            pub_date = datetime.now(timezone.utc)
        
        return NewsItem(
            id=str(item.get('id', '')),
            title=title,
            summary=summary,
            source=item.get('source', 'ForexNews'),
            published_at=pub_date,
            url=item.get('url', ''),
            currencies=currencies,
            impact=impact,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            keywords=self._extract_keywords(title),
            relevance_score=relevance,
        )
    
    async def _fetch_finnhub(self) -> List[NewsItem]:
        """Busca notícias do Finnhub."""
        news = []
        
        url = 'https://finnhub.io/api/v1/news'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params={
                    'token': self.finnhub_api_key,
                    'category': 'forex',
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data:
                        try:
                            news_item = self._parse_finnhub_item(item)
                            if news_item:
                                news.append(news_item)
                        except Exception as e:
                            self.logger.debug(f"Erro parsing Finnhub: {e}")
        
        return news
    
    def _parse_finnhub_item(self, item: Dict) -> Optional[NewsItem]:
        """Parse item do Finnhub."""
        headline = item.get('headline', '')
        summary = item.get('summary', '')[:500]
        
        currencies = self._extract_currencies_from_text(headline + ' ' + summary)
        
        sentiment_score = self._analyze_text_sentiment(headline + ' ' + summary)
        sentiment = self._score_to_sentiment(sentiment_score)
        
        impact = self._assess_news_impact(headline, summary)
        relevance = self._calculate_relevance(item, currencies, impact)
        
        try:
            pub_date = datetime.fromtimestamp(item.get('datetime', 0), tz=timezone.utc)
        except:
            pub_date = datetime.now(timezone.utc)
        
        return NewsItem(
            id=str(item.get('id', '')),
            title=headline,
            summary=summary,
            source=item.get('source', 'Finnhub'),
            published_at=pub_date,
            url=item.get('url', ''),
            currencies=currencies,
            impact=impact,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            keywords=self._extract_keywords(headline),
            relevance_score=relevance,
        )
    
    def _extract_currencies(self, symbol: str) -> List[str]:
        """Extrai moedas de um símbolo."""
        symbol = symbol.upper()
        
        if len(symbol) == 6:
            return [symbol[:3], symbol[3:]]
        
        if 'XAU' in symbol or 'GOLD' in symbol:
            return ['XAU', 'USD']
        
        return ['USD']
    
    def _extract_currencies_from_text(self, text: str) -> List[str]:
        """Extrai moedas mencionadas no texto."""
        currencies = []
        text_upper = text.upper()
        
        currency_map = {
            'USD': ['USD', 'DOLLAR', 'US$', 'GREENBACK', 'FED', 'FOMC'],
            'EUR': ['EUR', 'EURO', 'ECB', 'EUROZONE', 'EUROPE'],
            'GBP': ['GBP', 'POUND', 'STERLING', 'BOE', 'BRITAIN', 'UK'],
            'JPY': ['JPY', 'YEN', 'BOJ', 'JAPAN'],
            'AUD': ['AUD', 'AUSSIE', 'RBA', 'AUSTRALIA'],
            'CAD': ['CAD', 'LOONIE', 'BOC', 'CANADA'],
            'CHF': ['CHF', 'FRANC', 'SNB', 'SWISS'],
            'NZD': ['NZD', 'KIWI', 'RBNZ', 'NEW ZEALAND'],
            'XAU': ['GOLD', 'XAU', 'BULLION'],
        }
        
        for currency, keywords in currency_map.items():
            for keyword in keywords:
                if keyword in text_upper:
                    currencies.append(currency)
                    break
        
        return list(set(currencies)) or ['USD']
    
    def _analyze_text_sentiment(self, text: str) -> float:
        """Analisa sentimento do texto."""
        text_lower = text.lower()
        
        bullish_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
        bearish_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0
        
        return (bullish_count - bearish_count) / total
    
    def _assess_news_impact(self, title: str, summary: str) -> NewsImpact:
        """Avalia impacto da notícia."""
        text = (title + ' ' + summary).lower()
        
        # Very high impact
        very_high_kw = ['breaking', 'urgent', 'emergency', 'crash', 'crisis']
        if any(kw in text for kw in very_high_kw):
            return NewsImpact.VERY_HIGH
        
        # High impact
        high_count = sum(1 for kw in HIGH_IMPACT_KEYWORDS if kw in text)
        if high_count >= 2:
            return NewsImpact.HIGH
        
        # Medium impact
        if high_count >= 1:
            return NewsImpact.MEDIUM
        
        return NewsImpact.LOW
    
    def _calculate_relevance(
        self,
        item: Dict,
        currencies: List[str],
        impact: NewsImpact
    ) -> float:
        """Calcula relevância da notícia."""
        score = 0.0
        
        # Impact
        impact_scores = {
            NewsImpact.VERY_HIGH: 1.0,
            NewsImpact.HIGH: 0.8,
            NewsImpact.MEDIUM: 0.5,
            NewsImpact.LOW: 0.2,
            NewsImpact.NONE: 0.0,
        }
        score += impact_scores.get(impact, 0) * 0.5
        
        # Moedas
        score += len(currencies) * 0.1
        
        # Recência (notícias mais recentes são mais relevantes)
        # Isso é ajustado depois no sort
        
        return min(score, 1.0)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai keywords do texto."""
        # Remove pontuação e split
        words = re.findall(r'\b[A-Za-z]+\b', text)
        
        # Filtra stopwords básicas
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for'}
        
        keywords = [w.lower() for w in words if len(w) > 3 and w.lower() not in stopwords]
        
        return keywords[:10]
    
    def _score_to_sentiment(self, score: float) -> NewsSentiment:
        """Converte score para sentimento."""
        if score >= 0.5:
            return NewsSentiment.VERY_BULLISH
        elif score >= 0.2:
            return NewsSentiment.BULLISH
        elif score <= -0.5:
            return NewsSentiment.VERY_BEARISH
        elif score <= -0.2:
            return NewsSentiment.BEARISH
        else:
            return NewsSentiment.NEUTRAL
    
    def _calculate_overall_sentiment(self, news: List[NewsItem]) -> float:
        """Calcula sentimento geral das notícias."""
        if not news:
            return 0.0
        
        # Pondera por impacto e relevância
        weighted_sum = 0.0
        total_weight = 0.0
        
        for item in news[:20]:  # Top 20
            weight = item.relevance_score + 0.5
            if item.impact == NewsImpact.VERY_HIGH:
                weight *= 3
            elif item.impact == NewsImpact.HIGH:
                weight *= 2
            
            weighted_sum += item.sentiment_score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    def _assess_risk_level(
        self,
        news: List[NewsItem],
        has_breaking: bool
    ) -> str:
        """Avalia nível de risco baseado nas notícias."""
        if has_breaking:
            return 'high'
        
        high_impact_count = sum(
            1 for n in news[:10]
            if n.impact in [NewsImpact.VERY_HIGH, NewsImpact.HIGH]
        )
        
        if high_impact_count >= 3:
            return 'high'
        elif high_impact_count >= 1:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendation(
        self,
        sentiment: NewsSentiment,
        has_breaking: bool,
        high_impact: List[NewsItem],
        currencies: List[str]
    ) -> str:
        """Gera recomendação baseada nas notícias."""
        
        if has_breaking:
            return "🚨 BREAKING NEWS - Cautela máxima, volatilidade elevada"
        
        if len(high_impact) >= 3:
            return "⚠️ Múltiplas notícias de alto impacto - Reduzir exposição"
        
        curr_str = ', '.join(currencies) if currencies else 'todas moedas'
        
        if sentiment == NewsSentiment.VERY_BULLISH:
            return f"📈 Notícias muito positivas para {curr_str}"
        elif sentiment == NewsSentiment.BULLISH:
            return f"📈 Viés positivo nas notícias para {curr_str}"
        elif sentiment == NewsSentiment.VERY_BEARISH:
            return f"📉 Notícias muito negativas para {curr_str}"
        elif sentiment == NewsSentiment.BEARISH:
            return f"📉 Viés negativo nas notícias para {curr_str}"
        else:
            return f"📊 Notícias neutras para {curr_str}"
    
    def to_dict(self, result: NewsAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        news_list = []
        for n in result.news_items[:10]:
            news_list.append({
                'title': n.title[:100],
                'source': n.source,
                'published': n.published_at.isoformat(),
                'currencies': n.currencies,
                'impact': n.impact.name,
                'sentiment': n.sentiment.name,
                'sentiment_score': round(n.sentiment_score, 2),
            })
        
        return {
            'has_breaking_news': result.has_breaking_news,
            'overall_sentiment': result.overall_sentiment.name,
            'sentiment_score': round(result.sentiment_score, 2),
            'risk_level': result.risk_level,
            'affected_currencies': result.affected_currencies,
            'high_impact_count': len(result.high_impact_news),
            'recommendation': result.recommendation,
            'news': news_list,
            'details': result.details,
        }
