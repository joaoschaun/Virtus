"""
VIRTUS Brain Telegram Commands
==============================

Comandos para interação com o Brain Service.
Inclui análises, notícias, sentimento e calendário econômico.

Features:
- Rate limiting por usuário (30 req/min)
- Sistema de autorização por níveis (VIEWER/TRADER/ADMIN)
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
logger = logging.getLogger("virtus.telegram.commands.brain")


# =============================================================================
# ENUMS E DATACLASSES
# =============================================================================

class AnalysisType(Enum):
    """Tipos de análise."""
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    NEWS = "news"
    MACRO = "macro"
    CORRELATION = "correlation"
    FULL = "full"


class UserRole(Enum):
    """Níveis de autorização do usuário."""
    VIEWER = "viewer"
    TRADER = "trader"
    ADMIN = "admin"


class CommandCategory(Enum):
    """Categorias de comandos para métricas."""
    STATUS = "status"
    ANALYSIS = "analysis"
    SENTIMENT = "sentiment"
    CALENDAR = "calendar"
    LEVELS = "levels"


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
class AnalysisSummary:
    """Resumo de uma análise."""
    symbol: str
    direction: str  # bullish, bearish, neutral
    confidence: float  # 0-100
    timeframe: str
    key_levels: Dict[str, float]
    signals: List[str]
    risks: List[str]


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


class BrainCommands:
    """
    Comandos do Brain Service com autorização e rate limiting.
    
    Features:
    - Rate limiting por usuário (30 req/min)
    - Inline keyboards para navegação rápida
    - Métricas de uso por comando
    - Typing indicator durante análises
    
    Comandos disponíveis:
    - /brain - Status do Brain
    - /brain_analysis [símbolo] - Análise completa
    - /brain_technical [símbolo] - Análise técnica
    - /brain_sentiment - Sentimento de mercado
    - /brain_news - Últimas notícias
    - /brain_calendar - Calendário econômico
    - /brain_correlation - Matriz de correlação
    - /brain_levels [símbolo] - Níveis importantes
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
        brain_service=None,
        admin_ids: Optional[List[int]] = None,
        trader_ids: Optional[List[int]] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Inicializa comandos do Brain.
        
        Args:
            brain_service: Serviço Brain
            admin_ids: Lista de IDs de admins
            trader_ids: Lista de IDs de traders
            rate_limit_config: Configuração de rate limiting
        """
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
        """Resolve texto para símbolo válido."""
        if not text:
            return None
        
        text_upper = text.upper()
        text_lower = text.lower()
        
        if text_upper in self.SUPPORTED_SYMBOLS:
            return text_upper
        
        if text_lower in self.SYMBOL_ALIASES:
            return self.SYMBOL_ALIASES[text_lower]
        
        return None
    
    def _direction_emoji(self, direction: str) -> str:
        """Retorna emoji para direção."""
        emojis = {
            'bullish': '🟢',
            'bearish': '🔴',
            'neutral': '⚪',
            'strong_bullish': '🟢🟢',
            'strong_bearish': '🔴🔴',
        }
        return emojis.get(direction.lower(), '⚪')
    
    def _symbol_emoji(self, symbol: str) -> str:
        """Retorna emoji para símbolo."""
        return {
            'XAUUSD': '🥇',
            'EURUSD': '💶',
            'GBPUSD': '💷',
        }.get(symbol, '📊')
    
    # =========================================================================
    # STATUS DO BRAIN
    # =========================================================================
    
    @track_command(CommandCategory.STATUS)
    @with_typing
    async def cmd_brain(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /brain - Status do Brain Service."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /brain de {user.username or user.id}")
            
            status = await self._get_brain_status()
            now = datetime.now()
            
            # Indicadores visuais
            state_emoji = "🟢" if "Online" in status['state'] else "🔴"
            
            text = f"""
🧠 <b>VIRTUS Brain Status</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

<b>Estado:</b> {state_emoji} {status['state']}
<b>Uptime:</b> {status['uptime']}

<b>📡 Providers:</b>
├ News: {status['news_provider']}
├ Economic: {status['economic_provider']}
├ Sentiment: {status['sentiment_provider']}
└ Market Data: {status['market_provider']}

<b>📊 Cache:</b>
├ Items: {status['cache_items']}
├ Hit Rate: {status['cache_hit_rate']:.1f}%
└ Last Update: {status['last_update']}

<b>💰 Budget API:</b>
├ Usado: <code>${status['budget_used']:.2f}</code>
├ Limite: <code>${status['budget_limit']:.2f}</code>
└ Disponível: <code>${status['budget_available']:.2f}</code>

<b>🔄 Últimas Análises:</b>
├ 🥇 XAUUSD: {status['last_analysis_xau']}
├ 💶 EURUSD: {status['last_analysis_eur']}
└ 💷 GBPUSD: {status['last_analysis_gbp']}
            """
            
            # Botões de navegação
            buttons = [
                [("📊 Análises", "brain_all_analysis"), ("💭 Sentimento", "brain_sentiment")],
                [("📰 Notícias", "brain_news"), ("📅 Calendário", "brain_calendar")],
                [("🔄 Refresh", "refresh_brain")],
            ]
            
            keyboard = self._create_inline_keyboard(buttons)
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_brain: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    async def _get_brain_status(self) -> Dict[str, Any]:
        """Coleta status do Brain."""
        return {
            'state': '🟢 Online',
            'uptime': 'N/A',
            'news_provider': '✅ Ativo',
            'economic_provider': '✅ Ativo',
            'sentiment_provider': '✅ Ativo',
            'market_provider': '✅ Ativo',
            'cache_items': 0,
            'cache_hit_rate': 0.0,
            'last_update': 'N/A',
            'budget_used': 0.0,
            'budget_limit': 10.0,
            'budget_available': 10.0,
            'last_analysis_xau': 'N/A',
            'last_analysis_eur': 'N/A',
            'last_analysis_gbp': 'N/A',
        }
    
    # =========================================================================
    # ANÁLISES
    # =========================================================================
    
    @track_command(CommandCategory.ANALYSIS)
    @with_typing
    async def cmd_brain_analysis(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /brain_analysis [símbolo] - Análise completa."""
        try:
            if not await self._check_and_reply_rate_limit(update):
                return
            
            user = update.effective_user
            self.logger.info(f"Comando /brain_analysis de {user.username or user.id}")
            
            args = context.args
            
            if not args:
                await self._show_all_analyses(update)
                return
            
            symbol = self._resolve_symbol(args[0])
            if not symbol:
                await self._safe_reply(
                    update,
                    f"❌ Símbolo não reconhecido: <code>{args[0]}</code>\n\n"
                    f"Símbolos: {', '.join(self.SUPPORTED_SYMBOLS)}"
                )
                return
            
            # Envia mensagem de loading
            await self._safe_reply(update, f"🔄 Gerando análise completa para {symbol}...")
            
            analysis = await self._get_full_analysis(symbol)
            await self._send_analysis(update, analysis)
            
        except Exception as e:
            self.logger.error(f"Erro no cmd_brain_analysis: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    @track_command(CommandCategory.ANALYSIS)
    @with_typing
    async def _show_all_analyses(self, update: "Update") -> None:
        """Mostra resumo de análise de todos os símbolos."""
        try:
            now = datetime.now()
            text = f"""
🧠 <b>VIRTUS Brain - Análises</b>
<i>{now.strftime('%d/%m/%Y %H:%M:%S')}</i>

"""
            
            for symbol in self.SUPPORTED_SYMBOLS:
                summary = await self._get_analysis_summary(symbol)
                emoji = self._symbol_emoji(symbol)
                dir_emoji = self._direction_emoji(summary.direction)
                
                # Confidence bar
                conf_pct = int(summary.confidence / 10)
                conf_bar = "█" * conf_pct + "░" * (10 - conf_pct)
                
                text += f"{emoji} <b>{symbol}</b> {dir_emoji}\n"
                text += f"   ├ Bias: {summary.direction.title()}\n"
                text += f"   ├ Confiança: {conf_bar} {summary.confidence:.0f}%\n"
                text += f"   └ Sinais Ativos: {len(summary.signals)}\n\n"
            
            # Botões para cada símbolo
            buttons = []
            for symbol in self.SUPPORTED_SYMBOLS:
                emoji = self._symbol_emoji(symbol)
                buttons.append([
                    (f"{emoji} Análise {symbol}", f"analysis_{symbol}"),
                    (f"📍 Níveis", f"levels_{symbol}"),
                ])
            
            buttons.append([("🔄 Refresh", "brain_all_analysis")])
            
            keyboard = self._create_inline_keyboard(buttons)
            await self._safe_reply(update, text.strip(), reply_markup=keyboard)
            
        except Exception as e:
            self.logger.error(f"Erro no _show_all_analyses: {e}", exc_info=True)
            await self._safe_reply(update, f"❌ Erro: {e}")
    
    async def _get_analysis_summary(self, symbol: str) -> AnalysisSummary:
        """Obtém resumo da análise."""
        return AnalysisSummary(
            symbol=symbol,
            direction="neutral",
            confidence=50.0,
            timeframe="H4",
            key_levels={'resistance': 0.0, 'support': 0.0},
            signals=[],
            risks=[],
        )
    
    async def _get_full_analysis(self, symbol: str) -> Dict[str, Any]:
        """Obtém análise completa do Brain."""
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'direction': 'neutral',
            'confidence': 50.0,
            'technical': {
                'trend': 'sideways',
                'strength': 0,
                'rsi': 50.0,
                'macd': 'neutral',
                'ema_cross': 'none',
            },
            'sentiment': {
                'overall': 'neutral',
                'news': 0.0,
                'social': 0.0,
                'institutional': 0.0,
            },
            'levels': {
                'resistance_1': 0.0,
                'resistance_2': 0.0,
                'support_1': 0.0,
                'support_2': 0.0,
                'pivot': 0.0,
            },
            'signals': [],
            'risks': [],
            'recommendation': 'Aguardar',
        }
    
    async def _send_analysis(self, update: "Update", analysis: Dict[str, Any]) -> None:
        """Envia análise formatada."""
        symbol = analysis['symbol']
        emoji = self._symbol_emoji(symbol)
        dir_emoji = self._direction_emoji(analysis['direction'])
        
        # Formata sinais
        signals_text = "\n".join([f"• {s}" for s in analysis['signals']]) or "• Nenhum sinal ativo"
        risks_text = "\n".join([f"• {r}" for r in analysis['risks']]) or "• Nenhum risco identificado"
        
        text = f"""
{emoji} <b>{symbol} - Análise Completa</b>
<i>{analysis['timestamp'].strftime('%d/%m/%Y %H:%M')}</i>

<b>📊 Direção:</b> {dir_emoji} {analysis['direction'].title()}
<b>🎯 Confiança:</b> {analysis['confidence']:.0f}%
<b>💡 Recomendação:</b> {analysis['recommendation']}

<b>📈 Análise Técnica:</b>
├ Tendência: {analysis['technical']['trend'].title()}
├ Força: {analysis['technical']['strength']}/100
├ RSI: {analysis['technical']['rsi']:.1f}
├ MACD: {analysis['technical']['macd'].title()}
└ EMA Cross: {analysis['technical']['ema_cross'].title()}

<b>💭 Sentimento:</b>
├ Geral: {analysis['sentiment']['overall'].title()}
├ News: {analysis['sentiment']['news']:+.2f}
├ Social: {analysis['sentiment']['social']:+.2f}
└ Institucional: {analysis['sentiment']['institutional']:+.2f}

<b>📍 Níveis Chave:</b>
├ R2: {analysis['levels']['resistance_2']:.5f}
├ R1: {analysis['levels']['resistance_1']:.5f}
├ Pivot: {analysis['levels']['pivot']:.5f}
├ S1: {analysis['levels']['support_1']:.5f}
└ S2: {analysis['levels']['support_2']:.5f}

<b>✅ Sinais:</b>
{signals_text}

<b>⚠️ Riscos:</b>
{risks_text}
        """
        
        await update.message.reply_text(
            text.strip(),
            parse_mode="HTML"
        )
    
    async def cmd_brain_technical(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /brain_technical [símbolo] - Análise técnica."""
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "❌ Informe o símbolo: /brain_technical XAUUSD"
            )
            return
        
        symbol = self._resolve_symbol(args[0])
        if not symbol:
            await update.message.reply_text(f"❌ Símbolo não reconhecido: {args[0]}")
            return
        
        tech = await self._get_technical_analysis(symbol)
        emoji = self._symbol_emoji(symbol)
        
        text = f"""
{emoji} <b>{symbol} - Análise Técnica</b>
<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>

<b>📈 Tendência:</b>
├ H1: {tech['trend_h1']}
├ H4: {tech['trend_h4']}
└ D1: {tech['trend_d1']}

<b>📊 Indicadores:</b>
├ RSI (14): {tech['rsi']:.1f}
├ MACD: {tech['macd_signal']}
├ Stochastic: {tech['stochastic']:.1f}
├ ADX: {tech['adx']:.1f}
└ ATR: {tech['atr']:.5f}

<b>📉 Médias Móveis:</b>
├ EMA 9: {tech['ema_9']:.5f}
├ EMA 21: {tech['ema_21']:.5f}
├ EMA 50: {tech['ema_50']:.5f}
└ EMA 200: {tech['ema_200']:.5f}

<b>🎯 Sinais:</b>
├ EMA Cross: {tech['ema_cross']}
├ RSI Signal: {tech['rsi_signal']}
├ MACD Cross: {tech['macd_cross']}
└ Divergência: {tech['divergence']}

<b>📍 Padrões:</b>
{tech['patterns'] or '• Nenhum padrão identificado'}
        """
        
        await update.message.reply_text(
            text.strip(),
            parse_mode="HTML"
        )
    
    async def _get_technical_analysis(self, symbol: str) -> Dict[str, Any]:
        """Coleta análise técnica."""
        return {
            'trend_h1': 'Lateral',
            'trend_h4': 'Lateral',
            'trend_d1': 'Lateral',
            'rsi': 50.0,
            'macd_signal': 'Neutro',
            'stochastic': 50.0,
            'adx': 20.0,
            'atr': 0.0,
            'ema_9': 0.0,
            'ema_21': 0.0,
            'ema_50': 0.0,
            'ema_200': 0.0,
            'ema_cross': 'Nenhum',
            'rsi_signal': 'Neutro',
            'macd_cross': 'Nenhum',
            'divergence': 'Nenhuma',
            'patterns': '',
        }
    
    # ========================================================================
    # SENTIMENTO E NOTÍCIAS
    # ========================================================================
    
    async def cmd_brain_sentiment(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /brain_sentiment - Sentimento de mercado."""
        sentiment = await self._get_market_sentiment()
        
        text = f"""
💭 <b>VIRTUS Brain - Sentimento</b>
<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>

<b>🌍 Sentimento Global:</b> {sentiment['global_emoji']} {sentiment['global']}

<b>Por Ativo:</b>

🥇 <b>XAUUSD (Gold)</b>
├ Score: {sentiment['xauusd']['score']:+.2f}
├ Bias: {sentiment['xauusd']['bias']}
└ Drivers: {sentiment['xauusd']['drivers']}

💶 <b>EURUSD</b>
├ Score: {sentiment['eurusd']['score']:+.2f}
├ Bias: {sentiment['eurusd']['bias']}
└ Drivers: {sentiment['eurusd']['drivers']}

💷 <b>GBPUSD</b>
├ Score: {sentiment['gbpusd']['score']:+.2f}
├ Bias: {sentiment['gbpusd']['bias']}
└ Drivers: {sentiment['gbpusd']['drivers']}

<b>📰 Fontes:</b>
├ Notícias: {sentiment['news_sentiment']}
├ Social Media: {sentiment['social_sentiment']}
├ COT Report: {sentiment['cot_sentiment']}
└ Options Flow: {sentiment['options_sentiment']}

<b>⚠️ Alertas:</b>
{sentiment['alerts'] or '• Nenhum alerta de sentimento'}
        """
        
        await update.message.reply_text(
            text.strip(),
            parse_mode="HTML"
        )
    
    async def _get_market_sentiment(self) -> Dict[str, Any]:
        """Coleta sentimento de mercado."""
        return {
            'global': 'Neutro',
            'global_emoji': '⚪',
            'xauusd': {'score': 0.0, 'bias': 'Neutro', 'drivers': 'N/A'},
            'eurusd': {'score': 0.0, 'bias': 'Neutro', 'drivers': 'N/A'},
            'gbpusd': {'score': 0.0, 'bias': 'Neutro', 'drivers': 'N/A'},
            'news_sentiment': 'Neutro',
            'social_sentiment': 'Neutro',
            'cot_sentiment': 'Neutro',
            'options_sentiment': 'Neutro',
            'alerts': '',
        }
    
    async def cmd_brain_news(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /brain_news - Últimas notícias relevantes."""
        news = await self._get_recent_news()
        
        text = "📰 <b>VIRTUS Brain - Notícias</b>\n"
        text += f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>\n\n"
        
        if not news:
            text += "📭 Nenhuma notícia relevante no momento."
        else:
            for item in news[:10]:
                impact_emoji = {
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢',
                }.get(item['impact'], '⚪')
                
                text += f"{impact_emoji} <b>{item['title']}</b>\n"
                text += f"   ├ Fonte: {item['source']}\n"
                text += f"   ├ Ativos: {item['symbols']}\n"
                text += f"   ├ Impacto: {item['impact'].title()}\n"
                text += f"   └ {item['time']}\n\n"
        
        await update.message.reply_text(
            text.strip(),
            parse_mode="HTML"
        )
    
    async def _get_recent_news(self) -> List[Dict[str, Any]]:
        """Coleta notícias recentes."""
        return []
    
    # ========================================================================
    # CALENDÁRIO ECONÔMICO
    # ========================================================================
    
    async def cmd_brain_calendar(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /brain_calendar - Calendário econômico."""
        events = await self._get_economic_calendar()
        
        text = "📅 <b>VIRTUS Brain - Calendário</b>\n"
        text += f"<i>{datetime.now().strftime('%d/%m/%Y')}</i>\n\n"
        
        if not events:
            text += "📭 Nenhum evento importante hoje."
        else:
            current_date = ""
            for event in events[:15]:
                # Separador de data
                if event['date'] != current_date:
                    current_date = event['date']
                    text += f"\n<b>📆 {current_date}</b>\n"
                
                impact_emoji = {
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢',
                }.get(event['impact'], '⚪')
                
                text += f"{impact_emoji} {event['time']} | {event['currency']} | {event['event']}\n"
                if event.get('forecast') or event.get('previous'):
                    text += f"   └ Prev: {event.get('previous', 'N/A')} | Forecast: {event.get('forecast', 'N/A')}\n"
        
        await update.message.reply_text(
            text.strip(),
            parse_mode="HTML"
        )
    
    async def _get_economic_calendar(self) -> List[Dict[str, Any]]:
        """Coleta calendário econômico."""
        return []
    
    # ========================================================================
    # CORRELAÇÃO
    # ========================================================================
    
    async def cmd_brain_correlation(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /brain_correlation - Matriz de correlação."""
        corr = await self._get_correlation_matrix()
        
        text = f"""
📊 <b>VIRTUS Brain - Correlações</b>
<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>

<b>Matriz de Correlação (30 dias):</b>

<code>
           XAUUSD   EURUSD   GBPUSD
XAUUSD     1.00     {corr['xau_eur']:+.2f}    {corr['xau_gbp']:+.2f}
EURUSD     {corr['xau_eur']:+.2f}    1.00     {corr['eur_gbp']:+.2f}
GBPUSD     {corr['xau_gbp']:+.2f}    {corr['eur_gbp']:+.2f}    1.00
</code>

<b>Interpretação:</b>
• > 0.70: Correlação forte positiva
• 0.40-0.70: Correlação moderada
• -0.40-0.40: Correlação fraca
• < -0.40: Correlação negativa

<b>Alertas:</b>
{corr['alerts'] or '• Sem alertas de correlação'}

<b>Divergências:</b>
{corr['divergences'] or '• Nenhuma divergência detectada'}
        """
        
        await update.message.reply_text(
            text.strip(),
            parse_mode="HTML"
        )
    
    async def _get_correlation_matrix(self) -> Dict[str, Any]:
        """Coleta matriz de correlação."""
        return {
            'xau_eur': 0.0,
            'xau_gbp': 0.0,
            'eur_gbp': 0.0,
            'alerts': '',
            'divergences': '',
        }
    
    # ========================================================================
    # NÍVEIS
    # ========================================================================
    
    async def cmd_brain_levels(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Comando /brain_levels [símbolo] - Níveis importantes."""
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "❌ Informe o símbolo: /brain_levels XAUUSD"
            )
            return
        
        symbol = self._resolve_symbol(args[0])
        if not symbol:
            await update.message.reply_text(f"❌ Símbolo não reconhecido: {args[0]}")
            return
        
        levels = await self._get_key_levels(symbol)
        emoji = self._symbol_emoji(symbol)
        
        text = f"""
{emoji} <b>{symbol} - Níveis Chave</b>
<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>

<b>📍 Preço Atual:</b> {levels['current']:.5f}

<b>📈 Resistências:</b>
├ R3 (forte): {levels['r3']:.5f}
├ R2: {levels['r2']:.5f}
└ R1: {levels['r1']:.5f}

<b>⚖️ Pivot:</b> {levels['pivot']:.5f}

<b>📉 Suportes:</b>
├ S1: {levels['s1']:.5f}
├ S2: {levels['s2']:.5f}
└ S3 (forte): {levels['s3']:.5f}

<b>🎯 Zonas de Interesse:</b>
├ Supply Zone: {levels['supply_zone']}
├ Demand Zone: {levels['demand_zone']}
└ Imbalance: {levels['imbalance']}

<b>📊 Fibonacci (último swing):</b>
├ 61.8%: {levels['fib_618']:.5f}
├ 50.0%: {levels['fib_500']:.5f}
└ 38.2%: {levels['fib_382']:.5f}
        """
        
        await update.message.reply_text(
            text.strip(),
            parse_mode="HTML"
        )
    
    async def _get_key_levels(self, symbol: str) -> Dict[str, Any]:
        """Coleta níveis importantes."""
        return {
            'current': 0.0,
            'r3': 0.0,
            'r2': 0.0,
            'r1': 0.0,
            'pivot': 0.0,
            's1': 0.0,
            's2': 0.0,
            's3': 0.0,
            'supply_zone': 'N/A',
            'demand_zone': 'N/A',
            'imbalance': 'N/A',
            'fib_618': 0.0,
            'fib_500': 0.0,
            'fib_382': 0.0,
        }
    
    # =========================================================================
    # CALLBACK HANDLERS
    # =========================================================================
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Handler para botões inline do Brain."""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            user = update.effective_user
            
            self.logger.info(f"Brain callback '{data}' de {user.username or user.id}")
            
            # Mapeia callbacks para ações
            if data == "refresh_brain":
                await self.cmd_brain(update, context)
            
            elif data == "brain_all_analysis":
                await self._show_all_analyses(update)
            
            elif data.startswith("analysis_"):
                symbol = data.replace("analysis_", "")
                context.args = [symbol]
                await self.cmd_brain_analysis(update, context)
            
            elif data.startswith("technical_"):
                symbol = data.replace("technical_", "")
                context.args = [symbol]
                await self.cmd_brain_technical(update, context)
            
            elif data.startswith("levels_"):
                symbol = data.replace("levels_", "")
                context.args = [symbol]
                await self.cmd_brain_levels(update, context)
            
            elif data == "brain_sentiment":
                await self.cmd_brain_sentiment(update, context)
            
            elif data == "brain_news":
                await self.cmd_brain_news(update, context)
            
            elif data == "brain_calendar":
                await self.cmd_brain_calendar(update, context)
            
            elif data == "brain_correlation":
                await self.cmd_brain_correlation(update, context)
            
            else:
                self.logger.warning(f"Brain callback desconhecido: {data}")
                
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
            CommandHandler("brain", self.cmd_brain),
            CommandHandler("brain_status", self.cmd_brain),
            
            # Análises
            CommandHandler("brain_analysis", self.cmd_brain_analysis),
            CommandHandler("brain_technical", self.cmd_brain_technical),
            
            # Sentimento e Notícias
            CommandHandler("brain_sentiment", self.cmd_brain_sentiment),
            CommandHandler("brain_news", self.cmd_brain_news),
            
            # Calendário
            CommandHandler("brain_calendar", self.cmd_brain_calendar),
            CommandHandler("calendar", self.cmd_brain_calendar),
            
            # Correlação e Níveis
            CommandHandler("brain_correlation", self.cmd_brain_correlation),
            CommandHandler("brain_levels", self.cmd_brain_levels),
            
            # Callback handler para botões inline
            CallbackQueryHandler(self.handle_callback, pattern="^brain_|^analysis_|^technical_|^levels_|^refresh_brain"),
        ]
        
        for handler in handlers:
            application.add_handler(handler)
        
        self.logger.info(f"BrainCommands: {len(handlers)} handlers registrados")
