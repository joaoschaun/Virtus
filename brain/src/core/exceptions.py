"""
BRAIN - Exceções Customizadas
Exceções específicas do sistema
"""

from typing import Optional, Any


class BrainException(Exception):
    """Exceção base do sistema BRAIN"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ============================================================
# Exceções de Configuração
# ============================================================

class ConfigError(BrainException):
    """Erro de configuração"""
    pass


class ConfigNotFoundError(ConfigError):
    """Arquivo de configuração não encontrado"""
    pass


class ConfigValidationError(ConfigError):
    """Configuração inválida"""
    pass


# ============================================================
# Exceções do Brain Service
# ============================================================

class BrainError(BrainException):
    """Erro no serviço Brain"""
    pass


class CacheError(BrainError):
    """Erro no sistema de cache"""
    pass


class BudgetExceededError(BrainError):
    """Budget de API excedido"""
    
    def __init__(self, provider: str, limit: int, used: int):
        self.provider = provider
        self.limit = limit
        self.used = used
        super().__init__(
            f"Budget excedido para {provider}",
            {"limit": limit, "used": used}
        )


class ProviderError(BrainError):
    """Erro em provider de dados"""
    
    def __init__(self, provider: str, message: str, original_error: Optional[Exception] = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}", str(original_error) if original_error else None)


class RateLimitError(ProviderError):
    """Rate limit atingido"""
    pass


# ============================================================
# Exceções de Trading/Bot
# ============================================================

class TradingError(BrainException):
    """Erro de trading"""
    pass


class BotError(TradingError):
    """Erro no bot"""
    
    def __init__(self, bot_id: str, message: str, details: Optional[Any] = None):
        self.bot_id = bot_id
        super().__init__(f"[{bot_id}] {message}", details)


class BotNotFoundError(BotError):
    """Bot não encontrado"""
    pass


class BotAlreadyRunningError(BotError):
    """Bot já está rodando"""
    pass


class BotNotRunningError(BotError):
    """Bot não está rodando"""
    pass


# ============================================================
# Exceções de MT5
# ============================================================

class MT5Error(TradingError):
    """Erro do MetaTrader 5"""
    pass


class MT5ConnectionError(MT5Error):
    """Erro de conexão com MT5"""
    pass


class MT5OrderError(MT5Error):
    """Erro ao executar ordem"""
    
    def __init__(self, order_type: str, symbol: str, error_code: int, error_message: str):
        self.order_type = order_type
        self.symbol = symbol
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(
            f"Erro ao executar {order_type} em {symbol}: [{error_code}] {error_message}",
            {"code": error_code, "message": error_message}
        )


class MT5DataError(MT5Error):
    """Erro ao obter dados do MT5"""
    pass


# ============================================================
# Exceções de Posição
# ============================================================

class PositionError(TradingError):
    """Erro de posição"""
    pass


class PositionNotFoundError(PositionError):
    """Posição não encontrada"""
    
    def __init__(self, ticket: int):
        self.ticket = ticket
        super().__init__(f"Posição {ticket} não encontrada")


class PositionModificationError(PositionError):
    """Erro ao modificar posição"""
    pass


class PositionCloseError(PositionError):
    """Erro ao fechar posição"""
    pass


# ============================================================
# Exceções de Risco
# ============================================================

class RiskError(TradingError):
    """Erro de risco"""
    pass


class MaxPositionsError(RiskError):
    """Número máximo de posições atingido"""
    
    def __init__(self, current: int, max_allowed: int, scope: str = "global"):
        self.current = current
        self.max_allowed = max_allowed
        self.scope = scope
        super().__init__(
            f"Máximo de posições ({scope}) atingido: {current}/{max_allowed}",
            {"current": current, "max": max_allowed}
        )


class DailyLossLimitError(RiskError):
    """Limite de perda diária atingido"""
    
    def __init__(self, current_loss: float, limit: float, bot_id: Optional[str] = None):
        self.current_loss = current_loss
        self.limit = limit
        self.bot_id = bot_id
        scope = f"bot {bot_id}" if bot_id else "global"
        super().__init__(
            f"Limite de perda diária ({scope}) atingido: ${current_loss:.2f}/${limit:.2f}",
            {"current": current_loss, "limit": limit}
        )


class DrawdownLimitError(RiskError):
    """Limite de drawdown atingido"""
    
    def __init__(self, current_dd: float, limit: float):
        self.current_dd = current_dd
        self.limit = limit
        super().__init__(
            f"Limite de drawdown atingido: {current_dd:.2f}%/{limit:.2f}%",
            {"current": current_dd, "limit": limit}
        )


class CorrelationRiskError(RiskError):
    """Risco de correlação excedido"""
    
    def __init__(self, symbol1: str, symbol2: str, correlation: float, limit: float):
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.correlation = correlation
        self.limit = limit
        super().__init__(
            f"Correlação alta entre {symbol1} e {symbol2}: {correlation:.2f} (limite: {limit:.2f})",
            {"symbols": [symbol1, symbol2], "correlation": correlation}
        )


# ============================================================
# Exceções de Estratégia
# ============================================================

class StrategyError(TradingError):
    """Erro de estratégia"""
    pass


class StrategyNotFoundError(StrategyError):
    """Estratégia não encontrada"""
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        super().__init__(f"Estratégia '{strategy_name}' não encontrada")


class StrategyValidationError(StrategyError):
    """Erro de validação de estratégia"""
    pass


# ============================================================
# Exceções de Análise
# ============================================================

class AnalysisError(BrainException):
    """Erro de análise"""
    pass


class InsufficientDataError(AnalysisError):
    """Dados insuficientes para análise"""
    
    def __init__(self, required: int, available: int, data_type: str = "candles"):
        self.required = required
        self.available = available
        self.data_type = data_type
        super().__init__(
            f"Dados insuficientes para análise: {available}/{required} {data_type}",
            {"required": required, "available": available}
        )


# ============================================================
# Exceções de ML
# ============================================================

class MLError(BrainException):
    """Erro de Machine Learning"""
    pass


class ModelNotFoundError(MLError):
    """Modelo não encontrado"""
    
    def __init__(self, model_name: str, symbol: Optional[str] = None):
        self.model_name = model_name
        self.symbol = symbol
        msg = f"Modelo '{model_name}'"
        if symbol:
            msg += f" para {symbol}"
        msg += " não encontrado"
        super().__init__(msg)


class ModelLoadError(MLError):
    """Erro ao carregar modelo"""
    pass


class PredictionError(MLError):
    """Erro ao fazer predição"""
    pass


# ============================================================
# Exceções de Telegram
# ============================================================

class TelegramError(BrainException):
    """Erro do Telegram"""
    pass


class TelegramConnectionError(TelegramError):
    """Erro de conexão com Telegram"""
    pass


class TelegramSendError(TelegramError):
    """Erro ao enviar mensagem"""
    pass
