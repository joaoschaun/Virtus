"""
VIRTUS Bot Framework - Base Classes
====================================

Classes base para todos os tipos de bots do sistema VIRTUS.
Suporta: Forex, Arbitragem, Crypto, Stocks, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import asyncio
import uuid


class BotType(Enum):
    """Tipos de bot suportados."""
    FOREX = "forex"
    ARBITRAGE = "arbitrage"
    CRYPTO = "crypto"
    STOCKS = "stocks"
    FUTURES = "futures"
    OPTIONS = "options"
    CUSTOM = "custom"


class BotStatus(Enum):
    """Status do bot."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class MarketType(Enum):
    """Tipos de mercado."""
    MT5 = "mt5"
    BINANCE = "binance"
    BYBIT = "bybit"
    FTX = "ftx"
    KRAKEN = "kraken"
    B3 = "b3"
    NYSE = "nyse"
    CUSTOM = "custom"


@dataclass
class BotMetrics:
    """Métricas padronizadas de um bot."""
    # Identificação
    bot_id: str
    bot_type: BotType
    
    # Performance
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Financeiro
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    profit_factor: float = 0.0
    
    # Risco
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Sessão atual
    daily_trades: int = 0
    daily_profit: float = 0.0
    daily_win_rate: float = 0.0
    
    # Timestamps
    last_trade_time: Optional[datetime] = None
    last_update: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "bot_id": self.bot_id,
            "bot_type": self.bot_type.value,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 2),
            "gross_profit": round(self.gross_profit, 2),
            "gross_loss": round(self.gross_loss, 2),
            "net_profit": round(self.net_profit, 2),
            "profit_factor": round(self.profit_factor, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "current_drawdown": round(self.current_drawdown, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "daily_trades": self.daily_trades,
            "daily_profit": round(self.daily_profit, 2),
            "daily_win_rate": round(self.daily_win_rate, 2),
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "last_update": self.last_update.isoformat(),
        }
    
    def update_from_trade(self, profit: float, is_win: bool):
        """Atualiza métricas após um trade."""
        self.total_trades += 1
        self.daily_trades += 1
        
        if is_win:
            self.winning_trades += 1
            self.gross_profit += profit
        else:
            self.losing_trades += 1
            self.gross_loss += abs(profit)
        
        self.net_profit = self.gross_profit - self.gross_loss
        self.daily_profit += profit
        
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
        
        if self.daily_trades > 0:
            daily_wins = sum(1 for _ in range(self.daily_trades) if is_win)  # Simplificado
            self.daily_win_rate = (daily_wins / self.daily_trades) * 100
        
        if self.gross_loss > 0:
            self.profit_factor = self.gross_profit / self.gross_loss
        
        self.last_trade_time = datetime.now()
        self.last_update = datetime.now()


@dataclass
class BotConfig:
    """Configuração base de um bot."""
    # Identificação
    bot_id: str
    name: str
    bot_type: BotType
    
    # Mercado
    market: MarketType
    symbols: List[str] = field(default_factory=list)
    
    # Estratégias
    strategies: List[str] = field(default_factory=list)
    
    # Risco
    max_position_size: float = 0.1
    max_daily_loss: float = 100.0
    max_drawdown: float = 10.0
    risk_per_trade: float = 1.0
    
    # Operacional
    enabled: bool = True
    auto_start: bool = False
    trading_hours: Optional[Dict[str, str]] = None  # {"start": "09:00", "end": "17:00"}
    
    # Específico por tipo (flexível)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "bot_id": self.bot_id,
            "name": self.name,
            "bot_type": self.bot_type.value,
            "market": self.market.value,
            "symbols": self.symbols,
            "strategies": self.strategies,
            "max_position_size": self.max_position_size,
            "max_daily_loss": self.max_daily_loss,
            "max_drawdown": self.max_drawdown,
            "risk_per_trade": self.risk_per_trade,
            "enabled": self.enabled,
            "auto_start": self.auto_start,
            "trading_hours": self.trading_hours,
            "extra": self.extra,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BotConfig":
        """Cria instância a partir de dicionário."""
        return cls(
            bot_id=data.get("bot_id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Bot"),
            bot_type=BotType(data.get("bot_type", "custom")),
            market=MarketType(data.get("market", "custom")),
            symbols=data.get("symbols", []),
            strategies=data.get("strategies", []),
            max_position_size=data.get("max_position_size", 0.1),
            max_daily_loss=data.get("max_daily_loss", 100.0),
            max_drawdown=data.get("max_drawdown", 10.0),
            risk_per_trade=data.get("risk_per_trade", 1.0),
            enabled=data.get("enabled", True),
            auto_start=data.get("auto_start", False),
            trading_hours=data.get("trading_hours"),
            extra=data.get("extra", {}),
        )


class BaseBot(ABC):
    """
    Classe base abstrata para todos os bots.
    
    Todo novo tipo de bot deve herdar desta classe e implementar
    os métodos abstratos.
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.bot_id = config.bot_id
        self.name = config.name
        self.bot_type = config.bot_type
        
        self._status = BotStatus.STOPPED
        self._metrics = BotMetrics(bot_id=self.bot_id, bot_type=self.bot_type)
        self._positions: List[Dict[str, Any]] = []
        self._trade_history: List[Dict[str, Any]] = []
        
        # Callbacks para eventos
        self._on_trade_callbacks: List[Callable] = []
        self._on_status_change_callbacks: List[Callable] = []
        self._on_error_callbacks: List[Callable] = []
        
        # Task de execução
        self._run_task: Optional[asyncio.Task] = None
    
    # ==================== Propriedades ====================
    
    @property
    def status(self) -> BotStatus:
        """Status atual do bot."""
        return self._status
    
    @status.setter
    def status(self, value: BotStatus):
        """Define status e notifica callbacks."""
        old_status = self._status
        self._status = value
        self._notify_status_change(old_status, value)
    
    @property
    def metrics(self) -> BotMetrics:
        """Métricas do bot."""
        return self._metrics
    
    @property
    def positions(self) -> List[Dict[str, Any]]:
        """Posições abertas."""
        return self._positions
    
    @property
    def is_running(self) -> bool:
        """Verifica se está rodando."""
        return self._status == BotStatus.RUNNING
    
    # ==================== Métodos Abstratos ====================
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Conecta ao mercado/exchange.
        
        Returns:
            True se conectou com sucesso
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Desconecta do mercado/exchange.
        
        Returns:
            True se desconectou com sucesso
        """
        pass
    
    @abstractmethod
    async def execute_trade(
        self,
        symbol: str,
        side: str,  # "buy" ou "sell"
        size: float,
        price: Optional[float] = None,  # None para market order
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Executa uma operação.
        
        Args:
            symbol: Símbolo do ativo
            side: "buy" ou "sell"
            size: Tamanho da posição
            price: Preço limite (None para market)
            **kwargs: Parâmetros adicionais específicos
            
        Returns:
            Dados da ordem executada ou None se falhou
        """
        pass
    
    @abstractmethod
    async def close_position(
        self,
        position_id: str,
        **kwargs
    ) -> bool:
        """
        Fecha uma posição.
        
        Args:
            position_id: ID da posição
            **kwargs: Parâmetros adicionais
            
        Returns:
            True se fechou com sucesso
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Obtém informações da conta.
        
        Returns:
            Dict com balance, equity, margin, etc.
        """
        pass
    
    @abstractmethod
    async def get_market_data(
        self,
        symbol: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Obtém dados de mercado.
        
        Args:
            symbol: Símbolo do ativo
            **kwargs: Parâmetros adicionais (timeframe, etc.)
            
        Returns:
            Dict com preços, volume, etc.
        """
        pass
    
    @abstractmethod
    async def run_strategy(self):
        """
        Executa a lógica principal do bot.
        
        Este método é chamado continuamente enquanto o bot está rodando.
        Deve conter a lógica de análise e tomada de decisão.
        """
        pass
    
    # ==================== Métodos de Ciclo de Vida ====================
    
    async def start(self) -> bool:
        """Inicia o bot."""
        if self._status == BotStatus.RUNNING:
            return True
        
        try:
            self.status = BotStatus.STARTING
            
            # Conecta ao mercado
            if not await self.connect():
                self.status = BotStatus.ERROR
                return False
            
            # Inicia loop principal
            self._run_task = asyncio.create_task(self._main_loop())
            self.status = BotStatus.RUNNING
            
            return True
            
        except Exception as e:
            self._notify_error(e)
            self.status = BotStatus.ERROR
            return False
    
    async def stop(self) -> bool:
        """Para o bot."""
        if self._status == BotStatus.STOPPED:
            return True
        
        try:
            # Cancela task principal
            if self._run_task:
                self._run_task.cancel()
                try:
                    await self._run_task
                except asyncio.CancelledError:
                    pass
            
            # Desconecta
            await self.disconnect()
            
            self.status = BotStatus.STOPPED
            return True
            
        except Exception as e:
            self._notify_error(e)
            return False
    
    async def pause(self) -> bool:
        """Pausa o bot."""
        if self._status == BotStatus.RUNNING:
            self.status = BotStatus.PAUSED
            return True
        return False
    
    async def resume(self) -> bool:
        """Retoma o bot pausado."""
        if self._status == BotStatus.PAUSED:
            self.status = BotStatus.RUNNING
            return True
        return False
    
    async def _main_loop(self):
        """Loop principal de execução."""
        while self._status in [BotStatus.RUNNING, BotStatus.PAUSED]:
            try:
                if self._status == BotStatus.RUNNING:
                    await self.run_strategy()
                
                # Intervalo entre iterações (configurável)
                await asyncio.sleep(self.config.extra.get("loop_interval", 1.0))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._notify_error(e)
                await asyncio.sleep(5)  # Espera antes de tentar novamente
    
    # ==================== Métodos de Callback ====================
    
    def on_trade(self, callback: Callable):
        """Registra callback para quando um trade é executado."""
        self._on_trade_callbacks.append(callback)
    
    def on_status_change(self, callback: Callable):
        """Registra callback para mudança de status."""
        self._on_status_change_callbacks.append(callback)
    
    def on_error(self, callback: Callable):
        """Registra callback para erros."""
        self._on_error_callbacks.append(callback)
    
    def _notify_trade(self, trade: Dict[str, Any]):
        """Notifica callbacks sobre trade."""
        for callback in self._on_trade_callbacks:
            try:
                callback(self.bot_id, trade)
            except Exception:
                pass
    
    def _notify_status_change(self, old_status: BotStatus, new_status: BotStatus):
        """Notifica callbacks sobre mudança de status."""
        for callback in self._on_status_change_callbacks:
            try:
                callback(self.bot_id, old_status, new_status)
            except Exception:
                pass
    
    def _notify_error(self, error: Exception):
        """Notifica callbacks sobre erro."""
        for callback in self._on_error_callbacks:
            try:
                callback(self.bot_id, error)
            except Exception:
                pass
    
    # ==================== Métodos Utilitários ====================
    
    def get_state(self) -> Dict[str, Any]:
        """
        Retorna estado completo do bot para o dashboard.
        
        Returns:
            Dict com todas as informações do bot
        """
        return {
            "id": self.bot_id,
            "name": self.name,
            "type": self.bot_type.value,
            "status": self._status.value,
            "market": self.config.market.value,
            "symbols": self.config.symbols,
            "strategies": self.config.strategies,
            "metrics": self._metrics.to_dict(),
            "positions": self._positions,
            "config": self.config.to_dict(),
        }
    
    def update_metrics(self, profit: float, is_win: bool):
        """Atualiza métricas após trade."""
        self._metrics.update_from_trade(profit, is_win)
    
    def add_position(self, position: Dict[str, Any]):
        """Adiciona posição aberta."""
        self._positions.append(position)
    
    def remove_position(self, position_id: str):
        """Remove posição fechada."""
        self._positions = [p for p in self._positions if p.get("id") != position_id]
    
    def add_trade_history(self, trade: Dict[str, Any]):
        """Adiciona trade ao histórico."""
        self._trade_history.append(trade)
        # Mantém apenas últimos 1000 trades
        if len(self._trade_history) > 1000:
            self._trade_history = self._trade_history[-1000:]
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.bot_id} status={self._status.value}>"
