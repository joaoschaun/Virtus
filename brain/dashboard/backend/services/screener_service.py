"""
Screener Inteligente de Ações B3
Sistema de filtro avançado com ranking por múltiplos indicadores
"""
import httpx
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio


class ScreenerService:
    """Serviço de Screener Inteligente para Ações B3"""
    
    BASE_URL = "https://brapi.dev/api"
    API_KEY = os.getenv("BRAPI_API_KEY", "")
    
    # Pesos para cálculo do Score Value Investing
    VALUE_WEIGHTS = {
        'pl': 0.20,           # P/L - menor é melhor
        'pvp': 0.15,          # P/VP - menor é melhor
        'roe': 0.20,          # ROE - maior é melhor
        'dy': 0.20,           # Dividend Yield - maior é melhor
        'divida_ebitda': 0.15, # Dívida/EBITDA - menor é melhor
        'margem_liquida': 0.10 # Margem Líquida - maior é melhor
    }
    
    # Benchmarks para scoring (valores medianos do mercado)
    BENCHMARKS = {
        'pl': {'ideal': 10, 'max': 25},
        'pvp': {'ideal': 1.0, 'max': 3.0},
        'roe': {'ideal': 15, 'min': 5},
        'dy': {'ideal': 6, 'min': 2},
        'divida_ebitda': {'ideal': 2.0, 'max': 4.0},
        'margem_liquida': {'ideal': 15, 'min': 5}
    }
    
    # Setores para classificação
    SECTORS = {
        'Finance': 'Financeiro',
        'Utilities': 'Utilidades',
        'Energy Minerals': 'Energia',
        'Non-Energy Minerals': 'Mineração',
        'Retail Trade': 'Varejo',
        'Consumer Services': 'Serviços',
        'Health Services': 'Saúde',
        'Technology Services': 'Tecnologia',
        'Transportation': 'Transporte',
        'Communications': 'Comunicações',
        'Process Industries': 'Indústria',
        'Producer Manufacturing': 'Manufatura',
        'Consumer Non-Durables': 'Consumo',
        'Consumer Durables': 'Bens Duráveis',
        'Commercial Services': 'Serviços Comerciais',
        'Distribution Services': 'Distribuição',
        'Electronic Technology': 'Eletrônicos',
        'Health Technology': 'Saúde Tech',
        'Industrial Services': 'Serviços Industriais',
        'Miscellaneous': 'Outros'
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 300  # 5 minutos
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Faz requisição à API Brapi"""
        if params is None:
            params = {}
        params['token'] = self.API_KEY
        
        # Check cache
        cache_key = f"{endpoint}_{str(params)}"
        if cache_key in self._cache:
            if datetime.now().timestamp() - self._cache_time.get(cache_key, 0) < self._cache_ttl:
                return self._cache[cache_key]
        
        url = f"{self.BASE_URL}/{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Update cache
        self._cache[cache_key] = data
        self._cache_time[cache_key] = datetime.now().timestamp()
        
        return data
    
    def _calculate_score_component(self, value: float, metric: str, higher_is_better: bool) -> float:
        """Calcula pontuação de um componente (0-100)"""
        if value is None:
            return 50  # Valor neutro se não disponível
        
        benchmark = self.BENCHMARKS.get(metric, {})
        
        if higher_is_better:
            ideal = benchmark.get('ideal', 10)
            min_val = benchmark.get('min', 0)
            if value >= ideal:
                return 100
            elif value <= min_val:
                return 0
            else:
                return ((value - min_val) / (ideal - min_val)) * 100
        else:
            ideal = benchmark.get('ideal', 10)
            max_val = benchmark.get('max', 30)
            if value <= ideal:
                return 100
            elif value >= max_val:
                return 0
            else:
                return ((max_val - value) / (max_val - ideal)) * 100
    
    def _calculate_value_score(self, stock_data: Dict) -> Dict:
        """Calcula o Score de Value Investing (0-100)"""
        scores = {}
        
        # P/L Score (menor é melhor)
        pl = stock_data.get('priceEarnings') or stock_data.get('pl')
        if pl and pl > 0:
            scores['pl'] = self._calculate_score_component(pl, 'pl', False)
        else:
            scores['pl'] = 0
        
        # P/VP Score (menor é melhor)
        pvp = stock_data.get('priceToBook') or stock_data.get('pvp')
        if pvp and pvp > 0:
            scores['pvp'] = self._calculate_score_component(pvp, 'pvp', False)
        else:
            scores['pvp'] = 50
        
        # ROE Score (maior é melhor)
        roe = stock_data.get('returnOnEquity') or stock_data.get('roe')
        if roe:
            roe_pct = roe * 100 if roe < 1 else roe
            scores['roe'] = self._calculate_score_component(roe_pct, 'roe', True)
        else:
            scores['roe'] = 50
        
        # Dividend Yield Score (maior é melhor)
        dy = stock_data.get('dividendYield') or stock_data.get('dy')
        if dy:
            dy_pct = dy * 100 if dy < 1 else dy
            scores['dy'] = self._calculate_score_component(dy_pct, 'dy', True)
        else:
            scores['dy'] = 50
        
        # Dívida/EBITDA Score (menor é melhor)
        divida_ebitda = stock_data.get('debtToEbitda') or stock_data.get('divida_ebitda')
        if divida_ebitda is not None:
            scores['divida_ebitda'] = self._calculate_score_component(divida_ebitda, 'divida_ebitda', False)
        else:
            scores['divida_ebitda'] = 50
        
        # Margem Líquida Score (maior é melhor)
        margem = stock_data.get('profitMargin') or stock_data.get('margem_liquida')
        if margem:
            margem_pct = margem * 100 if margem < 1 else margem
            scores['margem_liquida'] = self._calculate_score_component(margem_pct, 'margem_liquida', True)
        else:
            scores['margem_liquida'] = 50
        
        # Calcula score final ponderado
        total_score = sum(
            scores[metric] * weight 
            for metric, weight in self.VALUE_WEIGHTS.items()
        )
        
        return {
            'total': round(total_score, 1),
            'components': {k: round(v, 1) for k, v in scores.items()},
            'grade': self._get_grade(total_score)
        }
    
    def _get_grade(self, score: float) -> str:
        """Converte score numérico em nota"""
        if score >= 80:
            return 'A'
        elif score >= 65:
            return 'B'
        elif score >= 50:
            return 'C'
        elif score >= 35:
            return 'D'
        else:
            return 'F'
    
    async def get_stocks_list(self, 
                              sector: str = None,
                              stock_type: str = 'stock',
                              sort_by: str = 'volume',
                              sort_order: str = 'desc',
                              limit: int = 50) -> Dict:
        """Lista ações com filtros básicos"""
        params = {
            'sortBy': sort_by,
            'sortOrder': sort_order,
            'limit': limit
        }
        
        if sector:
            params['sector'] = sector
        if stock_type:
            params['type'] = stock_type
        
        data = await self._make_request('quote/list', params)
        
        stocks = data.get('stocks', [])
        
        # Traduz setores
        for stock in stocks:
            eng_sector = stock.get('sector', '')
            stock['sector_pt'] = self.SECTORS.get(eng_sector, eng_sector)
        
        return {
            'stocks': stocks,
            'total': len(stocks),
            'sectors': list(self.SECTORS.values())
        }
    
    async def get_stock_fundamentals(self, ticker: str) -> Dict:
        """Obtém dados fundamentalistas de uma ação"""
        # Módulos de fundamentals
        modules = [
            'summaryProfile',
            'financialData',
            'defaultKeyStatistics'
        ]
        
        params = {
            'modules': ','.join(modules),
            'fundamental': 'true',
            'dividends': 'true'
        }
        
        data = await self._make_request(f'quote/{ticker}', params)
        
        if not data.get('results'):
            return None
        
        result = data['results'][0]
        
        # Extrai dados dos sub-objetos de módulos
        financial_data = result.get('financialData', {})
        key_stats = result.get('defaultKeyStatistics', {})
        summary_profile = result.get('summaryProfile', {})
        
        # Setor - pode vir de summaryProfile ou do resultado principal
        sector = summary_profile.get('sector') or result.get('sector', 'N/A')
        
        # Extrai dados fundamentalistas de todos os módulos
        fundamentals = {
            'ticker': ticker,
            'name': result.get('longName', result.get('shortName', ticker)),
            'sector': sector,
            'sector_pt': self.SECTORS.get(sector, 'Outros'),
            'price': result.get('regularMarketPrice', 0),
            'change': result.get('regularMarketChangePercent', 0),
            'marketCap': result.get('marketCap', 0),
            'logo': result.get('logourl', ''),
            
            # Indicadores fundamentalistas - prioriza módulos específicos
            'pl': result.get('priceEarnings'),
            'pvp': key_stats.get('priceToBook') or result.get('priceToBook'),
            'roe': financial_data.get('returnOnEquity'),
            'roa': financial_data.get('returnOnAssets'),
            'dy': key_stats.get('dividendYield'),  # dividendYield vem de defaultKeyStatistics em %
            'divida_ebitda': financial_data.get('debtToEquity'),
            'margem_liquida': financial_data.get('profitMargins'),
            'margem_bruta': financial_data.get('grossMargins'),
            'margem_operacional': financial_data.get('operatingMargins'),
            'lpa': result.get('earningsPerShare'),
            'vpa': key_stats.get('bookValue'),
            'ebitda': financial_data.get('ebitda'),
            'receita': financial_data.get('totalRevenue'),
            'lucro_liquido': financial_data.get('freeCashflow'),
            
            # Dados de mercado
            'volume': result.get('regularMarketVolume', 0),
            'high52w': result.get('fiftyTwoWeekHigh', 0),
            'low52w': result.get('fiftyTwoWeekLow', 0),
        }
        
        # Converte DY de percentual para decimal se necessário
        if fundamentals['dy'] and fundamentals['dy'] > 1:
            fundamentals['dy'] = fundamentals['dy'] / 100
        
        # Calcula score
        fundamentals['value_score'] = self._calculate_value_score(fundamentals)
        
        return fundamentals
    
    async def screener(self,
                       min_pl: float = None,
                       max_pl: float = None,
                       min_pvp: float = None,
                       max_pvp: float = None,
                       min_roe: float = None,
                       min_dy: float = None,
                       max_divida_ebitda: float = None,
                       sector: str = None,
                       min_market_cap: float = None,
                       sort_by: str = 'value_score',
                       limit: int = 30) -> Dict:
        """
        Screener avançado com múltiplos filtros
        Retorna ações que atendem aos critérios com score
        """
        # Primeiro, pega lista de ações
        stocks_data = await self.get_stocks_list(
            sector=sector,
            stock_type='stock',
            sort_by='volume',
            limit=200  # Pega mais para filtrar
        )
        
        stocks = stocks_data.get('stocks', [])
        filtered_results = []
        
        # Para cada ação, busca fundamentals e aplica filtros
        # Usa semáforo para limitar requisições paralelas
        semaphore = asyncio.Semaphore(5)
        
        async def process_stock(stock):
            async with semaphore:
                try:
                    ticker = stock.get('stock', '')
                    if not ticker or not ticker.endswith(('3', '4', '11')):
                        return None
                    
                    fundamentals = await self.get_stock_fundamentals(ticker)
                    if not fundamentals:
                        return None
                    
                    # Aplica filtros
                    if min_pl and (fundamentals.get('pl') is None or fundamentals.get('pl') < min_pl):
                        return None
                    if max_pl and fundamentals.get('pl') and fundamentals.get('pl') > max_pl:
                        return None
                    if min_pvp and (fundamentals.get('pvp') is None or fundamentals.get('pvp') < min_pvp):
                        return None
                    if max_pvp and fundamentals.get('pvp') and fundamentals.get('pvp') > max_pvp:
                        return None
                    if min_roe and (fundamentals.get('roe') is None or fundamentals.get('roe') < min_roe):
                        return None
                    if min_dy and (fundamentals.get('dy') is None or fundamentals.get('dy') < min_dy):
                        return None
                    if max_divida_ebitda and fundamentals.get('divida_ebitda') and fundamentals.get('divida_ebitda') > max_divida_ebitda:
                        return None
                    if min_market_cap and fundamentals.get('marketCap', 0) < min_market_cap:
                        return None
                    
                    return fundamentals
                    
                except Exception as e:
                    print(f"Erro ao processar {stock.get('stock')}: {e}")
                    return None
        
        # Processa em paralelo (limitado pelo semáforo)
        tasks = [process_stock(stock) for stock in stocks[:100]]  # Limita a 100
        results = await asyncio.gather(*tasks)
        
        # Remove None e ordena
        filtered_results = [r for r in results if r is not None]
        
        # Ordena pelo critério
        if sort_by == 'value_score':
            filtered_results.sort(key=lambda x: x.get('value_score', {}).get('total', 0), reverse=True)
        elif sort_by == 'dy':
            filtered_results.sort(key=lambda x: x.get('dy') or 0, reverse=True)
        elif sort_by == 'pl':
            filtered_results.sort(key=lambda x: x.get('pl') or 999)
        elif sort_by == 'pvp':
            filtered_results.sort(key=lambda x: x.get('pvp') or 999)
        elif sort_by == 'roe':
            filtered_results.sort(key=lambda x: x.get('roe') or 0, reverse=True)
        
        return {
            'results': filtered_results[:limit],
            'total': len(filtered_results),
            'filters_applied': {
                'min_pl': min_pl,
                'max_pl': max_pl,
                'min_pvp': min_pvp,
                'max_pvp': max_pvp,
                'min_roe': min_roe,
                'min_dy': min_dy,
                'max_divida_ebitda': max_divida_ebitda,
                'sector': sector,
                'min_market_cap': min_market_cap
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_top_value_stocks(self, limit: int = 20) -> Dict:
        """Retorna as melhores ações pelo score Value Investing"""
        return await self.screener(
            max_pl=20,
            max_pvp=3,
            min_roe=0.10,
            sort_by='value_score',
            limit=limit
        )
    
    async def get_top_dividend_stocks(self, limit: int = 20) -> Dict:
        """Retorna ações com maiores Dividend Yields"""
        return await self.screener(
            min_dy=0.04,
            max_pl=15,
            sort_by='dy',
            limit=limit
        )
    
    async def get_growth_stocks(self, limit: int = 20) -> Dict:
        """Retorna ações de crescimento (alto ROE)"""
        return await self.screener(
            min_roe=0.20,
            sort_by='roe',
            limit=limit
        )
    
    async def compare_stocks(self, tickers: List[str]) -> Dict:
        """Compara múltiplas ações lado a lado"""
        results = []
        
        for ticker in tickers[:10]:  # Limita a 10
            fundamentals = await self.get_stock_fundamentals(ticker)
            if fundamentals:
                results.append(fundamentals)
        
        # Ranking por cada métrica
        rankings = {}
        metrics = ['pl', 'pvp', 'roe', 'dy', 'value_score']
        
        for metric in metrics:
            if metric == 'value_score':
                sorted_stocks = sorted(results, key=lambda x: x.get('value_score', {}).get('total', 0), reverse=True)
            elif metric in ['pl', 'pvp']:
                sorted_stocks = sorted(results, key=lambda x: x.get(metric) or 999)
            else:
                sorted_stocks = sorted(results, key=lambda x: x.get(metric) or 0, reverse=True)
            
            rankings[metric] = [s['ticker'] for s in sorted_stocks]
        
        return {
            'stocks': results,
            'rankings': rankings,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_sector_analysis(self, sector: str = None) -> Dict:
        """Análise por setor - médias e destaques"""
        stocks_data = await self.get_stocks_list(
            sector=sector,
            limit=100
        )
        
        stocks = stocks_data.get('stocks', [])
        
        # Agrupa por setor
        sector_data = {}
        
        for stock in stocks:
            s = stock.get('sector', 'Outros')
            if s not in sector_data:
                sector_data[s] = {
                    'stocks': [],
                    'total_market_cap': 0,
                    'avg_change': 0
                }
            sector_data[s]['stocks'].append(stock)
            sector_data[s]['total_market_cap'] += stock.get('market_cap') or 0
        
        # Calcula médias
        for s, data in sector_data.items():
            if data['stocks']:
                changes = [st.get('change', 0) for st in data['stocks'] if st.get('change')]
                data['avg_change'] = sum(changes) / len(changes) if changes else 0
                data['count'] = len(data['stocks'])
                data['sector_pt'] = self.SECTORS.get(s, s)
                # Remove lista de stocks para reduzir payload
                data['top_stocks'] = [st['stock'] for st in data['stocks'][:5]]
                del data['stocks']
        
        return {
            'sectors': sector_data,
            'timestamp': datetime.now().isoformat()
        }
    
    async def close(self):
        """Fecha o cliente HTTP"""
        await self.client.aclose()


# Singleton
_screener_service = None

def get_screener_service() -> ScreenerService:
    global _screener_service
    if _screener_service is None:
        _screener_service = ScreenerService()
    return _screener_service
