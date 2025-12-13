"""
BRAIN - Market Advisor
Assessor de mercado para briefings diários
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..core.logger import get_logger
from ..core.types import NewsImpact
from ..brain import BrainService
from .telegram_bot import TelegramBot, get_telegram_bot

logger = get_logger("advisor")


class MarketAdvisor:
    """
    Assessor de Mercado
    
    Responsabilidades:
    - Gerar briefings matinais
    - Resumir notícias importantes
    - Alertar sobre eventos do calendário
    - Fornecer contexto macro
    """
    
    def __init__(
        self,
        brain_service: Optional[BrainService] = None,
        telegram_bot: Optional[TelegramBot] = None
    ):
        self._brain = brain_service or BrainService()
        self._telegram = telegram_bot or get_telegram_bot()
        
        # Símbolos para monitorar
        self._symbols = ["XAUUSD", "EURUSD", "GBPUSD"]
        
        # Horário do briefing
        self._briefing_hour = 8  # 8:00
        
        # Task de agendamento
        self._scheduler_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Inicia o advisor"""
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Market Advisor iniciado")
    
    async def stop(self):
        """Para o advisor"""
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Market Advisor parado")
    
    async def _scheduler_loop(self):
        """Loop de agendamento"""
        while True:
            try:
                now = datetime.now()
                
                # Verificar se é hora do briefing
                if now.hour == self._briefing_hour and now.minute == 0:
                    await self.send_morning_briefing()
                    await asyncio.sleep(60)  # Evitar duplicação
                
                # Verificar eventos próximos
                await self._check_upcoming_events()
                
                await asyncio.sleep(60)  # Verificar a cada minuto
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no scheduler: {e}")
                await asyncio.sleep(300)
    
    async def _check_upcoming_events(self):
        """Verifica eventos próximos e envia alertas"""
        try:
            events = await self._brain.get_calendar_events(days_ahead=1)
            
            now = datetime.now()
            
            for event in events:
                if event.impact != NewsImpact.HIGH:
                    continue
                
                time_until = event.datetime - now
                minutes_until = time_until.total_seconds() / 60
                
                # Alertar 30 minutos antes
                if 29 <= minutes_until <= 31:
                    await self._telegram.notify_alert(
                        level="warning",
                        title="Evento Econômico em 30min",
                        message=(
                            f"📅 {event.name_pt or event.name}\n"
                            f"🌍 {event.country}\n"
                            f"⏰ {event.datetime.strftime('%H:%M')}\n"
                            f"⚡ Alto Impacto"
                        )
                    )
                    
        except Exception as e:
            logger.error(f"Erro ao verificar eventos: {e}")
    
    # ==========================================================================
    # BRIEFINGS
    # ==========================================================================
    
    async def send_morning_briefing(self):
        """Envia briefing matinal"""
        logger.info("Gerando briefing matinal")
        
        try:
            briefing = await self.generate_briefing()
            await self._telegram.send_message(briefing)
            logger.info("Briefing matinal enviado")
        except Exception as e:
            logger.error(f"Erro ao enviar briefing: {e}")
    
    async def generate_briefing(self) -> str:
        """
        Gera briefing completo do mercado
        
        Returns:
            Texto do briefing em português
        """
        sections = []
        
        # Cabeçalho
        now = datetime.now()
        header = f"""
☀️ <b>BOM DIA! BRIEFING DO MERCADO</b>
📅 {now.strftime('%d/%m/%Y')} - {now.strftime('%A')}
"""
        sections.append(header)
        
        # Sessão de trading
        session = self._get_current_session()
        sections.append(f"🌍 <b>Sessão Atual:</b> {session}\n")
        
        # Calendário econômico
        calendar_section = await self._generate_calendar_section()
        sections.append(calendar_section)
        
        # Resumo de notícias
        news_section = await self._generate_news_section()
        sections.append(news_section)
        
        # Análise por símbolo
        for symbol in self._symbols:
            symbol_section = await self._generate_symbol_section(symbol)
            sections.append(symbol_section)
        
        # Recomendação geral
        recommendation = await self._generate_recommendation()
        sections.append(recommendation)
        
        return "\n".join(sections)
    
    def _get_current_session(self) -> str:
        """Retorna sessão atual de trading"""
        hour = datetime.now().hour
        
        if 0 <= hour < 8:
            return "Ásia/Sydney"
        elif 8 <= hour < 12:
            return "Europa/Londres"
        elif 12 <= hour < 17:
            return "Europa/Nova York"
        elif 17 <= hour < 21:
            return "Nova York"
        else:
            return "Ásia"
    
    async def _generate_calendar_section(self) -> str:
        """Gera seção do calendário"""
        try:
            events = await self._brain.get_calendar_events(days_ahead=1)
            
            if not events:
                return "📅 <b>Calendário:</b> Sem eventos importantes hoje.\n"
            
            section = "📅 <b>CALENDÁRIO ECONÔMICO</b>\n"
            
            # Filtrar eventos de hoje
            today = datetime.now().date()
            today_events = [
                e for e in events
                if e.datetime.date() == today
            ]
            
            if not today_events:
                section += "Sem eventos importantes hoje.\n"
                return section
            
            for event in today_events[:5]:  # Top 5
                impact_emoji = "🔴" if event.impact == NewsImpact.HIGH else "🟡"
                section += (
                    f"{impact_emoji} {event.datetime.strftime('%H:%M')} - "
                    f"<b>{event.name_pt or event.name}</b> ({event.country})\n"
                )
            
            return section + "\n"
            
        except Exception as e:
            logger.error(f"Erro ao gerar calendário: {e}")
            return "📅 <b>Calendário:</b> Erro ao carregar.\n"
    
    async def _generate_news_section(self) -> str:
        """Gera seção de notícias"""
        try:
            news_list = await self._brain.get_news(limit=10)
            
            if not news_list:
                return "📰 <b>Notícias:</b> Sem notícias recentes.\n"
            
            section = "📰 <b>PRINCIPAIS NOTÍCIAS</b>\n"
            
            for news in news_list[:5]:
                impact_emoji = "🔴" if news.impact == NewsImpact.HIGH else "🟡" if news.impact == NewsImpact.MEDIUM else "🟢"
                section += f"{impact_emoji} {news.title[:60]}...\n"
            
            return section + "\n"
            
        except Exception as e:
            logger.error(f"Erro ao gerar notícias: {e}")
            return "📰 <b>Notícias:</b> Erro ao carregar.\n"
    
    async def _generate_symbol_section(self, symbol: str) -> str:
        """Gera seção de análise por símbolo"""
        try:
            context = await self._brain.get_macro_context(symbol)
            
            symbol_names = {
                "XAUUSD": "🥇 OURO (XAU/USD)",
                "EURUSD": "💶 EUR/USD",
                "GBPUSD": "💷 GBP/USD"
            }
            
            name = symbol_names.get(symbol, symbol)
            section = f"\n{name}\n"
            
            # Bias geral
            bias = context.get("overall_bias", {})
            direction = bias.get("direction_pt", "Neutro")
            strength = bias.get("strength", 0)
            
            strength_text = "Fraco" if strength < 2 else "Moderado" if strength < 3 else "Forte"
            
            section += f"📊 <b>Viés:</b> {direction} ({strength_text})\n"
            
            # COT
            cot = context.get("cot", {})
            if cot.get("available"):
                section += f"🏦 <b>Institucionais:</b> {cot.get('speculator_bias', 'N/A')}\n"
            
            # Sentimento
            sentiment = context.get("sentiment_score", 0)
            sent_emoji = "🟢" if sentiment > 0.2 else "🔴" if sentiment < -0.2 else "🟡"
            section += f"{sent_emoji} <b>Sentimento:</b> {sentiment:.2f}\n"
            
            return section
            
        except Exception as e:
            logger.error(f"Erro ao gerar seção de {symbol}: {e}")
            return f"\n{symbol}: Erro ao analisar\n"
    
    async def _generate_recommendation(self) -> str:
        """Gera recomendação geral"""
        try:
            # Verificar calendário para risco
            events = await self._brain.get_calendar_events(days_ahead=1)
            high_impact_today = len([
                e for e in events
                if e.impact == NewsImpact.HIGH and e.datetime.date() == datetime.now().date()
            ])
            
            section = "\n💡 <b>RECOMENDAÇÃO</b>\n"
            
            if high_impact_today >= 3:
                section += (
                    "⚠️ <b>CAUTELA</b>: Múltiplos eventos de alto impacto hoje. "
                    "Considere reduzir exposição ou aguardar dados.\n"
                )
            elif high_impact_today >= 1:
                section += (
                    "⚡ Há eventos importantes hoje. "
                    "Opere com stops adequados e evite exposição excessiva próximo aos horários.\n"
                )
            else:
                section += (
                    "✅ Calendário favorável. "
                    "Operações normais podem ser realizadas.\n"
                )
            
            section += "\n🤖 <i>BRAIN Trading Bot</i>"
            
            return section
            
        except Exception as e:
            logger.error(f"Erro ao gerar recomendação: {e}")
            return "\n💡 <b>RECOMENDAÇÃO:</b> Erro ao analisar.\n"
    
    # ==========================================================================
    # MÉTODOS PÚBLICOS
    # ==========================================================================
    
    async def get_quick_analysis(self, symbol: str) -> str:
        """
        Obtém análise rápida de um símbolo
        
        Args:
            symbol: Símbolo
            
        Returns:
            Texto de análise
        """
        try:
            context = await self._brain.get_macro_context(symbol)
            
            bias = context.get("overall_bias", {})
            direction = bias.get("direction_pt", "Neutro")
            
            calendar = context.get("calendar", {})
            safe = calendar.get("safe_to_trade", True)
            
            return (
                f"📊 <b>{symbol}</b>\n"
                f"Viés: {direction}\n"
                f"Operar: {'✅ Sim' if safe else '⚠️ Cautela'}"
            )
            
        except Exception as e:
            return f"Erro ao analisar {symbol}: {e}"


def create_market_advisor(
    brain_service: Optional[BrainService] = None,
    telegram_bot: Optional[TelegramBot] = None
) -> MarketAdvisor:
    """Cria instância do Market Advisor"""
    return MarketAdvisor(brain_service, telegram_bot)
