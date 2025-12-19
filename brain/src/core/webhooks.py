"""
VIRTUS - Sistema de Webhooks
============================

Sistema de webhooks para notificar sistemas externos sobre eventos.
"""

import asyncio
import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import aiohttp

from .logger import get_logger
from .circuit_breaker import get_circuit_breaker

logger = get_logger("webhooks")


class WebhookEvent(Enum):
    """Tipos de eventos que podem disparar webhooks."""
    # Trading
    TRADE_OPENED = "trade.opened"
    TRADE_CLOSED = "trade.closed"
    TRADE_MODIFIED = "trade.modified"
    
    # Sinais
    SIGNAL_GENERATED = "signal.generated"
    SIGNAL_EXPIRED = "signal.expired"
    
    # Alertas
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"
    
    # Sistema
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
    SYSTEM_ERROR = "system.error"
    
    # Bot
    BOT_STARTED = "bot.started"
    BOT_STOPPED = "bot.stopped"
    BOT_ERROR = "bot.error"
    
    # Account
    ACCOUNT_UPDATE = "account.update"
    MARGIN_WARNING = "margin.warning"
    
    # Custom
    CUSTOM = "custom"


@dataclass
class WebhookConfig:
    """Configuração de um webhook."""
    id: str
    name: str
    url: str
    events: List[WebhookEvent]
    secret: Optional[str] = None  # Para assinatura HMAC
    enabled: bool = True
    timeout: float = 10.0
    max_retries: int = 3
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class WebhookDelivery:
    """Registro de entrega de webhook."""
    webhook_id: str
    event: str
    payload: Dict
    timestamp: datetime
    status: str  # pending, delivered, failed
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    attempts: int = 0
    error: Optional[str] = None


class WebhookManager:
    """
    Gerenciador de webhooks.
    
    Features:
    - Registro de múltiplos webhooks
    - Filtragem por tipo de evento
    - Assinatura HMAC para segurança
    - Retry com backoff
    - Circuit breaker por webhook
    - Histórico de entregas
    
    Uso:
        manager = WebhookManager()
        
        # Registrar webhook
        manager.register(WebhookConfig(
            id="tradingview",
            name="TradingView",
            url="https://webhook.site/...",
            events=[WebhookEvent.TRADE_OPENED, WebhookEvent.TRADE_CLOSED],
            secret="my-secret-key"
        ))
        
        # Disparar evento
        await manager.dispatch(
            WebhookEvent.TRADE_OPENED,
            {"symbol": "XAUUSD", "type": "BUY", "price": 2050.50}
        )
    """
    
    def __init__(self):
        self._webhooks: Dict[str, WebhookConfig] = {}
        self._deliveries: List[WebhookDelivery] = []
        self._max_deliveries = 1000
        self._listeners: Dict[WebhookEvent, List[Callable]] = {}
    
    def register(self, config: WebhookConfig):
        """Registra um novo webhook."""
        self._webhooks[config.id] = config
        logger.info(f"Webhook registrado: {config.name} ({config.id})")
    
    def unregister(self, webhook_id: str) -> bool:
        """Remove um webhook."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            logger.info(f"Webhook removido: {webhook_id}")
            return True
        return False
    
    def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Obtém configuração de um webhook."""
        return self._webhooks.get(webhook_id)
    
    def list_webhooks(self) -> List[WebhookConfig]:
        """Lista todos os webhooks."""
        return list(self._webhooks.values())
    
    def add_listener(self, event: WebhookEvent, callback: Callable):
        """Adiciona listener local para um evento."""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    async def dispatch(
        self,
        event: WebhookEvent,
        data: Dict[str, Any],
        webhook_ids: Optional[List[str]] = None
    ):
        """
        Dispara evento para webhooks registrados.
        
        Args:
            event: Tipo do evento
            data: Dados do evento
            webhook_ids: IDs específicos (se None, dispara para todos)
        """
        payload = {
            "event": event.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Chama listeners locais
        if event in self._listeners:
            for callback in self._listeners[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(payload)
                    else:
                        callback(payload)
                except Exception as e:
                    logger.error(f"Erro no listener {callback.__name__}: {e}")
        
        # Envia para webhooks remotos
        tasks = []
        for webhook_id, config in self._webhooks.items():
            # Filtro por IDs específicos
            if webhook_ids and webhook_id not in webhook_ids:
                continue
            
            # Filtro por eventos
            if event not in config.events and WebhookEvent.CUSTOM not in config.events:
                continue
            
            if not config.enabled:
                continue
            
            tasks.append(self._send_webhook(config, payload))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_webhook(
        self,
        config: WebhookConfig,
        payload: Dict
    ):
        """Envia requisição para um webhook."""
        delivery = WebhookDelivery(
            webhook_id=config.id,
            event=payload["event"],
            payload=payload,
            timestamp=datetime.utcnow(),
            status="pending"
        )
        
        # Circuit breaker por webhook
        cb = get_circuit_breaker(f"webhook_{config.id}")
        
        if not cb.can_execute():
            delivery.status = "failed"
            delivery.error = "Circuit breaker open"
            self._record_delivery(delivery)
            return
        
        headers = {
            "Content-Type": "application/json",
            **config.headers
        }
        
        # Assinatura HMAC
        if config.secret:
            payload_str = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                config.secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        
        # Timestamp para verificação
        headers["X-Webhook-Timestamp"] = str(int(time.time()))
        
        for attempt in range(config.max_retries):
            delivery.attempts = attempt + 1
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        config.url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=config.timeout)
                    ) as response:
                        delivery.response_code = response.status
                        delivery.response_body = await response.text()
                        
                        if response.status < 300:
                            delivery.status = "delivered"
                            cb.record_success()
                            logger.debug(
                                f"Webhook {config.id} entregue: "
                                f"{payload['event']} -> {response.status}"
                            )
                            break
                        else:
                            delivery.error = f"HTTP {response.status}"
                            cb.record_failure()
                            
            except asyncio.TimeoutError:
                delivery.error = "Timeout"
                cb.record_failure()
            except Exception as e:
                delivery.error = str(e)
                cb.record_failure()
            
            # Backoff exponencial
            if attempt < config.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        if delivery.status != "delivered":
            delivery.status = "failed"
            logger.warning(
                f"Webhook {config.id} falhou após {delivery.attempts} tentativas: "
                f"{delivery.error}"
            )
        
        self._record_delivery(delivery)
    
    def _record_delivery(self, delivery: WebhookDelivery):
        """Registra entrega no histórico."""
        self._deliveries.append(delivery)
        
        # Limita tamanho do histórico
        if len(self._deliveries) > self._max_deliveries:
            self._deliveries = self._deliveries[-self._max_deliveries:]
    
    def get_deliveries(
        self,
        webhook_id: Optional[str] = None,
        limit: int = 50
    ) -> List[WebhookDelivery]:
        """Retorna histórico de entregas."""
        deliveries = self._deliveries
        
        if webhook_id:
            deliveries = [d for d in deliveries if d.webhook_id == webhook_id]
        
        return deliveries[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de webhooks."""
        total = len(self._deliveries)
        delivered = sum(1 for d in self._deliveries if d.status == "delivered")
        failed = sum(1 for d in self._deliveries if d.status == "failed")
        
        return {
            "webhooks_registered": len(self._webhooks),
            "total_deliveries": total,
            "delivered": delivered,
            "failed": failed,
            "success_rate": f"{(delivered / total * 100):.1f}%" if total > 0 else "N/A",
            "by_webhook": {
                webhook_id: {
                    "enabled": config.enabled,
                    "events": [e.value for e in config.events],
                    "deliveries": sum(
                        1 for d in self._deliveries 
                        if d.webhook_id == webhook_id
                    )
                }
                for webhook_id, config in self._webhooks.items()
            }
        }


# ==================== INSTÂNCIA GLOBAL ====================

_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Retorna gerenciador de webhooks global."""
    global _manager
    if _manager is None:
        _manager = WebhookManager()
    return _manager


# Alias conveniente
async def dispatch_webhook(event: WebhookEvent, data: Dict):
    """Dispara webhook de forma conveniente."""
    manager = get_webhook_manager()
    await manager.dispatch(event, data)
