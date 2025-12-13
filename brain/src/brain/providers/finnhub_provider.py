"""
BRAIN - Finnhub Provider
Provider de dados financeiros Finnhub
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_provider import BaseProvider
from ...core.types import NewsItem, NewsImpact
from ...core.logger import get_logger
from ...core.exceptions import ProviderError

logger = get_logger("brain.provider.finnhub")


class FinnhubProvider(BaseProvider):
    """
    Provider de dados do Finnhub
    
    https://finnhub.io/
    
    Oferece:
    - Notícias gerais do mercado
    - Sentimento de mercado
    - Dados econômicos
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        self._api_key = self._api_key or os.getenv("FINNHUB_API_KEY")
        self._base_url = config.get("base_url", "https://finnhub.io/api/v1")
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Headers para Finnhub API"""
        return {
            "Accept": "application/json",
            "X-Finnhub-Token": self._api_key or ""
        }
    
    async def get_news(
        self,
        symbol: Optional[str] = None,
        limit: int = 20
    ) -> List[NewsItem]:
        """
        Busca notícias gerais do mercado
        
        Args:
            symbol: Símbolo (usado para filtrar relevância)
            limit: Número máximo
            
        Returns:
            Lista de NewsItem
        """
        if not self._api_key:
            logger.warning("Finnhub API key não configurada")
            return []
        
        try:
            # Finnhub usa categoria ao invés de símbolo
            category = self._get_category_for_symbol(symbol)
            
            params = {"category": category}
            
            response = await self._request("GET", "/news", params=params)
            
            news_list = []
            for item in response[:limit]:
                news = self._parse_news_item(item, symbol)
                if news:
                    news_list.append(news)
            
            logger.debug(f"Finnhub: {len(news_list)} notícias obtidas")
            return news_list
            
        except ProviderError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar Finnhub: {e}")
            return []
    
    def _get_category_for_symbol(self, symbol: Optional[str]) -> str:
        """Mapeia símbolo para categoria Finnhub"""
        if not symbol:
            return "general"
        
        symbol = symbol.upper()
        
        if "XAU" in symbol or "GOLD" in symbol:
            return "general"  # Finnhub não tem categoria específica para commodities
        elif any(c in symbol for c in ["EUR", "GBP", "JPY", "CHF", "AUD"]):
            return "forex"
        else:
            return "general"
    
    def _parse_news_item(
        self,
        data: Dict[str, Any],
        symbol: Optional[str]
    ) -> Optional[NewsItem]:
        """Converte resposta da API em NewsItem"""
        try:
            # Timestamp unix para datetime
            timestamp = data.get("datetime", 0)
            published_at = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
            
            # Finnhub não tem campo de impacto, estimamos por fonte
            source = data.get("source", "")
            impact = self._estimate_impact(source)
            
            # Determinar símbolos relevantes
            symbols = []
            if symbol:
                symbols = [symbol]
            else:
                symbols = self._extract_symbols_from_text(
                    data.get("headline", "") + " " + data.get("summary", "")
                )
            
            return NewsItem(
                id=str(data.get("id", "")),
                title=data.get("headline", ""),
                summary=data.get("summary", "")[:500],
                source=source,
                url=data.get("url", ""),
                published_at=published_at,
                symbols=symbols,
                impact=impact,
                sentiment=0.0
            )
        except Exception as e:
            logger.error(f"Erro ao parsear notícia Finnhub: {e}")
            return None
    
    def _estimate_impact(self, source: str) -> NewsImpact:
        """Estima impacto baseado na fonte"""
        high_impact_sources = [
            "reuters", "bloomberg", "wsj", "cnbc", "ft",
            "federal reserve", "ecb", "boe"
        ]
        
        medium_impact_sources = [
            "marketwatch", "investing", "fxstreet", "dailyfx"
        ]
        
        source_lower = source.lower()
        
        if any(s in source_lower for s in high_impact_sources):
            return NewsImpact.HIGH
        elif any(s in source_lower for s in medium_impact_sources):
            return NewsImpact.MEDIUM
        else:
            return NewsImpact.LOW
    
    def _extract_symbols_from_text(self, text: str) -> List[str]:
        """Extrai símbolos mencionados no texto"""
        symbols = []
        text_upper = text.upper()
        
        keywords = {
            "XAUUSD": ["GOLD", "XAU", "OURO", "PRECIOUS METAL"],
            "EURUSD": ["EUR/USD", "EURO", "EURUSD", "EUR"],
            "GBPUSD": ["GBP/USD", "POUND", "STERLING", "GBPUSD", "GBP"]
        }
        
        for symbol, kws in keywords.items():
            if any(kw in text_upper for kw in kws):
                symbols.append(symbol)
        
        return symbols
    
    async def get_market_sentiment(self) -> Dict[str, Any]:
        """
        Obtém sentimento geral do mercado
        
        Returns:
            Dict com métricas de sentimento
        """
        if not self._api_key:
            return {}
        
        try:
            # Finnhub Social Sentiment (para ações, mas útil como referência)
            response = await self._request(
                "GET",
                "/news-sentiment",
                params={"symbol": "SPY"}  # S&P 500 ETF como proxy
            )
            
            return {
                "buzz": response.get("buzz", {}),
                "sentiment": response.get("sentiment", {}),
                "company_news_score": response.get("companyNewsScore", 0)
            }
        except:
            return {}
    
    async def health_check(self) -> bool:
        """Verifica saúde do provider"""
        if not self._api_key:
            return False
        
        try:
            await self._request("GET", "/news", params={"category": "general"})
            return True
        except:
            return False
