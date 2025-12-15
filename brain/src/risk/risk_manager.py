"""
VIRTUS Risk Manager
====================

Gerenciamento de risco centralizado.
"""

import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import math

from ..core import Config, VirtusLogger, RiskConfig
from ..core.exceptions import RiskError


class RiskLevel(Enum):
    """Níveis de risco."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class RiskMetrics:
    """Métricas de risco."""
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    daily_loss: float = 0.0
    weekly_loss: float = 0.0
    open_positions: int = 0
    total_exposure: float = 0.0
    exposure_by_symbol: Dict[str, float] = field(default_factory=dict)
    correlation_exposure: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    risk_level: RiskLevel = RiskLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'current_drawdown': round(self.current_drawdown, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'daily_loss': round(self.daily_loss, 2),
            'weekly_loss': round(self.weekly_loss, 2),
            'open_positions': self.open_positions,
            'total_exposure': round(self.total_exposure, 4),
            'exposure_by_symbol': {k: round(v, 4) for k, v in self.exposure_by_symbol.items()},
            'correlation_exposure': round(self.correlation_exposure, 4),
            'var_95': round(self.var_95, 2),
            'risk_level': self.risk_level.name,
        }


@dataclass
class PositionSizing:
    """Resultado do cálculo de tamanho de posição."""
    volume: float
    risk_amount: float
    risk_percent: float
    stop_loss_pips: float
    max_loss: float
    allowed: bool
    reason: str = ""


class RiskManager:
    """
    Gerenciador de risco centralizado.
    
    Responsabilidades:
    - Cálculo de tamanho de posição
    - Monitoramento de drawdown
    - Controle de exposição
    - Circuit breakers
    - Limites por símbolo e geral
    """
    
    _instance: Optional['RiskManager'] = None
    
    def __init__(self, config: RiskConfig):
        self.config = config
        self.logger = VirtusLogger.get_logger("risk")
        
        # Métricas
        self.metrics = RiskMetrics()
        
        # Controle
        self._balance: float = 0.0
        self._equity: float = 0.0
        self._initial_balance: float = 0.0
        
        # Histórico de trades
        self._daily_trades: List[Dict] = []
        self._weekly_trades: List[Dict] = []
        
        # Limites
        self._max_daily_loss_pct = config.max_daily_loss_pct
        self._max_weekly_loss_pct = config.max_weekly_loss_pct
        self._max_total_exposure = config.max_total_exposure
        self._max_symbol_exposure = config.max_symbol_exposure
        self._max_correlated_exposure = config.max_correlated_exposure
        self._max_positions = config.max_positions
        self._default_risk_per_trade = config.risk_per_trade
        
        # Correlações entre pares (simplificado)
        self._correlations = {
            ('EURUSD', 'GBPUSD'): 0.85,
            ('EURUSD', 'XAUUSD'): 0.40,
            ('GBPUSD', 'XAUUSD'): 0.35,
        }
        
        # Circuit breaker
        self._circuit_breaker_active = False
        self._circuit_breaker_until: Optional[datetime] = None
        
        # Lock para thread-safety
        self._lock = asyncio.Lock()
        
        RiskManager._instance = self
    
    @classmethod
    def get_instance(cls) -> Optional['RiskManager']:
        """Obtém instância singleton."""
        return cls._instance
    
    async def update_account(self, balance: float, equity: float) -> None:
        """Atualiza informações da conta."""
        async with self._lock:
            if self._initial_balance == 0:
                self._initial_balance = balance
            
            self._balance = balance
            self._equity = equity
            
            # Atualiza drawdown
            self._update_drawdown()
    
    def _update_drawdown(self) -> None:
        """Atualiza cálculo de drawdown."""
        if self._initial_balance > 0:
            self.metrics.current_drawdown = (
                (self._initial_balance - self._equity) / self._initial_balance * 100
            )
            
            if self.metrics.current_drawdown > self.metrics.max_drawdown:
                self.metrics.max_drawdown = self.metrics.current_drawdown
            
            # Atualiza nível de risco
            self._update_risk_level()
    
    def _update_risk_level(self) -> None:
        """Atualiza nível de risco baseado nas métricas."""
        dd = self.metrics.current_drawdown
        
        if dd >= self._max_daily_loss_pct:
            self.metrics.risk_level = RiskLevel.CRITICAL
        elif dd >= self._max_daily_loss_pct * 0.7:
            self.metrics.risk_level = RiskLevel.HIGH
        elif dd >= self._max_daily_loss_pct * 0.4:
            self.metrics.risk_level = RiskLevel.MEDIUM
        else:
            self.metrics.risk_level = RiskLevel.LOW
    
    async def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        risk_percent: Optional[float] = None,
    ) -> PositionSizing:
        """
        Calcula tamanho da posição baseado no risco.
        
        Args:
            symbol: Símbolo a operar
            entry_price: Preço de entrada
            stop_loss: Preço do stop loss
            risk_percent: Percentual de risco (opcional, usa default)
            
        Returns:
            PositionSizing com detalhes do cálculo
        """
        async with self._lock:
            # Verifica circuit breaker
            if not await self._check_can_trade(symbol):
                return PositionSizing(
                    volume=0,
                    risk_amount=0,
                    risk_percent=0,
                    stop_loss_pips=0,
                    max_loss=0,
                    allowed=False,
                    reason="Circuit breaker ativo ou limite atingido"
                )
            
            # Usa risco padrão se não especificado
            risk_pct = risk_percent or self._default_risk_per_trade
            
            # Ajusta risco baseado no nível atual
            adjusted_risk = self._adjust_risk_for_conditions(risk_pct)
            
            # Calcula distância do stop em pips
            sl_distance = abs(entry_price - stop_loss)
            sl_pips = self._price_to_pips(symbol, sl_distance)
            
            if sl_pips <= 0:
                return PositionSizing(
                    volume=0,
                    risk_amount=0,
                    risk_percent=0,
                    stop_loss_pips=0,
                    max_loss=0,
                    allowed=False,
                    reason="Stop loss inválido"
                )
            
            # Calcula valor de risco
            risk_amount = self._balance * (adjusted_risk / 100)
            
            # Calcula valor do pip para o símbolo
            pip_value = self._get_pip_value(symbol, entry_price)
            
            # Calcula lote
            if pip_value > 0:
                volume = risk_amount / (sl_pips * pip_value)
            else:
                volume = 0.01  # Mínimo
            
            # Normaliza lote
            volume = self._normalize_volume(symbol, volume)
            
            # Verifica limites de exposição
            exposure_ok, exposure_reason = self._check_exposure(symbol, volume)
            
            if not exposure_ok:
                return PositionSizing(
                    volume=0,
                    risk_amount=risk_amount,
                    risk_percent=adjusted_risk,
                    stop_loss_pips=sl_pips,
                    max_loss=risk_amount,
                    allowed=False,
                    reason=exposure_reason
                )
            
            return PositionSizing(
                volume=volume,
                risk_amount=risk_amount,
                risk_percent=adjusted_risk,
                stop_loss_pips=sl_pips,
                max_loss=volume * sl_pips * pip_value,
                allowed=True,
                reason="OK"
            )
    
    def _adjust_risk_for_conditions(self, base_risk: float) -> float:
        """Ajusta risco baseado nas condições atuais."""
        adjusted = base_risk
        
        # Reduz risco se drawdown alto
        if self.metrics.current_drawdown > self._max_daily_loss_pct * 0.5:
            adjusted *= 0.5
        elif self.metrics.current_drawdown > self._max_daily_loss_pct * 0.3:
            adjusted *= 0.75
        
        # Reduz risco se muitas posições abertas
        if self.metrics.open_positions >= self._max_positions * 0.7:
            adjusted *= 0.75
        
        # Reduz risco baseado no nível
        risk_multipliers = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MEDIUM: 0.8,
            RiskLevel.HIGH: 0.5,
            RiskLevel.CRITICAL: 0.25,
        }
        adjusted *= risk_multipliers.get(self.metrics.risk_level, 1.0)
        
        return max(adjusted, 0.1)  # Mínimo 0.1%
    
    def _price_to_pips(self, symbol: str, price_diff: float) -> float:
        """Converte diferença de preço para pips."""
        # Determina multiplicador baseado no símbolo
        if 'JPY' in symbol:
            multiplier = 100  # 2 decimais
        elif 'XAU' in symbol:
            multiplier = 10  # 2 decimais para ouro
        else:
            multiplier = 10000  # 4 decimais para forex
        
        return abs(price_diff * multiplier)
    
    def _get_pip_value(self, symbol: str, price: float) -> float:
        """Calcula valor do pip para o símbolo."""
        # Valores aproximados por lote padrão
        pip_values = {
            'EURUSD': 10.0,
            'GBPUSD': 10.0,
            'XAUUSD': 1.0,  # Por pip em ouro
            # Adicionar mais conforme necessário
        }
        
        return pip_values.get(symbol, 10.0)
    
    def _normalize_volume(self, symbol: str, volume: float) -> float:
        """Normaliza volume para incrementos válidos."""
        min_lot = 0.01
        max_lot = 100.0
        lot_step = 0.01
        
        # Para ouro, pode ter limites diferentes
        if 'XAU' in symbol:
            min_lot = 0.01
            max_lot = 50.0
        
        # Arredonda para step
        volume = round(volume / lot_step) * lot_step
        
        # Aplica limites
        volume = max(min_lot, min(volume, max_lot))
        
        return round(volume, 2)
    
    def _check_exposure(self, symbol: str, volume: float) -> Tuple[bool, str]:
        """Verifica limites de exposição."""
        # Exposição do símbolo
        current_exposure = self.metrics.exposure_by_symbol.get(symbol, 0)
        new_exposure = current_exposure + volume
        
        if new_exposure > self._max_symbol_exposure:
            return False, f"Exposição máxima no {symbol} atingida"
        
        # Exposição total
        total = self.metrics.total_exposure + volume
        if total > self._max_total_exposure:
            return False, "Exposição total máxima atingida"
        
        # Exposição correlacionada
        corr_exposure = self._calculate_correlated_exposure(symbol, volume)
        if corr_exposure > self._max_correlated_exposure:
            return False, "Exposição correlacionada máxima atingida"
        
        return True, "OK"
    
    def _calculate_correlated_exposure(self, symbol: str, volume: float) -> float:
        """Calcula exposição em pares correlacionados."""
        exposure = volume
        
        for (sym1, sym2), correlation in self._correlations.items():
            if symbol == sym1 and sym2 in self.metrics.exposure_by_symbol:
                exposure += self.metrics.exposure_by_symbol[sym2] * correlation
            elif symbol == sym2 and sym1 in self.metrics.exposure_by_symbol:
                exposure += self.metrics.exposure_by_symbol[sym1] * correlation
        
        return exposure
    
    async def _check_can_trade(self, symbol: str) -> bool:
        """Verifica se pode operar."""
        # Circuit breaker
        if self._circuit_breaker_active:
            if self._circuit_breaker_until and datetime.now() < self._circuit_breaker_until:
                return False
            else:
                self._circuit_breaker_active = False
        
        # Verifica limite de posições
        if self.metrics.open_positions >= self._max_positions:
            return False
        
        # Verifica perda diária
        if self.metrics.daily_loss >= self._max_daily_loss_pct:
            await self._activate_circuit_breaker("Limite de perda diária atingido")
            return False
        
        # Verifica drawdown crítico
        if self.metrics.current_drawdown >= self._max_daily_loss_pct:
            await self._activate_circuit_breaker("Drawdown crítico")
            return False
        
        return True
    
    async def _activate_circuit_breaker(self, reason: str, duration_hours: int = 4) -> None:
        """Ativa circuit breaker."""
        self._circuit_breaker_active = True
        self._circuit_breaker_until = datetime.now() + timedelta(hours=duration_hours)
        
        self.logger.warning(
            f"🚨 Circuit Breaker ATIVADO: {reason} "
            f"(até {self._circuit_breaker_until.strftime('%H:%M')})"
        )
    
    async def register_trade_result(
        self,
        symbol: str,
        profit: float,
        volume: float,
        direction: str,
    ) -> None:
        """Registra resultado de um trade."""
        async with self._lock:
            trade_info = {
                'symbol': symbol,
                'profit': profit,
                'volume': volume,
                'direction': direction,
                'timestamp': datetime.now(),
            }
            
            self._daily_trades.append(trade_info)
            self._weekly_trades.append(trade_info)
            
            # Atualiza perda diária
            if profit < 0:
                loss_pct = abs(profit) / self._balance * 100 if self._balance > 0 else 0
                self.metrics.daily_loss += loss_pct
            
            # Atualiza exposição (remove posição fechada)
            if symbol in self.metrics.exposure_by_symbol:
                self.metrics.exposure_by_symbol[symbol] -= volume
                if self.metrics.exposure_by_symbol[symbol] <= 0:
                    del self.metrics.exposure_by_symbol[symbol]
            
            self.metrics.total_exposure -= volume
            if self.metrics.total_exposure < 0:
                self.metrics.total_exposure = 0
            
            self.metrics.open_positions = max(0, self.metrics.open_positions - 1)
    
    async def register_position_opened(self, symbol: str, volume: float) -> None:
        """Registra abertura de posição."""
        async with self._lock:
            self.metrics.open_positions += 1
            self.metrics.total_exposure += volume
            
            if symbol not in self.metrics.exposure_by_symbol:
                self.metrics.exposure_by_symbol[symbol] = 0
            self.metrics.exposure_by_symbol[symbol] += volume
    
    async def reset_daily_stats(self) -> None:
        """Reseta estatísticas diárias."""
        async with self._lock:
            self.metrics.daily_loss = 0
            self._daily_trades = []
            self.logger.info("📊 Estatísticas diárias resetadas")
    
    async def reset_weekly_stats(self) -> None:
        """Reseta estatísticas semanais."""
        async with self._lock:
            self.metrics.weekly_loss = 0
            self._weekly_trades = []
            self.logger.info("📊 Estatísticas semanais resetadas")
    
    def can_trade(self, symbol: str) -> bool:
        """Verificação síncrona se pode operar."""
        if self._circuit_breaker_active:
            return False
        if self.metrics.open_positions >= self._max_positions:
            return False
        if self.metrics.daily_loss >= self._max_daily_loss_pct:
            return False
        return True
    
    def get_metrics(self) -> RiskMetrics:
        """Retorna métricas atuais."""
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do gerenciador de risco."""
        return {
            'balance': self._balance,
            'equity': self._equity,
            'circuit_breaker_active': self._circuit_breaker_active,
            'circuit_breaker_until': (
                self._circuit_breaker_until.isoformat() 
                if self._circuit_breaker_until else None
            ),
            'metrics': self.metrics.to_dict(),
            'limits': {
                'max_daily_loss_pct': self._max_daily_loss_pct,
                'max_weekly_loss_pct': self._max_weekly_loss_pct,
                'max_total_exposure': self._max_total_exposure,
                'max_symbol_exposure': self._max_symbol_exposure,
                'max_positions': self._max_positions,
                'default_risk_per_trade': self._default_risk_per_trade,
            },
        }


# Factory function
def get_risk_manager() -> Optional[RiskManager]:
    """Obtém instância do gerenciador de risco."""
    return RiskManager.get_instance()
