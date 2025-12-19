"""
VIRTUS - Sistema de Alertas de Drawdown
========================================

Monitora drawdown em tempo real e dispara alertas quando atinge níveis críticos.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("virtus.drawdown_alert")


class AlertLevel(str, Enum):
    """Níveis de alerta de drawdown."""
    NORMAL = "normal"           # < 2%
    CAUTION = "caution"         # 2-5%
    WARNING = "warning"         # 5-10%
    CRITICAL = "critical"       # 10-15%
    EMERGENCY = "emergency"     # > 15%


class AlertAction(str, Enum):
    """Ações automáticas em resposta ao drawdown."""
    NONE = "none"
    NOTIFY = "notify"
    REDUCE_RISK = "reduce_risk"
    PAUSE_NEW_TRADES = "pause_new_trades"
    CLOSE_LOSERS = "close_losers"
    CLOSE_ALL = "close_all"


@dataclass
class DrawdownThreshold:
    """Configuração de threshold de drawdown."""
    level: AlertLevel
    percent: float
    action: AlertAction
    cooldown_minutes: int = 5  # Tempo mínimo entre alertas do mesmo nível


@dataclass
class DrawdownConfig:
    """Configuração do sistema de alertas."""
    # Thresholds padrão
    thresholds: List[DrawdownThreshold] = field(default_factory=lambda: [
        DrawdownThreshold(AlertLevel.CAUTION, 2.0, AlertAction.NOTIFY, 10),
        DrawdownThreshold(AlertLevel.WARNING, 5.0, AlertAction.NOTIFY, 5),
        DrawdownThreshold(AlertLevel.CRITICAL, 10.0, AlertAction.PAUSE_NEW_TRADES, 3),
        DrawdownThreshold(AlertLevel.EMERGENCY, 15.0, AlertAction.CLOSE_ALL, 1),
    ])
    
    # Monitoramento
    check_interval: float = 5.0  # segundos
    
    # Baseline
    use_daily_high: bool = True  # Usa high do dia como referência
    use_session_high: bool = False  # Usa high da sessão atual
    
    # Notificações
    telegram_enabled: bool = True
    webhook_enabled: bool = True
    email_enabled: bool = False
    
    # Recuperação
    recovery_threshold: float = 1.0  # % de recuperação para voltar ao normal


@dataclass
class DrawdownState:
    """Estado atual do drawdown."""
    current_equity: float = 0.0
    baseline_equity: float = 0.0
    peak_equity: float = 0.0
    
    drawdown_amount: float = 0.0
    drawdown_percent: float = 0.0
    
    current_level: AlertLevel = AlertLevel.NORMAL
    previous_level: AlertLevel = AlertLevel.NORMAL
    
    last_alert_time: Dict[AlertLevel, datetime] = field(default_factory=dict)
    alerts_today: int = 0
    
    # Histórico
    max_drawdown_today: float = 0.0
    max_drawdown_session: float = 0.0
    max_drawdown_all_time: float = 0.0
    
    trading_paused: bool = False
    positions_closed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_equity": round(self.current_equity, 2),
            "baseline_equity": round(self.baseline_equity, 2),
            "peak_equity": round(self.peak_equity, 2),
            "drawdown_amount": round(self.drawdown_amount, 2),
            "drawdown_percent": round(self.drawdown_percent, 2),
            "current_level": self.current_level.value,
            "alerts_today": self.alerts_today,
            "max_drawdown_today": round(self.max_drawdown_today, 2),
            "max_drawdown_session": round(self.max_drawdown_session, 2),
            "max_drawdown_all_time": round(self.max_drawdown_all_time, 2),
            "trading_paused": self.trading_paused,
        }


@dataclass
class DrawdownAlert:
    """Estrutura de um alerta de drawdown."""
    timestamp: datetime
    level: AlertLevel
    drawdown_percent: float
    drawdown_amount: float
    equity: float
    baseline: float
    action_taken: AlertAction
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "drawdown_percent": round(self.drawdown_percent, 2),
            "drawdown_amount": round(self.drawdown_amount, 2),
            "equity": round(self.equity, 2),
            "baseline": round(self.baseline, 2),
            "action_taken": self.action_taken.value,
            "message": self.message,
        }


class DrawdownMonitor:
    """
    Monitor de drawdown em tempo real.
    
    Uso:
        monitor = DrawdownMonitor(config)
        monitor.on_alert(callback)
        await monitor.start()
    """
    
    def __init__(self, config: Optional[DrawdownConfig] = None):
        self.config = config or DrawdownConfig()
        self.state = DrawdownState()
        
        # Callbacks
        self._alert_callbacks: List[Callable] = []
        self._action_callbacks: Dict[AlertAction, List[Callable]] = {
            action: [] for action in AlertAction
        }
        
        # Control
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Histórico de alertas
        self._alert_history: List[DrawdownAlert] = []
        self._max_history = 100
    
    def on_alert(self, callback: Callable):
        """Registra callback para qualquer alerta."""
        self._alert_callbacks.append(callback)
    
    def on_action(self, action: AlertAction, callback: Callable):
        """Registra callback para ação específica."""
        self._action_callbacks[action].append(callback)
    
    def set_baseline(self, equity: float):
        """Define baseline de equity."""
        self.state.baseline_equity = equity
        self.state.peak_equity = max(self.state.peak_equity, equity)
        logger.info(f"Baseline definido: ${equity:,.2f}")
    
    async def start(self, initial_equity: Optional[float] = None):
        """Inicia o monitoramento."""
        if self._running:
            return
        
        self._running = True
        
        if initial_equity:
            self.set_baseline(initial_equity)
        
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("📊 Drawdown Monitor iniciado")
    
    async def stop(self):
        """Para o monitoramento."""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Drawdown Monitor parado")
    
    async def update_equity(self, equity: float):
        """Atualiza equity atual e calcula drawdown."""
        self.state.current_equity = equity
        
        # Atualiza peak
        if equity > self.state.peak_equity:
            self.state.peak_equity = equity
        
        # Usa baseline ou peak para cálculo
        reference = self.state.baseline_equity or self.state.peak_equity
        
        if reference > 0:
            self.state.drawdown_amount = reference - equity
            self.state.drawdown_percent = (self.state.drawdown_amount / reference) * 100
            
            # Atualiza máximos
            self.state.max_drawdown_today = max(
                self.state.max_drawdown_today, 
                self.state.drawdown_percent
            )
            self.state.max_drawdown_session = max(
                self.state.max_drawdown_session, 
                self.state.drawdown_percent
            )
            self.state.max_drawdown_all_time = max(
                self.state.max_drawdown_all_time, 
                self.state.drawdown_percent
            )
        
        # Verifica thresholds
        await self._check_thresholds()
    
    async def _check_thresholds(self):
        """Verifica se algum threshold foi atingido."""
        new_level = AlertLevel.NORMAL
        triggered_threshold = None
        
        # Encontra o nível mais alto atingido
        for threshold in sorted(self.config.thresholds, key=lambda t: t.percent):
            if self.state.drawdown_percent >= threshold.percent:
                new_level = threshold.level
                triggered_threshold = threshold
        
        # Verifica se houve mudança de nível
        if new_level != self.state.current_level:
            # Escalada de nível (piorou)
            if self._level_value(new_level) > self._level_value(self.state.current_level):
                await self._trigger_alert(new_level, triggered_threshold)
            
            # Recuperação (melhorou)
            elif self._level_value(new_level) < self._level_value(self.state.current_level):
                await self._handle_recovery(new_level)
            
            self.state.previous_level = self.state.current_level
            self.state.current_level = new_level
    
    def _level_value(self, level: AlertLevel) -> int:
        """Retorna valor numérico do nível para comparação."""
        order = {
            AlertLevel.NORMAL: 0,
            AlertLevel.CAUTION: 1,
            AlertLevel.WARNING: 2,
            AlertLevel.CRITICAL: 3,
            AlertLevel.EMERGENCY: 4,
        }
        return order.get(level, 0)
    
    async def _trigger_alert(self, level: AlertLevel, threshold: Optional[DrawdownThreshold]):
        """Dispara alerta de drawdown."""
        now = datetime.now()
        
        # Verifica cooldown
        if level in self.state.last_alert_time:
            cooldown = timedelta(minutes=threshold.cooldown_minutes if threshold else 5)
            if now - self.state.last_alert_time[level] < cooldown:
                return
        
        self.state.last_alert_time[level] = now
        self.state.alerts_today += 1
        
        # Determina ação
        action = threshold.action if threshold else AlertAction.NOTIFY
        
        # Monta mensagem
        emoji = self._get_level_emoji(level)
        message = (
            f"{emoji} ALERTA DE DRAWDOWN: {level.value.upper()}\n"
            f"📉 Drawdown: {self.state.drawdown_percent:.2f}% (${self.state.drawdown_amount:,.2f})\n"
            f"💰 Equity: ${self.state.current_equity:,.2f}\n"
            f"📊 Baseline: ${self.state.baseline_equity:,.2f}\n"
            f"⚡ Ação: {action.value}"
        )
        
        logger.warning(message)
        
        # Cria alerta
        alert = DrawdownAlert(
            timestamp=now,
            level=level,
            drawdown_percent=self.state.drawdown_percent,
            drawdown_amount=self.state.drawdown_amount,
            equity=self.state.current_equity,
            baseline=self.state.baseline_equity,
            action_taken=action,
            message=message,
        )
        
        # Salva no histórico
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]
        
        # Executa ação
        await self._execute_action(action, alert)
        
        # Notifica callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Erro em callback de alerta: {e}")
    
    async def _execute_action(self, action: AlertAction, alert: DrawdownAlert):
        """Executa ação automática."""
        if action == AlertAction.PAUSE_NEW_TRADES:
            self.state.trading_paused = True
            logger.warning("⏸️ Trading pausado devido ao drawdown")
            
        elif action == AlertAction.CLOSE_ALL:
            self.state.trading_paused = True
            self.state.positions_closed = True
            logger.critical("🚨 FECHANDO TODAS AS POSIÇÕES!")
        
        # Notifica callbacks específicos da ação
        for callback in self._action_callbacks.get(action, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Erro em callback de ação {action}: {e}")
    
    async def _handle_recovery(self, new_level: AlertLevel):
        """Processa recuperação de drawdown."""
        if new_level == AlertLevel.NORMAL:
            if self.state.trading_paused:
                self.state.trading_paused = False
                logger.info("▶️ Trading retomado - drawdown normalizado")
            
            logger.info(f"✅ Drawdown recuperado: {self.state.drawdown_percent:.2f}%")
    
    def _get_level_emoji(self, level: AlertLevel) -> str:
        """Retorna emoji para o nível."""
        emojis = {
            AlertLevel.NORMAL: "✅",
            AlertLevel.CAUTION: "⚠️",
            AlertLevel.WARNING: "🟡",
            AlertLevel.CRITICAL: "🔴",
            AlertLevel.EMERGENCY: "🚨",
        }
        return emojis.get(level, "📊")
    
    async def _monitor_loop(self):
        """Loop principal de monitoramento."""
        while self._running:
            try:
                await asyncio.sleep(self.config.check_interval)
                
                # Obtém equity atual do MT5
                equity = await self._get_current_equity()
                if equity is not None:
                    await self.update_equity(equity)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no monitor loop: {e}")
    
    async def _get_current_equity(self) -> Optional[float]:
        """Obtém equity atual do MT5."""
        try:
            import MetaTrader5 as mt5
            
            account = mt5.account_info()
            if account:
                return account.equity
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter equity: {e}")
            return None
    
    def get_state(self) -> Dict[str, Any]:
        """Retorna estado atual."""
        return self.state.to_dict()
    
    def get_alerts(self, limit: int = 20) -> List[Dict]:
        """Retorna últimos alertas."""
        return [a.to_dict() for a in self._alert_history[-limit:]]
    
    def reset_daily_stats(self):
        """Reseta estatísticas diárias."""
        self.state.max_drawdown_today = 0.0
        self.state.alerts_today = 0
        logger.info("📊 Estatísticas diárias resetadas")


# Instância global
drawdown_monitor = DrawdownMonitor()


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    async def on_alert(alert: DrawdownAlert):
        print(f"🚨 ALERTA: {alert.level.value} - {alert.drawdown_percent:.2f}%")
    
    async def on_close_all(alert: DrawdownAlert):
        print("🚨 FECHANDO TUDO!")
        # Implementar fechamento de posições
    
    async def main():
        # Configura thresholds customizados
        config = DrawdownConfig(
            thresholds=[
                DrawdownThreshold(AlertLevel.CAUTION, 1.0, AlertAction.NOTIFY, 10),
                DrawdownThreshold(AlertLevel.WARNING, 3.0, AlertAction.NOTIFY, 5),
                DrawdownThreshold(AlertLevel.CRITICAL, 5.0, AlertAction.PAUSE_NEW_TRADES, 3),
                DrawdownThreshold(AlertLevel.EMERGENCY, 10.0, AlertAction.CLOSE_ALL, 1),
            ]
        )
        
        monitor = DrawdownMonitor(config)
        monitor.on_alert(on_alert)
        monitor.on_action(AlertAction.CLOSE_ALL, on_close_all)
        
        # Define baseline
        monitor.set_baseline(10000.0)
        
        # Inicia
        await monitor.start()
        
        # Simula drawdown
        for equity in [9900, 9700, 9500, 9400, 9000, 8500, 9200, 9800, 10000]:
            await monitor.update_equity(equity)
            print(f"Equity: ${equity} | DD: {monitor.state.drawdown_percent:.2f}%")
            await asyncio.sleep(1)
        
        await monitor.stop()
    
    asyncio.run(main())
