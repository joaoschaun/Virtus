"""
VIRTUS Bot-Specific Telegram Commands
=====================================

Comandos para controle individual de cada bot por símbolo.
Permite gerenciar XAUUSD, EURUSD, GBPUSD independentemente.

Features:
- Rate limiting por usuário
- Sistema de autorização por níveis (VIEWER/TRADER/ADMIN)
- Inline keyboards para navegação rápida
- Métricas de uso e latência por comando
- Confirmação 2-passos para comandos destrutivos
- Typing indicator durante processamento
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, TYPE_CHECKING, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import asyncio
import time
import logging

if TYPE_CHECKING:
    from telegram import Update, InlineKeyboardMarkup
    from telegram.ext import ContextTypes

# Logger para comandos
logger = logging.getLogger("virtus.telegram.commands.bot")


# =============================================================================
# ENUMS E DATACLASSES
# =============================================================================

class BotState(Enum):
    """Estados possíveis de um bot."""
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    ERROR = "error"
    STARTING = "starting"


class UserRole(Enum):
    """Níveis de autorização do usuário."""
    VIEWER = "viewer"
    TRADER = "trader"
    ADMIN = "admin"


class CommandCategory(Enum):
    """Categorias de comandos para métricas."""
    STATUS = "status"
    POSITIONS = "positions"
    HISTORY = "history"
    CONFIG = "config"
    CONTROL = "control"


@dataclass
class RateLimitConfig:
    """Configuração de rate limiting."""
    max_requests: int = 30
    window_seconds: int = 60
    cooldown_seconds: int = 60


@dataclass
class CommandMetrics:
    """Métricas de um comando."""
    name: str
    calls: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.calls if self.calls > 0 else 0.0
    
    def record_call(self, latency_ms: float, error: bool = False) -> None:
        self.calls += 1
        self.total_latency_ms += latency_ms
        if error:
            self.errors += 1


@dataclass
class UserRateLimit:
    """Rate limit por usuário."""
    user_id: int
    requests: List[datetime] = field(default_factory=list)
    blocked_until: Optional[datetime] = None
    
    def check_and_record(self, config: RateLimitConfig) -> bool:
        now = datetime.now()
        
        # Se está bloqueado
        if self.blocked_until and now < self.blocked_until:
            return False
        
        # Limpa bloqueio expirado
        if self.blocked_until and now >= self.blocked_until:
            self.blocked_until = None
            self.requests.clear()
        
        # Remove requests antigas
        cutoff = now - timedelta(seconds=config.window_seconds)
        self.requests = [r for r in self.requests if r > cutoff]
        
        # Verifica limite
        if len(self.requests) >= config.max_requests:
            self.blocked_until = now + timedelta(seconds=config.cooldown_seconds)
            return False
        
        # Registra nova request
        self.requests.append(now)
        return True


@dataclass
class BotSnapshot:
    """Snapshot do estado de um bot."""
    symbol: str
    state: BotState
    positions: int
    daily_pnl: float
    daily_trades: int
    win_rate: float
    drawdown: float
    last_trade: Optional[datetime]
    strategy: str
    risk_mode: str
    exposure: float = 0.0
    floating_pnl: float = 0.0


# =============================================================================
# DECORATORS
# =============================================================================

def require_role(min_role: UserRole):
    """Decorator que exige um nível mínimo de autorização."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
            user_id = update.effective_user.id
            user_role = self._get_user_role(user_id)
            
            role_order = {UserRole.VIEWER: 0, UserRole.TRADER: 1, UserRole.ADMIN: 2}
            
            if role_order[user_role] < role_order[min_role]:
                await self._safe_reply(
                    update,
                    f"🔒 <b>Acesso Negado</b>\n\n"
                    f"Este comando requer nível: <code>{min_role.value}</code>\n"
                    f"Seu nível: <code>{user_role.value}</code>"
                )
                return
            
            return await func(self, update, context, *args, **kwargs)
        return wrapper
    return decorator


def track_command(category: CommandCategory):
    """Decorator que registra métricas do comando."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
            start_time = time.time()
            error = False
            
            try:
                result = await func(self, update, context, *args, **kwargs)
                return result
            except Exception as e:
                error = True
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000
                self._record_metrics(func.__name__, latency_ms, error, category)
        return wrapper
    return decorator


def with_typing(func: Callable):
    """Decorator que mostra typing indicator."""
    @wraps(func)
    async def wrapper(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
        try:
            if update.effective_chat:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action="typing"
                )
        except:
            pass
        return await func(self, update, context, *args, **kwargs)
    return wrapper


class BotCommands:
    """
    Comandos para bots individuais com autorização e rate limiting.
    
    Features:
    - Rate limiting por usuário (30 req/min)
    - Autorização por níveis (VIEWER/TRADER/ADMIN)
    - Inline keyboards para navegação
    - Métricas de uso por comando
    - Confirmação 2-passos para fechamento
    
    Comandos disponíveis:
    - /bot [símbolo] - Status do bot
    - /bot_status [símbolo] - Status detalhado
    - /bot_positions [símbolo] - Posições do bot
    - /bot_history [símbolo] - Histórico de trades
    - /bot_pause [símbolo] - Pausa o bot (TRADER+)
    - /bot_resume [símbolo] - Retoma o bot (TRADER+)
    - /bot_config [símbolo] - Configuração atual
    - /bot_close [símbolo] - Fecha posições do bot (TRADER+)
    """
    
    # Símbolos suportados
    SUPPORTED_SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD']
    SYMBOL_ALIASES = {
        'gold': 'XAUUSD',
        'ouro': 'XAUUSD',
        'xau': 'XAUUSD',
        'euro': 'EURUSD',
        'eur': 'EURUSD',
        'gbp': 'GBPUSD',
        'libra': 'GBPUSD',
        'pound': 'GBPUSD',
        'cable': 'GBPUSD',
    }
    
    def __init__(
        self, 
        orchestrator=None, 
        bot_manager=None,
        admin_ids: Optional[List[int]] = None,
        trader_ids: Optional[List[int]] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Inicializa comandos de bot.
        
        Args:
            orchestrator: Orquestrador de bots
            bot_manager: Gerenciador de bots individuais
            admin_ids: Lista de IDs de admins
            trader_ids: Lista de IDs de traders
            rate_limit_config: Configuração de rate limiting
        """
        self.orchestrator = orchestrator
        self.bot_manager = bot_manager
        self.logger = logger
        
        # Autorização
        self._admin_ids = set(admin_ids or [])
        self._trader_ids = set(trader_ids or [])
        
        # Rate limiting
        self._rate_config = rate_limit_config or RateLimitConfig()
        self._rate_limits: Dict[int, UserRateLimit] = {}
        
        # Métricas
        self._metrics: Dict[str, CommandMetrics] = {}
        
        # Confirmações pendentes (para fechar posições)
        self._pending_confirmations: Dict[int, Dict[str, Any]] = {}
    
    # =========================================================================
    # MÉTODOS UTILITÁRIOS
    # =========================================================================
    
    def _get_user_role(self, user_id: int) -> UserRole:
        """Retorna o papel do usuário."""
        if user_id in self._admin_ids:
            return UserRole.ADMIN
        if user_id in self._trader_ids:
            return UserRole.TRADER
        return UserRole.VIEWER
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Verifica rate limit do usuário."""
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = UserRateLimit(user_id=user_id)
        return self._rate_limits[user_id].check_and_record(self._rate_config)
    
    def _record_metrics(
        self, command: str, latency_ms: float, error: bool, category: CommandCategory
    ) -> None:
        """Registra métricas de um comando."""
        if command not in self._metrics:
            self._metrics[command] = CommandMetrics(name=command)
        self._metrics[command].record_call(latency_ms, error)
    
    async def _safe_reply(
        self, 
        update: "Update", 
        text: str, 
        parse_mode: str = "HTML",
        reply_markup: Any = None,
    ) -> bool:
        """Reply seguro com tratamento de erro."""
        try:
            if update and update.message:
                await update.message.reply_text(
                    text, 
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True,
                )
                return True
            # Para callback queries
            elif update and update.callback_query:
                await update.callback_query.message.reply_text(
                    text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True,
                )
                return True
        except Exception as e:
            self.logger.error(f"Erro ao enviar resposta: {e}")
        return False
    
    async def _check_and_reply_rate_limit(self, update: "Update") -> bool:
        """Verifica rate limit e responde se bloqueado."""
        user_id = update.effective_user.id
        
        if not self._check_rate_limit(user_id):
            limit = self._rate_limits[user_id]
            remaining = (limit.blocked_until - datetime.now()).seconds if limit.blocked_until else 0
            
            await self._safe_reply(
                update,
                f"⏳ <b>Rate Limit Atingido</b>\n\n"
                f"Muitas requisições. Aguarde {remaining}s."
            )
            return False
        return True
    
    def _create_inline_keyboard(self, buttons: List[List[tuple]]) -> "InlineKeyboardMarkup":
        """Cria teclado inline."""
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = []
            for row in buttons:
                keyboard.append([
                    InlineKeyboardButton(text, callback_data=data)
                    for text, data in row
                ])
            
            return InlineKeyboardMarkup(keyboard)
        except ImportError:
            return None
    def _resolve_symbol(self, text: str) -> Optional[str]:
        """
        Resolve texto para símbolo válido.
        
        Args:
            text: Texto do usuário (pode ser alias)
            
        Returns:
            Símbolo válido ou None
        """
        if not text:
            return None
        
        text_upper = text.upper()
        text_lower = text.lower()
        
        # Verifica se é símbolo direto
        if text_upper in self.SUPPORTED_SYMBOLS:
            return text_upper
        
        # Verifica aliases
        if text_lower in self.SYMBOL_ALIASES:
            return self.SYMBOL_ALIASES[text_lower]
        
        return None
    
    def _format_symbol_emoji(self, symbol: str) -> str:
        """Retorna emoji para o símbolo."""
        emojis = {
            'XAUUSD': '🥇',
            'EURUSD': '💶',
            'GBPUSD': '💷',
        }
        return emojis.get(symbol, '📊')
    
    # =========================================================================
    # COMANDOS DE STATUS
    # =========================================================================
    
    @track_command(CommandCategory.STATUS)
    @with_typing
    async def cmd_bot(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot [símbolo] - Status rápido do bot."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /bot de {user.username or user.id}")
            
            args = context.args
            
            if not args:
                await self._show_all_bots(update)
                return
            
            symbol = self._resolve_symbol(args[0])
            if not symbol:
                await self._safe_reply(
                    update,
                    f"❌ Símbolo não reconhecido: <code>{args[0]}</code>\n\n"
                    f"Símbolos válidos: {', '.join(self.SUPPORTED_SYMBOLS)}\n"
                    f"Aliases: gold, euro, gbp, ouro, libra, etc."
                )
                return
            
            await self._show_bot_status(update, symbol)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_bot: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    @track_command(CommandCategory.STATUS)
    @with_typing
    async def _show_all_bots(self, update: "Update") -> None:
        """Mostra status de todos os bots com inline keyboards."""
        try:
            now = datetime.now()
            text = f"""
🤖 <b>VIRTUS - Status dos Bots</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

"""
            
            total_pnl = 0.0
            total_positions = 0
            
            for symbol in self.SUPPORTED_SYMBOLS:
                bot = await self._get_bot_snapshot(symbol)
                emoji = self._format_symbol_emoji(symbol)
                state_emoji = self._state_emoji(bot.state)
                
                total_pnl += bot.daily_pnl
                total_positions += bot.positions
                
                pnl_emoji = "+" if bot.daily_pnl >= 0 else ""
                
                text += f"{emoji} <b>{symbol}</b> {state_emoji}\n"
                text += f"   ├ Posições: {bot.positions}\n"
                text += f"   ├ P&L: {pnl_emoji}${bot.daily_pnl:,.2f}\n"
                text += f"   ├ Win Rate: {bot.win_rate:.1f}%\n"
                text += f"   └ Drawdown: {bot.drawdown:.2f}%\n\n"
            
            total_pnl_emoji = "📈" if total_pnl >= 0 else "📉"
            text += f"""
<b>━━━━━━━━━━━━━━━</b>
{total_pnl_emoji} <b>Total P&L:</b> ${total_pnl:+,.2f}
📊 <b>Posições:</b> {total_positions}
"""
            
            # Botões para cada símbolo
            buttons = []
            for symbol in self.SUPPORTED_SYMBOLS:
                emoji = self._format_symbol_emoji(symbol)
                buttons.append([
                    (f"{emoji} {symbol}", f"bot_detail_{symbol}"),
                    ("📊 Posições", f"bot_pos_{symbol}"),
                ])
            
            buttons.append([("🔄 Refresh", "refresh_all_bots")])
            
            keyboard = self._create_inline_keyboard(buttons)
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no _show_all_bots: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    @track_command(CommandCategory.STATUS)
    @with_typing
    async def _show_bot_status(self, update: "Update", symbol: str) -> None:
        """Mostra status detalhado de um bot com inline keyboards."""
        try:
            bot = await self._get_bot_snapshot(symbol)
            emoji = self._format_symbol_emoji(symbol)
            state_emoji = self._state_emoji(bot.state)
            user_role = self._get_user_role(update.effective_user.id)
            
            now = datetime.now()
            last_trade = "Nenhum hoje"
            if bot.last_trade:
                last_trade = bot.last_trade.strftime('%H:%M:%S')
            
            # Barras visuais
            wr_pct = int(bot.win_rate / 10)
            wr_bar = "🟩" * wr_pct + "⬜" * (10 - wr_pct)
            
            dd_pct = min(10, int(bot.drawdown / 1))  # Cada bloco = 1%
            dd_bar = ""
            for i in range(10):
                if i < dd_pct:
                    if dd_pct < 3:
                        dd_bar += "🟩"
                    elif dd_pct < 6:
                        dd_bar += "🟨"
                    else:
                        dd_bar += "🟥"
                else:
                    dd_bar += "⬜"
            
            pnl_emoji = "📈" if bot.daily_pnl >= 0 else "📉"
            
            text = f"""
{emoji} <b>{symbol} Bot Status</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

<b>Estado:</b> {state_emoji} {bot.state.value.title()}
<b>Estratégia:</b> {bot.strategy}
<b>Modo Risco:</b> {bot.risk_mode}

<b>{pnl_emoji} Performance Hoje:</b>
├ P&L: <code>${bot.daily_pnl:+,.2f}</code>
├ Trades: {bot.daily_trades}
├ Win Rate: {wr_bar} {bot.win_rate:.1f}%
└ Último: {last_trade}

<b>📈 Posições:</b>
├ Abertas: {bot.positions}
├ Floating: <code>${bot.floating_pnl:+,.2f}</code>
└ Exposição: <code>${bot.exposure:,.2f}</code>

<b>📉 Risco:</b>
{dd_bar} {bot.drawdown:.2f}%
            """
            
            # Botões de ação
            buttons = [
                [("📊 Posições", f"bot_pos_{symbol}"), ("📜 Histórico", f"bot_hist_{symbol}")],
                [("⚙️ Config", f"bot_cfg_{symbol}"), ("📈 Métricas", f"bot_metrics_{symbol}")],
            ]
            
            # Adiciona botões de controle se tem permissão
            if user_role in (UserRole.TRADER, UserRole.ADMIN):
                if bot.state == BotState.RUNNING:
                    buttons.append([("⏸️ Pausar", f"bot_pause_{symbol}")])
                else:
                    buttons.append([("▶️ Retomar", f"bot_resume_{symbol}")])
            
            buttons.append([("🔄 Refresh", f"bot_detail_{symbol}"), ("◀️ Voltar", "refresh_all_bots")])
            
            keyboard = self._create_inline_keyboard(buttons)
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no _show_bot_status: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    def _state_emoji(self, state: BotState) -> str:
        """Retorna emoji para o estado do bot."""
        emojis = {
            BotState.RUNNING: "🟢",
            BotState.PAUSED: "🟡",
            BotState.BLOCKED: "🔴",
            BotState.ERROR: "❌",
            BotState.STARTING: "🔄",
        }
        return emojis.get(state, "⚪")
    
    async def _get_bot_snapshot(self, symbol: str) -> BotSnapshot:
        """Coleta snapshot do estado do bot."""
        # Default values - seriam preenchidos pelo bot_manager real
        snapshot = BotSnapshot(
            symbol=symbol,
            state=BotState.RUNNING,
            positions=0,
            daily_pnl=0.0,
            daily_trades=0,
            win_rate=0.0,
            drawdown=0.0,
            last_trade=None,
            strategy="TrendStrategy",
            risk_mode="Normal",
            exposure=0.0,
            floating_pnl=0.0,
        )
        
        # Se tem bot_manager, pega dados reais
        if self.bot_manager:
            try:
                real_data = await self.bot_manager.get_bot_status(symbol)
                if real_data:
                    snapshot = BotSnapshot(**real_data)
            except Exception as e:
                self.logger.error(f"Erro ao obter status do bot {symbol}: {e}")
        
        return snapshot
    
    @track_command(CommandCategory.STATUS)
    async def cmd_bot_status(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot_status [símbolo] - Status detalhado."""
        await self.cmd_bot(update, context)
    
    # =========================================================================
    # POSIÇÕES E HISTÓRICO
    # =========================================================================
    
    @track_command(CommandCategory.POSITIONS)
    @with_typing
    async def cmd_bot_positions(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot_positions [símbolo] - Posições do bot."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            user_role = self._get_user_role(user.id)
            self.logger.info(f"Comando /bot_positions de {user.username or user.id}")
            
            args = context.args
            
            if not args:
                await self._safe_reply(
                    update,
                    "❌ Informe o símbolo: /bot_positions XAUUSD\n\n"
                    f"Símbolos: {', '.join(self.SUPPORTED_SYMBOLS)}"
                )
                return
            
            symbol = self._resolve_symbol(args[0])
            if not symbol:
                await self._safe_reply(update, f"❌ Símbolo não reconhecido: {args[0]}")
                return
            
            positions = await self._get_bot_positions(symbol)
            emoji = self._format_symbol_emoji(symbol)
            now = datetime.now()
            
            if not positions:
                keyboard = self._create_inline_keyboard([
                    [("📊 Status", f"bot_detail_{symbol}"), ("🔄 Refresh", f"bot_pos_{symbol}")],
                ])
                await self._safe_reply(
                    update,
                    f"{emoji} <b>{symbol}</b>\n"
                    f"<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>\n\n"
                    "📭 Nenhuma posição aberta.",
                    reply_markup=keyboard
                )
                return
            
            text = f"{emoji} <b>{symbol} - Posições Abertas</b>\n"
            text += f"<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>\n\n"
            
            total_pnl = 0.0
            total_volume = 0.0
            
            for i, pos in enumerate(positions, 1):
                direction = "🟢 LONG" if pos['type'] == 'long' else "🔴 SHORT"
                total_pnl += pos['pnl']
                total_volume += pos['volume']
                
                # Calcula % até SL/TP
                if pos['type'] == 'long':
                    sl_dist = ((pos['current'] - pos['sl']) / pos['current'] * 100) if pos['sl'] > 0 else 0
                    tp_dist = ((pos['tp'] - pos['current']) / pos['current'] * 100) if pos['tp'] > 0 else 0
                else:
                    sl_dist = ((pos['sl'] - pos['current']) / pos['current'] * 100) if pos['sl'] > 0 else 0
                    tp_dist = ((pos['current'] - pos['tp']) / pos['current'] * 100) if pos['tp'] > 0 else 0
                
                pnl_emoji = "+" if pos['pnl'] >= 0 else ""
                
                text += f"<b>#{i}</b> {direction}\n"
                text += f"├ Volume: <code>{pos['volume']:.2f}</code> lots\n"
                text += f"├ Entry: <code>{pos['entry']:.5f}</code>\n"
                text += f"├ Current: <code>{pos['current']:.5f}</code>\n"
                text += f"├ SL: <code>{pos['sl']:.5f}</code> ({sl_dist:.1f}%)\n"
                text += f"├ TP: <code>{pos['tp']:.5f}</code> ({tp_dist:.1f}%)\n"
                text += f"├ P&L: <code>{pnl_emoji}${pos['pnl']:.2f}</code>\n"
                text += f"└ Duração: {pos.get('duration', 'N/A')}\n\n"
            
            total_emoji = "📈" if total_pnl >= 0 else "📉"
            text += f"""
<b>━━━━━━━━━━━━━━━</b>
{total_emoji} <b>Total P&L:</b> <code>${total_pnl:+,.2f}</code>
📊 <b>Volume:</b> <code>{total_volume:.2f}</code> lots
"""
            
            # Botões de ação
            buttons = [[("📊 Status", f"bot_detail_{symbol}"), ("🔄 Refresh", f"bot_pos_{symbol}")]]
            
            if user_role in (UserRole.TRADER, UserRole.ADMIN) and positions:
                buttons.append([("⚠️ Fechar Todas", f"bot_close_{symbol}")])
            
            keyboard = self._create_inline_keyboard(buttons)
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_bot_positions: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    async def _get_bot_positions(self, symbol: str) -> List[Dict[str, Any]]:
        """Coleta posições do bot."""
        # Retorna lista vazia se não há conexão
        if self.bot_manager:
            try:
                return await self.bot_manager.get_positions(symbol)
            except:
                pass
        return []
    
    @track_command(CommandCategory.HISTORY)
    @with_typing
    async def cmd_bot_history(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot_history [símbolo] [dias] - Histórico de trades."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /bot_history de {user.username or user.id}")
            
            args = context.args
            
            if not args:
                await self._safe_reply(
                    update,
                    "❌ Informe o símbolo: /bot_history XAUUSD [dias]\n\n"
                    f"Símbolos: {', '.join(self.SUPPORTED_SYMBOLS)}\n"
                    "Exemplo: /bot_history gold 7"
                )
                return
            
            symbol = self._resolve_symbol(args[0])
            if not symbol:
                await self._safe_reply(update, f"❌ Símbolo não reconhecido: {args[0]}")
                return
            
            # Pega parâmetros adicionais (dias)
            days = 1
            if len(args) > 1:
                try:
                    days = min(30, max(1, int(args[1])))  # Entre 1 e 30 dias
                except:
                    pass
            
            history = await self._get_bot_history(symbol, days)
            emoji = self._format_symbol_emoji(symbol)
            now = datetime.now()
            
            period_text = "Hoje" if days == 1 else f"Últimos {days} dias"
            
            text = f"{emoji} <b>{symbol} - Histórico</b>\n"
            text += f"<i>{period_text} • {now.strftime('%d/%m/%Y %H:%M')}</i>\n\n"
            
            if not history['trades']:
                keyboard = self._create_inline_keyboard([
                    [("📊 Status", f"bot_detail_{symbol}"), ("📆 7 dias", f"bot_hist_{symbol}_7")],
                ])
                text += "📭 Nenhum trade no período."
                await self._safe_reply(update, text, reply_markup=keyboard)
                return
            
            # Win rate bar
            wr = history['win_rate']
            wr_bar = ""
            for i in range(10):
                if i < int(wr / 10):
                    wr_bar += "🟩" if wr >= 50 else "🟧"
                else:
                    wr_bar += "⬜"
            
            pnl_emoji = "📈" if history['total_pnl'] >= 0 else "📉"
            
            text += f"<b>{pnl_emoji} Resumo:</b>\n"
            text += f"├ Trades: {history['total_trades']}\n"
            text += f"├ ✅ Ganhos: {history['wins']}\n"
            text += f"├ ❌ Perdas: {history['losses']}\n"
            text += f"├ Win Rate: {wr_bar} {history['win_rate']:.1f}%\n"
            text += f"├ P&L Total: <code>${history['total_pnl']:+,.2f}</code>\n"
            text += f"├ 🏆 Melhor: <code>+${history['best_trade']:.2f}</code>\n"
            text += f"└ 💀 Pior: <code>-${abs(history['worst_trade']):.2f}</code>\n\n"
            
            text += f"<b>📜 Últimos Trades:</b>\n"
            for trade in history['trades'][-5:]:
                emoji_t = "✅" if trade['pnl'] >= 0 else "❌"
                direction = "🟢" if trade['direction'].lower() == 'buy' else "🔴"
                text += f"{emoji_t} {direction} <code>${trade['pnl']:+,.2f}</code> ({trade['time']})\n"
            
            # Botões
            buttons = [
                [("📅 Hoje", f"bot_hist_{symbol}_1"), ("📆 7d", f"bot_hist_{symbol}_7"), ("🗓️ 30d", f"bot_hist_{symbol}_30")],
                [("📊 Status", f"bot_detail_{symbol}"), ("📈 Métricas", f"bot_metrics_{symbol}")],
            ]
            
            keyboard = self._create_inline_keyboard(buttons)
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_bot_history: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    async def _get_bot_history(self, symbol: str, days: int) -> Dict[str, Any]:
        """Coleta histórico do bot."""
        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'trades': [],
        }
    
    # ========================================================================
    # CONFIGURAÇÃO
    # ========================================================================
    
    async def cmd_bot_config(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot_config [símbolo] - Configuração do bot."""
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "❌ Informe o símbolo: /bot_config XAUUSD"
            )
            return
        
        symbol = self._resolve_symbol(args[0])
        if not symbol:
            await update.message.reply_text(f"❌ Símbolo não reconhecido: {args[0]}")
            return
        
        config = await self._get_bot_config(symbol)
        emoji = self._format_symbol_emoji(symbol)
        
        text = f"""
{emoji} <b>{symbol} - Configuração</b>

<b>Estratégia:</b>
├ Tipo: {config['strategy']}
├ Timeframe: {config['timeframe']}
└ Indicators: {config['indicators']}

<b>Risco:</b>
├ Max Positions: {config['max_positions']}
├ Lot Size: {config['lot_size']}
├ SL (pips): {config['sl_pips']}
├ TP (pips): {config['tp_pips']}
└ Risk %: {config['risk_percent']}%

<b>Filtros:</b>
├ News Filter: {'✅' if config['news_filter'] else '❌'}
├ Session Filter: {'✅' if config['session_filter'] else '❌'}
└ Correlation Filter: {'✅' if config['correlation_filter'] else '❌'}

<b>Schedule:</b>
├ Start: {config['start_hour']}:00
└ End: {config['end_hour']}:00
        """
        
        await update.message.reply_text(
            text.strip(),
            parse_mode="HTML"
        )
    
    async def _get_bot_config(self, symbol: str) -> Dict[str, Any]:
        """Coleta configuração do bot."""
        return {
            'strategy': 'TrendStrategy',
            'timeframe': 'M15',
            'indicators': 'EMA, RSI, ATR',
            'max_positions': 3,
            'lot_size': 0.01,
            'sl_pips': 50,
            'tp_pips': 100,
            'risk_percent': 1.0,
            'news_filter': True,
            'session_filter': True,
            'correlation_filter': True,
            'start_hour': 8,
            'end_hour': 22,
        }
    
    # =========================================================================
    # CONTROLE
    # =========================================================================
    
    @track_command(CommandCategory.CONTROL)
    @require_role(UserRole.TRADER)
    async def cmd_bot_pause(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot_pause [símbolo] - Pausa o bot (requer TRADER+)."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /bot_pause de {user.username or user.id}")
            
            args = context.args
            
            if not args:
                await self._safe_reply(
                    update,
                    "❌ Informe o símbolo: /bot_pause XAUUSD"
                )
                return
            
            symbol = self._resolve_symbol(args[0])
            if not symbol:
                await self._safe_reply(update, f"❌ Símbolo não reconhecido: {args[0]}")
                return
            
            if self.orchestrator:
                await self.orchestrator.pause_bot(symbol)
            
            emoji = self._format_symbol_emoji(symbol)
            
            keyboard = self._create_inline_keyboard([
                [("▶️ Retomar", f"bot_resume_{symbol}"), ("📊 Status", f"bot_detail_{symbol}")],
            ])
            
            await self._safe_reply(
                update,
                f"{emoji} <b>{symbol}</b>\n\n"
                f"⏸️ <b>Bot pausado com sucesso</b>\n\n"
                f"Executado por: @{user.username or user.first_name}\n"
                f"Horário: {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"Use /bot_resume {symbol} ou o botão para retomar.",
                reply_markup=keyboard
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_bot_pause: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    @track_command(CommandCategory.CONTROL)
    @require_role(UserRole.TRADER)
    async def cmd_bot_resume(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot_resume [símbolo] - Retoma o bot (requer TRADER+)."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /bot_resume de {user.username or user.id}")
            
            args = context.args
            
            if not args:
                await self._safe_reply(
                    update,
                    "❌ Informe o símbolo: /bot_resume XAUUSD"
                )
                return
            
            symbol = self._resolve_symbol(args[0])
            if not symbol:
                await self._safe_reply(update, f"❌ Símbolo não reconhecido: {args[0]}")
                return
            
            if self.orchestrator:
                await self.orchestrator.resume_bot(symbol)
            
            emoji = self._format_symbol_emoji(symbol)
            
            keyboard = self._create_inline_keyboard([
                [("📊 Status", f"bot_detail_{symbol}"), ("📈 Posições", f"bot_pos_{symbol}")],
            ])
            
            await self._safe_reply(
                update,
                f"{emoji} <b>{symbol}</b>\n\n"
                f"▶️ <b>Bot retomado com sucesso</b>\n\n"
                f"Executado por: @{user.username or user.first_name}\n"
                f"Horário: {datetime.now().strftime('%H:%M:%S')}\n\n"
                "Operações voltando ao normal.",
                reply_markup=keyboard
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_bot_resume: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    @track_command(CommandCategory.CONTROL)
    @require_role(UserRole.TRADER)
    async def cmd_bot_close(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot_close [símbolo] - Fecha posições do bot (requer TRADER+)."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /bot_close de {user.username or user.id}")
            
            args = context.args
            
            if not args:
                await self._safe_reply(
                    update,
                    "❌ Informe o símbolo: /bot_close XAUUSD"
                )
                return
            
            symbol = self._resolve_symbol(args[0])
            if not symbol:
                await self._safe_reply(update, f"❌ Símbolo não reconhecido: {args[0]}")
                return
            
            emoji = self._format_symbol_emoji(symbol)
            
            # Armazena confirmação pendente
            self._pending_confirmations[user.id] = {
                'command': 'bot_close',
                'symbol': symbol,
                'timestamp': datetime.now(),
                'expires': datetime.now() + timedelta(minutes=2),
            }
            
            keyboard = self._create_inline_keyboard([
                [("⛔ CONFIRMAR FECHAMENTO", f"confirm_close_{symbol}")],
                [("❌ Cancelar", f"cancel_close_{symbol}")],
            ])
            
            await self._safe_reply(
                update,
                f"{emoji} <b>{symbol}</b>\n\n"
                f"⚠️ <b>ATENÇÃO:</b> Este comando irá:\n\n"
                f"1. Fechar TODAS as posições de {symbol}\n"
                f"2. Esta ação é IRREVERSÍVEL\n\n"
                f"❗ Expira em: 2 minutos\n\n"
                "Clique no botão para confirmar.",
                reply_markup=keyboard
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_bot_close: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    @track_command(CommandCategory.CONTROL)
    @require_role(UserRole.TRADER)
    async def cmd_bot_close_confirm(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot_close_confirm [símbolo] - Confirma fechamento."""
        try:
            user = update.effective_user
            args = context.args
            
            if not args:
                await self._safe_reply(update, "❌ Comando incompleto.")
                return
            
            symbol = self._resolve_symbol(args[0])
            if not symbol:
                await self._safe_reply(update, f"❌ Símbolo não reconhecido: {args[0]}")
                return
            
            # Verifica se há confirmação pendente
            pending = self._pending_confirmations.get(user.id)
            if not pending or pending.get('symbol') != symbol:
                await self._safe_reply(
                    update,
                    f"❌ Nenhuma confirmação pendente para {symbol}.\n"
                    f"Use /bot_close {symbol} primeiro."
                )
                return
            
            # Verifica se expirou
            if datetime.now() > pending['expires']:
                del self._pending_confirmations[user.id]
                await self._safe_reply(
                    update,
                    f"⏰ Confirmação expirada.\n"
                    f"Use /bot_close {symbol} novamente."
                )
                return
            
            # Remove confirmação pendente
            del self._pending_confirmations[user.id]
            
            self.logger.warning(f"Fechamento de posições {symbol} por {user.username or user.id}")
            
            if self.orchestrator:
                await self.orchestrator.close_all_positions(symbol)
            
            emoji = self._format_symbol_emoji(symbol)
            
            await self._safe_reply(
                update,
                f"{emoji} <b>{symbol}</b>\n\n"
                f"✅ <b>Todas as posições foram fechadas</b>\n\n"
                f"Executado por: @{user.username or user.first_name}\n"
                f"Horário: {datetime.now().strftime('%H:%M:%S')}"
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_bot_close_confirm: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    # ========================================================================
    # MÉTRICAS DETALHADAS
    # ========================================================================
    
    async def cmd_bot_metrics(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bot_metrics [símbolo] - Métricas detalhadas."""
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "❌ Informe o símbolo: /bot_metrics XAUUSD"
            )
            return
        
        symbol = self._resolve_symbol(args[0])
        if not symbol:
            await update.message.reply_text(f"❌ Símbolo não reconhecido: {args[0]}")
            return
        
        metrics = await self._get_bot_metrics(symbol)
        emoji = self._format_symbol_emoji(symbol)
        
        text = f"""
{emoji} <b>{symbol} - Métricas Completas</b>

<b>📊 Performance:</b>
├ Total P&L: ${metrics['total_pnl']:+,.2f}
├ Profit Factor: {metrics['profit_factor']:.2f}
├ Win Rate: {metrics['win_rate']:.1f}%
├ Avg Win: ${metrics['avg_win']:.2f}
├ Avg Loss: ${metrics['avg_loss']:.2f}
└ Expectancy: ${metrics['expectancy']:.2f}

<b>📈 Trades:</b>
├ Total: {metrics['total_trades']}
├ Wins: {metrics['wins']}
├ Losses: {metrics['losses']}
├ Breakeven: {metrics['breakeven']}
└ Max Consecutive Losses: {metrics['max_consecutive_losses']}

<b>📉 Risco:</b>
├ Max Drawdown: {metrics['max_drawdown']:.2f}%
├ Avg Drawdown: {metrics['avg_drawdown']:.2f}%
├ Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
└ Recovery Factor: {metrics['recovery_factor']:.2f}

<b>⏱️ Tempo:</b>
├ Avg Trade Duration: {metrics['avg_duration']}
├ Longest Win: {metrics['longest_win']}
└ Longest Loss: {metrics['longest_loss']}
        """
        
        await update.message.reply_text(
            text.strip(),
            parse_mode="HTML"
        )
    
    async def _get_bot_metrics(self, symbol: str) -> Dict[str, Any]:
        """Coleta métricas do bot."""
        return {
            'total_pnl': 0.0,
            'profit_factor': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'breakeven': 0,
            'max_consecutive_losses': 0,
            'max_drawdown': 0.0,
            'avg_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'recovery_factor': 0.0,
            'avg_duration': '0h',
            'longest_win': '0h',
            'longest_loss': '0h',
        }
    
    # =========================================================================
    # CALLBACK HANDLERS
    # =========================================================================
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Handler para botões inline do bot."""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            user = update.effective_user
            
            self.logger.info(f"Bot callback '{data}' de {user.username or user.id}")
            
            # Mapeia callbacks para ações
            if data == "refresh_all_bots":
                await self._show_all_bots(update)
            
            elif data.startswith("bot_detail_"):
                symbol = data.replace("bot_detail_", "")
                await self._show_bot_status(update, symbol)
            
            elif data.startswith("bot_pos_"):
                symbol = data.replace("bot_pos_", "")
                context.args = [symbol]
                await self.cmd_bot_positions(update, context)
            
            elif data.startswith("bot_hist_"):
                parts = data.replace("bot_hist_", "").split("_")
                symbol = parts[0]
                days = int(parts[1]) if len(parts) > 1 else 1
                context.args = [symbol, str(days)]
                await self.cmd_bot_history(update, context)
            
            elif data.startswith("bot_cfg_"):
                symbol = data.replace("bot_cfg_", "")
                context.args = [symbol]
                await self.cmd_bot_config(update, context)
            
            elif data.startswith("bot_metrics_"):
                symbol = data.replace("bot_metrics_", "")
                context.args = [symbol]
                await self.cmd_bot_metrics(update, context)
            
            elif data.startswith("bot_pause_"):
                symbol = data.replace("bot_pause_", "")
                context.args = [symbol]
                await self.cmd_bot_pause(update, context)
            
            elif data.startswith("bot_resume_"):
                symbol = data.replace("bot_resume_", "")
                context.args = [symbol]
                await self.cmd_bot_resume(update, context)
            
            elif data.startswith("bot_close_"):
                symbol = data.replace("bot_close_", "")
                context.args = [symbol]
                await self.cmd_bot_close(update, context)
            
            elif data.startswith("confirm_close_"):
                symbol = data.replace("confirm_close_", "")
                context.args = [symbol]
                await self.cmd_bot_close_confirm(update, context)
            
            elif data.startswith("cancel_close_"):
                symbol = data.replace("cancel_close_", "")
                if user.id in self._pending_confirmations:
                    del self._pending_confirmations[user.id]
                await query.edit_message_text(f"❌ Operação cancelada para {symbol}.")
            
            else:
                self.logger.warning(f"Bot callback desconhecido: {data}")
                
        except Exception as e:
            self.logger.error(f"Erro no handle_callback: {e}", exc_info=True)
    
    # =========================================================================
    # REGISTRO DE HANDLERS
    # =========================================================================
    
    def register_handlers(self, application) -> None:
        """
        Registra handlers no Application do telegram.
        
        Args:
            application: telegram.ext.Application
        """
        from telegram.ext import CommandHandler, CallbackQueryHandler
        
        handlers = [
            # Status
            CommandHandler("bot", self.cmd_bot),
            CommandHandler("bot_status", self.cmd_bot_status),
            
            # Posições e Histórico
            CommandHandler("bot_positions", self.cmd_bot_positions),
            CommandHandler("bot_history", self.cmd_bot_history),
            
            # Configuração
            CommandHandler("bot_config", self.cmd_bot_config),
            CommandHandler("bot_metrics", self.cmd_bot_metrics),
            
            # Controle
            CommandHandler("bot_pause", self.cmd_bot_pause),
            CommandHandler("bot_resume", self.cmd_bot_resume),
            CommandHandler("bot_close", self.cmd_bot_close),
            CommandHandler("bot_close_confirm", self.cmd_bot_close_confirm),
            
            # Callback handler para botões inline
            CallbackQueryHandler(self.handle_callback, pattern="^bot_|^confirm_close_|^cancel_close_|^refresh_all_bots"),
        ]
        
        for handler in handlers:
            application.add_handler(handler)
        
        self.logger.info(f"BotCommands: {len(handlers)} handlers registrados")
