"""
BRAIN - Database Manager
Gerenciamento de banco de dados para histórico e analytics
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from ..core.logger import get_logger

logger = get_logger("database")


@dataclass
class TradeRecord:
    """Registro de trade"""
    ticket: int
    symbol: str
    direction: str  # buy, sell
    volume: float
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    profit: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    strategy: str = ""
    bot_id: str = ""
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    status: str = "open"  # open, closed, cancelled
    metadata: Dict = None


@dataclass
class SignalRecord:
    """Registro de sinal gerado"""
    id: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.0
    strategy: str = ""
    bot_id: str = ""
    executed: bool = False
    execution_ticket: Optional[int] = None
    reason: str = ""
    created_at: Optional[datetime] = None


@dataclass
class BotSessionRecord:
    """Registro de sessão do bot"""
    session_id: str
    bot_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    max_drawdown: float = 0.0
    status: str = "running"


class DatabaseManager:
    """
    Gerenciador de Banco de Dados SQLite
    
    Armazena:
    - Histórico de trades
    - Sinais gerados
    - Sessões de bots
    - Métricas e analytics
    """
    
    def __init__(self, db_path: str = None):
        """
        Args:
            db_path: Caminho do banco de dados
        """
        if db_path:
            self._db_path = Path(db_path)
        else:
            self._db_path = Path("brain/data/brain/brain.db")
        
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexão"""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Inicializa tabelas do banco"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela de trades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER UNIQUE,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    volume REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    profit REAL DEFAULT 0,
                    commission REAL DEFAULT 0,
                    swap REAL DEFAULT 0,
                    strategy TEXT,
                    bot_id TEXT,
                    opened_at TIMESTAMP,
                    closed_at TIMESTAMP,
                    status TEXT DEFAULT 'open',
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de sinais
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    confidence REAL DEFAULT 0,
                    strategy TEXT,
                    bot_id TEXT,
                    executed INTEGER DEFAULT 0,
                    execution_ticket INTEGER,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de sessões
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_sessions (
                    session_id TEXT PRIMARY KEY,
                    bot_id TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de métricas diárias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    bot_id TEXT,
                    symbol TEXT,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    total_volume REAL DEFAULT 0,
                    best_trade REAL DEFAULT 0,
                    worst_trade REAL DEFAULT 0,
                    avg_trade_duration INTEGER DEFAULT 0,
                    UNIQUE(date, bot_id, symbol)
                )
            """)
            
            # Tabela de logs importantes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT,
                    category TEXT,
                    message TEXT,
                    details TEXT
                )
            """)
            
            # Índices para performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_bot ON trades(bot_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_metrics(date)")
            
            conn.commit()
            logger.info(f"Database inicializado: {self._db_path}")
    
    # ==========================================================================
    # TRADES
    # ==========================================================================
    
    def save_trade(self, trade: TradeRecord) -> bool:
        """Salva ou atualiza trade"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO trades (
                        ticket, symbol, direction, volume, entry_price,
                        exit_price, stop_loss, take_profit, profit,
                        commission, swap, strategy, bot_id, opened_at,
                        closed_at, status, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade.ticket, trade.symbol, trade.direction,
                    trade.volume, trade.entry_price, trade.exit_price,
                    trade.stop_loss, trade.take_profit, trade.profit,
                    trade.commission, trade.swap, trade.strategy,
                    trade.bot_id, trade.opened_at, trade.closed_at,
                    trade.status, json.dumps(trade.metadata) if trade.metadata else None
                ))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar trade: {e}")
                return False
    
    def get_trade(self, ticket: int) -> Optional[TradeRecord]:
        """Busca trade por ticket"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE ticket = ?", (ticket,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_trade(row)
            return None
    
    def get_trades(
        self,
        symbol: str = None,
        bot_id: str = None,
        status: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[TradeRecord]:
        """Busca trades com filtros"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if bot_id:
                query += " AND bot_id = ?"
                params.append(bot_id)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if start_date:
                query += " AND opened_at >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND opened_at <= ?"
                params.append(end_date)
            
            query += f" ORDER BY opened_at DESC LIMIT {limit}"
            
            cursor.execute(query, params)
            return [self._row_to_trade(row) for row in cursor.fetchall()]
    
    def _row_to_trade(self, row: sqlite3.Row) -> TradeRecord:
        """Converte row para TradeRecord"""
        return TradeRecord(
            ticket=row["ticket"],
            symbol=row["symbol"],
            direction=row["direction"],
            volume=row["volume"],
            entry_price=row["entry_price"],
            exit_price=row["exit_price"],
            stop_loss=row["stop_loss"],
            take_profit=row["take_profit"],
            profit=row["profit"],
            commission=row["commission"],
            swap=row["swap"],
            strategy=row["strategy"],
            bot_id=row["bot_id"],
            opened_at=row["opened_at"],
            closed_at=row["closed_at"],
            status=row["status"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None
        )
    
    # ==========================================================================
    # SIGNALS
    # ==========================================================================
    
    def save_signal(self, signal: SignalRecord) -> bool:
        """Salva sinal"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO signals (
                        id, symbol, direction, entry_price, stop_loss,
                        take_profit, confidence, strategy, bot_id,
                        executed, execution_ticket, reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal.id, signal.symbol, signal.direction,
                    signal.entry_price, signal.stop_loss, signal.take_profit,
                    signal.confidence, signal.strategy, signal.bot_id,
                    1 if signal.executed else 0, signal.execution_ticket,
                    signal.reason, signal.created_at or datetime.now()
                ))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Erro ao salvar signal: {e}")
                return False
    
    def get_signals(
        self,
        symbol: str = None,
        bot_id: str = None,
        executed: bool = None,
        limit: int = 50
    ) -> List[SignalRecord]:
        """Busca sinais"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM signals WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if bot_id:
                query += " AND bot_id = ?"
                params.append(bot_id)
            
            if executed is not None:
                query += " AND executed = ?"
                params.append(1 if executed else 0)
            
            query += f" ORDER BY created_at DESC LIMIT {limit}"
            
            cursor.execute(query, params)
            
            signals = []
            for row in cursor.fetchall():
                signals.append(SignalRecord(
                    id=row["id"],
                    symbol=row["symbol"],
                    direction=row["direction"],
                    entry_price=row["entry_price"],
                    stop_loss=row["stop_loss"],
                    take_profit=row["take_profit"],
                    confidence=row["confidence"],
                    strategy=row["strategy"],
                    bot_id=row["bot_id"],
                    executed=bool(row["executed"]),
                    execution_ticket=row["execution_ticket"],
                    reason=row["reason"],
                    created_at=row["created_at"]
                ))
            
            return signals
    
    # ==========================================================================
    # SESSIONS
    # ==========================================================================
    
    def start_session(self, bot_id: str, session_id: str) -> bool:
        """Inicia nova sessão"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO bot_sessions (
                        session_id, bot_id, started_at, status
                    ) VALUES (?, ?, ?, 'running')
                """, (session_id, bot_id, datetime.now()))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Erro ao iniciar sessão: {e}")
                return False
    
    def end_session(
        self,
        session_id: str,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        total_profit: float,
        max_drawdown: float
    ) -> bool:
        """Finaliza sessão"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    UPDATE bot_sessions SET
                        ended_at = ?,
                        total_trades = ?,
                        winning_trades = ?,
                        losing_trades = ?,
                        total_profit = ?,
                        max_drawdown = ?,
                        status = 'completed'
                    WHERE session_id = ?
                """, (
                    datetime.now(), total_trades, winning_trades,
                    losing_trades, total_profit, max_drawdown, session_id
                ))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Erro ao finalizar sessão: {e}")
                return False
    
    # ==========================================================================
    # MÉTRICAS
    # ==========================================================================
    
    def update_daily_metrics(
        self,
        date: datetime,
        bot_id: str,
        symbol: str,
        trades: int = 0,
        wins: int = 0,
        losses: int = 0,
        profit: float = 0,
        volume: float = 0
    ):
        """Atualiza métricas diárias"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO daily_metrics (
                    date, bot_id, symbol, total_trades, winning_trades,
                    losing_trades, total_profit, total_volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, bot_id, symbol) DO UPDATE SET
                    total_trades = total_trades + ?,
                    winning_trades = winning_trades + ?,
                    losing_trades = losing_trades + ?,
                    total_profit = total_profit + ?,
                    total_volume = total_volume + ?
            """, (
                date.date(), bot_id, symbol, trades, wins, losses, profit, volume,
                trades, wins, losses, profit, volume
            ))
            
            conn.commit()
    
    def get_performance_summary(
        self,
        bot_id: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Retorna resumo de performance"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            start_date = datetime.now() - timedelta(days=days)
            
            query = """
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END) as losses,
                    SUM(profit) as total_profit,
                    AVG(profit) as avg_profit,
                    MAX(profit) as best_trade,
                    MIN(profit) as worst_trade
                FROM trades
                WHERE status = 'closed' AND closed_at >= ?
            """
            params = [start_date]
            
            if bot_id:
                query += " AND bot_id = ?"
                params.append(bot_id)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            total = row["total_trades"] or 0
            wins = row["wins"] or 0
            
            return {
                "period_days": days,
                "total_trades": total,
                "winning_trades": wins,
                "losing_trades": row["losses"] or 0,
                "win_rate": (wins / total * 100) if total > 0 else 0,
                "total_profit": round(row["total_profit"] or 0, 2),
                "avg_profit": round(row["avg_profit"] or 0, 2),
                "best_trade": round(row["best_trade"] or 0, 2),
                "worst_trade": round(row["worst_trade"] or 0, 2)
            }
    
    # ==========================================================================
    # LOGS
    # ==========================================================================
    
    def log_event(
        self,
        level: str,
        category: str,
        message: str,
        details: Dict = None
    ):
        """Registra evento importante"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO event_logs (level, category, message, details)
                VALUES (?, ?, ?, ?)
            """, (
                level, category, message,
                json.dumps(details) if details else None
            ))
            
            conn.commit()
    
    def get_events(
        self,
        level: str = None,
        category: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Busca eventos"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM event_logs WHERE 1=1"
            params = []
            
            if level:
                query += " AND level = ?"
                params.append(level)
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += f" ORDER BY timestamp DESC LIMIT {limit}"
            
            cursor.execute(query, params)
            
            return [dict(row) for row in cursor.fetchall()]


# Singleton
_db_manager: Optional[DatabaseManager] = None


def get_database(db_path: str = None) -> DatabaseManager:
    """Obtém instância do DatabaseManager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager
