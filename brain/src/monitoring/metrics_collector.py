"""
VIRTUS Metrics Collector
=========================

Coleta de métricas em tempo real:
- Performance de trading (P&L, trades, win rate)
- Métricas de sistema (CPU, memória, latência)
- Métricas por bot/estratégia
- Histórico para análise
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import statistics

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger


class MetricType(Enum):
    """Tipos de métricas."""
    COUNTER = "counter"      # Sempre incrementa
    GAUGE = "gauge"          # Valor atual
    HISTOGRAM = "histogram"  # Distribuição de valores
    SUMMARY = "summary"      # Percentis


@dataclass
class Metric:
    """Uma métrica individual."""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class MetricSeries:
    """Série temporal de uma métrica."""
    name: str
    type: MetricType
    values: List[tuple] = field(default_factory=list)  # (timestamp, value)
    labels: Dict[str, str] = field(default_factory=dict)
    max_size: int = 1000
    
    def add(self, value: float, timestamp: datetime = None):
        """Adiciona valor à série."""
        ts = timestamp or datetime.now()
        self.values.append((ts, value))
        
        # Manter tamanho máximo
        if len(self.values) > self.max_size:
            self.values = self.values[-self.max_size:]
    
    def get_latest(self) -> Optional[float]:
        """Retorna último valor."""
        return self.values[-1][1] if self.values else None
    
    def get_average(self, minutes: int = 5) -> Optional[float]:
        """Retorna média dos últimos N minutos."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent = [v for ts, v in self.values if ts > cutoff]
        return statistics.mean(recent) if recent else None
    
    def get_percentile(self, p: float, minutes: int = 60) -> Optional[float]:
        """Retorna percentil dos últimos N minutos."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent = sorted([v for ts, v in self.values if ts > cutoff])
        if not recent:
            return None
        idx = int(len(recent) * p / 100)
        return recent[min(idx, len(recent) - 1)]


@dataclass 
class TradingMetrics:
    """Métricas de trading consolidadas."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_volume: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    peak_balance: float = 0.0
    win_streak: int = 0
    lose_streak: int = 0
    current_streak: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    profit_factor: float = 0.0
    
    @property
    def win_rate(self) -> float:
        """Calcula win rate."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100


class MetricsCollector:
    """
    Coletor central de métricas do VIRTUS.
    
    Coleta métricas de:
    - Performance de trading
    - Sistema (CPU, memória)
    - Latência de operações
    - Métricas por bot/estratégia
    """
    
    def __init__(self, retention_hours: int = 24):
        self.logger = VirtusLogger.get_logger("MetricsCollector")
        self.retention_hours = retention_hours
        
        # Armazenamento de métricas
        self._metrics: Dict[str, MetricSeries] = {}
        self._trading_metrics: Dict[str, TradingMetrics] = {}  # por bot
        self._global_trading = TradingMetrics()
        
        # Callbacks para alertas
        self._alert_callbacks: List[Callable] = []
        
        # Thresholds de alerta
        self._thresholds = {
            'max_drawdown': 10.0,      # %
            'lose_streak': 5,
            'cpu_usage': 90.0,         # %
            'memory_usage': 85.0,      # %
            'latency_ms': 1000,
        }
        
        # Task de coleta
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Inicializar métricas base
        self._init_base_metrics()
        
        self.logger.info("MetricsCollector inicializado")
    
    def _init_base_metrics(self):
        """Inicializa métricas base do sistema."""
        base_metrics = [
            ("system_cpu_percent", MetricType.GAUGE, "Uso de CPU (%)"),
            ("system_memory_percent", MetricType.GAUGE, "Uso de memória (%)"),
            ("system_disk_percent", MetricType.GAUGE, "Uso de disco (%)"),
            ("trading_latency_ms", MetricType.HISTOGRAM, "Latência de trading (ms)"),
            ("mt5_connection_status", MetricType.GAUGE, "Status conexão MT5"),
            ("active_positions", MetricType.GAUGE, "Posições abertas"),
            ("pending_orders", MetricType.GAUGE, "Ordens pendentes"),
            ("balance", MetricType.GAUGE, "Saldo da conta"),
            ("equity", MetricType.GAUGE, "Patrimônio"),
            ("margin_level", MetricType.GAUGE, "Nível de margem (%)"),
        ]
        
        for name, metric_type, desc in base_metrics:
            self._metrics[name] = MetricSeries(
                name=name,
                type=metric_type,
            )
    
    # ==================== COLETA DE MÉTRICAS ====================
    
    def record(self, name: str, value: float, labels: Dict[str, str] = None):
        """
        Registra uma métrica.
        
        Args:
            name: Nome da métrica
            value: Valor
            labels: Labels opcionais (bot, strategy, etc)
        """
        # Criar série se não existir
        if name not in self._metrics:
            self._metrics[name] = MetricSeries(
                name=name,
                type=MetricType.GAUGE,
                labels=labels or {}
            )
        
        self._metrics[name].add(value)
        
        # Verificar alertas
        self._check_alerts(name, value)
    
    def increment(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Incrementa um counter."""
        if name not in self._metrics:
            self._metrics[name] = MetricSeries(
                name=name,
                type=MetricType.COUNTER,
                labels=labels or {}
            )
        
        current = self._metrics[name].get_latest() or 0
        self._metrics[name].add(current + value)
    
    def record_latency(self, operation: str, latency_ms: float):
        """Registra latência de uma operação."""
        name = f"latency_{operation}_ms"
        self.record(name, latency_ms)
        
        # Também registrar na métrica geral de trading
        if "trading" in operation or "order" in operation:
            self.record("trading_latency_ms", latency_ms)
    
    def collect_system_metrics(self):
        """Coleta métricas do sistema."""
        try:
            # CPU
            cpu = psutil.cpu_percent(interval=0.1)
            self.record("system_cpu_percent", cpu)
            
            # Memória
            mem = psutil.virtual_memory()
            self.record("system_memory_percent", mem.percent)
            self.record("system_memory_used_gb", mem.used / (1024**3))
            
            # Disco
            disk = psutil.disk_usage('/')
            self.record("system_disk_percent", disk.percent)
            
            # Rede (bytes enviados/recebidos)
            net = psutil.net_io_counters()
            self.record("network_bytes_sent", net.bytes_sent)
            self.record("network_bytes_recv", net.bytes_recv)
            
        except Exception as e:
            self.logger.error(f"Erro coletando métricas do sistema: {e}")
    
    # ==================== MÉTRICAS DE TRADING ====================
    
    def record_trade(
        self,
        bot_id: str,
        pnl: float,
        volume: float,
        strategy: str = None,
        setup: str = None,
        duration_seconds: int = 0
    ):
        """
        Registra um trade finalizado.
        
        Args:
            bot_id: ID do bot
            pnl: Lucro/prejuízo
            volume: Volume negociado
            strategy: Nome da estratégia
            setup: Nome do setup
            duration_seconds: Duração do trade
        """
        # Métricas do bot
        if bot_id not in self._trading_metrics:
            self._trading_metrics[bot_id] = TradingMetrics()
        
        bot_metrics = self._trading_metrics[bot_id]
        self._update_trading_metrics(bot_metrics, pnl, volume)
        
        # Métricas globais
        self._update_trading_metrics(self._global_trading, pnl, volume)
        
        # Registrar séries temporais
        self.record(f"trade_pnl_{bot_id}", pnl)
        self.record(f"trade_volume_{bot_id}", volume)
        self.increment(f"trade_count_{bot_id}")
        
        if duration_seconds > 0:
            self.record(f"trade_duration_{bot_id}", duration_seconds)
        
        # Métricas por estratégia
        if strategy:
            self.increment(f"trades_by_strategy_{strategy}")
            self.record(f"pnl_by_strategy_{strategy}", pnl)
        
        if setup:
            self.increment(f"trades_by_setup_{setup}")
            self.record(f"pnl_by_setup_{setup}", pnl)
        
        self.logger.debug(f"Trade registrado: bot={bot_id}, pnl={pnl:.2f}")
    
    def _update_trading_metrics(self, metrics: TradingMetrics, pnl: float, volume: float):
        """Atualiza métricas de trading."""
        metrics.total_trades += 1
        metrics.total_pnl += pnl
        metrics.total_volume += volume
        
        if pnl > 0:
            metrics.winning_trades += 1
            metrics.largest_win = max(metrics.largest_win, pnl)
            
            # Streak
            if metrics.current_streak >= 0:
                metrics.current_streak += 1
            else:
                metrics.current_streak = 1
            metrics.win_streak = max(metrics.win_streak, metrics.current_streak)
        else:
            metrics.losing_trades += 1
            metrics.largest_loss = min(metrics.largest_loss, pnl)
            
            # Streak
            if metrics.current_streak <= 0:
                metrics.current_streak -= 1
            else:
                metrics.current_streak = -1
            metrics.lose_streak = max(metrics.lose_streak, abs(metrics.current_streak))
        
        # Médias
        if metrics.winning_trades > 0:
            total_wins = sum(1 for _ in range(metrics.winning_trades))
            # Aproximação simples
            metrics.avg_win = metrics.largest_win * 0.6  # Estimativa
        
        if metrics.losing_trades > 0:
            metrics.avg_loss = metrics.largest_loss * 0.6  # Estimativa
        
        # Profit factor
        if metrics.avg_loss != 0:
            gross_profit = metrics.winning_trades * abs(metrics.avg_win)
            gross_loss = metrics.losing_trades * abs(metrics.avg_loss)
            if gross_loss > 0:
                metrics.profit_factor = gross_profit / gross_loss
    
    def update_balance(self, balance: float, equity: float, margin_level: float = 0):
        """
        Atualiza métricas de saldo.
        
        Args:
            balance: Saldo atual
            equity: Patrimônio atual
            margin_level: Nível de margem (%)
        """
        self.record("balance", balance)
        self.record("equity", equity)
        if margin_level > 0:
            self.record("margin_level", margin_level)
        
        # Calcular drawdown
        if balance > self._global_trading.peak_balance:
            self._global_trading.peak_balance = balance
        
        if self._global_trading.peak_balance > 0:
            dd = ((self._global_trading.peak_balance - balance) / 
                  self._global_trading.peak_balance) * 100
            self._global_trading.current_drawdown = dd
            self._global_trading.max_drawdown = max(
                self._global_trading.max_drawdown, dd
            )
            
            self.record("current_drawdown", dd)
    
    def update_positions(self, active: int, pending: int = 0):
        """Atualiza contagem de posições."""
        self.record("active_positions", active)
        self.record("pending_orders", pending)
    
    def update_mt5_status(self, connected: bool, latency_ms: float = 0):
        """Atualiza status da conexão MT5."""
        self.record("mt5_connection_status", 1.0 if connected else 0.0)
        if latency_ms > 0:
            self.record_latency("mt5", latency_ms)
    
    # ==================== CONSULTA DE MÉTRICAS ====================
    
    def get_metric(self, name: str) -> Optional[MetricSeries]:
        """Retorna uma série de métricas."""
        return self._metrics.get(name)
    
    def get_latest(self, name: str) -> Optional[float]:
        """Retorna último valor de uma métrica."""
        series = self._metrics.get(name)
        return series.get_latest() if series else None
    
    def get_trading_metrics(self, bot_id: str = None) -> TradingMetrics:
        """
        Retorna métricas de trading.
        
        Args:
            bot_id: ID do bot (None para global)
        """
        if bot_id:
            return self._trading_metrics.get(bot_id, TradingMetrics())
        return self._global_trading
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Retorna todas as métricas atuais."""
        result = {}
        
        for name, series in self._metrics.items():
            result[name] = {
                'current': series.get_latest(),
                'avg_5min': series.get_average(5),
                'avg_1h': series.get_average(60),
                'p95': series.get_percentile(95),
            }
        
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo das métricas principais."""
        trading = self._global_trading
        
        return {
            'system': {
                'cpu_percent': self.get_latest('system_cpu_percent'),
                'memory_percent': self.get_latest('system_memory_percent'),
                'mt5_connected': self.get_latest('mt5_connection_status') == 1.0,
            },
            'trading': {
                'total_trades': trading.total_trades,
                'win_rate': trading.win_rate,
                'total_pnl': trading.total_pnl,
                'max_drawdown': trading.max_drawdown,
                'current_drawdown': trading.current_drawdown,
                'profit_factor': trading.profit_factor,
                'win_streak': trading.win_streak,
                'lose_streak': trading.lose_streak,
            },
            'account': {
                'balance': self.get_latest('balance'),
                'equity': self.get_latest('equity'),
                'margin_level': self.get_latest('margin_level'),
                'active_positions': self.get_latest('active_positions'),
            },
            'bots': {
                bot_id: {
                    'trades': m.total_trades,
                    'win_rate': m.win_rate,
                    'pnl': m.total_pnl,
                }
                for bot_id, m in self._trading_metrics.items()
            }
        }
    
    # ==================== ALERTAS ====================
    
    def set_threshold(self, name: str, value: float):
        """Define threshold para alertas."""
        self._thresholds[name] = value
    
    def add_alert_callback(self, callback: Callable[[str, str, float], None]):
        """
        Adiciona callback para alertas.
        
        Callback recebe: (alert_type, message, value)
        """
        self._alert_callbacks.append(callback)
    
    def _check_alerts(self, name: str, value: float):
        """Verifica se deve disparar alertas."""
        alerts = []
        
        # Drawdown
        if name == "current_drawdown" and value > self._thresholds.get('max_drawdown', 10):
            alerts.append(("DRAWDOWN", f"Drawdown alto: {value:.1f}%", value))
        
        # CPU
        if name == "system_cpu_percent" and value > self._thresholds.get('cpu_usage', 90):
            alerts.append(("CPU", f"CPU alta: {value:.1f}%", value))
        
        # Memória
        if name == "system_memory_percent" and value > self._thresholds.get('memory_usage', 85):
            alerts.append(("MEMORY", f"Memória alta: {value:.1f}%", value))
        
        # Latência
        if "latency" in name and value > self._thresholds.get('latency_ms', 1000):
            alerts.append(("LATENCY", f"Latência alta: {value:.0f}ms", value))
        
        # Lose streak
        trading = self._global_trading
        if trading.lose_streak >= self._thresholds.get('lose_streak', 5):
            if not hasattr(self, '_last_streak_alert') or self._last_streak_alert != trading.lose_streak:
                alerts.append(("STREAK", f"Sequência de perdas: {trading.lose_streak}", trading.lose_streak))
                self._last_streak_alert = trading.lose_streak
        
        # Disparar callbacks
        for alert_type, message, val in alerts:
            self.logger.warning(f"ALERTA [{alert_type}]: {message}")
            for callback in self._alert_callbacks:
                try:
                    callback(alert_type, message, val)
                except Exception as e:
                    self.logger.error(f"Erro em callback de alerta: {e}")
    
    # ==================== COLETA AUTOMÁTICA ====================
    
    async def start_collection(self, interval_seconds: int = 10):
        """Inicia coleta automática de métricas."""
        self._running = True
        self.logger.info(f"Iniciando coleta automática (intervalo: {interval_seconds}s)")
        
        while self._running:
            try:
                self.collect_system_metrics()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Erro na coleta: {e}")
                await asyncio.sleep(interval_seconds)
    
    def stop_collection(self):
        """Para coleta automática."""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
        self.logger.info("Coleta automática parada")
    
    # ==================== LIMPEZA ====================
    
    def cleanup_old_metrics(self):
        """Remove métricas antigas."""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        
        for series in self._metrics.values():
            series.values = [(ts, v) for ts, v in series.values if ts > cutoff]
        
        self.logger.debug("Métricas antigas removidas")
    
    def reset(self):
        """Reseta todas as métricas."""
        self._metrics.clear()
        self._trading_metrics.clear()
        self._global_trading = TradingMetrics()
        self._init_base_metrics()
        self.logger.info("Métricas resetadas")
