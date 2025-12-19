"""
VIRTUS - Métricas Prometheus
=============================

Exporta métricas para Prometheus/Grafana.
"""

import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import logging

logger = logging.getLogger("virtus.prometheus")


@dataclass
class MetricConfig:
    """Configuração de uma métrica."""
    name: str
    help: str
    type: str  # counter, gauge, histogram, summary
    labels: List[str] = field(default_factory=list)


class Counter:
    """Métrica de contador (só incrementa)."""
    
    def __init__(self, name: str, help: str, labels: List[str] = None):
        self.name = name
        self.help = help
        self.labels = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def inc(self, value: float = 1, **label_values):
        """Incrementa o contador."""
        key = self._label_key(label_values)
        with self._lock:
            self._values[key] += value
    
    def _label_key(self, label_values: Dict) -> tuple:
        return tuple(label_values.get(l, "") for l in self.labels)
    
    def collect(self) -> str:
        """Coleta métricas em formato Prometheus."""
        lines = [
            f"# HELP {self.name} {self.help}",
            f"# TYPE {self.name} counter",
        ]
        
        with self._lock:
            for labels, value in self._values.items():
                if self.labels:
                    label_str = ",".join(f'{l}="{v}"' for l, v in zip(self.labels, labels))
                    lines.append(f"{self.name}{{{label_str}}} {value}")
                else:
                    lines.append(f"{self.name} {value}")
        
        return "\n".join(lines)


class Gauge:
    """Métrica de gauge (pode subir ou descer)."""
    
    def __init__(self, name: str, help: str, labels: List[str] = None):
        self.name = name
        self.help = help
        self.labels = labels or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()
    
    def set(self, value: float, **label_values):
        """Define o valor."""
        key = self._label_key(label_values)
        with self._lock:
            self._values[key] = value
    
    def inc(self, value: float = 1, **label_values):
        """Incrementa o valor."""
        key = self._label_key(label_values)
        with self._lock:
            self._values[key] = self._values.get(key, 0) + value
    
    def dec(self, value: float = 1, **label_values):
        """Decrementa o valor."""
        key = self._label_key(label_values)
        with self._lock:
            self._values[key] = self._values.get(key, 0) - value
    
    def _label_key(self, label_values: Dict) -> tuple:
        return tuple(label_values.get(l, "") for l in self.labels)
    
    def collect(self) -> str:
        """Coleta métricas em formato Prometheus."""
        lines = [
            f"# HELP {self.name} {self.help}",
            f"# TYPE {self.name} gauge",
        ]
        
        with self._lock:
            for labels, value in self._values.items():
                if self.labels:
                    label_str = ",".join(f'{l}="{v}"' for l, v in zip(self.labels, labels))
                    lines.append(f"{self.name}{{{label_str}}} {value}")
                else:
                    lines.append(f"{self.name} {value}")
        
        return "\n".join(lines)


class Histogram:
    """Métrica de histograma."""
    
    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
    
    def __init__(self, name: str, help: str, labels: List[str] = None, buckets: List[float] = None):
        self.name = name
        self.help = help
        self.labels = labels or []
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._sums: Dict[tuple, float] = defaultdict(float)
        self._counts: Dict[tuple, int] = defaultdict(int)
        self._buckets: Dict[tuple, Dict[float, int]] = {}
        self._lock = threading.Lock()
    
    def observe(self, value: float, **label_values):
        """Observa um valor."""
        key = self._label_key(label_values)
        with self._lock:
            self._sums[key] += value
            self._counts[key] += 1
            
            if key not in self._buckets:
                self._buckets[key] = {b: 0 for b in self.buckets}
            
            for bucket in self.buckets:
                if value <= bucket:
                    self._buckets[key][bucket] += 1
    
    def _label_key(self, label_values: Dict) -> tuple:
        return tuple(label_values.get(l, "") for l in self.labels)
    
    def collect(self) -> str:
        """Coleta métricas em formato Prometheus."""
        lines = [
            f"# HELP {self.name} {self.help}",
            f"# TYPE {self.name} histogram",
        ]
        
        with self._lock:
            for labels in set(self._sums.keys()) | set(self._counts.keys()):
                label_str = ""
                if self.labels:
                    label_str = ",".join(f'{l}="{v}"' for l, v in zip(self.labels, labels))
                
                # Buckets
                if labels in self._buckets:
                    cumulative = 0
                    for bucket in self.buckets:
                        cumulative += self._buckets[labels].get(bucket, 0)
                        bucket_label = f'{label_str},le="{bucket}"' if label_str else f'le="{bucket}"'
                        lines.append(f"{self.name}_bucket{{{bucket_label}}} {cumulative}")
                    
                    inf_label = f'{label_str},le="+Inf"' if label_str else 'le="+Inf"'
                    lines.append(f"{self.name}_bucket{{{inf_label}}} {self._counts[labels]}")
                
                # Sum e count
                if label_str:
                    lines.append(f"{self.name}_sum{{{label_str}}} {self._sums[labels]}")
                    lines.append(f"{self.name}_count{{{label_str}}} {self._counts[labels]}")
                else:
                    lines.append(f"{self.name}_sum {self._sums[labels]}")
                    lines.append(f"{self.name}_count {self._counts[labels]}")
        
        return "\n".join(lines)


class PrometheusRegistry:
    """
    Registry de métricas Prometheus.
    
    Uso:
        registry = PrometheusRegistry()
        
        trades_total = registry.counter("virtus_trades_total", "Total de trades", ["symbol", "type"])
        equity_gauge = registry.gauge("virtus_equity", "Equity atual")
        
        trades_total.inc(symbol="XAUUSD", type="buy")
        equity_gauge.set(5000.0)
        
        print(registry.collect())
    """
    
    def __init__(self, prefix: str = "virtus"):
        self.prefix = prefix
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def _full_name(self, name: str) -> str:
        return f"{self.prefix}_{name}" if self.prefix else name
    
    def counter(self, name: str, help: str, labels: List[str] = None) -> Counter:
        """Cria ou retorna um counter."""
        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = Counter(full_name, help, labels)
            return self._metrics[full_name]
    
    def gauge(self, name: str, help: str, labels: List[str] = None) -> Gauge:
        """Cria ou retorna um gauge."""
        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = Gauge(full_name, help, labels)
            return self._metrics[full_name]
    
    def histogram(self, name: str, help: str, labels: List[str] = None, buckets: List[float] = None) -> Histogram:
        """Cria ou retorna um histogram."""
        full_name = self._full_name(name)
        with self._lock:
            if full_name not in self._metrics:
                self._metrics[full_name] = Histogram(full_name, help, labels, buckets)
            return self._metrics[full_name]
    
    def collect(self) -> str:
        """Coleta todas as métricas."""
        lines = []
        with self._lock:
            for metric in self._metrics.values():
                lines.append(metric.collect())
        return "\n\n".join(lines)


# ============================================================================
# MÉTRICAS PADRÃO DO VIRTUS
# ============================================================================

# Registry global
registry = PrometheusRegistry("virtus")

# === Métricas de Trading ===
trades_total = registry.counter(
    "trades_total",
    "Total de trades executados",
    ["symbol", "type", "bot_id"]
)

trade_profit = registry.counter(
    "trade_profit_total",
    "Lucro total em USD",
    ["symbol", "bot_id"]
)

trade_loss = registry.counter(
    "trade_loss_total",
    "Perda total em USD",
    ["symbol", "bot_id"]
)

trade_duration = registry.histogram(
    "trade_duration_seconds",
    "Duração dos trades em segundos",
    ["symbol"],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400]
)

# === Métricas de Conta ===
account_balance = registry.gauge(
    "account_balance",
    "Balance da conta em USD"
)

account_equity = registry.gauge(
    "account_equity",
    "Equity da conta em USD"
)

account_margin = registry.gauge(
    "account_margin",
    "Margem utilizada em USD"
)

account_drawdown = registry.gauge(
    "account_drawdown_percent",
    "Drawdown atual em percentual"
)

# === Métricas de Posições ===
open_positions = registry.gauge(
    "open_positions_total",
    "Total de posições abertas",
    ["symbol"]
)

position_volume = registry.gauge(
    "position_volume_total",
    "Volume total em aberto",
    ["symbol", "direction"]
)

# === Métricas de Bots ===
bot_status = registry.gauge(
    "bot_status",
    "Status do bot (1=running, 0=stopped)",
    ["bot_id", "symbol"]
)

bot_signals = registry.counter(
    "bot_signals_total",
    "Total de sinais gerados",
    ["bot_id", "symbol", "direction"]
)

# === Métricas de Sistema ===
api_requests = registry.counter(
    "api_requests_total",
    "Total de requests à API",
    ["method", "endpoint", "status"]
)

api_latency = registry.histogram(
    "api_latency_seconds",
    "Latência da API em segundos",
    ["endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

mt5_connection = registry.gauge(
    "mt5_connection_status",
    "Status da conexão MT5 (1=connected, 0=disconnected)"
)

errors_total = registry.counter(
    "errors_total",
    "Total de erros",
    ["type", "component"]
)

# === Métricas de Performance ===
win_rate = registry.gauge(
    "win_rate_percent",
    "Win rate em percentual",
    ["bot_id"]
)

profit_factor = registry.gauge(
    "profit_factor",
    "Profit factor",
    ["bot_id"]
)

sharpe_ratio = registry.gauge(
    "sharpe_ratio",
    "Sharpe ratio",
    ["bot_id"]
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def record_trade(
    symbol: str,
    trade_type: str,
    profit: float,
    duration_seconds: float,
    bot_id: str = "manual"
):
    """Registra métricas de um trade."""
    trades_total.inc(symbol=symbol, type=trade_type, bot_id=bot_id)
    
    if profit >= 0:
        trade_profit.inc(profit, symbol=symbol, bot_id=bot_id)
    else:
        trade_loss.inc(abs(profit), symbol=symbol, bot_id=bot_id)
    
    trade_duration.observe(duration_seconds, symbol=symbol)


def update_account_metrics(
    balance: float,
    equity: float,
    margin: float,
    drawdown_percent: float = 0
):
    """Atualiza métricas da conta."""
    account_balance.set(balance)
    account_equity.set(equity)
    account_margin.set(margin)
    account_drawdown.set(drawdown_percent)


def update_bot_metrics(
    bot_id: str,
    symbol: str,
    is_running: bool,
    current_win_rate: float = 0,
    current_profit_factor: float = 0
):
    """Atualiza métricas de um bot."""
    bot_status.set(1 if is_running else 0, bot_id=bot_id, symbol=symbol)
    win_rate.set(current_win_rate, bot_id=bot_id)
    profit_factor.set(current_profit_factor, bot_id=bot_id)


def record_api_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration_seconds: float
):
    """Registra métricas de request API."""
    api_requests.inc(method=method, endpoint=endpoint, status=str(status_code))
    api_latency.observe(duration_seconds, endpoint=endpoint)


def update_system_metrics():
    """
    Atualiza métricas do sistema.
    Chamado periodicamente pelo endpoint /metrics.
    """
    try:
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent()
        
        # Memória
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Atualiza gauges de sistema (se existirem)
        # Estas métricas são opcionais
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Erro ao atualizar métricas do sistema: {e}")


# ============================================================================
# FASTAPI ROUTES
# ============================================================================

from fastapi import APIRouter, Response

router = APIRouter(tags=["Prometheus"])


@router.get("/metrics")
async def prometheus_metrics():
    """Endpoint de métricas Prometheus."""
    return Response(
        content=registry.collect(),
        media_type="text/plain; charset=utf-8"
    )


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Simula algumas métricas
    record_trade("XAUUSD", "buy", 45.50, 3600, "XAUUSD_Scalper")
    record_trade("XAUUSD", "sell", -12.30, 1800, "XAUUSD_Scalper")
    record_trade("EURUSD", "buy", 28.00, 7200, "EURUSD_Trend")
    
    update_account_metrics(
        balance=10000.0,
        equity=10045.50,
        margin=500.0,
        drawdown_percent=2.5
    )
    
    update_bot_metrics(
        bot_id="XAUUSD_Scalper",
        symbol="XAUUSD",
        is_running=True,
        current_win_rate=62.5,
        current_profit_factor=1.85
    )
    
    record_api_request("GET", "/api/positions", 200, 0.05)
    record_api_request("POST", "/api/trade", 200, 0.15)
    
    print(registry.collect())
