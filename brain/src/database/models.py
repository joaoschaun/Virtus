"""
VIRTUS Database Models
======================

Modelos SQLAlchemy para persistência de dados do sistema de trading.
Suporta PostgreSQL com TimescaleDB para séries temporais.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean, 
    DateTime, Text, JSON, Enum, ForeignKey, Index,
    Numeric, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

# Tenta importar tipos PostgreSQL, fallback para genérico
try:
    from sqlalchemy.dialects.postgresql import JSONB as JSONType, UUID
except ImportError:
    JSONType = JSON
    UUID = String(36)

Base = declarative_base()


# ============================================================
# ENUMS
# ============================================================

class TradeDirection(PyEnum):
    """Direção do trade."""
    BUY = "buy"
    SELL = "sell"


class TradeStatus(PyEnum):
    """Status do trade."""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    ERROR = "error"


class SignalType(PyEnum):
    """Tipo de sinal."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class ExitReason(PyEnum):
    """Motivo de saída."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    BREAK_EVEN = "break_even"
    MANUAL = "manual"
    SIGNAL = "signal"
    TIME_EXIT = "time_exit"
    PARTIAL = "partial"
    HEDGE = "hedge"
    RISK_LIMIT = "risk_limit"


# ============================================================
# MODELOS PRINCIPAIS
# ============================================================

class Trade(Base):
    """
    Registro de trade executado.
    
    Armazena informações completas de cada trade, incluindo
    entrada, saída, métricas e metadados.
    """
    __tablename__ = 'trades'
    
    # Identificação
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    ticket = Column(BigInteger, unique=True, nullable=False, index=True)
    
    # Informações básicas
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(Enum(TradeDirection), nullable=False)
    volume = Column(Float, nullable=False)
    
    # Preços
    entry_price = Column(Numeric(18, 8), nullable=False)
    exit_price = Column(Numeric(18, 8))
    stop_loss = Column(Numeric(18, 8))
    take_profit = Column(Numeric(18, 8))
    
    # Timestamps
    open_time = Column(DateTime, nullable=False, index=True)
    close_time = Column(DateTime, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Resultado
    profit = Column(Numeric(18, 2))
    profit_pips = Column(Float)
    commission = Column(Numeric(18, 2), default=0)
    swap = Column(Numeric(18, 2), default=0)
    slippage_pips = Column(Float, default=0)
    
    # Status
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN, nullable=False, index=True)
    exit_reason = Column(Enum(ExitReason))
    
    # Contexto
    strategy = Column(String(100), index=True)
    bot_id = Column(String(50), index=True)
    magic_number = Column(Integer)
    comment = Column(Text)
    
    # Métricas
    mae = Column(Float)  # Maximum Adverse Excursion
    mfe = Column(Float)  # Maximum Favorable Excursion
    risk_reward = Column(Float)
    duration_minutes = Column(Integer)
    
    # Metadados JSON
    entry_context = Column(JSON)  # Contexto de mercado na entrada
    exit_context = Column(JSON)   # Contexto de mercado na saída
    signals = Column(JSON)        # Sinais que geraram o trade
    tags = Column(JSON)           # Tags para categorização
    
    # Relacionamentos
    partial_exits = relationship("PartialExit", back_populates="trade", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('ix_trades_symbol_open_time', 'symbol', 'open_time'),
        Index('ix_trades_strategy_status', 'strategy', 'status'),
        Index('ix_trades_bot_status', 'bot_id', 'status'),
        CheckConstraint('volume > 0', name='check_volume_positive'),
    )
    
    def __repr__(self):
        return f"<Trade {self.ticket} {self.symbol} {self.direction.value} {self.volume}>"
    
    @property
    def net_profit(self) -> float:
        """Lucro líquido (profit - commission - swap)."""
        if self.profit is None:
            return 0.0
        return float(self.profit) - float(self.commission or 0) - float(self.swap or 0)
    
    @property
    def is_winner(self) -> bool:
        """Trade foi vencedor?"""
        return self.net_profit > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'id': self.id,
            'uuid': str(self.uuid),
            'ticket': self.ticket,
            'symbol': self.symbol,
            'direction': self.direction.value if self.direction else None,
            'volume': self.volume,
            'entry_price': float(self.entry_price) if self.entry_price else None,
            'exit_price': float(self.exit_price) if self.exit_price else None,
            'stop_loss': float(self.stop_loss) if self.stop_loss else None,
            'take_profit': float(self.take_profit) if self.take_profit else None,
            'open_time': self.open_time.isoformat() if self.open_time else None,
            'close_time': self.close_time.isoformat() if self.close_time else None,
            'profit': float(self.profit) if self.profit else None,
            'profit_pips': self.profit_pips,
            'status': self.status.value if self.status else None,
            'exit_reason': self.exit_reason.value if self.exit_reason else None,
            'strategy': self.strategy,
            'bot_id': self.bot_id,
            'net_profit': self.net_profit,
            'is_winner': self.is_winner,
        }


class PartialExit(Base):
    """Saídas parciais de um trade."""
    __tablename__ = 'partial_exits'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(BigInteger, ForeignKey('trades.id', ondelete='CASCADE'), nullable=False)
    
    volume = Column(Float, nullable=False)
    exit_price = Column(Numeric(18, 8), nullable=False)
    profit = Column(Numeric(18, 2))
    exit_time = Column(DateTime, nullable=False)
    reason = Column(String(100))
    
    trade = relationship("Trade", back_populates="partial_exits")
    
    __table_args__ = (
        Index('ix_partial_exits_trade', 'trade_id'),
    )


class Signal(Base):
    """
    Registro de sinal gerado.
    
    Armazena todos os sinais gerados pelo sistema,
    permitindo análise de performance das estratégias.
    """
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Informações básicas
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(Enum(SignalType), nullable=False)
    strength = Column(String(20))  # weak, moderate, strong
    confidence = Column(Float)
    
    # Preços sugeridos
    entry_price = Column(Numeric(18, 8))
    stop_loss = Column(Numeric(18, 8))
    take_profit = Column(Numeric(18, 8))
    
    # Contexto
    strategy = Column(String(100))  # Sem index individual, usa composto
    timeframe = Column(String(10))
    market_regime = Column(String(50))
    
    # Timestamps
    generated_at = Column(DateTime, nullable=False, index=True)
    expired_at = Column(DateTime)
    executed_at = Column(DateTime)
    
    # Resultado
    was_executed = Column(Boolean, default=False)
    trade_ticket = Column(BigInteger)
    result_profit = Column(Numeric(18, 2))
    
    # Análise
    reasons = Column(JSON)  # Lista de razões do sinal
    indicators = Column(JSON)  # Valores dos indicadores
    market_context = Column(JSON)  # Contexto de mercado
    
    __table_args__ = (
        Index('ix_signals_symbol_generated', 'symbol', 'generated_at'),
        Index('ix_signals_strategy_generated', 'strategy', 'generated_at'),
    )
    
    def __repr__(self):
        return f"<Signal {self.symbol} {self.signal_type.value} @ {self.generated_at}>"


class DailyPerformance(Base):
    """
    Performance diária agregada.
    
    Métricas consolidadas por dia para análise de performance.
    """
    __tablename__ = 'daily_performance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificação
    date = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), index=True)  # NULL = todos os símbolos
    bot_id = Column(String(50), index=True)   # NULL = todos os bots
    strategy = Column(String(100), index=True)  # NULL = todas as estratégias
    
    # Métricas de trades
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # Resultado
    gross_profit = Column(Numeric(18, 2), default=0)
    gross_loss = Column(Numeric(18, 2), default=0)
    net_profit = Column(Numeric(18, 2), default=0)
    commission_total = Column(Numeric(18, 2), default=0)
    swap_total = Column(Numeric(18, 2), default=0)
    
    # Métricas
    win_rate = Column(Float)
    profit_factor = Column(Float)
    avg_profit = Column(Numeric(18, 2))
    avg_loss = Column(Numeric(18, 2))
    largest_win = Column(Numeric(18, 2))
    largest_loss = Column(Numeric(18, 2))
    avg_duration_minutes = Column(Float)
    
    # Capital
    starting_balance = Column(Numeric(18, 2))
    ending_balance = Column(Numeric(18, 2))
    max_drawdown = Column(Float)
    max_drawdown_value = Column(Numeric(18, 2))
    
    # Pips
    total_pips = Column(Float, default=0)
    avg_pips_per_trade = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('date', 'symbol', 'bot_id', 'strategy', name='uq_daily_performance'),
        Index('ix_daily_perf_date', 'date'),
    )


class AccountSnapshot(Base):
    """
    Snapshot do estado da conta.
    
    Registra periodicamente o estado da conta para
    análise de equity curve e drawdown.
    """
    __tablename__ = 'account_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Valores da conta
    balance = Column(Numeric(18, 2), nullable=False)
    equity = Column(Numeric(18, 2), nullable=False)
    margin = Column(Numeric(18, 2))
    free_margin = Column(Numeric(18, 2))
    margin_level = Column(Float)
    
    # Posições
    open_positions = Column(Integer, default=0)
    open_volume = Column(Float, default=0)
    unrealized_pnl = Column(Numeric(18, 2), default=0)
    
    # Drawdown
    peak_equity = Column(Numeric(18, 2))
    drawdown_percent = Column(Float, default=0)
    drawdown_value = Column(Numeric(18, 2), default=0)
    
    # Métricas do dia
    daily_pnl = Column(Numeric(18, 2), default=0)
    daily_trades = Column(Integer, default=0)
    
    __table_args__ = (
        Index('ix_snapshots_timestamp', 'timestamp'),
    )


class BotSession(Base):
    """
    Sessão de execução do bot.
    
    Registra cada sessão de operação do bot para
    análise de uptime e performance.
    """
    __tablename__ = 'bot_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    bot_id = Column(String(50), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    
    # Timestamps
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime)
    
    # Config
    config_snapshot = Column(JSON)  # Configuração usada na sessão
    
    # Resultado
    trades_count = Column(Integer, default=0)
    signals_count = Column(Integer, default=0)
    profit = Column(Numeric(18, 2), default=0)
    
    # Status
    status = Column(String(20), default='running')  # running, stopped, error
    stop_reason = Column(Text)
    error_message = Column(Text)
    
    __table_args__ = (
        Index('ix_bot_sessions_bot_started', 'bot_id', 'started_at'),
    )


class Alert(Base):
    """
    Alertas do sistema.
    
    Registra todos os alertas gerados pelo sistema
    para análise e auditoria.
    """
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Tipo e severidade
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False)  # info, warning, critical
    
    # Contexto
    symbol = Column(String(20), index=True)
    bot_id = Column(String(50), index=True)
    trade_ticket = Column(BigInteger)
    
    # Conteúdo
    title = Column(String(200), nullable=False)
    message = Column(Text)
    data = Column(JSON)
    
    # Status
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    __table_args__ = (
        Index('ix_alerts_type_created', 'alert_type', 'created_at'),
        Index('ix_alerts_severity', 'severity', 'acknowledged'),
    )


class MarketData(Base):
    """
    Dados de mercado históricos.
    
    Armazena candles para backtesting e análise.
    Ideal para usar com TimescaleDB como hypertable.
    """
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # OHLCV
    open = Column(Numeric(18, 8), nullable=False)
    high = Column(Numeric(18, 8), nullable=False)
    low = Column(Numeric(18, 8), nullable=False)
    close = Column(Numeric(18, 8), nullable=False)
    volume = Column(Float, nullable=False)
    
    # Tick volume
    tick_volume = Column(Integer)
    spread = Column(Integer)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uq_market_data'),
        Index('ix_market_data_symbol_tf_time', 'symbol', 'timeframe', 'timestamp'),
    )


# ============================================================
# HELPERS
# ============================================================

def create_all_tables(engine):
    """Cria todas as tabelas no banco."""
    Base.metadata.create_all(engine)


def drop_all_tables(engine):
    """Remove todas as tabelas (CUIDADO!)."""
    Base.metadata.drop_all(engine)
