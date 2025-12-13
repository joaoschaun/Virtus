"""
BRAIN - Bot Orchestrator
Orquestrador de múltiplos bots
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..core.logger import get_logger
from ..core.config import ConfigLoader
from ..core.exceptions import BrainError
from .trading_bot import TradingBot, BotState
from ..mt5 import MT5Manager, get_mt5_manager
from ..brain import BrainService

logger = get_logger("orchestrator")


@dataclass
class OrchestratorStats:
    """Estatísticas do orquestrador"""
    total_bots: int = 0
    running_bots: int = 0
    paused_bots: int = 0
    total_positions: int = 0
    total_profit_today: float = 0.0
    started_at: Optional[datetime] = None


class BotOrchestrator:
    """
    Orquestrador de bots de trading
    
    Responsabilidades:
    - Inicializar/parar bots
    - Coordenar recursos
    - Distribuir capital
    - Monitorar saúde
    - Gerenciar riscos globais
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Dependências
        self._mt5: Optional[MT5Manager] = None
        self._brain: Optional[BrainService] = None
        self._config_loader: Optional[ConfigLoader] = None
        
        # Bots gerenciados
        self._bots: Dict[str, TradingBot] = {}
        
        # Estado
        self._running = False
        self._stats = OrchestratorStats()
        
        # Tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._health_task: Optional[asyncio.Task] = None
        
        self._initialized = True
    
    async def initialize(
        self,
        config_path: str = "brain/config/config.yaml"
    ):
        """
        Inicializa o orquestrador
        
        Args:
            config_path: Caminho do arquivo de configuração
        """
        logger.info("Inicializando Bot Orchestrator")
        
        # Carregar configurações
        self._config_loader = ConfigLoader(config_path)
        config = self._config_loader.config
        
        # Inicializar MT5
        self._mt5 = get_mt5_manager()
        
        mt5_config = config.mt5
        await self._mt5.connect(
            login=mt5_config.login,
            password=mt5_config.password,
            server=mt5_config.server,
            path=mt5_config.path
        )
        
        # Inicializar Brain
        self._brain = BrainService()
        await self._brain.initialize()
        
        # Criar bots
        for bot_config in config.bots:
            if bot_config.enabled:
                bot = TradingBot(
                    config=bot_config,
                    mt5_manager=self._mt5,
                    brain_service=self._brain
                )
                self._bots[bot_config.id] = bot
        
        self._stats.total_bots = len(self._bots)
        logger.info(f"Orchestrator inicializado com {len(self._bots)} bots")
    
    async def start(self):
        """Inicia o orquestrador e todos os bots"""
        if self._running:
            logger.warning("Orchestrator já está rodando")
            return
        
        logger.info("Iniciando Bot Orchestrator")
        self._running = True
        self._stats.started_at = datetime.now()
        
        # Iniciar bots
        for bot_id, bot in self._bots.items():
            try:
                await bot.start()
                self._stats.running_bots += 1
            except Exception as e:
                logger.error(f"Erro ao iniciar bot {bot_id}: {e}")
        
        # Iniciar tasks de monitoramento
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._health_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Bot Orchestrator iniciado")
    
    async def stop(self):
        """Para o orquestrador e todos os bots"""
        logger.info("Parando Bot Orchestrator")
        self._running = False
        
        # Parar tasks
        if self._monitor_task:
            self._monitor_task.cancel()
        if self._health_task:
            self._health_task.cancel()
        
        # Parar bots
        for bot_id, bot in self._bots.items():
            try:
                await bot.stop()
            except Exception as e:
                logger.error(f"Erro ao parar bot {bot_id}: {e}")
        
        self._stats.running_bots = 0
        
        # Desconectar MT5
        if self._mt5:
            await self._mt5.disconnect()
        
        # Desligar Brain
        if self._brain:
            await self._brain.shutdown()
        
        logger.info("Bot Orchestrator parado")
    
    # ==========================================================================
    # GERENCIAMENTO DE BOTS
    # ==========================================================================
    
    async def start_bot(self, bot_id: str):
        """
        Inicia um bot específico
        
        Args:
            bot_id: ID do bot
        """
        bot = self._bots.get(bot_id)
        if not bot:
            raise BrainError(f"Bot não encontrado: {bot_id}")
        
        if bot.state == BotState.RUNNING:
            logger.warning(f"Bot {bot_id} já está rodando")
            return
        
        await bot.start()
        self._stats.running_bots += 1
        logger.info(f"Bot {bot_id} iniciado")
    
    async def stop_bot(self, bot_id: str):
        """
        Para um bot específico
        
        Args:
            bot_id: ID do bot
        """
        bot = self._bots.get(bot_id)
        if not bot:
            raise BrainError(f"Bot não encontrado: {bot_id}")
        
        await bot.stop()
        self._stats.running_bots -= 1
        logger.info(f"Bot {bot_id} parado")
    
    async def pause_bot(self, bot_id: str):
        """Pausa um bot"""
        bot = self._bots.get(bot_id)
        if bot:
            await bot.pause()
            self._stats.running_bots -= 1
            self._stats.paused_bots += 1
    
    async def resume_bot(self, bot_id: str):
        """Resume um bot pausado"""
        bot = self._bots.get(bot_id)
        if bot:
            await bot.resume()
            self._stats.paused_bots -= 1
            self._stats.running_bots += 1
    
    async def pause_all(self):
        """Pausa todos os bots"""
        for bot_id in self._bots:
            await self.pause_bot(bot_id)
    
    async def resume_all(self):
        """Resume todos os bots"""
        for bot_id in self._bots:
            if self._bots[bot_id].state == BotState.PAUSED:
                await self.resume_bot(bot_id)
    
    async def close_all_positions(self):
        """Fecha todas as posições de todos os bots"""
        logger.warning("FECHANDO TODAS AS POSIÇÕES")
        
        for bot in self._bots.values():
            await bot.close_all_positions()
    
    # ==========================================================================
    # MONITORAMENTO
    # ==========================================================================
    
    async def _monitor_loop(self):
        """Loop de monitoramento"""
        while self._running:
            try:
                await self._update_stats()
                await self._check_global_risk()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def _health_check_loop(self):
        """Loop de health check"""
        while self._running:
            try:
                await self._check_mt5_connection()
                await self._check_bots_health()
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no health check: {e}")
                await asyncio.sleep(60)
    
    async def _update_stats(self):
        """Atualiza estatísticas"""
        total_positions = 0
        total_profit = 0.0
        
        running = 0
        paused = 0
        
        for bot in self._bots.values():
            status = bot.get_status()
            total_positions += status.get("positions", 0)
            total_profit += status.get("stats", {}).get("profit_today", 0)
            
            if bot.state == BotState.RUNNING:
                running += 1
            elif bot.state == BotState.PAUSED:
                paused += 1
        
        self._stats.total_positions = total_positions
        self._stats.total_profit_today = total_profit
        self._stats.running_bots = running
        self._stats.paused_bots = paused
    
    async def _check_global_risk(self):
        """Verifica riscos globais"""
        # Obter info da conta
        if not self._mt5 or not self._mt5.is_connected:
            return
        
        account = await self._mt5.get_account_info()
        margin_level = account.get("margin_level", 100)
        
        # Margin call check
        if margin_level < 100:
            logger.critical(f"MARGIN CALL! Level: {margin_level}%")
            await self.close_all_positions()
            await self.pause_all()
        elif margin_level < 150:
            logger.warning(f"Margem baixa: {margin_level}%")
        
        # Drawdown diário
        # TODO: Implementar
    
    async def _check_mt5_connection(self):
        """Verifica conexão MT5"""
        if not self._mt5:
            return
        
        if not self._mt5.is_connected:
            logger.warning("Conexão MT5 perdida, tentando reconectar...")
            try:
                await self._mt5.connect()
            except Exception as e:
                logger.error(f"Falha ao reconectar MT5: {e}")
    
    async def _check_bots_health(self):
        """Verifica saúde dos bots"""
        for bot_id, bot in self._bots.items():
            if bot.state == BotState.ERROR:
                logger.warning(f"Bot {bot_id} em estado de erro")
                # Tentar reiniciar
                try:
                    await bot.stop()
                    await asyncio.sleep(1)
                    await bot.start()
                except Exception as e:
                    logger.error(f"Falha ao reiniciar bot {bot_id}: {e}")
    
    # ==========================================================================
    # INFORMAÇÕES
    # ==========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do orquestrador"""
        return {
            "running": self._running,
            "stats": {
                "total_bots": self._stats.total_bots,
                "running_bots": self._stats.running_bots,
                "paused_bots": self._stats.paused_bots,
                "total_positions": self._stats.total_positions,
                "total_profit_today": self._stats.total_profit_today,
                "started_at": self._stats.started_at.isoformat() if self._stats.started_at else None
            },
            "bots": {
                bot_id: bot.get_status()
                for bot_id, bot in self._bots.items()
            }
        }
    
    def get_bot(self, bot_id: str) -> Optional[TradingBot]:
        """Obtém um bot pelo ID"""
        return self._bots.get(bot_id)
    
    def list_bots(self) -> List[str]:
        """Lista IDs dos bots"""
        return list(self._bots.keys())


# Singleton global
_orchestrator: Optional[BotOrchestrator] = None


def get_orchestrator() -> BotOrchestrator:
    """Obtém instância global do orquestrador"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = BotOrchestrator()
    return _orchestrator
