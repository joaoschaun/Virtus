"""
VIRTUS Alert Manager
=====================

Sistema de alertas inteligentes para notificações
baseadas em condições de mercado e performance.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger


class AlertPriority(Enum):
    """Prioridade do alerta."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AlertType(Enum):
    """Tipos de alertas."""
    # Performance
    DRAWDOWN = "drawdown"
    WIN_STREAK = "win_streak"
    LOSE_STREAK = "lose_streak"
    DAILY_TARGET_HIT = "daily_target_hit"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    
    # Sistema
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"
    MT5_DISCONNECT = "mt5_disconnect"
    LATENCY_HIGH = "latency_high"
    
    # Trading
    POSITION_STUCK = "position_stuck"
    LARGE_POSITION = "large_position"
    MARGIN_LOW = "margin_low"
    
    # Mercado
    HIGH_VOLATILITY = "high_volatility"
    SPREAD_WIDE = "spread_wide"
    NEWS_EVENT = "news_event"
    
    # Bot
    BOT_ERROR = "bot_error"
    BOT_STOPPED = "bot_stopped"
    
    # Custom
    CUSTOM = "custom"


@dataclass
class Alert:
    """Um alerta."""
    type: AlertType
    priority: AlertPriority
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Metadados
    source: str = ""  # bot, system, market
    symbol: str = ""
    value: float = 0.0
    threshold: float = 0.0
    
    # Status
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    # Notificação
    notified: bool = False
    notification_channels: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.notification_channels:
            self.notification_channels = []
    
    @property
    def age_minutes(self) -> float:
        """Idade do alerta em minutos."""
        return (datetime.now() - self.timestamp).total_seconds() / 60
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dict."""
        return {
            'type': self.type.value,
            'priority': self.priority.value,
            'title': self.title,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'symbol': self.symbol,
            'value': self.value,
            'threshold': self.threshold,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
        }


@dataclass
class AlertRule:
    """Regra para geração de alertas."""
    name: str
    alert_type: AlertType
    priority: AlertPriority
    condition: Callable[[Dict[str, Any]], bool]
    message_template: str
    cooldown_minutes: int = 5  # Tempo mínimo entre alertas do mesmo tipo
    enabled: bool = True
    
    # Último disparo
    last_triggered: Optional[datetime] = None
    
    def can_trigger(self) -> bool:
        """Verifica se pode disparar (cooldown)."""
        if not self.enabled:
            return False
        if self.last_triggered is None:
            return True
        elapsed = (datetime.now() - self.last_triggered).total_seconds() / 60
        return elapsed >= self.cooldown_minutes


class AlertManager:
    """
    Gerenciador central de alertas.
    
    Features:
    - Regras configuráveis
    - Cooldown para evitar spam
    - Múltiplos canais de notificação
    - Histórico de alertas
    - Acknowledge e resolve
    """
    
    def __init__(self, max_history: int = 1000):
        self.logger = VirtusLogger.get_logger("AlertManager")
        
        # Regras de alerta
        self._rules: Dict[str, AlertRule] = {}
        
        # Alertas ativos e histórico
        self._active_alerts: List[Alert] = []
        self._alert_history: deque = deque(maxlen=max_history)
        
        # Callbacks de notificação
        self._notification_callbacks: Dict[str, Callable[[Alert], None]] = {}
        
        # Alertas únicos (não repetir enquanto ativo)
        self._active_alert_types: Set[str] = set()
        
        # Configurar regras padrão
        self._setup_default_rules()
        
        self.logger.info("AlertManager inicializado")
    
    def _setup_default_rules(self):
        """Configura regras padrão de alertas."""
        # Drawdown
        self.add_rule(AlertRule(
            name="drawdown_warning",
            alert_type=AlertType.DRAWDOWN,
            priority=AlertPriority.HIGH,
            condition=lambda ctx: ctx.get('drawdown', 0) >= 10,
            message_template="Drawdown atingiu {value:.1f}% (limite: {threshold}%)",
            cooldown_minutes=30,
        ))
        
        self.add_rule(AlertRule(
            name="drawdown_critical",
            alert_type=AlertType.DRAWDOWN,
            priority=AlertPriority.CRITICAL,
            condition=lambda ctx: ctx.get('drawdown', 0) >= 15,
            message_template="⚠️ CRÍTICO: Drawdown em {value:.1f}%!",
            cooldown_minutes=15,
        ))
        
        # Lose streak
        self.add_rule(AlertRule(
            name="lose_streak",
            alert_type=AlertType.LOSE_STREAK,
            priority=AlertPriority.HIGH,
            condition=lambda ctx: ctx.get('lose_streak', 0) >= 5,
            message_template="Sequência de {value} perdas consecutivas",
            cooldown_minutes=60,
        ))
        
        # Win streak (positivo)
        self.add_rule(AlertRule(
            name="win_streak",
            alert_type=AlertType.WIN_STREAK,
            priority=AlertPriority.LOW,
            condition=lambda ctx: ctx.get('win_streak', 0) >= 5,
            message_template="🔥 Sequência de {value} vitórias!",
            cooldown_minutes=60,
        ))
        
        # MT5 desconectado
        self.add_rule(AlertRule(
            name="mt5_disconnect",
            alert_type=AlertType.MT5_DISCONNECT,
            priority=AlertPriority.CRITICAL,
            condition=lambda ctx: not ctx.get('mt5_connected', True),
            message_template="❌ MT5 Desconectado!",
            cooldown_minutes=5,
        ))
        
        # CPU alta
        self.add_rule(AlertRule(
            name="cpu_high",
            alert_type=AlertType.CPU_HIGH,
            priority=AlertPriority.MEDIUM,
            condition=lambda ctx: ctx.get('cpu_percent', 0) >= 90,
            message_template="CPU em {value:.0f}%",
            cooldown_minutes=15,
        ))
        
        # Memória alta
        self.add_rule(AlertRule(
            name="memory_high",
            alert_type=AlertType.MEMORY_HIGH,
            priority=AlertPriority.MEDIUM,
            condition=lambda ctx: ctx.get('memory_percent', 0) >= 85,
            message_template="Memória em {value:.0f}%",
            cooldown_minutes=15,
        ))
        
        # Margem baixa
        self.add_rule(AlertRule(
            name="margin_low",
            alert_type=AlertType.MARGIN_LOW,
            priority=AlertPriority.HIGH,
            condition=lambda ctx: 0 < ctx.get('margin_level', 100) < 150,
            message_template="⚠️ Nível de margem baixo: {value:.0f}%",
            cooldown_minutes=10,
        ))
        
        # Daily loss limit
        self.add_rule(AlertRule(
            name="daily_loss_limit",
            alert_type=AlertType.DAILY_LOSS_LIMIT,
            priority=AlertPriority.CRITICAL,
            condition=lambda ctx: ctx.get('daily_pnl', 0) <= -ctx.get('daily_loss_limit', -500),
            message_template="🛑 Limite de perda diária atingido: ${value:.2f}",
            cooldown_minutes=60,
        ))
        
        # Daily target hit
        self.add_rule(AlertRule(
            name="daily_target",
            alert_type=AlertType.DAILY_TARGET_HIT,
            priority=AlertPriority.LOW,
            condition=lambda ctx: ctx.get('daily_pnl', 0) >= ctx.get('daily_target', 1000),
            message_template="🎯 Meta diária atingida: ${value:.2f}",
            cooldown_minutes=60,
        ))
    
    # ==================== REGRAS ====================
    
    def add_rule(self, rule: AlertRule):
        """Adiciona uma regra de alerta."""
        self._rules[rule.name] = rule
        self.logger.debug(f"Regra '{rule.name}' adicionada")
    
    def remove_rule(self, name: str):
        """Remove uma regra."""
        if name in self._rules:
            del self._rules[name]
    
    def enable_rule(self, name: str, enabled: bool = True):
        """Habilita/desabilita uma regra."""
        if name in self._rules:
            self._rules[name].enabled = enabled
    
    def get_rules(self) -> Dict[str, AlertRule]:
        """Retorna todas as regras."""
        return self._rules
    
    # ==================== AVALIAÇÃO ====================
    
    def evaluate(self, context: Dict[str, Any]) -> List[Alert]:
        """
        Avalia todas as regras contra o contexto.
        
        Args:
            context: Dict com métricas atuais
            
        Returns:
            Lista de alertas gerados
        """
        new_alerts = []
        
        for rule in self._rules.values():
            if not rule.can_trigger():
                continue
            
            try:
                if rule.condition(context):
                    alert = self._create_alert(rule, context)
                    new_alerts.append(alert)
                    
                    # Atualizar último disparo
                    rule.last_triggered = datetime.now()
                    
                    self.logger.info(f"Alerta gerado: {alert.title}")
            
            except Exception as e:
                self.logger.error(f"Erro avaliando regra '{rule.name}': {e}")
        
        # Adicionar aos ativos e notificar
        for alert in new_alerts:
            self._active_alerts.append(alert)
            self._alert_history.append(alert)
            self._notify(alert)
        
        return new_alerts
    
    def _create_alert(self, rule: AlertRule, context: Dict[str, Any]) -> Alert:
        """Cria um alerta a partir de uma regra."""
        # Extrair valores relevantes
        value = 0
        threshold = 0
        
        if rule.alert_type == AlertType.DRAWDOWN:
            value = context.get('drawdown', 0)
            threshold = 10 if 'warning' in rule.name else 15
        elif rule.alert_type in [AlertType.WIN_STREAK, AlertType.LOSE_STREAK]:
            value = context.get('win_streak' if 'win' in rule.name else 'lose_streak', 0)
        elif rule.alert_type == AlertType.CPU_HIGH:
            value = context.get('cpu_percent', 0)
            threshold = 90
        elif rule.alert_type == AlertType.MEMORY_HIGH:
            value = context.get('memory_percent', 0)
            threshold = 85
        elif rule.alert_type == AlertType.MARGIN_LOW:
            value = context.get('margin_level', 0)
            threshold = 150
        elif rule.alert_type in [AlertType.DAILY_LOSS_LIMIT, AlertType.DAILY_TARGET_HIT]:
            value = context.get('daily_pnl', 0)
        
        # Formatar mensagem
        message = rule.message_template.format(
            value=value,
            threshold=threshold,
            **context
        )
        
        return Alert(
            type=rule.alert_type,
            priority=rule.priority,
            title=f"[{rule.priority.name}] {rule.alert_type.value}",
            message=message,
            source=context.get('source', 'system'),
            symbol=context.get('symbol', ''),
            value=value,
            threshold=threshold,
        )
    
    # ==================== ALERTAS MANUAIS ====================
    
    def trigger_alert(
        self,
        alert_type: AlertType,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        **kwargs
    ) -> Alert:
        """
        Dispara um alerta manualmente.
        
        Args:
            alert_type: Tipo do alerta
            message: Mensagem
            priority: Prioridade
            **kwargs: Metadados adicionais
            
        Returns:
            Alerta criado
        """
        alert = Alert(
            type=alert_type,
            priority=priority,
            title=f"[{priority.name}] {alert_type.value}",
            message=message,
            source=kwargs.get('source', 'manual'),
            symbol=kwargs.get('symbol', ''),
            value=kwargs.get('value', 0),
        )
        
        self._active_alerts.append(alert)
        self._alert_history.append(alert)
        self._notify(alert)
        
        self.logger.info(f"Alerta manual: {message}")
        
        return alert
    
    def trigger_custom(
        self,
        title: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM
    ) -> Alert:
        """Dispara um alerta customizado."""
        return self.trigger_alert(
            AlertType.CUSTOM,
            message,
            priority,
            source='custom'
        )
    
    # ==================== GERENCIAMENTO ====================
    
    def acknowledge(self, alert_index: int) -> bool:
        """Marca um alerta como reconhecido."""
        if 0 <= alert_index < len(self._active_alerts):
            self._active_alerts[alert_index].acknowledged = True
            return True
        return False
    
    def resolve(self, alert_index: int) -> bool:
        """Resolve um alerta."""
        if 0 <= alert_index < len(self._active_alerts):
            alert = self._active_alerts[alert_index]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            return True
        return False
    
    def resolve_by_type(self, alert_type: AlertType):
        """Resolve todos os alertas de um tipo."""
        for alert in self._active_alerts:
            if alert.type == alert_type:
                alert.resolved = True
                alert.resolved_at = datetime.now()
    
    def clear_resolved(self):
        """Remove alertas resolvidos da lista ativa."""
        self._active_alerts = [a for a in self._active_alerts if not a.resolved]
    
    def clear_old(self, hours: int = 24):
        """Remove alertas antigos."""
        cutoff = datetime.now() - timedelta(hours=hours)
        self._active_alerts = [
            a for a in self._active_alerts 
            if a.timestamp > cutoff
        ]
    
    # ==================== CONSULTA ====================
    
    def get_active_alerts(
        self,
        priority: AlertPriority = None,
        alert_type: AlertType = None
    ) -> List[Alert]:
        """
        Retorna alertas ativos.
        
        Args:
            priority: Filtrar por prioridade
            alert_type: Filtrar por tipo
        """
        alerts = self._active_alerts
        
        if priority:
            alerts = [a for a in alerts if a.priority == priority]
        
        if alert_type:
            alerts = [a for a in alerts if a.type == alert_type]
        
        return sorted(alerts, key=lambda a: (a.priority.value, a.timestamp), reverse=True)
    
    def get_critical_alerts(self) -> List[Alert]:
        """Retorna alertas críticos não reconhecidos."""
        return [
            a for a in self._active_alerts 
            if a.priority == AlertPriority.CRITICAL and not a.acknowledged
        ]
    
    def get_history(self, limit: int = 100) -> List[Alert]:
        """Retorna histórico de alertas."""
        return list(self._alert_history)[-limit:]
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo dos alertas."""
        return {
            'total_active': len(self._active_alerts),
            'critical': len([a for a in self._active_alerts if a.priority == AlertPriority.CRITICAL]),
            'high': len([a for a in self._active_alerts if a.priority == AlertPriority.HIGH]),
            'medium': len([a for a in self._active_alerts if a.priority == AlertPriority.MEDIUM]),
            'low': len([a for a in self._active_alerts if a.priority == AlertPriority.LOW]),
            'unacknowledged': len([a for a in self._active_alerts if not a.acknowledged]),
            'history_count': len(self._alert_history),
        }
    
    def has_critical(self) -> bool:
        """Verifica se há alertas críticos."""
        return any(a.priority == AlertPriority.CRITICAL for a in self._active_alerts if not a.resolved)
    
    # ==================== NOTIFICAÇÕES ====================
    
    def add_notification_channel(
        self,
        name: str,
        callback: Callable[[Alert], None]
    ):
        """
        Adiciona canal de notificação.
        
        Args:
            name: Nome do canal (telegram, email, etc)
            callback: Função chamada para cada alerta
        """
        self._notification_callbacks[name] = callback
        self.logger.info(f"Canal de notificação '{name}' adicionado")
    
    def remove_notification_channel(self, name: str):
        """Remove canal de notificação."""
        if name in self._notification_callbacks:
            del self._notification_callbacks[name]
    
    def _notify(self, alert: Alert):
        """Envia notificações para todos os canais."""
        for channel_name, callback in self._notification_callbacks.items():
            try:
                callback(alert)
                alert.notification_channels.append(channel_name)
                alert.notified = True
            except Exception as e:
                self.logger.error(f"Erro notificando canal '{channel_name}': {e}")
    
    # ==================== FORMATAÇÃO ====================
    
    def format_alert_text(self, alert: Alert) -> str:
        """Formata alerta para texto."""
        priority_emoji = {
            AlertPriority.LOW: "ℹ️",
            AlertPriority.MEDIUM: "⚠️",
            AlertPriority.HIGH: "🔶",
            AlertPriority.CRITICAL: "🚨",
        }
        
        return (
            f"{priority_emoji.get(alert.priority, '•')} "
            f"[{alert.priority.name}] {alert.message}\n"
            f"   Hora: {alert.timestamp.strftime('%H:%M:%S')}"
        )
    
    def format_alerts_summary(self) -> str:
        """Formata resumo de alertas."""
        summary = self.get_summary()
        active = self.get_active_alerts()
        
        lines = [
            "📢 ALERTAS ATIVOS",
            "=" * 40,
            f"Total: {summary['total_active']}",
            f"  🚨 Crítico: {summary['critical']}",
            f"  🔶 Alto: {summary['high']}",
            f"  ⚠️ Médio: {summary['medium']}",
            f"  ℹ️ Baixo: {summary['low']}",
            "",
        ]
        
        if active:
            lines.append("Últimos alertas:")
            for alert in active[:5]:
                lines.append(self.format_alert_text(alert))
        else:
            lines.append("✅ Nenhum alerta ativo")
        
        return "\n".join(lines)
