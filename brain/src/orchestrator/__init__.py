"""
VIRTUS Orchestrator Module
===========================

Orquestrador central de bots de trading.
"""

from .bot_orchestrator import (
    BotOrchestrator,
    BotRegistry,
    BotSupervisor,
    get_orchestrator,
)

__all__ = [
    'BotOrchestrator',
    'BotRegistry',
    'BotSupervisor',
    'get_orchestrator',
]
