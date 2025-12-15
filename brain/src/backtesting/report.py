"""
VIRTUS Backtest Report
======================

Geração de relatórios de backtesting em múltiplos formatos.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from .metrics import PerformanceMetrics


class BacktestReport:
    """Gerador de relatórios de backtest."""
    
    def __init__(
        self,
        metrics: PerformanceMetrics,
        trades: List[Dict[str, Any]],
        equity_curve: List[float],
        timestamps: List[datetime],
        config: Optional[Dict[str, Any]] = None,
    ):
        self.metrics = metrics
        self.trades = trades
        self.equity_curve = equity_curve
        self.timestamps = timestamps
        self.config = config or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte relatório para dicionário."""
        return {
            'summary': {
                'total_return': round(self.metrics.total_return, 2),
                'total_profit': round(self.metrics.total_profit, 2),
                'max_drawdown': round(self.metrics.max_drawdown, 2),
                'sharpe_ratio': round(self.metrics.sharpe_ratio, 2),
                'sortino_ratio': round(self.metrics.sortino_ratio, 2),
                'profit_factor': round(self.metrics.profit_factor, 2),
                'win_rate': round(self.metrics.win_rate, 2),
                'total_trades': self.metrics.total_trades,
            },
            'returns': {
                'total_return': round(self.metrics.total_return, 2),
                'annualized_return': round(self.metrics.annualized_return, 2),
                'total_profit': round(self.metrics.total_profit, 2),
            },
            'risk': {
                'volatility': round(self.metrics.volatility, 2),
                'max_drawdown': round(self.metrics.max_drawdown, 2),
                'max_drawdown_duration': self.metrics.max_drawdown_duration,
                'avg_drawdown': round(self.metrics.avg_drawdown, 2),
                'var_95': round(self.metrics.var_95, 2),
                'cvar_95': round(self.metrics.cvar_95, 2),
            },
            'ratios': {
                'sharpe_ratio': round(self.metrics.sharpe_ratio, 2),
                'sortino_ratio': round(self.metrics.sortino_ratio, 2),
                'calmar_ratio': round(self.metrics.calmar_ratio, 2),
                'omega_ratio': round(self.metrics.omega_ratio, 2),
                'profit_factor': round(self.metrics.profit_factor, 2),
            },
            'trades': {
                'total_trades': self.metrics.total_trades,
                'winning_trades': self.metrics.winning_trades,
                'losing_trades': self.metrics.losing_trades,
                'win_rate': round(self.metrics.win_rate, 2),
                'avg_win': round(self.metrics.avg_win, 2),
                'avg_loss': round(self.metrics.avg_loss, 2),
                'largest_win': round(self.metrics.largest_win, 2),
                'largest_loss': round(self.metrics.largest_loss, 2),
                'avg_trade': round(self.metrics.avg_trade, 2),
                'avg_trade_duration': round(self.metrics.avg_trade_duration, 2),
                'max_consecutive_wins': self.metrics.max_consecutive_wins,
                'max_consecutive_losses': self.metrics.max_consecutive_losses,
            },
            'expectancy': {
                'expectancy': round(self.metrics.expectancy, 2),
                'expectancy_ratio': round(self.metrics.expectancy_ratio, 4),
            },
            'config': self.config,
            'period': {
                'start': self.metrics.start_date.isoformat() if self.metrics.start_date else None,
                'end': self.metrics.end_date.isoformat() if self.metrics.end_date else None,
                'trading_days': self.metrics.trading_days,
            }
        }
    
    def to_json(self, filepath: Optional[str] = None) -> str:
        """Exporta relatório para JSON."""
        data = self.to_dict()
        
        # Adiciona trades detalhados
        data['trade_history'] = [
            {
                'id': t.get('id', i),
                'symbol': t.get('symbol', ''),
                'direction': t.get('direction', ''),
                'entry_price': round(t.get('entry_price', 0), 5),
                'exit_price': round(t.get('exit_price', 0), 5),
                'volume': t.get('volume', 0),
                'pnl': round(t.get('pnl', 0), 2),
                'entry_time': t.get('entry_time').isoformat() if isinstance(t.get('entry_time'), datetime) else str(t.get('entry_time', '')),
                'exit_time': t.get('exit_time').isoformat() if isinstance(t.get('exit_time'), datetime) else str(t.get('exit_time', '')),
            }
            for i, t in enumerate(self.trades)
        ]
        
        json_str = json.dumps(data, indent=2, default=str)
        
        if filepath:
            Path(filepath).write_text(json_str)
        
        return json_str
    
    def to_text(self) -> str:
        """Gera relatório em texto formatado."""
        lines = []
        lines.append("=" * 60)
        lines.append("VIRTUS BACKTEST REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Período
        if self.metrics.start_date and self.metrics.end_date:
            lines.append(f"📅 Período: {self.metrics.start_date.strftime('%Y-%m-%d')} to {self.metrics.end_date.strftime('%Y-%m-%d')}")
            lines.append(f"📊 Dias de Trading: {self.metrics.trading_days}")
        lines.append("")
        
        # Resumo
        lines.append("-" * 40)
        lines.append("📈 RESUMO DE PERFORMANCE")
        lines.append("-" * 40)
        lines.append(f"  Retorno Total:     {self.metrics.total_return:>10.2f}%")
        lines.append(f"  Lucro Total:      ${self.metrics.total_profit:>10.2f}")
        lines.append(f"  Retorno Anual:     {self.metrics.annualized_return:>10.2f}%")
        lines.append(f"  Volatilidade:      {self.metrics.volatility:>10.2f}%")
        lines.append(f"  Max Drawdown:      {self.metrics.max_drawdown:>10.2f}%")
        lines.append("")
        
        # Ratios
        lines.append("-" * 40)
        lines.append("📊 RATIOS")
        lines.append("-" * 40)
        lines.append(f"  Sharpe Ratio:      {self.metrics.sharpe_ratio:>10.2f}")
        lines.append(f"  Sortino Ratio:     {self.metrics.sortino_ratio:>10.2f}")
        lines.append(f"  Calmar Ratio:      {self.metrics.calmar_ratio:>10.2f}")
        lines.append(f"  Profit Factor:     {self.metrics.profit_factor:>10.2f}")
        lines.append("")
        
        # Trades
        lines.append("-" * 40)
        lines.append("🎯 ESTATÍSTICAS DE TRADES")
        lines.append("-" * 40)
        lines.append(f"  Total Trades:      {self.metrics.total_trades:>10}")
        lines.append(f"  Trades Vencedores: {self.metrics.winning_trades:>10}")
        lines.append(f"  Trades Perdedores: {self.metrics.losing_trades:>10}")
        lines.append(f"  Win Rate:          {self.metrics.win_rate:>10.2f}%")
        lines.append(f"  Ganho Médio:      ${self.metrics.avg_win:>10.2f}")
        lines.append(f"  Perda Média:      ${self.metrics.avg_loss:>10.2f}")
        lines.append(f"  Maior Ganho:      ${self.metrics.largest_win:>10.2f}")
        lines.append(f"  Maior Perda:      ${self.metrics.largest_loss:>10.2f}")
        lines.append(f"  Trade Médio:      ${self.metrics.avg_trade:>10.2f}")
        lines.append("")
        
        # Consecutivos
        lines.append("-" * 40)
        lines.append("📈 SEQUÊNCIAS")
        lines.append("-" * 40)
        lines.append(f"  Max Wins Consec:   {self.metrics.max_consecutive_wins:>10}")
        lines.append(f"  Max Losses Consec: {self.metrics.max_consecutive_losses:>10}")
        lines.append("")
        
        # Risco
        lines.append("-" * 40)
        lines.append("⚠️ MÉTRICAS DE RISCO")
        lines.append("-" * 40)
        lines.append(f"  VaR (95%):         {self.metrics.var_95:>10.2f}%")
        lines.append(f"  CVaR (95%):        {self.metrics.cvar_95:>10.2f}%")
        lines.append(f"  DD Max Duração:    {self.metrics.max_drawdown_duration:>10} bars")
        lines.append("")
        
        # Expectancy
        lines.append("-" * 40)
        lines.append("🎲 EXPECTANCY")
        lines.append("-" * 40)
        lines.append(f"  Expectancy:       ${self.metrics.expectancy:>10.2f}")
        lines.append(f"  Kelly Criterion:   {self.metrics.expectancy_ratio:>10.4f}")
        lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def to_html(self, filepath: Optional[str] = None) -> str:
        """Gera relatório em HTML."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>VIRTUS Backtest Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #00d4ff; text-align: center; }}
        h2 {{ color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: #16213e; border-radius: 10px; padding: 20px; }}
        .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
        .metric-label {{ color: #888; }}
        .metric-value {{ font-weight: bold; }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff4444; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #0f3460; color: #00d4ff; }}
        tr:hover {{ background: #1f4287; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 VIRTUS Backtest Report</h1>
        
        <div class="grid">
            <div class="card">
                <h2>📈 Performance</h2>
                <div class="metric">
                    <span class="metric-label">Total Return</span>
                    <span class="metric-value {'positive' if self.metrics.total_return >= 0 else 'negative'}">{self.metrics.total_return:.2f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Profit</span>
                    <span class="metric-value {'positive' if self.metrics.total_profit >= 0 else 'negative'}">${self.metrics.total_profit:.2f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Annualized Return</span>
                    <span class="metric-value">{self.metrics.annualized_return:.2f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Volatility</span>
                    <span class="metric-value">{self.metrics.volatility:.2f}%</span>
                </div>
            </div>
            
            <div class="card">
                <h2>📊 Ratios</h2>
                <div class="metric">
                    <span class="metric-label">Sharpe Ratio</span>
                    <span class="metric-value">{self.metrics.sharpe_ratio:.2f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Sortino Ratio</span>
                    <span class="metric-value">{self.metrics.sortino_ratio:.2f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Calmar Ratio</span>
                    <span class="metric-value">{self.metrics.calmar_ratio:.2f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Profit Factor</span>
                    <span class="metric-value">{self.metrics.profit_factor:.2f}</span>
                </div>
            </div>
            
            <div class="card">
                <h2>🎯 Trades</h2>
                <div class="metric">
                    <span class="metric-label">Total Trades</span>
                    <span class="metric-value">{self.metrics.total_trades}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Win Rate</span>
                    <span class="metric-value">{self.metrics.win_rate:.2f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Win</span>
                    <span class="metric-value positive">${self.metrics.avg_win:.2f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Loss</span>
                    <span class="metric-value negative">${self.metrics.avg_loss:.2f}</span>
                </div>
            </div>
            
            <div class="card">
                <h2>⚠️ Risk</h2>
                <div class="metric">
                    <span class="metric-label">Max Drawdown</span>
                    <span class="metric-value negative">{self.metrics.max_drawdown:.2f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">VaR (95%)</span>
                    <span class="metric-value">{self.metrics.var_95:.2f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">CVaR (95%)</span>
                    <span class="metric-value">{self.metrics.cvar_95:.2f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Max DD Duration</span>
                    <span class="metric-value">{self.metrics.max_drawdown_duration} bars</span>
                </div>
            </div>
        </div>
        
        <h2>📝 Trade History (Last 20)</h2>
        <table>
            <tr>
                <th>#</th>
                <th>Symbol</th>
                <th>Direction</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>P&L</th>
                <th>Entry Time</th>
            </tr>
            {''.join(self._trade_row(i, t) for i, t in enumerate(self.trades[-20:]))}
        </table>
    </div>
</body>
</html>
"""
        
        if filepath:
            Path(filepath).write_text(html)
        
        return html
    
    def _trade_row(self, index: int, trade: Dict[str, Any]) -> str:
        """Gera linha da tabela de trades."""
        pnl = trade.get('pnl', 0)
        pnl_class = 'positive' if pnl >= 0 else 'negative'
        entry_time = trade.get('entry_time', '')
        if isinstance(entry_time, datetime):
            entry_time = entry_time.strftime('%Y-%m-%d %H:%M')
        
        return f"""
            <tr>
                <td>{index + 1}</td>
                <td>{trade.get('symbol', '')}</td>
                <td>{trade.get('direction', '')}</td>
                <td>{trade.get('entry_price', 0):.5f}</td>
                <td>{trade.get('exit_price', 0):.5f}</td>
                <td class="{pnl_class}">${pnl:.2f}</td>
                <td>{entry_time}</td>
            </tr>
        """
    
    def print_summary(self) -> None:
        """Imprime resumo no console."""
        print(self.to_text())
