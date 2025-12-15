"""
VIRTUS Telegram - Service
==========================

Serviço principal do Telegram Bot.
"""

import asyncio
import ssl
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import aiohttp

from ..core.logger import get_logger
from ..core.config import get_config
from ..core.exceptions import TelegramError, TelegramConnectionError, TelegramMessageError

logger = get_logger("telegram")


class TelegramService:
    """
    Serviço principal do Telegram.
    
    Responsabilidades:
    - Envio de mensagens
    - Formatação de mensagens
    - Gerenciamento de comandos
    - Webhooks (futuro)
    """
    
    _instance: Optional['TelegramService'] = None
    _lock = asyncio.Lock()
    
    API_URL = "https://api.telegram.org/bot{token}/{method}"
    
    def __init__(self):
        self._token: Optional[str] = None
        self._chat_id: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        
        # Handlers de comandos
        self._command_handlers: Dict[str, Callable] = {}
        
        # Rate limiting
        self._last_message_time: Optional[datetime] = None
        self._min_interval = 1.0  # segundos entre mensagens
    
    @classmethod
    async def get_instance(cls) -> 'TelegramService':
        """Retorna instância singleton"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                await cls._instance.initialize()
            return cls._instance
    
    async def initialize(self):
        """Inicializa o serviço"""
        if self._initialized:
            return
        
        logger.info("📱 Inicializando Telegram Service...")
        
        try:
            config = get_config()
            self._token = config.telegram.token
            self._chat_id = str(config.telegram.chat_id)
            
            if not self._token or not self._chat_id:
                raise TelegramError("Token ou Chat ID do Telegram não configurado")
            
            # Cria contexto SSL sem verificação (para ambientes com proxy/firewall)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(connector=connector)
            
            # Testa conexão
            me = await self._api_call('getMe')
            bot_name = me.get('username', 'Unknown')
            
            self._initialized = True
            logger.info(f"✅ Telegram Service inicializado - Bot: @{bot_name}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Telegram: {e}")
            raise TelegramConnectionError(str(e))
    
    async def _api_call(
        self,
        method: str,
        data: Optional[Dict] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Faz chamada à API do Telegram"""
        url = self.API_URL.format(token=self._token, method=method)
        
        try:
            async with self._session.post(
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                result = await response.json()
                
                if not result.get('ok'):
                    error_desc = result.get('description', 'Unknown error')
                    raise TelegramError(f"API Error: {error_desc}")
                
                return result.get('result', {})
                
        except aiohttp.ClientError as e:
            raise TelegramConnectionError(f"Erro de conexão: {e}")
    
    async def _rate_limit(self):
        """Aplica rate limiting"""
        if self._last_message_time:
            elapsed = (datetime.now() - self._last_message_time).total_seconds()
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
        self._last_message_time = datetime.now()
    
    # ========================================================================
    # ENVIO DE MENSAGENS
    # ========================================================================
    
    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "Markdown",
        disable_preview: bool = True,
        reply_markup: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Envia mensagem de texto.
        
        Args:
            text: Texto da mensagem (suporta Markdown)
            chat_id: ID do chat (default: chat configurado)
            parse_mode: Markdown ou HTML
            disable_preview: Desabilitar preview de links
            reply_markup: Botões inline (opcional)
            
        Returns:
            Dict com resultado
        """
        await self._rate_limit()
        
        data = {
            'chat_id': chat_id or self._chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_preview,
        }
        
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        try:
            result = await self._api_call('sendMessage', data)
            logger.debug(f"Mensagem enviada: {text[:50]}...")
            return result
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            raise TelegramMessageError(str(e))
    
    async def send_formatted_message(
        self,
        title: str,
        body: str,
        emoji: str = "📊",
        footer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia mensagem formatada padrão.
        
        Args:
            title: Título da mensagem
            body: Corpo da mensagem
            emoji: Emoji do título
            footer: Rodapé opcional
        """
        lines = [
            f"{emoji} *{title}*",
            "",
            body,
        ]
        
        if footer:
            lines.extend(["", f"_{footer}_"])
        
        text = "\n".join(lines)
        return await self.send_message(text)
    
    async def send_alert(
        self,
        message: str,
        level: str = "info"
    ) -> Dict[str, Any]:
        """
        Envia alerta.
        
        Args:
            message: Mensagem do alerta
            level: info, warning, error, success
        """
        emojis = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '🚨',
            'success': '✅',
        }
        
        emoji = emojis.get(level, 'ℹ️')
        text = f"{emoji} *ALERTA*\n\n{message}"
        
        return await self.send_message(text)
    
    async def send_trade_notification(
        self,
        action: str,
        symbol: str,
        volume: float,
        price: float,
        profit: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Envia notificação de trade.
        
        Args:
            action: OPEN, CLOSE, MODIFY
            symbol: Símbolo
            volume: Volume
            price: Preço
            profit: Lucro (para fechamento)
            sl: Stop loss
            tp: Take profit
        """
        emojis = {
            'OPEN': '🟢',
            'CLOSE': '🔴',
            'MODIFY': '🟡',
        }
        
        emoji = emojis.get(action, '📊')
        
        lines = [
            f"{emoji} *TRADE {action}*",
            "",
            f"📈 *{symbol}*",
            f"💰 Volume: {volume}",
            f"💵 Preço: {price:.5f}",
        ]
        
        if sl:
            lines.append(f"🛑 SL: {sl:.5f}")
        if tp:
            lines.append(f"🎯 TP: {tp:.5f}")
        if profit is not None:
            emoji_profit = "✅" if profit >= 0 else "❌"
            lines.append(f"{emoji_profit} Profit: ${profit:.2f}")
        
        lines.append(f"\n⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        text = "\n".join(lines)
        return await self.send_message(text)
    
    async def send_daily_summary(
        self,
        pnl: float,
        trades: int,
        win_rate: float,
        best_trade: float,
        worst_trade: float
    ) -> Dict[str, Any]:
        """
        Envia resumo diário.
        """
        emoji_pnl = "✅" if pnl >= 0 else "❌"
        
        text = f"""📊 *RESUMO DIÁRIO*

{emoji_pnl} *P&L Total:* ${pnl:.2f}
📈 *Trades:* {trades}
🎯 *Win Rate:* {win_rate:.1f}%
⬆️ *Melhor:* ${best_trade:.2f}
⬇️ *Pior:* ${worst_trade:.2f}

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
        
        return await self.send_message(text)
    
    # ========================================================================
    # BRIEFINGS
    # ========================================================================
    
    async def send_market_briefing(
        self,
        briefing_text: str
    ) -> Dict[str, Any]:
        """
        Envia briefing de mercado.
        
        Args:
            briefing_text: Texto do briefing formatado
        """
        return await self.send_message(briefing_text)
    
    async def send_news_digest(
        self,
        news_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Envia digest de notícias.
        
        Args:
            news_items: Lista de notícias
        """
        lines = ["📰 *NOTÍCIAS DO MERCADO*", ""]
        
        for i, news in enumerate(news_items[:5], 1):
            title = news.get('title', '')[:100]
            sentiment = news.get('sentiment', 0)
            
            emoji = "🟢" if sentiment > 0.2 else "🔴" if sentiment < -0.2 else "🟡"
            lines.append(f"{i}. {emoji} {title}")
        
        lines.append(f"\n⏰ {datetime.now().strftime('%H:%M')}")
        
        text = "\n".join(lines)
        return await self.send_message(text)
    
    async def send_calendar_events(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Envia eventos do calendário.
        """
        lines = ["📅 *EVENTOS ECONÔMICOS HOJE*", ""]
        
        impact_emoji = {
            'HIGH': '🔴',
            'MEDIUM': '🟡',
            'LOW': '🟢',
        }
        
        for event in events[:10]:
            emoji = impact_emoji.get(event.get('impact', 'LOW'), '⚪')
            time_str = event.get('time', '')
            name = event.get('name', '')[:50]
            currency = event.get('currency', '')
            
            lines.append(f"{emoji} {time_str} - {name} ({currency})")
        
        if not events:
            lines.append("_Nenhum evento de alto impacto hoje_")
        
        text = "\n".join(lines)
        return await self.send_message(text)
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    
    async def shutdown(self):
        """Encerra o serviço"""
        logger.info("📱 Encerrando Telegram Service...")
        
        if self._session:
            await self._session.close()
        
        logger.info("✅ Telegram Service encerrado")


# Helper
async def get_telegram() -> TelegramService:
    """Retorna instância do serviço Telegram"""
    return await TelegramService.get_instance()
