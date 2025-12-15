"""
VIRTUS ML - ML Backtester
==========================

Backtesting específico para modelos ML de trading.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from .ml_metrics import MLMetricsCalculator, TradingMetrics, ClassificationMetrics

logger = logging.getLogger(__name__)


class BacktestMode(Enum):
    """Modo de backtesting."""
    SIMPLE = "simple"              # Treino único
    WALK_FORWARD = "walk_forward"  # Walk-forward
    ANCHORED = "anchored"          # Expanding window
    ROLLING = "rolling"            # Rolling window


@dataclass
class BacktestConfig:
    """Configuração de backtest."""
    # Modo
    mode: BacktestMode = BacktestMode.WALK_FORWARD
    
    # Walk-forward settings
    train_window: int = 252   # ~1 ano para dados diários
    test_window: int = 21     # ~1 mês
    step_size: int = 21       # Passo entre folds
    
    # Trading settings
    initial_capital: float = 10000.0
    position_size: float = 1.0  # Fração do capital
    transaction_cost: float = 0.0001  # 1 pip spread
    slippage: float = 0.0001
    
    # Risk management
    max_position: float = 1.0
    stop_loss_pct: Optional[float] = 0.02
    take_profit_pct: Optional[float] = 0.04
    
    # Purge settings (evita leakage)
    purge_gap: int = 1  # Períodos entre treino e teste


@dataclass
class Trade:
    """Representa uma operação."""
    entry_time: datetime
    exit_time: datetime
    direction: int  # 1=long, -1=short
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    return_pct: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entry_time': self.entry_time,
            'exit_time': self.exit_time,
            'direction': 'LONG' if self.direction > 0 else 'SHORT',
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'size': self.size,
            'pnl': self.pnl,
            'return_pct': self.return_pct,
        }


@dataclass
class BacktestResult:
    """Resultado de um backtest."""
    # Performance
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    
    # Win/Loss
    win_rate: float
    profit_factor: float
    total_trades: int
    
    # Equity curve
    equity_curve: pd.Series
    daily_returns: pd.Series
    
    # Trades
    trades: List[Trade]
    
    # Classification
    classification_metrics: Optional[ClassificationMetrics] = None
    
    # Metadados
    config: BacktestConfig = field(default_factory=BacktestConfig)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'total_trades': self.total_trades,
        }


class MLBacktester:
    """
    Backtester especializado para modelos ML.
    
    Features:
    - Walk-forward testing
    - Purged K-Fold
    - Custos de transação
    - Métricas de classificação e trading
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.metrics_calculator = MLMetricsCalculator()
    
    def backtest(
        self,
        model,
        data: pd.DataFrame,
        feature_columns: List[str],
        target_column: str = 'target',
        price_column: str = 'close',
        train_func: Optional[Callable] = None,
        predict_func: Optional[Callable] = None
    ) -> BacktestResult:
        """
        Executa backtest do modelo.
        
        Args:
            model: Modelo ML (com fit/predict)
            data: DataFrame com features e target
            feature_columns: Colunas de features
            target_column: Coluna target
            price_column: Coluna de preços
            train_func: Função de treino customizada
            predict_func: Função de predição customizada
            
        Returns:
            BacktestResult
        """
        if self.config.mode == BacktestMode.WALK_FORWARD:
            return self._walk_forward_backtest(
                model, data, feature_columns, target_column, 
                price_column, train_func, predict_func
            )
        else:
            return self._simple_backtest(
                model, data, feature_columns, target_column,
                price_column, train_func, predict_func
            )
    
    def _walk_forward_backtest(
        self,
        model,
        data: pd.DataFrame,
        feature_columns: List[str],
        target_column: str,
        price_column: str,
        train_func: Optional[Callable],
        predict_func: Optional[Callable]
    ) -> BacktestResult:
        """Walk-forward backtesting."""
        
        all_predictions = []
        all_actuals = []
        all_returns = []
        all_trades = []
        equity = [self.config.initial_capital]
        
        n = len(data)
        train_window = self.config.train_window
        test_window = self.config.test_window
        step_size = self.config.step_size
        purge = self.config.purge_gap
        
        # Walk-forward loop
        for start in range(0, n - train_window - test_window - purge, step_size):
            # Define splits
            train_end = start + train_window
            test_start = train_end + purge
            test_end = min(test_start + test_window, n)
            
            # Dados
            train_data = data.iloc[start:train_end]
            test_data = data.iloc[test_start:test_end]
            
            if len(test_data) == 0:
                continue
            
            # Features e targets
            X_train = train_data[feature_columns].values
            y_train = train_data[target_column].values
            X_test = test_data[feature_columns].values
            y_test = test_data[target_column].values
            
            # Treina
            if train_func:
                train_func(model, X_train, y_train)
            elif hasattr(model, 'fit'):
                model.fit(X_train, y_train)
            
            # Prediz
            if predict_func:
                predictions = predict_func(model, X_test)
            elif hasattr(model, 'predict'):
                predictions = model.predict(X_test)
            else:
                raise ValueError("Model must have predict method")
            
            # Armazena
            all_predictions.extend(predictions)
            all_actuals.extend(y_test)
            
            # Calcula retornos
            prices = test_data[price_column].values
            returns = np.diff(prices) / prices[:-1]
            
            # Posições baseadas nas predições
            positions = self._predictions_to_positions(predictions[:-1])
            
            # Retornos da estratégia (com custos)
            strategy_returns = self._apply_trading_costs(
                returns, positions
            )
            
            all_returns.extend(strategy_returns)
            
            # Atualiza equity
            for ret in strategy_returns:
                equity.append(equity[-1] * (1 + ret))
            
            # Registra trades
            trades = self._extract_trades(
                test_data.index[:-1],
                prices[:-1],
                prices[1:],
                positions
            )
            all_trades.extend(trades)
        
        # Converte para arrays
        predictions = np.array(all_predictions)
        actuals = np.array(all_actuals)
        returns = np.array(all_returns)
        
        # Métricas de classificação
        class_metrics = self.metrics_calculator.calculate_classification_metrics(
            actuals[:len(predictions)], predictions
        )
        
        # Métricas de trading
        trading_metrics = self.metrics_calculator.calculate_trading_metrics(returns)
        
        # Equity curve
        equity_series = pd.Series(equity)
        returns_series = pd.Series(returns)
        
        return BacktestResult(
            total_return=trading_metrics.total_return,
            annual_return=trading_metrics.annual_return,
            sharpe_ratio=trading_metrics.sharpe_ratio,
            sortino_ratio=trading_metrics.sortino_ratio,
            max_drawdown=trading_metrics.max_drawdown,
            win_rate=trading_metrics.win_rate,
            profit_factor=trading_metrics.profit_factor,
            total_trades=len(all_trades),
            equity_curve=equity_series,
            daily_returns=returns_series,
            trades=all_trades,
            classification_metrics=class_metrics,
            config=self.config,
            start_date=data.index[0] if hasattr(data.index[0], 'date') else None,
            end_date=data.index[-1] if hasattr(data.index[-1], 'date') else None,
        )
    
    def _simple_backtest(
        self,
        model,
        data: pd.DataFrame,
        feature_columns: List[str],
        target_column: str,
        price_column: str,
        train_func: Optional[Callable],
        predict_func: Optional[Callable]
    ) -> BacktestResult:
        """Simple backtesting (treino/teste único)."""
        
        # Split simples
        split_idx = int(len(data) * 0.8)
        
        train_data = data.iloc[:split_idx]
        test_data = data.iloc[split_idx:]
        
        # Treina
        X_train = train_data[feature_columns].values
        y_train = train_data[target_column].values
        
        if train_func:
            train_func(model, X_train, y_train)
        elif hasattr(model, 'fit'):
            model.fit(X_train, y_train)
        
        # Prediz
        X_test = test_data[feature_columns].values
        
        if predict_func:
            predictions = predict_func(model, X_test)
        else:
            predictions = model.predict(X_test)
        
        y_test = test_data[target_column].values
        prices = test_data[price_column].values
        
        # Calcula retornos
        returns = np.diff(prices) / prices[:-1]
        positions = self._predictions_to_positions(predictions[:-1])
        strategy_returns = self._apply_trading_costs(returns, positions)
        
        # Equity
        equity = [self.config.initial_capital]
        for ret in strategy_returns:
            equity.append(equity[-1] * (1 + ret))
        
        # Métricas
        class_metrics = self.metrics_calculator.calculate_classification_metrics(
            y_test[:len(predictions)], predictions
        )
        trading_metrics = self.metrics_calculator.calculate_trading_metrics(
            strategy_returns
        )
        
        return BacktestResult(
            total_return=trading_metrics.total_return,
            annual_return=trading_metrics.annual_return,
            sharpe_ratio=trading_metrics.sharpe_ratio,
            sortino_ratio=trading_metrics.sortino_ratio,
            max_drawdown=trading_metrics.max_drawdown,
            win_rate=trading_metrics.win_rate,
            profit_factor=trading_metrics.profit_factor,
            total_trades=len(positions[positions != 0]),
            equity_curve=pd.Series(equity),
            daily_returns=pd.Series(strategy_returns),
            trades=[],
            classification_metrics=class_metrics,
            config=self.config,
        )
    
    def _predictions_to_positions(self, predictions: np.ndarray) -> np.ndarray:
        """Converte predições para posições."""
        # 0=DOWN -> -1, 1=NEUTRAL -> 0, 2=UP -> 1
        positions = np.zeros_like(predictions, dtype=np.float32)
        positions[predictions == 0] = -1 * self.config.position_size
        positions[predictions == 2] = 1 * self.config.position_size
        
        # Aplica limite de posição
        positions = np.clip(
            positions, 
            -self.config.max_position, 
            self.config.max_position
        )
        
        return positions
    
    def _apply_trading_costs(
        self,
        returns: np.ndarray,
        positions: np.ndarray
    ) -> np.ndarray:
        """Aplica custos de transação e slippage."""
        
        # Retornos da estratégia
        strategy_returns = returns * positions
        
        # Custos quando há mudança de posição
        position_changes = np.abs(np.diff(np.concatenate([[0], positions])))
        costs = position_changes * (self.config.transaction_cost + self.config.slippage)
        
        # Subtrai custos
        strategy_returns = strategy_returns - costs[:len(strategy_returns)]
        
        return strategy_returns
    
    def _extract_trades(
        self,
        timestamps,
        entry_prices: np.ndarray,
        exit_prices: np.ndarray,
        positions: np.ndarray
    ) -> List[Trade]:
        """Extrai trades das posições."""
        trades = []
        current_position = 0
        entry_idx = None
        
        for i, pos in enumerate(positions):
            if pos != current_position:
                if current_position != 0 and entry_idx is not None:
                    # Fecha posição anterior
                    direction = 1 if current_position > 0 else -1
                    entry_price = entry_prices[entry_idx]
                    exit_price = exit_prices[i]
                    
                    pnl = (exit_price - entry_price) * direction * abs(current_position)
                    return_pct = pnl / entry_price
                    
                    trade = Trade(
                        entry_time=timestamps[entry_idx] if hasattr(timestamps[entry_idx], 'strftime') else datetime.now(),
                        exit_time=timestamps[i] if hasattr(timestamps[i], 'strftime') else datetime.now(),
                        direction=direction,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        size=abs(current_position),
                        pnl=pnl,
                        return_pct=return_pct,
                    )
                    trades.append(trade)
                
                if pos != 0:
                    # Abre nova posição
                    entry_idx = i
                
                current_position = pos
        
        return trades
    
    def run_multiple_symbols(
        self,
        model_factory: Callable,
        datasets: Dict[str, pd.DataFrame],
        feature_columns: List[str],
        target_column: str = 'target'
    ) -> Dict[str, BacktestResult]:
        """
        Executa backtest em múltiplos símbolos.
        
        Args:
            model_factory: Função que cria novo modelo
            datasets: {symbol: DataFrame}
            feature_columns: Colunas de features
            target_column: Coluna target
            
        Returns:
            {symbol: BacktestResult}
        """
        results = {}
        
        for symbol, data in datasets.items():
            logger.info(f"Backtesting {symbol}...")
            
            model = model_factory()
            result = self.backtest(
                model, data, feature_columns, target_column
            )
            results[symbol] = result
            
            logger.info(
                f"{symbol}: Return={result.total_return:.2%}, "
                f"Sharpe={result.sharpe_ratio:.2f}"
            )
        
        return results
    
    def generate_report(self, result: BacktestResult) -> str:
        """Gera relatório textual do backtest."""
        
        lines = [
            "=" * 50,
            "RELATÓRIO DE BACKTEST ML",
            "=" * 50,
            "",
            f"Período: {result.start_date} a {result.end_date}",
            f"Modo: {result.config.mode.value}",
            "",
            "-" * 50,
            "PERFORMANCE",
            "-" * 50,
            f"Retorno Total: {result.total_return:.2%}",
            f"Retorno Anual: {result.annual_return:.2%}",
            f"Sharpe Ratio: {result.sharpe_ratio:.3f}",
            f"Sortino Ratio: {result.sortino_ratio:.3f}",
            f"Max Drawdown: {result.max_drawdown:.2%}",
            "",
            "-" * 50,
            "TRADES",
            "-" * 50,
            f"Total Trades: {result.total_trades}",
            f"Win Rate: {result.win_rate:.2%}",
            f"Profit Factor: {result.profit_factor:.2f}",
            "",
        ]
        
        if result.classification_metrics:
            lines.extend([
                "-" * 50,
                "CLASSIFICAÇÃO",
                "-" * 50,
                f"Accuracy: {result.classification_metrics.accuracy:.4f}",
                f"Macro F1: {result.classification_metrics.macro_f1:.4f}",
                f"Dir. Accuracy: {result.classification_metrics.directional_accuracy:.4f}",
                "",
            ])
        
        lines.extend([
            "=" * 50,
        ])
        
        return "\n".join(lines)
