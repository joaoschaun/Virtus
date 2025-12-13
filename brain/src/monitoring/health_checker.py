"""
BRAIN - Monitoring Module
Monitoramento de saúde do sistema
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.logger import get_logger

logger = get_logger("monitoring")


class HealthStatus(Enum):
    """Status de saúde"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Saúde de um componente"""
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: datetime = field(default_factory=datetime.now)
    message: str = ""
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """Métricas do sistema"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    disk_percent: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    process_memory_mb: float = 0.0
    active_threads: int = 0


class HealthChecker:
    """
    Verificador de Saúde
    
    Responsabilidades:
    - Monitorar componentes
    - Coletar métricas do sistema
    - Alertar sobre problemas
    """
    
    def __init__(self, check_interval: float = 30.0):
        self._interval = check_interval
        self._components: Dict[str, ComponentHealth] = {}
        self._health_checks: Dict[str, Callable] = {}
        self._metrics_history: List[SystemMetrics] = []
        self._max_history = 1000
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_status_change: Optional[Callable] = None
        self._on_critical: Optional[Callable] = None
    
    def register_component(
        self,
        name: str,
        health_check: Callable[[], bool] = None
    ):
        """
        Registra componente para monitoramento
        
        Args:
            name: Nome do componente
            health_check: Função que retorna True se saudável
        """
        self._components[name] = ComponentHealth(name=name)
        
        if health_check:
            self._health_checks[name] = health_check
        
        logger.debug(f"Componente registrado: {name}")
    
    async def start(self):
        """Inicia monitoramento"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("HealthChecker iniciado")
    
    async def stop(self):
        """Para monitoramento"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HealthChecker parado")
    
    async def _monitoring_loop(self):
        """Loop principal de monitoramento"""
        while self._running:
            try:
                # Verificar componentes
                await self._check_all_components()
                
                # Coletar métricas
                metrics = self._collect_system_metrics()
                self._metrics_history.append(metrics)
                
                # Limitar histórico
                if len(self._metrics_history) > self._max_history:
                    self._metrics_history = self._metrics_history[-self._max_history:]
                
            except Exception as e:
                logger.error(f"Erro no monitoramento: {e}")
            
            await asyncio.sleep(self._interval)
    
    async def _check_all_components(self):
        """Verifica todos os componentes"""
        for name, component in self._components.items():
            old_status = component.status
            
            try:
                if name in self._health_checks:
                    start = time.time()
                    
                    check_func = self._health_checks[name]
                    if asyncio.iscoroutinefunction(check_func):
                        is_healthy = await check_func()
                    else:
                        is_healthy = check_func()
                    
                    latency = (time.time() - start) * 1000
                    
                    component.latency_ms = latency
                    component.status = HealthStatus.HEALTHY if is_healthy else HealthStatus.CRITICAL
                    component.message = "OK" if is_healthy else "Check failed"
                else:
                    component.status = HealthStatus.UNKNOWN
                    component.message = "No health check defined"
                
            except Exception as e:
                component.status = HealthStatus.CRITICAL
                component.message = str(e)
            
            component.last_check = datetime.now()
            
            # Notificar mudança de status
            if component.status != old_status:
                await self._handle_status_change(component, old_status)
    
    async def _handle_status_change(
        self,
        component: ComponentHealth,
        old_status: HealthStatus
    ):
        """Trata mudança de status"""
        logger.warning(
            f"Mudança de status: {component.name} "
            f"{old_status.value} -> {component.status.value}"
        )
        
        if self._on_status_change:
            if asyncio.iscoroutinefunction(self._on_status_change):
                await self._on_status_change(component, old_status)
            else:
                self._on_status_change(component, old_status)
        
        if component.status == HealthStatus.CRITICAL and self._on_critical:
            if asyncio.iscoroutinefunction(self._on_critical):
                await self._on_critical(component)
            else:
                self._on_critical(component)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Coleta métricas do sistema"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            process = psutil.Process()
            
            return SystemMetrics(
                cpu_percent=cpu,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                disk_percent=disk.percent,
                network_sent_mb=net.bytes_sent / (1024 * 1024),
                network_recv_mb=net.bytes_recv / (1024 * 1024),
                process_memory_mb=process.memory_info().rss / (1024 * 1024),
                active_threads=process.num_threads()
            )
        except Exception as e:
            logger.error(f"Erro ao coletar métricas: {e}")
            return SystemMetrics()
    
    # ==========================================================================
    # REPORTS
    # ==========================================================================
    
    def get_overall_status(self) -> HealthStatus:
        """Retorna status geral do sistema"""
        if not self._components:
            return HealthStatus.UNKNOWN
        
        statuses = [c.status for c in self._components.values()]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        if HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        if HealthStatus.UNKNOWN in statuses:
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    def get_health_report(self) -> Dict[str, Any]:
        """Retorna relatório de saúde"""
        components = []
        
        for comp in self._components.values():
            components.append({
                "name": comp.name,
                "status": comp.status.value,
                "message": comp.message,
                "latency_ms": round(comp.latency_ms, 2),
                "last_check": comp.last_check.isoformat()
            })
        
        # Métricas recentes
        latest_metrics = self._metrics_history[-1] if self._metrics_history else None
        
        return {
            "overall_status": self.get_overall_status().value,
            "checked_at": datetime.now().isoformat(),
            "components": components,
            "system_metrics": {
                "cpu_percent": latest_metrics.cpu_percent if latest_metrics else 0,
                "memory_percent": latest_metrics.memory_percent if latest_metrics else 0,
                "process_memory_mb": round(latest_metrics.process_memory_mb, 2) if latest_metrics else 0,
                "active_threads": latest_metrics.active_threads if latest_metrics else 0
            } if latest_metrics else None
        }
    
    def get_metrics_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Retorna resumo de métricas do período"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent = [m for m in self._metrics_history if m.timestamp >= cutoff]
        
        if not recent:
            return {}
        
        return {
            "period_minutes": minutes,
            "samples": len(recent),
            "cpu": {
                "avg": round(sum(m.cpu_percent for m in recent) / len(recent), 2),
                "max": round(max(m.cpu_percent for m in recent), 2),
                "min": round(min(m.cpu_percent for m in recent), 2)
            },
            "memory": {
                "avg_percent": round(sum(m.memory_percent for m in recent) / len(recent), 2),
                "max_percent": round(max(m.memory_percent for m in recent), 2)
            },
            "process": {
                "avg_memory_mb": round(sum(m.process_memory_mb for m in recent) / len(recent), 2),
                "max_memory_mb": round(max(m.process_memory_mb for m in recent), 2)
            }
        }
    
    def set_callbacks(
        self,
        on_status_change: Callable = None,
        on_critical: Callable = None
    ):
        """Define callbacks para eventos"""
        self._on_status_change = on_status_change
        self._on_critical = on_critical


class AlertManager:
    """
    Gerenciador de Alertas
    
    Envia alertas baseados em condições
    """
    
    def __init__(self):
        self._rules: List[Dict] = []
        self._alert_history: List[Dict] = []
        self._cooldowns: Dict[str, datetime] = {}
        self._handlers: List[Callable] = []
    
    def add_rule(
        self,
        name: str,
        condition: Callable[[], bool],
        message: str,
        severity: str = "warning",
        cooldown_minutes: int = 15
    ):
        """
        Adiciona regra de alerta
        
        Args:
            name: Nome da regra
            condition: Função que retorna True para disparar
            message: Mensagem do alerta
            severity: Severidade (info, warning, critical)
            cooldown_minutes: Tempo mínimo entre alertas
        """
        self._rules.append({
            "name": name,
            "condition": condition,
            "message": message,
            "severity": severity,
            "cooldown": cooldown_minutes
        })
    
    def add_handler(self, handler: Callable):
        """Adiciona handler para alertas"""
        self._handlers.append(handler)
    
    async def check_rules(self):
        """Verifica todas as regras"""
        now = datetime.now()
        
        for rule in self._rules:
            name = rule["name"]
            
            # Verificar cooldown
            if name in self._cooldowns:
                if now < self._cooldowns[name]:
                    continue
            
            try:
                condition = rule["condition"]
                if asyncio.iscoroutinefunction(condition):
                    should_alert = await condition()
                else:
                    should_alert = condition()
                
                if should_alert:
                    await self._trigger_alert(rule)
                    
                    # Definir cooldown
                    self._cooldowns[name] = now + timedelta(minutes=rule["cooldown"])
                    
            except Exception as e:
                logger.error(f"Erro ao verificar regra {name}: {e}")
    
    async def _trigger_alert(self, rule: Dict):
        """Dispara alerta"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "name": rule["name"],
            "message": rule["message"],
            "severity": rule["severity"]
        }
        
        self._alert_history.append(alert)
        logger.warning(f"ALERTA [{rule['severity']}]: {rule['message']}")
        
        # Chamar handlers
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Erro no handler de alerta: {e}")
    
    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """Retorna alertas recentes"""
        return self._alert_history[-limit:]
