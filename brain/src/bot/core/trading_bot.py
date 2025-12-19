"""
VIRTUS Trading Bot
===================

Bot de trading independente por símbolo.
Integrado com TradingEngine para análise avançada.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path

from .bot_state import (
    BotState, TradingPhase, BotStateManager, BotStatistics, BotContext
)
from .trading_engine import TradingEngine, TradingMode, ExecutionMode, TradeDecision
from ...core import (
    Config, VirtusLogger, Signal, SignalType, SignalStrength, Position, PositionStatus,
    BotError, MT5Error
)
from ...brain import BrainService, get_brain
from ...mt5 import MT5Connection, MT5DataService, MT5OrderManager


class TradingBot:
    """
    Bot de trading independente para um símbolo específico.
    
    Integrado com TradingEngine para:
    - Análise técnica completa (MasterAnalyzer)
    - Múltiplas estratégias (Scalping, Trend, Reversal, Event)
    - Risk management avançado (Kelly, VaR)
    - Exit management (8 tipos de trailing)
    - ML predictions (ensemble learning)
    """
    
    def __init__(
        self,
        bot_id: str,
        symbol: str,
        config: Config,
        strategy: Optional[Any] = None,
        trading_mode: TradingMode = TradingMode.ADAPTIVE,
    ):
        self.bot_id = bot_id
        self.symbol = symbol
        self.config = config
        self.strategy = strategy
        self.trading_mode = trading_mode
        
        # Logger específico do bot
        self.logger = VirtusLogger.get_logger(f"bot.{symbol.lower()}")
        
        # State manager
        self.state_manager = BotStateManager(bot_id, symbol)
        
        # Serviços (serão injetados)
        self.brain: Optional[BrainService] = None
        self.mt5_data: Optional[MT5DataService] = None
        self.mt5_orders: Optional[MT5OrderManager] = None
        
        # ============================================
        # TRADING ENGINE - MOTOR AVANÇADO INTEGRADO
        # ============================================
        self.engine: Optional[TradingEngine] = None
        
        # Controle
        self._running = False
        self._main_task: Optional[asyncio.Task] = None
        self._analysis_interval = 5.0  # segundos
        self._position_check_interval = 1.0  # segundos
        
        # Callbacks
        self._on_signal_callbacks: List[Callable] = []
        self._on_trade_callbacks: List[Callable] = []
        
        # Posição atual
        self.current_position: Optional[Position] = None
        
        # Filtros (serão gerenciados pelo Engine, mas mantemos para fallback)
        self._min_signal_confidence = 0.6
        self._max_spread_pips = 3.0
        self._min_volatility = 0.0001
        self._max_volatility = 0.01
        
        # Circuit breaker
        self._max_consecutive_losses = 3
        self._max_daily_loss_pct = 5.0
        self._cooldown_after_loss = 300  # segundos
        self._last_loss_time: Optional[datetime] = None
        
        # Saldo da conta (para risk management)
        self._account_balance: float = 0.0
    
    async def initialize(self) -> bool:
        """Inicializa o bot com TradingEngine integrado."""
        try:
            await self.state_manager.set_state(BotState.INITIALIZING, "Iniciando bot")
            self.logger.info(f"🚀 Inicializando bot {self.bot_id} para {self.symbol}")
            
            # Obtém Brain (singleton)
            self.brain = await get_brain()
            if not self.brain:
                raise BotError(f"Brain não disponível para bot {self.bot_id}")
            
            # Obtém serviços MT5 (singletons)
            mt5_conn = await MT5Connection.get_instance()
            if not mt5_conn.is_connected:
                raise MT5Error("MT5 não conectado")
            
            self.mt5_data = await MT5DataService.get_instance()
            self.mt5_orders = await MT5OrderManager.get_instance()
            
            # Seleciona símbolo
            if not mt5_conn.select_symbol(self.symbol):
                raise BotError(f"Símbolo {self.symbol} não disponível")
            
            # Carrega configuração específica do bot
            await self._load_bot_config()
            
            # Obtém saldo da conta para risk management
            account_info = mt5_conn.account_info  # É propriedade, não método
            if account_info:
                self._account_balance = account_info.get('balance', 10000.0)
                self.logger.info(f"💰 Saldo da conta: ${self._account_balance:,.2f}")
            
            # ============================================
            # INICIALIZA TRADING ENGINE (MOTOR AVANÇADO)
            # Passa as estratégias configuradas no YAML do bot
            # ============================================
            
            # Obtém estratégias habilitadas do YAML do bot
            enabled_strategies = self._get_enabled_strategies()
            bot_yaml_config = self._get_bot_yaml_config()
            
            self.logger.info(f"📊 Estratégias do YAML: {enabled_strategies}")
            
            self.engine = TradingEngine(
                symbol=self.symbol,
                mode=self.trading_mode,
                execution_mode=ExecutionMode.NORMAL,
                risk_per_trade=self._get_risk_per_trade(),
                enabled_strategies=enabled_strategies,  # NOVO: passa estratégias do YAML
                bot_config=bot_yaml_config,  # NOVO: passa config completa
            )
            
            engine_ok = await self.engine.initialize(self._account_balance)
            if engine_ok:
                self.logger.success(f"✅ TradingEngine inicializado - Modo: {self.trading_mode.value}")
            else:
                self.logger.warning("⚠️ TradingEngine não inicializado completamente, usando modo básico")
            
            # Carrega estado anterior (se existir)
            state_file = Path(f"brain/data/bots/{self.symbol.lower()}/state.json")
            if state_file.exists():
                if await self.state_manager.load_state(str(state_file)):
                    self.logger.info("📂 Estado anterior carregado")
            
            # Verifica posições existentes
            await self._sync_positions()
            
            await self.state_manager.set_state(BotState.READY, "Bot pronto")
            self.logger.success(f"✅ Bot {self.bot_id} inicializado com TradingEngine")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar bot: {e}")
            await self.state_manager.set_state(BotState.ERROR, str(e))
            await self.state_manager.record_error(str(e))
            return False
    
    def _get_risk_per_trade(self) -> float:
        """Obtém risco por trade da configuração."""
        for bc in self.config.bots:
            if bc.symbol == self.symbol:
                return bc.risk.get('risk_per_trade', bc.risk.get('max_risk_per_trade', 0.01))
        return 0.01  # 1% padrão
    
    def _get_enabled_strategies(self) -> List[str]:
        """
        Obtém lista de estratégias habilitadas do YAML do bot.
        
        Returns:
            Lista de nomes de estratégias habilitadas
        """
        for bc in self.config.bots:
            if bc.symbol == self.symbol:
                strategies_config = bc.strategies
                # Obtém lista de estratégias habilitadas
                enabled_list = strategies_config.get('enabled', [])
                
                # Se não houver lista, verifica estratégias individuais
                if not enabled_list:
                    enabled_list = []
                    for strategy_name in ['scalping', 'trend_following', 'trend', 
                                         'reversal', 'event', 'breakout', 'range_trading']:
                        strategy_cfg = strategies_config.get(strategy_name, {})
                        if strategy_cfg.get('enabled', False):
                            enabled_list.append(strategy_name)
                
                self.logger.debug(f"Estratégias encontradas para {self.symbol}: {enabled_list}")
                return enabled_list
        
        return []  # Retorna vazio se não encontrar config
    
    def _get_bot_yaml_config(self) -> Dict[str, Any]:
        """
        Obtém configuração completa do bot do YAML.
        
        Returns:
            Dict com toda a configuração do bot
        """
        for bc in self.config.bots:
            if bc.symbol == self.symbol:
                return {
                    'id': bc.id,
                    'name': bc.name,
                    'symbol': bc.symbol,
                    'strategies': bc.strategies,
                    'risk': bc.risk,
                    'positions': bc.positions,
                    'ml': bc.ml,
                    'analysis': bc.analysis,
                }
        return {}
    
    async def _load_bot_config(self) -> None:
        """Carrega configuração específica do bot."""
        # Busca configuração do símbolo
        bot_config = None
        for bc in self.config.bots:
            if bc.symbol == self.symbol:
                bot_config = bc
                break
        
        if bot_config:
            # Pega analysis_interval do dict analysis ou usa default
            self._analysis_interval = bot_config.analysis.get('interval', 5.0)
            self._min_signal_confidence = bot_config.analysis.get('min_confidence', 0.6)
            self._max_consecutive_losses = bot_config.risk.get('max_consecutive_losses', 3)
    
    async def _sync_positions(self) -> None:
        """Sincroniza posições existentes no MT5."""
        try:
            positions = await self.mt5_orders.get_positions(self.symbol)
            
            if positions:
                # Pega a primeira posição (assumindo uma por símbolo)
                pos = positions[0]
                self.current_position = Position(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    type=pos.type,
                    volume=pos.volume,
                    open_price=pos.price_open,
                    current_price=pos.price_current,
                    sl=pos.sl,
                    tp=pos.tp,
                    profit=pos.profit,
                    status=PositionStatus.OPEN,
                    open_time=datetime.fromtimestamp(pos.time),
                )
                await self.state_manager.update_context(
                    has_position=True,
                    position_profit=pos.profit
                )
                self.logger.info(f"📊 Posição existente encontrada: #{pos.ticket}")
            else:
                self.current_position = None
                await self.state_manager.update_context(
                    has_position=False,
                    position_profit=0.0
                )
                
        except Exception as e:
            self.logger.warning(f"Erro ao sincronizar posições: {e}")
    
    async def start(self) -> None:
        """Inicia o loop principal do bot."""
        if self._running:
            self.logger.warning("Bot já está rodando")
            return
        
        await self.state_manager.set_state(BotState.RUNNING, "Loop iniciado")
        self._running = True
        
        self.logger.info(f"▶️ Bot {self.bot_id} iniciado")
        
        # Inicia task principal
        self._main_task = asyncio.create_task(self._main_loop())
    
    async def stop(self) -> None:
        """Para o bot."""
        if not self._running:
            return
        
        self._running = False
        
        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        
        # Salva estado
        await self._save_state()
        
        await self.state_manager.set_state(BotState.STOPPED, "Bot parado")
        self.logger.info(f"⏹️ Bot {self.bot_id} parado")
    
    async def pause(self) -> None:
        """Pausa o bot."""
        await self.state_manager.set_state(BotState.PAUSED, "Bot pausado")
        self.logger.info(f"⏸️ Bot {self.bot_id} pausado")
    
    async def resume(self) -> None:
        """Resume o bot."""
        if self.state_manager.context.state == BotState.PAUSED:
            await self.state_manager.set_state(BotState.RUNNING, "Bot resumido")
            self.logger.info(f"▶️ Bot {self.bot_id} resumido")
    
    async def _main_loop(self) -> None:
        """Loop principal do bot."""
        self.logger.info("🔄 Loop principal iniciado")
        
        while self._running:
            try:
                # Verifica se está pausado
                if self.state_manager.context.state == BotState.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                # Atualiza contexto de mercado
                await self._update_market_context()
                
                # Verifica circuit breaker
                if await self._check_circuit_breaker():
                    await asyncio.sleep(60)
                    continue
                
                # Se tem posição, gerencia
                if self.current_position:
                    await self.state_manager.set_phase(TradingPhase.MANAGING)
                    await self._manage_position()
                else:
                    # Sem posição, analisa mercado
                    await self.state_manager.set_phase(TradingPhase.ANALYZING)
                    await self._analyze_market()
                
                await asyncio.sleep(self._analysis_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Erro no loop principal: {e}")
                await self.state_manager.record_error(str(e))
                await asyncio.sleep(10)
        
        self.logger.info("🔄 Loop principal encerrado")
    
    async def _update_market_context(self) -> None:
        """Atualiza contexto de mercado."""
        try:
            # Preço atual
            tick = await self.mt5_data.get_price(self.symbol)
            if tick:
                await self.state_manager.update_context(
                    price=tick.get('last') or tick.get('bid'),
                    spread=tick.get('ask', 0) - tick.get('bid', 0)
                )
            
            # Volatilidade
            volatility = await self.mt5_data.get_volatility(self.symbol, period=20)
            if volatility:
                await self.state_manager.update_context(volatility=volatility)
            
            # Sessão de mercado
            session = self._get_market_session()
            await self.state_manager.update_context(session=session)
            
        except Exception as e:
            self.logger.debug(f"Erro ao atualizar contexto: {e}")
    
    def _get_market_session(self) -> str:
        """Determina sessão de mercado atual."""
        hour = datetime.utcnow().hour
        
        if 22 <= hour or hour < 7:
            return "asian"
        elif 7 <= hour < 12:
            return "london"
        elif 12 <= hour < 17:
            return "new_york"
        else:
            return "overlap"
    
    async def _check_circuit_breaker(self) -> bool:
        """Verifica se circuit breaker está ativo."""
        stats = self.state_manager.statistics
        
        # Perdas consecutivas
        if stats.consecutive_losses >= self._max_consecutive_losses:
            self.logger.warning(f"⚠️ Circuit breaker: {stats.consecutive_losses} perdas consecutivas")
            return True
        
        # Cooldown após perda
        if self._last_loss_time:
            elapsed = (datetime.now() - self._last_loss_time).total_seconds()
            if elapsed < self._cooldown_after_loss:
                return True
        
        return False
    
    async def _analyze_market(self) -> None:
        """
        Analisa mercado usando TradingEngine integrado.
        
        O TradingEngine coordena:
        - MasterTechnicalAnalyzer (20 tipos de análise)
        - 4 Estratégias (Scalping, Trend, Reversal, Event)
        - AdvancedRiskManager (Kelly, VaR)
        - PredictionService (ML ensemble)
        """
        try:
            await self.state_manager.set_phase(TradingPhase.ANALYZING)
            self.logger.info(f"🔍 [{self.symbol}] Iniciando análise de mercado...")
            
            # Verifica condições básicas
            if not self._check_basic_conditions():
                self.logger.info(f"⚠️ [{self.symbol}] Condições básicas não atendidas")
                return
            
            # Obtém dados do Brain e MT5
            market_data = await self._get_market_data()
            if not market_data:
                self.logger.info(f"⚠️ [{self.symbol}] Sem dados de mercado")
                return
            
            # Obtém preço atual
            tick = await self.mt5_data.get_price(self.symbol)
            if not tick:
                self.logger.info(f"⚠️ [{self.symbol}] Sem cotação atual")
                return
            current_price = tick.get('last') or tick.get('bid')
            
            # ============================================
            # USA TRADING ENGINE PARA DECISÃO COMPLETA
            # ============================================
            if self.engine and self.engine._initialized:
                # Análise completa com TradingEngine
                decision: TradeDecision = await self.engine.analyze_and_decide(
                    market_data=market_data,
                    current_price=current_price,
                )
                
                if decision.should_trade:
                    self.state_manager.statistics.record_signal()
                    await self.state_manager.set_phase(TradingPhase.SIGNAL_DETECTED)
                    
                    self.logger.info(
                        f"🎯 TradingEngine: {decision.direction.upper()} "
                        f"({decision.strategy_used}) - {decision.confidence:.1%}"
                    )
                    self.logger.info(f"   Setup: {decision.setup_name}")
                    self.logger.info(f"   R:R: {decision.risk_reward:.1f} | Kelly: {decision.kelly_fraction:.1%}")
                    self.logger.info(f"   Confirmações: {', '.join(decision.confirmations[:3])}")
                    
                    # Notifica callbacks
                    signal = self._decision_to_signal(decision)
                    for callback in self._on_signal_callbacks:
                        try:
                            await callback(signal)
                        except Exception:
                            pass
                    
                    # Executa trade baseado na decisão do Engine
                    await self._execute_engine_decision(decision)
                else:
                    # Sem trade - log rejections se houver
                    if decision.rejections:
                        self.logger.info(f"⏭️ Sem trade: {', '.join(decision.rejections[:3])}")
            else:
                # Fallback para lógica básica se Engine não inicializado
                await self._analyze_market_fallback(market_data)
                    
        except Exception as e:
            self.logger.error(f"Erro na análise: {e}")
    
    def _decision_to_signal(self, decision: TradeDecision) -> Signal:
        """Converte TradeDecision para Signal."""
        signal_type = SignalType.BUY if decision.direction == "buy" else SignalType.SELL
        
        # Mapeia confiança para SignalStrength
        if decision.confidence >= 0.8:
            strength = SignalStrength.STRONG
        elif decision.confidence >= 0.6:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
            
        return Signal(
            symbol=self.symbol,
            type=signal_type,
            strength=strength,
            timestamp=decision.timestamp,
            entry_price=decision.entry_price,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            strategy=decision.strategy_used,
            confidence=decision.confidence,
            reasons=decision.confirmations,
        )
    
    async def _execute_engine_decision(self, decision: TradeDecision) -> None:
        """Executa decisão do TradingEngine."""
        try:
            await self.state_manager.set_phase(TradingPhase.ENTERING)
            
            # Parâmetros já calculados pelo Engine
            from ...core.types import OrderType
            order_type = OrderType.BUY if decision.direction == "buy" else OrderType.SELL
            
            self.logger.info(
                f"📊 Executando: {order_type.value} {decision.position_size} lots @ {decision.entry_price:.5f}"
            )
            self.logger.info(
                f"   SL: {decision.stop_loss:.5f} | TP: {decision.take_profit:.5f}"
            )
            
            # Executa ordem via MT5 - send_market_order é async
            result = await self.mt5_orders.send_market_order(
                symbol=self.symbol,
                order_type=order_type,
                volume=decision.position_size,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                comment=f"VIRTUS_{self.bot_id}_{decision.strategy_used}"
            )
            
            if result and result.get('success'):
                ticket = result.get('ticket', 0)
                self.logger.success(
                    f"✅ Ordem executada: #{ticket} "
                    f"({decision.strategy_used} - {decision.setup_name})"
                )
                self.state_manager.statistics.record_signal(executed=True)
                
                # Cria posição - order_type deve ser OrderType, não SignalType
                from ...core.types import OrderType
                order_type = OrderType.BUY if decision.direction == "buy" else OrderType.SELL
                self.current_position = Position(
                    ticket=ticket,
                    symbol=self.symbol,
                    order_type=order_type,
                    volume=decision.position_size,
                    entry_price=result.get('price', decision.entry_price),
                    current_price=result.get('price', decision.entry_price),
                    stop_loss=decision.stop_loss,
                    take_profit=decision.take_profit,
                    profit=0.0,
                    status=PositionStatus.OPEN,
                    open_time=datetime.now(),
                )
                
                await self.state_manager.update_context(has_position=True)
                
                # Registra no Engine para estatísticas
                if self.engine:
                    self.engine._active_strategy = decision.strategy_used
                
                # Notifica callbacks
                for callback in self._on_trade_callbacks:
                    try:
                        await callback("entry", self.current_position)
                    except Exception:
                        pass
            else:
                error = result.get('error', 'Erro desconhecido') if result else "Erro desconhecido"
                self.logger.error(f"❌ Erro ao executar ordem: {error}")
                
        except Exception as e:
            self.logger.error(f"Erro ao executar decisão: {e}")
        
        await self.state_manager.set_phase(TradingPhase.WAITING)
    
    async def _analyze_market_fallback(self, market_data: Dict[str, Any]) -> None:
        """Análise de fallback quando Engine não está disponível."""
        signal = await self._generate_signal(market_data)
        
        if signal:
            self.state_manager.statistics.record_signal()
            
            if await self._validate_signal(signal):
                await self.state_manager.set_phase(TradingPhase.SIGNAL_DETECTED)
                self.logger.info(f"🎯 Sinal (fallback): {signal.type.name}")
                
                for callback in self._on_signal_callbacks:
                    try:
                        await callback(signal)
                    except Exception:
                        pass
                
                if await self._confirm_entry(signal):
                    await self._execute_entry(signal)
            else:
                self.state_manager.statistics.record_signal(filtered=True)
    
    def _check_basic_conditions(self) -> bool:
        """Verifica condições básicas para operar."""
        ctx = self.state_manager.context
        
        # Calcula spread máximo baseado no símbolo
        # Para Gold/Indices: spread em pontos (ex: XAUUSD spread ~0.10-0.50)
        # Para Forex: spread em pips (ex: EURUSD spread ~0.00010-0.00030)
        is_gold = self.symbol.upper().startswith("XAU")
        is_index = self.symbol.upper() in ["US30", "US500", "US100", "GER40"]
        
        if is_gold:
            max_spread = 3.0  # $3.00 de spread máximo para ouro
        elif is_index:
            max_spread = 5.0  # 5 pontos para índices
        else:
            max_spread = self._max_spread_pips * 0.0001  # Forex: pips em decimal
        
        # Log dos valores atuais
        self.logger.debug(
            f"📊 Condições: spread={ctx.spread:.5f} (max={max_spread:.5f}), "
            f"volatility={ctx.volatility:.5f} (min={self._min_volatility:.5f}, max={self._max_volatility:.5f})"
        )
        
        # Spread muito alto
        if ctx.spread > max_spread:
            self.logger.info(f"⚠️ Spread muito alto: {ctx.spread:.5f} > {max_spread:.5f}")
            return False
        
        # Para volatilidade 0, assumimos que ainda não foi calculada - permite trade
        if ctx.volatility == 0:
            self.logger.debug(f"⚠️ Volatilidade não calculada ainda, permitindo análise")
            return True
        
        # Volatilidade fora do range
        if ctx.volatility < self._min_volatility or ctx.volatility > self._max_volatility:
            self.logger.info(f"⚠️ Volatilidade fora do range: {ctx.volatility:.5f} (esperado: {self._min_volatility:.5f} - {self._max_volatility:.5f})")
            return False
        
        return True
    
    async def _get_market_data(self) -> Dict[str, Any]:
        """Obtém dados de mercado do Brain."""
        data = {
            'symbol': self.symbol,  # Incluir símbolo
        }
        
        try:
            # Candles (métodos assíncronos)
            candles = await self.mt5_data.get_candles(self.symbol, "H1", 100)
            if candles is not None:
                data['candles_h1'] = candles
            
            candles_m15 = await self.mt5_data.get_candles(self.symbol, "M15", 100)
            if candles_m15 is not None:
                data['candles_m15'] = candles_m15
            
            # Indicadores do Brain
            if self.brain:
                indicators = await self.brain.get_technical_indicators(self.symbol)
                data['indicators'] = indicators
                
                # Sentimento
                sentiment = await self.brain.get_sentiment(self.symbol)
                data['sentiment'] = sentiment
                
        except Exception as e:
            self.logger.debug(f"Erro ao obter dados: {e}")
        
        return data
    
    async def _generate_signal(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """Gera sinal de trading."""
        if self.strategy:
            # Usa estratégia configurada
            return await self.strategy.generate_signal(market_data)
        
        # Estratégia padrão simples (placeholder)
        return await self._default_signal_generation(market_data)
    
    async def _default_signal_generation(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """Geração de sinal padrão (placeholder)."""
        # Implementar lógica de sinal básica
        indicators = market_data.get('indicators', {})
        
        if not indicators:
            return None
        
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', {})
        
        # Lógica simples para demonstração
        if rsi and rsi < 30:
            return Signal(
                symbol=self.symbol,
                type=SignalType.BUY,
                strength=0.7,
                confidence=0.6,
                source="default",
                timestamp=datetime.now(),
                metadata={'rsi': rsi, 'reason': 'RSI oversold'}
            )
        elif rsi and rsi > 70:
            return Signal(
                symbol=self.symbol,
                type=SignalType.SELL,
                strength=0.7,
                confidence=0.6,
                source="default",
                timestamp=datetime.now(),
                metadata={'rsi': rsi, 'reason': 'RSI overbought'}
            )
        
        return None
    
    async def _validate_signal(self, signal: Signal) -> bool:
        """Valida sinal antes da execução."""
        # Confiança mínima
        if signal.confidence < self._min_signal_confidence:
            return False
        
        # Verifica se Brain aprova
        if self.brain:
            # Pode adicionar validação adicional do Brain
            pass
        
        return True
    
    async def _confirm_entry(self, signal: Signal) -> bool:
        """Confirma entrada."""
        await self.state_manager.set_phase(TradingPhase.CONFIRMING)
        
        # Aguarda um ciclo para confirmar
        await asyncio.sleep(1)
        
        # Re-verifica preço
        tick = await self.mt5_data.get_price(self.symbol)
        if not tick:
            return False
        
        return True
    
    async def _execute_entry(self, signal: Signal) -> None:
        """Executa entrada."""
        try:
            await self.state_manager.set_phase(TradingPhase.ENTERING)
            
            # Calcula parâmetros
            tick = await self.mt5_data.get_price(self.symbol)
            if not tick:
                return
            
            entry_price = tick.get('ask') if signal.type == SignalType.BUY else tick.get('bid')
            
            # Calcula SL/TP (simplificado)
            atr = await self.mt5_data.get_volatility(self.symbol, period=14) or 0.001
            sl_distance = atr * 2
            tp_distance = atr * 3
            
            if signal.type == SignalType.BUY:
                sl = entry_price - sl_distance
                tp = entry_price + tp_distance
            else:
                sl = entry_price + sl_distance
                tp = entry_price - tp_distance
            
            # Calcula lote (simplificado)
            volume = 0.01  # Lote mínimo para demo
            
            # Executa ordem
            result = self.mt5_orders.place_market_order(
                symbol=self.symbol,
                order_type="buy" if signal.type == SignalType.BUY else "sell",
                volume=volume,
                sl=sl,
                tp=tp,
                comment=f"VIRTUS_{self.bot_id}"
            )
            
            if result and result.retcode == 10009:  # TRADE_RETCODE_DONE
                self.logger.success(f"✅ Ordem executada: #{result.order}")
                self.state_manager.statistics.record_signal(executed=True)
                
                # Cria posição
                self.current_position = Position(
                    ticket=result.order,
                    symbol=self.symbol,
                    type=signal.type,
                    volume=volume,
                    open_price=entry_price,
                    current_price=entry_price,
                    sl=sl,
                    tp=tp,
                    profit=0.0,
                    status=PositionStatus.OPEN,
                    open_time=datetime.now(),
                )
                
                await self.state_manager.update_context(has_position=True)
                
                # Notifica callbacks
                for callback in self._on_trade_callbacks:
                    try:
                        await callback("entry", self.current_position)
                    except Exception:
                        pass
            else:
                error = result.comment if result else "Erro desconhecido"
                self.logger.error(f"❌ Erro ao executar ordem: {error}")
                
        except Exception as e:
            self.logger.error(f"Erro ao executar entrada: {e}")
        
        await self.state_manager.set_phase(TradingPhase.WAITING)
    
    async def _manage_position(self) -> None:
        """
        Gerencia posição aberta usando TradingEngine.
        
        O Engine coordena:
        - ExitManager (8 tipos de trailing stop)
        - PositionSupervisor (health check)
        - Break-even automático
        - Saídas parciais
        """
        if not self.current_position:
            return
        
        try:
            # Atualiza posição do MT5
            positions = await self.mt5_orders.get_positions(self.symbol)
            
            if not positions:
                # Posição fechada (TP/SL atingido)
                await self._handle_position_closed()
                return
            
            pos = positions[0]
            self.current_position.current_price = pos.price_current
            self.current_position.profit = pos.profit
            
            await self.state_manager.update_context(
                position_profit=pos.profit
            )
            
            # ============================================
            # USA TRADING ENGINE PARA GERENCIAR POSIÇÃO
            # ============================================
            if self.engine and self.engine._initialized:
                market_data = await self._get_market_data()
                
                actions = await self.engine.manage_position(
                    position=self.current_position,
                    market_data=market_data,
                    current_price=pos.price_current,
                )
                
                # Log health status
                health = actions.get('health', 'unknown')
                if health != 'healthy':
                    self.logger.info(f"⚠️ Saúde da posição: {health}")
                
                # Executa saída se necessário
                if actions.get('exit_signal'):
                    self.logger.warning(f"🚨 Sinal de saída: {actions.get('reason')}")
                    await self._execute_exit()
                    return
                
                # Modifica SL se necessário (trailing stop)
                if actions.get('modify_sl') and actions.get('new_sl'):
                    new_sl = actions['new_sl']
                    reason = actions.get('reason', 'Trailing stop')
                    
                    # Só move se for favorável
                    is_buy = self.current_position.type == SignalType.BUY
                    current_sl = self.current_position.sl
                    
                    should_move = (is_buy and new_sl > current_sl) or \
                                  (not is_buy and new_sl < current_sl)
                    
                    if should_move:
                        self.logger.info(
                            f"📈 {reason}: SL {current_sl:.5f} → {new_sl:.5f}"
                        )
                        await self._modify_position_sl(new_sl)
                
                # Saída parcial se necessário
                if actions.get('partial_exit') and actions.get('partial_volume', 0) > 0:
                    volume = actions['partial_volume']
                    reason = actions.get('reason', 'Saída parcial')
                    self.logger.info(f"📊 {reason}: fechando {volume} lots")
                    await self._execute_partial_exit(volume)
            else:
                # Fallback para trailing básico
                await self._check_trailing_stop()
            
            # Verifica saída manual
            if await self._should_exit():
                await self._execute_exit()
                
        except Exception as e:
            self.logger.error(f"Erro ao gerenciar posição: {e}")
    
    async def _modify_position_sl(self, new_sl: float) -> bool:
        """Modifica SL da posição."""
        if not self.current_position:
            return False
        
        try:
            result = self.mt5_orders.modify_position(
                ticket=self.current_position.ticket,
                sl=new_sl,
                tp=self.current_position.tp,
            )
            
            if result:
                self.current_position.sl = new_sl
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao modificar SL: {e}")
            return False
    
    async def _execute_partial_exit(self, volume: float) -> bool:
        """Executa saída parcial."""
        if not self.current_position:
            return False
        
        try:
            result = self.mt5_orders.close_position_partial(
                ticket=self.current_position.ticket,
                volume=volume,
            )
            
            if result:
                self.current_position.volume -= volume
                self.logger.success(f"✅ Saída parcial: {volume} lots")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Erro na saída parcial: {e}")
            return False
                
        except Exception as e:
            self.logger.error(f"Erro ao gerenciar posição: {e}")
    
    async def _handle_position_closed(self) -> None:
        """Trata posição fechada."""
        if self.current_position:
            profit = self.current_position.profit
            
            # Registra trade no state manager
            await self.state_manager.record_trade(profit)
            
            # Registra no TradingEngine para estatísticas
            if self.engine:
                strategy = self.engine._active_strategy or "unknown"
                self.engine.record_trade_result(profit, strategy)
            
            if profit < 0:
                self._last_loss_time = datetime.now()
            
            self.logger.info(
                f"📊 Posição fechada: "
                f"{'🟢' if profit >= 0 else '🔴'} ${profit:+.2f}"
            )
            
            # Notifica callbacks
            for callback in self._on_trade_callbacks:
                try:
                    await callback("exit", self.current_position)
                except Exception:
                    pass
            
            self.current_position = None
            await self.state_manager.update_context(
                has_position=False,
                position_profit=0.0
            )
    
    async def _check_trailing_stop(self) -> None:
        """Verifica e atualiza trailing stop."""
        if not self.current_position:
            return
        
        # Implementar lógica de trailing stop
        pass
    
    async def _should_exit(self) -> bool:
        """Verifica se deve sair da posição."""
        # Implementar lógica de saída
        return False
    
    async def _execute_exit(self) -> None:
        """Executa saída da posição."""
        if not self.current_position:
            return
        
        try:
            await self.state_manager.set_phase(TradingPhase.EXITING)
            
            result = self.mt5_orders.close_position(self.current_position.ticket)
            
            if result:
                self.logger.success(f"✅ Posição fechada manualmente")
                await self._handle_position_closed()
            else:
                self.logger.error("❌ Erro ao fechar posição")
                
        except Exception as e:
            self.logger.error(f"Erro ao executar saída: {e}")
        
        await self.state_manager.set_phase(TradingPhase.WAITING)
    
    async def _save_state(self) -> None:
        """Salva estado do bot."""
        try:
            state_dir = Path(f"brain/data/bots/{self.symbol.lower()}")
            state_dir.mkdir(parents=True, exist_ok=True)
            
            await self.state_manager.save_state(str(state_dir / "state.json"))
            self.logger.debug("Estado salvo")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar estado: {e}")
    
    # === API Pública ===
    
    def on_signal(self, callback: Callable) -> None:
        """Registra callback para sinais."""
        self._on_signal_callbacks.append(callback)
    
    def on_trade(self, callback: Callable) -> None:
        """Registra callback para trades."""
        self._on_trade_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do bot incluindo Engine."""
        status = self.state_manager.get_status()
        
        # Adiciona informações do TradingEngine
        if self.engine:
            status['engine'] = self.engine.get_status()
            status['engine_mode'] = self.trading_mode.value
        else:
            status['engine'] = None
            status['engine_mode'] = 'fallback'
        
        return status
    
    def get_engine_statistics(self) -> Optional[Dict[str, Any]]:
        """Retorna estatísticas do TradingEngine."""
        if self.engine:
            return self.engine.get_status().get('statistics')
        return None
    
    def get_recent_decisions(self, count: int = 10) -> List[Dict]:
        """Retorna decisões recentes do Engine."""
        if self.engine:
            return self.engine.get_recent_decisions(count)
        return []
    
    def get_statistics(self) -> BotStatistics:
        """Retorna estatísticas."""
        return self.state_manager.statistics
    
    def get_context(self) -> BotContext:
        """Retorna contexto atual."""
        return self.state_manager.context
    
    @property
    def is_running(self) -> bool:
        """Verifica se bot está rodando."""
        return self.state_manager.is_running()
    
    @property
    def can_trade(self) -> bool:
        """Verifica se bot pode operar."""
        return self.state_manager.can_trade()


# Factory function
def create_bot(
    symbol: str,
    config: Config,
    strategy: Optional[Any] = None,
    trading_mode: TradingMode = TradingMode.ADAPTIVE,
) -> TradingBot:
    """
    Cria instância de bot com TradingEngine integrado.
    
    Args:
        symbol: Símbolo para operar (ex: EURUSD)
        config: Configuração do sistema
        strategy: Estratégia opcional (se None, usa Engine adaptativo)
        trading_mode: Modo do TradingEngine (ADAPTIVE, SCALPING, TREND, etc)
    """
    bot_id = f"bot_{symbol.lower()}"
    return TradingBot(bot_id, symbol, config, strategy, trading_mode)
