"""
VIRTUS ML - Historical Data Collector
======================================

Coleta dados históricos do MT5 para treinamento de modelos ML.

Uso:
    python -m src.ml.data.historical_collector --symbol XAUUSD --timeframe H1 --days 365
    
    Ou via código:
    collector = HistoricalDataCollector()
    await collector.collect_all()
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import logging
import sys

import pandas as pd
import numpy as np

# Adiciona path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.logger import get_logger
from src.core.types import Timeframe
from src.mt5.mt5_connection import MT5Connection
from src.mt5.mt5_data import MT5DataService

logger = get_logger("historical_collector")


@dataclass
class CollectionConfig:
    """Configuração para coleta de dados."""
    # Símbolos para coletar
    symbols: List[str] = field(default_factory=lambda: [
        'XAUUSD',  # Gold
        'EURUSD',  # Euro
        'GBPUSD',  # Pound
    ])
    
    # Timeframes para coletar
    timeframes: List[str] = field(default_factory=lambda: [
        'D1',   # Diário - para análises de longo prazo
        'H4',   # 4 horas - swing trading
        'H1',   # 1 hora - intraday
        'M15',  # 15 minutos - scalping
        'M5',   # 5 minutos - scalping rápido
        'M1',   # 1 minuto - alta frequência
    ])
    
    # Período de coleta
    days_back: int = 365  # 1 ano por padrão
    
    # Diretório de saída
    output_dir: str = "data/historical"
    
    # Formato de saída
    output_format: str = "parquet"  # parquet ou csv
    
    # Máximo de candles por request (MT5 tem limite)
    max_candles_per_request: int = 10000


class HistoricalDataCollector:
    """
    Coletor de dados históricos do MT5.
    
    Baixa dados OHLCV de múltiplos símbolos e timeframes
    para uso em treinamento de modelos ML.
    """
    
    # Mapeamento de string para Timeframe
    TIMEFRAME_MAP = {
        'M1': Timeframe.M1,
        'M5': Timeframe.M5,
        'M15': Timeframe.M15,
        'M30': Timeframe.M30,
        'H1': Timeframe.H1,
        'H4': Timeframe.H4,
        'D1': Timeframe.D1,
        'W1': Timeframe.W1,
        'MN1': Timeframe.MN1,
    }
    
    # Candles típicos por dia para cada timeframe
    CANDLES_PER_DAY = {
        'M1': 1440,
        'M5': 288,
        'M15': 96,
        'M30': 48,
        'H1': 24,
        'H4': 6,
        'D1': 1,
        'W1': 0.2,
        'MN1': 0.033,
    }
    
    def __init__(self, config: Optional[CollectionConfig] = None):
        self.config = config or CollectionConfig()
        self._data_service: Optional[MT5DataService] = None
        self._output_path = Path(self.config.output_dir)
        
    async def initialize(self) -> bool:
        """Inicializa conexão com MT5."""
        try:
            self._data_service = await MT5DataService.get_instance()
            logger.info("✅ Conectado ao MT5 para coleta de dados")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao conectar MT5: {e}")
            return False
    
    async def collect_all(self) -> Dict[str, Any]:
        """
        Coleta todos os dados configurados.
        
        Returns:
            Resumo da coleta
        """
        if not await self.initialize():
            return {'success': False, 'error': 'Falha na conexão MT5'}
        
        # Cria diretório de saída
        self._output_path.mkdir(parents=True, exist_ok=True)
        
        results = {
            'success': True,
            'collected': [],
            'failed': [],
            'total_candles': 0,
            'started_at': datetime.now().isoformat(),
        }
        
        total_tasks = len(self.config.symbols) * len(self.config.timeframes)
        current = 0
        
        for symbol in self.config.symbols:
            for tf in self.config.timeframes:
                current += 1
                logger.info(f"📊 [{current}/{total_tasks}] Coletando {symbol} {tf}...")
                
                try:
                    df = await self.collect_symbol_timeframe(symbol, tf)
                    
                    if df is not None and len(df) > 0:
                        # Salva arquivo
                        filepath = self._save_data(df, symbol, tf)
                        results['collected'].append({
                            'symbol': symbol,
                            'timeframe': tf,
                            'candles': len(df),
                            'start': df.index[0].isoformat() if hasattr(df.index[0], 'isoformat') else str(df.index[0]),
                            'end': df.index[-1].isoformat() if hasattr(df.index[-1], 'isoformat') else str(df.index[-1]),
                            'file': str(filepath),
                        })
                        results['total_candles'] += len(df)
                        logger.info(f"   ✅ {len(df)} candles salvos")
                    else:
                        results['failed'].append({
                            'symbol': symbol,
                            'timeframe': tf,
                            'error': 'Sem dados'
                        })
                        logger.warning(f"   ⚠️ Sem dados para {symbol} {tf}")
                        
                except Exception as e:
                    results['failed'].append({
                        'symbol': symbol,
                        'timeframe': tf,
                        'error': str(e)
                    })
                    logger.error(f"   ❌ Erro: {e}")
                
                # Pequeno delay para não sobrecarregar
                await asyncio.sleep(0.5)
        
        results['completed_at'] = datetime.now().isoformat()
        results['success'] = len(results['failed']) == 0
        
        # Salva resumo
        self._save_summary(results)
        
        return results
    
    async def collect_symbol_timeframe(
        self,
        symbol: str,
        timeframe_str: str,
        days_back: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Coleta dados de um símbolo/timeframe específico.
        
        Args:
            symbol: Símbolo (ex: XAUUSD)
            timeframe_str: Timeframe como string (ex: H1)
            days_back: Dias para trás (usa config se None)
            
        Returns:
            DataFrame com OHLCV ou None se erro
        """
        days = days_back or self.config.days_back
        timeframe = self.TIMEFRAME_MAP.get(timeframe_str)
        
        if timeframe is None:
            logger.error(f"Timeframe inválido: {timeframe_str}")
            return None
        
        # Calcula número estimado de candles
        candles_per_day = self.CANDLES_PER_DAY.get(timeframe_str, 24)
        estimated_candles = int(days * candles_per_day)
        
        # Se for muito, coleta em partes
        if estimated_candles > self.config.max_candles_per_request:
            return await self._collect_in_chunks(
                symbol, timeframe, timeframe_str, days
            )
        
        # Coleta direta
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            df = await self._data_service.get_candles_range(
                symbol, timeframe, start_time, end_time
            )
            
            return self._process_dataframe(df, symbol, timeframe_str)
            
        except Exception as e:
            logger.error(f"Erro ao coletar {symbol} {timeframe_str}: {e}")
            return None
    
    async def _collect_in_chunks(
        self,
        symbol: str,
        timeframe: Timeframe,
        timeframe_str: str,
        total_days: int
    ) -> Optional[pd.DataFrame]:
        """Coleta dados em partes para evitar limites do MT5."""
        
        all_data = []
        chunk_days = 30  # 30 dias por chunk
        
        end_time = datetime.now()
        remaining_days = total_days
        
        while remaining_days > 0:
            days_to_collect = min(chunk_days, remaining_days)
            start_time = end_time - timedelta(days=days_to_collect)
            
            try:
                df = await self._data_service.get_candles_range(
                    symbol, timeframe, start_time, end_time
                )
                
                if df is not None and len(df) > 0:
                    all_data.append(df)
                    
            except Exception as e:
                logger.warning(f"Erro no chunk {start_time} - {end_time}: {e}")
            
            end_time = start_time
            remaining_days -= days_to_collect
            
            await asyncio.sleep(0.2)  # Pequeno delay
        
        if not all_data:
            return None
        
        # Combina todos os DataFrames
        combined = pd.concat(all_data)
        combined = combined[~combined.index.duplicated(keep='first')]
        combined = combined.sort_index()
        
        return self._process_dataframe(combined, symbol, timeframe_str)
    
    def _process_dataframe(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> pd.DataFrame:
        """Processa e limpa DataFrame."""
        
        if df is None or len(df) == 0:
            return df
        
        # Garante colunas padrão
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        
        # Renomeia se necessário
        rename_map = {
            'Open': 'open', 'High': 'high', 'Low': 'low', 
            'Close': 'close', 'Volume': 'volume',
            'tick_volume': 'volume'
        }
        df = df.rename(columns=rename_map)
        
        # Remove colunas extras
        cols_to_keep = [c for c in required_cols if c in df.columns]
        if 'spread' in df.columns:
            cols_to_keep.append('spread')
        if 'real_volume' in df.columns:
            cols_to_keep.append('real_volume')
        
        df = df[cols_to_keep]
        
        # Adiciona metadados
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        # Remove NaN
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        
        # Remove duplicatas de índice
        df = df[~df.index.duplicated(keep='first')]
        
        # Ordena por tempo
        df = df.sort_index()
        
        return df
    
    def _save_data(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> Path:
        """Salva DataFrame no formato configurado."""
        
        # Cria subdiretório por símbolo
        symbol_dir = self._output_path / symbol
        symbol_dir.mkdir(exist_ok=True)
        
        # Nome do arquivo
        timestamp = datetime.now().strftime('%Y%m%d')
        filename = f"{symbol}_{timeframe}_{timestamp}"
        
        if self.config.output_format == 'parquet':
            filepath = symbol_dir / f"{filename}.parquet"
            df.to_parquet(filepath, compression='snappy')
        else:
            filepath = symbol_dir / f"{filename}.csv"
            df.to_csv(filepath)
        
        return filepath
    
    def _save_summary(self, results: Dict[str, Any]) -> None:
        """Salva resumo da coleta."""
        import json
        
        summary_path = self._output_path / "collection_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📋 Resumo salvo em {summary_path}")


async def main():
    """Função principal para execução via CLI."""
    
    parser = argparse.ArgumentParser(
        description='Coleta dados históricos do MT5 para treinamento ML'
    )
    parser.add_argument(
        '--symbol', '-s',
        type=str,
        help='Símbolo específico (default: todos)'
    )
    parser.add_argument(
        '--timeframe', '-t',
        type=str,
        help='Timeframe específico (default: todos)'
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=365,
        help='Dias de histórico (default: 365)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='data/historical',
        help='Diretório de saída'
    )
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['parquet', 'csv'],
        default='parquet',
        help='Formato de saída'
    )
    
    args = parser.parse_args()
    
    # Configura coleta
    config = CollectionConfig(
        days_back=args.days,
        output_dir=args.output,
        output_format=args.format,
    )
    
    if args.symbol:
        config.symbols = [args.symbol]
    if args.timeframe:
        config.timeframes = [args.timeframe]
    
    # Executa
    print("=" * 70)
    print("      VIRTUS - Coletor de Dados Históricos para ML")
    print("=" * 70)
    print()
    print(f"Símbolos:   {', '.join(config.symbols)}")
    print(f"Timeframes: {', '.join(config.timeframes)}")
    print(f"Período:    {config.days_back} dias")
    print(f"Saída:      {config.output_dir}")
    print(f"Formato:    {config.output_format}")
    print()
    print("-" * 70)
    
    collector = HistoricalDataCollector(config)
    results = await collector.collect_all()
    
    print()
    print("-" * 70)
    print("RESULTADO:")
    print(f"  Total coletados: {len(results['collected'])}")
    print(f"  Total candles:   {results['total_candles']:,}")
    print(f"  Falhas:          {len(results['failed'])}")
    print("-" * 70)
    
    if results['collected']:
        print()
        print("Arquivos gerados:")
        for item in results['collected']:
            print(f"  {item['symbol']} {item['timeframe']}: {item['candles']:,} candles")
    
    if results['failed']:
        print()
        print("Falhas:")
        for item in results['failed']:
            print(f"  {item['symbol']} {item['timeframe']}: {item['error']}")


if __name__ == "__main__":
    asyncio.run(main())
