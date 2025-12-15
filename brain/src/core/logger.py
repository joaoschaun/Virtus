"""
VIRTUS Core - Sistema de Logging
================================

Logger configurável por módulo/bot com suporte a arquivos e console.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from logging.handlers import RotatingFileHandler


# Adiciona nível SUCCESS (entre INFO e WARNING)
SUCCESS = 25
logging.addLevelName(SUCCESS, 'SUCCESS')


# Cores para console (ANSI)
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BRIGHT_GREEN = '\033[1;92m'


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para diferentes níveis de log"""
    
    COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        SUCCESS: Colors.BRIGHT_GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.MAGENTA,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, Colors.WHITE)
        
        # Adiciona emoji baseado no módulo
        emoji = self._get_emoji(record.name)
        
        # Formata a mensagem
        record.emoji = emoji
        record.color = color
        record.reset = Colors.RESET
        
        return super().format(record)
    
    def _get_emoji(self, name: str) -> str:
        """Retorna emoji baseado no nome do logger"""
        emoji_map = {
            'brain': '🧠',
            'bot': '🤖',
            'gold': '🥇',
            'euro': '💶',
            'gbp': '💷',
            'telegram': '💬',
            'mt5': '📊',
            'risk': '⚠️',
            'position': '📈',
            'strategy': '🎯',
            'advisor': '📝',
            'ml': '🔮',
            'orchestrator': '🎭',
        }
        
        name_lower = name.lower()
        for key, emoji in emoji_map.items():
            if key in name_lower:
                return emoji
        return '📌'


class VirtusLogger:
    """
    Logger personalizado para VIRTUS
    
    Suporta:
    - Log em console colorido
    - Log em arquivo com rotação
    - Log separado por bot/módulo
    """
    
    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False
    _log_path: Optional[Path] = None
    _log_level: int = logging.INFO
    
    @classmethod
    def setup(
        cls,
        log_path: Optional[str] = None,
        level: str = "INFO",
        max_size_mb: int = 10,
        backup_count: int = 5
    ) -> None:
        """
        Configura o sistema de logging
        
        Args:
            log_path: Caminho para salvar logs
            level: Nível de log (DEBUG, INFO, WARNING, ERROR)
            max_size_mb: Tamanho máximo do arquivo de log
            backup_count: Número de backups a manter
        """
        cls._log_level = getattr(logging, level.upper(), logging.INFO)
        
        if log_path:
            cls._log_path = Path(log_path)
            cls._log_path.mkdir(parents=True, exist_ok=True)
        
        cls._max_size = max_size_mb * 1024 * 1024
        cls._backup_count = backup_count
        cls._initialized = True
    
    @classmethod
    def get_logger(
        cls,
        name: str,
        log_file: Optional[str] = None
    ) -> logging.Logger:
        """
        Obtém um logger configurado
        
        Args:
            name: Nome do logger (ex: "brain", "bot.gold")
            log_file: Arquivo de log específico (opcional)
        
        Returns:
            Logger configurado
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        # Criar logger
        logger = logging.getLogger(f"virtus.{name}")
        logger.setLevel(cls._log_level)
        logger.propagate = False
        
        # Handler de console com UTF-8 para suportar emojis no Windows
        import io
        if sys.platform == 'win32':
            # Força UTF-8 no stdout para Windows
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(cls._log_level)
        
        # Formato colorido para console
        console_format = "%(color)s%(emoji)s %(asctime)s [%(name)s] %(levelname)s: %(message)s%(reset)s"
        console_formatter = ColoredFormatter(console_format, datefmt='%H:%M:%S')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Handler de arquivo (se configurado)
        if cls._log_path:
            if log_file:
                file_path = cls._log_path / log_file
            else:
                file_path = cls._log_path / f"{name.replace('.', '_')}.log"
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=cls._max_size if hasattr(cls, '_max_size') else 10*1024*1024,
                backupCount=cls._backup_count if hasattr(cls, '_backup_count') else 5,
                encoding='utf-8'
            )
            file_handler.setLevel(cls._log_level)
            
            # Formato para arquivo (sem cores)
            file_format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
            file_formatter = logging.Formatter(file_format, datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return EnhancedLogger(logger)


class EnhancedLogger:
    """Logger wrapper com método success()"""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        self._logger.exception(msg, *args, **kwargs)
    
    def success(self, msg: str, *args, **kwargs):
        """Log de sucesso (nível SUCCESS = 25)"""
        self._logger.log(SUCCESS, msg, *args, **kwargs)
    
    def __getattr__(self, name):
        """Delega atributos desconhecidos ao logger interno"""
        return getattr(self._logger, name)


def get_logger(name: str, log_file: Optional[str] = None) -> EnhancedLogger:
    """
    Função helper para obter logger
    
    Args:
        name: Nome do logger
        log_file: Arquivo de log específico
    
    Returns:
        Logger configurado
    """
    return VirtusLogger.get_logger(name, log_file)


def setup_logger(
    log_path: Optional[str] = None,
    level: str = "INFO",
    max_size_mb: int = 10,
    backup_count: int = 5
) -> None:
    """
    Configura o sistema de logging
    
    Args:
        log_path: Caminho para salvar logs
        level: Nível de log
        max_size_mb: Tamanho máximo do arquivo
        backup_count: Número de backups
    """
    VirtusLogger.setup(log_path, level, max_size_mb, backup_count)


# Logger padrão do sistema
def get_system_logger() -> logging.Logger:
    """Retorna logger do sistema principal"""
    return get_logger("system")
