"""
VIRTUS - Environment Configuration
===================================

Carrega configurações de variáveis de ambiente com fallback para config.yaml.
SEMPRE prefere variáveis de ambiente para dados sensíveis.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Carrega .env se existir
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class EnvConfig:
    """
    Gerenciador de configurações via variáveis de ambiente.
    
    Prioridade:
    1. Variáveis de ambiente
    2. Arquivo .env
    3. Valores padrão (config.yaml)
    """
    
    # ==================== MT5 ====================
    
    @staticmethod
    def mt5_login() -> Optional[int]:
        """Login MT5 (sensível)."""
        val = os.getenv("MT5_LOGIN")
        return int(val) if val else None
    
    @staticmethod
    def mt5_password() -> Optional[str]:
        """Senha MT5 (sensível)."""
        return os.getenv("MT5_PASSWORD")
    
    @staticmethod
    def mt5_server() -> Optional[str]:
        """Servidor MT5."""
        return os.getenv("MT5_SERVER")
    
    @staticmethod
    def mt5_path() -> Optional[str]:
        """Caminho do terminal MT5."""
        return os.getenv("MT5_PATH")
    
    # ==================== TELEGRAM ====================
    
    @staticmethod
    def telegram_token() -> Optional[str]:
        """Token do bot Telegram (sensível)."""
        return os.getenv("TELEGRAM_BOT_TOKEN")
    
    @staticmethod
    def telegram_chat_id() -> Optional[str]:
        """Chat ID do Telegram."""
        return os.getenv("TELEGRAM_CHAT_ID")
    
    # ==================== API KEYS ====================
    
    @staticmethod
    def api_key_forexnews() -> Optional[str]:
        return os.getenv("API_KEY_FOREXNEWS")
    
    @staticmethod
    def api_key_finnhub() -> Optional[str]:
        return os.getenv("API_KEY_FINNHUB")
    
    @staticmethod
    def api_key_finazon() -> Optional[str]:
        return os.getenv("API_KEY_FINAZON")
    
    @staticmethod
    def api_key_twelvedata() -> Optional[str]:
        return os.getenv("API_KEY_TWELVEDATA")
    
    @staticmethod
    def api_key_fmp() -> Optional[str]:
        return os.getenv("API_KEY_FMP")
    
    @staticmethod
    def api_key_eodhd() -> Optional[str]:
        return os.getenv("API_KEY_EODHD")
    
    # ==================== DASHBOARD ====================
    
    @staticmethod
    def dashboard_secret_key() -> str:
        """Chave secreta para JWT (sensível)."""
        return os.getenv("DASHBOARD_SECRET_KEY", "virtus-secret-key-change-in-production")
    
    @staticmethod
    def dashboard_admin_password() -> Optional[str]:
        """Senha do admin do dashboard."""
        return os.getenv("DASHBOARD_ADMIN_PASSWORD")
    
    # ==================== AMBIENTE ====================
    
    @staticmethod
    def environment() -> str:
        """Ambiente atual: development, staging, production."""
        return os.getenv("ENVIRONMENT", "development")
    
    @staticmethod
    def is_production() -> bool:
        """Verifica se está em produção."""
        return EnvConfig.environment() == "production"
    
    @staticmethod
    def debug() -> bool:
        """Modo debug."""
        return os.getenv("DEBUG", "true").lower() == "true"
    
    # ==================== HELPERS ====================
    
    @staticmethod
    def get_or_default(env_var: str, default: str) -> str:
        """Obtém variável de ambiente ou retorna default."""
        return os.getenv(env_var, default)
    
    @staticmethod
    def require(env_var: str) -> str:
        """Obtém variável obrigatória ou levanta erro."""
        value = os.getenv(env_var)
        if not value:
            raise EnvironmentError(f"Variável de ambiente obrigatória não definida: {env_var}")
        return value


# Instância global para fácil acesso
env = EnvConfig()
