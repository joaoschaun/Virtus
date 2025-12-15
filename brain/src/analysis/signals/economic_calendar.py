"""
VIRTUS Economic Calendar
=========================

Integração com calendário econômico para evitar eventos de alto impacto.

Funcionalidades:
- Obtém eventos de APIs (Forex Factory, ForexNews, Finnhub)
- Classifica impacto (HIGH, MEDIUM, LOW)
- Bloqueia trades antes/depois de eventos de alto impacto
- Suporte a múltiplas moedas (USD, EUR, GBP, JPY, AUD, CAD, CHF, NZD)
- Cache para reduzir chamadas API
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta, timezone
import logging
import json


class EventImpact(Enum):
    """Impacto do evento econômico."""
    HIGH = auto()      # NFP, CPI, FOMC, ECB, etc.
    MEDIUM = auto()    # PMI, Retail Sales, etc.
    LOW = auto()       # Housing, Consumer Confidence
    NONE = auto()      # Sem impacto significativo


class EventRestriction(Enum):
    """Restrição de trading para o evento."""
    BLOCK_ALL = auto()       # Não operar
    BLOCK_CURRENCY = auto()  # Não operar par com essa moeda
    REDUCE_SIZE = auto()     # Reduzir tamanho
    TIGHTEN_STOPS = auto()   # Stops mais apertados
    NO_RESTRICTION = auto()  # Sem restrição


@dataclass
class EconomicEvent:
    """Um evento econômico."""
    id: str
    title: str
    currency: str
    impact: EventImpact
    datetime_utc: datetime
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    
    # Calculados
    restriction: EventRestriction = EventRestriction.NO_RESTRICTION
    minutes_until: int = 0
    
    def __post_init__(self):
        now = datetime.now(timezone.utc)
        if self.datetime_utc.tzinfo is None:
            self.datetime_utc = self.datetime_utc.replace(tzinfo=timezone.utc)
        
        diff = (self.datetime_utc - now).total_seconds() / 60
        self.minutes_until = int(diff)
        
        # Define restrição baseada no impacto
        if self.impact == EventImpact.HIGH:
            self.restriction = EventRestriction.BLOCK_CURRENCY
        elif self.impact == EventImpact.MEDIUM:
            self.restriction = EventRestriction.REDUCE_SIZE


@dataclass
class CalendarAnalysisResult:
    """Resultado da análise do calendário."""
    is_safe: bool
    blocking_event: Optional[EconomicEvent]
    upcoming_events: List[EconomicEvent]
    affected_currencies: List[str]
    restriction: EventRestriction
    risk_multiplier: float
    cooldown_minutes: int
    next_high_impact_event: Optional[EconomicEvent]
    details: Dict[str, Any]


# Eventos de alto impacto conhecidos
HIGH_IMPACT_EVENTS = [
    # USD
    'Non-Farm Payrolls', 'NFP', 'FOMC', 'Fed Interest Rate',
    'CPI', 'Core CPI', 'PPI', 'GDP', 'Retail Sales',
    'Unemployment Rate', 'Fed Chair Powell',
    
    # EUR
    'ECB Interest Rate', 'ECB Press Conference',
    'German CPI', 'Eurozone CPI', 'German GDP',
    
    # GBP
    'BOE Interest Rate', 'UK CPI', 'UK GDP',
    
    # JPY
    'BOJ Interest Rate', 'Japan CPI',
    
    # Others
    'RBA Interest Rate', 'BOC Interest Rate',
    'SNB Interest Rate', 'RBNZ Interest Rate',
]

MEDIUM_IMPACT_EVENTS = [
    'PMI', 'ISM Manufacturing', 'ISM Services',
    'Retail Sales', 'Industrial Production',
    'Housing Starts', 'Building Permits',
    'Trade Balance', 'Current Account',
    'Consumer Confidence', 'Business Confidence',
    'Employment Change', 'ADP Employment',
]


class EconomicCalendar:
    """
    Calendário econômico com integração de APIs.
    
    Gerencia eventos econômicos e protege contra
    volatilidade de notícias.
    """
    
    # Tempos de bloqueio (minutos)
    BLOCK_BEFORE_HIGH = 30     # 30 min antes de evento HIGH
    BLOCK_AFTER_HIGH = 15      # 15 min depois de evento HIGH
    BLOCK_BEFORE_MEDIUM = 10   # 10 min antes de evento MEDIUM
    BLOCK_AFTER_MEDIUM = 5     # 5 min depois de evento MEDIUM
    
    def __init__(
        self,
        logger: logging.Logger = None,
        # API Keys
        forexnews_api_key: str = None,
        finnhub_api_key: str = None,
        # Configurações
        cache_ttl_minutes: int = 30,
        currencies: List[str] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        
        self.forexnews_api_key = forexnews_api_key
        self.finnhub_api_key = finnhub_api_key
        
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.currencies = currencies or ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD']
        
        # Cache
        self._events_cache: List[EconomicEvent] = []
        self._cache_time: Optional[datetime] = None
    
    async def get_events(
        self,
        force_refresh: bool = False,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> List[EconomicEvent]:
        """
        Obtém eventos do calendário.
        
        Args:
            force_refresh: Força atualização do cache
            start_date: Data inicial (default: hoje)
            end_date: Data final (default: próximos 3 dias)
            
        Returns:
            Lista de eventos
        """
        now = datetime.now(timezone.utc)
        
        # Verifica cache
        if not force_refresh and self._cache_valid():
            return self._filter_events(self._events_cache, start_date, end_date)
        
        events = []
        
        # Tenta ForexNews API
        if self.forexnews_api_key:
            try:
                forexnews_events = await self._fetch_forexnews()
                events.extend(forexnews_events)
            except Exception as e:
                self.logger.warning(f"Erro ForexNews API: {e}")
        
        # Tenta Finnhub API
        if self.finnhub_api_key and not events:
            try:
                finnhub_events = await self._fetch_finnhub()
                events.extend(finnhub_events)
            except Exception as e:
                self.logger.warning(f"Erro Finnhub API: {e}")
        
        # Se não conseguiu de APIs, usa dados estáticos
        if not events:
            events = self._get_static_events()
        
        # Atualiza cache
        self._events_cache = events
        self._cache_time = now
        
        return self._filter_events(events, start_date, end_date)
    
    async def analyze(
        self,
        symbol: str,
        force_refresh: bool = False,
    ) -> CalendarAnalysisResult:
        """
        Analisa eventos para um símbolo.
        
        Args:
            symbol: Par de moedas (ex: 'EURUSD')
            force_refresh: Força atualização
            
        Returns:
            CalendarAnalysisResult
        """
        # Extrai moedas do símbolo
        currencies = self._extract_currencies(symbol)
        
        # Obtém eventos
        events = await self.get_events(force_refresh)
        
        # Filtra eventos relevantes para as moedas
        relevant_events = [
            e for e in events
            if e.currency in currencies
        ]
        
        # Ordena por horário
        relevant_events.sort(key=lambda e: e.datetime_utc)
        
        # Análise de bloqueio
        is_safe, blocking_event, restriction = self._check_blocking(relevant_events)
        
        # Calcula risk multiplier
        risk_mult = self._calculate_risk_multiplier(relevant_events)
        
        # Próximo evento de alto impacto
        next_high = next(
            (e for e in relevant_events if e.impact == EventImpact.HIGH and e.minutes_until > 0),
            None
        )
        
        # Cooldown
        cooldown = 0
        if blocking_event:
            if blocking_event.minutes_until < 0:
                # Evento já passou, cooldown é o restante
                if blocking_event.impact == EventImpact.HIGH:
                    cooldown = max(0, self.BLOCK_AFTER_HIGH + blocking_event.minutes_until)
                else:
                    cooldown = max(0, self.BLOCK_AFTER_MEDIUM + blocking_event.minutes_until)
            else:
                # Evento ainda não ocorreu
                cooldown = blocking_event.minutes_until
        
        return CalendarAnalysisResult(
            is_safe=is_safe,
            blocking_event=blocking_event,
            upcoming_events=relevant_events[:10],  # Próximos 10
            affected_currencies=currencies,
            restriction=restriction,
            risk_multiplier=risk_mult,
            cooldown_minutes=cooldown,
            next_high_impact_event=next_high,
            details={
                'total_events': len(relevant_events),
                'high_impact_count': len([e for e in relevant_events if e.impact == EventImpact.HIGH]),
                'currencies': currencies,
            }
        )
    
    def _cache_valid(self) -> bool:
        """Verifica se cache é válido."""
        if not self._cache_time or not self._events_cache:
            return False
        
        age = datetime.now(timezone.utc) - self._cache_time
        return age < self.cache_ttl
    
    def _filter_events(
        self,
        events: List[EconomicEvent],
        start: datetime = None,
        end: datetime = None,
    ) -> List[EconomicEvent]:
        """Filtra eventos por data."""
        now = datetime.now(timezone.utc)
        
        if start is None:
            start = now - timedelta(hours=2)  # Inclui eventos recentes
        
        if end is None:
            end = now + timedelta(days=3)
        
        return [
            e for e in events
            if start <= e.datetime_utc <= end
        ]
    
    def _extract_currencies(self, symbol: str) -> List[str]:
        """Extrai moedas de um símbolo."""
        symbol = symbol.upper()
        
        # Pares forex padrão (EURUSD, GBPJPY, etc.)
        if len(symbol) == 6:
            return [symbol[:3], symbol[3:]]
        
        # Ouro, Prata
        if 'XAU' in symbol or 'GOLD' in symbol:
            return ['USD', 'XAU']
        
        if 'XAG' in symbol or 'SILVER' in symbol:
            return ['USD', 'XAG']
        
        # Índices
        if 'US30' in symbol or 'DJ' in symbol:
            return ['USD']
        
        if 'US500' in symbol or 'SPX' in symbol:
            return ['USD']
        
        if 'NAS' in symbol or 'USTEC' in symbol:
            return ['USD']
        
        if 'DAX' in symbol or 'GER' in symbol:
            return ['EUR']
        
        if 'UK100' in symbol or 'FTSE' in symbol:
            return ['GBP']
        
        return ['USD']  # Default
    
    def _classify_impact(self, title: str) -> EventImpact:
        """Classifica impacto do evento pelo título."""
        title_upper = title.upper()
        
        # High impact
        for keyword in HIGH_IMPACT_EVENTS:
            if keyword.upper() in title_upper:
                return EventImpact.HIGH
        
        # Medium impact
        for keyword in MEDIUM_IMPACT_EVENTS:
            if keyword.upper() in title_upper:
                return EventImpact.MEDIUM
        
        return EventImpact.LOW
    
    def _check_blocking(
        self,
        events: List[EconomicEvent]
    ) -> Tuple[bool, Optional[EconomicEvent], EventRestriction]:
        """Verifica se algum evento bloqueia trading."""
        
        for event in events:
            minutes = event.minutes_until
            
            if event.impact == EventImpact.HIGH:
                # Antes do evento
                if 0 < minutes <= self.BLOCK_BEFORE_HIGH:
                    return False, event, EventRestriction.BLOCK_CURRENCY
                
                # Depois do evento
                if -self.BLOCK_AFTER_HIGH <= minutes <= 0:
                    return False, event, EventRestriction.BLOCK_CURRENCY
            
            elif event.impact == EventImpact.MEDIUM:
                if 0 < minutes <= self.BLOCK_BEFORE_MEDIUM:
                    return False, event, EventRestriction.REDUCE_SIZE
                
                if -self.BLOCK_AFTER_MEDIUM <= minutes <= 0:
                    return False, event, EventRestriction.REDUCE_SIZE
        
        return True, None, EventRestriction.NO_RESTRICTION
    
    def _calculate_risk_multiplier(self, events: List[EconomicEvent]) -> float:
        """Calcula multiplicador de risco baseado em eventos."""
        multiplier = 1.0
        
        for event in events:
            if event.minutes_until < 0:
                continue  # Já passou
            
            if event.minutes_until > 120:
                continue  # Muito distante
            
            if event.impact == EventImpact.HIGH:
                if event.minutes_until <= 60:
                    multiplier *= 0.5
                elif event.minutes_until <= 120:
                    multiplier *= 0.7
            
            elif event.impact == EventImpact.MEDIUM:
                if event.minutes_until <= 30:
                    multiplier *= 0.8
        
        return max(0.0, min(1.0, multiplier))
    
    async def _fetch_forexnews(self) -> List[EconomicEvent]:
        """Busca eventos da ForexNews API."""
        events = []
        
        url = 'https://forexnewsapi.com/api/v1/stat/calendar'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params={'token': self.forexnews_api_key}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get('data', []):
                        try:
                            event = EconomicEvent(
                                id=str(item.get('id', '')),
                                title=item.get('title', ''),
                                currency=item.get('currency', '').upper(),
                                impact=self._classify_impact(item.get('title', '')),
                                datetime_utc=datetime.fromisoformat(
                                    item.get('date', '').replace('Z', '+00:00')
                                ),
                                actual=item.get('actual'),
                                forecast=item.get('forecast'),
                                previous=item.get('previous'),
                            )
                            events.append(event)
                        except Exception as e:
                            self.logger.debug(f"Erro parsing evento: {e}")
        
        return events
    
    async def _fetch_finnhub(self) -> List[EconomicEvent]:
        """Busca eventos da Finnhub API."""
        events = []
        
        now = datetime.now(timezone.utc)
        start = now.strftime('%Y-%m-%d')
        end = (now + timedelta(days=7)).strftime('%Y-%m-%d')
        
        url = 'https://finnhub.io/api/v1/calendar/economic'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params={
                    'token': self.finnhub_api_key,
                    'from': start,
                    'to': end,
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get('economicCalendar', []):
                        try:
                            # Extrai moeda do país
                            country = item.get('country', '')
                            currency = self._country_to_currency(country)
                            
                            if currency not in self.currencies:
                                continue
                            
                            # Parse datetime
                            dt_str = f"{item.get('date', '')} {item.get('time', '00:00')}"
                            try:
                                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
                                dt = dt.replace(tzinfo=timezone.utc)
                            except:
                                dt = datetime.now(timezone.utc)
                            
                            event = EconomicEvent(
                                id=f"finnhub_{item.get('id', '')}",
                                title=item.get('event', ''),
                                currency=currency,
                                impact=self._classify_impact(item.get('event', '')),
                                datetime_utc=dt,
                                actual=str(item.get('actual', '')) if item.get('actual') else None,
                                forecast=str(item.get('estimate', '')) if item.get('estimate') else None,
                                previous=str(item.get('prev', '')) if item.get('prev') else None,
                            )
                            events.append(event)
                        except Exception as e:
                            self.logger.debug(f"Erro parsing Finnhub: {e}")
        
        return events
    
    def _country_to_currency(self, country: str) -> str:
        """Converte país para moeda."""
        mapping = {
            'US': 'USD', 'USA': 'USD', 'United States': 'USD',
            'EU': 'EUR', 'EMU': 'EUR', 'Eurozone': 'EUR', 'Germany': 'EUR',
            'UK': 'GBP', 'United Kingdom': 'GBP', 'Britain': 'GBP',
            'JP': 'JPY', 'Japan': 'JPY',
            'AU': 'AUD', 'Australia': 'AUD',
            'CA': 'CAD', 'Canada': 'CAD',
            'CH': 'CHF', 'Switzerland': 'CHF',
            'NZ': 'NZD', 'New Zealand': 'NZD',
        }
        return mapping.get(country, 'USD')
    
    def _get_static_events(self) -> List[EconomicEvent]:
        """
        Retorna eventos estáticos/recorrentes como fallback.
        
        NFP: Primeira sexta-feira do mês 12:30 UTC
        FOMC: 8 reuniões por ano 18:00 UTC
        """
        events = []
        now = datetime.now(timezone.utc)
        
        # Simula próximos eventos importantes
        # (Em produção, isso seria obtido das APIs)
        
        # Próxima sexta-feira (possível NFP)
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        
        next_friday = now + timedelta(days=days_until_friday)
        
        # Se for primeira sexta do mês
        if next_friday.day <= 7:
            events.append(EconomicEvent(
                id='static_nfp',
                title='Non-Farm Payrolls (NFP)',
                currency='USD',
                impact=EventImpact.HIGH,
                datetime_utc=next_friday.replace(hour=12, minute=30, second=0, microsecond=0),
            ))
        
        return events
    
    def is_safe_to_trade(
        self,
        result: CalendarAnalysisResult
    ) -> Tuple[bool, str]:
        """
        Verifica se é seguro operar.
        
        Returns:
            (is_safe, reason)
        """
        if result.is_safe:
            if result.next_high_impact_event:
                mins = result.next_high_impact_event.minutes_until
                if mins <= 60:
                    return True, f"⚠️ {result.next_high_impact_event.title} em {mins} min"
            return True, "OK - Sem eventos bloqueando"
        
        event = result.blocking_event
        if event:
            if event.minutes_until > 0:
                return False, f"🚫 {event.title} ({event.currency}) em {event.minutes_until} min"
            else:
                return False, f"🚫 {event.title} ({event.currency}) ocorreu há {abs(event.minutes_until)} min"
        
        return False, "Eventos pendentes - aguarde"
    
    def to_dict(self, result: CalendarAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        events_list = []
        for e in result.upcoming_events[:5]:
            events_list.append({
                'title': e.title,
                'currency': e.currency,
                'impact': e.impact.name,
                'minutes_until': e.minutes_until,
                'time': e.datetime_utc.strftime('%Y-%m-%d %H:%M UTC'),
                'actual': e.actual,
                'forecast': e.forecast,
                'previous': e.previous,
            })
        
        return {
            'is_safe': result.is_safe,
            'restriction': result.restriction.name,
            'risk_multiplier': round(result.risk_multiplier, 2),
            'cooldown_minutes': result.cooldown_minutes,
            'blocking_event': {
                'title': result.blocking_event.title,
                'currency': result.blocking_event.currency,
                'impact': result.blocking_event.impact.name,
                'minutes_until': result.blocking_event.minutes_until,
            } if result.blocking_event else None,
            'next_high_impact': {
                'title': result.next_high_impact_event.title,
                'minutes_until': result.next_high_impact_event.minutes_until,
            } if result.next_high_impact_event else None,
            'upcoming_events': events_list,
            'affected_currencies': result.affected_currencies,
        }
