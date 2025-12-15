"""
VIRTUS Global Telegram Commands
================================

Comandos globais para gerenciamento do sistema VIRTUS.
Inclui status geral, controle de bots, risco global, etc.

Features:
- Rate limiting por usuário
- Sistema de autorização por níveis
- Inline keyboards para ações rápidas
- Métricas de uso e latência
- Typing indicator durante processamento
- Confirmação 2-passos para comandos perigosos
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, TYPE_CHECKING
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
logger = logging.getLogger("virtus.telegram.commands")


# =============================================================================
# ENUMS E DATACLASSES
# =============================================================================

class UserRole(Enum):
    """Níveis de autorização do usuário."""
    VIEWER = "viewer"      # Apenas visualização
    TRADER = "trader"      # Pode operar
    ADMIN = "admin"        # Controle total


class CommandCategory(Enum):
    """Categorias de comandos para métricas."""
    STATUS = "status"
    TRADING = "trading"
    RISK = "risk"
    CONTROL = "control"
    INFO = "info"


@dataclass
class RateLimitConfig:
    """Configuração de rate limiting."""
    max_requests: int = 30      # Máximo de requisições
    window_seconds: int = 60    # Janela de tempo
    cooldown_seconds: int = 60  # Cooldown se exceder


@dataclass
class CommandMetrics:
    """Métricas de um comando."""
    name: str
    calls: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    last_called: Optional[datetime] = None
    
    @property
    def avg_latency_ms(self) -> float:
        """Latência média em ms."""
        return self.total_latency_ms / max(1, self.calls)
    
    def record_call(self, latency_ms: float, error: bool = False) -> None:
        """Registra uma chamada."""
        self.calls += 1
        self.total_latency_ms += latency_ms
        self.last_called = datetime.now()
        if error:
            self.errors += 1


@dataclass
class UserRateLimit:
    """Estado de rate limit de um usuário."""
    user_id: int
    requests: List[datetime] = field(default_factory=list)
    blocked_until: Optional[datetime] = None
    
    def is_blocked(self) -> bool:
        """Verifica se usuário está bloqueado."""
        if self.blocked_until and datetime.now() < self.blocked_until:
            return True
        return False
    
    def check_and_record(self, config: RateLimitConfig) -> bool:
        """
        Verifica rate limit e registra requisição.
        
        Returns:
            True se permitido, False se bloqueado
        """
        now = datetime.now()
        
        # Se está bloqueado
        if self.is_blocked():
            return False
        
        # Remove requisições antigas
        cutoff = now - timedelta(seconds=config.window_seconds)
        self.requests = [r for r in self.requests if r > cutoff]
        
        # Verifica limite
        if len(self.requests) >= config.max_requests:
            self.blocked_until = now + timedelta(seconds=config.cooldown_seconds)
            return False
        
        # Registra
        self.requests.append(now)
        return True


@dataclass
class CommandResponse:
    """Resposta de um comando."""
    text: str
    parse_mode: str = "HTML"
    reply_markup: Any = None
    disable_preview: bool = True


# =============================================================================
# DECORATORS
# =============================================================================

def require_role(min_role: UserRole):
    """
    Decorator que requer nível mínimo de autorização.
    
    Usage:
        @require_role(UserRole.ADMIN)
        async def cmd_dangerous(self, update, context):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
            user_id = update.effective_user.id
            user_role = self._get_user_role(user_id)
            
            # Hierarquia: ADMIN > TRADER > VIEWER
            role_hierarchy = {UserRole.VIEWER: 0, UserRole.TRADER: 1, UserRole.ADMIN: 2}
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(min_role, 0):
                await self._safe_reply(
                    update,
                    f"🔒 <b>Acesso Negado</b>\n\nEste comando requer nível: <code>{min_role.value}</code>"
                )
                self.logger.warning(f"Acesso negado para {user_id} em {func.__name__}")
                return
            
            return await func(self, update, context, *args, **kwargs)
        return wrapper
    return decorator


def track_command(category: CommandCategory):
    """
    Decorator que rastreia métricas do comando.
    
    Usage:
        @track_command(CommandCategory.STATUS)
        async def cmd_status(self, update, context):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
            start_time = time.perf_counter()
            error = False
            
            try:
                result = await func(self, update, context, *args, **kwargs)
                return result
            except Exception as e:
                error = True
                raise
            finally:
                latency_ms = (time.perf_counter() - start_time) * 1000
                self._record_metrics(func.__name__, latency_ms, error, category)
        return wrapper
    return decorator


def with_typing(func: Callable):
    """
    Decorator que mostra 'typing...' durante execução.
    
    Usage:
        @with_typing
        async def cmd_slow(self, update, context):
            ...
    """
    @wraps(func)
    async def wrapper(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", *args, **kwargs):
        try:
            await update.message.chat.send_action("typing")
        except:
            pass
        return await func(self, update, context, *args, **kwargs)
    return wrapper


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class GlobalCommands:
    """
    Comandos globais do sistema VIRTUS.
    
    Comandos disponíveis:
    - /start - Mensagem de boas-vindas
    - /status - Status geral do sistema
    - /bots - Lista todos os bots
    - /risk - Métricas de risco global
    - /equity - Informações de capital
    - /positions - Todas as posições abertas
    - /today - Resumo do dia
    - /help - Lista de comandos
    - /metrics - Métricas de uso (admin)
    
    Features:
    - Rate limiting por usuário (30 req/min)
    - 3 níveis de autorização (viewer, trader, admin)
    - Métricas de latência e uso
    - Confirmação 2-passos para comandos perigosos
    """
    
    # IDs de usuários autorizados (configurável via __init__)
    DEFAULT_ADMINS = {7005082427}  # Seu chat_id
    DEFAULT_TRADERS = set()
    
    def __init__(
        self, 
        orchestrator=None, 
        risk_manager=None,
        admin_ids: Optional[set] = None,
        trader_ids: Optional[set] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Inicializa comandos globais.
        
        Args:
            orchestrator: Orquestrador de bots (opcional)
            risk_manager: GlobalRiskManager (opcional)
            admin_ids: IDs de administradores
            trader_ids: IDs de traders
            rate_limit_config: Configuração de rate limiting
        """
        self.orchestrator = orchestrator
        self.risk_manager = risk_manager
        self.logger = logger
        
        # Autorização
        self._admin_ids = admin_ids or self.DEFAULT_ADMINS
        self._trader_ids = trader_ids or self.DEFAULT_TRADERS
        
        # Rate limiting
        self._rate_config = rate_limit_config or RateLimitConfig()
        self._rate_limits: Dict[int, UserRateLimit] = {}
        
        # Métricas
        self._metrics: Dict[str, CommandMetrics] = {}
        self._start_time = datetime.now()
        
        # Pending confirmations (para comandos perigosos)
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
        """
        Verifica rate limit do usuário.
        
        Returns:
            True se permitido, False se bloqueado
        """
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = UserRateLimit(user_id=user_id)
        
        return self._rate_limits[user_id].check_and_record(self._rate_config)
    
    def _record_metrics(
        self, 
        command: str, 
        latency_ms: float, 
        error: bool,
        category: CommandCategory
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
        disable_preview: bool = True,
    ) -> bool:
        """
        Reply seguro com tratamento de erro.
        
        Returns:
            True se enviou com sucesso
        """
        try:
            if update and update.message:
                await update.message.reply_text(
                    text, 
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    disable_web_page_preview=disable_preview,
                )
                return True
        except Exception as e:
            self.logger.error(f"Erro ao enviar resposta: {e}")
        return False
    
    async def _check_and_reply_rate_limit(self, update: "Update") -> bool:
        """
        Verifica rate limit e responde se bloqueado.
        
        Returns:
            True se permitido continuar, False se bloqueado
        """
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
        """
        Cria teclado inline.
        
        Args:
            buttons: Lista de linhas, cada linha é lista de (texto, callback_data)
        """
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
    
    # =========================================================================
    # COMANDOS BÁSICOS
    # =========================================================================
    
    @track_command(CommandCategory.INFO)
    async def cmd_start(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /start - Mensagem de boas-vindas."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            user_role = self._get_user_role(user.id)
            self.logger.info(f"Comando /start de {user.username or user.id} (role: {user_role.value})")
            
            # Botões rápidos
            keyboard = self._create_inline_keyboard([
                [("📊 Status", "quick_status"), ("💰 Equity", "quick_equity")],
                [("📈 Posições", "quick_positions"), ("⚠️ Risco", "quick_risk")],
            ])
            
            welcome_text = f"""
🤖 <b>VIRTUS Trading System</b>

Olá, <b>{user.first_name or 'Trader'}</b>!
Seu nível de acesso: <code>{user_role.value}</code>

<b>Comandos disponíveis:</b>

📊 <b>Status</b>
/status - Status geral do sistema
/bots - Lista de bots ativos
/positions - Posições abertas

💰 <b>Capital</b>
/equity - Informações de capital
/risk - Métricas de risco
/drawdown - Status de drawdown

📈 <b>Performance</b>
/today - Resumo do dia
/week - Resumo da semana
/month - Resumo do mês

🔧 <b>Controle</b> {'(restrito)' if user_role == UserRole.VIEWER else ''}
/pause - Pausa todos os bots
/resume - Retoma todos os bots
/emergency - Fecha tudo (EMERGÊNCIA)

ℹ️ /help - Lista completa de comandos
            """
            await self._safe_reply(update, welcome_text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_start: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    @track_command(CommandCategory.INFO)
    async def cmd_help(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /help - Lista de comandos."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            user_role = self._get_user_role(user.id)
            self.logger.info(f"Comando /help de {user.username or user.id}")
            
            help_text = """
📖 <b>VIRTUS - Lista de Comandos</b>

<b>🌐 Comandos Globais</b>
/start - Iniciar bot
/status - Status do sistema
/bots - Lista de bots
/positions - Posições abertas
/equity - Capital e margem
/risk - Métricas de risco
/drawdown - Status drawdown

<b>🤖 Comandos por Bot</b>
/bot_status [símbolo] - Status de um bot
/bot_positions [símbolo] - Posições do bot
/bot_history [símbolo] - Histórico do bot
/bot_pause [símbolo] - Pausa um bot
/bot_resume [símbolo] - Retoma um bot

<b>🧠 Comandos do Brain</b>
/brain_status - Status do Brain
/brain_analysis [símbolo] - Análise completa
/brain_sentiment - Sentimento de mercado
/brain_news - Últimas notícias

<b>📊 Comandos do Advisor</b>
/briefing - Briefing diário
/calendar - Calendário econômico
/outlook [símbolo] - Perspectiva do ativo
"""
            # Adiciona comandos de controle se tem permissão
            if user_role in (UserRole.TRADER, UserRole.ADMIN):
                help_text += """
<b>⚠️ Controle</b>
/pause - Pausa todos os bots
/resume - Retoma todos os bots
/emergency - Encerramento de emergência
"""
            
            # Adiciona comandos admin
            if user_role == UserRole.ADMIN:
                help_text += """
<b>🔧 Admin</b>
/metrics - Métricas de uso
/users - Gerenciar usuários
"""
            
            await self._safe_reply(update, help_text.strip())
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_help: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    @track_command(CommandCategory.STATUS)
    @with_typing
    async def cmd_status(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /status - Status geral do sistema com inline keyboards."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            user_role = self._get_user_role(user.id)
            self.logger.info(f"Comando /status de {user.username or user.id}")
            
            now = datetime.now()
            
            # Coleta informações
            status = await self._get_system_status()
            
            # Indicadores visuais
            system_emoji = "🟢" if status['system_state'] == 'Online' else "🔴"
            risk_emoji = {
                'Normal': '🟢', 'Elevated': '🟡', 'High': '🟠', 
                'Critical': '🔴', 'Emergency': '⛔'
            }.get(status['risk_level'], '⚪')
            
            pnl_emoji = "📈" if status['daily_pnl'] >= 0 else "📉"
            
            text = f"""
🖥️ <b>VIRTUS System Status</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

<b>Sistema:</b> {system_emoji} {status['system_state']}
<b>Uptime:</b> {status['uptime']}
<b>Modo:</b> {status['trading_mode']}

<b>📊 Bots:</b>
├ 🟢 Ativos: {status['active_bots']}
├ 🟡 Pausados: {status['paused_bots']}
└ 🔴 Bloqueados: {status['blocked_bots']}

<b>💰 Capital:</b>
├ Equity: ${status['equity']:,.2f}
├ Balance: ${status['balance']:,.2f}
└ Floating: ${status['floating']:+,.2f}

<b>📈 Posições:</b>
├ Total: {status['open_positions']}
├ Long: {status['long_positions']}
└ Short: {status['short_positions']}

<b>📉 Risco:</b>
├ Estado: {risk_emoji} {status['risk_level']}
├ Drawdown: {status['drawdown']:.2f}%
└ {pnl_emoji} Daily P&L: ${status['daily_pnl']:+,.2f}
            """
            
            # Botões de ação rápida
            buttons = [[("🔄 Refresh", "refresh_status"), ("📊 Detalhes", "detail_status")]]
            
            # Adiciona botões de controle se tem permissão
            if user_role in (UserRole.TRADER, UserRole.ADMIN):
                buttons.append([("⏸️ Pause All", "action_pause"), ("▶️ Resume All", "action_resume")])
            
            keyboard = self._create_inline_keyboard(buttons)
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_status: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro ao obter status: {e}")
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Coleta status do sistema."""
        # Default values se não há conexão
        status = {
            'system_state': '🟢 Online',
            'uptime': 'N/A',
            'trading_mode': 'Full',
            'active_bots': 0,
            'paused_bots': 0,
            'blocked_bots': 0,
            'equity': 0.0,
            'balance': 0.0,
            'floating': 0.0,
            'open_positions': 0,
            'long_positions': 0,
            'short_positions': 0,
            'drawdown': 0.0,
            'daily_pnl': 0.0,
            'risk_level': 'Normal',
        }
        
        # Se tiver orquestrador, pega dados reais
        if self.orchestrator:
            try:
                orch_status = await self.orchestrator.get_status()
                status.update(orch_status)
            except:
                pass
        
        # Se tiver risk manager
        if self.risk_manager:
            try:
                risk_metrics = self.risk_manager.get_metrics()
                status['drawdown'] = risk_metrics.global_drawdown
                status['risk_level'] = risk_metrics.state.value
                status['trading_mode'] = risk_metrics.trading_mode.value
            except:
                pass
        
        return status
    
    @track_command(CommandCategory.STATUS)
    @with_typing
    async def cmd_bots(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /bots - Lista todos os bots com inline keyboards."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            user_role = self._get_user_role(user.id)
            self.logger.info(f"Comando /bots de {user.username or user.id}")
            
            bots = await self._get_bots_info()
            
            if not bots:
                await self._safe_reply(update, "❌ Nenhum bot registrado.")
                return
            
            now = datetime.now()
            text = f"""
🤖 <b>VIRTUS - Bots Ativos</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

"""
            
            total_pnl = 0.0
            total_positions = 0
            
            for bot in bots:
                status_emoji = "🟢" if bot['active'] else ("🔴" if bot['blocked'] else "🟡")
                pnl_emoji = "+" if bot['daily_pnl'] >= 0 else ""
                total_pnl += bot['daily_pnl']
                total_positions += bot['positions']
                
                text += f"{status_emoji} <b>{bot['symbol']}</b>\n"
                text += f"   ├ Posições: {bot['positions']}\n"
                text += f"   ├ P&L Dia: {pnl_emoji}${bot['daily_pnl']:,.2f}\n"
                text += f"   ├ Win Rate: {bot.get('win_rate', 0):.1f}%\n"
                text += f"   └ Status: {bot['status']}\n\n"
            
            total_pnl_emoji = "📈" if total_pnl >= 0 else "📉"
            text += f"""
<b>━━━━━━━━━━━━━━━</b>
{total_pnl_emoji} <b>Total P&L:</b> ${total_pnl:+,.2f}
📊 <b>Total Posições:</b> {total_positions}
"""
            
            # Botões para cada bot
            bot_buttons = []
            for bot in bots:
                symbol = bot['symbol']
                bot_buttons.append([
                    (f"📊 {symbol}", f"bot_detail_{symbol}"),
                    (f"⏸️" if bot['active'] else "▶️", f"bot_toggle_{symbol}"),
                ])
            
            keyboard = self._create_inline_keyboard(bot_buttons)
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_bots: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro ao obter bots: {e}")
    
    async def _get_bots_info(self) -> List[Dict[str, Any]]:
        """Coleta informações de todos os bots."""
        bots = []
        
        # Símbolos padrão
        symbols = ['XAUUSD', 'EURUSD', 'GBPUSD']
        
        for symbol in symbols:
            bots.append({
                'symbol': symbol,
                'active': True,
                'blocked': False,
                'positions': 0,
                'daily_pnl': 0.0,
                'status': 'Operando',
            })
        
        return bots
    
    # =========================================================================
    # CAPITAL E RISCO
    # =========================================================================
    
    @track_command(CommandCategory.STATUS)
    @with_typing
    async def cmd_equity(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /equity - Informações detalhadas de capital."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /equity de {user.username or user.id}")
            
            equity_info = await self._get_equity_info()
            now = datetime.now()
            
            # Indicadores visuais
            margin_pct = (equity_info['margin_used'] / equity_info['equity'] * 100) if equity_info['equity'] > 0 else 0
            margin_bar = "█" * int(margin_pct / 10) + "░" * (10 - int(margin_pct / 10))
            
            pnl_today_emoji = "📈" if equity_info['pnl_today'] >= 0 else "📉"
            pnl_week_emoji = "📈" if equity_info['pnl_week'] >= 0 else "📉"
            pnl_month_emoji = "📈" if equity_info['pnl_month'] >= 0 else "📉"
            
            text = f"""
💰 <b>VIRTUS - Capital</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

<b>Conta:</b>
├ Equity: <code>${equity_info['equity']:,.2f}</code>
├ Balance: <code>${equity_info['balance']:,.2f}</code>
├ Margem Usada: <code>${equity_info['margin_used']:,.2f}</code>
└ Margem Livre: <code>${equity_info['margin_free']:,.2f}</code>

<b>Uso de Margem:</b>
{margin_bar} {margin_pct:.1f}%

<b>Exposição:</b>
├ Gross: <code>${equity_info['gross_exposure']:,.2f}</code>
├ Net: <code>${equity_info['net_exposure']:+,.2f}</code>
└ % Equity: {equity_info['exposure_pct']:.1f}%

<b>Performance:</b>
├ {pnl_today_emoji} Hoje: <code>${equity_info['pnl_today']:+,.2f}</code>
├ {pnl_week_emoji} Semana: <code>${equity_info['pnl_week']:+,.2f}</code>
└ {pnl_month_emoji} Mês: <code>${equity_info['pnl_month']:+,.2f}</code>
            """
            
            keyboard = self._create_inline_keyboard([
                [("📊 Por Símbolo", "equity_by_symbol"), ("📈 Gráfico", "equity_chart")],
                [("🔄 Refresh", "refresh_equity")],
            ])
            
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_equity: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro ao obter capital: {e}")
    
    async def _get_equity_info(self) -> Dict[str, float]:
        """Coleta informações de capital."""
        return {
            'equity': 10000.0,
            'balance': 10000.0,
            'margin_used': 0.0,
            'margin_free': 10000.0,
            'gross_exposure': 0.0,
            'net_exposure': 0.0,
            'exposure_pct': 0.0,
            'pnl_today': 0.0,
            'pnl_week': 0.0,
            'pnl_month': 0.0,
        }
    
    @track_command(CommandCategory.RISK)
    @with_typing
    async def cmd_risk(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /risk - Métricas de risco global com visualização avançada."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /risk de {user.username or user.id}")
            
            risk = await self._get_risk_metrics()
            now = datetime.now()
            
            # Emoji baseado no nível
            level_emoji = {
                'normal': '🟢',
                'elevated': '🟡',
                'high': '🟠',
                'critical': '🔴',
                'emergency': '⛔',
            }
            emoji = level_emoji.get(risk['state'].lower(), '⚪')
            
            # Barras de progresso
            dd_pct = min(100, int(risk['drawdown'] / risk['drawdown_limit'] * 100)) if risk['drawdown_limit'] > 0 else 0
            dd_bar = "█" * (dd_pct // 10) + "░" * (10 - dd_pct // 10)
            
            exp_pct = min(100, int(risk['exposure_pct'] / risk['exposure_limit'] * 100)) if risk['exposure_limit'] > 0 else 0
            exp_bar = "█" * (exp_pct // 10) + "░" * (10 - exp_pct // 10)
            
            loss_pct = min(100, int(abs(risk['daily_loss']) / risk['daily_loss_limit'] * 100)) if risk['daily_loss_limit'] > 0 else 0
            loss_bar = "█" * (loss_pct // 10) + "░" * (10 - loss_pct // 10)
            
            text = f"""
⚠️ <b>VIRTUS - Métricas de Risco</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

<b>Estado:</b> {emoji} {risk['state']}
<b>Modo:</b> {risk['trading_mode']}

<b>📉 Drawdown:</b>
{dd_bar} {risk['drawdown']:.2f}% / {risk['drawdown_limit']:.1f}%
├ Máximo: {risk['max_drawdown']:.2f}%
└ Limite: {risk['drawdown_limit']:.1f}%

<b>📊 Exposição:</b>
{exp_bar} {risk['exposure_pct']:.1f}% / {risk['exposure_limit']:.1f}%
├ Correlacionada: {risk['correlated_pct']:.1f}%
└ Limite: {risk['exposure_limit']:.1f}%

<b>📈 Posições:</b>
├ Abertas: {risk['positions']} / {risk['position_limit']}
├ Por Símbolo: máx {risk['max_per_symbol']}
└ Limite Global: {risk['position_limit']}

<b>💸 Daily Loss:</b>
{loss_bar} ${abs(risk['daily_loss']):,.2f} / ${risk['daily_loss_limit']:,.2f}
            """
            
            keyboard = self._create_inline_keyboard([
                [("📊 Por Símbolo", "risk_by_symbol"), ("📈 Histórico", "risk_history")],
                [("🔄 Refresh", "refresh_risk")],
            ])
            
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_risk: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro ao obter risco: {e}")
    
    async def _get_risk_metrics(self) -> Dict[str, Any]:
        """Coleta métricas de risco."""
        return {
            'state': 'Normal',
            'trading_mode': 'Full',
            'drawdown': 0.0,
            'max_drawdown': 0.0,
            'drawdown_limit': 10.0,
            'exposure_pct': 0.0,
            'correlated_pct': 0.0,
            'exposure_limit': 100.0,
            'positions': 0,
            'max_per_symbol': 3,
            'position_limit': 15,
            'daily_loss': 0.0,
            'daily_loss_limit': 500.0,
        }
    
    @track_command(CommandCategory.RISK)
    @with_typing
    async def cmd_drawdown(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /drawdown - Status detalhado de drawdown com visualização."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /drawdown de {user.username or user.id}")
            
            dd = await self._get_drawdown_info()
            now = datetime.now()
            
            # Barra de progresso visual
            progress = min(100, int(dd['current'] / dd['limit'] * 100)) if dd['limit'] > 0 else 0
            bar_filled = progress // 10
            bar = ""
            for i in range(10):
                if i < bar_filled:
                    if progress < 50:
                        bar += "🟢"
                    elif progress < 75:
                        bar += "🟡"
                    elif progress < 90:
                        bar += "🟠"
                    else:
                        bar += "🔴"
                else:
                    bar += "⬜"
            
            # Determina estado
            if dd['current'] < dd['warning']:
                state = "🟢 Normal"
            elif dd['current'] < dd['danger']:
                state = "🟡 Elevado"
            elif dd['current'] < dd['critical']:
                state = "🟠 Alto"
            else:
                state = "🔴 Crítico"
            
            text = f"""
📉 <b>VIRTUS - Drawdown Monitor</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

<b>Estado:</b> {state}

<b>Drawdown Atual:</b>
{bar} <code>{dd['current']:.2f}%</code>

<b>Limites:</b>
├ ⚠️ Warning: {dd['warning']:.1f}%
├ 🟠 Danger: {dd['danger']:.1f}%
├ 🔴 Critical: {dd['critical']:.1f}%
└ ⛔ Stop: {dd['limit']:.1f}%

<b>Histórico:</b>
├ 📅 Máximo Hoje: {dd['max_today']:.2f}%
├ 📆 Máximo Semana: {dd['max_week']:.2f}%
└ 🗓️ Máximo Mês: {dd['max_month']:.2f}%

<b>Recovery:</b>
├ 💎 Peak Equity: <code>${dd['peak']:,.2f}</code>
├ 💰 Equity Atual: <code>${dd['current_equity']:,.2f}</code>
└ 🎯 Para Recuperar: <code>${dd['to_recover']:,.2f}</code>
            """
            
            keyboard = self._create_inline_keyboard([
                [("📈 Histórico DD", "drawdown_history"), ("📊 Gráfico", "drawdown_chart")],
                [("🔄 Refresh", "refresh_drawdown")],
            ])
            
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_drawdown: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro ao obter drawdown: {e}")
    
    async def _get_drawdown_info(self) -> Dict[str, float]:
        """Coleta informações de drawdown."""
        return {
            'current': 0.0,
            'limit': 10.0,
            'warning': 5.0,
            'danger': 7.5,
            'critical': 10.0,
            'max_today': 0.0,
            'max_week': 0.0,
            'max_month': 0.0,
            'peak': 10000.0,
            'current_equity': 10000.0,
            'to_recover': 0.0,
        }
    
    # =========================================================================
    # POSIÇÕES
    # =========================================================================
    
    @track_command(CommandCategory.STATUS)
    @with_typing
    async def cmd_positions(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /positions - Todas as posições abertas com detalhes."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            user_role = self._get_user_role(user.id)
            self.logger.info(f"Comando /positions de {user.username or user.id}")
            
            positions = await self._get_all_positions()
            now = datetime.now()
            
            if not positions:
                keyboard = self._create_inline_keyboard([
                    [("🔄 Refresh", "refresh_positions")],
                ])
                await self._safe_reply(
                    update, 
                    f"📭 <b>Nenhuma posição aberta</b>\n<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>",
                    reply_markup=keyboard
                )
                return
            
            text = f"""
📊 <b>VIRTUS - Posições Abertas</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

"""
            
            total_pnl = 0.0
            total_volume = 0.0
            positions_by_type = {'long': 0, 'short': 0}
            
            for i, pos in enumerate(positions, 1):
                direction = "🟢 LONG" if pos['type'] == 'long' else "🔴 SHORT"
                pnl_emoji = "+" if pos['pnl'] >= 0 else ""
                total_pnl += pos['pnl']
                total_volume += pos['volume']
                positions_by_type[pos['type']] += 1
                
                # Calcula % do SL/TP
                if pos['type'] == 'long':
                    sl_pct = ((pos['current'] - pos['sl']) / pos['current'] * 100) if pos['sl'] > 0 else 0
                    tp_pct = ((pos['tp'] - pos['current']) / pos['current'] * 100) if pos['tp'] > 0 else 0
                else:
                    sl_pct = ((pos['sl'] - pos['current']) / pos['current'] * 100) if pos['sl'] > 0 else 0
                    tp_pct = ((pos['current'] - pos['tp']) / pos['current'] * 100) if pos['tp'] > 0 else 0
                
                text += f"<b>#{i} {pos['symbol']}</b> {direction}\n"
                text += f"├ Volume: <code>{pos['volume']:.2f}</code> lots\n"
                text += f"├ Entry: <code>{pos['entry']:.5f}</code>\n"
                text += f"├ Current: <code>{pos['current']:.5f}</code>\n"
                text += f"├ SL: <code>{pos['sl']:.5f}</code> ({sl_pct:.1f}%)\n"
                text += f"├ TP: <code>{pos['tp']:.5f}</code> ({tp_pct:.1f}%)\n"
                text += f"├ Duração: {pos.get('duration', 'N/A')}\n"
                text += f"└ P&L: <code>{pnl_emoji}${pos['pnl']:.2f}</code>\n\n"
            
            total_emoji = "📈" if total_pnl >= 0 else "📉"
            text += f"""
<b>━━━━━━━━━━━━━━━</b>
{total_emoji} <b>Total P&L:</b> <code>${total_pnl:+,.2f}</code>
📊 <b>Total Volume:</b> <code>{total_volume:.2f}</code> lots
🟢 <b>Long:</b> {positions_by_type['long']} | 🔴 <b>Short:</b> {positions_by_type['short']}
"""
            
            # Botões de ação
            buttons = [[("🔄 Refresh", "refresh_positions")]]
            
            if user_role in (UserRole.TRADER, UserRole.ADMIN):
                buttons.append([("⚠️ Fechar Todas", "action_close_all")])
            
            keyboard = self._create_inline_keyboard(buttons)
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_positions: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro ao obter posições: {e}")
    
    async def _get_all_positions(self) -> List[Dict[str, Any]]:
        """Coleta todas as posições abertas."""
        # Retorna lista vazia se não há conexão
        return []
    
    # =========================================================================
    # RESUMOS
    # =========================================================================
    
    @track_command(CommandCategory.STATUS)
    @with_typing
    async def cmd_today(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /today - Resumo completo do dia com estatísticas."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /today de {user.username or user.id}")
            
            today = await self._get_today_summary()
            now = datetime.now()
            
            pnl_emoji = "📈" if today['pnl'] >= 0 else "📉"
            
            # Barra de win rate
            wr = today['win_rate']
            wr_bar = ""
            for i in range(10):
                if i < int(wr / 10):
                    wr_bar += "🟩" if wr >= 50 else "🟧"
                else:
                    wr_bar += "⬜"
            
            text = f"""
{pnl_emoji} <b>VIRTUS - Resumo de Hoje</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

<b>💰 Performance:</b>
├ P&L: <code>${today['pnl']:+,.2f}</code>
├ Return: <code>{today['return_pct']:+.2f}%</code>
└ Max Drawdown: {today['max_dd']:.2f}%

<b>📊 Trades:</b>
├ Total: {today['total_trades']}
├ ✅ Ganhos: {today['wins']}
├ ❌ Perdas: {today['losses']}
└ Win Rate: {wr_bar} {today['win_rate']:.1f}%

<b>📈 Por Símbolo:</b>
"""
            for symbol, data in today['by_symbol'].items():
                pnl = data if isinstance(data, (int, float)) else data.get('pnl', 0)
                pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
                emoji = "🟢" if pnl >= 0 else "🔴"
                text += f"├ {emoji} {symbol}: <code>{pnl_str}</code>\n"
            
            text += f"""
<b>📍 Status Atual:</b>
├ Posições Abertas: {today['open_positions']}
└ Floating P&L: <code>${today['floating']:+,.2f}</code>

<b>⏰ Próximos Eventos:</b>
├ NY Open: {self._get_session_time('NY')}
├ EU Close: {self._get_session_time('EU_close')}
└ Asia Open: {self._get_session_time('Asia')}
            """
            
            keyboard = self._create_inline_keyboard([
                [("📆 Semana", "summary_week"), ("🗓️ Mês", "summary_month")],
                [("📊 Detalhes", "today_details"), ("🔄 Refresh", "refresh_today")],
            ])
            
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_today: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro ao obter resumo: {e}")
    
    def _get_session_time(self, session: str) -> str:
        """Retorna horário de sessão formatado."""
        sessions = {
            'NY': '09:30 EST',
            'EU_close': '11:30 EST',
            'Asia': '19:00 EST',
        }
        return sessions.get(session, 'N/A')
    
    async def _get_today_summary(self) -> Dict[str, Any]:
        """Coleta resumo do dia."""
        return {
            'pnl': 0.0,
            'return_pct': 0.0,
            'max_dd': 0.0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'by_symbol': {
                'XAUUSD': 0.0,
                'EURUSD': 0.0,
                'GBPUSD': 0.0,
            },
            'open_positions': 0,
            'floating': 0.0,
        }
    
    # =========================================================================
    # CONTROLE
    # =========================================================================
    
    @track_command(CommandCategory.CONTROL)
    @require_role(UserRole.TRADER)
    async def cmd_pause(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /pause - Pausa todos os bots (requer TRADER ou ADMIN)."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /pause de {user.username or user.id}")
            
            if self.orchestrator:
                await self.orchestrator.pause_all()
            
            keyboard = self._create_inline_keyboard([
                [("▶️ Retomar", "action_resume")],
            ])
            
            await self._safe_reply(
                update,
                f"⏸️ <b>Todos os bots foram pausados</b>\n\n"
                f"Executado por: {user.username or user.first_name}\n"
                f"Horário: {datetime.now().strftime('%H:%M:%S')}\n\n"
                "Use /resume ou o botão abaixo para retomar.",
                reply_markup=keyboard
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_pause: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro ao pausar: {e}")
    
    @track_command(CommandCategory.CONTROL)
    @require_role(UserRole.TRADER)
    async def cmd_resume(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /resume - Retoma todos os bots (requer TRADER ou ADMIN)."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /resume de {user.username or user.id}")
            
            if self.orchestrator:
                await self.orchestrator.resume_all()
            
            keyboard = self._create_inline_keyboard([
                [("📊 Status", "quick_status")],
            ])
            
            await self._safe_reply(
                update,
                f"▶️ <b>Todos os bots foram retomados</b>\n\n"
                f"Executado por: {user.username or user.first_name}\n"
                f"Horário: {datetime.now().strftime('%H:%M:%S')}\n\n"
                "Operações voltando ao normal.",
                reply_markup=keyboard
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_resume: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro ao retomar: {e}")
    
    @track_command(CommandCategory.CONTROL)
    @require_role(UserRole.ADMIN)
    async def cmd_emergency(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /emergency - Encerramento de emergência (requer ADMIN)."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /emergency de {user.username or user.id}")
            
            # Armazena confirmação pendente
            self._pending_confirmations[user.id] = {
                'command': 'emergency',
                'timestamp': datetime.now(),
                'expires': datetime.now() + timedelta(minutes=2),
            }
            
            keyboard = self._create_inline_keyboard([
                [("⛔ CONFIRMAR EMERGÊNCIA", "confirm_emergency")],
                [("❌ Cancelar", "cancel_emergency")],
            ])
            
            await self._safe_reply(
                update,
                "⛔ <b>EMERGENCY STOP</b>\n\n"
                "⚠️ <b>ATENÇÃO:</b> Este comando irá:\n\n"
                "1. ⏸️ Pausar todos os bots\n"
                "2. 📊 Fechar TODAS as posições\n"
                "3. ❌ Cancelar TODAS as ordens\n"
                "4. 🔒 Bloquear novas operações\n\n"
                "❗ <b>Esta ação é IRREVERSÍVEL</b>\n\n"
                f"Expira em: 2 minutos\n\n"
                "Clique no botão para confirmar ou /cancel para abortar.",
                reply_markup=keyboard
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_emergency: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    @track_command(CommandCategory.CONTROL)
    @require_role(UserRole.ADMIN)
    async def cmd_emergency_confirm(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /emergency_confirm - Confirma encerramento de emergência."""
        try:
            user = update.effective_user
            
            # Verifica se há confirmação pendente
            pending = self._pending_confirmations.get(user.id)
            if not pending or pending['command'] != 'emergency':
                await self._safe_reply(
                    update,
                    "❌ Nenhuma confirmação pendente.\n"
                    "Use /emergency primeiro."
                )
                return
            
            # Verifica se expirou
            if datetime.now() > pending['expires']:
                del self._pending_confirmations[user.id]
                await self._safe_reply(
                    update,
                    "⏰ Confirmação expirada.\n"
                    "Use /emergency novamente."
                )
                return
            
            # Remove confirmação pendente
            del self._pending_confirmations[user.id]
            
            self.logger.warning(f"EMERGENCY STOP executado por {user.username or user.id}")
            
            if self.orchestrator:
                await self.orchestrator.emergency_stop()
            
            await self._safe_reply(
                update,
                "🚨 <b>EMERGENCY STOP EXECUTADO</b>\n\n"
                f"Executado por: @{user.username or user.first_name}\n"
                f"Horário: {datetime.now().strftime('%H:%M:%S')}\n\n"
                "• ⏸️ Todos os bots foram parados\n"
                "• 📊 Todas as posições foram fechadas\n"
                "• ❌ Todas as ordens foram canceladas\n"
                "• 🔒 Sistema bloqueado\n\n"
                "⚠️ O sistema requer reinício manual."
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_emergency_confirm: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro crítico: {e}")
    
    # =========================================================================
    # MÉTRICAS ADMIN
    # =========================================================================
    
    @track_command(CommandCategory.INFO)
    @require_role(UserRole.ADMIN)
    async def cmd_metrics(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /metrics - Métricas de uso do bot (somente ADMIN)."""
        try:
            user = update.effective_user
            self.logger.info(f"Comando /metrics de {user.username or user.id}")
            
            now = datetime.now()
            
            text = f"""
📊 <b>VIRTUS - Métricas de Uso</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

<b>📈 Comandos:</b>
"""
            
            total_calls = 0
            total_errors = 0
            
            # Ordena métricas por número de chamadas
            sorted_metrics = sorted(
                self._metrics.items(),
                key=lambda x: x[1].calls,
                reverse=True
            )
            
            for cmd_name, metrics in sorted_metrics:
                total_calls += metrics.calls
                total_errors += metrics.errors
                avg_latency = metrics.avg_latency_ms
                error_rate = (metrics.errors / metrics.calls * 100) if metrics.calls > 0 else 0
                
                text += f"├ <code>{cmd_name}</code>\n"
                text += f"│  Calls: {metrics.calls} | Errors: {metrics.errors} ({error_rate:.1f}%)\n"
                text += f"│  Latency: {avg_latency:.0f}ms\n"
            
            text += f"""
<b>━━━━━━━━━━━━━━━</b>
<b>📊 Totais:</b>
├ Comandos: {total_calls}
├ Erros: {total_errors}
└ Taxa de Erro: {(total_errors/total_calls*100) if total_calls > 0 else 0:.1f}%

<b>👥 Rate Limits:</b>
├ Usuários monitorados: {len(self._rate_limits)}
└ Bloqueios ativos: {sum(1 for r in self._rate_limits.values() if r.blocked_until and r.blocked_until > now)}
"""
            
            await self._safe_reply(update, text.strip())
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_metrics: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    # =========================================================================
    # CALLBACK HANDLERS
    # =========================================================================
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Handler para botões inline."""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            user = update.effective_user
            
            self.logger.info(f"Callback '{data}' de {user.username or user.id}")
            
            # Mapeia callbacks para ações
            if data == "quick_status":
                await self.cmd_status(update, context)
            elif data == "quick_equity":
                await self.cmd_equity(update, context)
            elif data == "quick_positions":
                await self.cmd_positions(update, context)
            elif data == "quick_risk":
                await self.cmd_risk(update, context)
            elif data.startswith("refresh_"):
                # Refresh de qualquer comando
                cmd = data.replace("refresh_", "")
                handler = getattr(self, f"cmd_{cmd}", None)
                if handler:
                    await handler(update, context)
            elif data == "action_pause":
                await self.cmd_pause(update, context)
            elif data == "action_resume":
                await self.cmd_resume(update, context)
            elif data == "confirm_emergency":
                await self.cmd_emergency_confirm(update, context)
            elif data == "cancel_emergency":
                # Remove confirmação pendente
                if user.id in self._pending_confirmations:
                    del self._pending_confirmations[user.id]
                await query.edit_message_text("❌ Operação cancelada.")
            elif data.startswith("bot_detail_"):
                symbol = data.replace("bot_detail_", "")
                # Delega para bot_commands
                context.args = [symbol]
                # Seria integrado com bot_commands.cmd_bot_status
            elif data.startswith("bot_toggle_"):
                symbol = data.replace("bot_toggle_", "")
                # Delega para toggle do bot
            else:
                self.logger.warning(f"Callback desconhecido: {data}")
                
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
            # Básicos
            CommandHandler("start", self.cmd_start),
            CommandHandler("help", self.cmd_help),
            
            # Status
            CommandHandler("status", self.cmd_status),
            CommandHandler("bots", self.cmd_bots),
            
            # Capital e Risco
            CommandHandler("equity", self.cmd_equity),
            CommandHandler("risk", self.cmd_risk),
            CommandHandler("drawdown", self.cmd_drawdown),
            
            # Posições
            CommandHandler("positions", self.cmd_positions),
            
            # Resumos
            CommandHandler("today", self.cmd_today),
            
            # Controle
            CommandHandler("pause", self.cmd_pause),
            CommandHandler("resume", self.cmd_resume),
            CommandHandler("emergency", self.cmd_emergency),
            CommandHandler("emergency_confirm", self.cmd_emergency_confirm),
            
            # Admin
            CommandHandler("metrics", self.cmd_metrics),
            
            # Callback handler para botões inline
            CallbackQueryHandler(self.handle_callback),
        ]
        
        for handler in handlers:
            application.add_handler(handler)
        
        self.logger.info(f"GlobalCommands: {len(handlers)} handlers registrados")
