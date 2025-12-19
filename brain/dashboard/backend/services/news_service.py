"""
VIRTUS Dashboard - Serviço de Notícias com Áudio
=================================================

Fornece notícias financeiras em português com síntese de voz.
Integrado com o BrainService para dados em tempo real.
"""

import asyncio
import aiohttp
import hashlib
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import sys

logger = logging.getLogger(__name__)

# Adiciona path do src para imports do Brain
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

# Tenta importar módulos do Brain
BRAIN_AVAILABLE = False
try:
    from src.brain.brain_service import BrainService
    from src.core.types import NewsItem as BrainNewsItem, CalendarEvent, NewsImpact
    BRAIN_AVAILABLE = True
    logger.info("✅ Brain modules disponíveis para integração de notícias")
except ImportError as e:
    logger.warning(f"⚠️ Brain modules não disponíveis: {e}")

# Diretório para cache de áudio
AUDIO_CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class NewsCategory(Enum):
    """Categorias de notícias."""
    FOREX = "forex"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    ECONOMY = "economy"
    STOCKS = "stocks"
    ALL = "all"


class NewsPriority(Enum):
    """Prioridade da notícia."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class NewsItem:
    """Item de notícia."""
    id: str
    title: str
    summary: str
    content: str
    source: str
    category: NewsCategory
    priority: NewsPriority
    published_at: datetime
    url: Optional[str] = None
    
    # Ativos relacionados
    related_symbols: List[str] = field(default_factory=list)
    
    # Áudio
    audio_url: Optional[str] = None
    audio_duration_seconds: int = 0
    
    # Análise
    sentiment: Optional[str] = None  # bullish, bearish, neutral
    impact_score: float = 0.0  # 0 a 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'content': self.content,
            'source': self.source,
            'category': self.category.value,
            'priority': self.priority.value,
            'published_at': self.published_at.isoformat(),
            'url': self.url,
            'related_symbols': self.related_symbols,
            'audio_url': self.audio_url,
            'audio_duration_seconds': self.audio_duration_seconds,
            'sentiment': self.sentiment,
            'impact_score': self.impact_score,
        }


class TextToSpeechService:
    """Serviço de síntese de voz em português usando Edge TTS (Microsoft)."""
    
    def __init__(self, cache_dir: Path = AUDIO_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Vozes disponíveis em português brasileiro
        # Francisca é uma voz feminina natural, Antonio masculina
        self.voice = "pt-BR-FranciscaNeural"  # Voz feminina natural
        # Alternativas: "pt-BR-AntonioNeural" (masculino)
        
        # Tenta importar edge_tts
        try:
            import edge_tts
            self.edge_tts_available = True
        except ImportError:
            logger.warning("edge-tts não instalado. Instale com: pip install edge-tts")
            self.edge_tts_available = False
            
            # Fallback para gTTS
            try:
                from gtts import gTTS
                self.gtts_available = True
            except ImportError:
                self.gtts_available = False
    
    def _get_cache_path(self, text: str) -> Path:
        """Gera path de cache baseado no hash do texto."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return self.cache_dir / f"{text_hash}.mp3"
    
    async def text_to_speech(
        self,
        text: str,
        lang: str = "pt-br"
    ) -> Optional[Path]:
        """
        Converte texto para áudio em português usando Edge TTS (voz natural).
        
        Args:
            text: Texto para converter
            lang: Idioma (default: pt-br)
            
        Returns:
            Path do arquivo de áudio ou None
        """
        # Verifica cache primeiro
        cache_path = self._get_cache_path(text)
        if cache_path.exists():
            return cache_path
        
        # Tenta Edge TTS primeiro (voz mais natural)
        if self.edge_tts_available:
            try:
                import edge_tts
                
                # Usa voz neural da Microsoft (muito mais natural)
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(str(cache_path))
                
                logger.info(f"Áudio gerado (Edge TTS): {cache_path.name}")
                return cache_path
                
            except Exception as e:
                logger.error(f"Erro Edge TTS: {e}, tentando fallback...")
        
        # Fallback para gTTS se Edge TTS falhar
        if hasattr(self, 'gtts_available') and self.gtts_available:
            try:
                from gtts import gTTS
                
                # Gera áudio com gTTS (voz robótica)
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.save(str(cache_path))
                
                logger.info(f"Áudio gerado (gTTS fallback): {cache_path.name}")
                return cache_path
                
            except Exception as e:
                logger.error(f"Erro gTTS: {e}")
                return None
        
        logger.error("Nenhum serviço TTS disponível")
        return None
    
    def get_audio_duration(self, audio_path: Path) -> int:
        """Estima duração do áudio em segundos."""
        try:
            # Estimativa baseada no tamanho do arquivo
            # MP3 ~128kbps = ~16KB/segundo
            file_size = audio_path.stat().st_size
            return max(1, file_size // 16000)
        except:
            return 0
    
    def cleanup_old_cache(self, max_age_hours: int = 24):
        """Remove arquivos de cache antigos."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        for audio_file in self.cache_dir.glob("*.mp3"):
            try:
                mtime = datetime.fromtimestamp(audio_file.stat().st_mtime)
                if mtime < cutoff:
                    audio_file.unlink()
                    logger.debug(f"Cache removido: {audio_file.name}")
            except Exception as e:
                logger.warning(f"Erro ao limpar cache: {e}")


class NewsService:
    """
    Serviço de notícias financeiras em português.
    
    Fontes:
    - Brain Service (notícias do bot em tempo real)
    - Investing.com BR
    - InfoMoney
    - Valor Econômico
    - Bloomberg Línea
    """
    
    def __init__(self):
        self.tts = TextToSpeechService()
        self.news_cache: Dict[str, NewsItem] = {}
        self.last_fetch: Dict[NewsCategory, datetime] = {}
        self.fetch_interval = timedelta(minutes=15)
        
        # Brain Service (se disponível)
        self._brain: Optional[Any] = None
        self._brain_initialized = False
        
        # Palavras-chave para categorização
        self.category_keywords = {
            NewsCategory.FOREX: [
                'dólar', 'euro', 'libra', 'iene', 'câmbio', 'forex',
                'moeda', 'usd', 'eur', 'gbp', 'jpy', 'real'
            ],
            NewsCategory.COMMODITIES: [
                'ouro', 'prata', 'petróleo', 'commodity', 'xauusd',
                'wti', 'brent', 'minério', 'soja', 'milho'
            ],
            NewsCategory.CRYPTO: [
                'bitcoin', 'ethereum', 'cripto', 'blockchain',
                'btc', 'eth', 'criptomoeda'
            ],
            NewsCategory.ECONOMY: [
                'pib', 'inflação', 'juros', 'selic', 'copom', 'fed',
                'banco central', 'economia', 'fiscal', 'emprego'
            ],
            NewsCategory.STOCKS: [
                'ibovespa', 'b3', 'ação', 'ações', 'bolsa', 
                'nasdaq', 's&p', 'dow jones'
            ],
        }
        
        # Palavras para análise de sentimento
        self.bullish_words = [
            'alta', 'sobe', 'subiu', 'valoriza', 'positivo', 'otimismo',
            'ganho', 'lucro', 'recupera', 'avança', 'crescimento'
        ]
        self.bearish_words = [
            'queda', 'cai', 'caiu', 'desvaloriza', 'negativo', 'pessimismo',
            'perda', 'prejuízo', 'recua', 'tombo', 'recessão'
        ]
    
    async def _init_brain(self):
        """Inicializa conexão com o BrainService."""
        if self._brain_initialized:
            return
        
        if not BRAIN_AVAILABLE:
            self._brain_initialized = True
            return
        
        try:
            # Tenta inicializar o BrainService
            self._brain = BrainService()
            await self._brain.initialize()
            self._brain_initialized = True
            logger.info("✅ BrainService inicializado para notícias")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível inicializar BrainService: {e}")
            self._brain = None
            self._brain_initialized = True
    
    async def _fetch_brain_news(self) -> List[NewsItem]:
        """Busca notícias do BrainService."""
        news = []
        
        if not BRAIN_AVAILABLE or not self._brain:
            return news
        
        try:
            # Busca notícias do Brain
            brain_news = await self._brain.get_news(
                symbols=['XAUUSD', 'EURUSD', 'GBPUSD'],
                limit=10,
                hours_back=24
            )
            
            for bn in brain_news:
                # Converte BrainNewsItem para NewsItem do dashboard
                category = self._categorize_news(bn.title + " " + (bn.content or ""))
                sentiment, impact = self._analyze_sentiment(bn.title + " " + (bn.content or ""))
                
                # Mapeia impacto do Brain para prioridade
                if hasattr(bn, 'impact'):
                    if bn.impact == NewsImpact.HIGH:
                        priority = NewsPriority.HIGH
                    elif bn.impact == NewsImpact.MEDIUM:
                        priority = NewsPriority.MEDIUM
                    else:
                        priority = NewsPriority.LOW
                else:
                    priority = NewsPriority.MEDIUM
                
                news_item = NewsItem(
                    id=f"brain_{hashlib.md5(bn.title.encode()).hexdigest()[:12]}",
                    title=bn.title,
                    summary=bn.content[:200] + "..." if bn.content and len(bn.content) > 200 else (bn.content or bn.title),
                    content=bn.content or bn.title,
                    source=bn.source if hasattr(bn, 'source') else "Brain Analysis",
                    category=category,
                    priority=priority,
                    published_at=bn.timestamp if hasattr(bn, 'timestamp') else datetime.now(),
                    url=bn.url if hasattr(bn, 'url') else None,
                    related_symbols=bn.symbols if hasattr(bn, 'symbols') else [],
                    sentiment=sentiment,
                    impact_score=impact,
                )
                news.append(news_item)
            
            logger.info(f"📰 {len(news)} notícias obtidas do Brain")
            
        except Exception as e:
            logger.warning(f"Erro ao buscar notícias do Brain: {e}")
        
        return news
    
    async def _fetch_brain_calendar(self) -> List[NewsItem]:
        """Busca eventos do calendário econômico do BrainService."""
        news = []
        
        if not BRAIN_AVAILABLE or not self._brain:
            return news
        
        try:
            # Busca eventos do calendário
            events = await self._brain.get_calendar_events(days_ahead=1, min_impact="medium")
            
            for event in events:
                # Converte CalendarEvent para NewsItem
                impact_emoji = "🔴" if event.impact == NewsImpact.HIGH else "🟡" if event.impact == NewsImpact.MEDIUM else "🟢"
                
                title = event.name_pt if event.name_pt else event.name
                summary = f"{impact_emoji} {event.country} - {event.datetime.strftime('%H:%M')}"
                
                content = f"Evento: {title}\n"
                content += f"País: {event.country}\n"
                content += f"Horário: {event.datetime.strftime('%H:%M')}\n"
                if event.forecast:
                    content += f"Previsão: {event.forecast}\n"
                if event.previous:
                    content += f"Anterior: {event.previous}\n"
                
                priority = NewsPriority.HIGH if event.impact == NewsImpact.HIGH else NewsPriority.MEDIUM
                
                news_item = NewsItem(
                    id=f"cal_{event.id}",
                    title=f"📅 {title}",
                    summary=summary,
                    content=content,
                    source="Calendário Econômico",
                    category=NewsCategory.ECONOMY,
                    priority=priority,
                    published_at=event.datetime,
                    related_symbols=[event.currency] if event.currency else [],
                    sentiment='neutral',
                    impact_score=0.8 if event.impact == NewsImpact.HIGH else 0.5,
                )
                news.append(news_item)
            
            logger.info(f"📅 {len(news)} eventos do calendário obtidos do Brain")
            
        except Exception as e:
            logger.warning(f"Erro ao buscar calendário do Brain: {e}")
        
        return news

    async def fetch_news(
        self,
        category: NewsCategory = NewsCategory.ALL,
        limit: int = 10
    ) -> List[NewsItem]:
        """
        Busca notícias de múltiplas fontes.
        
        Prioridade:
        1. BrainService (notícias em tempo real do bot)
        2. RSS Feeds (Investing, InfoMoney, Valor)
        3. Calendário Econômico
        
        Args:
            category: Categoria de notícias
            limit: Número máximo de notícias
            
        Returns:
            Lista de NewsItem
        """
        news_items = []
        
        # Inicializa Brain se ainda não foi feito
        await self._init_brain()
        
        # Busca de múltiplas fontes em paralelo
        tasks = [
            self._fetch_brain_news(),        # Notícias do Brain (prioridade)
            self._fetch_brain_calendar(),    # Calendário do Brain
            self._fetch_investing_br(),
            self._fetch_rss_feeds(),
            self._fetch_economic_calendar(), # Fallback local
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                news_items.extend(result)
        
        # Remove duplicatas por título similar
        seen_titles = set()
        unique_news = []
        for item in news_items:
            normalized = item.title.lower().strip()[:50]
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique_news.append(item)
        news_items = unique_news
        
        # Filtra por categoria
        if category != NewsCategory.ALL:
            news_items = [n for n in news_items if n.category == category]
        
        # Ordena por prioridade e data (normaliza para comparação)
        def sort_key(x):
            # Converte para timestamp para evitar problemas de timezone
            timestamp = x.published_at.timestamp() if x.published_at else 0
            return (
                x.priority == NewsPriority.HIGH,
                x.priority == NewsPriority.MEDIUM,
                timestamp
            )
        
        news_items.sort(key=sort_key, reverse=True)
        
        # Limita
        news_items = news_items[:limit]
        
        # Gera áudio para cada notícia
        for news in news_items:
            await self._generate_audio(news)
            self.news_cache[news.id] = news
        
        return news_items
    
    async def _fetch_investing_br(self) -> List[NewsItem]:
        """Busca notícias do Investing.com BR."""
        news = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # RSS Feed do Investing.com Brasil
                url = "https://br.investing.com/rss/news.rss"
                
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        news = self._parse_rss(content, "Investing.com")
        except Exception as e:
            logger.warning(f"Erro ao buscar Investing.com: {e}")
        
        return news
    
    async def _fetch_rss_feeds(self) -> List[NewsItem]:
        """Busca de feeds RSS de fontes brasileiras."""
        news = []
        
        feeds = [
            ("https://www.infomoney.com.br/feed/", "InfoMoney"),
            ("https://valor.globo.com/rss/economia/", "Valor Econômico"),
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                for url, source in feeds:
                    try:
                        async with session.get(url, timeout=10) as response:
                            if response.status == 200:
                                content = await response.text()
                                parsed = self._parse_rss(content, source)
                                news.extend(parsed)
                    except Exception as e:
                        logger.debug(f"Erro em {source}: {e}")
        except Exception as e:
            logger.warning(f"Erro ao buscar RSS: {e}")
        
        return news
    
    async def _fetch_economic_calendar(self) -> List[NewsItem]:
        """Gera notícias do calendário econômico."""
        news = []
        
        # Eventos econômicos importantes de hoje
        events = await self._get_economic_events()
        
        for event in events:
            # Cria notícia para evento
            news_item = NewsItem(
                id=f"cal_{hashlib.md5(event['title'].encode()).hexdigest()[:12]}",
                title=event['title'],
                summary=event['summary'],
                content=event['content'],
                source="Calendário Econômico",
                category=NewsCategory.ECONOMY,
                priority=NewsPriority.HIGH if event.get('high_impact') else NewsPriority.MEDIUM,
                published_at=event.get('time', datetime.now()),
                related_symbols=event.get('symbols', []),
            )
            news.append(news_item)
        
        return news
    
    async def _get_economic_events(self) -> List[Dict]:
        """Retorna eventos econômicos do dia."""
        # Eventos simulados - em produção, integrar com API de calendário
        now = datetime.now()
        
        events = [
            {
                'title': 'Decisão de Juros do COPOM',
                'summary': 'Banco Central divulga decisão sobre taxa Selic.',
                'content': 'O Comitê de Política Monetária do Banco Central decide hoje sobre a taxa básica de juros. Analistas esperam manutenção da Selic em 11,75% ao ano, mas o cenário de inflação permanece no radar.',
                'high_impact': True,
                'time': now,
                'symbols': ['USDBRL', 'IBOV'],
            },
            {
                'title': 'Dados de Inflação nos EUA',
                'summary': 'CPI americano impacta mercados globais.',
                'content': 'O índice de preços ao consumidor dos Estados Unidos será divulgado às 10h30. O dado é crucial para as expectativas sobre a política monetária do Federal Reserve.',
                'high_impact': True,
                'time': now,
                'symbols': ['EURUSD', 'XAUUSD', 'US500'],
            },
        ]
        
        return events
    
    def _parse_rss(self, content: str, source: str) -> List[NewsItem]:
        """Parseia conteúdo RSS."""
        news = []
        
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            
            # Encontra items
            items = root.findall('.//item')
            
            for item in items[:10]:  # Limita a 10 por fonte
                title = item.findtext('title', '')
                description = item.findtext('description', '')
                link = item.findtext('link', '')
                pub_date = item.findtext('pubDate', '')
                
                if not title:
                    continue
                
                # Limpa HTML da descrição
                description = re.sub(r'<[^>]+>', '', description)
                description = description[:500]  # Limita tamanho
                
                # Parseia data
                try:
                    from email.utils import parsedate_to_datetime
                    published_at = parsedate_to_datetime(pub_date)
                except:
                    published_at = datetime.now()
                
                # Categoriza
                category = self._categorize_news(title + " " + description)
                
                # Analisa sentimento
                sentiment, impact = self._analyze_sentiment(title + " " + description)
                
                # Extrai símbolos relacionados
                symbols = self._extract_symbols(title + " " + description)
                
                # Determina prioridade
                priority = NewsPriority.HIGH if impact > 0.7 else (
                    NewsPriority.MEDIUM if impact > 0.4 else NewsPriority.LOW
                )
                
                news_item = NewsItem(
                    id=hashlib.md5(f"{source}_{title}".encode()).hexdigest()[:12],
                    title=title,
                    summary=description[:200] + "..." if len(description) > 200 else description,
                    content=description,
                    source=source,
                    category=category,
                    priority=priority,
                    published_at=published_at,
                    url=link,
                    related_symbols=symbols,
                    sentiment=sentiment,
                    impact_score=impact,
                )
                news.append(news_item)
                
        except Exception as e:
            logger.warning(f"Erro ao parsear RSS: {e}")
        
        return news
    
    def _categorize_news(self, text: str) -> NewsCategory:
        """Categoriza notícia baseado no conteúdo."""
        text_lower = text.lower()
        
        scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[category] = score
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        return NewsCategory.ECONOMY
    
    def _analyze_sentiment(self, text: str) -> tuple:
        """Analisa sentimento do texto."""
        text_lower = text.lower()
        
        bullish_count = sum(1 for word in self.bullish_words if word in text_lower)
        bearish_count = sum(1 for word in self.bearish_words if word in text_lower)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 'neutral', 0.3
        
        if bullish_count > bearish_count:
            sentiment = 'bullish'
            impact = min(1.0, 0.5 + (bullish_count - bearish_count) * 0.1)
        elif bearish_count > bullish_count:
            sentiment = 'bearish'
            impact = min(1.0, 0.5 + (bearish_count - bullish_count) * 0.1)
        else:
            sentiment = 'neutral'
            impact = 0.5
        
        return sentiment, impact
    
    def _extract_symbols(self, text: str) -> List[str]:
        """Extrai símbolos de ativos mencionados."""
        symbols = []
        text_upper = text.upper()
        
        symbol_map = {
            'DÓLAR': 'USDBRL',
            'EURO': 'EURUSD',
            'LIBRA': 'GBPUSD',
            'OURO': 'XAUUSD',
            'PETRÓLEO': 'USOIL',
            'BITCOIN': 'BTCUSD',
            'IBOVESPA': 'IBOV',
            'USDBRL': 'USDBRL',
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
            'XAUUSD': 'XAUUSD',
        }
        
        for keyword, symbol in symbol_map.items():
            if keyword in text.upper():
                if symbol not in symbols:
                    symbols.append(symbol)
        
        return symbols
    
    async def _generate_audio(self, news: NewsItem):
        """Gera áudio para uma notícia."""
        # Texto para áudio (título + resumo)
        text = f"{news.title}. {news.summary}"
        
        # Gera áudio
        audio_path = await self.tts.text_to_speech(text)
        
        if audio_path:
            # URL relativa para o frontend
            news.audio_url = f"/api/news/audio/{audio_path.name}"
            news.audio_duration_seconds = self.tts.get_audio_duration(audio_path)
    
    def get_cached_news(self, news_id: str) -> Optional[NewsItem]:
        """Retorna notícia do cache."""
        return self.news_cache.get(news_id)
    
    def get_audio_path(self, filename: str) -> Optional[Path]:
        """Retorna path do arquivo de áudio."""
        audio_path = AUDIO_CACHE_DIR / filename
        if audio_path.exists():
            return audio_path
        return None
    
    async def get_news_summary(self) -> str:
        """Gera resumo das notícias em texto para áudio."""
        news = await self.fetch_news(limit=5)
        
        if not news:
            return "Não há notícias relevantes no momento."
        
        summary = "Resumo das principais notícias financeiras. "
        
        for i, item in enumerate(news, 1):
            summary += f"Notícia {i}: {item.title}. "
            if item.sentiment == 'bullish':
                summary += "O mercado reage positivamente. "
            elif item.sentiment == 'bearish':
                summary += "O mercado demonstra cautela. "
        
        summary += "Fim do resumo de notícias."
        
        return summary


# Instância global
news_service = NewsService()
