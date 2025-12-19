"""
VIRTUS - Routes para Sistema de Auditoria
==========================================

Endpoints REST para consulta de logs de auditoria.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

# Adiciona path do src
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

router = APIRouter(prefix="/audit", tags=["Audit"])

# Import do módulo de auditoria
try:
    from src.core.audit import audit_log, AuditCategory
    AUDIT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Audit module not available: {e}")
    AUDIT_AVAILABLE = False


@router.get("/status")
async def get_audit_status():
    """Retorna status do sistema de auditoria."""
    if not AUDIT_AVAILABLE:
        return {"available": False, "message": "Sistema de Auditoria não disponível"}
    
    stats = audit_log.get_stats()
    return {
        "available": True,
        "db_path": str(audit_log.db_path),
        "stats": stats,
    }


@router.get("/logs")
async def get_audit_logs(
    category: Optional[str] = Query(None, description="Categoria: TRADE, CONFIG, AUTH, SYSTEM, RISK, BOT, API, ERROR"),
    user: Optional[str] = Query(None, description="Usuário"),
    start_date: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Consulta logs de auditoria.
    
    Filtros disponíveis:
    - category: Categoria do log (TRADE, CONFIG, AUTH, etc)
    - user: Usuário que executou a ação
    - start_date/end_date: Período
    - limit: Máximo de registros
    """
    if not AUDIT_AVAILABLE:
        raise HTTPException(503, "Sistema de Auditoria não disponível")
    
    # Parse datas
    start = None
    end = None
    try:
        if start_date:
            start = datetime.fromisoformat(start_date)
        if end_date:
            end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(400, "Formato de data inválido. Use YYYY-MM-DD")
    
    # Parse categoria
    cat = None
    if category:
        try:
            cat = AuditCategory(category.upper())
        except ValueError:
            raise HTTPException(400, f"Categoria inválida: {category}")
    
    # Consulta logs
    logs = audit_log.query(
        category=cat,
        user=user,
        start_date=start,
        end_date=end,
        limit=limit,
    )
    
    return {
        "count": len(logs),
        "logs": logs,
    }


@router.get("/stats")
async def get_audit_stats():
    """Retorna estatísticas do sistema de auditoria."""
    if not AUDIT_AVAILABLE:
        raise HTTPException(503, "Sistema de Auditoria não disponível")
    
    return audit_log.get_stats()


@router.get("/trades")
async def get_trade_audit_logs(
    limit: int = Query(50, ge=1, le=500),
):
    """Logs de auditoria específicos de trades."""
    if not AUDIT_AVAILABLE:
        raise HTTPException(503, "Sistema de Auditoria não disponível")
    
    logs = audit_log.query(
        category=AuditCategory.TRADE,
        limit=limit,
    )
    
    return {
        "count": len(logs),
        "logs": logs,
    }


@router.get("/auth")
async def get_auth_audit_logs(
    limit: int = Query(50, ge=1, le=500),
):
    """Logs de auditoria de autenticação."""
    if not AUDIT_AVAILABLE:
        raise HTTPException(503, "Sistema de Auditoria não disponível")
    
    logs = audit_log.query(
        category=AuditCategory.AUTH,
        limit=limit,
    )
    
    return {
        "count": len(logs),
        "logs": logs,
    }


@router.get("/config")
async def get_config_audit_logs(
    limit: int = Query(50, ge=1, le=500),
):
    """Logs de auditoria de alterações de configuração."""
    if not AUDIT_AVAILABLE:
        raise HTTPException(503, "Sistema de Auditoria não disponível")
    
    logs = audit_log.query(
        category=AuditCategory.CONFIG,
        limit=limit,
    )
    
    return {
        "count": len(logs),
        "logs": logs,
    }


@router.post("/cleanup")
async def cleanup_old_logs(
    days: int = Query(90, ge=7, le=365, description="Manter logs dos últimos N dias"),
):
    """Remove logs antigos."""
    if not AUDIT_AVAILABLE:
        raise HTTPException(503, "Sistema de Auditoria não disponível")
    
    deleted = audit_log.cleanup(days)
    
    return {
        "message": f"Limpeza concluída",
        "deleted_count": deleted,
        "retention_days": days,
    }
