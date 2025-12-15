"""
VIRTUS - Coleta Massiva de Dados Históricos MT5
Coleta dados de todos os timeframes para ML
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import json

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuração de coleta
SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD"]

# Timeframes e quantidade de candles a coletar
# MT5 limita ~100k candles por request, mas podemos pegar anos de dados
TIMEFRAMES_CONFIG = {
    "M1": {
        "mt5_tf": None,  # Será setado depois
        "bars": 500000,   # ~1 ano de M1 (mercado 24h)
        "description": "1 minuto"
    },
    "M5": {
        "mt5_tf": None,
        "bars": 200000,   # ~3 anos de M5
        "description": "5 minutos"
    },
    "M15": {
        "mt5_tf": None,
        "bars": 100000,   # ~4 anos de M15
        "description": "15 minutos"
    },
    "M30": {
        "mt5_tf": None,
        "bars": 80000,    # ~5 anos de M30
        "description": "30 minutos"
    },
    "H1": {
        "mt5_tf": None,
        "bars": 50000,    # ~6 anos de H1
        "description": "1 hora"
    },
    "H4": {
        "mt5_tf": None,
        "bars": 20000,    # ~8 anos de H4
        "description": "4 horas"
    },
    "D1": {
        "mt5_tf": None,
        "bars": 5000,     # ~20 anos de D1
        "description": "Diário"
    }
}


def setup_mt5():
    """Inicializa conexão com MT5"""
    try:
        import MetaTrader5 as mt5
        
        if not mt5.initialize():
            print(f"[ERRO] Falha ao inicializar MT5: {mt5.last_error()}")
            return None
            
        # Configurar timeframes
        TIMEFRAMES_CONFIG["M1"]["mt5_tf"] = mt5.TIMEFRAME_M1
        TIMEFRAMES_CONFIG["M5"]["mt5_tf"] = mt5.TIMEFRAME_M5
        TIMEFRAMES_CONFIG["M15"]["mt5_tf"] = mt5.TIMEFRAME_M15
        TIMEFRAMES_CONFIG["M30"]["mt5_tf"] = mt5.TIMEFRAME_M30
        TIMEFRAMES_CONFIG["H1"]["mt5_tf"] = mt5.TIMEFRAME_H1
        TIMEFRAMES_CONFIG["H4"]["mt5_tf"] = mt5.TIMEFRAME_H4
        TIMEFRAMES_CONFIG["D1"]["mt5_tf"] = mt5.TIMEFRAME_D1
        
        print(f"[OK] MT5 conectado - Build {mt5.version()}")
        return mt5
        
    except ImportError:
        print("[ERRO] MetaTrader5 não instalado")
        return None


def collect_data(mt5, symbol: str, timeframe: str, config: dict) -> pd.DataFrame:
    """Coleta dados de um símbolo/timeframe"""
    
    mt5_tf = config["mt5_tf"]
    bars = config["bars"]
    
    print(f"  Coletando {bars:,} candles de {symbol} {timeframe}...")
    
    # Coleta em lotes para evitar timeout
    all_data = []
    batch_size = 50000
    end_date = datetime.now()
    
    remaining = bars
    while remaining > 0:
        current_batch = min(batch_size, remaining)
        
        rates = mt5.copy_rates_from(
            symbol,
            mt5_tf,
            end_date,
            current_batch
        )
        
        if rates is None or len(rates) == 0:
            if len(all_data) == 0:
                print(f"    [WARN] Nenhum dado retornado")
                return pd.DataFrame()
            break
            
        df_batch = pd.DataFrame(rates)
        all_data.append(df_batch)
        
        # Atualizar para próximo lote (dados mais antigos)
        end_date = datetime.fromtimestamp(rates[0]['time']) - timedelta(minutes=1)
        remaining -= len(rates)
        
        if len(rates) < current_batch:
            # Não há mais dados disponíveis
            break
    
    if not all_data:
        return pd.DataFrame()
    
    # Combinar todos os lotes
    df = pd.concat(all_data, ignore_index=True)
    
    # Ordenar por tempo
    df = df.sort_values('time').reset_index(drop=True)
    
    # Remover duplicatas
    df = df.drop_duplicates(subset=['time']).reset_index(drop=True)
    
    # Converter timestamp
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Adicionar metadados
    df['symbol'] = symbol
    df['timeframe'] = timeframe
    
    print(f"    [OK] {len(df):,} candles coletados")
    print(f"    Período: {df['time'].min()} até {df['time'].max()}")
    
    return df


def save_data(df: pd.DataFrame, symbol: str, timeframe: str, base_path: Path):
    """Salva dados em CSV"""
    
    if df.empty:
        return None
        
    # Criar diretório
    output_dir = base_path / symbol / timeframe
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Salvar CSV
    csv_path = output_dir / "raw_data.csv"
    df.to_csv(csv_path, index=False)
    
    # Salvar metadata
    metadata = {
        "symbol": symbol,
        "timeframe": timeframe,
        "total_candles": len(df),
        "start_date": str(df['time'].min()),
        "end_date": str(df['time'].max()),
        "columns": list(df.columns),
        "collected_at": datetime.now().isoformat()
    }
    
    meta_path = output_dir / "collection_metadata.json"
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return csv_path


def main():
    """Executa coleta massiva"""
    
    print("=" * 60)
    print("     VIRTUS - COLETA MASSIVA DE DADOS MT5")
    print("=" * 60)
    print()
    
    # Inicializar MT5
    mt5 = setup_mt5()
    if mt5 is None:
        return
    
    # Path para salvar dados
    base_path = Path(__file__).parent.parent / "data" / "historical"
    base_path.mkdir(parents=True, exist_ok=True)
    
    # Estatísticas
    total_candles = 0
    collection_summary = []
    
    # Coletar para cada símbolo e timeframe
    for symbol in SYMBOLS:
        print(f"\n{'=' * 60}")
        print(f"  SÍMBOLO: {symbol}")
        print(f"{'=' * 60}")
        
        # Verificar se símbolo existe
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"  [ERRO] Símbolo {symbol} não encontrado")
            continue
            
        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)
        
        for tf_name, tf_config in TIMEFRAMES_CONFIG.items():
            print(f"\n  --- {tf_name} ({tf_config['description']}) ---")
            
            # Coletar dados
            df = collect_data(mt5, symbol, tf_name, tf_config)
            
            if df.empty:
                continue
            
            # Salvar dados
            csv_path = save_data(df, symbol, tf_name, base_path)
            
            if csv_path:
                total_candles += len(df)
                collection_summary.append({
                    "symbol": symbol,
                    "timeframe": tf_name,
                    "candles": len(df),
                    "start": str(df['time'].min()),
                    "end": str(df['time'].max()),
                    "file": str(csv_path)
                })
    
    # Fechar MT5
    mt5.shutdown()
    
    # Salvar resumo geral
    summary_path = base_path / "collection_summary.json"
    summary = {
        "total_candles": total_candles,
        "collected_at": datetime.now().isoformat(),
        "symbols": SYMBOLS,
        "timeframes": list(TIMEFRAMES_CONFIG.keys()),
        "details": collection_summary
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Resumo final
    print("\n" + "=" * 60)
    print("     RESUMO DA COLETA")
    print("=" * 60)
    print(f"\n  Total de candles coletados: {total_candles:,}")
    print(f"\n  Dados por símbolo/timeframe:")
    
    for item in collection_summary:
        print(f"    - {item['symbol']} {item['timeframe']}: {item['candles']:,} candles")
    
    print(f"\n  Dados salvos em: {base_path}")
    print(f"  Resumo: {summary_path}")
    print("\n" + "=" * 60)
    print("     COLETA CONCLUÍDA!")
    print("=" * 60)


if __name__ == "__main__":
    main()
