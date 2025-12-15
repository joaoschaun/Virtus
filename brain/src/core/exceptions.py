"""
VIRTUS Core - Exceptions
========================

Exceções customizadas do sistema.
"""

from typing import Optional, Any


# ============================================================================
# BASE EXCEPTIONS
# ============================================================================

class VirtusError(Exception):
    """Exceção base do sistema VIRTUS"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ============================================================================
# CONFIGURATION ERRORS
# ============================================================================

class ConfigurationError(VirtusError):
    """Erro de configuração"""
    pass


class ConfigNotFoundError(ConfigurationError):
    """Arquivo de configuração não encontrado"""
    pass


class InvalidConfigError(ConfigurationError):
    """Configuração inválida"""
    pass


# ============================================================================
# MT5 ERRORS
# ============================================================================

class MT5Error(VirtusError):
    """Erro relacionado ao MetaTrader 5"""
    pass


class MT5ConnectionError(MT5Error):
    """Erro de conexão com MT5"""
    pass


class MT5AuthenticationError(MT5Error):
    """Erro de autenticação no MT5"""
    pass


class MT5OrderError(MT5Error):
    """Erro ao processar ordem no MT5"""
    pass


class MT5SymbolError(MT5Error):
    """Erro relacionado a símbolo no MT5"""
    pass


class MT5DataError(MT5Error):
    """Erro ao obter dados do MT5"""
    pass


# ============================================================================
# API ERRORS
# ============================================================================

class APIError(VirtusError):
    """Erro de API externa"""
    
    def __init__(self, message: str, provider: str = "", 
                 status_code: Optional[int] = None, details: Optional[Any] = None):
        super().__init__(message, details)
        self.provider = provider
        self.status_code = status_code


class APIConnectionError(APIError):
    """Erro de conexão com API"""
    pass


class APIRateLimitError(APIError):
    """Rate limit excedido"""
    
    def __init__(self, message: str, provider: str = "", 
                 retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, provider, **kwargs)
        self.retry_after = retry_after


class APIAuthenticationError(APIError):
    """Erro de autenticação na API"""
    pass


class APIResponseError(APIError):
    """Erro na resposta da API"""
    pass


# ============================================================================
# BRAIN ERRORS
# ============================================================================

class BrainError(VirtusError):
    """Erro no módulo Brain"""
    pass


class CacheError(BrainError):
    """Erro no sistema de cache"""
    pass


class BudgetExceededError(BrainError):
    """Budget de API excedido"""
    
    def __init__(self, message: str, provider: str = "", 
                 budget_limit: float = 0, current_usage: float = 0, **kwargs):
        super().__init__(message, **kwargs)
        self.provider = provider
        self.budget_limit = budget_limit
        self.current_usage = current_usage


class ProviderUnavailableError(BrainError):
    """Provider não disponível"""
    pass


class NoDataError(BrainError):
    """Nenhum dado disponível"""
    pass


# ============================================================================
# BOT ERRORS
# ============================================================================

class BotError(VirtusError):
    """Erro relacionado a um bot"""
    pass


class BotStartupError(BotError):
    """Erro ao iniciar bot"""
    pass


class BotShutdownError(BotError):
    """Erro ao parar bot"""
    pass


class BotNotFoundError(BotError):
    """Bot não encontrado"""
    pass


class BotAlreadyRunningError(BotError):
    """Bot já está em execução"""
    pass


# ============================================================================
# STRATEGY ERRORS
# ============================================================================

class StrategyError(VirtusError):
    """Erro em estratégia"""
    pass


class InvalidSignalError(StrategyError):
    """Sinal inválido"""
    pass


class StrategyNotFoundError(StrategyError):
    """Estratégia não encontrada"""
    pass


# ============================================================================
# POSITION ERRORS
# ============================================================================

class PositionError(VirtusError):
    """Erro em posição"""
    pass


class PositionNotFoundError(PositionError):
    """Posição não encontrada"""
    pass


class InvalidPositionSizeError(PositionError):
    """Tamanho de posição inválido"""
    pass


class MaxPositionsExceededError(PositionError):
    """Máximo de posições excedido"""
    pass


# ============================================================================
# RISK ERRORS
# ============================================================================

class RiskError(VirtusError):
    """Erro no sistema de risco"""
    pass


class RiskLimitExceededError(RiskError):
    """Limite de risco excedido"""
    pass


class DrawdownLimitError(RiskError):
    """Limite de drawdown atingido"""
    pass


class DailyLossLimitError(RiskError):
    """Limite de perda diária atingido"""
    pass


# ============================================================================
# ANALYSIS ERRORS
# ============================================================================

class AnalysisError(VirtusError):
    """Erro em análise"""
    pass


class InsufficientDataError(AnalysisError):
    """Dados insuficientes para análise"""
    pass


class IndicatorError(AnalysisError):
    """Erro ao calcular indicador"""
    pass


# ============================================================================
# ML ERRORS
# ============================================================================

class MLError(VirtusError):
    """Erro no módulo de Machine Learning"""
    pass


class ModelNotFoundError(MLError):
    """Modelo não encontrado"""
    pass


class ModelTrainingError(MLError):
    """Erro no treinamento de modelo"""
    pass


class PredictionError(MLError):
    """Erro na predição"""
    pass


# ============================================================================
# TELEGRAM ERRORS
# ============================================================================

class TelegramError(VirtusError):
    """Erro no módulo Telegram"""
    pass


class TelegramConnectionError(TelegramError):
    """Erro de conexão com Telegram"""
    pass


class TelegramMessageError(TelegramError):
    """Erro ao enviar mensagem"""
    pass


# ============================================================================
# DATABASE ERRORS
# ============================================================================

class DatabaseError(VirtusError):
    """Erro de banco de dados"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Erro de conexão com banco"""
    pass


class RecordNotFoundError(DatabaseError):
    """Registro não encontrado"""
    pass


# ============================================================================
# ORCHESTRATOR ERRORS
# ============================================================================

class OrchestratorError(VirtusError):
    """Erro no orquestrador"""
    pass


class BotRegistrationError(OrchestratorError):
    """Erro ao registrar bot"""
    pass


class BotSupervisorError(OrchestratorError):
    """Erro no supervisor de bots"""
    pass
