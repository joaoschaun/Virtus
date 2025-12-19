"""
VIRTUS - Dividend Brain (Inteligência de Dividendos)
=====================================================

Sistema inteligente para:
1. Identificar melhores oportunidades de dividend capture
2. Gerar alertas de compra/venda
3. Otimizar alocação do portfólio
4. Criar planos de ação personalizados

Estratégias:
- Dividend Capture: Comprar antes, vender depois do ex
- Buy & Hold: Foco em yield on cost
- Income: Maximizar renda mensal
"""

import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Paths
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
DATA_PATH = BRAIN_PATH / "data"
BRAIN_DATA_PATH = DATA_PATH / "dividend_brain"
BRAIN_DATA_PATH.mkdir(parents=True, exist_ok=True)


class Strategy(str, Enum):
    """Estratégias de investimento."""
    DIVIDEND_CAPTURE = "dividend_capture"  # Comprar antes, vender depois
    BUY_AND_HOLD = "buy_and_hold"         # Manter para longo prazo
    INCOME_FOCUS = "income_focus"          # Maximizar renda mensal
    HYBRID = "hybrid"                       # Combinação das estratégias


class AlertType(str, Enum):
    """Tipo de alerta."""
    BUY_SIGNAL = "buy_signal"
    SELL_SIGNAL = "sell_signal"
    EX_DATE_APPROACHING = "ex_date_approaching"
    DIVIDEND_RECEIVED = "dividend_received"
    PRICE_DROP = "price_drop"
    OPPORTUNITY = "opportunity"


@dataclass
class TradingSignal:
    """Sinal de trading gerado pelo Brain."""
    id: str
    ticker: str
    company_name: str
    signal_type: str  # 'buy' ou 'sell'
    strategy: str
    reason: str
    
    # Preços
    current_price: float
    target_entry: float
    target_exit: float
    stop_loss: float
    
    # Timing
    suggested_buy_date: str
    ex_date: str
    suggested_sell_date: str
    
    # Dividendos
    expected_dividend: float
    dividend_yield: float
    
    # Análise
    score: float  # 0-100
    risk_level: str  # 'low', 'medium', 'high'
    expected_return: float  # % esperado total
    
    # Meta
    created_at: str
    valid_until: str
    status: str  # 'active', 'executed', 'expired', 'cancelled'


@dataclass
class ActionPlan:
    """Plano de ação gerado pelo Brain."""
    id: str
    name: str
    strategy: Strategy
    
    # Capital
    available_capital: float
    allocated_capital: float
    
    # Ações
    actions: List[Dict]  # Lista de TradingSignals simplificados
    
    # Projeções
    expected_dividends: float
    expected_return: float
    
    # Timing
    start_date: str
    end_date: str
    
    # Status
    status: str  # 'pending', 'in_progress', 'completed'
    created_at: str


class DividendBrain:
    """Inteligência artificial para estratégias de dividendos."""
    
    def __init__(self):
        self.signals_file = BRAIN_DATA_PATH / "signals.json"
        self.plans_file = BRAIN_DATA_PATH / "action_plans.json"
        self.alerts_file = BRAIN_DATA_PATH / "alerts.json"
        self.config_file = BRAIN_DATA_PATH / "brain_config.json"
        
        self._ensure_files()
        self._data_service = None
        self._portfolio_service = None
    
    def _ensure_files(self):
        for file in [self.signals_file, self.plans_file, self.alerts_file]:
            if not file.exists():
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
        if not self.config_file.exists():
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._default_config(), f, indent=2)
    
    def _default_config(self) -> Dict:
        return {
            'strategy': Strategy.HYBRID.value,
            'risk_tolerance': 'medium',  # low, medium, high
            'min_dividend_yield': 4.0,
            'max_pe_ratio': 15.0,
            'min_liquidity': 1000000,
            'buy_days_before_ex': 5,
            'sell_days_after_ex': 1,
            'max_position_percent': 20.0,  # Máximo % do portfólio em uma ação
            'sectors_preference': ['Energia Elétrica', 'Bancos', 'Seguros'],
            'sectors_avoid': [],
            'auto_alerts': True,
            'notification_channels': ['dashboard']
        }
    
    def _load_json(self, file: Path) -> Any:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_json(self, file: Path, data: Any):
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    async def _get_data_service(self):
        if self._data_service is None:
            try:
                from services.dividend_data_service import get_dividend_data_service
                self._data_service = get_dividend_data_service()
            except:
                pass
        return self._data_service
    
    async def _get_portfolio_service(self):
        if self._portfolio_service is None:
            try:
                from services.dividend_portfolio_service import get_portfolio_service
                self._portfolio_service = get_portfolio_service()
            except:
                pass
        return self._portfolio_service
    
    def get_config(self) -> Dict:
        """Retorna configuração do Brain."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                defaults = self._default_config()
                for k, v in defaults.items():
                    if k not in config:
                        config[k] = v
                return config
        except:
            return self._default_config()
    
    def update_config(self, config: Dict) -> Dict:
        """Atualiza configuração."""
        current = self.get_config()
        current.update(config)
        self._save_json(self.config_file, current)
        return current
    
    # ==================== ANÁLISE E SINAIS ====================
    
    async def analyze_opportunities(self, capital: float = 10000) -> List[TradingSignal]:
        """
        Analisa oportunidades e gera sinais de trading.
        
        Args:
            capital: Capital disponível para investir
        
        Returns:
            Lista de sinais ordenados por score
        """
        data_service = await self._get_data_service()
        if not data_service:
            return []
        
        config = self.get_config()
        signals = []
        
        # Busca próximos dividendos
        upcoming = await data_service.get_upcoming_dividends(
            days_ahead=30, 
            min_yield=config['min_dividend_yield']
        )
        
        today = date.today()
        
        for div in upcoming:
            try:
                # Pula se não atende critérios básicos
                if div.days_to_ex < 2:  # Muito próximo
                    continue
                
                if div.days_to_ex > config['buy_days_before_ex'] + 10:  # Muito longe
                    continue
                
                # Verifica setor
                if config['sectors_avoid'] and div.sector in config['sectors_avoid']:
                    continue
                
                # Busca dados fundamentalistas
                stock_data = await data_service.get_stock_data(div.ticker)
                
                pe_ratio = stock_data.get('pe_ratio', 0)
                if pe_ratio > config['max_pe_ratio'] and pe_ratio > 0:
                    continue
                
                # Calcula score
                score = self._calculate_opportunity_score(div, stock_data, config)
                
                if score < 50:  # Score mínimo
                    continue
                
                # Calcula preços alvo
                current_price = div.current_price
                target_entry = current_price * 0.98  # 2% abaixo
                stop_loss = current_price * 0.95  # 5% abaixo
                
                # Para dividend capture, vende após ex-date
                # Espera-se queda do preço da ação pelo valor do dividendo
                expected_price_drop = div.value_per_share
                target_exit = current_price - (expected_price_drop * 0.5)  # Conservador
                
                # Calcula retorno esperado
                dividend_return = (div.value_per_share / current_price) * 100
                price_return = ((target_exit - target_entry) / target_entry) * 100
                total_return = dividend_return + price_return
                
                # Datas sugeridas
                ex_date = datetime.strptime(div.ex_date, '%Y-%m-%d').date()
                buy_date = ex_date - timedelta(days=config['buy_days_before_ex'])
                sell_date = ex_date + timedelta(days=config['sell_days_after_ex'])
                
                # Define nível de risco
                risk_level = 'medium'
                if score >= 75 and pe_ratio < 10:
                    risk_level = 'low'
                elif score < 60 or pe_ratio > 15:
                    risk_level = 'high'
                
                # Determina tipo de sinal
                if div.days_to_ex <= config['buy_days_before_ex']:
                    signal_type = 'buy'
                    reason = f"Data Ex em {div.days_to_ex} dias. Comprar para garantir dividendo de {div.dividend_yield:.1f}%"
                else:
                    signal_type = 'watch'
                    reason = f"Oportunidade em {div.days_to_ex - config['buy_days_before_ex']} dias"
                
                signal = TradingSignal(
                    id=f"SIG-{div.ticker}-{today.strftime('%Y%m%d')}",
                    ticker=div.ticker,
                    company_name=div.company_name,
                    signal_type=signal_type,
                    strategy=config['strategy'],
                    reason=reason,
                    current_price=current_price,
                    target_entry=round(target_entry, 2),
                    target_exit=round(target_exit, 2),
                    stop_loss=round(stop_loss, 2),
                    suggested_buy_date=buy_date.isoformat(),
                    ex_date=div.ex_date,
                    suggested_sell_date=sell_date.isoformat(),
                    expected_dividend=div.value_per_share,
                    dividend_yield=div.dividend_yield,
                    score=score,
                    risk_level=risk_level,
                    expected_return=round(total_return, 2),
                    created_at=datetime.now().isoformat(),
                    valid_until=(ex_date - timedelta(days=1)).isoformat(),
                    status='active'
                )
                
                signals.append(signal)
                
            except Exception as e:
                logger.warning(f"Error analyzing {div.ticker}: {e}")
                continue
        
        # Ordena por score
        signals.sort(key=lambda x: x.score, reverse=True)
        
        # Salva sinais
        self._save_signals(signals)
        
        return signals
    
    def _calculate_opportunity_score(self, dividend, stock_data: Dict, config: Dict) -> float:
        """Calcula score de oportunidade (0-100)."""
        score = 50.0  # Base
        
        # Dividend Yield (+30 max)
        dy = dividend.annual_yield if hasattr(dividend, 'annual_yield') else dividend.dividend_yield * 4
        if dy >= 12:
            score += 30
        elif dy >= 8:
            score += 20
        elif dy >= 6:
            score += 15
        elif dy >= 4:
            score += 10
        
        # P/L (+15 max)
        pe = stock_data.get('pe_ratio', 0)
        if 0 < pe < 8:
            score += 15
        elif pe < 12:
            score += 10
        elif pe < 15:
            score += 5
        elif pe > 20:
            score -= 10
        
        # ROE (+10 max)
        roe = stock_data.get('roe', 0)
        if roe >= 20:
            score += 10
        elif roe >= 15:
            score += 7
        elif roe >= 10:
            score += 5
        
        # Timing (+15 max) - Melhor: 3-7 dias antes do ex
        days = dividend.days_to_ex
        if 3 <= days <= 7:
            score += 15
        elif 2 <= days <= 10:
            score += 10
        elif days < 2:
            score -= 15  # Muito arriscado
        
        # Volume/Liquidez (+10 max)
        volume = stock_data.get('avg_volume', 0)
        if volume >= 10000000:
            score += 10
        elif volume >= 1000000:
            score += 5
        elif volume < 100000:
            score -= 10
        
        # Setor preferido (+10)
        sector = stock_data.get('sector', '')
        if sector in config.get('sectors_preference', []):
            score += 10
        
        # Dívida (-10 se alta)
        debt = stock_data.get('debt_to_equity', 0)
        if debt > 150:
            score -= 10
        
        return min(100, max(0, score))
    
    def _save_signals(self, signals: List[TradingSignal]):
        """Salva sinais."""
        data = [asdict(s) for s in signals]
        self._save_json(self.signals_file, data)
    
    def get_active_signals(self) -> List[Dict]:
        """Retorna sinais ativos."""
        signals = self._load_json(self.signals_file)
        today = date.today().isoformat()
        return [s for s in signals if s.get('status') == 'active' and s.get('valid_until', '') >= today]
    
    # ==================== PLANOS DE AÇÃO ====================
    
    async def create_action_plan(self, capital: float, strategy: Strategy = Strategy.HYBRID,
                                  duration_days: int = 30) -> ActionPlan:
        """
        Cria plano de ação personalizado.
        
        Args:
            capital: Capital disponível
            strategy: Estratégia a usar
            duration_days: Duração do plano em dias
        """
        signals = await self.analyze_opportunities(capital)
        config = self.get_config()
        
        # Filtra sinais de compra
        buy_signals = [s for s in signals if s.signal_type == 'buy' and s.score >= 60]
        
        # Aloca capital (máximo por posição)
        max_per_position = capital * (config['max_position_percent'] / 100)
        
        actions = []
        allocated = 0
        
        for signal in buy_signals[:10]:  # Máximo 10 ações
            if allocated >= capital:
                break
            
            # Calcula quantidade de ações
            position_value = min(max_per_position, capital - allocated)
            shares = int(position_value / signal.current_price)
            
            if shares < 1:
                continue
            
            action_value = shares * signal.current_price
            expected_dividend = shares * signal.expected_dividend
            
            actions.append({
                'ticker': signal.ticker,
                'company_name': signal.company_name,
                'action': 'buy',
                'shares': shares,
                'price': signal.current_price,
                'total': action_value,
                'buy_date': signal.suggested_buy_date,
                'ex_date': signal.ex_date,
                'sell_date': signal.suggested_sell_date,
                'expected_dividend': expected_dividend,
                'dividend_yield': signal.dividend_yield,
                'score': signal.score
            })
            
            allocated += action_value
        
        # Calcula totais
        total_expected_dividends = sum(a['expected_dividend'] for a in actions)
        expected_return = (total_expected_dividends / allocated * 100) if allocated > 0 else 0
        
        today = date.today()
        plan = ActionPlan(
            id=f"PLAN-{today.strftime('%Y%m%d')}-{len(actions)}",
            name=f"Plano {strategy.value.replace('_', ' ').title()} - {today.strftime('%d/%m/%Y')}",
            strategy=strategy,
            available_capital=capital,
            allocated_capital=allocated,
            actions=actions,
            expected_dividends=total_expected_dividends,
            expected_return=round(expected_return, 2),
            start_date=today.isoformat(),
            end_date=(today + timedelta(days=duration_days)).isoformat(),
            status='pending',
            created_at=datetime.now().isoformat()
        )
        
        # Salva plano
        plans = self._load_json(self.plans_file)
        plans.append(asdict(plan))
        self._save_json(self.plans_file, plans)
        
        return plan
    
    def get_action_plans(self) -> List[Dict]:
        """Retorna planos de ação."""
        return self._load_json(self.plans_file)
    
    # ==================== ALERTAS ====================
    
    async def check_alerts(self) -> List[Dict]:
        """Verifica e gera alertas."""
        config = self.get_config()
        if not config.get('auto_alerts'):
            return []
        
        data_service = await self._get_data_service()
        portfolio_service = await self._get_portfolio_service()
        
        alerts = []
        today = date.today()
        
        # 1. Alertas de data ex se aproximando
        if data_service:
            upcoming = await data_service.get_upcoming_dividends(days_ahead=10)
            
            for div in upcoming:
                if div.days_to_ex <= config['buy_days_before_ex']:
                    alerts.append({
                        'type': AlertType.EX_DATE_APPROACHING.value,
                        'ticker': div.ticker,
                        'title': f'Data Ex de {div.ticker} em {div.days_to_ex} dias',
                        'message': f'{div.company_name} - Ex: {div.ex_date}. Dividendo: R$ {div.value_per_share:.2f} ({div.dividend_yield:.1f}%)',
                        'priority': 'high' if div.days_to_ex <= 2 else 'medium',
                        'created_at': datetime.now().isoformat()
                    })
        
        # 2. Alertas de posições (se tiver portfólio)
        if portfolio_service:
            positions = await portfolio_service.get_positions()
            projections = await portfolio_service.get_dividend_projections(30)
            
            for proj in projections:
                ex_date = datetime.strptime(proj.ex_date, '%Y-%m-%d').date()
                days_to_ex = (ex_date - today).days
                
                if 0 <= days_to_ex <= 2:
                    alerts.append({
                        'type': AlertType.DIVIDEND_RECEIVED.value,
                        'ticker': proj.ticker,
                        'title': f'Dividendo de {proj.ticker} garantido!',
                        'message': f'Você receberá R$ {proj.total_expected:.2f} em {proj.payment_date or "breve"}',
                        'priority': 'low',
                        'created_at': datetime.now().isoformat()
                    })
        
        # Salva alertas
        self._save_json(self.alerts_file, alerts)
        
        return alerts
    
    def get_alerts(self) -> List[Dict]:
        """Retorna alertas."""
        return self._load_json(self.alerts_file)
    
    # ==================== RECOMENDAÇÕES ====================
    
    async def get_recommendations(self, capital: float = 10000) -> Dict:
        """
        Gera recomendações personalizadas.
        
        Retorna:
        - Melhores oportunidades
        - Ações para evitar
        - Sugestão de alocação
        """
        signals = await self.analyze_opportunities(capital)
        config = self.get_config()
        
        # Melhores oportunidades
        top_opportunities = [
            {
                'ticker': s.ticker,
                'company_name': s.company_name,
                'score': s.score,
                'dividend_yield': s.dividend_yield,
                'days_to_ex': (datetime.strptime(s.ex_date, '%Y-%m-%d').date() - date.today()).days,
                'expected_return': s.expected_return,
                'reason': s.reason
            }
            for s in signals[:5] if s.score >= 60
        ]
        
        # Ações para evitar (score baixo)
        avoid = [
            {
                'ticker': s.ticker,
                'reason': f'Score baixo ({s.score:.0f}), risco {s.risk_level}'
            }
            for s in signals if s.score < 50
        ][:3]
        
        # Sugestão de alocação
        allocation = []
        remaining = capital
        max_per_position = capital * (config['max_position_percent'] / 100)
        
        for s in signals[:5]:
            if remaining <= 0:
                break
            position = min(max_per_position, remaining)
            shares = int(position / s.current_price)
            if shares > 0:
                allocation.append({
                    'ticker': s.ticker,
                    'shares': shares,
                    'value': shares * s.current_price,
                    'expected_dividend': shares * s.expected_dividend
                })
                remaining -= shares * s.current_price
        
        total_allocated = capital - remaining
        total_dividends = sum(a['expected_dividend'] for a in allocation)
        
        return {
            'top_opportunities': top_opportunities,
            'avoid': avoid,
            'suggested_allocation': allocation,
            'summary': {
                'capital': capital,
                'allocated': total_allocated,
                'remaining': remaining,
                'expected_dividends': total_dividends,
                'expected_yield': (total_dividends / total_allocated * 100) if total_allocated > 0 else 0
            },
            'generated_at': datetime.now().isoformat()
        }


# Singleton
_dividend_brain: Optional[DividendBrain] = None

def get_dividend_brain() -> DividendBrain:
    global _dividend_brain
    if _dividend_brain is None:
        _dividend_brain = DividendBrain()
    return _dividend_brain
