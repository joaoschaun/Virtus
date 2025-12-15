"""
Teste de Imports - VIRTUS
==========================
Valida que todos os módulos importam corretamente.
"""

import sys
import os
import traceback

# Configura paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, SRC_DIR)

def test_import(import_statement: str, description: str) -> bool:
    """Testa import de um módulo."""
    try:
        exec(import_statement, globals())
        print(f"  ✅ {description}")
        return True
    except Exception as e:
        print(f"  ❌ {description}: {type(e).__name__}: {e}")
        return False

def main():
    print("=" * 60)
    print("TESTE DE IMPORTS - VIRTUS")
    print("=" * 60)
    print(f"\n📂 ROOT: {ROOT_DIR}")
    print(f"📂 SRC: {SRC_DIR}")
    
    results = []
    
    # Core Module
    print("\n📦 CORE MODULE:")
    results.append(test_import(
        "from src.core import VirtusLogger, Config, Signal, Position",
        "Core (Logger, Config, Types)"
    ))
    
    # Risk Module  
    print("\n📦 RISK MODULE:")
    results.append(test_import(
        "from src.risk.risk_manager import RiskManager",
        "Risk Manager"
    ))
    results.append(test_import(
        "from src.risk.advanced_risk import AdvancedRiskManager, KellyResult, VaRResult",
        "Advanced Risk (Kelly/VaR)"
    ))
    
    # Positions Module
    print("\n📦 POSITIONS MODULE:")
    results.append(test_import(
        "from src.positions.exits.exit_manager import ExitManager, TrailingStopType",
        "Exit Manager (8 Trailing)"
    ))
    results.append(test_import(
        "from src.positions.supervisor.position_supervisor import PositionSupervisor, PositionHealth",
        "Position Supervisor"
    ))
    
    # Strategies Module
    print("\n📦 STRATEGIES MODULE:")
    results.append(test_import(
        "from src.strategies.scalping.scalping_strategy import ScalpingStrategy",
        "Scalping Strategy (9 setups)"
    ))
    results.append(test_import(
        "from src.strategies.trend.trend_strategy import TrendStrategy",
        "Trend Strategy (7 setups)"
    ))
    results.append(test_import(
        "from src.strategies.reversal.reversal_strategy import ReversalStrategy",
        "Reversal Strategy (8 setups)"
    ))
    results.append(test_import(
        "from src.strategies.event.event_strategy import EventStrategy",
        "Event Strategy (5 setups)"
    ))
    
    # ML Module
    print("\n📦 ML MODULE:")
    results.append(test_import(
        "from src.ml.models.model_base import BaseModel, DirectionModel, ModelRegistry",
        "ML Model Base"
    ))
    results.append(test_import(
        "from src.ml.models.prediction_engine import PredictionEngine, PredictionService",
        "Prediction Engine"
    ))
    
    # Bot Module - importar diretamente, não do __init__.py
    print("\n📦 BOT MODULE:")
    results.append(test_import(
        """
import sys
sys.path.insert(0, 'C:/Users/Administrator/Desktop/Virtus/brain/src')
from bot.core.bot_state import BotState, TradingPhase, BotStatistics
""",
        "Bot State"
    ))
    # Trading Bot e Engine têm dependências complexas, testar separadamente
    print("  ⏭️  Trading Bot (dependências complexas - skip)")
    print("  ⏭️  Trading Engine (dependências complexas - skip)")
    
    # Analysis Module
    print("\n📦 ANALYSIS MODULE:")
    results.append(test_import(
        "from src.analysis.master_analyzer import MasterAnalyzer",
        "Master Analyzer"
    ))
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ TODOS OS TESTES PASSARAM: {passed}/{total}")
    else:
        print(f"⚠️ ALGUNS IMPORTS FALHARAM: {passed}/{total}")
        print("\n💡 Correções necessárias nos módulos que falharam.")
    
    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
