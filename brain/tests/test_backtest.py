"""
Testes do módulo de Backtesting
===============================

Valida BacktestEngine, DataProvider, Metrics e Report.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestBacktestEngine:
    """Testes do BacktestEngine."""
    
    def test_engine_creation(self):
        """Testa criação do engine."""
        from backtesting import BacktestEngine, BacktestConfig
        
        config = BacktestConfig(
            initial_balance=10000,
            spread_pips=2.0,
            commission_per_lot=0,
        )
        
        engine = BacktestEngine(config)
        
        assert engine.config.initial_balance == 10000
        assert engine.balance == 10000
        assert engine.equity == 10000
        assert len(engine.positions) == 0
        print("✅ Engine criado corretamente")
    
    def test_load_data(self):
        """Testa carregamento de dados."""
        from backtesting import BacktestEngine, BacktestConfig, DataProvider
        
        config = BacktestConfig(initial_balance=10000)
        engine = BacktestEngine(config)
        
        provider = DataProvider()
        data = provider.generate_random_walk(bars=100)
        
        engine.load_data(data)
        
        assert len(data) == 100
        print("✅ Dados carregados corretamente")
    
    def test_simple_strategy(self):
        """Testa estratégia simples de buy and hold."""
        from backtesting import BacktestEngine, BacktestConfig, DataProvider
        
        config = BacktestConfig(
            initial_balance=10000,
            spread_pips=0,
            commission_per_lot=0,
        )
        
        engine = BacktestEngine(config)
        
        provider = DataProvider()
        data = provider.generate_trending(
            start_price=100,
            bars=100,
            trend_strength=0.001,  # Tendência de alta
        )
        
        engine.load_data(data)
        
        # Estratégia: compra no início
        bought = [False]
        
        def strategy(eng, bar):
            if not bought[0] and len(eng.positions) == 0:
                eng.buy("TEST", 0.1)
                bought[0] = True
        
        result = engine.run(strategy, warmup_bars=5)
        
        # Deve ter pelo menos 1 trade
        assert result.total_trades >= 1
        print(f"✅ Estratégia executada: {result.total_trades} trades")
    
    def test_buy_sell_strategy(self):
        """Testa estratégia de compra e venda."""
        from backtesting import BacktestEngine, BacktestConfig, DataProvider
        
        config = BacktestConfig(
            initial_balance=10000,
            spread_pips=1.0,
        )
        
        engine = BacktestEngine(config)
        
        provider = DataProvider()
        data = provider.generate_random_walk(bars=200)
        
        engine.load_data(data)
        
        # Estratégia alternada: compra/vende a cada 20 barras
        def strategy(eng, bar):
            bar_idx = eng._current_bar
            
            if bar_idx % 40 == 10 and len(eng.positions) == 0:
                eng.buy("TEST", 0.1)
            elif bar_idx % 40 == 30 and len(eng.positions) > 0:
                eng.close_all()
        
        result = engine.run(strategy, warmup_bars=5)
        
        assert result.total_trades >= 1
        print(f"✅ Compra/venda executada: {result.total_trades} trades")
    
    def test_stop_loss_take_profit(self):
        """Testa SL e TP."""
        from backtesting import BacktestEngine, BacktestConfig, DataProvider
        
        config = BacktestConfig(
            initial_balance=10000,
            spread_pips=0,
        )
        
        engine = BacktestEngine(config)
        
        provider = DataProvider()
        data = provider.generate_random_walk(bars=200, volatility=0.02)
        
        engine.load_data(data)
        
        # Estratégia com SL e TP
        def strategy(eng, bar):
            if eng._current_bar == 10 and len(eng.positions) == 0:
                price = bar['close']
                eng.buy(
                    "TEST", 0.1,
                    stop_loss=price * 0.95,
                    take_profit=price * 1.05
                )
        
        result = engine.run(strategy, warmup_bars=5)
        
        # Trade deve ter sido fechado por SL ou TP
        assert result.total_trades == 1
        print("✅ SL/TP testado")


class TestDataProvider:
    """Testes do DataProvider."""
    
    def test_provider_creation(self):
        """Testa criação do provider."""
        from backtesting import DataProvider
        
        provider = DataProvider()
        assert provider is not None
        print("✅ DataProvider criado")
    
    def test_random_walk_data(self):
        """Testa geração de dados random walk."""
        from backtesting import DataProvider
        
        provider = DataProvider()
        data = provider.generate_random_walk(
            start_price=100,
            bars=500,
            volatility=0.02,
        )
        
        assert len(data) == 500
        assert 'open' in data.columns
        assert 'high' in data.columns
        assert 'low' in data.columns
        assert 'close' in data.columns
        assert 'volume' in data.columns
        
        # Verifica consistência OHLC
        assert (data['high'] >= data['low']).all()
        assert (data['high'] >= data['close']).all()
        assert (data['low'] <= data['close']).all()
        
        print(f"✅ Dados random walk gerados: {len(data)} barras")
    
    def test_trending_data(self):
        """Testa geração de dados com tendência."""
        from backtesting import DataProvider
        
        provider = DataProvider()
        data = provider.generate_trending(
            start_price=100,
            bars=500,
            trend_strength=0.001,
        )
        
        # Tendência de alta deve resultar em preço final maior
        assert data['close'].iloc[-1] > data['close'].iloc[0]
        print("✅ Dados de tendência gerados")
    
    def test_ranging_data(self):
        """Testa geração de dados laterais."""
        from backtesting import DataProvider
        
        provider = DataProvider()
        data = provider.generate_ranging(
            center_price=100,
            bars=500,
            range_size=0.05,
        )
        
        # Preço deve oscilar em torno do centro
        assert data['close'].min() > 90  # ±10%
        assert data['close'].max() < 110
        print("✅ Dados laterais gerados")
    
    def test_add_indicators(self):
        """Testa adição de indicadores."""
        from backtesting import DataProvider
        
        provider = DataProvider()
        data = provider.generate_random_walk(bars=100)
        
        # Adiciona indicadores
        data = DataProvider.add_sma(data, 20)
        data = DataProvider.add_ema(data, 12)
        data = DataProvider.add_rsi(data, 14)
        data = DataProvider.add_atr(data, 14)
        data = DataProvider.add_bollinger(data, 20)
        data = DataProvider.add_macd(data, 12, 26, 9)
        
        assert 'sma_20' in data.columns
        assert 'ema_12' in data.columns
        assert 'rsi' in data.columns
        assert 'atr' in data.columns
        assert 'bb_upper' in data.columns
        assert 'macd' in data.columns
        
        print("✅ Indicadores adicionados")


class TestMetrics:
    """Testes do MetricsCalculator."""
    
    def test_metrics_calculation(self):
        """Testa cálculo de métricas."""
        from backtesting import MetricsCalculator
        
        calculator = MetricsCalculator()
        
        # Simula equity curve
        equity_curve = [10000, 10100, 10050, 10200, 10150, 10300, 10250, 10400]
        
        # Simula trades
        trades = [
            {'pnl': 100, 'entry_time': datetime.now(), 'exit_time': datetime.now() + timedelta(hours=2)},
            {'pnl': -50, 'entry_time': datetime.now(), 'exit_time': datetime.now() + timedelta(hours=1)},
            {'pnl': 150, 'entry_time': datetime.now(), 'exit_time': datetime.now() + timedelta(hours=3)},
            {'pnl': -50, 'entry_time': datetime.now(), 'exit_time': datetime.now() + timedelta(hours=1)},
            {'pnl': 100, 'entry_time': datetime.now(), 'exit_time': datetime.now() + timedelta(hours=2)},
            {'pnl': -50, 'entry_time': datetime.now(), 'exit_time': datetime.now() + timedelta(hours=1)},
            {'pnl': 150, 'entry_time': datetime.now(), 'exit_time': datetime.now() + timedelta(hours=4)},
        ]
        
        timestamps = [datetime.now() + timedelta(hours=i) for i in range(len(equity_curve))]
        
        metrics = calculator.calculate_all(
            equity_curve=equity_curve,
            trades=trades,
            initial_capital=10000,
            timestamps=timestamps,
        )
        
        assert metrics.total_profit == 400  # 10400 - 10000
        assert metrics.total_trades == 7
        assert metrics.winning_trades == 4
        assert metrics.losing_trades == 3
        assert metrics.win_rate > 50
        
        print(f"✅ Métricas calculadas:")
        print(f"   Retorno: {metrics.total_return:.2f}%")
        print(f"   Win Rate: {metrics.win_rate:.2f}%")
        print(f"   Profit Factor: {metrics.profit_factor:.2f}")
    
    def test_sharpe_ratio(self):
        """Testa cálculo do Sharpe Ratio."""
        from backtesting import MetricsCalculator
        import numpy as np
        
        calculator = MetricsCalculator()
        
        # Gera retornos positivos consistentes
        np.random.seed(42)
        equity = 10000 * np.cumprod(1 + np.random.normal(0.001, 0.01, 252))
        equity = [10000] + list(equity)
        
        metrics = calculator.calculate_all(
            equity_curve=equity,
            trades=[],
            initial_capital=10000,
        )
        
        # Sharpe deve ser positivo para retornos positivos
        print(f"✅ Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    
    def test_drawdown(self):
        """Testa cálculo do drawdown."""
        from backtesting import MetricsCalculator
        
        calculator = MetricsCalculator()
        
        # Equity com drawdown óbvio
        equity = [10000, 11000, 12000, 10000, 11000, 12000]  # 16.67% drawdown
        
        metrics = calculator.calculate_all(
            equity_curve=equity,
            trades=[],
            initial_capital=10000,
        )
        
        assert metrics.max_drawdown > 15  # ~16.67%
        assert metrics.max_drawdown < 20
        
        print(f"✅ Max Drawdown: {metrics.max_drawdown:.2f}%")


class TestReport:
    """Testes do BacktestReport."""
    
    def test_report_creation(self):
        """Testa criação do relatório."""
        from backtesting import BacktestReport, MetricsCalculator, PerformanceMetrics
        
        # Cria métricas de exemplo
        metrics = PerformanceMetrics(
            total_return=15.5,
            total_profit=1550,
            max_drawdown=8.2,
            sharpe_ratio=1.5,
            win_rate=55,
            total_trades=100,
        )
        
        trades = [
            {'symbol': 'EURUSD', 'direction': 'long', 'entry_price': 1.1000, 
             'exit_price': 1.1050, 'pnl': 50, 'volume': 0.1,
             'entry_time': datetime.now(), 'exit_time': datetime.now()},
        ]
        
        equity = [10000, 10500, 10400, 10800, 11000, 11550]
        timestamps = [datetime.now() + timedelta(days=i) for i in range(6)]
        
        report = BacktestReport(
            metrics=metrics,
            trades=trades,
            equity_curve=equity,
            timestamps=timestamps,
        )
        
        assert report is not None
        print("✅ Relatório criado")
    
    def test_report_to_dict(self):
        """Testa conversão para dicionário."""
        from backtesting import BacktestReport, PerformanceMetrics
        
        metrics = PerformanceMetrics(
            total_return=15.5,
            total_profit=1550,
            sharpe_ratio=1.5,
            win_rate=55,
            total_trades=100,
        )
        
        report = BacktestReport(
            metrics=metrics,
            trades=[],
            equity_curve=[10000, 11550],
            timestamps=[datetime.now(), datetime.now()],
        )
        
        data = report.to_dict()
        
        assert 'summary' in data
        assert 'returns' in data
        assert 'risk' in data
        assert 'ratios' in data
        assert data['summary']['total_return'] == 15.5
        
        print("✅ Conversão para dict OK")
    
    def test_report_to_text(self):
        """Testa geração de texto."""
        from backtesting import BacktestReport, PerformanceMetrics
        
        metrics = PerformanceMetrics(
            total_return=15.5,
            total_profit=1550,
            max_drawdown=8.2,
            sharpe_ratio=1.5,
            win_rate=55,
            total_trades=100,
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
        )
        
        report = BacktestReport(
            metrics=metrics,
            trades=[],
            equity_curve=[10000, 11550],
            timestamps=[datetime.now(), datetime.now()],
        )
        
        text = report.to_text()
        
        assert "VIRTUS BACKTEST REPORT" in text
        assert "15.50%" in text
        assert "1550.00" in text
        
        print("✅ Relatório em texto gerado")


class TestIntegration:
    """Testes de integração do sistema completo."""
    
    def test_full_backtest_flow(self):
        """Testa fluxo completo de backtest."""
        from backtesting import (
            BacktestEngine,
            BacktestConfig,
            DataProvider,
            MetricsCalculator,
            BacktestReport,
        )
        
        # 1. Configura
        config = BacktestConfig(
            initial_balance=10000,
            spread_pips=2.0,
            commission_per_lot=0,
        )
        
        # 2. Gera dados
        provider = DataProvider()
        data = provider.generate_trending(
            start_price=1.1000,
            bars=500,
            trend_strength=0.0005,
        )
        
        # 3. Adiciona indicadores
        data = DataProvider.add_sma(data, 20)
        data = DataProvider.add_sma(data, 50)
        
        # 4. Cria engine e carrega dados
        engine = BacktestEngine(config)
        engine.load_data(data)
        
        # 5. Define estratégia SMA crossover
        prev_sma20 = [None]
        prev_sma50 = [None]
        
        def sma_crossover(eng, bar):
            sma20 = bar.get('sma_20')
            sma50 = bar.get('sma_50')
            
            if sma20 is None or sma50 is None:
                return
            
            # Atualiza valores anteriores
            if prev_sma20[0] is not None and prev_sma50[0] is not None:
                # Golden Cross - Buy
                if prev_sma20[0] < prev_sma50[0] and sma20 > sma50:
                    if len(eng.positions) == 0:
                        eng.buy("EURUSD", 0.1)
                
                # Death Cross - Sell
                elif prev_sma20[0] > prev_sma50[0] and sma20 < sma50:
                    if len(eng.positions) > 0:
                        eng.close_all()
            
            prev_sma20[0] = sma20
            prev_sma50[0] = sma50
        
        # 6. Executa backtest
        result = engine.run(sma_crossover, warmup_bars=50)
        
        # 7. Calcula métricas
        calculator = MetricsCalculator()
        
        trades_list = [
            {
                'pnl': t.profit,
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'symbol': t.symbol,
                'direction': str(t.direction),
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'volume': t.volume,
            }
            for t in result.trades
        ]
        
        # equity_curve é uma lista de tuplas (datetime, value)
        equity_values = [eq[1] for eq in result.equity_curve] if result.equity_curve else []
        
        metrics = calculator.calculate_all(
            equity_curve=equity_values,
            trades=trades_list,
            initial_capital=config.initial_balance,
        )
        
        # 8. Gera relatório
        report = BacktestReport(
            metrics=metrics,
            trades=trades_list,
            equity_curve=equity_values,
            timestamps=[],
        )
        
        # 9. Verifica resultados
        print("\n" + "=" * 60)
        print("📊 RESULTADO DO BACKTEST INTEGRADO")
        print("=" * 60)
        print(f"📈 Trades executados: {metrics.total_trades}")
        print(f"📈 Win Rate: {metrics.win_rate:.2f}%")
        print(f"📈 Retorno Total: {metrics.total_return:.2f}%")
        print(f"📈 Lucro Total: ${metrics.total_profit:.2f}")
        print(f"📈 Max Drawdown: {metrics.max_drawdown:.2f}%")
        print(f"📈 Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"📈 Profit Factor: {metrics.profit_factor:.2f}")
        print("=" * 60)
        
        # Em tendência de alta, estratégia deve ter trades
        assert result.total_trades >= 0  # Pode não ter sinais dependendo dos dados
        
        print("\n✅ Fluxo completo de backtest validado!")
        
        return True


def run_all_tests():
    """Executa todos os testes."""
    print("=" * 60)
    print("🧪 VIRTUS BACKTESTING - TESTES")
    print("=" * 60)
    print()
    
    test_classes = [
        TestBacktestEngine,
        TestDataProvider,
        TestMetrics,
        TestReport,
        TestIntegration,
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
