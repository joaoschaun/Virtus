"""
VIRTUS - Sistema de Plugins para Estratégias
=============================================

Arquitetura extensível para adicionar novas estratégias facilmente.
"""

import os
import sys
import importlib
import importlib.util
import inspect
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List, Type
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio

logger = logging.getLogger("virtus.plugins")


# ============================================================================
# BASE CLASSES
# ============================================================================

class SignalType(str, Enum):
    """Tipo de sinal."""
    BUY = "buy"
    SELL = "sell"
    CLOSE_BUY = "close_buy"
    CLOSE_SELL = "close_sell"
    HOLD = "hold"


@dataclass
class Signal:
    """Sinal de trading gerado por uma estratégia."""
    type: SignalType
    symbol: str
    strategy: str
    confidence: float = 0.0  # 0-100
    sl: Optional[float] = None
    tp: Optional[float] = None
    volume: Optional[float] = None
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "sl": self.sl,
            "tp": self.tp,
            "volume": self.volume,
            "reason": self.reason,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PluginInfo:
    """Informações do plugin."""
    name: str
    version: str
    author: str
    description: str
    symbols: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "symbols": self.symbols,
            "timeframes": self.timeframes,
        }


class StrategyPlugin(ABC):
    """
    Base class para estratégias de trading.
    
    Para criar uma nova estratégia:
    1. Herde de StrategyPlugin
    2. Implemente os métodos abstratos
    3. Coloque o arquivo em brain/src/strategies/plugins/
    
    Exemplo:
        class MyStrategy(StrategyPlugin):
            info = PluginInfo(
                name="MyStrategy",
                version="1.0.0",
                author="Your Name",
                description="Minha estratégia customizada",
                symbols=["XAUUSD", "EURUSD"],
                timeframes=["M15", "H1"]
            )
            
            async def analyze(self, symbol, timeframe, candles, indicators):
                # Sua lógica aqui
                return Signal(...)
    """
    
    # Informações do plugin - OVERRIDE THIS
    info: PluginInfo = PluginInfo(
        name="BaseStrategy",
        version="0.0.0",
        author="Unknown",
        description="Base strategy class",
    )
    
    def __init__(self):
        self._enabled = True
        self._config: Dict[str, Any] = {}
        self._last_signal: Optional[Signal] = None
        self._stats = {
            "signals_generated": 0,
            "buy_signals": 0,
            "sell_signals": 0,
        }
    
    @abstractmethod
    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        indicators: Dict[str, Any],
    ) -> Optional[Signal]:
        """
        Analisa o mercado e gera sinal.
        
        Args:
            symbol: Par/símbolo (ex: XAUUSD)
            timeframe: Timeframe (ex: M15, H1)
            candles: Lista de candles OHLCV
            indicators: Indicadores técnicos pré-calculados
            
        Returns:
            Signal ou None
        """
        pass
    
    @abstractmethod
    def get_default_config(self) -> Dict[str, Any]:
        """
        Retorna configuração padrão.
        
        Returns:
            Dict com parâmetros configuráveis
        """
        pass
    
    def configure(self, config: Dict[str, Any]):
        """Configura a estratégia."""
        self._config = {**self.get_default_config(), **config}
    
    def enable(self):
        """Habilita a estratégia."""
        self._enabled = True
    
    def disable(self):
        """Desabilita a estratégia."""
        self._enabled = False
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @property
    def config(self) -> Dict[str, Any]:
        return self._config
    
    @property
    def last_signal(self) -> Optional[Signal]:
        return self._last_signal
    
    def get_stats(self) -> Dict[str, Any]:
        return self._stats.copy()
    
    def _record_signal(self, signal: Signal):
        """Registra sinal nas estatísticas."""
        self._last_signal = signal
        self._stats["signals_generated"] += 1
        if signal.type == SignalType.BUY:
            self._stats["buy_signals"] += 1
        elif signal.type == SignalType.SELL:
            self._stats["sell_signals"] += 1


# ============================================================================
# PLUGIN MANAGER
# ============================================================================

class PluginManager:
    """
    Gerenciador de plugins de estratégias.
    
    Carrega automaticamente plugins do diretório:
    brain/src/strategies/plugins/
    
    Uso:
        manager = PluginManager()
        manager.load_plugins()
        
        # Lista plugins
        for name, plugin in manager.plugins.items():
            print(f"{name}: {plugin.info.description}")
        
        # Executa análise
        signals = await manager.run_analysis("XAUUSD", "H1", candles, indicators)
    """
    
    def __init__(self, plugins_dir: Optional[str] = None):
        self.plugins_dir = plugins_dir or self._default_plugins_dir()
        self.plugins: Dict[str, StrategyPlugin] = {}
        self._loaded = False
    
    def _default_plugins_dir(self) -> str:
        """Retorna diretório padrão de plugins."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "strategies", "plugins")
    
    def load_plugins(self) -> int:
        """
        Carrega todos os plugins do diretório.
        
        Returns:
            Número de plugins carregados
        """
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir, exist_ok=True)
            logger.info(f"Criado diretório de plugins: {self.plugins_dir}")
        
        loaded = 0
        
        for filename in os.listdir(self.plugins_dir):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            
            try:
                plugin = self._load_plugin_file(
                    os.path.join(self.plugins_dir, filename)
                )
                if plugin:
                    self.register_plugin(plugin)
                    loaded += 1
            except Exception as e:
                logger.error(f"Erro carregando plugin {filename}: {e}")
        
        self._loaded = True
        logger.info(f"🔌 {loaded} plugins carregados")
        return loaded
    
    def _load_plugin_file(self, filepath: str) -> Optional[StrategyPlugin]:
        """Carrega plugin de um arquivo."""
        module_name = os.path.basename(filepath).replace(".py", "")
        
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if not spec or not spec.loader:
            return None
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Encontra classe de estratégia
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, StrategyPlugin) and obj != StrategyPlugin:
                return obj()
        
        return None
    
    def register_plugin(self, plugin: StrategyPlugin):
        """Registra um plugin manualmente."""
        name = plugin.info.name
        self.plugins[name] = plugin
        logger.info(f"🔌 Plugin registrado: {name} v{plugin.info.version}")
    
    def unregister_plugin(self, name: str) -> bool:
        """Remove um plugin."""
        if name in self.plugins:
            del self.plugins[name]
            logger.info(f"🔌 Plugin removido: {name}")
            return True
        return False
    
    def get_plugin(self, name: str) -> Optional[StrategyPlugin]:
        """Retorna um plugin por nome."""
        return self.plugins.get(name)
    
    def enable_plugin(self, name: str) -> bool:
        """Habilita um plugin."""
        plugin = self.plugins.get(name)
        if plugin:
            plugin.enable()
            return True
        return False
    
    def disable_plugin(self, name: str) -> bool:
        """Desabilita um plugin."""
        plugin = self.plugins.get(name)
        if plugin:
            plugin.disable()
            return True
        return False
    
    def configure_plugin(self, name: str, config: Dict[str, Any]) -> bool:
        """Configura um plugin."""
        plugin = self.plugins.get(name)
        if plugin:
            plugin.configure(config)
            return True
        return False
    
    async def run_analysis(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        indicators: Dict[str, Any],
        plugins: Optional[List[str]] = None,
    ) -> List[Signal]:
        """
        Executa análise em todos os plugins habilitados.
        
        Args:
            symbol: Par/símbolo
            timeframe: Timeframe
            candles: Lista de candles
            indicators: Indicadores técnicos
            plugins: Lista de plugins específicos (ou todos se None)
            
        Returns:
            Lista de sinais gerados
        """
        signals = []
        
        target_plugins = plugins or list(self.plugins.keys())
        
        for name in target_plugins:
            plugin = self.plugins.get(name)
            if not plugin or not plugin.enabled:
                continue
            
            # Verifica se suporta o símbolo
            if plugin.info.symbols and symbol not in plugin.info.symbols:
                continue
            
            # Verifica se suporta o timeframe
            if plugin.info.timeframes and timeframe not in plugin.info.timeframes:
                continue
            
            try:
                signal = await plugin.analyze(symbol, timeframe, candles, indicators)
                if signal and signal.type != SignalType.HOLD:
                    plugin._record_signal(signal)
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Erro no plugin {name}: {e}")
        
        return signals
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """Lista todos os plugins."""
        return [
            {
                **plugin.info.to_dict(),
                "enabled": plugin.enabled,
                "stats": plugin.get_stats(),
            }
            for plugin in self.plugins.values()
        ]


# ============================================================================
# EXAMPLE PLUGINS
# ============================================================================

class MACrossoverPlugin(StrategyPlugin):
    """Estratégia de cruzamento de médias móveis."""
    
    info = PluginInfo(
        name="MACrossover",
        version="1.0.0",
        author="VIRTUS",
        description="Cruzamento de médias móveis rápida/lenta",
        symbols=["XAUUSD", "EURUSD", "GBPUSD"],
        timeframes=["M15", "H1", "H4"],
    )
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "fast_period": 9,
            "slow_period": 21,
            "signal_threshold": 0.0001,
        }
    
    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        indicators: Dict[str, Any],
    ) -> Optional[Signal]:
        if len(candles) < self._config.get("slow_period", 21):
            return None
        
        # Obtém MAs dos indicadores ou calcula
        fast_ma = indicators.get("ma_fast", [])
        slow_ma = indicators.get("ma_slow", [])
        
        if not fast_ma or not slow_ma:
            return Signal(
                type=SignalType.HOLD,
                symbol=symbol,
                strategy=self.info.name,
                reason="Indicadores não disponíveis"
            )
        
        # Verifica cruzamento
        fast_current = fast_ma[-1]
        slow_current = slow_ma[-1]
        fast_prev = fast_ma[-2] if len(fast_ma) > 1 else fast_current
        slow_prev = slow_ma[-2] if len(slow_ma) > 1 else slow_current
        
        threshold = self._config.get("signal_threshold", 0.0001)
        
        # Cruzamento para cima (BUY)
        if fast_prev <= slow_prev and fast_current > slow_current + threshold:
            return Signal(
                type=SignalType.BUY,
                symbol=symbol,
                strategy=self.info.name,
                confidence=70.0,
                reason=f"MA{self._config['fast_period']} cruzou acima da MA{self._config['slow_period']}",
            )
        
        # Cruzamento para baixo (SELL)
        if fast_prev >= slow_prev and fast_current < slow_current - threshold:
            return Signal(
                type=SignalType.SELL,
                symbol=symbol,
                strategy=self.info.name,
                confidence=70.0,
                reason=f"MA{self._config['fast_period']} cruzou abaixo da MA{self._config['slow_period']}",
            )
        
        return Signal(
            type=SignalType.HOLD,
            symbol=symbol,
            strategy=self.info.name,
        )


class RSIOverboughtPlugin(StrategyPlugin):
    """Estratégia baseada em RSI sobrecomprado/sobrevendido."""
    
    info = PluginInfo(
        name="RSIOverbought",
        version="1.0.0",
        author="VIRTUS",
        description="Sinais baseados em níveis extremos de RSI",
        symbols=["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"],
        timeframes=["M15", "H1", "H4", "D1"],
    )
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            "rsi_period": 14,
            "overbought": 70,
            "oversold": 30,
        }
    
    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        indicators: Dict[str, Any],
    ) -> Optional[Signal]:
        rsi = indicators.get("rsi", [])
        
        if not rsi:
            return None
        
        current_rsi = rsi[-1]
        overbought = self._config.get("overbought", 70)
        oversold = self._config.get("oversold", 30)
        
        if current_rsi >= overbought:
            return Signal(
                type=SignalType.SELL,
                symbol=symbol,
                strategy=self.info.name,
                confidence=min(90, 50 + (current_rsi - overbought)),
                reason=f"RSI sobrecomprado: {current_rsi:.1f}",
                metadata={"rsi": current_rsi}
            )
        
        if current_rsi <= oversold:
            return Signal(
                type=SignalType.BUY,
                symbol=symbol,
                strategy=self.info.name,
                confidence=min(90, 50 + (oversold - current_rsi)),
                reason=f"RSI sobrevendido: {current_rsi:.1f}",
                metadata={"rsi": current_rsi}
            )
        
        return Signal(
            type=SignalType.HOLD,
            symbol=symbol,
            strategy=self.info.name,
        )


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

plugin_manager = PluginManager()

# Registra plugins built-in
plugin_manager.register_plugin(MACrossoverPlugin())
plugin_manager.register_plugin(RSIOverboughtPlugin())


# ============================================================================
# FASTAPI ROUTES
# ============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/plugins", tags=["Strategy Plugins"])


class PluginConfigRequest(BaseModel):
    config: Dict[str, Any]


@router.get("/")
async def list_strategy_plugins():
    """Lista todas as estratégias disponíveis."""
    return plugin_manager.list_plugins()


@router.get("/{name}")
async def get_strategy_plugin(name: str):
    """Retorna detalhes de uma estratégia."""
    plugin = plugin_manager.get_plugin(name)
    if not plugin:
        raise HTTPException(404, "Plugin não encontrado")
    
    return {
        **plugin.info.to_dict(),
        "enabled": plugin.enabled,
        "config": plugin.config,
        "default_config": plugin.get_default_config(),
        "stats": plugin.get_stats(),
        "last_signal": plugin.last_signal.to_dict() if plugin.last_signal else None,
    }


@router.post("/{name}/enable")
async def enable_strategy_plugin(name: str):
    """Habilita uma estratégia."""
    if plugin_manager.enable_plugin(name):
        return {"message": f"Plugin {name} habilitado"}
    raise HTTPException(404, "Plugin não encontrado")


@router.post("/{name}/disable")
async def disable_strategy_plugin(name: str):
    """Desabilita uma estratégia."""
    if plugin_manager.disable_plugin(name):
        return {"message": f"Plugin {name} desabilitado"}
    raise HTTPException(404, "Plugin não encontrado")


@router.post("/{name}/configure")
async def configure_strategy_plugin(name: str, request: PluginConfigRequest):
    """Configura uma estratégia."""
    if plugin_manager.configure_plugin(name, request.config):
        return {"message": f"Plugin {name} configurado", "config": request.config}
    raise HTTPException(404, "Plugin não encontrado")


@router.post("/reload")
async def reload_plugins():
    """Recarrega todos os plugins do diretório."""
    count = plugin_manager.load_plugins()
    return {"message": f"{count} plugins carregados"}


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    async def test():
        print("🔌 Plugin System Test\n")
        
        # Lista plugins
        print("Plugins disponíveis:")
        for p in plugin_manager.list_plugins():
            print(f"  - {p['name']} v{p['version']}: {p['description']}")
        
        # Configura plugin
        plugin_manager.configure_plugin("MACrossover", {
            "fast_period": 5,
            "slow_period": 15,
        })
        
        # Simula análise
        fake_candles = [{"close": 2050 + i * 0.5} for i in range(50)]
        fake_indicators = {
            "ma_fast": [2048, 2049, 2050, 2051, 2052],
            "ma_slow": [2045, 2047, 2049, 2050, 2051],
            "rsi": [45, 50, 55, 60, 72],
        }
        
        signals = await plugin_manager.run_analysis(
            symbol="XAUUSD",
            timeframe="H1",
            candles=fake_candles,
            indicators=fake_indicators,
        )
        
        print("\nSinais gerados:")
        for signal in signals:
            print(f"  - {signal.strategy}: {signal.type.value} | {signal.reason}")
        
        # Stats
        print("\nEstatísticas:")
        for name, plugin in plugin_manager.plugins.items():
            print(f"  - {name}: {plugin.get_stats()}")
    
    asyncio.run(test())
