"""
VIRTUS - Treinamento Walk-Forward (Sem Data Leakage)
=====================================================

Implementa validação walk-forward realista para trading:
- Treina apenas com dados passados
- Testa em dados futuros (nunca vistos)
- Remove features com informação do futuro
- Simula condições reais de mercado
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any, List, Tuple

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
import joblib


class WalkForwardTrainer:
    """
    Treinador com validação Walk-Forward.
    
    Walk-Forward significa:
    1. Treina no período T1 a T2
    2. Testa no período T2 a T3
    3. Avança a janela e repete
    
    Isso simula trading real onde só temos dados históricos.
    """
    
    def __init__(self, data_dir: str = "data/ml_ready", models_dir: str = "models/trained"):
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Features PROIBIDAS (contêm informação do futuro)
        self.forbidden_features = [
            'future_return',      # Retorno futuro - LEAKAGE DIRETO!
            'label_direction',    # É o label
            'label_return',       # É o label
            'label_volatility',   # É o label
            'time',               # Não é feature numérica
            'symbol',             # Não é feature numérica
            'timeframe'           # Não é feature numérica
        ]
        
        self.results = []
    
    def load_and_clean_data(self, symbol: str, timeframe: str) -> Tuple[pd.DataFrame, List[str]]:
        """
        Carrega dados e remove features com leakage.
        
        Returns:
            DataFrame limpo e lista de features válidas
        """
        data_path = self.data_dir / symbol / timeframe
        
        # Carrega todos os dados (train + val + test) para walk-forward
        dfs = []
        for file in ['train.csv', 'val.csv', 'test.csv']:
            file_path = data_path / file
            if file_path.exists():
                df = pd.read_csv(file_path)
                dfs.append(df)
        
        if not dfs:
            raise FileNotFoundError(f"Dados não encontrados: {data_path}")
        
        # Concatena todos os dados
        df = pd.concat(dfs, ignore_index=True)
        
        # Ordena por tempo (crucial para walk-forward)
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time').reset_index(drop=True)
        
        # Remove features proibidas
        feature_cols = [c for c in df.columns if c not in self.forbidden_features]
        
        # Mantém apenas numéricas
        numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
        
        print(f"  Features válidas: {len(numeric_cols)}")
        print(f"  Features removidas (leakage): {[f for f in self.forbidden_features if f in df.columns]}")
        
        return df, numeric_cols
    
    def walk_forward_split(
        self, 
        df: pd.DataFrame, 
        n_splits: int = 5,
        train_ratio: float = 0.7
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Cria splits walk-forward.
        
        Exemplo com 5 splits:
        Split 1: Train [0-70%], Test [70-76%]
        Split 2: Train [0-76%], Test [76-82%]
        Split 3: Train [0-82%], Test [82-88%]
        Split 4: Train [0-88%], Test [88-94%]
        Split 5: Train [0-94%], Test [94-100%]
        """
        n_samples = len(df)
        test_size = int(n_samples * (1 - train_ratio) / n_splits)
        
        splits = []
        for i in range(n_splits):
            # Índice final do teste
            test_end = n_samples - (n_splits - 1 - i) * test_size
            test_start = test_end - test_size
            train_end = test_start
            
            # Garante que train tem pelo menos 50% dos dados
            train_start = 0
            if train_end < n_samples * 0.3:
                continue
            
            train_idx = np.arange(train_start, train_end)
            test_idx = np.arange(test_start, test_end)
            
            splits.append((train_idx, test_idx))
        
        return splits
    
    def train_walkforward(
        self,
        symbol: str,
        timeframe: str,
        model_type: str = "random_forest",
        n_splits: int = 5
    ) -> Dict[str, Any]:
        """
        Treina modelo com validação walk-forward.
        """
        print(f"\n{'='*60}")
        print(f"Walk-Forward: {model_type} para {symbol} {timeframe}")
        print('='*60)
        
        # Carrega e limpa dados
        df, feature_cols = self.load_and_clean_data(symbol, timeframe)
        
        print(f"  Total de amostras: {len(df)}")
        
        # Prepara X e y
        X = df[feature_cols].values
        y = df['label_direction'].values
        
        # Remove NaN
        valid_mask = ~np.isnan(X).any(axis=1)
        X = X[valid_mask]
        y = y[valid_mask]
        df_clean = df[valid_mask].reset_index(drop=True)
        
        print(f"  Amostras válidas: {len(X)}")
        
        # Cria splits walk-forward
        splits = self.walk_forward_split(df_clean, n_splits=n_splits)
        
        print(f"  Splits walk-forward: {len(splits)}")
        
        # Métricas por split
        split_metrics = []
        all_predictions = []
        all_actuals = []
        
        for i, (train_idx, test_idx) in enumerate(splits):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            # Normaliza (fit apenas no treino!)
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Seleciona modelo
            if model_type == "random_forest":
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    min_samples_split=10,
                    min_samples_leaf=5,
                    n_jobs=-1,
                    random_state=42
                )
            elif model_type == "gradient_boosting":
                model = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    min_samples_split=10,
                    random_state=42
                )
            else:
                raise ValueError(f"Modelo não suportado: {model_type}")
            
            # Treina
            model.fit(X_train_scaled, y_train)
            
            # Prediz
            y_pred = model.predict(X_test_scaled)
            
            # Métricas
            acc = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            
            split_metrics.append({
                'split': i + 1,
                'train_size': len(train_idx),
                'test_size': len(test_idx),
                'accuracy': acc,
                'f1_score': f1
            })
            
            all_predictions.extend(y_pred)
            all_actuals.extend(y_test)
            
            print(f"  Split {i+1}: Train={len(train_idx)}, Test={len(test_idx)}, Acc={acc:.4f}, F1={f1:.4f}")
        
        # Métricas agregadas
        all_predictions = np.array(all_predictions)
        all_actuals = np.array(all_actuals)
        
        overall_accuracy = accuracy_score(all_actuals, all_predictions)
        overall_f1 = f1_score(all_actuals, all_predictions, average='weighted', zero_division=0)
        
        print(f"\n  === RESULTADOS WALK-FORWARD ===")
        print(f"  Accuracy Geral: {overall_accuracy:.4f} ({overall_accuracy*100:.2f}%)")
        print(f"  F1-Score Geral: {overall_f1:.4f}")
        
        # Confusion Matrix
        cm = confusion_matrix(all_actuals, all_predictions)
        print(f"\n  Confusion Matrix:")
        print(f"  {cm}")
        
        # Classification Report
        unique_labels = sorted(set(all_actuals) | set(all_predictions))
        label_names = {0: 'Down', 1: 'Neutral', 2: 'Up'}
        target_names = [label_names.get(l, str(l)) for l in unique_labels]
        
        print(f"\n  Classification Report:")
        report = classification_report(
            all_actuals, all_predictions, 
            labels=unique_labels, 
            target_names=target_names,
            zero_division=0
        )
        print(report)
        
        # Treina modelo final com TODOS os dados (para produção)
        print(f"\n  Treinando modelo final com todos os dados...")
        scaler_final = StandardScaler()
        X_scaled = scaler_final.fit_transform(X)
        
        if model_type == "random_forest":
            final_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                n_jobs=-1,
                random_state=42
            )
        else:
            final_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                min_samples_split=10,
                random_state=42
            )
        
        final_model.fit(X_scaled, y)
        
        # Salva modelo
        model_name = f"{symbol}_{timeframe}_{model_type}_wf"
        model_path = self.models_dir / f"{model_name}.joblib"
        scaler_path = self.models_dir / f"{model_name}_scaler.joblib"
        
        joblib.dump(final_model, model_path)
        joblib.dump(scaler_final, scaler_path)
        
        # Salva lista de features
        features_path = self.models_dir / f"{model_name}_features.json"
        with open(features_path, 'w') as f:
            json.dump(feature_cols, f)
        
        print(f"  Modelo salvo: {model_path}")
        
        # Resultado
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'model_type': model_type,
            'validation': 'walk_forward',
            'n_splits': len(splits),
            'total_samples': len(X),
            'accuracy': overall_accuracy,
            'f1_score': overall_f1,
            'split_metrics': split_metrics,
            'n_features': len(feature_cols),
            'model_path': str(model_path),
            'timestamp': datetime.now().isoformat()
        }
        
        self.results.append(result)
        return result
    
    def train_all(
        self, 
        symbols: List[str] = None, 
        timeframes: List[str] = None,
        model_types: List[str] = None
    ):
        """Treina todos os modelos com walk-forward."""
        symbols = symbols or ['XAUUSD', 'EURUSD', 'GBPUSD']
        timeframes = timeframes or ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
        model_types = model_types or ['random_forest', 'gradient_boosting']
        
        for symbol in symbols:
            for timeframe in timeframes:
                # Verifica se dados existem
                data_path = self.data_dir / symbol / timeframe
                if not data_path.exists():
                    print(f"\n[SKIP] Dados não encontrados: {symbol} {timeframe}")
                    continue
                
                for model_type in model_types:
                    try:
                        self.train_walkforward(symbol, timeframe, model_type)
                    except Exception as e:
                        print(f"\n[ERRO] {symbol} {timeframe} {model_type}: {e}")
                        import traceback
                        traceback.print_exc()
        
        # Salva resumo
        summary_path = self.models_dir / "walkforward_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Exibe resumo
        print(f"\n{'='*60}")
        print("RESUMO WALK-FORWARD (SEM DATA LEAKAGE)")
        print('='*60)
        
        if self.results:
            # Ordena por accuracy
            sorted_results = sorted(self.results, key=lambda x: x['accuracy'], reverse=True)
            
            print(f"\nTop 10 Modelos:")
            for i, r in enumerate(sorted_results[:10], 1):
                print(f"  {i}. {r['symbol']} {r['timeframe']} {r['model_type']}: "
                      f"Acc={r['accuracy']*100:.2f}% F1={r['f1_score']:.4f}")
            
            # Estatísticas gerais
            accs = [r['accuracy'] for r in self.results]
            print(f"\nEstatísticas:")
            print(f"  - Accuracy Média: {np.mean(accs)*100:.2f}%")
            print(f"  - Accuracy Mínima: {np.min(accs)*100:.2f}%")
            print(f"  - Accuracy Máxima: {np.max(accs)*100:.2f}%")
            print(f"  - Desvio Padrão: {np.std(accs)*100:.2f}%")
        
        print(f"\nTotal de modelos treinados: {len(self.results)}")
        print(f"Resumo salvo: {summary_path}")
        
        return self.results


def main():
    """Executa treinamento walk-forward."""
    print("="*60)
    print("   VIRTUS - TREINAMENTO WALK-FORWARD (REALISTA)")
    print("   Sem Data Leakage - Validação Temporal")
    print("="*60)
    
    trainer = WalkForwardTrainer()
    
    # Treina todos os modelos
    results = trainer.train_all(
        symbols=['XAUUSD', 'EURUSD', 'GBPUSD'],
        timeframes=['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'],
        model_types=['random_forest', 'gradient_boosting']
    )
    
    print("\n" + "="*60)
    print("     TREINAMENTO WALK-FORWARD CONCLUÍDO!")
    print("="*60)


if __name__ == "__main__":
    main()
