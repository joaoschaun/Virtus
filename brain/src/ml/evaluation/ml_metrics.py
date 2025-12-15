"""
VIRTUS ML - ML Metrics
=======================

Métricas especializadas para avaliação de modelos de trading.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ClassificationMetrics:
    """Métricas de classificação."""
    accuracy: float
    precision: Dict[str, float]
    recall: Dict[str, float]
    f1_score: Dict[str, float]
    confusion_matrix: np.ndarray
    
    # Macro/Weighted
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0
    weighted_f1: float = 0.0
    
    # Trading specific
    directional_accuracy: float = 0.0  # UP/DOWN corretos
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'accuracy': self.accuracy,
            'macro_precision': self.macro_precision,
            'macro_recall': self.macro_recall,
            'macro_f1': self.macro_f1,
            'weighted_f1': self.weighted_f1,
            'directional_accuracy': self.directional_accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
        }


@dataclass
class TradingMetrics:
    """Métricas específicas de trading."""
    # Returns
    total_return: float = 0.0
    annual_return: float = 0.0
    monthly_return: float = 0.0
    
    # Risk
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # em períodos
    
    # Win/Loss
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    
    # Trades
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_trade_duration: float = 0.0
    
    # Consistency
    recovery_factor: float = 0.0
    ulcer_index: float = 0.0
    
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
            'expectancy': self.expectancy,
        }


class MLMetricsCalculator:
    """
    Calculador de métricas ML para trading.
    
    Combina métricas de classificação tradicionais com
    métricas específicas de trading para avaliar modelos.
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
    
    def calculate_classification_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        labels: Optional[List[str]] = None
    ) -> ClassificationMetrics:
        """
        Calcula métricas de classificação.
        
        Args:
            y_true: Labels reais
            y_pred: Labels preditos
            labels: Nomes das classes
            
        Returns:
            ClassificationMetrics
        """
        labels = labels or ['DOWN', 'NEUTRAL', 'UP']
        n_classes = len(labels)
        
        # Confusion Matrix
        cm = self._confusion_matrix(y_true, y_pred, n_classes)
        
        # Accuracy
        accuracy = np.sum(y_true == y_pred) / len(y_true)
        
        # Per-class metrics
        precision = {}
        recall = {}
        f1 = {}
        
        for i, label in enumerate(labels):
            tp = cm[i, i]
            fp = np.sum(cm[:, i]) - tp
            fn = np.sum(cm[i, :]) - tp
            
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1_score = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
            
            precision[label] = prec
            recall[label] = rec
            f1[label] = f1_score
        
        # Macro metrics
        macro_precision = np.mean(list(precision.values()))
        macro_recall = np.mean(list(recall.values()))
        macro_f1 = np.mean(list(f1.values()))
        
        # Weighted F1
        supports = [np.sum(y_true == i) for i in range(n_classes)]
        total_support = sum(supports)
        weighted_f1 = sum(
            f1[labels[i]] * supports[i] / total_support 
            for i in range(n_classes)
        ) if total_support > 0 else 0
        
        # Directional accuracy (ignora NEUTRAL)
        if len(labels) >= 3:  # DOWN, NEUTRAL, UP
            directional_mask = (y_true != 1) | (y_pred != 1)  # Exclui quando ambos são NEUTRAL
            if np.sum(directional_mask) > 0:
                directional_accuracy = np.sum(
                    y_true[directional_mask] == y_pred[directional_mask]
                ) / np.sum(directional_mask)
            else:
                directional_accuracy = 0.0
        else:
            directional_accuracy = accuracy
        
        return ClassificationMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            confusion_matrix=cm,
            macro_precision=macro_precision,
            macro_recall=macro_recall,
            macro_f1=macro_f1,
            weighted_f1=weighted_f1,
            directional_accuracy=directional_accuracy,
        )
    
    def _confusion_matrix(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        n_classes: int
    ) -> np.ndarray:
        """Calcula confusion matrix."""
        cm = np.zeros((n_classes, n_classes), dtype=np.int32)
        
        for true, pred in zip(y_true, y_pred):
            cm[int(true), int(pred)] += 1
        
        return cm
    
    def calculate_trading_metrics(
        self,
        returns: np.ndarray,
        predictions: Optional[np.ndarray] = None,
        positions: Optional[np.ndarray] = None,
        periods_per_year: int = 252
    ) -> TradingMetrics:
        """
        Calcula métricas de trading.
        
        Args:
            returns: Retornos diários
            predictions: Predições (opcional)
            positions: Posições tomadas (opcional)
            periods_per_year: Períodos por ano
            
        Returns:
            TradingMetrics
        """
        # Se temos posições, calcula retornos da estratégia
        if positions is not None:
            strategy_returns = returns * np.roll(positions, 1)
            strategy_returns[0] = 0
        else:
            strategy_returns = returns
        
        # Returns
        total_return = np.nanprod(1 + strategy_returns) - 1
        n_periods = len(strategy_returns)
        annual_return = (1 + total_return) ** (periods_per_year / n_periods) - 1 if n_periods > 0 else 0
        monthly_return = (1 + annual_return) ** (1/12) - 1
        
        # Risk metrics
        sharpe = self._sharpe_ratio(strategy_returns, periods_per_year)
        sortino = self._sortino_ratio(strategy_returns, periods_per_year)
        max_dd, max_dd_duration = self._max_drawdown(strategy_returns)
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0
        
        # Win/Loss
        wins = strategy_returns[strategy_returns > 0]
        losses = strategy_returns[strategy_returns < 0]
        
        win_rate = len(wins) / len(strategy_returns) if len(strategy_returns) > 0 else 0
        avg_win = np.mean(wins) if len(wins) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        
        gross_profit = np.sum(wins) if len(wins) > 0 else 0
        gross_loss = abs(np.sum(losses)) if len(losses) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Expectancy
        expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss
        
        # Recovery factor
        recovery_factor = total_return / abs(max_dd) if max_dd != 0 else 0
        
        # Ulcer index
        ulcer = self._ulcer_index(strategy_returns)
        
        return TradingMetrics(
            total_return=total_return,
            annual_return=annual_return,
            monthly_return=monthly_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expectancy,
            total_trades=len(strategy_returns),
            winning_trades=len(wins),
            losing_trades=len(losses),
            recovery_factor=recovery_factor,
            ulcer_index=ulcer,
        )
    
    def _sharpe_ratio(
        self,
        returns: np.ndarray,
        periods_per_year: int
    ) -> float:
        """Calcula Sharpe Ratio."""
        excess_returns = returns - self.risk_free_rate / periods_per_year
        
        mean_excess = np.nanmean(excess_returns)
        std_excess = np.nanstd(excess_returns)
        
        if std_excess == 0:
            return 0.0
        
        return mean_excess / std_excess * np.sqrt(periods_per_year)
    
    def _sortino_ratio(
        self,
        returns: np.ndarray,
        periods_per_year: int
    ) -> float:
        """Calcula Sortino Ratio."""
        excess_returns = returns - self.risk_free_rate / periods_per_year
        
        mean_excess = np.nanmean(excess_returns)
        negative_returns = excess_returns[excess_returns < 0]
        
        if len(negative_returns) == 0:
            return float('inf')
        
        downside_std = np.nanstd(negative_returns)
        
        if downside_std == 0:
            return float('inf')
        
        return mean_excess / downside_std * np.sqrt(periods_per_year)
    
    def _max_drawdown(
        self,
        returns: np.ndarray
    ) -> Tuple[float, int]:
        """Calcula maximum drawdown e duração."""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        
        drawdowns = (cumulative - running_max) / running_max
        max_dd = np.min(drawdowns)
        
        # Duração do max drawdown
        max_dd_idx = np.argmin(drawdowns)
        peak_idx = np.argmax(cumulative[:max_dd_idx + 1])
        duration = max_dd_idx - peak_idx
        
        return max_dd, duration
    
    def _ulcer_index(self, returns: np.ndarray) -> float:
        """Calcula Ulcer Index."""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        
        drawdowns = (cumulative - running_max) / running_max
        squared_dd = drawdowns ** 2
        
        return np.sqrt(np.mean(squared_dd))
    
    def calculate_all_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        returns: np.ndarray,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calcula todas as métricas.
        
        Args:
            y_true: Labels reais
            y_pred: Labels preditos
            returns: Retornos de mercado
            labels: Nomes das classes
            
        Returns:
            Dicionário com todas as métricas
        """
        # Classification metrics
        class_metrics = self.calculate_classification_metrics(y_true, y_pred, labels)
        
        # Converte predições para posições
        # 0=DOWN -> -1, 1=NEUTRAL -> 0, 2=UP -> 1
        positions = np.zeros_like(y_pred, dtype=np.float32)
        positions[y_pred == 0] = -1
        positions[y_pred == 2] = 1
        
        # Trading metrics
        trading_metrics = self.calculate_trading_metrics(returns, y_pred, positions)
        
        return {
            'classification': class_metrics.to_dict(),
            'trading': trading_metrics.to_dict(),
        }


def calculate_information_coefficient(
    predictions: np.ndarray,
    returns: np.ndarray
) -> float:
    """
    Calcula Information Coefficient (IC).
    Correlação entre predições e retornos realizados.
    """
    # Remove NaN
    mask = ~(np.isnan(predictions) | np.isnan(returns))
    predictions = predictions[mask]
    returns = returns[mask]
    
    if len(predictions) < 2:
        return 0.0
    
    # Spearman correlation
    from scipy import stats
    ic, _ = stats.spearmanr(predictions, returns)
    
    return ic


def calculate_hit_rate(
    predictions: np.ndarray,
    returns: np.ndarray
) -> float:
    """
    Calcula hit rate (taxa de acerto direcional).
    """
    pred_direction = np.sign(predictions)
    actual_direction = np.sign(returns)
    
    correct = np.sum(pred_direction == actual_direction)
    total = len(predictions)
    
    return correct / total if total > 0 else 0.0
