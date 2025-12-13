"""
BRAIN - Risk Manager
Gerenciamento de risco
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.types import Position, Signal, OrderType
from ..core.logger import get_logger
from ..core.exceptions import RiskError

logger = get_logger("risk")


class RiskLevel(Enum):
    """Nível de risco"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskConfig:
    """Configuração de risco"""
    # Risco por trade
    risk_per_trade: float = 1.0  # % do equity
    max_risk_per_trade: float = 2.0
    
    # Risco total
    max_total_risk: float = 5.0  # % do equity
    max_daily_loss: float = 3.0  # % do equity
    max_weekly_loss: float = 7.0
    
    # Limites
    max_positions: int = 3
    max_positions_per_symbol: int = 1
    max_daily_trades: int = 10
    
    # Drawdown
    max_drawdown: float = 10.0  # %
    
    # Margem
    min_margin_level: float = 150  # %
    warning_margin_level: float = 200


@dataclass
class RiskState:
    """Estado atual de risco"""
    total_positions: int = 0
    total_risk_percent: float = 0.0
    daily_pnl: float = 0.0
    daily_trades: int = 0
    current_drawdown: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    
    # Por símbolo
    positions_by_symbol: Dict[str, int] = field(default_factory=dict)
    risk_by_symbol: Dict[str, float] = field(default_factory=dict)


class RiskManager:
    """
    Gerenciador de Risco
    
    Responsabilidades:
    - Calcular position sizing
    - Validar trades antes da execução
    - Monitorar exposição total
    - Limitar perdas
    """
    
    def __init__(self, config: RiskConfig = None):
        self._config = config or RiskConfig()
        self._state = RiskState()
        
        # Histórico do dia
        self._daily_trades: List[Dict] = []
        self._peak_equity: float = 0.0
        self._last_reset = datetime.now().date()
    
    @property
    def risk_level(self) -> RiskLevel:
        """Nível de risco atual"""
        return self._state.risk_level
    
    @property
    def can_trade(self) -> bool:
        """Verifica se pode abrir novos trades"""
        return self._state.risk_level != RiskLevel.CRITICAL
    
    def update_state(
        self,
        positions: List[Position],
        account_info: Dict[str, Any]
    ):
        """
        Atualiza estado de risco
        
        Args:
            positions: Lista de posições abertas
            account_info: Informações da conta
        """
        # Reset diário
        today = datetime.now().date()
        if today != self._last_reset:
            self._daily_reset()
            self._last_reset = today
        
        equity = account_info.get("equity", 0)
        balance = account_info.get("balance", 0)
        margin_level = account_info.get("margin_level", 100)
        
        # Atualizar peak equity
        if equity > self._peak_equity:
            self._peak_equity = equity
        
        # Calcular drawdown
        if self._peak_equity > 0:
            self._state.current_drawdown = (
                (self._peak_equity - equity) / self._peak_equity * 100
            )
        
        # Posições por símbolo
        self._state.positions_by_symbol.clear()
        self._state.risk_by_symbol.clear()
        total_risk = 0.0
        
        for pos in positions:
            symbol = pos.symbol
            
            # Contar posições
            self._state.positions_by_symbol[symbol] = \
                self._state.positions_by_symbol.get(symbol, 0) + 1
            
            # Calcular risco da posição
            if pos.stop_loss and equity > 0:
                sl_distance = abs(pos.price_open - pos.stop_loss)
                # Simplificado - assumindo pip value
                risk_value = sl_distance * pos.volume * 100000 * 0.0001
                risk_percent = (risk_value / equity) * 100
                
                self._state.risk_by_symbol[symbol] = \
                    self._state.risk_by_symbol.get(symbol, 0) + risk_percent
                total_risk += risk_percent
        
        self._state.total_positions = len(positions)
        self._state.total_risk_percent = total_risk
        
        # Determinar nível de risco
        self._state.risk_level = self._calculate_risk_level(margin_level)
    
    def _calculate_risk_level(self, margin_level: float) -> RiskLevel:
        """Calcula nível de risco atual"""
        # Crítico: margin call ou drawdown extremo
        if (margin_level < self._config.min_margin_level or
            self._state.current_drawdown >= self._config.max_drawdown or
            abs(self._state.daily_pnl) >= self._config.max_daily_loss):
            return RiskLevel.CRITICAL
        
        # Alto: próximo dos limites
        if (margin_level < self._config.warning_margin_level or
            self._state.total_risk_percent >= self._config.max_total_risk * 0.8 or
            self._state.current_drawdown >= self._config.max_drawdown * 0.7):
            return RiskLevel.HIGH
        
        # Médio: alguma exposição
        if (self._state.total_positions >= self._config.max_positions * 0.7 or
            self._state.total_risk_percent >= self._config.max_total_risk * 0.5):
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    def _daily_reset(self):
        """Reset de contadores diários"""
        self._state.daily_pnl = 0.0
        self._state.daily_trades = 0
        self._daily_trades.clear()
        logger.info("Reset diário de risco")
    
    # ==========================================================================
    # VALIDAÇÃO DE TRADES
    # ==========================================================================
    
    def validate_trade(
        self,
        signal: Signal,
        account_info: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Valida se trade pode ser executado
        
        Args:
            signal: Sinal a validar
            account_info: Info da conta
            
        Returns:
            Tuple (pode_executar, motivo)
        """
        # Verificar nível de risco
        if self._state.risk_level == RiskLevel.CRITICAL:
            return False, "Nível de risco crítico"
        
        # Verificar máximo de posições
        if self._state.total_positions >= self._config.max_positions:
            return False, f"Máximo de {self._config.max_positions} posições atingido"
        
        # Verificar posições por símbolo
        symbol_positions = self._state.positions_by_symbol.get(signal.symbol, 0)
        if symbol_positions >= self._config.max_positions_per_symbol:
            return False, f"Máximo de posições em {signal.symbol} atingido"
        
        # Verificar trades diários
        if self._state.daily_trades >= self._config.max_daily_trades:
            return False, f"Máximo de {self._config.max_daily_trades} trades diários atingido"
        
        # Verificar perda diária
        if self._state.daily_pnl <= -self._config.max_daily_loss:
            return False, "Perda diária máxima atingida"
        
        # Verificar risco total
        new_risk = self._calculate_signal_risk(signal, account_info)
        if self._state.total_risk_percent + new_risk > self._config.max_total_risk:
            return False, "Risco total máximo seria excedido"
        
        return True, "OK"
    
    def _calculate_signal_risk(
        self,
        signal: Signal,
        account_info: Dict[str, Any]
    ) -> float:
        """Calcula risco percentual de um sinal"""
        equity = account_info.get("equity", 1)
        
        if not signal.stop_loss:
            return self._config.max_risk_per_trade
        
        sl_distance = abs(signal.entry_price - signal.stop_loss)
        # Simplificado
        risk_pips = sl_distance / 0.0001 if "JPY" not in signal.symbol else sl_distance / 0.01
        
        # Assumindo 0.01 lot por enquanto
        risk_value = risk_pips * 0.1  # $0.1 por pip para 0.01 lot
        risk_percent = (risk_value / equity) * 100
        
        return risk_percent
    
    # ==========================================================================
    # POSITION SIZING
    # ==========================================================================
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        account_info: Dict[str, Any],
        risk_percent: Optional[float] = None
    ) -> float:
        """
        Calcula tamanho da posição baseado no risco
        
        Args:
            symbol: Símbolo
            entry_price: Preço de entrada
            stop_loss: Stop Loss
            account_info: Info da conta
            risk_percent: Risco % (usa config se None)
            
        Returns:
            Volume/lots
        """
        equity = account_info.get("equity", 0)
        if equity <= 0:
            return 0.01  # Mínimo
        
        # Risco em %
        risk_pct = risk_percent or self._config.risk_per_trade
        risk_pct = min(risk_pct, self._config.max_risk_per_trade)
        
        # Valor em risco
        risk_amount = equity * (risk_pct / 100)
        
        # Distância do SL em pips
        sl_distance = abs(entry_price - stop_loss)
        
        # Pip value (simplificado)
        if "JPY" in symbol:
            pip_value = sl_distance / 0.01
        elif "XAU" in symbol:
            pip_value = sl_distance / 0.1
        else:
            pip_value = sl_distance / 0.0001
        
        if pip_value <= 0:
            return 0.01
        
        # Valor do pip por lote padrão
        pip_per_lot = 10  # $10 por pip para 1 lote padrão (simplificado)
        
        # Calcular lots
        lots = risk_amount / (pip_value * pip_per_lot)
        
        # Arredondar para step
        lots = round(lots, 2)
        
        # Limites
        lots = max(0.01, min(lots, 10.0))
        
        return lots
    
    # ==========================================================================
    # STOP LOSS
    # ==========================================================================
    
    def calculate_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        atr: Optional[float] = None,
        method: str = "atr"
    ) -> float:
        """
        Calcula Stop Loss
        
        Args:
            symbol: Símbolo
            entry_price: Preço de entrada
            direction: "buy" ou "sell"
            atr: ATR atual (para método ATR)
            method: "atr", "percent", "pips"
            
        Returns:
            Preço do SL
        """
        if method == "atr" and atr:
            multiplier = 2.0
            sl_distance = atr * multiplier
        elif method == "percent":
            sl_percent = 1.0  # 1%
            sl_distance = entry_price * (sl_percent / 100)
        else:  # pips
            sl_pips = 50
            if "JPY" in symbol:
                sl_distance = sl_pips * 0.01
            elif "XAU" in symbol:
                sl_distance = sl_pips * 0.1
            else:
                sl_distance = sl_pips * 0.0001
        
        if direction.lower() == "buy":
            return entry_price - sl_distance
        else:
            return entry_price + sl_distance
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Retorna relatório de risco"""
        return {
            "risk_level": self._state.risk_level.value,
            "total_positions": self._state.total_positions,
            "total_risk_percent": round(self._state.total_risk_percent, 2),
            "daily_pnl": round(self._state.daily_pnl, 2),
            "daily_trades": self._state.daily_trades,
            "current_drawdown": round(self._state.current_drawdown, 2),
            "positions_by_symbol": self._state.positions_by_symbol,
            "can_trade": self.can_trade,
            "limits": {
                "max_positions": self._config.max_positions,
                "max_daily_trades": self._config.max_daily_trades,
                "max_risk_per_trade": self._config.max_risk_per_trade,
                "max_total_risk": self._config.max_total_risk,
                "max_daily_loss": self._config.max_daily_loss,
                "max_drawdown": self._config.max_drawdown
            }
        }


# Singleton global
_risk_manager: Optional[RiskManager] = None


def get_risk_manager(config: RiskConfig = None) -> RiskManager:
    """Obtém instância global do RiskManager"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager(config)
    return _risk_manager
