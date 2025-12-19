"""
VIRTUS - MT5 Auto-Recovery System
==================================

Sistema de reconexão automática para MetaTrader 5.
Monitora a conexão e reconecta automaticamente quando detecta falhas.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("virtus.mt5_recovery")


class ConnectionState(str, Enum):
    """Estados da conexão MT5."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    INITIALIZING = "initializing"


@dataclass
class RecoveryConfig:
    """Configuração do sistema de recovery."""
    # Tentativas de reconexão
    max_retries: int = 10
    base_delay: float = 1.0  # segundos
    max_delay: float = 60.0  # segundos
    exponential_base: float = 2.0
    
    # Health check
    health_check_interval: float = 5.0  # segundos
    health_check_timeout: float = 3.0  # segundos
    
    # Alertas
    alert_on_disconnect: bool = True
    alert_on_reconnect: bool = True
    alert_after_failures: int = 3
    
    # Ações automáticas
    auto_reconnect: bool = True
    close_positions_on_disconnect: bool = False  # Perigoso, use com cuidado
    pause_trading_on_disconnect: bool = True


@dataclass
class ConnectionStats:
    """Estatísticas de conexão."""
    total_disconnects: int = 0
    total_reconnects: int = 0
    last_disconnect: Optional[datetime] = None
    last_reconnect: Optional[datetime] = None
    current_session_start: Optional[datetime] = None
    total_downtime_seconds: float = 0.0
    consecutive_failures: int = 0
    uptime_percent: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_disconnects": self.total_disconnects,
            "total_reconnects": self.total_reconnects,
            "last_disconnect": self.last_disconnect.isoformat() if self.last_disconnect else None,
            "last_reconnect": self.last_reconnect.isoformat() if self.last_reconnect else None,
            "current_session_start": self.current_session_start.isoformat() if self.current_session_start else None,
            "total_downtime_seconds": round(self.total_downtime_seconds, 2),
            "consecutive_failures": self.consecutive_failures,
            "uptime_percent": round(self.uptime_percent, 2)
        }


class MT5Recovery:
    """
    Sistema de auto-recovery para conexão MT5.
    
    Uso:
        recovery = MT5Recovery(config)
        recovery.on_disconnect(callback)
        recovery.on_reconnect(callback)
        await recovery.start()
    """
    
    def __init__(self, config: Optional[RecoveryConfig] = None):
        self.config = config or RecoveryConfig()
        self.state = ConnectionState.DISCONNECTED
        self.stats = ConnectionStats()
        
        # Callbacks
        self._on_disconnect_callbacks: List[Callable] = []
        self._on_reconnect_callbacks: List[Callable] = []
        self._on_state_change_callbacks: List[Callable] = []
        
        # Control
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._disconnect_time: Optional[datetime] = None
        
        # MT5 credentials (set via configure)
        self._mt5_login: Optional[int] = None
        self._mt5_password: Optional[str] = None
        self._mt5_server: Optional[str] = None
        self._mt5_path: Optional[str] = None
    
    def configure(
        self,
        login: int,
        password: str,
        server: str,
        path: Optional[str] = None
    ):
        """Configura credenciais MT5."""
        self._mt5_login = login
        self._mt5_password = password
        self._mt5_server = server
        self._mt5_path = path
    
    def on_disconnect(self, callback: Callable):
        """Registra callback para desconexão."""
        self._on_disconnect_callbacks.append(callback)
    
    def on_reconnect(self, callback: Callable):
        """Registra callback para reconexão."""
        self._on_reconnect_callbacks.append(callback)
    
    def on_state_change(self, callback: Callable):
        """Registra callback para mudança de estado."""
        self._on_state_change_callbacks.append(callback)
    
    async def start(self):
        """Inicia o sistema de recovery."""
        if self._running:
            logger.warning("MT5 Recovery já está rodando")
            return
        
        self._running = True
        self.stats.current_session_start = datetime.now()
        
        logger.info("🔄 MT5 Recovery iniciado")
        
        # Tenta conexão inicial
        if await self._connect():
            self._set_state(ConnectionState.CONNECTED)
        else:
            self._set_state(ConnectionState.DISCONNECTED)
            if self.config.auto_reconnect:
                asyncio.create_task(self._reconnect_loop())
        
        # Inicia health check
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def stop(self):
        """Para o sistema de recovery."""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 MT5 Recovery parado")
    
    def _set_state(self, new_state: ConnectionState):
        """Atualiza estado e notifica callbacks."""
        old_state = self.state
        self.state = new_state
        
        if old_state != new_state:
            logger.info(f"MT5 Estado: {old_state} -> {new_state}")
            
            for callback in self._on_state_change_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(old_state, new_state))
                    else:
                        callback(old_state, new_state)
                except Exception as e:
                    logger.error(f"Erro em callback de estado: {e}")
    
    async def _connect(self) -> bool:
        """Tenta conectar ao MT5."""
        try:
            import MetaTrader5 as mt5
            
            # Shutdown se já inicializado
            mt5.shutdown()
            
            # Initialize
            init_kwargs = {}
            if self._mt5_path:
                init_kwargs["path"] = self._mt5_path
            if self._mt5_login:
                init_kwargs["login"] = self._mt5_login
            if self._mt5_password:
                init_kwargs["password"] = self._mt5_password
            if self._mt5_server:
                init_kwargs["server"] = self._mt5_server
            
            if not mt5.initialize(**init_kwargs):
                error = mt5.last_error()
                logger.error(f"MT5 initialize falhou: {error}")
                return False
            
            # Login se necessário
            if self._mt5_login and self._mt5_password:
                if not mt5.login(self._mt5_login, self._mt5_password, self._mt5_server):
                    error = mt5.last_error()
                    logger.error(f"MT5 login falhou: {error}")
                    return False
            
            # Verifica se está conectado
            account = mt5.account_info()
            if account is None:
                logger.error("MT5 account_info retornou None")
                return False
            
            logger.info(f"✅ MT5 conectado: {account.login} @ {account.server}")
            return True
            
        except ImportError:
            logger.error("Módulo MetaTrader5 não instalado")
            return False
        except Exception as e:
            logger.error(f"Erro ao conectar MT5: {e}")
            return False
    
    async def _check_connection(self) -> bool:
        """Verifica se a conexão MT5 está ativa."""
        try:
            import MetaTrader5 as mt5
            
            # Timeout para operação
            async def check():
                account = mt5.account_info()
                return account is not None
            
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(lambda: mt5.account_info() is not None),
                    timeout=self.config.health_check_timeout
                )
                return result
            except asyncio.TimeoutError:
                logger.warning("MT5 health check timeout")
                return False
                
        except Exception as e:
            logger.error(f"Erro no health check: {e}")
            return False
    
    async def _health_check_loop(self):
        """Loop de verificação de saúde da conexão."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if self.state == ConnectionState.RECONNECTING:
                    continue
                
                is_connected = await self._check_connection()
                
                if is_connected and self.state != ConnectionState.CONNECTED:
                    # Reconectou
                    self._handle_reconnection()
                    
                elif not is_connected and self.state == ConnectionState.CONNECTED:
                    # Desconectou
                    await self._handle_disconnection()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no health check loop: {e}")
    
    async def _handle_disconnection(self):
        """Processa desconexão."""
        self._disconnect_time = datetime.now()
        self.stats.total_disconnects += 1
        self.stats.last_disconnect = self._disconnect_time
        self.stats.consecutive_failures += 1
        
        self._set_state(ConnectionState.DISCONNECTED)
        
        logger.warning(f"⚠️ MT5 DESCONECTADO! Total: {self.stats.total_disconnects}")
        
        # Notifica callbacks
        for callback in self._on_disconnect_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.stats)
                else:
                    callback(self.stats)
            except Exception as e:
                logger.error(f"Erro em callback de desconexão: {e}")
        
        # Inicia reconexão automática
        if self.config.auto_reconnect:
            asyncio.create_task(self._reconnect_loop())
    
    def _handle_reconnection(self):
        """Processa reconexão bem-sucedida."""
        now = datetime.now()
        
        if self._disconnect_time:
            downtime = (now - self._disconnect_time).total_seconds()
            self.stats.total_downtime_seconds += downtime
            logger.info(f"Downtime: {downtime:.1f}s")
        
        self.stats.total_reconnects += 1
        self.stats.last_reconnect = now
        self.stats.consecutive_failures = 0
        
        # Calcula uptime
        if self.stats.current_session_start:
            total_time = (now - self.stats.current_session_start).total_seconds()
            if total_time > 0:
                uptime = total_time - self.stats.total_downtime_seconds
                self.stats.uptime_percent = (uptime / total_time) * 100
        
        self._set_state(ConnectionState.CONNECTED)
        self._disconnect_time = None
        
        logger.info(f"✅ MT5 RECONECTADO! Uptime: {self.stats.uptime_percent:.1f}%")
        
        # Notifica callbacks
        for callback in self._on_reconnect_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self.stats))
                else:
                    callback(self.stats)
            except Exception as e:
                logger.error(f"Erro em callback de reconexão: {e}")
    
    async def _reconnect_loop(self):
        """Loop de tentativas de reconexão."""
        if self.state == ConnectionState.RECONNECTING:
            return
        
        self._set_state(ConnectionState.RECONNECTING)
        
        retry_count = 0
        
        while self._running and retry_count < self.config.max_retries:
            retry_count += 1
            
            # Calcula delay com backoff exponencial
            delay = min(
                self.config.base_delay * (self.config.exponential_base ** (retry_count - 1)),
                self.config.max_delay
            )
            
            logger.info(f"🔄 Tentativa de reconexão {retry_count}/{self.config.max_retries} em {delay:.1f}s")
            
            await asyncio.sleep(delay)
            
            if await self._connect():
                self._handle_reconnection()
                return
            
            self.stats.consecutive_failures += 1
            
            # Alerta após X falhas consecutivas
            if self.stats.consecutive_failures >= self.config.alert_after_failures:
                logger.error(
                    f"🚨 {self.stats.consecutive_failures} falhas consecutivas de conexão MT5!"
                )
        
        # Esgotou tentativas
        self._set_state(ConnectionState.FAILED)
        logger.error(f"❌ MT5 Recovery falhou após {retry_count} tentativas")
    
    async def force_reconnect(self) -> bool:
        """Força uma reconexão imediata."""
        logger.info("🔄 Forçando reconexão MT5...")
        
        self._set_state(ConnectionState.RECONNECTING)
        
        if await self._connect():
            self._handle_reconnection()
            return True
        else:
            self._set_state(ConnectionState.DISCONNECTED)
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de conexão."""
        return {
            "state": self.state.value,
            "stats": self.stats.to_dict(),
            "config": {
                "auto_reconnect": self.config.auto_reconnect,
                "max_retries": self.config.max_retries,
                "health_check_interval": self.config.health_check_interval
            }
        }


# Instância global
mt5_recovery = MT5Recovery()


# ============================================================================
# DECORADOR PARA PROTEÇÃO DE OPERAÇÕES MT5
# ============================================================================

def with_mt5_recovery(func):
    """
    Decorador que garante conexão MT5 antes de executar.
    
    Uso:
        @with_mt5_recovery
        async def get_positions():
            ...
    """
    async def wrapper(*args, **kwargs):
        if mt5_recovery.state != ConnectionState.CONNECTED:
            logger.warning(f"MT5 não conectado (estado: {mt5_recovery.state})")
            
            # Tenta reconectar
            if mt5_recovery.config.auto_reconnect:
                success = await mt5_recovery.force_reconnect()
                if not success:
                    raise ConnectionError("MT5 não está conectado e reconexão falhou")
            else:
                raise ConnectionError("MT5 não está conectado")
        
        return await func(*args, **kwargs)
    
    return wrapper


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    async def on_disconnect(stats):
        print(f"🔴 Desconectado! Total: {stats.total_disconnects}")
    
    async def on_reconnect(stats):
        print(f"🟢 Reconectado! Uptime: {stats.uptime_percent:.1f}%")
    
    async def main():
        # Configura
        mt5_recovery.configure(
            login=61444598,
            password="sua_senha",
            server="Pepperstone-Demo"
        )
        
        # Registra callbacks
        mt5_recovery.on_disconnect(on_disconnect)
        mt5_recovery.on_reconnect(on_reconnect)
        
        # Inicia
        await mt5_recovery.start()
        
        # Mantém rodando
        try:
            while True:
                await asyncio.sleep(10)
                print(f"Estado: {mt5_recovery.state}")
        except KeyboardInterrupt:
            await mt5_recovery.stop()
    
    asyncio.run(main())
