"""
VIRTUS - Serviço de Portfólio de Dividendos
=============================================

Gerencia posições, calcula projeções e acompanha evolução do capital.

Funcionalidades:
1. Registro de compras/vendas
2. Cálculo de dividendos recebidos
3. Projeção de dividendos futuros
4. Evolução do patrimônio
5. Métricas de performance (yield on cost, etc)
"""

import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

# Paths
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
DATA_PATH = BRAIN_PATH / "data"
PORTFOLIO_PATH = DATA_PATH / "dividend_portfolio"
PORTFOLIO_PATH.mkdir(parents=True, exist_ok=True)


class TransactionType(str, Enum):
    """Tipo de transação."""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    JCP = "jcp"


@dataclass
class Transaction:
    """Transação de compra/venda/dividendo."""
    id: str
    ticker: str
    type: TransactionType
    date: str  # YYYY-MM-DD
    shares: int
    price: float  # Preço por ação ou valor do dividendo por ação
    total: float  # Valor total
    fees: float = 0.0  # Taxas/corretagem
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'ticker': self.ticker,
            'type': self.type.value if isinstance(self.type, TransactionType) else self.type,
            'date': self.date,
            'shares': self.shares,
            'price': self.price,
            'total': self.total,
            'fees': self.fees,
            'notes': self.notes,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Transaction':
        return cls(
            id=data['id'],
            ticker=data['ticker'],
            type=TransactionType(data['type']) if isinstance(data['type'], str) else data['type'],
            date=data['date'],
            shares=data['shares'],
            price=data['price'],
            total=data['total'],
            fees=data.get('fees', 0.0),
            notes=data.get('notes', ''),
            created_at=data.get('created_at', datetime.now().isoformat())
        )


@dataclass
class Position:
    """Posição em uma ação."""
    ticker: str
    company_name: str
    shares: int
    avg_price: float
    total_invested: float
    current_price: float
    current_value: float
    profit_loss: float
    profit_loss_percent: float
    dividends_received: float
    yield_on_cost: float  # Dividendos recebidos / Total investido
    last_update: str


@dataclass 
class DividendProjection:
    """Projeção de dividendo."""
    ticker: str
    company_name: str
    shares: int
    ex_date: str
    payment_date: str
    dividend_per_share: float
    total_expected: float
    status: str  # 'pending', 'confirmed', 'received'


@dataclass
class PortfolioSummary:
    """Resumo do portfólio."""
    total_invested: float
    total_current_value: float
    total_profit_loss: float
    total_profit_loss_percent: float
    total_dividends_received: float
    total_dividends_projected: float
    yield_on_cost: float
    monthly_dividend_avg: float
    positions_count: int
    last_update: str


class DividendPortfolioService:
    """Serviço de gestão do portfólio de dividendos."""
    
    def __init__(self):
        self.transactions_file = PORTFOLIO_PATH / "transactions.json"
        self.positions_file = PORTFOLIO_PATH / "positions.json"
        self.projections_file = PORTFOLIO_PATH / "projections.json"
        self.history_file = PORTFOLIO_PATH / "portfolio_history.json"
        self.settings_file = PORTFOLIO_PATH / "settings.json"
        
        self._ensure_files()
        self._data_service = None
    
    def _ensure_files(self):
        """Garante que arquivos existem."""
        for file in [self.transactions_file, self.positions_file, 
                     self.projections_file, self.history_file, self.settings_file]:
            if not file.exists():
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump([], f) if 'history' in str(file) or 'transactions' in str(file) or 'projections' in str(file) else json.dump({}, f)
    
    def _load_json(self, file: Path) -> Any:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return [] if 'history' in str(file) or 'transactions' in str(file) or 'projections' in str(file) else {}
    
    def _save_json(self, file: Path, data: Any):
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    async def _get_data_service(self):
        """Lazy load do serviço de dados."""
        if self._data_service is None:
            try:
                from services.dividend_data_service import get_dividend_data_service
                self._data_service = get_dividend_data_service()
            except:
                pass
        return self._data_service
    
    # ==================== TRANSAÇÕES ====================
    
    def get_transactions(self, ticker: Optional[str] = None, 
                        type_filter: Optional[TransactionType] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> List[Transaction]:
        """Retorna transações filtradas."""
        data = self._load_json(self.transactions_file)
        transactions = [Transaction.from_dict(t) for t in data]
        
        if ticker:
            transactions = [t for t in transactions if t.ticker.upper() == ticker.upper()]
        
        if type_filter:
            transactions = [t for t in transactions if t.type == type_filter]
        
        if start_date:
            transactions = [t for t in transactions if t.date >= start_date]
        
        if end_date:
            transactions = [t for t in transactions if t.date <= end_date]
        
        return sorted(transactions, key=lambda x: x.date, reverse=True)
    
    def add_transaction(self, ticker: str, type: TransactionType, 
                       date: str, shares: int, price: float,
                       fees: float = 0.0, notes: str = "") -> Transaction:
        """Adiciona nova transação."""
        total = shares * price
        if type == TransactionType.BUY:
            total += fees
        elif type == TransactionType.SELL:
            total -= fees
        
        transaction = Transaction(
            id=str(uuid.uuid4())[:8],
            ticker=ticker.upper(),
            type=type,
            date=date,
            shares=shares,
            price=price,
            total=total,
            fees=fees,
            notes=notes
        )
        
        data = self._load_json(self.transactions_file)
        data.append(transaction.to_dict())
        self._save_json(self.transactions_file, data)
        
        # Recalcula posições
        self._recalculate_positions()
        
        # Adiciona ao histórico
        self._add_to_history()
        
        return transaction
    
    def delete_transaction(self, transaction_id: str) -> bool:
        """Remove uma transação."""
        data = self._load_json(self.transactions_file)
        original_len = len(data)
        data = [t for t in data if t['id'] != transaction_id]
        
        if len(data) < original_len:
            self._save_json(self.transactions_file, data)
            self._recalculate_positions()
            return True
        return False
    
    def add_buy(self, ticker: str, date: str, shares: int, 
                price: float, fees: float = 0.0, notes: str = "") -> Transaction:
        """Registra uma compra."""
        return self.add_transaction(ticker, TransactionType.BUY, date, shares, price, fees, notes)
    
    def add_sell(self, ticker: str, date: str, shares: int,
                 price: float, fees: float = 0.0, notes: str = "") -> Transaction:
        """Registra uma venda."""
        return self.add_transaction(ticker, TransactionType.SELL, date, shares, price, fees, notes)
    
    def add_dividend_received(self, ticker: str, date: str, 
                              shares: int, dividend_per_share: float,
                              notes: str = "") -> Transaction:
        """Registra dividendo recebido."""
        return self.add_transaction(ticker, TransactionType.DIVIDEND, date, shares, 
                                   dividend_per_share, 0, notes)
    
    # ==================== POSIÇÕES ====================
    
    def _recalculate_positions(self):
        """Recalcula todas as posições com base nas transações."""
        transactions = self.get_transactions()
        positions: Dict[str, Dict] = {}
        
        for t in sorted(transactions, key=lambda x: x.date):
            ticker = t.ticker
            
            if ticker not in positions:
                positions[ticker] = {
                    'ticker': ticker,
                    'shares': 0,
                    'total_invested': 0,
                    'total_sold': 0,
                    'dividends_received': 0,
                    'buy_transactions': [],
                    'sell_transactions': [],
                    'dividend_transactions': []
                }
            
            if t.type == TransactionType.BUY:
                positions[ticker]['shares'] += t.shares
                positions[ticker]['total_invested'] += t.total
                positions[ticker]['buy_transactions'].append(t.to_dict())
                
            elif t.type == TransactionType.SELL:
                positions[ticker]['shares'] -= t.shares
                positions[ticker]['total_sold'] += t.total
                positions[ticker]['sell_transactions'].append(t.to_dict())
                
            elif t.type in [TransactionType.DIVIDEND, TransactionType.JCP]:
                positions[ticker]['dividends_received'] += t.total
                positions[ticker]['dividend_transactions'].append(t.to_dict())
        
        # Calcula preço médio
        for ticker, pos in positions.items():
            if pos['shares'] > 0:
                # Preço médio = Total investido líquido / Ações restantes
                net_invested = pos['total_invested'] - pos['total_sold']
                pos['avg_price'] = net_invested / pos['shares'] if pos['shares'] > 0 else 0
            else:
                pos['avg_price'] = 0
        
        self._save_json(self.positions_file, positions)
        return positions
    
    async def get_positions(self) -> List[Position]:
        """Retorna posições atualizadas com preços de mercado."""
        positions_data = self._load_json(self.positions_file)
        if not positions_data:
            self._recalculate_positions()
            positions_data = self._load_json(self.positions_file)
        
        positions = []
        data_service = await self._get_data_service()
        
        for ticker, data in positions_data.items():
            if data['shares'] <= 0:
                continue
            
            # Busca preço atual
            current_price = 0
            company_name = ticker
            
            if data_service:
                try:
                    stock_data = await data_service.get_stock_data(ticker)
                    current_price = stock_data.get('current_price', 0)
                    company_name = stock_data.get('company_name', ticker)
                except:
                    pass
            
            current_value = data['shares'] * current_price
            total_invested = data['total_invested'] - data['total_sold']
            profit_loss = current_value - total_invested + data['dividends_received']
            profit_loss_percent = (profit_loss / total_invested * 100) if total_invested > 0 else 0
            yield_on_cost = (data['dividends_received'] / total_invested * 100) if total_invested > 0 else 0
            
            positions.append(Position(
                ticker=ticker,
                company_name=company_name,
                shares=data['shares'],
                avg_price=data['avg_price'],
                total_invested=total_invested,
                current_price=current_price,
                current_value=current_value,
                profit_loss=profit_loss,
                profit_loss_percent=profit_loss_percent,
                dividends_received=data['dividends_received'],
                yield_on_cost=yield_on_cost,
                last_update=datetime.now().isoformat()
            ))
        
        return sorted(positions, key=lambda x: x.current_value, reverse=True)
    
    # ==================== PROJEÇÕES ====================
    
    async def get_dividend_projections(self, days_ahead: int = 90) -> List[DividendProjection]:
        """Calcula projeção de dividendos baseado nas posições."""
        positions = await self.get_positions()
        if not positions:
            return []
        
        projections = []
        data_service = await self._get_data_service()
        
        if not data_service:
            return []
        
        # Busca próximos dividendos
        upcoming = await data_service.get_upcoming_dividends(days_ahead=days_ahead)
        
        for dividend in upcoming:
            # Verifica se temos posição nesta ação
            position = next((p for p in positions if p.ticker == dividend.ticker), None)
            
            if position and position.shares > 0:
                total_expected = position.shares * dividend.value_per_share
                
                projections.append(DividendProjection(
                    ticker=dividend.ticker,
                    company_name=dividend.company_name,
                    shares=position.shares,
                    ex_date=dividend.ex_date,
                    payment_date=dividend.payment_date or '',
                    dividend_per_share=dividend.value_per_share,
                    total_expected=total_expected,
                    status='pending'
                ))
        
        return sorted(projections, key=lambda x: x.ex_date)
    
    # ==================== RESUMO/MÉTRICAS ====================
    
    async def get_portfolio_summary(self) -> PortfolioSummary:
        """Retorna resumo do portfólio."""
        positions = await self.get_positions()
        projections = await self.get_dividend_projections(90)
        
        total_invested = sum(p.total_invested for p in positions)
        total_current_value = sum(p.current_value for p in positions)
        total_dividends_received = sum(p.dividends_received for p in positions)
        total_dividends_projected = sum(proj.total_expected for proj in projections)
        
        profit_loss = total_current_value - total_invested + total_dividends_received
        profit_loss_percent = (profit_loss / total_invested * 100) if total_invested > 0 else 0
        yield_on_cost = (total_dividends_received / total_invested * 100) if total_invested > 0 else 0
        
        # Calcula média mensal de dividendos (últimos 12 meses)
        transactions = self.get_transactions(type_filter=TransactionType.DIVIDEND)
        twelve_months_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        recent_dividends = [t for t in transactions if t.date >= twelve_months_ago]
        monthly_dividend_avg = sum(t.total for t in recent_dividends) / 12
        
        return PortfolioSummary(
            total_invested=total_invested,
            total_current_value=total_current_value,
            total_profit_loss=profit_loss,
            total_profit_loss_percent=profit_loss_percent,
            total_dividends_received=total_dividends_received,
            total_dividends_projected=total_dividends_projected,
            yield_on_cost=yield_on_cost,
            monthly_dividend_avg=monthly_dividend_avg,
            positions_count=len(positions),
            last_update=datetime.now().isoformat()
        )
    
    # ==================== HISTÓRICO/EVOLUÇÃO ====================
    
    def _add_to_history(self):
        """Adiciona snapshot atual ao histórico."""
        history = self._load_json(self.history_file)
        positions_data = self._load_json(self.positions_file)
        
        total_invested = sum(
            p['total_invested'] - p['total_sold'] 
            for p in positions_data.values() if p['shares'] > 0
        )
        total_dividends = sum(
            p['dividends_received'] 
            for p in positions_data.values()
        )
        
        snapshot = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'total_invested': total_invested,
            'total_dividends': total_dividends,
            'positions_count': len([p for p in positions_data.values() if p['shares'] > 0])
        }
        
        # Evita duplicatas no mesmo dia
        today = datetime.now().strftime('%Y-%m-%d')
        history = [h for h in history if h['date'] != today]
        history.append(snapshot)
        
        # Mantém últimos 365 dias
        history = history[-365:]
        
        self._save_json(self.history_file, history)
    
    def get_portfolio_history(self, days: int = 365) -> List[Dict]:
        """Retorna histórico do portfólio."""
        history = self._load_json(self.history_file)
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        return [h for h in history if h['date'] >= cutoff]
    
    async def get_evolution_data(self, period: str = '1Y') -> Dict:
        """Retorna dados para gráfico de evolução."""
        days_map = {'1M': 30, '3M': 90, '6M': 180, '1Y': 365, 'ALL': 9999}
        days = days_map.get(period, 365)
        
        history = self.get_portfolio_history(days)
        positions = await self.get_positions()
        
        # Calcula valor atual
        current_value = sum(p.current_value for p in positions)
        total_dividends = sum(p.dividends_received for p in positions)
        
        # Adiciona ponto atual se não existe
        today = datetime.now().strftime('%Y-%m-%d')
        if not history or history[-1]['date'] != today:
            history.append({
                'date': today,
                'total_invested': sum(p.total_invested for p in positions),
                'total_dividends': total_dividends,
                'current_value': current_value
            })
        
        return {
            'history': history,
            'current_value': current_value,
            'total_dividends': total_dividends,
            'period': period
        }
    
    # ==================== SETTINGS ====================
    
    def get_settings(self) -> Dict:
        """Retorna configurações."""
        settings = self._load_json(self.settings_file)
        defaults = {
            'default_fees': 0.0,
            'alert_days_before_ex': 5,
            'min_dividend_yield': 5.0,
            'reinvest_dividends': False,
            'target_monthly_income': 1000.0
        }
        for k, v in defaults.items():
            if k not in settings:
                settings[k] = v
        return settings
    
    def update_settings(self, settings: Dict) -> Dict:
        """Atualiza configurações."""
        current = self.get_settings()
        current.update(settings)
        self._save_json(self.settings_file, current)
        return current


# Singleton
_portfolio_service: Optional[DividendPortfolioService] = None

def get_portfolio_service() -> DividendPortfolioService:
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = DividendPortfolioService()
    return _portfolio_service
