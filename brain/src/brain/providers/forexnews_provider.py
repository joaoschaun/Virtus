"""
BRAIN - ForexNews Provider
Provider de notícias forex
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_provider import BaseProvider
from ...core.types import NewsItem, NewsImpact
from ...core.logger import get_logger
from ...core.exceptions import ProviderError

logger = get_logger("brain.provider.forexnews")


class ForexNewsProvider(BaseProvider):
    """
    Provider de notícias do ForexNews API
    
    https://forexnewsapi.com/
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # API key do ambiente se não configurada
        self._api_key = self._api_key or os.getenv("FOREXNEWS_API_KEY")
        self._base_url = config.get("base_url", "https://forexnewsapi.com/api/v1")
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Headers para ForexNews API"""
        return {
            "Accept": "application/json",
            "apikey": self._api_key or ""
        }
    
    async def get_news(
        self,
        symbol: Optional[str] = None,
        limit: int = 20
    ) -> List[NewsItem]:
        """
        Busca notícias
        
        Args:
            symbol: Símbolo (XAUUSD, EURUSD, etc.) ou None para todas
            limit: Número máximo de notícias
            
        Returns:
            Lista de NewsItem
        """
        if not self._api_key:
            logger.warning("ForexNews API key não configurada")
            return []
        
        try:
            params = {
                "items": min(limit, 50),
                "page": 1
            }
            
            # Mapear símbolo para currencies
            if symbol:
                currencies = self._symbol_to_currencies(symbol)
                if currencies:
                    params["currencypair"] = currencies
            
            response = await self._request("GET", "/news", params=params)
            
            news_list = []
            for item in response.get("data", []):
                news = self._parse_news_item(item)
                if news:
                    news_list.append(news)
            
            logger.debug(f"ForexNews: {len(news_list)} notícias obtidas")
            return news_list
            
        except ProviderError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar ForexNews: {e}")
            return []
    
    def _symbol_to_currencies(self, symbol: str) -> Optional[str]:
        """Converte símbolo para formato da API"""
        symbol_map = {
            "XAUUSD": "XAU,USD",
            "EURUSD": "EUR,USD",
            "GBPUSD": "GBP,USD",
            "USDJPY": "USD,JPY",
            "USDCHF": "USD,CHF",
            "AUDUSD": "AUD,USD",
            "NZDUSD": "NZD,USD",
            "USDCAD": "USD,CAD"
        }
        return symbol_map.get(symbol.upper())
    
    def _parse_news_item(self, data: Dict[str, Any]) -> Optional[NewsItem]:
        """Converte resposta da API em NewsItem"""
        try:
            # Parse da data
            published_str = data.get("date", "")
            published_at = datetime.now()
            if published_str:
                try:
                    published_at = datetime.fromisoformat(
                        published_str.replace("Z", "+00:00")
                    )
                except:
                    pass
            
            # Determinar impacto
            importance = data.get("importance", "low")
            impact_map = {
                "high": NewsImpact.HIGH,
                "medium": NewsImpact.MEDIUM,
                "low": NewsImpact.LOW
            }
            impact = impact_map.get(importance.lower(), NewsImpact.LOW)
            
            # Extrair símbolos
            currencies = data.get("currencies", [])
            symbols = self._currencies_to_symbols(currencies)
            
            return NewsItem(
                id=str(data.get("news_id", "")),
                title=data.get("title", ""),
                summary=data.get("text", "")[:500],  # Limitar tamanho
                source=data.get("source_name", "ForexNews"),
                url=data.get("news_url", ""),
                published_at=published_at,
                symbols=symbols,
                impact=impact,
                sentiment=0.0  # Será calculado pelo SentimentAnalyzer
            )
        except Exception as e:
            logger.error(f"Erro ao parsear notícia: {e}")
            return None
    
    def _currencies_to_symbols(self, currencies: List[str]) -> List[str]:
        """Converte lista de moedas em símbolos"""
        symbols = []
        
        currency_set = set(c.upper() for c in currencies)
        
        if "XAU" in currency_set or "GOLD" in currency_set:
            symbols.append("XAUUSD")
        if "EUR" in currency_set and "USD" in currency_set:
            symbols.append("EURUSD")
        if "GBP" in currency_set and "USD" in currency_set:
            symbols.append("GBPUSD")
        
        return symbols
    
    async def health_check(self) -> bool:
        """Verifica saúde do provider"""
        if not self._api_key:
            return False
        
        try:
            await self._request("GET", "/news", params={"items": 1})
            return True
        except:
            return False
