"""
BRAIN - Cache Policy
Políticas de cache e TTL
"""

from enum import Enum
from typing import Dict


class CachePolicy(Enum):
    """Políticas de cache pré-definidas"""
    
    # Dados em tempo real (curto TTL)
    REALTIME = 30  # 30 segundos
    
    # Notícias (médio TTL)
    NEWS = 900  # 15 minutos
    
    # Sentimento (médio TTL)
    SENTIMENT = 600  # 10 minutos
    
    # Calendário econômico (longo TTL)
    CALENDAR = 3600  # 1 hora
    
    # COT Reports (muito longo TTL)
    COT = 86400  # 1 dia
    
    # Macro context (longo TTL)
    MACRO = 3600  # 1 hora
    
    # Análise técnica (curto TTL)
    TECHNICAL = 60  # 1 minuto
    
    # Configurações (muito longo TTL)
    CONFIG = 86400  # 1 dia


def get_ttl(data_type: str) -> int:
    """
    Retorna TTL em segundos para um tipo de dado
    
    Args:
        data_type: Tipo de dado ("news", "sentiment", etc.)
        
    Returns:
        TTL em segundos
    """
    ttl_map: Dict[str, int] = {
        "news": CachePolicy.NEWS.value,
        "sentiment": CachePolicy.SENTIMENT.value,
        "calendar": CachePolicy.CALENDAR.value,
        "cot": CachePolicy.COT.value,
        "macro": CachePolicy.MACRO.value,
        "technical": CachePolicy.TECHNICAL.value,
        "realtime": CachePolicy.REALTIME.value,
        "config": CachePolicy.CONFIG.value
    }
    
    return ttl_map.get(data_type, 300)  # Default: 5 minutos
