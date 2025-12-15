"""
Testes do módulo de Estratégias
================================

Valida ScalpingStrategy, TrendStrategy, ReversalStrategy e EventStrategy.
"""

import sys
from pathlib import Path
from datetime import datetime
import numpy as np

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestStrategyImports:
    """Testa imports das estratégias."""
    
    def test_import_base_strategy(self):
        """Testa import da BaseStrategy."""
        from strategies import BaseStrategy
        assert BaseStrategy is not None
        print("✅ BaseStrategy importada")
    
    def test_import_strategy_factory(self):
        """Testa import do StrategyFactory."""
        from strategies import StrategyFactory
        assert StrategyFactory is not None
        print("✅ StrategyFactory importado")
    
    def test_import_scalping_strategy(self):
        """Testa import da ScalpingStrategy."""
        from strategies import ScalpingStrategy, ScalpingConfig, ScalpingSetup
        assert ScalpingStrategy is not None
        assert ScalpingConfig is not None
        assert ScalpingSetup is not None
        print("✅ ScalpingStrategy importada")
    
    def test_import_trend_strategy(self):
        """Testa import da TrendStrategy."""
        from strategies import TrendStrategy, TrendConfig, TrendSetup
        assert TrendStrategy is not None
        assert TrendConfig is not None
        assert TrendSetup is not None
        print("✅ TrendStrategy importada")
    
    def test_import_reversal_strategy(self):
        """Testa import da ReversalStrategy."""
        from strategies import ReversalStrategy, ReversalConfig, ReversalSetup
        assert ReversalStrategy is not None
        assert ReversalConfig is not None
        assert ReversalSetup is not None
        print("✅ ReversalStrategy importada")
    
    def test_import_event_strategy(self):
        """Testa import da EventStrategy."""
        from strategies import EventStrategy, EventConfig, EventSetup
        assert EventStrategy is not None
        assert EventConfig is not None
        assert EventSetup is not None
        print("✅ EventStrategy importada")


class TestStrategyInstantiation:
    """Testa instanciação das estratégias."""
    
    def test_scalping_strategy_creation(self):
        """Testa criação da ScalpingStrategy."""
        from strategies import ScalpingStrategy, ScalpingConfig
        
        config = ScalpingConfig()
        strategy = ScalpingStrategy(config)
        
        assert strategy is not None
        assert strategy.config == config
        print(f"✅ ScalpingStrategy criada com {len(ScalpingConfig.__dataclass_fields__)} configurações")
    
    def test_trend_strategy_creation(self):
        """Testa criação da TrendStrategy."""
        from strategies import TrendStrategy, TrendConfig
        
        config = TrendConfig()
        strategy = TrendStrategy(config)
        
        assert strategy is not None
        assert strategy.config == config
        print(f"✅ TrendStrategy criada com {len(TrendConfig.__dataclass_fields__)} configurações")
    
    def test_reversal_strategy_creation(self):
        """Testa criação da ReversalStrategy."""
        from strategies import ReversalStrategy, ReversalConfig
        
        config = ReversalConfig()
        strategy = ReversalStrategy(config)
        
        assert strategy is not None
        assert strategy.config == config
        print(f"✅ ReversalStrategy criada com {len(ReversalConfig.__dataclass_fields__)} configurações")
    
    def test_event_strategy_creation(self):
        """Testa criação da EventStrategy."""
        from strategies import EventStrategy, EventConfig
        
        config = EventConfig()
        strategy = EventStrategy(config)
        
        assert strategy is not None
        assert strategy.config == config
        print(f"✅ EventStrategy criada com {len(EventConfig.__dataclass_fields__)} configurações")


class TestScalpingSetups:
    """Testa setups da estratégia de scalping."""
    
    def test_scalping_setup_types(self):
        """Verifica tipos de setup disponíveis."""
        from strategies import ScalpingSetup
        
        expected_setups = [
            "SPREAD_COMPRESSION",
            "LIQUIDITY_GRAB",
            "MOMENTUM_BURST",
            "ABSORPTION",
            "DELTA_DIVERGENCE",
            "VWAP_BOUNCE",
            "MICROSTRUCTURE_REVERSAL",
            "ORDER_BLOCK_TAP",
            "FVG_FILL",
        ]
        
        available = [s.name for s in ScalpingSetup]
        
        for setup in expected_setups:
            assert setup in available, f"Setup {setup} não encontrado"
        
        print(f"✅ ScalpingStrategy tem {len(available)} setups disponíveis")
    
    def test_scalping_config_defaults(self):
        """Verifica configurações padrão do scalping."""
        from strategies import ScalpingConfig
        
        config = ScalpingConfig()
        
        assert config.primary_tf == "M1"
        assert config.min_risk_reward >= 1.0
        assert config.max_spread_pips > 0
        
        print(f"✅ ScalpingConfig: TF={config.primary_tf}, RR≥{config.min_risk_reward}")


class TestTrendSetups:
    """Testa setups da estratégia de tendência."""
    
    def test_trend_setup_types(self):
        """Verifica tipos de setup disponíveis."""
        from strategies import TrendSetup
        
        expected_setups = [
            "BOS_CONTINUATION",
            "ORDER_BLOCK_PULLBACK",
            "FVG_RETEST",
            "FIBONACCI_PULLBACK",
            "MTF_ALIGNMENT",
            "STRUCTURE_SHIFT",
            "LIQUIDITY_SWEEP_CONTINUATION",
        ]
        
        available = [s.name for s in TrendSetup]
        
        for setup in expected_setups:
            assert setup in available, f"Setup {setup} não encontrado"
        
        print(f"✅ TrendStrategy tem {len(available)} setups disponíveis")
    
    def test_trend_config_defaults(self):
        """Verifica configurações padrão da tendência."""
        from strategies import TrendConfig
        
        config = TrendConfig()
        
        assert config.entry_tf == "M15"
        assert config.bias_tf == "H4"
        assert config.min_risk_reward >= 2.0
        
        print(f"✅ TrendConfig: Entry={config.entry_tf}, Bias={config.bias_tf}, RR≥{config.min_risk_reward}")


class TestReversalSetups:
    """Testa setups da estratégia de reversão."""
    
    def test_reversal_setup_types(self):
        """Verifica tipos de setup disponíveis."""
        from strategies import ReversalSetup
        
        expected_setups = [
            "CHOCH_REVERSAL",
            "DIVERGENCE_REVERSAL",
            "EXHAUSTION_PATTERN",
            "SUPPLY_DEMAND_REJECTION",
            "FIBONACCI_EXTENSION",
            "LIQUIDITY_TRAP",
            "WYCKOFF_SPRING_UPTHRUST",
            "DOUBLE_TOP_BOTTOM",
        ]
        
        available = [s.name for s in ReversalSetup]
        
        for setup in expected_setups:
            assert setup in available, f"Setup {setup} não encontrado"
        
        print(f"✅ ReversalStrategy tem {len(available)} setups disponíveis")
    
    def test_reversal_config_defaults(self):
        """Verifica configurações padrão da reversão."""
        from strategies import ReversalConfig
        
        config = ReversalConfig()
        
        assert config.signal_tf == "M15"
        assert config.min_risk_reward >= 2.0
        
        print(f"✅ ReversalConfig: Signal={config.signal_tf}, RR≥{config.min_risk_reward}")


class TestEventSetups:
    """Testa setups da estratégia de eventos."""
    
    def test_event_setup_types(self):
        """Verifica tipos de setup disponíveis."""
        from strategies import EventSetup
        
        # EventSetup deve ter pelo menos alguns tipos
        available = [s.name for s in EventSetup]
        assert len(available) >= 1, "EventSetup deve ter pelo menos 1 setup"
        
        print(f"✅ EventStrategy tem {len(available)} setups disponíveis")


class TestStrategySummary:
    """Resumo das estratégias."""
    
    def test_print_strategy_summary(self):
        """Imprime resumo de todas as estratégias."""
        from strategies import (
            ScalpingStrategy, ScalpingSetup, ScalpingConfig,
            TrendStrategy, TrendSetup, TrendConfig,
            ReversalStrategy, ReversalSetup, ReversalConfig,
            EventStrategy, EventSetup, EventConfig,
        )
        
        print("\n" + "=" * 60)
        print("📊 RESUMO DAS ESTRATÉGIAS VIRTUS")
        print("=" * 60)
        
        strategies = [
            ("Scalping", ScalpingSetup, ScalpingConfig),
            ("Trend", TrendSetup, TrendConfig),
            ("Reversal", ReversalSetup, ReversalConfig),
            ("Event", EventSetup, EventConfig),
        ]
        
        total_setups = 0
        
        for name, setup_enum, config_class in strategies:
            setups = [s.name for s in setup_enum]
            configs = list(config_class.__dataclass_fields__.keys())
            total_setups += len(setups)
            
            print(f"\n🎯 {name}Strategy")
            print(f"   Setups: {len(setups)}")
            print(f"   Configurações: {len(configs)}")
            print(f"   Setups disponíveis: {', '.join(setups[:3])}...")
        
        print(f"\n📈 Total de setups: {total_setups}")
        print("=" * 60)
        
        assert total_setups >= 20, "Deve haver pelo menos 20 setups no total"
        print("\n✅ Resumo das estratégias validado!")


def run_all_tests():
    """Executa todos os testes."""
    print("=" * 60)
    print("🧪 VIRTUS STRATEGIES - TESTES")
    print("=" * 60)
    print()
    
    test_classes = [
        TestStrategyImports,
        TestStrategyInstantiation,
        TestScalpingSetups,
        TestTrendSetups,
        TestReversalSetups,
        TestEventSetups,
        TestStrategySummary,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)
        
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                total_tests += 1
                try:
                    getattr(instance, method_name)()
                    passed_tests += 1
                except Exception as e:
                    failed_tests.append((f"{test_class.__name__}.{method_name}", str(e)))
                    print(f"❌ {method_name}: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTADO: {passed_tests}/{total_tests} testes passaram")
    print("=" * 60)
    
    if failed_tests:
        print("\n❌ Testes que falharam:")
        for name, error in failed_tests:
            print(f"   - {name}: {error}")
    else:
        print("\n✅ TODOS OS TESTES PASSARAM!")
    
    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
