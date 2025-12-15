"""
Teste Database - VIRTUS Trading System
======================================

Testa persistência de dados com SQLite.
"""

import sys
import os
from datetime import datetime, timedelta

# Configura path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))


def test_database():
    """Testa o módulo de database."""
    print("=" * 60)
    print("🗄️  TESTE DATABASE - VIRTUS TRADING SYSTEM")
    print("=" * 60)
    
    results = []
    
    # 1. Importação
    print("\n📦 1. TESTE IMPORTS")
    print("-" * 40)
    
    try:
        from src.database import (
            DatabaseConfig, DatabaseManager, get_database,
            Trade, Signal, TradeDirection, TradeStatus, ExitReason,
            TradeRepository, SignalRepository,
            create_all_tables,
        )
        print("  ✅ Imports OK")
        results.append(True)
    except Exception as e:
        print(f"  ❌ Import Error: {e}")
        results.append(False)
        return False
    
    # 2. Conexão
    print("\n📦 2. TESTE CONEXÃO")
    print("-" * 40)
    
    try:
        # Usa SQLite em memória para teste
        config = DatabaseConfig(
            driver="sqlite",
            sqlite_path=":memory:",
            echo=False,
        )
        
        # force_new=True para garantir nova instância
        db = DatabaseManager(config, force_new=True)
        print("  ✅ DatabaseManager criado")
        
        # Health check
        if db.health_check():
            print("  ✅ Health check OK")
        else:
            print("  ❌ Health check falhou")
            results.append(False)
            return False
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ Conexão Error: {e}")
        results.append(False)
        return False
    
    # 3. Criar tabelas
    print("\n📦 3. CRIAR TABELAS")
    print("-" * 40)
    
    try:
        db.create_tables()
        print("  ✅ Tabelas criadas")
        results.append(True)
    except Exception as e:
        print(f"  ❌ Create Tables Error: {e}")
        results.append(False)
        return False
    
    # 4. Trade Repository
    print("\n📦 4. TESTE TRADE REPOSITORY")
    print("-" * 40)
    
    try:
        trade_repo = TradeRepository(db)
        
        # Abre um trade
        trade1 = trade_repo.open_trade(
            ticket=12345678,
            symbol="XAUUSD",
            direction="buy",
            volume=0.1,
            entry_price=2000.50,
            stop_loss=1990.00,
            take_profit=2020.00,
            strategy="scalping",
            bot_id="gold_bot",
            comment="Test trade",
        )
        print(f"  ✅ Trade aberto: #{trade1.ticket}")
        
        # Abre outro trade
        trade2 = trade_repo.open_trade(
            ticket=12345679,
            symbol="EURUSD",
            direction="sell",
            volume=0.2,
            entry_price=1.0850,
            stop_loss=1.0900,
            take_profit=1.0750,
            strategy="trend",
            bot_id="euro_bot",
        )
        print(f"  ✅ Trade aberto: #{trade2.ticket}")
        
        # Lista trades abertos
        open_trades = trade_repo.get_open_trades()
        print(f"  ✅ Trades abertos: {len(open_trades)}")
        
        # Fecha trade 1 com lucro
        closed_trade = trade_repo.close_trade(
            ticket=12345678,
            exit_price=2015.00,
            profit=145.00,
            profit_pips=145,
            exit_reason="take_profit",
            commission=2.50,
            swap=0.30,
        )
        print(f"  ✅ Trade fechado: #{closed_trade.ticket} | Profit: ${closed_trade.net_profit:.2f}")
        
        # Fecha trade 2 com prejuízo
        closed_trade2 = trade_repo.close_trade(
            ticket=12345679,
            exit_price=1.0880,
            profit=-60.00,
            profit_pips=-30,
            exit_reason="stop_loss",
            commission=3.00,
        )
        print(f"  ✅ Trade fechado: #{closed_trade2.ticket} | Profit: ${closed_trade2.net_profit:.2f}")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ Trade Repository Error: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # 5. Estatísticas
    print("\n📦 5. TESTE ESTATÍSTICAS")
    print("-" * 40)
    
    try:
        stats = trade_repo.get_trade_stats()
        
        print(f"  📊 Total trades: {stats['total_trades']}")
        print(f"  📊 Win rate: {stats['win_rate']:.1f}%")
        print(f"  📊 Profit Factor: {stats['profit_factor']}")
        print(f"  📊 Total profit: ${stats['total_profit']:.2f}")
        print(f"  📊 Gross profit: ${stats['gross_profit']:.2f}")
        print(f"  📊 Gross loss: ${stats['gross_loss']:.2f}")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ Stats Error: {e}")
        results.append(False)
    
    # 6. Performance por símbolo
    print("\n📦 6. PERFORMANCE POR SÍMBOLO")
    print("-" * 40)
    
    try:
        by_symbol = trade_repo.get_performance_by_symbol()
        
        for symbol, perf in by_symbol.items():
            print(f"  📊 {symbol}:")
            print(f"      Trades: {perf['total_trades']}")
            print(f"      Win Rate: {perf['win_rate']:.1f}%")
            print(f"      Profit: ${perf['total_profit']:.2f}")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ Performance Error: {e}")
        results.append(False)
    
    # 7. Signal Repository
    print("\n📦 7. TESTE SIGNAL REPOSITORY")
    print("-" * 40)
    
    try:
        signal_repo = SignalRepository(db)
        
        # Registra sinais
        signal1 = signal_repo.record_signal(
            symbol="XAUUSD",
            signal_type="buy",
            strength="strong",
            confidence=0.85,
            entry_price=2000.50,
            stop_loss=1990.00,
            take_profit=2020.00,
            strategy="scalping",
            reasons=["RSI oversold", "Support level", "Bullish divergence"],
        )
        print(f"  ✅ Sinal registrado: {signal1.symbol} {signal1.signal_type.value}")
        
        signal2 = signal_repo.record_signal(
            symbol="EURUSD",
            signal_type="sell",
            strength="moderate",
            confidence=0.72,
            strategy="trend",
        )
        print(f"  ✅ Sinal registrado: {signal2.symbol} {signal2.signal_type.value}")
        
        # Marca como executado
        signal_repo.mark_executed(signal1.id, trade_ticket=12345678)
        print("  ✅ Sinal marcado como executado")
        
        # Stats
        signal_stats = signal_repo.get_signal_stats()
        print(f"  📊 Total sinais: {signal_stats['total_signals']}")
        print(f"  📊 Executados: {signal_stats['executed_signals']}")
        print(f"  📊 Taxa execução: {signal_stats['execution_rate']:.1f}%")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ Signal Repository Error: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # 8. Equity Curve
    print("\n📦 8. TESTE EQUITY CURVE")
    print("-" * 40)
    
    try:
        curve = trade_repo.get_equity_curve(initial_balance=5000)
        print(f"  ✅ Equity curve: {len(curve)} pontos")
        
        if curve:
            print(f"  📊 Initial: ${curve[0][1]:,.2f}")
            print(f"  📊 Final: ${curve[-1][1]:,.2f}")
        
        # Drawdown analysis
        dd = trade_repo.get_drawdown_analysis(initial_balance=5000)
        print(f"  📊 Max Drawdown: {dd['max_drawdown_percent']:.2f}%")
        print(f"  📊 Current Drawdown: {dd['current_drawdown_percent']:.2f}%")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ Equity Curve Error: {e}")
        results.append(False)
    
    # Resumo
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ TODOS OS TESTES PASSARAM: {passed}/{total}")
    else:
        print(f"⚠️ ALGUNS TESTES FALHARAM: {passed}/{total}")
    
    print("=" * 60)
    
    # Cleanup
    db.close()
    
    return passed == total


if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)
