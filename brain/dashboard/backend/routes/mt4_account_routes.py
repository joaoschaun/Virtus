"""
MT4 Account Routes - API para conta real MetaTrader 4

Endpoints para gerenciar dados da conta MT4.
Como MT4 não tem API Python oficial, suporta:
1. Importação manual de CSV/JSON do histórico
2. Entrada manual de dados
3. Conexão ZeroMQ (se EA estiver instalado)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import tempfile
import os

from services.mt4_account_service import get_mt4_service, MT4AccountService

router = APIRouter(prefix="/api/mt4-account", tags=["MT4 Account"])


class AccountInfoInput(BaseModel):
    """Input para configurar informações da conta"""
    login: int
    name: str
    server: str = "Pepperstone-Live"
    currency: str = "USD"
    balance: float
    equity: Optional[float] = None
    leverage: int = 100
    company: str = "Pepperstone"


class DepositInput(BaseModel):
    """Input para adicionar depósito"""
    amount: float
    date: Optional[str] = None
    comment: str = ""


class WithdrawalInput(BaseModel):
    """Input para adicionar saque"""
    amount: float
    date: Optional[str] = None
    comment: str = ""


class BalanceUpdateInput(BaseModel):
    """Input para atualizar saldo"""
    balance: float
    equity: Optional[float] = None


class TradeInput(BaseModel):
    """Input para adicionar trade manualmente"""
    ticket: int
    symbol: str
    type: str  # BUY ou SELL
    volume: float
    open_price: float
    close_price: float
    open_time: str
    close_time: str
    profit: float
    swap: float = 0
    commission: float = 0
    sl: float = 0
    tp: float = 0
    comment: str = ""


@router.get("/status")
async def get_status():
    """Obtém o status da conexão MT4"""
    service = get_mt4_service()
    account = service.get_account_info()
    
    return {
        "connected": service.is_connected(),
        "mode": service._mode,
        "has_data": account is not None,
        "message": "Dados configurados" if account else "Aguardando configuração",
        "account": {
            "login": account.login if account else None,
            "name": account.name if account else None,
            "server": account.server if account else None,
            "currency": account.currency if account else None,
            "balance": account.balance if account else None,
            "equity": account.equity if account else None,
            "leverage": account.leverage if account else None
        } if account else None
    }


@router.post("/setup")
async def setup_account(data: AccountInfoInput):
    """
    Configura informações da conta MT4.
    
    Use este endpoint para configurar manualmente os dados da conta.
    """
    service = get_mt4_service()
    
    service.set_account_info({
        "login": data.login,
        "name": data.name,
        "server": data.server,
        "currency": data.currency,
        "balance": data.balance,
        "equity": data.equity or data.balance,
        "margin": 0,
        "free_margin": data.balance,
        "margin_level": 0,
        "profit": 0,
        "leverage": data.leverage,
        "company": data.company
    })
    
    return {
        "success": True,
        "message": "Conta configurada com sucesso",
        "account": {
            "login": data.login,
            "name": data.name,
            "server": data.server
        }
    }


@router.post("/deposit")
async def add_deposit(data: DepositInput):
    """Adiciona um depósito"""
    service = get_mt4_service()
    service.add_deposit(data.amount, data.date, data.comment)
    
    return {
        "success": True,
        "message": f"Depósito de {data.amount} adicionado"
    }


@router.post("/withdrawal")
async def add_withdrawal(data: WithdrawalInput):
    """Adiciona um saque"""
    service = get_mt4_service()
    service.add_withdrawal(data.amount, data.date, data.comment)
    
    return {
        "success": True,
        "message": f"Saque de {data.amount} adicionado"
    }


@router.post("/update-balance")
async def update_balance(data: BalanceUpdateInput):
    """Atualiza o saldo atual"""
    service = get_mt4_service()
    service.update_balance(data.balance, data.equity)
    
    return {
        "success": True,
        "message": "Saldo atualizado"
    }


@router.post("/import/csv")
async def import_csv(file: UploadFile = File(...)):
    """
    Importa trades de um arquivo CSV exportado do MT4.
    
    Para exportar do MT4:
    1. Vá em Account History
    2. Clique direito → Save as Report (ou Save as Detailed Report)
    3. Salve como CSV
    """
    service = get_mt4_service()
    
    # Salvar arquivo temporário
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
        content = await file.read()
        f.write(content)
        temp_path = f.name
    
    try:
        count = service.import_trades_from_csv(temp_path)
        return {
            "success": True,
            "message": f"{count} trades importados com sucesso",
            "trades_imported": count
        }
    finally:
        os.unlink(temp_path)


@router.post("/import/json")
async def import_json(trades: List[TradeInput]):
    """
    Importa trades de dados JSON.
    
    Formato esperado:
    [
        {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": 0.1,
            "open_price": 1.1000,
            "close_price": 1.1050,
            "open_time": "2024-01-15 10:30:00",
            "close_time": "2024-01-15 14:45:00",
            "profit": 50.00,
            "swap": -0.50,
            "commission": -0.70
        }
    ]
    """
    service = get_mt4_service()
    
    trades_data = [t.dict() for t in trades]
    count = service.import_trades_from_json(trades_data)
    
    return {
        "success": True,
        "message": f"{count} trades importados",
        "trades_imported": count
    }


@router.post("/add-trade")
async def add_trade(trade: TradeInput):
    """Adiciona um trade manualmente"""
    service = get_mt4_service()
    
    count = service.import_trades_from_json([trade.dict()])
    
    return {
        "success": True,
        "message": "Trade adicionado"
    }


@router.get("/account")
async def get_account():
    """Obtém informações da conta"""
    service = get_mt4_service()
    account = service.get_account_info()
    
    if not account:
        return {
            "success": False,
            "message": "Conta não configurada. Use POST /api/mt4-account/setup primeiro."
        }
    
    return {
        "success": True,
        "data": {
            "login": account.login,
            "name": account.name,
            "server": account.server,
            "currency": account.currency,
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "free_margin": account.free_margin,
            "margin_level": account.margin_level,
            "profit": account.profit,
            "leverage": account.leverage,
            "company": account.company
        }
    }


@router.get("/metrics")
async def get_metrics(days: int = 30):
    """
    Obtém métricas calculadas.
    
    - days: Número de dias para calcular (0 = todos)
    """
    service = get_mt4_service()
    metrics = service.calculate_metrics(days)
    
    return {
        "success": True,
        "period_days": days,
        "data": {
            "balance": metrics.balance,
            "equity": metrics.equity,
            "profit": metrics.profit,
            "total_deposits": metrics.total_deposits,
            "total_withdrawals": metrics.total_withdrawals,
            "total_trades": metrics.total_trades,
            "total_profit": metrics.total_profit,
            "real_profit": metrics.real_profit,
            "total_volume": metrics.total_volume,
            "avg_daily_profit": metrics.avg_daily_profit,
            "avg_trade_profit": metrics.avg_trade_profit,
            "wins": metrics.wins,
            "losses": metrics.losses,
            "win_rate": metrics.win_rate,
            "max_drawdown": metrics.max_drawdown,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "current_drawdown": metrics.current_drawdown,
            "current_drawdown_pct": metrics.current_drawdown_pct,
            "profit_factor": metrics.profit_factor,
            "sharpe_ratio": metrics.sharpe_ratio,
            "recovery_factor": metrics.recovery_factor,
            "profit_today": metrics.profit_today,
            "profit_week": metrics.profit_week,
            "profit_month": metrics.profit_month,
            "profit_year": metrics.profit_year,
            "best_trade": metrics.best_trade,
            "worst_trade": metrics.worst_trade,
            "best_day": metrics.best_day,
            "worst_day": metrics.worst_day,
            "current_streak": metrics.current_streak,
            "max_win_streak": metrics.max_win_streak,
            "max_loss_streak": metrics.max_loss_streak
        }
    }


@router.get("/trades")
async def get_trades(days: int = 30):
    """
    Obtém histórico de trades.
    
    - days: Número de dias (0 = todos)
    """
    service = get_mt4_service()
    trades = service.get_trades(days)
    
    return {
        "success": True,
        "count": len(trades),
        "data": [
            {
                "ticket": t.ticket,
                "symbol": t.symbol,
                "type": t.type,
                "volume": t.volume,
                "open_price": t.open_price,
                "close_price": t.close_price,
                "open_time": t.open_time,
                "close_time": t.close_time,
                "profit": t.profit,
                "swap": t.swap,
                "commission": t.commission,
                "sl": t.sl,
                "tp": t.tp,
                "comment": t.comment,
                "total_pnl": t.profit + t.swap + t.commission
            }
            for t in trades
        ]
    }


@router.get("/deposits-withdrawals")
async def get_deposits_withdrawals():
    """Obtém histórico de depósitos e saques"""
    service = get_mt4_service()
    data = service.get_deposits_withdrawals()
    
    return {
        "success": True,
        "data": data
    }


@router.get("/daily-stats")
async def get_daily_stats(days: int = 30):
    """Obtém estatísticas diárias"""
    service = get_mt4_service()
    stats = service.get_daily_stats(days)
    
    return {
        "success": True,
        "count": len(stats),
        "data": stats
    }


@router.get("/symbol-stats")
async def get_symbol_stats():
    """Obtém estatísticas por símbolo"""
    service = get_mt4_service()
    stats = service.get_symbol_stats()
    
    return {
        "success": True,
        "count": len(stats),
        "data": stats
    }


@router.get("/equity-history")
async def get_equity_history(days: int = 30):
    """Obtém histórico de equity"""
    service = get_mt4_service()
    history = service.get_equity_history(days)
    
    return {
        "success": True,
        "count": len(history),
        "data": history
    }


@router.get("/summary")
async def get_summary():
    """Obtém resumo completo da conta"""
    service = get_mt4_service()
    return service.get_summary()


@router.post("/export")
async def export_data():
    """Exporta todos os dados para JSON"""
    service = get_mt4_service()
    data = service.export_to_json()
    
    return {
        "success": True,
        "data": data
    }


# ========== ZeroMQ Connection (opcional) ==========

@router.post("/connect-zmq")
async def connect_zmq(host: str = "localhost"):
    """
    Conecta ao MT4 via ZeroMQ.
    
    Requer:
    1. EA DWX_ZeroMQ_Server instalado no MT4
    2. pyzmq instalado (pip install pyzmq)
    """
    service = get_mt4_service()
    
    if service.connect_zmq(host):
        return {
            "success": True,
            "message": "Conectado ao MT4 via ZeroMQ"
        }
    else:
        return {
            "success": False,
            "message": "Falha ao conectar. Verifique se o EA está rodando no MT4 e se pyzmq está instalado."
        }


@router.post("/disconnect")
async def disconnect():
    """Desconecta do MT4"""
    service = get_mt4_service()
    service.disconnect()
    
    return {
        "success": True,
        "message": "Desconectado"
    }


# ========== Sync Endpoints (recebe dados do EA MT4) ==========

class SyncAccountInput(BaseModel):
    """Input para sincronização da conta via EA"""
    login: int
    name: str
    server: str
    currency: str
    balance: float
    equity: float
    margin: float = 0
    free_margin: float = 0
    profit: float = 0
    leverage: int = 100
    company: str = ""


class SyncTradeInput(BaseModel):
    """Input para sincronização de trade via EA"""
    ticket: int
    symbol: str
    type: str
    volume: float
    open_price: float
    close_price: float
    open_time: str
    close_time: str
    profit: float
    swap: float = 0
    commission: float = 0
    sl: float = 0
    tp: float = 0
    comment: str = ""


class SyncPositionInput(BaseModel):
    """Input para sincronização de posição aberta via EA"""
    ticket: int
    symbol: str
    type: str
    volume: float
    open_price: float
    current_price: float
    open_time: str
    profit: float
    swap: float = 0
    sl: float = 0
    tp: float = 0
    comment: str = ""


@router.post("/sync/account")
async def sync_account(data: SyncAccountInput):
    """
    Endpoint para receber dados da conta do EA MT4.
    O EA envia automaticamente os dados periodicamente.
    """
    service = get_mt4_service()
    
    # Atualizar informações da conta
    service.set_account_info({
        "login": data.login,
        "name": data.name,
        "server": data.server,
        "currency": data.currency,
        "balance": data.balance,
        "equity": data.equity,
        "margin": data.margin,
        "free_margin": data.free_margin,
        "profit": data.profit,
        "leverage": data.leverage,
        "company": data.company
    })
    
    # Salvar snapshot de equity
    service.update_balance(data.balance, data.equity)
    
    # Atualizar patrimônio automaticamente
    try:
        from services.patrimonio_service import get_patrimonio_service
        patrimonio = get_patrimonio_service()
        
        # Calcular lucro real
        metrics = service.calculate_metrics(0)
        real_profit = metrics.real_profit if metrics.real_profit > 0 else metrics.total_profit
        
        patrimonio.update_mt4(data.balance, real_profit)
    except Exception as e:
        print(f"⚠️ Erro ao atualizar patrimônio: {e}")
    
    print(f"📡 MT4 Sync: Conta {data.login} atualizada - Balance: {data.balance} {data.currency}")
    
    return {"success": True, "message": "Account synced"}


@router.post("/sync/trades")
async def sync_trades(trades: List[SyncTradeInput]):
    """
    Endpoint para receber histórico de trades do EA MT4.
    O EA envia os trades fechados automaticamente.
    """
    service = get_mt4_service()
    
    trades_data = [t.dict() for t in trades]
    count = service.import_trades_from_json(trades_data)
    
    print(f"📡 MT4 Sync: {count} trades importados")
    
    return {"success": True, "trades_imported": count}


@router.post("/sync/positions")
async def sync_positions(positions: List[SyncPositionInput]):
    """
    Endpoint para receber posições abertas do EA MT4.
    Armazena temporariamente para exibição no dashboard.
    """
    service = get_mt4_service()
    
    # Armazenar posições em memória (ou banco se preferir)
    service._open_positions = [p.dict() for p in positions]
    
    print(f"📡 MT4 Sync: {len(positions)} posições abertas")
    
    return {"success": True, "positions_count": len(positions)}


@router.get("/open-positions")
async def get_open_positions():
    """Obtém posições abertas sincronizadas do EA"""
    service = get_mt4_service()
    
    positions = getattr(service, '_open_positions', [])
    
    return {
        "success": True,
        "count": len(positions),
        "data": positions
    }
