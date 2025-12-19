"""
VIRTUS - Social Briefing Generator
===================================

Gera posts de briefing diário para redes sociais integrando:
- EODHD (notícias e calendário econômico)
- ForexNews API (notícias forex em tempo real)
- Investing.com (via news_service)
- TESS AI (análise de sentimento e geração de texto)

O briefing inclui:
- Principais notícias do dia
- Impacto no mercado
- Sentimento geral
- Eventos econômicos importantes
- Sinais por símbolo (XAUUSD, EURUSD, GBPUSD, USDJPY)
"""

import asyncio
import json
import logging
import hashlib
import unicodedata
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

try:
    import pytz
    BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')
except ImportError:
    BRAZIL_TZ = None

def get_brazil_now() -> datetime:
    """Retorna datetime atual no fuso horário do Brasil."""
    if BRAZIL_TZ:
        return datetime.now(BRAZIL_TZ)
    # Fallback: UTC-3 manual
    return datetime.utcnow() - timedelta(hours=3)

logger = logging.getLogger(__name__)

# Paths
BACKEND_PATH = Path(__file__).parent.parent
BRAIN_PATH = BACKEND_PATH.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

# Diretórios de dados
DATA_DIR = BRAIN_PATH / "data" / "social_media"
IMAGES_DIR = DATA_DIR / "images"
POSTS_FILE = DATA_DIR / "posts_history.json"

# Cria diretórios
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# Símbolos forex monitorados
FOREX_SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY']

# Nomes amigáveis
SYMBOL_NAMES = {
    'XAUUSD': '🥇 Ouro',
    'EURUSD': '🇪🇺 Euro/Dólar',
    'GBPUSD': '🇬🇧 Libra/Dólar',
    'USDJPY': '🇯🇵 Dólar/Iene',
}


class SocialBriefingGenerator:
    """
    Gerador de briefings diários para redes sociais.
    
    Combina dados de múltiplas fontes para criar posts
    informativos e engajantes sobre o mercado forex.
    """
    
    def __init__(self):
        self.posts_generated: List[Dict] = []
        self._load_history()
        
        # Serviços (inicializados sob demanda)
        self._forex_service = None
        self._news_service = None
        self._tess_analyzer = None
        self._tess_available = False
    
    def _load_history(self):
        """Carrega histórico de posts."""
        if POSTS_FILE.exists():
            with open(POSTS_FILE, 'r', encoding='utf-8') as f:
                self.posts_generated = json.load(f)
    
    def _save_history(self):
        """Salva histórico de posts."""
        with open(POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.posts_generated, f, indent=2, ensure_ascii=False)
    
    async def initialize(self):
        """Inicializa serviços necessários."""
        # Forex Briefing Service (EODHD + ForexNews)
        try:
            from services.forex_briefing_service import forex_briefing_service
            self._forex_service = forex_briefing_service
            await self._forex_service.initialize()
            logger.info("✅ ForexBriefingService inicializado")
        except Exception as e:
            logger.warning(f"ForexBriefingService não disponível: {e}")
        
        # News Service (Investing.com e outras)
        try:
            from services.news_service import NewsService
            self._news_service = NewsService()
            logger.info("✅ NewsService inicializado")
        except Exception as e:
            logger.warning(f"NewsService não disponível: {e}")
        
        # TESS AI
        try:
            from src.integrations.tess.market_analyzer import TessMarketAnalyzer
            self._tess_analyzer = TessMarketAnalyzer()
            await self._tess_analyzer.initialize()
            self._tess_available = True
            logger.info("✅ TESS AI disponível")
        except Exception as e:
            logger.warning(f"TESS não disponível: {e}")
    
    async def generate_daily_briefing_post(self) -> Dict:
        """
        Gera post de briefing diário completo.
        
        Returns:
            Dict com informações do post gerado
        """
        await self.initialize()
        
        # Usa timezone do Brasil
        today = get_brazil_now()
        
        # Coleta dados de todas as fontes
        all_data = await self._collect_all_data()
        
        # Gera texto do briefing
        caption = await self._generate_briefing_caption(all_data, today)
        
        # Gera imagem do briefing
        image_filename = await self._generate_briefing_image(all_data, today)
        
        # Cria registro do post
        post = {
            "id": len(self.posts_generated) + 1,
            "type": "daily_briefing",
            "title": f"📊 Briefing Forex - {today.strftime('%d/%m/%Y')}",
            "caption": caption,
            "image_file": image_filename,
            "created_at": today.isoformat(),
            "posted": False,
            "auto_generated": True,
            "data_sources": all_data.get('sources', []),
            "market_mood": all_data.get('market_mood', 'neutral'),
        }
        
        self.posts_generated.append(post)
        self._save_history()
        
        logger.info(f"✅ Post de briefing diário gerado: {post['title']}")
        return post
    
    async def _collect_all_data(self) -> Dict[str, Any]:
        """Coleta dados de todas as fontes disponíveis."""
        data = {
            'sources': [],
            'news': [],
            'events': [],
            'signals': {},
            'market_mood': 'neutral',
            'sentiment_score': 0.0,
        }
        
        # 1. Dados do ForexBriefingService (EODHD + ForexNews)
        if self._forex_service:
            try:
                briefing = await self._forex_service.get_daily_briefing(generate_audio=False)
                
                # Notícias
                for news in briefing.top_news:
                    data['news'].append({
                        'title': news.title,
                        'summary': news.summary,
                        'source': news.provider.upper(),
                        'sentiment': news.sentiment.value,
                        'impact': news.impact.value,
                        'symbols': news.symbols,
                    })
                
                # Eventos
                for event in briefing.key_events:
                    data['events'].append({
                        'name': event.name,
                        'country': event.country,
                        'date': event.date.isoformat() if hasattr(event.date, 'isoformat') else str(event.date),
                        'impact': event.impact.value,
                    })
                
                # Sinais
                data['signals'] = {
                    symbol: {
                        'direction': signal.direction.value,
                        'strength': signal.strength,
                        'summary': signal.summary,
                    }
                    for symbol, signal in briefing.signals.items()
                }
                
                # Humor do mercado
                data['market_mood'] = briefing.market_mood.value
                
                data['sources'].extend(['EODHD', 'ForexNews'])
                logger.info(f"✅ Dados do ForexBriefingService: {len(data['news'])} notícias, {len(data['events'])} eventos")
                
            except Exception as e:
                logger.error(f"Erro ao coletar dados ForexBriefing: {e}")
        
        # 2. Dados do NewsService (Investing.com e outras)
        if self._news_service:
            try:
                from services.news_service import NewsCategory
                news_list = await self._news_service.fetch_news(
                    category=NewsCategory.ALL,
                    limit=10
                )
                
                for news in news_list:
                    # Evita duplicatas (por título similar)
                    title_exists = any(
                        n['title'][:50].lower() == news.title[:50].lower() 
                        for n in data['news']
                    )
                    
                    if not title_exists:
                        data['news'].append({
                            'title': news.title,
                            'summary': news.summary if hasattr(news, 'summary') else news.content[:200],
                            'source': news.source,
                            'sentiment': news.sentiment if hasattr(news, 'sentiment') else 'neutral',
                            'impact': 'medium',
                            'symbols': self._extract_symbols(news.title),
                        })
                
                if 'Investing' not in data['sources']:
                    data['sources'].append('Investing')
                
                logger.info(f"✅ Dados do NewsService: {len(news_list)} notícias")
                
            except Exception as e:
                logger.error(f"Erro ao coletar dados NewsService: {e}")
        
        # 3. Análise com TESS AI
        if self._tess_available and data['news']:
            try:
                news_items = [
                    {'title': n['title'], 'content': n.get('summary', ''), 'source': n['source']}
                    for n in data['news'][:10]
                ]
                
                result = await self._tess_analyzer.analyze_news_sentiment(news_items)
                
                if result:
                    data['sentiment_score'] = result.confidence
                    if result.sentiment == 'bullish':
                        data['market_mood'] = 'bullish'
                    elif result.sentiment == 'bearish':
                        data['market_mood'] = 'bearish'
                    
                data['sources'].append('TESS AI')
                logger.info(f"✅ Análise TESS: sentimento={result.sentiment if result else 'N/A'}")
                
            except Exception as e:
                logger.error(f"Erro na análise TESS: {e}")
        
        # Calcula score de sentimento das notícias
        if data['news']:
            bullish = sum(1 for n in data['news'] if n.get('sentiment') == 'bullish')
            bearish = sum(1 for n in data['news'] if n.get('sentiment') == 'bearish')
            total = len(data['news'])
            
            if bullish > bearish * 1.5:
                data['market_mood'] = 'bullish'
            elif bearish > bullish * 1.5:
                data['market_mood'] = 'bearish'
        
        return data
    
    def _extract_symbols(self, text: str) -> List[str]:
        """Extrai símbolos forex do texto."""
        symbols = []
        text_upper = text.upper()
        
        keywords = {
            'XAUUSD': ['GOLD', 'OURO', 'XAU'],
            'EURUSD': ['EURO', 'EUR'],
            'GBPUSD': ['LIBRA', 'GBP', 'POUND'],
            'USDJPY': ['IENE', 'JPY', 'YEN'],
        }
        
        for symbol, kws in keywords.items():
            for kw in kws:
                if kw in text_upper:
                    if symbol not in symbols:
                        symbols.append(symbol)
                    break
        
        return symbols
    
    async def _generate_briefing_caption(self, data: Dict, date: datetime) -> str:
        """Gera caption do briefing para Instagram."""
        weekday_names = {
            0: 'segunda-feira', 1: 'terça-feira', 2: 'quarta-feira',
            3: 'quinta-feira', 4: 'sexta-feira', 5: 'sábado', 6: 'domingo'
        }
        
        mood_emoji = {
            'bullish': '📈',
            'bearish': '📉',
            'neutral': '➡️',
            'mixed': '🔄',
        }
        
        mood_text = {
            'bullish': 'otimista, com viés de alta',
            'bearish': 'cauteloso, com viés de baixa',
            'neutral': 'neutro, aguardando direção',
            'mixed': 'misto, com volatilidade esperada',
        }
        
        caption = f"📊 BRIEFING FOREX - {date.strftime('%d/%m/%Y')}\n"
        caption += f"🗓️ {weekday_names.get(date.weekday(), '')}\n\n"
        
        # Humor do mercado
        mood = data.get('market_mood', 'neutral')
        caption += f"{mood_emoji.get(mood, '📊')} SENTIMENTO: {mood_text.get(mood, 'indefinido').upper()}\n\n"
        
        # Sinais por símbolo
        if data.get('signals'):
            caption += "🎯 SINAIS DO DIA:\n"
            for symbol in FOREX_SYMBOLS:
                if symbol in data['signals']:
                    signal = data['signals'][symbol]
                    direction = signal.get('direction', 'neutral')
                    emoji = '🟢' if direction == 'bullish' else '🔴' if direction == 'bearish' else '⚪'
                    strength = int(signal.get('strength', 0) * 100)
                    caption += f"{emoji} {SYMBOL_NAMES.get(symbol, symbol)}: {direction.upper()} ({strength}%)\n"
            caption += "\n"
        
        # Eventos importantes
        high_impact_events = [e for e in data.get('events', []) if e.get('impact') == 'high']
        if high_impact_events:
            caption += "⚠️ EVENTOS IMPORTANTES:\n"
            for event in high_impact_events[:3]:
                caption += f"• {event['name']} ({event['country']})\n"
            caption += "\n"
        
        # Top notícias
        top_news = data.get('news', [])[:3]
        if top_news:
            caption += "📰 PRINCIPAIS NOTÍCIAS:\n"
            for i, news in enumerate(top_news, 1):
                sentiment_emoji = '🟢' if news.get('sentiment') == 'bullish' else '🔴' if news.get('sentiment') == 'bearish' else '⚪'
                title = news['title'][:60] + '...' if len(news['title']) > 60 else news['title']
                caption += f"{sentiment_emoji} {title}\n"
            caption += "\n"
        
        # Fontes
        sources = data.get('sources', [])
        if sources:
            caption += f"📡 Fontes: {', '.join(sources)}\n\n"
        
        # CTA e hashtags
        caption += "💡 Opere com sabedoria. Gerencie seu risco!\n\n"
        caption += "#Forex #Trading #XAUUSD #EURUSD #GBPUSD #USDJPY "
        caption += "#MercadoFinanceiro #DayTrading #Investimentos #Trader "
        caption += "#AnáliseTécnica #BriefingDiário #VirtusInvestimentos"
        
        return caption
    
    async def _generate_briefing_image(self, data: Dict, date: datetime) -> str:
        """
        Gera imagem do briefing usando TESS AI com overlay Virtus.
        
        Tenta primeiro gerar com TESS AI + overlay profissional.
        Se falhar, usa o gerador PIL como fallback.
        """
        
        # 1. Tentar gerar com TESS AI + Overlay Virtus
        tess_filename = await self._generate_tess_image_with_overlay(data, date)
        
        if tess_filename:
            return tess_filename
        
        # 2. Fallback: usar gerador PIL local
        return await self._generate_pil_image(data, date)
    
    async def _generate_tess_image_with_overlay(self, data: Dict, date: datetime) -> Optional[str]:
        """
        Gera imagem usando TESS AI com overlay do template Virtus.
        
        Returns:
            Nome do arquivo salvo ou None se falhar
        """
        try:
            from src.integrations.tess.image_generator import (
                TessImageGenerator, BriefingData
            )
            
            # Preparar dados do briefing
            briefing_data = BriefingData(
                date=date,
                sentiment=data.get('market_mood', 'neutral'),
                sentiment_score=data.get('sentiment_score', 0.5),
                main_symbols=list(data.get('signals', {}).keys())[:4] or FOREX_SYMBOLS[:4],
                top_news=[n.get('title', '') for n in data.get('news', [])[:2]],
                key_events=[e.get('name', '') for e in data.get('events', [])[:2]],
                signals=data.get('signals', {}),
                highlight=data.get('highlight', None)
            )
            
            # Gerar imagem com overlay
            timestamp = date.strftime("%Y%m%d_%H%M%S")
            filename = f"briefing_tess_{timestamp}.png"
            save_path = IMAGES_DIR / filename
            
            async with TessImageGenerator() as generator:
                await generator.generate_briefing_with_overlay(
                    data=briefing_data,
                    save_path=save_path
                )
            
            logger.info(f"✅ Imagem TESS + Overlay salva: {filename}")
            return filename
                
        except Exception as e:
            logger.warning(f"TESS image generation with overlay failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _generate_pil_image(self, data: Dict, date: datetime) -> str:
        """Gera imagem usando PIL (fallback)."""
        try:
            from src.social import ImageGenerator, ImageConfig, ImageTemplate
            
            image_gen = ImageGenerator(
                assets_dir=BRAIN_PATH / "dashboard" / "frontend" / "public"
            )
            
            # Prepara dados dos sinais para os cards
            signals_display = {}
            for symbol in FOREX_SYMBOLS:
                if symbol in data.get('signals', {}):
                    signal = data['signals'][symbol]
                    signals_display[symbol] = {
                        'direction': signal.get('direction', 'neutral'),
                        'strength': signal.get('strength', 0.5),
                        'summary': signal.get('summary', 'Aguardando dados')[:35]
                    }
                else:
                    signals_display[symbol] = {
                        'direction': data.get('market_mood', 'neutral'),
                        'strength': 0.5,
                        'summary': 'Análise pendente'
                    }
            
            # Config da imagem institucional
            config = ImageConfig(
                width=1080,
                height=1080,
                template=ImageTemplate.DAILY_SUMMARY,
                title=f"BRIEFING FOREX - {date.strftime('%d/%m/%Y')}",
                body=f"Sentimento: {data.get('market_mood', 'neutral').upper()}",
                trend=data.get('market_mood', 'neutral'),
                sentiment_score=data.get('sentiment_score', 0.5),
                hashtags=["Forex", "Trading", "XAUUSD", "EURUSD", "VirtusInvestimentos"]
            )
            
            # Gera imagem de resumo diário (usa o novo template institucional)
            image = image_gen.generate_daily_summary(config)
            
            # Salva imagem no diretório correto
            timestamp = date.strftime("%Y%m%d_%H%M%S")
            filename = f"briefing_{timestamp}.png"
            image_path = IMAGES_DIR / filename
            image.save(str(image_path), "PNG", quality=95)
            
            logger.info(f"✅ Imagem institucional gerada: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao gerar imagem: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    async def schedule_morning_briefing(self, hour: int = 7, minute: int = 0):
        """
        Agenda geração do briefing matinal.
        
        Args:
            hour: Hora para gerar (default: 7h Brasil)
            minute: Minuto (default: 0)
        """
        while True:
            # Usa timezone do Brasil
            now = get_brazil_now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if now >= target:
                target += timedelta(days=1)
            
            wait_seconds = (target - now).total_seconds()
            logger.info(f"⏰ Próximo briefing em {wait_seconds/3600:.1f} horas (horário de Brasília)")
            
            await asyncio.sleep(wait_seconds)
            
            try:
                await self.generate_daily_briefing_post()
                logger.info("✅ Briefing matinal gerado automaticamente!")
            except Exception as e:
                logger.error(f"❌ Erro ao gerar briefing matinal: {e}")


# Instância global
social_briefing_generator = SocialBriefingGenerator()
