"""
VIRTUS News Analyzer
=====================

Analisa e processa notícias do mercado financeiro.
Integra com providers do Brain para obter dados de múltiplas fontes.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
import re
from collections import defaultdict

try:
    from ...core import VirtusLogger
except ImportError:
    from core import VirtusLogger


class NewsImpact(Enum):
    """Impacto esperado da notícia."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NewsSentiment(Enum):
    """Sentimento da notícia."""
    VERY_BEARISH = -2
    BEARISH = -1
    NEUTRAL = 0
    BULLISH = 1
    VERY_BULLISH = 2


class NewsCategory(Enum):
    """Categoria da notícia."""
    ECONOMIC_DATA = "economic_data"
    CENTRAL_BANK = "central_bank"
    GEOPOLITICAL = "geopolitical"
    CORPORATE = "corporate"
    COMMODITY = "commodity"
    TECHNICAL = "technical"
    GENERAL = "general"


@dataclass
class NewsItem:
    """Uma notícia individual."""
    id: str
    title: str
    description: str
    source: str
    url: str
    published_at: datetime
    
    # Análise
    impact: NewsImpact = NewsImpact.LOW
    sentiment: NewsSentiment = NewsSentiment.NEUTRAL
    category: NewsCategory = NewsCategory.GENERAL
    
    # Relevância
    symbols: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    
    # Metadata
    processed: bool = False
    processed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'source': self.source,
            'published_at': self.published_at.isoformat(),
            'impact': self.impact.value,
            'sentiment': self.sentiment.name,
            'category': self.category.value,
            'symbols': self.symbols,
            'relevance_score': round(self.relevance_score, 3),
        }


@dataclass
class NewsSummary:
    """Resumo de notícias para um período/símbolo."""
    symbol: str
    period_start: datetime
    period_end: datetime
    
    # Contagens
    total_news: int = 0
    high_impact: int = 0
    
    # Sentimento agregado
    avg_sentiment: float = 0.0
    sentiment_direction: str = "neutral"
    
    # Top notícias
    top_bullish: List[NewsItem] = field(default_factory=list)
    top_bearish: List[NewsItem] = field(default_factory=list)
    
    # Por categoria
    by_category: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'period': f"{self.period_start.date()} - {self.period_end.date()}",
            'total_news': self.total_news,
            'high_impact': self.high_impact,
            'avg_sentiment': round(self.avg_sentiment, 2),
            'sentiment_direction': self.sentiment_direction,
            'by_category': self.by_category,
        }


class NewsAnalyzer:
    """
    Analisador de notícias para trading.
    
    Funcionalidades:
    - Categorização automática
    - Análise de sentimento
    - Extração de símbolos relevantes
    - Resumos por período
    """
    
    def __init__(self):
        self.logger = VirtusLogger.get_logger("news_analyzer")
        
        # Cache de notícias processadas
        self._news_cache: Dict[str, NewsItem] = {}
        self._cache_max_age = timedelta(hours=24)
        
        # Mapeamento de palavras-chave para símbolos
        self._symbol_keywords = self._build_symbol_keywords()
        
        # Palavras para análise de sentimento
        self._sentiment_words = self._build_sentiment_words()
        
        # Categorias de eventos
        self._event_categories = self._build_event_categories()
    
    def _build_symbol_keywords(self) -> Dict[str, List[str]]:
        """Constrói mapeamento de keywords para símbolos."""
        return {
            'XAUUSD': [
                'gold', 'ouro', 'xau', 'bullion', 'precious metal',
                'fed', 'inflation', 'dollar', 'treasury', 'haven',
                'geopolitical', 'war', 'crisis', 'yields',
            ],
            'EURUSD': [
                'euro', 'eur', 'ecb', 'european central bank',
                'eurozone', 'germany', 'france', 'draghi', 'lagarde',
                'eu', 'european union', 'bundesbank',
            ],
            'GBPUSD': [
                'pound', 'sterling', 'gbp', 'boe', 'bank of england',
                'uk', 'britain', 'brexit', 'british', 'london',
                'bailey', 'ftse',
            ],
            'USD': [
                'dollar', 'usd', 'fed', 'federal reserve', 'fomc',
                'powell', 'treasury', 'us economy', 'american',
                'nonfarm', 'payroll', 'cpi', 'ppi',
            ],
        }
    
    def _build_sentiment_words(self) -> Dict[str, List[str]]:
        """Constrói dicionário de palavras para sentiment."""
        return {
            'very_bullish': [
                'surge', 'soar', 'spike', 'boom', 'rally', 'jump',
                'breakthrough', 'record high', 'explosive growth',
                'strong beat', 'unexpected rise',
            ],
            'bullish': [
                'rise', 'gain', 'increase', 'positive', 'improve',
                'growth', 'advance', 'optimistic', 'bullish',
                'support', 'upward', 'beat expectations',
            ],
            'bearish': [
                'fall', 'drop', 'decline', 'negative', 'weak',
                'concerns', 'pressure', 'bearish', 'downward',
                'miss expectations', 'disappointing',
            ],
            'very_bearish': [
                'crash', 'plunge', 'collapse', 'crisis', 'panic',
                'recession', 'slump', 'meltdown', 'catastrophic',
                'worst', 'historic low', 'massive selloff',
            ],
        }
    
    def _build_event_categories(self) -> Dict[NewsCategory, List[str]]:
        """Constrói palavras para categorização."""
        return {
            NewsCategory.ECONOMIC_DATA: [
                'gdp', 'cpi', 'ppi', 'nonfarm', 'employment',
                'retail sales', 'manufacturing', 'pmi', 'ism',
                'trade balance', 'inflation', 'unemployment',
            ],
            NewsCategory.CENTRAL_BANK: [
                'fed', 'ecb', 'boe', 'fomc', 'rate decision',
                'interest rate', 'monetary policy', 'hawkish',
                'dovish', 'qe', 'taper', 'chairman', 'governor',
            ],
            NewsCategory.GEOPOLITICAL: [
                'war', 'conflict', 'sanctions', 'election',
                'political', 'trade war', 'tariff', 'summit',
                'diplomacy', 'tension', 'crisis',
            ],
            NewsCategory.COMMODITY: [
                'oil', 'gold', 'silver', 'copper', 'crude',
                'opec', 'commodity', 'mining', 'energy',
            ],
        }
    
    async def analyze_news(
        self,
        news_data: List[Dict[str, Any]],
        target_symbols: Optional[List[str]] = None
    ) -> List[NewsItem]:
        """
        Analisa lista de notícias.
        
        Args:
            news_data: Dados brutos das notícias
            target_symbols: Símbolos para filtrar relevância
            
        Returns:
            Lista de NewsItem processados
        """
        target_symbols = target_symbols or ['XAUUSD', 'EURUSD', 'GBPUSD']
        processed = []
        
        for raw_news in news_data:
            try:
                news_item = self._process_news(raw_news, target_symbols)
                if news_item and news_item.relevance_score > 0.2:
                    processed.append(news_item)
                    self._news_cache[news_item.id] = news_item
                    
            except Exception as e:
                self.logger.warning(f"Erro processando notícia: {e}")
                continue
        
        # Ordena por relevância
        processed.sort(key=lambda x: x.relevance_score, reverse=True)
        
        self.logger.info(f"Processadas {len(processed)} notícias relevantes")
        return processed
    
    def _process_news(
        self,
        raw: Dict[str, Any],
        target_symbols: List[str]
    ) -> Optional[NewsItem]:
        """Processa uma notícia individual."""
        
        # Extrai dados básicos
        title = raw.get('title', '') or raw.get('headline', '')
        description = raw.get('description', '') or raw.get('summary', '') or ''
        
        if not title:
            return None
        
        # Combina texto para análise
        full_text = f"{title} {description}".lower()
        
        # Identifica símbolos relevantes
        symbols = self._identify_symbols(full_text, target_symbols)
        
        # Analisa sentimento
        sentiment = self._analyze_sentiment(full_text)
        
        # Categoriza
        category = self._categorize(full_text)
        
        # Determina impacto
        impact = self._determine_impact(full_text, category)
        
        # Calcula relevância
        relevance = self._calculate_relevance(
            full_text, symbols, impact, target_symbols
        )
        
        # Parse da data
        published_at = self._parse_date(raw.get('publishedAt') or raw.get('datetime'))
        
        return NewsItem(
            id=raw.get('id', str(hash(title))),
            title=title,
            description=description[:500],
            source=raw.get('source', {}).get('name', '') or raw.get('source', 'Unknown'),
            url=raw.get('url', ''),
            published_at=published_at,
            impact=impact,
            sentiment=sentiment,
            category=category,
            symbols=symbols,
            keywords=self._extract_keywords(full_text),
            relevance_score=relevance,
            processed=True,
            processed_at=datetime.now(),
        )
    
    def _identify_symbols(
        self, text: str, target_symbols: List[str]
    ) -> List[str]:
        """Identifica símbolos mencionados no texto."""
        found = []
        
        for symbol, keywords in self._symbol_keywords.items():
            if symbol not in target_symbols and symbol != 'USD':
                continue
                
            for keyword in keywords:
                if keyword in text:
                    if symbol not in found:
                        found.append(symbol)
                    break
        
        # Se menciona USD, afeta todos os pares
        if 'USD' in found:
            found.remove('USD')
            for s in target_symbols:
                if s not in found:
                    found.append(s)
        
        return found
    
    def _analyze_sentiment(self, text: str) -> NewsSentiment:
        """Analisa sentimento do texto."""
        scores = {
            'very_bullish': 0,
            'bullish': 0,
            'bearish': 0,
            'very_bearish': 0,
        }
        
        for sentiment_type, words in self._sentiment_words.items():
            for word in words:
                if word in text:
                    scores[sentiment_type] += 1
        
        # Calcula score final
        final_score = (
            scores['very_bullish'] * 2 + 
            scores['bullish'] * 1 - 
            scores['bearish'] * 1 - 
            scores['very_bearish'] * 2
        )
        
        if final_score >= 3:
            return NewsSentiment.VERY_BULLISH
        elif final_score >= 1:
            return NewsSentiment.BULLISH
        elif final_score <= -3:
            return NewsSentiment.VERY_BEARISH
        elif final_score <= -1:
            return NewsSentiment.BEARISH
        else:
            return NewsSentiment.NEUTRAL
    
    def _categorize(self, text: str) -> NewsCategory:
        """Categoriza a notícia."""
        max_matches = 0
        best_category = NewsCategory.GENERAL
        
        for category, keywords in self._event_categories.items():
            matches = sum(1 for k in keywords if k in text)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        return best_category
    
    def _determine_impact(
        self, text: str, category: NewsCategory
    ) -> NewsImpact:
        """Determina impacto da notícia."""
        
        # Palavras de alto impacto
        critical_words = [
            'emergency', 'crisis', 'war', 'recession', 
            'collapse', 'rate decision', 'surprise', 'historic'
        ]
        
        high_words = [
            'fomc', 'fed', 'ecb', 'boe', 'nonfarm', 'cpi',
            'gdp', 'rate hike', 'rate cut', 'inflation',
        ]
        
        # Conta matches
        critical_count = sum(1 for w in critical_words if w in text)
        high_count = sum(1 for w in high_words if w in text)
        
        if critical_count >= 2:
            return NewsImpact.CRITICAL
        elif critical_count >= 1 or high_count >= 2:
            return NewsImpact.HIGH
        elif high_count >= 1 or category in [
            NewsCategory.CENTRAL_BANK, 
            NewsCategory.ECONOMIC_DATA
        ]:
            return NewsImpact.MEDIUM
        else:
            return NewsImpact.LOW
    
    def _calculate_relevance(
        self,
        text: str,
        symbols: List[str],
        impact: NewsImpact,
        target_symbols: List[str]
    ) -> float:
        """Calcula score de relevância."""
        score = 0.0
        
        # Base: símbolos encontrados
        symbol_match = len([s for s in symbols if s in target_symbols])
        score += symbol_match * 0.3
        
        # Impacto
        impact_scores = {
            NewsImpact.LOW: 0.1,
            NewsImpact.MEDIUM: 0.2,
            NewsImpact.HIGH: 0.3,
            NewsImpact.CRITICAL: 0.4,
        }
        score += impact_scores.get(impact, 0.1)
        
        # Recência (penaliza notícias antigas)
        # Aqui seria feito com base na data
        
        return min(1.0, score)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai palavras-chave do texto."""
        # Palavras relevantes para trading
        trading_words = [
            'fed', 'ecb', 'boe', 'fomc', 'rate', 'inflation',
            'gdp', 'cpi', 'employment', 'dollar', 'gold', 'euro',
            'pound', 'bullish', 'bearish', 'rally', 'crash',
        ]
        
        found = []
        for word in trading_words:
            if word in text and word not in found:
                found.append(word)
        
        return found[:10]  # Máximo 10 keywords
    
    def _parse_date(self, date_value: Any) -> datetime:
        """Parse de diferentes formatos de data."""
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, str):
            try:
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                pass
            
            try:
                return datetime.strptime(date_value, '%Y-%m-%dT%H:%M:%S')
            except:
                pass
        
        return datetime.now()
    
    # ========================================================================
    # SUMMARIES
    # ========================================================================
    
    async def get_symbol_summary(
        self,
        symbol: str,
        news_items: Optional[List[NewsItem]] = None,
        hours: int = 24
    ) -> NewsSummary:
        """
        Gera resumo de notícias para um símbolo.
        
        Args:
            symbol: Símbolo (ex: XAUUSD)
            news_items: Lista de notícias (usa cache se não fornecido)
            hours: Período em horas
            
        Returns:
            NewsSummary com análise agregada
        """
        now = datetime.now()
        period_start = now - timedelta(hours=hours)
        
        # Usa cache se não fornecido
        if news_items is None:
            news_items = [
                n for n in self._news_cache.values()
                if n.published_at >= period_start
            ]
        
        # Filtra por símbolo
        relevant = [
            n for n in news_items
            if symbol in n.symbols or not n.symbols
        ]
        
        if not relevant:
            return NewsSummary(
                symbol=symbol,
                period_start=period_start,
                period_end=now,
            )
        
        # Análises
        sentiments = [n.sentiment.value for n in relevant]
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        high_impact_count = len([
            n for n in relevant 
            if n.impact in [NewsImpact.HIGH, NewsImpact.CRITICAL]
        ])
        
        # Categoriza direção
        if avg_sentiment >= 1:
            direction = "bullish"
        elif avg_sentiment <= -1:
            direction = "bearish"
        else:
            direction = "neutral"
        
        # Top notícias por sentimento
        bullish_news = sorted(
            [n for n in relevant if n.sentiment.value > 0],
            key=lambda x: (x.sentiment.value, x.relevance_score),
            reverse=True
        )[:3]
        
        bearish_news = sorted(
            [n for n in relevant if n.sentiment.value < 0],
            key=lambda x: (abs(x.sentiment.value), x.relevance_score),
            reverse=True
        )[:3]
        
        # Contagem por categoria
        by_category = defaultdict(int)
        for n in relevant:
            by_category[n.category.value] += 1
        
        return NewsSummary(
            symbol=symbol,
            period_start=period_start,
            period_end=now,
            total_news=len(relevant),
            high_impact=high_impact_count,
            avg_sentiment=avg_sentiment,
            sentiment_direction=direction,
            top_bullish=bullish_news,
            top_bearish=bearish_news,
            by_category=dict(by_category),
        )
    
    async def get_daily_briefing(
        self,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Gera briefing diário de notícias.
        
        Returns:
            Dict com resumo geral e por símbolo
        """
        symbols = symbols or ['XAUUSD', 'EURUSD', 'GBPUSD']
        
        briefing = {
            'timestamp': datetime.now().isoformat(),
            'period': '24h',
            'summaries': {},
            'highlights': [],
            'overall_sentiment': 'neutral',
        }
        
        all_news = list(self._news_cache.values())
        sentiment_sum = 0
        
        for symbol in symbols:
            summary = await self.get_symbol_summary(symbol, all_news)
            briefing['summaries'][symbol] = summary.to_dict()
            sentiment_sum += summary.avg_sentiment
        
        # Overall sentiment
        if len(symbols) > 0:
            avg = sentiment_sum / len(symbols)
            if avg >= 0.5:
                briefing['overall_sentiment'] = 'bullish'
            elif avg <= -0.5:
                briefing['overall_sentiment'] = 'bearish'
        
        # Highlights - notícias de maior impacto
        highlights = sorted(
            all_news,
            key=lambda x: (
                x.impact == NewsImpact.CRITICAL,
                x.impact == NewsImpact.HIGH,
                x.relevance_score
            ),
            reverse=True
        )[:5]
        
        briefing['highlights'] = [n.to_dict() for n in highlights]
        
        return briefing
    
    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================
    
    def clear_cache(self, older_than_hours: Optional[int] = None) -> int:
        """Limpa cache de notícias."""
        if older_than_hours is None:
            count = len(self._news_cache)
            self._news_cache.clear()
            return count
        
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        to_remove = [
            k for k, v in self._news_cache.items()
            if v.published_at < cutoff
        ]
        
        for key in to_remove:
            del self._news_cache[key]
        
        return len(to_remove)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        if not self._news_cache:
            return {'count': 0}
        
        now = datetime.now()
        items = list(self._news_cache.values())
        
        return {
            'count': len(items),
            'oldest': min(n.published_at for n in items).isoformat(),
            'newest': max(n.published_at for n in items).isoformat(),
            'by_impact': {
                impact.value: len([n for n in items if n.impact == impact])
                for impact in NewsImpact
            },
        }
