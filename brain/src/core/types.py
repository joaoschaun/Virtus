"""
BRAIN - Type Definitions
Definições de tipos para todo o sistema
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union


# ============================================================
# ENUMS
# ============================================================

class OrderType(Enum):
    """Tipo de ordem"""
    BUY = "buy"
    SELL = "sell"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"


class SignalDirection(Enum):
    """Direção do sinal"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class SignalStrength(Enum):
    """Força do sinal"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class MarketRegime(Enum):
    """Regime de mercado"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"


class SentimentLevel(Enum):
    """Nível de sentimento"""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


class BotStatus(Enum):
    """Status do bot"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"


class PositionStatus(Enum):
    """Status da posição"""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    CANCELLED = "cancelled"


class NewsImpact(Enum):
    """Impacto de notícia"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Timeframe(Enum):
    """Timeframes suportados"""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


# ============================================================
# DATA CLASSES - Trading
# ============================================================

@dataclass
class Signal:
    """Sinal de trading"""
    symbol: str
    direction: SignalDirection
    strength: SignalStrength
    strategy: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def risk_reward_ratio(self) -> float:
        """Calcula o ratio risco/retorno"""
        if self.direction == SignalDirection.LONG:
            risk = self.entry_price - self.stop_loss
            reward = self.take_profit - self.entry_price
        else:
            risk = self.stop_loss - self.entry_price
            reward = self.entry_price - self.take_profit
        
        return reward / risk if risk > 0 else 0


@dataclass
class Position:
    """Posição de trading"""
    ticket: int
    symbol: str
    order_type: OrderType
    volume: float
    open_price: float
    open_time: datetime
    stop_loss: float = 0.0
    take_profit: float = 0.0
    current_price: float = 0.0
    profit: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    bot_id: str = ""
    strategy: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_buy(self) -> bool:
        return self.order_type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]
    
    @property
    def is_sell(self) -> bool:
        return self.order_type in [OrderType.SELL, OrderType.SELL_LIMIT, OrderType.SELL_STOP]
    
    @property
    def net_profit(self) -> float:
        return self.profit + self.commission + self.swap


@dataclass
class Trade:
    """Trade executado (histórico)"""
    ticket: int
    symbol: str
    order_type: OrderType
    volume: float
    open_price: float
    close_price: float
    open_time: datetime
    close_time: datetime
    profit: float
    commission: float
    swap: float
    bot_id: str = ""
    strategy: str = ""
    
    @property
    def duration_minutes(self) -> float:
        return (self.close_time - self.open_time).total_seconds() / 60
    
    @property
    def pips(self) -> float:
        """Calcula pips (aproximado)"""
        diff = self.close_price - self.open_price
        if self.order_type in [OrderType.SELL, OrderType.SELL_LIMIT, OrderType.SELL_STOP]:
            diff = -diff
        # Assumir 4 casas decimais para forex, 2 para gold
        if "XAU" in self.symbol or "GOLD" in self.symbol:
            return diff * 100
        return diff * 10000


# ============================================================
# DATA CLASSES - Analysis
# ============================================================

@dataclass
class TechnicalData:
    """Dados de análise técnica"""
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    
    # Preços
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    
    # Indicadores
    rsi: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    ema_fast: float = 0.0
    ema_slow: float = 0.0
    atr: float = 0.0
    adx: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    
    # Regime
    regime: MarketRegime = MarketRegime.RANGING


@dataclass
class SentimentData:
    """Dados de sentimento"""
    symbol: str
    timestamp: datetime
    
    # Scores
    news_sentiment: float = 0.0  # -1 a 1
    social_sentiment: float = 0.0
    institutional_sentiment: float = 0.0
    overall_sentiment: float = 0.0
    
    # Labels
    level: SentimentLevel = SentimentLevel.NEUTRAL
    explanation: str = ""


@dataclass
class NewsItem:
    """Item de notícia"""
    id: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    symbols: List[str] = field(default_factory=list)
    impact: NewsImpact = NewsImpact.LOW
    sentiment: float = 0.0  # -1 a 1
    
    # Tradução
    title_pt: str = ""
    summary_pt: str = ""


@dataclass
class CalendarEvent:
    """Evento do calendário econômico"""
    id: str
    name: str
    country: str
    currency: str
    datetime: datetime
    impact: NewsImpact
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    
    # Tradução
    name_pt: str = ""


@dataclass
class COTData:
    """Dados do Commitment of Traders"""
    symbol: str
    report_date: datetime
    
    # Posições
    commercial_long: int = 0
    commercial_short: int = 0
    non_commercial_long: int = 0
    non_commercial_short: int = 0
    
    # Mudanças
    commercial_net_change: int = 0
    non_commercial_net_change: int = 0
    
    @property
    def commercial_net(self) -> int:
        return self.commercial_long - self.commercial_short
    
    @property
    def non_commercial_net(self) -> int:
        return self.non_commercial_long - self.non_commercial_short


# ============================================================
# DATA CLASSES - Reporting
# ============================================================

@dataclass
class BotStats:
    """Estatísticas de um bot"""
    bot_id: str
    symbol: str
    period_start: datetime
    period_end: datetime
    
    # Performance
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    
    # Métricas
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Por estratégia
    stats_by_strategy: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class DailyBriefing:
    """Briefing diário"""
    date: datetime
    
    # Performance
    total_pnl: float = 0.0
    pnl_by_bot: Dict[str, float] = field(default_factory=dict)
    total_trades: int = 0
    win_rate: float = 0.0
    
    # Mercado
    news: List[NewsItem] = field(default_factory=list)
    sentiment_by_symbol: Dict[str, SentimentData] = field(default_factory=dict)
    calendar_events: List[CalendarEvent] = field(default_factory=list)
    
    # Riscos
    risks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ============================================================
# TYPE ALIASES
# ============================================================

# Preço como float
Price = float

# Volume como float
Volume = float

# Timestamp como datetime
Timestamp = datetime

# Dicionário de configuração
ConfigDict = Dict[str, Any]

# Lista de sinais
SignalList = List[Signal]

# Lista de posições
PositionList = List[Position]

# Mapa símbolo -> dados
SymbolDataMap = Dict[str, Any]
