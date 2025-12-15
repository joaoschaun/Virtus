"""
Teste de Conexão MT5
=====================
"""

import MetaTrader5 as mt5

def test_mt5():
    print("=" * 50)
    print("TESTE DE CONEXÃO MT5")
    print("=" * 50)
    
    # Versão
    print(f"\n📦 MT5 Package Version: {mt5.__version__}")
    
    # Inicializa
    print("\n🔄 Inicializando MT5...")
    if not mt5.initialize():
        print(f"❌ Falha ao inicializar: {mt5.last_error()}")
        return False
    
    print("✅ MT5 Inicializado!")
    
    # Info do terminal
    terminal_info = mt5.terminal_info()
    if terminal_info:
        print(f"\n📊 Terminal Info:")
        print(f"   Path: {terminal_info.path}")
        print(f"   Data Path: {terminal_info.data_path}")
        print(f"   Connected: {terminal_info.connected}")
        print(f"   Trade Allowed: {terminal_info.trade_allowed}")
    
    # Info da conta
    account_info = mt5.account_info()
    if account_info:
        print(f"\n💰 Account Info:")
        print(f"   Login: {account_info.login}")
        print(f"   Server: {account_info.server}")
        print(f"   Balance: ${account_info.balance:,.2f}")
        print(f"   Equity: ${account_info.equity:,.2f}")
        print(f"   Margin: ${account_info.margin:,.2f}")
        print(f"   Free Margin: ${account_info.margin_free:,.2f}")
        print(f"   Leverage: 1:{account_info.leverage}")
    
    # Testa símbolos
    print(f"\n📈 Testando Símbolos:")
    symbols = ["XAUUSD", "EURUSD", "GBPUSD"]
    
    for symbol in symbols:
        info = mt5.symbol_info(symbol)
        if info:
            tick = mt5.symbol_info_tick(symbol)
            print(f"   {symbol}: Bid={tick.bid:.5f} Ask={tick.ask:.5f} Spread={info.spread}")
        else:
            print(f"   {symbol}: ❌ Não disponível")
    
    # Fecha
    mt5.shutdown()
    print("\n✅ Teste concluído com sucesso!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_mt5()
