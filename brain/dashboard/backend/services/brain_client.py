"""
Brain API Client
=================

Cliente para consumir a Brain API (porta 8001).
Usado pelo Dashboard Backend para obter dados de trading.
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BrainAPIClient:
    """Cliente para a Brain API."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.timeout = 10.0
        self._connected = False
        self._last_check = None
    
    async def is_available(self) -> bool:
        """Verifica se a Brain API está disponível."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/api/health")
                self._connected = response.status_code == 200
                self._last_check = datetime.now()
                return self._connected
        except:
            self._connected = False
            return False
    
    async def get_status(self) -> Optional[Dict]:
        """Obtém status do sistema."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/status")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Brain API não disponível: {e}")
        return None
    
    async def get_account(self) -> Optional[Dict]:
        """Obtém informações da conta MT5."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/account")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Erro ao obter conta: {e}")
        return None
    
    async def get_positions(self) -> List[Dict]:
        """Obtém posições abertas."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/positions")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Erro ao obter posições: {e}")
        return []
    
    async def get_bots(self) -> List[Dict]:
        """Obtém status dos bots."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/bots")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Erro ao obter bots: {e}")
        return []
    
    async def start_bot(self, bot_id: str) -> bool:
        """Inicia um bot."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/bots/{bot_id}/start")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao iniciar bot {bot_id}: {e}")
        return False
    
    async def stop_bot(self, bot_id: str) -> bool:
        """Para um bot."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/bots/{bot_id}/stop")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao parar bot {bot_id}: {e}")
        return False
    
    async def get_analysis(self, symbol: str) -> Optional[Dict]:
        """Obtém análise de um símbolo."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/analysis/{symbol}")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Erro ao obter análise de {symbol}: {e}")
        return None
    
    async def get_signals(self) -> List[Dict]:
        """Obtém sinais ativos."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/signals")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Erro ao obter sinais: {e}")
        return []
    
    async def execute_trade(self, symbol: str, direction: str, volume: float, 
                           sl: float = None, tp: float = None) -> Optional[Dict]:
        """Executa um trade."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                data = {
                    "symbol": symbol,
                    "direction": direction,
                    "volume": volume,
                    "sl": sl,
                    "tp": tp,
                }
                response = await client.post(f"{self.base_url}/api/trade", json=data)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.json().get("detail", "Erro desconhecido")}
        except Exception as e:
            logger.error(f"Erro ao executar trade: {e}")
        return None
    
    async def close_position(self, ticket: int) -> Optional[Dict]:
        """Fecha uma posição."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(f"{self.base_url}/api/position/{ticket}")
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.json().get("detail", "Erro desconhecido")}
        except Exception as e:
            logger.error(f"Erro ao fechar posição {ticket}: {e}")
        return None
    
    async def get_history(self, days: int = 7) -> List[Dict]:
        """Obtém histórico de trades."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/history?days={days}")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Erro ao obter histórico: {e}")
        return []


# Instância global
brain_client = BrainAPIClient()


async def get_brain_client() -> BrainAPIClient:
    """Dependency injection para FastAPI."""
    return brain_client
