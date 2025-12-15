"""
VIRTUS Advisor Telegram Commands
================================

Comandos para o Market Advisor.
Fornece briefings diários, análises contextuais e recomendações em português.

Features:
- Rate limiting por usuário (30 req/min)
- Inline keyboards para navegação
- Métricas de uso e latência por comando
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
logger = logging.getLogger("virtus.telegram.commands.advisor")


# =============================================================================
# ENUMS E DATACLASSES
# =============================================================================

class MarketSession(Enum):
    """Sessões de mercado."""
    ASIA = "asia"
    EUROPE = "europe"
    US = "us"
    OVERLAP_EUROPE_US = "overlap_eu_us"
    CLOSED = "closed"


class MarketCondition(Enum):
    """Condições de mercado."""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"
    NEWS_DRIVEN = "news_driven"


class UserRole(Enum):
    """Níveis de autorização do usuário."""
    VIEWER = "viewer"
    TRADER = "trader"
    ADMIN = "admin"


class CommandCategory(Enum):
    """Categorias de comandos para métricas."""
    BRIEFING = "briefing"
    OUTLOOK = "outlook"
    OPPORTUNITY = "opportunity"
    SESSION = "session"
    PLAN = "plan"
    ALERT = "alert"
    ASK = "ask"
    METRICS = "metrics"


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
        
        if self.blocked_until and now < self.blocked_until:
            return False
        
        if self.blocked_until and now >= self.blocked_until:
            self.blocked_until = None
            self.requests.clear()
        
        cutoff = now - timedelta(seconds=config.window_seconds)
        self.requests = [r for r in self.requests if r > cutoff]
        
        if len(self.requests) >= config.max_requests:
            self.blocked_until = now + timedelta(seconds=config.cooldown_seconds)
            return False
        
        self.requests.append(now)
        return True


@dataclass
class DailyBriefing:
    """Briefing diário completo."""
    date: datetime
    session: MarketSession
    condition: MarketCondition
    key_themes: List[str]
    opportunities: List[Dict[str, Any]]
    risks: List[str]
    calendar_highlights: List[Dict[str, Any]]
    recommendations: List[str]


# =============================================================================
# DECORATORS
# =============================================================================

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


class AdvisorCommands:
    """
    Comandos do Market Advisor com rate limiting e métricas.
    
    Features:
    - Rate limiting por usuário (30 req/min)
    - Inline keyboards para navegação
    - Métricas de uso por comando
    - Typing indicator durante briefings
    
    Comandos disponíveis:
    - /briefing - Briefing diário completo
    - /morning - Briefing matinal
    - /outlook [símbolo] - Perspectiva do ativo
    - /opportunity - Oportunidades identificadas
    - /alert_levels - Níveis para alertas
    - /trading_plan - Plano de trading do dia
    - /session - Info da sessão atual
    - /ask [pergunta] - Perguntar ao advisor
    """
    
    SUPPORTED_SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD']
    SYMBOL_ALIASES = {
        'gold': 'XAUUSD',
        'ouro': 'XAUUSD',
        'xau': 'XAUUSD',
        'euro': 'EURUSD',
        'eur': 'EURUSD',
        'gbp': 'GBPUSD',
        'libra': 'GBPUSD',
        'cable': 'GBPUSD',
    }
    
    def __init__(
        self, 
        advisor_service=None, 
        brain_service=None,
        admin_ids: Optional[List[int]] = None,
        trader_ids: Optional[List[int]] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Inicializa comandos do Advisor.
        
        Args:
            advisor_service: Serviço de Market Advisor
            brain_service: Serviço Brain
            admin_ids: Lista de IDs de admins
            trader_ids: Lista de IDs de traders
            rate_limit_config: Configuração de rate limiting
        """
        self.advisor = advisor_service
        self.brain = brain_service
        self.logger = logger
        
        # Autorização
        self._admin_ids = set(admin_ids or [])
        self._trader_ids = set(trader_ids or [])
        
        # Rate limiting
        self._rate_config = rate_limit_config or RateLimitConfig()
        self._rate_limits: Dict[int, UserRateLimit] = {}
        
        # Métricas
        self._metrics: Dict[str, CommandMetrics] = {}
    
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
        """Resolve texto para símbolo."""
        if not text:
            return None
        
        text_upper = text.upper()
        text_lower = text.lower()
        
        if text_upper in self.SUPPORTED_SYMBOLS:
            return text_upper
        
        if text_lower in self.SYMBOL_ALIASES:
            return self.SYMBOL_ALIASES[text_lower]
        
        return None
    
    def _symbol_emoji(self, symbol: str) -> str:
        """Emoji do símbolo."""
        return {
            'XAUUSD': '🥇',
            'EURUSD': '💶',
            'GBPUSD': '💷',
        }.get(symbol, '📊')
    
    def _get_current_session(self) -> MarketSession:
        """Determina sessão atual baseada no horário UTC."""
        utc_hour = datetime.utcnow().hour
        
        if 0 <= utc_hour < 7:
            return MarketSession.ASIA
        elif 7 <= utc_hour < 12:
            return MarketSession.EUROPE
        elif 12 <= utc_hour < 16:
            return MarketSession.OVERLAP_EUROPE_US
        elif 16 <= utc_hour < 21:
            return MarketSession.US
        else:
            return MarketSession.CLOSED
    
    def _session_info(self, session: MarketSession) -> Dict[str, str]:
        """Info da sessão."""
        info = {
            MarketSession.ASIA: {
                'name': 'Sessão Asiática',
                'emoji': '🌏',
                'pairs': 'JPY pairs, AUD, NZD',
                'volatility': 'Baixa-Média',
            },
            MarketSession.EUROPE: {
                'name': 'Sessão Europeia',
                'emoji': '🌍',
                'pairs': 'EUR, GBP, CHF',
                'volatility': 'Média-Alta',
            },
            MarketSession.OVERLAP_EUROPE_US: {
                'name': 'Overlap Europa/EUA',
                'emoji': '🌎🌍',
                'pairs': 'Todos os majors',
                'volatility': 'Alta',
            },
            MarketSession.US: {
                'name': 'Sessão Americana',
                'emoji': '🌎',
                'pairs': 'USD pairs, CAD',
                'volatility': 'Média-Alta',
            },
            MarketSession.CLOSED: {
                'name': 'Mercado em Transição',
                'emoji': '🌙',
                'pairs': 'Liquidez reduzida',
                'volatility': 'Baixa',
            },
        }
        return info.get(session, info[MarketSession.CLOSED])
    
    # ========================================================================
    # BRIEFINGS
    # ========================================================================
    
    @track_command(CommandCategory.BRIEFING)
    @with_typing
    async def cmd_briefing(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /briefing - Briefing diário completo."""
        if not await self._check_and_reply_rate_limit(update):
            return
        
        await self._safe_reply(update, "📊 Gerando briefing completo...")
        
        briefing = await self._generate_daily_briefing()
        await self._send_briefing(update, briefing)
    
    async def _generate_daily_briefing(self) -> DailyBriefing:
        """Gera briefing diário."""
        return DailyBriefing(
            date=datetime.now(),
            session=self._get_current_session(),
            condition=MarketCondition.RANGING,
            key_themes=[],
            opportunities=[],
            risks=[],
            calendar_highlights=[],
            recommendations=[],
        )
    
    async def _send_briefing(self, update: "Update", briefing: DailyBriefing) -> None:
        """Envia briefing formatado."""
        session_info = self._session_info(briefing.session)
        
        # Temas principais
        themes_text = "\n".join([f"• {t}" for t in briefing.key_themes]) or "• Mercado sem eventos significativos"
        
        # Oportunidades
        opps_text = ""
        for opp in briefing.opportunities[:3]:
            opps_text += f"• {opp.get('symbol', 'N/A')}: {opp.get('description', 'N/A')}\n"
        opps_text = opps_text or "• Nenhuma oportunidade clara no momento"
        
        # Riscos
        risks_text = "\n".join([f"• {r}" for r in briefing.risks]) or "• Sem riscos elevados identificados"
        
        # Calendário
        calendar_text = ""
        for event in briefing.calendar_highlights[:5]:
            calendar_text += f"• {event.get('time', '')} - {event.get('event', 'N/A')}\n"
        calendar_text = calendar_text or "• Nenhum evento de alto impacto hoje"
        
        # Recomendações
        recs_text = "\n".join([f"• {r}" for r in briefing.recommendations]) or "• Aguardar configurações claras"
        
        text = f"""
📊 <b>VIRTUS Advisor - Briefing Diário</b>
<i>{briefing.date.strftime('%d/%m/%Y %H:%M')}</i>

{session_info['emoji']} <b>Sessão:</b> {session_info['name']}
📈 <b>Condição:</b> {briefing.condition.value.title()}
⚡ <b>Volatilidade Esperada:</b> {session_info['volatility']}

━━━━━━━━━━━━━━━━━━━━

<b>🎯 Temas Principais:</b>
{themes_text}

<b>💡 Oportunidades:</b>
{opps_text}

<b>⚠️ Riscos do Dia:</b>
{risks_text}

<b>📅 Calendário (Alto Impacto):</b>
{calendar_text}

<b>✅ Recomendações:</b>
{recs_text}

━━━━━━━━━━━━━━━━━━━━

<i>Use /outlook [símbolo] para análise detalhada</i>
        """
        
        # Keyboard para navegação rápida
        keyboard = self._create_inline_keyboard([
            [("🥇 Gold", "adv_outlook_XAUUSD"), ("💶 Euro", "adv_outlook_EURUSD")],
            [("💷 Libra", "adv_outlook_GBPUSD"), ("💡 Opps", "adv_opportunities")],
            [("📋 Plano", "adv_trading_plan"), ("🔔 Níveis", "adv_alert_levels")],
        ])
        
        await self._safe_reply(
            update,
            text.strip(),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    
    @track_command(CommandCategory.BRIEFING)
    @with_typing
    async def cmd_morning(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /morning - Briefing matinal."""
        if not await self._check_and_reply_rate_limit(update):
            return
        
        morning = await self._generate_morning_briefing()
        session_info = self._session_info(self._get_current_session())
        
        text = f"""
☀️ <b>Bom dia! VIRTUS Morning Briefing</b>
<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>

{session_info['emoji']} <b>Sessão:</b> {session_info['name']}

<b>🌍 O que aconteceu durante a noite:</b>
{morning['overnight_summary']}

<b>📊 Setup dos Ativos:</b>

🥇 <b>XAUUSD (Gold)</b>
├ Bias: {morning['xauusd']['bias']}
├ Níveis: S{morning['xauusd']['support']:.2f} | R{morning['xauusd']['resistance']:.2f}
└ Nota: {morning['xauusd']['note']}

💶 <b>EURUSD</b>
├ Bias: {morning['eurusd']['bias']}
├ Níveis: S{morning['eurusd']['support']:.5f} | R{morning['eurusd']['resistance']:.5f}
└ Nota: {morning['eurusd']['note']}

💷 <b>GBPUSD</b>
├ Bias: {morning['gbpusd']['bias']}
├ Níveis: S{morning['gbpusd']['support']:.5f} | R{morning['gbpusd']['resistance']:.5f}
└ Nota: {morning['gbpusd']['note']}

<b>📅 Eventos Importantes Hoje:</b>
{morning['key_events']}

<b>💡 Foco do Dia:</b>
{morning['focus']}

<i>Tenha um ótimo dia de trading! 🚀</i>
        """
        
        # Keyboard com ações rápidas
        keyboard = self._create_inline_keyboard([
            [("📋 Plano", "adv_trading_plan"), ("📊 Sessão", "adv_session")],
            [("💡 Oportunidades", "adv_opportunities")],
        ])
        
        await self._safe_reply(
            update,
            text.strip(),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    
    async def _generate_morning_briefing(self) -> Dict[str, Any]:
        """Gera briefing matinal."""
        return {
            'overnight_summary': '• Sessão asiática tranquila\n• Sem movimentos significativos',
            'xauusd': {
                'bias': '⚪ Neutro',
                'support': 0.0,
                'resistance': 0.0,
                'note': 'Aguardar direção',
            },
            'eurusd': {
                'bias': '⚪ Neutro',
                'support': 0.0,
                'resistance': 0.0,
                'note': 'Aguardar direção',
            },
            'gbpusd': {
                'bias': '⚪ Neutro',
                'support': 0.0,
                'resistance': 0.0,
                'note': 'Aguardar direção',
            },
            'key_events': '• Verificar calendário econômico',
            'focus': '• Gerenciar risco e aguardar setups claros',
        }
    
    # ========================================================================
    # OUTLOOK POR ATIVO
    # ========================================================================
    
    @track_command(CommandCategory.OUTLOOK)
    @with_typing
    async def cmd_outlook(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /outlook [símbolo] - Perspectiva do ativo."""
        if not await self._check_and_reply_rate_limit(update):
            return
        
        args = context.args
        
        if not args:
            await self._show_all_outlooks(update)
            return
        
        symbol = self._resolve_symbol(args[0])
        if not symbol:
            await self._safe_reply(update, f"❌ Símbolo não reconhecido: {args[0]}")
            return
        
        await self._safe_reply(update, f"📊 Analisando {symbol}...")
        
        outlook = await self._generate_outlook(symbol)
        await self._send_outlook(update, outlook)
    
    async def _show_all_outlooks(self, update: "Update") -> None:
        """Mostra outlook resumido de todos os ativos."""
        text = "📊 <b>VIRTUS Advisor - Outlooks</b>\n\n"
        
        for symbol in self.SUPPORTED_SYMBOLS:
            emoji = self._symbol_emoji(symbol)
            outlook = await self._get_quick_outlook(symbol)
            
            text += f"{emoji} <b>{symbol}</b>\n"
            text += f"   ├ Bias: {outlook['bias']}\n"
            text += f"   ├ Confiança: {outlook['confidence']}%\n"
            text += f"   └ Recomendação: {outlook['recommendation']}\n\n"
        
        text += "Toque abaixo para detalhes:"
        
        # Keyboard para seleção de ativo
        keyboard = self._create_inline_keyboard([
            [("🥇 Gold", "adv_outlook_XAUUSD"), ("💶 Euro", "adv_outlook_EURUSD")],
            [("💷 Libra", "adv_outlook_GBPUSD")],
        ])
        
        await self._safe_reply(
            update,
            text.strip(),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    
    async def _get_quick_outlook(self, symbol: str) -> Dict[str, Any]:
        """Outlook rápido de um ativo."""
        return {
            'bias': '⚪ Neutro',
            'confidence': 50,
            'recommendation': 'Aguardar',
        }
    
    async def _generate_outlook(self, symbol: str) -> Dict[str, Any]:
        """Gera outlook completo."""
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'bias': 'Neutro',
            'bias_emoji': '⚪',
            'confidence': 50,
            'timeframe_analysis': {
                'h1': 'Lateral',
                'h4': 'Lateral',
                'd1': 'Lateral',
            },
            'key_levels': {
                'resistance_1': 0.0,
                'resistance_2': 0.0,
                'support_1': 0.0,
                'support_2': 0.0,
            },
            'scenarios': {
                'bullish': 'Se romper acima de X...',
                'bearish': 'Se perder suporte em Y...',
            },
            'catalysts': [],
            'risks': [],
            'trading_idea': 'Aguardar configuração clara',
            'entry_zones': [],
            'targets': [],
            'stop_loss': 'A definir',
        }
    
    async def _send_outlook(self, update: "Update", outlook: Dict[str, Any]) -> None:
        """Envia outlook formatado."""
        symbol = outlook['symbol']
        emoji = self._symbol_emoji(symbol)
        
        # Cenários
        scenarios_text = f"• Bullish: {outlook['scenarios']['bullish']}\n"
        scenarios_text += f"• Bearish: {outlook['scenarios']['bearish']}"
        
        # Catalisadores
        catalysts_text = "\n".join([f"• {c}" for c in outlook['catalysts']]) or "• Nenhum catalisador próximo"
        
        # Riscos
        risks_text = "\n".join([f"• {r}" for r in outlook['risks']]) or "• Riscos normais de mercado"
        
        text = f"""
{emoji} <b>{symbol} - Outlook Completo</b>
<i>{outlook['timestamp'].strftime('%d/%m/%Y %H:%M')}</i>

<b>📊 Viés:</b> {outlook['bias_emoji']} {outlook['bias']}
<b>🎯 Confiança:</b> {outlook['confidence']}%

━━━━━━━━━━━━━━━━━━━━

<b>📈 Análise por Timeframe:</b>
├ H1: {outlook['timeframe_analysis']['h1']}
├ H4: {outlook['timeframe_analysis']['h4']}
└ D1: {outlook['timeframe_analysis']['d1']}

<b>📍 Níveis Chave:</b>
├ R2: {outlook['key_levels']['resistance_2']:.5f}
├ R1: {outlook['key_levels']['resistance_1']:.5f}
├ S1: {outlook['key_levels']['support_1']:.5f}
└ S2: {outlook['key_levels']['support_2']:.5f}

<b>🔮 Cenários:</b>
{scenarios_text}

<b>⚡ Catalisadores:</b>
{catalysts_text}

<b>⚠️ Riscos:</b>
{risks_text}

━━━━━━━━━━━━━━━━━━━━

<b>💡 Ideia de Trading:</b>
{outlook['trading_idea']}

<b>🛑 Stop Loss:</b> {outlook['stop_loss']}
        """
        
        # Keyboard para navegação entre ativos
        other_symbols = [s for s in self.SUPPORTED_SYMBOLS if s != symbol]
        buttons = [[
            (f"{self._symbol_emoji(s)} {s}", f"adv_outlook_{s}") 
            for s in other_symbols
        ]]
        buttons.append([("📊 Briefing", "adv_briefing"), ("💡 Opps", "adv_opportunities")])
        
        keyboard = self._create_inline_keyboard(buttons)
        
        await self._safe_reply(
            update,
            text.strip(),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    
    # ========================================================================
    # OPORTUNIDADES E PLANO
    # ========================================================================
    
    @track_command(CommandCategory.OPPORTUNITY)
    @with_typing
    async def cmd_opportunity(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /opportunity - Oportunidades identificadas."""
        if not await self._check_and_reply_rate_limit(update):
            return
        
        opportunities = await self._get_opportunities()
        
        text = "💡 <b>VIRTUS Advisor - Oportunidades</b>\n"
        text += f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>\n\n"
        
        if not opportunities:
            text += "📭 Nenhuma oportunidade clara no momento.\n\n"
            text += "<i>O sistema busca setups de alta probabilidade.\n"
            text += "Aguarde condições mais favoráveis.</i>"
        else:
            for i, opp in enumerate(opportunities, 1):
                emoji = self._symbol_emoji(opp['symbol'])
                dir_emoji = '🟢' if opp['direction'] == 'long' else '🔴'
                
                text += f"<b>#{i} {emoji} {opp['symbol']}</b> {dir_emoji}\n"
                text += f"├ Tipo: {opp['type']}\n"
                text += f"├ Entry: {opp['entry']:.5f}\n"
                text += f"├ SL: {opp['stop_loss']:.5f}\n"
                text += f"├ TP: {opp['take_profit']:.5f}\n"
                text += f"├ R:R: {opp['risk_reward']:.1f}\n"
                text += f"├ Confiança: {opp['confidence']}%\n"
                text += f"└ Nota: {opp['note']}\n\n"
        
        # Keyboard para ações relacionadas
        keyboard = self._create_inline_keyboard([
            [("📊 Briefing", "adv_briefing"), ("📋 Plano", "adv_trading_plan")],
            [("🔔 Níveis", "adv_alert_levels")],
        ])
        
        await self._safe_reply(
            update,
            text.strip(),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    
    async def _get_opportunities(self) -> List[Dict[str, Any]]:
        """Busca oportunidades atuais."""
        return []
    
    @track_command(CommandCategory.PLAN)
    @with_typing
    async def cmd_trading_plan(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /trading_plan - Plano de trading do dia."""
        if not await self._check_and_reply_rate_limit(update):
            return
        
        plan = await self._generate_trading_plan()
        
        text = f"""
📋 <b>VIRTUS Advisor - Plano de Trading</b>
<i>{datetime.now().strftime('%d/%m/%Y')}</i>

<b>⏰ Horários Importantes:</b>
{plan['key_times']}

<b>🎯 Objetivos do Dia:</b>
├ Max Loss: ${plan['max_loss']:.2f}
├ Target: ${plan['target']:.2f}
└ Max Trades: {plan['max_trades']}

<b>📊 Watchlist:</b>
{plan['watchlist']}

<b>🚫 Evitar:</b>
{plan['avoid']}

<b>✅ Checklist Pré-Trade:</b>
{plan['checklist']}

<b>📝 Notas:</b>
{plan['notes']}

━━━━━━━━━━━━━━━━━━━━

<i>Siga o plano. Disciplina gera consistência.</i>
        """
        
        # Keyboard para navegação
        keyboard = self._create_inline_keyboard([
            [("📊 Sessão", "adv_session"), ("💡 Opps", "adv_opportunities")],
            [("🔔 Níveis", "adv_alert_levels")],
        ])
        
        await self._safe_reply(
            update,
            text.strip(),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    
    async def _generate_trading_plan(self) -> Dict[str, Any]:
        """Gera plano de trading."""
        return {
            'key_times': '• 10:00 - Abertura Londres\n• 14:30 - Dados EUA\n• 15:30 - Abertura NY',
            'max_loss': 200.0,
            'target': 400.0,
            'max_trades': 5,
            'watchlist': '• XAUUSD - Aguardar breakout\n• EURUSD - Suporte em teste\n• GBPUSD - Lateralizado',
            'avoid': '• Trades durante notícias\n• Overtrading após loss\n• Aumento de posição perdedora',
            'checklist': '• ✅ Verificar calendário\n• ✅ Definir níveis de entrada\n• ✅ Calcular position size\n• ✅ Confirmar stop loss',
            'notes': '• Foco em qualidade, não quantidade\n• Respeitar o plano de risco',
        }
    
    # ========================================================================
    # SESSÃO E ALERTAS
    # ========================================================================
    
    @track_command(CommandCategory.SESSION)
    async def cmd_session(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /session - Info da sessão atual."""
        if not await self._check_and_reply_rate_limit(update):
            return
        
        session = self._get_current_session()
        info = self._session_info(session)
        
        # Próxima sessão
        next_session = await self._get_next_session_info()
        
        text = f"""
{info['emoji']} <b>VIRTUS Advisor - Sessão Atual</b>
<i>{datetime.now().strftime('%d/%m/%Y %H:%M UTC')}</i>

<b>Sessão:</b> {info['name']}
<b>Pares Principais:</b> {info['pairs']}
<b>Volatilidade Típica:</b> {info['volatility']}

<b>📊 Características:</b>
{await self._get_session_characteristics(session)}

<b>⏰ Próxima Sessão:</b>
├ {next_session['name']}
├ Início: {next_session['start']}
└ Em: {next_session['countdown']}

<b>💡 Dica:</b>
{await self._get_session_tip(session)}
        """
        
        # Keyboard para navegação
        keyboard = self._create_inline_keyboard([
            [("📊 Briefing", "adv_briefing"), ("📋 Plano", "adv_trading_plan")],
            [("💡 Opps", "adv_opportunities")],
        ])
        
        await self._safe_reply(
            update,
            text.strip(),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    
    async def _get_next_session_info(self) -> Dict[str, str]:
        """Info da próxima sessão."""
        return {
            'name': 'Próxima Sessão',
            'start': 'N/A',
            'countdown': 'N/A',
        }
    
    async def _get_session_characteristics(self, session: MarketSession) -> str:
        """Características da sessão."""
        chars = {
            MarketSession.ASIA: "• Volume mais baixo\n• Movimentos graduais\n• Ideal para range trading",
            MarketSession.EUROPE: "• Alto volume\n• Breakouts frequentes\n• Movimentos direcionais",
            MarketSession.OVERLAP_EUROPE_US: "• Máxima liquidez\n• Alta volatilidade\n• Melhores oportunidades",
            MarketSession.US: "• Volume significativo\n• Reações a dados\n• Continuação ou reversão de trends",
            MarketSession.CLOSED: "• Liquidez reduzida\n• Spreads maiores\n• Evitar trades grandes",
        }
        return chars.get(session, "• Características não disponíveis")
    
    async def _get_session_tip(self, session: MarketSession) -> str:
        """Dica para a sessão."""
        tips = {
            MarketSession.ASIA: "Considere range trading em pares JPY. Prepare setups para abertura europeia.",
            MarketSession.EUROPE: "Fique atento aos breakouts de ranges asiáticos. EUR e GBP são foco.",
            MarketSession.OVERLAP_EUROPE_US: "Melhor momento para tendências. Aproveite a liquidez alta.",
            MarketSession.US: "Monitore dados econômicos. USD pairs em destaque.",
            MarketSession.CLOSED: "Mercado fechando. Evite novos trades, gerencie posições existentes.",
        }
        return tips.get(session, "Mantenha disciplina e siga seu plano de trading.")
    
    @track_command(CommandCategory.ALERT)
    async def cmd_alert_levels(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /alert_levels - Níveis para alertas."""
        if not await self._check_and_reply_rate_limit(update):
            return
        
        levels = await self._get_alert_levels()
        
        text = "🔔 <b>VIRTUS Advisor - Níveis de Alerta</b>\n"
        text += f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>\n\n"
        
        for symbol in self.SUPPORTED_SYMBOLS:
            emoji = self._symbol_emoji(symbol)
            symbol_levels = levels.get(symbol, {})
            
            text += f"{emoji} <b>{symbol}</b>\n"
            text += f"├ 📈 Break Alto: {symbol_levels.get('break_high', 'N/A')}\n"
            text += f"├ 📉 Break Baixo: {symbol_levels.get('break_low', 'N/A')}\n"
            text += f"├ 🎯 Target 1: {symbol_levels.get('target_1', 'N/A')}\n"
            text += f"└ 🛑 Stop Area: {symbol_levels.get('stop_area', 'N/A')}\n\n"
        
        text += "<i>Alertas são enviados automaticamente ao atingir níveis.</i>"
        
        # Keyboard para ações
        keyboard = self._create_inline_keyboard([
            [("🥇 Gold", "adv_outlook_XAUUSD"), ("💶 Euro", "adv_outlook_EURUSD")],
            [("💷 Libra", "adv_outlook_GBPUSD")],
        ])
        
        await self._safe_reply(
            update,
            text.strip(),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    
    async def _get_alert_levels(self) -> Dict[str, Dict[str, str]]:
        """Coleta níveis para alertas."""
        return {
            'XAUUSD': {
                'break_high': 'N/A',
                'break_low': 'N/A',
                'target_1': 'N/A',
                'stop_area': 'N/A',
            },
            'EURUSD': {
                'break_high': 'N/A',
                'break_low': 'N/A',
                'target_1': 'N/A',
                'stop_area': 'N/A',
            },
            'GBPUSD': {
                'break_high': 'N/A',
                'break_low': 'N/A',
                'target_1': 'N/A',
                'stop_area': 'N/A',
            },
        }
    
    # ========================================================================
    # PERGUNTAS AO ADVISOR
    # ========================================================================
    
    @track_command(CommandCategory.ASK)
    @with_typing
    async def cmd_ask(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /ask [pergunta] - Perguntar ao advisor."""
        if not await self._check_and_reply_rate_limit(update):
            return
        
        args = context.args
        
        if not args:
            await self._safe_reply(
                update,
                "❓ <b>Faça uma pergunta ao Advisor:</b>\n\n"
                "Exemplos:\n"
                "/ask devo comprar ouro agora?\n"
                "/ask qual melhor momento para EURUSD?\n"
                "/ask o mercado está arriscado hoje?",
            )
            return
        
        question = " ".join(args)
        await self._safe_reply(update, "🤔 Analisando sua pergunta...")
        
        response = await self._answer_question(question)
        
        text = f"""
💬 <b>VIRTUS Advisor</b>

<b>Sua pergunta:</b>
"{question}"

<b>Resposta:</b>
{response['answer']}

<b>📊 Contexto:</b>
{response['context']}

<i>⚠️ Esta é uma análise automatizada. 
Sempre faça sua própria due diligence.</i>
        """
        
        # Keyboard com ações rápidas
        keyboard = self._create_inline_keyboard([
            [("📊 Briefing", "adv_briefing"), ("💡 Opps", "adv_opportunities")],
        ])
        
        await self._safe_reply(
            update,
            text.strip(),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    
    async def _answer_question(self, question: str) -> Dict[str, str]:
        """Responde pergunta do usuário."""
        # Análise básica da pergunta
        question_lower = question.lower()
        
        # Detecta símbolo na pergunta
        symbol = None
        for sym in self.SUPPORTED_SYMBOLS:
            if sym.lower() in question_lower:
                symbol = sym
                break
        
        for alias, sym in self.SYMBOL_ALIASES.items():
            if alias in question_lower:
                symbol = sym
                break
        
        return {
            'answer': 'No momento, recomendo aguardar configurações mais claras antes de tomar decisões. '
                     'O mercado está em período de consolidação e não apresenta oportunidades de alta probabilidade.',
            'context': f'• Sessão: {self._session_info(self._get_current_session())["name"]}\n'
                      f'• Volatilidade: Moderada\n'
                      f'• Eventos: Verificar calendário econômico',
        }
    
    # ========================================================================
    # CALLBACK HANDLER
    # ========================================================================
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Handler para callbacks de inline keyboard."""
        query = update.callback_query
        data = query.data
        
        try:
            await query.answer()
            
            # Parseia ação
            if data.startswith("adv_outlook_"):
                symbol = data.replace("adv_outlook_", "")
                if symbol in self.SUPPORTED_SYMBOLS:
                    outlook = await self._generate_outlook(symbol)
                    await self._send_outlook(update, outlook)
            
            elif data == "adv_briefing":
                briefing = await self._generate_daily_briefing()
                await self._send_briefing(update, briefing)
            
            elif data == "adv_opportunities":
                # Simula contexto com args vazio
                class MockContext:
                    args = []
                await self.cmd_opportunity(update, MockContext())
            
            elif data == "adv_trading_plan":
                class MockContext:
                    args = []
                await self.cmd_trading_plan(update, MockContext())
            
            elif data == "adv_session":
                class MockContext:
                    args = []
                await self.cmd_session(update, MockContext())
            
            elif data == "adv_alert_levels":
                class MockContext:
                    args = []
                await self.cmd_alert_levels(update, MockContext())
        
        except Exception as e:
            self.logger.error(f"Erro no callback advisor: {e}")
            try:
                await query.message.reply_text(
                    "❌ Erro ao processar ação.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    
    # ========================================================================
    # MÉTRICAS
    # ========================================================================
    
    @track_command(CommandCategory.METRICS)
    async def cmd_advisor_metrics(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /advisor_metrics - Métricas de uso (admin only)."""
        user_id = update.effective_user.id
        
        if self._get_user_role(user_id) != UserRole.ADMIN:
            await self._safe_reply(
                update,
                "❌ Acesso negado. Comando disponível apenas para admins."
            )
            return
        
        if not self._metrics:
            await self._safe_reply(update, "📊 Nenhuma métrica disponível ainda.")
            return
        
        text = "📊 <b>Métricas do Advisor</b>\n\n"
        
        total_calls = 0
        total_errors = 0
        
        for name, m in sorted(self._metrics.items(), key=lambda x: x[1].total_calls, reverse=True):
            total_calls += m.total_calls
            total_errors += m.error_count
            
            text += f"<b>/{name}</b>\n"
            text += f"├ Calls: {m.total_calls}\n"
            text += f"├ Erros: {m.error_count}\n"
            text += f"├ Latência: {m.avg_latency_ms:.1f}ms\n"
            text += f"└ Último: {m.last_called.strftime('%H:%M:%S') if m.last_called else 'N/A'}\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<b>Total:</b> {total_calls} calls, {total_errors} erros"
        
        await self._safe_reply(update, text.strip())
    
    # ========================================================================
    # REGISTRO DE HANDLERS
    # ========================================================================
    
    def register_handlers(self, application) -> None:
        """
        Registra handlers no Application do telegram.
        
        Args:
            application: telegram.ext.Application
        """
        from telegram.ext import CommandHandler, CallbackQueryHandler
        
        handlers = [
            # Briefings
            CommandHandler("briefing", self.cmd_briefing),
            CommandHandler("morning", self.cmd_morning),
            
            # Outlook
            CommandHandler("outlook", self.cmd_outlook),
            
            # Oportunidades e Plano
            CommandHandler("opportunity", self.cmd_opportunity),
            CommandHandler("opportunities", self.cmd_opportunity),
            CommandHandler("trading_plan", self.cmd_trading_plan),
            CommandHandler("plan", self.cmd_trading_plan),
            
            # Sessão e Alertas
            CommandHandler("session", self.cmd_session),
            CommandHandler("alert_levels", self.cmd_alert_levels),
            
            # Perguntas
            CommandHandler("ask", self.cmd_ask),
            
            # Métricas (admin)
            CommandHandler("advisor_metrics", self.cmd_advisor_metrics),
            
            # Callback handler para inline keyboards
            CallbackQueryHandler(self.handle_callback, pattern="^adv_"),
        ]
        
        for handler in handlers:
            application.add_handler(handler)
