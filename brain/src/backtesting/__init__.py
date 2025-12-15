"""
VIRTUS Backtesting Module
=========================

Sistema completo de backtesting para estratégias de trading.

Componentes:
- BacktestEngine: Motor principal de simulação
- DataProvider: Provedor de dados históricos (MT5, CSV)
- MetricsCalculator: Cálculo de métricas de performance
- BacktestReport: Geração de relatórios

Exemplo de uso:
    from src.backtesting import (
        BacktestEngine,
        BacktestConfig,
        DataProvider,
        MetricsCalculator,
        BacktestReport,
    )
    
    # Configura backtest
    config = BacktestConfig(
        initial_capital=10000,
        spread=0.0002,
        commission=0,
    )
    
    # Carrega dados
    provider = DataProvider()
    data = provider.get_mt5_data("EURUSD", "H1", start, end)
    
    # Executa backtest
    engine = BacktestEngine(config)
    
    for timestamp, bar in data.iterrows():
        # Lógica da estratégia
        if should_buy(bar):
            engine.buy(timestamp, bar['close'], 0.1)
        # ...
    
    # Obtém resultados
    result = engine.get_results()
    
    # Gera relatório
    calculator = MetricsCalculator()
    metrics = calculator.calculate_all(
        result.equity_curve,
        result.trades,
        config.initial_capital,
    )
    
    report = BacktestReport(metrics, result.trades, result.equity_curve, ...)
    report.print_summary()
"""

try:
    from .engine import (
        BacktestEngine,
        BacktestConfig,
        BacktestResult,
        Order,
        Position,
        Trade,
        OrderType,
        OrderStatus,
    )

    from .data_provider import (
        DataProvider,
        Timeframe,
    )

    from .metrics import (
        MetricsCalculator,
        PerformanceMetrics,
        MonthlyMetrics,
        RiskMetrics,
    )

    from .report import (
        BacktestReport,
    )
except ImportError:
    from backtesting.engine import (
        BacktestEngine,
        BacktestConfig,
        BacktestResult,
        Order,
        Position,
        Trade,
        OrderType,
        OrderStatus,
    )

    from backtesting.data_provider import (
        DataProvider,
        Timeframe,
    )

    from backtesting.metrics import (
        MetricsCalculator,
        PerformanceMetrics,
        MonthlyMetrics,
        RiskMetrics,
    )

    from backtesting.report import (
        BacktestReport,
    )


__all__ = [
    # Engine
    'BacktestEngine',
    'BacktestConfig',
    'BacktestResult',
    'Order',
    'Position',
    'Trade',
    'OrderType',
    'OrderStatus',
    # Data
    'DataProvider',
    'Timeframe',
    # Metrics
    'MetricsCalculator',
    'PerformanceMetrics',
    'MonthlyMetrics',
    'RiskMetrics',
    # Report
    'BacktestReport',
]
