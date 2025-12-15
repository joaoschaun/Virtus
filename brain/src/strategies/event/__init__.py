"""VIRTUS Event Strategy Module
=============================

Estratégia de event trading com 5 setups.
"""

# New advanced strategy
from .event_strategy import (
    EventStrategy,
    EventSetup,
    EventConfig,
)

__all__ = [
    'EventStrategy',
    'EventSetup',
    'EventConfig',
]
