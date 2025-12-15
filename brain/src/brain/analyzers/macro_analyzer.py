"""
VIRTUS Macro Analyzer
======================

Analisa indicadores macroeconômicos e seu impacto nos mercados.
Integra dados do calendário econômico com análise de tendências.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
from collections import defaultdict

try:
    from ...core import VirtusLogger
except ImportError:
    from core import VirtusLogger


class EventImpact(Enum):
    """Impacto do evento econômico."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class EventType(Enum):
    """Tipo de evento econômico."""
    INTEREST_RATE = "interest_rate"
    EMPLOYMENT = "employment"
    INFLATION = "inflation"
    GDP = "gdp"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    HOUSING = "housing"
    TRADE = "trade"
    CENTRAL_BANK = "central_bank"
    SPEECH = "speech"
    OTHER = "other"


class Currency(Enum):
    """Moedas principais."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    AUD = "AUD"
    CAD = "CAD"
    NZD = "NZD"


@dataclass
class EconomicEvent:
    """Evento do calendário econômico."""
    id: str
    name: str
    currency: Currency
    timestamp: datetime
    impact: EventImpact
    event_type: EventType
    
    # Valores
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    
    # Análise
    surprise: Optional[float] = None  # (actual - forecast) / forecast
    direction: str = "neutral"         # better, worse, neutral
    
    # Metadata
    unit: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'currency': self.currency.value,
            'timestamp': self.timestamp.isoformat(),
            'impact': self.impact.name,
            'type': self.event_type.value,
            'actual': self.actual,
            'forecast': self.forecast,
            'previous': self.previous,
            'surprise': round(self.surprise, 3) if self.surprise else None,
            'direction': self.direction,
        }
    
    @property
    def is_released(self) -> bool:
        """Se o resultado já foi divulgado."""
        return self.actual is not None


@dataclass
class MacroSnapshot:
    """Snapshot macroeconômico de uma economia."""
    currency: Currency
    timestamp: datetime
    
    # Indicadores principais
    interest_rate: Optional[float] = None
    inflation_cpi: Optional[float] = None
    gdp_growth: Optional[float] = None
    unemployment: Optional[float] = None
    
    # Tendências
    rate_trend: str = "stable"        # hiking, cutting, stable
    inflation_trend: str = "stable"   # rising, falling, stable
    growth_trend: str = "stable"      # expanding, contracting, stable
    
    # Score de saúde econômica (-100 a +100)
    health_score: float = 0.0
    
    # Próximos eventos importantes
    upcoming_high_impact: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'currency': self.currency.value,
            'timestamp': self.timestamp.isoformat(),
            'interest_rate': self.interest_rate,
            'inflation': self.inflation_cpi,
            'gdp_growth': self.gdp_growth,
            'unemployment': self.unemployment,
            'rate_trend': self.rate_trend,
            'inflation_trend': self.inflation_trend,
            'growth_trend': self.growth_trend,
            'health_score': round(self.health_score, 2),
            'upcoming_events': self.upcoming_high_impact[:3],
        }


@dataclass
class MacroConfig:
    """Configuração do analisador macro."""
    # Pesos para health score
    weights: Dict[str, float] = field(default_factory=lambda: {
        'gdp': 0.25,
        'employment': 0.25,
        'inflation': 0.20,
        'rates': 0.15,
        'trade': 0.15,
    })
    
    # Cache
    cache_hours: int = 4


class MacroAnalyzer:
    """
    Analisador macroeconômico.
    
    Responsabilidades:
    - Processar calendário econômico
    - Calcular impacto de eventos
    - Gerar snapshots por economia
    - Identificar tendências macro
    """
    
    def __init__(self, config: Optional[MacroConfig] = None):
        self.config = config or MacroConfig()
        self.logger = VirtusLogger.get_logger("macro_analyzer")
        
        # Eventos por moeda
        self._events: Dict[Currency, List[EconomicEvent]] = {
            c: [] for c in Currency
        }
        
        # Histórico de indicadores
        self._indicators: Dict[Currency, Dict[str, List[Tuple[datetime, float]]]] = {
            c: defaultdict(list) for c in Currency
        }
        
        # Cache de snapshots
        self._snapshots: Dict[Currency, MacroSnapshot] = {}
        
        # Mapeamento de eventos para símbolos
        self._currency_to_symbols = {
            Currency.USD: ['XAUUSD', 'EURUSD', 'GBPUSD'],
            Currency.EUR: ['EURUSD'],
            Currency.GBP: ['GBPUSD'],
        }
        
        # Classificação de eventos
        self._event_classifiers = self._build_event_classifiers()
    
    def _build_event_classifiers(self) -> Dict[str, EventType]:
        """Constrói classificadores de tipo de evento."""
        return {
            'interest rate': EventType.INTEREST_RATE,
            'fed funds': EventType.INTEREST_RATE,
            'ecb rate': EventType.INTEREST_RATE,
            'boe rate': EventType.INTEREST_RATE,
            'nonfarm': EventType.EMPLOYMENT,
            'payroll': EventType.EMPLOYMENT,
            'unemployment': EventType.EMPLOYMENT,
            'jobless': EventType.EMPLOYMENT,
            'employment': EventType.EMPLOYMENT,
            'cpi': EventType.INFLATION,
            'ppi': EventType.INFLATION,
            'inflation': EventType.INFLATION,
            'gdp': EventType.GDP,
            'retail sales': EventType.RETAIL,
            'pmi': EventType.MANUFACTURING,
            'ism': EventType.MANUFACTURING,
            'manufacturing': EventType.MANUFACTURING,
            'housing': EventType.HOUSING,
            'trade balance': EventType.TRADE,
            'fomc': EventType.CENTRAL_BANK,
            'ecb': EventType.CENTRAL_BANK,
            'boe': EventType.CENTRAL_BANK,
            'fed': EventType.CENTRAL_BANK,
            'speech': EventType.SPEECH,
            'speaks': EventType.SPEECH,
            'testimony': EventType.SPEECH,
        }
    
    # ========================================================================
    # PROCESSAMENTO DE EVENTOS
    # ========================================================================
    
    async def process_calendar_events(
        self,
        events_data: List[Dict[str, Any]]
    ) -> List[EconomicEvent]:
        """
        Processa eventos do calendário econômico.
        
        Args:
            events_data: Lista de eventos brutos
            
        Returns:
            Lista de EconomicEvent processados
        """
        processed = []
        
        for raw in events_data:
            try:
                event = self._process_event(raw)
                if event:
                    # Armazena
                    self._events[event.currency].append(event)
                    processed.append(event)
                    
                    # Atualiza histórico se tem actual
                    if event.is_released:
                        self._update_indicator_history(event)
                        
            except Exception as e:
                self.logger.warning(f"Erro processando evento: {e}")
        
        self.logger.info(f"Processados {len(processed)} eventos econômicos")
        return processed
    
    def _process_event(self, raw: Dict[str, Any]) -> Optional[EconomicEvent]:
        """Processa um evento individual."""
        name = raw.get('event', '') or raw.get('name', '')
        if not name:
            return None
        
        # Parse de moeda
        currency_str = raw.get('currency', '') or raw.get('country', '')
        try:
            currency = Currency(currency_str.upper())
        except ValueError:
            currency = Currency.USD  # Default
        
        # Parse de data
        timestamp = self._parse_timestamp(raw)
        
        # Determina impacto
        impact_str = str(raw.get('impact', '')).lower()
        if 'high' in impact_str or impact_str == '3':
            impact = EventImpact.HIGH
        elif 'medium' in impact_str or impact_str == '2':
            impact = EventImpact.MEDIUM
        else:
            impact = EventImpact.LOW
        
        # Classifica tipo
        event_type = self._classify_event(name)
        
        # Parse de valores
        actual = self._parse_value(raw.get('actual'))
        forecast = self._parse_value(raw.get('forecast'))
        previous = self._parse_value(raw.get('previous'))
        
        # Calcula surprise
        surprise = None
        direction = "neutral"
        if actual is not None and forecast is not None and forecast != 0:
            surprise = (actual - forecast) / abs(forecast)
            if surprise > 0.01:
                direction = "better"
            elif surprise < -0.01:
                direction = "worse"
        
        return EconomicEvent(
            id=raw.get('id', str(hash(f"{name}{timestamp}"))),
            name=name,
            currency=currency,
            timestamp=timestamp,
            impact=impact,
            event_type=event_type,
            actual=actual,
            forecast=forecast,
            previous=previous,
            surprise=surprise,
            direction=direction,
            unit=raw.get('unit', ''),
            description=raw.get('description', ''),
        )
    
    def _classify_event(self, name: str) -> EventType:
        """Classifica tipo de evento pelo nome."""
        name_lower = name.lower()
        
        for keyword, event_type in self._event_classifiers.items():
            if keyword in name_lower:
                return event_type
        
        return EventType.OTHER
    
    def _parse_timestamp(self, raw: Dict) -> datetime:
        """Parse de timestamp."""
        ts = raw.get('timestamp') or raw.get('date') or raw.get('datetime')
        
        if isinstance(ts, datetime):
            return ts
        
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                pass
        
        return datetime.now()
    
    def _parse_value(self, value: Any) -> Optional[float]:
        """Parse de valor numérico."""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove caracteres não numéricos exceto . e -
            clean = ''.join(c for c in value if c.isdigit() or c in '.-')
            try:
                return float(clean) if clean else None
            except ValueError:
                return None
        
        return None
    
    def _update_indicator_history(self, event: EconomicEvent) -> None:
        """Atualiza histórico de indicadores."""
        if event.actual is None:
            return
        
        # Mapeia tipo de evento para indicador
        indicator_map = {
            EventType.INTEREST_RATE: 'rate',
            EventType.INFLATION: 'inflation',
            EventType.GDP: 'gdp',
            EventType.EMPLOYMENT: 'employment',
        }
        
        indicator = indicator_map.get(event.event_type)
        if indicator:
            self._indicators[event.currency][indicator].append(
                (event.timestamp, event.actual)
            )
    
    # ========================================================================
    # ANÁLISE MACRO
    # ========================================================================
    
    async def get_macro_snapshot(
        self,
        currency: Currency
    ) -> MacroSnapshot:
        """
        Gera snapshot macroeconômico para uma moeda.
        
        Args:
            currency: Moeda (Currency.USD, EUR, GBP)
            
        Returns:
            MacroSnapshot com indicadores e tendências
        """
        indicators = self._indicators.get(currency, {})
        
        # Obtém últimos valores
        interest_rate = self._get_latest_value(indicators.get('rate', []))
        inflation = self._get_latest_value(indicators.get('inflation', []))
        gdp = self._get_latest_value(indicators.get('gdp', []))
        unemployment = self._get_latest_value(indicators.get('employment', []))
        
        # Determina tendências
        rate_trend = self._determine_trend(indicators.get('rate', []))
        inflation_trend = self._determine_trend(indicators.get('inflation', []))
        growth_trend = self._determine_trend(indicators.get('gdp', []))
        
        # Calcula health score
        health_score = self._calculate_health_score(
            currency, interest_rate, inflation, gdp, unemployment
        )
        
        # Próximos eventos importantes
        upcoming = self._get_upcoming_events(currency, hours=72)
        upcoming_names = [
            f"{e.name} ({e.timestamp.strftime('%d/%m %H:%M')})"
            for e in upcoming if e.impact == EventImpact.HIGH
        ][:3]
        
        snapshot = MacroSnapshot(
            currency=currency,
            timestamp=datetime.now(),
            interest_rate=interest_rate,
            inflation_cpi=inflation,
            gdp_growth=gdp,
            unemployment=unemployment,
            rate_trend=rate_trend,
            inflation_trend=inflation_trend,
            growth_trend=growth_trend,
            health_score=health_score,
            upcoming_high_impact=upcoming_names,
        )
        
        self._snapshots[currency] = snapshot
        return snapshot
    
    def _get_latest_value(
        self, history: List[Tuple[datetime, float]]
    ) -> Optional[float]:
        """Obtém valor mais recente."""
        if not history:
            return None
        return sorted(history, key=lambda x: x[0])[-1][1]
    
    def _determine_trend(
        self,
        history: List[Tuple[datetime, float]],
        periods: int = 3
    ) -> str:
        """Determina tendência de um indicador."""
        if len(history) < 2:
            return "stable"
        
        # Ordena por data
        sorted_history = sorted(history, key=lambda x: x[0])
        recent = sorted_history[-periods:]
        
        if len(recent) < 2:
            return "stable"
        
        # Calcula mudança
        changes = []
        for i in range(1, len(recent)):
            if recent[i-1][1] != 0:
                change = (recent[i][1] - recent[i-1][1]) / abs(recent[i-1][1])
                changes.append(change)
        
        if not changes:
            return "stable"
        
        avg_change = sum(changes) / len(changes)
        
        if avg_change > 0.02:
            return "rising" if "inflation" not in str(history) else "hiking"
        elif avg_change < -0.02:
            return "falling" if "inflation" not in str(history) else "cutting"
        return "stable"
    
    def _calculate_health_score(
        self,
        currency: Currency,
        rate: Optional[float],
        inflation: Optional[float],
        gdp: Optional[float],
        unemployment: Optional[float]
    ) -> float:
        """
        Calcula score de saúde econômica.
        
        Considera:
        - GDP positivo = bom
        - Inflação controlada (2-3%) = bom
        - Desemprego baixo = bom
        - Taxa de juros adequada = bom
        """
        score = 0.0
        weights = self.config.weights
        
        # GDP (positivo é bom)
        if gdp is not None:
            if gdp > 3:
                score += 100 * weights['gdp']
            elif gdp > 2:
                score += 70 * weights['gdp']
            elif gdp > 0:
                score += 40 * weights['gdp']
            elif gdp > -1:
                score += 0 * weights['gdp']
            else:
                score -= 50 * weights['gdp']
        
        # Inflação (2-3% é ideal)
        if inflation is not None:
            if 1.5 <= inflation <= 3.0:
                score += 100 * weights['inflation']
            elif 3.0 < inflation <= 4.0 or 1.0 <= inflation < 1.5:
                score += 50 * weights['inflation']
            elif inflation > 5:
                score -= 50 * weights['inflation']
            elif inflation < 0:
                score -= 30 * weights['inflation']
        
        # Emprego/Desemprego
        if unemployment is not None:
            if unemployment < 4:
                score += 100 * weights['employment']
            elif unemployment < 5:
                score += 70 * weights['employment']
            elif unemployment < 6:
                score += 40 * weights['employment']
            elif unemployment < 8:
                score += 0 * weights['employment']
            else:
                score -= 50 * weights['employment']
        
        return max(-100, min(100, score))
    
    def _get_upcoming_events(
        self,
        currency: Currency,
        hours: int = 24
    ) -> List[EconomicEvent]:
        """Obtém próximos eventos."""
        now = datetime.now()
        future = now + timedelta(hours=hours)
        
        upcoming = [
            e for e in self._events.get(currency, [])
            if now <= e.timestamp <= future
        ]
        
        return sorted(upcoming, key=lambda e: e.timestamp)
    
    # ========================================================================
    # ANÁLISE DE IMPACTO
    # ========================================================================
    
    async def analyze_event_impact(
        self,
        event: EconomicEvent
    ) -> Dict[str, Any]:
        """
        Analisa impacto potencial de um evento em símbolos.
        
        Args:
            event: Evento econômico
            
        Returns:
            Análise de impacto por símbolo
        """
        symbols = self._currency_to_symbols.get(event.currency, [])
        
        analysis = {
            'event': event.to_dict(),
            'impact_analysis': {},
            'trading_implications': [],
        }
        
        for symbol in symbols:
            impact = self._calculate_symbol_impact(event, symbol)
            analysis['impact_analysis'][symbol] = impact
        
        # Implicações para trading
        if event.impact == EventImpact.HIGH:
            if event.is_released:
                if event.direction == "better":
                    analysis['trading_implications'].append(
                        f"Resultado acima das expectativas favorece {event.currency.value}"
                    )
                elif event.direction == "worse":
                    analysis['trading_implications'].append(
                        f"Resultado abaixo das expectativas pressiona {event.currency.value}"
                    )
            else:
                analysis['trading_implications'].append(
                    f"Evento de alto impacto pendente - considerar reduzir exposição"
                )
        
        return analysis
    
    def _calculate_symbol_impact(
        self,
        event: EconomicEvent,
        symbol: str
    ) -> Dict[str, Any]:
        """Calcula impacto em um símbolo específico."""
        impact = {
            'expected_volatility': 'normal',
            'direction_bias': 'neutral',
            'confidence': 0.5,
        }
        
        # Base no impacto do evento
        if event.impact == EventImpact.HIGH:
            impact['expected_volatility'] = 'high'
        elif event.impact == EventImpact.MEDIUM:
            impact['expected_volatility'] = 'elevated'
        
        # Direção baseada no resultado
        if event.is_released and event.surprise is not None:
            # Para USD events
            if event.currency == Currency.USD:
                if 'USD' in symbol:
                    # USD é a moeda cotada (XAUUSD, EURUSD)
                    if event.direction == "better":
                        impact['direction_bias'] = 'bearish'  # USD forte
                    elif event.direction == "worse":
                        impact['direction_bias'] = 'bullish'  # USD fraco
            
            # Para EUR events
            elif event.currency == Currency.EUR and symbol == 'EURUSD':
                if event.direction == "better":
                    impact['direction_bias'] = 'bullish'
                elif event.direction == "worse":
                    impact['direction_bias'] = 'bearish'
            
            # Para GBP events
            elif event.currency == Currency.GBP and symbol == 'GBPUSD':
                if event.direction == "better":
                    impact['direction_bias'] = 'bullish'
                elif event.direction == "worse":
                    impact['direction_bias'] = 'bearish'
            
            # Confidence baseada no tamanho da surpresa
            if event.surprise:
                impact['confidence'] = min(0.9, 0.5 + abs(event.surprise))
        
        return impact
    
    # ========================================================================
    # COMPARAÇÃO ENTRE ECONOMIAS
    # ========================================================================
    
    async def compare_economies(
        self,
        currencies: Optional[List[Currency]] = None
    ) -> Dict[str, Any]:
        """
        Compara indicadores entre economias.
        
        Args:
            currencies: Lista de moedas para comparar
            
        Returns:
            Comparação detalhada
        """
        currencies = currencies or [Currency.USD, Currency.EUR, Currency.GBP]
        
        snapshots = {}
        for currency in currencies:
            snapshots[currency] = await self.get_macro_snapshot(currency)
        
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'snapshots': {c.value: s.to_dict() for c, s in snapshots.items()},
            'rankings': {},
            'analysis': [],
        }
        
        # Rankings
        if all(s.health_score is not None for s in snapshots.values()):
            ranked = sorted(
                snapshots.items(),
                key=lambda x: x[1].health_score,
                reverse=True
            )
            comparison['rankings']['health_score'] = [
                {'currency': c.value, 'score': s.health_score}
                for c, s in ranked
            ]
        
        # Análise qualitativa
        for currency, snapshot in snapshots.items():
            if snapshot.rate_trend == "hiking":
                comparison['analysis'].append(
                    f"{currency.value}: Banco central em ciclo de alta de juros"
                )
            elif snapshot.rate_trend == "cutting":
                comparison['analysis'].append(
                    f"{currency.value}: Banco central em ciclo de corte de juros"
                )
            
            if snapshot.inflation_trend == "rising" and (
                snapshot.inflation_cpi and snapshot.inflation_cpi > 4
            ):
                comparison['analysis'].append(
                    f"{currency.value}: Inflação elevada e em tendência de alta"
                )
        
        return comparison
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def get_todays_events(
        self,
        currencies: Optional[List[Currency]] = None
    ) -> List[EconomicEvent]:
        """Obtém eventos de hoje."""
        currencies = currencies or list(Currency)
        today = datetime.now().date()
        
        events = []
        for currency in currencies:
            for event in self._events.get(currency, []):
                if event.timestamp.date() == today:
                    events.append(event)
        
        return sorted(events, key=lambda e: e.timestamp)
    
    def get_high_impact_events(
        self,
        hours_ahead: int = 24
    ) -> List[EconomicEvent]:
        """Obtém eventos de alto impacto próximos."""
        now = datetime.now()
        future = now + timedelta(hours=hours_ahead)
        
        events = []
        for currency in Currency:
            for event in self._events.get(currency, []):
                if event.impact == EventImpact.HIGH:
                    if now <= event.timestamp <= future:
                        events.append(event)
        
        return sorted(events, key=lambda e: e.timestamp)
    
    def clear_old_events(self, days: int = 7) -> int:
        """Limpa eventos antigos."""
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        
        for currency in Currency:
            old_count = len(self._events[currency])
            self._events[currency] = [
                e for e in self._events[currency]
                if e.timestamp >= cutoff
            ]
            count += old_count - len(self._events[currency])
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do analisador."""
        total = sum(len(e) for e in self._events.values())
        
        return {
            'total_events': total,
            'by_currency': {
                c.value: len(self._events[c]) for c in Currency
            },
            'by_impact': {
                impact.name: sum(
                    1 for events in self._events.values()
                    for e in events if e.impact == impact
                )
                for impact in EventImpact
            },
            'snapshots_cached': len(self._snapshots),
        }
