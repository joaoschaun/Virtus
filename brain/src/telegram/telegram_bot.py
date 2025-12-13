"""
BRAIN - Telegram Bot
Bot do Telegram para notificações e comandos
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import os

from ..core.logger import get_logger
from ..core.exceptions import TelegramError

logger = get_logger("telegram")


@dataclass
class TelegramConfig:
    """Configuração do bot Telegram"""
    token: str
    chat_id: str
    enabled: bool = True
    admin_ids: List[str] = None


class TelegramBot:
    """
    Bot do Telegram para BRAIN
    
    Responsabilidades:
    - Enviar notificações de trades
    - Receber comandos
    - Enviar relatórios
    - Alertas de risco
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._token: Optional[str] = None
        self._chat_id: Optional[str] = None
        self._admin_ids: List[str] = []
        self._enabled = False
        
        self._bot = None  # Instância do telegram.Bot
        self._application = None  # Aplicação para handlers
        
        # Handlers de comandos
        self._command_handlers: Dict[str, Callable] = {}
        
        # Fila de mensagens
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._sender_task: Optional[asyncio.Task] = None
        
        self._initialized = True
    
    async def initialize(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        admin_ids: Optional[List[str]] = None
    ):
        """
        Inicializa o bot Telegram
        
        Args:
            token: Token do bot (ou TELEGRAM_BOT_TOKEN env)
            chat_id: ID do chat principal (ou TELEGRAM_CHAT_ID env)
            admin_ids: Lista de IDs de administradores
        """
        self._token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self._chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self._admin_ids = admin_ids or []
        
        if not self._token:
            logger.warning("Token do Telegram não configurado")
            self._enabled = False
            return
        
        if not self._chat_id:
            logger.warning("Chat ID do Telegram não configurado")
            self._enabled = False
            return
        
        try:
            # Importar telegram
            from telegram import Bot
            from telegram.ext import Application, CommandHandler
            
            # Criar bot
            self._bot = Bot(token=self._token)
            
            # Criar aplicação para handlers
            self._application = Application.builder().token(self._token).build()
            
            # Registrar handlers padrão
            self._register_default_handlers()
            
            self._enabled = True
            
            # Iniciar sender task
            self._sender_task = asyncio.create_task(self._message_sender_loop())
            
            logger.info("Telegram Bot inicializado")
            
            # Mensagem de teste
            await self.send_message("🤖 BRAIN Trading Bot iniciado!")
            
        except ImportError:
            logger.warning("python-telegram-bot não instalado")
            self._enabled = False
        except Exception as e:
            logger.error(f"Erro ao inicializar Telegram: {e}")
            self._enabled = False
    
    async def shutdown(self):
        """Desliga o bot"""
        if self._sender_task:
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass
        
        if self._application:
            await self._application.shutdown()
        
        self._enabled = False
        logger.info("Telegram Bot desligado")
    
    def _register_default_handlers(self):
        """Registra handlers de comandos padrão"""
        from telegram.ext import CommandHandler
        
        # /start
        self._application.add_handler(
            CommandHandler("start", self._cmd_start)
        )
        
        # /status
        self._application.add_handler(
            CommandHandler("status", self._cmd_status)
        )
        
        # /positions
        self._application.add_handler(
            CommandHandler("positions", self._cmd_positions)
        )
        
        # /briefing
        self._application.add_handler(
            CommandHandler("briefing", self._cmd_briefing)
        )
        
        # /pause
        self._application.add_handler(
            CommandHandler("pause", self._cmd_pause)
        )
        
        # /resume
        self._application.add_handler(
            CommandHandler("resume", self._cmd_resume)
        )
    
    # ==========================================================================
    # ENVIO DE MENSAGENS
    # ==========================================================================
    
    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML"
    ):
        """
        Envia mensagem
        
        Args:
            text: Texto da mensagem
            chat_id: ID do chat (default: chat principal)
            parse_mode: Modo de parse (HTML, Markdown)
        """
        if not self._enabled:
            return
        
        await self._message_queue.put({
            "text": text,
            "chat_id": chat_id or self._chat_id,
            "parse_mode": parse_mode
        })
    
    async def _message_sender_loop(self):
        """Loop de envio de mensagens"""
        while True:
            try:
                msg = await self._message_queue.get()
                
                await self._bot.send_message(
                    chat_id=msg["chat_id"],
                    text=msg["text"],
                    parse_mode=msg.get("parse_mode", "HTML")
                )
                
                # Rate limit
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem: {e}")
                await asyncio.sleep(1)
    
    # ==========================================================================
    # NOTIFICAÇÕES
    # ==========================================================================
    
    async def notify_trade_opened(
        self,
        symbol: str,
        direction: str,
        volume: float,
        price: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        strategy: str = ""
    ):
        """Notifica abertura de trade"""
        emoji = "🟢" if direction.upper() == "BUY" else "🔴"
        direction_pt = "COMPRA" if direction.upper() == "BUY" else "VENDA"
        
        text = f"""
{emoji} <b>TRADE ABERTO</b>

📊 <b>Símbolo:</b> {symbol}
📈 <b>Direção:</b> {direction_pt}
💰 <b>Volume:</b> {volume}
💵 <b>Preço:</b> {price}
🛑 <b>SL:</b> {sl or 'N/A'}
🎯 <b>TP:</b> {tp or 'N/A'}
📋 <b>Estratégia:</b> {strategy}
⏰ <b>Horário:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(text.strip())
    
    async def notify_trade_closed(
        self,
        symbol: str,
        direction: str,
        volume: float,
        open_price: float,
        close_price: float,
        profit: float,
        pips: float
    ):
        """Notifica fechamento de trade"""
        emoji = "✅" if profit >= 0 else "❌"
        result = "LUCRO" if profit >= 0 else "PREJUÍZO"
        
        text = f"""
{emoji} <b>TRADE FECHADO - {result}</b>

📊 <b>Símbolo:</b> {symbol}
📈 <b>Direção:</b> {direction}
💰 <b>Volume:</b> {volume}
💵 <b>Abertura:</b> {open_price}
💵 <b>Fechamento:</b> {close_price}
💰 <b>Resultado:</b> ${profit:.2f} ({pips:.1f} pips)
⏰ <b>Horário:</b> {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(text.strip())
    
    async def notify_alert(
        self,
        level: str,
        title: str,
        message: str
    ):
        """
        Envia alerta
        
        Args:
            level: critical, warning, info
            title: Título do alerta
            message: Mensagem
        """
        emoji_map = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        emoji = emoji_map.get(level, "📢")
        
        text = f"""
{emoji} <b>{title.upper()}</b>

{message}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(text.strip())
    
    async def send_daily_report(self, report: Dict[str, Any]):
        """
        Envia relatório diário
        
        Args:
            report: Dict com dados do relatório
        """
        trades = report.get("trades", 0)
        wins = report.get("wins", 0)
        losses = report.get("losses", 0)
        profit = report.get("profit", 0)
        win_rate = (wins / trades * 100) if trades > 0 else 0
        
        emoji = "🟢" if profit >= 0 else "🔴"
        
        text = f"""
📊 <b>RELATÓRIO DIÁRIO</b>
{datetime.now().strftime('%d/%m/%Y')}

{emoji} <b>Resultado:</b> ${profit:.2f}

📈 <b>Trades:</b> {trades}
✅ <b>Wins:</b> {wins}
❌ <b>Losses:</b> {losses}
📊 <b>Win Rate:</b> {win_rate:.1f}%

💼 <b>Por Símbolo:</b>
"""
        
        for symbol, data in report.get("by_symbol", {}).items():
            sym_emoji = "🟢" if data.get("profit", 0) >= 0 else "🔴"
            text += f"{sym_emoji} {symbol}: ${data.get('profit', 0):.2f}\n"
        
        await self.send_message(text.strip())
    
    # ==========================================================================
    # COMANDOS
    # ==========================================================================
    
    async def _cmd_start(self, update, context):
        """Handler do comando /start"""
        await update.message.reply_text(
            "🤖 <b>BRAIN Trading Bot</b>\n\n"
            "Comandos disponíveis:\n"
            "/status - Status do sistema\n"
            "/positions - Posições abertas\n"
            "/briefing - Briefing do mercado\n"
            "/pause - Pausar todos os bots\n"
            "/resume - Resumir bots\n",
            parse_mode="HTML"
        )
    
    async def _cmd_status(self, update, context):
        """Handler do comando /status"""
        # Callback será setado pelo orchestrator
        if "status_callback" in self._command_handlers:
            status = await self._command_handlers["status_callback"]()
            await update.message.reply_text(
                f"📊 <b>Status do Sistema</b>\n\n{status}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("Status não disponível")
    
    async def _cmd_positions(self, update, context):
        """Handler do comando /positions"""
        if "positions_callback" in self._command_handlers:
            positions = await self._command_handlers["positions_callback"]()
            await update.message.reply_text(
                f"💼 <b>Posições Abertas</b>\n\n{positions}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("Posições não disponíveis")
    
    async def _cmd_briefing(self, update, context):
        """Handler do comando /briefing"""
        if "briefing_callback" in self._command_handlers:
            briefing = await self._command_handlers["briefing_callback"]()
            await update.message.reply_text(briefing, parse_mode="HTML")
        else:
            await update.message.reply_text("Briefing não disponível")
    
    async def _cmd_pause(self, update, context):
        """Handler do comando /pause"""
        user_id = str(update.effective_user.id)
        
        if user_id not in self._admin_ids:
            await update.message.reply_text("⛔ Sem permissão")
            return
        
        if "pause_callback" in self._command_handlers:
            await self._command_handlers["pause_callback"]()
            await update.message.reply_text("⏸️ Bots pausados")
        else:
            await update.message.reply_text("Comando não disponível")
    
    async def _cmd_resume(self, update, context):
        """Handler do comando /resume"""
        user_id = str(update.effective_user.id)
        
        if user_id not in self._admin_ids:
            await update.message.reply_text("⛔ Sem permissão")
            return
        
        if "resume_callback" in self._command_handlers:
            await self._command_handlers["resume_callback"]()
            await update.message.reply_text("▶️ Bots resumidos")
        else:
            await update.message.reply_text("Comando não disponível")
    
    def set_command_handler(self, command: str, callback: Callable):
        """
        Define callback para um comando
        
        Args:
            command: Nome do comando (sem /)
            callback: Função callback
        """
        self._command_handlers[f"{command}_callback"] = callback


# Singleton global
_telegram_bot: Optional[TelegramBot] = None


def get_telegram_bot() -> TelegramBot:
    """Obtém instância global do bot Telegram"""
    global _telegram_bot
    if _telegram_bot is None:
        _telegram_bot = TelegramBot()
    return _telegram_bot
