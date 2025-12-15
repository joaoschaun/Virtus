"""
VIRTUS Social Media - Manager
==============================

Orquestrador principal do sistema de mídia social.
Integra geração de conteúdo, imagens, publicação e agendamento.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio
import logging
import sys

# Paths
BRAIN_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))

from .content_generator import ContentGenerator, PostContent, PostType
from .image_generator import ImageGenerator, ImageTemplate, ImageConfig
from .instagram_service import (
    InstagramService, 
    create_instagram_service,
    PostResult,
)
from .scheduler import SocialScheduler, ScheduledPost

logger = logging.getLogger(__name__)


@dataclass
class SocialMediaConfig:
    """Configuração do sistema de mídia social."""
    
    # Instagram credentials
    instagram_access_token: Optional[str] = None
    instagram_account_id: Optional[str] = None
    instagram_page_id: Optional[str] = None
    
    # Paths
    output_dir: Path = None
    assets_dir: Path = None
    
    # Configurações
    use_mock: bool = True  # Modo de teste
    auto_schedule: bool = True
    min_post_interval: int = 30  # minutos
    
    # Upload endpoint (para hospedar imagens)
    image_upload_endpoint: Optional[str] = None
    
    def __post_init__(self):
        if self.output_dir is None:
            self.output_dir = BRAIN_PATH / "data" / "social_media"
        if self.assets_dir is None:
            self.assets_dir = BRAIN_PATH / "dashboard" / "frontend" / "public"


class SocialMediaManager:
    """
    Gerenciador principal de mídia social.
    
    Responsabilidades:
    - Gerar conteúdo a partir de dados do Brain
    - Criar imagens profissionais
    - Publicar no Instagram
    - Agendar posts estrategicamente
    """
    
    def __init__(self, config: Optional[SocialMediaConfig] = None):
        self.config = config or SocialMediaConfig()
        
        # Cria diretórios
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        (self.config.output_dir / "images").mkdir(exist_ok=True)
        (self.config.output_dir / "posts").mkdir(exist_ok=True)
        
        # Componentes
        self.content_generator = ContentGenerator()
        self.image_generator = ImageGenerator(assets_dir=self.config.assets_dir)
        self.scheduler = SocialScheduler()
        
        # Serviço do Instagram
        self.instagram = create_instagram_service(
            access_token=self.config.instagram_access_token,
            instagram_account_id=self.config.instagram_account_id,
            page_id=self.config.instagram_page_id,
            use_mock=self.config.use_mock,
        )
        
        # Configura callback do scheduler
        self.scheduler.set_publish_callback(self._publish_post)
        
        # Estado
        self._running = False
    
    async def _publish_post(self, scheduled: ScheduledPost) -> PostResult:
        """
        Callback para publicar um post.
        
        Args:
            scheduled: Post agendado
            
        Returns:
            Resultado da publicação
        """
        content = scheduled.content
        
        try:
            # Gera imagem
            image_data = content.image_data
            template = image_data.get("template", "quote")
            
            config = ImageConfig(
                title=content.title,
                body=content.body,
                symbol=image_data.get("symbol"),
                trend=image_data.get("trend"),
                price=image_data.get("price"),
                support=image_data.get("support"),
                resistance=image_data.get("resistance"),
                hashtags=content.hashtags,
            )
            
            # Gera imagem baseada no template
            if template == "market_alert":
                image = self.image_generator.generate_market_alert(config)
            elif template == "daily_summary":
                image = self.image_generator.generate_daily_summary(config)
            elif template == "news_highlight":
                image = self.image_generator.generate_news_highlight(config)
            else:
                image = self.image_generator.generate_quote(config)
            
            # Salva imagem localmente
            image_path = self.config.output_dir / "images" / f"{scheduled.id}.png"
            self.image_generator.save(image, image_path)
            
            # Publica
            image_bytes = self.image_generator.to_bytes(image)
            result = await self.instagram.upload_image_bytes(
                image_bytes=image_bytes,
                caption=content.caption,
                upload_endpoint=self.config.image_upload_endpoint,
            )
            
            # Log
            if result.success:
                logger.info(f"Post publicado: {scheduled.id}")
            else:
                logger.error(f"Falha na publicação: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao publicar: {e}")
            return PostResult(success=False, error=str(e))
    
    # ==========================================
    # Métodos de Criação de Posts
    # ==========================================
    
    def create_market_alert(
        self,
        symbol: str,
        trend: str,
        price: float,
        support: float = None,
        resistance: float = None,
        analysis_text: str = None,
        schedule: str = "optimal",  # immediate, optimal, queue
    ) -> ScheduledPost:
        """
        Cria post de alerta de mercado.
        
        Args:
            symbol: Símbolo do ativo
            trend: "bullish", "bearish", "neutral"
            price: Preço atual
            support: Nível de suporte
            resistance: Nível de resistência
            analysis_text: Texto adicional
            schedule: Tipo de agendamento
            
        Returns:
            Post agendado
        """
        content = self.content_generator.generate_market_alert(
            symbol=symbol,
            trend=trend,
            price=price,
            support=support,
            resistance=resistance,
            analysis_text=analysis_text,
        )
        
        return self._schedule_content(content, schedule)
    
    def create_news_post(
        self,
        title: str,
        summary: str,
        sentiment: str = "neutral",
        related_symbols: List[str] = None,
        source: str = None,
        schedule: str = "optimal",
    ) -> ScheduledPost:
        """
        Cria post de notícia.
        
        Args:
            title: Título da notícia
            summary: Resumo
            sentiment: Sentimento
            related_symbols: Ativos relacionados
            source: Fonte
            schedule: Tipo de agendamento
            
        Returns:
            Post agendado
        """
        content = self.content_generator.generate_news_post(
            title=title,
            summary=summary,
            sentiment=sentiment,
            related_symbols=related_symbols,
            source=source,
        )
        
        return self._schedule_content(content, schedule)
    
    def create_daily_summary(
        self,
        highlights: List[Dict[str, Any]],
        market_sentiment: str = "neutral",
        schedule: str = "optimal",
    ) -> ScheduledPost:
        """
        Cria post de resumo diário.
        
        Args:
            highlights: Lista de destaques
            market_sentiment: Sentimento geral
            schedule: Tipo de agendamento
            
        Returns:
            Post agendado
        """
        content = self.content_generator.generate_daily_summary(
            highlights=highlights,
            market_sentiment=market_sentiment,
        )
        
        return self._schedule_content(content, schedule)
    
    def create_trading_tip(
        self,
        schedule: str = "optimal",
    ) -> ScheduledPost:
        """Cria post com dica de trading."""
        content = self.content_generator.generate_trading_tip()
        return self._schedule_content(content, schedule)
    
    def create_educational(
        self,
        schedule: str = "optimal",
    ) -> ScheduledPost:
        """Cria post educacional."""
        content = self.content_generator.generate_educational()
        return self._schedule_content(content, schedule)
    
    def _schedule_content(
        self,
        content: PostContent,
        schedule: str,
    ) -> ScheduledPost:
        """Agenda conteúdo baseado no tipo."""
        if schedule == "immediate":
            return self.scheduler.post_immediately(content)
        elif schedule == "optimal":
            return self.scheduler.schedule_optimal(content)
        else:
            return self.scheduler.add_to_queue(content)
    
    # ==========================================
    # Integração com Brain
    # ==========================================
    
    async def process_brain_analysis(
        self,
        analysis: Dict[str, Any],
    ) -> Optional[ScheduledPost]:
        """
        Processa análise do Brain e cria post se relevante.
        
        Args:
            analysis: Dados de análise do Brain
            
        Returns:
            Post agendado ou None
        """
        content = self.content_generator.generate_from_brain_analysis(analysis)
        
        if content:
            return self.scheduler.schedule_optimal(content)
        
        return None
    
    async def process_news(
        self,
        news: Dict[str, Any],
    ) -> Optional[ScheduledPost]:
        """
        Processa notícia e cria post se relevante.
        
        Args:
            news: Dados da notícia
            
        Returns:
            Post agendado ou None
        """
        # Filtra por importância
        impact = news.get("impact", "low")
        if impact not in ["high", "critical"]:
            return None
        
        return self.create_news_post(
            title=news.get("title", ""),
            summary=news.get("summary", news.get("description", "")),
            sentiment=news.get("sentiment", "neutral"),
            related_symbols=news.get("symbols", []),
            source=news.get("source"),
            schedule="immediate" if impact == "critical" else "optimal",
        )
    
    # ==========================================
    # Gestão
    # ==========================================
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do sistema."""
        return {
            "running": self._running,
            "config": {
                "use_mock": self.config.use_mock,
                "auto_schedule": self.config.auto_schedule,
            },
            "scheduler": self.scheduler.get_queue_status(),
            "instagram": self.instagram.get_stats(),
        }
    
    def get_pending_posts(self) -> List[Dict[str, Any]]:
        """Retorna posts pendentes."""
        return self.scheduler.get_pending_posts()
    
    def get_published_posts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retorna últimos posts publicados."""
        return self.scheduler.get_published_posts(limit)
    
    def cancel_post(self, post_id: str) -> bool:
        """Cancela post agendado."""
        return self.scheduler.cancel_post(post_id)
    
    async def start(self, interval: int = 60):
        """
        Inicia o manager.
        
        Args:
            interval: Intervalo de verificação em segundos
        """
        self._running = True
        logger.info("Social Media Manager iniciado")
        
        # Inicia scheduler
        await self.scheduler.start(interval)
    
    async def stop(self):
        """Para o manager."""
        self._running = False
        self.scheduler.stop()
        await self.instagram.close()
        logger.info("Social Media Manager parado")
    
    async def close(self):
        """Fecha conexões."""
        await self.stop()


# ==========================================
# API Routes para Dashboard
# ==========================================

def create_social_routes():
    """Cria rotas da API para o dashboard."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
    from typing import Optional, List
    
    router = APIRouter(prefix="/api/social", tags=["Social Media"])
    
    # Manager global
    manager: Optional[SocialMediaManager] = None
    
    class MarketAlertRequest(BaseModel):
        symbol: str
        trend: str
        price: float
        support: Optional[float] = None
        resistance: Optional[float] = None
        analysis_text: Optional[str] = None
        schedule: str = "optimal"
    
    class NewsPostRequest(BaseModel):
        title: str
        summary: str
        sentiment: str = "neutral"
        related_symbols: Optional[List[str]] = None
        schedule: str = "optimal"
    
    class DailySummaryRequest(BaseModel):
        highlights: List[dict]
        market_sentiment: str = "neutral"
        schedule: str = "optimal"
    
    @router.on_event("startup")
    async def startup():
        nonlocal manager
        manager = SocialMediaManager()
        await manager.start()
    
    @router.on_event("shutdown")
    async def shutdown():
        if manager:
            await manager.close()
    
    @router.get("/status")
    async def get_status():
        """Retorna status do sistema."""
        if not manager:
            raise HTTPException(500, "Manager não inicializado")
        return manager.get_status()
    
    @router.get("/posts/pending")
    async def get_pending():
        """Retorna posts pendentes."""
        if not manager:
            raise HTTPException(500, "Manager não inicializado")
        return manager.get_pending_posts()
    
    @router.get("/posts/published")
    async def get_published(limit: int = 20):
        """Retorna posts publicados."""
        if not manager:
            raise HTTPException(500, "Manager não inicializado")
        return manager.get_published_posts(limit)
    
    @router.post("/posts/market-alert")
    async def create_market_alert(request: MarketAlertRequest):
        """Cria post de alerta de mercado."""
        if not manager:
            raise HTTPException(500, "Manager não inicializado")
        
        post = manager.create_market_alert(
            symbol=request.symbol,
            trend=request.trend,
            price=request.price,
            support=request.support,
            resistance=request.resistance,
            analysis_text=request.analysis_text,
            schedule=request.schedule,
        )
        
        return {"success": True, "post_id": post.id}
    
    @router.post("/posts/news")
    async def create_news_post(request: NewsPostRequest):
        """Cria post de notícia."""
        if not manager:
            raise HTTPException(500, "Manager não inicializado")
        
        post = manager.create_news_post(
            title=request.title,
            summary=request.summary,
            sentiment=request.sentiment,
            related_symbols=request.related_symbols,
            schedule=request.schedule,
        )
        
        return {"success": True, "post_id": post.id}
    
    @router.post("/posts/daily-summary")
    async def create_daily_summary(request: DailySummaryRequest):
        """Cria resumo diário."""
        if not manager:
            raise HTTPException(500, "Manager não inicializado")
        
        post = manager.create_daily_summary(
            highlights=request.highlights,
            market_sentiment=request.market_sentiment,
            schedule=request.schedule,
        )
        
        return {"success": True, "post_id": post.id}
    
    @router.post("/posts/trading-tip")
    async def create_trading_tip():
        """Cria dica de trading."""
        if not manager:
            raise HTTPException(500, "Manager não inicializado")
        
        post = manager.create_trading_tip()
        return {"success": True, "post_id": post.id}
    
    @router.post("/posts/educational")
    async def create_educational():
        """Cria post educacional."""
        if not manager:
            raise HTTPException(500, "Manager não inicializado")
        
        post = manager.create_educational()
        return {"success": True, "post_id": post.id}
    
    @router.delete("/posts/{post_id}")
    async def cancel_post(post_id: str):
        """Cancela post agendado."""
        if not manager:
            raise HTTPException(500, "Manager não inicializado")
        
        success = manager.cancel_post(post_id)
        if not success:
            raise HTTPException(404, "Post não encontrado")
        
        return {"success": True}
    
    return router
