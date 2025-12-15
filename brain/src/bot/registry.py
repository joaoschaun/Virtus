"""
VIRTUS Bot Registry
====================

Sistema central de registro e gerenciamento de bots.
Permite adicionar/remover bots dinamicamente e agregar métricas.
"""

import asyncio
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Callable
from dataclasses import dataclass, field

from .base import BaseBot, BotConfig, BotType, BotStatus, BotMetrics, MarketType


@dataclass
class AggregatedMetrics:
    """Métricas agregadas de todos os bots."""
    total_bots: int = 0
    running_bots: int = 0
    paused_bots: int = 0
    stopped_bots: int = 0
    error_bots: int = 0
    
    # Performance agregada
    total_trades: int = 0
    total_profit: float = 0.0
    total_win_rate: float = 0.0
    
    # Por tipo
    by_type: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Por mercado
    by_market: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    last_update: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_bots": self.total_bots,
            "running_bots": self.running_bots,
            "paused_bots": self.paused_bots,
            "stopped_bots": self.stopped_bots,
            "error_bots": self.error_bots,
            "total_trades": self.total_trades,
            "total_profit": round(self.total_profit, 2),
            "total_win_rate": round(self.total_win_rate, 2),
            "by_type": self.by_type,
            "by_market": self.by_market,
            "last_update": self.last_update.isoformat(),
        }


class BotRegistry:
    """
    Registro central de bots.
    
    Funcionalidades:
    - Registro de tipos de bot
    - Instanciação dinâmica
    - Gerenciamento de ciclo de vida
    - Agregação de métricas
    - Persistência de configurações
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Tipos de bot registrados
        self._bot_types: Dict[BotType, Type[BaseBot]] = {}
        
        # Bots instanciados
        self._bots: Dict[str, BaseBot] = {}
        
        # Callbacks globais
        self._on_bot_registered: List[Callable] = []
        self._on_bot_removed: List[Callable] = []
        self._on_metrics_update: List[Callable] = []
        
        # Métricas agregadas
        self._aggregated = AggregatedMetrics()
        
        # Path para configs
        self._config_path: Optional[Path] = None
        
        self._initialized = True
    
    # ==================== Registro de Tipos ====================
    
    def register_bot_type(self, bot_type: BotType, bot_class: Type[BaseBot]):
        """
        Registra um tipo de bot.
        
        Args:
            bot_type: Tipo do bot (enum)
            bot_class: Classe que implementa BaseBot
        """
        if not issubclass(bot_class, BaseBot):
            raise ValueError(f"{bot_class} must be a subclass of BaseBot")
        
        self._bot_types[bot_type] = bot_class
    
    def get_registered_types(self) -> List[str]:
        """Retorna tipos de bot registrados."""
        return [t.value for t in self._bot_types.keys()]
    
    # ==================== Gerenciamento de Bots ====================
    
    def create_bot(self, config: BotConfig) -> Optional[BaseBot]:
        """
        Cria um bot a partir de configuração.
        
        Args:
            config: Configuração do bot
            
        Returns:
            Instância do bot ou None se tipo não registrado
        """
        bot_class = self._bot_types.get(config.bot_type)
        
        if not bot_class:
            # Usa classe genérica se disponível
            bot_class = self._bot_types.get(BotType.CUSTOM)
            if not bot_class:
                return None
        
        bot = bot_class(config)
        return bot
    
    def register_bot(self, bot: BaseBot) -> bool:
        """
        Registra um bot instanciado.
        
        Args:
            bot: Instância do bot
            
        Returns:
            True se registrado com sucesso
        """
        if bot.bot_id in self._bots:
            return False
        
        self._bots[bot.bot_id] = bot
        
        # Registra callbacks no bot
        bot.on_trade(self._on_trade_callback)
        bot.on_status_change(self._on_status_callback)
        bot.on_error(self._on_error_callback)
        
        # Notifica listeners
        for callback in self._on_bot_registered:
            try:
                callback(bot)
            except Exception:
                pass
        
        self._update_aggregated()
        return True
    
    def add_bot(self, config: BotConfig) -> Optional[BaseBot]:
        """
        Cria e registra um bot.
        
        Args:
            config: Configuração do bot
            
        Returns:
            Bot criado ou None se falhou
        """
        bot = self.create_bot(config)
        if bot and self.register_bot(bot):
            return bot
        return None
    
    def remove_bot(self, bot_id: str) -> bool:
        """
        Remove um bot do registro.
        
        Args:
            bot_id: ID do bot
            
        Returns:
            True se removido com sucesso
        """
        bot = self._bots.pop(bot_id, None)
        if not bot:
            return False
        
        # Para o bot se estiver rodando
        if bot.is_running:
            asyncio.create_task(bot.stop())
        
        # Notifica listeners
        for callback in self._on_bot_removed:
            try:
                callback(bot)
            except Exception:
                pass
        
        self._update_aggregated()
        return True
    
    def get_bot(self, bot_id: str) -> Optional[BaseBot]:
        """Obtém um bot pelo ID."""
        return self._bots.get(bot_id)
    
    def get_all_bots(self) -> List[BaseBot]:
        """Retorna todos os bots."""
        return list(self._bots.values())
    
    def get_bots_by_type(self, bot_type: BotType) -> List[BaseBot]:
        """Retorna bots de um tipo específico."""
        return [b for b in self._bots.values() if b.bot_type == bot_type]
    
    def get_bots_by_status(self, status: BotStatus) -> List[BaseBot]:
        """Retorna bots com um status específico."""
        return [b for b in self._bots.values() if b.status == status]
    
    def get_bots_by_market(self, market: MarketType) -> List[BaseBot]:
        """Retorna bots de um mercado específico."""
        return [b for b in self._bots.values() if b.config.market == market]
    
    # ==================== Controle em Lote ====================
    
    async def start_all(self) -> Dict[str, bool]:
        """Inicia todos os bots com auto_start=True."""
        results = {}
        for bot_id, bot in self._bots.items():
            if bot.config.auto_start and bot.status == BotStatus.STOPPED:
                results[bot_id] = await bot.start()
        return results
    
    async def stop_all(self) -> Dict[str, bool]:
        """Para todos os bots."""
        results = {}
        for bot_id, bot in self._bots.items():
            if bot.is_running:
                results[bot_id] = await bot.stop()
        return results
    
    async def start_by_type(self, bot_type: BotType) -> Dict[str, bool]:
        """Inicia todos os bots de um tipo."""
        results = {}
        for bot in self.get_bots_by_type(bot_type):
            if bot.status == BotStatus.STOPPED:
                results[bot.bot_id] = await bot.start()
        return results
    
    async def stop_by_type(self, bot_type: BotType) -> Dict[str, bool]:
        """Para todos os bots de um tipo."""
        results = {}
        for bot in self.get_bots_by_type(bot_type):
            if bot.is_running:
                results[bot.bot_id] = await bot.stop()
        return results
    
    # ==================== Métricas ====================
    
    def get_aggregated_metrics(self) -> AggregatedMetrics:
        """Retorna métricas agregadas."""
        self._update_aggregated()
        return self._aggregated
    
    def _update_aggregated(self):
        """Atualiza métricas agregadas."""
        agg = self._aggregated
        
        bots = list(self._bots.values())
        agg.total_bots = len(bots)
        
        # Contagem por status
        agg.running_bots = sum(1 for b in bots if b.status == BotStatus.RUNNING)
        agg.paused_bots = sum(1 for b in bots if b.status == BotStatus.PAUSED)
        agg.stopped_bots = sum(1 for b in bots if b.status == BotStatus.STOPPED)
        agg.error_bots = sum(1 for b in bots if b.status == BotStatus.ERROR)
        
        # Performance agregada
        agg.total_trades = sum(b.metrics.total_trades for b in bots)
        agg.total_profit = sum(b.metrics.net_profit for b in bots)
        
        if agg.total_bots > 0:
            agg.total_win_rate = sum(b.metrics.win_rate for b in bots) / agg.total_bots
        
        # Por tipo
        agg.by_type = {}
        for bot_type in BotType:
            type_bots = [b for b in bots if b.bot_type == bot_type]
            if type_bots:
                agg.by_type[bot_type.value] = {
                    "count": len(type_bots),
                    "running": sum(1 for b in type_bots if b.is_running),
                    "profit": sum(b.metrics.net_profit for b in type_bots),
                    "trades": sum(b.metrics.total_trades for b in type_bots),
                }
        
        # Por mercado
        agg.by_market = {}
        for market in MarketType:
            market_bots = [b for b in bots if b.config.market == market]
            if market_bots:
                agg.by_market[market.value] = {
                    "count": len(market_bots),
                    "running": sum(1 for b in market_bots if b.is_running),
                    "profit": sum(b.metrics.net_profit for b in market_bots),
                    "trades": sum(b.metrics.total_trades for b in market_bots),
                }
        
        agg.last_update = datetime.now()
        
        # Notifica listeners
        for callback in self._on_metrics_update:
            try:
                callback(agg)
            except Exception:
                pass
    
    # ==================== Callbacks Internos ====================
    
    def _on_trade_callback(self, bot_id: str, trade: Dict[str, Any]):
        """Callback quando um bot executa trade."""
        self._update_aggregated()
    
    def _on_status_callback(self, bot_id: str, old_status: BotStatus, new_status: BotStatus):
        """Callback quando status de bot muda."""
        self._update_aggregated()
    
    def _on_error_callback(self, bot_id: str, error: Exception):
        """Callback quando bot tem erro."""
        pass
    
    # ==================== Persistência ====================
    
    def set_config_path(self, path: Path):
        """Define path para arquivos de configuração."""
        self._config_path = path
    
    def load_configs_from_directory(self, directory: Path) -> int:
        """
        Carrega configurações de um diretório.
        
        Args:
            directory: Diretório com arquivos YAML
            
        Returns:
            Número de bots carregados
        """
        loaded = 0
        
        if not directory.exists():
            return 0
        
        for yaml_file in directory.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    continue
                
                # Extrai bot_id do nome do arquivo
                bot_id = yaml_file.stem
                data['bot_id'] = bot_id
                
                config = BotConfig.from_dict(data)
                
                if self.add_bot(config):
                    loaded += 1
                    
            except Exception as e:
                print(f"Error loading {yaml_file}: {e}")
        
        return loaded
    
    def save_bot_config(self, bot_id: str) -> bool:
        """
        Salva configuração de um bot em arquivo.
        
        Args:
            bot_id: ID do bot
            
        Returns:
            True se salvou com sucesso
        """
        if not self._config_path:
            return False
        
        bot = self.get_bot(bot_id)
        if not bot:
            return False
        
        try:
            config_file = self._config_path / f"{bot_id}.yaml"
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(bot.config.to_dict(), f, default_flow_style=False)
            return True
        except Exception:
            return False
    
    # ==================== Eventos ====================
    
    def on_bot_registered(self, callback: Callable):
        """Registra callback para quando bot é registrado."""
        self._on_bot_registered.append(callback)
    
    def on_bot_removed(self, callback: Callable):
        """Registra callback para quando bot é removido."""
        self._on_bot_removed.append(callback)
    
    def on_metrics_update(self, callback: Callable):
        """Registra callback para atualização de métricas."""
        self._on_metrics_update.append(callback)
    
    # ==================== Estado para Dashboard ====================
    
    def get_dashboard_state(self) -> Dict[str, Any]:
        """
        Retorna estado completo para o dashboard.
        
        Returns:
            Dict com todos os dados para exibição
        """
        return {
            "bots": [b.get_state() for b in self._bots.values()],
            "aggregated": self.get_aggregated_metrics().to_dict(),
            "registered_types": self.get_registered_types(),
            "summary": {
                "total": len(self._bots),
                "running": sum(1 for b in self._bots.values() if b.is_running),
                "by_type": {
                    t.value: sum(1 for b in self._bots.values() if b.bot_type == t)
                    for t in BotType if any(b.bot_type == t for b in self._bots.values())
                },
            },
        }


# Instância global (singleton)
bot_registry = BotRegistry()
