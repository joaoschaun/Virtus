"""
VIRTUS Trading System - Brapi API Service
Integração completa com a API Brapi para dados do mercado brasileiro.

Recursos disponíveis:
- Ações (cotações, histórico, dividendos, fundamentalistas)
- FIIs (Fundos Imobiliários)
- Criptomoedas
- Moedas/Câmbio
- Inflação (IPCA, IGP-M)
- Taxa SELIC

API Key: Premium Plan
"""

import httpx
import asyncio
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class BrapiService:
    """Serviço completo para integração com a API Brapi."""
    
    BASE_URL = "https://brapi.dev/api"
    API_KEY = os.getenv("BRAPI_API_KEY", "")  # Premium Plan
    
    # Módulos disponíveis para dados fundamentalistas
    AVAILABLE_MODULES = [
        "summaryProfile",           # Perfil da empresa
        "balanceSheetHistory",      # Balanço Patrimonial Anual
        "balanceSheetHistoryQuarterly",  # Balanço Patrimonial Trimestral
        "defaultKeyStatistics",     # Estatísticas principais (TTM)
        "defaultKeyStatisticsHistory",
        "defaultKeyStatisticsHistoryQuarterly",
        "incomeStatementHistory",   # DRE Anual
        "incomeStatementHistoryQuarterly",  # DRE Trimestral
        "financialData",            # Dados financeiros (TTM)
        "financialDataHistory",
        "financialDataHistoryQuarterly",
        "valueAddedHistory",        # DVA Anual
        "valueAddedHistoryQuarterly",
        "cashflowHistory",          # DFC Anual
        "cashflowHistoryQuarterly"  # DFC Trimestral
    ]
    
    # Ranges disponíveis para histórico
    VALID_RANGES = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    
    # Intervalos disponíveis
    VALID_INTERVALS = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
    
    def __init__(self, api_key: Optional[str] = None):
        """Inicializa o serviço Brapi."""
        self.api_key = api_key or self.API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    async def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Faz uma requisição à API Brapi."""
        url = f"{self.BASE_URL}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro HTTP Brapi: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Erro na API Brapi: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Erro na requisição Brapi: {str(e)}")
                raise
    
    # ==================== AÇÕES E FUNDOS ====================
    
    async def get_quote(
        self,
        tickers: List[str],
        range: Optional[str] = None,
        interval: Optional[str] = None,
        fundamental: bool = False,
        dividends: bool = False,
        modules: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Obtém cotação detalhada de ações, FIIs, ETFs, BDRs.
        
        Args:
            tickers: Lista de símbolos (ex: ['PETR4', 'VALE3'])
            range: Período histórico (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Intervalo dos dados (1m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo)
            fundamental: Incluir dados fundamentalistas básicos
            dividends: Incluir histórico de dividendos
            modules: Módulos adicionais de dados financeiros
        
        Returns:
            Dados da cotação com todos os campos solicitados
        """
        params = {}
        
        if range:
            params["range"] = range
        if interval:
            params["interval"] = interval
        if fundamental:
            params["fundamental"] = "true"
        if dividends:
            params["dividends"] = "true"
        if modules:
            params["modules"] = ",".join(modules)
        
        ticker_str = ",".join(tickers)
        return await self._make_request(f"/quote/{ticker_str}", params)
    
    async def get_stock_list(
        self,
        search: Optional[str] = None,
        sort_by: str = "close",
        sort_order: str = "desc",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Lista todas as ações disponíveis na B3.
        
        Args:
            search: Termo de busca (nome ou ticker)
            sort_by: Campo para ordenação (close, volume, market_cap, etc)
            sort_order: Direção (asc, desc)
            limit: Quantidade máxima de resultados
        
        Returns:
            Lista de ações com cotações básicas
        """
        params = {
            "sortBy": sort_by,
            "sortOrder": sort_order,
            "limit": limit
        }
        
        if search:
            params["search"] = search
            
        return await self._make_request("/quote/list", params)
    
    async def get_fundamentals(
        self,
        ticker: str,
        modules: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Obtém dados fundamentalistas completos de uma ação.
        
        Args:
            ticker: Símbolo da ação
            modules: Lista de módulos (se None, retorna todos)
        
        Returns:
            Dados fundamentalistas completos
        """
        if modules is None:
            modules = self.AVAILABLE_MODULES
            
        return await self.get_quote(
            tickers=[ticker],
            modules=modules,
            fundamental=True,
            dividends=True
        )
    
    async def get_dividends(
        self,
        ticker: str
    ) -> Dict[str, Any]:
        """
        Obtém histórico de dividendos de uma ação.
        
        Args:
            ticker: Símbolo da ação
        
        Returns:
            Histórico de dividendos e JCP
        """
        result = await self.get_quote(
            tickers=[ticker],
            dividends=True
        )
        
        if result.get("results") and len(result["results"]) > 0:
            return {
                "symbol": ticker,
                "dividendsData": result["results"][0].get("dividendsData", {}),
                "priceEarnings": result["results"][0].get("priceEarnings"),
                "earningsPerShare": result["results"][0].get("earningsPerShare")
            }
        return {"symbol": ticker, "dividendsData": {}}
    
    async def get_historical_data(
        self,
        ticker: str,
        range: str = "1y",
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """
        Obtém dados históricos de preço de uma ação.
        
        Args:
            ticker: Símbolo da ação
            range: Período (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Intervalo (1m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo)
        
        Returns:
            Série histórica de preços
        """
        result = await self.get_quote(
            tickers=[ticker],
            range=range,
            interval=interval
        )
        
        if result.get("results") and len(result["results"]) > 0:
            return {
                "symbol": ticker,
                "historicalDataPrice": result["results"][0].get("historicalDataPrice", []),
                "validRanges": result["results"][0].get("validRanges", []),
                "validIntervals": result["results"][0].get("validIntervals", [])
            }
        return {"symbol": ticker, "historicalDataPrice": []}
    
    # ==================== CRIPTOMOEDAS ====================
    
    async def get_crypto_quote(
        self,
        coins: List[str],
        currency: str = "BRL",
        range: Optional[str] = None,
        interval: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtém cotação de criptomoedas.
        
        Args:
            coins: Lista de siglas (BTC, ETH, ADA, SOL, etc)
            currency: Moeda de referência (BRL, USD)
            range: Período histórico
            interval: Intervalo dos dados
        
        Returns:
            Cotações das criptomoedas
        """
        params = {
            "coin": ",".join(coins),
            "currency": currency
        }
        
        if range:
            params["range"] = range
        if interval:
            params["interval"] = interval
            
        return await self._make_request("/v2/crypto", params)
    
    async def list_available_cryptos(self) -> Dict[str, Any]:
        """
        Lista todas as criptomoedas disponíveis.
        
        Returns:
            Lista de criptomoedas suportadas
        """
        return await self._make_request("/v2/crypto/available")
    
    # ==================== MOEDAS/CÂMBIO ====================
    
    async def get_currency_quote(
        self,
        pairs: List[str]
    ) -> Dict[str, Any]:
        """
        Obtém cotação de pares de moedas.
        
        Args:
            pairs: Lista de pares (ex: ['USD-BRL', 'EUR-BRL', 'BTC-BRL'])
        
        Returns:
            Cotações dos pares de moedas
        """
        params = {
            "currency": ",".join(pairs)
        }
        
        return await self._make_request("/v2/currency", params)
    
    async def list_available_currencies(self) -> Dict[str, Any]:
        """
        Lista todos os pares de moedas disponíveis.
        
        Returns:
            Lista de pares de moedas suportados
        """
        return await self._make_request("/v2/currency/available")
    
    # ==================== INFLAÇÃO ====================
    
    async def get_inflation(
        self,
        country: str = "brazil",
        historical: bool = True,  # Brapi API requer historical=true
        start: Optional[str] = None,
        end: Optional[str] = None,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Obtém dados de inflação (IPCA).
        
        Args:
            country: País (brazil)
            historical: Incluir dados históricos (Brapi requer True)
            start: Data inicial (DD/MM/YYYY)
            end: Data final (DD/MM/YYYY)
            sort_by: Campo de ordenação (date, value)
            sort_order: Direção (asc, desc)
        
        Returns:
            Dados de inflação
        """
        # Brapi API só funciona com historical=true
        params = {
            "country": country,
            "historical": "true",  # Sempre true - API Brapi não suporta false
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        if start:
            params["start"] = start
        if end:
            params["end"] = end
            
        return await self._make_request("/v2/inflation", params)
    
    async def list_inflation_countries(self) -> Dict[str, Any]:
        """
        Lista países com dados de inflação disponíveis.
        
        Returns:
            Lista de países
        """
        return await self._make_request("/v2/inflation/available")
    
    # ==================== TAXA SELIC ====================
    
    async def get_prime_rate(
        self,
        country: str = "brazil",
        historical: bool = False,  # Opcional - sem historical retorna apenas última taxa
        start: Optional[str] = None,
        end: Optional[str] = None,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Obtém dados da taxa SELIC.
        
        Args:
            country: País (brazil)
            historical: Incluir dados históricos
            start: Data inicial (DD/MM/YYYY)
            end: Data final (DD/MM/YYYY)
            sort_by: Campo de ordenação (date, value)
            sort_order: Direção (asc, desc)
        
        Returns:
            Dados da taxa SELIC
        """
        params = {
            "country": country,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        # Só enviar historical se for True
        if historical:
            params["historical"] = "true"
        
        if start:
            params["start"] = start
        if end:
            params["end"] = end
            
        return await self._make_request("/v2/prime-rate", params)
    
    async def list_prime_rate_countries(self) -> Dict[str, Any]:
        """
        Lista países com dados de taxa de juros disponíveis.
        
        Returns:
            Lista de países
        """
        return await self._make_request("/v2/prime-rate/available")
    
    # ==================== FIIs (FUNDOS IMOBILIÁRIOS) ====================
    
    async def get_fii_quote(
        self,
        tickers: List[str],
        dividends: bool = True
    ) -> Dict[str, Any]:
        """
        Obtém cotação de FIIs (Fundos Imobiliários).
        
        Args:
            tickers: Lista de símbolos de FIIs (ex: ['HGLG11', 'MXRF11'])
            dividends: Incluir dados de dividendos
        
        Returns:
            Cotações dos FIIs com dados de rendimentos
        """
        return await self.get_quote(
            tickers=tickers,
            dividends=dividends,
            fundamental=True
        )
    
    async def search_fiis(
        self,
        search: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Busca FIIs disponíveis.
        
        Args:
            search: Termo de busca
            limit: Quantidade máxima
        
        Returns:
            Lista de FIIs
        """
        # FIIs terminam com 11
        result = await self.get_stock_list(search=search, limit=limit)
        
        if result.get("stocks"):
            fiis = [
                stock for stock in result["stocks"]
                if stock.get("stock", "").endswith("11")
            ]
            return {"fiis": fiis, "count": len(fiis)}
        
        return {"fiis": [], "count": 0}
    
    # ==================== SCREENER / FILTROS ====================
    
    async def get_top_gainers(self, limit: int = 10) -> Dict[str, Any]:
        """Obtém as ações com maior alta do dia."""
        result = await self.get_stock_list(
            sort_by="change",
            sort_order="desc",
            limit=limit
        )
        return result
    
    async def get_top_losers(self, limit: int = 10) -> Dict[str, Any]:
        """Obtém as ações com maior queda do dia."""
        result = await self.get_stock_list(
            sort_by="change",
            sort_order="asc",
            limit=limit
        )
        return result
    
    async def get_most_traded(self, limit: int = 10) -> Dict[str, Any]:
        """Obtém as ações mais negociadas do dia."""
        result = await self.get_stock_list(
            sort_by="volume",
            sort_order="desc",
            limit=limit
        )
        return result
    
    async def get_highest_dividend_yield(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém ações com maior dividend yield.
        Nota: Requer busca individual para cada ação.
        """
        # Popular tickers com alto DY conhecido
        high_dy_tickers = [
            "PETR4", "VALE3", "BBAS3", "TAEE11", "CSMG3",
            "BBSE3", "TRPL4", "ITSA4", "CMIG4", "CPLE6"
        ]
        
        results = []
        for ticker in high_dy_tickers[:limit]:
            try:
                data = await self.get_quote(
                    tickers=[ticker],
                    fundamental=True,
                    dividends=True
                )
                if data.get("results"):
                    results.append(data["results"][0])
            except Exception as e:
                logger.warning(f"Erro ao buscar {ticker}: {e}")
                
        return results
    
    # ==================== ÍNDICES ====================
    
    async def get_index_quote(
        self,
        index: str = "^BVSP"
    ) -> Dict[str, Any]:
        """
        Obtém cotação de índices (Ibovespa, etc).
        
        Args:
            index: Símbolo do índice (^BVSP para Ibovespa)
        
        Returns:
            Cotação do índice
        """
        return await self.get_quote(tickers=[index])
    
    async def get_ibovespa(self) -> Dict[str, Any]:
        """Obtém cotação atual do Ibovespa."""
        return await self.get_index_quote("^BVSP")
    
    async def get_ifix(self) -> Dict[str, Any]:
        """Obtém cotação atual do IFIX (índice de FIIs)."""
        return await self.get_index_quote("^IFIX")
    
    # ==================== DASHBOARD / RESUMO ====================
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """
        Obtém resumo geral do mercado.
        
        Returns:
            Dados consolidados do mercado brasileiro
        """
        try:
            # Buscar dados em paralelo
            ibov_task = self.get_ibovespa()
            currency_task = self.get_currency_quote(["USD-BRL", "EUR-BRL"])
            crypto_task = self.get_crypto_quote(["BTC", "ETH"], "BRL")
            # Inflação requer historical=True
            inflation_task = self.get_inflation(historical=True)
            # SELIC pode usar historical=False
            selic_task = self.get_prime_rate(historical=False)
            top_gainers_task = self.get_top_gainers(5)
            top_losers_task = self.get_top_losers(5)
            
            results = await asyncio.gather(
                ibov_task,
                currency_task,
                crypto_task,
                inflation_task,
                selic_task,
                top_gainers_task,
                top_losers_task,
                return_exceptions=True
            )
            
            # Mapear topGainers e topLosers para formato esperado pelo frontend
            def map_stocks(data):
                if isinstance(data, Exception) or not data:
                    return None
                stocks = data.get('stocks', [])
                mapped = []
                for s in stocks:
                    mapped.append({
                        'symbol': s.get('stock'),
                        'shortName': s.get('name'),
                        'regularMarketPrice': s.get('close', 0),
                        'regularMarketChangePercent': s.get('change', 0),
                        'regularMarketVolume': s.get('volume', 0),
                        'marketCap': s.get('market_cap'),
                        'logourl': s.get('logo'),
                    })
                return {'stocks': mapped}
            
            return {
                "ibovespa": results[0] if not isinstance(results[0], Exception) else None,
                "currencies": results[1] if not isinstance(results[1], Exception) else None,
                "crypto": results[2] if not isinstance(results[2], Exception) else None,
                "inflation": results[3] if not isinstance(results[3], Exception) else None,
                "selic": results[4] if not isinstance(results[4], Exception) else None,
                "topGainers": map_stocks(results[5]),
                "topLosers": map_stocks(results[6]),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Erro ao obter resumo do mercado: {e}")
            return {"error": str(e)}


# Instância global do serviço
brapi_service = BrapiService()


# Funções de conveniência
async def get_quote(tickers: List[str], **kwargs) -> Dict[str, Any]:
    """Wrapper para obter cotação."""
    return await brapi_service.get_quote(tickers, **kwargs)

async def get_stock_list(**kwargs) -> Dict[str, Any]:
    """Wrapper para listar ações."""
    return await brapi_service.get_stock_list(**kwargs)

async def get_crypto_quote(coins: List[str], **kwargs) -> Dict[str, Any]:
    """Wrapper para obter cotação de criptomoedas."""
    return await brapi_service.get_crypto_quote(coins, **kwargs)

async def get_currency_quote(pairs: List[str]) -> Dict[str, Any]:
    """Wrapper para obter cotação de moedas."""
    return await brapi_service.get_currency_quote(pairs)

async def get_market_summary() -> Dict[str, Any]:
    """Wrapper para obter resumo do mercado."""
    return await brapi_service.get_market_summary()
