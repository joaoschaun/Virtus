"""
VIRTUS Integration Tests
========================

Testes de integração para todos os módulos criados.
Valida que os arquivos existem e têm estrutura correta.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import ast
import sys
import os

# Path do projeto
PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def file_exists(relative_path: str) -> bool:
    """Verifica se arquivo existe."""
    return (SRC_PATH / relative_path).exists()


def get_file_content(relative_path: str) -> str:
    """Lê conteúdo do arquivo."""
    file_path = SRC_PATH / relative_path
    if file_path.exists():
        return file_path.read_text(encoding='utf-8')
    return ""


def file_has_class(relative_path: str, class_name: str) -> bool:
    """Verifica se arquivo define uma classe."""
    content = get_file_content(relative_path)
    return f"class {class_name}" in content


def file_has_function(relative_path: str, function_name: str) -> bool:
    """Verifica se arquivo define uma função."""
    content = get_file_content(relative_path)
    return f"def {function_name}" in content or f"async def {function_name}" in content


def file_has_import(relative_path: str, import_name: str) -> bool:
    """Verifica se arquivo importa algo."""
    content = get_file_content(relative_path)
    return import_name in content


def count_lines(relative_path: str) -> int:
    """Conta linhas não vazias do arquivo."""
    content = get_file_content(relative_path)
    return len([l for l in content.split('\n') if l.strip()])


# =============================================================================
# TESTS: FILE EXISTENCE
# =============================================================================

class TestFileExistence:
    """Verifica que todos os arquivos necessários existem."""
    
    def test_position_manager_exists(self):
        assert file_exists("positions/position_manager.py")
    
    def test_position_monitor_exists(self):
        assert file_exists("positions/position_monitor.py")
    
    def test_trailing_stop_exists(self):
        assert file_exists("positions/exits/trailing_stop.py")
    
    def test_strategy_factory_exists(self):
        assert file_exists("strategies/strategy_factory.py")
    
    def test_news_analyzer_exists(self):
        assert file_exists("brain/analyzers/news_analyzer.py")
    
    def test_sentiment_analyzer_exists(self):
        assert file_exists("brain/analyzers/sentiment_analyzer.py")
    
    def test_macro_analyzer_exists(self):
        assert file_exists("brain/analyzers/macro_analyzer.py")
    
    def test_correlation_analyzer_exists(self):
        assert file_exists("brain/analyzers/correlation_analyzer.py")
    
    def test_global_risk_exists(self):
        assert file_exists("risk/global_risk.py")
    
    def test_correlation_risk_exists(self):
        assert file_exists("risk/correlation_risk.py")
    
    def test_exposure_manager_exists(self):
        assert file_exists("risk/exposure_manager.py")
    
    def test_global_commands_exists(self):
        assert file_exists("telegram/commands/global_commands.py")
    
    def test_bot_commands_exists(self):
        assert file_exists("telegram/commands/bot_commands.py")
    
    def test_brain_commands_exists(self):
        assert file_exists("telegram/commands/brain_commands.py")
    
    def test_advisor_commands_exists(self):
        assert file_exists("telegram/commands/advisor_commands.py")
    
    def test_model_registry_exists(self):
        assert file_exists("ml/training/model_registry.py")
    
    def test_trainer_service_exists(self):
        assert file_exists("ml/training/trainer_service.py")


# =============================================================================
# TESTS: FILE SIZE (não são stubs)
# =============================================================================

class TestFileSize:
    """Verifica que arquivos não são stubs (têm conteúdo substancial)."""
    
    MIN_LINES = 200  # Arquivos devem ter pelo menos 200 linhas
    
    def test_position_manager_not_stub(self):
        lines = count_lines("positions/position_manager.py")
        assert lines >= self.MIN_LINES, f"position_manager.py tem apenas {lines} linhas"
    
    def test_position_monitor_not_stub(self):
        lines = count_lines("positions/position_monitor.py")
        assert lines >= self.MIN_LINES, f"position_monitor.py tem apenas {lines} linhas"
    
    def test_trailing_stop_not_stub(self):
        lines = count_lines("positions/exits/trailing_stop.py")
        assert lines >= self.MIN_LINES, f"trailing_stop.py tem apenas {lines} linhas"
    
    def test_strategy_factory_not_stub(self):
        lines = count_lines("strategies/strategy_factory.py")
        assert lines >= self.MIN_LINES, f"strategy_factory.py tem apenas {lines} linhas"
    
    def test_news_analyzer_not_stub(self):
        lines = count_lines("brain/analyzers/news_analyzer.py")
        assert lines >= self.MIN_LINES, f"news_analyzer.py tem apenas {lines} linhas"
    
    def test_sentiment_analyzer_not_stub(self):
        lines = count_lines("brain/analyzers/sentiment_analyzer.py")
        assert lines >= self.MIN_LINES, f"sentiment_analyzer.py tem apenas {lines} linhas"
    
    def test_macro_analyzer_not_stub(self):
        lines = count_lines("brain/analyzers/macro_analyzer.py")
        assert lines >= self.MIN_LINES, f"macro_analyzer.py tem apenas {lines} linhas"
    
    def test_correlation_analyzer_not_stub(self):
        lines = count_lines("brain/analyzers/correlation_analyzer.py")
        assert lines >= self.MIN_LINES, f"correlation_analyzer.py tem apenas {lines} linhas"
    
    def test_global_risk_not_stub(self):
        lines = count_lines("risk/global_risk.py")
        assert lines >= self.MIN_LINES, f"global_risk.py tem apenas {lines} linhas"
    
    def test_correlation_risk_not_stub(self):
        lines = count_lines("risk/correlation_risk.py")
        assert lines >= self.MIN_LINES, f"correlation_risk.py tem apenas {lines} linhas"
    
    def test_exposure_manager_not_stub(self):
        lines = count_lines("risk/exposure_manager.py")
        assert lines >= self.MIN_LINES, f"exposure_manager.py tem apenas {lines} linhas"
    
    def test_global_commands_not_stub(self):
        lines = count_lines("telegram/commands/global_commands.py")
        assert lines >= self.MIN_LINES, f"global_commands.py tem apenas {lines} linhas"
    
    def test_bot_commands_not_stub(self):
        lines = count_lines("telegram/commands/bot_commands.py")
        assert lines >= self.MIN_LINES, f"bot_commands.py tem apenas {lines} linhas"
    
    def test_brain_commands_not_stub(self):
        lines = count_lines("telegram/commands/brain_commands.py")
        assert lines >= self.MIN_LINES, f"brain_commands.py tem apenas {lines} linhas"
    
    def test_advisor_commands_not_stub(self):
        lines = count_lines("telegram/commands/advisor_commands.py")
        assert lines >= self.MIN_LINES, f"advisor_commands.py tem apenas {lines} linhas"
    
    def test_model_registry_not_stub(self):
        lines = count_lines("ml/training/model_registry.py")
        assert lines >= self.MIN_LINES, f"model_registry.py tem apenas {lines} linhas"
    
    def test_trainer_service_not_stub(self):
        lines = count_lines("ml/training/trainer_service.py")
        assert lines >= self.MIN_LINES, f"trainer_service.py tem apenas {lines} linhas"


# =============================================================================
# TESTS: POSITIONS MODULE STRUCTURE
# =============================================================================

class TestPositionsModule:
    """Testa estrutura do módulo positions."""
    
    def test_position_manager_has_main_class(self):
        assert file_has_class("positions/position_manager.py", "PositionManager")
    
    def test_position_manager_has_record_class(self):
        assert file_has_class("positions/position_manager.py", "PositionRecord")
    
    def test_position_manager_has_metrics(self):
        assert file_has_class("positions/position_manager.py", "PositionMetrics")
    
    def test_position_monitor_has_main_class(self):
        assert file_has_class("positions/position_monitor.py", "PositionMonitor")
    
    def test_position_monitor_has_config(self):
        assert file_has_class("positions/position_monitor.py", "MonitorConfig")
    
    def test_trailing_stop_has_main_class(self):
        # Arquivo usa TrailingStop ou TrailingStopManager
        content = get_file_content("positions/exits/trailing_stop.py")
        assert "class TrailingStop" in content or "class TrailingStopManager" in content
    
    def test_trailing_stop_has_trailing_types(self):
        content = get_file_content("positions/exits/trailing_stop.py")
        # Verifica todos os 8 tipos de trailing
        trailing_types = [
            "FIXED_PIPS",
            "ATR_BASED",
            "PERCENTAGE",
            "CHANDELIER",
            "PARABOLIC_SAR",
            "SWING_BASED",
            "STEP_TRAIL",
            "BREAKEVEN_TRAIL",
        ]
        for tt in trailing_types:
            assert tt in content, f"TrailingType {tt} não encontrado"


# =============================================================================
# TESTS: STRATEGIES MODULE STRUCTURE
# =============================================================================

class TestStrategiesModule:
    """Testa estrutura do módulo strategies."""
    
    def test_strategy_factory_has_main_class(self):
        assert file_has_class("strategies/strategy_factory.py", "StrategyFactory")
    
    def test_strategy_factory_has_registry(self):
        assert file_has_class("strategies/strategy_factory.py", "StrategyRegistry")
    
    def test_strategy_factory_has_combiner(self):
        assert file_has_class("strategies/strategy_factory.py", "StrategyCombiner")
    
    def test_strategy_factory_has_decorator(self):
        assert file_has_function("strategies/strategy_factory.py", "register_strategy")


# =============================================================================
# TESTS: BRAIN ANALYZERS STRUCTURE
# =============================================================================

class TestBrainAnalyzers:
    """Testa estrutura dos brain analyzers."""
    
    def test_news_analyzer_has_main_class(self):
        assert file_has_class("brain/analyzers/news_analyzer.py", "NewsAnalyzer")
    
    def test_news_analyzer_has_item_class(self):
        assert file_has_class("brain/analyzers/news_analyzer.py", "NewsItem")
    
    def test_sentiment_analyzer_has_main_class(self):
        assert file_has_class("brain/analyzers/sentiment_analyzer.py", "SentimentAnalyzer")
    
    def test_sentiment_analyzer_has_composite(self):
        assert file_has_class("brain/analyzers/sentiment_analyzer.py", "CompositeSentiment")
    
    def test_macro_analyzer_has_main_class(self):
        assert file_has_class("brain/analyzers/macro_analyzer.py", "MacroAnalyzer")
    
    def test_macro_analyzer_has_event_class(self):
        assert file_has_class("brain/analyzers/macro_analyzer.py", "EconomicEvent")
    
    def test_correlation_analyzer_has_main_class(self):
        assert file_has_class("brain/analyzers/correlation_analyzer.py", "CorrelationAnalyzer")
    
    def test_correlation_analyzer_has_matrix(self):
        assert file_has_class("brain/analyzers/correlation_analyzer.py", "CorrelationMatrix")


# =============================================================================
# TESTS: RISK MODULE STRUCTURE
# =============================================================================

class TestRiskModule:
    """Testa estrutura do módulo risk."""
    
    def test_global_risk_has_main_class(self):
        assert file_has_class("risk/global_risk.py", "GlobalRiskManager")
    
    def test_global_risk_has_state_enum(self):
        assert file_has_class("risk/global_risk.py", "GlobalRiskState")
    
    def test_global_risk_has_trading_mode(self):
        content = get_file_content("risk/global_risk.py")
        assert "TradingMode" in content
        assert "FULL" in content
        assert "REDUCED" in content
        # Pode ser CLOSE_ONLY ou DEFENSIVE
        assert "CLOSE_ONLY" in content or "DEFENSIVE" in content
        assert "STOPPED" in content
    
    def test_correlation_risk_has_main_class(self):
        assert file_has_class("risk/correlation_risk.py", "CorrelationRiskManager")
    
    def test_exposure_manager_has_main_class(self):
        assert file_has_class("risk/exposure_manager.py", "ExposureManager")
    
    def test_exposure_manager_has_asset_class(self):
        assert file_has_class("risk/exposure_manager.py", "AssetClass")


# =============================================================================
# TESTS: TELEGRAM COMMANDS STRUCTURE
# =============================================================================

class TestTelegramCommands:
    """Testa estrutura dos comandos telegram."""
    
    def test_global_commands_has_main_class(self):
        assert file_has_class("telegram/commands/global_commands.py", "GlobalCommands")
    
    def test_global_commands_has_start(self):
        assert file_has_function("telegram/commands/global_commands.py", "cmd_start")
    
    def test_global_commands_has_status(self):
        assert file_has_function("telegram/commands/global_commands.py", "cmd_status")
    
    def test_global_commands_has_emergency(self):
        assert file_has_function("telegram/commands/global_commands.py", "cmd_emergency")
    
    def test_bot_commands_has_main_class(self):
        assert file_has_class("telegram/commands/bot_commands.py", "BotCommands")
    
    def test_bot_commands_has_symbols(self):
        content = get_file_content("telegram/commands/bot_commands.py")
        assert "XAUUSD" in content
        assert "EURUSD" in content
        assert "GBPUSD" in content
    
    def test_brain_commands_has_main_class(self):
        assert file_has_class("telegram/commands/brain_commands.py", "BrainCommands")
    
    def test_brain_commands_has_analysis(self):
        assert file_has_function("telegram/commands/brain_commands.py", "cmd_brain_analysis")
    
    def test_advisor_commands_has_main_class(self):
        assert file_has_class("telegram/commands/advisor_commands.py", "AdvisorCommands")
    
    def test_advisor_commands_has_briefing(self):
        assert file_has_function("telegram/commands/advisor_commands.py", "cmd_briefing")


# =============================================================================
# TESTS: ML TRAINING STRUCTURE
# =============================================================================

class TestMLTraining:
    """Testa estrutura do módulo ml.training."""
    
    def test_model_registry_has_main_class(self):
        assert file_has_class("ml/training/model_registry.py", "ModelRegistry")
    
    def test_model_registry_has_version(self):
        assert file_has_class("ml/training/model_registry.py", "ModelVersion")
    
    def test_model_registry_has_model_type(self):
        content = get_file_content("ml/training/model_registry.py")
        assert "ModelType" in content
        assert "DIRECTION" in content
        assert "VOLATILITY" in content
    
    def test_model_registry_has_deploy(self):
        assert file_has_function("ml/training/model_registry.py", "deploy_model")
    
    def test_trainer_service_has_main_class(self):
        assert file_has_class("ml/training/trainer_service.py", "TrainerService")
    
    def test_trainer_service_has_job(self):
        assert file_has_class("ml/training/trainer_service.py", "TrainingJob")
    
    def test_trainer_service_has_training_status(self):
        content = get_file_content("ml/training/trainer_service.py")
        assert "TrainingStatus" in content
        assert "PENDING" in content
        assert "TRAINING" in content
        assert "COMPLETED" in content
    
    def test_trainer_service_has_start_training(self):
        assert file_has_function("ml/training/trainer_service.py", "start_training")


# =============================================================================
# TESTS: INIT FILES
# =============================================================================

class TestInitFiles:
    """Verifica que __init__.py exportam corretamente."""
    
    def test_positions_init_exports(self):
        content = get_file_content("positions/__init__.py")
        assert "PositionManager" in content
        assert "PositionMonitor" in content
        assert "TrailingStop" in content  # Pode ser TrailingStop ou TrailingStopManager
    
    def test_strategies_init_exports(self):
        content = get_file_content("strategies/__init__.py")
        assert "StrategyFactory" in content
        assert "StrategyRegistry" in content
        assert "register_strategy" in content
    
    def test_brain_analyzers_init_exports(self):
        content = get_file_content("brain/analyzers/__init__.py")
        assert "NewsAnalyzer" in content
        assert "SentimentAnalyzer" in content
        assert "MacroAnalyzer" in content
        assert "CorrelationAnalyzer" in content
    
    def test_risk_init_exports(self):
        content = get_file_content("risk/__init__.py")
        assert "GlobalRiskManager" in content
        assert "CorrelationRiskManager" in content
        assert "ExposureManager" in content
    
    def test_telegram_commands_init_exports(self):
        content = get_file_content("telegram/commands/__init__.py")
        assert "GlobalCommands" in content
        assert "BotCommands" in content
        assert "BrainCommands" in content
        assert "AdvisorCommands" in content
    
    def test_ml_training_init_exports(self):
        content = get_file_content("ml/training/__init__.py")
        assert "TrainerService" in content
        assert "ModelRegistry" in content


# =============================================================================
# SUMMARY TEST
# =============================================================================

class TestSummary:
    """Teste resumo de todos os módulos."""
    
    def test_total_new_modules(self):
        """Verifica quantidade total de módulos novos."""
        new_files = [
            "positions/position_manager.py",
            "positions/position_monitor.py",
            "positions/exits/trailing_stop.py",
            "strategies/strategy_factory.py",
            "brain/analyzers/news_analyzer.py",
            "brain/analyzers/sentiment_analyzer.py",
            "brain/analyzers/macro_analyzer.py",
            "brain/analyzers/correlation_analyzer.py",
            "risk/global_risk.py",
            "risk/correlation_risk.py",
            "risk/exposure_manager.py",
            "telegram/commands/global_commands.py",
            "telegram/commands/bot_commands.py",
            "telegram/commands/brain_commands.py",
            "telegram/commands/advisor_commands.py",
            "ml/training/model_registry.py",
            "ml/training/trainer_service.py",
        ]
        
        existing = sum(1 for f in new_files if file_exists(f))
        assert existing == len(new_files), f"Apenas {existing}/{len(new_files)} arquivos existem"
    
    def test_total_lines_of_code(self):
        """Verifica total de linhas de código nos novos módulos."""
        new_files = [
            "positions/position_manager.py",
            "positions/position_monitor.py",
            "positions/exits/trailing_stop.py",
            "strategies/strategy_factory.py",
            "brain/analyzers/news_analyzer.py",
            "brain/analyzers/sentiment_analyzer.py",
            "brain/analyzers/macro_analyzer.py",
            "brain/analyzers/correlation_analyzer.py",
            "risk/global_risk.py",
            "risk/correlation_risk.py",
            "risk/exposure_manager.py",
            "telegram/commands/global_commands.py",
            "telegram/commands/bot_commands.py",
            "telegram/commands/brain_commands.py",
            "telegram/commands/advisor_commands.py",
            "ml/training/model_registry.py",
            "ml/training/trainer_service.py",
        ]
        
        total_lines = sum(count_lines(f) for f in new_files if file_exists(f))
        
        # Devem ter pelo menos 6000 linhas no total (17 arquivos * ~350 linhas média)
        assert total_lines >= 6000, f"Apenas {total_lines} linhas totais (esperado >= 6000)"
        
        print(f"\n✅ Total de linhas nos novos módulos: {total_lines}")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
    ])
