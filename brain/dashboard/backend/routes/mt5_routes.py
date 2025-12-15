"""
VIRTUS Dashboard Backend - Rotas MT5
====================================

Integração real com MetaTrader 5.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/mt5", tags=["MT5"])

# ==================== MODELOS ====================

class MT5Credentials(BaseModel):
    login: int
    password: str
    server: str

class SyncRequest(BaseModel):
    days: int = 30
    symbol: Optional[str] = None

# ==================== ESTADO ====================

class MT5State:
    """Estado da conexão MT5."""
    connected: bool = False
    account_info: Optional[Dict] = None
    last_sync: Optional[datetime] = None

mt5_state = MT5State()

# ==================== HELPERS ====================

def get_mt5():
    """Obtém instância MT5."""
    try:
        import MetaTrader5 as mt5
        return mt5
    except ImportError:
        return None

def ensure_connected():
    """Garante conexão MT5."""
    mt5 = get_mt5()
    if mt5 is None:
        raise HTTPException(status_code=503, detail="MT5 não disponível")
    
    if not mt5.initialize():
        raise HTTPException(status_code=503, detail="Falha ao inicializar MT5")
    
    return mt5

# ==================== ROTAS ====================

@router.get("/status")
async def mt5_status():
    """Status da conexão MT5."""
    mt5 = get_mt5()
    
    if mt5 is None:
        return {"connected": False, "error": "MT5 não instalado"}
    
    if not mt5.initialize():
        return {"connected": False, "error": "MT5 não inicializado"}
    
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        return {"connected": False, "error": "Nenhuma conta conectada"}
    
    terminal = mt5.terminal_info()
    
    result = {
        "connected": True,
        "account": {
            "login": account.login,
            "server": account.server,
            "name": account.name,
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "free_margin": account.margin_free,
            "margin_level": account.margin_level if account.margin_level else 0,
            "profit": account.profit,
            "currency": account.currency,
            "leverage": account.leverage,
        },
        "terminal": {
            "name": terminal.name if terminal else "N/A",
            "path": terminal.path if terminal else "N/A",
            "connected": terminal.connected if terminal else False,
            "trade_allowed": terminal.trade_allowed if terminal else False,
        },
        "last_sync": mt5_state.last_sync.isoformat() if mt5_state.last_sync else None,
    }
    
    mt5_state.connected = True
    mt5_state.account_info = result["account"]
    
    mt5.shutdown()
    return result

@router.post("/connect")
async def mt5_connect(credentials: Optional[MT5Credentials] = None):
    """Conecta ao MT5."""
    mt5 = get_mt5()
    
    if mt5 is None:
        raise HTTPException(status_code=503, detail="MT5 não disponível")
    
    if credentials:
        if not mt5.initialize(
            login=credentials.login,
            password=credentials.password,
            server=credentials.server
        ):
            error = mt5.last_error()
            raise HTTPException(
                status_code=401, 
                detail=f"Falha ao conectar: {error}"
            )
    else:
        if not mt5.initialize():
            error = mt5.last_error()
            raise HTTPException(
                status_code=503, 
                detail=f"Falha ao inicializar: {error}"
            )
    
    account = mt5.account_info()
    mt5_state.connected = True
    
    return {
        "connected": True,
        "login": account.login,
        "server": account.server,
        "balance": account.balance,
    }

@router.post("/disconnect")
async def mt5_disconnect():
    """Desconecta do MT5."""
    mt5 = get_mt5()
    if mt5:
        mt5.shutdown()
    mt5_state.connected = False
    return {"connected": False}

@router.get("/account")
async def mt5_account():
    """Informações da conta MT5."""
    mt5 = ensure_connected()
    
    account = mt5.account_info()
    if not account:
        mt5.shutdown()
        raise HTTPException(status_code=500, detail="Falha ao obter conta")
    
    result = {
        "login": account.login,
        "trade_mode": account.trade_mode,
        "leverage": account.leverage,
        "limit_orders": account.limit_orders,
        "margin_so_mode": account.margin_so_mode,
        "trade_allowed": account.trade_allowed,
        "trade_expert": account.trade_expert,
        "balance": account.balance,
        "credit": account.credit,
        "profit": account.profit,
        "equity": account.equity,
        "margin": account.margin,
        "margin_free": account.margin_free,
        "margin_level": account.margin_level,
        "margin_so_call": account.margin_so_call,
        "margin_so_so": account.margin_so_so,
        "margin_initial": account.margin_initial,
        "margin_maintenance": account.margin_maintenance,
        "assets": account.assets,
        "liabilities": account.liabilities,
        "commission_blocked": account.commission_blocked,
        "name": account.name,
        "server": account.server,
        "currency": account.currency,
        "company": account.company,
    }
    
    mt5.shutdown()
    return result

@router.get("/positions")
async def mt5_positions():
    """Posições abertas no MT5."""
    mt5 = ensure_connected()
    
    positions = mt5.positions_get()
    
    if positions is None:
        mt5.shutdown()
        return {"positions": [], "total": 0}
    
    result = []
    for pos in positions:
        result.append({
            "ticket": pos.ticket,
            "time": datetime.fromtimestamp(pos.time).isoformat(),
            "time_update": datetime.fromtimestamp(pos.time_update).isoformat(),
            "type": "BUY" if pos.type == 0 else "SELL",
            "magic": pos.magic,
            "identifier": pos.identifier,
            "reason": pos.reason,
            "volume": pos.volume,
            "price_open": pos.price_open,
            "sl": pos.sl,
            "tp": pos.tp,
            "price_current": pos.price_current,
            "swap": pos.swap,
            "profit": pos.profit,
            "symbol": pos.symbol,
            "comment": pos.comment,
            "external_id": pos.external_id,
        })
    
    total_profit = sum(p["profit"] for p in result)
    
    mt5.shutdown()
    return {
        "positions": result,
        "total": len(result),
        "total_profit": round(total_profit, 2),
    }

@router.get("/orders")
async def mt5_orders():
    """Ordens pendentes no MT5."""
    mt5 = ensure_connected()
    
    orders = mt5.orders_get()
    
    if orders is None:
        mt5.shutdown()
        return {"orders": [], "total": 0}
    
    type_map = {
        0: "BUY", 1: "SELL", 2: "BUY_LIMIT", 3: "SELL_LIMIT",
        4: "BUY_STOP", 5: "SELL_STOP", 6: "BUY_STOP_LIMIT", 7: "SELL_STOP_LIMIT"
    }
    
    result = []
    for order in orders:
        result.append({
            "ticket": order.ticket,
            "time_setup": datetime.fromtimestamp(order.time_setup).isoformat(),
            "type": type_map.get(order.type, str(order.type)),
            "type_filling": order.type_filling,
            "type_time": order.type_time,
            "time_expiration": datetime.fromtimestamp(order.time_expiration).isoformat() if order.time_expiration else None,
            "magic": order.magic,
            "position_id": order.position_id,
            "volume_initial": order.volume_initial,
            "volume_current": order.volume_current,
            "price_open": order.price_open,
            "sl": order.sl,
            "tp": order.tp,
            "price_current": order.price_current,
            "price_stoplimit": order.price_stoplimit,
            "symbol": order.symbol,
            "comment": order.comment,
            "external_id": order.external_id,
        })
    
    mt5.shutdown()
    return {"orders": result, "total": len(result)}

@router.get("/history")
async def mt5_history(
    days: int = Query(default=30, ge=1, le=365),
    symbol: Optional[str] = None
):
    """Histórico de trades do MT5."""
    mt5 = ensure_connected()
    
    from_date = datetime.now() - timedelta(days=days)
    to_date = datetime.now()
    
    # Histórico de deals (execuções)
    if symbol:
        deals = mt5.history_deals_get(from_date, to_date, symbol=symbol)
    else:
        deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None:
        mt5.shutdown()
        return {"trades": [], "total": 0}
    
    # Agrupar deals por position_id para formar trades completos
    positions_deals = {}
    for deal in deals:
        pos_id = deal.position_id
        if pos_id not in positions_deals:
            positions_deals[pos_id] = []
        positions_deals[pos_id].append(deal)
    
    trades = []
    for pos_id, pos_deals in positions_deals.items():
        if len(pos_deals) < 2:
            continue  # Precisa de entry e exit
        
        # Ordenar por tempo
        pos_deals = sorted(pos_deals, key=lambda x: x.time)
        
        entry = pos_deals[0]
        exit_deal = pos_deals[-1]
        
        # Calcular P&L
        total_profit = sum(d.profit for d in pos_deals)
        total_commission = sum(d.commission for d in pos_deals)
        total_swap = sum(d.swap for d in pos_deals)
        
        trades.append({
            "position_id": pos_id,
            "ticket_entry": entry.ticket,
            "ticket_exit": exit_deal.ticket,
            "symbol": entry.symbol,
            "type": "BUY" if entry.type == 0 else "SELL",
            "volume": entry.volume,
            "entry_price": entry.price,
            "exit_price": exit_deal.price,
            "entry_time": datetime.fromtimestamp(entry.time).isoformat(),
            "exit_time": datetime.fromtimestamp(exit_deal.time).isoformat(),
            "profit": round(total_profit, 2),
            "commission": round(total_commission, 2),
            "swap": round(total_swap, 2),
            "net_profit": round(total_profit + total_commission + total_swap, 2),
            "magic": entry.magic,
            "comment": entry.comment,
        })
    
    # Ordenar por data de saída (mais recente primeiro)
    trades = sorted(trades, key=lambda x: x["exit_time"], reverse=True)
    
    # Estatísticas
    total_trades = len(trades)
    wins = [t for t in trades if t["net_profit"] > 0]
    losses = [t for t in trades if t["net_profit"] <= 0]
    
    stats = {
        "total_trades": total_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(len(wins) / total_trades * 100, 2) if total_trades > 0 else 0,
        "total_pnl": round(sum(t["net_profit"] for t in trades), 2),
        "gross_profit": round(sum(t["net_profit"] for t in wins), 2),
        "gross_loss": round(sum(t["net_profit"] for t in losses), 2),
        "avg_win": round(sum(t["net_profit"] for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(t["net_profit"] for t in losses) / len(losses), 2) if losses else 0,
    }
    
    mt5_state.last_sync = datetime.now()
    
    mt5.shutdown()
    return {
        "trades": trades,
        "total": total_trades,
        "stats": stats,
        "period_days": days,
        "last_sync": mt5_state.last_sync.isoformat(),
    }

@router.post("/sync")
async def mt5_sync(request: SyncRequest):
    """Sincroniza histórico do MT5 com banco de dados local."""
    mt5 = ensure_connected()
    
    from_date = datetime.now() - timedelta(days=request.days)
    to_date = datetime.now()
    
    # Obter deals
    if request.symbol:
        deals = mt5.history_deals_get(from_date, to_date, symbol=request.symbol)
    else:
        deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None:
        mt5.shutdown()
        return {"synced": 0, "message": "Nenhum deal encontrado"}
    
    # Aqui salvaria no banco de dados
    synced_count = len(deals)
    mt5_state.last_sync = datetime.now()
    
    mt5.shutdown()
    return {
        "synced": synced_count,
        "period_days": request.days,
        "symbol": request.symbol or "ALL",
        "last_sync": mt5_state.last_sync.isoformat(),
    }

@router.get("/symbols")
async def mt5_symbols():
    """Lista símbolos disponíveis no MT5."""
    mt5 = ensure_connected()
    
    symbols = mt5.symbols_get()
    
    if symbols is None:
        mt5.shutdown()
        return {"symbols": [], "total": 0}
    
    result = []
    for sym in symbols:
        if sym.visible:  # Apenas símbolos visíveis
            result.append({
                "name": sym.name,
                "description": sym.description,
                "path": sym.path,
                "spread": sym.spread,
                "digits": sym.digits,
                "trade_mode": sym.trade_mode,
                "volume_min": sym.volume_min,
                "volume_max": sym.volume_max,
                "volume_step": sym.volume_step,
            })
    
    mt5.shutdown()
    return {"symbols": result, "total": len(result)}

@router.get("/symbol/{symbol}")
async def mt5_symbol_info(symbol: str):
    """Informações de um símbolo específico."""
    mt5 = ensure_connected()
    
    info = mt5.symbol_info(symbol)
    
    if info is None:
        mt5.shutdown()
        raise HTTPException(status_code=404, detail=f"Símbolo {symbol} não encontrado")
    
    tick = mt5.symbol_info_tick(symbol)
    
    result = {
        "name": info.name,
        "description": info.description,
        "path": info.path,
        "point": info.point,
        "digits": info.digits,
        "spread": info.spread,
        "trade_mode": info.trade_mode,
        "volume_min": info.volume_min,
        "volume_max": info.volume_max,
        "volume_step": info.volume_step,
        "trade_contract_size": info.trade_contract_size,
        "currency_base": info.currency_base,
        "currency_profit": info.currency_profit,
        "currency_margin": info.currency_margin,
    }
    
    if tick:
        result["tick"] = {
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "volume": tick.volume,
            "time": datetime.fromtimestamp(tick.time).isoformat(),
        }
    
    mt5.shutdown()
    return result
