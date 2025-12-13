"""
BRAIN - Test Suite
Testes unitários do sistema
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch


# =============================================================================
# TEST: Core Types
# =============================================================================

class TestCoreTypes:
    """Testes para tipos do core"""
    
    def test_signal_creation(self):
        """Testa criação de Signal"""
        from brain.src.core.types import Signal
        
        signal = Signal(
            symbol="XAUUSD",
            direction="buy",
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            confidence=0.75,
            strategy="scalping"
        )
        
        assert signal.symbol == "XAUUSD"
        assert signal.direction == "buy"
        assert signal.entry_price == 2000.0
        assert signal.risk_reward_ratio == 2.0  # 20 TP / 10 SL
    
    def test_position_dataclass(self):
        """Testa Position dataclass"""
        from brain.src.core.types import Position, OrderType
        
        pos = Position(
            ticket=12345,
            symbol="EURUSD",
            type=OrderType.BUY,
            volume=0.1,
            price_open=1.1000,
            price_current=1.1050,
            profit=50.0
        )
        
        assert pos.ticket == 12345
        assert pos.volume == 0.1
        assert pos.profit == 50.0


# =============================================================================
# TEST: Technical Indicators
# =============================================================================

class TestTechnicalIndicators:
    """Testes para indicadores técnicos"""
    
    @pytest.fixture
    def sample_data(self):
        """Dados de teste"""
        return np.array([
            100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
            111, 110, 112, 114, 113, 115, 117, 116, 118, 120
        ], dtype=float)
    
    def test_sma_calculation(self, sample_data):
        """Testa cálculo de SMA"""
        from brain.src.analysis.technical.indicators import TechnicalIndicators
        
        sma = TechnicalIndicators.sma(sample_data, 5)
        
        # SMA(5) do índice 4 = média de [100,102,101,103,105] = 102.2
        assert not np.isnan(sma[4])
        assert round(sma[4], 1) == 102.2
    
    def test_ema_calculation(self, sample_data):
        """Testa cálculo de EMA"""
        from brain.src.analysis.technical.indicators import TechnicalIndicators
        
        ema = TechnicalIndicators.ema(sample_data, 5)
        
        # Primeira EMA = SMA
        assert not np.isnan(ema[4])
        # EMA deve ser diferente de SMA após o período inicial
        assert ema[10] != TechnicalIndicators.sma(sample_data, 5)[10]
    
    def test_rsi_bounds(self, sample_data):
        """Testa que RSI fica entre 0-100"""
        from brain.src.analysis.technical.indicators import TechnicalIndicators
        
        rsi = TechnicalIndicators.rsi(sample_data, 14)
        
        # RSI válidos devem estar entre 0-100
        valid_rsi = rsi[~np.isnan(rsi)]
        assert all(0 <= v <= 100 for v in valid_rsi)
    
    def test_macd_components(self, sample_data):
        """Testa componentes do MACD"""
        from brain.src.analysis.technical.indicators import TechnicalIndicators
        
        macd_line, signal_line, histogram = TechnicalIndicators.macd(sample_data)
        
        assert len(macd_line) == len(sample_data)
        assert len(signal_line) == len(sample_data)
        assert len(histogram) == len(sample_data)
        
        # Histogram = MACD - Signal
        valid_idx = ~np.isnan(macd_line) & ~np.isnan(signal_line)
        np.testing.assert_array_almost_equal(
            histogram[valid_idx],
            macd_line[valid_idx] - signal_line[valid_idx]
        )
    
    def test_bollinger_bands(self, sample_data):
        """Testa Bollinger Bands"""
        from brain.src.analysis.technical.indicators import TechnicalIndicators
        
        upper, middle, lower = TechnicalIndicators.bollinger_bands(sample_data, 5)
        
        # Upper > Middle > Lower
        valid_idx = ~np.isnan(upper)
        assert all(upper[valid_idx] > middle[valid_idx])
        assert all(middle[valid_idx] > lower[valid_idx])


# =============================================================================
# TEST: Pattern Recognition
# =============================================================================

class TestPatternRecognition:
    """Testes para reconhecimento de padrões"""
    
    def test_doji_detection(self):
        """Testa detecção de Doji"""
        from brain.src.analysis.technical.patterns import PatternRecognizer, PatternType
        
        recognizer = PatternRecognizer()
        
        # Doji: O e C próximos, com sombras
        opens = np.array([100.0])
        highs = np.array([102.0])
        lows = np.array([98.0])
        closes = np.array([100.05])  # Muito próximo do open
        
        patterns = recognizer._detect_candlestick_patterns(opens, highs, lows, closes)
        
        doji_patterns = [p for p in patterns if p.type == PatternType.DOJI]
        assert len(doji_patterns) > 0
    
    def test_engulfing_detection(self):
        """Testa detecção de Engulfing"""
        from brain.src.analysis.technical.patterns import PatternRecognizer, PatternType, PatternDirection
        
        recognizer = PatternRecognizer()
        
        # Bullish Engulfing
        opens = np.array([102.0, 99.0])   # Primeira bearish, segunda abre abaixo
        highs = np.array([103.0, 104.0])
        lows = np.array([100.0, 98.0])
        closes = np.array([100.5, 103.5])  # Segunda fecha acima da primeira
        
        patterns = recognizer._detect_candlestick_patterns(opens, highs, lows, closes)
        
        engulfing = [p for p in patterns if p.type == PatternType.ENGULFING]
        assert len(engulfing) > 0
        assert engulfing[0].direction == PatternDirection.BULLISH


# =============================================================================
# TEST: Risk Manager
# =============================================================================

class TestRiskManager:
    """Testes para gerenciamento de risco"""
    
    @pytest.fixture
    def risk_manager(self):
        """Fixture do RiskManager"""
        from brain.src.risk.risk_manager import RiskManager, RiskConfig
        
        config = RiskConfig(
            risk_per_trade=1.0,
            max_positions=3,
            max_daily_trades=10
        )
        return RiskManager(config)
    
    def test_position_sizing(self, risk_manager):
        """Testa cálculo de position sizing"""
        account = {"equity": 10000}
        
        volume = risk_manager.calculate_position_size(
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0950,  # 50 pips
            account_info=account,
            risk_percent=1.0
        )
        
        # Volume deve ser positivo e razoável
        assert volume > 0
        assert volume <= 10.0
    
    def test_validate_trade_max_positions(self, risk_manager):
        """Testa validação de máximo de posições"""
        from brain.src.core.types import Signal
        
        # Simular estado com posições no limite
        risk_manager._state.total_positions = 3
        
        signal = Signal(
            symbol="EURUSD",
            direction="buy",
            entry_price=1.1000,
            stop_loss=1.0950
        )
        
        can_trade, reason = risk_manager.validate_trade(signal, {"equity": 10000})
        
        assert not can_trade
        assert "posições" in reason.lower()
    
    def test_risk_level_calculation(self, risk_manager):
        """Testa cálculo de nível de risco"""
        from brain.src.risk.risk_manager import RiskLevel
        
        # Nível baixo com margem alta
        level = risk_manager._calculate_risk_level(margin_level=500)
        assert level == RiskLevel.LOW
        
        # Nível crítico com margem baixa
        level = risk_manager._calculate_risk_level(margin_level=100)
        assert level == RiskLevel.CRITICAL


# =============================================================================
# TEST: Database Manager
# =============================================================================

class TestDatabaseManager:
    """Testes para gerenciamento de banco de dados"""
    
    @pytest.fixture
    def db_manager(self, tmp_path):
        """Fixture com banco temporário"""
        from brain.src.database.db_manager import DatabaseManager
        
        db_path = tmp_path / "test.db"
        return DatabaseManager(str(db_path))
    
    def test_save_and_get_trade(self, db_manager):
        """Testa salvar e recuperar trade"""
        from brain.src.database.db_manager import TradeRecord
        
        trade = TradeRecord(
            ticket=12345,
            symbol="XAUUSD",
            direction="buy",
            volume=0.1,
            entry_price=2000.0,
            profit=50.0,
            strategy="scalping"
        )
        
        assert db_manager.save_trade(trade)
        
        retrieved = db_manager.get_trade(12345)
        assert retrieved is not None
        assert retrieved.symbol == "XAUUSD"
        assert retrieved.profit == 50.0
    
    def test_save_signal(self, db_manager):
        """Testa salvar sinal"""
        from brain.src.database.db_manager import SignalRecord
        
        signal = SignalRecord(
            id="sig_001",
            symbol="EURUSD",
            direction="sell",
            entry_price=1.1000,
            confidence=0.8,
            strategy="trend"
        )
        
        assert db_manager.save_signal(signal)
        
        signals = db_manager.get_signals(symbol="EURUSD")
        assert len(signals) > 0
        assert signals[0].direction == "sell"
    
    def test_performance_summary(self, db_manager):
        """Testa resumo de performance"""
        from brain.src.database.db_manager import TradeRecord
        
        # Criar trades de teste
        for i, profit in enumerate([50, -20, 30, -10, 40]):
            trade = TradeRecord(
                ticket=100 + i,
                symbol="XAUUSD",
                direction="buy",
                volume=0.1,
                entry_price=2000.0,
                exit_price=2000.0 + profit/10,
                profit=profit,
                status="closed",
                closed_at=datetime.now()
            )
            db_manager.save_trade(trade)
        
        summary = db_manager.get_performance_summary(days=30)
        
        assert summary["total_trades"] == 5
        assert summary["winning_trades"] == 3
        assert summary["total_profit"] == 90


# =============================================================================
# TEST: Health Checker
# =============================================================================

class TestHealthChecker:
    """Testes para monitoramento de saúde"""
    
    @pytest.fixture
    def health_checker(self):
        """Fixture do HealthChecker"""
        from brain.src.monitoring.health_checker import HealthChecker
        return HealthChecker(check_interval=1.0)
    
    def test_register_component(self, health_checker):
        """Testa registro de componente"""
        health_checker.register_component("test_component", lambda: True)
        
        assert "test_component" in health_checker._components
    
    @pytest.mark.asyncio
    async def test_health_check(self, health_checker):
        """Testa verificação de saúde"""
        from brain.src.monitoring.health_checker import HealthStatus
        
        health_checker.register_component("healthy", lambda: True)
        health_checker.register_component("unhealthy", lambda: False)
        
        await health_checker._check_all_components()
        
        assert health_checker._components["healthy"].status == HealthStatus.HEALTHY
        assert health_checker._components["unhealthy"].status == HealthStatus.CRITICAL
    
    def test_overall_status(self, health_checker):
        """Testa status geral"""
        from brain.src.monitoring.health_checker import HealthStatus
        
        health_checker.register_component("comp1")
        health_checker.register_component("comp2")
        
        # Ambos unknown
        health_checker._components["comp1"].status = HealthStatus.HEALTHY
        health_checker._components["comp2"].status = HealthStatus.CRITICAL
        
        # Critical deve prevalecer
        assert health_checker.get_overall_status() == HealthStatus.CRITICAL


# =============================================================================
# TEST: Strategy Base
# =============================================================================

class TestStrategyBase:
    """Testes para estratégias"""
    
    def test_strategy_factory(self):
        """Testa registro e criação de estratégias"""
        from brain.src.strategies.base_strategy import StrategyFactory, StrategyConfig
        
        # Scalping deve estar registrada
        config = StrategyConfig(
            name="test_scalping",
            symbol="XAUUSD",
            timeframe="M5"
        )
        
        strategy = StrategyFactory.create("scalping", config)
        assert strategy is not None
    
    def test_strategy_config(self):
        """Testa configuração de estratégia"""
        from brain.src.strategies.base_strategy import StrategyConfig
        
        config = StrategyConfig(
            name="test",
            symbol="EURUSD",
            timeframe="H1",
            risk_per_trade=1.5,
            max_trades_per_day=5
        )
        
        assert config.risk_per_trade == 1.5
        assert config.max_trades_per_day == 5


# =============================================================================
# FIXTURES GLOBAIS
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop para testes async"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
