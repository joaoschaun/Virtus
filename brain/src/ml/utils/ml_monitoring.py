"""
VIRTUS ML - Monitoring
=======================

Monitoramento de modelos ML em produção.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import threading
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PredictionRecord:
    """Registro de uma predição."""
    timestamp: datetime
    model_name: str
    symbol: str
    
    # Predição
    predicted_class: int
    confidence: float
    probabilities: List[float]
    
    # Ground truth (preenchido depois)
    actual_class: Optional[int] = None
    actual_return: Optional[float] = None
    
    # Performance
    is_correct: Optional[bool] = None
    pnl: Optional[float] = None


@dataclass
class DriftMetrics:
    """Métricas de drift."""
    feature_drift: Dict[str, float]
    prediction_drift: float
    confidence_drift: float
    
    is_drifting: bool
    drift_score: float
    
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """Métricas de performance em tempo real."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    
    win_rate: float
    avg_pnl: float
    sharpe_ratio: float
    
    total_predictions: int
    correct_predictions: int
    
    period_start: datetime
    period_end: datetime


class MLMonitor:
    """
    Monitor de modelos ML em produção.
    
    Features:
    - Tracking de predições
    - Detecção de drift
    - Métricas em tempo real
    - Alertas automáticos
    """
    
    def __init__(
        self,
        model_name: str,
        window_size: int = 1000,
        drift_threshold: float = 0.1,
        performance_threshold: float = 0.5,
        log_dir: Optional[Path] = None
    ):
        self.model_name = model_name
        self.window_size = window_size
        self.drift_threshold = drift_threshold
        self.performance_threshold = performance_threshold
        self.log_dir = log_dir
        
        # Storage
        self.predictions: deque = deque(maxlen=window_size)
        self.feature_history: deque = deque(maxlen=window_size)
        
        # Baseline (definido durante warm-up)
        self.baseline_feature_stats: Optional[Dict[str, Tuple[float, float]]] = None
        self.baseline_prediction_dist: Optional[np.ndarray] = None
        
        # Estado
        self.is_warmup = True
        self.warmup_count = 0
        self.warmup_target = min(100, window_size // 10)
        
        # Métricas acumuladas
        self.total_predictions = 0
        self.correct_predictions = 0
        self.total_pnl = 0.0
        
        # Threading
        self._lock = threading.Lock()
        
        # Alertas
        self.alert_callbacks: List[callable] = []
    
    def log_prediction(
        self,
        symbol: str,
        predicted_class: int,
        confidence: float,
        probabilities: List[float],
        features: Optional[np.ndarray] = None
    ) -> PredictionRecord:
        """
        Registra uma predição.
        
        Args:
            symbol: Símbolo do ativo
            predicted_class: Classe predita
            confidence: Confiança
            probabilities: Probabilidades por classe
            features: Features usadas (opcional)
            
        Returns:
            PredictionRecord
        """
        with self._lock:
            record = PredictionRecord(
                timestamp=datetime.now(),
                model_name=self.model_name,
                symbol=symbol,
                predicted_class=predicted_class,
                confidence=confidence,
                probabilities=probabilities,
            )
            
            self.predictions.append(record)
            
            if features is not None:
                self.feature_history.append(features)
            
            self.total_predictions += 1
            
            # Atualiza warmup
            if self.is_warmup:
                self.warmup_count += 1
                if self.warmup_count >= self.warmup_target:
                    self._finalize_warmup()
            
            return record
    
    def log_outcome(
        self,
        prediction_timestamp: datetime,
        actual_class: int,
        actual_return: float
    ):
        """
        Registra o outcome real de uma predição.
        
        Args:
            prediction_timestamp: Timestamp da predição
            actual_class: Classe real
            actual_return: Retorno realizado
        """
        with self._lock:
            # Encontra predição correspondente
            for record in self.predictions:
                if abs((record.timestamp - prediction_timestamp).total_seconds()) < 60:
                    record.actual_class = actual_class
                    record.actual_return = actual_return
                    record.is_correct = record.predicted_class == actual_class
                    
                    # Calcula PnL
                    if record.predicted_class == 2:  # UP -> long
                        record.pnl = actual_return
                    elif record.predicted_class == 0:  # DOWN -> short
                        record.pnl = -actual_return
                    else:
                        record.pnl = 0
                    
                    # Atualiza acumulados
                    if record.is_correct:
                        self.correct_predictions += 1
                    self.total_pnl += record.pnl if record.pnl else 0
                    
                    break
    
    def _finalize_warmup(self):
        """Finaliza período de warmup e define baselines."""
        
        # Baseline de features
        if self.feature_history:
            features = np.array(list(self.feature_history))
            self.baseline_feature_stats = {}
            
            for i in range(features.shape[1]):
                self.baseline_feature_stats[f"feature_{i}"] = (
                    np.mean(features[:, i]),
                    np.std(features[:, i])
                )
        
        # Baseline de predições
        predictions = [p.predicted_class for p in self.predictions]
        classes = np.unique(predictions)
        self.baseline_prediction_dist = np.array([
            np.mean(np.array(predictions) == c) for c in range(max(classes) + 1)
        ])
        
        self.is_warmup = False
        logger.info(f"Warmup finalizado para {self.model_name}")
    
    def check_drift(self) -> DriftMetrics:
        """
        Verifica drift nos dados/predições.
        
        Returns:
            DriftMetrics
        """
        feature_drift = {}
        
        # Feature drift
        if self.baseline_feature_stats and self.feature_history:
            recent_features = np.array(list(self.feature_history)[-100:])
            
            for i, (name, (baseline_mean, baseline_std)) in enumerate(
                self.baseline_feature_stats.items()
            ):
                if i >= recent_features.shape[1]:
                    continue
                
                current_mean = np.mean(recent_features[:, i])
                
                if baseline_std > 0:
                    drift = abs(current_mean - baseline_mean) / baseline_std
                else:
                    drift = 0
                
                feature_drift[name] = drift
        
        # Prediction distribution drift
        prediction_drift = 0.0
        if self.baseline_prediction_dist is not None:
            recent_preds = [p.predicted_class for p in list(self.predictions)[-100:]]
            
            if recent_preds:
                n_classes = len(self.baseline_prediction_dist)
                current_dist = np.array([
                    np.mean(np.array(recent_preds) == c) for c in range(n_classes)
                ])
                
                # KL divergence simplificada
                prediction_drift = np.sum(
                    np.abs(current_dist - self.baseline_prediction_dist)
                )
        
        # Confidence drift
        recent_conf = [p.confidence for p in list(self.predictions)[-100:]]
        baseline_conf = [p.confidence for p in list(self.predictions)[:100]]
        
        if recent_conf and baseline_conf:
            confidence_drift = abs(np.mean(recent_conf) - np.mean(baseline_conf))
        else:
            confidence_drift = 0.0
        
        # Score total
        feature_drift_score = np.mean(list(feature_drift.values())) if feature_drift else 0
        drift_score = (feature_drift_score + prediction_drift + confidence_drift) / 3
        is_drifting = drift_score > self.drift_threshold
        
        metrics = DriftMetrics(
            feature_drift=feature_drift,
            prediction_drift=prediction_drift,
            confidence_drift=confidence_drift,
            is_drifting=is_drifting,
            drift_score=drift_score,
        )
        
        if is_drifting:
            self._trigger_alert("drift", metrics)
        
        return metrics
    
    def get_performance_metrics(
        self,
        lookback_hours: int = 24
    ) -> PerformanceMetrics:
        """
        Calcula métricas de performance recentes.
        
        Args:
            lookback_hours: Horas de lookback
            
        Returns:
            PerformanceMetrics
        """
        cutoff = datetime.now() - timedelta(hours=lookback_hours)
        
        recent = [
            p for p in self.predictions 
            if p.timestamp >= cutoff and p.actual_class is not None
        ]
        
        if not recent:
            return PerformanceMetrics(
                accuracy=0, precision=0, recall=0, f1_score=0,
                win_rate=0, avg_pnl=0, sharpe_ratio=0,
                total_predictions=0, correct_predictions=0,
                period_start=cutoff, period_end=datetime.now()
            )
        
        # Classificação
        y_true = [p.actual_class for p in recent]
        y_pred = [p.predicted_class for p in recent]
        
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        accuracy = correct / len(recent)
        
        # Precision/Recall para classe UP (2)
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == 2 and p == 2)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != 2 and p == 2)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == 2 and p != 2)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        # Trading metrics
        pnls = [p.pnl for p in recent if p.pnl is not None]
        
        if pnls:
            wins = [p for p in pnls if p > 0]
            win_rate = len(wins) / len(pnls)
            avg_pnl = np.mean(pnls)
            
            # Sharpe (aproximado)
            if np.std(pnls) > 0:
                sharpe = np.mean(pnls) / np.std(pnls) * np.sqrt(252)
            else:
                sharpe = 0
        else:
            win_rate = 0
            avg_pnl = 0
            sharpe = 0
        
        metrics = PerformanceMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            win_rate=win_rate,
            avg_pnl=avg_pnl,
            sharpe_ratio=sharpe,
            total_predictions=len(recent),
            correct_predictions=correct,
            period_start=cutoff,
            period_end=datetime.now(),
        )
        
        # Verifica threshold
        if accuracy < self.performance_threshold:
            self._trigger_alert("low_performance", metrics)
        
        return metrics
    
    def register_alert_callback(self, callback: callable):
        """Registra callback para alertas."""
        self.alert_callbacks.append(callback)
    
    def _trigger_alert(self, alert_type: str, data: Any):
        """Dispara alerta."""
        logger.warning(f"ALERTA [{self.model_name}]: {alert_type}")
        
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, self.model_name, data)
            except Exception as e:
                logger.error(f"Erro no callback de alerta: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo do monitor."""
        return {
            'model_name': self.model_name,
            'total_predictions': self.total_predictions,
            'correct_predictions': self.correct_predictions,
            'accuracy': self.correct_predictions / self.total_predictions if self.total_predictions > 0 else 0,
            'total_pnl': self.total_pnl,
            'is_warmup': self.is_warmup,
            'window_size': len(self.predictions),
        }
    
    def export_logs(self, filepath: Path):
        """Exporta logs para arquivo."""
        data = {
            'model_name': self.model_name,
            'exported_at': datetime.now().isoformat(),
            'summary': self.get_summary(),
            'predictions': [
                {
                    'timestamp': p.timestamp.isoformat(),
                    'symbol': p.symbol,
                    'predicted_class': p.predicted_class,
                    'confidence': p.confidence,
                    'actual_class': p.actual_class,
                    'is_correct': p.is_correct,
                    'pnl': p.pnl,
                }
                for p in self.predictions
            ],
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Logs exportados para {filepath}")


class ModelHealthChecker:
    """Verificador de saúde de modelos."""
    
    def __init__(self):
        self.monitors: Dict[str, MLMonitor] = {}
    
    def register_model(
        self,
        model_name: str,
        monitor: MLMonitor
    ):
        """Registra modelo para monitoramento."""
        self.monitors[model_name] = monitor
    
    def check_all(self) -> Dict[str, Dict[str, Any]]:
        """Verifica saúde de todos os modelos."""
        results = {}
        
        for name, monitor in self.monitors.items():
            drift = monitor.check_drift()
            perf = monitor.get_performance_metrics()
            
            results[name] = {
                'healthy': not drift.is_drifting and perf.accuracy >= monitor.performance_threshold,
                'drift_score': drift.drift_score,
                'is_drifting': drift.is_drifting,
                'accuracy': perf.accuracy,
                'sharpe': perf.sharpe_ratio,
            }
        
        return results
