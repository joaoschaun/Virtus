"""
VIRTUS Analytics Dashboard
===========================

Dashboard analítico para visualização de dados e métricas.
Fornece dados formatados para frontend.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import json

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger


@dataclass
class DashboardCard:
    """Card para dashboard."""
    title: str
    value: Any
    subtitle: str = ""
    change: float = 0.0  # % de mudança
    trend: str = "neutral"  # up, down, neutral
    icon: str = ""
    color: str = "default"  # success, danger, warning, default


@dataclass
class ChartData:
    """Dados para gráfico."""
    labels: List[str]
    datasets: List[Dict[str, Any]]
    chart_type: str = "line"  # line, bar, pie, doughnut


class AnalyticsDashboard:
    """
    Dashboard analítico para visualização.
    
    Fornece dados formatados para:
    - Cards de métricas
    - Gráficos
    - Tabelas
    - Comparações
    """
    
    def __init__(self):
        self.logger = VirtusLogger.get_logger("AnalyticsDashboard")
        self.logger.info("AnalyticsDashboard inicializado")
    
    def get_overview_cards(
        self,
        trades: List[Dict[str, Any]],
        balance: float = 0,
        equity: float = 0
    ) -> List[DashboardCard]:
        """
        Gera cards para overview do dashboard.
        
        Args:
            trades: Lista de trades
            balance: Saldo atual
            equity: Patrimônio atual
            
        Returns:
            Lista de cards
        """
        cards = []
        
        # Total P&L
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        cards.append(DashboardCard(
            title="P&L Total",
            value=f"${total_pnl:,.2f}",
            trend="up" if total_pnl > 0 else "down" if total_pnl < 0 else "neutral",
            icon="💰",
            color="success" if total_pnl > 0 else "danger"
        ))
        
        # Total Trades
        cards.append(DashboardCard(
            title="Total Trades",
            value=len(trades),
            icon="📊",
            color="default"
        ))
        
        # Win Rate
        wins = len([t for t in trades if t.get('pnl', 0) > 0])
        win_rate = (wins / len(trades) * 100) if trades else 0
        cards.append(DashboardCard(
            title="Win Rate",
            value=f"{win_rate:.1f}%",
            icon="🎯",
            color="success" if win_rate >= 50 else "warning" if win_rate >= 40 else "danger"
        ))
        
        # Balance
        if balance > 0:
            cards.append(DashboardCard(
                title="Saldo",
                value=f"${balance:,.2f}",
                icon="💵",
                color="default"
            ))
        
        # Equity
        if equity > 0:
            cards.append(DashboardCard(
                title="Patrimônio",
                value=f"${equity:,.2f}",
                icon="📈",
                color="default"
            ))
        
        # Profit Factor
        gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        cards.append(DashboardCard(
            title="Profit Factor",
            value=f"{pf:.2f}",
            icon="📐",
            color="success" if pf >= 1.5 else "warning" if pf >= 1 else "danger"
        ))
        
        return cards
    
    def get_pnl_chart(
        self,
        trades: List[Dict[str, Any]],
        period: str = "daily"  # daily, weekly, monthly
    ) -> ChartData:
        """
        Gera dados para gráfico de P&L.
        
        Args:
            trades: Lista de trades
            period: Período de agregação
            
        Returns:
            Dados do gráfico
        """
        if not trades:
            return ChartData(labels=[], datasets=[])
        
        # Agrupar por período
        grouped = self._group_by_period(trades, period)
        
        labels = list(grouped.keys())
        pnl_values = [sum(t.get('pnl', 0) for t in g) for g in grouped.values()]
        cumulative = []
        running = 0
        for pnl in pnl_values:
            running += pnl
            cumulative.append(running)
        
        return ChartData(
            labels=labels,
            datasets=[
                {
                    'label': 'P&L por Período',
                    'data': pnl_values,
                    'type': 'bar',
                    'backgroundColor': ['#00ff88' if v >= 0 else '#ff4444' for v in pnl_values],
                },
                {
                    'label': 'P&L Acumulado',
                    'data': cumulative,
                    'type': 'line',
                    'borderColor': '#00d4ff',
                    'fill': False,
                }
            ],
            chart_type="bar"
        )
    
    def get_equity_curve(
        self,
        trades: List[Dict[str, Any]],
        initial_balance: float = 10000
    ) -> ChartData:
        """
        Gera curva de patrimônio.
        
        Args:
            trades: Lista de trades ordenados por tempo
            initial_balance: Saldo inicial
            
        Returns:
            Dados do gráfico
        """
        if not trades:
            return ChartData(labels=[], datasets=[])
        
        # Ordenar por tempo
        sorted_trades = sorted(trades, key=lambda t: t.get('close_time', ''))
        
        labels = ['Início']
        equity = [initial_balance]
        current = initial_balance
        
        for trade in sorted_trades:
            pnl = trade.get('pnl', 0)
            current += pnl
            
            close_time = trade.get('close_time', '')
            if isinstance(close_time, datetime):
                label = close_time.strftime('%d/%m %H:%M')
            elif isinstance(close_time, str):
                try:
                    dt = datetime.fromisoformat(close_time)
                    label = dt.strftime('%d/%m %H:%M')
                except:
                    label = str(len(labels))
            else:
                label = str(len(labels))
            
            labels.append(label)
            equity.append(current)
        
        return ChartData(
            labels=labels,
            datasets=[{
                'label': 'Patrimônio',
                'data': equity,
                'borderColor': '#00d4ff',
                'backgroundColor': 'rgba(0, 212, 255, 0.1)',
                'fill': True,
            }],
            chart_type="line"
        )
    
    def get_win_loss_distribution(self, trades: List[Dict[str, Any]]) -> ChartData:
        """
        Gera distribuição de wins/losses.
        
        Returns:
            Dados do gráfico (pie/doughnut)
        """
        wins = len([t for t in trades if t.get('pnl', 0) > 0])
        losses = len([t for t in trades if t.get('pnl', 0) < 0])
        breakeven = len([t for t in trades if t.get('pnl', 0) == 0])
        
        return ChartData(
            labels=['Vitórias', 'Derrotas', 'Empate'],
            datasets=[{
                'data': [wins, losses, breakeven],
                'backgroundColor': ['#00ff88', '#ff4444', '#888888'],
            }],
            chart_type="doughnut"
        )
    
    def get_strategy_breakdown(self, trades: List[Dict[str, Any]]) -> ChartData:
        """
        Gera breakdown por estratégia.
        
        Returns:
            Dados do gráfico (bar horizontal)
        """
        # Agrupar por estratégia
        strategies = {}
        for trade in trades:
            strat = trade.get('strategy', 'unknown')
            if strat not in strategies:
                strategies[strat] = {'trades': 0, 'pnl': 0}
            strategies[strat]['trades'] += 1
            strategies[strat]['pnl'] += trade.get('pnl', 0)
        
        # Ordenar por P&L
        sorted_strats = sorted(strategies.items(), key=lambda x: x[1]['pnl'], reverse=True)
        
        return ChartData(
            labels=[s[0] for s in sorted_strats],
            datasets=[{
                'label': 'P&L por Estratégia',
                'data': [s[1]['pnl'] for s in sorted_strats],
                'backgroundColor': ['#00ff88' if s[1]['pnl'] >= 0 else '#ff4444' for s in sorted_strats],
            }],
            chart_type="bar"
        )
    
    def get_hourly_performance(self, trades: List[Dict[str, Any]]) -> ChartData:
        """
        Gera performance por hora.
        
        Returns:
            Dados do gráfico
        """
        hours = {h: {'trades': 0, 'pnl': 0} for h in range(24)}
        
        for trade in trades:
            close_time = trade.get('close_time')
            if isinstance(close_time, datetime):
                hour = close_time.hour
            elif isinstance(close_time, str):
                try:
                    hour = datetime.fromisoformat(close_time).hour
                except:
                    continue
            else:
                continue
            
            hours[hour]['trades'] += 1
            hours[hour]['pnl'] += trade.get('pnl', 0)
        
        return ChartData(
            labels=[f"{h:02d}:00" for h in range(24)],
            datasets=[
                {
                    'label': 'P&L por Hora',
                    'data': [hours[h]['pnl'] for h in range(24)],
                    'backgroundColor': ['#00ff88' if hours[h]['pnl'] >= 0 else '#ff4444' for h in range(24)],
                },
            ],
            chart_type="bar"
        )
    
    def get_weekday_performance(self, trades: List[Dict[str, Any]]) -> ChartData:
        """
        Gera performance por dia da semana.
        
        Returns:
            Dados do gráfico
        """
        weekdays = {i: {'trades': 0, 'pnl': 0} for i in range(7)}
        names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        
        for trade in trades:
            close_time = trade.get('close_time')
            if isinstance(close_time, datetime):
                weekday = close_time.weekday()
            elif isinstance(close_time, str):
                try:
                    weekday = datetime.fromisoformat(close_time).weekday()
                except:
                    continue
            else:
                continue
            
            weekdays[weekday]['trades'] += 1
            weekdays[weekday]['pnl'] += trade.get('pnl', 0)
        
        return ChartData(
            labels=names,
            datasets=[{
                'label': 'P&L por Dia',
                'data': [weekdays[i]['pnl'] for i in range(7)],
                'backgroundColor': ['#00ff88' if weekdays[i]['pnl'] >= 0 else '#ff4444' for i in range(7)],
            }],
            chart_type="bar"
        )
    
    def get_trade_table(
        self,
        trades: List[Dict[str, Any]],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Gera dados para tabela de trades.
        
        Args:
            trades: Lista de trades
            limit: Limite de registros
            
        Returns:
            Lista de trades formatados
        """
        # Ordenar por tempo (mais recentes primeiro)
        sorted_trades = sorted(
            trades, 
            key=lambda t: t.get('close_time', ''), 
            reverse=True
        )[:limit]
        
        result = []
        for trade in sorted_trades:
            close_time = trade.get('close_time', '')
            if isinstance(close_time, datetime):
                formatted_time = close_time.strftime('%d/%m/%Y %H:%M')
            elif isinstance(close_time, str):
                try:
                    formatted_time = datetime.fromisoformat(close_time).strftime('%d/%m/%Y %H:%M')
                except:
                    formatted_time = close_time
            else:
                formatted_time = str(close_time)
            
            pnl = trade.get('pnl', 0)
            
            result.append({
                'id': trade.get('id', ''),
                'symbol': trade.get('symbol', ''),
                'direction': trade.get('direction', trade.get('type', '')),
                'strategy': trade.get('strategy', ''),
                'setup': trade.get('setup', ''),
                'entry_price': trade.get('entry_price', 0),
                'exit_price': trade.get('exit_price', 0),
                'volume': trade.get('volume', 0),
                'pnl': pnl,
                'pnl_formatted': f"${pnl:,.2f}",
                'pnl_class': 'positive' if pnl > 0 else 'negative' if pnl < 0 else 'neutral',
                'close_time': formatted_time,
                'duration': trade.get('duration', ''),
            })
        
        return result
    
    def get_full_dashboard_data(
        self,
        trades: List[Dict[str, Any]],
        balance: float = 10000,
        equity: float = 10000
    ) -> Dict[str, Any]:
        """
        Gera todos os dados do dashboard.
        
        Returns:
            Dict com todos os dados formatados
        """
        return {
            'cards': [asdict(c) for c in self.get_overview_cards(trades, balance, equity)],
            'charts': {
                'pnl': asdict(self.get_pnl_chart(trades)),
                'equity': asdict(self.get_equity_curve(trades, balance)),
                'win_loss': asdict(self.get_win_loss_distribution(trades)),
                'strategy': asdict(self.get_strategy_breakdown(trades)),
                'hourly': asdict(self.get_hourly_performance(trades)),
                'weekday': asdict(self.get_weekday_performance(trades)),
            },
            'trades': self.get_trade_table(trades),
            'generated_at': datetime.now().isoformat(),
        }
    
    def to_json(self, trades: List[Dict[str, Any]], **kwargs) -> str:
        """Exporta dashboard como JSON."""
        data = self.get_full_dashboard_data(trades, **kwargs)
        return json.dumps(data, indent=2, default=str)
    
    # ==================== HELPERS ====================
    
    def _group_by_period(
        self,
        trades: List[Dict[str, Any]],
        period: str
    ) -> Dict[str, List[Dict]]:
        """Agrupa trades por período."""
        groups = {}
        
        for trade in sorted(trades, key=lambda t: t.get('close_time', '')):
            close_time = trade.get('close_time')
            
            if isinstance(close_time, str):
                try:
                    close_time = datetime.fromisoformat(close_time)
                except:
                    continue
            elif not isinstance(close_time, datetime):
                continue
            
            if period == "daily":
                key = close_time.strftime('%d/%m')
            elif period == "weekly":
                # Início da semana
                week_start = close_time - timedelta(days=close_time.weekday())
                key = week_start.strftime('%d/%m')
            elif period == "monthly":
                key = close_time.strftime('%m/%Y')
            else:
                key = close_time.strftime('%d/%m')
            
            if key not in groups:
                groups[key] = []
            groups[key].append(trade)
        
        return groups
