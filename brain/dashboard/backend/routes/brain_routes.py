"""
Brain Integration Routes
========================

Rotas que integram com a Brain API (porta 8001).
Quando a Brain API está disponível, os dados vêm dela.
Quando não está, usa fallback local.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/brain", tags=["Brain Integration"])

BRAIN_API_URL = "http://localhost:8001"


async def check_brain_api() -> bool:
    """Verifica se a Brain API está disponível."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{BRAIN_API_URL}/api/health")
            return response.status_code == 200
    except:
        return False


@router.get("/health")
async def brain_health():
    """Status da conexão com Brain API."""
    available = await check_brain_api()
    return {
        "brain_api_available": available,
        "brain_api_url": BRAIN_API_URL,
        "mode": "connected" if available else "standalone"
    }


@router.get("/status")
async def get_brain_status():
    """Obtém status do sistema via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BRAIN_API_URL}/api/status")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Brain API indisponível: {e}")
    
    # Fallback
    return {
        "system_status": "unknown",
        "brain_api": "offline",
        "message": "Brain API não está disponível. Inicie com start_trading.ps1"
    }


@router.get("/account")
async def get_brain_account():
    """Obtém informações da conta MT5 via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BRAIN_API_URL}/api/account")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Erro ao obter conta: {e}")
    
    return {"error": "Brain API não disponível", "balance": 0, "equity": 0}


@router.get("/positions")
async def get_brain_positions():
    """Obtém posições abertas via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BRAIN_API_URL}/api/positions")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Erro ao obter posições: {e}")
    
    return []


@router.get("/bots")
async def get_brain_bots():
    """Obtém status dos bots via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BRAIN_API_URL}/api/bots")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Erro ao obter bots: {e}")
    
    return []


@router.post("/bots/{bot_id}/start")
async def start_brain_bot(bot_id: str):
    """Inicia um bot via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{BRAIN_API_URL}/api/bots/{bot_id}/start")
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": response.json().get("detail", "Erro")}
    except Exception as e:
        logger.error(f"Erro ao iniciar bot: {e}")
    
    return {"success": False, "error": "Brain API não disponível"}


@router.post("/bots/{bot_id}/stop")
async def stop_brain_bot(bot_id: str):
    """Para um bot via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{BRAIN_API_URL}/api/bots/{bot_id}/stop")
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": response.json().get("detail", "Erro")}
    except Exception as e:
        logger.error(f"Erro ao parar bot: {e}")
    
    return {"success": False, "error": "Brain API não disponível"}


@router.get("/analysis/{symbol}")
async def get_brain_analysis(symbol: str):
    """Obtém análise de um símbolo via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{BRAIN_API_URL}/api/analysis/{symbol}")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Erro ao obter análise: {e}")
    
    return {"symbol": symbol, "error": "Brain API não disponível"}


@router.get("/signals")
async def get_brain_signals():
    """Obtém sinais ativos via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BRAIN_API_URL}/api/signals")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Erro ao obter sinais: {e}")
    
    return []


@router.post("/trade")
async def execute_brain_trade(trade_request: dict):
    """Executa um trade via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{BRAIN_API_URL}/api/trade", json=trade_request)
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": response.json().get("detail", "Erro")}
    except Exception as e:
        logger.error(f"Erro ao executar trade: {e}")
    
    return {"success": False, "error": "Brain API não disponível"}


@router.delete("/position/{ticket}")
async def close_brain_position(ticket: int):
    """Fecha uma posição via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.delete(f"{BRAIN_API_URL}/api/position/{ticket}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": response.json().get("detail", "Erro")}
    except Exception as e:
        logger.error(f"Erro ao fechar posição: {e}")
    
    return {"success": False, "error": "Brain API não disponível"}


@router.get("/history")
async def get_brain_history(days: int = 7):
    """Obtém histórico de trades via Brain API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BRAIN_API_URL}/api/history?days={days}")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Erro ao obter histórico: {e}")
    
    return []
