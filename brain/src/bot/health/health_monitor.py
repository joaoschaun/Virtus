"""
VIRTUS Bot Health Monitor
==========================

Monitoramento de saúde do bot.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum, auto


class HealthStatus(Enum):
    """Status de saúde."""
    HEALTHY = auto()
    WARNING = auto()
    CRITICAL = auto()
    UNKNOWN = auto()


@dataclass
class HealthCheck:
    """Resultado de verificação de saúde."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BotHealth:
    """Saúde geral do bot."""
    bot_id: str
    overall_status: HealthStatus
    checks: List[HealthCheck]
    last_check: datetime
    uptime_seconds: float
    error_rate: float
    response_time_ms: float


class BotHealthMonitor:
    """
    Monitor de saúde do bot.
    
    Verifica:
    - Conexão MT5
    - Comunicação com Brain
    - Performance
    - Taxas de erro
    """
    
    def __init__(self, bot_id: str):
        self.bot_id = bot_id
        self._start_time = datetime.now()
        self._checks: List[HealthCheck] = []
        self._error_count = 0
        self._request_count = 0
        self._response_times: List[float] = []
        self._max_response_times = 100
        
        # Thresholds
        self._error_rate_warning = 0.05  # 5%
        self._error_rate_critical = 0.15  # 15%
        self._response_time_warning = 500  # ms
        self._response_time_critical = 2000  # ms
    
    async def check_health(
        self,
        mt5_connected: bool = True,
        brain_available: bool = True,
        has_recent_data: bool = True,
    ) -> BotHealth:
        """Executa verificação completa de saúde."""
        checks = []
        
        # Check MT5
        checks.append(HealthCheck(
            name="mt5_connection",
            status=HealthStatus.HEALTHY if mt5_connected else HealthStatus.CRITICAL,
            message="MT5 conectado" if mt5_connected else "MT5 desconectado",
        ))
        
        # Check Brain
        checks.append(HealthCheck(
            name="brain_service",
            status=HealthStatus.HEALTHY if brain_available else HealthStatus.WARNING,
            message="Brain disponível" if brain_available else "Brain indisponível",
        ))
        
        # Check dados recentes
        checks.append(HealthCheck(
            name="data_freshness",
            status=HealthStatus.HEALTHY if has_recent_data else HealthStatus.WARNING,
            message="Dados atualizados" if has_recent_data else "Dados desatualizados",
        ))
        
        # Check taxa de erros
        error_rate = self._calculate_error_rate()
        if error_rate >= self._error_rate_critical:
            error_status = HealthStatus.CRITICAL
        elif error_rate >= self._error_rate_warning:
            error_status = HealthStatus.WARNING
        else:
            error_status = HealthStatus.HEALTHY
        
        checks.append(HealthCheck(
            name="error_rate",
            status=error_status,
            message=f"Taxa de erros: {error_rate:.1%}",
            details={'error_rate': error_rate},
        ))
        
        # Check tempo de resposta
        avg_response = self._calculate_avg_response_time()
        if avg_response >= self._response_time_critical:
            response_status = HealthStatus.CRITICAL
        elif avg_response >= self._response_time_warning:
            response_status = HealthStatus.WARNING
        else:
            response_status = HealthStatus.HEALTHY
        
        checks.append(HealthCheck(
            name="response_time",
            status=response_status,
            message=f"Tempo médio: {avg_response:.0f}ms",
            details={'avg_response_ms': avg_response},
        ))
        
        # Determina status geral
        overall = self._determine_overall_status(checks)
        
        self._checks = checks
        
        return BotHealth(
            bot_id=self.bot_id,
            overall_status=overall,
            checks=checks,
            last_check=datetime.now(),
            uptime_seconds=(datetime.now() - self._start_time).total_seconds(),
            error_rate=error_rate,
            response_time_ms=avg_response,
        )
    
    def record_request(self, response_time_ms: float, success: bool = True) -> None:
        """Registra uma requisição."""
        self._request_count += 1
        
        if not success:
            self._error_count += 1
        
        self._response_times.append(response_time_ms)
        if len(self._response_times) > self._max_response_times:
            self._response_times = self._response_times[-self._max_response_times:]
    
    def record_error(self) -> None:
        """Registra um erro."""
        self._error_count += 1
        self._request_count += 1
    
    def _calculate_error_rate(self) -> float:
        """Calcula taxa de erros."""
        if self._request_count == 0:
            return 0.0
        return self._error_count / self._request_count
    
    def _calculate_avg_response_time(self) -> float:
        """Calcula tempo médio de resposta."""
        if not self._response_times:
            return 0.0
        return sum(self._response_times) / len(self._response_times)
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Determina status geral baseado nas verificações."""
        statuses = [c.status for c in checks]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo de saúde."""
        return {
            'bot_id': self.bot_id,
            'uptime_hours': (datetime.now() - self._start_time).total_seconds() / 3600,
            'total_requests': self._request_count,
            'total_errors': self._error_count,
            'error_rate': self._calculate_error_rate(),
            'avg_response_ms': self._calculate_avg_response_time(),
            'checks': [
                {
                    'name': c.name,
                    'status': c.status.name,
                    'message': c.message,
                }
                for c in self._checks
            ],
        }
    
    def reset_stats(self) -> None:
        """Reseta estatísticas."""
        self._error_count = 0
        self._request_count = 0
        self._response_times = []
