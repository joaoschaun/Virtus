"""
VIRTUS Strategy Factory
========================

Factory completa para criação e gerenciamento de estratégias.
Inclui auto-registro, validação e configuração dinâmica.
"""

from datetime import datetime
from typing import Dict, Optional, Type, List, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
import importlib
import inspect
from pathlib import Path

try:
    from ..core import VirtusLogger
    from ..core.types import Signal, SignalDirection, Timeframe
except ImportError:
    from core import VirtusLogger
    from core.types import Signal, SignalDirection, Timeframe


class StrategyCategory(Enum):
    """Categorias de estratégias."""
    TREND = "trend"
    SCALPING = "scalping"
    REVERSAL = "reversal"
    EVENT = "event"
    BREAKOUT = "breakout"
    MEAN_REVERSION = "mean_reversion"
    HYBRID = "hybrid"


class StrategyStatus(Enum):
    """Status da estratégia."""
    ACTIVE = "active"
    PAUSED = "paused"
    TESTING = "testing"
    DEPRECATED = "deprecated"


@dataclass
class StrategyInfo:
    """Informações sobre uma estratégia registrada."""
    name: str
    class_ref: Type
    category: StrategyCategory
    symbols: List[str]           # Símbolos suportados (* = todos)
    timeframes: List[str]        # Timeframes recomendados
    status: StrategyStatus = StrategyStatus.ACTIVE
    
    # Metadata
    version: str = "1.0.0"
    author: str = "VIRTUS"
    description: str = ""
    
    # Performance
    min_confidence: float = 0.6
    min_risk_reward: float = 1.5
    max_daily_trades: int = 10
    
    # Registro
    registered_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'category': self.category.value,
            'symbols': self.symbols,
            'timeframes': self.timeframes,
            'status': self.status.value,
            'version': self.version,
            'description': self.description,
            'min_confidence': self.min_confidence,
            'min_risk_reward': self.min_risk_reward,
            'max_daily_trades': self.max_daily_trades,
        }


@dataclass 
class StrategyConfig:
    """Configuração dinâmica para instância de estratégia."""
    symbol: str
    timeframe: str = "M15"
    
    # Risk
    risk_percent: float = 1.0
    max_positions: int = 3
    
    # Filters
    min_confidence: float = 0.6
    min_risk_reward: float = 2.0
    
    # Session
    allowed_sessions: List[str] = field(default_factory=lambda: ["london", "new_york"])
    
    # Custom parameters
    params: Dict[str, Any] = field(default_factory=dict)


class StrategyRegistry:
    """
    Registro central de estratégias.
    
    Responsável por:
    - Armazenar referências às classes de estratégia
    - Validar compatibilidade símbolo/timeframe
    - Gerenciar status das estratégias
    """
    
    def __init__(self):
        self._strategies: Dict[str, StrategyInfo] = {}
        self._by_category: Dict[StrategyCategory, List[str]] = {
            cat: [] for cat in StrategyCategory
        }
        self._by_symbol: Dict[str, Set[str]] = {}
        self.logger = VirtusLogger.get_logger("strategy_registry")
    
    def register(
        self,
        strategy_class: Type,
        name: Optional[str] = None,
        category: StrategyCategory = StrategyCategory.HYBRID,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        **kwargs
    ) -> bool:
        """
        Registra uma estratégia.
        
        Args:
            strategy_class: Classe da estratégia
            name: Nome (usa classe se não fornecido)
            category: Categoria
            symbols: Símbolos suportados
            timeframes: Timeframes recomendados
            **kwargs: Metadata adicional
            
        Returns:
            True se registrada com sucesso
        """
        name = name or strategy_class.__name__
        
        if name in self._strategies:
            self.logger.warning(f"Estratégia {name} já registrada, sobrescrevendo")
        
        symbols = symbols or ["*"]
        timeframes = timeframes or ["M15", "H1"]
        
        info = StrategyInfo(
            name=name,
            class_ref=strategy_class,
            category=category,
            symbols=symbols,
            timeframes=timeframes,
            version=kwargs.get('version', '1.0.0'),
            author=kwargs.get('author', 'VIRTUS'),
            description=kwargs.get('description', strategy_class.__doc__ or ''),
            min_confidence=kwargs.get('min_confidence', 0.6),
            min_risk_reward=kwargs.get('min_risk_reward', 1.5),
            max_daily_trades=kwargs.get('max_daily_trades', 10),
        )
        
        self._strategies[name] = info
        
        # Indexa por categoria
        if name not in self._by_category[category]:
            self._by_category[category].append(name)
        
        # Indexa por símbolo
        for symbol in symbols:
            if symbol not in self._by_symbol:
                self._by_symbol[symbol] = set()
            self._by_symbol[symbol].add(name)
        
        self.logger.info(f"Estratégia registrada: {name} [{category.value}]")
        return True
    
    def unregister(self, name: str) -> bool:
        """Remove uma estratégia do registro."""
        if name not in self._strategies:
            return False
        
        info = self._strategies[name]
        
        # Remove dos índices
        if name in self._by_category[info.category]:
            self._by_category[info.category].remove(name)
        
        for symbol in info.symbols:
            if symbol in self._by_symbol:
                self._by_symbol[symbol].discard(name)
        
        del self._strategies[name]
        self.logger.info(f"Estratégia removida: {name}")
        return True
    
    def get(self, name: str) -> Optional[StrategyInfo]:
        """Obtém info de uma estratégia."""
        return self._strategies.get(name)
    
    def get_class(self, name: str) -> Optional[Type]:
        """Obtém classe de uma estratégia."""
        info = self._strategies.get(name)
        return info.class_ref if info else None
    
    def list_all(self) -> List[str]:
        """Lista todas as estratégias."""
        return list(self._strategies.keys())
    
    def list_by_category(self, category: StrategyCategory) -> List[str]:
        """Lista estratégias por categoria."""
        return self._by_category.get(category, [])
    
    def list_by_symbol(self, symbol: str) -> List[str]:
        """Lista estratégias compatíveis com um símbolo."""
        compatible = set()
        
        # Estratégias específicas para o símbolo
        if symbol in self._by_symbol:
            compatible.update(self._by_symbol[symbol])
        
        # Estratégias universais (*)
        if "*" in self._by_symbol:
            compatible.update(self._by_symbol["*"])
        
        return list(compatible)
    
    def list_active(self) -> List[str]:
        """Lista estratégias ativas."""
        return [
            name for name, info in self._strategies.items()
            if info.status == StrategyStatus.ACTIVE
        ]
    
    def set_status(self, name: str, status: StrategyStatus) -> bool:
        """Altera status de uma estratégia."""
        if name in self._strategies:
            self._strategies[name].status = status
            self.logger.info(f"Status {name} -> {status.value}")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do registro."""
        return {
            'total': len(self._strategies),
            'by_category': {
                cat.value: len(names) 
                for cat, names in self._by_category.items()
            },
            'by_status': {
                status.value: len([
                    s for s in self._strategies.values() 
                    if s.status == status
                ])
                for status in StrategyStatus
            },
            'symbols_covered': len(self._by_symbol),
        }


# ============================================================================
# GLOBAL REGISTRY
# ============================================================================

_registry = StrategyRegistry()


def register_strategy(
    name: Optional[str] = None,
    category: StrategyCategory = StrategyCategory.HYBRID,
    symbols: Optional[List[str]] = None,
    timeframes: Optional[List[str]] = None,
    **kwargs
) -> Callable:
    """
    Decorator para registrar estratégias automaticamente.
    
    Uso:
        @register_strategy(
            name="TrendSMC",
            category=StrategyCategory.TREND,
            symbols=["XAUUSD", "EURUSD"],
            timeframes=["M15", "H1"]
        )
        class TrendStrategy(BaseStrategy):
            ...
    """
    def decorator(cls):
        _registry.register(
            strategy_class=cls,
            name=name,
            category=category,
            symbols=symbols,
            timeframes=timeframes,
            **kwargs
        )
        return cls
    return decorator


# ============================================================================
# STRATEGY FACTORY
# ============================================================================

class StrategyFactory:
    """
    Factory para criação de instâncias de estratégia.
    
    Responsabilidades:
    - Criar instâncias configuradas
    - Validar compatibilidade
    - Gerenciar ciclo de vida
    """
    
    def __init__(self, registry: Optional[StrategyRegistry] = None):
        self.registry = registry or _registry
        self.logger = VirtusLogger.get_logger("strategy_factory")
        
        # Cache de instâncias ativas
        self._instances: Dict[str, Any] = {}
        
        # Auto-discovery
        self._auto_discover()
    
    def _auto_discover(self) -> None:
        """
        Auto-descobre e registra estratégias dos módulos.
        """
        strategies_path = Path(__file__).parent
        
        # Módulos de estratégia
        strategy_modules = [
            ('trend', 'trend_strategy', 'TrendStrategy'),
            ('scalping', 'scalping_strategy', 'ScalpingStrategy'),
            ('reversal', 'reversal_strategy', 'ReversalStrategy'),
            ('event', 'event_strategy', 'EventStrategy'),
        ]
        
        for subdir, module_name, class_name in strategy_modules:
            try:
                module_path = f"src.strategies.{subdir}.{module_name}"
                module = importlib.import_module(module_path)
                
                strategy_class = getattr(module, class_name, None)
                if strategy_class:
                    # Determina categoria
                    category_map = {
                        'trend': StrategyCategory.TREND,
                        'scalping': StrategyCategory.SCALPING,
                        'reversal': StrategyCategory.REVERSAL,
                        'event': StrategyCategory.EVENT,
                    }
                    
                    self.registry.register(
                        strategy_class=strategy_class,
                        name=class_name,
                        category=category_map.get(subdir, StrategyCategory.HYBRID),
                        symbols=["*"],
                        timeframes=["M15", "H1", "H4"],
                    )
                    
            except ImportError as e:
                self.logger.debug(f"Módulo {subdir} não encontrado: {e}")
            except Exception as e:
                self.logger.warning(f"Erro ao descobrir {subdir}: {e}")
    
    def create(
        self,
        strategy_name: str,
        config: Optional[StrategyConfig] = None,
        symbol: Optional[str] = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Cria uma instância de estratégia.
        
        Args:
            strategy_name: Nome da estratégia
            config: Configuração
            symbol: Símbolo (se config não fornecido)
            **kwargs: Parâmetros adicionais
            
        Returns:
            Instância da estratégia ou None
        """
        info = self.registry.get(strategy_name)
        
        if not info:
            self.logger.error(f"Estratégia não encontrada: {strategy_name}")
            return None
        
        if info.status == StrategyStatus.DEPRECATED:
            self.logger.warning(f"Estratégia {strategy_name} está deprecated")
        
        # Configura
        if not config:
            config = StrategyConfig(symbol=symbol or "XAUUSD")
        
        # Valida compatibilidade de símbolo
        if config.symbol not in info.symbols and "*" not in info.symbols:
            self.logger.warning(
                f"Símbolo {config.symbol} não recomendado para {strategy_name}"
            )
        
        # Cria instância
        try:
            strategy_class = info.class_ref
            
            # Verifica parâmetros do construtor
            sig = inspect.signature(strategy_class.__init__)
            params = list(sig.parameters.keys())
            
            init_kwargs = {'symbol': config.symbol}
            
            # Adiciona parâmetros opcionais se aceitos
            if 'timeframe' in params:
                init_kwargs['timeframe'] = config.timeframe
            if 'config' in params:
                init_kwargs['config'] = config
            
            # Merge kwargs extras
            for key, value in kwargs.items():
                if key in params:
                    init_kwargs[key] = value
            
            instance = strategy_class(**init_kwargs)
            
            # Armazena referência
            instance_key = f"{strategy_name}_{config.symbol}"
            self._instances[instance_key] = instance
            
            self.logger.info(
                f"Estratégia criada: {strategy_name} para {config.symbol}"
            )
            return instance
            
        except Exception as e:
            self.logger.error(f"Erro criando {strategy_name}: {e}")
            return None
    
    def create_multiple(
        self,
        symbol: str,
        strategy_names: Optional[List[str]] = None,
        categories: Optional[List[StrategyCategory]] = None
    ) -> List[Any]:
        """
        Cria múltiplas estratégias para um símbolo.
        
        Args:
            symbol: Símbolo
            strategy_names: Lista de nomes específicos
            categories: Lista de categorias
            
        Returns:
            Lista de instâncias criadas
        """
        instances = []
        
        if strategy_names:
            names_to_create = strategy_names
        elif categories:
            names_to_create = []
            for cat in categories:
                names_to_create.extend(self.registry.list_by_category(cat))
        else:
            names_to_create = self.registry.list_by_symbol(symbol)
        
        for name in names_to_create:
            info = self.registry.get(name)
            if info and info.status == StrategyStatus.ACTIVE:
                instance = self.create(name, symbol=symbol)
                if instance:
                    instances.append(instance)
        
        self.logger.info(
            f"Criadas {len(instances)} estratégias para {symbol}"
        )
        return instances
    
    def get_instance(self, strategy_name: str, symbol: str) -> Optional[Any]:
        """Obtém instância existente."""
        key = f"{strategy_name}_{symbol}"
        return self._instances.get(key)
    
    def destroy_instance(self, strategy_name: str, symbol: str) -> bool:
        """Remove instância."""
        key = f"{strategy_name}_{symbol}"
        if key in self._instances:
            del self._instances[key]
            return True
        return False
    
    def destroy_all(self, symbol: Optional[str] = None) -> int:
        """Remove todas as instâncias (opcionalmente por símbolo)."""
        count = 0
        keys_to_remove = []
        
        for key in self._instances:
            if symbol is None or key.endswith(f"_{symbol}"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._instances[key]
            count += 1
        
        return count
    
    def list_instances(self) -> Dict[str, List[str]]:
        """Lista instâncias ativas por símbolo."""
        result: Dict[str, List[str]] = {}
        
        for key in self._instances:
            parts = key.rsplit('_', 1)
            if len(parts) == 2:
                strategy_name, symbol = parts
                if symbol not in result:
                    result[symbol] = []
                result[symbol].append(strategy_name)
        
        return result


# ============================================================================
# STRATEGY COMBINER
# ============================================================================

class StrategyCombiner:
    """
    Combina sinais de múltiplas estratégias.
    
    Métodos de combinação:
    - UNANIMOUS: Todas devem concordar
    - MAJORITY: Maioria vence
    - WEIGHTED: Ponderado por performance
    - BEST_CONFIDENCE: Melhor confiança
    """
    
    class CombineMethod(Enum):
        UNANIMOUS = "unanimous"
        MAJORITY = "majority"
        WEIGHTED = "weighted"
        BEST_CONFIDENCE = "best_confidence"
    
    def __init__(self, method: CombineMethod = None):
        self.method = method or self.CombineMethod.MAJORITY
        self.logger = VirtusLogger.get_logger("strategy_combiner")
        
        # Pesos para método WEIGHTED
        self.weights: Dict[str, float] = {}
    
    def set_weight(self, strategy_name: str, weight: float) -> None:
        """Define peso para uma estratégia."""
        self.weights[strategy_name] = max(0.0, min(2.0, weight))
    
    async def combine_signals(
        self,
        signals: List[Dict[str, Any]],
        min_confidence: float = 0.6
    ) -> Optional[Dict[str, Any]]:
        """
        Combina múltiplos sinais.
        
        Args:
            signals: Lista de sinais de diferentes estratégias
            min_confidence: Confiança mínima para considerar
            
        Returns:
            Sinal combinado ou None se não há consenso
        """
        if not signals:
            return None
        
        # Filtra por confiança mínima
        valid_signals = [
            s for s in signals 
            if s.get('confidence', 0) >= min_confidence
        ]
        
        if not valid_signals:
            return None
        
        if self.method == self.CombineMethod.UNANIMOUS:
            return self._combine_unanimous(valid_signals)
        elif self.method == self.CombineMethod.MAJORITY:
            return self._combine_majority(valid_signals)
        elif self.method == self.CombineMethod.WEIGHTED:
            return self._combine_weighted(valid_signals)
        else:
            return self._combine_best_confidence(valid_signals)
    
    def _combine_unanimous(
        self, signals: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Todas as estratégias devem concordar."""
        if len(signals) < 2:
            return signals[0] if signals else None
        
        # Verifica direção
        directions = set(s.get('direction') for s in signals)
        if len(directions) != 1:
            self.logger.debug("Não há unanimidade nas direções")
            return None
        
        # Usa médias para preços
        avg_confidence = sum(s.get('confidence', 0) for s in signals) / len(signals)
        avg_entry = sum(s.get('entry', 0) for s in signals) / len(signals)
        
        # SL mais conservador (mais longe)
        direction = signals[0].get('direction')
        if direction == 'buy':
            sl = min(s.get('sl', float('inf')) for s in signals)
        else:
            sl = max(s.get('sl', 0) for s in signals)
        
        # TP mais conservador (mais perto)
        if direction == 'buy':
            tp = min(s.get('tp', float('inf')) for s in signals)
        else:
            tp = max(s.get('tp', 0) for s in signals)
        
        return {
            'direction': direction,
            'entry': avg_entry,
            'sl': sl,
            'tp': tp,
            'confidence': avg_confidence,
            'strategies': [s.get('strategy_name') for s in signals],
            'combination': 'unanimous',
        }
    
    def _combine_majority(
        self, signals: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Maioria das estratégias decide."""
        if not signals:
            return None
        
        # Conta direções
        buy_signals = [s for s in signals if s.get('direction') == 'buy']
        sell_signals = [s for s in signals if s.get('direction') == 'sell']
        
        if len(buy_signals) > len(sell_signals):
            winner_signals = buy_signals
            direction = 'buy'
        elif len(sell_signals) > len(buy_signals):
            winner_signals = sell_signals
            direction = 'sell'
        else:
            # Empate - usa maior confiança
            best_buy = max(buy_signals, key=lambda s: s.get('confidence', 0)) if buy_signals else None
            best_sell = max(sell_signals, key=lambda s: s.get('confidence', 0)) if sell_signals else None
            
            if best_buy and best_sell:
                if best_buy.get('confidence', 0) > best_sell.get('confidence', 0):
                    winner_signals = buy_signals
                    direction = 'buy'
                else:
                    winner_signals = sell_signals
                    direction = 'sell'
            elif best_buy:
                winner_signals = buy_signals
                direction = 'buy'
            else:
                winner_signals = sell_signals
                direction = 'sell'
        
        if not winner_signals:
            return None
        
        # Calcula médias
        avg_confidence = sum(s.get('confidence', 0) for s in winner_signals) / len(winner_signals)
        avg_entry = sum(s.get('entry', 0) for s in winner_signals) / len(winner_signals)
        
        if direction == 'buy':
            sl = min(s.get('sl', float('inf')) for s in winner_signals)
            tp = min(s.get('tp', float('inf')) for s in winner_signals)
        else:
            sl = max(s.get('sl', 0) for s in winner_signals)
            tp = max(s.get('tp', 0) for s in winner_signals)
        
        return {
            'direction': direction,
            'entry': avg_entry,
            'sl': sl,
            'tp': tp,
            'confidence': avg_confidence,
            'strategies': [s.get('strategy_name') for s in winner_signals],
            'vote_count': len(winner_signals),
            'total_signals': len(signals),
            'combination': 'majority',
        }
    
    def _combine_weighted(
        self, signals: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Combinação ponderada por peso das estratégias."""
        if not signals:
            return None
        
        # Calcula scores ponderados por direção
        buy_score = 0.0
        sell_score = 0.0
        
        for signal in signals:
            strategy_name = signal.get('strategy_name', '')
            weight = self.weights.get(strategy_name, 1.0)
            confidence = signal.get('confidence', 0.5)
            
            score = weight * confidence
            
            if signal.get('direction') == 'buy':
                buy_score += score
            else:
                sell_score += score
        
        # Decide direção
        if buy_score > sell_score:
            direction = 'buy'
            winner_signals = [s for s in signals if s.get('direction') == 'buy']
        else:
            direction = 'sell'
            winner_signals = [s for s in signals if s.get('direction') == 'sell']
        
        if not winner_signals:
            return None
        
        # Média ponderada
        total_weight = sum(
            self.weights.get(s.get('strategy_name', ''), 1.0) 
            for s in winner_signals
        )
        
        weighted_entry = sum(
            s.get('entry', 0) * self.weights.get(s.get('strategy_name', ''), 1.0)
            for s in winner_signals
        ) / total_weight
        
        weighted_confidence = sum(
            s.get('confidence', 0) * self.weights.get(s.get('strategy_name', ''), 1.0)
            for s in winner_signals
        ) / total_weight
        
        if direction == 'buy':
            sl = min(s.get('sl', float('inf')) for s in winner_signals)
            tp = min(s.get('tp', float('inf')) for s in winner_signals)
        else:
            sl = max(s.get('sl', 0) for s in winner_signals)
            tp = max(s.get('tp', 0) for s in winner_signals)
        
        return {
            'direction': direction,
            'entry': weighted_entry,
            'sl': sl,
            'tp': tp,
            'confidence': weighted_confidence,
            'strategies': [s.get('strategy_name') for s in winner_signals],
            'buy_score': round(buy_score, 3),
            'sell_score': round(sell_score, 3),
            'combination': 'weighted',
        }
    
    def _combine_best_confidence(
        self, signals: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Usa o sinal com maior confiança."""
        if not signals:
            return None
        
        best = max(signals, key=lambda s: s.get('confidence', 0))
        
        return {
            **best,
            'combination': 'best_confidence',
        }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Registry
    'StrategyRegistry',
    'StrategyInfo',
    'StrategyCategory',
    'StrategyStatus',
    # Factory
    'StrategyFactory',
    'StrategyConfig',
    # Combiner
    'StrategyCombiner',
    # Decorator
    'register_strategy',
    # Global registry
    '_registry',
]
