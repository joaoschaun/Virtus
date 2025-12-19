"""
Rotas da Carteira de FIIs
"""
from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, List
from pydantic import BaseModel
from services.fii_portfolio_service import get_fii_portfolio_service

router = APIRouter(prefix="/fii-portfolio", tags=["FII Portfolio"])


class PositionCreate(BaseModel):
    ticker: str
    quantity: int
    avg_price: float
    category: str = "outros"


class PositionUpdate(BaseModel):
    quantity: Optional[int] = None
    avg_price: Optional[float] = None
    category: Optional[str] = None


@router.get("/fiis")
async def list_all_fiis(
    sort_by: str = Query("volume", description="Ordenar por: volume, dy, change"),
    limit: int = Query(50, ge=1, le=200)
):
    """Lista todos os FIIs disponíveis"""
    service = get_fii_portfolio_service()
    return await service.get_all_fiis(sort_by=sort_by, limit=limit)


@router.get("/quote/{ticker}")
async def get_fii_quote(ticker: str):
    """Obtém cotação de um FII"""
    service = get_fii_portfolio_service()
    result = await service.get_fii_quote(ticker.upper())
    
    if not result:
        raise HTTPException(status_code=404, detail=f"FII {ticker} não encontrado")
    
    return result


@router.get("/dividends/{ticker}")
async def get_fii_dividends(
    ticker: str,
    limit: int = Query(12, ge=1, le=24)
):
    """Obtém histórico de dividendos de um FII"""
    service = get_fii_portfolio_service()
    result = await service.get_fii_dividends(ticker.upper(), limit)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"FII {ticker} não encontrado")
    
    return result


@router.get("/portfolio")
async def get_portfolio(user_id: str = Query("default")):
    """
    Obtém carteira completa com cotações atualizadas
    Inclui: posições, resumo, renda mensal, ganhos/perdas
    """
    service = get_fii_portfolio_service()
    return await service.get_portfolio(user_id)


@router.post("/portfolio/add")
async def add_position(
    position: PositionCreate,
    user_id: str = Query("default")
):
    """
    Adiciona posição à carteira
    Se já existir, atualiza preço médio
    """
    service = get_fii_portfolio_service()
    return await service.add_position(
        ticker=position.ticker.upper(),
        quantity=position.quantity,
        avg_price=position.avg_price,
        category=position.category,
        user_id=user_id
    )


@router.put("/portfolio/{ticker}")
async def update_position(
    ticker: str,
    position: PositionUpdate,
    user_id: str = Query("default")
):
    """Atualiza posição existente"""
    service = get_fii_portfolio_service()
    return await service.update_position(
        ticker=ticker.upper(),
        quantity=position.quantity,
        avg_price=position.avg_price,
        category=position.category,
        user_id=user_id
    )


@router.delete("/portfolio/{ticker}")
async def remove_position(
    ticker: str,
    user_id: str = Query("default")
):
    """Remove posição da carteira"""
    service = get_fii_portfolio_service()
    return await service.remove_position(ticker.upper(), user_id)


@router.get("/calculator")
async def income_calculator(
    target_monthly: float = Query(..., description="Renda mensal desejada em R$"),
    avg_dy: float = Query(8.0, description="DY médio esperado (%)")
):
    """
    Calculadora de renda passiva
    Quanto preciso investir para atingir X de renda mensal?
    """
    service = get_fii_portfolio_service()
    return await service.calculate_income(target_monthly, avg_dy)


@router.get("/calendar")
async def payment_calendar(user_id: str = Query("default")):
    """
    Agenda de pagamentos de dividendos
    Baseado na carteira do usuário
    """
    service = get_fii_portfolio_service()
    return await service.get_payment_calendar(user_id)


@router.get("/suggestions")
async def get_suggestions(
    category: Optional[str] = Query(None, description="Categoria: logistica, shoppings, lajes, papel"),
    min_dy: float = Query(6.0, description="DY mínimo (%)"),
    max_pvp: float = Query(1.1, description="P/VP máximo")
):
    """
    Sugere FIIs baseado em critérios
    Retorna FIIs com bom DY e P/VP favorável
    """
    service = get_fii_portfolio_service()
    return await service.get_suggestions(
        category=category,
        min_dy=min_dy,
        max_pvp=max_pvp
    )


@router.get("/categories")
async def list_categories():
    """Lista categorias de FIIs"""
    service = get_fii_portfolio_service()
    return {
        "categories": service.FII_CATEGORIES,
        "popular_fiis": service.POPULAR_FIIS
    }


@router.get("/simulate")
async def simulate_portfolio(
    tickers: str = Query(..., description="Tickers separados por vírgula"),
    investment: float = Query(10000, description="Valor total a investir")
):
    """
    Simula carteira com valor igual em cada FII
    Retorna renda esperada
    """
    ticker_list = [t.strip().upper() for t in tickers.split(',')]
    
    if len(ticker_list) < 1:
        raise HTTPException(status_code=400, detail="Forneça pelo menos 1 ticker")
    
    if len(ticker_list) > 20:
        raise HTTPException(status_code=400, detail="Máximo de 20 tickers")
    
    service = get_fii_portfolio_service()
    
    # Valor por FII
    per_fii = investment / len(ticker_list)
    
    positions = []
    total_monthly = 0
    
    for ticker in ticker_list:
        try:
            quote = await service.get_fii_quote(ticker)
            dividends = await service.get_fii_dividends(ticker)
            
            if quote and dividends:
                quantity = int(per_fii / quote['price'])
                monthly = quantity * dividends.get('avg_monthly', 0)
                invested = quantity * quote['price']
                
                positions.append({
                    'ticker': ticker,
                    'price': quote['price'],
                    'quantity': quantity,
                    'invested': round(invested, 2),
                    'monthly_income': round(monthly, 2),
                    'dy_12m': dividends.get('dy_12m', 0)
                })
                total_monthly += monthly
        except:
            continue
    
    total_invested = sum(p['invested'] for p in positions)
    
    return {
        'positions': positions,
        'summary': {
            'total_invested': round(total_invested, 2),
            'monthly_income': round(total_monthly, 2),
            'yearly_income': round(total_monthly * 12, 2),
            'effective_dy': round((total_monthly * 12 / total_invested * 100), 2) if total_invested > 0 else 0
        },
        'input': {
            'investment': investment,
            'tickers': ticker_list
        }
    }
