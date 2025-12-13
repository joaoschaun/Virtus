"""
🧠 BRAIN SERVICE
Serviço central de dados e análises - Singleton compartilhado por todos os bots
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..core.config import Config
from ..core.logger import get_logger
from ..core.types import (
    NewsItem, SentimentData, CalendarEvent, COTData,
    SentimentLevel, NewsImpact
)
from ..core.exceptions import BrainError, BudgetExceededError

from .cache.memory_cache import MemoryCache
from .budget.budget_manager import BudgetManager
from .providers.forexnews_provider import ForexNewsProvider
from .providers.finnhub_provider import FinnhubProvider
from .providers.cot_provider import COTProvider
from .providers.calendar_provider import CalendarProvider
from .analyzers.news_analyzer import NewsAnalyzer
from .analyzers.sentiment_analyzer import SentimentAnalyzer
from .analyzers.macro_analyzer import MacroAnalyzer

logger = get_logger("brain")


@dataclass
class BrainStatus:
    """Status do Brain Service"""
    running: bool
    cache_status: Dict[str, Any]
    budget_status: Dict[str, Any]
    providers_status: Dict[str, bool]
    last_update: datetime


class BrainService:
    """
    🧠 BRAIN - Serviço Central de Dados
    
    Singleton que gerencia:
    - Cache compartilhado (evita chamadas duplicadas de API)
    - Budget de APIs (controle de gastos)
    - Providers de dados (notícias, calendário, COT, etc.)
    - Analyzers (sentimento, macro, etc.)
    
    Todos os bots consultam o Brain para obter dados de mercado.
    """
    
    _instance: Optional["BrainService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._running = False
        
        # Configuração
        self._config = Config()
        self._brain_config = self._config.brain
        
        # Cache
        self._cache = MemoryCache(
            max_size=self._brain_config.cache.get("max_size", 1000)
        )
        
        # Budget Manager
        self._budget = BudgetManager(self._brain_config.budget)
        
        # Providers
        self._providers = {}
        self._init_providers()
        
        # Analyzers
        self._analyzers = {}
        self._init_analyzers()
        
        logger.info("🧠 Brain Service inicializado")
    
    def _init_providers(self):
        """Inicializa os providers de dados"""
        providers_config = self._brain_config.providers
        
        if providers_config.get("forexnews", {}).get("enabled", False):
            self._providers["forexnews"] = ForexNewsProvider(
                providers_config.get("forexnews", {})
            )
        
        if providers_config.get("finnhub", {}).get("enabled", False):
            self._providers["finnhub"] = FinnhubProvider(
                providers_config.get("finnhub", {})
            )
        
        if providers_config.get("cot", {}).get("enabled", False):
            self._providers["cot"] = COTProvider(
                providers_config.get("cot", {})
            )
        
        if providers_config.get("calendar", {}).get("enabled", False):
            self._providers["calendar"] = CalendarProvider(
                providers_config.get("calendar", {})
            )
        
        logger.info(f"🔌 {len(self._providers)} providers inicializados")
    
    def _init_analyzers(self):
        """Inicializa os analyzers"""
        analyzers_config = self._brain_config.analyzers
        
        if analyzers_config.get("news", {}).get("enabled", True):
            self._analyzers["news"] = NewsAnalyzer(analyzers_config.get("news", {}))
        
        if analyzers_config.get("sentiment", {}).get("enabled", True):
            self._analyzers["sentiment"] = SentimentAnalyzer(analyzers_config.get("sentiment", {}))
        
        if analyzers_config.get("macro", {}).get("enabled", True):
            self._analyzers["macro"] = MacroAnalyzer(analyzers_config.get("macro", {}))
        
        logger.info(f"📊 {len(self._analyzers)} analyzers inicializados")
    
    # ============================================================
    # Lifecycle
    # ============================================================
    
    async def start(self):
        """Inicia o Brain Service"""
        if self._running:
            logger.warning("Brain já está rodando")
            return
        
        self._running = True
        logger.info("🧠 Brain Service iniciado")
    
    async def stop(self):
        """Para o Brain Service"""
        self._running = False
        self._cache.clear()
        logger.info("🧠 Brain Service parado")
    
    # ============================================================
    # API de Notícias
    # ============================================================
    
    async def get_news(
        self,
        symbol: Optional[str] = None,
        limit: int = 10,
        min_impact: str = "low"
    ) -> List[NewsItem]:
        """
        Obtém notícias do mercado
        
        Args:
            symbol: Símbolo específico (ex: "XAUUSD") ou None para todas
            limit: Número máximo de notícias
            min_impact: Impacto mínimo ("low", "medium", "high")
            
        Returns:
            Lista de NewsItem
        """
        cache_key = f"news:{symbol or 'all'}:{min_impact}"
        ttl = self._brain_config.cache.get("ttl", {}).get("news", 900)
        
        # Verificar cache
        cached = self._cache.get(cache_key)
        if cached:
            logger.debug(f"📰 News do cache: {len(cached)} itens")
            return cached[:limit]
        
        # Buscar de providers
        news = []
        
        if "forexnews" in self._providers:
            if self._budget.can_use("forexnews"):
                try:
                    provider_news = await self._providers["forexnews"].get_news(symbol)
                    news.extend(provider_news)
                    self._budget.record_usage("forexnews")
                except Exception as e:
                    logger.error(f"Erro ao buscar ForexNews: {e}")
        
        if "finnhub" in self._providers:
            if self._budget.can_use("finnhub"):
                try:
                    provider_news = await self._providers["finnhub"].get_news(symbol)
                    news.extend(provider_news)
                    self._budget.record_usage("finnhub")
                except Exception as e:
                    logger.error(f"Erro ao buscar Finnhub: {e}")
        
        # Filtrar por impacto
        impact_levels = {"low": 0, "medium": 1, "high": 2}
        min_level = impact_levels.get(min_impact, 0)
        news = [
            n for n in news 
            if impact_levels.get(n.impact.value if isinstance(n.impact, NewsImpact) else n.impact, 0) >= min_level
        ]
        
        # Ordenar por data
        news.sort(key=lambda x: x.published_at, reverse=True)
        
        # Cachear
        self._cache.set(cache_key, news, ttl=ttl)
        
        logger.debug(f"📰 News buscadas: {len(news)} itens")
        return news[:limit]
    
    async def get_news_summary(
        self,
        symbol: str,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Obtém resumo de notícias para um símbolo
        
        Returns:
            Dict com notícias resumidas e traduzidas
        """
        if "news" not in self._analyzers:
            return {"news": [], "summary": ""}
        
        news = await self.get_news(symbol, limit=10, min_impact="medium")
        return self._analyzers["news"].summarize(news, language="pt")
    
    # ============================================================
    # API de Sentimento
    # ============================================================
    
    async def get_sentiment(self, symbol: str) -> SentimentData:
        """
        Obtém análise de sentimento para um símbolo
        
        Args:
            symbol: Símbolo (ex: "XAUUSD")
            
        Returns:
            SentimentData com scores e análise
        """
        cache_key = f"sentiment:{symbol}"
        ttl = self._brain_config.cache.get("ttl", {}).get("sentiment", 600)
        
        # Verificar cache
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        
        # Buscar notícias para análise
        news = await self.get_news(symbol, limit=20)
        
        # Analisar sentimento
        if "sentiment" in self._analyzers:
            sentiment = self._analyzers["sentiment"].analyze(symbol, news)
        else:
            sentiment = SentimentData(
                symbol=symbol,
                timestamp=datetime.now(),
                level=SentimentLevel.NEUTRAL
            )
        
        # Cachear
        self._cache.set(cache_key, sentiment, ttl=ttl)
        
        return sentiment
    
    # ============================================================
    # API de Calendário Econômico
    # ============================================================
    
    async def get_calendar_events(
        self,
        days_ahead: int = 1,
        min_impact: str = "low"
    ) -> List[CalendarEvent]:
        """
        Obtém eventos do calendário econômico
        
        Args:
            days_ahead: Dias à frente para buscar
            min_impact: Impacto mínimo
            
        Returns:
            Lista de CalendarEvent
        """
        cache_key = f"calendar:{days_ahead}:{min_impact}"
        ttl = self._brain_config.cache.get("ttl", {}).get("calendar", 3600)
        
        # Verificar cache
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        
        events = []
        
        if "calendar" in self._providers:
            if self._budget.can_use("calendar"):
                try:
                    events = await self._providers["calendar"].get_events(days_ahead)
                    self._budget.record_usage("calendar")
                except Exception as e:
                    logger.error(f"Erro ao buscar calendário: {e}")
        
        # Filtrar por impacto
        impact_levels = {"low": 0, "medium": 1, "high": 2}
        min_level = impact_levels.get(min_impact, 0)
        events = [
            e for e in events
            if impact_levels.get(e.impact.value if isinstance(e.impact, NewsImpact) else e.impact, 0) >= min_level
        ]
        
        # Ordenar por data
        events.sort(key=lambda x: x.datetime)
        
        # Cachear
        self._cache.set(cache_key, events, ttl=ttl)
        
        return events
    
    async def get_high_impact_events(
        self,
        hours_ahead: int = 24
    ) -> List[CalendarEvent]:
        """Obtém apenas eventos de alto impacto"""
        events = await self.get_calendar_events(days_ahead=2, min_impact="high")
        
        cutoff = datetime.now() + timedelta(hours=hours_ahead)
        return [e for e in events if e.datetime <= cutoff]
    
    # ============================================================
    # API de COT (Commitment of Traders)
    # ============================================================
    
    async def get_cot_data(self, symbol: str) -> Optional[COTData]:
        """
        Obtém dados do COT Report
        
        Args:
            symbol: Símbolo (ex: "XAUUSD")
            
        Returns:
            COTData ou None
        """
        cache_key = f"cot:{symbol}"
        ttl = self._brain_config.cache.get("ttl", {}).get("cot", 86400)
        
        # Verificar cache
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        
        cot_data = None
        
        if "cot" in self._providers:
            if self._budget.can_use("cot"):
                try:
                    cot_data = await self._providers["cot"].get_data(symbol)
                    self._budget.record_usage("cot")
                except Exception as e:
                    logger.error(f"Erro ao buscar COT: {e}")
        
        if cot_data:
            self._cache.set(cache_key, cot_data, ttl=ttl)
        
        return cot_data
    
    # ============================================================
    # API de Contexto Macro
    # ============================================================
    
    async def get_macro_context(self) -> Dict[str, Any]:
        """
        Obtém contexto macroeconômico geral
        
        Returns:
            Dict com indicadores macro e análise
        """
        cache_key = "macro:context"
        ttl = self._brain_config.cache.get("ttl", {}).get("macro", 3600)
        
        # Verificar cache
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        
        context = {}
        
        if "macro" in self._analyzers:
            context = await self._analyzers["macro"].get_context()
        
        self._cache.set(cache_key, context, ttl=ttl)
        
        return context
    
    # ============================================================
    # API de Status
    # ============================================================
    
    def get_status(self) -> BrainStatus:
        """Retorna status do Brain Service"""
        return BrainStatus(
            running=self._running,
            cache_status=self._cache.get_stats(),
            budget_status=self._budget.get_status(),
            providers_status={
                name: True for name in self._providers.keys()
            },
            last_update=datetime.now()
        )
    
    def get_budget_status(self) -> Dict[str, Any]:
        """Retorna status do budget de APIs"""
        return self._budget.get_status()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        return self._cache.get_stats()


# ============================================================
# Singleton Helper
# ============================================================

_brain_instance: Optional[BrainService] = None


def get_brain() -> BrainService:
    """
    Retorna instância singleton do Brain Service
    
    Uso:
        brain = get_brain()
        news = await brain.get_news("XAUUSD")
    """
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = BrainService()
    return _brain_instance
