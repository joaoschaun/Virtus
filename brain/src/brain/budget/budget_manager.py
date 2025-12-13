"""
BRAIN - Budget Manager
Gerenciador de budget de APIs
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Optional
from threading import Lock

from ...core.logger import get_logger
from ...core.config import BASE_DIR
from ...core.exceptions import BudgetExceededError

logger = get_logger("brain.budget")


# Arquivo de estado do budget
BUDGET_STATE_FILE = BASE_DIR / "data" / "brain" / "budget_state.json"


class BudgetManager:
    """
    Gerenciador de Budget de APIs
    
    Controla o uso de APIs pagas/limitadas:
    - Limite diário
    - Limite mensal
    - Rate limiting por minuto
    - Persistência de estado
    """
    
    def __init__(self, budget_config: Dict[str, Any]):
        self._config = budget_config
        self._lock = Lock()
        
        # Estado de uso
        self._usage: Dict[str, Dict[str, Any]] = {}
        self._last_reset_date: Optional[date] = None
        
        # Carregar estado persistido
        self._load_state()
        
        # Resetar se mudou o dia
        self._check_daily_reset()
    
    def _load_state(self):
        """Carrega estado do arquivo"""
        try:
            if BUDGET_STATE_FILE.exists():
                with open(BUDGET_STATE_FILE, "r") as f:
                    data = json.load(f)
                    self._usage = data.get("usage", {})
                    reset_str = data.get("last_reset_date")
                    if reset_str:
                        self._last_reset_date = datetime.strptime(reset_str, "%Y-%m-%d").date()
                logger.debug("📊 Estado do budget carregado")
        except Exception as e:
            logger.error(f"Erro ao carregar estado do budget: {e}")
            self._usage = {}
    
    def _save_state(self):
        """Salva estado no arquivo"""
        try:
            BUDGET_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "usage": self._usage,
                "last_reset_date": self._last_reset_date.isoformat() if self._last_reset_date else None,
                "updated_at": datetime.now().isoformat()
            }
            
            with open(BUDGET_STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar estado do budget: {e}")
    
    def _check_daily_reset(self):
        """Verifica se precisa resetar contadores diários"""
        today = date.today()
        
        if self._last_reset_date != today:
            logger.info("📊 Resetando contadores diários de budget")
            
            for provider in self._usage:
                self._usage[provider]["daily_used"] = 0
                self._usage[provider]["minute_used"] = 0
                self._usage[provider]["last_minute"] = None
            
            self._last_reset_date = today
            self._save_state()
    
    def _get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Obtém configuração de um provider"""
        return self._config.get(provider, {})
    
    def _get_usage(self, provider: str) -> Dict[str, Any]:
        """Obtém ou inicializa uso de um provider"""
        if provider not in self._usage:
            self._usage[provider] = {
                "daily_used": 0,
                "monthly_used": 0,
                "minute_used": 0,
                "last_minute": None,
                "last_request": None
            }
        return self._usage[provider]
    
    def can_use(self, provider: str) -> bool:
        """
        Verifica se pode usar um provider
        
        Args:
            provider: Nome do provider ("forexnews", "finnhub", etc.)
            
        Returns:
            True se pode usar, False caso contrário
        """
        with self._lock:
            config = self._get_provider_config(provider)
            usage = self._get_usage(provider)
            
            # Verificar limite diário
            daily_limit = config.get("daily_limit", float("inf"))
            if usage["daily_used"] >= daily_limit:
                logger.warning(f"⚠️ Limite diário atingido para {provider}")
                return False
            
            # Verificar rate limit por minuto
            rpm_limit = config.get("requests_per_minute", float("inf"))
            current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            if usage["last_minute"] != current_minute:
                usage["minute_used"] = 0
                usage["last_minute"] = current_minute
            
            if usage["minute_used"] >= rpm_limit:
                logger.debug(f"⏳ Rate limit atingido para {provider}")
                return False
            
            return True
    
    def record_usage(self, provider: str, count: int = 1):
        """
        Registra uso de um provider
        
        Args:
            provider: Nome do provider
            count: Número de requisições (default: 1)
        """
        with self._lock:
            usage = self._get_usage(provider)
            
            usage["daily_used"] += count
            usage["monthly_used"] += count
            usage["minute_used"] += count
            usage["last_request"] = datetime.now().isoformat()
            
            current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
            if usage["last_minute"] != current_minute:
                usage["minute_used"] = count
                usage["last_minute"] = current_minute
            
            self._save_state()
            
            logger.debug(f"📊 {provider}: {usage['daily_used']} requisições hoje")
    
    def get_remaining(self, provider: str) -> Dict[str, int]:
        """
        Retorna limites restantes de um provider
        
        Returns:
            Dict com limites restantes
        """
        with self._lock:
            config = self._get_provider_config(provider)
            usage = self._get_usage(provider)
            
            daily_limit = config.get("daily_limit", 0)
            monthly_limit = config.get("monthly_limit", 0)
            rpm_limit = config.get("requests_per_minute", 0)
            
            return {
                "daily_remaining": max(0, daily_limit - usage["daily_used"]),
                "monthly_remaining": max(0, monthly_limit - usage["monthly_used"]),
                "minute_remaining": max(0, rpm_limit - usage.get("minute_used", 0))
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do budget"""
        with self._lock:
            status = {
                "date": date.today().isoformat(),
                "providers": {}
            }
            
            for provider in self._config:
                config = self._get_provider_config(provider)
                usage = self._get_usage(provider)
                
                daily_limit = config.get("daily_limit", 0)
                monthly_limit = config.get("monthly_limit", 0)
                
                status["providers"][provider] = {
                    "daily_limit": daily_limit,
                    "daily_used": usage.get("daily_used", 0),
                    "daily_remaining": max(0, daily_limit - usage.get("daily_used", 0)),
                    "monthly_limit": monthly_limit,
                    "monthly_used": usage.get("monthly_used", 0),
                    "monthly_remaining": max(0, monthly_limit - usage.get("monthly_used", 0)),
                    "priority": config.get("priority", "normal"),
                    "last_request": usage.get("last_request")
                }
            
            return status
    
    def reset_daily(self):
        """Força reset dos contadores diários"""
        with self._lock:
            for provider in self._usage:
                self._usage[provider]["daily_used"] = 0
                self._usage[provider]["minute_used"] = 0
            
            self._last_reset_date = date.today()
            self._save_state()
            logger.info("📊 Contadores diários resetados")
    
    def reset_monthly(self):
        """Força reset dos contadores mensais"""
        with self._lock:
            for provider in self._usage:
                self._usage[provider]["monthly_used"] = 0
            
            self._save_state()
            logger.info("📊 Contadores mensais resetados")
