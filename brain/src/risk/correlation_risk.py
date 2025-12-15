"""
VIRTUS Correlation Risk Manager
================================

Gerencia risco de correlação entre posições.
Previne concentração excessiva em ativos correlacionados.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger


class CorrelationLevel(Enum):
    """Nível de correlação entre ativos."""
    NONE = "none"          # |corr| < 0.2
    WEAK = "weak"          # 0.2 <= |corr| < 0.4
    MODERATE = "moderate"  # 0.4 <= |corr| < 0.6
    STRONG = "strong"      # 0.6 <= |corr| < 0.8
    VERY_STRONG = "very_strong"  # |corr| >= 0.8


@dataclass
class CorrelationEntry:
    """Entrada de correlação entre dois ativos."""
    symbol_a: str
    symbol_b: str
    correlation: float
    level: CorrelationLevel
    last_update: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pair': f"{self.symbol_a}/{self.symbol_b}",
            'correlation': round(self.correlation, 3),
            'level': self.level.value,
        }


@dataclass
class PositionExposure:
    """Exposição de uma posição."""
    symbol: str
    direction: str  # 'long' ou 'short'
    volume: float
    notional_value: float  # Valor em USD
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'volume': round(self.volume, 2),
            'notional': round(self.notional_value, 2),
        }


@dataclass
class CorrelationRiskMetrics:
    """Métricas de risco de correlação."""
    # Exposição total
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    
    # Correlação
    weighted_correlation: float = 0.0
    max_correlated_exposure: float = 0.0
    correlated_pairs: int = 0
    
    # Risk scores
    concentration_score: float = 0.0
    diversification_score: float = 0.0
    correlation_risk_score: float = 0.0
    
    # Alertas
    alerts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'gross_exposure': round(self.gross_exposure, 2),
            'net_exposure': round(self.net_exposure, 2),
            'weighted_correlation': round(self.weighted_correlation, 3),
            'max_correlated_exposure': round(self.max_correlated_exposure, 2),
            'correlated_pairs': self.correlated_pairs,
            'concentration_score': round(self.concentration_score, 2),
            'diversification_score': round(self.diversification_score, 2),
            'correlation_risk_score': round(self.correlation_risk_score, 2),
            'alerts': self.alerts,
        }


@dataclass
class CorrelationRiskConfig:
    """Configuração do gerenciador de correlação."""
    # Thresholds
    high_correlation_threshold: float = 0.7
    warning_correlation_threshold: float = 0.5
    
    # Limites de exposição
    max_correlated_exposure_pct: float = 50.0
    max_single_asset_pct: float = 30.0
    
    # Penalidades
    correlation_penalty_factor: float = 0.5  # Redução de volume para correlated
    
    # Atualização
    correlation_update_hours: int = 24


class CorrelationRiskManager:
    """
    Gerenciador de risco de correlação.
    
    Responsabilidades:
    - Monitorar correlações entre ativos
    - Calcular exposição correlacionada
    - Limitar concentração
    - Ajustar sizing por correlação
    """
    
    def __init__(self, config: Optional[CorrelationRiskConfig] = None):
        self.config = config or CorrelationRiskConfig()
        self.logger = VirtusLogger.get_logger("correlation_risk")
        
        # Matriz de correlação
        self._correlations: Dict[str, Dict[str, CorrelationEntry]] = {}
        
        # Posições atuais
        self._positions: Dict[str, PositionExposure] = {}
        
        # Métricas
        self.metrics = CorrelationRiskMetrics()
        
        # Correlações conhecidas (valores padrão)
        self._default_correlations = {
            ('XAUUSD', 'EURUSD'): 0.50,   # Ambos vs USD
            ('XAUUSD', 'GBPUSD'): 0.45,
            ('EURUSD', 'GBPUSD'): 0.75,   # Pares europeus
            ('XAUUSD', 'USDJPY'): -0.60,  # Ouro vs risk-on
            ('EURUSD', 'USDJPY'): -0.30,
        }
        
        self._initialize_default_correlations()
    
    def _initialize_default_correlations(self) -> None:
        """Inicializa correlações padrão."""
        for (sym_a, sym_b), corr in self._default_correlations.items():
            self._set_correlation(sym_a, sym_b, corr)
    
    def _set_correlation(
        self,
        symbol_a: str,
        symbol_b: str,
        correlation: float
    ) -> None:
        """Define correlação entre dois símbolos."""
        level = self._get_correlation_level(correlation)
        
        entry = CorrelationEntry(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            correlation=correlation,
            level=level,
            last_update=datetime.now(),
        )
        
        if symbol_a not in self._correlations:
            self._correlations[symbol_a] = {}
        if symbol_b not in self._correlations:
            self._correlations[symbol_b] = {}
        
        self._correlations[symbol_a][symbol_b] = entry
        self._correlations[symbol_b][symbol_a] = CorrelationEntry(
            symbol_a=symbol_b,
            symbol_b=symbol_a,
            correlation=correlation,
            level=level,
            last_update=datetime.now(),
        )
    
    def _get_correlation_level(self, correlation: float) -> CorrelationLevel:
        """Determina nível de correlação."""
        abs_corr = abs(correlation)
        
        if abs_corr >= 0.8:
            return CorrelationLevel.VERY_STRONG
        elif abs_corr >= 0.6:
            return CorrelationLevel.STRONG
        elif abs_corr >= 0.4:
            return CorrelationLevel.MODERATE
        elif abs_corr >= 0.2:
            return CorrelationLevel.WEAK
        return CorrelationLevel.NONE
    
    # ========================================================================
    # ATUALIZAÇÃO DE CORRELAÇÕES
    # ========================================================================
    
    async def update_correlations(
        self,
        correlations: Dict[str, Dict[str, float]]
    ) -> None:
        """
        Atualiza matriz de correlações.
        
        Args:
            correlations: Dict {symbol_a: {symbol_b: correlation}}
        """
        for symbol_a, pairs in correlations.items():
            for symbol_b, corr in pairs.items():
                if symbol_a != symbol_b:
                    self._set_correlation(symbol_a, symbol_b, corr)
        
        self.logger.debug(
            f"Correlações atualizadas para {len(self._correlations)} símbolos"
        )
    
    def get_correlation(
        self,
        symbol_a: str,
        symbol_b: str
    ) -> Optional[float]:
        """Obtém correlação entre dois símbolos."""
        if symbol_a in self._correlations:
            if symbol_b in self._correlations[symbol_a]:
                return self._correlations[symbol_a][symbol_b].correlation
        return None
    
    # ========================================================================
    # POSIÇÕES
    # ========================================================================
    
    async def update_position(
        self,
        symbol: str,
        direction: str,
        volume: float,
        notional_value: float
    ) -> None:
        """
        Atualiza ou adiciona posição.
        
        Args:
            symbol: Símbolo
            direction: 'long' ou 'short'
            volume: Volume
            notional_value: Valor em USD
        """
        if volume <= 0:
            # Remove posição
            if symbol in self._positions:
                del self._positions[symbol]
        else:
            self._positions[symbol] = PositionExposure(
                symbol=symbol,
                direction=direction,
                volume=volume,
                notional_value=notional_value,
            )
        
        # Recalcula métricas
        await self._calculate_metrics()
    
    async def clear_position(self, symbol: str) -> None:
        """Remove posição."""
        if symbol in self._positions:
            del self._positions[symbol]
            await self._calculate_metrics()
    
    # ========================================================================
    # CÁLCULO DE MÉTRICAS
    # ========================================================================
    
    async def _calculate_metrics(self) -> None:
        """Calcula todas as métricas de risco de correlação."""
        if not self._positions:
            self.metrics = CorrelationRiskMetrics()
            return
        
        # Exposição total
        gross_exposure = sum(p.notional_value for p in self._positions.values())
        
        # Exposição líquida (long - short)
        long_exposure = sum(
            p.notional_value for p in self._positions.values()
            if p.direction == 'long'
        )
        short_exposure = sum(
            p.notional_value for p in self._positions.values()
            if p.direction == 'short'
        )
        net_exposure = long_exposure - short_exposure
        
        # Calcula exposição correlacionada
        correlated_exposure = 0.0
        correlated_pairs = 0
        weighted_corr_sum = 0.0
        weight_sum = 0.0
        
        symbols = list(self._positions.keys())
        for i, sym_a in enumerate(symbols):
            for sym_b in symbols[i+1:]:
                corr = self.get_correlation(sym_a, sym_b)
                if corr is not None and abs(corr) > self.config.warning_correlation_threshold:
                    pos_a = self._positions[sym_a]
                    pos_b = self._positions[sym_b]
                    
                    # Exposição é maior se mesma direção e correlação positiva
                    # ou direção oposta e correlação negativa
                    same_direction = pos_a.direction == pos_b.direction
                    adds_risk = (same_direction and corr > 0) or (not same_direction and corr < 0)
                    
                    if adds_risk:
                        exposure = min(pos_a.notional_value, pos_b.notional_value) * abs(corr)
                        correlated_exposure += exposure
                        correlated_pairs += 1
                    
                    # Weighted correlation
                    weight = pos_a.notional_value + pos_b.notional_value
                    weighted_corr_sum += corr * weight
                    weight_sum += weight
        
        weighted_correlation = weighted_corr_sum / max(1, weight_sum)
        
        # Concentration score (HHI - Herfindahl-Hirschman Index)
        if gross_exposure > 0:
            weights = [p.notional_value / gross_exposure for p in self._positions.values()]
            hhi = sum(w**2 for w in weights)
            concentration_score = hhi * 100
        else:
            concentration_score = 0.0
        
        # Diversification score (inverso da concentração)
        n_positions = len(self._positions)
        if n_positions > 1:
            diversification_score = (1 - concentration_score / 100) * 100 * (n_positions / (n_positions + 1))
        else:
            diversification_score = 0.0
        
        # Correlation risk score (0-100)
        correlation_risk_score = min(100, (
            abs(weighted_correlation) * 30 +
            (correlated_exposure / max(1, gross_exposure)) * 50 +
            concentration_score * 0.2
        ))
        
        # Alertas
        alerts = []
        if correlated_exposure / max(1, gross_exposure) > self.config.max_correlated_exposure_pct / 100:
            alerts.append("Exposição correlacionada alta")
        
        max_single = max((p.notional_value for p in self._positions.values()), default=0)
        if max_single / max(1, gross_exposure) > self.config.max_single_asset_pct / 100:
            alerts.append("Concentração em único ativo")
        
        if abs(weighted_correlation) > self.config.high_correlation_threshold:
            alerts.append("Correlação média alta entre posições")
        
        self.metrics = CorrelationRiskMetrics(
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            weighted_correlation=weighted_correlation,
            max_correlated_exposure=correlated_exposure,
            correlated_pairs=correlated_pairs,
            concentration_score=concentration_score,
            diversification_score=diversification_score,
            correlation_risk_score=correlation_risk_score,
            alerts=alerts,
        )
    
    # ========================================================================
    # AJUSTE DE SIZING
    # ========================================================================
    
    def get_volume_adjustment(
        self,
        new_symbol: str,
        new_direction: str,
        base_volume: float
    ) -> Tuple[float, str]:
        """
        Calcula ajuste de volume baseado em correlação.
        
        Args:
            new_symbol: Símbolo da nova posição
            new_direction: Direção da nova posição
            base_volume: Volume base desejado
            
        Returns:
            (volume_ajustado, motivo)
        """
        if not self._positions:
            return base_volume, "Sem posições existentes"
        
        max_correlation = 0.0
        most_correlated = None
        
        for symbol, position in self._positions.items():
            corr = self.get_correlation(new_symbol, symbol)
            if corr is None:
                continue
            
            # Verifica se adiciona risco
            same_direction = new_direction == position.direction
            adds_risk = (same_direction and corr > 0) or (not same_direction and corr < 0)
            
            if adds_risk and abs(corr) > max_correlation:
                max_correlation = abs(corr)
                most_correlated = symbol
        
        if max_correlation > self.config.high_correlation_threshold:
            # Alta correlação - reduz significativamente
            adjustment = 1 - (max_correlation * self.config.correlation_penalty_factor)
            adjusted_volume = base_volume * adjustment
            return adjusted_volume, f"Alta correlação com {most_correlated}: {max_correlation:.2f}"
        
        elif max_correlation > self.config.warning_correlation_threshold:
            # Correlação moderada - reduz um pouco
            adjustment = 1 - (max_correlation * self.config.correlation_penalty_factor * 0.5)
            adjusted_volume = base_volume * adjustment
            return adjusted_volume, f"Correlação moderada com {most_correlated}: {max_correlation:.2f}"
        
        return base_volume, "Sem correlação significativa"
    
    def can_add_position(
        self,
        new_symbol: str,
        new_notional: float
    ) -> Tuple[bool, str]:
        """
        Verifica se pode adicionar posição.
        
        Args:
            new_symbol: Símbolo da nova posição
            new_notional: Valor notional
            
        Returns:
            (permitido, motivo)
        """
        # Concentração em único ativo
        if new_symbol in self._positions:
            current = self._positions[new_symbol].notional_value
            total = self.metrics.gross_exposure + new_notional
            if (current + new_notional) / total > self.config.max_single_asset_pct / 100:
                return False, f"Excederia concentração máxima em {new_symbol}"
        
        # Exposição correlacionada
        potential_correlated = self._calculate_potential_correlated_exposure(
            new_symbol, new_notional
        )
        new_total = self.metrics.gross_exposure + new_notional
        
        if potential_correlated / max(1, new_total) > self.config.max_correlated_exposure_pct / 100:
            return False, "Excederia limite de exposição correlacionada"
        
        return True, "OK"
    
    def _calculate_potential_correlated_exposure(
        self,
        new_symbol: str,
        new_notional: float
    ) -> float:
        """Calcula potencial exposição correlacionada com nova posição."""
        correlated = self.metrics.max_correlated_exposure
        
        for symbol, position in self._positions.items():
            corr = self.get_correlation(new_symbol, symbol)
            if corr is not None and abs(corr) > self.config.warning_correlation_threshold:
                correlated += min(new_notional, position.notional_value) * abs(corr)
        
        return correlated
    
    # ========================================================================
    # CONSULTAS
    # ========================================================================
    
    def get_metrics(self) -> CorrelationRiskMetrics:
        """Retorna métricas atuais."""
        return self.metrics
    
    def get_correlated_symbols(self, symbol: str) -> List[Dict[str, Any]]:
        """Lista símbolos correlacionados com o dado."""
        correlated = []
        
        if symbol in self._correlations:
            for sym, entry in self._correlations[symbol].items():
                if abs(entry.correlation) > self.config.warning_correlation_threshold:
                    correlated.append(entry.to_dict())
        
        return sorted(correlated, key=lambda x: abs(x['correlation']), reverse=True)
    
    def get_portfolio_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """Retorna matriz de correlação das posições atuais."""
        symbols = list(self._positions.keys())
        matrix = {}
        
        for sym_a in symbols:
            matrix[sym_a] = {}
            for sym_b in symbols:
                if sym_a == sym_b:
                    matrix[sym_a][sym_b] = 1.0
                else:
                    corr = self.get_correlation(sym_a, sym_b)
                    matrix[sym_a][sym_b] = corr if corr is not None else 0.0
        
        return matrix
