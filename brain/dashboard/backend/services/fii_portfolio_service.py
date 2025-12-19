"""
FII Portfolio Service
Sistema completo para análise e gestão de carteira de FIIs
"""
import httpx
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import json
from pathlib import Path


class FIIPortfolioService:
    """Serviço de Carteira de FIIs"""
    
    BASE_URL = "https://brapi.dev/api"
    API_KEY = os.getenv("BRAPI_API_KEY", "")
    
    # Categorias de FIIs
    FII_CATEGORIES = {
        'tijolo': {
            'name': 'Tijolo',
            'description': 'Fundos que investem em imóveis físicos',
            'subcategories': ['logistica', 'shoppings', 'lajes', 'hibrido', 'hospitalar', 'educacional', 'hotel']
        },
        'papel': {
            'name': 'Papel',
            'description': 'Fundos que investem em títulos imobiliários (CRI, LCI)',
            'subcategories': ['cri', 'lci', 'hibrido_papel']
        },
        'fof': {
            'name': 'Fundos de Fundos',
            'description': 'Fundos que investem em outros FIIs',
            'subcategories': ['fof']
        },
        'desenvolvimento': {
            'name': 'Desenvolvimento',
            'description': 'Fundos focados em construção e desenvolvimento',
            'subcategories': ['desenvolvimento']
        }
    }
    
    # FIIs populares por categoria (para sugestões)
    POPULAR_FIIS = {
        'logistica': ['HGLG11', 'XPLG11', 'VILG11', 'BTLG11', 'LVBI11'],
        'shoppings': ['XPML11', 'VISC11', 'HSML11', 'MALL11'],
        'lajes': ['HGRE11', 'BRCR11', 'PVBI11', 'RBRP11'],
        'papel': ['KNCR11', 'KNIP11', 'MXRF11', 'IRDM11', 'CPTS11'],
        'fof': ['BCFF11', 'MGFF11', 'RBFF11'],
        'hibrido': ['HGBS11', 'KNRI11', 'RECT11']
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.data_dir = Path(__file__).parent.parent.parent / 'data' / 'fii_portfolio'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 300
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Faz requisição à API Brapi"""
        if params is None:
            params = {}
        params['token'] = self.API_KEY
        
        cache_key = f"{endpoint}_{str(params)}"
        if cache_key in self._cache:
            if datetime.now().timestamp() - self._cache_time.get(cache_key, 0) < self._cache_ttl:
                return self._cache[cache_key]
        
        url = f"{self.BASE_URL}/{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        self._cache[cache_key] = data
        self._cache_time[cache_key] = datetime.now().timestamp()
        
        return data
    
    def _load_portfolio(self, user_id: str = 'default') -> Dict:
        """Carrega carteira do usuário"""
        file_path = self.data_dir / f'portfolio_{user_id}.json'
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'user_id': user_id,
            'positions': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    
    def _save_portfolio(self, portfolio: Dict, user_id: str = 'default'):
        """Salva carteira do usuário"""
        portfolio['updated_at'] = datetime.now().isoformat()
        file_path = self.data_dir / f'portfolio_{user_id}.json'
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(portfolio, f, indent=2, ensure_ascii=False)
    
    async def get_fii_quote(self, ticker: str) -> Dict:
        """Obtém cotação e dados de um FII"""
        data = await self._make_request(f'quote/{ticker}', {'fundamental': 'true'})
        
        if not data.get('results'):
            return None
        
        result = data['results'][0]
        
        return {
            'ticker': ticker,
            'name': result.get('longName', result.get('shortName', ticker)),
            'price': result.get('regularMarketPrice', 0),
            'change': result.get('regularMarketChange', 0),
            'changePercent': result.get('regularMarketChangePercent', 0),
            'previousClose': result.get('regularMarketPreviousClose', 0),
            'volume': result.get('regularMarketVolume', 0),
            'marketCap': result.get('marketCap', 0),
            'high52w': result.get('fiftyTwoWeekHigh', 0),
            'low52w': result.get('fiftyTwoWeekLow', 0),
            'logo': result.get('logourl', ''),
            'dy': result.get('dividendYield'),
            'pvp': result.get('priceToBook'),
            'updatedAt': datetime.now().isoformat()
        }
    
    async def get_fii_dividends(self, ticker: str, limit: int = 12) -> Dict:
        """Obtém histórico de dividendos de um FII"""
        data = await self._make_request(f'quote/{ticker}', {
            'dividends': 'true',
            'range': '1y'
        })
        
        if not data.get('results'):
            return None
        
        result = data['results'][0]
        dividends = result.get('dividendsData', {}).get('cashDividends', [])
        
        # Processa dividendos
        processed = []
        total_12m = 0
        
        for div in dividends[:limit]:
            amount = div.get('rate', 0)
            total_12m += amount
            processed.append({
                'paymentDate': div.get('paymentDate'),
                'rate': amount,
                'type': div.get('type', 'DIVIDEND')
            })
        
        # Calcula DY baseado nos últimos 12 meses
        current_price = result.get('regularMarketPrice', 0)
        dy_12m = (total_12m / current_price * 100) if current_price > 0 else 0
        
        # Média mensal
        avg_monthly = total_12m / len(processed) if processed else 0
        
        return {
            'ticker': ticker,
            'dividends': processed,
            'total_12m': round(total_12m, 2),
            'dy_12m': round(dy_12m, 2),
            'avg_monthly': round(avg_monthly, 2),
            'current_price': current_price
        }
    
    async def get_all_fiis(self, sort_by: str = 'dy', limit: int = 50) -> Dict:
        """Lista todos os FIIs disponíveis"""
        data = await self._make_request('quote/list', {
            'type': 'fund',
            'sortBy': 'volume',
            'sortOrder': 'desc',
            'limit': 200
        })
        
        stocks = data.get('stocks', [])
        
        # Filtra apenas FIIs (terminam em 11)
        fiis = [s for s in stocks if s.get('stock', '').endswith('11')]
        
        # Enriquece com dados
        enriched = []
        for fii in fiis[:limit]:
            enriched.append({
                'ticker': fii.get('stock'),
                'name': fii.get('name'),
                'price': fii.get('close'),
                'change': fii.get('change'),
                'volume': fii.get('volume'),
                'marketCap': fii.get('market_cap'),
                'logo': fii.get('logo'),
                'sector': fii.get('sector')
            })
        
        # Ordena
        if sort_by == 'volume':
            enriched.sort(key=lambda x: x.get('volume') or 0, reverse=True)
        elif sort_by == 'change':
            enriched.sort(key=lambda x: x.get('change') or 0, reverse=True)
        
        return {
            'fiis': enriched,
            'total': len(enriched),
            'timestamp': datetime.now().isoformat()
        }
    
    async def add_position(self, 
                          ticker: str, 
                          quantity: int, 
                          avg_price: float,
                          category: str = 'outros',
                          user_id: str = 'default') -> Dict:
        """Adiciona posição à carteira"""
        portfolio = self._load_portfolio(user_id)
        
        # Verifica se já existe
        existing = next((p for p in portfolio['positions'] if p['ticker'] == ticker), None)
        
        if existing:
            # Atualiza posição existente (preço médio)
            total_qty = existing['quantity'] + quantity
            total_cost = (existing['quantity'] * existing['avg_price']) + (quantity * avg_price)
            existing['quantity'] = total_qty
            existing['avg_price'] = round(total_cost / total_qty, 2)
            existing['category'] = category
            existing['updated_at'] = datetime.now().isoformat()
        else:
            # Nova posição
            portfolio['positions'].append({
                'ticker': ticker,
                'quantity': quantity,
                'avg_price': round(avg_price, 2),
                'category': category,
                'added_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
        
        self._save_portfolio(portfolio, user_id)
        return await self.get_portfolio(user_id)
    
    async def remove_position(self, ticker: str, user_id: str = 'default') -> Dict:
        """Remove posição da carteira"""
        portfolio = self._load_portfolio(user_id)
        portfolio['positions'] = [p for p in portfolio['positions'] if p['ticker'] != ticker]
        self._save_portfolio(portfolio, user_id)
        return await self.get_portfolio(user_id)
    
    async def update_position(self,
                             ticker: str,
                             quantity: int = None,
                             avg_price: float = None,
                             category: str = None,
                             user_id: str = 'default') -> Dict:
        """Atualiza posição existente"""
        portfolio = self._load_portfolio(user_id)
        
        for position in portfolio['positions']:
            if position['ticker'] == ticker:
                if quantity is not None:
                    position['quantity'] = quantity
                if avg_price is not None:
                    position['avg_price'] = round(avg_price, 2)
                if category is not None:
                    position['category'] = category
                position['updated_at'] = datetime.now().isoformat()
                break
        
        self._save_portfolio(portfolio, user_id)
        return await self.get_portfolio(user_id)
    
    async def get_portfolio(self, user_id: str = 'default') -> Dict:
        """Obtém carteira completa com cotações atualizadas"""
        portfolio = self._load_portfolio(user_id)
        positions = portfolio.get('positions', [])
        
        if not positions:
            return {
                'positions': [],
                'summary': {
                    'total_invested': 0,
                    'current_value': 0,
                    'total_gain': 0,
                    'total_gain_percent': 0,
                    'monthly_income': 0,
                    'avg_dy': 0
                },
                'by_category': {},
                'timestamp': datetime.now().isoformat()
            }
        
        # Busca cotações atuais em paralelo
        async def fetch_position_data(position):
            ticker = position['ticker']
            try:
                quote = await self.get_fii_quote(ticker)
                dividends = await self.get_fii_dividends(ticker)
                
                if quote:
                    current_price = quote['price']
                    invested = position['quantity'] * position['avg_price']
                    current_value = position['quantity'] * current_price
                    gain = current_value - invested
                    gain_percent = (gain / invested * 100) if invested > 0 else 0
                    
                    # Renda mensal estimada
                    monthly_div = dividends.get('avg_monthly', 0) if dividends else 0
                    monthly_income = position['quantity'] * monthly_div
                    
                    return {
                        **position,
                        'current_price': current_price,
                        'invested': round(invested, 2),
                        'current_value': round(current_value, 2),
                        'gain': round(gain, 2),
                        'gain_percent': round(gain_percent, 2),
                        'monthly_income': round(monthly_income, 2),
                        'dy_12m': dividends.get('dy_12m', 0) if dividends else 0,
                        'name': quote.get('name', ticker),
                        'logo': quote.get('logo', ''),
                        'change_today': quote.get('changePercent', 0)
                    }
            except Exception as e:
                print(f"Erro ao buscar dados de {ticker}: {e}")
            
            return {
                **position,
                'current_price': position['avg_price'],
                'invested': position['quantity'] * position['avg_price'],
                'current_value': position['quantity'] * position['avg_price'],
                'gain': 0,
                'gain_percent': 0,
                'monthly_income': 0,
                'dy_12m': 0,
                'error': True
            }
        
        # Processa posições
        tasks = [fetch_position_data(p) for p in positions]
        enriched_positions = await asyncio.gather(*tasks)
        
        # Calcula resumo
        total_invested = sum(p['invested'] for p in enriched_positions)
        current_value = sum(p['current_value'] for p in enriched_positions)
        total_gain = current_value - total_invested
        total_gain_percent = (total_gain / total_invested * 100) if total_invested > 0 else 0
        monthly_income = sum(p['monthly_income'] for p in enriched_positions)
        
        # DY médio ponderado
        weighted_dy = sum(p['dy_12m'] * p['current_value'] for p in enriched_positions)
        avg_dy = weighted_dy / current_value if current_value > 0 else 0
        
        # Agrupa por categoria
        by_category = {}
        for p in enriched_positions:
            cat = p.get('category', 'outros')
            if cat not in by_category:
                by_category[cat] = {
                    'positions': [],
                    'total_invested': 0,
                    'current_value': 0,
                    'monthly_income': 0
                }
            by_category[cat]['positions'].append(p['ticker'])
            by_category[cat]['total_invested'] += p['invested']
            by_category[cat]['current_value'] += p['current_value']
            by_category[cat]['monthly_income'] += p['monthly_income']
        
        # Calcula peso de cada categoria
        for cat in by_category:
            by_category[cat]['weight'] = round(
                by_category[cat]['current_value'] / current_value * 100, 1
            ) if current_value > 0 else 0
        
        return {
            'positions': enriched_positions,
            'summary': {
                'total_invested': round(total_invested, 2),
                'current_value': round(current_value, 2),
                'total_gain': round(total_gain, 2),
                'total_gain_percent': round(total_gain_percent, 2),
                'monthly_income': round(monthly_income, 2),
                'yearly_income': round(monthly_income * 12, 2),
                'avg_dy': round(avg_dy, 2),
                'position_count': len(enriched_positions)
            },
            'by_category': by_category,
            'timestamp': datetime.now().isoformat()
        }
    
    async def calculate_income(self, 
                              target_monthly: float,
                              avg_dy: float = 8.0) -> Dict:
        """
        Calculadora de renda passiva
        Quanto preciso investir para atingir renda mensal X?
        """
        # DY anual
        annual_dy = avg_dy / 100
        
        # Renda anual necessária
        target_yearly = target_monthly * 12
        
        # Patrimônio necessário
        required_capital = target_yearly / annual_dy if annual_dy > 0 else 0
        
        # Sugestões com diferentes DYs
        scenarios = []
        for dy in [6, 8, 10, 12]:
            capital = (target_monthly * 12) / (dy / 100)
            scenarios.append({
                'dy': dy,
                'required_capital': round(capital, 2),
                'monthly_income': target_monthly
            })
        
        return {
            'target_monthly': target_monthly,
            'target_yearly': target_yearly,
            'assumed_dy': avg_dy,
            'required_capital': round(required_capital, 2),
            'scenarios': scenarios,
            'tips': [
                'FIIs de papel (CRIs) costumam ter DY mais alto mas mais volátil',
                'FIIs de tijolo tendem a ser mais estáveis mas com DY menor',
                'Diversifique entre pelo menos 5-10 FIIs diferentes',
                'Considere a vacância e qualidade dos imóveis'
            ]
        }
    
    async def get_payment_calendar(self, user_id: str = 'default') -> Dict:
        """
        Agenda de pagamentos de dividendos
        """
        portfolio = self._load_portfolio(user_id)
        positions = portfolio.get('positions', [])
        
        payments = []
        
        for position in positions:
            try:
                dividends = await self.get_fii_dividends(position['ticker'])
                if dividends and dividends.get('dividends'):
                    for div in dividends['dividends'][:3]:  # Últimos 3
                        payments.append({
                            'ticker': position['ticker'],
                            'date': div['paymentDate'],
                            'rate_per_share': div['rate'],
                            'total': round(div['rate'] * position['quantity'], 2),
                            'quantity': position['quantity']
                        })
            except:
                continue
        
        # Ordena por data
        payments.sort(key=lambda x: x['date'] if x['date'] else '', reverse=True)
        
        # Agrupa por mês
        by_month = {}
        for p in payments:
            if p['date']:
                month = p['date'][:7]  # YYYY-MM
                if month not in by_month:
                    by_month[month] = {'payments': [], 'total': 0}
                by_month[month]['payments'].append(p)
                by_month[month]['total'] += p['total']
        
        return {
            'payments': payments[:20],
            'by_month': by_month,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_suggestions(self, 
                             category: str = None,
                             min_dy: float = 6.0,
                             max_pvp: float = 1.1) -> Dict:
        """
        Sugere FIIs baseado em critérios
        """
        all_fiis = await self.get_all_fiis(limit=100)
        fiis = all_fiis.get('fiis', [])
        
        # Busca dados detalhados
        suggestions = []
        
        for fii_info in fiis[:30]:  # Limita processamento
            try:
                ticker = fii_info['ticker']
                quote = await self.get_fii_quote(ticker)
                dividends = await self.get_fii_dividends(ticker)
                
                if not quote or not dividends:
                    continue
                
                dy = dividends.get('dy_12m', 0)
                pvp = quote.get('pvp') or 1.0
                
                # Aplica filtros
                if dy < min_dy:
                    continue
                if pvp > max_pvp:
                    continue
                
                # Score simples
                score = dy * 10 + (1 / pvp if pvp > 0 else 0) * 20
                
                suggestions.append({
                    'ticker': ticker,
                    'name': quote.get('name', ticker),
                    'price': quote['price'],
                    'dy_12m': dy,
                    'pvp': pvp,
                    'avg_monthly': dividends.get('avg_monthly', 0),
                    'logo': quote.get('logo', ''),
                    'score': round(score, 1)
                })
                
            except Exception as e:
                continue
        
        # Ordena por score
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'suggestions': suggestions[:15],
            'filters': {
                'min_dy': min_dy,
                'max_pvp': max_pvp,
                'category': category
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def close(self):
        """Fecha cliente HTTP"""
        await self.client.aclose()


# Singleton
_fii_service = None

def get_fii_portfolio_service() -> FIIPortfolioService:
    global _fii_service
    if _fii_service is None:
        _fii_service = FIIPortfolioService()
    return _fii_service
