"""
Teste Funcional - VIRTUS Trading System
=========================================

Testa o fluxo completo do sistema em modo simulação.
"""

import asyncio
import sys
import os

# Configura path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

import MetaTrader5 as mt5


async def test_full_system():
    """Teste funcional completo."""
    print("=" * 60)
    print("🧪 TESTE FUNCIONAL - VIRTUS TRADING SYSTEM")
    print("=" * 60)
    
    results = []
    
    # 1. Conexão MT5
    print("\n📊 1. TESTE MT5")
    print("-" * 40)
    
    if not mt5.initialize():
        print("  ❌ Falha ao inicializar MT5")
        return False
    
    print("  ✅ MT5 inicializado")
    
    account = mt5.account_info()
    print(f"  ✅ Conta: {account.login} | Balance: ${account.balance:,.2f}")
    
    # Testa dados de mercado
    symbols = ["XAUUSD", "EURUSD", "GBPUSD"]
    for symbol in symbols:
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            print(f"  ✅ {symbol}: {tick.bid:.5f}")
            results.append(True)
        else:
            print(f"  ❌ {symbol}: Sem dados")
            results.append(False)
    
    # Testa candles
    candles = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 100)
    if candles is not None and len(candles) > 0:
        print(f"  ✅ Candles XAUUSD H1: {len(candles)} bars")
        results.append(True)
    else:
        print("  ❌ Falha ao obter candles")
        results.append(False)
    
    # 2. Core Module
    print("\n📦 2. TESTE CORE MODULE")
    print("-" * 40)
    
    try:
        from src.core import VirtusLogger, Config, Signal, SignalType, SignalStrength
        from datetime import datetime
        
        # VirtusLogger usa classmethod get_logger()
        logger = VirtusLogger.get_logger("test")
        logger.info("Logger funcionando!")
        print("  ✅ Logger OK")
        
        config = Config()
        print("  ✅ Config carregada")
        
        # Teste Signal
        signal = Signal(
            symbol="XAUUSD",
            type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            timestamp=datetime.now(),
            entry_price=2000.0,
            confidence=0.85
        )
        print(f"  ✅ Signal: {signal.type.value} @ {signal.entry_price}")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ Core Module: {e}")
        results.append(False)
    
    # 3. Risk Module
    print("\n📦 3. TESTE RISK MODULE")
    print("-" * 40)
    
    try:
        from src.risk.advanced_risk import AdvancedRiskManager, SizingMethod
        
        risk_mgr = AdvancedRiskManager(
            initial_capital=account.balance,
            sizing_method=SizingMethod.HALF_KELLY
        )
        
        print("  ✅ AdvancedRiskManager criado")
        print(f"  ✅ Capital inicial: ${account.balance:,.2f}")
        print("  ✅ Método: HALF_KELLY")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ Risk Module: {e}")
        results.append(False)
    
    # 4. Strategies Module
    print("\n📦 4. TESTE STRATEGIES MODULE")
    print("-" * 40)
    
    try:
        from src.strategies.scalping.scalping_strategy import ScalpingStrategy
        from src.strategies.trend.trend_strategy import TrendStrategy
        
        scalping = ScalpingStrategy()
        trend = TrendStrategy()
        
        print(f"  ✅ Scalping Strategy: {scalping.name}")
        print(f"  ✅ Trend Strategy: {trend.name}")
        results.append(True)
    except Exception as e:
        print(f"  ❌ Strategies Module: {e}")
        results.append(False)
    
    # 5. ML Module
    print("\n📦 5. TESTE ML MODULE")
    print("-" * 40)
    
    try:
        from src.ml.models.prediction_engine import PredictionService
        
        pred_service = PredictionService()
        await pred_service.initialize()
        
        # Testa predição
        market_data = {
            'rsi': 45,
            'macd_histogram': 0.002,
            'adx': 25,
            'close': 2000.0,
            'sma_20': 1995.0,
            'sma_50': 1990.0,
            'volume': 1000,
            'avg_volume': 800,
        }
        
        prediction = await pred_service.predict("XAUUSD", market_data)
        if prediction:
            print(f"  ✅ ML Prediction: {prediction.direction} ({prediction.confidence:.1%})")
        else:
            print("  ⚠️ ML sem predição (modelo não treinado)")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ ML Module: {e}")
        results.append(False)
    
    # 6. Position Management
    print("\n📦 6. TESTE POSITION MANAGEMENT")
    print("-" * 40)
    
    try:
        from src.positions.supervisor.position_supervisor import PositionSupervisor, BreakEvenConfig
        
        be_config = BreakEvenConfig(
            enabled=True,
            activation_pips=15.0,
            offset_pips=1.0
        )
        supervisor = PositionSupervisor(be_config=be_config)
        print("  ✅ Position Supervisor inicializado")
        print(f"  ✅ Break-even: {be_config.activation_pips} pips")
        results.append(True)
    except Exception as e:
        print(f"  ❌ Position Management: {e}")
        results.append(False)
    
    # Encerra MT5
    mt5.shutdown()
    
    # Resumo
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ TODOS OS TESTES PASSARAM: {passed}/{total}")
    else:
        print(f"⚠️ ALGUNS TESTES FALHARAM: {passed}/{total}")
    
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(test_full_system())
    sys.exit(0 if success else 1)
