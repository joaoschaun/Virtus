"""
VIRTUS - Auto Post Generator
=============================

Gera posts automaticamente baseado nas notícias do Brain.
Integra com news_service para criar posts prontos.

Suporta:
- Geração de captions com templates (padrão)
- Geração de captions com TESS AI (opcional, se configurado)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

import unicodedata
import re

logger = logging.getLogger(__name__)

# Paths
BACKEND_PATH = Path(__file__).parent.parent  # services/ -> backend/
BRAIN_PATH = BACKEND_PATH.parent.parent  # backend/ -> dashboard/ -> brain/
sys.path.insert(0, str(BRAIN_PATH))

# Flag para TESS AI
TESS_ENABLED = False
TESS_CLIENT = None

# Tenta importar TESS AI (opcional)
try:
    from src.integrations.tess import TessClient
    from src.integrations.tess.caption_service import TessCaptionService
    
    # Verifica se tem config
    tess_config_path = BRAIN_PATH / "config" / "tess.yaml"
    if tess_config_path.exists():
        import yaml
        with open(tess_config_path, 'r', encoding='utf-8') as f:
            tess_config = yaml.safe_load(f)
            if tess_config and tess_config.get('api_key'):
                TESS_ENABLED = True
                logger.info("✅ TESS AI habilitada para geração de captions")
except ImportError:
    logger.info("ℹ️ TESS AI não disponível, usando templates padrão")

# Diretórios de dados
DATA_DIR = BRAIN_PATH / "data" / "social_media"
IMAGES_DIR = DATA_DIR / "images"
POSTS_FILE = DATA_DIR / "posts_history.json"

# Cria diretórios
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)


class AutoPostGenerator:
    """
    Gerador automático de posts.
    
    Pega notícias do news_service e gera posts prontos.
    """
    
    def __init__(self):
        self.posts_generated: List[Dict] = []
        self._load_history()
        
        # IDs de notícias já processadas (para não duplicar)
        self.processed_news_ids: set = set()
        self._load_processed_ids()
    
    def _load_history(self):
        """Carrega histórico de posts."""
        if POSTS_FILE.exists():
            with open(POSTS_FILE, 'r', encoding='utf-8') as f:
                self.posts_generated = json.load(f)
    
    def _save_history(self):
        """Salva histórico de posts."""
        with open(POSTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.posts_generated, f, indent=2, ensure_ascii=False)
    
    def _load_processed_ids(self):
        """Carrega IDs de notícias já processadas."""
        processed_file = DATA_DIR / "processed_news.json"
        if processed_file.exists():
            with open(processed_file, 'r', encoding='utf-8') as f:
                self.processed_news_ids = set(json.load(f))
    
    def _save_processed_ids(self):
        """Salva IDs processados."""
        processed_file = DATA_DIR / "processed_news.json"
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.processed_news_ids), f)
    
    async def generate_single_news_post(self, news_data: Dict) -> Optional[Dict]:
        """
        Gera post a partir de uma notícia selecionada manualmente.
        
        Args:
            news_data: Dict com title, summary, sentiment, category, tickers, source
            
        Returns:
            Post gerado ou None
        """
        try:
            # Cria objeto simples para compatibilidade com _generate_news_post
            class NewsObject:
                def __init__(self, data):
                    self.title = data.get('title', '')
                    self.summary = data.get('summary', '')
                    self.content = data.get('summary', '')
                    self.sentiment = data.get('sentiment', 'neutral')
                    self.source = data.get('source', 'Virtus')
                    self.tickers = data.get('tickers', [])
                    
                    # Categoria
                    from services.news_service import NewsCategory
                    cat_str = data.get('category', 'stocks_br')
                    try:
                        self.category = NewsCategory(cat_str)
                    except:
                        self.category = NewsCategory.ALL
            
            news_obj = NewsObject(news_data)
            
            print(f"🖼️ Gerando post da notícia selecionada: {news_obj.title[:50]}...")
            post = await self._generate_news_post(news_obj, use_ai=True)
            
            return post
            
        except Exception as e:
            import traceback
            print(f"❌ Erro ao gerar post de notícia selecionada: {e}")
            traceback.print_exc()
            return None
    
    async def fetch_and_generate(self, limit: int = 5) -> List[Dict]:
        """
        Busca notícias e gera posts automaticamente.
        
        Args:
            limit: Número máximo de notícias para processar
            
        Returns:
            Lista de posts gerados
        """
        from services.news_service import NewsService, NewsCategory
        
        news_service = NewsService()
        generated = []
        
        try:
            # Busca notícias recentes
            print(f"🔍 Buscando notícias...")
            news_list = await news_service.fetch_news(
                category=NewsCategory.ALL,
                limit=limit * 2  # Busca mais para filtrar
            )
            
            print(f"📰 {len(news_list)} notícias encontradas")
            
            for news in news_list[:limit]:
                # Pula se já processou
                news_id = f"{news.source}_{news.title[:50]}"
                if news_id in self.processed_news_ids:
                    print(f"⏭️ Já processada: {news.title[:40]}...")
                    continue
                
                print(f"🖼️ Gerando post: {news.title[:40]}...")
                # Gera post
                post = await self._generate_news_post(news)
                if post:
                    generated.append(post)
                    self.processed_news_ids.add(news_id)
            
            # Salva IDs processados
            self._save_processed_ids()
            
        except Exception as e:
            import traceback
            print(f"❌ Erro ao buscar notícias: {e}")
            traceback.print_exc()
        
        return generated
    
    async def _generate_news_post(self, news, use_ai: bool = True) -> Optional[Dict]:
        """
        Gera post a partir de uma notícia.
        
        Args:
            news: Objeto de notícia
            use_ai: Se True e TESS habilitada, usa IA para caption
        """
        try:
            from src.social import ContentGenerator, ImageGenerator, ImageConfig
            
            content_gen = ContentGenerator()
            image_gen = ImageGenerator(
                assets_dir=BRAIN_PATH / "dashboard" / "frontend" / "public"
            )
            
            # Determina sentimento
            sentiment = news.sentiment if hasattr(news, 'sentiment') else "neutral"
            if sentiment not in ["bullish", "bearish", "neutral"]:
                sentiment = "neutral"
            
            # Pega summary ou content
            summary_text = news.summary if news.summary else news.content[:200] if news.content else news.title
            content_text = news.content if news.content else summary_text
            
            # Extrai símbolos relacionados
            related_symbols = self._extract_symbols(news.title + " " + content_text)
            
            # ==================== GERAÇÃO DE CAPTION ====================
            caption_text = ""
            ai_generated = False
            credits_used = 0.0
            
            # Tenta usar TESS AI se habilitada
            if use_ai and TESS_ENABLED:
                try:
                    caption_text, credits_used = await self._generate_caption_with_tess(
                        news_title=news.title,
                        news_summary=summary_text,
                        sentiment=sentiment,
                        symbols=related_symbols
                    )
                    ai_generated = True
                    print(f"🤖 Caption gerada com TESS AI (créditos: {credits_used:.4f})")
                except Exception as e:
                    print(f"⚠️ Falha na TESS AI, usando template: {e}")
            
            # Fallback para templates se não usou IA
            if not caption_text:
                content = content_gen.generate_news_post(
                    title=news.title,
                    summary=summary_text,
                    sentiment=sentiment,
                    related_symbols=related_symbols,
                )
                caption_text = content.caption
            
            # ==================== GERAÇÃO DE IMAGEM ====================
            # Tenta usar TESS AI para imagem profissional
            filename = await self._generate_news_image_tess(
                news=news,
                sentiment=sentiment,
                symbols=related_symbols
            )
            
            # Fallback para PIL se TESS falhar
            if not filename:
                config = ImageConfig(
                    title=news.title[:80],  # Limita tamanho
                    body=summary_text[:200] if summary_text else news.title,
                    trend=sentiment,
                )
                
                image = image_gen.generate_news_highlight(config)
                
                # Salva imagem com nome ASCII-safe
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Remove acentos e caracteres especiais
                safe_title = unicodedata.normalize('NFKD', news.title[:30])
                safe_title = safe_title.encode('ASCII', 'ignore').decode('ASCII')
                safe_title = re.sub(r'[^a-zA-Z0-9\s]', '', safe_title)
                safe_title = safe_title.strip().replace(" ", "_")[:20]
                if not safe_title:
                    safe_title = "news"
                filename = f"news_{safe_title}_{timestamp}.png"
                image_path = IMAGES_DIR / filename
                image_gen.save(image, image_path)
            
            # Cria registro do post
            post = {
                "id": len(self.posts_generated) + 1,
                "type": "news_auto",
                "title": news.title,
                "caption": caption_text,
                "image_file": filename,
                "source": news.source if hasattr(news, 'source') else "Brain",
                "sentiment": sentiment,
                "category": news.category.value if hasattr(news, 'category') else "general",
                "created_at": datetime.now().isoformat(),
                "posted": False,
                "auto_generated": True,
                "ai_generated": ai_generated,
                "ai_credits": credits_used if ai_generated else 0,
            }
            
            self.posts_generated.append(post)
            self._save_history()
            
            print(f"✅ Post gerado: {news.title[:50]}...")
            return post
            
        except Exception as e:
            print(f"❌ Erro ao gerar post: {e}")
            return None
    
    def _extract_symbols(self, text: str) -> List[str]:
        """Extrai símbolos de trading do texto."""
        symbols = []
        text_upper = text.upper()
        
        known_symbols = [
            "XAUUSD", "GOLD", "OURO",
            "EURUSD", "EUR/USD", "EURO",
            "GBPUSD", "GBP/USD", "LIBRA",
            "USDJPY", "USD/JPY",
            "BTCUSD", "BITCOIN", "BTC",
            "ETHUSD", "ETHEREUM", "ETH",
            "DXY", "DÓLAR", "DOLLAR",
            "S&P", "SPX", "SP500",
            "NASDAQ", "NDX",
        ]
        
        for symbol in known_symbols:
            if symbol in text_upper:
                # Normaliza para formato padrão
                if symbol in ["GOLD", "OURO"]:
                    symbols.append("XAUUSD")
                elif symbol in ["EURO", "EUR/USD"]:
                    symbols.append("EURUSD")
                elif symbol in ["LIBRA", "GBP/USD"]:
                    symbols.append("GBPUSD")
                elif symbol in ["BITCOIN", "BTC"]:
                    symbols.append("BTCUSD")
                elif symbol in ["ETHEREUM", "ETH"]:
                    symbols.append("ETHUSD")
                else:
                    symbols.append(symbol)
        
        return list(set(symbols))[:3]  # Máximo 3 símbolos
    
    async def _generate_caption_with_tess(
        self,
        news_title: str,
        news_summary: str,
        sentiment: str,
        symbols: List[str]
    ) -> tuple:
        """
        Gera caption usando TESS AI.
        
        Args:
            news_title: Título da notícia
            news_summary: Resumo da notícia
            sentiment: bullish/bearish/neutral
            symbols: Símbolos relacionados
            
        Returns:
            Tuple (caption_text, credits_used)
        """
        if not TESS_ENABLED:
            return ("", 0.0)
        
        try:
            import yaml
            tess_config_path = BRAIN_PATH / "config" / "tess.yaml"
            
            with open(tess_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            async with TessCaptionService(api_key=config['api_key']) as service:
                result = await service.news_to_instagram_caption(
                    news_title=news_title,
                    news_summary=news_summary,
                    news_sentiment=sentiment,
                    related_symbols=symbols
                )
                
                return (result.text, result.credits_spent)
                
        except Exception as e:
            logger.error(f"Erro ao gerar caption com TESS: {e}")
            raise
    
    async def _generate_news_image_tess(
        self,
        news,
        sentiment: str,
        symbols: List[str]
    ) -> Optional[str]:
        """
        Gera imagem de notícia usando TESS AI com overlay Virtus.
        
        Args:
            news: Objeto de notícia
            sentiment: bullish/bearish/neutral
            symbols: Símbolos relacionados
            
        Returns:
            Nome do arquivo salvo ou None se falhar
        """
        if not TESS_ENABLED:
            return None
        
        try:
            from src.integrations.tess.image_generator import (
                TessImageGenerator, NewsData
            )
            
            # Mapear sentimento
            sentiment_map = {
                "bullish": "positive",
                "bearish": "negative",
                "neutral": "neutral"
            }
            
            # Determinar impacto baseado no conteúdo
            impact = "medium"
            high_impact_words = ["breaking", "urgente", "histórico", "recorde", "crise", "colapso", "dispara"]
            title_lower = news.title.lower()
            for word in high_impact_words:
                if word in title_lower:
                    impact = "high"
                    break
            
            # Preparar dados da notícia
            news_data = NewsData(
                title=news.title,
                summary=news.summary if news.summary else news.title,
                sentiment=sentiment_map.get(sentiment, "neutral"),
                impact=impact,
                symbols=symbols,
                source=news.source if hasattr(news, 'source') else ""
            )
            
            # Gerar nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = unicodedata.normalize('NFKD', news.title[:20])
            safe_title = safe_title.encode('ASCII', 'ignore').decode('ASCII')
            safe_title = re.sub(r'[^a-zA-Z0-9\s]', '', safe_title)
            safe_title = safe_title.strip().replace(" ", "_")[:15]
            if not safe_title:
                safe_title = "news"
            filename = f"news_tess_{safe_title}_{timestamp}.png"
            save_path = IMAGES_DIR / filename
            
            # Gerar imagem com overlay
            async with TessImageGenerator() as generator:
                await generator.generate_news_with_overlay(
                    news=news_data,
                    save_path=save_path
                )
            
            print(f"🎨 Imagem TESS gerada: {filename}")
            return filename
            
        except Exception as e:
            logger.warning(f"TESS news image generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def generate_market_summary(self) -> Optional[Dict]:
        """Gera resumo diário do mercado."""
        try:
            from src.social import ContentGenerator, ImageGenerator, ImageConfig
            
            content_gen = ContentGenerator()
            image_gen = ImageGenerator(
                assets_dir=BRAIN_PATH / "dashboard" / "frontend" / "public"
            )
            
            # TODO: Pegar dados reais do Brain
            # Por enquanto, gera template
            highlights = [
                {"symbol": "XAUUSD", "change": 0.75},
                {"symbol": "EURUSD", "change": -0.23},
                {"symbol": "GBPUSD", "change": 0.15},
            ]
            
            content = content_gen.generate_daily_summary(
                highlights=highlights,
                market_sentiment="neutral",
            )
            
            config = ImageConfig(
                title=content.title,
                body=content.body,
            )
            
            image = image_gen.generate_daily_summary(config)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"daily_summary_{timestamp}.png"
            image_path = IMAGES_DIR / filename
            image_gen.save(image, image_path)
            
            post = {
                "id": len(self.posts_generated) + 1,
                "type": "daily_summary",
                "title": content.title,
                "caption": content.caption,
                "image_file": filename,
                "created_at": datetime.now().isoformat(),
                "posted": False,
                "auto_generated": True,
            }
            
            self.posts_generated.append(post)
            self._save_history()
            
            return post
            
        except Exception as e:
            print(f"Erro ao gerar resumo: {e}")
            return None
    
    async def generate_trading_tip(self) -> Optional[Dict]:
        """Gera dica de trading."""
        try:
            from src.social import ContentGenerator, ImageGenerator, ImageConfig
            
            content_gen = ContentGenerator()
            image_gen = ImageGenerator(
                assets_dir=BRAIN_PATH / "dashboard" / "frontend" / "public"
            )
            
            content = content_gen.generate_trading_tip()
            
            config = ImageConfig(
                title=content.title,
                body=content.body,
            )
            
            image = image_gen.generate_quote(config)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tip_{timestamp}.png"
            image_path = IMAGES_DIR / filename
            image_gen.save(image, image_path)
            
            post = {
                "id": len(self.posts_generated) + 1,
                "type": "trading_tip",
                "title": content.title,
                "caption": content.caption,
                "image_file": filename,
                "created_at": datetime.now().isoformat(),
                "posted": False,
                "auto_generated": True,
            }
            
            self.posts_generated.append(post)
            self._save_history()
            
            return post
            
        except Exception as e:
            print(f"Erro ao gerar dica: {e}")
            return None
    
    def get_pending_posts(self) -> List[Dict]:
        """Retorna posts não postados ainda."""
        self._load_history()
        return [p for p in self.posts_generated if not p.get("posted", False)]
    
    def mark_as_posted(self, post_id: int) -> bool:
        """Marca post como já postado."""
        for post in self.posts_generated:
            if post["id"] == post_id:
                post["posted"] = True
                post["posted_at"] = datetime.now().isoformat()
                self._save_history()
                return True
        return False


# Instância global
auto_generator = AutoPostGenerator()


async def auto_generate_from_news(limit: int = 3) -> List[Dict]:
    """Função helper para gerar posts das notícias."""
    return await auto_generator.fetch_and_generate(limit)


async def generate_all_content() -> Dict[str, Any]:
    """Gera todos os tipos de conteúdo."""
    results = {
        "news_posts": [],
        "daily_summary": None,
        "trading_tip": None,
    }
    
    # Gera posts de notícias
    results["news_posts"] = await auto_generator.fetch_and_generate(3)
    
    # Gera resumo diário (uma vez por dia)
    # results["daily_summary"] = await auto_generator.generate_market_summary()
    
    # Gera dica de trading
    results["trading_tip"] = await auto_generator.generate_trading_tip()
    
    return results
