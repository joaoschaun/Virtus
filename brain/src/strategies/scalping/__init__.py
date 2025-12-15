"""VIRTUS Scalping Strategy Module
================================

Estratégia de scalping com 9 setups de microestrutura.
"""

# Legacy
try:
    from .scalping import ScalpingStrategy as LegacyScalpingStrategy
    from .adaptive_scalping import AdaptiveScalpingStrategy
except ImportError:
    pass

# New advanced strategy
from .scalping_strategy import (
    ScalpingStrategy,
    ScalpingSetup,
    ScalpingConfig,
)

__all__ = [
    'ScalpingStrategy',
    'ScalpingSetup',
    'ScalpingConfig',
]
