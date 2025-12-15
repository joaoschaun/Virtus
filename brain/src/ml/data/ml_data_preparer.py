"""
ML Data Preparer - Prepara dados históricos para treinamento de modelos ML.

Este módulo transforma dados brutos OHLCV em datasets prontos para treinar modelos de:
- Predição de direção (Up/Down/Neutral)
- Detecção de padrões (candlestick patterns)
- Predição de volatilidade
- Scalping signals
"""

import os
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json
import logging

logger = logging.getLogger('virtus.ml_data_preparer')


@dataclass
class PreparerConfig:
    """Configuração para preparação de dados ML."""
    input_dir: str = 'data/historical'
    output_dir: str = 'data/ml_ready'
    lookback_periods: int = 60  # Candles de contexto
    prediction_horizon: int = 5  # Candles à frente para prever
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    min_movement_pips: float = 5.0  # Movimento mínimo para label "significativo"


class MLDataPreparer:
    """
    Prepara dados para treinamento de modelos ML.
    
    Features geradas:
    - OHLCV normalizados
    - Returns (retornos percentuais)
    - Volatilidade (ATR, desvio padrão)
    - Indicadores técnicos (RSI, MACD, Bollinger)
    - Padrões de candlestick
    - Features temporais (hora, dia da semana)
    """
    
    def __init__(self, config: PreparerConfig):
        self.config = config
        self.input_path = Path(config.input_dir)
        self.output_path = Path(config.output_dir)
        
        # Criar diretório de saída
        self.output_path.mkdir(parents=True, exist_ok=True)
        
    def prepare_all(self) -> Dict:
        """
        Prepara todos os dados disponíveis.
        
        Returns:
            Dict com estatísticas de preparação
        """
        results = {
            'prepared': [],
            'failed': [],
            'total_samples': 0
        }
        
        # Encontrar todos os CSVs
        csv_files = list(self.input_path.glob('**/*.csv'))
        
        if not csv_files:
            logger.warning("⚠️ Nenhum arquivo CSV encontrado em %s", self.input_path)
            return results
            
        logger.info("📂 Encontrados %d arquivos CSV para processar", len(csv_files))
        
        for csv_file in csv_files:
            try:
                # Extrair símbolo e timeframe do nome
                parts = csv_file.stem.split('_')
                if len(parts) >= 2:
                    symbol = parts[0]
                    timeframe = parts[1]
                else:
                    symbol = csv_file.parent.name
                    timeframe = csv_file.stem.split('_')[0] if '_' in csv_file.stem else 'unknown'
                
                logger.info("📊 Preparando %s %s...", symbol, timeframe)
                
                # Preparar dataset
                stats = self._prepare_file(csv_file, symbol, timeframe)
                
                if stats:
                    results['prepared'].append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'samples': stats['total_samples'],
                        'train': stats['train_samples'],
                        'val': stats['val_samples'],
                        'test': stats['test_samples'],
                        'features': stats['feature_count']
                    })
                    results['total_samples'] += stats['total_samples']
                    logger.info("   ✅ %d samples (%d features)", 
                              stats['total_samples'], stats['feature_count'])
                    
            except Exception as e:
                logger.error("   ❌ Erro: %s", str(e))
                results['failed'].append({
                    'file': str(csv_file),
                    'error': str(e)
                })
                
        # Salvar resumo
        summary_file = self.output_path / 'preparation_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info("📋 Resumo salvo em %s", summary_file)
        
        return results
        
    def _prepare_file(self, csv_file: Path, symbol: str, timeframe: str) -> Optional[Dict]:
        """Prepara um arquivo CSV específico."""
        
        # Carregar dados
        df = pd.read_csv(csv_file, parse_dates=['time'])
        
        if len(df) < self.config.lookback_periods + self.config.prediction_horizon + 100:
            logger.warning("   ⚠️ Dados insuficientes: %d candles", len(df))
            return None
            
        # Gerar features
        df_features = self._generate_features(df, symbol)
        
        # Gerar labels
        df_features = self._generate_labels(df_features)
        
        # Remover NaN
        df_features = df_features.dropna()
        
        if len(df_features) < 100:
            logger.warning("   ⚠️ Poucos dados após processamento: %d", len(df_features))
            return None
            
        # Split train/val/test
        train_df, val_df, test_df = self._split_data(df_features)
        
        # Criar diretório para símbolo/timeframe
        output_dir = self.output_path / symbol / timeframe
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Salvar datasets
        train_df.to_csv(output_dir / 'train.csv', index=False)
        val_df.to_csv(output_dir / 'val.csv', index=False)
        test_df.to_csv(output_dir / 'test.csv', index=False)
        
        # Salvar metadados
        feature_cols = [c for c in df_features.columns 
                       if c not in ['time', 'label_direction', 'label_return', 'label_volatility']]
        
        metadata = {
            'symbol': symbol,
            'timeframe': timeframe,
            'features': feature_cols,
            'label_columns': ['label_direction', 'label_return', 'label_volatility'],
            'lookback': self.config.lookback_periods,
            'horizon': self.config.prediction_horizon,
            'created_at': datetime.now().isoformat()
        }
        
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
            
        return {
            'total_samples': len(df_features),
            'train_samples': len(train_df),
            'val_samples': len(val_df),
            'test_samples': len(test_df),
            'feature_count': len(feature_cols)
        }
        
    def _generate_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Gera features para ML a partir dos dados OHLCV.
        """
        df = df.copy()
        
        # ========== FEATURES BÁSICAS ==========
        
        # Returns (retornos)
        df['return_1'] = df['close'].pct_change()
        df['return_5'] = df['close'].pct_change(5)
        df['return_10'] = df['close'].pct_change(10)
        df['return_20'] = df['close'].pct_change(20)
        
        # Log returns
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # ========== VOLATILIDADE ==========
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = true_range.rolling(14).mean()
        df['atr_ratio'] = df['atr_14'] / df['close']
        
        # Volatilidade histórica
        df['volatility_10'] = df['log_return'].rolling(10).std() * np.sqrt(252)
        df['volatility_20'] = df['log_return'].rolling(20).std() * np.sqrt(252)
        
        # ========== MÉDIAS MÓVEIS ==========
        
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['ema_10'] = df['close'].ewm(span=10).mean()
        df['ema_20'] = df['close'].ewm(span=20).mean()
        
        # Distância do preço às médias (normalizada)
        df['dist_sma_10'] = (df['close'] - df['sma_10']) / df['sma_10']
        df['dist_sma_20'] = (df['close'] - df['sma_20']) / df['sma_20']
        df['dist_sma_50'] = (df['close'] - df['sma_50']) / df['sma_50']
        
        # Cross de médias
        df['sma_cross_10_20'] = (df['sma_10'] > df['sma_20']).astype(int)
        df['sma_cross_20_50'] = (df['sma_20'] > df['sma_50']).astype(int)
        
        # ========== MOMENTUM ==========
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # RSI normalizado para [-1, 1]
        df['rsi_norm'] = (df['rsi_14'] - 50) / 50
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Normalizar MACD pelo preço
        df['macd_norm'] = df['macd'] / df['close'] * 100
        
        # Stochastic
        low_14 = df['low'].rolling(14).min()
        high_14 = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * (df['close'] - low_14) / (high_14 - low_14 + 1e-10)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        
        # ========== BOLLINGER BANDS ==========
        
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10)
        
        # ========== CANDLESTICK PATTERNS ==========
        
        # Tamanho do corpo
        df['body_size'] = abs(df['close'] - df['open']) / df['open']
        
        # Sombras
        df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['open']
        df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['open']
        
        # Direção do candle
        df['candle_direction'] = (df['close'] > df['open']).astype(int)
        
        # Doji (corpo muito pequeno)
        df['is_doji'] = (df['body_size'] < df['body_size'].rolling(20).mean() * 0.1).astype(int)
        
        # Hammer/Hanging Man (sombra inferior longa)
        df['is_hammer'] = ((df['lower_shadow'] > df['body_size'] * 2) & 
                          (df['upper_shadow'] < df['body_size'] * 0.5)).astype(int)
        
        # ========== VOLUME ==========
        
        if 'tick_volume' in df.columns:
            df['volume_sma_10'] = df['tick_volume'].rolling(10).mean()
            df['volume_ratio'] = df['tick_volume'] / (df['volume_sma_10'] + 1)
            df['volume_change'] = df['tick_volume'].pct_change()
        
        # ========== FEATURES TEMPORAIS ==========
        
        df['hour'] = df['time'].dt.hour
        df['day_of_week'] = df['time'].dt.dayofweek
        
        # London session (8-17 GMT)
        df['is_london'] = ((df['hour'] >= 8) & (df['hour'] < 17)).astype(int)
        # NY session (13-22 GMT)
        df['is_ny'] = ((df['hour'] >= 13) & (df['hour'] < 22)).astype(int)
        # Asian session (0-8 GMT)
        df['is_asian'] = ((df['hour'] >= 0) & (df['hour'] < 8)).astype(int)
        
        # Codificação cíclica de hora
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # ========== LOOKBACK FEATURES ==========
        
        # Últimos N candles de direção
        for i in range(1, 6):
            df[f'dir_lag_{i}'] = df['candle_direction'].shift(i)
            df[f'return_lag_{i}'] = df['return_1'].shift(i)
        
        # Sequência de direção (quantos candles na mesma direção)
        df['direction_streak'] = self._calculate_streak(df['candle_direction'])
        
        return df
        
    def _generate_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gera labels para diferentes tipos de predição.
        """
        df = df.copy()
        horizon = self.config.prediction_horizon
        
        # ========== LABEL: DIREÇÃO ==========
        # 0 = Down, 1 = Neutral, 2 = Up
        
        future_return = df['close'].shift(-horizon) / df['close'] - 1
        
        # Determinar threshold baseado no símbolo
        # Para XAUUSD usa pontos, para forex usa pips
        threshold = self.config.min_movement_pips / 10000  # 5 pips default
        
        df['label_direction'] = 1  # Neutral
        df.loc[future_return > threshold, 'label_direction'] = 2  # Up
        df.loc[future_return < -threshold, 'label_direction'] = 0  # Down
        
        # ========== LABEL: RETURN ==========
        # Retorno contínuo (para regressão)
        df['label_return'] = future_return
        
        # ========== LABEL: VOLATILIDADE ==========
        # Volatilidade futura alta/baixa
        future_volatility = df['atr_ratio'].shift(-horizon)
        median_vol = df['atr_ratio'].rolling(50).median()
        df['label_volatility'] = (future_volatility > median_vol).astype(int)
        
        return df
        
    def _split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Divide dados em train/val/test mantendo ordem temporal.
        """
        n = len(df)
        train_end = int(n * self.config.train_ratio)
        val_end = int(n * (self.config.train_ratio + self.config.val_ratio))
        
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()
        
        return train_df, val_df, test_df
        
    def _calculate_streak(self, series: pd.Series) -> pd.Series:
        """Calcula sequência de valores iguais."""
        streak = pd.Series(index=series.index, dtype=int)
        streak.iloc[0] = 1
        
        for i in range(1, len(series)):
            if series.iloc[i] == series.iloc[i-1]:
                streak.iloc[i] = streak.iloc[i-1] + 1
            else:
                streak.iloc[i] = 1
                
        return streak


# ========== CLI ==========

if __name__ == '__main__':
    import sys
    
    # Configuração de logging
    logging.basicConfig(
        level=logging.INFO,
        format='📌 %(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print("=" * 70)
    print("      ML DATA PREPARER - Preparação de Dados para Treinamento")
    print("=" * 70)
    print()
    
    config = PreparerConfig()
    preparer = MLDataPreparer(config)
    
    results = preparer.prepare_all()
    
    print()
    print("=" * 70)
    print("RESULTADO:")
    print("=" * 70)
    print()
    
    if results['prepared']:
        print("Datasets preparados:")
        for item in results['prepared']:
            print(f"  {item['symbol']} {item['timeframe']}:")
            print(f"    Samples: {item['samples']} ({item['features']} features)")
            print(f"    Train: {item['train']}, Val: {item['val']}, Test: {item['test']}")
        print()
        print(f"TOTAL: {results['total_samples']} samples preparados")
    
    if results['failed']:
        print()
        print("Falhas:")
        for item in results['failed']:
            print(f"  {item['file']}: {item['error']}")
