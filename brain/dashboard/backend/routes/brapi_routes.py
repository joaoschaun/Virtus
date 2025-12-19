"""
VIRTUS Trading System - Rotas da API Brapi
Endpoints para acesso aos dados do mercado brasileiro via Brapi.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

from services.brapi_service import brapi_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brapi", tags=["Brapi - Mercado Brasileiro"])


# ==================== AÇÕES ====================

@router.get("/quote/{tickers}")
async def get_quote(
    tickers: str,
    range: Optional[str] = Query(None, description="Período: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"),
    interval: Optional[str] = Query(None, description="Intervalo: 1m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo"),
    fundamental: bool = Query(False, description="Incluir dados fundamentalistas"),
    dividends: bool = Query(False, description="Incluir histórico de dividendos"),
    modules: Optional[str] = Query(None, description="Módulos adicionais separados por vírgula")
):
    """
    Obtém cotação detalhada de ações, FIIs, ETFs, BDRs.
    
    Exemplos:
    - /quote/PETR4
    - /quote/PETR4,VALE3?fundamental=true&dividends=true
    - /quote/ITUB4?range=1mo&interval=1d
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        module_list = [m.strip() for m in modules.split(",")] if modules else None
        
        result = await brapi_service.get_quote(
            tickers=ticker_list,
            range=range,
            interval=interval,
            fundamental=fundamental,
            dividends=dividends,
            modules=module_list
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar cotação: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks")
async def list_stocks(
    search: Optional[str] = Query(None, description="Buscar por nome ou ticker"),
    sort_by: str = Query("close", description="Ordenar por: close, volume, market_cap, change"),
    sort_order: str = Query("desc", description="Direção: asc, desc"),
    limit: int = Query(50, ge=1, le=500, description="Quantidade máxima")
):
    """
    Lista todas as ações disponíveis na B3.
    
    Exemplos:
    - /stocks?limit=20
    - /stocks?search=petro
    - /stocks?sort_by=volume&sort_order=desc
    """
    try:
        result = await brapi_service.get_stock_list(
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao listar ações: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fundamentals/{ticker}")
async def get_fundamentals(
    ticker: str,
    modules: Optional[str] = Query(None, description="Módulos específicos separados por vírgula")
):
    """
    Obtém dados fundamentalistas completos de uma ação.
    
    Módulos disponíveis:
    - summaryProfile: Perfil da empresa
    - balanceSheetHistory: Balanço Patrimonial Anual
    - balanceSheetHistoryQuarterly: Balanço Patrimonial Trimestral
    - incomeStatementHistory: DRE Anual
    - incomeStatementHistoryQuarterly: DRE Trimestral
    - financialData: Dados financeiros (TTM)
    - cashflowHistory: Fluxo de Caixa Anual
    - defaultKeyStatistics: Estatísticas principais
    """
    try:
        module_list = [m.strip() for m in modules.split(",")] if modules else None
        result = await brapi_service.get_fundamentals(
            ticker=ticker.upper(),
            modules=module_list
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar fundamentalistas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dividends/{ticker}")
async def get_dividends(ticker: str):
    """
    Obtém histórico de dividendos de uma ação.
    
    Retorna:
    - cashDividends: Dividendos em dinheiro e JCP
    - stockDividends: Desdobramentos e grupamentos
    - priceEarnings: P/L
    - earningsPerShare: LPA
    """
    try:
        result = await brapi_service.get_dividends(ticker.upper())
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar dividendos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/{ticker}")
async def get_historical(
    ticker: str,
    range: str = Query("1y", description="Período: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"),
    interval: str = Query("1d", description="Intervalo: 1m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo")
):
    """
    Obtém dados históricos de preço de uma ação.
    
    Exemplos:
    - /historical/PETR4?range=1mo&interval=1d
    - /historical/VALE3?range=1y&interval=1wk
    """
    try:
        result = await brapi_service.get_historical_data(
            ticker=ticker.upper(),
            range=range,
            interval=interval
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SCREENER ====================

@router.get("/screener/top-gainers")
async def get_top_gainers(limit: int = Query(10, ge=1, le=50)):
    """Obtém as ações com maior alta do dia."""
    try:
        result = await brapi_service.get_top_gainers(limit)
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar maiores altas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/top-losers")
async def get_top_losers(limit: int = Query(10, ge=1, le=50)):
    """Obtém as ações com maior queda do dia."""
    try:
        result = await brapi_service.get_top_losers(limit)
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar maiores quedas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/most-traded")
async def get_most_traded(limit: int = Query(10, ge=1, le=50)):
    """Obtém as ações mais negociadas do dia."""
    try:
        result = await brapi_service.get_most_traded(limit)
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar mais negociadas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FIIs ====================

@router.get("/fiis/quote/{tickers}")
async def get_fii_quote(
    tickers: str,
    dividends: bool = Query(True, description="Incluir dados de rendimentos")
):
    """
    Obtém cotação de FIIs (Fundos Imobiliários).
    
    Exemplos:
    - /fiis/quote/HGLG11
    - /fiis/quote/HGLG11,MXRF11,XPLG11
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        result = await brapi_service.get_fii_quote(ticker_list, dividends)
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar FIIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fiis/search")
async def search_fiis(
    search: Optional[str] = Query(None, description="Buscar por nome ou ticker"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Busca FIIs disponíveis.
    
    Retorna apenas ativos que terminam com '11' (padrão de FIIs).
    """
    try:
        result = await brapi_service.search_fiis(search, limit)
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar FIIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CRIPTOMOEDAS ====================

@router.get("/crypto/quote")
async def get_crypto_quote(
    coins: str = Query(..., description="Siglas separadas por vírgula: BTC,ETH,ADA"),
    currency: str = Query("BRL", description="Moeda de referência: BRL, USD"),
    range: Optional[str] = Query(None, description="Período histórico"),
    interval: Optional[str] = Query(None, description="Intervalo dos dados")
):
    """
    Obtém cotação de criptomoedas.
    
    Exemplos:
    - /crypto/quote?coins=BTC,ETH&currency=BRL
    - /crypto/quote?coins=BTC&range=1mo&interval=1d
    """
    try:
        coin_list = [c.strip().upper() for c in coins.split(",")]
        result = await brapi_service.get_crypto_quote(
            coins=coin_list,
            currency=currency,
            range=range,
            interval=interval
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar criptomoedas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crypto/available")
async def list_available_cryptos():
    """Lista todas as criptomoedas disponíveis."""
    try:
        result = await brapi_service.list_available_cryptos()
        return result
    except Exception as e:
        logger.error(f"Erro ao listar criptomoedas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MOEDAS/CÂMBIO ====================

@router.get("/currency/quote")
async def get_currency_quote(
    pairs: str = Query(..., description="Pares separados por vírgula: USD-BRL,EUR-BRL")
):
    """
    Obtém cotação de pares de moedas.
    
    Exemplos:
    - /currency/quote?pairs=USD-BRL
    - /currency/quote?pairs=USD-BRL,EUR-BRL,GBP-BRL
    """
    try:
        pair_list = [p.strip().upper() for p in pairs.split(",")]
        result = await brapi_service.get_currency_quote(pair_list)
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar moedas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/currency/available")
async def list_available_currencies():
    """Lista todos os pares de moedas disponíveis."""
    try:
        result = await brapi_service.list_available_currencies()
        return result
    except Exception as e:
        logger.error(f"Erro ao listar moedas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== INFLAÇÃO ====================

@router.get("/inflation")
async def get_inflation(
    country: str = Query("brazil", description="País"),
    historical: bool = Query(False, description="Incluir dados históricos"),
    start: Optional[str] = Query(None, description="Data inicial (DD/MM/YYYY)"),
    end: Optional[str] = Query(None, description="Data final (DD/MM/YYYY)"),
    sort_by: str = Query("date", description="Ordenar por: date, value"),
    sort_order: str = Query("desc", description="Direção: asc, desc")
):
    """
    Obtém dados de inflação (IPCA).
    
    Exemplos:
    - /inflation?historical=true
    - /inflation?start=01/01/2023&end=31/12/2023
    """
    try:
        result = await brapi_service.get_inflation(
            country=country,
            historical=historical,
            start=start,
            end=end,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar inflação: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inflation/countries")
async def list_inflation_countries():
    """Lista países com dados de inflação disponíveis."""
    try:
        result = await brapi_service.list_inflation_countries()
        return result
    except Exception as e:
        logger.error(f"Erro ao listar países: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TAXA SELIC ====================

@router.get("/selic")
async def get_selic(
    country: str = Query("brazil", description="País"),
    historical: bool = Query(False, description="Incluir dados históricos"),
    start: Optional[str] = Query(None, description="Data inicial (DD/MM/YYYY)"),
    end: Optional[str] = Query(None, description="Data final (DD/MM/YYYY)"),
    sort_by: str = Query("date", description="Ordenar por: date, value"),
    sort_order: str = Query("desc", description="Direção: asc, desc")
):
    """
    Obtém dados da taxa SELIC.
    
    Exemplos:
    - /selic?historical=true
    - /selic?start=01/01/2023&end=31/12/2023
    """
    try:
        result = await brapi_service.get_prime_rate(
            country=country,
            historical=historical,
            start=start,
            end=end,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar SELIC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selic/countries")
async def list_selic_countries():
    """Lista países com dados de taxa de juros disponíveis."""
    try:
        result = await brapi_service.list_prime_rate_countries()
        return result
    except Exception as e:
        logger.error(f"Erro ao listar países: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ÍNDICES ====================

@router.get("/index/{symbol}")
async def get_index_quote(
    symbol: str = "^BVSP"
):
    """
    Obtém cotação de índices.
    
    Símbolos comuns:
    - ^BVSP: Ibovespa
    - ^IFIX: Índice de FIIs
    """
    try:
        result = await brapi_service.get_index_quote(symbol)
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar índice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ibovespa")
async def get_ibovespa():
    """Obtém cotação atual do Ibovespa."""
    try:
        result = await brapi_service.get_ibovespa()
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar Ibovespa: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ifix")
async def get_ifix():
    """Obtém cotação atual do IFIX."""
    try:
        result = await brapi_service.get_ifix()
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar IFIX: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RESUMO DO MERCADO ====================

@router.get("/market-summary")
async def get_market_summary():
    """
    Obtém resumo geral do mercado brasileiro.
    
    Inclui:
    - Ibovespa
    - Principais moedas (USD, EUR)
    - Principais criptomoedas (BTC, ETH)
    - Inflação atual
    - Taxa SELIC
    - Top 5 maiores altas
    - Top 5 maiores quedas
    """
    try:
        result = await brapi_service.get_market_summary()
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar resumo do mercado: {e}")
        raise HTTPException(status_code=500, detail=str(e))
