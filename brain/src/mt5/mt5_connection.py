"""
VIRTUS MT5 - Connection Manager
================================

Gerenciador de conexão com MetaTrader 5.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import MetaTrader5 as mt5

from ..core.logger import get_logger
from ..core.config import get_config
from ..core.exceptions import (
    MT5ConnectionError, MT5AuthenticationError, MT5SymbolError
)

logger = get_logger("mt5")


class MT5ConnectionStatus(Enum):
    """Status da conexão MT5"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"


class MT5Connection:
    """
    Gerenciador de conexão com MetaTrader 5.
    
    Singleton que mantém a conexão ativa com o terminal MT5.
    
    Uso:
        mt5_conn = await MT5Connection.get_instance()
        if mt5_conn.is_connected:
            # usar mt5
    """
    
    _instance: Optional['MT5Connection'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._status = MT5ConnectionStatus.DISCONNECTED
        self._account_info: Optional[Dict[str, Any]] = None
        self._terminal_info: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
    
    @classmethod
    async def get_instance(cls) -> 'MT5Connection':
        """Retorna instância singleton"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    @property
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self._status == MT5ConnectionStatus.CONNECTED and mt5.terminal_info() is not None
    
    @property
    def status(self) -> MT5ConnectionStatus:
        """Status atual da conexão"""
        return self._status
    
    @property
    def account_info(self) -> Optional[Dict[str, Any]]:
        """Informações da conta"""
        return self._account_info
    
    @property
    def last_error(self) -> Optional[str]:
        """Último erro"""
        return self._last_error
    
    async def connect(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        path: Optional[str] = None
    ) -> bool:
        """
        Conecta ao MetaTrader 5.
        
        Args:
            login: Número da conta (opcional, usa config)
            password: Senha (opcional, usa config)
            server: Servidor (opcional, usa config)
            path: Caminho do terminal (opcional)
            
        Returns:
            True se conectado com sucesso
        """
        self._status = MT5ConnectionStatus.CONNECTING
        logger.info("🔌 Conectando ao MetaTrader 5...")
        
        try:
            # Carrega config se não fornecido
            config = get_config()
            login = login or config.mt5.login
            password = password or config.mt5.password
            server = server or config.mt5.server
            path = path or config.mt5.path
            
            # Tenta inicializar MT5 - primeiro sem path, depois com path
            initialized = False
            
            # Tentativa 1: Inicializar sem path (usa terminal já aberto)
            if mt5.initialize():
                initialized = True
                logger.info("✅ MT5 inicializado (terminal existente)")
            # Tentativa 2: Inicializar com path
            elif path and mt5.initialize(path=path):
                initialized = True
                logger.info(f"✅ MT5 inicializado com path: {path}")
            
            if not initialized:
                error = mt5.last_error()
                self._last_error = f"Falha ao inicializar MT5: {error}"
                self._status = MT5ConnectionStatus.ERROR
                logger.error(f"❌ {self._last_error}")
                logger.error("💡 Dica: Abra o MetaTrader 5 e faça login manualmente primeiro")
                raise MT5ConnectionError(self._last_error)
            
            # Verifica se já está logado na conta correta
            current_account = mt5.account_info()
            if current_account and current_account.login == login:
                logger.info(f"✅ Já logado na conta {login}")
            # Login apenas se necessário
            elif login and password and server:
                authorized = mt5.login(
                    login=login,
                    password=password,
                    server=server
                )
                
                if not authorized:
                    error = mt5.last_error()
                    self._last_error = f"Falha no login MT5: {error}"
                    self._status = MT5ConnectionStatus.ERROR
                    logger.error(f"❌ {self._last_error}")
                    raise MT5AuthenticationError(self._last_error)
            
            # Obtém informações
            self._terminal_info = mt5.terminal_info()._asdict()
            self._account_info = mt5.account_info()._asdict()
            
            self._status = MT5ConnectionStatus.CONNECTED
            self._reconnect_attempts = 0
            
            logger.info(f"✅ Conectado ao MT5 - Conta: {self._account_info['login']}")
            logger.info(f"   Server: {self._account_info['server']}")
            logger.info(f"   Balance: ${self._account_info['balance']:.2f}")
            
            return True
            
        except MT5ConnectionError:
            raise
        except MT5AuthenticationError:
            raise
        except Exception as e:
            self._last_error = str(e)
            self._status = MT5ConnectionStatus.ERROR
            logger.error(f"❌ Erro ao conectar MT5: {e}")
            raise MT5ConnectionError(str(e))
    
    async def disconnect(self):
        """Desconecta do MT5"""
        logger.info("🔌 Desconectando do MT5...")
        mt5.shutdown()
        self._status = MT5ConnectionStatus.DISCONNECTED
        self._account_info = None
        self._terminal_info = None
        logger.info("✅ Desconectado do MT5")
    
    async def reconnect(self) -> bool:
        """Tenta reconectar ao MT5"""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("❌ Máximo de tentativas de reconexão excedido")
            return False
        
        self._reconnect_attempts += 1
        logger.warning(f"⚠️ Tentando reconectar ({self._reconnect_attempts}/{self._max_reconnect_attempts})...")
        
        await asyncio.sleep(5)  # Aguarda antes de reconectar
        
        try:
            await self.disconnect()
            return await self.connect()
        except Exception as e:
            logger.error(f"❌ Falha na reconexão: {e}")
            return False
    
    async def ensure_connected(self) -> bool:
        """Garante que está conectado, reconectando se necessário"""
        if self.is_connected:
            return True
        return await self.reconnect()
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações de um símbolo.
        
        Args:
            symbol: Símbolo (ex: 'XAUUSD')
            
        Returns:
            Dict com informações do símbolo
        """
        if not self.is_connected:
            return None
        
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        
        return info._asdict()
    
    def select_symbol(self, symbol: str) -> bool:
        """
        Seleciona símbolo para trading.
        
        Args:
            symbol: Símbolo
            
        Returns:
            True se selecionado com sucesso
        """
        if not self.is_connected:
            return False
        
        # Verifica se existe
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.warning(f"Símbolo {symbol} não encontrado")
            return False
        
        # Habilita no Market Watch
        if not info.visible:
            if not mt5.symbol_select(symbol, True):
                logger.warning(f"Não foi possível selecionar {symbol}")
                return False
        
        return True
    
    def get_account_balance(self) -> float:
        """Retorna saldo da conta"""
        if self.is_connected:
            info = mt5.account_info()
            return info.balance if info else 0.0
        return 0.0
    
    def get_account_equity(self) -> float:
        """Retorna equity da conta"""
        if self.is_connected:
            info = mt5.account_info()
            return info.equity if info else 0.0
        return 0.0
    
    def get_account_margin(self) -> float:
        """Retorna margem usada"""
        if self.is_connected:
            info = mt5.account_info()
            return info.margin if info else 0.0
        return 0.0
    
    def get_account_free_margin(self) -> float:
        """Retorna margem livre"""
        if self.is_connected:
            info = mt5.account_info()
            return info.margin_free if info else 0.0
        return 0.0
    
    def refresh_account_info(self):
        """Atualiza informações da conta"""
        if self.is_connected:
            info = mt5.account_info()
            if info:
                self._account_info = info._asdict()
    
    def get_status_report(self) -> Dict[str, Any]:
        """Retorna relatório de status"""
        self.refresh_account_info()
        
        return {
            'status': self._status.value,
            'connected': self.is_connected,
            'last_error': self._last_error,
            'reconnect_attempts': self._reconnect_attempts,
            'account': self._account_info,
            'terminal': self._terminal_info,
        }


# Helper para obter conexão
async def get_mt5_connection() -> MT5Connection:
    """Retorna instância da conexão MT5"""
    return await MT5Connection.get_instance()
