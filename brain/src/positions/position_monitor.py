"""
VIRTUS Position Monitor
========================

Monitor em tempo real de posições.
Responsável por:
- Monitoramento contínuo de preços
- Detecção de triggers (trailing, breakeven, TP parcial)
- Alertas de risco
- Gestão dinâmica de saídas
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict

from ..core import VirtusLogger, Position, OrderType
from ..core.exceptions import PositionError
from .position_manager import PositionManager, PositionRecord, PositionMetrics, PositionEvent
from .position_state import PositionState, StateType
from .exits import ExitManager, ExitSignal, ExitReason, TrailingStopConfig, PartialExitConfig


class AlertLevel(Enum):
    """Níveis de alerta."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


class MonitorAlert(Enum):
    """Tipos de alertas do monitor."""
    # P&L Alerts
    PROFIT_TARGET = "profit_target"
    LOSS_LIMIT = "loss_limit"
    DRAWDOWN_HIGH = "drawdown_high"
    
    # Action Alerts
    TRAILING_ACTIVATED = "trailing_activated"
    BREAKEVEN_TRIGGERED = "breakeven_triggered"
    PARTIAL_CLOSE_READY = "partial_close_ready"
    
    # Risk Alerts
    POSITION_TOO_LONG = "position_too_long"
    VOLATILITY_SPIKE = "volatility_spike"
    SPREAD_HIGH = "spread_high"
    
    # Market Alerts
    NEWS_APPROACHING = "news_approaching"
    SESSION_ENDING = "session_ending"


@dataclass
class AlertRecord:
    """Registro de alerta."""
    alert_type: MonitorAlert
    level: AlertLevel
    ticket: int
    symbol: str
    message: str
    value: float = 0.0
    threshold: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.alert_type.value,
            'level': self.level.value,
            'ticket': self.ticket,
            'symbol': self.symbol,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class MonitorConfig:
    """Configuração do monitor."""
    # Intervalos
    check_interval: float = 1.0  # segundos
    price_update_interval: float = 0.5  # segundos
    
    # Trailing Stop
    trailing_enabled: bool = True
    trailing_activation_pips: float = 15.0
    trailing_distance_pips: float = 10.0
    trailing_step_pips: float = 5.0
    
    # Breakeven
    breakeven_enabled: bool = True
    breakeven_activation_pips: float = 10.0
    breakeven_lock_pips: float = 2.0
    
    # Partial Close
    partial_close_enabled: bool = True
    partial_close_levels: List[Dict] = field(default_factory=lambda: [
        {'pips': 20, 'percent': 30},
        {'pips': 40, 'percent': 30},
        {'pips': 60, 'percent': 40},
    ])
    
    # Alertas
    profit_alert_pips: float = 30.0
    loss_alert_pips: float = 20.0
    max_position_hours: int = 24
    max_drawdown_percent: float = 50.0  # % do lucro máximo
    
    # Spread
    max_spread_pips: float = 5.0


@dataclass
class PositionMonitorState:
    """Estado de monitoramento de uma posição."""
    ticket: int
    symbol: str
    
    # Status de features
    trailing_active: bool = False
    trailing_start_price: Optional[float] = None
    breakeven_set: bool = False
    partial_closes_done: int = 0
    
    # Tracking
    last_check: datetime = field(default_factory=datetime.now)
    last_price: float = 0.0
    last_spread: float = 0.0
    
    # Alertas enviados (evita duplicatas)
    alerts_sent: set = field(default_factory=set)
    
    # Métricas de pico
    peak_profit_pips: float = 0.0
    peak_drawdown_pips: float = 0.0


class PositionMonitor:
    """
    Monitor em tempo real de posições.
    
    Monitora continuamente todas as posições ativas e executa
    ações automáticas baseadas em configuração:
    - Trailing stop dinâmico
    - Breakeven automático
    - Fechamento parcial
    - Alertas de risco
    
    Cada bot tem seu próprio PositionMonitor.
    """
    
    def __init__(
        self,
        position_manager: PositionManager,
        mt5_data: Any = None,  # MT5DataService
        config: Optional[MonitorConfig] = None
    ):
        self.position_manager = position_manager
        self.mt5_data = mt5_data
        self.config = config or MonitorConfig()
        
        self.symbol = position_manager.symbol
        self.logger = VirtusLogger.get_logger(f"monitor.{self.symbol.lower()}")
        
        # Estados de monitoramento por posição
        self._states: Dict[int, PositionMonitorState] = {}
        
        # Alertas ativos
        self._alerts: List[AlertRecord] = []
        
        # Callbacks
        self._alert_callbacks: List[Callable] = []
        self._action_callbacks: List[Callable] = []
        
        # Controle do loop
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Pip value
        self._pip_value = self._get_pip_value()
        
        # Cache de preços
        self._price_cache: Dict[str, Tuple[float, float, datetime]] = {}  # bid, ask, time
    
    def _get_pip_value(self) -> float:
        """Retorna valor do pip."""
        pip_values = {
            'XAUUSD': 0.01,
            'EURUSD': 0.0001,
            'GBPUSD': 0.0001,
            'USDJPY': 0.01,
        }
        return pip_values.get(self.symbol, 0.0001)
    
    # ========================================================================
    # CONTROLE DO MONITOR
    # ========================================================================
    
    async def start(self) -> None:
        """Inicia o monitor."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        self.logger.info(f"🔍 Monitor de posições iniciado para {self.symbol}")
    
    async def stop(self) -> None:
        """Para o monitor."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(f"🔍 Monitor de posições parado para {self.symbol}")
    
    async def _monitor_loop(self) -> None:
        """Loop principal de monitoramento."""
        while self._running:
            try:
                await self._check_all_positions()
                await asyncio.sleep(self.config.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Erro no loop de monitoramento: {e}")
                await asyncio.sleep(5)
    
    # ========================================================================
    # MONITORAMENTO
    # ========================================================================
    
    async def _check_all_positions(self) -> None:
        """Verifica todas as posições ativas."""
        positions = self.position_manager.get_all_positions()
        
        for position in positions:
            await self._check_position(position)
    
    async def _check_position(self, position: PositionRecord) -> None:
        """
        Verifica uma posição específica.
        
        Executa todas as verificações:
        - Atualização de preço
        - Trailing stop
        - Breakeven
        - Fechamento parcial
        - Alertas
        """
        ticket = position.ticket
        
        # Obtém ou cria estado de monitoramento
        if ticket not in self._states:
            self._states[ticket] = PositionMonitorState(
                ticket=ticket,
                symbol=position.symbol
            )
        
        state = self._states[ticket]
        
        # Atualiza preço atual
        current_price, spread = await self._get_current_price()
        if current_price <= 0:
            return
        
        state.last_price = current_price
        state.last_spread = spread
        state.last_check = datetime.now()
        
        # Atualiza métricas da posição
        metrics = await self.position_manager.update_position(
            ticket=ticket,
            current_price=current_price
        )
        
        # Calcula P&L em pips
        pnl_pips = self._calculate_pnl_pips(position, current_price)
        
        # Atualiza picos
        if pnl_pips > state.peak_profit_pips:
            state.peak_profit_pips = pnl_pips
        if pnl_pips < state.peak_drawdown_pips:
            state.peak_drawdown_pips = pnl_pips
        
        # Executa verificações
        await self._check_breakeven(position, state, pnl_pips)
        await self._check_trailing_stop(position, state, pnl_pips, current_price)
        await self._check_partial_close(position, state, pnl_pips, current_price)
        await self._check_alerts(position, state, pnl_pips, metrics)
    
    async def _get_current_price(self) -> Tuple[float, float]:
        """
        Obtém preço atual e spread.
        
        Returns:
            (preço_médio, spread)
        """
        try:
            if self.mt5_data:
                tick = self.mt5_data.get_tick(self.symbol)
                if tick:
                    mid_price = (tick.bid + tick.ask) / 2
                    spread = tick.ask - tick.bid
                    return mid_price, spread / self._pip_value
            
            # Fallback: usa cache ou retorna 0
            if self.symbol in self._price_cache:
                bid, ask, _ = self._price_cache[self.symbol]
                return (bid + ask) / 2, (ask - bid) / self._pip_value
            
            return 0.0, 0.0
            
        except Exception as e:
            self.logger.error(f"Erro ao obter preço: {e}")
            return 0.0, 0.0
    
    def _calculate_pnl_pips(self, position: PositionRecord, current_price: float) -> float:
        """Calcula P&L em pips."""
        if position.order_type == OrderType.BUY:
            return (current_price - position.entry_price) / self._pip_value
        else:
            return (position.entry_price - current_price) / self._pip_value
    
    # ========================================================================
    # BREAKEVEN
    # ========================================================================
    
    async def _check_breakeven(
        self,
        position: PositionRecord,
        state: PositionMonitorState,
        pnl_pips: float
    ) -> None:
        """Verifica e aplica breakeven."""
        if not self.config.breakeven_enabled:
            return
        
        if state.breakeven_set:
            return  # Já foi aplicado
        
        # Verifica se atingiu ativação
        if pnl_pips >= self.config.breakeven_activation_pips:
            success = await self.position_manager.set_breakeven(
                ticket=position.ticket,
                lock_pips=self.config.breakeven_lock_pips
            )
            
            if success:
                state.breakeven_set = True
                
                # Cria alerta
                await self._create_alert(
                    alert_type=MonitorAlert.BREAKEVEN_TRIGGERED,
                    level=AlertLevel.INFO,
                    position=position,
                    message=f"Breakeven ativado (lucro: {pnl_pips:.1f} pips)",
                    value=pnl_pips,
                    threshold=self.config.breakeven_activation_pips
                )
                
                # Notifica callback
                await self._notify_action('breakeven', position, {
                    'pnl_pips': pnl_pips,
                    'lock_pips': self.config.breakeven_lock_pips
                })
    
    # ========================================================================
    # TRAILING STOP
    # ========================================================================
    
    async def _check_trailing_stop(
        self,
        position: PositionRecord,
        state: PositionMonitorState,
        pnl_pips: float,
        current_price: float
    ) -> None:
        """Verifica e atualiza trailing stop."""
        if not self.config.trailing_enabled:
            return
        
        # Ativa trailing quando atingir threshold
        if not state.trailing_active:
            if pnl_pips >= self.config.trailing_activation_pips:
                state.trailing_active = True
                state.trailing_start_price = current_price
                
                await self._create_alert(
                    alert_type=MonitorAlert.TRAILING_ACTIVATED,
                    level=AlertLevel.INFO,
                    position=position,
                    message=f"Trailing Stop ativado (lucro: {pnl_pips:.1f} pips)",
                    value=pnl_pips,
                    threshold=self.config.trailing_activation_pips
                )
            return
        
        # Calcula novo SL
        is_buy = position.order_type == OrderType.BUY
        distance = self.config.trailing_distance_pips * self._pip_value
        
        if is_buy:
            new_sl = current_price - distance
            # Só atualiza se for melhor e tiver movido o step mínimo
            min_move = position.current_sl + (self.config.trailing_step_pips * self._pip_value)
            if new_sl > min_move:
                await self.position_manager.update_trailing_stop(
                    ticket=position.ticket,
                    new_sl=new_sl,
                    distance_pips=self.config.trailing_distance_pips
                )
        else:
            new_sl = current_price + distance
            max_move = position.current_sl - (self.config.trailing_step_pips * self._pip_value)
            if new_sl < max_move:
                await self.position_manager.update_trailing_stop(
                    ticket=position.ticket,
                    new_sl=new_sl,
                    distance_pips=self.config.trailing_distance_pips
                )
    
    # ========================================================================
    # PARTIAL CLOSE
    # ========================================================================
    
    async def _check_partial_close(
        self,
        position: PositionRecord,
        state: PositionMonitorState,
        pnl_pips: float,
        current_price: float
    ) -> None:
        """Verifica e executa fechamento parcial."""
        if not self.config.partial_close_enabled:
            return
        
        levels = self.config.partial_close_levels
        
        if state.partial_closes_done >= len(levels):
            return  # Todos os níveis já foram executados
        
        # Verifica próximo nível
        next_level = levels[state.partial_closes_done]
        target_pips = next_level['pips']
        close_percent = next_level['percent']
        
        if pnl_pips >= target_pips:
            try:
                result = await self.position_manager.partial_close(
                    ticket=position.ticket,
                    close_percent=close_percent,
                    exit_price=current_price
                )
                
                state.partial_closes_done += 1
                
                await self._create_alert(
                    alert_type=MonitorAlert.PARTIAL_CLOSE_READY,
                    level=AlertLevel.INFO,
                    position=position,
                    message=f"Fechamento parcial: {close_percent}% @ {pnl_pips:.1f} pips",
                    value=pnl_pips,
                    threshold=target_pips
                )
                
                await self._notify_action('partial_close', position, {
                    'percent': close_percent,
                    'pnl_pips': pnl_pips,
                    'partial_pnl': result['partial_pnl']
                })
                
            except PositionError as e:
                self.logger.warning(f"Erro no fechamento parcial: {e}")
    
    # ========================================================================
    # ALERTAS
    # ========================================================================
    
    async def _check_alerts(
        self,
        position: PositionRecord,
        state: PositionMonitorState,
        pnl_pips: float,
        metrics: PositionMetrics
    ) -> None:
        """Verifica condições de alerta."""
        
        # Alerta de lucro
        if pnl_pips >= self.config.profit_alert_pips:
            alert_key = f"profit_{position.ticket}"
            if alert_key not in state.alerts_sent:
                await self._create_alert(
                    alert_type=MonitorAlert.PROFIT_TARGET,
                    level=AlertLevel.INFO,
                    position=position,
                    message=f"Posição em lucro significativo: {pnl_pips:.1f} pips",
                    value=pnl_pips,
                    threshold=self.config.profit_alert_pips
                )
                state.alerts_sent.add(alert_key)
        
        # Alerta de perda
        if pnl_pips <= -self.config.loss_alert_pips:
            alert_key = f"loss_{position.ticket}"
            if alert_key not in state.alerts_sent:
                await self._create_alert(
                    alert_type=MonitorAlert.LOSS_LIMIT,
                    level=AlertLevel.WARNING,
                    position=position,
                    message=f"Posição em perda: {pnl_pips:.1f} pips",
                    value=pnl_pips,
                    threshold=-self.config.loss_alert_pips
                )
                state.alerts_sent.add(alert_key)
        
        # Alerta de drawdown (% do lucro máximo)
        if state.peak_profit_pips > 10:  # Só se teve lucro significativo
            drawdown_from_peak = state.peak_profit_pips - pnl_pips
            drawdown_percent = (drawdown_from_peak / state.peak_profit_pips) * 100
            
            if drawdown_percent >= self.config.max_drawdown_percent:
                alert_key = f"drawdown_{position.ticket}"
                if alert_key not in state.alerts_sent:
                    await self._create_alert(
                        alert_type=MonitorAlert.DRAWDOWN_HIGH,
                        level=AlertLevel.WARNING,
                        position=position,
                        message=f"Drawdown alto: {drawdown_percent:.1f}% do lucro máximo",
                        value=drawdown_percent,
                        threshold=self.config.max_drawdown_percent
                    )
                    state.alerts_sent.add(alert_key)
        
        # Alerta de duração da posição
        duration_hours = metrics.duration_seconds / 3600
        if duration_hours >= self.config.max_position_hours:
            alert_key = f"duration_{position.ticket}"
            if alert_key not in state.alerts_sent:
                await self._create_alert(
                    alert_type=MonitorAlert.POSITION_TOO_LONG,
                    level=AlertLevel.WARNING,
                    position=position,
                    message=f"Posição aberta há {duration_hours:.1f} horas",
                    value=duration_hours,
                    threshold=self.config.max_position_hours
                )
                state.alerts_sent.add(alert_key)
        
        # Alerta de spread alto
        if state.last_spread > self.config.max_spread_pips:
            alert_key = f"spread_{position.ticket}_{int(datetime.now().timestamp() / 300)}"  # A cada 5 min
            if alert_key not in state.alerts_sent:
                await self._create_alert(
                    alert_type=MonitorAlert.SPREAD_HIGH,
                    level=AlertLevel.WARNING,
                    position=position,
                    message=f"Spread alto: {state.last_spread:.1f} pips",
                    value=state.last_spread,
                    threshold=self.config.max_spread_pips
                )
                state.alerts_sent.add(alert_key)
    
    async def _create_alert(
        self,
        alert_type: MonitorAlert,
        level: AlertLevel,
        position: PositionRecord,
        message: str,
        value: float = 0.0,
        threshold: float = 0.0
    ) -> AlertRecord:
        """Cria e registra um alerta."""
        alert = AlertRecord(
            alert_type=alert_type,
            level=level,
            ticket=position.ticket,
            symbol=position.symbol,
            message=message,
            value=value,
            threshold=threshold
        )
        
        self._alerts.append(alert)
        
        # Log
        log_msg = f"[{alert_type.value}] #{position.ticket}: {message}"
        if level == AlertLevel.URGENT or level == AlertLevel.CRITICAL:
            self.logger.warning(f"⚠️ {log_msg}")
        else:
            self.logger.info(f"ℹ️ {log_msg}")
        
        # Notifica callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Erro no callback de alerta: {e}")
        
        return alert
    
    async def _notify_action(
        self,
        action: str,
        position: PositionRecord,
        data: Dict[str, Any]
    ) -> None:
        """Notifica callbacks de ação."""
        for callback in self._action_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(action, position, data)
                else:
                    callback(action, position, data)
            except Exception as e:
                self.logger.error(f"Erro no callback de ação: {e}")
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def on_alert(self, callback: Callable) -> None:
        """Registra callback para alertas."""
        self._alert_callbacks.append(callback)
    
    def on_action(self, callback: Callable) -> None:
        """Registra callback para ações (trailing, breakeven, etc)."""
        self._action_callbacks.append(callback)
    
    # ========================================================================
    # CONSULTAS
    # ========================================================================
    
    def get_monitor_state(self, ticket: int) -> Optional[PositionMonitorState]:
        """Obtém estado de monitoramento de uma posição."""
        return self._states.get(ticket)
    
    def get_alerts(
        self,
        ticket: Optional[int] = None,
        level: Optional[AlertLevel] = None,
        limit: int = 50
    ) -> List[AlertRecord]:
        """
        Obtém alertas.
        
        Args:
            ticket: Filtrar por ticket
            level: Filtrar por nível
            limit: Máximo de alertas
            
        Returns:
            Lista de alertas
        """
        alerts = self._alerts
        
        if ticket:
            alerts = [a for a in alerts if a.ticket == ticket]
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        # Ordena por timestamp (mais recente primeiro)
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)
        
        return alerts[:limit]
    
    def get_unacknowledged_alerts(self) -> List[AlertRecord]:
        """Obtém alertas não reconhecidos."""
        return [a for a in self._alerts if not a.acknowledged]
    
    def acknowledge_alert(self, timestamp: datetime) -> bool:
        """Marca alerta como reconhecido."""
        for alert in self._alerts:
            if alert.timestamp == timestamp:
                alert.acknowledged = True
                return True
        return False
    
    def clear_alerts(self, older_than_hours: int = 24) -> int:
        """Remove alertas antigos."""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        old_count = len(self._alerts)
        self._alerts = [a for a in self._alerts if a.timestamp > cutoff]
        return old_count - len(self._alerts)
    
    # ========================================================================
    # CLEANUP
    # ========================================================================
    
    def cleanup_closed_position(self, ticket: int) -> None:
        """Remove estado de posição fechada."""
        if ticket in self._states:
            del self._states[ticket]
    
    async def close(self) -> None:
        """Fecha o monitor."""
        await self.stop()
        self._states.clear()
        self.logger.info(f"Monitor {self.symbol} fechado")


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_position_monitor(
    position_manager: PositionManager,
    mt5_data: Any = None,
    config: Optional[Dict] = None
) -> PositionMonitor:
    """
    Factory para criar PositionMonitor.
    
    Args:
        position_manager: PositionManager associado
        mt5_data: MT5DataService (opcional)
        config: Configuração como dicionário
        
    Returns:
        PositionMonitor configurado
    """
    monitor_config = None
    
    if config:
        monitor_config = MonitorConfig(
            check_interval=config.get('check_interval', 1.0),
            trailing_enabled=config.get('trailing_stop', {}).get('enabled', True),
            trailing_activation_pips=config.get('trailing_stop', {}).get('activation_pips', 15.0),
            trailing_distance_pips=config.get('trailing_stop', {}).get('distance_pips', 10.0),
            breakeven_enabled=config.get('breakeven', {}).get('enabled', True),
            breakeven_activation_pips=config.get('breakeven', {}).get('activation_pips', 10.0),
            breakeven_lock_pips=config.get('breakeven', {}).get('lock_pips', 2.0),
            partial_close_enabled=config.get('partial_close', {}).get('enabled', True),
            partial_close_levels=config.get('partial_close', {}).get('levels', []),
        )
    
    return PositionMonitor(
        position_manager=position_manager,
        mt5_data=mt5_data,
        config=monitor_config
    )
