"""
VIRTUS Dashboard - Rotas do Forex Briefing
==========================================

Rotas API para o sistema de briefing forex:
- /api/forex/news - Notícias forex agregadas
- /api/forex/calendar - Calendário econômico
- /api/forex/signals - Sinais por símbolo
- /api/forex/briefing/daily - Briefing completo
- /api/forex/briefing/audio - Áudio do briefing
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import logging

from services.forex_briefing_service import forex_briefing_service, FOREX_SYMBOLS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forex", tags=["forex"])


@router.get("/news")
async def get_forex_news(
    symbols: Optional[str] = Query(None, description="Símbolos separados por vírgula (ex: XAUUSD,EURUSD)"),
    limit: int = Query(20, ge=1, le=50, description="Número máximo de notícias"),
    hours_back: int = Query(24, ge=1, le=168, description="Horas no passado para buscar")
):
    """
    Busca notícias relevantes para forex de múltiplas fontes.
    
    Fontes:
    - EODHD News API
    - ForexNews API (se configurada)
    
    As notícias são analisadas para identificar símbolos relevantes,
    sentimento e impacto no mercado.
    """
    try:
        symbol_list = symbols.split(',') if symbols else None
        
        if symbol_list:
            # Valida símbolos
            invalid = [s for s in symbol_list if s not in FOREX_SYMBOLS]
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Símbolos inválidos: {invalid}. Válidos: {FOREX_SYMBOLS}"
                )
        
        news = await forex_briefing_service.get_forex_news(
            symbols=symbol_list,
            limit=limit,
            hours_back=hours_back
        )
        
        return {
            "success": True,
            "count": len(news),
            "symbols": symbol_list or FOREX_SYMBOLS,
            "timestamp": datetime.now().isoformat(),
            "news": [n.to_dict() for n in news]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar notícias forex: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar")
async def get_forex_calendar(
    days_ahead: int = Query(7, ge=1, le=30, description="Dias à frente"),
    countries: Optional[str] = Query(None, description="Países separados por vírgula (ex: US,EU,GB)"),
    min_impact: str = Query("medium", description="Impacto mínimo: low, medium, high")
):
    """
    Obtém calendário econômico filtrado para forex.
    
    Retorna eventos econômicos que podem impactar os principais
    pares forex, filtrados por países relevantes e nível de impacto.
    """
    try:
        country_list = countries.split(',') if countries else None
        
        if min_impact not in ['low', 'medium', 'high']:
            raise HTTPException(
                status_code=400,
                detail="min_impact deve ser: low, medium ou high"
            )
        
        events = await forex_briefing_service.get_forex_calendar(
            days_ahead=days_ahead,
            countries=country_list,
            min_impact=min_impact
        )
        
        return {
            "success": True,
            "count": len(events),
            "days_ahead": days_ahead,
            "min_impact": min_impact,
            "timestamp": datetime.now().isoformat(),
            "events": [e.to_dict() for e in events]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar calendário: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_all_signals():
    """
    Obtém sinais indicativos para todos os símbolos forex monitorados.
    
    Cada sinal indica:
    - Direção do mercado (bullish, bearish, neutral)
    - Força do sinal (0 a 1)
    - Sentimento das notícias
    - Impacto do calendário
    - Resumo textual
    """
    try:
        signals = {}
        
        for symbol in FOREX_SYMBOLS:
            signal = await forex_briefing_service.get_symbol_signal(symbol)
            signals[symbol] = signal.to_dict()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "signals": signals
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar sinais: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/{symbol}")
async def get_symbol_signal(symbol: str):
    """
    Obtém sinal indicativo para um símbolo específico.
    
    Args:
        symbol: Símbolo forex (ex: XAUUSD, EURUSD)
    """
    try:
        symbol = symbol.upper()
        
        if symbol not in FOREX_SYMBOLS:
            raise HTTPException(
                status_code=400,
                detail=f"Símbolo inválido: {symbol}. Válidos: {FOREX_SYMBOLS}"
            )
        
        signal = await forex_briefing_service.get_symbol_signal(symbol)
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "signal": signal.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar sinal para {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefing/daily")
async def get_daily_briefing(
    symbols: Optional[str] = Query(None, description="Símbolos separados por vírgula"),
    generate_audio: bool = Query(True, description="Gerar áudio do briefing")
):
    """
    Gera briefing diário completo para operações forex.
    
    O briefing inclui:
    - Humor geral do mercado
    - Sinais por símbolo
    - Top 5 notícias
    - Eventos de alto impacto
    - Texto para áudio (português)
    - Post para redes sociais
    
    O áudio é gerado automaticamente em português brasileiro.
    """
    try:
        symbol_list = symbols.split(',') if symbols else None
        
        if symbol_list:
            invalid = [s for s in symbol_list if s not in FOREX_SYMBOLS]
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Símbolos inválidos: {invalid}. Válidos: {FOREX_SYMBOLS}"
                )
        
        briefing = await forex_briefing_service.get_daily_briefing(
            symbols=symbol_list,
            generate_audio=generate_audio
        )
        
        return {
            "success": True,
            "briefing": briefing.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar briefing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefing/audio/{filename}")
async def get_briefing_audio(filename: str):
    """
    Retorna arquivo de áudio do briefing.
    
    Args:
        filename: Nome do arquivo de áudio
    """
    try:
        # Caminhos possíveis para o áudio - corrigido para estrutura real
        # O diretório brain está em: C:\Users\Administrator\Desktop\Virtus\brain
        # E os áudios ficam em: brain\data\audio_cache
        
        # Caminho absoluto do sistema
        VIRTUS_ROOT = Path("C:/Users/Administrator/Desktop/Virtus")
        BRAIN_PATH = VIRTUS_ROOT / "brain"
        
        possible_paths = [
            # Caminho principal correto
            BRAIN_PATH / "data" / "audio_cache" / filename,
            # Caminhos relativos como fallback
            Path(__file__).resolve().parent.parent.parent / "data" / "audio_cache" / filename,
            Path(__file__).resolve().parent.parent.parent.parent / "data" / "audio_cache" / filename,
        ]
        
        for audio_path in possible_paths:
            logger.info(f"Verificando caminho de áudio: {audio_path}")
            if audio_path.exists():
                logger.info(f"Áudio encontrado: {audio_path}")
                return FileResponse(
                    path=str(audio_path),
                    media_type="audio/mpeg",
                    filename=filename
                )
        
        logger.error(f"Áudio não encontrado em nenhum caminho: {filename}")
        logger.error(f"Caminhos tentados: {[str(p) for p in possible_paths]}")
        raise HTTPException(status_code=404, detail=f"Áudio não encontrado: {filename}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao servir áudio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefing/social")
async def get_social_post():
    """
    Gera post para redes sociais com o resumo do mercado.
    
    O post é formatado com emojis e hashtags apropriados
    para publicação no Instagram, Twitter e LinkedIn.
    """
    try:
        briefing = await forex_briefing_service.get_daily_briefing(
            generate_audio=False
        )
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "post": briefing.social_post,
            "market_mood": briefing.market_mood.value,
            "headline": briefing.headline
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar post social: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def forex_health():
    """
    Verifica saúde do serviço de forex briefing.
    """
    try:
        await forex_briefing_service.initialize()
        
        return {
            "status": "healthy",
            "service": "forex_briefing",
            "tess_available": forex_briefing_service._tess_available,
            "tts_available": forex_briefing_service._tts is not None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/briefing/generate-social-post")
async def generate_social_briefing_post():
    """
    Gera post de briefing diário para redes sociais.
    
    Integra dados de:
    - EODHD (notícias, calendário)
    - ForexNews API (notícias forex)
    - Investing.com (via NewsService existente)
    - TESS AI (análise de sentimento e geração de texto)
    
    Cria imagem + caption prontos para postar no Instagram.
    """
    try:
        from services.social_briefing_generator import social_briefing_generator
        
        post = await social_briefing_generator.generate_daily_briefing_post()
        
        return {
            "success": True,
            "post": post,
            "message": "Post de briefing diário gerado com sucesso!"
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar post de briefing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
