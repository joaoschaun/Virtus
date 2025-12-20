"""
MT4 Account Service - Integração com conta real MetaTrader 4

Para usar esta integração, você precisa:
1. Instalar o Expert Advisor (EA) DWX_ZeroMQ_Server no MT4
2. Configurar as portas no EA (padrão: PUSH=32768, PULL=32769, PUB=32770)
3. O EA criará um servidor ZeroMQ que este serviço conectará

Alternativa: Se a Pepperstone oferecer API REST, podemos usar diretamente.
"""

import json
import time
import sqlite3
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path
import threading


@dataclass
class MT4AccountInfo:
    """Informações da conta MT4"""
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
    company: str = ""
    trade_allowed: bool = True


@dataclass
class MT4Trade:
    """Trade do histórico MT4"""
    ticket: int
    symbol: str
    type: str  # BUY, SELL
    volume: float
    open_price: float
    close_price: float
    open_time: str
    close_time: str
    profit: float
    swap: float
    commission: float
    sl: float = 0
    tp: float = 0
    comment: str = ""


@dataclass
class MT4Position:
    """Posição aberta MT4"""
    ticket: int
    symbol: str
    type: str
    volume: float
    open_price: float
    current_price: float
    open_time: str
    profit: float
    swap: float
    sl: float = 0
    tp: float = 0
    comment: str = ""


@dataclass
class MT4Metrics:
    """Métricas calculadas"""
    balance: float = 0
    equity: float = 0
    profit: float = 0
    total_deposits: float = 0
    total_withdrawals: float = 0
    total_trades: int = 0
    total_profit: float = 0  # Lucro dos trades sincronizados
    real_profit: float = 0   # Lucro real = saldo - depósitos + saques
    total_volume: float = 0
    avg_daily_profit: float = 0
    avg_trade_profit: float = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0
    max_drawdown: float = 0
    max_drawdown_pct: float = 0
    current_drawdown: float = 0
    current_drawdown_pct: float = 0
    profit_factor: float = 0
    sharpe_ratio: float = 0
    recovery_factor: float = 0
    profit_today: float = 0
    profit_week: float = 0
    profit_month: float = 0
    profit_year: float = 0
    best_trade: float = 0
    worst_trade: float = 0
    best_day: float = 0
    worst_day: float = 0
    current_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0


class MT4ZeroMQConnector:
    """
    Conector ZeroMQ para MT4.
    Requer o EA DWX_ZeroMQ_Server instalado no MT4.
    """
    
    def __init__(self, push_port: int = 32768, pull_port: int = 32769, pub_port: int = 32770):
        self.push_port = push_port
        self.pull_port = pull_port
        self.pub_port = pub_port
        self.connected = False
        self.context = None
        self.push_socket = None
        self.pull_socket = None
        self._zmq_available = False
        
        try:
            import zmq
            self._zmq_available = True
            self.zmq = zmq
        except ImportError:
            print("⚠️ ZeroMQ não instalado. Execute: pip install pyzmq")
    
    def connect(self, host: str = "localhost") -> bool:
        """Conecta ao servidor ZeroMQ do MT4"""
        if not self._zmq_available:
            return False
            
        try:
            self.context = self.zmq.Context()
            
            # Socket PUSH para enviar comandos
            self.push_socket = self.context.socket(self.zmq.PUSH)
            self.push_socket.connect(f"tcp://{host}:{self.push_port}")
            
            # Socket PULL para receber respostas
            self.pull_socket = self.context.socket(self.zmq.PULL)
            self.pull_socket.connect(f"tcp://{host}:{self.pull_port}")
            self.pull_socket.setsockopt(self.zmq.RCVTIMEO, 5000)  # 5s timeout
            
            self.connected = True
            return True
        except Exception as e:
            print(f"Erro ao conectar ZeroMQ: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do servidor"""
        if self.push_socket:
            self.push_socket.close()
        if self.pull_socket:
            self.pull_socket.close()
        if self.context:
            self.context.term()
        self.connected = False
    
    def send_command(self, command: dict) -> Optional[dict]:
        """Envia comando e aguarda resposta"""
        if not self.connected:
            return None
            
        try:
            self.push_socket.send_json(command)
            response = self.pull_socket.recv_json()
            return response
        except Exception as e:
            print(f"Erro ao enviar comando: {e}")
            return None
    
    def get_account_info(self) -> Optional[dict]:
        """Obtém informações da conta"""
        return self.send_command({"action": "GET_ACCOUNT_INFO"})
    
    def get_open_trades(self) -> Optional[dict]:
        """Obtém trades abertos"""
        return self.send_command({"action": "GET_OPEN_TRADES"})
    
    def get_historical_trades(self) -> Optional[dict]:
        """Obtém histórico de trades"""
        return self.send_command({"action": "GET_HISTORICAL_TRADES"})


class MT4AccountService:
    """
    Serviço principal para gerenciar dados da conta MT4.
    
    Suporta múltiplos modos de operação:
    1. ZeroMQ: Conexão direta com MT4 via EA
    2. Manual: Importação de dados via arquivo CSV/JSON exportado do MT4
    3. Database: Armazenamento local para histórico
    """
    
    def __init__(self, db_path: str = None):
        self.zmq_connector = MT4ZeroMQConnector()
        self.connected = False
        self.account_info: Optional[MT4AccountInfo] = None
        self._mode = "manual"  # zmq, manual, api
        
        # Database para armazenar dados importados
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), 
                "..", "data", "mt4_account.db"
            )
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Inicializa o banco de dados SQLite"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de informações da conta
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_info (
                id INTEGER PRIMARY KEY,
                login INTEGER,
                name TEXT,
                server TEXT,
                currency TEXT,
                balance REAL,
                equity REAL,
                leverage INTEGER,
                company TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                ticket INTEGER PRIMARY KEY,
                symbol TEXT,
                type TEXT,
                volume REAL,
                open_price REAL,
                close_price REAL,
                open_time TIMESTAMP,
                close_time TIMESTAMP,
                profit REAL,
                swap REAL,
                commission REAL,
                sl REAL,
                tp REAL,
                comment TEXT
            )
        """)
        
        # Tabela de depósitos/saques
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deposits_withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                amount REAL,
                date TIMESTAMP,
                comment TEXT
            )
        """)
        
        # Tabela de snapshots de equity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                balance REAL,
                equity REAL,
                profit REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def connect_zmq(self, host: str = "localhost") -> bool:
        """Conecta via ZeroMQ ao MT4"""
        if self.zmq_connector.connect(host):
            self._mode = "zmq"
            self.connected = True
            return True
        return False
    
    def disconnect(self):
        """Desconecta"""
        if self._mode == "zmq":
            self.zmq_connector.disconnect()
        self.connected = False
    
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self.connected or self._mode == "manual"
    
    def set_account_info(self, info: dict):
        """Define informações da conta manualmente"""
        self.account_info = MT4AccountInfo(
            login=info.get("login", 0),
            name=info.get("name", ""),
            server=info.get("server", ""),
            currency=info.get("currency", "USD"),
            balance=info.get("balance", 0),
            equity=info.get("equity", 0),
            margin=info.get("margin", 0),
            free_margin=info.get("free_margin", 0),
            margin_level=info.get("margin_level", 0),
            profit=info.get("profit", 0),
            leverage=info.get("leverage", 100),
            company=info.get("company", ""),
            trade_allowed=info.get("trade_allowed", True)
        )
        self._save_account_info()
        self._mode = "manual"
        self.connected = True
    
    def _save_account_info(self):
        """Salva informações da conta no banco"""
        if not self.account_info:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM account_info")
        cursor.execute("""
            INSERT INTO account_info (login, name, server, currency, balance, equity, leverage, company)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.account_info.login,
            self.account_info.name,
            self.account_info.server,
            self.account_info.currency,
            self.account_info.balance,
            self.account_info.equity,
            self.account_info.leverage,
            self.account_info.company
        ))
        
        conn.commit()
        conn.close()
    
    def _load_account_info(self) -> Optional[MT4AccountInfo]:
        """Carrega informações da conta do banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM account_info LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return MT4AccountInfo(
                login=row[1],
                name=row[2],
                server=row[3],
                currency=row[4],
                balance=row[5],
                equity=row[6],
                margin=0,
                free_margin=0,
                margin_level=0,
                profit=0,
                leverage=row[7],
                company=row[8]
            )
        return None
    
    def get_account_info(self) -> Optional[MT4AccountInfo]:
        """Obtém informações da conta"""
        if self._mode == "zmq" and self.connected:
            data = self.zmq_connector.get_account_info()
            if data:
                self.set_account_info(data)
        
        if not self.account_info:
            self.account_info = self._load_account_info()
        
        return self.account_info
    
    def import_trades_from_csv(self, csv_path: str) -> int:
        """
        Importa trades de um arquivo CSV exportado do MT4.
        
        Formato esperado do CSV (exportado do MT4 Account History):
        Ticket,Open Time,Type,Size,Item,Price,S/L,T/P,Close Time,Price,Commission,Taxes,Swap,Profit
        """
        import csv
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        count = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        # Adaptar campos do CSV do MT4
                        ticket = int(row.get('Ticket', row.get('ticket', 0)))
                        if ticket == 0:
                            continue
                        
                        trade_type = row.get('Type', row.get('type', '')).upper()
                        if trade_type in ['BALANCE', 'CREDIT']:
                            # É um depósito/saque
                            amount = float(row.get('Profit', row.get('profit', 0)))
                            cursor.execute("""
                                INSERT OR REPLACE INTO deposits_withdrawals (type, amount, date, comment)
                                VALUES (?, ?, ?, ?)
                            """, (
                                'deposit' if amount > 0 else 'withdrawal',
                                abs(amount),
                                row.get('Close Time', row.get('close_time', '')),
                                row.get('Item', row.get('symbol', ''))
                            ))
                            continue
                        
                        if trade_type not in ['BUY', 'SELL']:
                            continue
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO trades 
                            (ticket, symbol, type, volume, open_price, close_price, 
                             open_time, close_time, profit, swap, commission, sl, tp, comment)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            ticket,
                            row.get('Item', row.get('symbol', '')),
                            trade_type,
                            float(row.get('Size', row.get('volume', 0))),
                            float(row.get('Price', row.get('open_price', 0))),
                            float(row.get('Price.1', row.get('close_price', 0))),
                            row.get('Open Time', row.get('open_time', '')),
                            row.get('Close Time', row.get('close_time', '')),
                            float(row.get('Profit', row.get('profit', 0))),
                            float(row.get('Swap', row.get('swap', 0))),
                            float(row.get('Commission', row.get('commission', 0))),
                            float(row.get('S/L', row.get('sl', 0))),
                            float(row.get('T/P', row.get('tp', 0))),
                            row.get('Comment', row.get('comment', ''))
                        ))
                        count += 1
                        
                    except (ValueError, KeyError) as e:
                        print(f"Erro ao processar linha: {e}")
                        continue
            
            conn.commit()
        except Exception as e:
            print(f"Erro ao importar CSV: {e}")
        finally:
            conn.close()
        
        return count
    
    def import_trades_from_json(self, json_data: List[dict]) -> int:
        """Importa trades de dados JSON"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        count = 0
        
        for trade in json_data:
            try:
                trade_type = trade.get('type', '').upper()
                
                if trade_type in ['BALANCE', 'DEPOSIT', 'WITHDRAWAL']:
                    amount = float(trade.get('profit', trade.get('amount', 0)))
                    cursor.execute("""
                        INSERT INTO deposits_withdrawals (type, amount, date, comment)
                        VALUES (?, ?, ?, ?)
                    """, (
                        'deposit' if amount > 0 else 'withdrawal',
                        abs(amount),
                        trade.get('close_time', trade.get('date', '')),
                        trade.get('comment', '')
                    ))
                    continue
                
                if trade_type not in ['BUY', 'SELL']:
                    continue
                
                cursor.execute("""
                    INSERT OR REPLACE INTO trades 
                    (ticket, symbol, type, volume, open_price, close_price, 
                     open_time, close_time, profit, swap, commission, sl, tp, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(trade.get('ticket', 0)),
                    trade.get('symbol', ''),
                    trade_type,
                    float(trade.get('volume', trade.get('lots', 0))),
                    float(trade.get('open_price', 0)),
                    float(trade.get('close_price', 0)),
                    trade.get('open_time', ''),
                    trade.get('close_time', ''),
                    float(trade.get('profit', 0)),
                    float(trade.get('swap', 0)),
                    float(trade.get('commission', 0)),
                    float(trade.get('sl', 0)),
                    float(trade.get('tp', 0)),
                    trade.get('comment', '')
                ))
                count += 1
                
            except (ValueError, KeyError) as e:
                print(f"Erro ao processar trade: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return count
    
    def add_deposit(self, amount: float, date: str = None, comment: str = ""):
        """Adiciona um depósito manualmente"""
        if date is None:
            date = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO deposits_withdrawals (type, amount, date, comment)
            VALUES ('deposit', ?, ?, ?)
        """, (amount, date, comment))
        conn.commit()
        conn.close()
    
    def add_withdrawal(self, amount: float, date: str = None, comment: str = ""):
        """Adiciona um saque manualmente"""
        if date is None:
            date = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO deposits_withdrawals (type, amount, date, comment)
            VALUES ('withdrawal', ?, ?, ?)
        """, (amount, date, comment))
        conn.commit()
        conn.close()
    
    def get_trades(self, days: int = 30) -> List[MT4Trade]:
        """Obtém histórico de trades"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if days > 0:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute("""
                SELECT * FROM trades WHERE close_time >= ? ORDER BY close_time DESC
            """, (start_date,))
        else:
            cursor.execute("SELECT * FROM trades ORDER BY close_time DESC")
        
        rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trades.append(MT4Trade(
                ticket=row[0],
                symbol=row[1],
                type=row[2],
                volume=row[3],
                open_price=row[4],
                close_price=row[5],
                open_time=row[6],
                close_time=row[7],
                profit=row[8],
                swap=row[9],
                commission=row[10],
                sl=row[11],
                tp=row[12],
                comment=row[13]
            ))
        
        return trades
    
    def get_deposits_withdrawals(self) -> dict:
        """Obtém depósitos e saques"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM deposits_withdrawals ORDER BY date DESC")
        rows = cursor.fetchall()
        
        cursor.execute("SELECT SUM(amount) FROM deposits_withdrawals WHERE type = 'deposit'")
        total_deposits = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(amount) FROM deposits_withdrawals WHERE type = 'withdrawal'")
        total_withdrawals = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "deposits": [{"amount": r[2], "date": r[3], "comment": r[4]} for r in rows if r[1] == 'deposit'],
            "withdrawals": [{"amount": r[2], "date": r[3], "comment": r[4]} for r in rows if r[1] == 'withdrawal'],
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "net": total_deposits - total_withdrawals
        }
    
    def calculate_metrics(self, days: int = 30) -> MT4Metrics:
        """Calcula métricas completas"""
        trades = self.get_trades(days if days > 0 else 0)
        deposits = self.get_deposits_withdrawals()
        account = self.get_account_info()
        
        metrics = MT4Metrics()
        
        if account:
            metrics.balance = account.balance
            metrics.equity = account.equity
            metrics.profit = account.profit
        
        metrics.total_deposits = deposits["total_deposits"]
        metrics.total_withdrawals = deposits["total_withdrawals"]
        metrics.total_trades = len(trades)
        
        # Calcular lucro real: saldo - depósitos + saques
        if metrics.balance > 0 and metrics.total_deposits > 0:
            metrics.real_profit = metrics.balance - metrics.total_deposits + metrics.total_withdrawals
        
        if not trades:
            return metrics
        
        # Calcular lucros
        profits = [t.profit + t.swap + t.commission for t in trades]
        metrics.total_profit = sum(profits)
        metrics.total_volume = sum(t.volume for t in trades)
        
        # Wins e Losses
        metrics.wins = sum(1 for p in profits if p > 0)
        metrics.losses = sum(1 for p in profits if p < 0)
        
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.wins / metrics.total_trades) * 100
            metrics.avg_trade_profit = metrics.total_profit / metrics.total_trades
        
        # Melhor e pior trade
        if profits:
            metrics.best_trade = max(profits)
            metrics.worst_trade = min(profits)
        
        # Profit Factor
        gross_profit = sum(p for p in profits if p > 0)
        gross_loss = abs(sum(p for p in profits if p < 0))
        if gross_loss > 0:
            metrics.profit_factor = gross_profit / gross_loss
        
        # Lucro por período
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        year_start = today_start.replace(month=1, day=1)
        
        for trade in trades:
            try:
                # Formato MT4: "2025.12.19 19:42" -> converter para datetime
                close_time_str = trade.close_time.replace('.', '-').replace(' ', 'T')
                # Se não tiver segundos, adicionar
                if close_time_str.count(':') == 1:
                    close_time_str += ':00'
                close_time = datetime.fromisoformat(close_time_str)
                profit = trade.profit + trade.swap + trade.commission
                
                if close_time >= today_start:
                    metrics.profit_today += profit
                if close_time >= week_start:
                    metrics.profit_week += profit
                if close_time >= month_start:
                    metrics.profit_month += profit
                if close_time >= year_start:
                    metrics.profit_year += profit
            except Exception as e:
                # Fallback: tentar outro formato
                try:
                    close_time = datetime.strptime(trade.close_time, "%Y.%m.%d %H:%M")
                    profit = trade.profit + trade.swap + trade.commission
                    
                    if close_time >= today_start:
                        metrics.profit_today += profit
                    if close_time >= week_start:
                        metrics.profit_week += profit
                    if close_time >= month_start:
                        metrics.profit_month += profit
                    if close_time >= year_start:
                        metrics.profit_year += profit
                except:
                    pass
        
        # Lucro diário médio
        daily_profits = {}
        for trade in trades:
            try:
                date = trade.close_time.split(' ')[0].split('T')[0]
                profit = trade.profit + trade.swap + trade.commission
                daily_profits[date] = daily_profits.get(date, 0) + profit
            except:
                pass
        
        if daily_profits:
            values = list(daily_profits.values())
            metrics.avg_daily_profit = sum(values) / len(values)
            metrics.best_day = max(values)
            metrics.worst_day = min(values)
        
        # Drawdown - calcular baseado no equity histórico
        # Se não tiver depósitos registrados, estimar saldo inicial
        initial_balance = metrics.total_deposits if metrics.total_deposits > 0 else (metrics.balance - metrics.total_profit)
        
        if initial_balance > 0 or metrics.balance > 0:
            # Usar o maior valor como base
            base_balance = max(initial_balance, 1)  # Evitar divisão por zero
            peak = base_balance
            max_dd = 0
            running_pnl = 0
            
            # Ordenar trades por data de fechamento (mais antigo primeiro)
            sorted_trades = sorted(trades, key=lambda t: t.close_time)
            
            for trade in sorted_trades:
                profit = trade.profit + trade.swap + trade.commission
                running_pnl += profit
                current_equity = base_balance + running_pnl
                
                if current_equity > peak:
                    peak = current_equity
                
                dd = peak - current_equity
                if dd > max_dd:
                    max_dd = dd
            
            metrics.max_drawdown = max_dd
            if peak > 0:
                metrics.max_drawdown_pct = (max_dd / peak) * 100
            
            # Current drawdown
            if account and account.equity > 0:
                peak_equity = max(base_balance + metrics.total_profit, account.equity)
                metrics.current_drawdown = max(0, peak_equity - account.equity)
                metrics.current_drawdown_pct = (metrics.current_drawdown / peak_equity) * 100 if peak_equity > 0 else 0
        
        # Recovery Factor
        if metrics.max_drawdown > 0:
            metrics.recovery_factor = metrics.total_profit / metrics.max_drawdown
        
        # Sharpe Ratio simplificado
        if profits and len(profits) > 1:
            import statistics
            try:
                mean_return = statistics.mean(profits)
                std_return = statistics.stdev(profits)
                if std_return > 0:
                    metrics.sharpe_ratio = mean_return / std_return
            except:
                pass
        
        # Streaks
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        win_streak = 0
        loss_streak = 0
        
        for profit in profits:
            if profit > 0:
                win_streak += 1
                loss_streak = 0
                max_win_streak = max(max_win_streak, win_streak)
            elif profit < 0:
                loss_streak += 1
                win_streak = 0
                max_loss_streak = max(max_loss_streak, loss_streak)
        
        # Current streak
        if profits:
            if profits[0] > 0:
                for p in profits:
                    if p > 0:
                        current_streak += 1
                    else:
                        break
            elif profits[0] < 0:
                for p in profits:
                    if p < 0:
                        current_streak -= 1
                    else:
                        break
        
        metrics.current_streak = current_streak
        metrics.max_win_streak = max_win_streak
        metrics.max_loss_streak = max_loss_streak
        
        return metrics
    
    def get_daily_stats(self, days: int = 30) -> List[dict]:
        """Obtém estatísticas diárias"""
        trades = self.get_trades(days)
        
        daily_stats = {}
        for trade in trades:
            try:
                date = trade.close_time.split(' ')[0].split('T')[0]
                if date not in daily_stats:
                    daily_stats[date] = {
                        "date": date,
                        "trades": 0,
                        "profit": 0,
                        "volume": 0,
                        "wins": 0,
                        "losses": 0
                    }
                
                profit = trade.profit + trade.swap + trade.commission
                daily_stats[date]["trades"] += 1
                daily_stats[date]["profit"] += profit
                daily_stats[date]["volume"] += trade.volume
                
                if profit > 0:
                    daily_stats[date]["wins"] += 1
                elif profit < 0:
                    daily_stats[date]["losses"] += 1
            except:
                pass
        
        # Calcular win rate
        for stats in daily_stats.values():
            total = stats["wins"] + stats["losses"]
            stats["win_rate"] = (stats["wins"] / total * 100) if total > 0 else 0
        
        return sorted(daily_stats.values(), key=lambda x: x["date"], reverse=True)
    
    def get_symbol_stats(self) -> Dict[str, dict]:
        """Obtém estatísticas por símbolo"""
        trades = self.get_trades(0)  # Todos os trades
        
        symbol_stats = {}
        for trade in trades:
            symbol = trade.symbol
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    "trades": 0,
                    "profit": 0,
                    "volume": 0,
                    "wins": 0,
                    "losses": 0
                }
            
            profit = trade.profit + trade.swap + trade.commission
            symbol_stats[symbol]["trades"] += 1
            symbol_stats[symbol]["profit"] += profit
            symbol_stats[symbol]["volume"] += trade.volume
            
            if profit > 0:
                symbol_stats[symbol]["wins"] += 1
            elif profit < 0:
                symbol_stats[symbol]["losses"] += 1
        
        # Calcular win rate e média
        for symbol, stats in symbol_stats.items():
            total = stats["wins"] + stats["losses"]
            stats["win_rate"] = (stats["wins"] / total * 100) if total > 0 else 0
            stats["avg_profit"] = stats["profit"] / stats["trades"] if stats["trades"] > 0 else 0
        
        # Ordenar por lucro
        return dict(sorted(symbol_stats.items(), key=lambda x: x[1]["profit"], reverse=True))
    
    def update_balance(self, balance: float, equity: float = None):
        """Atualiza o saldo manualmente"""
        if equity is None:
            equity = balance
        
        if self.account_info:
            self.account_info.balance = balance
            self.account_info.equity = equity
            self._save_account_info()
        
        # Salvar snapshot
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO equity_snapshots (balance, equity, profit)
            VALUES (?, ?, ?)
        """, (balance, equity, equity - balance))
        conn.commit()
        conn.close()
    
    def get_equity_history(self, days: int = 30) -> List[dict]:
        """Obtém histórico de equity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT balance, equity, profit, timestamp 
            FROM equity_snapshots 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (start_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {"balance": r[0], "equity": r[1], "profit": r[2], "timestamp": r[3]}
            for r in rows
        ]
    
    def export_to_json(self, filepath: str = None) -> dict:
        """Exporta todos os dados para JSON"""
        data = {
            "exported_at": datetime.now().isoformat(),
            "account": asdict(self.get_account_info()) if self.get_account_info() else None,
            "metrics": asdict(self.calculate_metrics(0)),
            "deposits_withdrawals": self.get_deposits_withdrawals(),
            "daily_stats": self.get_daily_stats(0),
            "symbol_stats": self.get_symbol_stats(),
            "trades": [asdict(t) for t in self.get_trades(0)]
        }
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        return data
    
    def get_summary(self) -> dict:
        """Obtém um resumo completo da conta"""
        account = self.get_account_info()
        metrics = self.calculate_metrics(30)
        deposits = self.get_deposits_withdrawals()
        daily = self.get_daily_stats(7)
        symbols = self.get_symbol_stats()
        
        # Top 5 símbolos
        top_symbols = dict(list(symbols.items())[:5])
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "account": asdict(account) if account else None,
            "metrics": asdict(metrics),
            "deposits_withdrawals": {
                "total_deposits": deposits["total_deposits"],
                "total_withdrawals": deposits["total_withdrawals"],
                "net": deposits["net"]
            },
            "daily_performance": {
                "count": len(daily),
                "data": daily
            },
            "symbols": {
                "count": len(symbols),
                "top_5": top_symbols
            }
        }


# Instância global
_mt4_service: Optional[MT4AccountService] = None

def get_mt4_service() -> MT4AccountService:
    """Obtém a instância do serviço MT4"""
    global _mt4_service
    if _mt4_service is None:
        _mt4_service = MT4AccountService()
    return _mt4_service
