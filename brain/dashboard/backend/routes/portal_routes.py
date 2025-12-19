"""
VIRTUS Portal - API Routes
===========================

Rotas da API para o portal público VIRTUS.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from services.portal_service import get_portal_service, NewsCategory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portal", tags=["portal"])


@router.get("/home")
async def get_homepage_data():
    """
    Retorna todos os dados para a homepage do portal.
    
    Inclui:
    - Índices de mercado (Ibovespa, S&P500, Dólar, etc)
    - Cotações de ações brasileiras
    - Notícias recentes
    - Calendário econômico do dia
    - Sentimento de mercado
    """
    try:
        service = get_portal_service()
        data = await service.get_homepage_data()
        return data
    except Exception as e:
        logger.error(f"Erro ao buscar dados da homepage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indices")
async def get_market_indices():
    """
    Retorna cotações dos principais índices de mercado.
    
    Índices incluídos:
    - Ibovespa (^BVSP)
    - S&P 500 (^GSPC)
    - Nasdaq (^IXIC)
    - Dow Jones (^DJI)
    - Dólar (USDBRL)
    - Euro (EURBRL)
    - Bitcoin (BTC-USD)
    - Ouro (GC=F)
    """
    try:
        service = get_portal_service()
        indices = await service.get_market_indices()
        return {
            'success': True,
            'data': {k: v.to_dict() for k, v in indices.items()}
        }
    except Exception as e:
        logger.error(f"Erro ao buscar índices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quotes/brazil")
async def get_brazil_quotes(
    symbols: Optional[str] = Query(
        None, 
        description="Lista de símbolos separados por vírgula (ex: PETR4,VALE3,ITUB4)"
    )
):
    """
    Retorna cotações de ações brasileiras.
    
    Se nenhum símbolo for especificado, retorna as principais ações do Ibovespa.
    """
    try:
        service = get_portal_service()
        symbol_list = symbols.split(',') if symbols else None
        quotes = await service.get_brazil_quotes(symbol_list)
        return {
            'success': True,
            'count': len(quotes),
            'data': [q.to_dict() for q in quotes]
        }
    except Exception as e:
        logger.error(f"Erro ao buscar cotações Brasil: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news")
async def get_news(
    category: Optional[str] = Query(None, description="Categoria: forex, stocks_br, stocks_us, commodities, crypto, economy"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Retorna notícias do mercado financeiro.
    
    Fontes:
    - ForexNews API (forex, commodities)
    - EODHD (ações brasileiras)
    """
    try:
        service = get_portal_service()
        all_news = []
        
        if category in [None, 'forex', 'commodities']:
            forex_news = await service.get_forex_news(limit=limit)
            all_news.extend([n.to_dict() for n in forex_news])
        
        if category in [None, 'stocks_br']:
            br_news = await service.get_eodhd_news(limit=limit)
            all_news.extend([n.to_dict() for n in br_news])
        
        # Ordena por data
        all_news.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        return {
            'success': True,
            'count': len(all_news[:limit]),
            'data': all_news[:limit]
        }
    except Exception as e:
        logger.error(f"Erro ao buscar notícias: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/forex")
async def get_forex_news(
    currencies: Optional[str] = Query(None, description="Pares de moedas (ex: EUR-USD,GBP-USD,XAU-USD)"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Retorna notícias de forex via ForexNews API.
    """
    try:
        service = get_portal_service()
        currency_list = currencies.split(',') if currencies else None
        news = await service.get_forex_news(limit=limit, currencies=currency_list)
        return {
            'success': True,
            'count': len(news),
            'data': [n.to_dict() for n in news]
        }
    except Exception as e:
        logger.error(f"Erro ao buscar notícias forex: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/brazil")
async def get_brazil_news(
    symbols: Optional[str] = Query(None, description="Símbolos de ações (ex: PETR4,VALE3,ITUB4)"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Retorna notícias de ações brasileiras via EODHD API.
    """
    try:
        service = get_portal_service()
        symbol_list = [f"{s.strip()}.SA" for s in symbols.split(',')] if symbols else None
        logger.info(f"Buscando notícias BR com symbols: {symbol_list}")
        news = await service.get_eodhd_news(symbols=symbol_list, limit=limit)
        logger.info(f"Retornando {len(news)} notícias BR")
        return {
            'success': True,
            'count': len(news),
            'data': [n.to_dict() for n in news]
        }
    except Exception as e:
        logger.error(f"Erro ao buscar notícias Brasil: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar")
async def get_economic_calendar(
    days: int = Query(0, ge=0, le=7, description="Dias a partir de hoje (0 = hoje)")
):
    """
    Retorna calendário econômico.
    
    Eventos são ordenados por impacto (alto primeiro) e horário.
    Horários são exibidos no fuso de Brasília.
    """
    try:
        service = get_portal_service()
        events = await service.get_economic_calendar(days=days)
        
        # Separa por impacto
        high_impact = [e.to_dict() for e in events if e.impact == 'high']
        medium_impact = [e.to_dict() for e in events if e.impact == 'medium']
        low_impact = [e.to_dict() for e in events if e.impact == 'low']
        
        return {
            'success': True,
            'date': (service._cache.get(f'calendar_{days}', {}).get('timestamp') or 0),
            'count': len(events),
            'high_impact_count': len(high_impact),
            'events': {
                'all': [e.to_dict() for e in events],
                'high': high_impact,
                'medium': medium_impact,
                'low': low_impact
            }
        }
    except Exception as e:
        logger.error(f"Erro ao buscar calendário: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/high-impact")
async def get_high_impact_events(
    days: int = Query(0, ge=0, le=7)
):
    """
    Retorna apenas eventos de alto impacto do calendário econômico.
    """
    try:
        service = get_portal_service()
        events = await service.get_economic_calendar(days=days)
        high_impact = [e.to_dict() for e in events if e.impact == 'high']
        
        return {
            'success': True,
            'count': len(high_impact),
            'events': high_impact
        }
    except Exception as e:
        logger.error(f"Erro ao buscar eventos de alto impacto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticker")
async def get_ticker_data():
    """
    Retorna dados para o ticker de cotações (barra superior).
    
    Dados compactos dos principais índices para atualização em tempo real.
    """
    try:
        service = get_portal_service()
        indices = await service.get_market_indices()
        
        ticker_items = []
        for key in ['ibovespa', 'sp500', 'dolar', 'euro', 'bitcoin']:
            if key in indices:
                q = indices[key]
                change_val = float(q.change) if q.change else 0
                ticker_items.append({
                    'symbol': key,
                    'name': q.name,
                    'price': q.price,
                    'change': q.change,
                    'change_percent': q.change_percent,
                    'direction': 'up' if change_val >= 0 else 'down'
                })
        
        return {
            'success': True,
            'items': ticker_items
        }
    except Exception as e:
        logger.error(f"Erro ao buscar ticker: {e}")
        raise HTTPException(status_code=500, detail=str(e))
