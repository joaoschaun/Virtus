"""
VIRTUS Daily Report
====================

Relatório diário de trading com métricas e análises.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger

from .report_builder import ReportBuilder, ReportData, ReportFormat


class DailyReport(ReportBuilder):
    """
    Gerador de relatórios diários.
    
    Analisa performance do dia, compara com dias anteriores
    e identifica padrões.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = VirtusLogger.get_logger("DailyReport")
        self.logger.info("DailyReport inicializado")
    
    def build(self, data: ReportData) -> str:
        """Constrói relatório diário em texto."""
        return self.to_text(data)
    
    def build_from_trades(
        self,
        trades: List[Dict[str, Any]],
        target_date: date = None,
        format: ReportFormat = ReportFormat.TEXT
    ) -> str:
        """
        Constrói relatório a partir de lista de trades.
        
        Args:
            trades: Lista de trades do dia
            target_date: Data alvo (padrão: hoje)
            format: Formato de saída
            
        Returns:
            Relatório formatado
        """
        target_date = target_date or date.today()
        
        # Filtrar trades do dia
        day_trades = [
            t for t in trades 
            if self._get_trade_date(t) == target_date
        ]
        
        # Calcular métricas
        data = self._calculate_metrics(day_trades, target_date)
        
        # Gerar no formato solicitado
        if format == ReportFormat.JSON:
            return self.to_json(data)
        elif format == ReportFormat.HTML:
            return self.to_html(data)
        elif format == ReportFormat.MARKDOWN:
            return self.to_markdown(data)
        else:
            return self.to_text(data)
    
    def _get_trade_date(self, trade: Dict[str, Any]) -> date:
        """Extrai data de um trade."""
        close_time = trade.get('close_time') or trade.get('exit_time') or trade.get('timestamp')
        if isinstance(close_time, datetime):
            return close_time.date()
        elif isinstance(close_time, str):
            return datetime.fromisoformat(close_time).date()
        return date.today()
    
    def _calculate_metrics(self, trades: List[Dict[str, Any]], target_date: date) -> ReportData:
        """Calcula métricas do dia."""
        data = ReportData(
            start_date=datetime.combine(target_date, datetime.min.time()),
            end_date=datetime.combine(target_date, datetime.max.time())
        )
        
        if not trades:
            return data
        
        # Métricas básicas
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
        
        # Streaks
        data.max_win_streak, data.max_lose_streak = self._calculate_streaks(trades)
        
        # Por bot
        data.bot_stats = self._group_by_field(trades, 'bot_id')
        
        # Por estratégia
        data.strategy_stats = self._group_by_field(trades, 'strategy')
        
        # Por setup
        data.setup_stats = self._group_by_field(trades, 'setup')
        
        # Por símbolo
        data.symbol_stats = self._group_by_field(trades, 'symbol')
        
        # Por hora
        data.hourly_stats = self._group_by_hour(trades)
        
        return data
    
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
            # pnl == 0: mantém streaks
        
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
    
    def _group_by_hour(self, trades: List[Dict[str, Any]]) -> Dict[int, Dict]:
        """Agrupa trades por hora."""
        hours = {h: {'trades': 0, 'wins': 0, 'pnl': 0} for h in range(24)}
        
        for trade in trades:
            close_time = trade.get('close_time')
            if isinstance(close_time, datetime):
                hour = close_time.hour
            elif isinstance(close_time, str):
                hour = datetime.fromisoformat(close_time).hour
            else:
                continue
            
            hours[hour]['trades'] += 1
            if trade.get('pnl', 0) > 0:
                hours[hour]['wins'] += 1
            hours[hour]['pnl'] += trade.get('pnl', 0)
        
        # Calcular win rate
        for hour, stats in hours.items():
            if stats['trades'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['trades']) * 100
        
        # Remover horas sem trades
        return {h: s for h, s in hours.items() if s['trades'] > 0}
    
    def generate_summary(self, trades: List[Dict[str, Any]], target_date: date = None) -> str:
        """
        Gera resumo curto para Telegram/notificações.
        
        Args:
            trades: Lista de trades
            target_date: Data alvo
            
        Returns:
            Resumo compacto
        """
        target_date = target_date or date.today()
        data = self._calculate_metrics(
            [t for t in trades if self._get_trade_date(t) == target_date],
            target_date
        )
        
        emoji = "🟢" if data.total_pnl >= 0 else "🔴"
        
        summary = f"""
📊 *Resumo Diário - {target_date.strftime('%d/%m/%Y')}*

{emoji} *P&L:* ${data.total_pnl:,.2f}
📈 *Trades:* {data.total_trades} ({data.winning_trades}W / {data.losing_trades}L)
🎯 *Win Rate:* {data.win_rate:.1f}%
📉 *Max DD:* {data.max_drawdown:.2f}%

💰 *Maior Ganho:* ${data.largest_win:,.2f}
💸 *Maior Perda:* ${data.largest_loss:,.2f}
"""
        return summary.strip()
