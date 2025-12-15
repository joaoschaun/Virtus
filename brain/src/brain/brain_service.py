"""
VIRTUS Brain - Brain Service
=============================

Serviço central do Brain - orquestra providers, cache e budget.
Singleton que fornece dados unificados para todos os bots.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..core.logger import get_logger
from ..core.config import Config, get_config
from ..core.types import (
    NewsItem, MarketSentiment, EconomicEvent,
    SentimentLevel, NewsImpact, DailyBriefing
)
from ..core.exceptions import (
    BrainError, ProviderUnavailableError, NoDataError
)
from .cache import CacheManager, get_cache_manager
from .budget import BudgetManager, get_budget_manager
from .providers import (
    ForexNewsProvider,
    FinnhubProvider,
    TwelveDataProvider,
    FMPProvider,
    CFTCProvider
)

logger = get_logger("brain")


class BrainService:
    """
    Serviço central do Brain.
    
    Responsabilidades:
    - Gerenciar providers de dados
    - Agregar dados de múltiplas fontes
    - Coordenar cache e budget
    - Fornecer dados unificados para bots
    
    Uso:
        brain = await BrainService.get_instance()
        news = await brain.get_news(['XAUUSD'])
        sentiment = await brain.get_sentiment('XAUUSD')
    """
    
    _instance: Optional['BrainService'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self.config: Optional[Config] = None
        self.cache_manager: Optional[CacheManager] = None
        self.budget_manager: Optional[BudgetManager] = None
        
        # Providers
        self._forexnews: Optional[ForexNewsProvider] = None
        self._finnhub: Optional[FinnhubProvider] = None
        self._twelvedata: Optional[TwelveDataProvider] = None
        self._fmp: Optional[FMPProvider] = None
        self._cftc: Optional[CFTCProvider] = None
        
        # Status
        self._initialized = False
        self._provider_status: Dict[str, bool] = {}
    
    @classmethod
    async def get_instance(cls) -> 'BrainService':
        """Retorna instância singleton do Brain"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                await cls._instance.initialize()
            return cls._instance
    
    async def initialize(self):
        """Inicializa o Brain Service"""
        if self._initialized:
            return
        
        logger.info("🧠 Inicializando Brain Service...")
        
        try:
            # Carrega configuração
            self.config = get_config()
            
            # Inicializa cache e budget
            data_dir = Path(self.config.data_dir) / "brain"
            self.cache_manager = get_cache_manager(data_dir / "cache")
            self.budget_manager = get_budget_manager(data_dir)
            
            # Configura callbacks de alerta de budget
            self.budget_manager.add_alert_callback(self._on_budget_alert)
            
            # Inicializa providers
            await self._initialize_providers()
            
            # Verifica saúde dos providers
            await self._check_providers_health()
            
            self._initialized = True
            logger.info("✅ Brain Service inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Brain: {e}")
            raise BrainError(f"Falha na inicialização: {e}")
    
    async def _initialize_providers(self):
        """Inicializa todos os providers"""
        api_keys = self.config.api_keys
        
        # ForexNews (principal para notícias)
        if api_keys.forexnews:
            self._forexnews = ForexNewsProvider(
                api_key=api_keys.forexnews,
                cache_manager=self.cache_manager,
                budget_manager=self.budget_manager
            )
            logger.debug("Provider ForexNews inicializado")
        
        # Finnhub (calendário e backup de notícias)
        if api_keys.finnhub:
            self._finnhub = FinnhubProvider(
                api_key=api_keys.finnhub,
                cache_manager=self.cache_manager,
                budget_manager=self.budget_manager
            )
            logger.debug("Provider Finnhub inicializado")
        
        # TwelveData (indicadores técnicos e preços)
        if api_keys.twelvedata:
            self._twelvedata = TwelveDataProvider(
                api_key=api_keys.twelvedata,
                cache_manager=self.cache_manager,
                budget_manager=self.budget_manager
            )
            logger.debug("Provider TwelveData inicializado")
        
        # FMP (backup calendário)
        if api_keys.fmp:
            self._fmp = FMPProvider(
                api_key=api_keys.fmp,
                cache_manager=self.cache_manager,
                budget_manager=self.budget_manager
            )
            logger.debug("Provider FMP inicializado")
        
        # CFTC (COT Reports - gratuito)
        self._cftc = CFTCProvider()
        logger.debug("Provider CFTC inicializado (gratuito)")
    
    async def _check_providers_health(self):
        """Verifica status de saúde dos providers"""
        providers = [
            ('cftc', self._cftc),
            ('forexnews', self._forexnews),
            ('finnhub', self._finnhub),
            ('twelvedata', self._twelvedata),
            ('fmp', self._fmp),
        ]
        
        for name, provider in providers:
            if provider:
                try:
                    status = await asyncio.wait_for(
                        provider.health_check(),
                        timeout=10
                    )
                    self._provider_status[name] = status
                    emoji = "✅" if status else "❌"
                    logger.info(f"{emoji} Provider {name}: {'OK' if status else 'FALHA'}")
                except asyncio.TimeoutError:
                    self._provider_status[name] = False
                    logger.warning(f"⏱️ Provider {name}: timeout")
                except Exception as e:
                    self._provider_status[name] = False
                    logger.warning(f"❌ Provider {name}: {e}")
    
    async def _on_budget_alert(self, level: str, provider: str, message: str):
        """Callback para alertas de budget"""
        logger.warning(f"Budget Alert [{level}]: {message}")
        # TODO: Integrar com Telegram para enviar alertas
    
    # ========================================================================
    # MÉTODOS PÚBLICOS - NOTÍCIAS
    # ========================================================================
    
    async def get_news(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 10,
        hours_back: int = 24
    ) -> List[NewsItem]:
        """
        Busca notícias agregadas de múltiplos providers.
        
        Args:
            symbols: Símbolos para filtrar (None = todos)
            limit: Número máximo de notícias
            hours_back: Horas no passado
            
        Returns:
            Lista de notícias ordenadas por timestamp
        """
        # Tenta cache primeiro
        cache_key = f"news:{':'.join(symbols or ['all'])}:{hours_back}"
        cached = await self.cache_manager.get(cache_key, 'news')
        if cached:
            return cached[:limit]
        
        all_news = []
        
        # ForexNews (principal)
        if self._forexnews and self._provider_status.get('forexnews'):
            try:
                news = await self._forexnews.get_news(symbols, limit * 2, hours_back)
                all_news.extend(news)
            except Exception as e:
                logger.warning(f"Erro ForexNews: {e}")
        
        # Finnhub (backup)
        if self._finnhub and self._provider_status.get('finnhub'):
            try:
                news = await self._finnhub.get_news(symbols, limit)
                all_news.extend(news)
            except Exception as e:
                logger.warning(f"Erro Finnhub: {e}")
        
        # Remove duplicatas (por título similar)
        unique_news = self._deduplicate_news(all_news)
        
        # Ordena por timestamp (mais recentes primeiro)
        # Normaliza para comparar datas com/sem timezone
        from datetime import timezone
        def get_timestamp(x):
            if x.timestamp.tzinfo is None:
                return x.timestamp.replace(tzinfo=timezone.utc)
            return x.timestamp
        
        unique_news.sort(key=get_timestamp, reverse=True)
        
        # Cache resultado
        await self.cache_manager.set(cache_key, unique_news, 'news')
        
        return unique_news[:limit]
    
    def _deduplicate_news(self, news: List[NewsItem]) -> List[NewsItem]:
        """Remove notícias duplicadas por título similar"""
        seen_titles = set()
        unique = []
        
        for item in news:
            # Normaliza título para comparação
            normalized = item.title.lower().strip()[:50]
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(item)
        
        return unique
    
    # ========================================================================
    # MÉTODOS PÚBLICOS - SENTIMENTO
    # ========================================================================
    
    async def get_sentiment(
        self,
        symbol: str
    ) -> MarketSentiment:
        """
        Calcula sentimento agregado para um símbolo.
        
        Args:
            symbol: Símbolo (ex: 'XAUUSD')
            
        Returns:
            MarketSentiment com scores agregados
        """
        # Tenta cache
        cache_key = f"sentiment:{symbol}"
        cached = await self.cache_manager.get(cache_key, 'sentiment')
        if cached:
            return cached
        
        sentiments = []
        
        # ForexNews sentiment
        if self._forexnews and self._provider_status.get('forexnews'):
            try:
                sent = await self._forexnews.get_sentiment(symbol)
                if sent:
                    sentiments.append(sent)
            except Exception as e:
                logger.warning(f"Erro sentimento ForexNews: {e}")
        
        # Agrega sentimentos
        if not sentiments:
            result = MarketSentiment(
                symbol=symbol,
                timestamp=datetime.now(),
                overall_sentiment=0.0,
                sentiment_level=SentimentLevel.NEUTRAL,
                explanation_pt="Dados de sentimento não disponíveis"
            )
        else:
            # Média ponderada
            total_score = sum(s.news_sentiment for s in sentiments)
            avg_score = total_score / len(sentiments)
            
            # Determina nível
            if avg_score >= 0.5:
                level = SentimentLevel.VERY_BULLISH
            elif avg_score >= 0.2:
                level = SentimentLevel.BULLISH
            elif avg_score >= -0.2:
                level = SentimentLevel.NEUTRAL
            elif avg_score >= -0.5:
                level = SentimentLevel.BEARISH
            else:
                level = SentimentLevel.VERY_BEARISH
            
            result = MarketSentiment(
                symbol=symbol,
                timestamp=datetime.now(),
                news_sentiment=avg_score,
                overall_sentiment=avg_score,
                sentiment_level=level,
                news_count=sum(s.news_count for s in sentiments),
                sources=[s.sources[0] for s in sentiments if s.sources],
                explanation_pt=sentiments[0].explanation_pt if sentiments else ""
            )
        
        # Cache
        await self.cache_manager.set(cache_key, result, 'sentiment')
        
        return result
    
    # ========================================================================
    # MÉTODOS PÚBLICOS - CALENDÁRIO
    # ========================================================================
    
    async def get_calendar_events(
        self,
        currencies: Optional[List[str]] = None,
        days_ahead: int = 7,
        impact_filter: Optional[NewsImpact] = None
    ) -> List[EconomicEvent]:
        """
        Busca eventos do calendário econômico.
        
        Args:
            currencies: Moedas para filtrar
            days_ahead: Dias à frente
            impact_filter: Filtrar por impacto mínimo
            
        Returns:
            Lista de eventos
        """
        # Tenta cache
        cache_key = f"calendar:{':'.join(currencies or ['all'])}:{days_ahead}"
        cached = await self.cache_manager.get(cache_key, 'calendar')
        if cached:
            events = cached
        else:
            events = []
            
            # Finnhub (principal para calendário)
            if self._finnhub and self._provider_status.get('finnhub'):
                try:
                    ev = await self._finnhub.get_events(
                        start_date=datetime.now(),
                        end_date=datetime.now() + timedelta(days=days_ahead),
                        currencies=currencies
                    )
                    events.extend(ev)
                except Exception as e:
                    logger.warning(f"Erro calendário Finnhub: {e}")
            
            # FMP (backup)
            if self._fmp and self._provider_status.get('fmp') and not events:
                try:
                    ev = await self._fmp.get_events(
                        start_date=datetime.now(),
                        end_date=datetime.now() + timedelta(days=days_ahead),
                        currencies=currencies
                    )
                    events.extend(ev)
                except Exception as e:
                    logger.warning(f"Erro calendário FMP: {e}")
            
            # Cache
            if events:
                await self.cache_manager.set(cache_key, events, 'calendar')
        
        # Filtra por impacto se especificado
        if impact_filter:
            impact_values = {NewsImpact.LOW: 1, NewsImpact.MEDIUM: 2, NewsImpact.HIGH: 3}
            min_impact = impact_values.get(impact_filter, 1)
            events = [e for e in events if impact_values.get(e.impact, 1) >= min_impact]
        
        return events
    
    async def get_today_events(
        self,
        currencies: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """Busca eventos de hoje"""
        if self._finnhub and self._provider_status.get('finnhub'):
            return await self._finnhub.get_today_events(currencies)
        return []
    
    # ========================================================================
    # MÉTODOS PÚBLICOS - COT
    # ========================================================================
    
    async def get_cot_analysis(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        Busca análise do COT para um símbolo.
        Usa CFTC (fonte oficial, gratuita) como principal.
        
        Args:
            symbol: Símbolo
            
        Returns:
            Análise do COT
        """
        # Tenta cache
        cache_key = f"cot:{symbol}"
        cached = await self.cache_manager.get(cache_key, 'cot')
        if cached:
            return cached
        
        # CFTC é gratuito e sempre disponível
        if self._cftc:
            try:
                cot_report = await self._cftc.get_cot_report(symbol)
                if cot_report:
                    result = {
                        'symbol': symbol,
                        'available': True,
                        'report_date': cot_report.report_date.isoformat(),
                        'nc_long': cot_report.nc_long,
                        'nc_short': cot_report.nc_short,
                        'nc_net': cot_report.nc_net,
                        'comm_long': cot_report.comm_long,
                        'comm_short': cot_report.comm_short,
                        'comm_net': cot_report.comm_net,
                        'open_interest': cot_report.open_interest,
                        'sentiment': cot_report.sentiment,
                        'explanation_pt': cot_report.explanation_pt,
                        'source': 'CFTC'
                    }
                    await self.cache_manager.set(cache_key, result, 'cot')
                    return result
            except Exception as e:
                logger.warning(f"Erro COT CFTC: {e}")
        
        # Fallback para FMP se disponível
        if self._fmp and self._provider_status.get('fmp'):
            try:
                cot = await self._fmp.get_cot_analysis(symbol)
                if cot and cot.get('available'):
                    await self.cache_manager.set(cache_key, cot, 'cot')
                return cot
            except Exception as e:
                logger.warning(f"Erro COT FMP: {e}")
        
        return {
            'symbol': symbol,
            'available': False,
            'message': 'Dados COT não disponíveis'
        }
    
    # ========================================================================
    # MÉTODOS PÚBLICOS - INDICADORES TÉCNICOS
    # ========================================================================
    
    async def get_technical_indicators(
        self,
        symbol: str,
        interval: str = '1h'
    ) -> Dict[str, Any]:
        """
        Busca indicadores técnicos de um símbolo.
        
        Args:
            symbol: Símbolo
            interval: Timeframe
            
        Returns:
            Dict com indicadores
        """
        # Tenta cache
        cache_key = f"indicators:{symbol}:{interval}"
        cached = await self.cache_manager.get(cache_key, 'indicator')
        if cached:
            return cached
        
        if self._twelvedata and self._provider_status.get('twelvedata'):
            try:
                indicators = await self._twelvedata.get_all_indicators(symbol, interval)
                await self.cache_manager.set(cache_key, indicators, 'indicator')
                return indicators
            except Exception as e:
                logger.warning(f"Erro indicadores TwelveData: {e}")
        
        return {
            'symbol': symbol,
            'interval': interval,
            'error': 'Indicadores não disponíveis'
        }
    
    # ========================================================================
    # MÉTODOS PÚBLICOS - BRIEFING
    # ========================================================================
    
    async def generate_daily_briefing(
        self,
        symbols: Optional[List[str]] = None
    ) -> DailyBriefing:
        """
        Gera briefing diário completo.
        
        Args:
            symbols: Símbolos para incluir (default: todos configurados)
            
        Returns:
            DailyBriefing com todas as informações
        """
        if symbols is None:
            symbols = self.config.symbols if self.config else ['XAUUSD', 'EURUSD', 'GBPUSD']
        
        logger.info(f"📋 Gerando briefing diário para {symbols}")
        
        # Coleta dados em paralelo
        news_task = self.get_news(symbols, limit=5, hours_back=24)
        events_task = self.get_today_events()
        
        sentiments_tasks = [self.get_sentiment(s) for s in symbols]
        
        # Aguarda todas as tasks
        results = await asyncio.gather(
            news_task,
            events_task,
            *sentiments_tasks,
            return_exceptions=True
        )
        
        # Processa resultados
        news = results[0] if not isinstance(results[0], Exception) else []
        events = results[1] if not isinstance(results[1], Exception) else []
        sentiments = {}
        for i, symbol in enumerate(symbols):
            result = results[2 + i]
            if not isinstance(result, Exception):
                sentiments[symbol] = result
        
        # Monta briefing
        briefing = DailyBriefing(
            date=datetime.now(),
            top_news=news,
            events=events,
            sentiments=sentiments,
            summary_pt=self._generate_briefing_summary(news, events, sentiments)
        )
        
        return briefing
    
    def _generate_briefing_summary(
        self,
        news: List[NewsItem],
        events: List[EconomicEvent],
        sentiments: Dict[str, MarketSentiment]
    ) -> str:
        """Gera resumo do briefing em português"""
        lines = [
            "📊 **BRIEFING DIÁRIO DO MERCADO**",
            f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            ""
        ]
        
        # Sentimentos
        if sentiments:
            lines.append("**SENTIMENTO POR ATIVO:**")
            for symbol, sent in sentiments.items():
                emoji = "🟢" if sent.overall_sentiment > 0.2 else "🔴" if sent.overall_sentiment < -0.2 else "🟡"
                lines.append(f"{emoji} {symbol}: {sent.sentiment_level.value} ({sent.overall_sentiment:+.2f})")
            lines.append("")
        
        # Eventos importantes
        high_impact = [e for e in events if e.impact == NewsImpact.HIGH]
        if high_impact:
            lines.append("**⚠️ EVENTOS DE ALTO IMPACTO HOJE:**")
            for event in high_impact[:5]:
                time_str = event.timestamp.strftime('%H:%M')
                lines.append(f"• {time_str} - {event.name_pt or event.name} ({event.currency})")
            lines.append("")
        
        # Notícias principais
        if news:
            lines.append("**📰 PRINCIPAIS NOTÍCIAS:**")
            for item in news[:3]:
                lines.append(f"• {item.title}")
            lines.append("")
        
        return "\n".join(lines)
    
    # ========================================================================
    # STATUS E MÉTRICAS
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do Brain"""
        return {
            'initialized': self._initialized,
            'providers': self._provider_status,
            'cache_stats': self.cache_manager.get_stats() if self.cache_manager else {},
            'budget_status': self.budget_manager.get_all_status() if self.budget_manager else {},
        }
    
    async def shutdown(self):
        """Encerra o Brain Service"""
        logger.info("🧠 Encerrando Brain Service...")
        
        # Fecha providers
        for provider in [self._forexnews, self._finnhub, self._twelvedata, self._fmp]:
            if provider:
                await provider.close()
        
        logger.info("✅ Brain Service encerrado")


# Função helper para obter instância
async def get_brain() -> BrainService:
    """Retorna instância do Brain Service"""
    return await BrainService.get_instance()
