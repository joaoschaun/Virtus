"""
VIRTUS Event Strategy
======================

Estratégia para trading de eventos econômicos com:
- Pre-event positioning
- Post-event momentum
- News fade trades
- Straddle/Strangle logic
- Impact-based filtering
- Volatility expectation
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto

try:
    from ...core import VirtusLogger
    from ...core.types import Signal, SignalDirection, SignalStrength
except ImportError:
    from core import VirtusLogger
    from core.types import Signal, SignalDirection, SignalStrength


class EventType(Enum):
    """Tipos de eventos."""
    NFP = "nfp"
    FOMC = "fomc"
    CPI = "cpi"
    GDP = "gdp"
    RATE_DECISION = "rate_decision"
    PMI = "pmi"
    EMPLOYMENT = "employment"
    RETAIL_SALES = "retail_sales"
    OTHER_HIGH_IMPACT = "other_high_impact"


class EventSetup(Enum):
    """Setups de evento."""
    PRE_EVENT_BREAKOUT = "pre_event_breakout"
    POST_EVENT_MOMENTUM = "post_event_momentum"
    NEWS_FADE = "news_fade"
    RANGE_EXPANSION = "range_expansion"
    VOLATILITY_SQUEEZE_RELEASE = "volatility_squeeze_release"


class EventImpact(Enum):
    """Impacto do evento."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    EXTREME = 4  # FOMC, NFP


@dataclass
class EventInfo:
    """Informações do evento."""
    name: str
    event_type: EventType
    impact: EventImpact
    time: datetime
    currency: str
    forecast: Optional[float] = None
    previous: Optional[float] = None
    actual: Optional[float] = None
    
    @property
    def minutes_until(self) -> int:
        """Minutos até o evento."""
        return int((self.time - datetime.now()).total_seconds() / 60)
    
    @property
    def minutes_since(self) -> int:
        """Minutos desde o evento."""
        return int((datetime.now() - self.time).total_seconds() / 60)
    
    @property
    def is_past(self) -> bool:
        """Se o evento já ocorreu."""
        return datetime.now() > self.time
    
    @property
    def surprise_factor(self) -> Optional[float]:
        """Fator surpresa (desvio do forecast)."""
        if self.actual is None or self.forecast is None:
            return None
        if self.forecast == 0:
            return 0
        return (self.actual - self.forecast) / abs(self.forecast)


@dataclass
class EventSignal:
    """Sinal de evento."""
    setup: EventSetup
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    event: EventInfo
    expected_move_pips: float
    time_limit_minutes: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventConfig:
    """Configuração da estratégia de eventos."""
    # Timing
    pre_event_window_minutes: int = 30  # Janela antes do evento
    post_event_window_minutes: int = 60  # Janela após evento
    fade_delay_minutes: int = 5  # Delay para fade trade
    
    # Risk
    max_risk_percent: float = 0.5  # Risk menor em eventos
    min_risk_reward: float = 1.5
    
    # Filters
    min_impact: EventImpact = EventImpact.HIGH
    trade_currencies: List[str] = field(default_factory=lambda: ["USD", "EUR", "GBP", "JPY"])
    
    # Volatility
    min_atr_expansion: float = 1.5  # ATR deve expandir 1.5x
    expected_move_by_event: Dict[str, float] = field(default_factory=lambda: {
        'nfp': 50,  # pips
        'fomc': 80,
        'cpi': 40,
        'rate_decision': 60,
        'gdp': 35,
        'pmi': 25,
        'employment': 30,
        'retail_sales': 25,
    })


class EventStrategy:
    """
    Estratégia de Trading em Eventos Econômicos.
    
    Setups:
    1. Pre-Event Breakout - Trade breakout antes do evento
    2. Post-Event Momentum - Trade na direção do movimento inicial
    3. News Fade - Fade do movimento exagerado
    4. Range Expansion - Trade expansão de range pós-evento
    5. Volatility Squeeze Release - Entry após squeeze de volatilidade
    
    Lógica:
    - Identifica eventos de alto impacto
    - Analisa posicionamento pré-evento
    - Executa estratégia apropriada baseada no timing
    - Gerencia risco extra em volatilidade alta
    """
    
    def __init__(self, config: Optional[EventConfig] = None):
        self.config = config or EventConfig()
        self.logger = VirtusLogger.get_logger("event_strategy")
        
        # Cache de eventos processados
        self._processed_events: Dict[str, datetime] = {}
    
    async def evaluate(
        self,
        symbol: str,
        current_price: float,
        atr: float,
        # Event data
        upcoming_events: List[EventInfo] = None,
        recent_events: List[EventInfo] = None,
        # Price action
        range_high: float = 0,
        range_low: float = 0,
        volatility_percentile: float = 50,
        in_squeeze: bool = False,
        # Technical
        trend: str = "neutral",
        momentum: float = 0,
    ) -> Optional[EventSignal]:
        """
        Avalia setups de eventos.
        """
        upcoming_events = upcoming_events or []
        recent_events = recent_events or []
        
        # Filtra eventos relevantes
        relevant_upcoming = [
            e for e in upcoming_events
            if e.impact.value >= self.config.min_impact.value
            and e.currency in self.config.trade_currencies
            and 0 < e.minutes_until <= self.config.pre_event_window_minutes
        ]
        
        relevant_recent = [
            e for e in recent_events
            if e.impact.value >= self.config.min_impact.value
            and e.currency in self.config.trade_currencies
            and 0 < e.minutes_since <= self.config.post_event_window_minutes
        ]
        
        signals: List[EventSignal] = []
        
        # === PRE-EVENT SETUPS ===
        for event in relevant_upcoming:
            # 1. Pre-Event Breakout (squeeze release)
            if in_squeeze and event.minutes_until <= 15:
                signal = self._evaluate_pre_event_breakout(
                    symbol, current_price, atr, event,
                    range_high, range_low, volatility_percentile
                )
                if signal:
                    signals.append(signal)
        
        # === POST-EVENT SETUPS ===
        for event in relevant_recent:
            event_key = f"{event.name}_{event.time.isoformat()}"
            
            # Evita processar mesmo evento múltiplas vezes
            if event_key in self._processed_events:
                continue
            
            # 2. Post-Event Momentum
            if event.minutes_since <= 10:
                signal = self._evaluate_post_event_momentum(
                    symbol, current_price, atr, event,
                    range_high, range_low, momentum
                )
                if signal:
                    signals.append(signal)
                    self._processed_events[event_key] = datetime.now()
            
            # 3. News Fade
            elif self.config.fade_delay_minutes <= event.minutes_since <= 30:
                signal = self._evaluate_news_fade(
                    symbol, current_price, atr, event,
                    range_high, range_low, volatility_percentile
                )
                if signal:
                    signals.append(signal)
            
            # 4. Range Expansion
            if event.minutes_since <= 45:
                signal = self._evaluate_range_expansion(
                    symbol, current_price, atr, event,
                    range_high, range_low, trend
                )
                if signal:
                    signals.append(signal)
        
        # === VOLATILITY SQUEEZE RELEASE ===
        if in_squeeze and not relevant_upcoming:
            # Squeeze sem evento = potencial release técnico
            signal = self._evaluate_squeeze_release(
                symbol, current_price, atr,
                range_high, range_low, volatility_percentile
            )
            if signal:
                signals.append(signal)
        
        # Seleciona melhor sinal
        if not signals:
            return None
        
        best_signal = max(signals, key=lambda s: s.confidence)
        
        self.logger.info(
            f"📰 Event signal: {best_signal.setup.value} "
            f"Event: {best_signal.event.name if best_signal.event else 'squeeze'} "
            f"{best_signal.direction.value} @ {best_signal.entry_price:.5f}"
        )
        
        return best_signal
    
    def _evaluate_pre_event_breakout(
        self,
        symbol: str,
        price: float,
        atr: float,
        event: EventInfo,
        range_high: float,
        range_low: float,
        volatility_percentile: float
    ) -> Optional[EventSignal]:
        """
        Pre-Event Breakout Setup.
        
        Trade breakout do range antes do evento.
        Aproveita o squeeze de volatilidade que precede eventos.
        """
        if volatility_percentile > 30:  # Precisa estar em squeeze
            return None
        
        range_size = range_high - range_low
        mid_range = (range_high + range_low) / 2
        
        # Determina direção pelo posicionamento atual
        if price > mid_range + range_size * 0.3:
            # Próximo do high = viés bullish
            direction = SignalDirection.BUY
            entry = range_high + atr * 0.1
            sl = range_low - atr * 0.2
        elif price < mid_range - range_size * 0.3:
            # Próximo do low = viés bearish
            direction = SignalDirection.SELL
            entry = range_low - atr * 0.1
            sl = range_high + atr * 0.2
        else:
            return None  # Muito no meio
        
        expected_move = self._get_expected_move(event.event_type.value, symbol)
        tp_distance = expected_move * 0.6  # 60% do move esperado
        
        if direction == SignalDirection.BUY:
            tp = entry + self._pips_to_price(symbol, tp_distance)
        else:
            tp = entry - self._pips_to_price(symbol, tp_distance)
        
        sl_distance = abs(entry - sl)
        tp_dist = abs(tp - entry)
        rr = tp_dist / sl_distance if sl_distance > 0 else 0
        
        if rr < self.config.min_risk_reward:
            return None
        
        return EventSignal(
            setup=EventSetup.PRE_EVENT_BREAKOUT,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.55,  # Menor confiança pré-evento
            event=event,
            expected_move_pips=expected_move,
            time_limit_minutes=event.minutes_until + 15,
            metadata={
                'range_high': range_high,
                'range_low': range_low,
            }
        )
    
    def _evaluate_post_event_momentum(
        self,
        symbol: str,
        price: float,
        atr: float,
        event: EventInfo,
        range_high: float,
        range_low: float,
        momentum: float
    ) -> Optional[EventSignal]:
        """
        Post-Event Momentum Setup.
        
        Trade na direção do movimento inicial após o evento.
        """
        if abs(momentum) < 0.3:
            return None  # Momentum muito fraco
        
        # Analisa surpresa
        surprise = event.surprise_factor
        
        direction = SignalDirection.BUY if momentum > 0 else SignalDirection.SELL
        
        # Ajusta confiança pela surpresa
        confidence = 0.65
        if surprise is not None:
            if abs(surprise) > 0.5:  # Grande surpresa
                confidence += 0.15
            elif abs(surprise) > 0.2:
                confidence += 0.08
        
        expected_move = self._get_expected_move(event.event_type.value, symbol)
        
        if direction == SignalDirection.BUY:
            sl = price - atr * 1.5
            tp = price + self._pips_to_price(symbol, expected_move * 0.5)
        else:
            sl = price + atr * 1.5
            tp = price - self._pips_to_price(symbol, expected_move * 0.5)
        
        sl_distance = abs(price - sl)
        tp_dist = abs(tp - price)
        rr = tp_dist / sl_distance if sl_distance > 0 else 0
        
        if rr < self.config.min_risk_reward:
            return None
        
        return EventSignal(
            setup=EventSetup.POST_EVENT_MOMENTUM,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            confidence=min(confidence, 0.85),
            event=event,
            expected_move_pips=expected_move,
            time_limit_minutes=30,
            metadata={
                'momentum': momentum,
                'surprise_factor': surprise,
            }
        )
    
    def _evaluate_news_fade(
        self,
        symbol: str,
        price: float,
        atr: float,
        event: EventInfo,
        range_high: float,
        range_low: float,
        volatility_percentile: float
    ) -> Optional[EventSignal]:
        """
        News Fade Setup.
        
        Fade do movimento exagerado após notícia.
        """
        if volatility_percentile < 80:
            return None  # Volatilidade não está alta o suficiente para fade
        
        expected_move = self._get_expected_move(event.event_type.value, symbol)
        expected_price = self._pips_to_price(symbol, expected_move)
        
        # Calcula extensão do movimento
        range_size = range_high - range_low
        
        # Se movimento foi > 120% do esperado, considera fade
        move_ratio = range_size / expected_price if expected_price > 0 else 0
        
        if move_ratio < 1.2:
            return None  # Movimento não foi exagerado
        
        # Determina direção do fade (oposto ao movimento)
        mid = (range_high + range_low) / 2
        
        if price > mid:
            # Preço acima do meio = fade para baixo
            direction = SignalDirection.SELL
            sl = range_high + atr * 0.3
            tp = mid
        else:
            direction = SignalDirection.BUY
            sl = range_low - atr * 0.3
            tp = mid
        
        sl_distance = abs(price - sl)
        tp_dist = abs(tp - price)
        rr = tp_dist / sl_distance if sl_distance > 0 else 0
        
        if rr < self.config.min_risk_reward:
            return None
        
        return EventSignal(
            setup=EventSetup.NEWS_FADE,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.60,
            event=event,
            expected_move_pips=expected_move,
            time_limit_minutes=45,
            metadata={
                'move_ratio': move_ratio,
                'range_high': range_high,
                'range_low': range_low,
            }
        )
    
    def _evaluate_range_expansion(
        self,
        symbol: str,
        price: float,
        atr: float,
        event: EventInfo,
        range_high: float,
        range_low: float,
        trend: str
    ) -> Optional[EventSignal]:
        """
        Range Expansion Setup.
        
        Trade continuação após expansão de range pós-evento.
        """
        if trend == "neutral":
            return None
        
        direction = SignalDirection.BUY if trend == "bullish" else SignalDirection.SELL
        
        # Entry em pullback após expansão
        range_size = range_high - range_low
        pullback_zone = range_size * 0.382
        
        if direction == SignalDirection.BUY:
            entry_zone = range_high - pullback_zone
            if price > entry_zone:
                return None  # Não está em pullback
            
            sl = range_low - atr * 0.2
            tp = range_high + range_size * 0.618
        else:
            entry_zone = range_low + pullback_zone
            if price < entry_zone:
                return None
            
            sl = range_high + atr * 0.2
            tp = range_low - range_size * 0.618
        
        sl_distance = abs(price - sl)
        tp_dist = abs(tp - price)
        rr = tp_dist / sl_distance if sl_distance > 0 else 0
        
        if rr < self.config.min_risk_reward:
            return None
        
        return EventSignal(
            setup=EventSetup.RANGE_EXPANSION,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.62,
            event=event,
            expected_move_pips=self._get_expected_move(event.event_type.value, symbol),
            time_limit_minutes=60,
            metadata={
                'trend': trend,
                'range_size': range_size,
            }
        )
    
    def _evaluate_squeeze_release(
        self,
        symbol: str,
        price: float,
        atr: float,
        range_high: float,
        range_low: float,
        volatility_percentile: float
    ) -> Optional[EventSignal]:
        """
        Volatility Squeeze Release Setup.
        
        Trade breakout de squeeze de volatilidade (sem evento específico).
        """
        if volatility_percentile > 20:
            return None  # Não está em squeeze suficiente
        
        range_size = range_high - range_low
        
        # Breakout setup
        breakout_buffer = atr * 0.2
        
        if price >= range_high - breakout_buffer:
            direction = SignalDirection.BUY
            entry = range_high + breakout_buffer
            sl = range_low - atr * 0.3
        elif price <= range_low + breakout_buffer:
            direction = SignalDirection.SELL
            entry = range_low - breakout_buffer
            sl = range_high + atr * 0.3
        else:
            return None
        
        # TP baseado em expansão típica de squeeze
        expected_expansion = range_size * 1.618
        
        if direction == SignalDirection.BUY:
            tp = entry + expected_expansion
        else:
            tp = entry - expected_expansion
        
        sl_distance = abs(entry - sl)
        tp_dist = abs(tp - entry)
        rr = tp_dist / sl_distance if sl_distance > 0 else 0
        
        if rr < self.config.min_risk_reward:
            return None
        
        # Cria evento "fake" para o sinal
        fake_event = EventInfo(
            name="Volatility Squeeze",
            event_type=EventType.OTHER_HIGH_IMPACT,
            impact=EventImpact.MEDIUM,
            time=datetime.now(),
            currency="ALL"
        )
        
        return EventSignal(
            setup=EventSetup.VOLATILITY_SQUEEZE_RELEASE,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.58,
            event=fake_event,
            expected_move_pips=expected_expansion / self._pips_to_price(symbol, 1),
            time_limit_minutes=120,
            metadata={
                'volatility_percentile': volatility_percentile,
                'range_size': range_size,
            }
        )
    
    def _get_expected_move(self, event_type: str, symbol: str) -> float:
        """Retorna movimento esperado em pips para o evento."""
        base_move = self.config.expected_move_by_event.get(event_type, 30)
        
        # Ajusta por símbolo
        if 'XAU' in symbol:
            base_move *= 3  # Ouro move mais
        elif 'JPY' in symbol:
            base_move *= 0.8
        
        return base_move
    
    def _pips_to_price(self, symbol: str, pips: float) -> float:
        """Converte pips para valor de preço."""
        if 'JPY' in symbol:
            return pips / 100
        elif 'XAU' in symbol:
            return pips / 10
        else:
            return pips / 10000
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna informações da estratégia."""
        return {
            'name': 'VIRTUS Event Strategy',
            'type': 'event',
            'setups': [s.value for s in EventSetup],
            'config': {
                'pre_event_window': f"{self.config.pre_event_window_minutes} min",
                'post_event_window': f"{self.config.post_event_window_minutes} min",
                'min_impact': self.config.min_impact.name,
                'currencies': self.config.trade_currencies,
            },
        }
