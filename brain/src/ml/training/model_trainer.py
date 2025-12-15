"""
ML Model Trainer - Script de treinamento para modelos de predição de direção.

Este script treina modelos usando os dados preparados pelo MLDataPreparer.
Suporta diferentes algoritmos e salva modelos treinados para uso em produção.
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger('virtus.ml_trainer')


@dataclass
class TrainingConfig:
    """Configuração de treinamento."""
    data_dir: str = 'data/ml_ready'
    models_dir: str = 'models/trained'
    symbols: List[str] = None
    timeframes: List[str] = None
    model_type: str = 'random_forest'  # random_forest, gradient_boosting, xgboost
    target: str = 'label_direction'  # label_direction, label_return, label_volatility
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ['XAUUSD', 'EURUSD', 'GBPUSD']
        if self.timeframes is None:
            self.timeframes = ['M5', 'M15', 'H1']


class MLModelTrainer:
    """
    Treinador de modelos ML para trading.
    
    Algoritmos disponíveis:
    - RandomForest: Robusto, bom para features não-lineares
    - GradientBoosting: Alta precisão, mais lento
    - XGBoost: Performance otimizada (requer xgboost instalado)
    """
    
    # Features a serem usadas no treinamento
    FEATURE_COLUMNS = [
        # Returns
        'return_1', 'return_5', 'return_10', 'return_20', 'log_return',
        # Volatilidade
        'atr_ratio', 'volatility_10', 'volatility_20',
        # Médias móveis
        'dist_sma_10', 'dist_sma_20', 'dist_sma_50',
        'sma_cross_10_20', 'sma_cross_20_50',
        # Momentum
        'rsi_norm', 'macd_norm', 'macd_hist', 'stoch_k', 'stoch_d',
        # Bollinger
        'bb_width', 'bb_position',
        # Candlestick
        'body_size', 'upper_shadow', 'lower_shadow', 'candle_direction',
        'is_doji', 'is_hammer',
        # Volume
        'volume_ratio',
        # Temporal
        'is_london', 'is_ny', 'is_asian', 'hour_sin', 'hour_cos',
        # Lags
        'dir_lag_1', 'dir_lag_2', 'dir_lag_3', 'dir_lag_4', 'dir_lag_5',
        'return_lag_1', 'return_lag_2', 'return_lag_3',
        'direction_streak'
    ]
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.data_path = Path(config.data_dir)
        self.models_path = Path(config.models_dir)
        self.models_path.mkdir(parents=True, exist_ok=True)
        
    def train_all(self) -> Dict:
        """
        Treina modelos para todos os símbolos e timeframes configurados.
        
        Returns:
            Dict com resultados de treinamento
        """
        results = {
            'trained': [],
            'failed': [],
            'timestamp': datetime.now().isoformat()
        }
        
        total = len(self.config.symbols) * len(self.config.timeframes)
        current = 0
        
        for symbol in self.config.symbols:
            for timeframe in self.config.timeframes:
                current += 1
                logger.info("🔄 [%d/%d] Treinando %s %s...", 
                          current, total, symbol, timeframe)
                
                try:
                    metrics = self.train_model(symbol, timeframe)
                    
                    if metrics:
                        results['trained'].append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            **metrics
                        })
                        logger.info("   ✅ Accuracy: %.2f%% | F1: %.2f", 
                                  metrics['accuracy'] * 100, metrics['f1_score'])
                    else:
                        results['failed'].append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'error': 'Dados insuficientes'
                        })
                        
                except Exception as e:
                    logger.error("   ❌ Erro: %s", str(e))
                    results['failed'].append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'error': str(e)
                    })
                    
        # Salvar resumo
        summary_file = self.models_path / 'training_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        return results
        
    def train_model(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        Treina um modelo específico para symbol/timeframe.
        """
        # Carregar dados
        data_dir = self.data_path / symbol / timeframe
        
        if not data_dir.exists():
            logger.warning("   ⚠️ Diretório não encontrado: %s", data_dir)
            return None
            
        train_df = pd.read_csv(data_dir / 'train.csv')
        val_df = pd.read_csv(data_dir / 'val.csv')
        test_df = pd.read_csv(data_dir / 'test.csv')
        
        if len(train_df) < 100:
            logger.warning("   ⚠️ Dados insuficientes: %d samples", len(train_df))
            return None
            
        # Selecionar features disponíveis
        available_features = [f for f in self.FEATURE_COLUMNS if f in train_df.columns]
        
        if len(available_features) < 10:
            logger.warning("   ⚠️ Features insuficientes: %d", len(available_features))
            return None
            
        # Preparar dados
        X_train = train_df[available_features].values
        y_train = train_df[self.config.target].values
        
        X_val = val_df[available_features].values
        y_val = val_df[self.config.target].values
        
        X_test = test_df[available_features].values
        y_test = test_df[self.config.target].values
        
        # Remover NaN
        mask_train = ~np.isnan(X_train).any(axis=1)
        mask_val = ~np.isnan(X_val).any(axis=1)
        mask_test = ~np.isnan(X_test).any(axis=1)
        
        X_train, y_train = X_train[mask_train], y_train[mask_train]
        X_val, y_val = X_val[mask_val], y_val[mask_val]
        X_test, y_test = X_test[mask_test], y_test[mask_test]
        
        # Criar modelo
        model = self._create_model()
        
        # Treinar
        model.fit(X_train, y_train)
        
        # Avaliar
        metrics = self._evaluate_model(model, X_test, y_test)
        
        # Salvar modelo
        model_dir = self.models_path / symbol / timeframe
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_file = model_dir / f'{self.config.model_type}.pkl'
        with open(model_file, 'wb') as f:
            pickle.dump(model, f)
            
        # Salvar metadados
        metadata = {
            'symbol': symbol,
            'timeframe': timeframe,
            'model_type': self.config.model_type,
            'target': self.config.target,
            'features': available_features,
            'train_samples': len(X_train),
            'metrics': metrics,
            'trained_at': datetime.now().isoformat()
        }
        
        with open(model_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
            
        return metrics
        
    def _create_model(self):
        """Cria modelo baseado na configuração."""
        
        if self.config.model_type == 'random_forest':
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1
            )
            
        elif self.config.model_type == 'gradient_boosting':
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
            
        elif self.config.model_type == 'xgboost':
            try:
                from xgboost import XGBClassifier
                return XGBClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42,
                    use_label_encoder=False,
                    eval_metric='mlogloss'
                )
            except ImportError:
                logger.warning("⚠️ XGBoost não instalado, usando RandomForest")
                from sklearn.ensemble import RandomForestClassifier
                return RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
        else:
            raise ValueError(f"Modelo desconhecido: {self.config.model_type}")
            
    def _evaluate_model(self, model, X_test, y_test) -> Dict:
        """Avalia modelo no conjunto de teste."""
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, 
            f1_score, classification_report, confusion_matrix
        )
        
        y_pred = model.predict(X_test)
        
        # Métricas
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        return {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'confusion_matrix': cm.tolist(),
            'test_samples': len(y_test)
        }


# ========== CLI ==========

if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='📌 %(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print("=" * 70)
    print("      ML MODEL TRAINER - Treinamento de Modelos")
    print("=" * 70)
    print()
    
    config = TrainingConfig(
        symbols=['XAUUSD', 'EURUSD', 'GBPUSD'],
        timeframes=['M5', 'M15', 'H1'],
        model_type='random_forest',
        target='label_direction'
    )
    
    print("Configuração:")
    print(f"  Símbolos: {config.symbols}")
    print(f"  Timeframes: {config.timeframes}")
    print(f"  Modelo: {config.model_type}")
    print(f"  Target: {config.target}")
    print()
    
    trainer = MLModelTrainer(config)
    results = trainer.train_all()
    
    print()
    print("=" * 70)
    print("RESULTADOS DO TREINAMENTO")
    print("=" * 70)
    print()
    
    if results['trained']:
        print("Modelos treinados:")
        print()
        
        # Agrupar por símbolo
        by_symbol = {}
        for item in results['trained']:
            sym = item['symbol']
            if sym not in by_symbol:
                by_symbol[sym] = []
            by_symbol[sym].append(item)
            
        for symbol, items in by_symbol.items():
            print(f"{symbol}:")
            for item in items:
                print(f"  {item['timeframe']}: Acc={item['accuracy']*100:.1f}% | F1={item['f1_score']:.2f}")
            
            # Média
            avg_acc = sum(i['accuracy'] for i in items) / len(items)
            avg_f1 = sum(i['f1_score'] for i in items) / len(items)
            print(f"  MÉDIA: Acc={avg_acc*100:.1f}% | F1={avg_f1:.2f}")
            print()
            
    if results['failed']:
        print("Falhas:")
        for item in results['failed']:
            print(f"  {item['symbol']} {item['timeframe']}: {item['error']}")
