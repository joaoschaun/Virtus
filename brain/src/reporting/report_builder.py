"""
VIRTUS Report Builder
======================

Base para geração de relatórios com múltiplos formatos.
"""

from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger


class ReportFormat(Enum):
    """Formatos de relatório."""
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class ReportSection:
    """Seção de um relatório."""
    title: str
    content: Dict[str, Any]
    order: int = 0
    
    
@dataclass
class ReportData:
    """Dados consolidados para relatório."""
    # Período
    start_date: datetime
    end_date: datetime
    
    # Métricas gerais
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    
    # Performance
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Risk
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # em minutos
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # Streaks
    max_win_streak: int = 0
    max_lose_streak: int = 0
    
    # Por bot
    bot_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Por estratégia
    strategy_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Por setup
    setup_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Por símbolo
    symbol_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Por dia da semana
    weekday_stats: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    
    # Por hora
    hourly_stats: Dict[int, Dict[str, Any]] = field(default_factory=dict)


class ReportBuilder(ABC):
    """
    Base abstrata para construção de relatórios.
    
    Subclasses implementam relatórios específicos (diário, semanal, etc).
    """
    
    def __init__(self):
        self.logger = VirtusLogger.get_logger(self.__class__.__name__)
        self.sections: List[ReportSection] = []
    
    def add_section(self, title: str, content: Dict[str, Any], order: int = None):
        """Adiciona seção ao relatório."""
        if order is None:
            order = len(self.sections)
        self.sections.append(ReportSection(title=title, content=content, order=order))
    
    def clear_sections(self):
        """Limpa seções."""
        self.sections.clear()
    
    @abstractmethod
    def build(self, data: ReportData) -> str:
        """Constrói o relatório."""
        pass
    
    def to_text(self, data: ReportData) -> str:
        """Gera relatório em texto."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"  RELATÓRIO - {data.start_date.strftime('%d/%m/%Y')} a {data.end_date.strftime('%d/%m/%Y')}")
        lines.append("=" * 60)
        lines.append("")
        
        # Resumo geral
        lines.append("📊 RESUMO GERAL")
        lines.append("-" * 40)
        lines.append(f"  Total de Trades: {data.total_trades}")
        lines.append(f"  Trades Vencedores: {data.winning_trades}")
        lines.append(f"  Trades Perdedores: {data.losing_trades}")
        lines.append(f"  Win Rate: {data.win_rate:.1f}%")
        lines.append("")
        
        # P&L
        lines.append("💰 P&L")
        lines.append("-" * 40)
        lines.append(f"  Total P&L: ${data.total_pnl:,.2f}")
        lines.append(f"  Lucro Bruto: ${data.gross_profit:,.2f}")
        lines.append(f"  Perda Bruta: ${data.gross_loss:,.2f}")
        lines.append(f"  Profit Factor: {data.profit_factor:.2f}")
        lines.append("")
        
        # Médias
        lines.append("📈 MÉDIAS")
        lines.append("-" * 40)
        lines.append(f"  Média Ganho: ${data.avg_win:,.2f}")
        lines.append(f"  Média Perda: ${data.avg_loss:,.2f}")
        lines.append(f"  Maior Ganho: ${data.largest_win:,.2f}")
        lines.append(f"  Maior Perda: ${data.largest_loss:,.2f}")
        lines.append("")
        
        # Risco
        lines.append("⚠️ RISCO")
        lines.append("-" * 40)
        lines.append(f"  Max Drawdown: {data.max_drawdown:.2f}%")
        lines.append(f"  Sharpe Ratio: {data.sharpe_ratio:.2f}")
        lines.append(f"  Sortino Ratio: {data.sortino_ratio:.2f}")
        lines.append("")
        
        # Streaks
        lines.append("🔥 STREAKS")
        lines.append("-" * 40)
        lines.append(f"  Maior Sequência Vitórias: {data.max_win_streak}")
        lines.append(f"  Maior Sequência Perdas: {data.max_lose_streak}")
        lines.append("")
        
        # Por bot
        if data.bot_stats:
            lines.append("🤖 POR BOT")
            lines.append("-" * 40)
            for bot_id, stats in data.bot_stats.items():
                lines.append(f"  {bot_id}:")
                lines.append(f"    Trades: {stats.get('trades', 0)}, WR: {stats.get('win_rate', 0):.1f}%, P&L: ${stats.get('pnl', 0):,.2f}")
            lines.append("")
        
        # Por estratégia
        if data.strategy_stats:
            lines.append("📋 POR ESTRATÉGIA")
            lines.append("-" * 40)
            for strategy, stats in data.strategy_stats.items():
                lines.append(f"  {strategy}:")
                lines.append(f"    Trades: {stats.get('trades', 0)}, WR: {stats.get('win_rate', 0):.1f}%, P&L: ${stats.get('pnl', 0):,.2f}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append(f"  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def to_json(self, data: ReportData) -> str:
        """Gera relatório em JSON."""
        report = {
            'period': {
                'start': data.start_date.isoformat(),
                'end': data.end_date.isoformat(),
            },
            'summary': {
                'total_trades': data.total_trades,
                'winning_trades': data.winning_trades,
                'losing_trades': data.losing_trades,
                'win_rate': data.win_rate,
                'total_pnl': data.total_pnl,
                'profit_factor': data.profit_factor,
            },
            'pnl': {
                'gross_profit': data.gross_profit,
                'gross_loss': data.gross_loss,
                'avg_win': data.avg_win,
                'avg_loss': data.avg_loss,
                'largest_win': data.largest_win,
                'largest_loss': data.largest_loss,
            },
            'risk': {
                'max_drawdown': data.max_drawdown,
                'sharpe_ratio': data.sharpe_ratio,
                'sortino_ratio': data.sortino_ratio,
            },
            'streaks': {
                'max_win_streak': data.max_win_streak,
                'max_lose_streak': data.max_lose_streak,
            },
            'by_bot': data.bot_stats,
            'by_strategy': data.strategy_stats,
            'by_setup': data.setup_stats,
            'by_symbol': data.symbol_stats,
            'generated_at': datetime.now().isoformat(),
        }
        
        return json.dumps(report, indent=2, default=str)
    
    def to_html(self, data: ReportData) -> str:
        """Gera relatório em HTML."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>VIRTUS Report - {data.start_date.strftime('%d/%m/%Y')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; padding: 20px; background: #16213e; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ color: #00d4ff; margin: 0; }}
        .section {{ background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 15px; }}
        .section h2 {{ color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .metric {{ background: #0f3460; padding: 15px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #00d4ff; }}
        .metric-label {{ font-size: 12px; color: #888; margin-top: 5px; }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff4444; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #0f3460; color: #00d4ff; }}
        .footer {{ text-align: center; padding: 20px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 VIRTUS Trading Report</h1>
            <p>{data.start_date.strftime('%d/%m/%Y')} - {data.end_date.strftime('%d/%m/%Y')}</p>
        </div>
        
        <div class="section">
            <h2>📈 Resumo Geral</h2>
            <div class="grid">
                <div class="metric">
                    <div class="metric-value">{data.total_trades}</div>
                    <div class="metric-label">Total Trades</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{data.win_rate:.1f}%</div>
                    <div class="metric-label">Win Rate</div>
                </div>
                <div class="metric">
                    <div class="metric-value {'positive' if data.total_pnl >= 0 else 'negative'}">${data.total_pnl:,.2f}</div>
                    <div class="metric-label">Total P&L</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{data.profit_factor:.2f}</div>
                    <div class="metric-label">Profit Factor</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>⚠️ Risco</h2>
            <div class="grid">
                <div class="metric">
                    <div class="metric-value negative">{data.max_drawdown:.2f}%</div>
                    <div class="metric-label">Max Drawdown</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{data.sharpe_ratio:.2f}</div>
                    <div class="metric-label">Sharpe Ratio</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{data.sortino_ratio:.2f}</div>
                    <div class="metric-label">Sortino Ratio</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | VIRTUS Trading System
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def to_markdown(self, data: ReportData) -> str:
        """Gera relatório em Markdown."""
        lines = []
        lines.append(f"# 📊 VIRTUS Trading Report")
        lines.append(f"**Período:** {data.start_date.strftime('%d/%m/%Y')} - {data.end_date.strftime('%d/%m/%Y')}")
        lines.append("")
        
        lines.append("## 📈 Resumo Geral")
        lines.append("")
        lines.append("| Métrica | Valor |")
        lines.append("|---------|-------|")
        lines.append(f"| Total Trades | {data.total_trades} |")
        lines.append(f"| Trades Vencedores | {data.winning_trades} |")
        lines.append(f"| Trades Perdedores | {data.losing_trades} |")
        lines.append(f"| Win Rate | {data.win_rate:.1f}% |")
        lines.append("")
        
        lines.append("## 💰 P&L")
        lines.append("")
        lines.append("| Métrica | Valor |")
        lines.append("|---------|-------|")
        lines.append(f"| Total P&L | ${data.total_pnl:,.2f} |")
        lines.append(f"| Lucro Bruto | ${data.gross_profit:,.2f} |")
        lines.append(f"| Perda Bruta | ${data.gross_loss:,.2f} |")
        lines.append(f"| Profit Factor | {data.profit_factor:.2f} |")
        lines.append("")
        
        lines.append("## ⚠️ Risco")
        lines.append("")
        lines.append("| Métrica | Valor |")
        lines.append("|---------|-------|")
        lines.append(f"| Max Drawdown | {data.max_drawdown:.2f}% |")
        lines.append(f"| Sharpe Ratio | {data.sharpe_ratio:.2f} |")
        lines.append(f"| Sortino Ratio | {data.sortino_ratio:.2f} |")
        lines.append("")
        
        if data.strategy_stats:
            lines.append("## 📋 Por Estratégia")
            lines.append("")
            lines.append("| Estratégia | Trades | Win Rate | P&L |")
            lines.append("|------------|--------|----------|-----|")
            for strategy, stats in data.strategy_stats.items():
                lines.append(f"| {strategy} | {stats.get('trades', 0)} | {stats.get('win_rate', 0):.1f}% | ${stats.get('pnl', 0):,.2f} |")
            lines.append("")
        
        lines.append("---")
        lines.append(f"*Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*")
        
        return "\n".join(lines)
