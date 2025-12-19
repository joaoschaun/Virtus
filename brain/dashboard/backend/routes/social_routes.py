"""
VIRTUS Dashboard - Social Media Routes
======================================

API para gerenciar posts de social media.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from datetime import datetime
import json
import sys

# Caminho raiz do Virtus - corrigido para estrutura real do sistema
VIRTUS_ROOT = Path("C:/Users/Administrator/Desktop/Virtus")
BRAIN_PATH = VIRTUS_ROOT / "brain"
sys.path.insert(0, str(BRAIN_PATH))

router = APIRouter(prefix="/social", tags=["Social Media"])

# Diretórios - usando caminho absoluto correto
DATA_DIR = BRAIN_PATH / "data" / "social_media"
IMAGES_DIR = DATA_DIR / "images"
POSTS_DIR = DATA_DIR / "posts"

# Cria diretórios se não existem
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
POSTS_DIR.mkdir(exist_ok=True)


class MarketAlertRequest(BaseModel):
    symbol: str
    trend: str  # bullish, bearish, neutral
    price: float
    support: Optional[float] = None
    resistance: Optional[float] = None


class NewsPostRequest(BaseModel):
    title: str
    summary: str
    sentiment: str = "neutral"


class TipRequest(BaseModel):
    type: str = "trading_tip"  # trading_tip ou educational


# Estado dos posts
posts_db: List[dict] = []


def load_posts():
    """Carrega posts do arquivo."""
    global posts_db
    posts_file = DATA_DIR / "posts_history.json"
    if posts_file.exists():
        with open(posts_file, 'r', encoding='utf-8') as f:
            posts_db = json.load(f)
    return posts_db


def save_posts():
    """Salva posts no arquivo."""
    posts_file = DATA_DIR / "posts_history.json"
    with open(posts_file, 'w', encoding='utf-8') as f:
        json.dump(posts_db, f, indent=2, ensure_ascii=False)


# Carrega ao iniciar
load_posts()


@router.get("/status")
async def get_status():
    """Retorna status do sistema de social media."""
    return {
        "enabled": True,
        "mode": "manual",  # manual = gera imagem, usuário posta
        "posts_generated": len(posts_db),
        "images_dir": str(IMAGES_DIR),
    }


@router.get("/posts")
async def get_posts(limit: int = 20):
    """Retorna últimos posts gerados."""
    load_posts()
    return {
        "posts": posts_db[-limit:][::-1],  # Mais recentes primeiro
        "total": len(posts_db),
    }


@router.post("/generate/market-alert")
async def generate_market_alert(request: MarketAlertRequest):
    """Gera post de alerta de mercado."""
    try:
        from src.social import ContentGenerator, ImageGenerator, ImageConfig
        
        content_gen = ContentGenerator()
        image_gen = ImageGenerator(
            assets_dir=BRAIN_PATH / "dashboard" / "frontend" / "public"
        )
        
        # Gera conteúdo
        content = content_gen.generate_market_alert(
            symbol=request.symbol,
            trend=request.trend,
            price=request.price,
            support=request.support,
            resistance=request.resistance,
        )
        
        # Gera imagem
        config = ImageConfig(
            title=content.title,
            symbol=request.symbol,
            trend=request.trend,
            price=request.price,
            support=request.support,
            resistance=request.resistance,
            hashtags=content.hashtags,
        )
        
        image = image_gen.generate_market_alert(config)
        
        # Salva imagem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"market_alert_{request.symbol}_{timestamp}.png"
        image_path = IMAGES_DIR / filename
        image_gen.save(image, image_path)
        
        # Salva post
        post = {
            "id": len(posts_db) + 1,
            "type": "market_alert",
            "title": content.title,
            "caption": content.caption,
            "image_file": filename,
            "symbol": request.symbol,
            "trend": request.trend,
            "price": request.price,
            "created_at": datetime.now().isoformat(),
            "posted": False,
        }
        posts_db.append(post)
        save_posts()
        
        return {
            "success": True,
            "post": post,
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar post: {str(e)}")


@router.post("/generate/news")
async def generate_news_post(request: NewsPostRequest):
    """Gera post de notícia."""
    try:
        from src.social import ContentGenerator, ImageGenerator, ImageConfig
        
        content_gen = ContentGenerator()
        image_gen = ImageGenerator(
            assets_dir=BRAIN_PATH / "dashboard" / "frontend" / "public"
        )
        
        # Gera conteúdo
        content = content_gen.generate_news_post(
            title=request.title,
            summary=request.summary,
            sentiment=request.sentiment,
        )
        
        # Gera imagem
        config = ImageConfig(
            title=request.title,
            body=request.summary,
            trend=request.sentiment,
        )
        
        image = image_gen.generate_news_highlight(config)
        
        # Salva imagem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_{timestamp}.png"
        image_path = IMAGES_DIR / filename
        image_gen.save(image, image_path)
        
        # Salva post
        post = {
            "id": len(posts_db) + 1,
            "type": "news",
            "title": request.title,
            "caption": content.caption,
            "image_file": filename,
            "sentiment": request.sentiment,
            "created_at": datetime.now().isoformat(),
            "posted": False,
        }
        posts_db.append(post)
        save_posts()
        
        return {
            "success": True,
            "post": post,
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar post: {str(e)}")


@router.post("/generate/tip")
async def generate_tip(request: TipRequest):
    """Gera post de dica ou educacional."""
    try:
        from src.social import ContentGenerator, ImageGenerator, ImageConfig
        
        content_gen = ContentGenerator()
        image_gen = ImageGenerator(
            assets_dir=BRAIN_PATH / "dashboard" / "frontend" / "public"
        )
        
        # Gera conteúdo
        if request.type == "educational":
            content = content_gen.generate_educational()
        else:
            content = content_gen.generate_trading_tip()
        
        # Gera imagem
        config = ImageConfig(
            title=content.title,
            body=content.body,
        )
        
        image = image_gen.generate_quote(config)
        
        # Salva imagem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tip_{timestamp}.png"
        image_path = IMAGES_DIR / filename
        image_gen.save(image, image_path)
        
        # Salva post
        post = {
            "id": len(posts_db) + 1,
            "type": request.type,
            "title": content.title,
            "caption": content.caption,
            "image_file": filename,
            "created_at": datetime.now().isoformat(),
            "posted": False,
        }
        posts_db.append(post)
        save_posts()
        
        return {
            "success": True,
            "post": post,
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar post: {str(e)}")


@router.get("/image/{filename:path}")
async def get_image(filename: str):
    """Retorna imagem do post."""
    from urllib.parse import unquote
    
    # Decodifica URL encoding
    decoded_filename = unquote(filename)
    image_path = IMAGES_DIR / decoded_filename
    
    if not image_path.exists():
        # Tenta encontrar arquivo similar
        for f in IMAGES_DIR.glob("*.png"):
            if decoded_filename in f.name or f.name in decoded_filename:
                image_path = f
                break
    
    if not image_path.exists():
        raise HTTPException(404, f"Imagem não encontrada: {decoded_filename}")
    
    return FileResponse(
        image_path,
        media_type="image/png",
        filename=image_path.name,
    )


@router.get("/download/{filename:path}")
async def download_image(filename: str):
    """Download da imagem."""
    from urllib.parse import unquote
    
    decoded_filename = unquote(filename)
    image_path = IMAGES_DIR / decoded_filename
    
    if not image_path.exists():
        # Tenta encontrar arquivo similar
        for f in IMAGES_DIR.glob("*.png"):
            if decoded_filename in f.name or f.name in decoded_filename:
                image_path = f
                break
    
    if not image_path.exists():
        raise HTTPException(404, f"Imagem não encontrada: {decoded_filename}")
    
    return FileResponse(
        image_path,
        media_type="image/png",
        filename=image_path.name,
        headers={"Content-Disposition": f"attachment; filename={image_path.name}"}
    )


@router.post("/posts/{post_id}/mark-posted")
async def mark_as_posted(post_id: int):
    """Marca post como publicado."""
    load_posts()
    
    for post in posts_db:
        if post["id"] == post_id:
            post["posted"] = True
            post["posted_at"] = datetime.now().isoformat()
            save_posts()
            return {"success": True, "post": post}
    
    raise HTTPException(404, "Post não encontrado")


@router.delete("/posts/{post_id}")
async def delete_post(post_id: int):
    """Deleta um post."""
    global posts_db
    load_posts()
    
    for i, post in enumerate(posts_db):
        if post["id"] == post_id:
            # Remove imagem
            image_path = IMAGES_DIR / post.get("image_file", "")
            if image_path.exists():
                image_path.unlink()
            
            # Remove do banco
            posts_db.pop(i)
            save_posts()
            return {"success": True}
    
    raise HTTPException(404, "Post não encontrado")


# ============================================================
# GERAÇÃO AUTOMÁTICA - Integração com News Service do Brain
# ============================================================

@router.post("/auto/generate-from-news")
async def auto_generate_from_news(limit: int = 3):
    """
    Gera posts automaticamente das últimas notícias do Brain.
    
    O sistema:
    1. Busca notícias do news_service
    2. Gera imagem com branding Virtus
    3. Cria caption pronta para Instagram
    4. Você só baixa e posta!
    """
    try:
        from services.auto_post_generator import auto_generator
        
        posts = await auto_generator.fetch_and_generate(limit)
        
        # Recarrega posts_db para incluir os novos
        load_posts()
        
        return {
            "success": True,
            "generated": len(posts),
            "posts": posts,
            "message": f"{len(posts)} posts gerados das notícias!"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar posts: {str(e)}")


@router.post("/auto/generate-tip")
async def auto_generate_tip():
    """Gera uma dica de trading automaticamente."""
    try:
        from services.auto_post_generator import auto_generator
        
        post = await auto_generator.generate_trading_tip()
        
        if post:
            load_posts()
            return {
                "success": True,
                "post": post,
            }
        else:
            return {
                "success": False,
                "message": "Não foi possível gerar dica"
            }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar dica: {str(e)}")


@router.post("/auto/generate-summary")
async def auto_generate_summary():
    """Gera resumo diário do mercado."""
    try:
        from services.auto_post_generator import auto_generator
        
        post = await auto_generator.generate_market_summary()
        
        if post:
            load_posts()
            return {
                "success": True,
                "post": post,
            }
        else:
            return {
                "success": False,
                "message": "Não foi possível gerar resumo"
            }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar resumo: {str(e)}")


@router.get("/pending")
async def get_pending_posts():
    """Retorna posts prontos para postar (não postados ainda)."""
    load_posts()
    pending = [p for p in posts_db if not p.get("posted", False)]
    
    return {
        "pending": pending[::-1],  # Mais recentes primeiro
        "count": len(pending),
    }


# ============================================================
# BRIEFING DIÁRIO - Integração com EODHD + ForexNews + Investing
# ============================================================

@router.post("/briefing/generate")
async def generate_daily_briefing():
    """
    Gera post de briefing diário para redes sociais.
    
    Integra dados de múltiplas fontes:
    - EODHD API (notícias e calendário econômico)
    - ForexNews API (notícias forex em tempo real)
    - Investing.com (notícias gerais)
    - TESS AI (análise de sentimento)
    
    Cria:
    - Imagem com design Virtus
    - Caption completa pronta para Instagram
    - Informações sobre sinais, eventos e notícias
    """
    try:
        from services.social_briefing_generator import social_briefing_generator
        
        post = await social_briefing_generator.generate_daily_briefing_post()
        
        # Recarrega para incluir o novo post
        load_posts()
        
        return {
            "success": True,
            "post": post,
            "message": "✅ Briefing diário gerado com sucesso! Pronto para postar."
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Erro ao gerar briefing: {str(e)}")


@router.get("/briefing/preview")
async def preview_briefing():
    """
    Prévia do briefing sem gerar imagem.
    
    Útil para verificar os dados antes de gerar o post completo.
    """
    try:
        from services.social_briefing_generator import social_briefing_generator
        
        await social_briefing_generator.initialize()
        data = await social_briefing_generator._collect_all_data()
        
        # Gera apenas o texto
        caption = await social_briefing_generator._generate_briefing_caption(
            data, 
            datetime.now()
        )
        
        return {
            "success": True,
            "preview": {
                "caption": caption,
                "market_mood": data.get('market_mood'),
                "news_count": len(data.get('news', [])),
                "events_count": len(data.get('events', [])),
                "signals": data.get('signals', {}),
                "sources": data.get('sources', []),
            }
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar prévia: {str(e)}")


# ============================================================
# NOTÍCIAS BRASILEIRAS - Seleção manual para posts
# ============================================================

@router.get("/news/brazil")
async def get_brazil_news_for_social(limit: int = 10):
    """
    Busca notícias de ações brasileiras para seleção manual.
    
    Retorna notícias traduzidas prontas para criar posts.
    """
    try:
        from services.portal_service import get_portal_service
        
        service = get_portal_service()
        news = await service.get_eodhd_news(limit=limit)
        
        return {
            "success": True,
            "count": len(news),
            "news": [n.to_dict() for n in news]
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao buscar notícias: {str(e)}")


@router.get("/news/all")
async def get_all_news_for_social(limit: int = 15):
    """
    Busca todas as notícias (forex + brasil) para seleção manual.
    """
    try:
        from services.portal_service import get_portal_service
        
        service = get_portal_service()
        
        # Busca ambas as fontes
        forex_news = await service.get_forex_news(limit=limit//2)
        brazil_news = await service.get_eodhd_news(limit=limit//2)
        
        all_news = []
        for n in forex_news:
            all_news.append(n.to_dict())
        for n in brazil_news:
            all_news.append(n.to_dict())
        
        # Ordena por data
        all_news.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        return {
            "success": True,
            "count": len(all_news),
            "news": all_news[:limit]
        }
        
    except Exception as e:
        raise HTTPException(500, f"Erro ao buscar notícias: {str(e)}")


class SelectedNewsRequest(BaseModel):
    """Request para gerar post de notícia selecionada."""
    title: str
    summary: str
    sentiment: str = "neutral"
    category: str = "stocks_br"
    tickers: List[str] = []
    source: str = ""


@router.post("/generate/from-selected-news")
async def generate_from_selected_news(request: SelectedNewsRequest):
    """
    Gera post a partir de uma notícia selecionada pelo usuário.
    
    Permite escolher qual notícia virar post antes de gerar.
    """
    try:
        from services.auto_post_generator import auto_generator
        
        # Prepara dados da notícia no formato esperado
        news_data = {
            'title': request.title,
            'summary': request.summary,
            'sentiment': request.sentiment,
            'category': request.category,
            'tickers': request.tickers,
            'source': request.source,
            'published_at': datetime.now().isoformat()
        }
        
        # Gera o post
        post = await auto_generator.generate_single_news_post(news_data)
        
        if post:
            load_posts()
            return {
                "success": True,
                "post": post,
                "message": "✅ Post gerado com sucesso!"
            }
        else:
            raise HTTPException(500, "Falha ao gerar post")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Erro ao gerar post: {str(e)}")

