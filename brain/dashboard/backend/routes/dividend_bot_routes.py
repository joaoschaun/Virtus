"""
VIRTUS Dashboard - Dividend Capture Bot API
=============================================

Bot gerenciador e analisador de ações com foco em:
- Data ex-dividendo (comprar antes)
- Recebimento de dividendos
- Venda estratégica após recebimento

Estratégia "Dividend Capture":
1. Identificar ações com dividendos próximos
2. Comprar antes da data ex-dividendo
3. Receber o dividendo
4. Vender após (considerando queda típica pós-ex)
"""

import os
import json
import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

# Paths
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
DATA_PATH = BRAIN_PATH / "data"
DIVIDEND_BOT_PATH = DATA_PATH / "dividend_bot"
DIVIDEND_BOT_PATH.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/dividend-bot", tags=["Dividend Capture Bot"])


# ==================== ENUMS ====================

class DividendType(str, Enum):
    """Tipo de provento."""
    DIVIDEND = "dividend"           # Dividendo
    JCP = "jcp"                     # Juros sobre Capital Próprio
    BONUS = "bonus"                 # Bonificação
    SUBSCRIPTION = "subscription"   # Direito de subscrição


class RecommendationAction(str, Enum):
    """Ação recomendada."""
    BUY = "buy"                     # Comprar agora
    WAIT = "wait"                   # Aguardar melhor momento
    HOLD = "hold"                   # Manter posição
    SELL = "sell"                   # Vender
    AVOID = "avoid"                 # Evitar (risco alto)


class OperationStatus(str, Enum):
    """Status da operação de dividend capture."""
    PLANNED = "planned"             # Planejada
    WAITING_ENTRY = "waiting_entry" # Aguardando ponto de entrada
    POSITION_OPEN = "position_open" # Posição aberta
    EX_DATE_PASSED = "ex_date_passed"  # Data ex passou
    DIVIDEND_RECEIVED = "dividend_received"  # Dividendo recebido
    CLOSED = "closed"               # Operação fechada
    CANCELLED = "cancelled"         # Cancelada


# ==================== MODELS - INPUT ====================

class StockAnalysisRequest(BaseModel):
    """Request para análise de ação."""
    ticker: str = Field(..., description="Código da ação (ex: PETR4, VALE3)")
    investment_amount: float = Field(1000.0, description="Valor a investir em R$")


class DividendOperationCreate(BaseModel):
    """Criar nova operação de dividend capture."""
    ticker: str = Field(..., description="Código da ação")
    target_shares: int = Field(..., description="Quantidade de ações alvo")
    max_entry_price: float = Field(..., description="Preço máximo de entrada")
    expected_dividend: float = Field(..., description="Dividendo esperado por ação")
    ex_date: str = Field(..., description="Data ex-dividendo (YYYY-MM-DD)")
    payment_date: Optional[str] = Field(None, description="Data de pagamento")
    notes: str = Field("", description="Observações")


class PortfolioAddStock(BaseModel):
    """Adicionar ação ao watchlist."""
    ticker: str
    target_dividend_yield: float = Field(6.0, description="DY mínimo desejado %")
    max_pe_ratio: float = Field(15.0, description="P/L máximo aceitável")
    sectors: List[str] = Field(default_factory=list, description="Setores de interesse")


class TradeExecution(BaseModel):
    """Registrar execução de trade."""
    operation_id: str
    action: str = Field(..., description="'buy' ou 'sell'")
    shares: int
    price: float
    fees: float = Field(0.0, description="Taxas e corretagem")
    executed_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ==================== MODELS - OUTPUT ====================

class DividendInfo(BaseModel):
    """Informações de dividendo."""
    ticker: str
    company_name: str
    dividend_type: DividendType
    value_per_share: float
    ex_date: str
    payment_date: Optional[str]
    dividend_yield: float
    announcement_date: Optional[str]


class StockAnalysis(BaseModel):
    """Análise completa de ação para dividend capture."""
    ticker: str
    company_name: str
    current_price: float
    
    # Dividendos
    next_dividend: Optional[DividendInfo]
    annual_dividend_yield: float
    dividend_history: List[DividendInfo]
    dividend_consistency: float  # 0-100%
    
    # Fundamentals
    pe_ratio: float
    pb_ratio: float
    roe: float
    debt_to_equity: float
    payout_ratio: float
    
    # Technical
    price_vs_52w_high: float
    price_vs_52w_low: float
    avg_volume: float
    volatility: float
    
    # Recommendation
    recommendation: RecommendationAction
    recommendation_reason: str
    score: float  # 0-100
    
    # Strategy
    suggested_entry_price: float
    suggested_exit_price: float
    expected_return: float
    risk_level: str  # low, medium, high
    
    # Timing
    days_to_ex_date: Optional[int]
    optimal_buy_window: Optional[str]
    optimal_sell_window: Optional[str]


class DividendOperation(BaseModel):
    """Operação de dividend capture."""
    id: str
    ticker: str
    status: OperationStatus
    
    # Planning
    target_shares: int
    max_entry_price: float
    expected_dividend: float
    ex_date: str
    payment_date: Optional[str]
    
    # Execution
    bought_shares: int = 0
    avg_buy_price: float = 0.0
    total_invested: float = 0.0
    
    sold_shares: int = 0
    avg_sell_price: float = 0.0
    total_received: float = 0.0
    
    # Results
    dividend_received: float = 0.0
    total_fees: float = 0.0
    gross_profit: float = 0.0
    net_profit: float = 0.0
    return_percentage: float = 0.0
    
    # Metadata
    created_at: str
    updated_at: str
    notes: str = ""


class CalendarEvent(BaseModel):
    """Evento no calendário de dividendos."""
    date: str
    ticker: str
    company_name: str
    event_type: str  # "ex_date", "payment_date", "announcement"
    dividend_value: float
    dividend_yield: float
    has_position: bool = False
    # Novos campos
    buy_limit_date: Optional[str] = None  # Data limite para comprar (1 dia antes da data ex)
    avg_historical_dividend: Optional[float] = None  # Média histórica de dividendos por ação
    company_score: Optional[float] = None  # Score/nota da empresa (0-100)
    sector: Optional[str] = None  # Setor da empresa


class DividendCalendar(BaseModel):
    """Calendário de dividendos."""
    events: List[CalendarEvent]
    total_expected_dividends: float
    next_7_days: List[CalendarEvent]
    next_30_days: List[CalendarEvent]


class PortfolioSummary(BaseModel):
    """Resumo do portfólio de dividend capture."""
    total_invested: float
    total_dividends_received: float
    total_capital_gains: float
    total_profit: float
    return_percentage: float
    
    active_operations: int
    completed_operations: int
    success_rate: float
    
    best_operation: Optional[Dict]
    worst_operation: Optional[Dict]
    
    monthly_dividend_projection: float
    annual_dividend_projection: float


# ==================== DATA STORAGE ====================

class DividendBotStorage:
    """Gerenciador de dados do bot de dividendos."""
    
    def __init__(self):
        self.operations_file = DIVIDEND_BOT_PATH / "operations.json"
        self.watchlist_file = DIVIDEND_BOT_PATH / "watchlist.json"
        self.history_file = DIVIDEND_BOT_PATH / "history.json"
        self.settings_file = DIVIDEND_BOT_PATH / "settings.json"
        
        self._ensure_files()
    
    def _ensure_files(self):
        """Garante que arquivos existem."""
        for file in [self.operations_file, self.watchlist_file, self.history_file, self.settings_file]:
            if not file.exists():
                with open(file, 'w') as f:
                    json.dump([], f) if 'history' in str(file) or 'operations' in str(file) else json.dump({}, f)
    
    def _load_json(self, file: Path) -> Any:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return [] if 'history' in str(file) or 'operations' in str(file) else {}
    
    def _save_json(self, file: Path, data: Any):
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    # Operations
    def get_operations(self, status: Optional[str] = None) -> List[Dict]:
        ops = self._load_json(self.operations_file)
        if status:
            ops = [o for o in ops if o.get('status') == status]
        return ops
    
    def get_operation(self, op_id: str) -> Optional[Dict]:
        ops = self.get_operations()
        for op in ops:
            if op.get('id') == op_id:
                return op
        return None
    
    def save_operation(self, operation: Dict):
        ops = self.get_operations()
        
        # Update or add
        found = False
        for i, op in enumerate(ops):
            if op.get('id') == operation.get('id'):
                ops[i] = operation
                found = True
                break
        
        if not found:
            ops.append(operation)
        
        self._save_json(self.operations_file, ops)
    
    def delete_operation(self, op_id: str):
        ops = self.get_operations()
        ops = [o for o in ops if o.get('id') != op_id]
        self._save_json(self.operations_file, ops)
    
    # Watchlist
    def get_watchlist(self) -> Dict:
        return self._load_json(self.watchlist_file)
    
    def save_watchlist(self, watchlist: Dict):
        self._save_json(self.watchlist_file, watchlist)
    
    # History
    def get_history(self, limit: int = 100) -> List[Dict]:
        history = self._load_json(self.history_file)
        return history[-limit:]
    
    def add_to_history(self, entry: Dict):
        history = self._load_json(self.history_file)
        history.append(entry)
        # Keep last 1000 entries
        if len(history) > 1000:
            history = history[-1000:]
        self._save_json(self.history_file, history)
    
    # Settings
    def get_settings(self) -> Dict:
        settings = self._load_json(self.settings_file)
        # Defaults
        defaults = {
            "min_dividend_yield": 5.0,
            "max_pe_ratio": 20.0,
            "min_liquidity": 100000,
            "buy_days_before_ex": 5,
            "sell_days_after_ex": 3,
            "max_position_size": 10000,
            "sectors_whitelist": [],
            "sectors_blacklist": [],
            "auto_trade": False,
            "notifications": True
        }
        for k, v in defaults.items():
            if k not in settings:
                settings[k] = v
        return settings
    
    def save_settings(self, settings: Dict):
        self._save_json(self.settings_file, settings)


# Instância global
storage = DividendBotStorage()


# ==================== DATA SERVICE INTEGRATION ====================

# Importar serviço real de dados
import sys
from pathlib import Path
services_path = Path(__file__).parent.parent / "services"
sys.path.insert(0, str(services_path))

try:
    from services.dividend_data_service import (
        get_dividend_data_service, 
        DividendDataService as RealDataService,
        DividendSocialGenerator
    )
    REAL_SERVICE_AVAILABLE = True
except ImportError:
    REAL_SERVICE_AVAILABLE = False
    RealDataService = None


class DividendDataService:
    """Serviço de dados de dividendos - integrado com APIs reais."""
    
    def __init__(self):
        self._real_service = get_dividend_data_service() if REAL_SERVICE_AVAILABLE else None
        self._social_generator = DividendSocialGenerator(self._real_service) if REAL_SERVICE_AVAILABLE else None
    
    @staticmethod
    def get_upcoming_dividends(days_ahead: int = 30) -> List[DividendInfo]:
        """Retorna dividendos próximos (mock data)."""
        # Em produção, buscar de API real
        today = date.today()
        mock_data = [
            {
                "ticker": "PETR4",
                "company_name": "Petrobras PN",
                "dividend_type": "dividend",
                "value_per_share": 1.45,
                "ex_date": (today + timedelta(days=5)).isoformat(),
                "payment_date": (today + timedelta(days=20)).isoformat(),
                "dividend_yield": 4.2,
                "announcement_date": (today - timedelta(days=10)).isoformat()
            },
            {
                "ticker": "VALE3",
                "company_name": "Vale ON",
                "dividend_type": "dividend",
                "value_per_share": 2.10,
                "ex_date": (today + timedelta(days=8)).isoformat(),
                "payment_date": (today + timedelta(days=25)).isoformat(),
                "dividend_yield": 3.8,
                "announcement_date": (today - timedelta(days=5)).isoformat()
            },
            {
                "ticker": "BBAS3",
                "company_name": "Banco do Brasil ON",
                "dividend_type": "jcp",
                "value_per_share": 0.85,
                "ex_date": (today + timedelta(days=12)).isoformat(),
                "payment_date": (today + timedelta(days=30)).isoformat(),
                "dividend_yield": 2.9,
                "announcement_date": (today - timedelta(days=3)).isoformat()
            },
            {
                "ticker": "ITUB4",
                "company_name": "Itaú Unibanco PN",
                "dividend_type": "dividend",
                "value_per_share": 0.65,
                "ex_date": (today + timedelta(days=15)).isoformat(),
                "payment_date": (today + timedelta(days=35)).isoformat(),
                "dividend_yield": 2.1,
                "announcement_date": (today - timedelta(days=7)).isoformat()
            },
            {
                "ticker": "TAEE11",
                "company_name": "Taesa Unit",
                "dividend_type": "dividend",
                "value_per_share": 1.20,
                "ex_date": (today + timedelta(days=3)).isoformat(),
                "payment_date": (today + timedelta(days=15)).isoformat(),
                "dividend_yield": 8.5,
                "announcement_date": (today - timedelta(days=15)).isoformat()
            },
            {
                "ticker": "BBSE3",
                "company_name": "BB Seguridade ON",
                "dividend_type": "dividend",
                "value_per_share": 0.95,
                "ex_date": (today + timedelta(days=7)).isoformat(),
                "payment_date": (today + timedelta(days=22)).isoformat(),
                "dividend_yield": 7.2,
                "announcement_date": (today - timedelta(days=8)).isoformat()
            }
        ]
        
        return [DividendInfo(**d) for d in mock_data]
    
    @staticmethod
    def analyze_stock(ticker: str, investment_amount: float = 1000.0) -> StockAnalysis:
        """Analisa ação para dividend capture (mock)."""
        # Em produção, buscar dados reais
        today = date.today()
        
        # Mock data baseado no ticker
        mock_stocks = {
            "PETR4": {
                "company_name": "Petrobras PN",
                "current_price": 34.50,
                "pe_ratio": 4.2,
                "pb_ratio": 1.1,
                "roe": 28.5,
                "debt_to_equity": 0.65,
                "payout_ratio": 45.0,
                "annual_dividend_yield": 18.5,
                "dividend_consistency": 75.0,
                "volatility": 32.0,
                "avg_volume": 50000000,
                "next_dividend_value": 1.45,
                "days_to_ex": 5,
                "score": 78
            },
            "VALE3": {
                "company_name": "Vale ON",
                "current_price": 58.20,
                "pe_ratio": 5.8,
                "pb_ratio": 1.4,
                "roe": 22.0,
                "debt_to_equity": 0.45,
                "payout_ratio": 60.0,
                "annual_dividend_yield": 12.0,
                "dividend_consistency": 70.0,
                "volatility": 28.0,
                "avg_volume": 35000000,
                "next_dividend_value": 2.10,
                "days_to_ex": 8,
                "score": 75
            },
            "TAEE11": {
                "company_name": "Taesa Unit",
                "current_price": 35.80,
                "pe_ratio": 8.5,
                "pb_ratio": 2.2,
                "roe": 25.0,
                "debt_to_equity": 1.2,
                "payout_ratio": 95.0,
                "annual_dividend_yield": 9.5,
                "dividend_consistency": 95.0,
                "volatility": 15.0,
                "avg_volume": 5000000,
                "next_dividend_value": 1.20,
                "days_to_ex": 3,
                "score": 85
            },
            "BBSE3": {
                "company_name": "BB Seguridade ON",
                "current_price": 32.40,
                "pe_ratio": 9.2,
                "pb_ratio": 5.5,
                "roe": 58.0,
                "debt_to_equity": 0.1,
                "payout_ratio": 80.0,
                "annual_dividend_yield": 8.0,
                "dividend_consistency": 90.0,
                "volatility": 18.0,
                "avg_volume": 8000000,
                "next_dividend_value": 0.95,
                "days_to_ex": 7,
                "score": 88
            }
        }
        
        # Default para tickers não mapeados
        stock = mock_stocks.get(ticker.upper(), {
            "company_name": f"{ticker.upper()} Corp",
            "current_price": 25.00,
            "pe_ratio": 12.0,
            "pb_ratio": 2.0,
            "roe": 15.0,
            "debt_to_equity": 0.5,
            "payout_ratio": 50.0,
            "annual_dividend_yield": 5.0,
            "dividend_consistency": 60.0,
            "volatility": 25.0,
            "avg_volume": 1000000,
            "next_dividend_value": 0.50,
            "days_to_ex": 15,
            "score": 60
        })
        
        current_price = stock["current_price"]
        next_div_value = stock["next_dividend_value"]
        days_to_ex = stock["days_to_ex"]
        
        # Calcular recomendação
        score = stock["score"]
        if days_to_ex <= 2:
            recommendation = RecommendationAction.AVOID
            reason = "Muito próximo da data ex - risco de queda pós-ex"
        elif days_to_ex <= 5 and score >= 75:
            recommendation = RecommendationAction.BUY
            reason = "Bom momento para entrada - dividendo próximo com bom score"
        elif score >= 80:
            recommendation = RecommendationAction.BUY
            reason = "Ação com excelente score para dividend capture"
        elif score >= 60:
            recommendation = RecommendationAction.WAIT
            reason = "Score moderado - aguardar melhor ponto de entrada"
        else:
            recommendation = RecommendationAction.AVOID
            reason = "Score baixo - não recomendado para esta estratégia"
        
        # Calcular preços sugeridos
        suggested_entry = current_price * 0.98  # 2% abaixo do atual
        suggested_exit = current_price * 0.99   # 1% abaixo (após queda do ex-div)
        expected_return = ((next_div_value + (suggested_exit - suggested_entry)) / suggested_entry) * 100
        
        # Risk level
        volatility = stock["volatility"]
        if volatility < 20:
            risk = "low"
        elif volatility < 30:
            risk = "medium"
        else:
            risk = "high"
        
        # Dividend history (mock)
        dividend_history = [
            DividendInfo(
                ticker=ticker.upper(),
                company_name=stock["company_name"],
                dividend_type=DividendType.DIVIDEND,
                value_per_share=next_div_value * 0.9,
                ex_date=(today - timedelta(days=90)).isoformat(),
                payment_date=(today - timedelta(days=75)).isoformat(),
                dividend_yield=stock["annual_dividend_yield"] / 4,
                announcement_date=None
            ),
            DividendInfo(
                ticker=ticker.upper(),
                company_name=stock["company_name"],
                dividend_type=DividendType.DIVIDEND,
                value_per_share=next_div_value * 0.95,
                ex_date=(today - timedelta(days=180)).isoformat(),
                payment_date=(today - timedelta(days=165)).isoformat(),
                dividend_yield=stock["annual_dividend_yield"] / 4,
                announcement_date=None
            )
        ]
        
        next_dividend = DividendInfo(
            ticker=ticker.upper(),
            company_name=stock["company_name"],
            dividend_type=DividendType.DIVIDEND,
            value_per_share=next_div_value,
            ex_date=(today + timedelta(days=days_to_ex)).isoformat(),
            payment_date=(today + timedelta(days=days_to_ex + 15)).isoformat(),
            dividend_yield=(next_div_value / current_price) * 100,
            announcement_date=(today - timedelta(days=10)).isoformat()
        )
        
        return StockAnalysis(
            ticker=ticker.upper(),
            company_name=stock["company_name"],
            current_price=current_price,
            next_dividend=next_dividend,
            annual_dividend_yield=stock["annual_dividend_yield"],
            dividend_history=dividend_history,
            dividend_consistency=stock["dividend_consistency"],
            pe_ratio=stock["pe_ratio"],
            pb_ratio=stock["pb_ratio"],
            roe=stock["roe"],
            debt_to_equity=stock["debt_to_equity"],
            payout_ratio=stock["payout_ratio"],
            price_vs_52w_high=-15.0,  # 15% abaixo da máxima
            price_vs_52w_low=25.0,    # 25% acima da mínima
            avg_volume=stock["avg_volume"],
            volatility=volatility,
            recommendation=recommendation,
            recommendation_reason=reason,
            score=score,
            suggested_entry_price=round(suggested_entry, 2),
            suggested_exit_price=round(suggested_exit, 2),
            expected_return=round(expected_return, 2),
            risk_level=risk,
            days_to_ex_date=days_to_ex,
            optimal_buy_window=f"{days_to_ex - 3} a {days_to_ex - 1} dias antes da data ex",
            optimal_sell_window="1 a 3 dias após a data ex"
        )


data_service = DividendDataService()


# ==================== ENDPOINTS ====================

@router.get("/")
async def dividend_bot_info():
    """Informações do Dividend Capture Bot."""
    settings = storage.get_settings()
    ops = storage.get_operations()
    active_ops = [o for o in ops if o.get('status') not in ['closed', 'cancelled']]
    
    return {
        "name": "VIRTUS Dividend Capture Bot",
        "version": "1.0.0",
        "description": "Bot para estratégia de captura de dividendos",
        "strategy": {
            "name": "Dividend Capture",
            "steps": [
                "1. Identificar ações com dividendos próximos",
                "2. Analisar fundamentals e timing",
                "3. Comprar antes da data ex-dividendo",
                "4. Receber o dividendo",
                "5. Vender após estabilização do preço"
            ]
        },
        "settings": settings,
        "stats": {
            "active_operations": len(active_ops),
            "total_operations": len(ops),
            "watchlist_size": len(storage.get_watchlist().get('stocks', []))
        }
    }


# ==================== DIVIDENDS CALENDAR ====================

# Cache para dados históricos (evita refetch)
_stock_data_cache: Dict[str, Dict] = {}

async def _get_stock_historical_data(ticker: str) -> Dict:
    """Busca dados históricos e score da ação."""
    if ticker in _stock_data_cache:
        return _stock_data_cache[ticker]
    
    result = {
        "avg_historical_dividend": None,
        "company_score": None,
        "sector": None
    }
    
    # Tenta usar o serviço real de dados
    if data_service._real_service:
        try:
            import asyncio
            real_svc = data_service._real_service
            
            # Busca dados da ação
            stock_data = await real_svc.get_stock_data(ticker)
            dividends = await real_svc.get_dividends(ticker)
            
            # Calcula média histórica
            if dividends and len(dividends) > 0:
                values = [d.get('value', 0) for d in dividends if d.get('value', 0) > 0]
                if values:
                    result["avg_historical_dividend"] = round(sum(values) / len(values), 4)
            
            # Score baseado em fundamentalistas
            if stock_data:
                score = 50  # Base
                
                # DY alto = bom
                dy = stock_data.get('dividend_yield', 0)
                if dy > 10: score += 15
                elif dy > 6: score += 10
                elif dy > 3: score += 5
                
                # P/L baixo = bom
                pe = stock_data.get('pe_ratio', 0)
                if 0 < pe < 8: score += 15
                elif 0 < pe < 12: score += 10
                elif 0 < pe < 18: score += 5
                
                # ROE alto = bom
                roe = stock_data.get('roe', 0)
                if roe > 20: score += 10
                elif roe > 15: score += 5
                
                # Payout saudável (não muito alto)
                payout = stock_data.get('payout_ratio', 0)
                if 30 <= payout <= 80: score += 10
                elif payout < 100: score += 5
                
                result["company_score"] = min(100, max(0, score))
                result["sector"] = stock_data.get('sector', 'Outros')
        except Exception as e:
            logger.warning(f"Erro ao buscar dados históricos para {ticker}: {e}")
    
    _stock_data_cache[ticker] = result
    return result


@router.get("/calendar", response_model=DividendCalendar)
async def get_dividend_calendar(
    days_ahead: int = Query(30, ge=1, le=90, description="Dias à frente")
):
    """
    Retorna calendário de dividendos.
    
    Mostra todas as datas ex-dividendo e pagamentos próximos.
    Inclui data limite de compra (1 dia antes da data ex) e média histórica.
    """
    dividends = data_service.get_upcoming_dividends(days_ahead)
    today = date.today()
    
    # Get active operations to mark "has_position"
    ops = storage.get_operations()
    active_tickers = {o['ticker'] for o in ops if o.get('status') == 'position_open'}
    
    events = []
    for div in dividends:
        # Busca dados históricos
        hist_data = await _get_stock_historical_data(div.ticker)
        
        # Calcula data limite de compra (1 dia útil antes da data ex)
        ex_date = date.fromisoformat(div.ex_date)
        buy_limit = ex_date - timedelta(days=1)
        # Se cair no fim de semana, volta para sexta
        while buy_limit.weekday() >= 5:  # 5=Sábado, 6=Domingo
            buy_limit -= timedelta(days=1)
        
        # Ex-date event
        events.append(CalendarEvent(
            date=div.ex_date,
            ticker=div.ticker,
            company_name=div.company_name,
            event_type="ex_date",
            dividend_value=div.value_per_share,
            dividend_yield=div.dividend_yield,
            has_position=div.ticker in active_tickers,
            buy_limit_date=buy_limit.isoformat(),
            avg_historical_dividend=hist_data.get("avg_historical_dividend"),
            company_score=hist_data.get("company_score"),
            sector=hist_data.get("sector")
        ))
        
        # Payment date event
        if div.payment_date:
            events.append(CalendarEvent(
                date=div.payment_date,
                ticker=div.ticker,
                company_name=div.company_name,
                event_type="payment_date",
                dividend_value=div.value_per_share,
                dividend_yield=div.dividend_yield,
                has_position=div.ticker in active_tickers,
                buy_limit_date=buy_limit.isoformat(),
                avg_historical_dividend=hist_data.get("avg_historical_dividend"),
                company_score=hist_data.get("company_score"),
                sector=hist_data.get("sector")
            ))
    
    # Sort by date
    events.sort(key=lambda x: x.date)
    
    # Filter for 7 and 30 days
    next_7 = [e for e in events if date.fromisoformat(e.date) <= today + timedelta(days=7)]
    next_30 = [e for e in events if date.fromisoformat(e.date) <= today + timedelta(days=30)]
    
    # Calculate total expected
    total_expected = sum(
        div.value_per_share 
        for div in dividends 
        if div.ticker in active_tickers
    )
    
    return DividendCalendar(
        events=events,
        total_expected_dividends=total_expected,
        next_7_days=next_7,
        next_30_days=next_30
    )


@router.get("/upcoming")
async def get_upcoming_dividends(
    min_yield: float = Query(3.0, description="Dividend Yield mínimo %"),
    days_ahead: int = Query(30, ge=1, le=90),
    sort_by: str = Query("ex_date", enum=["ex_date", "yield", "value"])
):
    """
    Lista dividendos próximos filtrados.
    
    Útil para identificar oportunidades de dividend capture.
    """
    dividends = data_service.get_upcoming_dividends(days_ahead)
    
    # Filter by yield
    filtered = [d for d in dividends if d.dividend_yield >= min_yield]
    
    # Sort
    if sort_by == "yield":
        filtered.sort(key=lambda x: x.dividend_yield, reverse=True)
    elif sort_by == "value":
        filtered.sort(key=lambda x: x.value_per_share, reverse=True)
    else:
        filtered.sort(key=lambda x: x.ex_date)
    
    return {
        "dividends": [d.dict() for d in filtered],
        "total": len(filtered),
        "filters": {
            "min_yield": min_yield,
            "days_ahead": days_ahead
        }
    }


# ==================== STOCK ANALYSIS ====================

@router.post("/analyze", response_model=StockAnalysis)
async def analyze_stock(request: StockAnalysisRequest):
    """
    Análise completa de ação para dividend capture.
    
    Retorna:
    - Dados do próximo dividendo
    - Análise fundamentalista
    - Recomendação de compra/venda
    - Timing sugerido
    """
    analysis = data_service.analyze_stock(request.ticker, request.investment_amount)
    return analysis


@router.get("/analyze/{ticker}")
async def analyze_stock_get(
    ticker: str,
    investment: float = Query(1000.0, description="Valor a investir R$")
):
    """Análise de ação via GET."""
    analysis = data_service.analyze_stock(ticker, investment)
    return analysis


@router.post("/analyze-batch")
async def analyze_multiple_stocks(tickers: List[str]):
    """
    Análise de múltiplas ações.
    
    Útil para comparar oportunidades.
    """
    results = []
    for ticker in tickers[:10]:  # Max 10
        try:
            analysis = data_service.analyze_stock(ticker)
            results.append(analysis.dict())
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})
    
    # Sort by score
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return {
        "analyses": results,
        "total": len(results),
        "best_opportunity": results[0] if results else None
    }


@router.get("/recommendations")
async def get_recommendations(
    min_score: float = Query(70.0, description="Score mínimo"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Retorna as melhores recomendações de dividend capture.
    """
    # Get all upcoming dividends and analyze
    dividends = data_service.get_upcoming_dividends(30)
    tickers = list(set(d.ticker for d in dividends))
    
    analyses = []
    for ticker in tickers:
        try:
            analysis = data_service.analyze_stock(ticker)
            if analysis.score >= min_score:
                analyses.append(analysis.dict())
        except:
            pass
    
    # Sort by score
    analyses.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        "recommendations": analyses[:limit],
        "total": len(analyses),
        "criteria": {
            "min_score": min_score,
            "strategy": "dividend_capture"
        }
    }


# ==================== OPERATIONS ====================

@router.get("/operations")
async def list_operations(
    status: Optional[str] = Query(None, description="Filtrar por status")
):
    """Lista todas as operações de dividend capture."""
    operations = storage.get_operations(status)
    
    # Group by status
    by_status = {}
    for op in operations:
        s = op.get('status', 'unknown')
        if s not in by_status:
            by_status[s] = []
        by_status[s].append(op)
    
    return {
        "operations": operations,
        "total": len(operations),
        "by_status": {k: len(v) for k, v in by_status.items()}
    }


@router.post("/operations")
async def create_operation(op: DividendOperationCreate):
    """
    Cria nova operação de dividend capture.
    
    Planeje a operação antes da data ex-dividendo.
    """
    import uuid
    
    now = datetime.now().isoformat()
    operation = {
        "id": str(uuid.uuid4())[:8],
        "ticker": op.ticker.upper(),
        "status": OperationStatus.PLANNED.value,
        "target_shares": op.target_shares,
        "max_entry_price": op.max_entry_price,
        "expected_dividend": op.expected_dividend,
        "ex_date": op.ex_date,
        "payment_date": op.payment_date,
        "bought_shares": 0,
        "avg_buy_price": 0.0,
        "total_invested": 0.0,
        "sold_shares": 0,
        "avg_sell_price": 0.0,
        "total_received": 0.0,
        "dividend_received": 0.0,
        "total_fees": 0.0,
        "gross_profit": 0.0,
        "net_profit": 0.0,
        "return_percentage": 0.0,
        "created_at": now,
        "updated_at": now,
        "notes": op.notes
    }
    
    storage.save_operation(operation)
    
    # Add to history
    storage.add_to_history({
        "type": "operation_created",
        "operation_id": operation["id"],
        "ticker": op.ticker,
        "timestamp": now
    })
    
    return {
        "success": True,
        "operation": operation,
        "message": f"Operação {operation['id']} criada para {op.ticker}"
    }


@router.get("/operations/{op_id}")
async def get_operation(op_id: str):
    """Retorna detalhes de uma operação."""
    operation = storage.get_operation(op_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operação não encontrada")
    
    # Add current analysis
    analysis = None
    try:
        analysis = data_service.analyze_stock(operation['ticker'])
    except:
        pass
    
    return {
        "operation": operation,
        "current_analysis": analysis.dict() if analysis else None
    }


@router.post("/operations/{op_id}/trade")
async def register_trade(op_id: str, trade: TradeExecution):
    """
    Registra execução de compra ou venda.
    """
    operation = storage.get_operation(op_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operação não encontrada")
    
    now = datetime.now().isoformat()
    
    if trade.action == "buy":
        # Update buy info
        total_shares = operation['bought_shares'] + trade.shares
        total_cost = (operation['avg_buy_price'] * operation['bought_shares']) + (trade.price * trade.shares)
        
        operation['bought_shares'] = total_shares
        operation['avg_buy_price'] = total_cost / total_shares if total_shares > 0 else 0
        operation['total_invested'] = total_cost
        operation['status'] = OperationStatus.POSITION_OPEN.value
        
    elif trade.action == "sell":
        # Update sell info
        total_shares = operation['sold_shares'] + trade.shares
        total_received = (operation['avg_sell_price'] * operation['sold_shares']) + (trade.price * trade.shares)
        
        operation['sold_shares'] = total_shares
        operation['avg_sell_price'] = total_received / total_shares if total_shares > 0 else 0
        operation['total_received'] = total_received
        
        # Check if fully closed
        if operation['sold_shares'] >= operation['bought_shares']:
            operation['status'] = OperationStatus.CLOSED.value
    
    # Update fees and profit
    operation['total_fees'] += trade.fees
    operation['gross_profit'] = (
        operation['total_received'] + 
        operation['dividend_received'] - 
        operation['total_invested']
    )
    operation['net_profit'] = operation['gross_profit'] - operation['total_fees']
    
    if operation['total_invested'] > 0:
        operation['return_percentage'] = (operation['net_profit'] / operation['total_invested']) * 100
    
    operation['updated_at'] = now
    
    storage.save_operation(operation)
    
    # Add to history
    storage.add_to_history({
        "type": f"trade_{trade.action}",
        "operation_id": op_id,
        "ticker": operation['ticker'],
        "shares": trade.shares,
        "price": trade.price,
        "timestamp": now
    })
    
    return {
        "success": True,
        "operation": operation,
        "message": f"Trade de {trade.action} registrado"
    }


@router.post("/operations/{op_id}/dividend")
async def register_dividend(
    op_id: str,
    amount: float = Query(..., description="Valor total do dividendo recebido")
):
    """Registra recebimento de dividendo."""
    operation = storage.get_operation(op_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operação não encontrada")
    
    now = datetime.now().isoformat()
    
    operation['dividend_received'] += amount
    operation['status'] = OperationStatus.DIVIDEND_RECEIVED.value
    
    # Recalculate profit
    operation['gross_profit'] = (
        operation['total_received'] + 
        operation['dividend_received'] - 
        operation['total_invested']
    )
    operation['net_profit'] = operation['gross_profit'] - operation['total_fees']
    
    if operation['total_invested'] > 0:
        operation['return_percentage'] = (operation['net_profit'] / operation['total_invested']) * 100
    
    operation['updated_at'] = now
    
    storage.save_operation(operation)
    
    storage.add_to_history({
        "type": "dividend_received",
        "operation_id": op_id,
        "ticker": operation['ticker'],
        "amount": amount,
        "timestamp": now
    })
    
    return {
        "success": True,
        "operation": operation,
        "message": f"Dividendo de R$ {amount:.2f} registrado"
    }


@router.delete("/operations/{op_id}")
async def cancel_operation(op_id: str):
    """Cancela uma operação."""
    operation = storage.get_operation(op_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operação não encontrada")
    
    if operation['bought_shares'] > 0:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível cancelar operação com posição aberta"
        )
    
    operation['status'] = OperationStatus.CANCELLED.value
    operation['updated_at'] = datetime.now().isoformat()
    storage.save_operation(operation)
    
    return {"success": True, "message": "Operação cancelada"}


# ==================== PORTFOLIO ====================

@router.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary():
    """
    Resumo do portfólio de dividend capture.
    """
    operations = storage.get_operations()
    
    closed_ops = [o for o in operations if o.get('status') == 'closed']
    active_ops = [o for o in operations if o.get('status') not in ['closed', 'cancelled']]
    
    total_invested = sum(o.get('total_invested', 0) for o in operations)
    total_dividends = sum(o.get('dividend_received', 0) for o in operations)
    total_capital_gains = sum(
        o.get('total_received', 0) - o.get('total_invested', 0) 
        for o in closed_ops
    )
    total_profit = sum(o.get('net_profit', 0) for o in closed_ops)
    
    # Success rate
    profitable_ops = len([o for o in closed_ops if o.get('net_profit', 0) > 0])
    success_rate = (profitable_ops / len(closed_ops) * 100) if closed_ops else 0
    
    # Best/worst
    if closed_ops:
        sorted_by_return = sorted(closed_ops, key=lambda x: x.get('return_percentage', 0))
        best = sorted_by_return[-1]
        worst = sorted_by_return[0]
    else:
        best = worst = None
    
    return PortfolioSummary(
        total_invested=total_invested,
        total_dividends_received=total_dividends,
        total_capital_gains=total_capital_gains,
        total_profit=total_profit,
        return_percentage=(total_profit / total_invested * 100) if total_invested > 0 else 0,
        active_operations=len(active_ops),
        completed_operations=len(closed_ops),
        success_rate=success_rate,
        best_operation={
            "ticker": best.get('ticker'),
            "return": best.get('return_percentage')
        } if best else None,
        worst_operation={
            "ticker": worst.get('ticker'),
            "return": worst.get('return_percentage')
        } if worst else None,
        monthly_dividend_projection=total_dividends / 12 if total_dividends > 0 else 0,
        annual_dividend_projection=total_dividends
    )


@router.get("/portfolio/history")
async def get_history(
    limit: int = Query(50, ge=1, le=200),
    type: Optional[str] = Query(None, description="Filtrar por tipo")
):
    """Retorna histórico de ações."""
    history = storage.get_history(limit)
    
    if type:
        history = [h for h in history if h.get('type') == type]
    
    return {
        "history": history,
        "total": len(history)
    }


# ==================== WATCHLIST ====================

@router.get("/watchlist")
async def get_watchlist():
    """Retorna watchlist de ações para dividend capture."""
    watchlist = storage.get_watchlist()
    stocks = watchlist.get('stocks', [])
    
    # Add current analysis for each
    enriched = []
    for stock in stocks:
        try:
            analysis = data_service.analyze_stock(stock['ticker'])
            enriched.append({
                **stock,
                "current_price": analysis.current_price,
                "next_dividend": analysis.next_dividend.dict() if analysis.next_dividend else None,
                "recommendation": analysis.recommendation.value,
                "score": analysis.score
            })
        except:
            enriched.append(stock)
    
    return {
        "stocks": enriched,
        "total": len(enriched)
    }


@router.post("/watchlist")
async def add_to_watchlist(stock: PortfolioAddStock):
    """Adiciona ação ao watchlist."""
    watchlist = storage.get_watchlist()
    stocks = watchlist.get('stocks', [])
    
    # Check if exists
    for s in stocks:
        if s['ticker'].upper() == stock.ticker.upper():
            raise HTTPException(status_code=400, detail="Ação já está no watchlist")
    
    stocks.append({
        "ticker": stock.ticker.upper(),
        "target_dividend_yield": stock.target_dividend_yield,
        "max_pe_ratio": stock.max_pe_ratio,
        "sectors": stock.sectors,
        "added_at": datetime.now().isoformat()
    })
    
    watchlist['stocks'] = stocks
    storage.save_watchlist(watchlist)
    
    return {"success": True, "message": f"{stock.ticker} adicionado ao watchlist"}


@router.delete("/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    """Remove ação do watchlist."""
    watchlist = storage.get_watchlist()
    stocks = watchlist.get('stocks', [])
    
    stocks = [s for s in stocks if s['ticker'].upper() != ticker.upper()]
    watchlist['stocks'] = stocks
    storage.save_watchlist(watchlist)
    
    return {"success": True, "message": f"{ticker} removido do watchlist"}


# ==================== SETTINGS ====================

@router.get("/settings")
async def get_settings():
    """Retorna configurações do bot."""
    return storage.get_settings()


@router.put("/settings")
async def update_settings(settings: Dict[str, Any]):
    """Atualiza configurações."""
    current = storage.get_settings()
    current.update(settings)
    storage.save_settings(current)
    return {"success": True, "settings": current}


# ==================== SIMULATION ====================

@router.post("/simulate")
async def simulate_dividend_capture(
    ticker: str = Query(...),
    investment: float = Query(1000.0),
    entry_days_before_ex: int = Query(3),
    exit_days_after_ex: int = Query(2)
):
    """
    Simula operação de dividend capture.
    
    Estima retorno baseado em dados históricos.
    """
    analysis = data_service.analyze_stock(ticker, investment)
    
    if not analysis.next_dividend:
        raise HTTPException(status_code=400, detail="Ação sem dividendo próximo")
    
    current_price = analysis.current_price
    dividend = analysis.next_dividend.value_per_share
    
    # Simulate entry (assume slight premium before ex-date)
    entry_price = current_price * 1.005  # 0.5% premium
    shares = int(investment / entry_price)
    actual_investment = shares * entry_price
    
    # Simulate exit (assume price drops by ~dividend amount after ex-date)
    exit_price = entry_price - (dividend * 0.8)  # 80% of dividend drop
    
    # Calculate
    total_dividends = shares * dividend
    sale_proceeds = shares * exit_price
    gross_profit = (sale_proceeds - actual_investment) + total_dividends
    
    # Estimate fees (corretagem + emolumentos + IR sobre dividendos se JCP)
    fees = (actual_investment + sale_proceeds) * 0.0003  # ~0.03% each way
    
    net_profit = gross_profit - fees
    return_pct = (net_profit / actual_investment) * 100
    
    return {
        "simulation": {
            "ticker": ticker,
            "investment": investment,
            "actual_investment": round(actual_investment, 2),
            "shares": shares,
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "dividend_per_share": dividend,
            "total_dividends": round(total_dividends, 2),
            "sale_proceeds": round(sale_proceeds, 2),
            "capital_gain_loss": round(sale_proceeds - actual_investment, 2),
            "estimated_fees": round(fees, 2),
            "gross_profit": round(gross_profit, 2),
            "net_profit": round(net_profit, 2),
            "return_percentage": round(return_pct, 2)
        },
        "parameters": {
            "entry_days_before_ex": entry_days_before_ex,
            "exit_days_after_ex": exit_days_after_ex
        },
        "analysis": {
            "recommendation": analysis.recommendation.value,
            "score": analysis.score,
            "risk": analysis.risk_level
        },
        "note": "Esta é uma simulação. Resultados reais podem variar."
    }

# ==================== REAL DATA ENDPOINTS ====================

@router.get("/real/upcoming")
async def get_real_upcoming_dividends(
    days_ahead: int = Query(30, ge=1, le=60),
    min_yield: float = Query(0, ge=0)
):
    """
    Retorna dividendos próximos usando dados reais.
    
    Fontes: Yahoo Finance, Brapi, StatusInvest
    """
    if not REAL_SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Serviço de dados reais não disponível. Verifique se as dependências estão instaladas (yfinance, beautifulsoup4)."
        )
    
    service = get_dividend_data_service()
    upcoming = await service.get_upcoming_dividends(days_ahead=days_ahead, min_yield=min_yield)
    
    return {
        "dividends": [
            {
                "ticker": d.ticker,
                "company_name": d.company_name,
                "sector": d.sector,
                "current_price": d.current_price,
                "dividend_type": d.dividend_type,
                "value_per_share": d.value_per_share,
                "ex_date": d.ex_date,
                "payment_date": d.payment_date,
                "dividend_yield": d.dividend_yield,
                "days_to_ex": d.days_to_ex,
                "annual_yield": d.annual_yield,
                "recommendation": d.recommendation,
                "score": d.score
            }
            for d in upcoming
        ],
        "total": len(upcoming),
        "source": "combined_apis",
        "updated_at": datetime.now().isoformat()
    }


@router.get("/real/analyze/{ticker}")
async def get_real_stock_analysis(ticker: str):
    """
    Análise de ação com dados reais.
    
    Combina múltiplas fontes para análise fundamentalista.
    """
    if not REAL_SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Serviço de dados reais não disponível."
        )
    
    service = get_dividend_data_service()
    fundamentals = await service.get_fundamentals(ticker)
    dividends = await service.get_dividends(ticker)
    
    return {
        "ticker": fundamentals.ticker,
        "company_name": fundamentals.company_name,
        "sector": fundamentals.sector,
        "current_price": fundamentals.current_price,
        "fundamentals": {
            "dividend_yield": fundamentals.dividend_yield,
            "annual_dividend": fundamentals.annual_dividend,
            "payout_ratio": fundamentals.payout_ratio,
            "dividend_consistency": fundamentals.dividend_consistency,
            "pe_ratio": fundamentals.pe_ratio,
            "pb_ratio": fundamentals.pb_ratio,
            "roe": fundamentals.roe,
            "debt_to_equity": fundamentals.debt_to_equity,
            "market_cap": fundamentals.market_cap,
            "avg_volume": fundamentals.avg_volume,
            "volatility_30d": fundamentals.volatility_30d,
            "price_52w_high": fundamentals.price_52w_high,
            "price_52w_low": fundamentals.price_52w_low
        },
        "dividend_history": dividends[:8],
        "source": fundamentals.source,
        "last_update": fundamentals.last_update
    }


@router.get("/real/quote/{ticker}")
async def get_real_quote(ticker: str):
    """
    Cotação atual com dados reais.
    """
    if not REAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Serviço não disponível.")
    
    service = get_dividend_data_service()
    data = await service.get_stock_data(ticker)
    
    return {
        "ticker": data.get("ticker", ticker),
        "company_name": data.get("company_name", ticker),
        "current_price": data.get("current_price", 0),
        "previous_close": data.get("previous_close", 0),
        "dividend_yield": data.get("dividend_yield", 0),
        "pe_ratio": data.get("pe_ratio", 0),
        "market_cap": data.get("market_cap", 0),
        "avg_volume": data.get("avg_volume", 0),
        "52w_high": data.get("52w_high", 0),
        "52w_low": data.get("52w_low", 0),
        "source": data.get("source", "unknown"),
        "last_update": data.get("last_update", datetime.now().isoformat())
    }


# ==================== SOCIAL MEDIA INTEGRATION ====================

@router.get("/social/daily-opportunities")
async def get_social_daily_opportunities():
    """
    Gera conteúdo para redes sociais - Oportunidades diárias.
    
    Retorna texto formatado para post e dados estruturados.
    """
    if not REAL_SERVICE_AVAILABLE:
        # Fallback com mock
        return {
            "title": "📊 Top Dividendos da Semana",
            "content": "⚠️ Serviço de dados reais não disponível. Configure as APIs.",
            "hashtags": "#dividendos #acoes #b3",
            "data": []
        }
    
    service = get_dividend_data_service()
    generator = DividendSocialGenerator(service)
    
    return await generator.generate_daily_opportunities()


@router.get("/social/stock-analysis/{ticker}")
async def get_social_stock_analysis(ticker: str):
    """
    Gera análise de ação formatada para redes sociais.
    """
    if not REAL_SERVICE_AVAILABLE:
        return {
            "title": f"📊 Análise {ticker}",
            "content": "⚠️ Serviço de dados reais não disponível.",
            "hashtags": f"#{ticker.lower()} #dividendos",
            "data": {}
        }
    
    service = get_dividend_data_service()
    generator = DividendSocialGenerator(service)
    
    return await generator.generate_stock_analysis(ticker)


@router.get("/social/weekly-summary")
async def get_social_weekly_summary():
    """
    Gera resumo semanal para redes sociais.
    """
    if not REAL_SERVICE_AVAILABLE:
        return {
            "title": "📅 Resumo Semanal",
            "content": "⚠️ Serviço não disponível.",
            "hashtags": "#dividendos #resumo",
            "data": {}
        }
    
    service = get_dividend_data_service()
    generator = DividendSocialGenerator(service)
    
    return await generator.generate_weekly_summary()


# ==================== HEALTH & STATUS ====================

@router.get("/health")
async def dividend_bot_health():
    """Status de saúde do módulo de dividendos."""
    checks = {
        "storage": True,
        "real_data_service": REAL_SERVICE_AVAILABLE,
        "yahoo_finance": False,
        "brapi": False,
        "statusinvest": False
    }
    
    # Testa disponibilidade do yfinance
    try:
        import yfinance
        checks["yahoo_finance"] = True
    except ImportError:
        pass
    
    # Testa Brapi
    import os
    if os.environ.get("BRAPI_API_KEY"):
        checks["brapi"] = True
    
    # Testa BeautifulSoup
    try:
        from bs4 import BeautifulSoup
        checks["statusinvest"] = True
    except ImportError:
        pass
    
    all_ok = all(v for k, v in checks.items() if k == "storage")
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
        "message": "Para dados reais, instale: pip install yfinance beautifulsoup4 aiohttp",
        "brapi_key_configured": bool(os.environ.get("BRAPI_API_KEY")),
        "timestamp": datetime.now().isoformat()
    }