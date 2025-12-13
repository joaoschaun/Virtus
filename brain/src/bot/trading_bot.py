"""
BRAIN - Trading Bot
Bot de trading para um símbolo específico
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from ..core.logger import get_logger
from ..core.config import BotConfig
from ..core.types import (
    Signal, SignalDirection, Position, OrderType,
    Timeframe, MarketRegime
)
from ..core.exceptions import BotError, RiskError
from ..mt5 import (
    MT5Manager, get_mt5_manager,
    OrderManager, OrderRequest, create_order_manager,
    MT5DataFeed, create_datafeed
)
from ..brain import BrainService

logger = get_logger("bot")


class BotState(Enum):
    """Estado do bot"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class BotStats:
    """Estatísticas do bot"""
    trades_today: int = 0
    wins_today: int = 0
    losses_today: int = 0
    profit_today: float = 0.0
    max_drawdown_today: float = 0.0
    signals_generated: int = 0
    signals_executed: int = 0
    last_trade_time: Optional[datetime] = None
    started_at: Optional[datetime] = None


class TradingBot:
    """
    Bot de trading para um símbolo
    
    Responsabilidades:
    - Receber dados de mercado
    - Gerar sinais via estratégias
    - Validar com Brain e Risk
    - Executar ordens
    - Gerenciar posições
    """
    
    def __init__(
        self,
        config: BotConfig,
        mt5_manager: Optional[MT5Manager] = None,
        brain_service: Optional[BrainService] = None
    ):
        self._config = config
        self._bot_id = config.id
        self._symbol = config.symbol
        
        # Dependências
        self._mt5 = mt5_manager or get_mt5_manager()
        self._brain = brain_service or BrainService()
        self._order_manager = create_order_manager(self._mt5)
        self._datafeed = create_datafeed(self._mt5)
        
        # Estado
        self._state = BotState.STOPPED
        self._stats = BotStats()
        
        # Estratégias ativas
        self._strategies: List[Any] = []
        
        # Posições do bot
        self._positions: List[Position] = []
        
        # Sinais pendentes
        self._pending_signals: List[Signal] = []
        
        # Lock de execução
        self._lock = asyncio.Lock()
        
        # Task principal
        self._main_task: Optional[asyncio.Task] = None
        
        # Logger específico
        self._logger = get_logger(f"bot.{self._bot_id}")
    
    @property
    def bot_id(self) -> str:
        return self._bot_id
    
    @property
    def symbol(self) -> str:
        return self._symbol
    
    @property
    def state(self) -> BotState:
        return self._state
    
    @property
    def is_running(self) -> bool:
        return self._state == BotState.RUNNING
    
    @property
    def stats(self) -> BotStats:
        return self._stats
    
    async def start(self):
        """Inicia o bot"""
        if self._state == BotState.RUNNING:
            self._logger.warning("Bot já está rodando")
            return
        
        self._logger.info(f"Iniciando bot {self._bot_id} para {self._symbol}")
        self._state = BotState.STARTING
        
        try:
            # Verificar conexão MT5
            if not self._mt5.is_connected:
                raise BotError("MT5 não conectado")
            
            # Iniciar datafeed
            await self._datafeed.start()
            self._datafeed.subscribe(
                self._symbol,
                on_tick=self._on_tick,
                on_bar=self._on_bar,
                timeframe=self._config.primary_timeframe
            )
            
            # Carregar estratégias
            await self._load_strategies()
            
            # Carregar posições existentes
            await self._sync_positions()
            
            # Iniciar loop principal
            self._main_task = asyncio.create_task(self._main_loop())
            
            self._state = BotState.RUNNING
            self._stats.started_at = datetime.now()
            
            self._logger.info(f"Bot {self._bot_id} iniciado com sucesso")
            
        except Exception as e:
            self._state = BotState.ERROR
            self._logger.error(f"Erro ao iniciar bot: {e}")
            raise
    
    async def stop(self):
        """Para o bot"""
        self._logger.info(f"Parando bot {self._bot_id}")
        
        self._state = BotState.STOPPED
        
        # Cancelar task principal
        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        
        # Parar datafeed
        await self._datafeed.stop()
        
        self._logger.info(f"Bot {self._bot_id} parado")
    
    async def pause(self):
        """Pausa o bot (não abre novas posições)"""
        self._state = BotState.PAUSED
        self._logger.info(f"Bot {self._bot_id} pausado")
    
    async def resume(self):
        """Resume o bot"""
        if self._state == BotState.PAUSED:
            self._state = BotState.RUNNING
            self._logger.info(f"Bot {self._bot_id} resumido")
    
    # ==========================================================================
    # LOOP PRINCIPAL
    # ==========================================================================
    
    async def _main_loop(self):
        """Loop principal do bot"""
        while self._state in [BotState.RUNNING, BotState.PAUSED]:
            try:
                # Sincronizar posições
                await self._sync_positions()
                
                # Processar sinais pendentes
                if self._state == BotState.RUNNING:
                    await self._process_pending_signals()
                
                # Gerenciar posições existentes
                await self._manage_positions()
                
                # Intervalo
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Erro no loop principal: {e}")
                await asyncio.sleep(5)
    
    def _on_tick(self, tick):
        """Callback para novos ticks"""
        # Estratégias podem reagir a ticks se necessário
        pass
    
    def _on_bar(self, bar):
        """Callback para novas barras"""
        # Gerar sinais quando nova barra fecha
        asyncio.create_task(self._generate_signals())
    
    # ==========================================================================
    # ESTRATÉGIAS E SINAIS
    # ==========================================================================
    
    async def _load_strategies(self):
        """Carrega estratégias configuradas"""
        # TODO: Carregar estratégias baseado na config
        # Por enquanto, lista vazia
        self._strategies = []
        self._logger.debug(f"Carregadas {len(self._strategies)} estratégias")
    
    async def _generate_signals(self):
        """Gera sinais das estratégias"""
        if self._state != BotState.RUNNING:
            return
        
        async with self._lock:
            signals = []
            
            # Obter dados
            bars = await self._datafeed.get_bars(
                self._symbol,
                self._config.primary_timeframe,
                count=200
            )
            
            # Obter contexto do Brain
            context = await self._brain.get_macro_context(self._symbol)
            
            # Gerar sinal de cada estratégia
            for strategy in self._strategies:
                try:
                    signal = await strategy.generate_signal(bars, context)
                    if signal:
                        signals.append(signal)
                except Exception as e:
                    self._logger.error(f"Erro na estratégia {strategy.name}: {e}")
            
            # Adicionar sinais à fila
            for signal in signals:
                self._stats.signals_generated += 1
                self._pending_signals.append(signal)
    
    async def _process_pending_signals(self):
        """Processa sinais pendentes"""
        if not self._pending_signals:
            return
        
        async with self._lock:
            signals_to_process = self._pending_signals.copy()
            self._pending_signals.clear()
            
            for signal in signals_to_process:
                await self._execute_signal(signal)
    
    async def _execute_signal(self, signal: Signal):
        """
        Executa um sinal
        
        Args:
            signal: Sinal a executar
        """
        try:
            # Verificar se pode abrir posição
            if not await self._can_open_position():
                self._logger.debug("Não é possível abrir nova posição")
                return
            
            # Validar com risk management
            if not await self._validate_risk(signal):
                self._logger.debug("Sinal rejeitado pelo risk management")
                return
            
            # Consultar Brain para validação final
            brain_ok = await self._validate_with_brain(signal)
            if not brain_ok:
                self._logger.debug("Sinal rejeitado pelo Brain")
                return
            
            # Calcular volume
            volume = await self._calculate_volume(signal)
            
            # Preparar ordem
            order_type = OrderType.BUY if signal.direction == SignalDirection.BUY else OrderType.SELL
            
            request = OrderRequest(
                symbol=self._symbol,
                order_type=order_type,
                volume=volume,
                sl=signal.stop_loss,
                tp=signal.take_profit,
                magic=self._config.magic_number,
                comment=f"{self._bot_id}_{signal.strategy}",
                bot_id=self._bot_id,
                signal_id=signal.id
            )
            
            # Executar
            result = await self._order_manager.send_order(request)
            
            if result.success:
                self._stats.signals_executed += 1
                self._stats.last_trade_time = datetime.now()
                self._stats.trades_today += 1
                
                self._logger.info(
                    f"Sinal executado: {signal.direction.value} @ {result.price}"
                )
            else:
                self._logger.warning(f"Falha ao executar sinal: {result.message}")
                
        except Exception as e:
            self._logger.error(f"Erro ao executar sinal: {e}")
    
    # ==========================================================================
    # VALIDAÇÕES
    # ==========================================================================
    
    async def _can_open_position(self) -> bool:
        """Verifica se pode abrir nova posição"""
        # Limite de posições
        max_positions = self._config.risk.get("max_positions", 1)
        if len(self._positions) >= max_positions:
            return False
        
        # Limite de trades diários
        max_daily = self._config.risk.get("max_daily_trades", 10)
        if self._stats.trades_today >= max_daily:
            return False
        
        # Verificar horário de trading
        if not self._is_trading_hour():
            return False
        
        return True
    
    def _is_trading_hour(self) -> bool:
        """Verifica se está no horário de trading"""
        now = datetime.now()
        hour = now.hour
        
        sessions = self._config.sessions
        
        # Verificar cada sessão
        for session in sessions:
            start = session.get("start", 0)
            end = session.get("end", 24)
            
            if start <= hour < end:
                return True
        
        return False
    
    async def _validate_risk(self, signal: Signal) -> bool:
        """Valida sinal com risk management"""
        # TODO: Implementar validação completa
        
        # Verificar confiança mínima
        min_confidence = self._config.risk.get("min_signal_confidence", 0.6)
        if signal.confidence < min_confidence:
            return False
        
        return True
    
    async def _validate_with_brain(self, signal: Signal) -> bool:
        """Valida sinal com Brain service"""
        try:
            # Verificar calendário
            events = await self._brain.get_calendar_events(self._symbol, days_ahead=1)
            high_impact = [e for e in events if e.impact.value == "high"]
            
            # Se há evento de alto impacto próximo, não operar
            if high_impact:
                for event in high_impact:
                    time_until = event.datetime - datetime.now()
                    if time_until.total_seconds() < 3600:  # Menos de 1 hora
                        self._logger.info(
                            f"Evento de alto impacto próximo: {event.name}"
                        )
                        return False
            
            return True
            
        except Exception as e:
            self._logger.warning(f"Erro ao validar com Brain: {e}")
            return True  # Permite em caso de erro
    
    async def _calculate_volume(self, signal: Signal) -> float:
        """Calcula volume para o trade"""
        # Obter info da conta
        account = await self._mt5.get_account_info()
        equity = account.get("equity", 0)
        
        # Risco por trade
        risk_percent = self._config.risk.get("risk_per_trade", 1.0) / 100
        risk_amount = equity * risk_percent
        
        # Distância do SL em pips
        tick = await self._mt5.get_tick(self._symbol)
        current_price = tick["bid"] if signal.direction == SignalDirection.SELL else tick["ask"]
        
        if signal.stop_loss:
            sl_distance_pips = abs(current_price - signal.stop_loss) / 0.0001  # Simplificado
        else:
            sl_distance_pips = 50  # Default
        
        # Calcular volume
        volume = await self._order_manager.calculate_position_size(
            self._symbol,
            risk_amount,
            sl_distance_pips
        )
        
        # Limites
        min_vol = self._config.risk.get("min_lot_size", 0.01)
        max_vol = self._config.risk.get("max_lot_size", 1.0)
        
        return max(min_vol, min(volume, max_vol))
    
    # ==========================================================================
    # GERENCIAMENTO DE POSIÇÕES
    # ==========================================================================
    
    async def _sync_positions(self):
        """Sincroniza posições com MT5"""
        mt5_positions = await self._mt5.get_positions(self._symbol)
        
        # Filtrar por magic number
        self._positions = [
            p for p in mt5_positions
            if p.magic == self._config.magic_number
        ]
    
    async def _manage_positions(self):
        """Gerencia posições abertas"""
        for position in self._positions:
            try:
                await self._check_trailing_stop(position)
                await self._check_breakeven(position)
            except Exception as e:
                self._logger.error(f"Erro ao gerenciar posição {position.ticket}: {e}")
    
    async def _check_trailing_stop(self, position: Position):
        """Verifica e atualiza trailing stop"""
        if not self._config.risk.get("use_trailing_stop", False):
            return
        
        # TODO: Implementar trailing stop
        pass
    
    async def _check_breakeven(self, position: Position):
        """Verifica e ativa breakeven"""
        if not self._config.risk.get("use_breakeven", False):
            return
        
        # TODO: Implementar breakeven
        pass
    
    # ==========================================================================
    # MÉTODOS PÚBLICOS
    # ==========================================================================
    
    async def close_all_positions(self):
        """Fecha todas as posições do bot"""
        for position in self._positions:
            try:
                await self._order_manager.close_position(position.ticket)
            except Exception as e:
                self._logger.error(f"Erro ao fechar posição {position.ticket}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do bot"""
        return {
            "bot_id": self._bot_id,
            "symbol": self._symbol,
            "state": self._state.value,
            "positions": len(self._positions),
            "stats": {
                "trades_today": self._stats.trades_today,
                "wins_today": self._stats.wins_today,
                "losses_today": self._stats.losses_today,
                "profit_today": self._stats.profit_today,
                "signals_generated": self._stats.signals_generated,
                "signals_executed": self._stats.signals_executed,
                "started_at": self._stats.started_at.isoformat() if self._stats.started_at else None
            }
        }
