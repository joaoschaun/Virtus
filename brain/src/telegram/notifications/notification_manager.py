"""
BRAIN - Notificações do Telegram
Sistema de notificações automáticas
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ...core.logger import get_logger

logger = get_logger("telegram.notifications")


class NotificationType(Enum):
    """Tipos de notificação"""
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    SIGNAL_GENERATED = "signal_generated"
    BREAKEVEN = "breakeven"
    TRAILING_UPDATE = "trailing_update"
    ALERT = "alert"
    ERROR = "error"
    BOT_STATUS = "bot_status"
    DAILY_SUMMARY = "daily_summary"


class NotificationPriority(Enum):
    """Prioridade da notificação"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Notification:
    """Representa uma notificação"""
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    bot_id: Optional[str] = None
    symbol: Optional[str] = None


class NotificationManager:
    """
    Gerenciador de Notificações
    
    Responsabilidades:
    - Formatar mensagens
    - Filtrar por prioridade
    - Enviar via Telegram
    - Rate limiting de notificações
    """
    
    def __init__(self, telegram_bot=None, min_priority: NotificationPriority = NotificationPriority.NORMAL):
        self._telegram = telegram_bot
        self._min_priority = min_priority
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Rate limiting
        self._last_sent: Dict[str, datetime] = {}
        self._cooldowns: Dict[NotificationType, int] = {
            NotificationType.SIGNAL_GENERATED: 60,  # 1 min
            NotificationType.TRAILING_UPDATE: 300,  # 5 min
            NotificationType.BOT_STATUS: 600,  # 10 min
        }
    
    async def start(self):
        """Inicia processamento de notificações"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._process_queue())
        logger.info("NotificationManager iniciado")
    
    async def stop(self):
        """Para processamento"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("NotificationManager parado")
    
    async def _process_queue(self):
        """Processa fila de notificações"""
        while self._running:
            try:
                notification = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                await self._send_notification(notification)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Erro ao processar notificação: {e}")
    
    async def _send_notification(self, notification: Notification):
        """Envia notificação"""
        # Verificar prioridade
        if notification.priority.value < self._min_priority.value:
            return
        
        # Verificar cooldown
        if not self._check_cooldown(notification):
            return
        
        # Formatar mensagem
        message = self._format_message(notification)
        
        # Enviar via Telegram
        if self._telegram:
            try:
                await self._telegram.send_message(message)
                self._last_sent[notification.type.value] = datetime.now()
            except Exception as e:
                logger.error(f"Erro ao enviar notificação: {e}")
    
    def _check_cooldown(self, notification: Notification) -> bool:
        """Verifica se pode enviar (cooldown)"""
        cooldown = self._cooldowns.get(notification.type, 0)
        
        if cooldown == 0:
            return True
        
        last = self._last_sent.get(notification.type.value)
        if not last:
            return True
        
        elapsed = (datetime.now() - last).total_seconds()
        return elapsed >= cooldown
    
    def _format_message(self, notification: Notification) -> str:
        """Formata mensagem da notificação"""
        formatters = {
            NotificationType.TRADE_OPENED: self._format_trade_opened,
            NotificationType.TRADE_CLOSED: self._format_trade_closed,
            NotificationType.SIGNAL_GENERATED: self._format_signal,
            NotificationType.BREAKEVEN: self._format_breakeven,
            NotificationType.TRAILING_UPDATE: self._format_trailing,
            NotificationType.ALERT: self._format_alert,
            NotificationType.ERROR: self._format_error,
            NotificationType.BOT_STATUS: self._format_bot_status,
            NotificationType.DAILY_SUMMARY: self._format_daily_summary,
        }
        
        formatter = formatters.get(notification.type, self._format_generic)
        return formatter(notification)
    
    # ==========================================================================
    # FORMATADORES
    # ==========================================================================
    
    def _format_trade_opened(self, n: Notification) -> str:
        """Formata notificação de trade aberto"""
        data = n.data
        direction = "🟢 COMPRA" if data.get("direction") == "buy" else "🔴 VENDA"
        
        return (
            f"📈 **TRADE ABERTO**\n\n"
            f"{direction} **{data.get('symbol', n.symbol)}**\n"
            f"📊 Volume: {data.get('volume', 0)} lots\n"
            f"💰 Entrada: {data.get('entry_price', 0):.5f}\n"
            f"🛑 SL: {data.get('stop_loss', 0):.5f}\n"
            f"🎯 TP: {data.get('take_profit', 0):.5f}\n"
            f"📋 Ticket: #{data.get('ticket', 0)}\n"
            f"🤖 Bot: {n.bot_id or 'N/A'}\n"
            f"⏰ {n.timestamp.strftime('%H:%M:%S')}"
        )
    
    def _format_trade_closed(self, n: Notification) -> str:
        """Formata notificação de trade fechado"""
        data = n.data
        profit = data.get("profit", 0)
        profit_emoji = "✅" if profit > 0 else "❌"
        
        return (
            f"{profit_emoji} **TRADE FECHADO**\n\n"
            f"**{data.get('symbol', n.symbol)}**\n"
            f"💰 Resultado: ${profit:+.2f}\n"
            f"📊 Pips: {data.get('pips', 0):+.1f}\n"
            f"⏱️ Duração: {data.get('duration', 'N/A')}\n"
            f"📋 Ticket: #{data.get('ticket', 0)}\n"
            f"📝 Motivo: {data.get('close_reason', 'N/A')}"
        )
    
    def _format_signal(self, n: Notification) -> str:
        """Formata notificação de sinal"""
        data = n.data
        direction = "🟢" if data.get("direction") == "buy" else "🔴"
        
        return (
            f"📡 **SINAL GERADO**\n\n"
            f"{direction} **{data.get('symbol', n.symbol)}** - {data.get('direction', '').upper()}\n"
            f"📊 Confiança: {data.get('confidence', 0)*100:.0f}%\n"
            f"💰 Entrada: {data.get('entry_price', 0):.5f}\n"
            f"🎯 R:R: {data.get('risk_reward', 0):.1f}\n"
            f"📋 Estratégia: {data.get('strategy', 'N/A')}"
        )
    
    def _format_breakeven(self, n: Notification) -> str:
        """Formata notificação de breakeven"""
        data = n.data
        
        return (
            f"⚖️ **BREAKEVEN**\n\n"
            f"**{data.get('symbol', n.symbol)}** #{data.get('ticket', 0)}\n"
            f"🎯 Novo SL: {data.get('new_sl', 0):.5f}\n"
            f"💰 Protegido: ${data.get('protected_profit', 0):.2f}"
        )
    
    def _format_trailing(self, n: Notification) -> str:
        """Formata notificação de trailing"""
        data = n.data
        
        return (
            f"📈 **TRAILING STOP**\n\n"
            f"**{data.get('symbol', n.symbol)}** #{data.get('ticket', 0)}\n"
            f"🎯 SL: {data.get('old_sl', 0):.5f} → {data.get('new_sl', 0):.5f}\n"
            f"💰 Lucro protegido: ${data.get('protected', 0):.2f}"
        )
    
    def _format_alert(self, n: Notification) -> str:
        """Formata alerta"""
        priority_emoji = {
            NotificationPriority.LOW: "ℹ️",
            NotificationPriority.NORMAL: "⚠️",
            NotificationPriority.HIGH: "🚨",
            NotificationPriority.CRITICAL: "🔴"
        }.get(n.priority, "⚠️")
        
        return (
            f"{priority_emoji} **{n.title}**\n\n"
            f"{n.message}"
        )
    
    def _format_error(self, n: Notification) -> str:
        """Formata erro"""
        return (
            f"❌ **ERRO**\n\n"
            f"**{n.title}**\n"
            f"{n.message}\n\n"
            f"🤖 Bot: {n.bot_id or 'Sistema'}\n"
            f"⏰ {n.timestamp.strftime('%H:%M:%S')}"
        )
    
    def _format_bot_status(self, n: Notification) -> str:
        """Formata status do bot"""
        data = n.data
        state = data.get("state", "unknown")
        
        state_emoji = {
            "running": "🟢",
            "paused": "🟡",
            "stopped": "🔴",
            "error": "❌"
        }.get(state, "⚪")
        
        return (
            f"🤖 **STATUS DO BOT**\n\n"
            f"**{n.bot_id}** {state_emoji} {state.upper()}\n"
            f"📊 Trades hoje: {data.get('trades_today', 0)}\n"
            f"💰 P&L: ${data.get('daily_pnl', 0):+.2f}"
        )
    
    def _format_daily_summary(self, n: Notification) -> str:
        """Formata resumo diário"""
        data = n.data
        
        return (
            f"📊 **RESUMO DO DIA**\n"
            f"{datetime.now().strftime('%d/%m/%Y')}\n\n"
            f"🔄 Trades: {data.get('total_trades', 0)}\n"
            f"✅ Wins: {data.get('wins', 0)} | ❌ Losses: {data.get('losses', 0)}\n"
            f"📈 Win Rate: {data.get('win_rate', 0):.1f}%\n"
            f"💰 P&L: ${data.get('total_profit', 0):+.2f}\n"
            f"📉 Max DD: {data.get('max_drawdown', 0):.1f}%\n\n"
            f"🏆 Melhor: ${data.get('best_trade', 0):+.2f}\n"
            f"💔 Pior: ${data.get('worst_trade', 0):+.2f}"
        )
    
    def _format_generic(self, n: Notification) -> str:
        """Formatação genérica"""
        return (
            f"📢 **{n.title}**\n\n"
            f"{n.message}"
        )
    
    # ==========================================================================
    # API PÚBLICA
    # ==========================================================================
    
    async def notify(
        self,
        type: NotificationType,
        title: str,
        message: str = "",
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Dict = None,
        bot_id: str = None,
        symbol: str = None
    ):
        """
        Adiciona notificação à fila
        
        Args:
            type: Tipo da notificação
            title: Título
            message: Mensagem
            priority: Prioridade
            data: Dados adicionais
            bot_id: ID do bot (opcional)
            symbol: Símbolo (opcional)
        """
        notification = Notification(
            type=type,
            title=title,
            message=message,
            priority=priority,
            data=data or {},
            bot_id=bot_id,
            symbol=symbol
        )
        
        await self._queue.put(notification)
    
    async def notify_trade_opened(
        self,
        symbol: str,
        direction: str,
        volume: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        ticket: int,
        bot_id: str = None
    ):
        """Notifica abertura de trade"""
        await self.notify(
            type=NotificationType.TRADE_OPENED,
            title="Trade Aberto",
            priority=NotificationPriority.HIGH,
            data={
                "symbol": symbol,
                "direction": direction,
                "volume": volume,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "ticket": ticket
            },
            bot_id=bot_id,
            symbol=symbol
        )
    
    async def notify_trade_closed(
        self,
        symbol: str,
        profit: float,
        pips: float,
        duration: str,
        ticket: int,
        close_reason: str = "manual",
        bot_id: str = None
    ):
        """Notifica fechamento de trade"""
        await self.notify(
            type=NotificationType.TRADE_CLOSED,
            title="Trade Fechado",
            priority=NotificationPriority.HIGH,
            data={
                "symbol": symbol,
                "profit": profit,
                "pips": pips,
                "duration": duration,
                "ticket": ticket,
                "close_reason": close_reason
            },
            bot_id=bot_id,
            symbol=symbol
        )
    
    async def notify_error(
        self,
        title: str,
        message: str,
        bot_id: str = None
    ):
        """Notifica erro"""
        await self.notify(
            type=NotificationType.ERROR,
            title=title,
            message=message,
            priority=NotificationPriority.CRITICAL,
            bot_id=bot_id
        )
    
    async def notify_alert(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ):
        """Envia alerta"""
        await self.notify(
            type=NotificationType.ALERT,
            title=title,
            message=message,
            priority=priority
        )
