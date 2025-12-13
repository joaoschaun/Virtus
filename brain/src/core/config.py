"""
BRAIN - Módulo de Configuração
Carrega e gerencia todas as configurações do sistema
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"


@dataclass
class MT5Config:
    """Configuração do MetaTrader 5"""
    path: str
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    timeout: int = 60000
    portable: bool = False
    
    def __post_init__(self):
        # Carregar de variáveis de ambiente se não definido
        self.login = self.login or os.getenv("MT5_LOGIN")
        self.password = self.password or os.getenv("MT5_PASSWORD")
        self.server = self.server or os.getenv("MT5_SERVER")
        
        if self.login:
            self.login = int(self.login)


@dataclass
class RiskConfig:
    """Configuração de risco global"""
    max_total_positions: int = 6
    max_daily_loss_usd: float = 500.0
    max_daily_loss_percent: float = 5.0
    max_drawdown_percent: float = 10.0
    correlation_limit: float = 0.7


@dataclass
class LocalizationConfig:
    """Configuração de localização"""
    language: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"
    date_format: str = "%d/%m/%Y"
    time_format: str = "%H:%M:%S"


@dataclass
class LoggingConfig:
    """Configuração de logging"""
    level: str = "INFO"
    file_rotation: str = "daily"
    max_files: int = 30
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


@dataclass
class ReportingConfig:
    """Configuração de relatórios"""
    daily_briefing_enabled: bool = True
    daily_briefing_hour: int = 7
    daily_briefing_minute: int = 30
    weekly_report_enabled: bool = True
    weekly_report_day: str = "monday"
    weekly_report_hour: int = 8


@dataclass
class BotConfig:
    """Configuração de um bot individual"""
    id: str
    name: str
    symbol: str
    enabled: bool = True
    description: str = ""
    strategies: Dict[str, Any] = field(default_factory=dict)
    risk: Dict[str, Any] = field(default_factory=dict)
    positions: Dict[str, Any] = field(default_factory=dict)
    ml: Dict[str, Any] = field(default_factory=dict)
    analysis: Dict[str, Any] = field(default_factory=dict)
    brain: Dict[str, Any] = field(default_factory=dict)
    schedule: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, filepath: Path) -> "BotConfig":
        """Carrega configuração de bot de arquivo YAML"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        bot_data = data.get("bot", {})
        return cls(
            id=bot_data.get("id", "unknown"),
            name=bot_data.get("name", "Unknown Bot"),
            symbol=bot_data.get("symbol", ""),
            enabled=bot_data.get("enabled", True),
            description=bot_data.get("description", ""),
            strategies=data.get("strategies", {}),
            risk=data.get("risk", {}),
            positions=data.get("positions", {}),
            ml=data.get("ml", {}),
            analysis=data.get("analysis", {}),
            brain=data.get("brain", {}),
            schedule=data.get("schedule", {})
        )


@dataclass
class BrainConfig:
    """Configuração do Brain Service"""
    cache: Dict[str, Any] = field(default_factory=dict)
    budget: Dict[str, Any] = field(default_factory=dict)
    providers: Dict[str, Any] = field(default_factory=dict)
    analyzers: Dict[str, Any] = field(default_factory=dict)
    symbols: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, filepath: Path) -> "BrainConfig":
        """Carrega configuração do Brain de arquivo YAML"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return cls(
            cache=data.get("cache", {}),
            budget=data.get("budget", {}),
            providers=data.get("providers", {}),
            analyzers=data.get("analyzers", {}),
            symbols=data.get("symbols", {})
        )


class Config:
    """
    Gerenciador central de configurações
    
    Singleton que carrega e disponibiliza todas as configurações do sistema.
    """
    
    _instance: Optional["Config"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._config_data: Dict[str, Any] = {}
        self._bot_configs: Dict[str, BotConfig] = {}
        self._brain_config: Optional[BrainConfig] = None
        
        # Carregar configurações
        self._load_main_config()
        self._load_brain_config()
        self._load_bot_configs()
    
    def _load_main_config(self):
        """Carrega configuração principal"""
        config_path = CONFIG_DIR / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config_data = yaml.safe_load(f)
    
    def _load_brain_config(self):
        """Carrega configuração do Brain"""
        brain_path = CONFIG_DIR / "brain.yaml"
        if brain_path.exists():
            self._brain_config = BrainConfig.from_yaml(brain_path)
    
    def _load_bot_configs(self):
        """Carrega configurações de todos os bots"""
        bots_dir = CONFIG_DIR / "bots"
        if bots_dir.exists():
            for yaml_file in bots_dir.glob("*.yaml"):
                bot_config = BotConfig.from_yaml(yaml_file)
                self._bot_configs[bot_config.id] = bot_config
    
    # === Propriedades de acesso ===
    
    @property
    def system(self) -> Dict[str, Any]:
        """Configuração do sistema"""
        return self._config_data.get("system", {})
    
    @property
    def mt5(self) -> MT5Config:
        """Configuração do MT5"""
        mt5_data = self._config_data.get("mt5", {})
        return MT5Config(**mt5_data)
    
    @property
    def risk(self) -> RiskConfig:
        """Configuração de risco global"""
        risk_data = self._config_data.get("risk", {})
        return RiskConfig(**{k: v for k, v in risk_data.items() if k in RiskConfig.__dataclass_fields__})
    
    @property
    def localization(self) -> LocalizationConfig:
        """Configuração de localização"""
        loc_data = self._config_data.get("localization", {})
        return LocalizationConfig(**loc_data)
    
    @property
    def logging(self) -> LoggingConfig:
        """Configuração de logging"""
        log_data = self._config_data.get("logging", {})
        return LoggingConfig(**log_data)
    
    @property
    def brain(self) -> BrainConfig:
        """Configuração do Brain Service"""
        return self._brain_config
    
    @property
    def enabled_bots(self) -> List[str]:
        """Lista de IDs dos bots habilitados"""
        return self._config_data.get("bots", {}).get("enabled", [])
    
    @property
    def trading_interval(self) -> int:
        """Intervalo de trading em segundos"""
        return self._config_data.get("bots", {}).get("trading_interval", 5)
    
    @property
    def position_check_interval(self) -> int:
        """Intervalo de verificação de posições em segundos"""
        return self._config_data.get("bots", {}).get("position_check_interval", 2)
    
    # === Métodos de acesso a bots ===
    
    def get_bot_config(self, bot_id: str) -> Optional[BotConfig]:
        """Retorna configuração de um bot específico"""
        return self._bot_configs.get(bot_id)
    
    def get_all_bot_configs(self) -> Dict[str, BotConfig]:
        """Retorna todas as configurações de bots"""
        return self._bot_configs
    
    def get_enabled_bot_configs(self) -> List[BotConfig]:
        """Retorna configurações apenas dos bots habilitados"""
        return [
            self._bot_configs[bot_id] 
            for bot_id in self.enabled_bots 
            if bot_id in self._bot_configs and self._bot_configs[bot_id].enabled
        ]
    
    # === Métodos de acesso genérico ===
    
    def get(self, key: str, default: Any = None) -> Any:
        """Acesso genérico a configurações"""
        keys = key.split(".")
        value = self._config_data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    def reload(self):
        """Recarrega todas as configurações"""
        self._initialized = False
        self.__init__()


def load_config() -> Config:
    """Função helper para carregar configuração"""
    return Config()


def get_config() -> Config:
    """Retorna instância singleton da configuração"""
    return Config()
