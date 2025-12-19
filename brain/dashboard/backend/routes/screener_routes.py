"""
Rotas do Screener Inteligente de Ações B3
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from services.screener_service import get_screener_service

router = APIRouter(prefix="/screener", tags=["Screener B3"])


@router.get("/stocks")
async def list_stocks(
    sector: Optional[str] = Query(None, description="Filtrar por setor"),
    stock_type: str = Query("stock", description="Tipo: stock, fund, bdr"),
    sort_by: str = Query("volume", description="Ordenar por: volume, change, market_cap"),
    sort_order: str = Query("desc", description="Ordem: asc, desc"),
    limit: int = Query(50, ge=1, le=200)
):
    """Lista ações com filtros básicos"""
    service = get_screener_service()
    return await service.get_stocks_list(
        sector=sector,
        stock_type=stock_type,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit
    )


@router.get("/fundamentals/{ticker}")
async def get_fundamentals(ticker: str):
    """Obtém dados fundamentalistas de uma ação"""
    service = get_screener_service()
    result = await service.get_stock_fundamentals(ticker.upper())
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Ação {ticker} não encontrada")
    
    return result


@router.get("/filter")
async def screener_filter(
    min_pl: Optional[float] = Query(None, description="P/L mínimo"),
    max_pl: Optional[float] = Query(None, description="P/L máximo"),
    min_pvp: Optional[float] = Query(None, description="P/VP mínimo"),
    max_pvp: Optional[float] = Query(None, description="P/VP máximo"),
    min_roe: Optional[float] = Query(None, description="ROE mínimo (decimal, ex: 0.15 = 15%)"),
    min_dy: Optional[float] = Query(None, description="DY mínimo (decimal, ex: 0.05 = 5%)"),
    max_divida_ebitda: Optional[float] = Query(None, description="Dívida/EBITDA máximo"),
    sector: Optional[str] = Query(None, description="Setor"),
    min_market_cap: Optional[float] = Query(None, description="Market Cap mínimo"),
    sort_by: str = Query("value_score", description="Ordenar por: value_score, dy, pl, pvp, roe"),
    limit: int = Query(30, ge=1, le=100)
):
    """
    Screener avançado com múltiplos filtros
    Retorna ações que atendem aos critérios com score Value Investing
    """
    service = get_screener_service()
    return await service.screener(
        min_pl=min_pl,
        max_pl=max_pl,
        min_pvp=min_pvp,
        max_pvp=max_pvp,
        min_roe=min_roe,
        min_dy=min_dy,
        max_divida_ebitda=max_divida_ebitda,
        sector=sector,
        min_market_cap=min_market_cap,
        sort_by=sort_by,
        limit=limit
    )


@router.get("/top-value")
async def top_value_stocks(limit: int = Query(20, ge=1, le=50)):
    """
    Top ações pelo Score Value Investing
    Filtro: P/L < 20, P/VP < 3, ROE > 10%
    """
    service = get_screener_service()
    return await service.get_top_value_stocks(limit)


@router.get("/top-dividends")
async def top_dividend_stocks(limit: int = Query(20, ge=1, le=50)):
    """
    Top ações pagadoras de dividendos
    Filtro: DY > 4%, P/L < 15
    """
    service = get_screener_service()
    return await service.get_top_dividend_stocks(limit)


@router.get("/growth")
async def growth_stocks(limit: int = Query(20, ge=1, le=50)):
    """
    Ações de crescimento (alto ROE)
    Filtro: ROE > 20%
    """
    service = get_screener_service()
    return await service.get_growth_stocks(limit)


@router.get("/compare")
async def compare_stocks(tickers: str = Query(..., description="Tickers separados por vírgula")):
    """
    Compara múltiplas ações lado a lado
    Exemplo: /compare?tickers=PETR4,VALE3,ITUB4
    """
    ticker_list = [t.strip().upper() for t in tickers.split(',')]
    
    if len(ticker_list) < 2:
        raise HTTPException(status_code=400, detail="Forneça pelo menos 2 tickers para comparação")
    
    if len(ticker_list) > 10:
        raise HTTPException(status_code=400, detail="Máximo de 10 tickers por comparação")
    
    service = get_screener_service()
    return await service.compare_stocks(ticker_list)


@router.get("/sectors")
async def sector_analysis(sector: Optional[str] = Query(None)):
    """
    Análise por setor
    Retorna médias e destaques de cada setor
    """
    service = get_screener_service()
    return await service.get_sector_analysis(sector)


@router.get("/sectors/list")
async def list_sectors():
    """Lista todos os setores disponíveis"""
    service = get_screener_service()
    return {
        "sectors": list(service.SECTORS.items()),
        "total": len(service.SECTORS)
    }


@router.get("/presets")
async def get_presets():
    """
    Retorna filtros pré-configurados para diferentes estratégias
    """
    return {
        "presets": [
            {
                "id": "value",
                "name": "Value Investing",
                "description": "Ações subvalorizadas com bons fundamentos",
                "filters": {
                    "max_pl": 15,
                    "max_pvp": 2,
                    "min_roe": 0.12,
                    "min_dy": 0.03
                }
            },
            {
                "id": "dividends",
                "name": "Dividendos",
                "description": "Foco em renda passiva",
                "filters": {
                    "min_dy": 0.05,
                    "max_pl": 12,
                    "min_roe": 0.08
                }
            },
            {
                "id": "growth",
                "name": "Crescimento",
                "description": "Empresas com alto potencial de crescimento",
                "filters": {
                    "min_roe": 0.20,
                    "min_market_cap": 10000000000
                }
            },
            {
                "id": "quality",
                "name": "Qualidade",
                "description": "Empresas sólidas e bem administradas",
                "filters": {
                    "min_roe": 0.15,
                    "max_divida_ebitda": 2.5,
                    "min_market_cap": 5000000000
                }
            },
            {
                "id": "small_caps",
                "name": "Small Caps Value",
                "description": "Pequenas empresas subvalorizadas",
                "filters": {
                    "max_pl": 10,
                    "max_pvp": 1.5,
                    "max_market_cap": 5000000000
                }
            },
            {
                "id": "blue_chips",
                "name": "Blue Chips",
                "description": "Grandes empresas consolidadas",
                "filters": {
                    "min_market_cap": 50000000000,
                    "min_dy": 0.02
                }
            }
        ]
    }
