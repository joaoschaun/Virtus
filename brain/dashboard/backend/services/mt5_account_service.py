"""
VIRTUS MT5 Account Service
===========================

Serviço completo para integração com conta MT5 real.
Métricas de conta, histórico de trades, depósitos, equity, etc.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Tenta importar MT5
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


class TradeType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"


class DealType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    BALANCE = "BALANCE"
    CREDIT = "CREDIT"
    CHARGE = "CHARGE"
    CORRECTION = "CORRECTION"
    BONUS = "BONUS"
    COMMISSION = "COMMISSION"
    COMMISSION_DAILY = "COMMISSION_DAILY"
    COMMISSION_MONTHLY = "COMMISSION_MONTHLY"
    COMMISSION_AGENT = "COMMISSION_AGENT"
    INTEREST = "INTEREST"
    CANCELED = "CANCELED"
    DIVIDEND = "DIVIDEND"
    DIVIDEND_FRANKED = "DIVIDEND_FRANKED"
    TAX = "TAX"


@dataclass
class AccountInfo:
    """Informações da conta MT5."""
    login: int
    name: str
    server: str
    currency: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float
    leverage: int
    trade_allowed: bool
    company: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TradeHistory:
    """Histórico de trade."""
    ticket: int
    order: int
    time: datetime
    type: str
    entry: str  # DEAL_ENTRY_IN, DEAL_ENTRY_OUT
    symbol: str
    volume: float
    price: float
    profit: float
    swap: float
    commission: float
    fee: float
    comment: str = ""
    magic: int = 0
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['time'] = self.time.isoformat()
        return d


@dataclass
class DepositWithdrawal:
    """Depósito ou saque."""
    ticket: int
    time: datetime
    type: str  # DEPOSIT, WITHDRAWAL
    amount: float
    comment: str
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['time'] = self.time.isoformat()
        return d


@dataclass 
class DailyStats:
    """Estatísticas diárias."""
    date: str
    trades: int
    profit: float
    volume: float
    win_rate: float
    wins: int
    losses: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AccountMetrics:
    """Métricas completas da conta."""
    # Conta
    balance: float
    equity: float
    margin: float
    free_margin: float
    profit: float
    
    # Totais
    total_deposits: float
    total_withdrawals: float
    total_trades: int
    total_profit: float
    total_volume: float
    
    # Médias
    avg_daily_profit: float
    avg_trade_profit: float
    avg_trade_volume: float
    avg_trade_duration_minutes: float
    
    # Win Rate
    wins: int
    losses: int
    win_rate: float
    
    # Drawdown
    max_drawdown: float
    max_drawdown_pct: float
    current_drawdown: float
    current_drawdown_pct: float
    
    # Risco
    profit_factor: float
    sharpe_ratio: float
    recovery_factor: float
    
    # Por período
    profit_today: float
    profit_week: float
    profit_month: float
    profit_year: float
    
    # Melhor/Pior
    best_trade: float
    worst_trade: float
    best_day: float
    worst_day: float
    
    # Sequências
    current_streak: int  # positivo = wins, negativo = losses
    max_win_streak: int
    max_loss_streak: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


class MT5AccountService:
    """Serviço de conta MT5."""
    
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path(__file__).parent.parent.parent.parent / "data" / "mt5_account"
        self.data_path.mkdir(parents=True, exist_ok=True)
        self._connected = False
        self._account_info: Optional[AccountInfo] = None
        
    @property
    def is_available(self) -> bool:
        """Verifica se MT5 está disponível."""
        return MT5_AVAILABLE
    
    @property
    def is_connected(self) -> bool:
        """Verifica se está conectado."""
        if not MT5_AVAILABLE:
            return False
        try:
            return mt5.terminal_info() is not None
        except:
            return False
    
    def connect(self, login: Optional[int] = None, password: Optional[str] = None, 
                server: Optional[str] = None) -> Tuple[bool, str]:
        """
        Conecta ao MT5.
        Se credenciais não fornecidas, usa as do ambiente ou tenta conexão automática.
        """
        if not MT5_AVAILABLE:
            return False, "MetaTrader5 não está instalado"
        
        # Tenta inicializar
        if not mt5.initialize():
            return False, f"Falha ao inicializar MT5: {mt5.last_error()}"
        
        # Se login fornecido, faz login explícito
        if login and password and server:
            authorized = mt5.login(login=login, password=password, server=server)
            if not authorized:
                mt5.shutdown()
                return False, f"Falha no login: {mt5.last_error()}"
        
        # Verifica conexão
        account = mt5.account_info()
        if account is None:
            mt5.shutdown()
            return False, "Nenhuma conta conectada no terminal MT5"
        
        self._connected = True
        self._account_info = self._parse_account_info(account)
        
        logger.info(f"Conectado à conta {account.login} @ {account.server}")
        return True, f"Conectado: {account.name} ({account.login})"
    
    def disconnect(self):
        """Desconecta do MT5."""
        if MT5_AVAILABLE:
            mt5.shutdown()
        self._connected = False
        self._account_info = None
    
    def _parse_account_info(self, account) -> AccountInfo:
        """Converte info da conta MT5."""
        return AccountInfo(
            login=account.login,
            name=account.name,
            server=account.server,
            currency=account.currency,
            balance=account.balance,
            equity=account.equity,
            margin=account.margin,
            free_margin=account.margin_free,
            margin_level=account.margin_level if account.margin_level else 0,
            profit=account.profit,
            leverage=account.leverage,
            trade_allowed=account.trade_allowed,
            company=account.company if hasattr(account, 'company') else ""
        )
    
    def get_account_info(self) -> Optional[AccountInfo]:
        """Retorna informações atuais da conta."""
        if not self.is_connected:
            return None
        
        account = mt5.account_info()
        if account is None:
            return None
        
        return self._parse_account_info(account)
    
    def get_deals_history(self, days: int = 365) -> List[TradeHistory]:
        """
        Obtém histórico de deals (trades fechados).
        
        Args:
            days: Quantidade de dias para buscar (padrão: 365)
        """
        if not self.is_connected:
            return []
        
        from_date = datetime.now() - timedelta(days=days)
        to_date = datetime.now() + timedelta(days=1)
        
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            return []
        
        history = []
        for deal in deals:
            # Mapear tipo do deal
            deal_type = self._map_deal_type(deal.type)
            
            # Mapear entrada
            entry_map = {0: "IN", 1: "OUT", 2: "INOUT", 3: "OUT_BY"}
            entry = entry_map.get(deal.entry, "UNKNOWN")
            
            trade = TradeHistory(
                ticket=deal.ticket,
                order=deal.order,
                time=datetime.fromtimestamp(deal.time),
                type=deal_type,
                entry=entry,
                symbol=deal.symbol,
                volume=deal.volume,
                price=deal.price,
                profit=deal.profit,
                swap=deal.swap,
                commission=deal.commission,
                fee=deal.fee if hasattr(deal, 'fee') else 0,
                comment=deal.comment,
                magic=deal.magic
            )
            history.append(trade)
        
        return history
    
    def _map_deal_type(self, deal_type: int) -> str:
        """Mapeia tipo de deal."""
        type_map = {
            0: "BUY",
            1: "SELL", 
            2: "BALANCE",
            3: "CREDIT",
            4: "CHARGE",
            5: "CORRECTION",
            6: "BONUS",
            7: "COMMISSION",
            8: "COMMISSION_DAILY",
            9: "COMMISSION_MONTHLY",
            10: "COMMISSION_AGENT",
            11: "INTEREST",
            12: "CANCELED",
            13: "DIVIDEND",
            14: "DIVIDEND_FRANKED",
            15: "TAX"
        }
        return type_map.get(deal_type, "UNKNOWN")
    
    def get_deposits_withdrawals(self, days: int = 365) -> List[DepositWithdrawal]:
        """
        Obtém histórico de depósitos e saques.
        """
        deals = self.get_deals_history(days)
        
        deposits_withdrawals = []
        for deal in deals:
            if deal.type == "BALANCE":
                op_type = "DEPOSIT" if deal.profit > 0 else "WITHDRAWAL"
                dw = DepositWithdrawal(
                    ticket=deal.ticket,
                    time=deal.time,
                    type=op_type,
                    amount=abs(deal.profit),
                    comment=deal.comment
                )
                deposits_withdrawals.append(dw)
        
        return deposits_withdrawals
    
    def get_trades_only(self, days: int = 365) -> List[TradeHistory]:
        """
        Obtém apenas trades (exclui balance, comissões, etc).
        """
        deals = self.get_deals_history(days)
        return [d for d in deals if d.type in ["BUY", "SELL"] and d.entry == "OUT"]
    
    def get_open_positions(self) -> List[Dict]:
        """Obtém posições abertas."""
        if not self.is_connected:
            return []
        
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        result = []
        for pos in positions:
            result.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == 0 else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'swap': pos.swap,
                'time': datetime.fromtimestamp(pos.time).isoformat(),
                'sl': pos.sl,
                'tp': pos.tp,
                'magic': pos.magic,
                'comment': pos.comment
            })
        
        return result
    
    def get_pending_orders(self) -> List[Dict]:
        """Obtém ordens pendentes."""
        if not self.is_connected:
            return []
        
        orders = mt5.orders_get()
        if orders is None:
            return []
        
        result = []
        for order in orders:
            order_types = {
                0: "BUY", 1: "SELL",
                2: "BUY_LIMIT", 3: "SELL_LIMIT",
                4: "BUY_STOP", 5: "SELL_STOP",
                6: "BUY_STOP_LIMIT", 7: "SELL_STOP_LIMIT"
            }
            result.append({
                'ticket': order.ticket,
                'symbol': order.symbol,
                'type': order_types.get(order.type, "UNKNOWN"),
                'volume': order.volume_current,
                'price_open': order.price_open,
                'price_current': order.price_current,
                'sl': order.sl,
                'tp': order.tp,
                'time': datetime.fromtimestamp(order.time_setup).isoformat(),
                'magic': order.magic,
                'comment': order.comment
            })
        
        return result
    
    def calculate_metrics(self, days: int = 365) -> AccountMetrics:
        """
        Calcula métricas completas da conta.
        """
        account = self.get_account_info()
        if account is None:
            raise ValueError("Não conectado ao MT5")
        
        # Buscar históricos
        all_deals = self.get_deals_history(days)
        trades = self.get_trades_only(days)
        deposits = self.get_deposits_withdrawals(days)
        
        # Totais de depósitos/saques
        total_deposits = sum(d.amount for d in deposits if d.type == "DEPOSIT")
        total_withdrawals = sum(d.amount for d in deposits if d.type == "WITHDRAWAL")
        
        # Estatísticas de trades
        total_trades = len(trades)
        total_profit = sum(t.profit + t.swap + t.commission for t in trades)
        total_volume = sum(t.volume for t in trades)
        
        # Wins/Losses
        wins = len([t for t in trades if t.profit > 0])
        losses = len([t for t in trades if t.profit < 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        # Médias
        avg_trade_profit = total_profit / total_trades if total_trades > 0 else 0
        avg_trade_volume = total_volume / total_trades if total_trades > 0 else 0
        
        # Lucro médio diário
        if trades:
            days_with_trades = len(set(t.time.date() for t in trades))
            avg_daily_profit = total_profit / days_with_trades if days_with_trades > 0 else 0
        else:
            avg_daily_profit = 0
        
        # Duração média dos trades (aproximado)
        avg_trade_duration_minutes = 0  # Precisa de dados adicionais
        
        # Drawdown (simplificado)
        max_drawdown, max_drawdown_pct = self._calculate_drawdown(trades, total_deposits)
        current_drawdown = max(0, total_deposits - account.balance)
        current_drawdown_pct = (current_drawdown / total_deposits * 100) if total_deposits > 0 else 0
        
        # Profit Factor
        gross_profit = sum(t.profit for t in trades if t.profit > 0)
        gross_loss = abs(sum(t.profit for t in trades if t.profit < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        # Sharpe Ratio (simplificado)
        sharpe_ratio = self._calculate_sharpe(trades)
        
        # Recovery Factor
        recovery_factor = total_profit / max_drawdown if max_drawdown > 0 else float('inf') if total_profit > 0 else 0
        
        # Lucros por período
        now = datetime.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)
        
        profit_today = sum(t.profit + t.swap + t.commission for t in trades if t.time.date() == today)
        profit_week = sum(t.profit + t.swap + t.commission for t in trades if t.time.date() >= week_ago)
        profit_month = sum(t.profit + t.swap + t.commission for t in trades if t.time.date() >= month_ago)
        profit_year = sum(t.profit + t.swap + t.commission for t in trades if t.time.date() >= year_ago)
        
        # Melhor/Pior trade
        trade_profits = [t.profit for t in trades]
        best_trade = max(trade_profits) if trade_profits else 0
        worst_trade = min(trade_profits) if trade_profits else 0
        
        # Melhor/Pior dia
        daily_profits = self._calculate_daily_profits(trades)
        best_day = max(daily_profits.values()) if daily_profits else 0
        worst_day = min(daily_profits.values()) if daily_profits else 0
        
        # Sequências (streaks)
        current_streak, max_win_streak, max_loss_streak = self._calculate_streaks(trades)
        
        return AccountMetrics(
            balance=account.balance,
            equity=account.equity,
            margin=account.margin,
            free_margin=account.free_margin,
            profit=account.profit,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            total_trades=total_trades,
            total_profit=total_profit,
            total_volume=total_volume,
            avg_daily_profit=avg_daily_profit,
            avg_trade_profit=avg_trade_profit,
            avg_trade_volume=avg_trade_volume,
            avg_trade_duration_minutes=avg_trade_duration_minutes,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            current_drawdown=current_drawdown,
            current_drawdown_pct=current_drawdown_pct,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            recovery_factor=recovery_factor,
            profit_today=profit_today,
            profit_week=profit_week,
            profit_month=profit_month,
            profit_year=profit_year,
            best_trade=best_trade,
            worst_trade=worst_trade,
            best_day=best_day,
            worst_day=worst_day,
            current_streak=current_streak,
            max_win_streak=max_win_streak,
            max_loss_streak=max_loss_streak
        )
    
    def _calculate_drawdown(self, trades: List[TradeHistory], initial_balance: float) -> Tuple[float, float]:
        """Calcula drawdown máximo."""
        if not trades:
            return 0, 0
        
        # Ordenar por tempo
        sorted_trades = sorted(trades, key=lambda t: t.time)
        
        balance = initial_balance
        peak = initial_balance
        max_drawdown = 0
        max_drawdown_pct = 0
        
        for trade in sorted_trades:
            balance += trade.profit + trade.swap + trade.commission
            peak = max(peak, balance)
            drawdown = peak - balance
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        return max_drawdown, max_drawdown_pct
    
    def _calculate_sharpe(self, trades: List[TradeHistory], risk_free_rate: float = 0) -> float:
        """Calcula Sharpe Ratio simplificado."""
        if len(trades) < 2:
            return 0
        
        profits = [t.profit for t in trades]
        avg_profit = sum(profits) / len(profits)
        
        # Desvio padrão
        variance = sum((p - avg_profit) ** 2 for p in profits) / len(profits)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0
        
        return (avg_profit - risk_free_rate) / std_dev
    
    def _calculate_daily_profits(self, trades: List[TradeHistory]) -> Dict[str, float]:
        """Calcula lucro por dia."""
        daily = {}
        for trade in trades:
            date_str = trade.time.strftime("%Y-%m-%d")
            if date_str not in daily:
                daily[date_str] = 0
            daily[date_str] += trade.profit + trade.swap + trade.commission
        return daily
    
    def _calculate_streaks(self, trades: List[TradeHistory]) -> Tuple[int, int, int]:
        """Calcula sequências de wins/losses."""
        if not trades:
            return 0, 0, 0
        
        sorted_trades = sorted(trades, key=lambda t: t.time)
        
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        win_streak = 0
        loss_streak = 0
        
        for trade in sorted_trades:
            if trade.profit > 0:
                win_streak += 1
                loss_streak = 0
                max_win_streak = max(max_win_streak, win_streak)
            elif trade.profit < 0:
                loss_streak += 1
                win_streak = 0
                max_loss_streak = max(max_loss_streak, loss_streak)
            else:
                # Breakeven, não afeta streak
                pass
        
        # Current streak
        if win_streak > 0:
            current_streak = win_streak
        elif loss_streak > 0:
            current_streak = -loss_streak
        
        return current_streak, max_win_streak, max_loss_streak
    
    def get_daily_stats(self, days: int = 30) -> List[DailyStats]:
        """Obtém estatísticas diárias."""
        trades = self.get_trades_only(days)
        daily_profits = self._calculate_daily_profits(trades)
        
        stats = []
        for date_str, profit in sorted(daily_profits.items()):
            day_trades = [t for t in trades if t.time.strftime("%Y-%m-%d") == date_str]
            day_wins = len([t for t in day_trades if t.profit > 0])
            day_losses = len([t for t in day_trades if t.profit < 0])
            day_volume = sum(t.volume for t in day_trades)
            
            stats.append(DailyStats(
                date=date_str,
                trades=len(day_trades),
                profit=profit,
                volume=day_volume,
                win_rate=(day_wins / len(day_trades) * 100) if day_trades else 0,
                wins=day_wins,
                losses=day_losses
            ))
        
        return stats
    
    def get_symbol_stats(self, days: int = 365) -> Dict[str, Dict]:
        """Obtém estatísticas por símbolo."""
        trades = self.get_trades_only(days)
        
        symbols = {}
        for trade in trades:
            if trade.symbol not in symbols:
                symbols[trade.symbol] = {
                    'trades': 0,
                    'profit': 0,
                    'volume': 0,
                    'wins': 0,
                    'losses': 0
                }
            
            s = symbols[trade.symbol]
            s['trades'] += 1
            s['profit'] += trade.profit + trade.swap + trade.commission
            s['volume'] += trade.volume
            if trade.profit > 0:
                s['wins'] += 1
            elif trade.profit < 0:
                s['losses'] += 1
        
        # Calcular win rate
        for symbol, data in symbols.items():
            data['win_rate'] = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0
            data['avg_profit'] = data['profit'] / data['trades'] if data['trades'] > 0 else 0
        
        return symbols
    
    def export_to_json(self, filepath: Optional[Path] = None) -> str:
        """Exporta todos os dados para JSON."""
        if filepath is None:
            filepath = self.data_path / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        account = self.get_account_info()
        metrics = self.calculate_metrics()
        trades = self.get_trades_only()
        deposits = self.get_deposits_withdrawals()
        positions = self.get_open_positions()
        orders = self.get_pending_orders()
        daily_stats = self.get_daily_stats(30)
        symbol_stats = self.get_symbol_stats()
        
        data = {
            'export_date': datetime.now().isoformat(),
            'account': account.to_dict() if account else None,
            'metrics': metrics.to_dict(),
            'positions': positions,
            'pending_orders': orders,
            'trades_count': len(trades),
            'trades': [t.to_dict() for t in trades[-100:]],  # Últimos 100
            'deposits_withdrawals': [d.to_dict() for d in deposits],
            'daily_stats': [s.to_dict() for s in daily_stats],
            'symbol_stats': symbol_stats
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)


# Singleton
_mt5_service: Optional[MT5AccountService] = None

def get_mt5_account_service() -> MT5AccountService:
    """Obtém instância do serviço."""
    global _mt5_service
    if _mt5_service is None:
        _mt5_service = MT5AccountService()
    return _mt5_service
