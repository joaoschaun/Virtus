"""
VIRTUS Dashboard - MT5 Account Routes
======================================

API para integração com conta MT5 real.
Métricas, histórico, depósitos, equity, etc.
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

from services.mt5_account_service import (
    get_mt5_account_service, 
    MT5AccountService,
    AccountInfo,
    AccountMetrics
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mt5-account", tags=["MT5 Account"])


# ==================== MODELOS ====================

class ConnectRequest(BaseModel):
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None


class StatusResponse(BaseModel):
    connected: bool
    mt5_available: bool
    message: str
    account: Optional[Dict] = None


# ==================== ROTAS ====================

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Verifica status da conexão MT5.
    
    Returns:
        StatusResponse: Status da conexão e info da conta se conectado
    """
    service = get_mt5_account_service()
    
    if not service.is_available:
        return StatusResponse(
            connected=False,
            mt5_available=False,
            message="MetaTrader5 não está instalado neste servidor"
        )
    
    if not service.is_connected:
        # Tenta conectar automaticamente
        success, msg = service.connect()
        if not success:
            return StatusResponse(
                connected=False,
                mt5_available=True,
                message=msg
            )
    
    account = service.get_account_info()
    return StatusResponse(
        connected=True,
        mt5_available=True,
        message="Conectado",
        account=account.to_dict() if account else None
    )


@router.post("/connect")
async def connect(request: ConnectRequest):
    """
    Conecta ao MT5.
    
    Se credenciais não fornecidas, tenta usar a conta já logada no terminal.
    """
    service = get_mt5_account_service()
    
    if not service.is_available:
        raise HTTPException(status_code=503, detail="MetaTrader5 não está instalado")
    
    success, message = service.connect(
        login=request.login,
        password=request.password,
        server=request.server
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    account = service.get_account_info()
    return {
        "success": True,
        "message": message,
        "account": account.to_dict() if account else None
    }


@router.post("/disconnect")
async def disconnect():
    """Desconecta do MT5."""
    service = get_mt5_account_service()
    service.disconnect()
    return {"success": True, "message": "Desconectado"}


@router.get("/account")
async def get_account():
    """
    Retorna informações da conta.
    
    Returns:
        Dict: Informações da conta (balance, equity, margin, etc)
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    account = service.get_account_info()
    if account is None:
        raise HTTPException(status_code=503, detail="Não conectado ao MT5")
    
    return {
        "success": True,
        "data": account.to_dict()
    }


@router.get("/metrics")
async def get_metrics(days: int = Query(365, ge=1, le=3650)):
    """
    Retorna métricas completas da conta.
    
    Args:
        days: Período em dias para calcular métricas (padrão: 365)
    
    Returns:
        Dict: Métricas completas (win rate, drawdown, profit factor, etc)
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    if not service.is_connected:
        raise HTTPException(status_code=503, detail="Não conectado ao MT5")
    
    try:
        metrics = service.calculate_metrics(days)
        return {
            "success": True,
            "period_days": days,
            "data": metrics.to_dict()
        }
    except Exception as e:
        logger.error(f"Erro ao calcular métricas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions():
    """
    Retorna posições abertas.
    
    Returns:
        List: Lista de posições abertas
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    positions = service.get_open_positions()
    return {
        "success": True,
        "count": len(positions),
        "data": positions
    }


@router.get("/orders")
async def get_pending_orders():
    """
    Retorna ordens pendentes.
    
    Returns:
        List: Lista de ordens pendentes
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    orders = service.get_pending_orders()
    return {
        "success": True,
        "count": len(orders),
        "data": orders
    }


@router.get("/trades")
async def get_trades(
    days: int = Query(30, ge=1, le=3650),
    symbol: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Retorna histórico de trades.
    
    Args:
        days: Período em dias (padrão: 30)
        symbol: Filtrar por símbolo (opcional)
        limit: Limite de trades retornados (padrão: 100)
    
    Returns:
        List: Lista de trades
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    trades = service.get_trades_only(days)
    
    # Filtrar por símbolo se especificado
    if symbol:
        trades = [t for t in trades if t.symbol == symbol.upper()]
    
    # Ordenar por data (mais recentes primeiro)
    trades.sort(key=lambda t: t.time, reverse=True)
    
    # Limitar
    trades = trades[:limit]
    
    return {
        "success": True,
        "period_days": days,
        "count": len(trades),
        "data": [t.to_dict() for t in trades]
    }


@router.get("/deposits-withdrawals")
async def get_deposits_withdrawals(days: int = Query(365, ge=1, le=3650)):
    """
    Retorna histórico de depósitos e saques.
    
    Args:
        days: Período em dias (padrão: 365)
    
    Returns:
        Dict: Lista de depósitos/saques e totais
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    operations = service.get_deposits_withdrawals(days)
    
    total_deposits = sum(op.amount for op in operations if op.type == "DEPOSIT")
    total_withdrawals = sum(op.amount for op in operations if op.type == "WITHDRAWAL")
    
    return {
        "success": True,
        "period_days": days,
        "summary": {
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "net": total_deposits - total_withdrawals
        },
        "count": len(operations),
        "data": [op.to_dict() for op in operations]
    }


@router.get("/daily-stats")
async def get_daily_stats(days: int = Query(30, ge=1, le=365)):
    """
    Retorna estatísticas diárias.
    
    Args:
        days: Período em dias (padrão: 30)
    
    Returns:
        List: Estatísticas por dia
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    stats = service.get_daily_stats(days)
    
    return {
        "success": True,
        "period_days": days,
        "count": len(stats),
        "data": [s.to_dict() for s in stats]
    }


@router.get("/symbol-stats")
async def get_symbol_stats(days: int = Query(365, ge=1, le=3650)):
    """
    Retorna estatísticas por símbolo.
    
    Args:
        days: Período em dias (padrão: 365)
    
    Returns:
        Dict: Estatísticas agrupadas por símbolo
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    stats = service.get_symbol_stats(days)
    
    return {
        "success": True,
        "period_days": days,
        "symbols": len(stats),
        "data": stats
    }


@router.get("/summary")
async def get_account_summary():
    """
    Retorna resumo completo da conta em uma única chamada.
    
    Ideal para dashboard - retorna tudo de uma vez.
    
    Returns:
        Dict: Resumo completo com account, metrics, positions, etc
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        success, msg = service.connect()
        if not success:
            raise HTTPException(status_code=503, detail=msg)
    
    try:
        account = service.get_account_info()
        metrics = service.calculate_metrics(365)
        positions = service.get_open_positions()
        orders = service.get_pending_orders()
        daily_stats = service.get_daily_stats(30)
        symbol_stats = service.get_symbol_stats(365)
        deposits = service.get_deposits_withdrawals(365)
        
        total_deposits = sum(op.amount for op in deposits if op.type == "DEPOSIT")
        total_withdrawals = sum(op.amount for op in deposits if op.type == "WITHDRAWAL")
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "account": account.to_dict() if account else None,
            "metrics": metrics.to_dict(),
            "positions": {
                "count": len(positions),
                "total_profit": sum(p['profit'] for p in positions),
                "data": positions
            },
            "pending_orders": {
                "count": len(orders),
                "data": orders
            },
            "deposits_withdrawals": {
                "total_deposits": total_deposits,
                "total_withdrawals": total_withdrawals,
                "net": total_deposits - total_withdrawals
            },
            "daily_performance": {
                "count": len(daily_stats),
                "data": [s.to_dict() for s in daily_stats[-7:]]  # Últimos 7 dias
            },
            "symbols": {
                "count": len(symbol_stats),
                "top_5": dict(sorted(
                    symbol_stats.items(), 
                    key=lambda x: x[1]['profit'], 
                    reverse=True
                )[:5])
            }
        }
    except Exception as e:
        logger.error(f"Erro ao gerar resumo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_data():
    """
    Exporta todos os dados para arquivo JSON.
    
    Returns:
        Dict: Path do arquivo exportado
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    if not service.is_connected:
        raise HTTPException(status_code=503, detail="Não conectado ao MT5")
    
    try:
        filepath = service.export_to_json()
        return {
            "success": True,
            "message": "Dados exportados com sucesso",
            "file": filepath
        }
    except Exception as e:
        logger.error(f"Erro ao exportar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equity-history")
async def get_equity_history(days: int = Query(30, ge=1, le=365)):
    """
    Retorna histórico de equity (aproximado baseado em trades).
    
    Args:
        days: Período em dias (padrão: 30)
    
    Returns:
        List: Evolução do equity dia a dia
    """
    service = get_mt5_account_service()
    
    if not service.is_connected:
        service.connect()
    
    if not service.is_connected:
        raise HTTPException(status_code=503, detail="Não conectado ao MT5")
    
    # Buscar depósitos e trades
    deposits = service.get_deposits_withdrawals(days)
    trades = service.get_trades_only(days)
    
    # Calcular equity inicial (depósitos - saques antes do período)
    all_deposits = service.get_deposits_withdrawals(3650)  # Todos
    initial_balance = sum(d.amount if d.type == "DEPOSIT" else -d.amount for d in all_deposits)
    
    # Subtrair lucro das trades do período para obter balance inicial do período
    period_profit = sum(t.profit + t.swap + t.commission for t in trades)
    account = service.get_account_info()
    if account:
        initial_balance = account.balance - period_profit
    
    # Construir histórico dia a dia
    from datetime import timedelta
    history = []
    current_balance = initial_balance
    
    # Agrupar trades e depósitos por dia
    from collections import defaultdict
    daily_changes = defaultdict(lambda: {'trades_profit': 0, 'deposits': 0, 'withdrawals': 0})
    
    for trade in trades:
        date_str = trade.time.strftime("%Y-%m-%d")
        daily_changes[date_str]['trades_profit'] += trade.profit + trade.swap + trade.commission
    
    for dep in deposits:
        date_str = dep.time.strftime("%Y-%m-%d")
        if dep.type == "DEPOSIT":
            daily_changes[date_str]['deposits'] += dep.amount
        else:
            daily_changes[date_str]['withdrawals'] += dep.amount
    
    # Gerar série temporal
    from datetime import date
    start_date = date.today() - timedelta(days=days)
    
    for i in range(days + 1):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        changes = daily_changes.get(date_str, {'trades_profit': 0, 'deposits': 0, 'withdrawals': 0})
        current_balance += changes['trades_profit'] + changes['deposits'] - changes['withdrawals']
        
        history.append({
            'date': date_str,
            'equity': round(current_balance, 2),
            'profit': round(changes['trades_profit'], 2),
            'deposits': round(changes['deposits'], 2),
            'withdrawals': round(changes['withdrawals'], 2)
        })
    
    return {
        "success": True,
        "period_days": days,
        "count": len(history),
        "data": history
    }
