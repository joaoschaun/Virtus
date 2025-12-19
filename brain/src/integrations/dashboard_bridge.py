"""
Dashboard Bridge - Integração Bot Principal <-> Dashboard
==========================================================

Este módulo permite que o bot principal envie dados em tempo real
para o dashboard via WebSocket e arquivo compartilhado.
"""

import asyncio
import json
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import websockets
from websockets.exceptions import ConnectionClosed

from src.core.logger import VirtusLogger


class DashboardBridge:
    """
    Ponte de comunicação entre o bot principal e o dashboard.
    
    Envia atualizações em tempo real via:
    1. WebSocket (conexão direta ao backend)
    2. Arquivo JSON compartilhado (fallback)
    """
    
    _instance: Optional['DashboardBridge'] = None
    
    def __init__(self):
        self.logger = VirtusLogger.get_logger("dashboard_bridge")
        
        # Configurações
        self.ws_url = "ws://localhost:8000/ws/internal"
        self.data_file = Path(__file__).parent.parent.parent / "data" / "bot_state.json"
        
        # Estado
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._running = False
        self._reconnect_task: Optional[asyncio.Task] = None
        
        # Cache de dados
        self._state: Dict[str, Any] = {
            "system_status": "offline",
            "mt5_connected": False,
            "account": {},
            "bots": [],
            "positions": [],
            "signals": [],
            "metrics": {},
            "last_update": None,
        }
    
    @classmethod
    async def get_instance(cls) -> 'DashboardBridge':
        """Singleton."""
        if cls._instance is None:
            cls._instance = DashboardBridge()
            await cls._instance.start()
        return cls._instance
    
    async def start(self):
        """Inicia a bridge."""
        if self._running:
            return
        
        self._running = True
        self.logger.info("🔗 Dashboard Bridge iniciando...")
        
        # Tenta conectar via WebSocket
        asyncio.create_task(self._connect_ws())
        
        # Garante que o diretório de dados existe
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
    
    async def stop(self):
        """Para a bridge."""
        self._running = False
        
        if self._reconnect_task:
            self._reconnect_task.cancel()
        
        if self._ws:
            await self._ws.close()
        
        self.logger.info("🔗 Dashboard Bridge parada")
    
    async def _connect_ws(self):
        """Conecta ao WebSocket do dashboard."""
        while self._running:
            try:
                self._ws = await websockets.connect(self.ws_url)
                self._connected = True
                self.logger.success("✅ Conectado ao Dashboard via WebSocket")
                
                # Envia estado inicial
                await self._send_ws({"type": "bot_connected", "data": self._state})
                
                # Mantém conexão e processa mensagens
                async for message in self._ws:
                    try:
                        data = json.loads(message)
                        await self._handle_ws_message(data)
                    except json.JSONDecodeError:
                        pass
                        
            except ConnectionClosed:
                self.logger.warning("⚠️ Conexão WebSocket fechada")
            except Exception as e:
                # WebSocket pode não estar disponível, usa fallback
                pass
            
            self._connected = False
            
            if self._running:
                await asyncio.sleep(5)  # Reconectar em 5s
    
    async def _send_ws(self, data: Dict[str, Any]):
        """Envia dados via WebSocket."""
        if self._ws and self._connected:
            try:
                await self._ws.send(json.dumps(data, default=str))
            except Exception:
                self._connected = False
    
    async def _handle_ws_message(self, data: Dict[str, Any]):
        """Processa mensagens do dashboard."""
        msg_type = data.get("type")
        
        if msg_type == "ping":
            await self._send_ws({"type": "pong"})
        elif msg_type == "get_status":
            await self._send_ws({"type": "status", "data": self._state})
    
    async def _save_state_to_file(self):
        """Salva estado em arquivo JSON (fallback)."""
        try:
            async with aiofiles.open(self.data_file, 'w') as f:
                await f.write(json.dumps(self._state, default=str, indent=2))
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao salvar estado: {e}")
    
    # ==================== MÉTODOS DE ATUALIZAÇÃO ====================
    
    async def update_system_status(self, status: str):
        """Atualiza status do sistema."""
        self._state["system_status"] = status
        self._state["last_update"] = datetime.now().isoformat()
        
        await self._broadcast({
            "type": "system_status",
            "data": {"status": status, "timestamp": self._state["last_update"]}
        })
    
    async def update_mt5_status(self, connected: bool, account: Optional[Dict] = None):
        """Atualiza status da conexão MT5."""
        self._state["mt5_connected"] = connected
        self._state["account"] = account or {}
        self._state["last_update"] = datetime.now().isoformat()
        
        await self._broadcast({
            "type": "mt5_status",
            "data": {
                "connected": connected,
                "account": account,
                "timestamp": self._state["last_update"]
            }
        })
    
    async def update_bots(self, bots: List[Dict]):
        """Atualiza lista de bots."""
        self._state["bots"] = bots
        self._state["last_update"] = datetime.now().isoformat()
        
        await self._broadcast({
            "type": "bots_update",
            "data": {"bots": bots, "timestamp": self._state["last_update"]}
        })
    
    async def update_positions(self, positions: List[Dict]):
        """Atualiza posições abertas."""
        self._state["positions"] = positions
        self._state["last_update"] = datetime.now().isoformat()
        
        await self._broadcast({
            "type": "positions_update",
            "data": {"positions": positions, "timestamp": self._state["last_update"]}
        })
    
    async def update_signals(self, signals: List[Dict]):
        """Atualiza sinais recentes."""
        self._state["signals"] = signals
        self._state["last_update"] = datetime.now().isoformat()
        
        await self._broadcast({
            "type": "signals_update",
            "data": {"signals": signals, "timestamp": self._state["last_update"]}
        })
    
    async def update_metrics(self, metrics: Dict[str, Any]):
        """Atualiza métricas de performance."""
        self._state["metrics"] = metrics
        self._state["last_update"] = datetime.now().isoformat()
        
        await self._broadcast({
            "type": "metrics_update",
            "data": {"metrics": metrics, "timestamp": self._state["last_update"]}
        })
    
    async def send_trade_event(self, trade: Dict[str, Any], event_type: str = "trade_opened"):
        """Envia evento de trade."""
        await self._broadcast({
            "type": event_type,
            "data": {"trade": trade, "timestamp": datetime.now().isoformat()}
        })
    
    async def send_alert(self, message: str, level: str = "info"):
        """Envia alerta para o dashboard."""
        await self._broadcast({
            "type": "alert",
            "data": {
                "message": message,
                "level": level,
                "timestamp": datetime.now().isoformat()
            }
        })
    
    async def _broadcast(self, data: Dict[str, Any]):
        """Envia dados via WebSocket e salva em arquivo."""
        # Tenta WebSocket primeiro
        await self._send_ws(data)
        
        # Sempre salva em arquivo como backup
        await self._save_state_to_file()
    
    def get_state(self) -> Dict[str, Any]:
        """Retorna estado atual."""
        return self._state.copy()
    
    @property
    def is_connected(self) -> bool:
        """Retorna se está conectado ao dashboard."""
        return self._connected


# Singleton global
_bridge: Optional[DashboardBridge] = None


async def get_dashboard_bridge() -> DashboardBridge:
    """Obtém instância da bridge."""
    global _bridge
    if _bridge is None:
        _bridge = await DashboardBridge.get_instance()
    return _bridge
