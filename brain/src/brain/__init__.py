"""
VIRTUS Brain Module
===================

Serviço centralizado de dados e análises.
Coração do sistema VIRTUS - fornece dados unificados para todos os bots.
"""

from .brain_service import BrainService, get_brain
from .cache import CacheManager, get_cache_manager, cached
from .budget import BudgetManager, get_budget_manager
from .providers import (
    ForexNewsProvider,
    FinnhubProvider,
    TwelveDataProvider,
    FMPProvider
)

__all__ = [
    # Service
    'BrainService',
    'get_brain',
    
    # Cache
    'CacheManager',
    'get_cache_manager',
    'cached',
    
    # Budget
    'BudgetManager',
    'get_budget_manager',
    
    # Providers
    'ForexNewsProvider',
    'FinnhubProvider',
    'TwelveDataProvider',
    'FMPProvider',
]
