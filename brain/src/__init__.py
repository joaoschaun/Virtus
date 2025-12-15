"""
VIRTUS - Sistema Multi-Bot de Trading
=====================================

Arquitetura:
- Brain Central: Gerenciamento de APIs, cache e dados compartilhados
- Bots Independentes: Um bot por símbolo (XAUUSD, EURUSD, GBPUSD)
- Orquestrador: Coordenação e supervisão dos bots
- Advisor: Relatórios e análises de mercado em português

Autor: joaoschaun
Versão: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "joaoschaun"

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.config import Config
    from .brain.brain_service import BrainService
    from .orchestrator.bot_orchestrator import BotOrchestrator
