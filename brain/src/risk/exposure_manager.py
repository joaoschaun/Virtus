"""
VIRTUS Exposure Manager
========================

Gerenciamento detalhado de exposição de mercado.
Controla alocação por símbolo, setor e tipo de ativo.

Features:
- Tracking de exposição por símbolo, classe e correlação
- Verificação de limites com ajustes dinâmicos
- Alocação de capital inteligente
- Hedging management com correlation-aware exposure
- Event system para alertas de violação de limites
- Contribution to portfolio risk

Classes Principais:
- ExposureManager: Gerenciador principal de exposição
- SymbolExposure: Exposição detalhada por símbolo
- ExposureMetrics: Métricas globais de exposição
- ClassExposure: Exposição agregada por classe
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
import math

try:
    from ..core import VirtusLogger
except ImportError:
    from core import VirtusLogger


# =============================================================================
# ENUMS
# =============================================================================

class AssetClass(Enum):
    """Classe de ativo."""
    FOREX_MAJOR = "forex_major"
    FOREX_MINOR = "forex_minor"
    FOREX_EXOTIC = "forex_exotic"
    COMMODITY = "commodity"
    INDEX = "index"
    CRYPTO = "crypto"


class ExposureType(Enum):
    """Tipo de exposição."""
    LONG = "long"
    SHORT = "short"
    HEDGED = "hedged"


class ExposureEvent(Enum):
    """Eventos de exposição para callbacks."""
    LIMIT_WARNING = "limit_warning"      # Atingiu 80% do limite
    LIMIT_BREACH = "limit_breach"        # Violou limite
    CONCENTRATION_HIGH = "concentration" # Alta concentração
    CORRELATION_RISK = "correlation"     # Risco de correlação
    HEDGE_IMBALANCE = "hedge_imbalance"  # Hedge desbalanceado


class VolatilityRegime(Enum):
    """Regime de volatilidade do mercado."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class SymbolExposure:
    """Exposição de um símbolo."""
    symbol: str
    asset_class: AssetClass
    
    # Volumes
    long_volume: float = 0.0
    short_volume: float = 0.0
    net_volume: float = 0.0
    
    # Valores (USD)
    long_notional: float = 0.0
    short_notional: float = 0.0
    net_notional: float = 0.0
    
    # P&L
    unrealized_pnl: float = 0.0
    realized_pnl_today: float = 0.0
    
    # Posições
    long_positions: int = 0
    short_positions: int = 0
    
    # Limites
    max_exposure_pct: float = 0.0  # Percentual do portfólio
    
    # Risk contribution (novo)
    var_contribution: float = 0.0  # Contribuição ao VaR do portfolio
    beta_to_portfolio: float = 1.0  # Beta em relação ao portfolio
    
    # Timestamps (novo)
    first_position_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'asset_class': self.asset_class.value,
            'long_volume': round(self.long_volume, 2),
            'short_volume': round(self.short_volume, 2),
            'net_volume': round(self.net_volume, 2),
            'net_notional': round(self.net_notional, 2),
            'unrealized_pnl': round(self.unrealized_pnl, 2),
            'positions': self.long_positions + self.short_positions,
            'var_contribution': round(self.var_contribution, 4),
            'beta': round(self.beta_to_portfolio, 2),
        }
    
    @property
    def gross_volume(self) -> float:
        return self.long_volume + abs(self.short_volume)
    
    @property
    def gross_notional(self) -> float:
        return self.long_notional + abs(self.short_notional)
    
    @property
    def exposure_type(self) -> ExposureType:
        if abs(self.long_notional - abs(self.short_notional)) < max(self.long_notional, abs(self.short_notional)) * 0.1:
            return ExposureType.HEDGED
        return ExposureType.LONG if self.net_notional >= 0 else ExposureType.SHORT
    
    @property
    def hedge_ratio(self) -> float:
        """Ratio de hedge (short/long)."""
        if self.long_notional == 0:
            return float('inf') if self.short_notional > 0 else 0.0
        return abs(self.short_notional) / self.long_notional


@dataclass
class ClassExposure:
    """Exposição agregada por classe de ativo."""
    asset_class: AssetClass
    symbols: List[str]
    
    # Totais
    gross_notional: float = 0.0
    net_notional: float = 0.0
    total_positions: int = 0
    
    # P&L
    unrealized_pnl: float = 0.0
    
    # Percentual do portfólio
    allocation_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'asset_class': self.asset_class.value,
            'symbols': self.symbols,
            'gross_notional': round(self.gross_notional, 2),
            'net_notional': round(self.net_notional, 2),
            'positions': self.total_positions,
            'allocation_pct': round(self.allocation_pct, 2),
        }


@dataclass
class ExposureMetrics:
    """Métricas globais de exposição."""
    # Totais
    total_long_notional: float = 0.0
    total_short_notional: float = 0.0
    gross_notional: float = 0.0
    net_notional: float = 0.0
    
    # Percentuais (do equity)
    gross_exposure_pct: float = 0.0
    net_exposure_pct: float = 0.0
    long_exposure_pct: float = 0.0
    short_exposure_pct: float = 0.0
    
    # Contagens
    total_positions: int = 0
    long_positions: int = 0
    short_positions: int = 0
    
    # P&L
    total_unrealized: float = 0.0
    total_realized_today: float = 0.0
    
    # Por classe
    by_class: Dict[str, float] = field(default_factory=dict)
    
    # Limites
    available_exposure: float = 0.0  # Quanto ainda pode expor
    
    # Métricas avançadas (novo)
    concentration_index: float = 0.0  # HHI (0-1, maior = mais concentrado)
    effective_positions: float = 0.0  # 1/HHI (quantos ativos "efetivos")
    portfolio_var: float = 0.0  # VaR estimado do portfolio
    correlation_adjusted_exposure: float = 0.0  # Exposição ajustada por correlação
    hedge_effectiveness: float = 0.0  # Efetividade do hedge (0-100%)
    
    # Status
    regime: VolatilityRegime = VolatilityRegime.NORMAL
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'gross_notional': round(self.gross_notional, 2),
            'net_notional': round(self.net_notional, 2),
            'gross_exposure_pct': round(self.gross_exposure_pct, 2),
            'net_exposure_pct': round(self.net_exposure_pct, 2),
            'total_positions': self.total_positions,
            'total_unrealized': round(self.total_unrealized, 2),
            'by_class': {k: round(v, 2) for k, v in self.by_class.items()},
            'available_exposure': round(self.available_exposure, 2),
            'concentration_index': round(self.concentration_index, 4),
            'effective_positions': round(self.effective_positions, 2),
            'portfolio_var': round(self.portfolio_var, 2),
            'correlation_adjusted': round(self.correlation_adjusted_exposure, 2),
            'hedge_effectiveness': round(self.hedge_effectiveness, 2),
            'regime': self.regime.value,
            'warnings': self.warnings,
        }


@dataclass
class ExposureConfig:
    """Configuração do gerenciador de exposição."""
    # Limites globais (% do equity)
    max_gross_exposure_pct: float = 100.0
    max_net_exposure_pct: float = 50.0
    max_long_exposure_pct: float = 80.0
    max_short_exposure_pct: float = 80.0
    
    # Limites por símbolo
    max_single_symbol_pct: float = 25.0
    max_positions_per_symbol: int = 3
    
    # Limites por classe
    max_class_exposure_pct: Dict[AssetClass, float] = field(default_factory=lambda: {
        AssetClass.FOREX_MAJOR: 60.0,
        AssetClass.FOREX_MINOR: 40.0,
        AssetClass.FOREX_EXOTIC: 20.0,
        AssetClass.COMMODITY: 40.0,
        AssetClass.INDEX: 30.0,
        AssetClass.CRYPTO: 10.0,
    })
    
    # Hedging
    allow_hedging: bool = True
    max_hedge_ratio: float = 1.0  # Ratio max short/long
    
    # Limites dinâmicos (novo)
    dynamic_limits_enabled: bool = True
    volatility_multipliers: Dict[VolatilityRegime, float] = field(default_factory=lambda: {
        VolatilityRegime.LOW: 1.2,
        VolatilityRegime.NORMAL: 1.0,
        VolatilityRegime.HIGH: 0.7,
        VolatilityRegime.EXTREME: 0.4,
    })
    
    # Concentration limits (novo)
    max_concentration_index: float = 0.4  # HHI máximo (0.4 = ~2.5 ativos efetivos)
    min_effective_positions: float = 2.0  # Mínimo de ativos efetivos
    
    # Correlation adjustments (novo)
    correlation_penalty: float = 0.2  # Penalidade para ativos correlacionados
    warning_threshold_pct: float = 80.0  # % do limite para gerar warning


@dataclass 
class CorrelationPair:
    """Par de correlação entre símbolos."""
    symbol1: str
    symbol2: str
    correlation: float  # -1 a 1
    
    @property
    def is_highly_correlated(self) -> bool:
        return abs(self.correlation) > 0.7
    
    @property
    def is_hedging(self) -> bool:
        return self.correlation < -0.5


class ExposureManager:
    """
    Gerenciador de exposição de mercado.
    
    Responsabilidades:
    - Tracking de exposição por símbolo/classe
    - Verificação de limites com ajustes dinâmicos
    - Alocação de capital
    - Hedging management
    - Correlation-aware exposure monitoring
    - Event-driven alerts
    
    Uso:
        manager = ExposureManager()
        await manager.set_equity(10000)
        await manager.add_position("EURUSD", "long", 0.1, 1000)
        
        can_add, reason = manager.can_add_exposure("GBPUSD", "long", 2000)
        if can_add:
            await manager.add_position("GBPUSD", "long", 0.2, 2000)
    """
    
    # Correlações conhecidas entre pares
    KNOWN_CORRELATIONS = [
        CorrelationPair("EURUSD", "GBPUSD", 0.85),
        CorrelationPair("EURUSD", "USDCHF", -0.90),
        CorrelationPair("GBPUSD", "GBPJPY", 0.75),
        CorrelationPair("AUDUSD", "NZDUSD", 0.90),
        CorrelationPair("XAUUSD", "USDCHF", -0.60),
        CorrelationPair("XAUUSD", "EURUSD", 0.40),
        CorrelationPair("USDJPY", "US100", 0.65),
    ]
    
    def __init__(
        self, 
        config: Optional[ExposureConfig] = None,
        event_callback: Optional[Callable[[ExposureEvent, Dict[str, Any]], None]] = None,
    ):
        """
        Inicializa ExposureManager.
        
        Args:
            config: Configuração de limites
            event_callback: Callback para eventos (warnings, breaches)
        """
        self.config = config or ExposureConfig()
        self.logger = VirtusLogger.get_logger("exposure_manager")
        
        # Callback para eventos
        self._event_callback = event_callback
        
        # Exposição por símbolo
        self._symbols: Dict[str, SymbolExposure] = {}
        
        # Classificação de símbolos
        self._symbol_classes = self._build_symbol_classes()
        
        # Correlações como dict para lookup rápido
        self._correlations = self._build_correlation_map()
        
        # Equity para cálculos
        self._equity: float = 0.0
        
        # Regime atual de volatilidade
        self._volatility_regime = VolatilityRegime.NORMAL
        
        # Métricas
        self.metrics = ExposureMetrics()
        
        # Histórico de eventos
        self._event_history: List[Tuple[datetime, ExposureEvent, Dict[str, Any]]] = []
    
    def _build_symbol_classes(self) -> Dict[str, AssetClass]:
        """Constrói mapeamento de símbolos para classes."""
        return {
            # Forex Major
            'EURUSD': AssetClass.FOREX_MAJOR,
            'GBPUSD': AssetClass.FOREX_MAJOR,
            'USDJPY': AssetClass.FOREX_MAJOR,
            'USDCHF': AssetClass.FOREX_MAJOR,
            'AUDUSD': AssetClass.FOREX_MAJOR,
            'USDCAD': AssetClass.FOREX_MAJOR,
            'NZDUSD': AssetClass.FOREX_MAJOR,
            # Forex Minor
            'EURGBP': AssetClass.FOREX_MINOR,
            'EURJPY': AssetClass.FOREX_MINOR,
            'GBPJPY': AssetClass.FOREX_MINOR,
            'AUDJPY': AssetClass.FOREX_MINOR,
            # Commodities
            'XAUUSD': AssetClass.COMMODITY,
            'XAGUSD': AssetClass.COMMODITY,
            'USOIL': AssetClass.COMMODITY,
            'UKOIL': AssetClass.COMMODITY,
            # Índices
            'US30': AssetClass.INDEX,
            'US500': AssetClass.INDEX,
            'US100': AssetClass.INDEX,
            'GER40': AssetClass.INDEX,
            # Crypto
            'BTCUSD': AssetClass.CRYPTO,
            'ETHUSD': AssetClass.CRYPTO,
        }
    
    def _build_correlation_map(self) -> Dict[str, Dict[str, float]]:
        """Constrói mapa de correlações para lookup rápido."""
        corr_map: Dict[str, Dict[str, float]] = {}
        
        for pair in self.KNOWN_CORRELATIONS:
            if pair.symbol1 not in corr_map:
                corr_map[pair.symbol1] = {}
            if pair.symbol2 not in corr_map:
                corr_map[pair.symbol2] = {}
            
            corr_map[pair.symbol1][pair.symbol2] = pair.correlation
            corr_map[pair.symbol2][pair.symbol1] = pair.correlation
        
        return corr_map
    
    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Obtém correlação entre dois símbolos."""
        if symbol1 == symbol2:
            return 1.0
        return self._correlations.get(symbol1, {}).get(symbol2, 0.0)
    
    def get_asset_class(self, symbol: str) -> AssetClass:
        """Obtém classe de um símbolo."""
        return self._symbol_classes.get(symbol, AssetClass.FOREX_EXOTIC)
    
    # ========================================================================
    # ATUALIZAÇÃO
    # ========================================================================
    
    async def set_equity(self, equity: float) -> None:
        """Define equity para cálculos percentuais."""
        self._equity = equity
        await self._recalculate_metrics()
    
    async def set_volatility_regime(self, regime: VolatilityRegime) -> None:
        """
        Define regime de volatilidade para ajustar limites.
        
        Args:
            regime: Regime atual de volatilidade
        """
        old_regime = self._volatility_regime
        self._volatility_regime = regime
        
        if old_regime != regime:
            self.logger.info(f"Regime de volatilidade: {old_regime.value} -> {regime.value}")
            await self._recalculate_metrics()
    
    def _get_adjusted_limit(self, base_limit: float) -> float:
        """Obtém limite ajustado pelo regime de volatilidade."""
        if not self.config.dynamic_limits_enabled:
            return base_limit
        
        multiplier = self.config.volatility_multipliers.get(
            self._volatility_regime, 
            1.0
        )
        return base_limit * multiplier
    
    async def add_position(
        self,
        symbol: str,
        direction: str,  # 'long' ou 'short'
        volume: float,
        notional: float,
        unrealized_pnl: float = 0.0
    ) -> None:
        """
        Adiciona ou atualiza posição.
        
        Args:
            symbol: Símbolo
            direction: 'long' ou 'short'
            volume: Volume
            notional: Valor em USD
            unrealized_pnl: P&L não realizado
        """
        now = datetime.now()
        
        if symbol not in self._symbols:
            self._symbols[symbol] = SymbolExposure(
                symbol=symbol,
                asset_class=self.get_asset_class(symbol),
                first_position_time=now,
            )
        
        exp = self._symbols[symbol]
        exp.last_update_time = now
        
        if direction == 'long':
            exp.long_volume += volume
            exp.long_notional += notional
            exp.long_positions += 1
        else:
            exp.short_volume += volume
            exp.short_notional += notional
            exp.short_positions += 1
        
        exp.net_volume = exp.long_volume - exp.short_volume
        exp.net_notional = exp.long_notional - exp.short_notional
        exp.unrealized_pnl += unrealized_pnl
        
        await self._recalculate_metrics()
        await self._check_and_emit_events()
    
    async def remove_position(
        self,
        symbol: str,
        direction: str,
        volume: float,
        notional: float,
        realized_pnl: float = 0.0
    ) -> None:
        """Remove posição fechada."""
        if symbol not in self._symbols:
            return
        
        exp = self._symbols[symbol]
        
        if direction == 'long':
            exp.long_volume = max(0, exp.long_volume - volume)
            exp.long_notional = max(0, exp.long_notional - notional)
            exp.long_positions = max(0, exp.long_positions - 1)
        else:
            exp.short_volume = max(0, exp.short_volume - volume)
            exp.short_notional = max(0, exp.short_notional - notional)
            exp.short_positions = max(0, exp.short_positions - 1)
        
        exp.net_volume = exp.long_volume - exp.short_volume
        exp.net_notional = exp.long_notional - exp.short_notional
        exp.realized_pnl_today += realized_pnl
        
        # Remove se sem posições
        if exp.long_positions == 0 and exp.short_positions == 0:
            del self._symbols[symbol]
        
        await self._recalculate_metrics()
    
    async def update_unrealized_pnl(
        self,
        symbol: str,
        unrealized_pnl: float
    ) -> None:
        """Atualiza P&L não realizado de um símbolo."""
        if symbol in self._symbols:
            self._symbols[symbol].unrealized_pnl = unrealized_pnl
            await self._recalculate_metrics()
    
    async def clear_all(self) -> None:
        """Limpa todas as exposições."""
        self._symbols.clear()
        self.metrics = ExposureMetrics()
    
    # ========================================================================
    # CÁLCULO DE MÉTRICAS
    # ========================================================================
    
    async def _recalculate_metrics(self) -> None:
        """Recalcula todas as métricas."""
        total_long = sum(e.long_notional for e in self._symbols.values())
        total_short = sum(e.short_notional for e in self._symbols.values())
        gross = total_long + total_short
        net = total_long - total_short
        
        total_unrealized = sum(e.unrealized_pnl for e in self._symbols.values())
        total_realized = sum(e.realized_pnl_today for e in self._symbols.values())
        
        long_positions = sum(e.long_positions for e in self._symbols.values())
        short_positions = sum(e.short_positions for e in self._symbols.values())
        
        # Percentuais
        equity = max(1, self._equity)
        
        # Por classe
        by_class: Dict[str, float] = {}
        for exp in self._symbols.values():
            class_name = exp.asset_class.value
            by_class[class_name] = by_class.get(class_name, 0) + exp.gross_notional
        
        # Available exposure (ajustado por volatilidade)
        max_gross_adj = self._get_adjusted_limit(self.config.max_gross_exposure_pct) * equity / 100
        available = max(0, max_gross_adj - gross)
        
        # ====== MÉTRICAS AVANÇADAS ======
        
        # Concentration Index (HHI - Herfindahl-Hirschman Index)
        concentration = self._calculate_concentration_index(gross)
        effective_positions = 1.0 / concentration if concentration > 0 else 0.0
        
        # Portfolio VaR contribution
        portfolio_var = self._estimate_portfolio_var(equity)
        
        # Correlation-adjusted exposure
        corr_adjusted = self._calculate_correlation_adjusted_exposure(gross)
        
        # Hedge effectiveness
        hedge_eff = self._calculate_hedge_effectiveness(total_long, total_short)
        
        # Warnings
        warnings = self._generate_warnings(gross, equity, concentration)
        
        self.metrics = ExposureMetrics(
            total_long_notional=total_long,
            total_short_notional=total_short,
            gross_notional=gross,
            net_notional=net,
            gross_exposure_pct=(gross / equity) * 100,
            net_exposure_pct=(net / equity) * 100,
            long_exposure_pct=(total_long / equity) * 100,
            short_exposure_pct=(total_short / equity) * 100,
            total_positions=long_positions + short_positions,
            long_positions=long_positions,
            short_positions=short_positions,
            total_unrealized=total_unrealized,
            total_realized_today=total_realized,
            by_class=by_class,
            available_exposure=available,
            concentration_index=concentration,
            effective_positions=effective_positions,
            portfolio_var=portfolio_var,
            correlation_adjusted_exposure=corr_adjusted,
            hedge_effectiveness=hedge_eff,
            regime=self._volatility_regime,
            warnings=warnings,
        )
    
    def _calculate_concentration_index(self, gross: float) -> float:
        """
        Calcula índice de concentração Herfindahl-Hirschman.
        
        Returns:
            HHI entre 0 (diversificado) e 1 (concentrado)
        """
        if gross <= 0 or not self._symbols:
            return 0.0
        
        hhi = sum(
            (exp.gross_notional / gross) ** 2 
            for exp in self._symbols.values()
        )
        return hhi
    
    def _estimate_portfolio_var(self, equity: float, confidence: float = 0.95) -> float:
        """
        Estima VaR do portfolio considerando correlações.
        
        Usa aproximação simplificada baseada em:
        - Volatilidades típicas por classe de ativo
        - Correlações conhecidas
        
        Args:
            equity: Equity base
            confidence: Nível de confiança (default 95%)
            
        Returns:
            VaR estimado em USD
        """
        if not self._symbols:
            return 0.0
        
        # Volatilidades diárias típicas por classe (%)
        vol_by_class = {
            AssetClass.FOREX_MAJOR: 0.5,
            AssetClass.FOREX_MINOR: 0.7,
            AssetClass.FOREX_EXOTIC: 1.2,
            AssetClass.COMMODITY: 1.5,
            AssetClass.INDEX: 1.0,
            AssetClass.CRYPTO: 4.0,
        }
        
        # Multiplier para confidence level
        z_score = 1.645 if confidence == 0.95 else 2.326  # 95% or 99%
        
        # Volatilidade ponderada do portfolio
        total_notional = sum(exp.gross_notional for exp in self._symbols.values())
        if total_notional <= 0:
            return 0.0
        
        weighted_var_sq = 0.0
        symbols_list = list(self._symbols.values())
        
        for i, exp_i in enumerate(symbols_list):
            vol_i = vol_by_class.get(exp_i.asset_class, 1.0) / 100
            weight_i = exp_i.gross_notional / total_notional
            
            # Variância própria
            weighted_var_sq += (weight_i * vol_i) ** 2
            
            # Covariâncias
            for j, exp_j in enumerate(symbols_list[i+1:], i+1):
                vol_j = vol_by_class.get(exp_j.asset_class, 1.0) / 100
                weight_j = exp_j.gross_notional / total_notional
                corr = self.get_correlation(exp_i.symbol, exp_j.symbol)
                
                weighted_var_sq += 2 * weight_i * weight_j * vol_i * vol_j * corr
        
        portfolio_vol = math.sqrt(max(0, weighted_var_sq))
        var = total_notional * portfolio_vol * z_score
        
        return var
    
    def _calculate_correlation_adjusted_exposure(self, gross: float) -> float:
        """
        Calcula exposição ajustada por correlação.
        
        Ativos correlacionados aumentam exposição efetiva.
        
        Returns:
            Exposição ajustada
        """
        if gross <= 0 or len(self._symbols) < 2:
            return gross
        
        penalty = 0.0
        symbols_list = list(self._symbols.keys())
        
        for i, sym1 in enumerate(symbols_list):
            for sym2 in symbols_list[i+1:]:
                corr = abs(self.get_correlation(sym1, sym2))
                
                if corr > 0.7:  # Alta correlação
                    # Penalidade proporcional à correlação e tamanho
                    exp1 = self._symbols[sym1].gross_notional
                    exp2 = self._symbols[sym2].gross_notional
                    combined = min(exp1, exp2)
                    
                    penalty += combined * (corr - 0.5) * self.config.correlation_penalty
        
        return gross + penalty
    
    def _calculate_hedge_effectiveness(self, total_long: float, total_short: float) -> float:
        """
        Calcula efetividade do hedge.
        
        100% = perfeitamente hedgeado
        0% = sem hedge
        
        Returns:
            Porcentagem de efetividade
        """
        if total_long == 0 and total_short == 0:
            return 0.0
        
        gross = total_long + total_short
        if gross == 0:
            return 0.0
        
        # Quanto do menor lado está "coberto" pelo maior
        hedged = min(total_long, total_short) * 2
        effectiveness = (hedged / gross) * 100
        
        return effectiveness
    
    def _generate_warnings(
        self, 
        gross: float, 
        equity: float, 
        concentration: float
    ) -> List[str]:
        """Gera lista de warnings atuais."""
        warnings = []
        
        # Warning de exposição
        gross_pct = (gross / equity) * 100
        max_gross_adj = self._get_adjusted_limit(self.config.max_gross_exposure_pct)
        
        if gross_pct >= max_gross_adj * 0.8:
            warnings.append(f"Exposição gross em {gross_pct:.1f}% (limite: {max_gross_adj:.1f}%)")
        
        # Warning de concentração
        if concentration > self.config.max_concentration_index:
            warnings.append(f"Alta concentração (HHI: {concentration:.2f})")
        
        # Warning de regime de volatilidade
        if self._volatility_regime in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME]:
            warnings.append(f"Regime de volatilidade: {self._volatility_regime.value}")
        
        return warnings
    
    async def _check_and_emit_events(self) -> None:
        """Verifica condições e emite eventos se necessário."""
        if not self._event_callback:
            return
        
        equity = max(1, self._equity)
        
        # Check limit warning (80%)
        gross_pct = self.metrics.gross_exposure_pct
        max_adj = self._get_adjusted_limit(self.config.max_gross_exposure_pct)
        
        if gross_pct >= max_adj * 0.8:
            self._emit_event(
                ExposureEvent.LIMIT_WARNING,
                {'current_pct': gross_pct, 'limit_pct': max_adj}
            )
        
        # Check concentration
        if self.metrics.concentration_index > self.config.max_concentration_index:
            self._emit_event(
                ExposureEvent.CONCENTRATION_HIGH,
                {'hhi': self.metrics.concentration_index}
            )
        
        # Check correlation risk
        if self.metrics.correlation_adjusted_exposure > self.metrics.gross_notional * 1.2:
            self._emit_event(
                ExposureEvent.CORRELATION_RISK,
                {'adjusted': self.metrics.correlation_adjusted_exposure}
            )
    
    def _emit_event(self, event: ExposureEvent, data: Dict[str, Any]) -> None:
        """Emite evento para callback."""
        now = datetime.now()
        self._event_history.append((now, event, data))
        
        # Limita histórico a 100 eventos
        if len(self._event_history) > 100:
            self._event_history = self._event_history[-100:]
        
        if self._event_callback:
            try:
                self._event_callback(event, data)
            except Exception as e:
                self.logger.error(f"Erro ao emitir evento {event}: {e}")
    
    # ========================================================================
    # VERIFICAÇÃO DE LIMITES
    # ========================================================================
    
    def can_add_exposure(
        self,
        symbol: str,
        direction: str,
        notional: float
    ) -> tuple[bool, str]:
        """
        Verifica se pode adicionar exposição.
        
        Considera:
        - Limites globais ajustados por volatilidade
        - Limites por símbolo e classe
        - Correlações com posições existentes
        - Concentração do portfolio
        
        Args:
            symbol: Símbolo
            direction: 'long' ou 'short'
            notional: Valor em USD
            
        Returns:
            (permitido, motivo)
        """
        equity = max(1, self._equity)
        
        # Exposição gross (ajustada por volatilidade)
        max_gross = self._get_adjusted_limit(self.config.max_gross_exposure_pct)
        new_gross = self.metrics.gross_notional + notional
        if (new_gross / equity) * 100 > max_gross:
            return False, f"Excederia exposição gross máxima ({max_gross:.1f}%)"
        
        # Exposição por direção
        if direction == 'long':
            max_long = self._get_adjusted_limit(self.config.max_long_exposure_pct)
            new_long = self.metrics.total_long_notional + notional
            if (new_long / equity) * 100 > max_long:
                return False, f"Excederia exposição long máxima ({max_long:.1f}%)"
        else:
            max_short = self._get_adjusted_limit(self.config.max_short_exposure_pct)
            new_short = self.metrics.total_short_notional + notional
            if (new_short / equity) * 100 > max_short:
                return False, f"Excederia exposição short máxima ({max_short:.1f}%)"
        
        # Exposição por símbolo
        if symbol in self._symbols:
            current = self._symbols[symbol].gross_notional
            if ((current + notional) / equity) * 100 > self.config.max_single_symbol_pct:
                return False, f"Excederia concentração máxima em {symbol}"
            
            # Posições por símbolo
            positions = self._symbols[symbol].long_positions + self._symbols[symbol].short_positions
            if positions >= self.config.max_positions_per_symbol:
                return False, f"Limite de posições em {symbol}"
        
        # Exposição por classe
        asset_class = self.get_asset_class(symbol)
        class_limit = self.config.max_class_exposure_pct.get(asset_class, 100)
        class_limit_adj = self._get_adjusted_limit(class_limit)
        current_class = self.metrics.by_class.get(asset_class.value, 0)
        
        if ((current_class + notional) / equity) * 100 > class_limit_adj:
            return False, f"Excederia limite para {asset_class.value} ({class_limit_adj:.1f}%)"
        
        # Verificação de correlação
        correlation_warning = self._check_correlation_risk(symbol, notional)
        if correlation_warning:
            return False, correlation_warning
        
        # Verificação de concentração
        new_concentration = self._estimate_new_concentration(symbol, notional)
        if new_concentration > self.config.max_concentration_index:
            return False, f"Excederia concentração máxima (HHI: {new_concentration:.2f})"
        
        return True, "OK"
    
    def _check_correlation_risk(self, symbol: str, notional: float) -> Optional[str]:
        """Verifica risco de correlação com posições existentes."""
        if len(self._symbols) == 0:
            return None
        
        # Verifica correlações altas
        for existing_symbol, exp in self._symbols.items():
            if existing_symbol == symbol:
                continue
            
            corr = abs(self.get_correlation(symbol, existing_symbol))
            
            if corr > 0.85:
                combined_notional = exp.gross_notional + notional
                equity = max(1, self._equity)
                combined_pct = (combined_notional / equity) * 100
                
                if combined_pct > self.config.max_single_symbol_pct:
                    return (
                        f"Alta correlação ({corr:.0%}) com {existing_symbol}. "
                        f"Exposição combinada: {combined_pct:.1f}%"
                    )
        
        return None
    
    def _estimate_new_concentration(self, symbol: str, notional: float) -> float:
        """Estima HHI se adicionar nova posição."""
        if notional <= 0:
            return self.metrics.concentration_index
        
        # Copia notionals atuais
        notionals = {s: exp.gross_notional for s, exp in self._symbols.items()}
        notionals[symbol] = notionals.get(symbol, 0) + notional
        
        gross = sum(notionals.values())
        if gross <= 0:
            return 0.0
        
        hhi = sum((n / gross) ** 2 for n in notionals.values())
        return hhi
    
    def get_max_allowed_notional(
        self,
        symbol: str,
        direction: str
    ) -> float:
        """
        Retorna máximo notional permitido.
        
        Considera todos os limites incluindo ajustes dinâmicos
        e restrições de correlação.
        
        Args:
            symbol: Símbolo
            direction: 'long' ou 'short'
            
        Returns:
            Máximo valor notional permitido
        """
        equity = max(1, self._equity)
        limits = []
        
        # Limite global (ajustado)
        max_gross = (self._get_adjusted_limit(self.config.max_gross_exposure_pct) / 100) * equity
        available_gross = max_gross - self.metrics.gross_notional
        limits.append(available_gross)
        
        # Limite por direção (ajustado)
        if direction == 'long':
            max_long = (self._get_adjusted_limit(self.config.max_long_exposure_pct) / 100) * equity
            available_long = max_long - self.metrics.total_long_notional
            limits.append(available_long)
        else:
            max_short = (self._get_adjusted_limit(self.config.max_short_exposure_pct) / 100) * equity
            available_short = max_short - self.metrics.total_short_notional
            limits.append(available_short)
        
        # Limite por símbolo
        max_symbol = (self.config.max_single_symbol_pct / 100) * equity
        current_symbol = self._symbols.get(symbol, SymbolExposure(symbol, AssetClass.FOREX_EXOTIC)).gross_notional
        available_symbol = max_symbol - current_symbol
        limits.append(available_symbol)
        
        # Limite por classe (ajustado)
        asset_class = self.get_asset_class(symbol)
        class_limit_pct = self.config.max_class_exposure_pct.get(asset_class, 100)
        max_class = (self._get_adjusted_limit(class_limit_pct) / 100) * equity
        current_class = self.metrics.by_class.get(asset_class.value, 0)
        available_class = max_class - current_class
        limits.append(available_class)
        
        # Limite por correlação
        corr_limit = self._get_correlation_limit(symbol, equity)
        if corr_limit is not None:
            limits.append(corr_limit)
        
        return max(0, min(limits))
    
    def _get_correlation_limit(self, symbol: str, equity: float) -> Optional[float]:
        """Calcula limite baseado em correlações existentes."""
        max_corr_exposure = float('inf')
        
        for existing_symbol, exp in self._symbols.items():
            if existing_symbol == symbol:
                continue
            
            corr = abs(self.get_correlation(symbol, existing_symbol))
            
            if corr > 0.7:
                # Limita exposição combinada
                max_combined = (self.config.max_single_symbol_pct / 100) * equity
                available = max_combined - exp.gross_notional
                max_corr_exposure = min(max_corr_exposure, available)
        
        return max_corr_exposure if max_corr_exposure != float('inf') else None
    
    # ========================================================================
    # CONSULTAS
    # ========================================================================
    
    def get_symbol_exposure(self, symbol: str) -> Optional[SymbolExposure]:
        """Retorna exposição de um símbolo."""
        return self._symbols.get(symbol)
    
    def get_all_exposures(self) -> Dict[str, SymbolExposure]:
        """Retorna todas as exposições."""
        return self._symbols.copy()
    
    def get_class_exposure(self, asset_class: AssetClass) -> ClassExposure:
        """Retorna exposição agregada de uma classe."""
        symbols = []
        gross = 0.0
        net = 0.0
        positions = 0
        unrealized = 0.0
        
        for exp in self._symbols.values():
            if exp.asset_class == asset_class:
                symbols.append(exp.symbol)
                gross += exp.gross_notional
                net += exp.net_notional
                positions += exp.long_positions + exp.short_positions
                unrealized += exp.unrealized_pnl
        
        allocation = (gross / max(1, self._equity)) * 100
        
        return ClassExposure(
            asset_class=asset_class,
            symbols=symbols,
            gross_notional=gross,
            net_notional=net,
            total_positions=positions,
            unrealized_pnl=unrealized,
            allocation_pct=allocation,
        )
    
    def get_metrics(self) -> ExposureMetrics:
        """Retorna métricas globais."""
        return self.metrics
    
    def get_exposure_summary(self) -> Dict[str, Any]:
        """Retorna resumo de exposição."""
        return {
            'metrics': self.metrics.to_dict(),
            'by_symbol': {
                s: e.to_dict() for s, e in self._symbols.items()
            },
            'by_class': {
                ac.value: self.get_class_exposure(ac).to_dict()
                for ac in AssetClass
                if self.metrics.by_class.get(ac.value, 0) > 0
            },
        }
    
    # ========================================================================
    # RESET
    # ========================================================================
    
    async def daily_reset(self) -> None:
        """Reset diário."""
        for exp in self._symbols.values():
            exp.realized_pnl_today = 0.0
        
        # Limpa histórico de eventos
        self._event_history.clear()
        
        self.logger.info("Reset diário de P&L e eventos realizado")
    
    # ========================================================================
    # CONSULTAS AVANÇADAS
    # ========================================================================
    
    def get_correlated_pairs(self, min_correlation: float = 0.7) -> List[Tuple[str, str, float]]:
        """
        Retorna pares de símbolos correlacionados nas posições atuais.
        
        Args:
            min_correlation: Correlação mínima (absoluta)
            
        Returns:
            Lista de (symbol1, symbol2, correlation)
        """
        result = []
        symbols = list(self._symbols.keys())
        
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                corr = self.get_correlation(sym1, sym2)
                if abs(corr) >= min_correlation:
                    result.append((sym1, sym2, corr))
        
        return sorted(result, key=lambda x: abs(x[2]), reverse=True)
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Retorna resumo de risco do portfolio."""
        equity = max(1, self._equity)
        
        return {
            'equity': round(equity, 2),
            'gross_exposure': round(self.metrics.gross_notional, 2),
            'gross_exposure_pct': round(self.metrics.gross_exposure_pct, 2),
            'net_exposure': round(self.metrics.net_notional, 2),
            'net_exposure_pct': round(self.metrics.net_exposure_pct, 2),
            'portfolio_var_95': round(self.metrics.portfolio_var, 2),
            'concentration_hhi': round(self.metrics.concentration_index, 4),
            'effective_positions': round(self.metrics.effective_positions, 2),
            'correlation_adjusted_exposure': round(self.metrics.correlation_adjusted_exposure, 2),
            'hedge_effectiveness_pct': round(self.metrics.hedge_effectiveness, 2),
            'volatility_regime': self._volatility_regime.value,
            'warnings': self.metrics.warnings,
            'correlated_pairs': self.get_correlated_pairs(0.7),
        }
    
    def get_event_history(
        self, 
        event_type: Optional[ExposureEvent] = None,
        since: Optional[datetime] = None
    ) -> List[Tuple[datetime, ExposureEvent, Dict[str, Any]]]:
        """
        Retorna histórico de eventos.
        
        Args:
            event_type: Filtrar por tipo de evento
            since: Filtrar eventos após esta data
            
        Returns:
            Lista de (timestamp, event, data)
        """
        result = self._event_history
        
        if event_type:
            result = [(t, e, d) for t, e, d in result if e == event_type]
        
        if since:
            result = [(t, e, d) for t, e, d in result if t >= since]
        
        return result
    
    def get_suggested_action(self) -> Optional[Dict[str, Any]]:
        """
        Sugere ação baseada no estado atual do portfolio.
        
        Returns:
            Dict com sugestão ou None se nenhuma ação necessária
        """
        suggestions = []
        
        # Alta concentração
        if self.metrics.concentration_index > self.config.max_concentration_index:
            suggestions.append({
                'type': 'diversify',
                'reason': f"Alta concentração (HHI: {self.metrics.concentration_index:.2f})",
                'suggestion': "Considere diversificar ou reduzir posições concentradas"
            })
        
        # Alta correlação
        correlated = self.get_correlated_pairs(0.8)
        if correlated:
            sym1, sym2, corr = correlated[0]
            suggestions.append({
                'type': 'correlation_risk',
                'reason': f"Alta correlação entre {sym1} e {sym2} ({corr:.0%})",
                'suggestion': "Considere fechar uma das posições ou usar como hedge"
            })
        
        # Regime de alta volatilidade
        if self._volatility_regime in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME]:
            suggestions.append({
                'type': 'reduce_exposure',
                'reason': f"Volatilidade {self._volatility_regime.value}",
                'suggestion': "Considere reduzir exposição ou apertar stops"
            })
        
        # Exposição perto do limite
        max_adj = self._get_adjusted_limit(self.config.max_gross_exposure_pct)
        if self.metrics.gross_exposure_pct >= max_adj * 0.9:
            suggestions.append({
                'type': 'near_limit',
                'reason': f"Exposição em {self.metrics.gross_exposure_pct:.1f}% (limite: {max_adj:.1f}%)",
                'suggestion': "Não abra novas posições ou considere reduzir"
            })
        
        return suggestions[0] if suggestions else None
