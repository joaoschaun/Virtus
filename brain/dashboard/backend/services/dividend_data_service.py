"""
VIRTUS - Serviço de Dados de Dividendos B3
===========================================

Combina múltiplas fontes de dados:
1. Yahoo Finance (yfinance) - Cotações e dividendos históricos
2. Brapi.dev - API REST brasileira (requer API key)
3. StatusInvest - Web scraping (fallback)

Cache inteligente para reduzir requisições.
"""

import os
import json
import asyncio
import aiohttp
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

# Tentativa de imports opcionais
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None

logger = logging.getLogger(__name__)

# Paths
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
DATA_PATH = BRAIN_PATH / "data"
DIVIDEND_CACHE_PATH = DATA_PATH / "dividend_cache"
DIVIDEND_CACHE_PATH.mkdir(parents=True, exist_ok=True)


class DataSource(str, Enum):
    """Fonte de dados."""
    YAHOO = "yahoo"
    BRAPI = "brapi"
    STATUS_INVEST = "statusinvest"
    CACHE = "cache"
    MOCK = "mock"


@dataclass
class DividendData:
    """Dados de um dividendo."""
    ticker: str
    company_name: str
    dividend_type: str  # dividend, jcp, bonus
    value_per_share: float
    ex_date: str
    payment_date: Optional[str]
    record_date: Optional[str]
    dividend_yield: float
    source: str


@dataclass
class StockFundamentals:
    """Dados fundamentalistas de uma ação."""
    ticker: str
    company_name: str
    sector: str
    current_price: float
    
    # Dividendos
    annual_dividend: float
    dividend_yield: float
    payout_ratio: float
    dividend_consistency: float  # 0-100
    
    # Valuation
    pe_ratio: float
    pb_ratio: float
    ev_ebitda: float
    
    # Profitability
    roe: float
    roa: float
    net_margin: float
    
    # Financial Health
    debt_to_equity: float
    current_ratio: float
    
    # Market
    market_cap: float
    avg_volume: float
    volatility_30d: float
    
    # Price ranges
    price_52w_high: float
    price_52w_low: float
    
    # Metadata
    last_update: str
    source: str


@dataclass
class UpcomingDividend:
    """Dividendo próximo."""
    ticker: str
    company_name: str
    sector: str
    current_price: float
    dividend_type: str
    value_per_share: float
    ex_date: str
    payment_date: Optional[str]
    dividend_yield: float
    days_to_ex: int
    annual_yield: float
    recommendation: str  # buy, wait, avoid
    score: float


class DividendDataService:
    """
    Serviço unificado de dados de dividendos.
    
    Combina Yahoo Finance, Brapi e StatusInvest com cache inteligente.
    """
    
    # Brapi API Key (Premium Plan)
    BRAPI_API_KEY = os.getenv("BRAPI_API_KEY", "")
    
    def __init__(self):
        self.brapi_key = self.BRAPI_API_KEY
        self.cache_ttl = 3600  # 1 hora
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Cache em memória
        self._price_cache: Dict[str, Tuple[float, datetime]] = {}
        self._dividend_cache: Dict[str, Tuple[List[Dict], datetime]] = {}
        self._fundamentals_cache: Dict[str, Tuple[Dict, datetime]] = {}
        
        # Setores B3 (mapeamento básico)
        self.sectors = {
            "PETR": "Petróleo e Gás",
            "VALE": "Mineração",
            "ITUB": "Bancos",
            "BBDC": "Bancos",
            "BBAS": "Bancos",
            "ABEV": "Bebidas",
            "WEGE": "Bens Industriais",
            "RENT": "Aluguel de Carros",
            "TAEE": "Energia Elétrica",
            "TRPL": "Energia Elétrica",
            "EGIE": "Energia Elétrica",
            "CPLE": "Energia Elétrica",
            "ENGI": "Energia Elétrica",
            "BBSE": "Seguros",
            "VIVT": "Telecomunicações",
            "RADL": "Varejo Farmacêutico",
            "MGLU": "Varejo",
            "LREN": "Varejo",
            "SUZB": "Papel e Celulose",
            "KLBN": "Papel e Celulose",
            "JBSS": "Alimentos",
            "BRFS": "Alimentos",
            "CSAN": "Combustíveis",
            "UGPA": "Combustíveis",
            "HYPE": "Farmacêutico",
            "FLRY": "Saúde",
            "HAPV": "Saúde",
            "CYRE": "Construção",
            "MRVE": "Construção",
            "EZTC": "Construção",
            "B3SA": "Serviços Financeiros",
            "TOTS": "Tecnologia",
            "LWSA": "Tecnologia",
            "PRIO": "Petróleo e Gás",
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna sessão HTTP."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "VIRTUS-DividendBot/1.0"}
            )
        return self._session
    
    async def close(self):
        """Fecha sessão HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _get_sector(self, ticker: str) -> str:
        """Retorna setor da ação."""
        base = ticker[:4].upper()
        return self.sectors.get(base, "Outros")
    
    def _load_cache(self, cache_type: str, key: str) -> Optional[Dict]:
        """Carrega dados do cache em disco."""
        cache_file = DIVIDEND_CACHE_PATH / f"{cache_type}_{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Verifica TTL
                    cached_at = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
                    if (datetime.now() - cached_at).total_seconds() < self.cache_ttl:
                        return data.get('data')
            except:
                pass
        return None
    
    def _save_cache(self, cache_type: str, key: str, data: Any):
        """Salva dados no cache em disco."""
        cache_file = DIVIDEND_CACHE_PATH / f"{cache_type}_{key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'cached_at': datetime.now().isoformat(),
                    'data': data
                }, f, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")
    
    # ==================== YAHOO FINANCE ====================
    
    async def _get_yahoo_data(self, ticker: str) -> Optional[Dict]:
        """Busca dados do Yahoo Finance."""
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            # Yahoo usa .SA para B3
            yahoo_ticker = f"{ticker}.SA"
            stock = yf.Ticker(yahoo_ticker)
            
            info = stock.info
            if not info or 'regularMarketPrice' not in info:
                return None
            
            # Histórico de dividendos - ordena do mais recente para o mais antigo
            dividends = stock.dividends
            dividend_history = []
            if dividends is not None and len(dividends) > 0:
                # Reverte para ter os mais recentes primeiro
                for date_idx, value in reversed(list(dividends.tail(12).items())):
                    dividend_history.append({
                        'date': date_idx.strftime('%Y-%m-%d'),
                        'value': float(value)
                    })
            
            return {
                'ticker': ticker,
                'company_name': info.get('longName', info.get('shortName', ticker)),
                'current_price': info.get('regularMarketPrice', 0),
                'previous_close': info.get('previousClose', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0) or 0,
                'pb_ratio': info.get('priceToBook', 0) or 0,
                'dividend_yield': (info.get('dividendYield', 0) or 0) * 100,
                'dividend_rate': info.get('dividendRate', 0) or 0,
                'payout_ratio': (info.get('payoutRatio', 0) or 0) * 100,
                'roe': (info.get('returnOnEquity', 0) or 0) * 100,
                'debt_to_equity': info.get('debtToEquity', 0) or 0,
                'avg_volume': info.get('averageVolume', 0) or 0,
                '52w_high': info.get('fiftyTwoWeekHigh', 0) or 0,
                '52w_low': info.get('fiftyTwoWeekLow', 0) or 0,
                'dividend_history': dividend_history,
                'source': DataSource.YAHOO.value
            }
        except Exception as e:
            logger.warning(f"Yahoo Finance error for {ticker}: {e}")
            return None
    
    # ==================== BRAPI ====================
    
    async def _get_brapi_quote(self, ticker: str) -> Optional[Dict]:
        """Busca cotação da Brapi."""
        if not self.brapi_key:
            return None
        
        try:
            session = await self._get_session()
            url = f"https://brapi.dev/api/quote/{ticker}"
            params = {"token": self.brapi_key}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('results'):
                        result = data['results'][0]
                        return {
                            'ticker': ticker,
                            'company_name': result.get('longName', ticker),
                            'current_price': result.get('regularMarketPrice', 0),
                            'previous_close': result.get('regularMarketPreviousClose', 0),
                            'market_cap': result.get('marketCap', 0),
                            'pe_ratio': result.get('priceEarnings', 0) or 0,
                            'dividend_yield': result.get('dividendYield', 0) or 0,
                            'avg_volume': result.get('averageDailyVolume3Month', 0) or 0,
                            '52w_high': result.get('fiftyTwoWeekHigh', 0) or 0,
                            '52w_low': result.get('fiftyTwoWeekLow', 0) or 0,
                            'source': DataSource.BRAPI.value
                        }
        except Exception as e:
            logger.warning(f"Brapi error for {ticker}: {e}")
        return None
    
    async def _get_brapi_dividends(self, ticker: str) -> Optional[List[Dict]]:
        """Busca dividendos da Brapi."""
        if not self.brapi_key:
            return None
        
        try:
            session = await self._get_session()
            url = f"https://brapi.dev/api/quote/{ticker}"
            params = {"token": self.brapi_key, "dividends": "true"}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('results'):
                        result = data['results'][0]
                        dividends = result.get('dividendsData', {}).get('cashDividends', [])
                        return [{
                            'date': d.get('exDividendDate', ''),
                            'payment_date': d.get('paymentDate', ''),
                            'value': d.get('rate', 0),
                            'type': d.get('dividendType', 'DIVIDEND')
                        } for d in dividends[:12]]
        except Exception as e:
            logger.warning(f"Brapi dividends error for {ticker}: {e}")
        return None
    
    # ==================== STATUS INVEST (Scraping) ====================
    
    async def _get_statusinvest_data(self, ticker: str) -> Optional[Dict]:
        """Busca dados do StatusInvest via scraping."""
        if not BS4_AVAILABLE:
            return None
        
        try:
            session = await self._get_session()
            url = f"https://statusinvest.com.br/acoes/{ticker.lower()}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    def get_value(title: str) -> float:
                        try:
                            elem = soup.find('span', {'title': title})
                            if elem:
                                parent = elem.find_parent('div', class_='info')
                                if parent:
                                    value_elem = parent.find('strong', class_='value')
                                    if value_elem:
                                        text = value_elem.text.strip()
                                        text = text.replace('.', '').replace(',', '.').replace('%', '').replace('R$', '').strip()
                                        return float(text) if text and text != '-' else 0
                        except:
                            pass
                        return 0
                    
                    # Busca nome da empresa
                    company_name = ticker
                    title_elem = soup.find('h1', class_='lh-4')
                    if title_elem:
                        company_name = title_elem.text.strip()
                    
                    return {
                        'ticker': ticker,
                        'company_name': company_name,
                        'current_price': get_value('Valor atual do ativo'),
                        'dividend_yield': get_value('Dividend Yield com base nos últimos 12 meses'),
                        'pe_ratio': get_value('Preço da ação dividido pelo lucro'),
                        'pb_ratio': get_value('Preço da ação dividido pelo valor patrimonial'),
                        'roe': get_value('Retorno sobre o patrimônio líquido'),
                        'payout_ratio': get_value('Dividendos distribuídos em relação ao lucro'),
                        'debt_to_equity': get_value('Dívida líquida / Patrimônio'),
                        'source': DataSource.STATUS_INVEST.value
                    }
        except Exception as e:
            logger.warning(f"StatusInvest error for {ticker}: {e}")
        return None
    
    # ==================== UNIFIED METHODS ====================
    
    async def get_stock_data(self, ticker: str) -> Dict:
        """
        Busca dados de uma ação de múltiplas fontes.
        Prioridade: Cache > Yahoo > Brapi > StatusInvest > Mock
        """
        ticker = ticker.upper().replace('.SA', '')
        
        # 1. Tenta cache
        cached = self._load_cache('stock', ticker)
        if cached:
            cached['source'] = DataSource.CACHE.value
            return cached
        
        data = None
        
        # 2. Tenta Yahoo Finance (mais completo)
        data = await self._get_yahoo_data(ticker)
        
        # 3. Fallback para Brapi
        if not data:
            data = await self._get_brapi_quote(ticker)
        
        # 4. Fallback para StatusInvest
        if not data:
            data = await self._get_statusinvest_data(ticker)
        
        # 5. Mock se nada funcionou
        if not data:
            data = self._get_mock_data(ticker)
        
        # Enriquece com setor
        data['sector'] = self._get_sector(ticker)
        data['last_update'] = datetime.now().isoformat()
        
        # Salva cache
        self._save_cache('stock', ticker, data)
        
        return data
    
    async def get_dividends(self, ticker: str, limit: int = 12) -> List[Dict]:
        """
        Busca histórico de dividendos.
        """
        ticker = ticker.upper().replace('.SA', '')
        
        # 1. Tenta cache
        cached = self._load_cache('dividends', ticker)
        if cached:
            # Valida cache - verifica se tem datas válidas
            valid_cached = [d for d in cached if d.get('date') and d['date'] not in ('', 'None', None)]
            if valid_cached:
                return valid_cached[:limit]
        
        dividends = None
        
        # 2. Tenta Yahoo PRIMEIRO (tem datas ex-dividendo corretas)
        yahoo_data = await self._get_yahoo_data(ticker)
        if yahoo_data:
            dividends = yahoo_data.get('dividend_history', [])
        
        # 3. Fallback Brapi (pode ter datas incompletas)
        if not dividends:
            dividends = await self._get_brapi_dividends(ticker)
            # Filtra registros sem data ex
            if dividends:
                dividends = [d for d in dividends if d.get('date') and d['date'] not in ('', 'None', None)]
        
        # 4. Mock
        if not dividends:
            dividends = self._get_mock_dividends(ticker)
        
        # Salva cache
        self._save_cache('dividends', ticker, dividends)
        
        return dividends[:limit]
    
    async def get_upcoming_dividends(self, days_ahead: int = 30, min_yield: float = 0) -> List[UpcomingDividend]:
        """
        Retorna dividendos próximos.
        
        Busca de fontes disponíveis ou usa dados conhecidos.
        """
        # Lista de ações conhecidas por bons dividendos
        dividend_stocks = [
            "TAEE11", "BBSE3", "TRPL4", "CPLE6", "EGIE3",
            "PETR4", "VALE3", "BBAS3", "ITUB4", "BBDC4",
            "VIVT3", "CMIG4", "CSAN3", "KLBN11", "SUZB3"
        ]
        
        upcoming = []
        today = date.today()
        
        def parse_date(date_str: str) -> Optional[date]:
            """Parse date from various formats."""
            if not date_str or date_str in ('', 'None', None):
                return None
            try:
                # Tenta formato YYYY-MM-DD
                return datetime.strptime(date_str[:10], '%Y-%m-%d').date()
            except:
                try:
                    # Tenta formato ISO completo
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                except:
                    return None
        
        for ticker in dividend_stocks:
            try:
                stock_data = await self.get_stock_data(ticker)
                dividends = await self.get_dividends(ticker)
                
                if not stock_data or not dividends:
                    continue
                
                # Estima próximo dividendo baseado no histórico
                if len(dividends) >= 2:
                    # Calcula intervalo médio entre dividendos
                    try:
                        # Parse datas com tratamento de erros
                        dates = []
                        for d in dividends[:6]:
                            parsed = parse_date(d.get('date', ''))
                            if parsed:
                                dates.append(parsed)
                        
                        if len(dates) >= 2:
                            avg_interval = sum((dates[i] - dates[i+1]).days for i in range(len(dates)-1)) // (len(dates)-1)
                            next_ex_date = dates[0] + timedelta(days=avg_interval)
                            
                            # Se já passou, próximo ciclo
                            while next_ex_date < today:
                                next_ex_date += timedelta(days=avg_interval)
                            
                            days_to_ex = (next_ex_date - today).days
                            
                            if days_to_ex <= days_ahead:
                                # Estima valor baseado na média
                                avg_dividend = sum(d.get('value', 0) for d in dividends[:4]) / min(4, len(dividends))
                                current_price = stock_data.get('current_price', 0)
                                
                                if current_price > 0:
                                    dy = (avg_dividend / current_price) * 100
                                    annual_yield = stock_data.get('dividend_yield', dy * 4)
                                    
                                    if dy >= min_yield:
                                        # Score e recomendação
                                        score = self._calculate_score(stock_data, days_to_ex, annual_yield)
                                        recommendation = self._get_recommendation(score, days_to_ex)
                                        
                                        upcoming.append(UpcomingDividend(
                                            ticker=ticker,
                                            company_name=stock_data.get('company_name', ticker),
                                            sector=stock_data.get('sector', 'Outros'),
                                            current_price=current_price,
                                            dividend_type='dividend',
                                            value_per_share=round(avg_dividend, 2),
                                            ex_date=next_ex_date.isoformat(),
                                            payment_date=(next_ex_date + timedelta(days=15)).isoformat(),
                                            dividend_yield=round(dy, 2),
                                            days_to_ex=days_to_ex,
                                            annual_yield=round(annual_yield, 2),
                                            recommendation=recommendation,
                                            score=score
                                        ))
                    except Exception as e:
                        logger.warning(f"Error processing {ticker}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Error getting upcoming for {ticker}: {e}")
                continue
        
        # Ordena por data ex
        upcoming.sort(key=lambda x: x.ex_date)
        
        return upcoming
    
    async def get_fundamentals(self, ticker: str) -> StockFundamentals:
        """Retorna análise fundamentalista completa."""
        stock_data = await self.get_stock_data(ticker)
        dividends = await self.get_dividends(ticker)
        
        # Calcula consistência de dividendos
        consistency = 0
        if len(dividends) >= 4:
            # Se pagou dividendos nos últimos 4 trimestres
            consistency = min(100, len(dividends) * 25)
        
        # Calcula volatilidade estimada
        volatility = 25.0  # Default
        if stock_data.get('52w_high') and stock_data.get('52w_low'):
            high = stock_data['52w_high']
            low = stock_data['52w_low']
            if low > 0:
                volatility = ((high - low) / low) * 100
        
        return StockFundamentals(
            ticker=ticker,
            company_name=stock_data.get('company_name', ticker),
            sector=stock_data.get('sector', 'Outros'),
            current_price=stock_data.get('current_price', 0),
            annual_dividend=stock_data.get('dividend_rate', 0),
            dividend_yield=stock_data.get('dividend_yield', 0),
            payout_ratio=stock_data.get('payout_ratio', 0),
            dividend_consistency=consistency,
            pe_ratio=stock_data.get('pe_ratio', 0),
            pb_ratio=stock_data.get('pb_ratio', 0),
            ev_ebitda=0,  # Não disponível em todas as fontes
            roe=stock_data.get('roe', 0),
            roa=0,
            net_margin=0,
            debt_to_equity=stock_data.get('debt_to_equity', 0),
            current_ratio=0,
            market_cap=stock_data.get('market_cap', 0),
            avg_volume=stock_data.get('avg_volume', 0),
            volatility_30d=volatility,
            price_52w_high=stock_data.get('52w_high', 0),
            price_52w_low=stock_data.get('52w_low', 0),
            last_update=stock_data.get('last_update', datetime.now().isoformat()),
            source=stock_data.get('source', 'unknown')
        )
    
    def _calculate_score(self, stock_data: Dict, days_to_ex: int, annual_yield: float) -> float:
        """Calcula score para dividend capture."""
        score = 50.0  # Base
        
        # Dividend Yield (máx +25)
        if annual_yield >= 10:
            score += 25
        elif annual_yield >= 6:
            score += 15
        elif annual_yield >= 4:
            score += 10
        
        # P/L (máx +15)
        pe = stock_data.get('pe_ratio', 0)
        if 0 < pe < 8:
            score += 15
        elif pe < 12:
            score += 10
        elif pe < 20:
            score += 5
        
        # Timing (máx +15)
        if 3 <= days_to_ex <= 7:
            score += 15
        elif 2 <= days_to_ex <= 10:
            score += 10
        elif days_to_ex < 2:
            score -= 10  # Muito próximo
        
        # ROE (máx +10)
        roe = stock_data.get('roe', 0)
        if roe >= 20:
            score += 10
        elif roe >= 15:
            score += 7
        elif roe >= 10:
            score += 5
        
        # Volume/Liquidez (máx +10)
        volume = stock_data.get('avg_volume', 0)
        if volume >= 10000000:
            score += 10
        elif volume >= 1000000:
            score += 5
        
        # Dívida (máx +5)
        debt = stock_data.get('debt_to_equity', 0)
        if debt < 50:
            score += 5
        elif debt > 150:
            score -= 5
        
        return min(100, max(0, score))
    
    def _get_recommendation(self, score: float, days_to_ex: int) -> str:
        """Retorna recomendação baseada no score."""
        if days_to_ex < 2:
            return "avoid"
        if score >= 75:
            return "buy"
        if score >= 55:
            return "wait"
        return "avoid"
    
    def _get_mock_data(self, ticker: str) -> Dict:
        """Retorna dados mock para ticker."""
        import random
        base_price = random.uniform(20, 80)
        
        return {
            'ticker': ticker,
            'company_name': f"{ticker} Corp",
            'current_price': round(base_price, 2),
            'previous_close': round(base_price * 0.99, 2),
            'market_cap': random.randint(1000000000, 100000000000),
            'pe_ratio': round(random.uniform(5, 20), 1),
            'pb_ratio': round(random.uniform(0.5, 3), 1),
            'dividend_yield': round(random.uniform(2, 12), 1),
            'payout_ratio': round(random.uniform(30, 80), 1),
            'roe': round(random.uniform(10, 30), 1),
            'debt_to_equity': round(random.uniform(20, 150), 1),
            'avg_volume': random.randint(100000, 50000000),
            '52w_high': round(base_price * 1.3, 2),
            '52w_low': round(base_price * 0.7, 2),
            'source': DataSource.MOCK.value
        }
    
    def _get_mock_dividends(self, ticker: str) -> List[Dict]:
        """Retorna dividendos mock."""
        import random
        today = date.today()
        dividends = []
        
        for i in range(8):
            ex_date = today - timedelta(days=90 * i)
            dividends.append({
                'date': ex_date.isoformat(),
                'payment_date': (ex_date + timedelta(days=15)).isoformat(),
                'value': round(random.uniform(0.3, 2.5), 2),
                'type': 'DIVIDEND'
            })
        
        return dividends


# ==================== SOCIAL MEDIA INTEGRATION ====================

class DividendSocialGenerator:
    """Gera conteúdo para redes sociais sobre dividendos."""
    
    def __init__(self, data_service: DividendDataService):
        self.data_service = data_service
    
    async def generate_daily_opportunities(self) -> Dict[str, str]:
        """Gera post diário com oportunidades de dividendos."""
        upcoming = await self.data_service.get_upcoming_dividends(days_ahead=14, min_yield=3)
        
        if not upcoming:
            return {
                'title': '📊 Dividendos da Semana',
                'content': 'Sem dividendos relevantes nos próximos dias.',
                'hashtags': '#dividendos #acoes #b3'
            }
        
        # Seleciona top 5 por score
        top = sorted(upcoming, key=lambda x: x.score, reverse=True)[:5]
        
        lines = ["📊 **TOP DIVIDENDOS DA SEMANA**\n"]
        
        for i, div in enumerate(top, 1):
            emoji = "🏆" if i == 1 else "💰"
            lines.append(
                f"{emoji} **{div.ticker}** ({div.company_name[:20]})\n"
                f"   📅 Ex: {div.ex_date} ({div.days_to_ex} dias)\n"
                f"   💵 R$ {div.value_per_share:.2f}/ação (DY: {div.dividend_yield:.1f}%)\n"
                f"   📈 Score: {div.score:.0f}/100 - {div.recommendation.upper()}\n"
            )
        
        lines.append("\n⚠️ Não é recomendação de investimento.")
        
        return {
            'title': '📊 Top Dividendos da Semana',
            'content': '\n'.join(lines),
            'hashtags': '#dividendos #acoes #b3 #investimentos #rendavariavel',
            'data': [asdict(d) for d in top]
        }
    
    async def generate_stock_analysis(self, ticker: str) -> Dict[str, str]:
        """Gera análise de ação específica para redes sociais."""
        fundamentals = await self.data_service.get_fundamentals(ticker)
        
        # Classificação
        rating = "⭐⭐⭐⭐⭐" if fundamentals.dividend_yield >= 8 else \
                 "⭐⭐⭐⭐" if fundamentals.dividend_yield >= 6 else \
                 "⭐⭐⭐" if fundamentals.dividend_yield >= 4 else \
                 "⭐⭐" if fundamentals.dividend_yield >= 2 else "⭐"
        
        content = f"""
📊 **ANÁLISE: {ticker}**
{fundamentals.company_name}

💰 **Dividendos**
• DY Anual: {fundamentals.dividend_yield:.1f}%
• Payout: {fundamentals.payout_ratio:.0f}%
• Consistência: {fundamentals.dividend_consistency:.0f}%

📈 **Valuation**
• P/L: {fundamentals.pe_ratio:.1f}
• P/VP: {fundamentals.pb_ratio:.1f}
• ROE: {fundamentals.roe:.1f}%

💵 **Preço**
• Atual: R$ {fundamentals.current_price:.2f}
• Máx 52s: R$ {fundamentals.price_52w_high:.2f}
• Mín 52s: R$ {fundamentals.price_52w_low:.2f}

{rating} Rating Dividendos

⚠️ Não é recomendação de investimento.
        """
        
        return {
            'title': f'📊 Análise {ticker}',
            'content': content.strip(),
            'hashtags': f'#{ticker.lower()} #dividendos #analise #acoes #b3',
            'data': asdict(fundamentals)
        }
    
    async def generate_weekly_summary(self) -> Dict[str, str]:
        """Gera resumo semanal de dividendos."""
        upcoming = await self.data_service.get_upcoming_dividends(days_ahead=7)
        
        total_companies = len(upcoming)
        avg_yield = sum(d.dividend_yield for d in upcoming) / total_companies if total_companies else 0
        
        by_sector = {}
        for div in upcoming:
            sector = div.sector
            if sector not in by_sector:
                by_sector[sector] = []
            by_sector[sector].append(div)
        
        lines = [
            "📅 **RESUMO SEMANAL - DIVIDENDOS**\n",
            f"📊 {total_companies} empresas com data ex esta semana",
            f"📈 DY médio: {avg_yield:.1f}%\n",
            "**Por Setor:**"
        ]
        
        for sector, divs in sorted(by_sector.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            lines.append(f"• {sector}: {len(divs)} empresas")
        
        if upcoming:
            best = max(upcoming, key=lambda x: x.score)
            lines.append(f"\n🏆 **Destaque:** {best.ticker} (Score {best.score:.0f})")
        
        lines.append("\n⚠️ Não é recomendação de investimento.")
        
        return {
            'title': '📅 Resumo Semanal - Dividendos',
            'content': '\n'.join(lines),
            'hashtags': '#dividendos #acoes #b3 #investimentos #resumo',
            'data': {
                'total': total_companies,
                'avg_yield': avg_yield,
                'by_sector': {k: len(v) for k, v in by_sector.items()}
            }
        }


# Singleton
_data_service: Optional[DividendDataService] = None


def get_dividend_data_service() -> DividendDataService:
    """Retorna instância singleton do serviço."""
    global _data_service
    if _data_service is None:
        _data_service = DividendDataService()
    return _data_service
