"""
VIRTUS Backtest Metrics
=======================

Cálculo de métricas de performance para backtesting.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
import pandas as pd


@dataclass
class PerformanceMetrics:
    """Métricas completas de performance."""
    
    # --- Retornos ---
    total_return: float = 0.0          # Retorno total (%)
    total_profit: float = 0.0          # Lucro total ($)
    annualized_return: float = 0.0     # Retorno anualizado (%)
    
    # --- Risco ---
    volatility: float = 0.0            # Volatilidade anualizada
    max_drawdown: float = 0.0          # Drawdown máximo (%)
    max_drawdown_duration: int = 0     # Duração do drawdown máximo (dias)
    avg_drawdown: float = 0.0          # Drawdown médio
    var_95: float = 0.0                # Value at Risk 95%
    cvar_95: float = 0.0               # Conditional VaR 95%
    
    # --- Ratios ---
    sharpe_ratio: float = 0.0          # Sharpe Ratio
    sortino_ratio: float = 0.0         # Sortino Ratio
    calmar_ratio: float = 0.0          # Calmar Ratio
    omega_ratio: float = 0.0           # Omega Ratio
    profit_factor: float = 0.0         # Profit Factor
    
    # --- Trades ---
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_trade: float = 0.0
    
    # --- Tempo ---
    avg_trade_duration: float = 0.0    # Duração média (horas)
    avg_bars_in_trade: float = 0.0     # Média de barras por trade
    
    # --- Consecutivos ---
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # --- Expectancy ---
    expectancy: float = 0.0            # Ganho esperado por trade
    expectancy_ratio: float = 0.0      # Kelly Criterion
    
    # --- Metadados ---
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trading_days: int = 0


class MetricsCalculator:
    """Calculador de métricas de performance."""
    
    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.0  # Taxa livre de risco anual
    
    def __init__(self, risk_free_rate: float = 0.0):
        self.risk_free_rate = risk_free_rate
    
    def calculate_all(
        self,
        equity_curve: List[float],
        trades: List[Dict[str, Any]],
        initial_capital: float,
        timestamps: Optional[List[datetime]] = None,
    ) -> PerformanceMetrics:
        """
        Calcula todas as métricas de performance.
        
        Args:
            equity_curve: Lista de valores de equity
            trades: Lista de trades executados
            initial_capital: Capital inicial
            timestamps: Timestamps da equity curve
        
        Returns:
            PerformanceMetrics com todas as métricas
        """
        metrics = PerformanceMetrics()
        
        if not equity_curve:
            return metrics
        
        equity = np.array(equity_curve)
        
        # Datas
        if timestamps:
            metrics.start_date = timestamps[0]
            metrics.end_date = timestamps[-1]
            metrics.trading_days = len(set(t.date() for t in timestamps))
        
        # Retornos
        metrics.total_profit = equity[-1] - initial_capital
        metrics.total_return = (equity[-1] / initial_capital - 1) * 100
        
        # Calcula retornos diários
        returns = np.diff(equity) / equity[:-1]
        
        if len(returns) > 0:
            # Volatilidade anualizada
            metrics.volatility = np.std(returns) * np.sqrt(self.TRADING_DAYS_PER_YEAR) * 100
            
            # Retorno anualizado
            if metrics.trading_days > 0:
                years = metrics.trading_days / self.TRADING_DAYS_PER_YEAR
                if years > 0:
                    metrics.annualized_return = ((equity[-1] / initial_capital) ** (1/years) - 1) * 100
            
            # Drawdown
            dd_metrics = self._calculate_drawdown(equity)
            metrics.max_drawdown = dd_metrics['max_drawdown']
            metrics.max_drawdown_duration = dd_metrics['max_duration']
            metrics.avg_drawdown = dd_metrics['avg_drawdown']
            
            # Ratios
            metrics.sharpe_ratio = self._sharpe_ratio(returns)
            metrics.sortino_ratio = self._sortino_ratio(returns)
            metrics.calmar_ratio = self._calmar_ratio(
                metrics.annualized_return, 
                metrics.max_drawdown
            )
            metrics.omega_ratio = self._omega_ratio(returns)
            
            # VaR
            metrics.var_95 = self._var(returns, 0.05) * 100
            metrics.cvar_95 = self._cvar(returns, 0.05) * 100
        
        # Trade metrics
        if trades:
            trade_metrics = self._calculate_trade_metrics(trades)
            metrics.total_trades = trade_metrics['total_trades']
            metrics.winning_trades = trade_metrics['winning_trades']
            metrics.losing_trades = trade_metrics['losing_trades']
            metrics.win_rate = trade_metrics['win_rate']
            metrics.avg_win = trade_metrics['avg_win']
            metrics.avg_loss = trade_metrics['avg_loss']
            metrics.largest_win = trade_metrics['largest_win']
            metrics.largest_loss = trade_metrics['largest_loss']
            metrics.avg_trade = trade_metrics['avg_trade']
            metrics.profit_factor = trade_metrics['profit_factor']
            metrics.avg_trade_duration = trade_metrics['avg_duration']
            metrics.max_consecutive_wins = trade_metrics['max_consecutive_wins']
            metrics.max_consecutive_losses = trade_metrics['max_consecutive_losses']
            
            # Expectancy
            metrics.expectancy = trade_metrics['expectancy']
            metrics.expectancy_ratio = trade_metrics['expectancy_ratio']
        
        return metrics
    
    def _calculate_drawdown(self, equity: np.ndarray) -> Dict[str, float]:
        """Calcula métricas de drawdown."""
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak * 100
        
        max_dd = np.max(drawdown)
        avg_dd = np.mean(drawdown)
        
        # Duração do drawdown máximo
        in_drawdown = drawdown > 0
        max_duration = 0
        current_duration = 0
        
        for is_dd in in_drawdown:
            if is_dd:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        return {
            'max_drawdown': max_dd,
            'avg_drawdown': avg_dd,
            'max_duration': max_duration,
        }
    
    def _sharpe_ratio(self, returns: np.ndarray) -> float:
        """Calcula Sharpe Ratio."""
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        
        daily_rf = self.risk_free_rate / self.TRADING_DAYS_PER_YEAR
        excess_returns = returns - daily_rf
        
        return np.mean(excess_returns) / np.std(returns) * np.sqrt(self.TRADING_DAYS_PER_YEAR)
    
    def _sortino_ratio(self, returns: np.ndarray) -> float:
        """Calcula Sortino Ratio (considera apenas downside risk)."""
        if len(returns) == 0:
            return 0.0
        
        daily_rf = self.risk_free_rate / self.TRADING_DAYS_PER_YEAR
        excess_returns = returns - daily_rf
        
        # Downside returns
        downside = returns[returns < 0]
        if len(downside) == 0 or np.std(downside) == 0:
            return float('inf') if np.mean(excess_returns) > 0 else 0.0
        
        downside_std = np.std(downside)
        
        return np.mean(excess_returns) / downside_std * np.sqrt(self.TRADING_DAYS_PER_YEAR)
    
    def _calmar_ratio(self, annualized_return: float, max_drawdown: float) -> float:
        """Calcula Calmar Ratio (retorno / max drawdown)."""
        if max_drawdown == 0:
            return float('inf') if annualized_return > 0 else 0.0
        return annualized_return / max_drawdown
    
    def _omega_ratio(self, returns: np.ndarray, threshold: float = 0.0) -> float:
        """Calcula Omega Ratio."""
        if len(returns) == 0:
            return 0.0
        
        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns < threshold]
        
        sum_losses = np.sum(losses)
        if sum_losses == 0:
            return float('inf') if np.sum(gains) > 0 else 0.0
        
        return np.sum(gains) / sum_losses
    
    def _var(self, returns: np.ndarray, confidence: float = 0.05) -> float:
        """Calcula Value at Risk."""
        if len(returns) == 0:
            return 0.0
        return np.percentile(returns, confidence * 100)
    
    def _cvar(self, returns: np.ndarray, confidence: float = 0.05) -> float:
        """Calcula Conditional VaR (Expected Shortfall)."""
        if len(returns) == 0:
            return 0.0
        var = self._var(returns, confidence)
        return np.mean(returns[returns <= var])
    
    def _calculate_trade_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula métricas baseadas nos trades."""
        if not trades:
            return self._empty_trade_metrics()
        
        pnls = [t.get('pnl', 0) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        total_trades = len(trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        # Profit Factor
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Duração média
        durations = []
        for t in trades:
            if 'entry_time' in t and 'exit_time' in t:
                entry = t['entry_time']
                exit = t['exit_time']
                if isinstance(entry, datetime) and isinstance(exit, datetime):
                    duration = (exit - entry).total_seconds() / 3600  # Em horas
                    durations.append(duration)
        
        avg_duration = np.mean(durations) if durations else 0
        
        # Consecutivos
        max_consecutive_wins = self._max_consecutive(pnls, lambda x: x > 0)
        max_consecutive_losses = self._max_consecutive(pnls, lambda x: x < 0)
        
        # Expectancy
        expectancy = np.mean(pnls) if pnls else 0
        
        # Kelly Criterion / Expectancy Ratio
        if avg_loss != 0:
            win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 1
            win_prob = win_rate / 100
            expectancy_ratio = win_prob - (1 - win_prob) / win_loss_ratio
        else:
            expectancy_ratio = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': max(wins) if wins else 0,
            'largest_loss': min(losses) if losses else 0,
            'avg_trade': np.mean(pnls) if pnls else 0,
            'profit_factor': profit_factor,
            'avg_duration': avg_duration,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'expectancy': expectancy,
            'expectancy_ratio': expectancy_ratio,
        }
    
    def _max_consecutive(self, values: List[float], condition) -> int:
        """Calcula máximo de valores consecutivos que satisfazem condição."""
        max_count = 0
        current_count = 0
        
        for v in values:
            if condition(v):
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count
    
    def _empty_trade_metrics(self) -> Dict[str, Any]:
        """Retorna métricas vazias de trades."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'avg_trade': 0,
            'profit_factor': 0,
            'avg_duration': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'expectancy': 0,
            'expectancy_ratio': 0,
        }


class MonthlyMetrics:
    """Análise mensal de performance."""
    
    @staticmethod
    def calculate(
        equity_curve: List[float],
        timestamps: List[datetime],
        initial_capital: float,
    ) -> pd.DataFrame:
        """
        Calcula retornos mensais.
        
        Returns:
            DataFrame com retornos por mês/ano
        """
        if not equity_curve or not timestamps:
            return pd.DataFrame()
        
        df = pd.DataFrame({
            'equity': equity_curve,
            'timestamp': timestamps
        })
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Retorno mensal
        monthly = df.resample('M').last()
        monthly['return'] = monthly['equity'].pct_change() * 100
        monthly.loc[monthly.index[0], 'return'] = (
            (monthly['equity'].iloc[0] / initial_capital) - 1
        ) * 100
        
        # Pivot para visualização
        monthly['year'] = monthly.index.year
        monthly['month'] = monthly.index.month
        
        pivot = monthly.pivot(index='year', columns='month', values='return')
        pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:len(pivot.columns)]
        
        # Adiciona total anual
        pivot['Year'] = pivot.sum(axis=1)
        
        return pivot


class RiskMetrics:
    """Métricas de risco adicionais."""
    
    @staticmethod
    def rolling_sharpe(
        equity_curve: List[float],
        window: int = 252,
    ) -> np.ndarray:
        """Calcula Sharpe Ratio em janela móvel."""
        equity = np.array(equity_curve)
        returns = np.diff(equity) / equity[:-1]
        
        rolling_mean = pd.Series(returns).rolling(window).mean()
        rolling_std = pd.Series(returns).rolling(window).std()
        
        sharpe = (rolling_mean / rolling_std) * np.sqrt(252)
        return sharpe.values
    
    @staticmethod
    def rolling_drawdown(
        equity_curve: List[float],
        window: int = 252,
    ) -> np.ndarray:
        """Calcula drawdown em janela móvel."""
        equity = np.array(equity_curve)
        
        drawdowns = []
        for i in range(len(equity)):
            start = max(0, i - window)
            window_equity = equity[start:i+1]
            peak = np.max(window_equity)
            dd = (peak - equity[i]) / peak * 100
            drawdowns.append(dd)
        
        return np.array(drawdowns)
    
    @staticmethod
    def underwater_curve(equity_curve: List[float]) -> np.ndarray:
        """Calcula curva underwater (drawdown contínuo)."""
        equity = np.array(equity_curve)
        peak = np.maximum.accumulate(equity)
        underwater = (peak - equity) / peak * 100
        return underwater
