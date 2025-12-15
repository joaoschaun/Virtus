"""
VIRTUS Advanced Risk Management
================================

Gestão de risco extremamente avançada com:
- Kelly Criterion para sizing otimizado
- Monte Carlo VaR (Value at Risk)
- Expected Shortfall (CVaR)
- Optimal F (Ralph Vince)
- Dynamic Position Sizing
- Anti-Martingale progression
- Equity Curve Trading
- Risk Parity
- Maximum Adverse Excursion (MAE)
- Maximum Favorable Excursion (MFE)
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque
import random

from ..core import VirtusLogger


class SizingMethod(Enum):
    """Métodos de position sizing."""
    FIXED_PERCENT = "fixed_percent"
    KELLY = "kelly"
    HALF_KELLY = "half_kelly"
    QUARTER_KELLY = "quarter_kelly"
    OPTIMAL_F = "optimal_f"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    RISK_PARITY = "risk_parity"
    ANTI_MARTINGALE = "anti_martingale"


class DrawdownState(Enum):
    """Estados de drawdown."""
    NORMAL = auto()
    WARNING = auto()
    DANGER = auto()
    CRITICAL = auto()
    RECOVERY = auto()


@dataclass
class TradeStatistics:
    """Estatísticas detalhadas de trading."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # Valores
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    
    # Ratios
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    payoff_ratio: float = 0.0
    
    # MAE/MFE
    average_mae: float = 0.0
    average_mfe: float = 0.0
    mae_mfe_ratio: float = 0.0
    
    # R-Multiples
    average_r: float = 0.0
    r_expectancy: float = 0.0
    sqn: float = 0.0  # System Quality Number
    
    def update(self, trades: List[Dict]) -> None:
        """Atualiza estatísticas com lista de trades."""
        if not trades:
            return
        
        self.total_trades = len(trades)
        
        profits = [t.get('profit', 0) for t in trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]
        
        self.winning_trades = len(wins)
        self.losing_trades = len(losses)
        
        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades
        
        if wins:
            self.gross_profit = sum(wins)
            self.largest_win = max(wins)
            self.average_win = np.mean(wins)
        
        if losses:
            self.gross_loss = abs(sum(losses))
            self.largest_loss = abs(min(losses))
            self.average_loss = abs(np.mean(losses))
        
        if self.gross_loss > 0:
            self.profit_factor = self.gross_profit / self.gross_loss
        
        if self.average_loss > 0:
            self.payoff_ratio = self.average_win / self.average_loss
        
        # Expectancy (per dollar risked)
        if self.average_loss > 0:
            self.expectancy = (
                self.win_rate * self.average_win - 
                (1 - self.win_rate) * self.average_loss
            )
        
        # R-Multiples
        r_values = [t.get('r_multiple', 0) for t in trades if 'r_multiple' in t]
        if r_values:
            self.average_r = np.mean(r_values)
            self.r_expectancy = np.mean(r_values)
            
            # SQN (System Quality Number)
            if len(r_values) >= 20:
                std_r = np.std(r_values)
                if std_r > 0:
                    self.sqn = (np.mean(r_values) / std_r) * np.sqrt(len(r_values))
        
        # Consecutive wins/losses
        self._calculate_consecutive(profits)
        
        # MAE/MFE
        maes = [t.get('mae', 0) for t in trades if 'mae' in t]
        mfes = [t.get('mfe', 0) for t in trades if 'mfe' in t]
        
        if maes:
            self.average_mae = np.mean(maes)
        if mfes:
            self.average_mfe = np.mean(mfes)
        if self.average_mfe > 0:
            self.mae_mfe_ratio = self.average_mae / self.average_mfe
    
    def _calculate_consecutive(self, profits: List[float]) -> None:
        """Calcula sequências consecutivas."""
        current_wins = 0
        current_losses = 0
        
        for p in profits:
            if p > 0:
                current_wins += 1
                current_losses = 0
                self.max_consecutive_wins = max(self.max_consecutive_wins, current_wins)
            elif p < 0:
                current_losses += 1
                current_wins = 0
                self.max_consecutive_losses = max(self.max_consecutive_losses, current_losses)
        
        self.consecutive_wins = current_wins
        self.consecutive_losses = current_losses


@dataclass
class VaRResult:
    """Resultado do cálculo de Value at Risk."""
    var_95: float
    var_99: float
    cvar_95: float  # Conditional VaR (Expected Shortfall)
    cvar_99: float
    max_expected_loss: float
    confidence_level: float
    holding_period: str
    method: str


@dataclass
class KellyResult:
    """Resultado do cálculo de Kelly."""
    full_kelly: float
    half_kelly: float
    quarter_kelly: float
    optimal_f: float
    recommended_size: float
    edge: float
    odds: float
    max_drawdown_expected: float


@dataclass 
class EquityCurveState:
    """Estado da equity curve."""
    above_ma: bool = True
    trend: str = "up"  # up, down, sideways
    regime: str = "normal"  # normal, drawdown, recovery
    trading_allowed: bool = True
    size_multiplier: float = 1.0
    
    # Métricas
    current_equity: float = 0.0
    peak_equity: float = 0.0
    ma_equity: float = 0.0
    drawdown_pct: float = 0.0
    days_in_drawdown: int = 0


class AdvancedRiskManager:
    """
    Gerenciador de risco avançado.
    
    Features:
    - Kelly Criterion e Optimal F
    - Monte Carlo VaR
    - Equity Curve Trading
    - Dynamic Position Sizing
    - Anti-Martingale
    - Risk Parity
    """
    
    def __init__(
        self,
        initial_capital: float = 10000,
        sizing_method: SizingMethod = SizingMethod.HALF_KELLY,
        max_position_size: float = 0.1,  # 10% max
        equity_curve_ma_period: int = 20,
        monte_carlo_simulations: int = 10000,
    ):
        self.logger = VirtusLogger.get_logger("advanced_risk")
        
        # Capital
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
        # Sizing
        self.sizing_method = sizing_method
        self.max_position_size = max_position_size
        
        # Equity Curve
        self.equity_ma_period = equity_curve_ma_period
        self.equity_history: deque = deque(maxlen=500)
        self.equity_state = EquityCurveState()
        
        # Monte Carlo
        self.mc_simulations = monte_carlo_simulations
        
        # Trade history
        self.trades: List[Dict] = []
        self.statistics = TradeStatistics()
        
        # Anti-Martingale
        self.anti_martingale_factor = 1.5
        self.max_anti_martingale_multiplier = 3.0
        
        # Drawdown management
        self.drawdown_state = DrawdownState.NORMAL
        self.drawdown_threshold_warning = 5.0  # 5%
        self.drawdown_threshold_danger = 10.0
        self.drawdown_threshold_critical = 15.0
        
        # Lock
        self._lock = asyncio.Lock()
    
    async def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float] = None,
        volatility: Optional[float] = None,
        correlation_factor: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Calcula tamanho de posição usando método avançado.
        
        Returns:
            Dict com detalhes completos do sizing
        """
        async with self._lock:
            # Atualiza estatísticas
            self.statistics.update(self.trades)
            
            # Calcula Kelly e Optimal F
            kelly_result = self._calculate_kelly()
            
            # Distância do stop
            risk_distance = abs(entry_price - stop_loss) / entry_price
            
            # Base size por método
            base_size = self._get_base_size_by_method(
                kelly_result,
                risk_distance,
                volatility
            )
            
            # Ajusta pelo estado da equity curve
            equity_multiplier = self._get_equity_curve_multiplier()
            
            # Ajusta por anti-martingale se em série positiva
            am_multiplier = self._get_anti_martingale_multiplier()
            
            # Ajusta por drawdown
            dd_multiplier = self._get_drawdown_multiplier()
            
            # Ajusta por correlação
            corr_multiplier = 1.0 / max(correlation_factor, 0.5)
            
            # Calcula tamanho final
            final_size = (
                base_size * 
                equity_multiplier * 
                am_multiplier * 
                dd_multiplier * 
                corr_multiplier
            )
            
            # Aplica limites
            final_size = min(final_size, self.max_position_size)
            final_size = max(final_size, 0.001)  # Mínimo 0.1%
            
            # Calcula valores
            risk_amount = self.current_capital * final_size
            position_value = risk_amount / risk_distance if risk_distance > 0 else 0
            
            return {
                'size_percent': round(final_size * 100, 2),
                'risk_amount': round(risk_amount, 2),
                'position_value': round(position_value, 2),
                
                'method': self.sizing_method.value,
                'kelly_full': round(kelly_result.full_kelly * 100, 2),
                'kelly_half': round(kelly_result.half_kelly * 100, 2),
                'optimal_f': round(kelly_result.optimal_f * 100, 2),
                
                'multipliers': {
                    'equity_curve': round(equity_multiplier, 2),
                    'anti_martingale': round(am_multiplier, 2),
                    'drawdown': round(dd_multiplier, 2),
                    'correlation': round(corr_multiplier, 2),
                },
                
                'equity_state': {
                    'above_ma': self.equity_state.above_ma,
                    'trend': self.equity_state.trend,
                    'trading_allowed': self.equity_state.trading_allowed,
                },
                
                'statistics': {
                    'win_rate': round(self.statistics.win_rate * 100, 1),
                    'profit_factor': round(self.statistics.profit_factor, 2),
                    'expectancy': round(self.statistics.expectancy, 2),
                    'sqn': round(self.statistics.sqn, 2),
                },
                
                'allowed': self.equity_state.trading_allowed and dd_multiplier > 0,
            }
    
    def _calculate_kelly(self) -> KellyResult:
        """
        Calcula Kelly Criterion e Optimal F.
        
        Kelly Formula: f* = (bp - q) / b
        Onde:
        - b = odds (payoff ratio)
        - p = probabilidade de ganho (win rate)
        - q = probabilidade de perda (1 - p)
        """
        win_rate = self.statistics.win_rate
        payoff = self.statistics.payoff_ratio
        
        if win_rate == 0 or payoff == 0:
            return KellyResult(
                full_kelly=0.02,
                half_kelly=0.01,
                quarter_kelly=0.005,
                optimal_f=0.02,
                recommended_size=0.01,
                edge=0,
                odds=0,
                max_drawdown_expected=0.10
            )
        
        # Kelly básico
        q = 1 - win_rate
        full_kelly = (win_rate * payoff - q) / payoff
        
        # Limita Kelly negativo
        full_kelly = max(full_kelly, 0)
        
        # Frações de Kelly (mais conservadoras)
        half_kelly = full_kelly / 2
        quarter_kelly = full_kelly / 4
        
        # Optimal F (Ralph Vince)
        # Encontra a fração que maximiza crescimento geométrico
        optimal_f = self._calculate_optimal_f()
        
        # Edge (vantagem esperada)
        edge = win_rate * payoff - q
        
        # Drawdown esperado com Kelly
        # Aproximação: max_dd ≈ -2 * Kelly * ln(0.95)
        max_dd_expected = abs(2 * full_kelly * np.log(0.95)) if full_kelly > 0 else 0.10
        
        # Recomendação baseada no método
        if self.sizing_method == SizingMethod.KELLY:
            recommended = full_kelly
        elif self.sizing_method == SizingMethod.HALF_KELLY:
            recommended = half_kelly
        elif self.sizing_method == SizingMethod.QUARTER_KELLY:
            recommended = quarter_kelly
        elif self.sizing_method == SizingMethod.OPTIMAL_F:
            recommended = optimal_f
        else:
            recommended = half_kelly
        
        return KellyResult(
            full_kelly=full_kelly,
            half_kelly=half_kelly,
            quarter_kelly=quarter_kelly,
            optimal_f=optimal_f,
            recommended_size=min(recommended, self.max_position_size),
            edge=edge,
            odds=payoff,
            max_drawdown_expected=max_dd_expected
        )
    
    def _calculate_optimal_f(self) -> float:
        """
        Calcula Optimal F usando método de Ralph Vince.
        
        Optimal F maximiza o TWR (Terminal Wealth Relative)
        """
        if len(self.trades) < 10:
            return 0.02  # Default 2%
        
        returns = [t.get('profit', 0) / self.initial_capital for t in self.trades[-100:]]
        
        if not returns:
            return 0.02
        
        # Maior perda (em valor absoluto)
        largest_loss = abs(min(returns)) if min(returns) < 0 else 0.01
        
        # Busca Optimal F testando diferentes valores
        best_f = 0.01
        best_twr = 1.0
        
        for f in np.arange(0.01, 0.50, 0.01):
            twr = 1.0
            
            for r in returns:
                # HPR = 1 + f * (-trade_return / largest_loss)
                hpr = 1 + f * (r / largest_loss)
                
                if hpr <= 0:
                    twr = 0
                    break
                
                twr *= hpr
            
            if twr > best_twr:
                best_twr = twr
                best_f = f
        
        return best_f
    
    def _get_base_size_by_method(
        self,
        kelly: KellyResult,
        risk_distance: float,
        volatility: Optional[float]
    ) -> float:
        """Retorna tamanho base pelo método selecionado."""
        if self.sizing_method == SizingMethod.FIXED_PERCENT:
            return 0.02  # 2% fixo
        
        elif self.sizing_method == SizingMethod.KELLY:
            return kelly.full_kelly
        
        elif self.sizing_method == SizingMethod.HALF_KELLY:
            return kelly.half_kelly
        
        elif self.sizing_method == SizingMethod.QUARTER_KELLY:
            return kelly.quarter_kelly
        
        elif self.sizing_method == SizingMethod.OPTIMAL_F:
            return kelly.optimal_f
        
        elif self.sizing_method == SizingMethod.VOLATILITY_ADJUSTED:
            if volatility and volatility > 0:
                # Target volatility de 2%
                target_vol = 0.02
                return target_vol / volatility
            return 0.02
        
        elif self.sizing_method == SizingMethod.RISK_PARITY:
            # Equal risk contribution
            # Simplificado: aloca para manter volatilidade igual entre posições
            if volatility and volatility > 0:
                return 0.02 / volatility
            return 0.02
        
        elif self.sizing_method == SizingMethod.ANTI_MARTINGALE:
            # Aumenta após ganhos, reduz após perdas
            base = kelly.half_kelly
            return base * self._get_anti_martingale_multiplier()
        
        return 0.02  # Default
    
    def _get_equity_curve_multiplier(self) -> float:
        """
        Calcula multiplicador baseado na equity curve.
        
        Equity Curve Trading:
        - Se equity acima da MA: trade normalmente
        - Se equity abaixo da MA: reduz ou para de operar
        """
        if not self.equity_history:
            return 1.0
        
        equity_list = list(self.equity_history)
        
        if len(equity_list) < self.equity_ma_period:
            return 1.0
        
        # Calcula MA
        ma = np.mean(equity_list[-self.equity_ma_period:])
        current = equity_list[-1]
        
        # Atualiza estado
        self.equity_state.current_equity = current
        self.equity_state.ma_equity = ma
        self.equity_state.above_ma = current >= ma
        
        # Determina trend
        if len(equity_list) >= 5:
            recent = equity_list[-5:]
            if all(recent[i] <= recent[i+1] for i in range(len(recent)-1)):
                self.equity_state.trend = "up"
            elif all(recent[i] >= recent[i+1] for i in range(len(recent)-1)):
                self.equity_state.trend = "down"
            else:
                self.equity_state.trend = "sideways"
        
        # Calcula multiplicador
        if current >= ma:
            # Acima da MA - pode aumentar levemente
            if self.equity_state.trend == "up":
                return 1.2
            return 1.0
        else:
            # Abaixo da MA
            distance_below = (ma - current) / ma
            
            if distance_below > 0.10:  # Mais de 10% abaixo
                self.equity_state.trading_allowed = False
                return 0.0
            elif distance_below > 0.05:  # 5-10% abaixo
                self.equity_state.trading_allowed = True
                return 0.25
            else:  # Menos de 5% abaixo
                self.equity_state.trading_allowed = True
                return 0.5
    
    def _get_anti_martingale_multiplier(self) -> float:
        """
        Calcula multiplicador anti-martingale.
        
        Anti-Martingale:
        - Aumenta após ganhos consecutivos
        - Reduz após perdas consecutivas
        """
        consecutive_wins = self.statistics.consecutive_wins
        consecutive_losses = self.statistics.consecutive_losses
        
        if consecutive_wins >= 3:
            # Aumenta progressivamente
            multiplier = 1 + (consecutive_wins - 2) * 0.25
            return min(multiplier, self.max_anti_martingale_multiplier)
        
        elif consecutive_losses >= 2:
            # Reduz progressivamente
            multiplier = 1 / (1 + consecutive_losses * 0.25)
            return max(multiplier, 0.25)
        
        return 1.0
    
    def _get_drawdown_multiplier(self) -> float:
        """Calcula multiplicador baseado no drawdown atual."""
        if self.peak_capital <= 0:
            return 1.0
        
        current_dd = (self.peak_capital - self.current_capital) / self.peak_capital * 100
        
        if current_dd >= self.drawdown_threshold_critical:
            self.drawdown_state = DrawdownState.CRITICAL
            return 0.0  # Para de operar
        
        elif current_dd >= self.drawdown_threshold_danger:
            self.drawdown_state = DrawdownState.DANGER
            return 0.25
        
        elif current_dd >= self.drawdown_threshold_warning:
            self.drawdown_state = DrawdownState.WARNING
            return 0.5
        
        else:
            self.drawdown_state = DrawdownState.NORMAL
            return 1.0
    
    async def calculate_var(
        self,
        holding_period_days: int = 1,
        confidence_levels: List[float] = [0.95, 0.99]
    ) -> VaRResult:
        """
        Calcula Value at Risk usando Monte Carlo.
        
        Args:
            holding_period_days: Período de holding
            confidence_levels: Níveis de confiança
            
        Returns:
            VaRResult com VaR e CVaR
        """
        if len(self.trades) < 20:
            return VaRResult(
                var_95=self.current_capital * 0.02,
                var_99=self.current_capital * 0.03,
                cvar_95=self.current_capital * 0.025,
                cvar_99=self.current_capital * 0.04,
                max_expected_loss=self.current_capital * 0.05,
                confidence_level=0.95,
                holding_period=f"{holding_period_days} day(s)",
                method="default"
            )
        
        # Retornos históricos
        returns = np.array([
            t.get('profit', 0) / self.initial_capital 
            for t in self.trades
        ])
        
        # Parâmetros da distribuição
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Monte Carlo Simulation
        simulated_returns = np.random.normal(
            mean_return * holding_period_days,
            std_return * np.sqrt(holding_period_days),
            self.mc_simulations
        )
        
        # Portfolio values
        simulated_values = self.current_capital * (1 + simulated_returns)
        
        # Perdas (valores negativos = perdas)
        losses = self.current_capital - simulated_values
        losses = np.sort(losses)
        
        # VaR
        var_95 = np.percentile(losses, 95)
        var_99 = np.percentile(losses, 99)
        
        # CVaR (Expected Shortfall)
        # Média das perdas além do VaR
        cvar_95 = np.mean(losses[losses >= var_95]) if np.any(losses >= var_95) else var_95
        cvar_99 = np.mean(losses[losses >= var_99]) if np.any(losses >= var_99) else var_99
        
        return VaRResult(
            var_95=round(var_95, 2),
            var_99=round(var_99, 2),
            cvar_95=round(cvar_95, 2),
            cvar_99=round(cvar_99, 2),
            max_expected_loss=round(max(losses), 2),
            confidence_level=0.95,
            holding_period=f"{holding_period_days} day(s)",
            method="monte_carlo"
        )
    
    async def simulate_future_equity(
        self,
        num_trades: int = 100,
        num_simulations: int = 1000
    ) -> Dict[str, Any]:
        """
        Simula cenários futuros de equity usando Monte Carlo.
        
        Returns:
            Dict com estatísticas das simulações
        """
        if len(self.trades) < 20:
            return {'error': 'Insufficient trade history'}
        
        returns = [
            t.get('profit', 0) / self.initial_capital 
            for t in self.trades
        ]
        
        # Parâmetros
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        final_equities = []
        max_drawdowns = []
        
        for _ in range(num_simulations):
            equity = self.current_capital
            peak = equity
            max_dd = 0
            
            # Simula sequência de trades
            sim_returns = np.random.normal(mean_return, std_return, num_trades)
            
            for r in sim_returns:
                equity *= (1 + r)
                peak = max(peak, equity)
                dd = (peak - equity) / peak
                max_dd = max(max_dd, dd)
            
            final_equities.append(equity)
            max_drawdowns.append(max_dd)
        
        final_equities = np.array(final_equities)
        max_drawdowns = np.array(max_drawdowns)
        
        return {
            'starting_equity': self.current_capital,
            'num_trades': num_trades,
            'num_simulations': num_simulations,
            
            'final_equity': {
                'mean': round(np.mean(final_equities), 2),
                'median': round(np.median(final_equities), 2),
                'std': round(np.std(final_equities), 2),
                'min': round(np.min(final_equities), 2),
                'max': round(np.max(final_equities), 2),
                'percentile_5': round(np.percentile(final_equities, 5), 2),
                'percentile_25': round(np.percentile(final_equities, 25), 2),
                'percentile_75': round(np.percentile(final_equities, 75), 2),
                'percentile_95': round(np.percentile(final_equities, 95), 2),
            },
            
            'max_drawdown': {
                'mean': round(np.mean(max_drawdowns) * 100, 2),
                'median': round(np.median(max_drawdowns) * 100, 2),
                'percentile_95': round(np.percentile(max_drawdowns, 95) * 100, 2),
                'worst_case': round(np.max(max_drawdowns) * 100, 2),
            },
            
            'probability': {
                'profit': round(np.mean(final_equities > self.current_capital) * 100, 1),
                'double': round(np.mean(final_equities > self.current_capital * 2) * 100, 1),
                'ruin_50pct': round(np.mean(final_equities < self.current_capital * 0.5) * 100, 1),
            }
        }
    
    async def record_trade(self, trade: Dict[str, Any]) -> None:
        """Registra um trade no histórico."""
        async with self._lock:
            # Adiciona timestamp se não existir
            if 'timestamp' not in trade:
                trade['timestamp'] = datetime.now()
            
            # Calcula R-Multiple se possível
            if 'initial_risk' in trade and trade.get('initial_risk', 0) > 0:
                trade['r_multiple'] = trade.get('profit', 0) / trade['initial_risk']
            
            self.trades.append(trade)
            
            # Atualiza capital
            self.current_capital += trade.get('profit', 0)
            self.peak_capital = max(self.peak_capital, self.current_capital)
            
            # Atualiza equity history
            self.equity_history.append(self.current_capital)
            
            # Atualiza estatísticas
            self.statistics.update(self.trades)
            
            self.logger.debug(
                f"Trade recorded: {trade.get('profit', 0):.2f} | "
                f"Capital: {self.current_capital:.2f}"
            )
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Gera relatório completo de risco."""
        kelly = self._calculate_kelly()
        
        return {
            'capital': {
                'initial': self.initial_capital,
                'current': round(self.current_capital, 2),
                'peak': round(self.peak_capital, 2),
                'drawdown_pct': round(
                    (self.peak_capital - self.current_capital) / self.peak_capital * 100
                    if self.peak_capital > 0 else 0, 2
                ),
            },
            
            'sizing': {
                'method': self.sizing_method.value,
                'kelly_full': round(kelly.full_kelly * 100, 2),
                'kelly_half': round(kelly.half_kelly * 100, 2),
                'optimal_f': round(kelly.optimal_f * 100, 2),
                'recommended': round(kelly.recommended_size * 100, 2),
                'max_allowed': self.max_position_size * 100,
            },
            
            'statistics': {
                'total_trades': self.statistics.total_trades,
                'win_rate': round(self.statistics.win_rate * 100, 1),
                'profit_factor': round(self.statistics.profit_factor, 2),
                'expectancy': round(self.statistics.expectancy, 2),
                'payoff_ratio': round(self.statistics.payoff_ratio, 2),
                'sqn': round(self.statistics.sqn, 2),
                'consecutive_wins': self.statistics.consecutive_wins,
                'consecutive_losses': self.statistics.consecutive_losses,
            },
            
            'equity_curve': {
                'above_ma': self.equity_state.above_ma,
                'trend': self.equity_state.trend,
                'trading_allowed': self.equity_state.trading_allowed,
            },
            
            'drawdown_state': self.drawdown_state.name,
            
            'edge': {
                'value': round(kelly.edge, 4),
                'has_edge': kelly.edge > 0,
            }
        }
