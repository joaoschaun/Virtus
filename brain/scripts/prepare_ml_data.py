"""
VIRTUS - Preparação de Dados para ML
Cria features e labels a partir de dados históricos coletados
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))


class MLDataPreparer:
    """Prepara dados para treinamento de modelos ML"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.historical_path = base_path / "data" / "historical"
        self.ml_ready_path = base_path / "data" / "ml_ready"
        self.ml_ready_path.mkdir(parents=True, exist_ok=True)
        
    def load_raw_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Carrega dados brutos coletados"""
        csv_path = self.historical_path / symbol / timeframe / "raw_data.csv"
        
        if not csv_path.exists():
            print(f"  [WARN] Arquivo não encontrado: {csv_path}")
            return pd.DataFrame()
            
        df = pd.read_csv(csv_path)
        df['time'] = pd.to_datetime(df['time'])
        return df
        
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona indicadores técnicos como features"""
        
        if df.empty or len(df) < 50:
            return df
            
        # Cópia para evitar warnings
        df = df.copy()
        
        # === MÉDIAS MÓVEIS ===
        for period in [5, 10, 20, 50, 100, 200]:
            if len(df) >= period:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
                df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # === RSI ===
        for period in [7, 14, 21]:
            if len(df) >= period + 1:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / (loss + 1e-10)
                df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # === MACD ===
        if len(df) >= 26:
            ema_12 = df['close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # === BOLLINGER BANDS ===
        for period in [20]:
            if len(df) >= period:
                sma = df['close'].rolling(window=period).mean()
                std = df['close'].rolling(window=period).std()
                df[f'bb_upper_{period}'] = sma + (std * 2)
                df[f'bb_lower_{period}'] = sma - (std * 2)
                df[f'bb_width_{period}'] = (df[f'bb_upper_{period}'] - df[f'bb_lower_{period}']) / sma
                df[f'bb_pct_{period}'] = (df['close'] - df[f'bb_lower_{period}']) / (df[f'bb_upper_{period}'] - df[f'bb_lower_{period}'] + 1e-10)
        
        # === ATR (Average True Range) ===
        for period in [14]:
            if len(df) >= period + 1:
                high_low = df['high'] - df['low']
                high_close = np.abs(df['high'] - df['close'].shift())
                low_close = np.abs(df['low'] - df['close'].shift())
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                df[f'atr_{period}'] = tr.rolling(window=period).mean()
        
        # === STOCHASTIC ===
        for period in [14]:
            if len(df) >= period:
                low_min = df['low'].rolling(window=period).min()
                high_max = df['high'].rolling(window=period).max()
                df[f'stoch_k_{period}'] = 100 * (df['close'] - low_min) / (high_max - low_min + 1e-10)
                df[f'stoch_d_{period}'] = df[f'stoch_k_{period}'].rolling(window=3).mean()
        
        # === MOMENTUM E ROC ===
        for period in [10, 20]:
            if len(df) >= period + 1:
                df[f'momentum_{period}'] = df['close'] - df['close'].shift(period)
                df[f'roc_{period}'] = ((df['close'] - df['close'].shift(period)) / (df['close'].shift(period) + 1e-10)) * 100
        
        # === PRICE PATTERNS ===
        df['body_size'] = abs(df['close'] - df['open'])
        df['upper_shadow'] = df['high'] - df[['close', 'open']].max(axis=1)
        df['lower_shadow'] = df[['close', 'open']].min(axis=1) - df['low']
        df['body_ratio'] = df['body_size'] / (df['high'] - df['low'] + 1e-10)
        df['is_bullish'] = (df['close'] > df['open']).astype(int)
        
        # === VOLUME INDICATORS ===
        if 'tick_volume' in df.columns:
            df['volume_sma_20'] = df['tick_volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['tick_volume'] / (df['volume_sma_20'] + 1e-10)
        
        # === PRICE CHANGE ===
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_10'] = df['close'].pct_change(10)
        
        # === VOLATILITY ===
        df['volatility_10'] = df['close'].rolling(window=10).std()
        df['volatility_20'] = df['close'].rolling(window=20).std()
        
        # === DISTANCE FROM MOVING AVERAGES ===
        if 'sma_20' in df.columns:
            df['dist_sma_20'] = (df['close'] - df['sma_20']) / (df['sma_20'] + 1e-10)
        if 'sma_50' in df.columns:
            df['dist_sma_50'] = (df['close'] - df['sma_50']) / (df['sma_50'] + 1e-10)
        if 'ema_20' in df.columns:
            df['dist_ema_20'] = (df['close'] - df['ema_20']) / (df['ema_20'] + 1e-10)
            
        return df
        
    def add_labels(self, df: pd.DataFrame, look_ahead: int = 5) -> pd.DataFrame:
        """Adiciona labels para classificação"""
        
        if df.empty:
            return df
            
        df = df.copy()
        
        # Retorno futuro
        df['future_return'] = df['close'].shift(-look_ahead) / df['close'] - 1
        
        # Label de direção (classificação 3 classes)
        # Threshold baseado em volatilidade
        volatility = df['close'].pct_change().std()
        threshold = volatility * 0.5  # 50% da volatilidade como threshold
        
        df['label_direction'] = 1  # Neutral por padrão
        df.loc[df['future_return'] > threshold, 'label_direction'] = 2  # Up
        df.loc[df['future_return'] < -threshold, 'label_direction'] = 0  # Down
        
        # Label de retorno (regressão)
        df['label_return'] = df['future_return']
        
        # Label de volatilidade futura
        df['label_volatility'] = df['close'].pct_change().rolling(window=look_ahead).std().shift(-look_ahead)
        
        return df
        
    def prepare_dataset(self, symbol: str, timeframe: str) -> dict:
        """Prepara dataset completo para um símbolo/timeframe"""
        
        print(f"\n  Preparando {symbol} {timeframe}...")
        
        # Carregar dados
        df = self.load_raw_data(symbol, timeframe)
        if df.empty:
            return None
            
        print(f"    Dados brutos: {len(df):,} candles")
        
        # Adicionar indicadores
        df = self.add_technical_indicators(df)
        
        # Adicionar labels
        df = self.add_labels(df)
        
        # Remover linhas com NaN
        initial_len = len(df)
        df = df.dropna()
        print(f"    Após limpeza: {len(df):,} amostras ({initial_len - len(df):,} removidas)")
        
        if len(df) < 100:
            print(f"    [WARN] Dados insuficientes para {symbol} {timeframe}")
            return None
        
        # Split train/val/test (70/15/15)
        n = len(df)
        train_end = int(n * 0.70)
        val_end = int(n * 0.85)
        
        train_df = df.iloc[:train_end]
        val_df = df.iloc[train_end:val_end]
        test_df = df.iloc[val_end:]
        
        print(f"    Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")
        
        # Salvar datasets
        output_dir = self.ml_ready_path / symbol / timeframe
        output_dir.mkdir(parents=True, exist_ok=True)
        
        train_df.to_csv(output_dir / "train.csv", index=False)
        val_df.to_csv(output_dir / "val.csv", index=False)
        test_df.to_csv(output_dir / "test.csv", index=False)
        
        # Metadata
        feature_cols = [c for c in df.columns if c not in ['time', 'symbol', 'timeframe', 'future_return', 
                                                            'label_direction', 'label_return', 'label_volatility']]
        
        metadata = {
            "symbol": symbol,
            "timeframe": timeframe,
            "total_samples": len(df),
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "features": feature_cols,
            "n_features": len(feature_cols),
            "label_distribution": df['label_direction'].value_counts().to_dict(),
            "date_range": {
                "start": str(df['time'].min()),
                "end": str(df['time'].max())
            },
            "prepared_at": datetime.now().isoformat()
        }
        
        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
            
        return metadata
        
    def prepare_all(self, symbols: list, timeframes: list):
        """Prepara todos os datasets"""
        
        print("=" * 60)
        print("     VIRTUS - PREPARAÇÃO DE DADOS ML")
        print("=" * 60)
        
        all_results = []
        
        for symbol in symbols:
            print(f"\n{'=' * 60}")
            print(f"  SÍMBOLO: {symbol}")
            print(f"{'=' * 60}")
            
            for tf in timeframes:
                result = self.prepare_dataset(symbol, tf)
                if result:
                    all_results.append(result)
        
        # Resumo geral
        summary = {
            "total_datasets": len(all_results),
            "total_samples": sum(r["total_samples"] for r in all_results),
            "prepared_at": datetime.now().isoformat(),
            "datasets": all_results
        }
        
        summary_path = self.ml_ready_path / "preparation_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
            
        print("\n" + "=" * 60)
        print("     RESUMO DA PREPARAÇÃO")
        print("=" * 60)
        print(f"\n  Total de datasets: {len(all_results)}")
        print(f"  Total de amostras: {sum(r['total_samples'] for r in all_results):,}")
        print(f"\n  Datasets preparados:")
        
        for r in all_results:
            print(f"    - {r['symbol']} {r['timeframe']}: {r['total_samples']:,} amostras ({r['n_features']} features)")
            
        print(f"\n  Dados salvos em: {self.ml_ready_path}")
        print("\n" + "=" * 60)
        print("     PREPARAÇÃO CONCLUÍDA!")
        print("=" * 60)
        
        return summary


def main():
    base_path = Path(__file__).parent.parent
    
    preparer = MLDataPreparer(base_path)
    
    symbols = ["XAUUSD", "EURUSD", "GBPUSD"]
    timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
    
    preparer.prepare_all(symbols, timeframes)


if __name__ == "__main__":
    main()
