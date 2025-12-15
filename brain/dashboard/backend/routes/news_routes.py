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
