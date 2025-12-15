"""
VIRTUS Weekly Report
=====================

Relatório semanal de trading com análises comparativas.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger

from .report_builder import ReportBuilder, ReportData, ReportFormat
from .daily_report import DailyReport


class WeeklyReport(ReportBuilder):
    """
    Gerador de relatórios semanais.
    
    Analisa performance da semana, compara com semanas anteriores,
    identifica melhores/piores dias e padrões semanais.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = VirtusLogger.get_logger("WeeklyReport")
        self.daily_report = DailyReport()
        self.logger.info("WeeklyReport inicializado")
    
    def build(self, data: ReportData) -> str:
        """Constrói relatório semanal em texto."""
        return self.to_text(data)
    
    def build_from_trades(
        self,
        trades: List[Dict[str, Any]],
        week_start: date = None,
        format: ReportFormat = ReportFormat.TEXT
    ) -> str:
        """
        Constrói relatório a partir de lista de trades.
        
        Args:
            trades: Lista de trades
            week_start: Início da semana (segunda-feira)
            format: Formato de saída
            
        Returns:
            Relatório formatado
        """
        # Calcular início da semana (segunda-feira)
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        # Filtrar trades da semana
        week_trades = [
            t for t in trades 
            if week_start <= self._get_trade_date(t) <= week_end
        ]
        
        # Calcular métricas
        data = self._calculate_weekly_metrics(week_trades, week_start, week_end)
        
        # Adicionar análise por dia
        data.weekday_stats = self._calculate_weekday_stats(week_trades)
        
        # Gerar no formato solicitado
        if format == ReportFormat.JSON:
            return self.to_json(data)
        elif format == ReportFormat.HTML:
            return self._to_weekly_html(data)
        elif format == ReportFormat.MARKDOWN:
            return self._to_weekly_markdown(data)
        else:
            return self._to_weekly_text(data)
    
    def _get_trade_date(self, trade: Dict[str, Any]) -> date:
        """Extrai data de um trade."""
        close_time = trade.get('close_time') or trade.get('exit_time') or trade.get('timestamp')
        if isinstance(close_time, datetime):
            return close_time.date()
        elif isinstance(close_time, str):
            return datetime.fromisoformat(close_time).date()
        return date.today()
    
    def _calculate_weekly_metrics(
        self, 
        trades: List[Dict[str, Any]], 
        week_start: date,
        week_end: date
    ) -> ReportData:
        """Calcula métricas da semana."""
        data = ReportData(
            start_date=datetime.combine(week_start, datetime.min.time()),
            end_date=datetime.combine(week_end, datetime.max.time())
        )
        
        if not trades:
            return data
        
        # Métricas básicas (reutiliza lógica do DailyReport)
        data.total_trades = len(trades)
        
        winners = [t for t in trades if t.get('pnl', 0) > 0]
        losers = [t for t in trades if t.get('pnl', 0) < 0]
        
        data.winning_trades = len(winners)
        data.losing_trades = len(losers)
        
        # P&L
        pnls = [t.get('pnl', 0) for t in trades]
        data.total_pnl = sum(pnls)
        data.gross_profit = sum(p for p in pnls if p > 0)
        data.gross_loss = sum(p for p in pnls if p < 0)
        
        # Win rate e Profit Factor
        if data.total_trades > 0:
            data.win_rate = (data.winning_trades / data.total_trades) * 100
        
        if data.gross_loss != 0:
            data.profit_factor = abs(data.gross_profit / data.gross_loss)
        
        # Médias
        if data.winning_trades > 0:
            data.avg_win = data.gross_profit / data.winning_trades
            data.largest_win = max(t.get('pnl', 0) for t in winners)
        
        if data.losing_trades > 0:
            data.avg_loss = data.gross_loss / data.losing_trades
            data.largest_loss = min(t.get('pnl', 0) for t in losers)
        
        # Streaks da semana
        data.max_win_streak, data.max_lose_streak = self._calculate_streaks(trades)
        
        # Por bot
        data.bot_stats = self._group_by_field(trades, 'bot_id')
        
        # Por estratégia
        data.strategy_stats = self._group_by_field(trades, 'strategy')
        
        # Por setup
        data.setup_stats = self._group_by_field(trades, 'setup')
        
        # Por símbolo
        data.symbol_stats = self._group_by_field(trades, 'symbol')
        
        return data
    
    def _calculate_weekday_stats(self, trades: List[Dict[str, Any]]) -> Dict[int, Dict]:
        """Calcula estatísticas por dia da semana."""
        # 0 = Segunda, 6 = Domingo
        weekday_names = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        stats = {i: {'name': weekday_names[i], 'trades': 0, 'wins': 0, 'pnl': 0} for i in range(7)}
        
        for trade in trades:
            trade_date = self._get_trade_date(trade)
            weekday = trade_date.weekday()
            
            stats[weekday]['trades'] += 1
            if trade.get('pnl', 0) > 0:
                stats[weekday]['wins'] += 1
            stats[weekday]['pnl'] += trade.get('pnl', 0)
        
        # Calcular win rate
        for day, data in stats.items():
            if data['trades'] > 0:
                data['win_rate'] = (data['wins'] / data['trades']) * 100
            else:
                data['win_rate'] = 0
        
        return stats
    
    def _calculate_streaks(self, trades: List[Dict[str, Any]]) -> tuple:
        """Calcula sequências de vitórias/derrotas."""
        if not trades:
            return 0, 0
        
        max_win = max_lose = 0
        current_win = current_lose = 0
        
        for trade in sorted(trades, key=lambda t: t.get('close_time', '')):
            pnl = trade.get('pnl', 0)
            
            if pnl > 0:
                current_win += 1
                current_lose = 0
                max_win = max(max_win, current_win)
            elif pnl < 0:
                current_lose += 1
                current_win = 0
                max_lose = max(max_lose, current_lose)
        
        return max_win, max_lose
    
    def _group_by_field(self, trades: List[Dict[str, Any]], field: str) -> Dict[str, Dict]:
        """Agrupa trades por campo."""
        groups = {}
        
        for trade in trades:
            key = trade.get(field, 'unknown')
            if key not in groups:
                groups[key] = {'trades': 0, 'wins': 0, 'pnl': 0}
            
            groups[key]['trades'] += 1
            if trade.get('pnl', 0) > 0:
                groups[key]['wins'] += 1
            groups[key]['pnl'] += trade.get('pnl', 0)
        
        # Calcular win rate
        for key, stats in groups.items():
            if stats['trades'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['trades']) * 100
            else:
                stats['win_rate'] = 0
        
        return groups
    
    def _to_weekly_text(self, data: ReportData) -> str:
        """Gera relatório semanal em texto."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"  📅 RELATÓRIO SEMANAL - {data.start_date.strftime('%d/%m')} a {data.end_date.strftime('%d/%m/%Y')}")
        lines.append("=" * 70)
        lines.append("")
        
        # Resumo
        lines.append("📊 RESUMO DA SEMANA")
        lines.append("-" * 50)
        lines.append(f"  Total de Trades: {data.total_trades}")
        lines.append(f"  Trades Vencedores: {data.winning_trades}")
        lines.append(f"  Trades Perdedores: {data.losing_trades}")
        lines.append(f"  Win Rate: {data.win_rate:.1f}%")
        lines.append("")
        
        # P&L
        emoji = "🟢" if data.total_pnl >= 0 else "🔴"
        lines.append(f"💰 P&L: {emoji} ${data.total_pnl:,.2f}")
        lines.append(f"   Lucro Bruto: ${data.gross_profit:,.2f}")
        lines.append(f"   Perda Bruta: ${data.gross_loss:,.2f}")
        lines.append(f"   Profit Factor: {data.profit_factor:.2f}")
        lines.append("")
        
        # Por dia da semana
        if data.weekday_stats:
            lines.append("📅 PERFORMANCE POR DIA")
            lines.append("-" * 50)
            for day, stats in sorted(data.weekday_stats.items()):
                if stats['trades'] > 0:
                    day_emoji = "🟢" if stats['pnl'] >= 0 else "🔴"
                    lines.append(f"  {stats['name']}: {stats['trades']} trades, WR {stats['win_rate']:.0f}%, {day_emoji} ${stats['pnl']:,.2f}")
            lines.append("")
        
        # Por estratégia
        if data.strategy_stats:
            lines.append("📋 POR ESTRATÉGIA")
            lines.append("-" * 50)
            for strategy, stats in sorted(data.strategy_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
                strat_emoji = "🟢" if stats['pnl'] >= 0 else "🔴"
                lines.append(f"  {strategy}: {stats['trades']} trades, WR {stats['win_rate']:.0f}%, {strat_emoji} ${stats['pnl']:,.2f}")
            lines.append("")
        
        # Por símbolo
        if data.symbol_stats:
            lines.append("💹 POR SÍMBOLO")
            lines.append("-" * 50)
            for symbol, stats in sorted(data.symbol_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
                sym_emoji = "🟢" if stats['pnl'] >= 0 else "🔴"
                lines.append(f"  {symbol}: {stats['trades']} trades, WR {stats['win_rate']:.0f}%, {sym_emoji} ${stats['pnl']:,.2f}")
            lines.append("")
        
        # Melhores setups
        if data.setup_stats:
            lines.append("🎯 TOP SETUPS")
            lines.append("-" * 50)
            top_setups = sorted(data.setup_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)[:5]
            for setup, stats in top_setups:
                setup_emoji = "🟢" if stats['pnl'] >= 0 else "🔴"
                lines.append(f"  {setup}: {stats['trades']} trades, WR {stats['win_rate']:.0f}%, {setup_emoji} ${stats['pnl']:,.2f}")
            lines.append("")
        
        lines.append("=" * 70)
        lines.append(f"  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _to_weekly_markdown(self, data: ReportData) -> str:
        """Gera relatório semanal em Markdown."""
        lines = []
        lines.append(f"# 📅 Relatório Semanal VIRTUS")
        lines.append(f"**Período:** {data.start_date.strftime('%d/%m')} - {data.end_date.strftime('%d/%m/%Y')}")
        lines.append("")
        
        # Resumo
        lines.append("## 📊 Resumo")
        lines.append("")
        lines.append("| Métrica | Valor |")
        lines.append("|---------|-------|")
        lines.append(f"| Total Trades | {data.total_trades} |")
        lines.append(f"| Win Rate | {data.win_rate:.1f}% |")
        lines.append(f"| Total P&L | ${data.total_pnl:,.2f} |")
        lines.append(f"| Profit Factor | {data.profit_factor:.2f} |")
        lines.append("")
        
        # Por dia
        if data.weekday_stats:
            lines.append("## 📅 Por Dia da Semana")
            lines.append("")
            lines.append("| Dia | Trades | Win Rate | P&L |")
            lines.append("|-----|--------|----------|-----|")
            for day, stats in sorted(data.weekday_stats.items()):
                if stats['trades'] > 0:
                    lines.append(f"| {stats['name']} | {stats['trades']} | {stats['win_rate']:.0f}% | ${stats['pnl']:,.2f} |")
            lines.append("")
        
        # Por estratégia
        if data.strategy_stats:
            lines.append("## 📋 Por Estratégia")
            lines.append("")
            lines.append("| Estratégia | Trades | Win Rate | P&L |")
            lines.append("|------------|--------|----------|-----|")
            for strategy, stats in sorted(data.strategy_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
                lines.append(f"| {strategy} | {stats['trades']} | {stats['win_rate']:.0f}% | ${stats['pnl']:,.2f} |")
            lines.append("")
        
        lines.append("---")
        lines.append(f"*Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*")
        
        return "\n".join(lines)
    
    def _to_weekly_html(self, data: ReportData) -> str:
        """Gera relatório semanal em HTML."""
        # Reutiliza base com customizações
        html = self.to_html(data)
        
        # Adicionar seção de dias da semana
        if data.weekday_stats:
            weekday_section = """
        <div class="section">
            <h2>📅 Performance por Dia</h2>
            <table>
                <tr><th>Dia</th><th>Trades</th><th>Win Rate</th><th>P&L</th></tr>
"""
            for day, stats in sorted(data.weekday_stats.items()):
                if stats['trades'] > 0:
                    pnl_class = "positive" if stats['pnl'] >= 0 else "negative"
                    weekday_section += f"""
                <tr>
                    <td>{stats['name']}</td>
                    <td>{stats['trades']}</td>
                    <td>{stats['win_rate']:.0f}%</td>
                    <td class="{pnl_class}">${stats['pnl']:,.2f}</td>
                </tr>
"""
            weekday_section += """
            </table>
        </div>
"""
            # Inserir antes do footer
            html = html.replace('<div class="footer">', weekday_section + '\n        <div class="footer">')
        
        return html
    
    def generate_summary(self, trades: List[Dict[str, Any]], week_start: date = None) -> str:
        """
        Gera resumo curto para Telegram/notificações.
        
        Args:
            trades: Lista de trades
            week_start: Início da semana
            
        Returns:
            Resumo compacto
        """
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        week_trades = [
            t for t in trades 
            if week_start <= self._get_trade_date(t) <= week_end
        ]
        
        data = self._calculate_weekly_metrics(week_trades, week_start, week_end)
        
        emoji = "🟢" if data.total_pnl >= 0 else "🔴"
        
        # Melhor dia
        weekday_stats = self._calculate_weekday_stats(week_trades)
        best_day = max(weekday_stats.items(), key=lambda x: x[1]['pnl'])[1] if weekday_stats else None
        
        summary = f"""
📅 *Resumo Semanal - {week_start.strftime('%d/%m')} a {week_end.strftime('%d/%m')}*

{emoji} *P&L Semanal:* ${data.total_pnl:,.2f}
📈 *Trades:* {data.total_trades} ({data.winning_trades}W / {data.losing_trades}L)
🎯 *Win Rate:* {data.win_rate:.1f}%
📊 *Profit Factor:* {data.profit_factor:.2f}
"""
        
        if best_day and best_day['trades'] > 0:
            summary += f"\n🏆 *Melhor Dia:* {best_day['name']} (${best_day['pnl']:,.2f})"
        
        return summary.strip()
