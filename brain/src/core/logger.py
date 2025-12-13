"""
BRAIN - Módulo de Logging
Sistema de logging centralizado com suporte a múltiplos bots
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from .config import Config, BASE_DIR


# Diretório de logs
LOGS_DIR = BASE_DIR / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para console"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[41m',  # Red background
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class BrainLogger:
    """
    Gerenciador de logging do sistema BRAIN
    
    Características:
    - Logger separado por bot
    - Rotação de arquivos
    - Cores no console
    - Níveis configuráveis
    """
    
    _instance: Optional["BrainLogger"] = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._config = Config()
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """Configura o logger raiz"""
        log_config = self._config.logging
        
        # Configurar logger raiz
        root_logger = logging.getLogger("brain")
        root_logger.setLevel(getattr(logging, log_config.level.upper()))
        
        # Handler de console com cores
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = ColoredFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Handler de arquivo principal
        main_log_path = LOGS_DIR / "brain.log"
        file_handler = TimedRotatingFileHandler(
            main_log_path,
            when="midnight",
            interval=1,
            backupCount=log_config.max_files,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(log_config.format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        self._loggers["brain"] = root_logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Retorna um logger para um módulo/bot específico
        
        Args:
            name: Nome do logger (ex: "gold", "euro", "brain.cache")
        
        Returns:
            Logger configurado
        """
        if name in self._loggers:
            return self._loggers[name]
        
        log_config = self._config.logging
        
        # Criar logger filho
        logger = logging.getLogger(f"brain.{name}")
        logger.setLevel(getattr(logging, log_config.level.upper()))
        
        # Handler de arquivo específico para bots
        if name in ["gold", "euro", "gbp"]:
            bot_log_path = LOGS_DIR / f"{name}.log"
            bot_handler = TimedRotatingFileHandler(
                bot_log_path,
                when="midnight",
                interval=1,
                backupCount=log_config.max_files,
                encoding="utf-8"
            )
            bot_handler.setLevel(logging.DEBUG)
            bot_formatter = logging.Formatter(log_config.format)
            bot_handler.setFormatter(bot_formatter)
            logger.addHandler(bot_handler)
        
        self._loggers[name] = logger
        return logger
    
    def set_level(self, level: str, logger_name: Optional[str] = None):
        """Define o nível de logging"""
        level_value = getattr(logging, level.upper())
        
        if logger_name:
            if logger_name in self._loggers:
                self._loggers[logger_name].setLevel(level_value)
        else:
            for logger in self._loggers.values():
                logger.setLevel(level_value)


# Instância global
_logger_manager: Optional[BrainLogger] = None


def setup_logger() -> BrainLogger:
    """Inicializa o sistema de logging"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = BrainLogger()
    return _logger_manager


def get_logger(name: str = "brain") -> logging.Logger:
    """
    Retorna um logger configurado
    
    Args:
        name: Nome do logger
        
    Returns:
        Logger configurado
        
    Exemplo:
        logger = get_logger("gold")
        logger.info("Bot Gold iniciado")
    """
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = BrainLogger()
    return _logger_manager.get_logger(name)


# Aliases para conveniência
def debug(msg: str, name: str = "brain"):
    get_logger(name).debug(msg)

def info(msg: str, name: str = "brain"):
    get_logger(name).info(msg)

def warning(msg: str, name: str = "brain"):
    get_logger(name).warning(msg)

def error(msg: str, name: str = "brain"):
    get_logger(name).error(msg)

def critical(msg: str, name: str = "brain"):
    get_logger(name).critical(msg)
