"""
VIRTUS Dashboard Backend - WebSocket Module
============================================
"""

from .manager import (
    WebSocketManager,
    WebSocketClient,
    ChannelType,
    ws_manager,
    websocket_handler,
)

__all__ = [
    "WebSocketManager",
    "WebSocketClient",
    "ChannelType",
    "ws_manager",
    "websocket_handler",
]
