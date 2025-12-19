"""
VIRTUS Dashboard - Rotas de Notícias
=====================================

Endpoints para notícias com áudio em português.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from services.news_service import (
    news_service,
    NewsCategory,
    NewsPriority,
    NewsItem,
)

router = APIRouter(prefix="/news", tags=["Notícias"])


class NewsResponse(BaseModel):
    """Resposta de notícia."""
    id: str
    title: str
    summary: str
    content: str
    source: str
    category: str
    priority: str
    published_at: str
    url: Optional[str]
    related_symbols: List[str]
    audio_url: Optional[str]
    audio_duration_seconds: int
    sentiment: Optional[str]
    impact_score: float


class NewsListResponse(BaseModel):
    """Lista de notícias."""
    news: List[NewsResponse]
    total: int
    category: str
    updated_at: str


@router.get("", response_model=NewsListResponse)
async def get_news(
    category: str = Query("all", description="Categoria: forex, commodities, crypto, economy, stocks, all"),
    limit: int = Query(10, ge=1, le=50, description="Número máximo de notícias"),
):
    """
    Busca notícias financeiras em português.
    
    Retorna lista de notícias com URLs para áudio.
    """
    try:
        # Converte categoria
        try:
            news_category = NewsCategory(category.lower())
        except ValueError:
            news_category = NewsCategory.ALL
        
        # Busca notícias
        news_items = await news_service.fetch_news(
            category=news_category,
            limit=limit
        )
        
        return NewsListResponse(
            news=[
                NewsResponse(
                    id=n.id,
                    title=n.title,
                    summary=n.summary,
                    content=n.content,
                    source=n.source,
                    category=n.category.value,
                    priority=n.priority.value,
                    published_at=n.published_at.isoformat(),
                    url=n.url,
                    related_symbols=n.related_symbols,
                    audio_url=n.audio_url,
                    audio_duration_seconds=n.audio_duration_seconds,
                    sentiment=n.sentiment,
                    impact_score=n.impact_score,
                )
                for n in news_items
            ],
            total=len(news_items),
            category=category,
            updated_at=datetime.now().isoformat(),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar notícias: {str(e)}")


@router.get("/audio/{filename}")
async def get_audio(filename: str):
    """
    Retorna arquivo de áudio de uma notícia.
    
    O áudio é gerado em português brasileiro usando TTS.
    """
    audio_path = news_service.get_audio_path(filename)
    
    if not audio_path:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=filename,
    )


@router.get("/summary/audio")
async def get_summary_audio():
    """
    Retorna áudio com resumo das principais notícias.
    
    Ideal para ouvir um briefing rápido do mercado.
    """
    try:
        # Gera texto do resumo
        summary_text = await news_service.get_news_summary()
        
        # Gera áudio
        audio_path = await news_service.tts.text_to_speech(summary_text)
        
        if not audio_path:
            raise HTTPException(
                status_code=500, 
                detail="Não foi possível gerar áudio. Verifique se gTTS está instalado."
            )
        
        return FileResponse(
            path=str(audio_path),
            media_type="audio/mpeg",
            filename="news_summary.mp3",
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resumo: {str(e)}")


@router.get("/{news_id}", response_model=NewsResponse)
async def get_news_by_id(news_id: str):
    """
    Retorna uma notícia específica pelo ID.
    """
    news = news_service.get_cached_news(news_id)
    
    if not news:
        raise HTTPException(status_code=404, detail="Notícia não encontrada")
    
    return NewsResponse(
        id=news.id,
        title=news.title,
        summary=news.summary,
        content=news.content,
        source=news.source,
        category=news.category.value,
        priority=news.priority.value,
        published_at=news.published_at.isoformat(),
        url=news.url,
        related_symbols=news.related_symbols,
        audio_url=news.audio_url,
        audio_duration_seconds=news.audio_duration_seconds,
        sentiment=news.sentiment,
        impact_score=news.impact_score,
    )


@router.post("/{news_id}/play")
async def mark_news_played(news_id: str):
    """
    Marca notícia como reproduzida (para analytics).
    """
    news = news_service.get_cached_news(news_id)
    
    if not news:
        raise HTTPException(status_code=404, detail="Notícia não encontrada")
    
    # Aqui você pode registrar analytics
    return {"status": "ok", "news_id": news_id, "played_at": datetime.now().isoformat()}


@router.get("/categories/list")
async def list_categories():
    """
    Lista categorias disponíveis.
    """
    return {
        "categories": [
            {"value": "all", "label": "Todas", "icon": "📰"},
            {"value": "forex", "label": "Forex", "icon": "💱"},
            {"value": "commodities", "label": "Commodities", "icon": "🥇"},
            {"value": "crypto", "label": "Cripto", "icon": "₿"},
            {"value": "economy", "label": "Economia", "icon": "📊"},
            {"value": "stocks", "label": "Ações", "icon": "📈"},
        ]
    }


@router.get("/social/feed")
async def get_social_feed(
    limit: int = Query(5, ge=1, le=20, description="Número de notícias para social"),
):
    """
    Retorna notícias formatadas para publicação em redes sociais.
    
    Inclui:
    - Texto formatado para Twitter/Instagram
    - Hashtags relevantes
    - Emojis contextuais
    - URL do áudio
    """
    try:
        # Busca notícias de alta prioridade
        news_items = await news_service.fetch_news(limit=limit)
        
        social_posts = []
        for news in news_items:
            # Formata para redes sociais
            emoji = "📈" if news.sentiment == "bullish" else "📉" if news.sentiment == "bearish" else "📊"
            
            # Gera hashtags baseado nos símbolos
            hashtags = ["#Trading", "#Mercado"]
            for symbol in news.related_symbols:
                hashtags.append(f"#{symbol}")
            if news.category.value == "forex":
                hashtags.append("#Forex")
            elif news.category.value == "commodities":
                hashtags.append("#Ouro")
            elif news.category.value == "economy":
                hashtags.append("#Economia")
            
            # Texto para Twitter (max 280 chars)
            twitter_text = f"{emoji} {news.title}\n\n{news.summary[:150]}...\n\n{' '.join(hashtags[:5])}"
            if len(twitter_text) > 280:
                twitter_text = twitter_text[:277] + "..."
            
            # Texto para Instagram (pode ser mais longo)
            instagram_text = f"{emoji} {news.title}\n\n{news.summary}\n\n{' '.join(hashtags)}\n\n🔊 Ouça em áudio em português!"
            
            social_posts.append({
                "news_id": news.id,
                "title": news.title,
                "twitter_text": twitter_text,
                "instagram_text": instagram_text,
                "hashtags": hashtags,
                "sentiment": news.sentiment,
                "priority": news.priority.value,
                "audio_url": news.audio_url,
                "audio_duration": news.audio_duration_seconds,
                "symbols": news.related_symbols,
                "category": news.category.value,
                "published_at": news.published_at.isoformat(),
            })
        
        return {
            "posts": social_posts,
            "total": len(social_posts),
            "generated_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar feed social: {str(e)}")


@router.get("/briefing/morning")
async def get_morning_briefing():
    """
    Retorna briefing matinal com resumo das principais notícias.
    
    Ideal para:
    - Post automático nas redes sociais
    - Áudio de abertura do mercado
    - Newsletter diária
    """
    try:
        # Busca notícias de todas as categorias
        news_items = await news_service.fetch_news(limit=10)
        
        # Agrupa por categoria
        by_category = {}
        for news in news_items:
            cat = news.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(news)
        
        # Gera texto do briefing
        briefing_text = "🌅 BOM DIA, TRADER!\n\n"
        briefing_text += f"📅 {datetime.now().strftime('%d/%m/%Y - %A')}\n\n"
        briefing_text += "📰 PRINCIPAIS NOTÍCIAS:\n\n"
        
        for i, news in enumerate(news_items[:5], 1):
            emoji = "📈" if news.sentiment == "bullish" else "📉" if news.sentiment == "bearish" else "📊"
            briefing_text += f"{i}. {emoji} {news.title}\n"
        
        briefing_text += "\n💡 Mantenha-se informado e opere com sabedoria!\n"
        briefing_text += "#Trading #MercadoFinanceiro #BomDiaTrader"
        
        # Gera áudio do briefing
        audio_path = await news_service.tts.text_to_speech(
            f"Bom dia, trader! Hoje é {datetime.now().strftime('%d de %B de %Y')}. "
            + "Aqui estão as principais notícias do mercado. "
            + " ".join([f"{n.title}. " for n in news_items[:5]])
            + "Mantenha-se informado e opere com sabedoria!"
        )
        
        audio_url = f"/api/news/audio/{audio_path.name}" if audio_path else None
        
        return {
            "date": datetime.now().isoformat(),
            "text": briefing_text,
            "audio_url": audio_url,
            "news_count": len(news_items),
            "by_category": {k: len(v) for k, v in by_category.items()},
            "top_news": [
                {
                    "title": n.title,
                    "sentiment": n.sentiment,
                    "symbols": n.related_symbols,
                }
                for n in news_items[:5]
            ],
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar briefing: {str(e)}")