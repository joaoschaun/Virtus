"""
VIRTUS Telegram Module
======================

Integração com Telegram para notificações e comandos.
"""

from .telegram_service import TelegramService, get_telegram

__all__ = [
    'TelegramService',
    'get_telegram',
]
