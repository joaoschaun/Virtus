"""
VIRTUS Brain - ForexNews Provider
==================================

Provider para API ForexNews - principal fonte de notícias e sentimento.

API Docs: https://forexnewsapi.com/
Features:
- Notícias de forex em tempo real
- Análise de sentimento
- Filtro por moedas
- Alto volume de requisições (1000/dia)
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base_provider import NewsProvider, SentimentProvider
from ...core.logger import get_logger
from ...core.types import NewsItem, MarketSentiment, SentimentLevel, NewsImpact
from ..cache import cached, CacheManager
from ..budget import BudgetManager

logger = get_logger("forexnews")


class ForexNewsProvider(NewsProvider, SentimentProvider):
    """
    Provider para ForexNews API.
    
    Principal fonte para:
    - Notícias de forex
    - Sentimento de mercado
    - Headlines para briefings
    """
    
    PROVIDER_NAME = "forexnews"
    BASE_URL = "https://forexnewsapi.com/api/v1"
    
    # Mapeamento de símbolos para formato ForexNewsAPI (EUR-USD format)
    SYMBOL_TO_PAIR = {
        'XAUUSD': 'XAU-USD',
        'EURUSD': 'EUR-USD',
        'GBPUSD': 'GBP-USD',
        'USDJPY': 'USD-JPY',
        'USDCHF': 'USD-CHF',
        'AUDUSD': 'AUD-USD',
        'USDCAD': 'USD-CAD',
        'NZDUSD': 'NZD-USD',
        'EURGBP': 'EUR-GBP',
        'EURJPY': 'EUR-JPY',
        'GBPJPY': 'GBP-JPY',
        'XAGUSD': 'XAG-USD',  # Silver
    }
    
    # Mapeamento de sentimento
    SENTIMENT_MAP = {
        'very_positive': SentimentLevel.VERY_BULLISH,
        'positive': SentimentLevel.BULLISH,
        'neutral': SentimentLevel.NEUTRAL,
        'negative': SentimentLevel.BEARISH,
        'very_negative': SentimentLevel.VERY_BEARISH,
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
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers com autenticação"""
        return {
            'Authorization': f'Bearer {self.api_key}'
        }
    
    def _symbol_to_pair(self, symbol: str) -> str:
        """Converte símbolo em formato ForexNewsAPI (EUR-USD)"""
        return self.SYMBOL_TO_PAIR.get(symbol, symbol)
    
    # ========================================================================
    # MÉTODOS PÚBLICOS
    # ========================================================================
    
    async def health_check(self) -> bool:
        """Verifica se a API está disponível"""
        try:
            params = {
                'token': self.api_key,
                'currencypair': 'EUR-USD',
                'items': 1
            }
            await self.get('', params=params)  # Endpoint raiz com params
            return True
        except Exception as e:
            logger.error(f"ForexNews health check falhou: {e}")
            return False
    
    async def get_supported_symbols(self) -> List[str]:
        """Retorna símbolos suportados"""
        return list(self.SYMBOL_TO_CURRENCIES.keys())
    
    async def get_news(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 10,
        hours_back: int = 24
    ) -> List[NewsItem]:
        """
        Busca notícias para símbolos.
        
        Args:
            symbols: Lista de símbolos (ex: ['XAUUSD', 'EURUSD'])
            limit: Número máximo de notícias
            hours_back: Horas no passado para buscar
            
        Returns:
            Lista de NewsItem
        """
        all_news = []
        
        # Se nenhum símbolo especificado, busca para todos os pares configurados
        if not symbols:
            symbols = list(self.SYMBOL_TO_PAIR.keys())[:3]  # Top 3 por padrão
        
        # Busca notícias para cada símbolo (API aceita um par por vez)
        for symbol in symbols:
            currency_pair = self._symbol_to_pair(symbol)
            
            params = {
                'token': self.api_key,
                'currencypair': currency_pair,
                'items': min(limit, 50),  # API max é 50
            }
            
            try:
                response = await self.get('', params=params)  # Endpoint raiz com params
                
                for item in response.get('data', []):
                    news = self._parse_news_item(item, [symbol])
                    if news:
                        all_news.append(news)
                        
            except Exception as e:
                logger.warning(f"Erro ao buscar notícias para {symbol}: {e}")
                continue
        
        # Remove duplicatas por URL e ordena por data
        seen_urls = set()
        unique_news = []
        for news in all_news:
            if news.url not in seen_urls:
                seen_urls.add(news.url)
                unique_news.append(news)
        
        unique_news.sort(key=lambda x: x.timestamp, reverse=True)
        
        logger.debug(f"ForexNews: {len(unique_news)} notícias encontradas")
        return unique_news[:limit]
    
    async def get_sentiment(
        self,
        symbol: str
    ) -> Optional[MarketSentiment]:
        """
        Calcula sentimento agregado para um símbolo.
        
        Args:
            symbol: Símbolo (ex: 'XAUUSD')
            
        Returns:
            MarketSentiment com scores agregados
        """
        try:
            # Busca notícias recentes
            news = await self.get_news(symbols=[symbol], limit=20, hours_back=24)
            
            if not news:
                return MarketSentiment(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    news_sentiment=0.0,
                    overall_sentiment=0.0,
                    sentiment_level=SentimentLevel.NEUTRAL,
                    explanation_pt="Sem notícias recentes para análise"
                )
            
            # Agrega sentimentos
            total_score = sum(n.sentiment_score for n in news)
            avg_score = total_score / len(news)
            
            # Determina nível
            if avg_score >= 0.6:
                level = SentimentLevel.VERY_BULLISH
            elif avg_score >= 0.2:
                level = SentimentLevel.BULLISH
            elif avg_score >= -0.2:
                level = SentimentLevel.NEUTRAL
            elif avg_score >= -0.6:
                level = SentimentLevel.BEARISH
            else:
                level = SentimentLevel.VERY_BEARISH
            
            # Monta explicação
            explanation_pt = self._generate_sentiment_explanation(
                symbol, avg_score, len(news), level
            )
            
            return MarketSentiment(
                symbol=symbol,
                timestamp=datetime.now(),
                news_sentiment=avg_score,
                overall_sentiment=avg_score,
                sentiment_level=level,
                news_count=len(news),
                sources=['ForexNews'],
                explanation_pt=explanation_pt
            )
            
        except Exception as e:
            logger.error(f"Erro ao calcular sentimento ForexNews: {e}")
            return None
    
    async def get_top_headlines(
        self,
        limit: int = 5
    ) -> List[NewsItem]:
        """
        Busca principais headlines do dia.
        
        Args:
            limit: Número de headlines
            
        Returns:
            Lista de headlines principais
        """
        # Busca notícias dos principais pares
        headlines = []
        main_pairs = ['EUR-USD', 'GBP-USD', 'XAU-USD']
        
        for pair in main_pairs:
            params = {
                'token': self.api_key,
                'currencypair': pair,
                'items': limit
            }
            
            try:
                response = await self.get('', params=params)
                
                for item in response.get('data', []):
                    news = self._parse_news_item(item, [])
                    if news:
                        headlines.append(news)
            except Exception as e:
                logger.warning(f"Erro ao buscar headlines para {pair}: {e}")
                continue
        
        # Remove duplicatas e ordena por data
        seen_urls = set()
        unique_headlines = []
        for news in headlines:
            if news.url not in seen_urls:
                seen_urls.add(news.url)
                unique_headlines.append(news)
        
        unique_headlines.sort(key=lambda x: x.timestamp, reverse=True)
        return unique_headlines[:limit]
    
    # ========================================================================
    # MÉTODOS PRIVADOS
    # ========================================================================
    
    def _parse_news_item(
        self,
        data: Dict[str, Any],
        symbols: List[str]
    ) -> Optional[NewsItem]:
        """Converte resposta da API em NewsItem"""
        try:
            # Parse timestamp - formato: "Sun, 14 Dec 2025 00:52:46 -0500"
            date_str = data.get('date', '')
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    timestamp = parsedate_to_datetime(date_str)
                except:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # Extrai sentimento - ForexNewsAPI retorna "Positive", "Negative", "Neutral"
            sentiment_str = data.get('sentiment', 'Neutral').lower()
            
            # Mapeia para score numérico
            sentiment_scores = {
                'positive': 0.5,
                'negative': -0.5,
                'neutral': 0.0,
            }
            sentiment_score = sentiment_scores.get(sentiment_str, 0.0)
            
            # Mapeia para SentimentLevel
            sentiment_levels = {
                'positive': SentimentLevel.BULLISH,
                'negative': SentimentLevel.BEARISH,
                'neutral': SentimentLevel.NEUTRAL,
            }
            sentiment_label = sentiment_levels.get(sentiment_str, SentimentLevel.NEUTRAL)
            
            # Determina impacto
            impact = self._determine_impact(data)
            
            # Extrai símbolos da notícia (currency field: ["EUR-USD"])
            news_currencies = data.get('currency', [])
            if news_currencies and not symbols:
                # Converte EUR-USD para EURUSD
                symbols = [c.replace('-', '') for c in news_currencies]
            
            return NewsItem(
                title=data.get('title', ''),
                summary=data.get('text', '')[:500],
                source=data.get('source_name', 'ForexNews'),
                timestamp=timestamp,
                url=data.get('news_url'),
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                impact=impact,
                symbols=symbols
            )
            
        except Exception as e:
            logger.warning(f"Erro ao parsear notícia: {e}")
            return None
    
    def _determine_impact(self, data: Dict[str, Any]) -> NewsImpact:
        """Determina impacto da notícia"""
        # Analisa keywords para determinar impacto
        title = data.get('title', '').lower()
        text = data.get('text', '').lower()
        content = title + ' ' + text
        
        high_impact_keywords = [
            'fed', 'fomc', 'interest rate', 'inflation', 'gdp',
            'payroll', 'unemployment', 'central bank', 'ecb',
            'boe', 'breaking', 'urgent', 'crisis'
        ]
        
        medium_impact_keywords = [
            'retail sales', 'manufacturing', 'pmi', 'consumer',
            'trade balance', 'housing', 'earnings'
        ]
        
        for keyword in high_impact_keywords:
            if keyword in content:
                return NewsImpact.HIGH
        
        for keyword in medium_impact_keywords:
            if keyword in content:
                return NewsImpact.MEDIUM
        
        return NewsImpact.LOW
    
    def _generate_sentiment_explanation(
        self,
        symbol: str,
        score: float,
        news_count: int,
        level: SentimentLevel
    ) -> str:
        """Gera explicação em português do sentimento"""
        
        level_text = {
            SentimentLevel.VERY_BULLISH: "muito positivo (altista forte)",
            SentimentLevel.BULLISH: "positivo (altista)",
            SentimentLevel.NEUTRAL: "neutro",
            SentimentLevel.BEARISH: "negativo (baixista)",
            SentimentLevel.VERY_BEARISH: "muito negativo (baixista forte)"
        }
        
        return (
            f"Análise de {news_count} notícias recentes sobre {symbol}. "
            f"Sentimento geral: {level_text.get(level, 'neutro')} "
            f"(score: {score:.2f})"
        )
