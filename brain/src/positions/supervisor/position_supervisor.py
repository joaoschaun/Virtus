"""
VIRTUS Position Supervisor
===========================

Supervisor de posições em tempo real com:
- Monitoramento contínuo de todas as posições
- Break-even automático
- Detecção de hedge
- Health check das posições
- Alertas de anomalias
- Auto-recovery
- Correlação entre posições
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict
import numpy as np

from ...core import VirtusLogger


class PositionHealth(Enum):
    """Estado de saúde da posição."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    STALE = "stale"  # Sem atualização há muito tempo
    ORPHAN = "orphan"  # Sem correspondência no broker


class AlertType(Enum):
    """Tipos de alerta."""
    DRAWDOWN_HIGH = "drawdown_high"
    POSITION_STUCK = "position_stuck"
    HEDGE_DETECTED = "hedge_detected"
    CORRELATION_RISK = "correlation_risk"
    SL_NOT_SET = "sl_not_set"
    TP_NOT_SET = "tp_not_set"
    EXPOSURE_HIGH = "exposure_high"
    MAE_EXCESSIVE = "mae_excessive"
    TIME_IN_TRADE = "time_in_trade"
    SLIPPAGE_DETECTED = "slippage_detected"


@dataclass
class PositionInfo:
    """Informações completas de uma posição."""
    ticket: int
    symbol: str
    direction: str  # "buy" ou "sell"
    volume: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    profit: float
    swap: float
    commission: float
    open_time: datetime
    magic_number: int
    comment: str
    
    # Métricas calculadas
    profit_pips: float = 0.0
    drawdown: float = 0.0
    mae: float = 0.0  # Maximum Adverse Excursion
    mfe: float = 0.0  # Maximum Favorable Excursion
    time_in_trade: timedelta = field(default_factory=timedelta)
    health: PositionHealth = PositionHealth.HEALTHY
    
    # Tracking
    last_update: datetime = field(default_factory=datetime.now)
    highest_profit: float = 0.0
    lowest_profit: float = 0.0
    be_activated: bool = False


@dataclass
class SupervisorAlert:
    """Alerta do supervisor."""
    alert_type: AlertType
    severity: str  # "info", "warning", "critical"
    position_ticket: Optional[int]
    symbol: Optional[str]
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


@dataclass
class HedgeInfo:
    """Informações de hedge detectado."""
    symbol: str
    long_tickets: List[int]
    short_tickets: List[int]
    net_volume: float
    total_volume: float
    is_full_hedge: bool
    profit_loss: float


@dataclass
class BreakEvenConfig:
    """Configuração de break-even."""
    enabled: bool = True
    activation_pips: float = 15.0  # Pips de lucro para ativar
    offset_pips: float = 1.0  # Pips acima do entry para BE
    trail_after_be: bool = True
    trail_pips: float = 10.0


class PositionSupervisor:
    """
    Supervisor de posições em tempo real.
    
    Features:
    - Monitoramento contínuo
    - Break-even automático
    - Detecção de hedge
    - Health monitoring
    - Alertas
    - Correlação de risco
    """
    
    def __init__(
        self,
        be_config: Optional[BreakEvenConfig] = None,
        check_interval: float = 1.0,  # segundos
        max_drawdown_alert: float = 2.0,  # porcentagem
        max_time_in_trade_hours: float = 24.0,
        correlation_threshold: float = 0.7,
    ):
        self.logger = VirtusLogger.get_logger("position_supervisor")
        
        self.be_config = be_config or BreakEvenConfig()
        self.check_interval = check_interval
        self.max_drawdown_alert = max_drawdown_alert
        self.max_time_hours = max_time_in_trade_hours
        self.correlation_threshold = correlation_threshold
        
        # Posições
        self.positions: Dict[int, PositionInfo] = {}
        
        # Alertas
        self.alerts: List[SupervisorAlert] = []
        self.max_alerts = 100
        
        # Hedges detectados
        self.hedges: Dict[str, HedgeInfo] = {}
        
        # Correlações conhecidas
        self._correlations = {
            ('EURUSD', 'GBPUSD'): 0.85,
            ('EURUSD', 'USDCHF'): -0.90,
            ('GBPUSD', 'USDCHF'): -0.85,
            ('AUDUSD', 'NZDUSD'): 0.90,
            ('USDJPY', 'EURJPY'): 0.85,
            ('XAUUSD', 'EURUSD'): 0.40,
            ('XAUUSD', 'DXY'): -0.80,
        }
        
        # Callbacks
        self._on_alert_callbacks: List[Callable] = []
        self._on_be_callbacks: List[Callable] = []
        
        # Estado
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Lock
        self._lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Inicia o supervisor."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._supervision_loop())
        self.logger.info("🔍 Position Supervisor started")
    
    async def stop(self) -> None:
        """Para o supervisor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("Position Supervisor stopped")
    
    async def _supervision_loop(self) -> None:
        """Loop principal de supervisão."""
        while self._running:
            try:
                await self._check_all_positions()
                await self._detect_hedges()
                await self._check_correlation_risk()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Supervision loop error: {e}")
                await asyncio.sleep(5)
    
    async def update_position(
        self,
        ticket: int,
        current_price: float,
        profit: float,
        **kwargs
    ) -> None:
        """Atualiza informações de uma posição."""
        async with self._lock:
            if ticket not in self.positions:
                return
            
            pos = self.positions[ticket]
            pos.current_price = current_price
            pos.profit = profit
            pos.last_update = datetime.now()
            
            # Atualiza time in trade
            pos.time_in_trade = datetime.now() - pos.open_time
            
            # Calcula profit em pips
            pos.profit_pips = self._calculate_pips(pos)
            
            # Atualiza MAE/MFE
            if profit > pos.highest_profit:
                pos.highest_profit = profit
                pos.mfe = profit
            if profit < pos.lowest_profit:
                pos.lowest_profit = profit
                pos.mae = abs(profit)
            
            # Calcula drawdown do pico
            if pos.highest_profit > 0:
                pos.drawdown = (pos.highest_profit - profit) / pos.highest_profit * 100
            
            # Atualiza outros campos
            for key, value in kwargs.items():
                if hasattr(pos, key):
                    setattr(pos, key, value)
            
            # Verifica break-even
            await self._check_breakeven(pos)
            
            # Verifica saúde
            self._update_health(pos)
    
    async def register_position(self, position_info: PositionInfo) -> None:
        """Registra nova posição para supervisão."""
        async with self._lock:
            position_info.last_update = datetime.now()
            position_info.highest_profit = position_info.profit
            position_info.lowest_profit = position_info.profit
            self.positions[position_info.ticket] = position_info
            
            self.logger.info(
                f"Position registered: #{position_info.ticket} "
                f"{position_info.direction.upper()} {position_info.symbol}"
            )
            
            # Verifica se tem SL/TP
            if not position_info.stop_loss:
                self._add_alert(
                    AlertType.SL_NOT_SET,
                    "warning",
                    position_info.ticket,
                    position_info.symbol,
                    f"Position #{position_info.ticket} has no stop loss"
                )
    
    async def unregister_position(self, ticket: int) -> None:
        """Remove posição da supervisão."""
        async with self._lock:
            if ticket in self.positions:
                del self.positions[ticket]
                self.logger.debug(f"Position #{ticket} unregistered")
    
    async def _check_all_positions(self) -> None:
        """Verifica todas as posições."""
        async with self._lock:
            for ticket, pos in list(self.positions.items()):
                # Verifica se está stale
                time_since_update = datetime.now() - pos.last_update
                if time_since_update.total_seconds() > 60:
                    pos.health = PositionHealth.STALE
                    continue
                
                # Verifica drawdown alto
                if pos.drawdown > self.max_drawdown_alert:
                    self._add_alert(
                        AlertType.DRAWDOWN_HIGH,
                        "warning",
                        ticket,
                        pos.symbol,
                        f"Position #{ticket} drawdown at {pos.drawdown:.1f}%",
                        {'drawdown': pos.drawdown, 'profit': pos.profit}
                    )
                
                # Verifica tempo em trade
                hours_in_trade = pos.time_in_trade.total_seconds() / 3600
                if hours_in_trade > self.max_time_hours:
                    self._add_alert(
                        AlertType.TIME_IN_TRADE,
                        "info",
                        ticket,
                        pos.symbol,
                        f"Position #{ticket} open for {hours_in_trade:.1f} hours"
                    )
                
                # Verifica MAE excessivo
                if pos.mae > 0 and pos.entry_price > 0:
                    mae_pct = pos.mae / (pos.entry_price * pos.volume * 100000) * 100
                    if mae_pct > 3.0:  # 3% MAE
                        self._add_alert(
                            AlertType.MAE_EXCESSIVE,
                            "warning",
                            ticket,
                            pos.symbol,
                            f"Position #{ticket} has excessive MAE: ${pos.mae:.2f}"
                        )
    
    async def _check_breakeven(self, pos: PositionInfo) -> None:
        """Verifica e aplica break-even."""
        if not self.be_config.enabled:
            return
        
        if pos.be_activated:
            return  # Já ativou BE
        
        if not pos.stop_loss:
            return  # Não tem SL
        
        # Verifica se atingiu os pips de ativação
        if pos.profit_pips >= self.be_config.activation_pips:
            # Calcula novo SL (break-even + offset)
            offset = self.be_config.offset_pips
            
            if 'JPY' in pos.symbol:
                offset_price = offset / 100
            elif 'XAU' in pos.symbol:
                offset_price = offset / 10
            else:
                offset_price = offset / 10000
            
            if pos.direction == "buy":
                new_sl = pos.entry_price + offset_price
                if new_sl > pos.stop_loss:
                    pos.be_activated = True
                    
                    # Notifica callbacks
                    for callback in self._on_be_callbacks:
                        await callback(pos.ticket, new_sl)
                    
                    self.logger.info(
                        f"🛡️ Break-even activated for #{pos.ticket} "
                        f"at {new_sl:.5f}"
                    )
            else:
                new_sl = pos.entry_price - offset_price
                if new_sl < pos.stop_loss:
                    pos.be_activated = True
                    
                    for callback in self._on_be_callbacks:
                        await callback(pos.ticket, new_sl)
                    
                    self.logger.info(
                        f"🛡️ Break-even activated for #{pos.ticket} "
                        f"at {new_sl:.5f}"
                    )
    
    async def _detect_hedges(self) -> None:
        """Detecta posições em hedge."""
        async with self._lock:
            # Agrupa por símbolo
            by_symbol: Dict[str, List[PositionInfo]] = defaultdict(list)
            for pos in self.positions.values():
                by_symbol[pos.symbol].append(pos)
            
            self.hedges.clear()
            
            for symbol, positions in by_symbol.items():
                longs = [p for p in positions if p.direction == "buy"]
                shorts = [p for p in positions if p.direction == "sell"]
                
                if longs and shorts:
                    long_volume = sum(p.volume for p in longs)
                    short_volume = sum(p.volume for p in shorts)
                    net_volume = long_volume - short_volume
                    total_volume = long_volume + short_volume
                    
                    is_full = abs(net_volume) < 0.01
                    
                    total_profit = sum(p.profit for p in positions)
                    
                    hedge_info = HedgeInfo(
                        symbol=symbol,
                        long_tickets=[p.ticket for p in longs],
                        short_tickets=[p.ticket for p in shorts],
                        net_volume=net_volume,
                        total_volume=total_volume,
                        is_full_hedge=is_full,
                        profit_loss=total_profit
                    )
                    
                    self.hedges[symbol] = hedge_info
                    
                    # Alerta
                    self._add_alert(
                        AlertType.HEDGE_DETECTED,
                        "warning" if is_full else "info",
                        None,
                        symbol,
                        f"Hedge detected on {symbol}: "
                        f"Long {long_volume:.2f} vs Short {short_volume:.2f}",
                        {'hedge_info': hedge_info.__dict__}
                    )
    
    async def _check_correlation_risk(self) -> None:
        """Verifica risco de correlação entre posições."""
        async with self._lock:
            symbols = list(set(p.symbol for p in self.positions.values()))
            
            if len(symbols) < 2:
                return
            
            for i, sym1 in enumerate(symbols):
                for sym2 in symbols[i+1:]:
                    correlation = self._get_correlation(sym1, sym2)
                    
                    if abs(correlation) >= self.correlation_threshold:
                        # Verifica se posições estão na mesma direção (risco)
                        # ou direções opostas (hedge natural)
                        
                        pos1 = [p for p in self.positions.values() if p.symbol == sym1]
                        pos2 = [p for p in self.positions.values() if p.symbol == sym2]
                        
                        if not pos1 or not pos2:
                            continue
                        
                        dir1 = pos1[0].direction
                        dir2 = pos2[0].direction
                        
                        # Se correlação positiva e mesma direção = risco
                        # Se correlação negativa e direções opostas = risco
                        risky = (
                            (correlation > 0 and dir1 == dir2) or
                            (correlation < 0 and dir1 != dir2)
                        )
                        
                        if risky:
                            self._add_alert(
                                AlertType.CORRELATION_RISK,
                                "warning",
                                None,
                                f"{sym1}/{sym2}",
                                f"Correlated positions: {sym1} and {sym2} "
                                f"(correlation: {correlation:.2f})",
                                {'symbols': [sym1, sym2], 'correlation': correlation}
                            )
    
    def _get_correlation(self, sym1: str, sym2: str) -> float:
        """Obtém correlação entre dois símbolos."""
        # Verifica ambas as direções
        if (sym1, sym2) in self._correlations:
            return self._correlations[(sym1, sym2)]
        elif (sym2, sym1) in self._correlations:
            return self._correlations[(sym2, sym1)]
        return 0.0
    
    def _calculate_pips(self, pos: PositionInfo) -> float:
        """Calcula lucro em pips."""
        if pos.direction == "buy":
            diff = pos.current_price - pos.entry_price
        else:
            diff = pos.entry_price - pos.current_price
        
        if 'JPY' in pos.symbol:
            return diff * 100
        elif 'XAU' in pos.symbol:
            return diff * 10
        else:
            return diff * 10000
    
    def _update_health(self, pos: PositionInfo) -> None:
        """Atualiza status de saúde da posição."""
        issues = 0
        
        # Sem stop loss
        if not pos.stop_loss:
            issues += 2
        
        # Drawdown alto
        if pos.drawdown > self.max_drawdown_alert:
            issues += 1
        
        # MAE excessivo
        if pos.mae > pos.mfe * 2 and pos.mfe > 0:
            issues += 1
        
        # Tempo excessivo
        if pos.time_in_trade.total_seconds() > self.max_time_hours * 3600:
            issues += 1
        
        if issues >= 3:
            pos.health = PositionHealth.CRITICAL
        elif issues >= 1:
            pos.health = PositionHealth.WARNING
        else:
            pos.health = PositionHealth.HEALTHY
    
    def _add_alert(
        self,
        alert_type: AlertType,
        severity: str,
        ticket: Optional[int],
        symbol: Optional[str],
        message: str,
        data: Dict[str, Any] = None
    ) -> None:
        """Adiciona um alerta."""
        # Evita duplicatas recentes (últimos 5 minutos)
        for existing in self.alerts[-20:]:
            if (existing.alert_type == alert_type and 
                existing.position_ticket == ticket and
                (datetime.now() - existing.timestamp).total_seconds() < 300):
                return
        
        alert = SupervisorAlert(
            alert_type=alert_type,
            severity=severity,
            position_ticket=ticket,
            symbol=symbol,
            message=message,
            data=data or {}
        )
        
        self.alerts.append(alert)
        
        # Limita tamanho
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Log
        if severity == "critical":
            self.logger.error(f"🚨 {message}")
        elif severity == "warning":
            self.logger.warning(f"⚠️ {message}")
        else:
            self.logger.info(f"ℹ️ {message}")
        
        # Notifica callbacks
        for callback in self._on_alert_callbacks:
            asyncio.create_task(callback(alert))
    
    def on_alert(self, callback: Callable) -> None:
        """Registra callback para alertas."""
        self._on_alert_callbacks.append(callback)
    
    def on_breakeven(self, callback: Callable) -> None:
        """Registra callback para break-even."""
        self._on_be_callbacks.append(callback)
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """Retorna resumo de todas as posições."""
        if not self.positions:
            return {
                'total_positions': 0,
                'total_profit': 0,
                'by_symbol': {},
                'health': {'healthy': 0, 'warning': 0, 'critical': 0}
            }
        
        total_profit = sum(p.profit for p in self.positions.values())
        
        by_symbol = defaultdict(lambda: {'count': 0, 'profit': 0, 'volume': 0})
        for pos in self.positions.values():
            by_symbol[pos.symbol]['count'] += 1
            by_symbol[pos.symbol]['profit'] += pos.profit
            by_symbol[pos.symbol]['volume'] += pos.volume
        
        health_counts = defaultdict(int)
        for pos in self.positions.values():
            health_counts[pos.health.value] += 1
        
        return {
            'total_positions': len(self.positions),
            'total_profit': round(total_profit, 2),
            'total_volume': round(sum(p.volume for p in self.positions.values()), 2),
            'by_symbol': dict(by_symbol),
            'health': dict(health_counts),
            'hedges_detected': len(self.hedges),
            'recent_alerts': len([a for a in self.alerts if not a.acknowledged])
        }
    
    def get_position_details(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Retorna detalhes de uma posição específica."""
        pos = self.positions.get(ticket)
        if not pos:
            return None
        
        return {
            'ticket': pos.ticket,
            'symbol': pos.symbol,
            'direction': pos.direction,
            'volume': pos.volume,
            'entry_price': pos.entry_price,
            'current_price': pos.current_price,
            'stop_loss': pos.stop_loss,
            'take_profit': pos.take_profit,
            'profit': round(pos.profit, 2),
            'profit_pips': round(pos.profit_pips, 1),
            'mae': round(pos.mae, 2),
            'mfe': round(pos.mfe, 2),
            'drawdown': round(pos.drawdown, 1),
            'time_in_trade': str(pos.time_in_trade),
            'health': pos.health.value,
            'be_activated': pos.be_activated,
        }
    
    def get_alerts(
        self, 
        severity: Optional[str] = None,
        unacknowledged_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Retorna alertas filtrados."""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        
        return [
            {
                'type': a.alert_type.value,
                'severity': a.severity,
                'ticket': a.position_ticket,
                'symbol': a.symbol,
                'message': a.message,
                'timestamp': a.timestamp.isoformat(),
                'acknowledged': a.acknowledged,
            }
            for a in alerts[-20:]  # Últimos 20
        ]
    
    def acknowledge_alert(self, index: int) -> bool:
        """Marca alerta como reconhecido."""
        if 0 <= index < len(self.alerts):
            self.alerts[index].acknowledged = True
            return True
        return False
    
    def get_hedges(self) -> Dict[str, Dict[str, Any]]:
        """Retorna hedges detectados."""
        return {
            symbol: {
                'long_tickets': h.long_tickets,
                'short_tickets': h.short_tickets,
                'net_volume': h.net_volume,
                'total_volume': h.total_volume,
                'is_full_hedge': h.is_full_hedge,
                'profit_loss': round(h.profit_loss, 2),
            }
            for symbol, h in self.hedges.items()
        }
