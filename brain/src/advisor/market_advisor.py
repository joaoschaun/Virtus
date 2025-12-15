"""
VIRTUS Advisor - Market Advisor Service
========================================

Serviço de consultoria de mercado via Telegram.
Fornece briefings diários, análises e alertas em português.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..core.logger import get_logger
from ..core.config import get_config
from ..core.types import (
    NewsItem, MarketSentiment, EconomicEvent,
    SentimentLevel, NewsImpact, DailyBriefing
)
from ..core.scheduler import Scheduler, get_scheduler, daily
from ..brain import BrainService, get_brain
from ..telegram import TelegramService, get_telegram

logger = get_logger("advisor")


@dataclass
class AdvisorConfig:
    """Configuração do Advisor"""
    morning_briefing_hour: int = 7
    morning_briefing_minute: int = 30
    evening_summary_hour: int = 20
    evening_summary_minute: int = 0
    news_check_interval: int = 30  # minutos
    high_impact_alerts: bool = True
    sentiment_alerts: bool = True
    symbols: List[str] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ['XAUUSD', 'EURUSD', 'GBPUSD']


class MarketAdvisor:
    """
    Consultor de Mercado VIRTUS.
    
    Funcionalidades:
    - Briefing matinal com análise do dia
    - Resumo do fechamento
    - Alertas de notícias importantes
    - Análise de sentimento em tempo real
    - Eventos do calendário econômico
    
    Todas as mensagens são em português brasileiro.
    """
    
    _instance: Optional['MarketAdvisor'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._brain: Optional[BrainService] = None
        self._telegram: Optional[TelegramService] = None
        self._scheduler: Optional[Scheduler] = None
        self._config: Optional[AdvisorConfig] = None
        self._initialized = False
        
        # Último sentimento por símbolo (para detectar mudanças)
        self._last_sentiments: Dict[str, SentimentLevel] = {}
        
        # Últimas notícias enviadas (evita duplicatas)
        self._sent_news_ids: set = set()
    
    async def _safe_send_message(self, text: str):
        """Envia mensagem de forma segura (verifica se Telegram está disponível)"""
        if self._telegram:
            try:
                await self._telegram.send_message(text)
            except Exception as e:
                logger.warning(f"⚠️ Falha ao enviar mensagem Telegram: {e}")
        else:
            logger.info(f"[Telegram não disponível] {text[:100]}...")
    
    async def _safe_send_alert(self, text: str, level: str = "info"):
        """Envia alerta de forma segura"""
        if self._telegram:
            try:
                await self._telegram.send_message(text)
            except Exception as e:
                logger.warning(f"⚠️ Falha ao enviar alerta Telegram: {e}")
        else:
            logger.info(f"[Alerta-{level}] {text}")
    
    @classmethod
    async def get_instance(cls) -> 'MarketAdvisor':
        """Retorna instância singleton"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                await cls._instance.initialize()
            return cls._instance
    
    async def initialize(self):
        """Inicializa o Advisor"""
        if self._initialized:
            return
        
        logger.info("🎯 Inicializando Market Advisor...")
        
        try:
            # Carrega serviços
            self._brain = await get_brain()
            
            # Telegram é opcional
            try:
                config = get_config()
                if config.telegram.token and config.telegram.chat_id:
                    self._telegram = await get_telegram()
                else:
                    self._telegram = None
                    logger.warning("⚠️ Telegram não configurado - Advisor funcionará sem notificações")
            except Exception:
                self._telegram = None
                logger.warning("⚠️ Telegram não disponível - Advisor funcionará sem notificações")
            
            self._scheduler = get_scheduler()
            
            # Carrega configuração
            config = get_config()
            core_advisor = config.advisor if hasattr(config, 'advisor') else None
            
            # Extrai valores do config (dataclass ou dict)
            if core_advisor:
                daily_briefing = getattr(core_advisor, 'daily_briefing', {}) or {}
                morning_hour = daily_briefing.get('hour', 7) if isinstance(daily_briefing, dict) else 7
                morning_min = daily_briefing.get('minute', 30) if isinstance(daily_briefing, dict) else 30
            else:
                morning_hour = 7
                morning_min = 30
            
            self._config = AdvisorConfig(
                morning_briefing_hour=morning_hour,
                morning_briefing_minute=morning_min,
                evening_summary_hour=20,
                evening_summary_minute=0,
                news_check_interval=30,
                high_impact_alerts=True,
                sentiment_alerts=True,
                symbols=['XAUUSD', 'EURUSD', 'GBPUSD'],
            )
            
            # Agenda tarefas
            await self._schedule_tasks()
            
            self._initialized = True
            logger.info("✅ Market Advisor inicializado")
            
            # Envia mensagem de início
            await self._safe_send_alert(
                "🤖 *VIRTUS Advisor Iniciado*\n\n"
                "Monitorando mercados e preparando análises.",
                level="success"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Advisor: {e}")
            raise
    
    async def start(self):
        """Inicia o serviço de advisor"""
        if not self._initialized:
            await self.initialize()
        logger.info("🎯 Market Advisor iniciado")
    
    async def stop(self):
        """Para o serviço de advisor"""
        logger.info("🛑 Market Advisor parando...")
        # Poderia limpar tarefas agendadas aqui se necessário
        logger.info("✅ Market Advisor parado")
    
    async def _schedule_tasks(self):
        """Agenda tarefas periódicas"""
        # Briefing matinal
        morning_time = datetime.now().replace(
            hour=self._config.morning_briefing_hour,
            minute=self._config.morning_briefing_minute,
            second=0,
            microsecond=0
        )
        self._scheduler.add_scheduled_task(
            name="morning_briefing",
            callback=self.send_morning_briefing,
            run_at=morning_time,
            repeat_daily=True
        )
        
        # Resumo noturno
        evening_time = datetime.now().replace(
            hour=self._config.evening_summary_hour,
            minute=self._config.evening_summary_minute,
            second=0,
            microsecond=0
        )
        self._scheduler.add_scheduled_task(
            name="evening_summary",
            callback=self.send_evening_summary,
            run_at=evening_time,
            repeat_daily=True
        )
        
        # Verificação de notícias
        self._scheduler.add_periodic_task(
            name="news_check",
            callback=self.check_important_news,
            interval_seconds=self._config.news_check_interval * 60,
            start_immediately=False
        )
        
        # Verificação de eventos do dia
        self._scheduler.add_periodic_task(
            name="event_check",
            callback=self.check_upcoming_events,
            interval_seconds=3600,  # A cada hora
            start_immediately=False
        )
        
        logger.info("📅 Tarefas do Advisor agendadas")
    
    # ========================================================================
    # BRIEFINGS
    # ========================================================================
    
    async def send_morning_briefing(self):
        """Envia briefing matinal completo"""
        logger.info("📋 Preparando briefing matinal...")
        
        try:
            # Gera briefing via Brain
            briefing = await self._brain.generate_daily_briefing(self._config.symbols)
            
            # Formata mensagem
            text = self._format_morning_briefing(briefing)
            
            # Envia
            await self._safe_send_message(text)
            
            logger.info("✅ Briefing matinal enviado")
            
        except Exception as e:
            logger.error(f"❌ Erro no briefing matinal: {e}")
            await self._safe_send_alert(
                f"Erro ao gerar briefing matinal: {str(e)[:100]}",
                level="error"
            )
    
    def _format_morning_briefing(self, briefing: DailyBriefing) -> str:
        """Formata o briefing matinal em português"""
        lines = [
            "☀️ *BOM DIA! BRIEFING DO MERCADO*",
            f"📅 {briefing.date.strftime('%d/%m/%Y')}",
            "",
        ]
        
        # Sentimentos
        if briefing.sentiments:
            lines.append("📊 *SENTIMENTO POR ATIVO:*")
            for symbol, sentiment in briefing.sentiments.items():
                emoji = self._sentiment_emoji(sentiment.sentiment_level)
                score_text = f"({sentiment.overall_sentiment:+.2f})"
                lines.append(f"  {emoji} {symbol}: {self._sentiment_text(sentiment.sentiment_level)} {score_text}")
            lines.append("")
        
        # Eventos importantes do dia
        high_impact_events = [e for e in briefing.events if e.impact == NewsImpact.HIGH]
        if high_impact_events:
            lines.append("⚠️ *EVENTOS DE ALTO IMPACTO HOJE:*")
            for event in high_impact_events[:5]:
                time_str = event.timestamp.strftime('%H:%M')
                name = event.name_pt or event.name
                lines.append(f"  🔴 {time_str} - {name} ({event.currency})")
            lines.append("")
        
        # Notícias principais
        if briefing.top_news:
            lines.append("📰 *PRINCIPAIS NOTÍCIAS:*")
            for news in briefing.top_news[:3]:
                emoji = self._sentiment_emoji_score(news.sentiment_score)
                title = news.title[:80]
                lines.append(f"  {emoji} {title}")
            lines.append("")
        
        # Resumo
        if briefing.summary_pt:
            lines.append("📝 *RESUMO:*")
            lines.append(briefing.summary_pt)
        
        lines.append(f"\n⏰ Gerado às {datetime.now().strftime('%H:%M')}")
        
        return "\n".join(lines)
    
    async def send_evening_summary(self):
        """Envia resumo do fechamento"""
        logger.info("📋 Preparando resumo do fechamento...")
        
        try:
            # Coleta dados
            sentiments = {}
            for symbol in self._config.symbols:
                sentiments[symbol] = await self._brain.get_sentiment(symbol)
            
            # Formata mensagem
            text = self._format_evening_summary(sentiments)
            
            await self._safe_send_message(text)
            
            logger.info("✅ Resumo noturno enviado")
            
        except Exception as e:
            logger.error(f"❌ Erro no resumo noturno: {e}")
    
    def _format_evening_summary(self, sentiments: Dict[str, MarketSentiment]) -> str:
        """Formata resumo do fechamento"""
        lines = [
            "🌙 *RESUMO DO FECHAMENTO*",
            f"📅 {datetime.now().strftime('%d/%m/%Y')}",
            "",
            "📊 *SENTIMENTO FINAL DO DIA:*",
        ]
        
        for symbol, sentiment in sentiments.items():
            emoji = self._sentiment_emoji(sentiment.sentiment_level)
            lines.append(
                f"  {emoji} {symbol}: {self._sentiment_text(sentiment.sentiment_level)} "
                f"({sentiment.overall_sentiment:+.2f})"
            )
        
        lines.extend([
            "",
            "🌙 _Boas análises e até amanhã!_",
            f"⏰ {datetime.now().strftime('%H:%M')}"
        ])
        
        return "\n".join(lines)
    
    # ========================================================================
    # ALERTAS
    # ========================================================================
    
    async def check_important_news(self):
        """Verifica notícias importantes"""
        if not self._config.high_impact_alerts:
            return
        
        try:
            news = await self._brain.get_news(self._config.symbols, limit=10, hours_back=1)
            
            for item in news:
                # Evita duplicatas
                news_id = f"{item.title[:30]}_{item.timestamp.isoformat()}"
                if news_id in self._sent_news_ids:
                    continue
                
                # Verifica impacto
                if item.impact == NewsImpact.HIGH:
                    await self._send_news_alert(item)
                    self._sent_news_ids.add(news_id)
            
            # Limpa IDs antigos
            if len(self._sent_news_ids) > 100:
                self._sent_news_ids = set(list(self._sent_news_ids)[-50:])
                
        except Exception as e:
            logger.warning(f"Erro ao verificar notícias: {e}")
    
    async def _send_news_alert(self, news: NewsItem):
        """Envia alerta de notícia importante"""
        emoji = self._sentiment_emoji_score(news.sentiment_score)
        
        text = f"""🚨 *NOTÍCIA IMPORTANTE*

{emoji} *{news.title}*

📰 Fonte: {news.source}
🎯 Impacto: ALTO
📊 Sentimento: {news.sentiment_score:+.2f}

⏰ {news.timestamp.strftime('%H:%M')}"""
        
        await self._safe_send_message(text)
    
    async def check_upcoming_events(self):
        """Verifica eventos próximos"""
        if not self._config.high_impact_alerts:
            return
        
        try:
            events = await self._brain.get_today_events(currencies=['USD', 'EUR', 'GBP'])
            
            now = datetime.now()
            for event in events:
                # Alerta 30 min antes de eventos de alto impacto
                time_until = (event.timestamp - now).total_seconds() / 60
                
                if event.impact == NewsImpact.HIGH and 25 <= time_until <= 35:
                    await self._send_event_alert(event)
                    
        except Exception as e:
            logger.warning(f"Erro ao verificar eventos: {e}")
    
    async def _send_event_alert(self, event: EconomicEvent):
        """Envia alerta de evento próximo"""
        text = f"""⏰ *EVENTO EM 30 MINUTOS*

🔴 *{event.name_pt or event.name}*

💱 Moeda: {event.currency}
📊 Previsão: {event.forecast or 'N/A'}
📈 Anterior: {event.previous or 'N/A'}

⚠️ Evento de ALTO IMPACTO - Considere gerenciar posições"""
        
        await self._safe_send_message(text)
    
    async def check_sentiment_changes(self):
        """Verifica mudanças significativas no sentimento"""
        if not self._config.sentiment_alerts:
            return
        
        try:
            for symbol in self._config.symbols:
                sentiment = await self._brain.get_sentiment(symbol)
                
                last_level = self._last_sentiments.get(symbol)
                current_level = sentiment.sentiment_level
                
                if last_level and self._is_significant_change(last_level, current_level):
                    await self._send_sentiment_change_alert(symbol, last_level, current_level, sentiment)
                
                self._last_sentiments[symbol] = current_level
                
        except Exception as e:
            logger.warning(f"Erro ao verificar sentimento: {e}")
    
    def _is_significant_change(self, old: SentimentLevel, new: SentimentLevel) -> bool:
        """Verifica se houve mudança significativa no sentimento"""
        levels = [
            SentimentLevel.VERY_BEARISH,
            SentimentLevel.BEARISH,
            SentimentLevel.NEUTRAL,
            SentimentLevel.BULLISH,
            SentimentLevel.VERY_BULLISH
        ]
        
        old_idx = levels.index(old)
        new_idx = levels.index(new)
        
        # Mudança de pelo menos 2 níveis
        return abs(new_idx - old_idx) >= 2
    
    async def _send_sentiment_change_alert(
        self,
        symbol: str,
        old_level: SentimentLevel,
        new_level: SentimentLevel,
        sentiment: MarketSentiment
    ):
        """Envia alerta de mudança de sentimento"""
        direction = "📈" if new_level.value > old_level.value else "📉"
        
        text = f"""🔄 *MUDANÇA DE SENTIMENTO*

{direction} *{symbol}*

De: {self._sentiment_text(old_level)}
Para: {self._sentiment_text(new_level)}

📊 Score atual: {sentiment.overall_sentiment:+.2f}
📰 Baseado em {sentiment.news_count} notícias

⏰ {datetime.now().strftime('%H:%M')}"""
        
        await self._safe_send_message(text)
    
    # ========================================================================
    # COMANDOS MANUAIS
    # ========================================================================
    
    async def send_quick_analysis(self, symbol: str):
        """
        Envia análise rápida de um símbolo.
        
        Args:
            symbol: Símbolo para analisar
        """
        try:
            # Coleta dados
            sentiment = await self._brain.get_sentiment(symbol)
            indicators = await self._brain.get_technical_indicators(symbol)
            cot = await self._brain.get_cot_analysis(symbol)
            
            # Formata
            text = self._format_quick_analysis(symbol, sentiment, indicators, cot)
            
            await self._safe_send_message(text)
            
        except Exception as e:
            logger.error(f"Erro na análise rápida: {e}")
            await self._safe_send_alert(f"Erro ao analisar {symbol}", level="error")
    
    def _format_quick_analysis(
        self,
        symbol: str,
        sentiment: MarketSentiment,
        indicators: Dict[str, Any],
        cot: Dict[str, Any]
    ) -> str:
        """Formata análise rápida"""
        lines = [
            f"📊 *ANÁLISE RÁPIDA: {symbol}*",
            f"⏰ {datetime.now().strftime('%H:%M')}",
            "",
        ]
        
        # Sentimento
        emoji = self._sentiment_emoji(sentiment.sentiment_level)
        lines.extend([
            "*SENTIMENTO:*",
            f"  {emoji} {self._sentiment_text(sentiment.sentiment_level)} ({sentiment.overall_sentiment:+.2f})",
            ""
        ])
        
        # Indicadores
        if indicators and not indicators.get('error'):
            lines.append("*INDICADORES (H1):*")
            
            rsi = indicators.get('rsi')
            if rsi:
                rsi_emoji = "🔴" if rsi > 70 else "🟢" if rsi < 30 else "🟡"
                lines.append(f"  RSI: {rsi_emoji} {rsi:.1f}")
            
            macd = indicators.get('macd')
            if macd:
                macd_emoji = "🟢" if macd['histogram'] > 0 else "🔴"
                lines.append(f"  MACD: {macd_emoji} {macd['histogram']:.5f}")
            
            lines.append("")
        
        # COT
        if cot and cot.get('available'):
            lines.extend([
                "*INSTITUCIONAL (COT):*",
                f"  Viés: {cot.get('institutional_bias', 'N/A')}",
                ""
            ])
        
        return "\n".join(lines)
    
    async def send_calendar_today(self):
        """Envia eventos do dia"""
        try:
            events = await self._brain.get_today_events()
            
            await self._telegram.send_calendar_events([{
                'time': e.timestamp.strftime('%H:%M'),
                'name': e.name_pt or e.name,
                'currency': e.currency,
                'impact': e.impact.value
            } for e in events])
            
        except Exception as e:
            logger.error(f"Erro ao enviar calendário: {e}")
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _sentiment_emoji(self, level: SentimentLevel) -> str:
        """Retorna emoji para nível de sentimento"""
        emojis = {
            SentimentLevel.VERY_BULLISH: "🟢🟢",
            SentimentLevel.BULLISH: "🟢",
            SentimentLevel.NEUTRAL: "🟡",
            SentimentLevel.BEARISH: "🔴",
            SentimentLevel.VERY_BEARISH: "🔴🔴",
        }
        return emojis.get(level, "⚪")
    
    def _sentiment_emoji_score(self, score: float) -> str:
        """Retorna emoji para score de sentimento"""
        if score > 0.5:
            return "🟢🟢"
        elif score > 0.2:
            return "🟢"
        elif score > -0.2:
            return "🟡"
        elif score > -0.5:
            return "🔴"
        else:
            return "🔴🔴"
    
    def _sentiment_text(self, level: SentimentLevel) -> str:
        """Retorna texto em português para nível de sentimento"""
        texts = {
            SentimentLevel.VERY_BULLISH: "Muito Altista",
            SentimentLevel.BULLISH: "Altista",
            SentimentLevel.NEUTRAL: "Neutro",
            SentimentLevel.BEARISH: "Baixista",
            SentimentLevel.VERY_BEARISH: "Muito Baixista",
        }
        return texts.get(level, "Indefinido")
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    
    async def shutdown(self):
        """Encerra o Advisor"""
        logger.info("🎯 Encerrando Market Advisor...")
        
        try:
            await self._safe_send_alert(
                "🤖 *VIRTUS Advisor Encerrado*\n\nAté a próxima!",
                level="info"
            )
        except:
            pass
        
        logger.info("✅ Market Advisor encerrado")


# Helper
async def get_advisor() -> MarketAdvisor:
    """Retorna instância do Market Advisor"""
    return await MarketAdvisor.get_instance()
