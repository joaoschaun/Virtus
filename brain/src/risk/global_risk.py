"""
VIRTUS Global Risk Manager
===========================

Gerenciamento de risco global para múltiplos bots.
Coordena exposição total e limites cross-symbol.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio

try:
    from ..core import VirtusLogger, RiskConfig
except ImportError:
    from core import VirtusLogger, RiskConfig


class GlobalRiskState(Enum):
    """Estado global de risco."""
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class TradingMode(Enum):
    """Modo de trading baseado no risco."""
    FULL = "full"              # Trading normal
    REDUCED = "reduced"        # Tamanhos reduzidos
    DEFENSIVE = "defensive"    # Apenas proteção
    STOPPED = "stopped"        # Sem novos trades


@dataclass
class BotRiskStatus:
    """Status de risco de um bot individual."""
    bot_id: str
    symbol: str
    
    # Exposição
    open_positions: int = 0
    total_volume: float = 0.0
    unrealized_pnl: float = 0.0
    
    # Drawdown
    daily_pnl: float = 0.0
    max_drawdown_today: float = 0.0
    
    # Estado
    is_active: bool = True
    is_blocked: bool = False
    block_reason: str = ""
    
    # Timestamp
    last_update: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'bot_id': self.bot_id,
            'symbol': self.symbol,
            'open_positions': self.open_positions,
            'total_volume': round(self.total_volume, 2),
            'unrealized_pnl': round(self.unrealized_pnl, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'is_active': self.is_active,
            'is_blocked': self.is_blocked,
        }


@dataclass
class GlobalRiskMetrics:
    """Métricas de risco globais."""
    state: GlobalRiskState = GlobalRiskState.NORMAL
    trading_mode: TradingMode = TradingMode.FULL
    
    # Totais
    total_equity: float = 0.0
    total_balance: float = 0.0
    total_unrealized: float = 0.0
    total_positions: int = 0
    
    # Exposição
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    exposure_pct: float = 0.0
    
    # Drawdown
    global_drawdown: float = 0.0
    max_drawdown: float = 0.0
    
    # Por bot
    active_bots: int = 0
    blocked_bots: int = 0
    
    # Limites
    margin_usage_pct: float = 0.0
    daily_loss_pct: float = 0.0
    
    # Risk metrics
    correlation_risk: float = 0.0
    concentration_risk: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'state': self.state.value,
            'trading_mode': self.trading_mode.value,
            'total_equity': round(self.total_equity, 2),
            'total_positions': self.total_positions,
            'gross_exposure': round(self.gross_exposure, 2),
            'exposure_pct': round(self.exposure_pct, 2),
            'global_drawdown': round(self.global_drawdown, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'active_bots': self.active_bots,
            'blocked_bots': self.blocked_bots,
            'daily_loss_pct': round(self.daily_loss_pct, 2),
        }


@dataclass
class GlobalRiskConfig:
    """Configuração de risco global."""
    # Limites globais
    max_global_drawdown_pct: float = 10.0
    max_daily_loss_pct: float = 5.0
    max_total_positions: int = 15
    max_gross_exposure_pct: float = 50.0
    
    # Limites por bot
    max_positions_per_bot: int = 5
    max_loss_per_bot_pct: float = 3.0
    
    # Concentração
    max_symbol_concentration_pct: float = 40.0
    max_correlated_exposure_pct: float = 60.0
    
    # Circuit breakers
    drawdown_warning_pct: float = 5.0
    drawdown_danger_pct: float = 7.5
    drawdown_critical_pct: float = 10.0
    
    # Recovery
    recovery_threshold_pct: float = 2.0  # Drawdown necessário para voltar ao normal


class GlobalRiskManager:
    """
    Gerenciador de risco global para múltiplos bots.
    
    Responsabilidades:
    - Coordenação de risco entre bots
    - Limites globais de exposição
    - Circuit breakers globais
    - Balanceamento de risco
    """
    
    _instance: Optional['GlobalRiskManager'] = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[GlobalRiskConfig] = None):
        if hasattr(self, '_initialized'):
            return
        
        self.config = config or GlobalRiskConfig()
        self.logger = VirtusLogger.get_logger("global_risk")
        
        # Estado
        self.metrics = GlobalRiskMetrics()
        
        # Bots registrados
        self._bots: Dict[str, BotRiskStatus] = {}
        
        # Histórico
        self._equity_history: List[tuple[datetime, float]] = []
        self._peak_equity: float = 0.0
        
        # Bloqueios
        self._blocked_bots: Set[str] = set()
        self._global_block = False
        self._block_reason = ""
        
        self._initialized = True
    
    # ========================================================================
    # REGISTRO DE BOTS
    # ========================================================================
    
    def register_bot(
        self,
        bot_id: str,
        symbol: str
    ) -> None:
        """
        Registra um bot no gerenciador global.
        
        Args:
            bot_id: ID único do bot
            symbol: Símbolo que o bot opera
        """
        self._bots[bot_id] = BotRiskStatus(
            bot_id=bot_id,
            symbol=symbol,
        )
        self.logger.info(f"Bot registrado: {bot_id} ({symbol})")
    
    def unregister_bot(self, bot_id: str) -> None:
        """Remove um bot do gerenciador."""
        if bot_id in self._bots:
            del self._bots[bot_id]
            self._blocked_bots.discard(bot_id)
            self.logger.info(f"Bot removido: {bot_id}")
    
    # ========================================================================
    # ATUALIZAÇÃO DE ESTADO
    # ========================================================================
    
    async def update_bot_status(
        self,
        bot_id: str,
        positions: int = 0,
        volume: float = 0.0,
        unrealized_pnl: float = 0.0,
        daily_pnl: float = 0.0
    ) -> None:
        """
        Atualiza status de risco de um bot.
        
        Args:
            bot_id: ID do bot
            positions: Número de posições abertas
            volume: Volume total
            unrealized_pnl: P&L não realizado
            daily_pnl: P&L do dia
        """
        if bot_id not in self._bots:
            return
        
        status = self._bots[bot_id]
        status.open_positions = positions
        status.total_volume = volume
        status.unrealized_pnl = unrealized_pnl
        status.daily_pnl = daily_pnl
        status.last_update = datetime.now()
        
        # Verifica limites do bot
        await self._check_bot_limits(bot_id)
    
    async def update_global_state(
        self,
        equity: float,
        balance: float,
        margin_used: float = 0.0
    ) -> None:
        """
        Atualiza estado global.
        
        Args:
            equity: Equity total da conta
            balance: Balance da conta
            margin_used: Margem utilizada
        """
        # Atualiza métricas
        self.metrics.total_equity = equity
        self.metrics.total_balance = balance
        self.metrics.total_unrealized = equity - balance
        
        # Margin usage
        if equity > 0:
            self.metrics.margin_usage_pct = (margin_used / equity) * 100
        
        # Atualiza drawdown
        if equity > self._peak_equity:
            self._peak_equity = equity
        
        if self._peak_equity > 0:
            self.metrics.global_drawdown = (
                (self._peak_equity - equity) / self._peak_equity
            ) * 100
            
            if self.metrics.global_drawdown > self.metrics.max_drawdown:
                self.metrics.max_drawdown = self.metrics.global_drawdown
        
        # Histórico
        self._equity_history.append((datetime.now(), equity))
        
        # Mantém apenas 30 dias
        cutoff = datetime.now() - timedelta(days=30)
        self._equity_history = [
            (t, e) for t, e in self._equity_history
            if t >= cutoff
        ]
        
        # Calcula métricas agregadas
        await self._update_aggregated_metrics()
        
        # Verifica limites globais
        await self._check_global_limits()
    
    async def _update_aggregated_metrics(self) -> None:
        """Atualiza métricas agregadas de todos os bots."""
        total_positions = 0
        gross_exposure = 0.0
        active_bots = 0
        blocked_bots = 0
        
        for bot_id, status in self._bots.items():
            total_positions += status.open_positions
            gross_exposure += status.total_volume
            
            if status.is_active and not status.is_blocked:
                active_bots += 1
            if status.is_blocked:
                blocked_bots += 1
        
        self.metrics.total_positions = total_positions
        self.metrics.gross_exposure = gross_exposure
        self.metrics.active_bots = active_bots
        self.metrics.blocked_bots = blocked_bots
        
        # Exposure percentage
        if self.metrics.total_equity > 0:
            self.metrics.exposure_pct = (
                gross_exposure * 100000 / self.metrics.total_equity
            ) * 100  # Assumindo 100k por lot
    
    # ========================================================================
    # VERIFICAÇÃO DE LIMITES
    # ========================================================================
    
    async def _check_bot_limits(self, bot_id: str) -> None:
        """Verifica limites de um bot específico."""
        if bot_id not in self._bots:
            return
        
        status = self._bots[bot_id]
        
        # Limite de posições
        if status.open_positions > self.config.max_positions_per_bot:
            await self._block_bot(
                bot_id,
                f"Excedeu limite de posições: {status.open_positions}"
            )
            return
        
        # Limite de loss diário
        if self.metrics.total_balance > 0:
            loss_pct = abs(status.daily_pnl / self.metrics.total_balance) * 100
            if loss_pct > self.config.max_loss_per_bot_pct:
                await self._block_bot(
                    bot_id,
                    f"Excedeu loss diário: {loss_pct:.2f}%"
                )
    
    async def _check_global_limits(self) -> None:
        """Verifica limites globais."""
        # Drawdown
        dd = self.metrics.global_drawdown
        
        if dd >= self.config.drawdown_critical_pct:
            self.metrics.state = GlobalRiskState.CRITICAL
            self.metrics.trading_mode = TradingMode.STOPPED
            await self._global_stop("Drawdown crítico")
            
        elif dd >= self.config.drawdown_danger_pct:
            self.metrics.state = GlobalRiskState.HIGH
            self.metrics.trading_mode = TradingMode.DEFENSIVE
            
        elif dd >= self.config.drawdown_warning_pct:
            self.metrics.state = GlobalRiskState.ELEVATED
            self.metrics.trading_mode = TradingMode.REDUCED
            
        elif dd < self.config.recovery_threshold_pct:
            if self.metrics.state != GlobalRiskState.CRITICAL:
                self.metrics.state = GlobalRiskState.NORMAL
                self.metrics.trading_mode = TradingMode.FULL
        
        # Posições totais
        if self.metrics.total_positions > self.config.max_total_positions:
            self.metrics.trading_mode = TradingMode.STOPPED
            self.logger.warning(
                f"Limite de posições excedido: {self.metrics.total_positions}"
            )
        
        # Exposição
        if self.metrics.exposure_pct > self.config.max_gross_exposure_pct:
            self.metrics.trading_mode = TradingMode.STOPPED
            self.logger.warning(
                f"Exposição excedida: {self.metrics.exposure_pct:.2f}%"
            )
    
    # ========================================================================
    # BLOQUEIOS
    # ========================================================================
    
    async def _block_bot(self, bot_id: str, reason: str) -> None:
        """Bloqueia um bot."""
        if bot_id in self._bots:
            self._bots[bot_id].is_blocked = True
            self._bots[bot_id].block_reason = reason
            self._blocked_bots.add(bot_id)
            self.logger.warning(f"Bot bloqueado: {bot_id} - {reason}")
    
    async def unblock_bot(self, bot_id: str) -> bool:
        """Desbloqueia um bot."""
        if bot_id in self._bots:
            self._bots[bot_id].is_blocked = False
            self._bots[bot_id].block_reason = ""
            self._blocked_bots.discard(bot_id)
            self.logger.info(f"Bot desbloqueado: {bot_id}")
            return True
        return False
    
    async def _global_stop(self, reason: str) -> None:
        """Para todos os bots."""
        self._global_block = True
        self._block_reason = reason
        
        for bot_id in self._bots:
            await self._block_bot(bot_id, f"Global stop: {reason}")
        
        self.logger.critical(f"GLOBAL STOP ATIVADO: {reason}")
    
    async def global_resume(self) -> bool:
        """Resume trading global."""
        if self.metrics.global_drawdown < self.config.drawdown_danger_pct:
            self._global_block = False
            self._block_reason = ""
            
            for bot_id in list(self._blocked_bots):
                await self.unblock_bot(bot_id)
            
            self.metrics.state = GlobalRiskState.NORMAL
            self.metrics.trading_mode = TradingMode.FULL
            
            self.logger.info("Trading global retomado")
            return True
        
        return False
    
    # ========================================================================
    # PERMISSÕES
    # ========================================================================
    
    def can_open_position(
        self,
        bot_id: str,
        volume: float = 0.0
    ) -> tuple[bool, str]:
        """
        Verifica se um bot pode abrir posição.
        
        Args:
            bot_id: ID do bot
            volume: Volume desejado
            
        Returns:
            (permitido, motivo)
        """
        # Bloqueio global
        if self._global_block:
            return False, f"Bloqueio global: {self._block_reason}"
        
        # Trading mode
        if self.metrics.trading_mode == TradingMode.STOPPED:
            return False, "Trading pausado"
        
        # Bot bloqueado
        if bot_id in self._blocked_bots:
            reason = self._bots.get(bot_id, BotRiskStatus(bot_id, "")).block_reason
            return False, f"Bot bloqueado: {reason}"
        
        # Limite de posições
        if self.metrics.total_positions >= self.config.max_total_positions:
            return False, "Limite de posições atingido"
        
        # Bot individual
        if bot_id in self._bots:
            status = self._bots[bot_id]
            if status.open_positions >= self.config.max_positions_per_bot:
                return False, "Limite de posições do bot atingido"
        
        # Exposição
        new_exposure = self.metrics.exposure_pct + (volume * 100000 / max(1, self.metrics.total_equity)) * 100
        if new_exposure > self.config.max_gross_exposure_pct:
            return False, f"Exposição excederia limite: {new_exposure:.1f}%"
        
        return True, "OK"
    
    def get_allowed_volume(self, bot_id: str, base_volume: float) -> float:
        """
        Ajusta volume baseado no modo de trading.
        
        Args:
            bot_id: ID do bot
            base_volume: Volume base desejado
            
        Returns:
            Volume ajustado
        """
        multipliers = {
            TradingMode.FULL: 1.0,
            TradingMode.REDUCED: 0.5,
            TradingMode.DEFENSIVE: 0.25,
            TradingMode.STOPPED: 0.0,
        }
        
        mult = multipliers.get(self.metrics.trading_mode, 0.0)
        return base_volume * mult
    
    # ========================================================================
    # CONSULTAS
    # ========================================================================
    
    def get_metrics(self) -> GlobalRiskMetrics:
        """Retorna métricas globais."""
        return self.metrics
    
    def get_bot_status(self, bot_id: str) -> Optional[BotRiskStatus]:
        """Retorna status de um bot."""
        return self._bots.get(bot_id)
    
    def get_all_bots_status(self) -> Dict[str, BotRiskStatus]:
        """Retorna status de todos os bots."""
        return self._bots.copy()
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Retorna resumo do estado global."""
        return {
            'metrics': self.metrics.to_dict(),
            'global_blocked': self._global_block,
            'block_reason': self._block_reason,
            'bots': {
                bot_id: status.to_dict()
                for bot_id, status in self._bots.items()
            },
        }
    
    # ========================================================================
    # RESET
    # ========================================================================
    
    async def daily_reset(self) -> None:
        """Reset diário de métricas."""
        self.logger.info("Reset diário de métricas de risco")
        
        # Reset de P&L diário dos bots
        for status in self._bots.values():
            status.daily_pnl = 0.0
            status.max_drawdown_today = 0.0
        
        # Reset de estado se não crítico
        if self.metrics.state != GlobalRiskState.CRITICAL:
            self.metrics.daily_loss_pct = 0.0
