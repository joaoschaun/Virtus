"""
VIRTUS Performance Attribution
================================

Análise de atribuição de performance para identificar
fontes de lucro/perda por diferentes dimensões.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger


class AttributionDimension(Enum):
    """Dimensões de atribuição."""
    STRATEGY = "strategy"
    SETUP = "setup"
    SYMBOL = "symbol"
    BOT = "bot"
    TIMEFRAME = "timeframe"
    SESSION = "session"  # Asia, London, NY
    WEEKDAY = "weekday"
    HOUR = "hour"
    DIRECTION = "direction"  # Long/Short
    DURATION = "duration"  # Scalp, Intraday, Swing


@dataclass
class AttributionResult:
    """Resultado de atribuição para uma categoria."""
    category: str
    dimension: str
    
    # Métricas básicas
    trades: int = 0
    wins: int = 0
    losses: int = 0
    
    # P&L
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    
    # Performance
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Contribuição
    pnl_contribution: float = 0.0  # % do P&L total
    trade_contribution: float = 0.0  # % dos trades
    
    # Consistência
    std_dev: float = 0.0
    sharpe: float = 0.0
    
    # Ranking
    rank: int = 0
    
    @property
    def is_profitable(self) -> bool:
        return self.total_pnl > 0


@dataclass
class AttributionSummary:
    """Resumo completo de atribuição."""
    dimension: AttributionDimension
    period_start: datetime
    period_end: datetime
    
    # Totais
    total_trades: int = 0
    total_pnl: float = 0.0
    
    # Resultados por categoria
    results: List[AttributionResult] = field(default_factory=list)
    
    # Best/Worst
    best_performer: Optional[AttributionResult] = None
    worst_performer: Optional[AttributionResult] = None
    
    # Concentração
    top_3_contribution: float = 0.0  # % do P&L dos top 3


class PerformanceAttribution:
    """
    Análise de atribuição de performance.
    
    Identifica fontes de P&L por múltiplas dimensões:
    - Estratégia
    - Setup
    - Símbolo
    - Bot
    - Sessão de mercado
    - Dia da semana
    - Hora
    """
    
    def __init__(self):
        self.logger = VirtusLogger.get_logger("PerformanceAttribution")
        
        # Definição de sessões
        self.sessions = {
            'asia': (0, 9),      # 00:00 - 09:00 UTC
            'london': (7, 16),   # 07:00 - 16:00 UTC
            'new_york': (13, 22), # 13:00 - 22:00 UTC
        }
        
        self.logger.info("PerformanceAttribution inicializado")
    
    def analyze(
        self,
        trades: List[Dict[str, Any]],
        dimension: AttributionDimension,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> AttributionSummary:
        """
        Analisa atribuição por uma dimensão.
        
        Args:
            trades: Lista de trades
            dimension: Dimensão de análise
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Resumo de atribuição
        """
        # Filtrar por período
        if start_date:
            trades = [t for t in trades if self._get_trade_time(t) >= start_date]
        if end_date:
            trades = [t for t in trades if self._get_trade_time(t) <= end_date]
        
        if not trades:
            return AttributionSummary(
                dimension=dimension,
                period_start=start_date or datetime.now(),
                period_end=end_date or datetime.now()
            )
        
        # Agrupar por dimensão
        groups = self._group_by_dimension(trades, dimension)
        
        # Calcular métricas para cada grupo
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        total_trades = len(trades)
        
        results = []
        for category, category_trades in groups.items():
            result = self._calculate_attribution(
                category=category,
                dimension=dimension.value,
                trades=category_trades,
                total_pnl=total_pnl,
                total_trades=total_trades
            )
            results.append(result)
        
        # Ordenar por P&L (decrescente)
        results.sort(key=lambda x: x.total_pnl, reverse=True)
        
        # Atribuir ranking
        for i, result in enumerate(results):
            result.rank = i + 1
        
        # Criar resumo
        summary = AttributionSummary(
            dimension=dimension,
            period_start=start_date or min(self._get_trade_time(t) for t in trades),
            period_end=end_date or max(self._get_trade_time(t) for t in trades),
            total_trades=total_trades,
            total_pnl=total_pnl,
            results=results,
            best_performer=results[0] if results else None,
            worst_performer=results[-1] if results else None,
        )
        
        # Calcular concentração top 3
        if len(results) >= 3:
            top_3_pnl = sum(r.total_pnl for r in results[:3])
            summary.top_3_contribution = (top_3_pnl / total_pnl * 100) if total_pnl != 0 else 0
        
        return summary
    
    def analyze_all_dimensions(
        self,
        trades: List[Dict[str, Any]],
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[AttributionDimension, AttributionSummary]:
        """
        Analisa atribuição por todas as dimensões.
        
        Returns:
            Dict com resumo para cada dimensão
        """
        results = {}
        
        for dimension in AttributionDimension:
            try:
                results[dimension] = self.analyze(trades, dimension, start_date, end_date)
            except Exception as e:
                self.logger.error(f"Erro analisando dimensão {dimension}: {e}")
        
        return results
    
    def get_best_performers(
        self,
        trades: List[Dict[str, Any]],
        top_n: int = 5
    ) -> Dict[str, List[AttributionResult]]:
        """
        Retorna melhores performers por dimensão.
        
        Args:
            trades: Lista de trades
            top_n: Quantidade de top performers
            
        Returns:
            Dict com top performers por dimensão
        """
        best = {}
        
        for dimension in [AttributionDimension.STRATEGY, AttributionDimension.SETUP, 
                          AttributionDimension.SYMBOL, AttributionDimension.SESSION]:
            summary = self.analyze(trades, dimension)
            best[dimension.value] = summary.results[:top_n]
        
        return best
    
    def get_worst_performers(
        self,
        trades: List[Dict[str, Any]],
        bottom_n: int = 5
    ) -> Dict[str, List[AttributionResult]]:
        """
        Retorna piores performers por dimensão.
        
        Args:
            trades: Lista de trades
            bottom_n: Quantidade de worst performers
            
        Returns:
            Dict com worst performers por dimensão
        """
        worst = {}
        
        for dimension in [AttributionDimension.STRATEGY, AttributionDimension.SETUP,
                          AttributionDimension.SYMBOL, AttributionDimension.SESSION]:
            summary = self.analyze(trades, dimension)
            # Pegar os últimos (piores)
            worst[dimension.value] = summary.results[-bottom_n:] if len(summary.results) >= bottom_n else summary.results
        
        return worst
    
    def generate_report(
        self,
        trades: List[Dict[str, Any]],
        dimensions: List[AttributionDimension] = None
    ) -> str:
        """
        Gera relatório completo de atribuição.
        
        Args:
            trades: Lista de trades
            dimensions: Dimensões a analisar (None = todas)
            
        Returns:
            Relatório em texto
        """
        if dimensions is None:
            dimensions = [
                AttributionDimension.STRATEGY,
                AttributionDimension.SETUP,
                AttributionDimension.SYMBOL,
                AttributionDimension.SESSION,
                AttributionDimension.WEEKDAY,
            ]
        
        lines = []
        lines.append("=" * 70)
        lines.append("  📊 ANÁLISE DE ATRIBUIÇÃO DE PERFORMANCE")
        lines.append("=" * 70)
        lines.append("")
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        lines.append(f"  Total de Trades: {len(trades)}")
        lines.append(f"  P&L Total: ${total_pnl:,.2f}")
        lines.append("")
        
        for dimension in dimensions:
            summary = self.analyze(trades, dimension)
            
            lines.append(f"📈 POR {dimension.value.upper()}")
            lines.append("-" * 50)
            
            if not summary.results:
                lines.append("  Sem dados")
                lines.append("")
                continue
            
            # Top 5
            for result in summary.results[:5]:
                emoji = "🟢" if result.is_profitable else "🔴"
                contribution = f"({result.pnl_contribution:+.1f}%)" if total_pnl != 0 else ""
                lines.append(
                    f"  {result.rank}. {result.category}: "
                    f"{result.trades} trades, WR {result.win_rate:.0f}%, "
                    f"{emoji} ${result.total_pnl:,.2f} {contribution}"
                )
            
            if len(summary.results) > 5:
                lines.append(f"  ... e mais {len(summary.results) - 5} categorias")
            
            lines.append("")
        
        # Insights
        lines.append("💡 INSIGHTS")
        lines.append("-" * 50)
        
        # Melhor estratégia
        strat_summary = self.analyze(trades, AttributionDimension.STRATEGY)
        if strat_summary.best_performer:
            lines.append(f"  ✓ Melhor Estratégia: {strat_summary.best_performer.category} "
                        f"(${strat_summary.best_performer.total_pnl:,.2f})")
        
        # Melhor setup
        setup_summary = self.analyze(trades, AttributionDimension.SETUP)
        if setup_summary.best_performer:
            lines.append(f"  ✓ Melhor Setup: {setup_summary.best_performer.category} "
                        f"(${setup_summary.best_performer.total_pnl:,.2f})")
        
        # Melhor sessão
        session_summary = self.analyze(trades, AttributionDimension.SESSION)
        if session_summary.best_performer:
            lines.append(f"  ✓ Melhor Sessão: {session_summary.best_performer.category} "
                        f"(${session_summary.best_performer.total_pnl:,.2f})")
        
        # Alertas
        lines.append("")
        lines.append("⚠️ ALERTAS")
        lines.append("-" * 50)
        
        # Estratégias perdedoras
        losing_strategies = [r for r in strat_summary.results if not r.is_profitable]
        if losing_strategies:
            for strat in losing_strategies[:3]:
                lines.append(f"  ✗ {strat.category}: ${strat.total_pnl:,.2f} "
                            f"(WR {strat.win_rate:.0f}%)")
        
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    # ==================== HELPERS ====================
    
    def _get_trade_time(self, trade: Dict[str, Any]) -> datetime:
        """Extrai datetime de um trade."""
        close_time = trade.get('close_time') or trade.get('exit_time') or trade.get('timestamp')
        if isinstance(close_time, datetime):
            return close_time
        elif isinstance(close_time, str):
            return datetime.fromisoformat(close_time)
        return datetime.now()
    
    def _group_by_dimension(
        self,
        trades: List[Dict[str, Any]],
        dimension: AttributionDimension
    ) -> Dict[str, List[Dict]]:
        """Agrupa trades por dimensão."""
        groups = {}
        
        for trade in trades:
            category = self._get_category(trade, dimension)
            if category not in groups:
                groups[category] = []
            groups[category].append(trade)
        
        return groups
    
    def _get_category(self, trade: Dict[str, Any], dimension: AttributionDimension) -> str:
        """Obtém categoria do trade para uma dimensão."""
        if dimension == AttributionDimension.STRATEGY:
            return trade.get('strategy', 'unknown')
        
        elif dimension == AttributionDimension.SETUP:
            return trade.get('setup', 'unknown')
        
        elif dimension == AttributionDimension.SYMBOL:
            return trade.get('symbol', 'unknown')
        
        elif dimension == AttributionDimension.BOT:
            return trade.get('bot_id', 'unknown')
        
        elif dimension == AttributionDimension.TIMEFRAME:
            return trade.get('timeframe', 'unknown')
        
        elif dimension == AttributionDimension.SESSION:
            trade_time = self._get_trade_time(trade)
            hour = trade_time.hour
            
            for session, (start, end) in self.sessions.items():
                if start <= hour < end:
                    return session
            return 'off_hours'
        
        elif dimension == AttributionDimension.WEEKDAY:
            trade_time = self._get_trade_time(trade)
            weekdays = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            return weekdays[trade_time.weekday()]
        
        elif dimension == AttributionDimension.HOUR:
            trade_time = self._get_trade_time(trade)
            return f"{trade_time.hour:02d}:00"
        
        elif dimension == AttributionDimension.DIRECTION:
            direction = trade.get('direction', trade.get('type', 'unknown'))
            if direction in ['buy', 'long', 'BUY', 'LONG']:
                return 'LONG'
            elif direction in ['sell', 'short', 'SELL', 'SHORT']:
                return 'SHORT'
            return str(direction)
        
        elif dimension == AttributionDimension.DURATION:
            # Classificar por duração
            duration = trade.get('duration_seconds', 0)
            if duration < 300:  # < 5 min
                return 'Scalp'
            elif duration < 3600:  # < 1 hora
                return 'Intraday'
            elif duration < 86400:  # < 1 dia
                return 'Day Trade'
            else:
                return 'Swing'
        
        return 'unknown'
    
    def _calculate_attribution(
        self,
        category: str,
        dimension: str,
        trades: List[Dict[str, Any]],
        total_pnl: float,
        total_trades: int
    ) -> AttributionResult:
        """Calcula atribuição para uma categoria."""
        result = AttributionResult(
            category=category,
            dimension=dimension,
            trades=len(trades)
        )
        
        if not trades:
            return result
        
        pnls = [t.get('pnl', 0) for t in trades]
        
        # Básico
        result.wins = len([p for p in pnls if p > 0])
        result.losses = len([p for p in pnls if p < 0])
        
        # P&L
        result.total_pnl = sum(pnls)
        result.gross_profit = sum(p for p in pnls if p > 0)
        result.gross_loss = sum(p for p in pnls if p < 0)
        
        # Performance
        if result.trades > 0:
            result.win_rate = (result.wins / result.trades) * 100
            result.avg_pnl = result.total_pnl / result.trades
        
        if result.wins > 0:
            result.avg_win = result.gross_profit / result.wins
        
        if result.losses > 0:
            result.avg_loss = result.gross_loss / result.losses
        
        if result.gross_loss != 0:
            result.profit_factor = abs(result.gross_profit / result.gross_loss)
        
        # Contribuição
        if total_pnl != 0:
            result.pnl_contribution = (result.total_pnl / total_pnl) * 100
        
        if total_trades > 0:
            result.trade_contribution = (result.trades / total_trades) * 100
        
        # Consistência
        if len(pnls) > 1:
            result.std_dev = statistics.stdev(pnls)
            if result.std_dev > 0:
                result.sharpe = (result.avg_pnl / result.std_dev) * (252 ** 0.5)  # Anualizado
        
        return result
