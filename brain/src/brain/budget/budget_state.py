"""
BRAIN - Budget State
Estado persistente do budget
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Any


@dataclass
class ProviderUsage:
    """Uso de um provider"""
    daily_used: int = 0
    monthly_used: int = 0
    minute_used: int = 0
    last_minute: str = ""
    last_request: str = ""


@dataclass
class BudgetState:
    """Estado completo do budget"""
    last_reset_date: date = field(default_factory=date.today)
    providers: Dict[str, ProviderUsage] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "last_reset_date": self.last_reset_date.isoformat(),
            "providers": {
                name: {
                    "daily_used": usage.daily_used,
                    "monthly_used": usage.monthly_used,
                    "minute_used": usage.minute_used,
                    "last_minute": usage.last_minute,
                    "last_request": usage.last_request
                }
                for name, usage in self.providers.items()
            },
            "updated_at": datetime.now().isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BudgetState":
        """Cria a partir de dicionário"""
        state = cls()
        
        if "last_reset_date" in data:
            state.last_reset_date = datetime.strptime(
                data["last_reset_date"], "%Y-%m-%d"
            ).date()
        
        for name, usage_data in data.get("providers", {}).items():
            state.providers[name] = ProviderUsage(
                daily_used=usage_data.get("daily_used", 0),
                monthly_used=usage_data.get("monthly_used", 0),
                minute_used=usage_data.get("minute_used", 0),
                last_minute=usage_data.get("last_minute", ""),
                last_request=usage_data.get("last_request", "")
            )
        
        return state
