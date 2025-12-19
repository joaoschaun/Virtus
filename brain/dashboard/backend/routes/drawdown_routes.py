"""
VIRTUS - Routes para Drawdown Monitor
======================================

Endpoints REST para monitoramento de drawdown.
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

# Adiciona path do src
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

router = APIRouter(prefix="/drawdown", tags=["Drawdown Monitor"])

# Import do módulo de drawdown
try:
    from src.monitoring.drawdown_alert import drawdown_monitor, DrawdownThreshold, AlertLevel, AlertAction
    DRAWDOWN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Drawdown Monitor module not available: {e}")
    DRAWDOWN_AVAILABLE = False


class ThresholdConfig(BaseModel):
    caution: float = 2.0
    warning: float = 5.0
    critical: float = 10.0
    emergency: float = 15.0


@router.get("/status")
async def get_drawdown_status():
    """Retorna status atual do drawdown."""
    if not DRAWDOWN_AVAILABLE:
        return {"available": False, "message": "Drawdown Monitor não disponível"}
    
    current_level = "unknown"
    if drawdown_monitor.state:
        current_level = drawdown_monitor.state.current_level.value
    
    return {
        "available": True,
        "running": drawdown_monitor._running,
        "state": drawdown_monitor.state.to_dict() if drawdown_monitor.state else None,
        "alert_level": current_level,
    }


@router.post("/start")
async def start_drawdown_monitor():
    """Inicia o monitoramento de drawdown."""
    if not DRAWDOWN_AVAILABLE:
        raise HTTPException(503, "Drawdown Monitor não disponível")
    
    await drawdown_monitor.start()
    return {"message": "Drawdown Monitor iniciado"}


@router.post("/stop")
async def stop_drawdown_monitor():
    """Para o monitoramento de drawdown."""
    if not DRAWDOWN_AVAILABLE:
        raise HTTPException(503, "Drawdown Monitor não disponível")
    
    await drawdown_monitor.stop()
    return {"message": "Drawdown Monitor parado"}


@router.get("/state")
async def get_drawdown_state():
    """Retorna estado atual do drawdown."""
    if not DRAWDOWN_AVAILABLE:
        raise HTTPException(503, "Drawdown Monitor não disponível")
    
    if not drawdown_monitor.state:
        return {"message": "Estado não disponível"}
    
    return drawdown_monitor.state.to_dict()


@router.get("/alerts")
async def get_drawdown_alerts(limit: int = Query(50, ge=1, le=200)):
    """Retorna histórico de alertas."""
    if not DRAWDOWN_AVAILABLE:
        raise HTTPException(503, "Drawdown Monitor não disponível")
    
    alerts = [a.to_dict() for a in drawdown_monitor._alert_history[-limit:]]
    return {
        "count": len(alerts),
        "alerts": alerts,
    }


@router.get("/thresholds")
async def get_thresholds():
    """Retorna configuração de thresholds."""
    if not DRAWDOWN_AVAILABLE:
        raise HTTPException(503, "Drawdown Monitor não disponível")
    
    return {
        "thresholds": [t.to_dict() for t in drawdown_monitor.thresholds],
    }


@router.post("/thresholds")
async def update_thresholds(config: ThresholdConfig):
    """Atualiza configuração de thresholds."""
    if not DRAWDOWN_AVAILABLE:
        raise HTTPException(503, "Drawdown Monitor não disponível")
    
    # Atualiza thresholds
    drawdown_monitor.thresholds = [
        DrawdownThreshold(
            level=AlertLevel.CAUTION,
            percentage=config.caution,
            actions=[AlertAction.NOTIFY],
            message=f"Drawdown atingiu {config.caution}%"
        ),
        DrawdownThreshold(
            level=AlertLevel.WARNING,
            percentage=config.warning,
            actions=[AlertAction.NOTIFY, AlertAction.REDUCE_RISK],
            message=f"Drawdown atingiu {config.warning}% - Reduzindo risco"
        ),
        DrawdownThreshold(
            level=AlertLevel.CRITICAL,
            percentage=config.critical,
            actions=[AlertAction.NOTIFY, AlertAction.PAUSE_NEW_TRADES],
            message=f"CRÍTICO: Drawdown atingiu {config.critical}% - Pausando novos trades"
        ),
        DrawdownThreshold(
            level=AlertLevel.EMERGENCY,
            percentage=config.emergency,
            actions=[AlertAction.NOTIFY, AlertAction.CLOSE_ALL],
            message=f"EMERGÊNCIA: Drawdown atingiu {config.emergency}% - Fechando todas as posições"
        ),
    ]
    
    return {
        "message": "Thresholds atualizados",
        "thresholds": [t.to_dict() for t in drawdown_monitor.thresholds],
    }


@router.post("/reset-peak")
async def reset_peak_balance():
    """Reseta o pico de balance para o valor atual."""
    if not DRAWDOWN_AVAILABLE:
        raise HTTPException(503, "Drawdown Monitor não disponível")
    
    if drawdown_monitor.state:
        drawdown_monitor.state.peak_balance = drawdown_monitor.state.current_balance
        drawdown_monitor.state.current_drawdown = 0.0
        drawdown_monitor.state.drawdown_percentage = 0.0
        drawdown_monitor._current_level = AlertLevel.NORMAL
        
        return {
            "message": "Pico resetado",
            "new_peak": drawdown_monitor.state.peak_balance,
        }
    
    return {"message": "Estado não disponível"}
