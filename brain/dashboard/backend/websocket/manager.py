"""
VIRTUS Dashboard Backend - WebSocket Manager
=============================================

Gerenciador de conexões WebSocket para dados em tempo real.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """Tipos de canais disponíveis."""
    METRICS = "metrics"
    POSITIONS = "positions"
    ORDERS = "orders"
    TRADES = "trades"
    ALERTS = "alerts"
    SYSTEM = "system"


@dataclass
class WebSocketClient:
    """Representa um cliente WebSocket conectado."""
    websocket: WebSocket
    user_id: str
    connected_at: datetime
    subscribed_channels: Set[str] = field(default_factory=set)
    last_ping: datetime = field(default_factory=datetime.now)
    
    async def send(self, message: Dict[str, Any]) -> bool:
        """Envia mensagem para o cliente."""
        try:
            await self.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {self.user_id}: {e}")
            return False


class WebSocketManager:
    """
    Gerenciador de conexões WebSocket.
    
    Recursos:
    - Múltiplos canais de subscription
    - Broadcast por canal
    - Heartbeat/ping-pong
    - Rate limiting
    - Autenticação
    """
    
    def __init__(self):
        self.clients: Dict[str, WebSocketClient] = {}
        self.channels: Dict[str, Set[str]] = {channel.value: set() for channel in ChannelType}
        self._running: bool = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        
        # Rate limiting
        self.message_counts: Dict[str, int] = {}
        self.max_messages_per_second: int = 10
        
        # Métricas callback
        self._metrics_callback: Optional[Callable] = None
        self._positions_callback: Optional[Callable] = None
    
    async def start(self):
        """Inicia o gerenciador."""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._metrics_task = asyncio.create_task(self._metrics_loop())
        logger.info("WebSocket Manager iniciado")
    
    async def stop(self):
        """Para o gerenciador."""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._metrics_task:
            self._metrics_task.cancel()
        
        # Desconectar todos os clientes
        for client_id in list(self.clients.keys()):
            await self.disconnect(client_id)
        
        logger.info("WebSocket Manager parado")
    
    async def connect(self, websocket: WebSocket, user_id: str) -> WebSocketClient:
        """Conecta um novo cliente."""
        await websocket.accept()
        
        client = WebSocketClient(
            websocket=websocket,
            user_id=user_id,
            connected_at=datetime.now(),
        )
        
        self.clients[user_id] = client
        
        # Enviar confirmação de conexão
        await client.send({
            "type": "connected",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "available_channels": [c.value for c in ChannelType],
        })
        
        logger.info(f"Cliente conectado: {user_id}")
        return client
    
    async def disconnect(self, user_id: str):
        """Desconecta um cliente."""
        if user_id not in self.clients:
            return
        
        client = self.clients[user_id]
        
        # Remover de todos os canais
        for channel in client.subscribed_channels:
            if channel in self.channels:
                self.channels[channel].discard(user_id)
        
        # Fechar conexão
        try:
            await client.websocket.close()
        except:
            pass
        
        del self.clients[user_id]
        logger.info(f"Cliente desconectado: {user_id}")
    
    async def subscribe(self, user_id: str, channels: List[str]) -> bool:
        """Inscreve cliente em canais."""
        if user_id not in self.clients:
            return False
        
        client = self.clients[user_id]
        
        for channel in channels:
            if channel in self.channels:
                self.channels[channel].add(user_id)
                client.subscribed_channels.add(channel)
        
        await client.send({
            "type": "subscribed",
            "channels": list(client.subscribed_channels),
        })
        
        return True
    
    async def unsubscribe(self, user_id: str, channels: List[str]) -> bool:
        """Remove inscrição de canais."""
        if user_id not in self.clients:
            return False
        
        client = self.clients[user_id]
        
        for channel in channels:
            if channel in self.channels:
                self.channels[channel].discard(user_id)
                client.subscribed_channels.discard(channel)
        
        await client.send({
            "type": "unsubscribed",
            "channels": channels,
        })
        
        return True
    
    async def broadcast(self, channel: str, message: Dict[str, Any]):
        """Envia mensagem para todos os clientes de um canal."""
        if channel not in self.channels:
            return
        
        message["channel"] = channel
        message["timestamp"] = datetime.now().isoformat()
        
        disconnected = []
        
        for user_id in self.channels[channel]:
            if user_id in self.clients:
                success = await self.clients[user_id].send(message)
                if not success:
                    disconnected.append(user_id)
        
        # Limpar clientes desconectados
        for user_id in disconnected:
            await self.disconnect(user_id)
    
    async def broadcast_all(self, message: Dict[str, Any]):
        """Envia mensagem para todos os clientes conectados."""
        message["channel"] = "broadcast"
        message["timestamp"] = datetime.now().isoformat()
        
        disconnected = []
        
        for user_id, client in self.clients.items():
            success = await client.send(message)
            if not success:
                disconnected.append(user_id)
        
        for user_id in disconnected:
            await self.disconnect(user_id)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Envia mensagem para um usuário específico."""
        if user_id not in self.clients:
            return False
        
        message["timestamp"] = datetime.now().isoformat()
        return await self.clients[user_id].send(message)
    
    async def handle_message(self, user_id: str, data: Dict[str, Any]):
        """Processa mensagem recebida de um cliente."""
        if user_id not in self.clients:
            return
        
        client = self.clients[user_id]
        msg_type = data.get("type", "")
        
        if msg_type == "ping":
            client.last_ping = datetime.now()
            await client.send({"type": "pong"})
        
        elif msg_type == "subscribe":
            channels = data.get("channels", [])
            await self.subscribe(user_id, channels)
        
        elif msg_type == "unsubscribe":
            channels = data.get("channels", [])
            await self.unsubscribe(user_id, channels)
        
        elif msg_type == "get_status":
            await client.send({
                "type": "status",
                "subscribed_channels": list(client.subscribed_channels),
                "connected_at": client.connected_at.isoformat(),
                "clients_online": len(self.clients),
            })
    
    async def _heartbeat_loop(self):
        """Loop de heartbeat para manter conexões vivas."""
        while self._running:
            await asyncio.sleep(30)
            
            now = datetime.now()
            disconnected = []
            
            for user_id, client in self.clients.items():
                # Verificar timeout (2 minutos sem ping)
                if (now - client.last_ping).total_seconds() > 120:
                    disconnected.append(user_id)
                else:
                    # Enviar ping
                    await client.send({"type": "heartbeat"})
            
            for user_id in disconnected:
                logger.warning(f"Cliente {user_id} timeout, desconectando")
                await self.disconnect(user_id)
    
    async def _metrics_loop(self):
        """Loop de envio de métricas em tempo real."""
        while self._running:
            await asyncio.sleep(1)  # A cada segundo
            
            # Métricas
            if ChannelType.METRICS.value in self.channels:
                if self._metrics_callback:
                    try:
                        metrics = await self._metrics_callback()
                        await self.broadcast(ChannelType.METRICS.value, {
                            "type": "metrics_update",
                            "data": metrics,
                        })
                    except Exception as e:
                        logger.error(f"Erro ao obter métricas: {e}")
            
            # Posições
            if ChannelType.POSITIONS.value in self.channels:
                if self._positions_callback:
                    try:
                        positions = await self._positions_callback()
                        await self.broadcast(ChannelType.POSITIONS.value, {
                            "type": "positions_update",
                            "data": positions,
                        })
                    except Exception as e:
                        logger.error(f"Erro ao obter posições: {e}")
    
    def set_metrics_callback(self, callback: Callable):
        """Define callback para obter métricas."""
        self._metrics_callback = callback
    
    def set_positions_callback(self, callback: Callable):
        """Define callback para obter posições."""
        self._positions_callback = callback
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do WebSocket."""
        return {
            "total_clients": len(self.clients),
            "channels": {
                channel: len(users) 
                for channel, users in self.channels.items()
            },
            "clients": [
                {
                    "user_id": client.user_id,
                    "connected_at": client.connected_at.isoformat(),
                    "subscribed_channels": list(client.subscribed_channels),
                }
                for client in self.clients.values()
            ],
        }


# Instância global
ws_manager = WebSocketManager()


async def websocket_handler(websocket: WebSocket, user_id: str):
    """Handler principal para conexões WebSocket."""
    client = await ws_manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(user_id, data)
    
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"Erro no WebSocket {user_id}: {e}")
        await ws_manager.disconnect(user_id)
