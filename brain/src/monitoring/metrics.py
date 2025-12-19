"""
VIRTUS - Sistema de Métricas
============================

Coleta e expõe métricas do sistema para monitoramento.
Pode ser integrado com Prometheus/Grafana.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import json
from pathlib import Path


@dataclass
class TradeMetrics:
    """Métricas de um trade."""
    symbol: str
    direction: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    profit: float = 0.0
    duration_seconds: int = 0
    strategy: str = ""
    setup: str = ""


@dataclass 
class BotMetrics:
    """Métricas de um bot."""
    bot_id: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_duration: float = 0.0
    last_trade_time: Optional[datetime] = None
    uptime_seconds: int = 0
    errors_count: int = 0


@dataclass
class SystemMetrics:
    """Métricas do sistema."""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    mt5_connected: bool = False
    mt5_latency_ms: float = 0.0
    active_positions: int = 0
    pending_orders: int = 0
    account_balance: float = 0.0
    account_equity: float = 0.0
    daily_profit: float = 0.0
    api_calls_count: int = 0
    api_errors_count: int = 0


class MetricsCollector:
    """
    Coletor centralizado de métricas.
    
    Funcionalidades:
    - Coleta métricas de bots, trades e sistema
    - Mantém histórico para análise
    - Exporta para arquivo JSON
    - Calcula estatísticas agregadas
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/metrics")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Métricas por bot
        self._bot_metrics: Dict[str, BotMetrics] = {}
        
        # Histórico de trades
        self._trades: List[TradeMetrics] = []
        
        # Métricas do sistema
        self._system_metrics: List[SystemMetrics] = []
        self._max_history = 1440  # 24 horas em minutos
        
        # Contadores
        self._counters: Dict[str, int] = defaultdict(int)
        
        # Timers
        self._timers: Dict[str, List[float]] = defaultdict(list)
        
        # Lock para thread safety
        self._lock = threading.Lock()
        
        # Carregar métricas persistidas
        self._load_metrics()
    
    def _load_metrics(self):
        """Carrega métricas do disco."""
        try:
            metrics_file = self.data_dir / "metrics_history.json"
            if metrics_file.exists():
                with open(metrics_file) as f:
                    data = json.load(f)
                    # Carregar apenas o resumo
                    self._counters.update(data.get("counters", {}))
        except Exception as e:
            print(f"Aviso: Não foi possível carregar métricas: {e}")
    
    def _save_metrics(self):
        """Salva métricas no disco."""
        try:
            metrics_file = self.data_dir / "metrics_history.json"
            
            data = {
                "timestamp": datetime.now().isoformat(),
                "counters": dict(self._counters),
                "bot_metrics": {
                    bot_id: {
                        "total_trades": m.total_trades,
                        "winning_trades": m.winning_trades,
                        "total_profit": m.total_profit,
                        "win_rate": m.win_rate,
                    }
                    for bot_id, m in self._bot_metrics.items()
                },
                "summary": self.get_summary(),
            }
            
            with open(metrics_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Aviso: Não foi possível salvar métricas: {e}")
    
    # ==================== CONTADORES ====================
    
    def increment(self, name: str, value: int = 1):
        """Incrementa um contador."""
        with self._lock:
            self._counters[name] += value
    
    def get_counter(self, name: str) -> int:
        """Retorna valor de um contador."""
        return self._counters.get(name, 0)
    
    # ==================== TIMERS ====================
    
    def record_time(self, name: str, duration_ms: float):
        """Registra tempo de uma operação."""
        with self._lock:
            self._timers[name].append(duration_ms)
            # Manter apenas últimas 100 amostras
            if len(self._timers[name]) > 100:
                self._timers[name] = self._timers[name][-100:]
    
    def get_avg_time(self, name: str) -> float:
        """Retorna tempo médio de uma operação."""
        times = self._timers.get(name, [])
        return sum(times) / len(times) if times else 0.0
    
    # ==================== TRADES ====================
    
    def record_trade(self, trade: TradeMetrics):
        """Registra um trade."""
        with self._lock:
            self._trades.append(trade)
            
            # Atualizar métricas do bot
            bot_id = trade.setup.split("_")[0] if trade.setup else "unknown"
            if bot_id not in self._bot_metrics:
                self._bot_metrics[bot_id] = BotMetrics(bot_id=bot_id)
            
            metrics = self._bot_metrics[bot_id]
            metrics.total_trades += 1
            
            if trade.profit > 0:
                metrics.winning_trades += 1
                metrics.total_profit += trade.profit
            else:
                metrics.losing_trades += 1
                metrics.total_loss += abs(trade.profit)
            
            # Recalcular win rate e profit factor
            if metrics.total_trades > 0:
                metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
            
            if metrics.total_loss > 0:
                metrics.profit_factor = metrics.total_profit / metrics.total_loss
            
            metrics.last_trade_time = trade.exit_time or datetime.now()
            
            # Incrementar contadores globais
            self._counters["total_trades"] += 1
            if trade.profit > 0:
                self._counters["winning_trades"] += 1
            else:
                self._counters["losing_trades"] += 1
        
        # Salvar periodicamente
        if self._counters["total_trades"] % 10 == 0:
            self._save_metrics()
    
    # ==================== SISTEMA ====================
    
    def record_system_metrics(self, metrics: SystemMetrics):
        """Registra métricas do sistema."""
        with self._lock:
            self._system_metrics.append(metrics)
            if len(self._system_metrics) > self._max_history:
                self._system_metrics = self._system_metrics[-self._max_history:]
    
    def get_latest_system_metrics(self) -> Optional[SystemMetrics]:
        """Retorna métricas mais recentes."""
        return self._system_metrics[-1] if self._system_metrics else None
    
    # ==================== RESUMO ====================
    
    def get_summary(self) -> Dict:
        """Retorna resumo de todas as métricas."""
        with self._lock:
            total_trades = self._counters.get("total_trades", 0)
            winning = self._counters.get("winning_trades", 0)
            
            win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
            
            return {
                "timestamp": datetime.now().isoformat(),
                "trading": {
                    "total_trades": total_trades,
                    "winning_trades": winning,
                    "losing_trades": self._counters.get("losing_trades", 0),
                    "win_rate": round(win_rate, 2),
                },
                "api": {
                    "total_calls": self._counters.get("api_calls", 0),
                    "errors": self._counters.get("api_errors", 0),
                    "avg_latency_ms": round(self.get_avg_time("api_call"), 2),
                },
                "mt5": {
                    "reconnections": self._counters.get("mt5_reconnections", 0),
                    "avg_latency_ms": round(self.get_avg_time("mt5_operation"), 2),
                },
                "bots": {
                    bot_id: {
                        "trades": m.total_trades,
                        "win_rate": round(m.win_rate, 2),
                        "profit": round(m.total_profit - m.total_loss, 2),
                    }
                    for bot_id, m in self._bot_metrics.items()
                },
            }
    
    def get_bot_metrics(self, bot_id: str) -> Optional[BotMetrics]:
        """Retorna métricas de um bot específico."""
        return self._bot_metrics.get(bot_id)
    
    def export_report(self, filepath: Optional[Path] = None) -> str:
        """Exporta relatório completo."""
        filepath = filepath or self.data_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "counters": dict(self._counters),
            "bot_details": {
                bot_id: {
                    "total_trades": m.total_trades,
                    "winning_trades": m.winning_trades,
                    "losing_trades": m.losing_trades,
                    "total_profit": m.total_profit,
                    "total_loss": m.total_loss,
                    "win_rate": m.win_rate,
                    "profit_factor": m.profit_factor,
                }
                for bot_id, m in self._bot_metrics.items()
            },
        }
        
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        return str(filepath)


# Instância global
_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Retorna o coletor de métricas global."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


# Decorators úteis
def track_time(metric_name: str):
    """Decorator para medir tempo de execução."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = (time.time() - start) * 1000
                get_metrics().record_time(metric_name, duration)
        return wrapper
    return decorator


def count_calls(metric_name: str):
    """Decorator para contar chamadas."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            get_metrics().increment(metric_name)
            return func(*args, **kwargs)
        return wrapper
    return decorator
