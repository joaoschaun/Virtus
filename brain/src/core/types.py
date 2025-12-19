"""
VIRTUS Core - Type Definitions
==============================

Tipos e estruturas de dados usados em todo o sistema.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Union


# ============================================================================
# ENUMS
# ============================================================================

class OrderType(Enum):
    """Tipo de ordem"""
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"


class PositionStatus(Enum):
    """Status de uma posição"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class SignalType(Enum):
    """Tipo de sinal de trading"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"


# Alias para compatibilidade
SignalDirection = SignalType


class SignalStrength(Enum):
    """Força do sinal"""
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


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


class MarketRegime(Enum):
    """Regime de mercado"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    UNKNOWN = "UNKNOWN"


class SentimentLevel(Enum):
    """Nível de sentimento"""
    VERY_BEARISH = "VERY_BEARISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    BULLISH = "BULLISH"
    VERY_BULLISH = "VERY_BULLISH"


class NewsImpact(Enum):
    """Impacto de notícia"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class BotStatus(Enum):
    """Status do bot"""
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


# ============================================================================
# DATA CLASSES - SINAIS
# ============================================================================

@dataclass
class Signal:
    """Sinal de trading"""
    symbol: str
    type: SignalType
    strength: SignalStrength
    timestamp: datetime
    
    # Preços sugeridos
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Metadados
    strategy: Optional[str] = None
    confidence: float = 0.0
    reasons: List[str] = field(default_factory=list)
    
    # Contexto
    timeframe: Optional[Timeframe] = None
    market_regime: Optional[MarketRegime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'type': self.type.value,
            'strength': self.strength.value,
            'timestamp': self.timestamp.isoformat(),
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'strategy': self.strategy,
            'confidence': self.confidence,
            'reasons': self.reasons,
        }


# ============================================================================
# DATA CLASSES - POSIÇÕES
# ============================================================================

@dataclass
class Position:
    """Posição de trading"""
    ticket: int
    symbol: str
    order_type: OrderType
    volume: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # Status
    status: PositionStatus = PositionStatus.OPEN
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    
    # P&L
    profit: float = 0.0
    swap: float = 0.0
    commission: float = 0.0
    
    # Metadados
    bot_id: Optional[str] = None
    strategy: Optional[str] = None
    magic_number: Optional[int] = None
    comment: Optional[str] = None
    
    @property
    def is_buy(self) -> bool:
        return self.order_type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]
    
    @property
    def pips(self) -> float:
        """Calcula pips de lucro/prejuízo"""
        if self.is_buy:
            diff = self.current_price - self.entry_price
        else:
            diff = self.entry_price - self.current_price
        
        # Ajuste para diferentes tipos de pares
        if 'JPY' in self.symbol:
            return diff * 100
        elif 'XAU' in self.symbol:
            return diff * 10
        else:
            return diff * 10000
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticket': self.ticket,
            'symbol': self.symbol,
            'order_type': self.order_type.value,
            'volume': self.volume,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'profit': self.profit,
            'pips': self.pips,
            'status': self.status.value,
            'bot_id': self.bot_id,
            'strategy': self.strategy,
        }


# ============================================================================
# DATA CLASSES - ANÁLISE
# ============================================================================

@dataclass
class TechnicalAnalysis:
    """Resultado de análise técnica"""
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    
    # Indicadores
    rsi: Optional[float] = None
    macd: Optional[Dict[str, float]] = None
    ema: Optional[Dict[str, float]] = None
    bb: Optional[Dict[str, float]] = None
    atr: Optional[float] = None
    adx: Optional[float] = None
    
    # Padrões
    patterns: List[str] = field(default_factory=list)
    
    # Suporte/Resistência
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    
    # Tendência
    trend: Optional[str] = None
    trend_strength: float = 0.0
    
    # Sinal derivado
    signal: Optional[SignalType] = None
    signal_strength: float = 0.0


@dataclass
class SmartMoneyAnalysis:
    """Análise de Smart Money / Institucional"""
    symbol: str
    timestamp: datetime
    
    # Order Blocks
    bullish_order_blocks: List[Dict[str, float]] = field(default_factory=list)
    bearish_order_blocks: List[Dict[str, float]] = field(default_factory=list)
    
    # Liquidity
    buy_liquidity_zones: List[Dict[str, float]] = field(default_factory=list)
    sell_liquidity_zones: List[Dict[str, float]] = field(default_factory=list)
    
    # FVG (Fair Value Gaps)
    bullish_fvg: List[Dict[str, float]] = field(default_factory=list)
    bearish_fvg: List[Dict[str, float]] = field(default_factory=list)
    
    # Bias
    institutional_bias: Optional[str] = None
    bias_strength: float = 0.0


# ============================================================================
# DATA CLASSES - NOTÍCIAS E SENTIMENTO
# ============================================================================

@dataclass
class NewsItem:
    """Item de notícia"""
    title: str
    summary: str
    source: str
    timestamp: datetime
    url: Optional[str] = None
    
    # Sentimento
    sentiment_score: float = 0.0
    sentiment_label: Optional[SentimentLevel] = None
    
    # Impacto
    impact: NewsImpact = NewsImpact.LOW
    
    # Símbolos afetados
    symbols: List[str] = field(default_factory=list)
    
    # Tradução
    title_pt: Optional[str] = None
    summary_pt: Optional[str] = None


@dataclass
class MarketSentiment:
    """Sentimento de mercado agregado"""
    symbol: str
    timestamp: datetime
    
    # Scores
    news_sentiment: float = 0.0
    social_sentiment: float = 0.0
    institutional_sentiment: float = 0.0
    overall_sentiment: float = 0.0
    
    # Labels
    sentiment_level: SentimentLevel = SentimentLevel.NEUTRAL
    
    # Explicação
    explanation: str = ""
    explanation_pt: str = ""
    
    # Fontes
    news_count: int = 0
    sources: List[str] = field(default_factory=list)


@dataclass
class EconomicEvent:
    """Evento do calendário econômico"""
    name: str
    country: str
    currency: str
    timestamp: datetime
    
    impact: NewsImpact = NewsImpact.LOW
    
    # Valores
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    
    # Tradução
    name_pt: Optional[str] = None


# Alias para compatibilidade
CalendarEvent = EconomicEvent


# ============================================================================
# DATA CLASSES - RELATÓRIOS
# ============================================================================

@dataclass
class DailyPerformance:
    """Performance diária de um bot"""
    date: datetime
    bot_id: str
    symbol: str
    
    # Trades
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # P&L
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    
    # Métricas
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Estratégias
    trades_by_strategy: Dict[str, int] = field(default_factory=dict)
    pnl_by_strategy: Dict[str, float] = field(default_factory=dict)


@dataclass
class GlobalPerformance:
    """Performance global de todos os bots"""
    date: datetime
    
    # Totais
    total_pnl: float = 0.0
    total_trades: int = 0
    
    # Por bot
    by_bot: Dict[str, DailyPerformance] = field(default_factory=dict)
    
    # Exposição
    max_exposure: float = 0.0
    max_drawdown: float = 0.0


# ============================================================================
# DATA CLASSES - BRIEFING
# ============================================================================

@dataclass
class DailyBriefing:
    """Briefing diário completo"""
    date: datetime
    
    # Performance
    performance: Optional[GlobalPerformance] = None
    
    # Notícias
    top_news: List[NewsItem] = field(default_factory=list)
    
    # Sentimento por símbolo
    sentiments: Dict[str, MarketSentiment] = field(default_factory=dict)
    
    # Eventos do dia
    events: List[EconomicEvent] = field(default_factory=list)
    
    # Alertas
    alerts: List[str] = field(default_factory=list)
    
    # Resumo em português
    summary_pt: str = ""


# ============================================================================
# RISK CONFIG
# ============================================================================

@dataclass
class RiskConfig:
    """Configuração de risco para o sistema"""
    # Limites de perda
    max_daily_loss_pct: float = 5.0  # % máximo de perda diária
    max_weekly_loss_pct: float = 10.0  # % máximo de perda semanal
    max_drawdown: float = 10.0  # % máximo de drawdown
    
    # Exposição
    max_total_exposure: float = 3.0  # lotes totais máximos
    max_symbol_exposure: float = 1.0  # lotes máximos por símbolo
    max_correlated_exposure: float = 2.0  # lotes máximos em pares correlacionados
    max_positions: int = 5  # número máximo de posições abertas
    
    # Risco por trade
    risk_per_trade: float = 1.0  # % do capital por trade
    max_position_size: float = 1.0  # tamanho máximo de posição em lotes
    min_risk_reward: float = 1.5  # ratio mínimo de risco/retorno
    
    # Trailing stop
    use_trailing_stop: bool = True
    trailing_stop_pips: float = 20.0
    break_even_pips: float = 15.0
    
    # Aliases para compatibilidade
    @property
    def max_risk_per_trade(self) -> float:
        return self.risk_per_trade
    
    @property
    def max_daily_loss(self) -> float:
        return self.max_daily_loss_pct
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_daily_loss_pct': self.max_daily_loss_pct,
            'max_weekly_loss_pct': self.max_weekly_loss_pct,
            'max_drawdown': self.max_drawdown,
            'max_total_exposure': self.max_total_exposure,
            'max_symbol_exposure': self.max_symbol_exposure,
            'max_correlated_exposure': self.max_correlated_exposure,
            'max_positions': self.max_positions,
            'risk_per_trade': self.risk_per_trade,
            'max_position_size': self.max_position_size,
            'min_risk_reward': self.min_risk_reward,
            'use_trailing_stop': self.use_trailing_stop,
            'trailing_stop_pips': self.trailing_stop_pips,
            'break_even_pips': self.break_even_pips,
        }


# ============================================================================
# TYPE ALIASES
# ============================================================================

OHLC = Dict[str, Union[float, datetime]]  # Open, High, Low, Close, Volume, Time
CandleData = List[OHLC]
PriceLevel = Dict[str, float]  # {'price': float, 'strength': float}
