"""
VIRTUS - Script de Treinamento de Modelos Simples
==================================================

Treina modelos de ML usando os dados preparados.
"""

import sys
import os

# Adiciona o diretório brain ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
import pickle
from typing import Dict, Any, Tuple

# ML imports
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib


class SimpleModelTrainer:
    """Treinador de modelos simples para análise de mercado."""
    
    def __init__(self, data_dir: str = "data/ml_ready", models_dir: str = "models/trained"):
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.scaler = StandardScaler()
        self.results = {}
    
    def load_data(self, symbol: str, timeframe: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Carrega dados preparados (train e test separados)."""
        data_path = self.data_dir / symbol / timeframe
        
        train_file = data_path / "train.csv"
        test_file = data_path / "test.csv"
        
        if not train_file.exists():
            raise FileNotFoundError(f"Train não encontrado: {train_file}")
        
        print(f"  Carregando {train_file}...")
        train_df = pd.read_csv(train_file)
        test_df = pd.read_csv(test_file)
        
        # Colunas de features (exclui time, symbol, timeframe e labels)
        exclude_cols = ['time', 'symbol', 'timeframe', 'label_direction', 'label_return', 'label_volatility']
        feature_cols = [c for c in train_df.columns if c not in exclude_cols]
        
        # Features e labels
        X_train = train_df[feature_cols].select_dtypes(include=[np.number]).values
        y_train = train_df['label_direction'].values
        
        X_test = test_df[feature_cols].select_dtypes(include=[np.number]).values
        y_test = test_df['label_direction'].values
        
        # Remove NaN
        train_mask = ~np.isnan(X_train).any(axis=1)
        X_train = X_train[train_mask]
        y_train = y_train[train_mask]
        
        test_mask = ~np.isnan(X_test).any(axis=1)
        X_test = X_test[test_mask]
        y_test = y_test[test_mask]
        
        print(f"  Train: {X_train.shape[0]} samples, {X_train.shape[1]} features")
        print(f"  Test: {X_test.shape[0]} samples")
        
        return X_train, y_train, X_test, y_test
    
    def train_model(
        self,
        symbol: str,
        timeframe: str,
        model_type: str = "random_forest"
    ) -> Dict[str, Any]:
        """
        Treina um modelo.
        
        Args:
            symbol: Símbolo (XAUUSD, EURUSD, etc)
            timeframe: Timeframe (M1, H1, D1, etc)
            model_type: Tipo de modelo
            
        Returns:
            Dict com métricas
        """
        print(f"\n{'='*60}")
        print(f"Treinando {model_type} para {symbol} {timeframe}")
        print('='*60)
        
        # Carrega dados (já separados em train/test)
        X_train, y_train, X_test, y_test = self.load_data(symbol, timeframe)
        
        print(f"  Train: {len(X_train)}, Test: {len(X_test)}")
        
        # Normaliza
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Seleciona modelo
        if model_type == "random_forest":
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                n_jobs=-1,
                random_state=42
            )
        elif model_type == "gradient_boosting":
            model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        elif model_type == "logistic":
            model = LogisticRegression(
                max_iter=1000,
                random_state=42
            )
        else:
            raise ValueError(f"Modelo não suportado: {model_type}")
        
        # Treina
        print(f"  Treinando {model_type}...")
        start_time = datetime.now()
        model.fit(X_train_scaled, y_train)
        train_time = (datetime.now() - start_time).total_seconds()
        
        # Avalia
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\n  Resultados:")
        print(f"  - Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"  - Tempo treino: {train_time:.2f}s")
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"\n  Confusion Matrix:")
        print(f"  {cm}")
        
        # Classification report - com labels explícitos para evitar erros
        print(f"\n  Classification Report:")
        unique_labels = sorted(set(y_test) | set(y_pred))
        label_names = {0: 'Down', 1: 'Neutral', 2: 'Up'}
        target_names = [label_names.get(l, str(l)) for l in unique_labels]
        report = classification_report(y_test, y_pred, labels=unique_labels, target_names=target_names, zero_division=0)
        print(report)
        
        # Salva modelo
        model_name = f"{symbol}_{timeframe}_{model_type}"
        model_path = self.models_dir / f"{model_name}.joblib"
        scaler_path = self.models_dir / f"{model_name}_scaler.joblib"
        
        joblib.dump(model, model_path)
        joblib.dump(self.scaler, scaler_path)
        print(f"\n  Modelo salvo: {model_path}")
        
        # Resultados
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'model_type': model_type,
            'accuracy': accuracy,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'train_time': train_time,
            'model_path': str(model_path),
            'timestamp': datetime.now().isoformat()
        }
        
        self.results[model_name] = result
        
        return result
    
    def train_all(self, symbols: list = None, timeframes: list = None):
        """Treina modelos para todos os símbolos e timeframes."""
        symbols = symbols or ['XAUUSD', 'EURUSD', 'GBPUSD']
        timeframes = timeframes or ['H1', 'H4', 'D1']
        model_types = ['random_forest', 'gradient_boosting']
        
        all_results = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                # Verifica se dados existem
                data_path = self.data_dir / symbol / timeframe / "train.csv"
                if not data_path.exists():
                    print(f"\n[SKIP] Dados não encontrados: {symbol} {timeframe}")
                    continue
                
                for model_type in model_types:
                    try:
                        result = self.train_model(symbol, timeframe, model_type)
                        all_results.append(result)
                    except Exception as e:
                        print(f"\n[ERRO] {symbol} {timeframe} {model_type}: {e}")
                        import traceback
                        traceback.print_exc()
        
        # Salva resumo
        summary_path = self.models_dir / "training_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\n{'='*60}")
        print("RESUMO DO TREINAMENTO")
        print('='*60)
        
        # Ordena por accuracy
        all_results.sort(key=lambda x: x['accuracy'], reverse=True)
        
        print(f"\nTop 5 Modelos:")
        for i, r in enumerate(all_results[:5], 1):
            print(f"  {i}. {r['symbol']} {r['timeframe']} {r['model_type']}: {r['accuracy']*100:.2f}%")
        
        print(f"\nTotal de modelos treinados: {len(all_results)}")
        print(f"Resumo salvo: {summary_path}")
        
        return all_results


def main():
    """Executa treinamento."""
    print("="*60)
    print("     VIRTUS - TREINAMENTO DE MODELOS ML")
    print("="*60)
    
    trainer = SimpleModelTrainer()
    
    # Treina para TODOS os timeframes disponíveis
    results = trainer.train_all(
        symbols=['XAUUSD', 'EURUSD', 'GBPUSD'],
        timeframes=['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
    )
    
    print("\n" + "="*60)
    print("     TREINAMENTO CONCLUÍDO!")
    print("="*60)


if __name__ == "__main__":
    main()
