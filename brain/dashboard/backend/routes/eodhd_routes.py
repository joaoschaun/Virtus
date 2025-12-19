"""
VIRTUS Dashboard - EODHD Routes
================================

API endpoints para dados financeiros do EODHD.
Fornece acesso a market data, calendário econômico, notícias e análises.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import sys
import os

# Adiciona o path do brain
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

router = APIRouter(prefix="/eodhd", tags=["EODHD Financial Data"])


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class MarketQuote(BaseModel):
    """Cotação de mercado"""
    symbol: str
    price: float
    change: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[float] = None
    timestamp: Optional[str] = None


class EconomicEvent(BaseModel):
    """Evento econômico"""
    date: str
    event: str
    country: str
    actual: Optional[str] = None
    previous: Optional[str] = None
    estimate: Optional[str] = None
    impact: Optional[str] = None


class NewsArticle(BaseModel):
    """Artigo de notícia"""
    title: str
    date: str
    content: Optional[str] = None
    link: Optional[str] = None
    symbols: Optional[List[str]] = None
    sentiment: Optional[float] = None


class TechnicalIndicator(BaseModel):
    """Indicador técnico"""
    name: str
    value: float
    signal: Optional[str] = None
    timestamp: Optional[str] = None


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

# API Key EODHD
EODHD_API_KEY = os.getenv("EODHD_API_KEY", "")

# Provider singleton
_eodhd_provider = None


async def get_provider():
    """Obtém instância do provider EODHD"""
    global _eodhd_provider
    
    if _eodhd_provider is None:
        try:
            from src.brain.providers import EODHDProvider
            _eodhd_provider = EODHDProvider(api_key=EODHD_API_KEY)
        except ImportError:
            # Fallback: importa diretamente
            import aiohttp
            
            class SimpleEODHDProvider:
                """Provider simplificado para o dashboard"""
                def __init__(self, api_key: str):
                    self.api_key = api_key
                    self.base_url = "https://eodhd.com/api"
                
                async def _fetch(self, endpoint: str, params: dict = None):
                    params = params or {}
                    params['api_token'] = self.api_key
                    params['fmt'] = 'json'
                    
                    async with aiohttp.ClientSession() as session:
                        url = f"{self.base_url}{endpoint}"
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                return await response.json()
                            return None
                
                async def get_live_price(self, symbol: str):
                    return await self._fetch(f"/real-time/{symbol}")
                
                async def get_eod_data(self, symbol: str, from_date=None, to_date=None):
                    params = {}
                    if from_date:
                        params['from'] = from_date.strftime('%Y-%m-%d')
                    if to_date:
                        params['to'] = to_date.strftime('%Y-%m-%d')
                    return await self._fetch(f"/eod/{symbol}", params)
                
                async def get_intraday(self, symbol: str, interval: str = "5m"):
                    return await self._fetch(f"/intraday/{symbol}", {'interval': interval})
                
                async def get_news(self, symbols: List[str] = None, limit: int = 50):
                    params = {'limit': limit}
                    if symbols:
                        params['s'] = ','.join(symbols)
                    return await self._fetch("/news", params)
                
                async def get_economic_events(self, from_date=None, to_date=None, country=None):
                    params = {}
                    if from_date:
                        params['from'] = from_date.strftime('%Y-%m-%d')
                    if to_date:
                        params['to'] = to_date.strftime('%Y-%m-%d')
                    if country:
                        params['country'] = country
                    return await self._fetch("/economic-events", params)
                
                async def get_earnings(self, from_date=None, to_date=None):
                    params = {}
                    if from_date:
                        params['from'] = from_date.strftime('%Y-%m-%d')
                    if to_date:
                        params['to'] = to_date.strftime('%Y-%m-%d')
                    return await self._fetch("/calendar/earnings", params)
                
                async def get_technical(self, symbol: str, function: str, period: int = 14):
                    params = {'function': function, 'period': period}
                    return await self._fetch(f"/technical/{symbol}", params)
                
                async def get_fundamentals(self, symbol: str):
                    return await self._fetch(f"/fundamentals/{symbol}")
                
                async def get_macro(self, country: str, indicator: str = None):
                    params = {}
                    if indicator:
                        params['indicator'] = indicator
                    return await self._fetch(f"/macro-indicator/{country}", params)
                
                async def search(self, query: str):
                    return await self._fetch(f"/search/{query}")
            
            _eodhd_provider = SimpleEODHDProvider(EODHD_API_KEY)
    
    return _eodhd_provider


# ============================================================================
# MARKET DATA ENDPOINTS
# ============================================================================

@router.get("/market/overview")
async def get_market_overview():
    """
    Obtém visão geral do mercado.
    
    Retorna cotações de:
    - Forex (principais pares)
    - Índices
    - Criptomoedas
    - Commodities
    """
    provider = await get_provider()
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "forex": {},
        "indices": {},
        "crypto": {},
        "commodities": {}
    }
    
    # Forex
    forex_pairs = [
        ("EURUSD", "EURUSD.FOREX"),
        ("GBPUSD", "GBPUSD.FOREX"),
        ("USDJPY", "USDJPY.FOREX"),
        ("XAUUSD", "XAUUSD.FOREX"),
        ("XAGUSD", "XAGUSD.FOREX"),
    ]
    
    for name, symbol in forex_pairs:
        try:
            data = await provider.get_live_price(symbol)
            if data:
                result["forex"][name] = data
        except Exception as e:
            pass
    
    # Índices
    indices = [
        ("S&P 500", "GSPC.INDX"),
        ("Dow Jones", "DJI.INDX"),
        ("NASDAQ", "IXIC.INDX"),
        ("VIX", "VIX.INDX"),
    ]
    
    for name, symbol in indices:
        try:
            data = await provider.get_live_price(symbol)
            if data:
                result["indices"][name] = data
        except Exception as e:
            pass
    
    # Crypto
    cryptos = [
        ("Bitcoin", "BTC-USD.CC"),
        ("Ethereum", "ETH-USD.CC"),
    ]
    
    for name, symbol in cryptos:
        try:
            data = await provider.get_live_price(symbol)
            if data:
                result["crypto"][name] = data
        except Exception as e:
            pass
    
    return result


@router.get("/market/quote/{symbol}")
async def get_quote(
    symbol: str,
    exchange: str = Query("FOREX", description="Exchange (FOREX, US, CC, INDX)")
):
    """
    Obtém cotação de um símbolo específico.
    
    Args:
        symbol: Símbolo (ex: EURUSD, AAPL, BTC-USD)
        exchange: Exchange (FOREX, US, CC, INDX)
    """
    provider = await get_provider()
    
    full_symbol = f"{symbol}.{exchange}"
    
    try:
        data = await provider.get_live_price(full_symbol)
        if data:
            return {
                "symbol": symbol,
                "exchange": exchange,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/historical/{symbol}")
async def get_historical(
    symbol: str,
    exchange: str = Query("FOREX", description="Exchange"),
    days: int = Query(30, description="Dias de histórico"),
    interval: str = Query("daily", description="Intervalo: daily, intraday")
):
    """
    Obtém dados históricos de um símbolo.
    """
    provider = await get_provider()
    
    full_symbol = f"{symbol}.{exchange}"
    from_date = datetime.now() - timedelta(days=days)
    
    try:
        if interval == "intraday":
            data = await provider.get_intraday(full_symbol)
        else:
            data = await provider.get_eod_data(full_symbol, from_date)
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "interval": interval,
            "data": data or [],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ECONOMIC CALENDAR ENDPOINTS
# ============================================================================

@router.get("/calendar/events")
async def get_economic_events(
    country: Optional[str] = Query(None, description="Código do país (US, GB, EU)"),
    days: int = Query(7, description="Dias à frente")
):
    """
    Obtém eventos do calendário econômico.
    """
    provider = await get_provider()
    
    from_date = datetime.now()
    to_date = from_date + timedelta(days=days)
    
    try:
        events = await provider.get_economic_events(from_date, to_date, country)
        
        return {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "country": country or "all",
            "events": events or [],
            "count": len(events) if events else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/earnings")
async def get_earnings_calendar(
    days: int = Query(7, description="Dias à frente")
):
    """
    Obtém calendário de earnings.
    """
    provider = await get_provider()
    
    from_date = datetime.now()
    to_date = from_date + timedelta(days=days)
    
    try:
        earnings = await provider.get_earnings(from_date, to_date)
        
        return {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "earnings": earnings or [],
            "count": len(earnings) if earnings else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/today")
async def get_today_events():
    """
    Obtém todos os eventos de hoje.
    """
    provider = await get_provider()
    
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    
    result = {
        "date": today.strftime("%Y-%m-%d"),
        "economic_events": [],
        "earnings": []
    }
    
    try:
        events = await provider.get_economic_events(today, tomorrow)
        result["economic_events"] = events or []
    except:
        pass
    
    try:
        earnings = await provider.get_earnings(today, tomorrow)
        result["earnings"] = earnings or []
    except:
        pass
    
    return result


# ============================================================================
# NEWS & SENTIMENT ENDPOINTS
# ============================================================================

@router.get("/news")
async def get_news(
    symbols: Optional[str] = Query(None, description="Símbolos separados por vírgula"),
    topic: Optional[str] = Query(None, description="Tópico/tag"),
    limit: int = Query(20, description="Limite de notícias")
):
    """
    Obtém notícias financeiras.
    """
    provider = await get_provider()
    
    symbol_list = symbols.split(",") if symbols else None
    
    try:
        news = await provider.get_news(symbol_list, limit)
        
        return {
            "symbols": symbol_list,
            "topic": topic,
            "news": news or [],
            "count": len(news) if news else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/forex")
async def get_forex_news(limit: int = Query(20)):
    """Obtém notícias de Forex"""
    provider = await get_provider()
    
    forex_symbols = ["EURUSD.FOREX", "GBPUSD.FOREX", "XAUUSD.FOREX"]
    
    try:
        news = await provider.get_news(forex_symbols, limit)
        return {
            "category": "forex",
            "news": news or [],
            "count": len(news) if news else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/crypto")
async def get_crypto_news(limit: int = Query(20)):
    """Obtém notícias de Crypto"""
    provider = await get_provider()
    
    crypto_symbols = ["BTC-USD.CC", "ETH-USD.CC"]
    
    try:
        news = await provider.get_news(crypto_symbols, limit)
        return {
            "category": "crypto",
            "news": news or [],
            "count": len(news) if news else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TECHNICAL ANALYSIS ENDPOINTS
# ============================================================================

@router.get("/technical/{symbol}")
async def get_technical_indicators(
    symbol: str,
    exchange: str = Query("FOREX"),
    indicators: str = Query("sma,ema,rsi,macd", description="Indicadores separados por vírgula"),
    period: int = Query(14, description="Período")
):
    """
    Obtém indicadores técnicos de um símbolo.
    
    Indicadores disponíveis:
    - sma, ema, wma (médias móveis)
    - rsi (momentum)
    - macd (tendência/momentum)
    - bbands (volatilidade)
    - stoch (oscilador)
    - atr (volatilidade)
    - adx (força da tendência)
    """
    provider = await get_provider()
    
    full_symbol = f"{symbol}.{exchange}"
    indicator_list = indicators.split(",")
    
    result = {
        "symbol": symbol,
        "exchange": exchange,
        "period": period,
        "indicators": {},
        "timestamp": datetime.now().isoformat()
    }
    
    for indicator in indicator_list:
        indicator = indicator.strip().lower()
        try:
            data = await provider.get_technical(full_symbol, indicator, period)
            result["indicators"][indicator] = data
        except Exception as e:
            result["indicators"][indicator] = {"error": str(e)}
    
    return result


@router.get("/technical/analysis/{symbol}")
async def get_full_analysis(
    symbol: str,
    exchange: str = Query("FOREX")
):
    """
    Obtém análise técnica completa de um símbolo.
    """
    provider = await get_provider()
    
    full_symbol = f"{symbol}.{exchange}"
    
    analysis = {
        "symbol": symbol,
        "exchange": exchange,
        "timestamp": datetime.now().isoformat(),
        "trend": {},
        "momentum": {},
        "volatility": {},
        "summary": {
            "signal": "NEUTRAL",
            "strength": 0
        }
    }
    
    # Tendência
    try:
        analysis["trend"]["sma_20"] = await provider.get_technical(full_symbol, "sma", 20)
        analysis["trend"]["sma_50"] = await provider.get_technical(full_symbol, "sma", 50)
        analysis["trend"]["ema_20"] = await provider.get_technical(full_symbol, "ema", 20)
    except:
        pass
    
    # Momentum
    try:
        analysis["momentum"]["rsi"] = await provider.get_technical(full_symbol, "rsi", 14)
        analysis["momentum"]["macd"] = await provider.get_technical(full_symbol, "macd", 12)
    except:
        pass
    
    # Volatilidade
    try:
        analysis["volatility"]["bbands"] = await provider.get_technical(full_symbol, "bbands", 20)
        analysis["volatility"]["atr"] = await provider.get_technical(full_symbol, "atr", 14)
    except:
        pass
    
    # Calcula resumo
    signals = []
    
    # RSI signal
    if analysis["momentum"].get("rsi"):
        rsi_data = analysis["momentum"]["rsi"]
        if isinstance(rsi_data, list) and len(rsi_data) > 0:
            rsi_value = rsi_data[-1].get("rsi", 50) if isinstance(rsi_data[-1], dict) else 50
            if rsi_value < 30:
                signals.append(("BUY", 0.7))
            elif rsi_value > 70:
                signals.append(("SELL", 0.7))
            else:
                signals.append(("NEUTRAL", 0.3))
    
    if signals:
        buy_signals = sum(1 for s, _ in signals if s == "BUY")
        sell_signals = sum(1 for s, _ in signals if s == "SELL")
        
        if buy_signals > sell_signals:
            analysis["summary"]["signal"] = "BUY"
            analysis["summary"]["strength"] = buy_signals / len(signals)
        elif sell_signals > buy_signals:
            analysis["summary"]["signal"] = "SELL"
            analysis["summary"]["strength"] = sell_signals / len(signals)
    
    return analysis


# ============================================================================
# FUNDAMENTAL DATA ENDPOINTS
# ============================================================================

@router.get("/fundamentals/{symbol}")
async def get_fundamentals(
    symbol: str,
    exchange: str = Query("US", description="Exchange")
):
    """
    Obtém dados fundamentalistas de uma ação.
    """
    provider = await get_provider()
    
    full_symbol = f"{symbol}.{exchange}"
    
    try:
        data = await provider.get_fundamentals(full_symbol)
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MACRO DATA ENDPOINTS
# ============================================================================

@router.get("/macro/{country}")
async def get_macro_data(
    country: str,
    indicator: Optional[str] = Query(None, description="Indicador específico")
):
    """
    Obtém dados macroeconômicos de um país.
    
    Indicadores disponíveis:
    - gdp_growth_annual
    - inflation_consumer_prices_annual
    - unemployment_rate
    - real_interest_rate
    - government_debt_to_gdp
    """
    provider = await get_provider()
    
    try:
        data = await provider.get_macro(country.upper(), indicator)
        
        return {
            "country": country.upper(),
            "indicator": indicator,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/overview")
async def get_macro_overview():
    """
    Obtém visão geral macroeconômica dos principais países.
    """
    provider = await get_provider()
    
    countries = ["USA", "GBR", "EUR", "JPN", "BRA"]
    indicators = ["gdp_growth_annual", "inflation_consumer_prices_annual", "unemployment_rate"]
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "countries": {}
    }
    
    for country in countries:
        result["countries"][country] = {}
        for indicator in indicators:
            try:
                data = await provider.get_macro(country, indicator)
                result["countries"][country][indicator] = data
            except:
                result["countries"][country][indicator] = None
    
    return result


# ============================================================================
# SEARCH ENDPOINT
# ============================================================================

@router.get("/search")
async def search_symbols(
    query: str = Query(..., description="Termo de busca")
):
    """
    Busca símbolos por nome ou código.
    """
    provider = await get_provider()
    
    try:
        results = await provider.search(query)
        
        return {
            "query": query,
            "results": results or [],
            "count": len(results) if results else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """
    Verifica saúde da conexão com EODHD.
    """
    provider = await get_provider()
    
    try:
        # Tenta fazer uma requisição simples (news é gratuito)
        data = await provider.get_news(limit=1)
        
        return {
            "status": "healthy" if data else "degraded",
            "provider": "eodhd",
            "api_key_configured": bool(EODHD_API_KEY),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "provider": "eodhd",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
