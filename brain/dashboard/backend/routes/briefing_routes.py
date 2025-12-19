"""
VIRTUS Dashboard - Daily Briefing Routes
=========================================

Endpoints para o briefing diário completo.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from services.daily_briefing_service import daily_briefing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/briefing", tags=["Daily Briefing"])


@router.get("/daily")
async def get_daily_briefing() -> Dict[str, Any]:
    """
    Retorna o briefing diário completo.
    
    Inclui:
    - Visão geral do mercado
    - Principais notícias
    - Calendário econômico
    - Alertas de dividendos
    - Texto para áudio
    """
    try:
        briefing = await daily_briefing_service.generate_briefing()
        return briefing.to_dict()
    except Exception as e:
        logger.error(f"Erro ao gerar briefing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market")
async def get_market_overview() -> Dict[str, Any]:
    """Retorna apenas a visão geral do mercado."""
    try:
        briefing = await daily_briefing_service.generate_briefing()
        return {
            'ibovespa': briefing.market_overview.ibovespa,
            'dolar': briefing.market_overview.dolar,
            'sp500': briefing.market_overview.sp500,
            'sentiment': briefing.market_overview.sentiment.value,
            'sentiment_description': briefing.market_overview.sentiment_description
        }
    except Exception as e:
        logger.error(f"Erro ao buscar mercado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dividends/urgent")
async def get_urgent_dividends() -> Dict[str, Any]:
    """Retorna alertas urgentes de dividendos."""
    try:
        briefing = await daily_briefing_service.generate_briefing()
        urgent = [d for d in briefing.dividend_alerts if d.urgency in ['today', 'urgent']]
        return {
            'alerts': [
                {
                    'ticker': d.ticker,
                    'company_name': d.company_name,
                    'buy_limit_date': d.buy_limit_date,
                    'dividend_value': d.dividend_value,
                    'dividend_yield': d.dividend_yield,
                    'days_remaining': d.days_remaining,
                    'urgency': d.urgency
                } for d in urgent
            ],
            'total': len(urgent)
        }
    except Exception as e:
        logger.error(f"Erro ao buscar dividendos urgentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio-text")
async def get_audio_text() -> Dict[str, Any]:
    """Retorna o texto otimizado para síntese de voz."""
    try:
        briefing = await daily_briefing_service.generate_briefing()
        return {
            'text': briefing.audio_text,
            'date': briefing.date,
            'weekday': briefing.weekday
        }
    except Exception as e:
        logger.error(f"Erro ao gerar texto de áudio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
