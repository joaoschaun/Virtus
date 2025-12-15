"""VIRTUS Positions Module
========================

Gerenciamento de posições com:
- Position Manager: Gerenciamento completo de posições
- Position Monitor: Monitoramento em tempo real com trailing/breakeven
- Exit Manager: 8 tipos de trailing stop, saídas parciais
- Position Supervisor: Health check e alertas
"""

from .position_manager import (
    PositionManager,
    PositionRecord,
    PositionMetrics,
    PositionEvent,
    create_position_manager
)
from .position_monitor import (
    PositionMonitor,
    MonitorConfig,
    MonitorAlert,
    AlertLevel,
    AlertRecord,
    create_position_monitor
)
from .position_state import PositionState, StateType

# Exit Manager
try:
    from .exits.exit_manager import (
        ExitManager,
        TrailingStopType,
        ExitReason,
        TrailingStopConfig,
        PartialExitConfig,
    )
except ImportError:
    pass

# Trailing Stop
try:
    from .exits.trailing_stop import (
        TrailingStop,
        TrailingStopType,
        TrailingStopConfig,
        TrailingStopState,
    )
except ImportError:
    TrailingStop = None

# Position Supervisor
try:
    from .supervisor.position_supervisor import (
        PositionSupervisor,
        PositionHealth,
        BreakEvenConfig,
        PositionInfo,
        SupervisorAlert,
        AlertType,
    )
except ImportError:
    pass

__all__ = [
    # Position Manager
    'PositionManager',
    'PositionRecord',
    'PositionMetrics',
    'PositionEvent',
    'create_position_manager',
    
    # Position Monitor
    'PositionMonitor',
    'MonitorConfig',
    'MonitorAlert',
    'AlertLevel',
    'AlertRecord',
    'create_position_monitor',
    
    # Trailing Stop
    'TrailingStop',
    'TrailingStopType',
    'TrailingStopConfig',
    
    # Exit Manager
    'ExitManager',
    'ExitReason',
    
    # State
    'PositionState',
    'StateType',
]
