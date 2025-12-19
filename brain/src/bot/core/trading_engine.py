"""
VIRTUS Trading Engine
======================

Motor de trading integrado que coordena:
- Estratégias avançadas
- Risk management (Kelly, VaR)
- Exit management (8 tipos de trailing)
- Position supervision
- ML predictions
- Analysis pipeline

Este é o cérebro operacional do bot de trading.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import numpy as np

from ...core import (
    VirtusLogger, Signal, SignalType, Position, PositionStatus,
    Timeframe
)
from ...risk import RiskManager
from ...risk.advanced_risk import AdvancedRiskManager
from ...positions.exits import ExitManager, TrailingType
from ...positions.supervisor.position_supervisor import PositionSupervisor, PositionHealth
from ...strategies.scalping.scalping_strategy import ScalpingStrategy
from ...strategies.trend.trend_strategy import TrendStrategy
from ...strategies.reversal.reversal_strategy import ReversalStrategy
from ...strategies.event.event_strategy import EventStrategy
from ...ml.models.prediction_engine import PredictionService, EnsemblePrediction
from ...analysis.master_analyzer import MasterTechnicalAnalyzer as MasterAnalyzer


class TradingMode(Enum):
    """Modos de operação do engine."""
    SCALPING = "scalping"          # Scalping agressivo
    TREND_FOLLOWING = "trend"      # Seguir tendência
    REVERSAL = "reversal"          # Reversões
    EVENT_DRIVEN = "event"         # Baseado em eventos
    ADAPTIVE = "adaptive"          # Adaptativo (auto-seleção)
    CONSERVATIVE = "conservative"  # Conservador (todos validam)


class ExecutionMode(Enum):
    """Modos de execução."""
    AGGRESSIVE = "aggressive"  # Entrada imediata
    NORMAL = "normal"         # Confirmação padrão
    CONSERVATIVE = "conservative"  # Múltiplas confirmações


@dataclass
class TradeDecision:
    """Decisão de trade integrada."""
    should_trade: bool
    direction: str  # "buy", "sell", "none"
    confidence: float
    
    # Detalhes
    strategy_used: str
    setup_name: str
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    
    # Risk metrics
    risk_reward: float
    kelly_fraction: float
    var_impact: float
    
    # Confirmations
    ml_prediction: Optional[EnsemblePrediction] = None
    analysis_score: float = 0.0
    confirmations: List[str] = field(default_factory=list)
    rejections: List[str] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    execution_mode: ExecutionMode = ExecutionMode.NORMAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'should_trade': self.should_trade,
            'direction': self.direction,
            'confidence': round(self.confidence, 4),
            'strategy': self.strategy_used,
            'setup': self.setup_name,
            'entry': round(self.entry_price, 5),
            'sl': round(self.stop_loss, 5),
            'tp': round(self.take_profit, 5),
            'size': round(self.position_size, 2),
            'risk_reward': round(self.risk_reward, 2),
            'confirmations': self.confirmations,
            'rejections': self.rejections,
        }


@dataclass
class EngineStatistics:
    """Estatísticas do engine."""
    # Análises
    total_analyses: int = 0
    signals_generated: int = 0
    signals_filtered: int = 0
    signals_executed: int = 0
    
    # Trades
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    max_drawdown: float = 0.0
    
    # Por estratégia
    strategy_wins: Dict[str, int] = field(default_factory=dict)
    strategy_losses: Dict[str, int] = field(default_factory=dict)
    
    # Performance
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Time tracking
    started_at: datetime = field(default_factory=datetime.now)
    last_trade_at: Optional[datetime] = None
    
    @property
    def win_rate(self) -> float:
        """Taxa de acerto."""
        total = self.winning_trades + self.losing_trades
        return self.winning_trades / total if total > 0 else 0.0
    
    @property
    def profit_factor(self) -> float:
        """Profit factor."""
        if self.avg_loss == 0:
            return 0.0
        gross_profit = self.avg_win * self.winning_trades
        gross_loss = abs(self.avg_loss) * self.losing_trades
        return gross_profit / gross_loss if gross_loss > 0 else 0.0
    
    def record_trade(self, profit: float, strategy: str) -> None:
        """Registra resultado de trade."""
        self.total_trades += 1
        self.total_profit += profit
        self.last_trade_at = datetime.now()
        
        if profit >= 0:
            self.winning_trades += 1
            self.best_trade = max(self.best_trade, profit)
            self.strategy_wins[strategy] = self.strategy_wins.get(strategy, 0) + 1
        else:
            self.losing_trades += 1
            self.worst_trade = min(self.worst_trade, profit)
            self.strategy_losses[strategy] = self.strategy_losses.get(strategy, 0) + 1
        
        # Atualiza médias
        if self.winning_trades > 0:
            wins = [self.best_trade]  # Simplificado
            self.avg_win = self.total_profit / self.winning_trades if self.total_profit > 0 else 0
        if self.losing_trades > 0:
            self.avg_loss = self.total_profit / self.losing_trades if self.total_profit < 0 else 0


class TradingEngine:
    """
    Motor de Trading Integrado VIRTUS.
    
    Coordena todos os componentes avançados:
    - Múltiplas estratégias (Scalping, Trend, Reversal, Event)
    - Risk management avançado (Kelly, VaR, Anti-Martingale)
    - Exit management (8 tipos de trailing stop)
    - Position supervision (monitoramento real-time)
    - ML predictions (ensemble learning)
    - Analysis pipeline (20 analisadores)
    
    Features:
    - Adaptive strategy selection
    - Multi-timeframe validation
    - Confluence scoring
    - Smart position sizing
    - Dynamic risk adjustment
    - Performance tracking
    """
    
    def __init__(
        self,
        symbol: str,
        mode: TradingMode = TradingMode.ADAPTIVE,
        execution_mode: ExecutionMode = ExecutionMode.NORMAL,
        risk_per_trade: float = 0.01,  # 1% por trade
        enabled_strategies: Optional[List[str]] = None,  # Estratégias habilitadas do YAML
        bot_config: Optional[Dict[str, Any]] = None,  # Configuração completa do bot YAML
    ):
        self.symbol = symbol
        self.mode = mode
        self.execution_mode = execution_mode
        self.risk_per_trade = risk_per_trade
        self.enabled_strategies = enabled_strategies or []  # Lista de estratégias do YAML
        self.bot_config = bot_config or {}  # Config completa do bot
        
        self.logger = VirtusLogger.get_logger(f"trading_engine.{symbol.lower()}")
        
        # Componentes
        self.analyzer: Optional[MasterAnalyzer] = None
        self.risk_manager: Optional[AdvancedRiskManager] = None
        self.exit_manager: Optional[ExitManager] = None
        self.position_supervisor: Optional[PositionSupervisor] = None
        self.prediction_service: Optional[PredictionService] = None
        
        # Estratégias
        self.scalping_strategy: Optional[ScalpingStrategy] = None
        self.trend_strategy: Optional[TrendStrategy] = None
        self.reversal_strategy: Optional[ReversalStrategy] = None
        self.event_strategy: Optional[EventStrategy] = None
        
        # Estado
        self._initialized = False
        self._active_strategy: Optional[str] = None
        
        # Estatísticas
        self.statistics = EngineStatistics()
        
        # Decision history
        self._decisions: deque = deque(maxlen=1000)
        
        # Configuração por modo - usa estratégias do YAML se fornecidas
        self._mode_config = self._get_mode_config(mode)
        
        # Sobrescreve estratégias do modo com as do YAML se fornecidas
        if self.enabled_strategies:
            self._mode_config['strategies'] = self.enabled_strategies
            self.logger.info(f"📊 Usando estratégias do YAML: {self.enabled_strategies}")
        
        # Thresholds - AGRESSIVO para mais trades
        self._min_confluence = 0.35  # Muito agressivo
        self._min_ml_confidence = 0.45  # Aceita menor confiança ML
        self._min_risk_reward = 1.0  # Aceita R:R 1:1
        
    def _get_mode_config(self, mode: TradingMode) -> Dict[str, Any]:
        """Obtém configuração por modo."""
        configs = {
            TradingMode.SCALPING: {
                'primary_timeframe': Timeframe.M1,
                'confirmation_timeframe': Timeframe.M5,
                'min_confluence': 0.30,  # AGRESSIVO
                'min_risk_reward': 1.0,  # Aceita 1:1
                'use_ml': True,
                'trailing_type': TrailingType.ATR_BASED,
                'strategies': ['scalping'],
            },
            TradingMode.TREND_FOLLOWING: {
                'primary_timeframe': Timeframe.H1,
                'confirmation_timeframe': Timeframe.H4,
                'min_confluence': 0.50,  # Era 0.65
                'min_risk_reward': 1.5,  # Era 2.0
                'use_ml': True,
                'trailing_type': TrailingType.SWING_BASED,
                'strategies': ['trend'],
            },
            TradingMode.REVERSAL: {
                'primary_timeframe': Timeframe.M15,
                'confirmation_timeframe': Timeframe.H1,
                'min_confluence': 0.55,  # Era 0.7
                'min_risk_reward': 2.0,  # Era 2.5
                'use_ml': True,
                'trailing_type': TrailingType.CHANDELIER,
                'strategies': ['reversal'],
            },
            TradingMode.EVENT_DRIVEN: {
                'primary_timeframe': Timeframe.M5,
                'confirmation_timeframe': Timeframe.M15,
                'min_confluence': 0.45,  # Era 0.6
                'min_risk_reward': 1.2,  # Era 1.5
                'use_ml': False,
                'trailing_type': TrailingType.STEP_TRAIL,
                'strategies': ['event'],
            },
            TradingMode.ADAPTIVE: {
                'primary_timeframe': Timeframe.M15,
                'confirmation_timeframe': Timeframe.H1,
                'min_confluence': 0.30,  # AGRESSIVO - aceita 30%
                'min_risk_reward': 1.0,  # Aceita 1:1
                'use_ml': True,
                'trailing_type': TrailingType.ATR_BASED,
                'strategies': ['scalping', 'trend', 'reversal', 'event'],
            },
            TradingMode.CONSERVATIVE: {
                'primary_timeframe': Timeframe.H1,
                'confirmation_timeframe': Timeframe.H4,
                'min_confluence': 0.60,  # Era 0.75
                'min_risk_reward': 2.0,  # Era 3.0
                'use_ml': True,
                'trailing_type': TrailingType.SWING_BASED,
                'strategies': ['trend', 'reversal'],
            },
        }
        return configs.get(mode, configs[TradingMode.ADAPTIVE])
    
    async def initialize(self, account_balance: float) -> bool:
        """
        Inicializa o engine com todos os componentes.
        
        Args:
            account_balance: Saldo da conta para cálculos de risco
        """
        try:
            self.logger.info(f"🚀 Inicializando Trading Engine para {self.symbol}")
            
            # Inicializa Master Analyzer (já inicializa no __init__)
            self.analyzer = MasterAnalyzer(logger=self.logger)
            self.logger.info("✅ Master Analyzer inicializado")
            
            # Inicializa Risk Manager avançado
            self.risk_manager = AdvancedRiskManager(
                initial_capital=account_balance,
            )
            self.logger.info("✅ Advanced Risk Manager inicializado")
            
            # Inicializa Exit Manager
            self.exit_manager = ExitManager()  # Usa configs padrão
            self.logger.info("✅ Exit Manager inicializado")
            
            # Inicializa Position Supervisor
            self.position_supervisor = PositionSupervisor()  # Usa configs padrão
            self.logger.info("✅ Position Supervisor inicializado")
            
            # Inicializa estratégias conforme modo
            await self._initialize_strategies()
            
            # Inicializa ML
            if self._mode_config['use_ml']:
                self.prediction_service = PredictionService()
                await self.prediction_service.initialize()
                self.logger.info("✅ Prediction Service inicializado")
            
            self._initialized = True
            self.logger.success(f"✅ Trading Engine inicializado - Modo: {self.mode.value}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar Trading Engine: {e}")
            return False
    
    async def _initialize_strategies(self) -> None:
        """Inicializa estratégias configuradas (do YAML ou modo)."""
        strategies = self._mode_config['strategies']
        strategy_configs = self.bot_config.get('strategies', {})
        
        self.logger.info(f"📊 Inicializando estratégias: {strategies}")
        
        if 'scalping' in strategies:
            # Obtém configuração específica de scalping do YAML
            scalping_config = strategy_configs.get('scalping', {})
            self.scalping_strategy = ScalpingStrategy()
            self.logger.info(f"  ✅ Scalping Strategy ativada (weight: {scalping_config.get('weight', 1.0)})")
            
        if 'trend' in strategies or 'trend_following' in strategies:
            trend_config = strategy_configs.get('trend_following', {})
            self.trend_strategy = TrendStrategy()
            self.logger.info(f"  ✅ Trend Strategy ativada (weight: {trend_config.get('weight', 1.0)})")
            
        if 'reversal' in strategies:
            reversal_config = strategy_configs.get('reversal', {})
            self.reversal_strategy = ReversalStrategy()
            self.logger.info(f"  ✅ Reversal Strategy ativada (weight: {reversal_config.get('weight', 1.0)})")
            
        if 'event' in strategies:
            event_config = strategy_configs.get('event', {})
            self.event_strategy = EventStrategy()
            self.logger.info(f"  ✅ Event Strategy ativada (weight: {event_config.get('weight', 1.0)})")
        
        # Estratégias extras configuradas nos YAMLs dos bots
        if 'range_trading' in strategies:
            # Range trading usa a mesma lógica de reversal
            if not self.reversal_strategy:
                self.reversal_strategy = ReversalStrategy()
                self.logger.info("  ✅ Range Trading (via Reversal Strategy) ativada")
        
        if 'breakout' in strategies:
            # Breakout usa a mesma lógica de trend
            if not self.trend_strategy:
                self.trend_strategy = TrendStrategy()
                self.logger.info("  ✅ Breakout (via Trend Strategy) ativada")
        
        active_count = sum([
            1 for s in [self.scalping_strategy, self.trend_strategy, 
                       self.reversal_strategy, self.event_strategy] if s
        ])
        self.logger.info(f"📊 Total de estratégias ativas: {active_count}")
    
    async def analyze_and_decide(
        self,
        market_data: Dict[str, Any],
        current_price: float,
    ) -> TradeDecision:
        """
        Executa análise completa e retorna decisão de trade.
        
        Este é o método principal que integra todos os componentes.
        
        Args:
            market_data: Dados de mercado atuais
            current_price: Preço atual
            
        Returns:
            TradeDecision com todos os detalhes
        """
        if not self._initialized:
            return self._create_no_trade_decision("Engine não inicializado")
        
        self.statistics.total_analyses += 1
        confirmations = []
        rejections = []
        
        try:
            # 1. Análise completa do mercado
            analysis = await self._run_full_analysis(market_data)
            
            # Adiciona current_price à análise para as estratégias
            analysis['price'] = current_price
            analysis['tick'] = {'bid': current_price, 'ask': current_price * 1.0001}
            
            # Debug: verifica tipo da análise
            self.logger.info(f"Analysis type: {type(analysis)}")
            self.logger.info(f"Analysis score: {analysis.get('score', 0)}")
            self.logger.info(f"Analysis trend: {analysis.get('trend', {})}")
            self.logger.info(f"Analysis regime: {analysis.get('regime', {})}")
            
            if not analysis or not isinstance(analysis, dict):
                return self._create_no_trade_decision(f"Análise inválida: {type(analysis)}")
            
            # Score mínimo reduzido para 0.25 para permitir mais trades
            if analysis.get('score', 0) < 0.25:
                return self._create_no_trade_decision(f"Análise insuficiente (score={analysis.get('score', 0):.2f})")
            
            # 2. Seleciona estratégia (se adaptativo)
            selected_strategy, confidence = await self._select_strategy(analysis)
            
            if not selected_strategy:
                return self._create_no_trade_decision("Nenhuma estratégia aplicável")
            
            # 3. Gera sinais da estratégia selecionada
            setup_signal = await self._generate_strategy_signal(
                selected_strategy, market_data, analysis
            )
            
            if not setup_signal:
                return self._create_no_trade_decision("Sem setup válido")
            
            self.statistics.signals_generated += 1
            confirmations.append(f"Setup: {setup_signal.get('name')}")
            
            # 4. Validação ML (se ativo)
            ml_prediction = None
            if self.prediction_service:
                ml_prediction = await self.prediction_service.predict(
                    self.symbol, market_data
                )
                
                if ml_prediction and ml_prediction.confidence > self._min_ml_confidence:
                    if ml_prediction.direction == setup_signal.get('direction'):
                        confirmations.append(f"ML confirma ({ml_prediction.confidence:.1%})")
                    else:
                        rejections.append(f"ML diverge ({ml_prediction.direction})")
            
            # 5. Validação de risco
            risk_validation = await self._validate_risk(
                setup_signal, current_price, analysis
            )
            
            if not risk_validation['approved']:
                rejections.extend(risk_validation['reasons'])
                return self._create_no_trade_decision(
                    "Risco não aprovado",
                    setup_signal, ml_prediction, confirmations, rejections
                )
            
            confirmations.extend(risk_validation['confirmations'])
            
            # 6. Calcula position size
            position_size = await self._calculate_position_size(
                setup_signal, risk_validation
            )
            
            # 7. Validação de confluência final
            confluence_score = self._calculate_confluence(
                analysis, setup_signal, ml_prediction, confirmations, rejections
            )
            
            if confluence_score < self._mode_config['min_confluence']:
                self.statistics.signals_filtered += 1
                return self._create_no_trade_decision(
                    f"Confluência baixa: {confluence_score:.1%}",
                    setup_signal, ml_prediction, confirmations, rejections
                )
            
            confirmations.append(f"Confluência: {confluence_score:.1%}")
            
            # 8. Cria decisão final
            decision = TradeDecision(
                should_trade=True,
                direction=setup_signal['direction'],
                confidence=confluence_score,
                strategy_used=selected_strategy,
                setup_name=setup_signal['name'],
                entry_price=setup_signal.get('entry', current_price),
                stop_loss=setup_signal['sl'],
                take_profit=setup_signal['tp'],
                position_size=position_size,
                risk_reward=risk_validation['risk_reward'],
                kelly_fraction=risk_validation.get('kelly', 0),
                var_impact=risk_validation.get('var_impact', 0),
                ml_prediction=ml_prediction,
                analysis_score=analysis.get('score', 0),
                confirmations=confirmations,
                rejections=rejections,
                execution_mode=self.execution_mode,
            )
            
            self._decisions.append(decision)
            self.logger.info(
                f"🎯 Trade Decision: {decision.direction.upper()} "
                f"({decision.strategy_used}) - Confidence: {decision.confidence:.1%}"
            )
            
            return decision
            
        except Exception as e:
            import traceback
            self.logger.error(f"Erro em analyze_and_decide: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return self._create_no_trade_decision(f"Erro: {str(e)}")
    
    async def _run_full_analysis(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executa análise completa usando Master Analyzer."""
        if not self.analyzer:
            return {}
        
        try:
            return await self.analyzer.analyze_full(market_data)
        except Exception as e:
            self.logger.error(f"Erro na análise: {e}")
            return {}
    
    async def _select_strategy(
        self,
        analysis: Dict[str, Any]
    ) -> Tuple[Optional[str], float]:
        """
        Seleciona a melhor estratégia baseada na análise.
        
        Returns:
            Tupla (nome_estrategia, confiança)
        """
        if self.mode != TradingMode.ADAPTIVE:
            # Modo fixo, retorna estratégia do modo
            strategies = self._mode_config['strategies']
            return strategies[0] if strategies else None, 0.7
        
        # Modo adaptativo - seleciona baseado no regime
        regime = analysis.get('regime', {})
        
        # trend pode ser string ('bullish'/'bearish') ou dict
        trend_data = analysis.get('trend', {})
        if isinstance(trend_data, dict):
            trend_strength = trend_data.get('strength', 50)
        else:
            # trend é string, usa trend_strength separado
            trend_strength = analysis.get('trend_strength', 50)
        
        # volatility pode ser dict ou string
        vol_data = analysis.get('volatility', {})
        if isinstance(vol_data, dict):
            volatility = vol_data.get('level', 'medium')
        else:
            volatility = vol_data if vol_data else 'medium'
        
        scores = {}
        
        # Avalia cada estratégia
        if self.scalping_strategy:
            scores['scalping'] = self._score_scalping_conditions(
                volatility, trend_strength, regime
            )
        
        if self.trend_strategy:
            scores['trend'] = self._score_trend_conditions(
                volatility, trend_strength, regime
            )
        
        if self.reversal_strategy:
            scores['reversal'] = self._score_reversal_conditions(
                volatility, trend_strength, regime, analysis
            )
        
        if self.event_strategy:
            scores['event'] = self._score_event_conditions(analysis)
        
        if not scores:
            return None, 0.0
        
        # Seleciona melhor
        best_strategy = max(scores, key=scores.get)
        best_score = scores[best_strategy]
        
        self.logger.info(f"Strategy scores: {scores}")
        self.logger.info(f"Best strategy: {best_strategy} (score={best_score:.2f})")
        
        # Score mínimo reduzido de 0.4 para 0.25 para permitir mais trades
        if best_score < 0.25:
            return None, 0.0
        
        self._active_strategy = best_strategy
        return best_strategy, best_score
    
    def _score_scalping_conditions(
        self,
        volatility: str,
        trend_strength: float,
        regime: Dict
    ) -> float:
        """Pontua condições para scalping."""
        score = 0.5
        
        # Volatilidade moderada é melhor
        if volatility == 'medium':
            score += 0.2
        elif volatility == 'low':
            score += 0.1
        elif volatility == 'high':
            score -= 0.2
        
        # Trend fraco a moderado
        if 30 <= trend_strength <= 60:
            score += 0.2
        
        # Regime ranging
        if regime.get('type') == 'ranging':
            score += 0.2
        
        return min(1.0, max(0.0, score))
    
    def _score_trend_conditions(
        self,
        volatility: str,
        trend_strength: float,
        regime: Dict
    ) -> float:
        """Pontua condições para trend following."""
        score = 0.5
        
        # Volatilidade baixa a moderada
        if volatility in ['low', 'medium']:
            score += 0.15
        
        # Trend forte
        if trend_strength > 60:
            score += 0.25
        elif trend_strength > 40:
            score += 0.1
        
        # Regime trending
        if regime.get('type') == 'trending':
            score += 0.2
        
        return min(1.0, max(0.0, score))
    
    def _score_reversal_conditions(
        self,
        volatility: str,
        trend_strength: float,
        regime: Dict,
        analysis: Dict
    ) -> float:
        """Pontua condições para reversão."""
        score = 0.4
        
        # Volatilidade alta (exaustão)
        if volatility == 'high':
            score += 0.15
        
        # Trend forte mas com sinais de exaustão
        if trend_strength > 70:
            score += 0.2
        
        # Divergências
        divergence = analysis.get('divergence', {})
        if divergence.get('detected'):
            score += 0.25
        
        # Em níveis extremos
        zones = analysis.get('zones', {})
        if zones.get('at_support') or zones.get('at_resistance'):
            score += 0.2
        
        return min(1.0, max(0.0, score))
    
    def _score_event_conditions(self, analysis: Dict) -> float:
        """Pontua condições para event trading."""
        score = 0.3
        
        # Eventos próximos
        events = analysis.get('events', {})
        if events.get('upcoming_news'):
            score += 0.3
        
        # Alta volatilidade esperada
        if events.get('high_impact'):
            score += 0.2
        
        return min(1.0, max(0.0, score))
    
    async def _generate_strategy_signal(
        self,
        strategy_name: str,
        market_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Gera sinal da estratégia selecionada."""
        strategy = None
        
        if strategy_name == 'scalping':
            strategy = self.scalping_strategy
        elif strategy_name == 'trend':
            strategy = self.trend_strategy
        elif strategy_name == 'reversal':
            strategy = self.reversal_strategy
        elif strategy_name == 'event':
            strategy = self.event_strategy
        
        if not strategy:
            return None
        
        try:
            setups = await strategy.find_setups(market_data, analysis)
            
            if not setups:
                return None
            
            # Retorna melhor setup
            best_setup = max(setups, key=lambda s: s.get('score', 0))
            return best_setup
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar sinal: {e}")
            return None
    
    async def _validate_risk(
        self,
        setup: Dict[str, Any],
        current_price: float,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Valida setup do ponto de vista de risco."""
        confirmations = []
        reasons = []
        
        entry = setup.get('entry', current_price)
        sl = setup.get('sl', 0)
        tp = setup.get('tp', 0)
        
        if not sl or not tp:
            return {'approved': False, 'reasons': ['SL/TP não definidos']}
        
        # Calcula Risk/Reward
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        risk_reward = reward / risk if risk > 0 else 0
        
        if risk_reward < self._mode_config['min_risk_reward']:
            reasons.append(f"R:R baixo ({risk_reward:.1f})")
        else:
            confirmations.append(f"R:R: {risk_reward:.1f}")
        
        # Validação Kelly simplificada
        kelly = 0.0
        if self.risk_manager:
            try:
                # Tenta usar o método do risk_manager se disponível
                if hasattr(self.risk_manager, 'calculate_kelly_criterion'):
                    kelly_result = self.risk_manager.calculate_kelly_criterion(
                        win_rate=self.statistics.win_rate or 0.5,
                        avg_win_loss_ratio=risk_reward
                    )
                    kelly = kelly_result.kelly_fraction
                else:
                    # Cálculo simplificado: Kelly = (win_rate * R:R - (1-win_rate)) / R:R
                    win_rate = self.statistics.win_rate or 0.5
                    kelly = (win_rate * risk_reward - (1 - win_rate)) / risk_reward if risk_reward > 0 else 0
                    kelly = max(0, min(kelly, 0.25))  # Limita Kelly entre 0 e 25%
                
                if kelly < 0.01:
                    # Não bloqueia se Kelly baixo, apenas avisa
                    confirmations.append(f"Kelly: {kelly:.1%} (baixo)")
                else:
                    confirmations.append(f"Kelly: {kelly:.1%}")
            except Exception as e:
                self.logger.warning(f"Erro calculando Kelly: {e}")
                confirmations.append("Kelly: N/A")
        
        # Validação de risco simples
        # Verifica se o risco é aceitável (máx 2% do capital)
        if self.risk_manager and hasattr(self.risk_manager, 'account_balance'):
            max_risk_amount = self.risk_manager.account_balance * 0.02  # 2% max
            if risk > max_risk_amount:
                reasons.append(f"Risco alto ({risk:.2f} > {max_risk_amount:.2f})")
            else:
                confirmations.append(f"Risco: ${risk:.2f}")
        
        approved = len(reasons) == 0
        
        return {
            'approved': approved,
            'confirmations': confirmations,
            'reasons': reasons,
            'risk_reward': risk_reward,
            'kelly': kelly,
        }
    
    async def _calculate_position_size(
        self,
        setup: Dict[str, Any],
        risk_validation: Dict[str, Any]
    ) -> float:
        """Calcula tamanho da posição."""
        if not self.risk_manager:
            return 0.01  # Mínimo
        
        entry = setup.get('entry', 0)
        sl = setup.get('sl', 0)
        
        if not entry or not sl:
            return 0.01
        
        # Usa Kelly com limite de segurança
        kelly = risk_validation.get('kelly', 0)
        
        try:
            # Cálculo simplificado: risco 1% do capital
            risk = abs(entry - sl)
            account_balance = getattr(self.risk_manager, 'account_balance', 5000)
            max_risk = account_balance * 0.01  # 1% do capital
            
            # Para XAUUSD, cada ponto = $1 por lote padrão
            if 'XAU' in self.symbol or 'GOLD' in self.symbol.upper():
                size = max_risk / risk if risk > 0 else 0.01
            else:
                # Para forex, calcular baseado em pips
                point_value = 0.0001 if 'JPY' not in self.symbol else 0.01
                pips = risk / point_value
                size = max_risk / (pips * 10) if pips > 0 else 0.01  # 10 USD por pip em lot padrão
            
            size = float(size) if size else 0.01
        except Exception as e:
            self.logger.warning(f"Erro calculando position size: {e}, usando 0.01")
            size = 0.01
        
        # Garante mínimo e máximo - CONSERVADOR para conta de $5000
        return max(0.01, min(0.01, size))  # Fixo 0.01 lotes para conservar capital
    
    def _count_consecutive_wins(self) -> int:
        """Conta vitórias consecutivas recentes."""
        # Simplificado - usar histórico real
        recent = list(self._decisions)[-10:]
        consecutive = 0
        
        for d in reversed(recent):
            if hasattr(d, 'was_profitable') and d.was_profitable:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def _calculate_confluence(
        self,
        analysis: Dict,
        setup: Dict,
        ml_prediction: Optional[EnsemblePrediction],
        confirmations: List[str],
        rejections: List[str]
    ) -> float:
        """Calcula score de confluência."""
        score = 0.0
        factors = 0
        
        # Análise base
        analysis_score = analysis.get('score', 0.5)
        score += analysis_score * 0.3
        factors += 0.3
        
        # Setup quality
        setup_score = setup.get('score', 0.5)
        score += setup_score * 0.3
        factors += 0.3
        
        # ML prediction
        if ml_prediction:
            if ml_prediction.direction == setup.get('direction'):
                score += ml_prediction.confidence * 0.2
            else:
                score -= 0.1
            factors += 0.2
        
        # Confirmações vs rejeições
        conf_ratio = len(confirmations) / max(1, len(confirmations) + len(rejections))
        score += conf_ratio * 0.2
        factors += 0.2
        
        return score / factors if factors > 0 else 0.0
    
    def _create_no_trade_decision(
        self,
        reason: str,
        setup: Optional[Dict] = None,
        ml_prediction: Optional[EnsemblePrediction] = None,
        confirmations: Optional[List[str]] = None,
        rejections: Optional[List[str]] = None,
    ) -> TradeDecision:
        """Cria decisão de não operar."""
        return TradeDecision(
            should_trade=False,
            direction="none",
            confidence=0.0,
            strategy_used="",
            setup_name=setup.get('name', '') if setup else "",
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            position_size=0.0,
            risk_reward=0.0,
            kelly_fraction=0.0,
            var_impact=0.0,
            ml_prediction=ml_prediction,
            confirmations=confirmations or [],
            rejections=(rejections or []) + [reason],
        )
    
    # === Position Management ===
    
    async def manage_position(
        self,
        position: Position,
        market_data: Dict[str, Any],
        current_price: float
    ) -> Dict[str, Any]:
        """
        Gerencia posição aberta usando Exit Manager e Position Supervisor.
        
        Returns:
            Dict com ações recomendadas
        """
        actions = {
            'exit_signal': False,
            'modify_sl': False,
            'modify_tp': False,
            'new_sl': None,
            'new_tp': None,
            'partial_exit': False,
            'partial_volume': 0.0,
            'reason': '',
            'health': 'healthy',
        }
        
        if not self.exit_manager or not self.position_supervisor:
            return actions
        
        try:
            # 1. Supervisiona posição
            if self.position_supervisor:
                health = await self.position_supervisor.check_position_health(
                    position, market_data
                )
                actions['health'] = health.name
                
                if health == PositionHealth.CRITICAL:
                    actions['exit_signal'] = True
                    actions['reason'] = "Saúde crítica"
                    return actions
            
            # 2. Calcula trailing stop
            trailing_result = await self.exit_manager.calculate_trailing_stop(
                position=position,
                current_price=current_price,
                market_data=market_data,
            )
            
            if trailing_result['should_update']:
                actions['modify_sl'] = True
                actions['new_sl'] = trailing_result['new_sl']
            
            # 3. Verifica saídas parciais
            partial_result = await self.exit_manager.check_partial_exit(
                position=position,
                current_price=current_price,
            )
            
            if partial_result['should_exit']:
                actions['partial_exit'] = True
                actions['partial_volume'] = partial_result['volume']
                actions['reason'] = partial_result['reason']
            
            # 4. Verifica break-even
            be_result = await self.position_supervisor.check_break_even(
                position, current_price
            )
            
            if be_result['should_move']:
                actions['modify_sl'] = True
                actions['new_sl'] = be_result['new_sl']
                actions['reason'] = "Move to break-even"
            
            return actions
            
        except Exception as e:
            self.logger.error(f"Erro ao gerenciar posição: {e}")
            return actions
    
    def record_trade_result(self, profit: float, strategy: str) -> None:
        """Registra resultado do trade."""
        self.statistics.record_trade(profit, strategy)
        
        if profit >= 0:
            self.statistics.signals_executed += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do engine."""
        return {
            'symbol': self.symbol,
            'mode': self.mode.value,
            'execution_mode': self.execution_mode.value,
            'initialized': self._initialized,
            'active_strategy': self._active_strategy,
            'statistics': {
                'total_analyses': self.statistics.total_analyses,
                'signals_generated': self.statistics.signals_generated,
                'signals_filtered': self.statistics.signals_filtered,
                'signals_executed': self.statistics.signals_executed,
                'total_trades': self.statistics.total_trades,
                'win_rate': round(self.statistics.win_rate, 4),
                'profit_factor': round(self.statistics.profit_factor, 2),
                'total_profit': round(self.statistics.total_profit, 2),
            },
            'config': {
                'min_confluence': self._min_confluence,
                'min_risk_reward': self._mode_config['min_risk_reward'],
                'use_ml': self._mode_config['use_ml'],
            },
        }
    
    def get_recent_decisions(self, count: int = 10) -> List[Dict]:
        """Retorna decisões recentes."""
        decisions = list(self._decisions)[-count:]
        return [d.to_dict() for d in decisions]
