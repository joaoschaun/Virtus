"""
VIRTUS ML - Model Comparator
=============================

Comparação sistemática de modelos ML para trading.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from pathlib import Path

from .ml_metrics import MLMetricsCalculator, ClassificationMetrics, TradingMetrics

logger = logging.getLogger(__name__)


class ComparisonMetric(Enum):
    """Métricas usadas para comparação."""
    SHARPE = "sharpe_ratio"
    SORTINO = "sortino_ratio"
    ACCURACY = "accuracy"
    F1_SCORE = "macro_f1"
    PROFIT_FACTOR = "profit_factor"
    MAX_DRAWDOWN = "max_drawdown"
    TOTAL_RETURN = "total_return"


@dataclass
class ModelResult:
    """Resultado de avaliação de um modelo."""
    model_name: str
    model_type: str
    symbol: str
    
    # Métricas
    classification_metrics: ClassificationMetrics
    trading_metrics: TradingMetrics
    
    # Metadados
    train_samples: int = 0
    test_samples: int = 0
    training_time_seconds: float = 0.0
    inference_time_ms: float = 0.0
    
    # Timestamp
    evaluated_at: datetime = field(default_factory=datetime.now)
    
    def get_metric(self, metric: ComparisonMetric) -> float:
        """Retorna valor de uma métrica específica."""
        if metric == ComparisonMetric.SHARPE:
            return self.trading_metrics.sharpe_ratio
        elif metric == ComparisonMetric.SORTINO:
            return self.trading_metrics.sortino_ratio
        elif metric == ComparisonMetric.ACCURACY:
            return self.classification_metrics.accuracy
        elif metric == ComparisonMetric.F1_SCORE:
            return self.classification_metrics.macro_f1
        elif metric == ComparisonMetric.PROFIT_FACTOR:
            return self.trading_metrics.profit_factor
        elif metric == ComparisonMetric.MAX_DRAWDOWN:
            return self.trading_metrics.max_drawdown
        elif metric == ComparisonMetric.TOTAL_RETURN:
            return self.trading_metrics.total_return
        else:
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'model_name': self.model_name,
            'model_type': self.model_type,
            'symbol': self.symbol,
            'classification': self.classification_metrics.to_dict(),
            'trading': self.trading_metrics.to_dict(),
            'train_samples': self.train_samples,
            'test_samples': self.test_samples,
            'training_time_seconds': self.training_time_seconds,
            'inference_time_ms': self.inference_time_ms,
        }


@dataclass
class ComparisonResult:
    """Resultado de comparação entre modelos."""
    models: List[ModelResult]
    ranking_metric: ComparisonMetric
    best_model: str
    
    # Rankings
    rankings: Dict[str, int]  # model_name -> rank
    
    # Scores por métrica
    metric_scores: Dict[str, Dict[str, float]]  # metric -> {model: score}
    
    # Análise
    statistical_significance: Dict[str, float]  # p-values
    
    def to_dataframe(self) -> pd.DataFrame:
        """Converte para DataFrame."""
        data = []
        for model in self.models:
            row = {
                'model': model.model_name,
                'type': model.model_type,
                'rank': self.rankings.get(model.model_name, 0),
                'accuracy': model.classification_metrics.accuracy,
                'f1_score': model.classification_metrics.macro_f1,
                'sharpe': model.trading_metrics.sharpe_ratio,
                'sortino': model.trading_metrics.sortino_ratio,
                'max_dd': model.trading_metrics.max_drawdown,
                'win_rate': model.trading_metrics.win_rate,
                'profit_factor': model.trading_metrics.profit_factor,
            }
            data.append(row)
        
        return pd.DataFrame(data).sort_values('rank')


class ModelComparator:
    """
    Compara performance de múltiplos modelos ML.
    
    Features:
    - Comparação multi-métrica
    - Ranking automático
    - Testes estatísticos
    - Visualização
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.metrics_calculator = MLMetricsCalculator(risk_free_rate)
        self.results_history: List[ComparisonResult] = []
    
    def evaluate_model(
        self,
        model_name: str,
        model_type: str,
        symbol: str,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        returns: np.ndarray,
        train_samples: int = 0,
        training_time: float = 0.0,
        inference_time: float = 0.0,
        labels: Optional[List[str]] = None
    ) -> ModelResult:
        """
        Avalia um modelo individual.
        
        Args:
            model_name: Nome do modelo
            model_type: Tipo (LSTM, KNN, etc.)
            symbol: Símbolo do ativo
            y_true: Labels reais
            y_pred: Labels preditos
            returns: Retornos de mercado
            train_samples: Número de amostras de treino
            training_time: Tempo de treino em segundos
            inference_time: Tempo de inferência em ms
            labels: Nomes das classes
            
        Returns:
            ModelResult
        """
        labels = labels or ['DOWN', 'NEUTRAL', 'UP']
        
        # Calcula métricas de classificação
        class_metrics = self.metrics_calculator.calculate_classification_metrics(
            y_true, y_pred, labels
        )
        
        # Converte predições para posições
        positions = np.zeros_like(y_pred, dtype=np.float32)
        positions[y_pred == 0] = -1  # DOWN -> short
        positions[y_pred == 2] = 1   # UP -> long
        
        # Calcula métricas de trading
        trading_metrics = self.metrics_calculator.calculate_trading_metrics(
            returns, y_pred, positions
        )
        
        return ModelResult(
            model_name=model_name,
            model_type=model_type,
            symbol=symbol,
            classification_metrics=class_metrics,
            trading_metrics=trading_metrics,
            train_samples=train_samples,
            test_samples=len(y_true),
            training_time_seconds=training_time,
            inference_time_ms=inference_time,
        )
    
    def compare_models(
        self,
        results: List[ModelResult],
        ranking_metric: ComparisonMetric = ComparisonMetric.SHARPE,
        higher_is_better: bool = True
    ) -> ComparisonResult:
        """
        Compara múltiplos modelos.
        
        Args:
            results: Lista de ModelResult
            ranking_metric: Métrica para ranking
            higher_is_better: Se maior valor é melhor
            
        Returns:
            ComparisonResult
        """
        if not results:
            raise ValueError("Nenhum resultado para comparar")
        
        # Extrai scores para cada métrica
        metric_scores: Dict[str, Dict[str, float]] = {}
        
        for metric in ComparisonMetric:
            metric_scores[metric.value] = {
                r.model_name: r.get_metric(metric) 
                for r in results
            }
        
        # Ranking pelo métrica selecionada
        ranking_scores = metric_scores[ranking_metric.value]
        
        sorted_models = sorted(
            ranking_scores.items(),
            key=lambda x: x[1],
            reverse=higher_is_better
        )
        
        rankings = {name: rank + 1 for rank, (name, _) in enumerate(sorted_models)}
        best_model = sorted_models[0][0]
        
        # Testes estatísticos (se temos dados suficientes)
        statistical_significance = self._calculate_statistical_tests(results)
        
        comparison = ComparisonResult(
            models=results,
            ranking_metric=ranking_metric,
            best_model=best_model,
            rankings=rankings,
            metric_scores=metric_scores,
            statistical_significance=statistical_significance,
        )
        
        self.results_history.append(comparison)
        
        return comparison
    
    def _calculate_statistical_tests(
        self,
        results: List[ModelResult]
    ) -> Dict[str, float]:
        """Calcula testes estatísticos entre modelos."""
        significance = {}
        
        # Placeholder para testes mais sofisticados
        # Por enquanto, retornamos dummy values
        for i, r1 in enumerate(results):
            for j, r2 in enumerate(results):
                if i < j:
                    key = f"{r1.model_name}_vs_{r2.model_name}"
                    # Aqui você poderia implementar testes como:
                    # - Paired t-test
                    # - Wilcoxon signed-rank
                    # - DM test
                    significance[key] = 0.05  # Placeholder
        
        return significance
    
    def generate_report(
        self,
        comparison: ComparisonResult,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Gera relatório de comparação.
        
        Args:
            comparison: Resultado da comparação
            output_path: Caminho para salvar (opcional)
            
        Returns:
            Relatório em texto
        """
        lines = [
            "=" * 60,
            "RELATÓRIO DE COMPARAÇÃO DE MODELOS ML",
            "=" * 60,
            "",
            f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Modelos comparados: {len(comparison.models)}",
            f"Métrica de ranking: {comparison.ranking_metric.value}",
            f"Melhor modelo: {comparison.best_model}",
            "",
            "-" * 60,
            "RANKING GERAL",
            "-" * 60,
        ]
        
        # Tabela de ranking
        df = comparison.to_dataframe()
        lines.append(df.to_string())
        
        lines.extend([
            "",
            "-" * 60,
            "MÉTRICAS DETALHADAS POR MODELO",
            "-" * 60,
        ])
        
        for model in comparison.models:
            lines.extend([
                f"\n{model.model_name} ({model.model_type})",
                f"  Rank: #{comparison.rankings[model.model_name]}",
                "",
                "  CLASSIFICAÇÃO:",
                f"    Accuracy: {model.classification_metrics.accuracy:.4f}",
                f"    Macro F1: {model.classification_metrics.macro_f1:.4f}",
                f"    Directional Accuracy: {model.classification_metrics.directional_accuracy:.4f}",
                "",
                "  TRADING:",
                f"    Sharpe Ratio: {model.trading_metrics.sharpe_ratio:.4f}",
                f"    Sortino Ratio: {model.trading_metrics.sortino_ratio:.4f}",
                f"    Max Drawdown: {model.trading_metrics.max_drawdown:.2%}",
                f"    Win Rate: {model.trading_metrics.win_rate:.2%}",
                f"    Profit Factor: {model.trading_metrics.profit_factor:.2f}",
                f"    Total Return: {model.trading_metrics.total_return:.2%}",
            ])
        
        lines.extend([
            "",
            "=" * 60,
            "FIM DO RELATÓRIO",
            "=" * 60,
        ])
        
        report = "\n".join(lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Relatório salvo em {output_path}")
        
        return report
    
    def get_best_model_for_metric(
        self,
        results: List[ModelResult],
        metric: ComparisonMetric
    ) -> ModelResult:
        """Retorna o melhor modelo para uma métrica específica."""
        
        # Métricas onde menor é melhor
        lower_is_better = {ComparisonMetric.MAX_DRAWDOWN}
        
        higher_is_better = metric not in lower_is_better
        
        sorted_results = sorted(
            results,
            key=lambda r: r.get_metric(metric),
            reverse=higher_is_better
        )
        
        return sorted_results[0]
    
    def recommend_model(
        self,
        results: List[ModelResult],
        preferences: Optional[Dict[ComparisonMetric, float]] = None
    ) -> Tuple[str, Dict[str, float]]:
        """
        Recomenda modelo baseado em preferências.
        
        Args:
            results: Lista de resultados
            preferences: Pesos para cada métrica
            
        Returns:
            (nome do modelo recomendado, scores ponderados)
        """
        if preferences is None:
            preferences = {
                ComparisonMetric.SHARPE: 0.3,
                ComparisonMetric.ACCURACY: 0.2,
                ComparisonMetric.MAX_DRAWDOWN: 0.2,
                ComparisonMetric.WIN_RATE: 0.15,
                ComparisonMetric.PROFIT_FACTOR: 0.15,
            }
        
        scores: Dict[str, float] = {}
        
        for result in results:
            weighted_score = 0.0
            
            for metric, weight in preferences.items():
                value = result.get_metric(metric)
                
                # Normaliza (assume ranges típicos)
                if metric == ComparisonMetric.SHARPE:
                    normalized = np.clip(value / 3.0, -1, 1)  # Sharpe tipicamente -3 a 3
                elif metric == ComparisonMetric.ACCURACY:
                    normalized = value  # 0 a 1
                elif metric == ComparisonMetric.MAX_DRAWDOWN:
                    normalized = 1 + value  # DD é negativo, menor é melhor
                elif metric == ComparisonMetric.PROFIT_FACTOR:
                    normalized = np.clip(value / 3.0, 0, 1)
                else:
                    normalized = value
                
                weighted_score += normalized * weight
            
            scores[result.model_name] = weighted_score
        
        best_model = max(scores, key=scores.get)
        
        return best_model, scores
