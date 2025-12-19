"""
VIRTUS Core - Módulo de Configuração
====================================

Carregamento e gerenciamento de configurações YAML.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .types import RiskConfig  # Usar RiskConfig de types.py


@dataclass
class MT5Config:
    """Configuração do MetaTrader 5"""
    path: str
    login: int
    password: str
    server: str
    timeout: int = 60000
    retries: int = 3
    retry_delay: int = 5


@dataclass
class TelegramConfig:
    """Configuração do Telegram"""
    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = True
    notifications: Dict[str, bool] = field(default_factory=lambda: {
        'trades': True,
        'alerts': True,
        'daily_report': True,
        'errors': True
    })
    
    @property
    def token(self) -> str:
        """Alias para bot_token"""
        return self.bot_token


@dataclass
class APIKeysConfig:
    """Configuração das API Keys"""
    forexnews: str = ""
    finnhub: str = ""
    finazon: str = ""
    twelvedata: str = ""
    financialmodelingprep: str = ""
    eodhd: str = ""
    
    @property
    def fmp(self) -> str:
        """Alias para financialmodelingprep"""
        return self.financialmodelingprep


@dataclass
class AdvisorConfig:
    """Configuração do Advisor (Relatórios)"""
    enabled: bool = True
    language: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"
    daily_briefing: Dict[str, Any] = field(default_factory=dict)
    news: Dict[str, Any] = field(default_factory=dict)
    sentiment: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BotConfig:
    """Configuração de um Bot individual"""
    id: str
    name: str
    symbol: str
    enabled: bool
    priority: str
    config_file: str
    
    # Intervalo de análise em segundos
    analysis_interval: float = 5.0
    
    # Estratégias
    strategies: Dict[str, Any] = field(default_factory=dict)
    
    # Risco
    risk: Dict[str, Any] = field(default_factory=dict)
    
    # Posições
    positions: Dict[str, Any] = field(default_factory=dict)
    
    # ML
    ml: Dict[str, Any] = field(default_factory=dict)
    
    # Análise
    analysis: Dict[str, Any] = field(default_factory=dict)
    
    # Brain
    brain: Dict[str, Any] = field(default_factory=dict)


class Config:
    """
    Gerenciador de Configuração Principal
    
    Carrega e gerencia todas as configurações do sistema VIRTUS.
    """
    
    _instance: Optional['Config'] = None
    
    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Determinar caminho do config - SEMPRE usar caminho absoluto
        if config_path:
            self.config_path = Path(config_path).resolve()
        else:
            self.config_path = Path(__file__).resolve().parent.parent.parent / "config"
        
        # Carregar configurações
        self._raw_config: Dict[str, Any] = {}
        self._brain_config: Dict[str, Any] = {}
        self._bot_configs: Dict[str, BotConfig] = {}
        
        self._load_configs()
    
    def _load_configs(self) -> None:
        """Carrega todos os arquivos de configuração"""
        # Config principal
        main_config_path = self.config_path / "config.yaml"
        if main_config_path.exists():
            with open(main_config_path, 'r', encoding='utf-8') as f:
                self._raw_config = yaml.safe_load(f)
        
        # Config do Brain
        brain_config_path = self.config_path / "brain.yaml"
        if brain_config_path.exists():
            with open(brain_config_path, 'r', encoding='utf-8') as f:
                self._brain_config = yaml.safe_load(f)
        
        # Obtém configuração de enabled do config.yaml principal
        # Isso permite sobrescrever o enabled dos YAMLs individuais
        main_bots_config = self._raw_config.get('bots', {})
        
        # Configs dos bots
        bots_path = self.config_path / "bots"
        if bots_path.exists():
            for bot_file in bots_path.glob("*.yaml"):
                with open(bot_file, 'r', encoding='utf-8') as f:
                    bot_data = yaml.safe_load(f)
                    if bot_data and 'bot' in bot_data:
                        bot_info = bot_data['bot']
                        bot_id = bot_info.get('id', bot_file.stem)
                        
                        # Verifica se há override de enabled no config.yaml principal
                        # Procura por bot_id + "_bot" (ex: gold_bot, euro_bot)
                        main_bot_key = f"{bot_id}_bot"
                        main_bot_override = main_bots_config.get(main_bot_key, {})
                        
                        # Usa enabled do config.yaml principal se existir,
                        # senão usa o do arquivo individual do bot
                        enabled = main_bot_override.get(
                            'enabled', 
                            bot_info.get('enabled', False)
                        )
                        
                        # Prioridade também pode ser sobrescrita
                        priority = main_bot_override.get(
                            'priority',
                            bot_info.get('priority', 'normal')
                        )
                        
                        bot_config = BotConfig(
                            id=bot_id,
                            name=bot_info.get('name', ''),
                            symbol=bot_info.get('symbol', ''),
                            enabled=enabled,
                            priority=priority,
                            config_file=str(bot_file),
                            analysis_interval=bot_info.get('analysis_interval', 5.0),
                            strategies=bot_data.get('strategies', {}),
                            risk=bot_data.get('risk', {}),
                            positions=bot_data.get('positions', {}),
                            ml=bot_data.get('ml', {}),
                            analysis=bot_data.get('analysis', {}),
                            brain=bot_data.get('brain', {})
                        )
                        self._bot_configs[bot_config.id] = bot_config
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'Config':
        """Carrega configuração de um arquivo YAML."""
        # Reset singleton para permitir novo caminho
        cls._instance = None
        # from_yaml recebe o path do arquivo, não do diretório
        # Extrair o diretório pai do arquivo config e resolver para path absoluto
        config_dir = str(Path(config_path).resolve().parent)
        instance = cls(config_dir)
        # Força reload para garantir que os bots sejam carregados
        instance.reload()
        return instance
    
    def reload(self) -> None:
        """Recarrega todas as configurações"""
        self._load_configs()
    
    # ========== Propriedades de Acesso ==========
    
    @property
    def mt5(self) -> MT5Config:
        """Retorna configuração do MT5"""
        mt5_data = self._raw_config.get('mt5', {})
        return MT5Config(
            path=mt5_data.get('path', ''),
            login=mt5_data.get('login', 0),
            password=mt5_data.get('password', ''),
            server=mt5_data.get('server', ''),
            timeout=mt5_data.get('timeout', 60000),
            retries=mt5_data.get('retries', 3),
            retry_delay=mt5_data.get('retry_delay', 5)
        )
    
    @property
    def telegram(self) -> TelegramConfig:
        """Retorna configuração do Telegram"""
        tg_data = self._raw_config.get('telegram', {})
        return TelegramConfig(
            bot_token=tg_data.get('bot_token', ''),
            chat_id=tg_data.get('chat_id', ''),
            enabled=tg_data.get('enabled', True),
            notifications=tg_data.get('notifications', {})
        )
    
    @property
    def api_keys(self) -> APIKeysConfig:
        """Retorna API Keys"""
        keys = self._raw_config.get('api_keys', {})
        return APIKeysConfig(
            forexnews=keys.get('forexnews', ''),
            finnhub=keys.get('finnhub', ''),
            finazon=keys.get('finazon', ''),
            twelvedata=keys.get('twelvedata', ''),
            financialmodelingprep=keys.get('financialmodelingprep', '')
        )
    
    @property
    def risk(self) -> RiskConfig:
        """Retorna configuração de risco global"""
        risk_data = self._raw_config.get('risk', {})
        return RiskConfig(
            max_daily_loss_pct=risk_data.get('max_daily_loss_pct', risk_data.get('max_daily_loss_usd', 500.0) / 100),
            max_weekly_loss_pct=risk_data.get('max_weekly_loss_pct', 10.0),
            max_drawdown=risk_data.get('max_drawdown_percent', risk_data.get('max_drawdown', 10.0)),
            max_total_exposure=risk_data.get('max_total_exposure', risk_data.get('max_exposure_percent', 30.0) / 10),
            max_symbol_exposure=risk_data.get('max_symbol_exposure', 1.0),
            max_correlated_exposure=risk_data.get('max_correlated_exposure', risk_data.get('correlation_limit', 0.7) * 3),
            max_positions=risk_data.get('max_positions', risk_data.get('max_total_positions', 6)),
            risk_per_trade=risk_data.get('risk_per_trade', 1.0),
            max_position_size=risk_data.get('max_position_size', 1.0),
            min_risk_reward=risk_data.get('min_risk_reward', 1.5),
            use_trailing_stop=risk_data.get('use_trailing_stop', True),
            trailing_stop_pips=risk_data.get('trailing_stop_pips', 20.0),
            break_even_pips=risk_data.get('break_even_pips', 15.0),
        )
    
    @property
    def advisor(self) -> AdvisorConfig:
        """Retorna configuração do Advisor"""
        adv_data = self._raw_config.get('advisor', {})
        return AdvisorConfig(
            enabled=adv_data.get('enabled', True),
            language=adv_data.get('language', 'pt-BR'),
            timezone=adv_data.get('timezone', 'America/Sao_Paulo'),
            daily_briefing=adv_data.get('daily_briefing', {}),
            news=adv_data.get('news', {}),
            sentiment=adv_data.get('sentiment', {})
        )
    
    @property
    def symbols(self) -> List[str]:
        """Retorna lista de símbolos habilitados"""
        return self._raw_config.get('symbols', {}).get('enabled', [])
    
    @property
    def brain_config(self) -> Dict[str, Any]:
        """Retorna configuração completa do Brain"""
        return self._brain_config
    
    @property
    def data_dir(self) -> str:
        """Retorna diretório de dados"""
        return str(self.config_path.parent / "data")
    
    # ========== Métodos de Bot ==========
    
    def get_bot_config(self, bot_id: str) -> Optional[BotConfig]:
        """Retorna configuração de um bot específico"""
        return self._bot_configs.get(bot_id)
    
    def get_all_bot_configs(self) -> Dict[str, BotConfig]:
        """Retorna todas as configurações de bots"""
        return self._bot_configs
    
    def get_enabled_bots(self) -> List[BotConfig]:
        """Retorna apenas bots habilitados"""
        return [bot for bot in self._bot_configs.values() if bot.enabled]
    
    @property
    def bots(self) -> List[BotConfig]:
        """Retorna lista de todos os bots configurados"""
        return list(self._bot_configs.values())
    
    # ========== Métodos Utilitários ==========
    
    def get(self, key: str, default: Any = None) -> Any:
        """Acesso genérico a configurações"""
        keys = key.split('.')
        value = self._raw_config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def get_brain(self, key: str, default: Any = None) -> Any:
        """Acesso a configurações do Brain"""
        keys = key.split('.')
        value = self._brain_config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


# Função helper para obter config global
def get_config(config_path: Optional[str] = None) -> Config:
    """Retorna instância singleton da configuração"""
    # Se já existe uma instância, retorna ela
    if Config._instance is not None:
        return Config._instance
    
    # Se não há path especificado, usa o path padrão absoluto baseado no diretório do módulo
    if config_path is None:
        # O diretório config está no mesmo nível que src (onde este arquivo está)
        # Este arquivo está em: brain/src/core/config.py
        # Config está em: brain/config/
        module_dir = Path(__file__).parent.parent.parent  # brain/
        config_path = str(module_dir / "config")
    
    return Config(config_path)


def load_config(config_path: Optional[str] = None) -> Config:
    """Carrega e retorna configuração (alias para get_config)"""
    return get_config(config_path)
