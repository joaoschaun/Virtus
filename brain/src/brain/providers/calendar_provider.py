"""
BRAIN - Calendar Provider
Provider de calendário econômico
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import aiohttp

from .base_provider import BaseProvider
from ...core.types import CalendarEvent, NewsImpact
from ...core.logger import get_logger
from ...core.exceptions import ProviderError

logger = get_logger("brain.provider.calendar")


class CalendarProvider(BaseProvider):
    """
    Provider de calendário econômico
    
    Fontes possíveis:
    - Investing.com (scraping)
    - ForexFactory (scraping)
    - APIs pagas
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._source = config.get("source", "investing")
    
    async def get_events(
        self,
        days_ahead: int = 7,
        countries: Optional[List[str]] = None
    ) -> List[CalendarEvent]:
        """
        Obtém eventos do calendário econômico
        
        Args:
            days_ahead: Dias à frente para buscar
            countries: Lista de países (ex: ["US", "EU", "GB"])
            
        Returns:
            Lista de CalendarEvent
        """
        try:
            # Por enquanto, retornar eventos simulados
            # TODO: Implementar scraping ou API real
            
            events = self._get_sample_events(days_ahead)
            
            # Filtrar por países se especificado
            if countries:
                events = [
                    e for e in events
                    if e.country in countries
                ]
            
            return events
            
        except Exception as e:
            logger.error(f"Erro ao buscar calendário: {e}")
            return []
    
    def _get_sample_events(self, days_ahead: int) -> List[CalendarEvent]:
        """Retorna eventos de exemplo para desenvolvimento"""
        now = datetime.now()
        
        # Eventos comuns de alto impacto
        sample_events = [
            {
                "name": "Non-Farm Payrolls",
                "name_pt": "Folha de Pagamento Não-Agrícola",
                "country": "US",
                "currency": "USD",
                "impact": NewsImpact.HIGH,
                "time_offset": timedelta(days=2, hours=8, minutes=30)
            },
            {
                "name": "FOMC Meeting Minutes",
                "name_pt": "Atas da Reunião do FOMC",
                "country": "US",
                "currency": "USD",
                "impact": NewsImpact.HIGH,
                "time_offset": timedelta(days=3, hours=14)
            },
            {
                "name": "ECB Interest Rate Decision",
                "name_pt": "Decisão de Taxa de Juros do BCE",
                "country": "EU",
                "currency": "EUR",
                "impact": NewsImpact.HIGH,
                "time_offset": timedelta(days=5, hours=7, minutes=45)
            },
            {
                "name": "BOE Interest Rate Decision",
                "name_pt": "Decisão de Taxa de Juros do BOE",
                "country": "GB",
                "currency": "GBP",
                "impact": NewsImpact.HIGH,
                "time_offset": timedelta(days=4, hours=7)
            },
            {
                "name": "US CPI m/m",
                "name_pt": "IPC dos EUA (mensal)",
                "country": "US",
                "currency": "USD",
                "impact": NewsImpact.HIGH,
                "time_offset": timedelta(days=1, hours=8, minutes=30)
            },
            {
                "name": "US Retail Sales m/m",
                "name_pt": "Vendas no Varejo dos EUA",
                "country": "US",
                "currency": "USD",
                "impact": NewsImpact.MEDIUM,
                "time_offset": timedelta(days=6, hours=8, minutes=30)
            },
            {
                "name": "German ZEW Economic Sentiment",
                "name_pt": "Sentimento Econômico ZEW Alemão",
                "country": "DE",
                "currency": "EUR",
                "impact": NewsImpact.MEDIUM,
                "time_offset": timedelta(days=2, hours=5)
            }
        ]
        
        events = []
        for i, evt in enumerate(sample_events):
            event_time = now + evt["time_offset"]
            
            # Só incluir eventos dentro do período solicitado
            if event_time <= now + timedelta(days=days_ahead):
                events.append(CalendarEvent(
                    id=f"evt_{i}",
                    name=evt["name"],
                    name_pt=evt["name_pt"],
                    country=evt["country"],
                    currency=evt["currency"],
                    datetime=event_time,
                    impact=evt["impact"],
                    forecast="--",
                    previous="--"
                ))
        
        # Ordenar por data
        events.sort(key=lambda x: x.datetime)
        
        return events
    
    async def get_events_for_symbol(
        self,
        symbol: str,
        days_ahead: int = 7
    ) -> List[CalendarEvent]:
        """
        Obtém eventos relevantes para um símbolo específico
        
        Args:
            symbol: Símbolo (XAUUSD, EURUSD, etc.)
            days_ahead: Dias à frente
            
        Returns:
            Lista de eventos filtrados
        """
        # Mapear símbolo para países/moedas relevantes
        symbol_countries = self._get_relevant_countries(symbol)
        
        all_events = await self.get_events(days_ahead)
        
        # Filtrar eventos relevantes
        relevant = [
            e for e in all_events
            if e.country in symbol_countries or e.currency in symbol_countries
        ]
        
        return relevant
    
    def _get_relevant_countries(self, symbol: str) -> List[str]:
        """Retorna países/moedas relevantes para um símbolo"""
        symbol = symbol.upper()
        
        relevance_map = {
            "XAUUSD": ["US", "USD"],  # Gold é afetado principalmente por USD
            "EURUSD": ["US", "USD", "EU", "EUR", "DE"],
            "GBPUSD": ["US", "USD", "GB", "GBP"],
            "USDJPY": ["US", "USD", "JP", "JPY"],
            "USDCHF": ["US", "USD", "CH", "CHF"],
            "AUDUSD": ["US", "USD", "AU", "AUD"],
            "NZDUSD": ["US", "USD", "NZ", "NZD"],
            "USDCAD": ["US", "USD", "CA", "CAD"],
        }
        
        return relevance_map.get(symbol, ["US", "USD"])
    
    async def health_check(self) -> bool:
        """Verifica saúde do provider"""
        return True
