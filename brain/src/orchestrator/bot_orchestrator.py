"""
VIRTUS Bot Orchestrator
========================

Orquestrador central que gerencia todos os bots de trading.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import json

from ..core import Config, VirtusLogger, BotConfig
from ..core.exceptions import OrchestratorError, BotError
from ..bot import TradingBot, create_bot, BotState, BotHealthMonitor, HealthStatus
from ..brain import BrainService, get_brain
from ..mt5 import MT5Connection
from ..telegram import TelegramService


class BotRegistry:
    """
    Registro central de bots.
    
    Mantém referências e metadados de todos os bots ativos.
    """
    
    def __init__(self):
        self._bots: Dict[str, TradingBot] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def register(self, bot: TradingBot, metadata: Optional[Dict] = None) -> None:
        """Registra um bot."""
        async with self._lock:
            self._bots[bot.bot_id] = bot
            self._metadata[bot.bot_id] = metadata or {}
            self._metadata[bot.bot_id]['registered_at'] = datetime.now().isoformat()
    
    async def unregister(self, bot_id: str) -> Optional[TradingBot]:
        """Remove um bot do registro."""
        async with self._lock:
            bot = self._bots.pop(bot_id, None)
            self._metadata.pop(bot_id, None)
            return bot
    
    def get(self, bot_id: str) -> Optional[TradingBot]:
        """Obtém um bot pelo ID."""
        return self._bots.get(bot_id)
    
    def get_by_symbol(self, symbol: str) -> Optional[TradingBot]:
        """Obtém um bot pelo símbolo."""
        for bot in self._bots.values():
            if bot.symbol == symbol:
                return bot
        return None
    
    def get_all(self) -> List[TradingBot]:
        """Retorna todos os bots."""
        return list(self._bots.values())
    
    def get_running(self) -> List[TradingBot]:
        """Retorna bots em execução."""
        return [b for b in self._bots.values() if b.is_running]
    
    def count(self) -> int:
        """Conta total de bots."""
        return len(self._bots)
    
    def get_metadata(self, bot_id: str) -> Dict[str, Any]:
        """Obtém metadados de um bot."""
        return self._metadata.get(bot_id, {})


class BotSupervisor:
    """
    Supervisor de bots.
    
    Monitora saúde dos bots e toma ações corretivas.
    """
    
    def __init__(self, registry: BotRegistry, logger: VirtusLogger):
        self.registry = registry
        self.logger = logger
        self._health_monitors: Dict[str, BotHealthMonitor] = {}
        self._check_interval = 30  # segundos
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Callbacks para eventos
        self._on_bot_unhealthy: List[Callable] = []
        self._on_bot_recovered: List[Callable] = []
    
    async def start(self) -> None:
        """Inicia supervisão."""
        self._running = True
        self._task = asyncio.create_task(self._supervision_loop())
        self.logger.info("🔍 Supervisor iniciado")
    
    async def stop(self) -> None:
        """Para supervisão."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("🔍 Supervisor parado")
    
    async def _supervision_loop(self) -> None:
        """Loop de supervisão."""
        while self._running:
            try:
                await self._check_all_bots()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Erro na supervisão: {e}")
                await asyncio.sleep(5)
    
    async def _check_all_bots(self) -> None:
        """Verifica todos os bots."""
        for bot in self.registry.get_all():
            await self._check_bot(bot)
    
    async def _check_bot(self, bot: TradingBot) -> None:
        """Verifica saúde de um bot."""
        try:
            # Obtém ou cria monitor
            if bot.bot_id not in self._health_monitors:
                self._health_monitors[bot.bot_id] = BotHealthMonitor(bot.bot_id)
            
            monitor = self._health_monitors[bot.bot_id]
            
            # Executa verificação
            health = await monitor.check_health(
                mt5_connected=True,  # Verificar MT5
                brain_available=True,  # Verificar Brain
                has_recent_data=True,  # Verificar dados
            )
            
            # Toma ações baseado no status
            if health.overall_status == HealthStatus.CRITICAL:
                await self._handle_critical_bot(bot, health)
            elif health.overall_status == HealthStatus.WARNING:
                await self._handle_warning_bot(bot, health)
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar bot {bot.bot_id}: {e}")
    
    async def _handle_critical_bot(self, bot: TradingBot, health: Any) -> None:
        """Trata bot em estado crítico."""
        self.logger.warning(f"⚠️ Bot {bot.bot_id} em estado CRÍTICO")
        
        # Pausa o bot
        await bot.pause()
        
        # Notifica callbacks
        for callback in self._on_bot_unhealthy:
            try:
                await callback(bot, health)
            except Exception:
                pass
    
    async def _handle_warning_bot(self, bot: TradingBot, health: Any) -> None:
        """Trata bot em estado de alerta."""
        self.logger.info(f"⚡ Bot {bot.bot_id} em estado de ALERTA")
    
    def on_bot_unhealthy(self, callback: Callable) -> None:
        """Registra callback para bot não saudável."""
        self._on_bot_unhealthy.append(callback)
    
    def on_bot_recovered(self, callback: Callable) -> None:
        """Registra callback para bot recuperado."""
        self._on_bot_recovered.append(callback)


class BotOrchestrator:
    """
    Orquestrador central de bots.
    
    Responsabilidades:
    - Criar e gerenciar bots
    - Coordenar inicialização/parada
    - Gerenciar recursos compartilhados
    - Monitorar performance geral
    """
    
    _instance: Optional['BotOrchestrator'] = None
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = VirtusLogger.get_logger("orchestrator")
        
        # Registry e Supervisor
        self.registry = BotRegistry()
        self.supervisor = BotSupervisor(self.registry, self.logger)
        
        # Serviços
        self.brain: Optional[BrainService] = None
        self.mt5: Optional[MT5Connection] = None
        self.telegram: Optional[TelegramService] = None
        
        # Estado
        self._running = False
        self._initialized = False
        
        # Callbacks
        self._on_all_started: List[Callable] = []
        self._on_all_stopped: List[Callable] = []
        
        BotOrchestrator._instance = self
    
    @classmethod
    def get_instance(cls) -> Optional['BotOrchestrator']:
        """Obtém instância singleton."""
        return cls._instance
    
    async def initialize(self) -> bool:
        """Inicializa o orquestrador."""
        try:
            self.logger.info("🚀 Inicializando Orchestrator...")
            
            # Inicializa MT5 (já deve estar conectado pelo main.py)
            self.mt5 = await MT5Connection.get_instance()
            if not self.mt5.is_connected:
                if not await self._connect_mt5():
                    raise OrchestratorError("Falha ao conectar MT5")
            else:
                self.logger.info("✅ MT5 já estava conectado")
            
            # Inicializa Brain
            self.brain = await get_brain()
            if not self.brain:
                self.logger.warning("Brain não inicializado")
            
            # Inicializa Telegram (opcional)
            try:
                config = self.config
                if config.telegram.token and config.telegram.chat_id:
                    self.telegram = await TelegramService.get_instance()
                else:
                    self.telegram = None
            except Exception:
                self.telegram = None
            
            # Cria bots para cada símbolo configurado
            await self._create_bots()
            
            self._initialized = True
            self.logger.success("✅ Orchestrator inicializado")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar Orchestrator: {e}")
            return False
    
    async def _connect_mt5(self) -> bool:
        """Conecta ao MT5."""
        try:
            mt5_config = self.config.mt5
            
            connected = await self.mt5.connect(
                login=mt5_config.login,
                password=mt5_config.password,
                server=mt5_config.server,
            )
            
            if connected:
                self.logger.success("✅ MT5 conectado")
                return True
            else:
                self.logger.error("❌ Falha ao conectar MT5")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao conectar MT5: {e}")
            return False
    
    async def _create_bots(self) -> None:
        """Cria bots para cada símbolo configurado."""
        for bot_config in self.config.bots:
            if not bot_config.enabled:
                continue
            
            try:
                bot = create_bot(
                    symbol=bot_config.symbol,
                    config=self.config,
                    strategy=None,  # Estratégia será definida depois
                )
                
                await self.registry.register(bot, {
                    'config': bot_config.__dict__,
                })
                
                self.logger.info(f"📊 Bot criado para {bot_config.symbol}")
                
            except Exception as e:
                self.logger.error(f"Erro ao criar bot para {bot_config.symbol}: {e}")
    
    async def start(self) -> None:
        """Inicia todos os bots."""
        if not self._initialized:
            raise OrchestratorError("Orchestrator não inicializado")
        
        self.logger.info("▶️ Iniciando todos os bots...")
        self._running = True
        
        # Inicia supervisor
        await self.supervisor.start()
        
        # Inicializa e inicia cada bot
        tasks = []
        for bot in self.registry.get_all():
            tasks.append(self._start_bot(bot))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Notifica callbacks
        for callback in self._on_all_started:
            try:
                await callback()
            except Exception:
                pass
        
        running_count = len(self.registry.get_running())
        total_count = self.registry.count()
        
        self.logger.success(f"✅ {running_count}/{total_count} bots iniciados")
        
        # Notifica via Telegram (com verificação de disponibilidade)
        if self.telegram and hasattr(self.telegram, '_initialized') and self.telegram._initialized:
            try:
                await self.telegram.send_message(
                    f"🤖 *VIRTUS Iniciado*\n\n"
                    f"📊 Bots ativos: {running_count}/{total_count}\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Falha ao enviar notificação Telegram: {e}")
    
    async def _start_bot(self, bot: TradingBot) -> bool:
        """Inicia um bot individual."""
        try:
            # Inicializa
            if not await bot.initialize():
                self.logger.error(f"Falha ao inicializar bot {bot.bot_id}")
                return False
            
            # Registra callbacks
            bot.on_signal(self._on_bot_signal)
            bot.on_trade(self._on_bot_trade)
            
            # Inicia
            await bot.start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar bot {bot.bot_id}: {e}")
            return False
    
    async def stop(self) -> None:
        """Para todos os bots."""
        self.logger.info("⏹️ Parando todos os bots...")
        self._running = False
        
        # Para supervisor
        await self.supervisor.stop()
        
        # Para cada bot
        tasks = []
        for bot in self.registry.get_all():
            tasks.append(bot.stop())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Desconecta MT5
        if self.mt5:
            await self.mt5.disconnect()
        
        # Notifica callbacks
        for callback in self._on_all_stopped:
            try:
                await callback()
            except Exception:
                pass
        
        self.logger.success("✅ Todos os bots parados")
        
        # Notifica via Telegram
        if self.telegram and hasattr(self.telegram, '_initialized') and self.telegram._initialized:
            try:
                await self.telegram.send_message(
                    f"🔴 *VIRTUS Parado*\n\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Falha ao enviar notificação Telegram: {e}")
    
    async def pause_all(self) -> None:
        """Pausa todos os bots."""
        for bot in self.registry.get_running():
            await bot.pause()
        self.logger.info("⏸️ Todos os bots pausados")
    
    async def resume_all(self) -> None:
        """Resume todos os bots."""
        for bot in self.registry.get_all():
            await bot.resume()
        self.logger.info("▶️ Todos os bots resumidos")
    
    async def restart_bot(self, bot_id: str) -> bool:
        """Reinicia um bot específico."""
        bot = self.registry.get(bot_id)
        if not bot:
            return False
        
        await bot.stop()
        await asyncio.sleep(1)
        return await self._start_bot(bot)
    
    async def _on_bot_signal(self, signal: Any) -> None:
        """Callback para sinais de bots."""
        self.logger.debug(f"Sinal recebido: {signal.symbol} - {signal.type.name}")
    
    async def _on_bot_trade(self, action: str, position: Any) -> None:
        """Callback para trades de bots."""
        if self.telegram and hasattr(self.telegram, '_initialized') and self.telegram._initialized:
            try:
                emoji = "🟢" if action == "entry" else "🔴"
                await self.telegram.send_trade_notification(
                    symbol=position.symbol,
                    action=action,
                    price=position.open_price if action == "entry" else position.current_price,
                    profit=position.profit,
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Falha ao enviar notificação de trade: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status geral do sistema."""
        bots_status = []
        for bot in self.registry.get_all():
            status = bot.get_status()
            bots_status.append({
                'id': bot.bot_id,
                'symbol': bot.symbol,
                'state': status['context']['state'],
                'has_position': status['context']['has_position'],
                'total_trades': status['statistics']['total_trades'],
                'win_rate': status['statistics']['win_rate'],
                'net_profit': status['statistics']['net_profit'],
            })
        
        return {
            'running': self._running,
            'total_bots': self.registry.count(),
            'running_bots': len(self.registry.get_running()),
            'mt5_connected': self.mt5.connected if self.mt5 else False,
            'brain_available': self.brain is not None,
            'bots': bots_status,
            'timestamp': datetime.now().isoformat(),
        }
    
    def get_bot(self, identifier: str) -> Optional[TradingBot]:
        """Obtém bot por ID ou símbolo."""
        bot = self.registry.get(identifier)
        if not bot:
            bot = self.registry.get_by_symbol(identifier.upper())
        return bot
    
    def on_all_started(self, callback: Callable) -> None:
        """Registra callback para quando todos os bots iniciarem."""
        self._on_all_started.append(callback)
    
    def on_all_stopped(self, callback: Callable) -> None:
        """Registra callback para quando todos os bots pararem."""
        self._on_all_stopped.append(callback)


# Função auxiliar
def get_orchestrator() -> Optional[BotOrchestrator]:
    """Obtém instância do orquestrador."""
    return BotOrchestrator.get_instance()
