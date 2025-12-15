"""
VIRTUS Prometheus Exporter
===========================

Exporta métricas no formato Prometheus para integração
com sistemas de monitoramento externos.
"""

from typing import Dict, List, Optional
from datetime import datetime

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger

from .metrics_collector import MetricsCollector, MetricType


class PrometheusExporter:
    """
    Exportador de métricas no formato Prometheus.
    
    Gera métricas em texto plano compatível com Prometheus scraping.
    """
    
    def __init__(self, collector: MetricsCollector, prefix: str = "virtus"):
        self.logger = VirtusLogger.get_logger("PrometheusExporter")
        self.collector = collector
        self.prefix = prefix
        
        self.logger.info("PrometheusExporter inicializado")
    
    def export(self) -> str:
        """
        Exporta todas as métricas no formato Prometheus.
        
        Returns:
            String com métricas formatadas
        """
        lines = []
        
        # Header
        lines.append(f"# VIRTUS Metrics Export - {datetime.now().isoformat()}")
        lines.append("")
        
        # Métricas de sistema
        lines.extend(self._export_system_metrics())
        
        # Métricas de trading
        lines.extend(self._export_trading_metrics())
        
        # Métricas de conta
        lines.extend(self._export_account_metrics())
        
        # Métricas de bots
        lines.extend(self._export_bot_metrics())
        
        return "\n".join(lines)
    
    def _export_system_metrics(self) -> List[str]:
        """Exporta métricas do sistema."""
        lines = []
        lines.append("# HELP virtus_cpu_percent CPU usage percentage")
        lines.append("# TYPE virtus_cpu_percent gauge")
        
        cpu = self.collector.get_latest("system_cpu_percent")
        if cpu is not None:
            lines.append(f"{self.prefix}_cpu_percent {cpu}")
        
        lines.append("")
        lines.append("# HELP virtus_memory_percent Memory usage percentage")
        lines.append("# TYPE virtus_memory_percent gauge")
        
        mem = self.collector.get_latest("system_memory_percent")
        if mem is not None:
            lines.append(f"{self.prefix}_memory_percent {mem}")
        
        lines.append("")
        lines.append("# HELP virtus_mt5_connected MT5 connection status")
        lines.append("# TYPE virtus_mt5_connected gauge")
        
        mt5 = self.collector.get_latest("mt5_connection_status")
        if mt5 is not None:
            lines.append(f"{self.prefix}_mt5_connected {int(mt5)}")
        
        lines.append("")
        return lines
    
    def _export_trading_metrics(self) -> List[str]:
        """Exporta métricas de trading."""
        lines = []
        trading = self.collector.get_trading_metrics()
        
        # Total trades
        lines.append("# HELP virtus_trades_total Total number of trades")
        lines.append("# TYPE virtus_trades_total counter")
        lines.append(f"{self.prefix}_trades_total {trading.total_trades}")
        lines.append("")
        
        # Win rate
        lines.append("# HELP virtus_win_rate Win rate percentage")
        lines.append("# TYPE virtus_win_rate gauge")
        lines.append(f"{self.prefix}_win_rate {trading.win_rate:.2f}")
        lines.append("")
        
        # PnL
        lines.append("# HELP virtus_pnl_total Total profit/loss")
        lines.append("# TYPE virtus_pnl_total gauge")
        lines.append(f"{self.prefix}_pnl_total {trading.total_pnl:.2f}")
        lines.append("")
        
        # Drawdown
        lines.append("# HELP virtus_drawdown_current Current drawdown percentage")
        lines.append("# TYPE virtus_drawdown_current gauge")
        lines.append(f"{self.prefix}_drawdown_current {trading.current_drawdown:.2f}")
        lines.append("")
        
        lines.append("# HELP virtus_drawdown_max Maximum drawdown percentage")
        lines.append("# TYPE virtus_drawdown_max gauge")
        lines.append(f"{self.prefix}_drawdown_max {trading.max_drawdown:.2f}")
        lines.append("")
        
        # Profit factor
        lines.append("# HELP virtus_profit_factor Profit factor")
        lines.append("# TYPE virtus_profit_factor gauge")
        lines.append(f"{self.prefix}_profit_factor {trading.profit_factor:.2f}")
        lines.append("")
        
        return lines
    
    def _export_account_metrics(self) -> List[str]:
        """Exporta métricas da conta."""
        lines = []
        
        # Balance
        lines.append("# HELP virtus_balance Account balance")
        lines.append("# TYPE virtus_balance gauge")
        balance = self.collector.get_latest("balance")
        if balance is not None:
            lines.append(f"{self.prefix}_balance {balance:.2f}")
        lines.append("")
        
        # Equity
        lines.append("# HELP virtus_equity Account equity")
        lines.append("# TYPE virtus_equity gauge")
        equity = self.collector.get_latest("equity")
        if equity is not None:
            lines.append(f"{self.prefix}_equity {equity:.2f}")
        lines.append("")
        
        # Positions
        lines.append("# HELP virtus_positions_active Active positions count")
        lines.append("# TYPE virtus_positions_active gauge")
        positions = self.collector.get_latest("active_positions")
        if positions is not None:
            lines.append(f"{self.prefix}_positions_active {int(positions)}")
        lines.append("")
        
        return lines
    
    def _export_bot_metrics(self) -> List[str]:
        """Exporta métricas por bot."""
        lines = []
        
        lines.append("# HELP virtus_bot_trades Bot trades count")
        lines.append("# TYPE virtus_bot_trades counter")
        
        lines.append("# HELP virtus_bot_pnl Bot profit/loss")
        lines.append("# TYPE virtus_bot_pnl gauge")
        
        lines.append("# HELP virtus_bot_winrate Bot win rate")
        lines.append("# TYPE virtus_bot_winrate gauge")
        
        for bot_id in self.collector._trading_metrics.keys():
            metrics = self.collector.get_trading_metrics(bot_id)
            
            lines.append(f'{self.prefix}_bot_trades{{bot="{bot_id}"}} {metrics.total_trades}')
            lines.append(f'{self.prefix}_bot_pnl{{bot="{bot_id}"}} {metrics.total_pnl:.2f}')
            lines.append(f'{self.prefix}_bot_winrate{{bot="{bot_id}"}} {metrics.win_rate:.2f}')
        
        lines.append("")
        return lines
    
    def get_metrics_endpoint(self) -> str:
        """
        Retorna métricas para endpoint HTTP.
        
        Usado quando integrado com um servidor HTTP.
        """
        return self.export()


class HealthAggregator:
    """
    Agregador de status de saúde do sistema.
    
    Verifica múltiplos componentes e gera status consolidado.
    """
    
    def __init__(self, collector: MetricsCollector):
        self.logger = VirtusLogger.get_logger("HealthAggregator")
        self.collector = collector
        
        # Thresholds de saúde
        self.thresholds = {
            'cpu_critical': 95.0,
            'cpu_warning': 80.0,
            'memory_critical': 95.0,
            'memory_warning': 80.0,
            'drawdown_critical': 15.0,
            'drawdown_warning': 10.0,
            'lose_streak_warning': 5,
        }
        
        self.logger.info("HealthAggregator inicializado")
    
    def check_health(self) -> Dict[str, any]:
        """
        Verifica saúde de todos os componentes.
        
        Returns:
            Dict com status de cada componente
        """
        components = {}
        
        # Sistema
        components['system'] = self._check_system_health()
        
        # MT5
        components['mt5'] = self._check_mt5_health()
        
        # Trading
        components['trading'] = self._check_trading_health()
        
        # Status geral
        statuses = [c['status'] for c in components.values()]
        
        if 'critical' in statuses:
            overall = 'critical'
        elif 'warning' in statuses:
            overall = 'warning'
        else:
            overall = 'healthy'
        
        return {
            'status': overall,
            'timestamp': datetime.now().isoformat(),
            'components': components,
        }
    
    def _check_system_health(self) -> Dict[str, any]:
        """Verifica saúde do sistema."""
        cpu = self.collector.get_latest("system_cpu_percent") or 0
        mem = self.collector.get_latest("system_memory_percent") or 0
        
        issues = []
        status = 'healthy'
        
        if cpu >= self.thresholds['cpu_critical']:
            status = 'critical'
            issues.append(f"CPU crítica: {cpu:.1f}%")
        elif cpu >= self.thresholds['cpu_warning']:
            status = 'warning'
            issues.append(f"CPU alta: {cpu:.1f}%")
        
        if mem >= self.thresholds['memory_critical']:
            status = 'critical'
            issues.append(f"Memória crítica: {mem:.1f}%")
        elif mem >= self.thresholds['memory_warning']:
            if status != 'critical':
                status = 'warning'
            issues.append(f"Memória alta: {mem:.1f}%")
        
        return {
            'status': status,
            'cpu_percent': cpu,
            'memory_percent': mem,
            'issues': issues,
        }
    
    def _check_mt5_health(self) -> Dict[str, any]:
        """Verifica saúde da conexão MT5."""
        connected = self.collector.get_latest("mt5_connection_status")
        latency = self.collector.get_latest("latency_mt5_ms") or 0
        
        if connected is None or connected == 0:
            return {
                'status': 'critical',
                'connected': False,
                'latency_ms': 0,
                'issues': ['MT5 desconectado'],
            }
        
        issues = []
        status = 'healthy'
        
        if latency > 1000:
            status = 'warning'
            issues.append(f"Latência alta: {latency:.0f}ms")
        
        return {
            'status': status,
            'connected': True,
            'latency_ms': latency,
            'issues': issues,
        }
    
    def _check_trading_health(self) -> Dict[str, any]:
        """Verifica saúde do trading."""
        trading = self.collector.get_trading_metrics()
        
        issues = []
        status = 'healthy'
        
        # Drawdown
        if trading.current_drawdown >= self.thresholds['drawdown_critical']:
            status = 'critical'
            issues.append(f"Drawdown crítico: {trading.current_drawdown:.1f}%")
        elif trading.current_drawdown >= self.thresholds['drawdown_warning']:
            status = 'warning'
            issues.append(f"Drawdown alto: {trading.current_drawdown:.1f}%")
        
        # Lose streak
        if trading.lose_streak >= self.thresholds['lose_streak_warning']:
            if status != 'critical':
                status = 'warning'
            issues.append(f"Sequência de perdas: {trading.lose_streak}")
        
        return {
            'status': status,
            'total_trades': trading.total_trades,
            'win_rate': trading.win_rate,
            'current_drawdown': trading.current_drawdown,
            'lose_streak': trading.lose_streak,
            'issues': issues,
        }
    
    def is_healthy(self) -> bool:
        """Retorna True se sistema está saudável."""
        health = self.check_health()
        return health['status'] == 'healthy'
    
    def get_issues(self) -> List[str]:
        """Retorna lista de problemas atuais."""
        health = self.check_health()
        issues = []
        for component in health['components'].values():
            issues.extend(component.get('issues', []))
        return issues
