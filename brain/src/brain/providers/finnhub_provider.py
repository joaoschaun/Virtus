"""
VIRTUS Brain - Finnhub Provider
================================

Provider para API Finnhub - calendário econômico e notícias.

API Docs: https://finnhub.io/docs/api/
Features:
- Calendário econômico
- Notícias de mercado
- Dados fundamentais
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base_provider import CalendarProvider, NewsProvider
from ...core.logger import get_logger
from ...core.types import EconomicEvent, NewsItem, NewsImpact, SentimentLevel
from ..cache import CacheManager
from ..budget import BudgetManager

logger = get_logger("finnhub")


class FinnhubProvider(CalendarProvider, NewsProvider):
    """
    Provider para Finnhub API.
    
    Principal fonte para:
    - Calendário econômico
    - Notícias gerais de mercado
    """
    
    PROVIDER_NAME = "finnhub"
    BASE_URL = "https://finnhub.io/api/v1"
    
    # Mapeamento de moedas para países/regiões
    CURRENCY_TO_COUNTRY = {
        'USD': 'US',
        'EUR': 'EU',
        'GBP': 'GB',
        'JPY': 'JP',
        'CHF': 'CH',
        'AUD': 'AU',
        'NZD': 'NZ',
        'CAD': 'CA',
    }
    
    # Mapeamento de impacto
    IMPACT_MAP = {
        'low': NewsImpact.LOW,
        'medium': NewsImpact.MEDIUM,
        'high': NewsImpact.HIGH,
        1: NewsImpact.LOW,
        2: NewsImpact.MEDIUM,
        3: NewsImpact.HIGH,
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
    
    def _get_params(self) -> Dict[str, str]:
        """Parâmetros base com token"""
        return {'token': self.api_key}
    
    # ========================================================================
    # MÉTODOS PÚBLICOS
    # ========================================================================
    
    async def health_check(self) -> bool:
        """Verifica se a API está disponível"""
        try:
            params = self._get_params()
            params['category'] = 'forex'  # Buscar notícias forex para test
            await self.get('news', params=params)
            return True
        except Exception as e:
            logger.error(f"Finnhub health check falhou: {e}")
            return False
    
    async def get_supported_symbols(self) -> List[str]:
        """Retorna símbolos suportados"""
        return ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY']
    
    async def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        currencies: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """
        Busca eventos do calendário econômico.
        
        Args:
            start_date: Data inicial (default: hoje)
            end_date: Data final (default: +7 dias)
            currencies: Moedas para filtrar
            
        Returns:
            Lista de EconomicEvent
        """
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date + timedelta(days=7)
        
        params = self._get_params()
        params['from'] = start_date.strftime('%Y-%m-%d')
        params['to'] = end_date.strftime('%Y-%m-%d')
        
        try:
            response = await self.get('calendar/economic', params=params)
            
            events = []
            for item in response.get('economicCalendar', []):
                event = self._parse_economic_event(item)
                if event:
                    # Filtra por moeda se especificado
                    if currencies is None or event.currency in currencies:
                        events.append(event)
            
            # Ordena por timestamp
            events.sort(key=lambda x: x.timestamp)
            
            logger.debug(f"Finnhub: {len(events)} eventos encontrados")
            return events
            
        except Exception as e:
            logger.error(f"Erro ao buscar calendário Finnhub: {e}")
            return []
    
    async def get_news(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[NewsItem]:
        """
        Busca notícias gerais de mercado.
        
        Args:
            symbols: Não usado (finnhub retorna notícias gerais)
            limit: Número máximo de notícias
            
        Returns:
            Lista de NewsItem
        """
        params = self._get_params()
        params['category'] = 'forex'
        
        try:
            response = await self.get('news', params=params)
            
            news_items = []
            for item in response[:limit]:
                news = self._parse_news_item(item)
                if news:
                    news_items.append(news)
            
            logger.debug(f"Finnhub: {len(news_items)} notícias encontradas")
            return news_items
            
        except Exception as e:
            logger.error(f"Erro ao buscar notícias Finnhub: {e}")
            return []
    
    async def get_today_events(
        self,
        currencies: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """
        Busca eventos de hoje.
        
        Args:
            currencies: Moedas para filtrar
            
        Returns:
            Lista de eventos do dia
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        return await self.get_events(
            start_date=today,
            end_date=tomorrow,
            currencies=currencies
        )
    
    async def get_high_impact_events(
        self,
        days_ahead: int = 7,
        currencies: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """
        Busca eventos de alto impacto.
        
        Args:
            days_ahead: Dias para frente
            currencies: Moedas para filtrar
            
        Returns:
            Eventos de alto impacto
        """
        events = await self.get_events(
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=days_ahead),
            currencies=currencies
        )
        
        return [e for e in events if e.impact == NewsImpact.HIGH]
    
    # ========================================================================
    # MÉTODOS PRIVADOS
    # ========================================================================
    
    def _parse_economic_event(
        self,
        data: Dict[str, Any]
    ) -> Optional[EconomicEvent]:
        """Converte resposta da API em EconomicEvent"""
        try:
            # Parse timestamp
            timestamp_str = data.get('time')
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                # Usa data se não tiver hora
                date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
                timestamp = datetime.strptime(date_str, '%Y-%m-%d')
            
            # País para moeda
            country = data.get('country', '')
            currency = next(
                (k for k, v in self.CURRENCY_TO_COUNTRY.items() if v == country),
                country
            )
            
            # Impacto
            impact_raw = data.get('impact', 'low')
            impact = self.IMPACT_MAP.get(impact_raw, NewsImpact.LOW)
            
            # Nome em português (traduções básicas)
            name = data.get('event', '')
            name_pt = self._translate_event_name(name)
            
            return EconomicEvent(
                name=name,
                country=country,
                currency=currency,
                timestamp=timestamp,
                impact=impact,
                actual=data.get('actual'),
                forecast=data.get('estimate'),
                previous=data.get('prev'),
                name_pt=name_pt
            )
            
        except Exception as e:
            logger.warning(f"Erro ao parsear evento: {e}")
            return None
    
    def _parse_news_item(
        self,
        data: Dict[str, Any]
    ) -> Optional[NewsItem]:
        """Converte resposta da API em NewsItem"""
        try:
            # Timestamp
            timestamp_raw = data.get('datetime')
            if timestamp_raw:
                timestamp = datetime.fromtimestamp(timestamp_raw)
            else:
                timestamp = datetime.now()
            
            return NewsItem(
                title=data.get('headline', ''),
                summary=data.get('summary', '')[:500],
                source=data.get('source', 'Finnhub'),
                timestamp=timestamp,
                url=data.get('url'),
                sentiment_score=0,  # Finnhub não fornece sentimento
                sentiment_label=SentimentLevel.NEUTRAL,
                impact=NewsImpact.LOW,
                symbols=[]
            )
            
        except Exception as e:
            logger.warning(f"Erro ao parsear notícia: {e}")
            return None
    
    def _translate_event_name(self, name: str) -> str:
        """Traduz nomes de eventos comuns para português"""
        translations = {
            # Fed/US
            'Interest Rate Decision': 'Decisão de Taxa de Juros',
            'FOMC Meeting Minutes': 'Atas da Reunião do FOMC',
            'Non-Farm Payrolls': 'Folha de Pagamento Não-Agrícola',
            'Unemployment Rate': 'Taxa de Desemprego',
            'CPI': 'Índice de Preços ao Consumidor',
            'Core CPI': 'IPC Núcleo',
            'PPI': 'Índice de Preços ao Produtor',
            'GDP': 'PIB',
            'Retail Sales': 'Vendas no Varejo',
            'Consumer Confidence': 'Confiança do Consumidor',
            'Manufacturing PMI': 'PMI Industrial',
            'Services PMI': 'PMI de Serviços',
            'Trade Balance': 'Balança Comercial',
            'Housing Starts': 'Início de Construções',
            'Building Permits': 'Licenças de Construção',
            'Durable Goods Orders': 'Pedidos de Bens Duráveis',
            'Initial Jobless Claims': 'Pedidos Iniciais de Seguro-Desemprego',
            
            # ECB/EU
            'ECB Interest Rate Decision': 'Decisão de Taxa do BCE',
            'ECB Press Conference': 'Conferência do BCE',
            
            # BoE/UK
            'BoE Interest Rate Decision': 'Decisão de Taxa do BoE',
            'BoE Meeting Minutes': 'Atas do BoE',
        }
        
        for eng, pt in translations.items():
            if eng.lower() in name.lower():
                return pt
        
        return name
