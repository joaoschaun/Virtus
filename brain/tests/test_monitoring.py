"""
Testes do módulo de Monitoring & Reporting
==========================================

Valida MetricsCollector, Reports, Attribution e Alerts.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def generate_mock_trades(count: int = 50) -> list:
    """Gera trades fictícios para teste."""
    trades = []
    strategies = ['ScalpingStrategy', 'TrendStrategy', 'ReversalStrategy']
    setups = ['SPREAD_COMPRESSION', 'BOS_CONTINUATION', 'CHOCH_REVERSAL', 'FVG_FILL']
    symbols = ['EURUSD', 'GBPUSD', 'XAUUSD']
    
    base_time = datetime.now() - timedelta(days=7)
    
    for i in range(count):
        pnl = random.uniform(-100, 150) if random.random() > 0.4 else random.uniform(-50, -10)
        
        trade = {
            'id': i + 1,
            'symbol': random.choice(symbols),
            'direction': random.choice(['buy', 'sell']),
            'strategy': random.choice(strategies),
            'setup': random.choice(setups),
            'entry_price': 1.1000 + random.uniform(-0.01, 0.01),
            'exit_price': 1.1000 + random.uniform(-0.01, 0.01),
            'volume': random.uniform(0.1, 1.0),
            'pnl': pnl,
            'close_time': base_time + timedelta(hours=i * 3 + random.randint(0, 2)),
            'bot_id': f'bot_{random.randint(1, 3)}',
            'duration_seconds': random.randint(60, 7200),
        }
        trades.append(trade)
    
    return trades


class TestMetricsCollector:
    """Testes do MetricsCollector."""
    
    def test_creation(self):
        """Testa criação do collector."""
        from monitoring import MetricsCollector
        
        collector = MetricsCollector()
        assert collector is not None
        print("✅ MetricsCollector criado")
    
    def test_record_metric(self):
        """Testa registro de métrica."""
        from monitoring import MetricsCollector
        
        collector = MetricsCollector()
        collector.record("test_metric", 42.5)
        
        value = collector.get_latest("test_metric")
        assert value == 42.5
        print("✅ Métrica registrada e recuperada")
    
    def test_system_metrics(self):
        """Testa coleta de métricas do sistema."""
        from monitoring import MetricsCollector
        
        collector = MetricsCollector()
        collector.collect_system_metrics()
        
        cpu = collector.get_latest("system_cpu_percent")
        mem = collector.get_latest("system_memory_percent")
        
        assert cpu is not None
        assert mem is not None
        assert 0 <= cpu <= 100
        assert 0 <= mem <= 100
        print(f"✅ Métricas do sistema: CPU={cpu:.1f}%, MEM={mem:.1f}%")
    
    def test_record_trade(self):
        """Testa registro de trade."""
        from monitoring import MetricsCollector
        
        collector = MetricsCollector()
        collector.record_trade(
            bot_id="bot_test",
            pnl=150.0,
            volume=1.0,
            strategy="ScalpingStrategy",
            setup="SPREAD_COMPRESSION"
        )
        
        metrics = collector.get_trading_metrics("bot_test")
        assert metrics.total_trades == 1
        assert metrics.winning_trades == 1
        assert metrics.total_pnl == 150.0
        print("✅ Trade registrado corretamente")
    
    def test_trading_metrics(self):
        """Testa métricas de trading consolidadas."""
        from monitoring import MetricsCollector
        
        collector = MetricsCollector()
        
        # Registrar alguns trades
        collector.record_trade("bot_1", 100, 1.0)
        collector.record_trade("bot_1", -50, 0.5)
        collector.record_trade("bot_1", 75, 0.8)
        
        metrics = collector.get_trading_metrics("bot_1")
        global_metrics = collector.get_trading_metrics()
        
        assert metrics.total_trades == 3
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 1
        assert metrics.total_pnl == 125.0  # 100 - 50 + 75
        assert metrics.win_rate > 60  # 2/3 = 66.67%
        
        print(f"✅ Trading metrics: {metrics.total_trades} trades, WR={metrics.win_rate:.1f}%")
    
    def test_balance_update(self):
        """Testa atualização de saldo e drawdown."""
        from monitoring import MetricsCollector
        
        collector = MetricsCollector()
        
        collector.update_balance(10000, 10000)
        collector.update_balance(10500, 10500)  # Novo pico
        collector.update_balance(9800, 9800)    # Drawdown
        
        dd = collector.get_latest("current_drawdown")
        assert dd is not None
        assert dd > 0  # Deve ter drawdown
        
        metrics = collector.get_trading_metrics()
        assert metrics.peak_balance == 10500
        print(f"✅ Drawdown calculado: {dd:.2f}%")


class TestDailyReport:
    """Testes do DailyReport."""
    
    def test_creation(self):
        """Testa criação do report."""
        from reporting import DailyReport
        
        report = DailyReport()
        assert report is not None
        print("✅ DailyReport criado")
    
    def test_build_from_trades(self):
        """Testa geração de relatório."""
        from reporting import DailyReport
        from datetime import date
        
        report = DailyReport()
        trades = generate_mock_trades(20)
        
        # Ajustar trades para hoje
        today = date.today()
        for trade in trades[:10]:
            trade['close_time'] = datetime.combine(today, datetime.min.time()) + timedelta(hours=random.randint(1, 23))
        
        text = report.build_from_trades(trades, today)
        
        assert "RESUMO GERAL" in text
        assert "P&L" in text
        print("✅ Relatório diário gerado")
    
    def test_formats(self):
        """Testa diferentes formatos."""
        from reporting import DailyReport, ReportFormat
        from datetime import date
        
        report = DailyReport()
        trades = generate_mock_trades(10)
        
        today = date.today()
        for trade in trades:
            trade['close_time'] = datetime.combine(today, datetime.min.time()) + timedelta(hours=random.randint(1, 23))
        
        # Text
        text = report.build_from_trades(trades, today, ReportFormat.TEXT)
        assert len(text) > 0
        
        # JSON
        json_out = report.build_from_trades(trades, today, ReportFormat.JSON)
        assert "{" in json_out
        
        # HTML
        html = report.build_from_trades(trades, today, ReportFormat.HTML)
        assert "<html>" in html
        
        # Markdown
        md = report.build_from_trades(trades, today, ReportFormat.MARKDOWN)
        assert "# " in md or "## " in md
        
        print("✅ Todos os formatos gerados: TEXT, JSON, HTML, MD")


class TestWeeklyReport:
    """Testes do WeeklyReport."""
    
    def test_creation(self):
        """Testa criação do report."""
        from reporting import WeeklyReport
        
        report = WeeklyReport()
        assert report is not None
        print("✅ WeeklyReport criado")
    
    def test_weekday_analysis(self):
        """Testa análise por dia da semana."""
        from reporting import WeeklyReport
        from datetime import date
        
        report = WeeklyReport()
        trades = generate_mock_trades(30)
        
        text = report.build_from_trades(trades)
        
        assert "SEMANAL" in text or "semanal" in text.lower()
        print("✅ Relatório semanal com análise por dia")
    
    def test_summary(self):
        """Testa geração de resumo."""
        from reporting import WeeklyReport
        
        report = WeeklyReport()
        trades = generate_mock_trades(20)
        
        summary = report.generate_summary(trades)
        
        assert "Semanal" in summary or "semanal" in summary.lower()
        assert "$" in summary
        print("✅ Resumo semanal gerado")


class TestPerformanceAttribution:
    """Testes do PerformanceAttribution."""
    
    def test_creation(self):
        """Testa criação."""
        from reporting import PerformanceAttribution
        
        attr = PerformanceAttribution()
        assert attr is not None
        print("✅ PerformanceAttribution criado")
    
    def test_analyze_strategy(self):
        """Testa análise por estratégia."""
        from reporting import PerformanceAttribution, AttributionDimension
        
        attr = PerformanceAttribution()
        trades = generate_mock_trades(50)
        
        summary = attr.analyze(trades, AttributionDimension.STRATEGY)
        
        assert summary.total_trades == 50
        assert len(summary.results) > 0
        assert summary.best_performer is not None
        
        print(f"✅ Atribuição por estratégia: {len(summary.results)} categorias")
    
    def test_analyze_setup(self):
        """Testa análise por setup."""
        from reporting import PerformanceAttribution, AttributionDimension
        
        attr = PerformanceAttribution()
        trades = generate_mock_trades(50)
        
        summary = attr.analyze(trades, AttributionDimension.SETUP)
        
        assert len(summary.results) > 0
        print(f"✅ Atribuição por setup: melhor = {summary.best_performer.category if summary.best_performer else 'N/A'}")
    
    def test_analyze_session(self):
        """Testa análise por sessão."""
        from reporting import PerformanceAttribution, AttributionDimension
        
        attr = PerformanceAttribution()
        trades = generate_mock_trades(50)
        
        summary = attr.analyze(trades, AttributionDimension.SESSION)
        
        assert len(summary.results) > 0
        print(f"✅ Atribuição por sessão: {[r.category for r in summary.results]}")
    
    def test_generate_report(self):
        """Testa geração de relatório completo."""
        from reporting import PerformanceAttribution
        
        attr = PerformanceAttribution()
        trades = generate_mock_trades(50)
        
        report = attr.generate_report(trades)
        
        assert "ATRIBUIÇÃO" in report
        assert "ESTRATÉGIA" in report or "POR STRATEGY" in report
        print("✅ Relatório de atribuição gerado")


class TestAnalyticsDashboard:
    """Testes do AnalyticsDashboard."""
    
    def test_creation(self):
        """Testa criação."""
        from reporting import AnalyticsDashboard
        
        dashboard = AnalyticsDashboard()
        assert dashboard is not None
        print("✅ AnalyticsDashboard criado")
    
    def test_overview_cards(self):
        """Testa geração de cards."""
        from reporting import AnalyticsDashboard
        
        dashboard = AnalyticsDashboard()
        trades = generate_mock_trades(30)
        
        cards = dashboard.get_overview_cards(trades, balance=10000, equity=10500)
        
        assert len(cards) >= 4
        assert any("P&L" in c.title for c in cards)
        assert any("Trade" in c.title for c in cards)
        print(f"✅ {len(cards)} cards gerados")
    
    def test_charts(self):
        """Testa geração de dados de gráficos."""
        from reporting import AnalyticsDashboard
        
        dashboard = AnalyticsDashboard()
        trades = generate_mock_trades(30)
        
        # PnL Chart
        pnl_chart = dashboard.get_pnl_chart(trades)
        assert len(pnl_chart.labels) > 0
        
        # Equity Curve
        equity_chart = dashboard.get_equity_curve(trades)
        assert len(equity_chart.labels) > 0
        
        # Win/Loss
        wl_chart = dashboard.get_win_loss_distribution(trades)
        assert wl_chart.chart_type == "doughnut"
        
        print("✅ Dados de gráficos gerados")
    
    def test_full_dashboard(self):
        """Testa geração completa do dashboard."""
        from reporting import AnalyticsDashboard
        
        dashboard = AnalyticsDashboard()
        trades = generate_mock_trades(50)
        
        data = dashboard.get_full_dashboard_data(trades)
        
        assert 'cards' in data
        assert 'charts' in data
        assert 'trades' in data
        assert len(data['trades']) <= 50
        
        print("✅ Dashboard completo gerado")


class TestAlertManager:
    """Testes do AlertManager."""
    
    def test_creation(self):
        """Testa criação."""
        from monitoring import AlertManager
        
        manager = AlertManager()
        assert manager is not None
        print("✅ AlertManager criado")
    
    def test_default_rules(self):
        """Testa regras padrão."""
        from monitoring import AlertManager
        
        manager = AlertManager()
        rules = manager.get_rules()
        
        assert len(rules) > 0
        assert "drawdown_warning" in rules
        assert "mt5_disconnect" in rules
        print(f"✅ {len(rules)} regras padrão configuradas")
    
    def test_evaluate_drawdown(self):
        """Testa avaliação de drawdown."""
        from monitoring import AlertManager, AlertType
        
        manager = AlertManager()
        
        # Contexto com drawdown alto
        context = {
            'drawdown': 12.0,
            'mt5_connected': True,
            'cpu_percent': 50,
            'memory_percent': 60,
        }
        
        alerts = manager.evaluate(context)
        
        # Deve ter alerta de drawdown
        dd_alerts = [a for a in alerts if a.type == AlertType.DRAWDOWN]
        assert len(dd_alerts) > 0
        print(f"✅ Alerta de drawdown disparado: {dd_alerts[0].message}")
    
    def test_manual_alert(self):
        """Testa alerta manual."""
        from monitoring import AlertManager, AlertType, AlertPriority
        
        manager = AlertManager()
        
        alert = manager.trigger_alert(
            AlertType.CUSTOM,
            "Teste de alerta manual",
            AlertPriority.HIGH
        )
        
        assert alert is not None
        assert len(manager.get_active_alerts()) > 0
        print("✅ Alerta manual criado")
    
    def test_acknowledge_resolve(self):
        """Testa acknowledge e resolve."""
        from monitoring import AlertManager, AlertType, AlertPriority
        
        manager = AlertManager()
        
        alert = manager.trigger_alert(AlertType.CUSTOM, "Teste", AlertPriority.MEDIUM)
        
        # Acknowledge
        manager.acknowledge(0)
        assert manager.get_active_alerts()[0].acknowledged
        
        # Resolve
        manager.resolve(0)
        assert manager.get_active_alerts()[0].resolved
        
        print("✅ Acknowledge e Resolve funcionando")
    
    def test_notification_callback(self):
        """Testa callback de notificação."""
        from monitoring import AlertManager, AlertType, AlertPriority
        
        manager = AlertManager()
        
        notifications_received = []
        
        def on_alert(alert):
            notifications_received.append(alert)
        
        manager.add_notification_channel("test", on_alert)
        manager.trigger_alert(AlertType.CUSTOM, "Teste callback", AlertPriority.LOW)
        
        assert len(notifications_received) == 1
        print("✅ Callback de notificação funcionando")
    
    def test_critical_check(self):
        """Testa verificação de alertas críticos."""
        from monitoring import AlertManager
        
        manager = AlertManager()
        
        # Contexto com MT5 desconectado (crítico)
        context = {
            'mt5_connected': False,
            'drawdown': 5,
            'cpu_percent': 50,
            'memory_percent': 60,
        }
        
        manager.evaluate(context)
        
        assert manager.has_critical()
        print("✅ Detecção de alerta crítico funcionando")


class TestPrometheusExporter:
    """Testes do PrometheusExporter."""
    
    def test_export(self):
        """Testa exportação Prometheus."""
        from monitoring import MetricsCollector, PrometheusExporter
        
        collector = MetricsCollector()
        collector.collect_system_metrics()
        collector.record_trade("bot_1", 100, 1.0)
        
        exporter = PrometheusExporter(collector)
        output = exporter.export()
        
        assert "virtus_cpu_percent" in output
        assert "virtus_trades_total" in output
        print("✅ Export Prometheus gerado")


class TestHealthAggregator:
    """Testes do HealthAggregator."""
    
    def test_check_health(self):
        """Testa verificação de saúde."""
        from monitoring import MetricsCollector, HealthAggregator
        
        collector = MetricsCollector()
        collector.collect_system_metrics()
        collector.update_mt5_status(True, 50)
        
        health = HealthAggregator(collector)
        status = health.check_health()
        
        assert 'status' in status
        assert 'components' in status
        assert status['status'] in ['healthy', 'warning', 'critical']
        print(f"✅ Health check: {status['status']}")


# ==================== RUNNER ====================

def run_tests():
    """Executa todos os testes."""
    print("=" * 60)
    print("🧪 VIRTUS MONITORING & REPORTING - TESTES")
    print("=" * 60)
    print()
    
    test_classes = [
        TestMetricsCollector,
        TestDailyReport,
        TestWeeklyReport,
        TestPerformanceAttribution,
        TestAnalyticsDashboard,
        TestAlertManager,
        TestPrometheusExporter,
        TestHealthAggregator,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)
        
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total_tests += 1
                try:
                    getattr(instance, method_name)()
                    passed_tests += 1
                except Exception as e:
                    failed_tests.append(f"{test_class.__name__}.{method_name}: {e}")
                    print(f"❌ {method_name}: {e}")
    
    print()
    print("=" * 60)
    print(f"📊 RESULTADO: {passed_tests}/{total_tests} testes passaram")
    print("=" * 60)
    
    if failed_tests:
        print()
        print("❌ Testes que falharam:")
        for fail in failed_tests:
            print(f"   - {fail}")
    else:
        print()
        print("✅ TODOS OS TESTES PASSARAM!")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
