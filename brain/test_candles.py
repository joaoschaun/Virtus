"""
Teste de Análise de Candles em Todos os Timeframes
===================================================
"""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def test_candles():
    # Inicializa MT5
    if not mt5.initialize():
        print('❌ Erro ao inicializar MT5')
        return False

    # Verifica conta
    account = mt5.account_info()
    print('='*60)
    print('📊 CONTA MT5:')
    print(f'  👤 Login: {account.login}')
    print(f'  📛 Nome: {account.name}')
    print(f'  🖥️ Servidor: {account.server}')
    print(f'  💰 Saldo: ${account.balance:.2f}')
    print(f'  📈 Equity: ${account.equity:.2f}')
    print('='*60)

    # Testa candles em todos os timeframes
    print('\n🕯️ TESTANDO CANDLES POR TIMEFRAME:')
    print('-'*60)

    timeframes = {
        'M1': mt5.TIMEFRAME_M1,
        'M5': mt5.TIMEFRAME_M5,
        'M15': mt5.TIMEFRAME_M15,
        'M30': mt5.TIMEFRAME_M30,
        'H1': mt5.TIMEFRAME_H1,
        'H4': mt5.TIMEFRAME_H4,
        'D1': mt5.TIMEFRAME_D1,
        'W1': mt5.TIMEFRAME_W1,
    }

    symbols = ['XAUUSD', 'EURUSD', 'GBPUSD']
    all_results = {}

    for symbol in symbols:
        print(f'\n📈 {symbol}:')
        results = []
        
        for tf_name, tf_value in timeframes.items():
            rates = mt5.copy_rates_from_pos(symbol, tf_value, 0, 10)
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                last = df.iloc[-1]
                change = ((last['close'] - last['open']) / last['open']) * 100
                emoji = '🟢' if change > 0 else '🔴' if change < 0 else '🟡'
                print(f"  {tf_name:4} | {emoji} {last['time'].strftime('%d/%m %H:%M')} | O:{last['open']:.2f} H:{last['high']:.2f} L:{last['low']:.2f} C:{last['close']:.2f} ({change:+.2f}%)")
                results.append(True)
            else:
                print(f"  {tf_name:4} | ❌ Sem dados")
                results.append(False)
        
        all_results[symbol] = results

    print('\n' + '='*60)
    print('📊 RESUMO:')
    for symbol, results in all_results.items():
        ok_count = sum(results)
        total = len(results)
        status = '✅' if ok_count == total else '⚠️'
        print(f"  {status} {symbol}: {ok_count}/{total} timeframes OK")
    
    print('='*60)
    print(f'⏰ Teste realizado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')
    
    mt5.shutdown()
    return True

if __name__ == "__main__":
    test_candles()
