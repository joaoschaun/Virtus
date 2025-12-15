"""
VIRTUS Trade Repository
=======================

Repository pattern para operações de trades.
Encapsula toda a lógica de persistência de trades.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import Session

from .models import (
    Trade, PartialExit, Signal, DailyPerformance,
    TradeDirection, TradeStatus, ExitReason, SignalType
)
from .manager import DatabaseManager, get_database
from ..core import VirtusLogger


class TradeRepository:
    """
    Repository para operações de Trade.
    
    Encapsula CRUD e queries complexas de trades.
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_database()
        self.logger = VirtusLogger.get_logger("trade_repository")
    
    # ============================================================
    # CRUD BÁSICO
    # ============================================================
    
    def create(self, trade: Trade) -> Trade:
        """Cria um novo trade."""
        with self.db.session() as session:
            session.add(trade)
            session.flush()
            session.refresh(trade)
            self.logger.info(f"Trade created: {trade.ticket}")
            return trade
    
    def get_by_id(self, trade_id: int) -> Optional[Trade]:
        """Busca trade por ID."""
        with self.db.session() as session:
            return session.query(Trade).filter(Trade.id == trade_id).first()
    
    def get_by_ticket(self, ticket: int) -> Optional[Trade]:
        """Busca trade por ticket MT5."""
        with self.db.session() as session:
            return session.query(Trade).filter(Trade.ticket == ticket).first()
    
    def get_by_uuid(self, uuid: str) -> Optional[Trade]:
        """Busca trade por UUID."""
        with self.db.session() as session:
            return session.query(Trade).filter(Trade.uuid == uuid).first()
    
    def update(self, trade: Trade) -> Trade:
        """Atualiza um trade existente."""
        with self.db.session() as session:
            session.merge(trade)
            self.logger.debug(f"Trade updated: {trade.ticket}")
            return trade
    
    def delete(self, trade_id: int) -> bool:
        """Remove um trade."""
        with self.db.session() as session:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                session.delete(trade)
                self.logger.warning(f"Trade deleted: {trade.ticket}")
                return True
            return False
    
    # ============================================================
    # OPERAÇÕES DE TRADING
    # ============================================================
    
    def open_trade(
        self,
        ticket: int,
        symbol: str,
        direction: str,
        volume: float,
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy: Optional[str] = None,
        bot_id: Optional[str] = None,
        magic_number: Optional[int] = None,
        comment: Optional[str] = None,
        entry_context: Optional[dict] = None,
    ) -> Trade:
        """
        Registra abertura de trade.
        """
        trade = Trade(
            ticket=ticket,
            symbol=symbol,
            direction=TradeDirection(direction.lower()),
            volume=volume,
            entry_price=Decimal(str(entry_price)),
            stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
            take_profit=Decimal(str(take_profit)) if take_profit else None,
            open_time=datetime.now(),
            status=TradeStatus.OPEN,
            strategy=strategy,
            bot_id=bot_id,
            magic_number=magic_number,
            comment=comment,
            entry_context=entry_context,
        )
        
        return self.create(trade)
    
    def close_trade(
        self,
        ticket: int,
        exit_price: float,
        profit: float,
        profit_pips: float,
        exit_reason: str,
        commission: float = 0,
        swap: float = 0,
        slippage_pips: float = 0,
        exit_context: Optional[dict] = None,
    ) -> Optional[Trade]:
        """
        Registra fechamento de trade.
        """
        with self.db.session() as session:
            trade = session.query(Trade).filter(Trade.ticket == ticket).first()
            
            if not trade:
                self.logger.warning(f"Trade not found for close: {ticket}")
                return None
            
            trade.exit_price = Decimal(str(exit_price))
            trade.profit = Decimal(str(profit))
            trade.profit_pips = profit_pips
            trade.commission = Decimal(str(commission))
            trade.swap = Decimal(str(swap))
            trade.slippage_pips = slippage_pips
            trade.close_time = datetime.now()
            trade.status = TradeStatus.CLOSED
            trade.exit_reason = ExitReason(exit_reason)
            trade.exit_context = exit_context
            
            # Calcula duração
            if trade.open_time:
                duration = datetime.now() - trade.open_time
                trade.duration_minutes = int(duration.total_seconds() / 60)
            
            session.flush()
            session.refresh(trade)
            
            self.logger.info(
                f"Trade closed: {ticket} | Profit: ${profit:.2f} | "
                f"Reason: {exit_reason}"
            )
            
            return trade
    
    def update_trade_metrics(
        self,
        ticket: int,
        mae: Optional[float] = None,
        mfe: Optional[float] = None,
        risk_reward: Optional[float] = None,
    ) -> Optional[Trade]:
        """
        Atualiza métricas de um trade aberto.
        """
        with self.db.session() as session:
            trade = session.query(Trade).filter(Trade.ticket == ticket).first()
            
            if not trade:
                return None
            
            if mae is not None:
                trade.mae = mae
            if mfe is not None:
                trade.mfe = mfe
            if risk_reward is not None:
                trade.risk_reward = risk_reward
            
            return trade
    
    def add_partial_exit(
        self,
        ticket: int,
        volume: float,
        exit_price: float,
        profit: float,
        reason: str = "partial",
    ) -> Optional[PartialExit]:
        """
        Registra saída parcial de um trade.
        """
        with self.db.session() as session:
            trade = session.query(Trade).filter(Trade.ticket == ticket).first()
            
            if not trade:
                self.logger.warning(f"Trade not found for partial exit: {ticket}")
                return None
            
            partial = PartialExit(
                trade_id=trade.id,
                volume=volume,
                exit_price=Decimal(str(exit_price)),
                profit=Decimal(str(profit)),
                exit_time=datetime.now(),
                reason=reason,
            )
            
            session.add(partial)
            
            self.logger.info(
                f"Partial exit: {ticket} | Volume: {volume} | Profit: ${profit:.2f}"
            )
            
            return partial
    
    # ============================================================
    # QUERIES
    # ============================================================
    
    def get_open_trades(
        self,
        symbol: Optional[str] = None,
        bot_id: Optional[str] = None,
    ) -> List[Trade]:
        """Retorna trades abertos."""
        with self.db.session() as session:
            query = session.query(Trade).filter(Trade.status == TradeStatus.OPEN)
            
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if bot_id:
                query = query.filter(Trade.bot_id == bot_id)
            
            return query.order_by(Trade.open_time).all()
    
    def get_trades_by_period(
        self,
        start_date: datetime,
        end_date: datetime,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        status: Optional[TradeStatus] = None,
    ) -> List[Trade]:
        """Retorna trades em um período."""
        with self.db.session() as session:
            query = session.query(Trade).filter(
                Trade.open_time >= start_date,
                Trade.open_time <= end_date
            )
            
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if strategy:
                query = query.filter(Trade.strategy == strategy)
            if status:
                query = query.filter(Trade.status == status)
            
            return query.order_by(Trade.open_time).all()
    
    def get_recent_trades(
        self,
        limit: int = 50,
        symbol: Optional[str] = None,
        status: Optional[TradeStatus] = None,
    ) -> List[Trade]:
        """Retorna trades mais recentes."""
        with self.db.session() as session:
            query = session.query(Trade)
            
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if status:
                query = query.filter(Trade.status == status)
            
            return query.order_by(desc(Trade.open_time)).limit(limit).all()
    
    def get_today_trades(self, symbol: Optional[str] = None) -> List[Trade]:
        """Retorna trades de hoje."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.get_trades_by_period(today, datetime.now(), symbol)
    
    # ============================================================
    # ESTATÍSTICAS
    # ============================================================
    
    def get_trade_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calcula estatísticas de trades.
        """
        with self.db.session() as session:
            query = session.query(Trade).filter(Trade.status == TradeStatus.CLOSED)
            
            if start_date:
                query = query.filter(Trade.close_time >= start_date)
            if end_date:
                query = query.filter(Trade.close_time <= end_date)
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if strategy:
                query = query.filter(Trade.strategy == strategy)
            
            trades = query.all()
            
            if not trades:
                return self._empty_stats()
            
            # Calcula métricas
            total = len(trades)
            winners = [t for t in trades if t.net_profit > 0]
            losers = [t for t in trades if t.net_profit <= 0]
            
            total_profit = sum(t.net_profit for t in trades)
            gross_profit = sum(t.net_profit for t in winners) if winners else 0
            gross_loss = abs(sum(t.net_profit for t in losers)) if losers else 0
            
            win_rate = len(winners) / total if total > 0 else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            avg_win = gross_profit / len(winners) if winners else 0
            avg_loss = gross_loss / len(losers) if losers else 0
            
            return {
                'total_trades': total,
                'winning_trades': len(winners),
                'losing_trades': len(losers),
                'win_rate': round(win_rate * 100, 2),
                'profit_factor': round(profit_factor, 2),
                'total_profit': round(total_profit, 2),
                'gross_profit': round(gross_profit, 2),
                'gross_loss': round(gross_loss, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'largest_win': max((t.net_profit for t in winners), default=0),
                'largest_loss': min((t.net_profit for t in losers), default=0),
                'avg_duration_minutes': sum(t.duration_minutes or 0 for t in trades) / total,
                'total_pips': sum(t.profit_pips or 0 for t in trades),
            }
    
    def _empty_stats(self) -> Dict[str, Any]:
        """Estatísticas vazias."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'total_profit': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'avg_duration_minutes': 0,
            'total_pips': 0,
        }
    
    def get_performance_by_symbol(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Performance agrupada por símbolo."""
        with self.db.session() as session:
            query = session.query(Trade).filter(Trade.status == TradeStatus.CLOSED)
            
            if start_date:
                query = query.filter(Trade.close_time >= start_date)
            if end_date:
                query = query.filter(Trade.close_time <= end_date)
            
            trades = query.all()
            
            # Agrupa por símbolo
            by_symbol = {}
            for trade in trades:
                if trade.symbol not in by_symbol:
                    by_symbol[trade.symbol] = []
                by_symbol[trade.symbol].append(trade)
            
            # Calcula stats por símbolo
            result = {}
            for symbol, symbol_trades in by_symbol.items():
                winners = [t for t in symbol_trades if t.net_profit > 0]
                total = len(symbol_trades)
                
                result[symbol] = {
                    'total_trades': total,
                    'win_rate': len(winners) / total * 100 if total > 0 else 0,
                    'total_profit': sum(t.net_profit for t in symbol_trades),
                    'total_pips': sum(t.profit_pips or 0 for t in symbol_trades),
                }
            
            return result
    
    def get_performance_by_strategy(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Performance agrupada por estratégia."""
        with self.db.session() as session:
            query = session.query(Trade).filter(
                Trade.status == TradeStatus.CLOSED,
                Trade.strategy.isnot(None)
            )
            
            if start_date:
                query = query.filter(Trade.close_time >= start_date)
            if end_date:
                query = query.filter(Trade.close_time <= end_date)
            
            trades = query.all()
            
            # Agrupa por estratégia
            by_strategy = {}
            for trade in trades:
                strategy = trade.strategy or "unknown"
                if strategy not in by_strategy:
                    by_strategy[strategy] = []
                by_strategy[strategy].append(trade)
            
            # Calcula stats
            result = {}
            for strategy, strategy_trades in by_strategy.items():
                winners = [t for t in strategy_trades if t.net_profit > 0]
                total = len(strategy_trades)
                
                result[strategy] = {
                    'total_trades': total,
                    'win_rate': len(winners) / total * 100 if total > 0 else 0,
                    'total_profit': sum(t.net_profit for t in strategy_trades),
                    'profit_factor': self._calc_profit_factor(strategy_trades),
                }
            
            return result
    
    def _calc_profit_factor(self, trades: List[Trade]) -> float:
        """Calcula profit factor de uma lista de trades."""
        gross_profit = sum(t.net_profit for t in trades if t.net_profit > 0)
        gross_loss = abs(sum(t.net_profit for t in trades if t.net_profit <= 0))
        return round(gross_profit / gross_loss, 2) if gross_loss > 0 else float('inf')
    
    def get_equity_curve(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_balance: float = 10000,
    ) -> List[Tuple[datetime, float]]:
        """
        Retorna curva de equity.
        """
        with self.db.session() as session:
            query = session.query(Trade).filter(
                Trade.status == TradeStatus.CLOSED
            ).order_by(Trade.close_time)
            
            if start_date:
                query = query.filter(Trade.close_time >= start_date)
            if end_date:
                query = query.filter(Trade.close_time <= end_date)
            
            trades = query.all()
            
            curve = [(start_date or datetime.now() - timedelta(days=30), initial_balance)]
            balance = initial_balance
            
            for trade in trades:
                balance += trade.net_profit
                curve.append((trade.close_time, balance))
            
            return curve
    
    def get_drawdown_analysis(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_balance: float = 10000,
    ) -> Dict[str, Any]:
        """
        Analisa drawdowns.
        """
        curve = self.get_equity_curve(start_date, end_date, initial_balance)
        
        if len(curve) < 2:
            return {
                'max_drawdown_percent': 0,
                'max_drawdown_value': 0,
                'current_drawdown_percent': 0,
                'recovery_time_days': 0,
            }
        
        peak = initial_balance
        max_dd_percent = 0
        max_dd_value = 0
        
        for timestamp, equity in curve:
            if equity > peak:
                peak = equity
            
            dd_value = peak - equity
            dd_percent = (dd_value / peak) * 100 if peak > 0 else 0
            
            if dd_percent > max_dd_percent:
                max_dd_percent = dd_percent
                max_dd_value = dd_value
        
        current_equity = curve[-1][1]
        current_dd = ((peak - current_equity) / peak) * 100 if peak > 0 else 0
        
        return {
            'max_drawdown_percent': round(max_dd_percent, 2),
            'max_drawdown_value': round(max_dd_value, 2),
            'current_drawdown_percent': round(current_dd, 2),
            'peak_equity': round(peak, 2),
            'current_equity': round(current_equity, 2),
        }


class SignalRepository:
    """
    Repository para operações de Signal.
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_database()
        self.logger = VirtusLogger.get_logger("signal_repository")
    
    def create(self, signal: Signal) -> Signal:
        """Cria um novo sinal."""
        with self.db.session() as session:
            session.add(signal)
            session.flush()
            session.refresh(signal)
            return signal
    
    def record_signal(
        self,
        symbol: str,
        signal_type: str,
        strength: str,
        confidence: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy: Optional[str] = None,
        timeframe: Optional[str] = None,
        reasons: Optional[List[str]] = None,
        indicators: Optional[dict] = None,
        market_context: Optional[dict] = None,
    ) -> Signal:
        """
        Registra um sinal gerado.
        """
        signal = Signal(
            symbol=symbol,
            signal_type=SignalType(signal_type.lower()),
            strength=strength,
            confidence=confidence,
            entry_price=Decimal(str(entry_price)) if entry_price else None,
            stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
            take_profit=Decimal(str(take_profit)) if take_profit else None,
            strategy=strategy,
            timeframe=timeframe,
            generated_at=datetime.now(),
            reasons=reasons,
            indicators=indicators,
            market_context=market_context,
        )
        
        return self.create(signal)
    
    def mark_executed(
        self,
        signal_id: int,
        trade_ticket: int,
    ) -> Optional[Signal]:
        """Marca sinal como executado."""
        with self.db.session() as session:
            signal = session.query(Signal).filter(Signal.id == signal_id).first()
            
            if signal:
                signal.was_executed = True
                signal.executed_at = datetime.now()
                signal.trade_ticket = trade_ticket
            
            return signal
    
    def get_recent_signals(
        self,
        limit: int = 100,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
    ) -> List[Signal]:
        """Retorna sinais recentes."""
        with self.db.session() as session:
            query = session.query(Signal)
            
            if symbol:
                query = query.filter(Signal.symbol == symbol)
            if strategy:
                query = query.filter(Signal.strategy == strategy)
            
            return query.order_by(desc(Signal.generated_at)).limit(limit).all()
    
    def get_signal_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Estatísticas de sinais."""
        with self.db.session() as session:
            query = session.query(Signal)
            
            if start_date:
                query = query.filter(Signal.generated_at >= start_date)
            if end_date:
                query = query.filter(Signal.generated_at <= end_date)
            if strategy:
                query = query.filter(Signal.strategy == strategy)
            
            signals = query.all()
            
            if not signals:
                return {
                    'total_signals': 0,
                    'executed_signals': 0,
                    'execution_rate': 0,
                    'by_type': {},
                }
            
            executed = [s for s in signals if s.was_executed]
            
            by_type = {}
            for signal in signals:
                stype = signal.signal_type.value
                if stype not in by_type:
                    by_type[stype] = 0
                by_type[stype] += 1
            
            return {
                'total_signals': len(signals),
                'executed_signals': len(executed),
                'execution_rate': len(executed) / len(signals) * 100,
                'by_type': by_type,
                'avg_confidence': sum(s.confidence or 0 for s in signals) / len(signals),
            }


class PerformanceRepository:
    """
    Repository para operações de Performance diária.
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_database()
        self.logger = VirtusLogger.get_logger("performance_repository")
    
    def get_by_date(self, date: datetime) -> Optional[DailyPerformance]:
        """Busca performance por data."""
        with self.db.session() as session:
            return session.query(DailyPerformance).filter(
                func.date(DailyPerformance.date) == date.date()
            ).first()
    
    def get_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 30
    ) -> List[DailyPerformance]:
        """Busca performances em um período."""
        with self.db.session() as session:
            query = session.query(DailyPerformance)
            
            if start_date:
                query = query.filter(DailyPerformance.date >= start_date)
            if end_date:
                query = query.filter(DailyPerformance.date <= end_date)
            
            return query.order_by(desc(DailyPerformance.date)).limit(limit).all()
    
    def create_or_update(self, performance: DailyPerformance) -> DailyPerformance:
        """Cria ou atualiza performance diária."""
        with self.db.session() as session:
            existing = session.query(DailyPerformance).filter(
                func.date(DailyPerformance.date) == performance.date.date()
            ).first()
            
            if existing:
                for key, value in performance.__dict__.items():
                    if not key.startswith('_'):
                        setattr(existing, key, value)
                session.flush()
                return existing
            else:
                session.add(performance)
                session.flush()
                session.refresh(performance)
                return performance
    
    def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """Resumo de performance dos últimos N dias."""
        start_date = datetime.now() - timedelta(days=days)
        performances = self.get_range(start_date=start_date, limit=days)
        
        if not performances:
            return {
                'total_profit': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_daily_profit': 0,
                'best_day': None,
                'worst_day': None,
            }
        
        total_profit = sum(p.total_profit or 0 for p in performances)
        total_trades = sum(p.total_trades or 0 for p in performances)
        total_wins = sum(p.winning_trades or 0 for p in performances)
        
        best = max(performances, key=lambda p: p.total_profit or 0)
        worst = min(performances, key=lambda p: p.total_profit or 0)
        
        return {
            'total_profit': total_profit,
            'total_trades': total_trades,
            'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
            'avg_daily_profit': total_profit / len(performances),
            'best_day': {'date': best.date.isoformat(), 'profit': best.total_profit},
            'worst_day': {'date': worst.date.isoformat(), 'profit': worst.total_profit},
            'days_analyzed': len(performances),
        }
