"""
VIRTUS - Routes para Paper Trading
===================================

Endpoints REST para simulação de trades.
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Adiciona path do src
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

router = APIRouter(prefix="/paper", tags=["Paper Trading"])

# Import do módulo de paper trading
try:
    from src.core.paper_trading import paper_trading, OrderType
    PAPER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Paper Trading module not available: {e}")
    PAPER_AVAILABLE = False


class OpenPositionRequest(BaseModel):
    symbol: str
    type: str  # buy, sell
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: str = ""


class ModifyPositionRequest(BaseModel):
    sl: Optional[float] = None
    tp: Optional[float] = None


@router.get("/status")
async def get_paper_status():
    """Retorna status do paper trading."""
    if not PAPER_AVAILABLE:
        return {"available": False, "message": "Paper Trading não disponível"}
    
    return {
        "available": True,
        "running": paper_trading._running,
        "account": paper_trading.get_account(),
        "open_positions": len(paper_trading.positions),
    }


@router.post("/start")
async def start_paper_trading():
    """Inicia o engine de paper trading."""
    if not PAPER_AVAILABLE:
        raise HTTPException(503, "Paper Trading não disponível")
    
    await paper_trading.start()
    return {"message": "Paper Trading iniciado", "status": "running"}


@router.post("/stop")
async def stop_paper_trading():
    """Para o engine de paper trading."""
    if not PAPER_AVAILABLE:
        raise HTTPException(503, "Paper Trading não disponível")
    
    await paper_trading.stop()
    return {"message": "Paper Trading parado", "status": "stopped"}


@router.get("/account")
async def get_paper_account():
    """Retorna informações da conta paper."""
    if not PAPER_AVAILABLE:
        raise HTTPException(503, "Paper Trading não disponível")
    
    return paper_trading.get_account()


@router.get("/positions")
async def get_paper_positions():
    """Retorna posições abertas."""
    if not PAPER_AVAILABLE:
        return []  # Retorna array vazio se não disponível
    
    positions = paper_trading.get_positions()
    return positions if positions else []


@router.get("/history")
async def get_paper_history(limit: int = 100):
    """Retorna histórico de trades."""
    if not PAPER_AVAILABLE:
        return []  # Retorna array vazio se não disponível
    
    history = paper_trading.get_history(limit)
    return history if history else []


@router.get("/stats")
async def get_paper_stats():
    """Retorna estatísticas de trading."""
    if not PAPER_AVAILABLE:
        raise HTTPException(503, "Paper Trading não disponível")
    
    return paper_trading.get_stats()


@router.post("/trade")
async def open_paper_trade(request: OpenPositionRequest):
    """Abre um trade paper."""
    if not PAPER_AVAILABLE:
        raise HTTPException(503, "Paper Trading não disponível")
    
    order_type = OrderType.BUY if request.type.lower() == "buy" else OrderType.SELL
    
    ticket = await paper_trading.open_position(
        symbol=request.symbol,
        order_type=order_type,
        volume=request.volume,
        sl=request.sl,
        tp=request.tp,
        comment=request.comment,
    )
    
    if ticket is None:
        raise HTTPException(400, "Falha ao abrir posição")
    
    return {"ticket": ticket, "message": "Posição aberta com sucesso"}


@router.delete("/trade/{ticket}")
async def close_paper_trade(ticket: int):
    """Fecha um trade paper."""
    if not PAPER_AVAILABLE:
        raise HTTPException(503, "Paper Trading não disponível")
    
    success = await paper_trading.close_position(ticket)
    
    if not success:
        raise HTTPException(400, "Falha ao fechar posição")
    
    return {"message": "Posição fechada com sucesso"}


@router.patch("/trade/{ticket}")
async def modify_paper_trade(ticket: int, request: ModifyPositionRequest):
    """Modifica SL/TP de um trade."""
    if not PAPER_AVAILABLE:
        raise HTTPException(503, "Paper Trading não disponível")
    
    success = await paper_trading.modify_position(ticket, request.sl, request.tp)
    
    if not success:
        raise HTTPException(400, "Falha ao modificar posição")
    
    return {"message": "Posição modificada com sucesso"}


@router.get("/price/{symbol}")
async def get_paper_price(symbol: str):
    """Retorna preço atual do símbolo."""
    if not PAPER_AVAILABLE:
        raise HTTPException(503, "Paper Trading não disponível")
    
    price = paper_trading.get_price(symbol)
    if not price:
        raise HTTPException(404, "Símbolo não encontrado")
    return price
