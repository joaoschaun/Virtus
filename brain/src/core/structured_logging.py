"""
VIRTUS - Logging Estruturado (JSON)
===================================

Sistema de logging com formato JSON para análise facilitada.
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """
    Formatter que produz logs em formato JSON.
    
    Ideal para:
    - Ingestão em sistemas como ELK Stack, Datadog, Splunk
    - Análise automatizada de logs
    - Correlação de eventos
    """
    
    def __init__(
        self,
        include_extras: bool = True,
        include_stack_trace: bool = True,
        timestamp_format: str = "%Y-%m-%dT%H:%M:%S.%fZ"
    ):
        super().__init__()
        self.include_extras = include_extras
        self.include_stack_trace = include_stack_trace
        self.timestamp_format = timestamp_format
    
    def format(self, record: logging.LogRecord) -> str:
        """Formata o log record como JSON."""
        log_data = {
            "timestamp": datetime.utcnow().strftime(self.timestamp_format),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Adiciona campos extras se existirem
        if self.include_extras and hasattr(record, "extra"):
            log_data["extra"] = record.extra
        
        # Adiciona exceção se houver
        if record.exc_info and self.include_stack_trace:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Campos extras comuns
        if hasattr(record, "bot_id"):
            log_data["bot_id"] = record.bot_id
        if hasattr(record, "symbol"):
            log_data["symbol"] = record.symbol
        if hasattr(record, "trade_id"):
            log_data["trade_id"] = record.trade_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class StructuredLogger(logging.Logger):
    """
    Logger que facilita logging estruturado.
    
    Uso:
        logger = StructuredLogger("bot.gold")
        logger.info("Trade executado", extra={
            "symbol": "XAUUSD",
            "type": "BUY",
            "price": 2050.50
        })
    """
    
    def _log_with_context(
        self,
        level: int,
        msg: str,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log com contexto estruturado."""
        if extra:
            kwargs["extra"] = {"extra": extra}
        super().log(level, msg, **kwargs)
    
    def info_structured(self, msg: str, **kwargs):
        self._log_with_context(logging.INFO, msg, kwargs)
    
    def warning_structured(self, msg: str, **kwargs):
        self._log_with_context(logging.WARNING, msg, kwargs)
    
    def error_structured(self, msg: str, **kwargs):
        self._log_with_context(logging.ERROR, msg, kwargs)
    
    def debug_structured(self, msg: str, **kwargs):
        self._log_with_context(logging.DEBUG, msg, kwargs)


def setup_json_logging(
    log_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
    console_json: bool = False
) -> logging.Logger:
    """
    Configura logging JSON para o sistema.
    
    Args:
        log_dir: Diretório para arquivos de log
        log_level: Nível de log
        console_json: Se True, console também usa JSON
        
    Returns:
        Logger configurado
    """
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / "data" / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Logger root
    logger = logging.getLogger("virtus")
    logger.setLevel(log_level)
    logger.handlers.clear()
    
    # Handler JSON para arquivo
    json_file = log_dir / "virtus.json.log"
    json_handler = logging.FileHandler(json_file, encoding="utf-8")
    json_handler.setFormatter(JSONFormatter())
    json_handler.setLevel(log_level)
    logger.addHandler(json_handler)
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    if console_json:
        console_handler.setFormatter(JSONFormatter())
    else:
        # Formato legível para humanos no console
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        ))
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)
    
    return logger


class LogContext:
    """
    Context manager para adicionar contexto temporário aos logs.
    
    Uso:
        with LogContext(request_id="abc123", user="admin"):
            logger.info("Processando...")  # Inclui request_id e user
    """
    
    _context: Dict[str, Any] = {}
    
    def __init__(self, **kwargs):
        self.new_context = kwargs
        self.old_context = {}
    
    def __enter__(self):
        self.old_context = LogContext._context.copy()
        LogContext._context.update(self.new_context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        LogContext._context = self.old_context
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        return cls._context.get(key, default)
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        return cls._context.copy()


class ContextAwareJSONFormatter(JSONFormatter):
    """Formatter que inclui contexto global."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Adiciona contexto global ao record
        context = LogContext.get_all()
        if context:
            if not hasattr(record, "extra"):
                record.extra = {}
            record.extra.update(context)
        
        return super().format(record)


# ==================== HELPERS ====================

def log_trade(
    logger: logging.Logger,
    action: str,
    symbol: str,
    **kwargs
):
    """Helper para logging de trades."""
    logger.info(
        f"Trade {action}: {symbol}",
        extra={
            "event_type": "trade",
            "action": action,
            "symbol": symbol,
            **kwargs
        }
    )


def log_signal(
    logger: logging.Logger,
    symbol: str,
    direction: str,
    confidence: float,
    **kwargs
):
    """Helper para logging de sinais."""
    logger.info(
        f"Signal: {symbol} {direction} (conf: {confidence:.0%})",
        extra={
            "event_type": "signal",
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            **kwargs
        }
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict] = None
):
    """Helper para logging de erros."""
    logger.error(
        f"Error: {type(error).__name__}: {error}",
        exc_info=True,
        extra={
            "event_type": "error",
            "error_type": type(error).__name__,
            **(context or {})
        }
    )
