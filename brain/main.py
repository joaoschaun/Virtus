"""
BRAIN - Main Entry Point
Ponto de entrada principal do sistema
"""

import asyncio
import signal
import sys
from typing import Optional

# Adicionar src ao path
sys.path.insert(0, "brain/src")

from core.logger import get_logger, setup_logging
from core.config import ConfigLoader
from orchestrator.bot_orchestrator import BotOrchestrator, get_orchestrator
from telegram.telegram_bot import get_telegram_bot
from advisor.market_advisor import create_market_advisor
from brain import BrainService

logger = get_logger("main")


class BRAINApplication:
    """
    Aplicação principal BRAIN
    
    Coordena todos os componentes:
    - Orchestrator (gerencia bots)
    - Telegram Bot (notificações e comandos)
    - Market Advisor (briefings)
    - Brain Service (dados centralizados)
    """
    
    def __init__(self, config_path: str = "brain/config/config.yaml"):
        self._config_path = config_path
        self._config_loader: Optional[ConfigLoader] = None
        
        # Componentes
        self._orchestrator: Optional[BotOrchestrator] = None
        self._telegram: Optional[object] = None
        self._advisor: Optional[object] = None
        self._brain: Optional[BrainService] = None
        
        # Controle
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Inicializa todos os componentes"""
        logger.info("=" * 60)
        logger.info("BRAIN Trading System - Iniciando...")
        logger.info("=" * 60)
        
        # Carregar configuração
        logger.info("Carregando configurações...")
        self._config_loader = ConfigLoader(self._config_path)
        config = self._config_loader.config
        
        # Inicializar Brain Service
        logger.info("Inicializando Brain Service...")
        self._brain = BrainService()
        await self._brain.initialize()
        
        # Inicializar Orchestrator
        logger.info("Inicializando Bot Orchestrator...")
        self._orchestrator = get_orchestrator()
        await self._orchestrator.initialize(self._config_path)
        
        # Inicializar Telegram
        telegram_config = config.telegram
        if telegram_config and telegram_config.get("enabled", False):
            logger.info("Inicializando Telegram Bot...")
            self._telegram = get_telegram_bot()
            await self._telegram.initialize(
                token=telegram_config.get("token"),
                chat_id=telegram_config.get("chat_id"),
                admin_ids=telegram_config.get("admin_ids", [])
            )
            
            # Registrar callbacks
            self._telegram.set_command_handler("status", self._get_status)
            self._telegram.set_command_handler("positions", self._get_positions)
            self._telegram.set_command_handler("briefing", self._get_briefing)
            self._telegram.set_command_handler("pause", self._pause_all)
            self._telegram.set_command_handler("resume", self._resume_all)
        
        # Inicializar Market Advisor
        logger.info("Inicializando Market Advisor...")
        self._advisor = create_market_advisor(self._brain, self._telegram)
        
        logger.info("Inicialização completa!")
    
    async def start(self):
        """Inicia a aplicação"""
        if self._running:
            return
        
        self._running = True
        
        logger.info("Iniciando componentes...")
        
        # Iniciar Orchestrator (inicia os bots)
        await self._orchestrator.start()
        
        # Iniciar Advisor
        await self._advisor.start()
        
        logger.info("=" * 60)
        logger.info("BRAIN Trading System - ATIVO")
        logger.info("=" * 60)
        
        # Enviar notificação
        if self._telegram:
            await self._telegram.send_message(
                "🚀 <b>BRAIN Trading System Iniciado!</b>\n\n"
                f"Bots ativos: {len(self._orchestrator.list_bots())}"
            )
    
    async def stop(self):
        """Para a aplicação"""
        if not self._running:
            return
        
        logger.info("Parando BRAIN Trading System...")
        
        # Notificar
        if self._telegram:
            await self._telegram.send_message(
                "⏹️ <b>BRAIN Trading System Parando...</b>"
            )
        
        # Parar componentes
        if self._advisor:
            await self._advisor.stop()
        
        if self._orchestrator:
            await self._orchestrator.stop()
        
        if self._telegram:
            await self._telegram.shutdown()
        
        if self._brain:
            await self._brain.shutdown()
        
        self._running = False
        self._shutdown_event.set()
        
        logger.info("BRAIN Trading System parado")
    
    async def run(self):
        """Executa a aplicação até receber sinal de parada"""
        await self.initialize()
        await self.start()
        
        # Aguardar shutdown
        await self._shutdown_event.wait()
    
    # ==========================================================================
    # CALLBACKS PARA TELEGRAM
    # ==========================================================================
    
    async def _get_status(self) -> str:
        """Retorna status formatado"""
        status = self._orchestrator.get_status()
        
        return (
            f"<b>Bots:</b> {status['stats']['running_bots']}/{status['stats']['total_bots']} ativos\n"
            f"<b>Posições:</b> {status['stats']['total_positions']}\n"
            f"<b>Lucro Hoje:</b> ${status['stats']['total_profit_today']:.2f}"
        )
    
    async def _get_positions(self) -> str:
        """Retorna posições formatadas"""
        status = self._orchestrator.get_status()
        
        if status['stats']['total_positions'] == 0:
            return "Nenhuma posição aberta."
        
        text = ""
        for bot_id, bot_status in status.get('bots', {}).items():
            if bot_status.get('positions', 0) > 0:
                text += f"<b>{bot_status['symbol']}:</b> {bot_status['positions']} posição(ões)\n"
        
        return text or "Nenhuma posição aberta."
    
    async def _get_briefing(self) -> str:
        """Retorna briefing do mercado"""
        return await self._advisor.generate_briefing()
    
    async def _pause_all(self):
        """Pausa todos os bots"""
        await self._orchestrator.pause_all()
    
    async def _resume_all(self):
        """Resume todos os bots"""
        await self._orchestrator.resume_all()


async def main():
    """Função principal"""
    # Setup logging
    setup_logging()
    
    # Criar aplicação
    app = BRAINApplication()
    
    # Handler de sinais
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Sinal de shutdown recebido")
        asyncio.create_task(app.stop())
    
    # Registrar handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows
            signal.signal(sig, lambda s, f: signal_handler())
    
    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário")
        await app.stop()
    except Exception as e:
        logger.critical(f"Erro fatal: {e}")
        await app.stop()
        raise


if __name__ == "__main__":
    asyncio.run(main())
