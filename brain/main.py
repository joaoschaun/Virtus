"""
VIRTUS Trading System
======================

Sistema de trading automatizado multi-símbolo com inteligência centralizada.

Componentes principais:
- Brain: Serviço central de dados (APIs, cache, orçamento)
- Bots: Traders independentes por símbolo
- Orchestrator: Gerenciador central de bots
- Advisor: Consultor de mercado via Telegram
- Risk: Gerenciamento centralizado de risco

Uso:
    python main.py [--mode=MODE] [--config=PATH]
    
Modos:
    full: Sistema completo (padrão)
    advisor: Apenas assessor de mercado
    backtest: Modo de backtesting
"""

import asyncio
import signal
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# Adiciona diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core import Config, VirtusLogger
from src.core.exceptions import VirtusError
from src.brain import BrainService
from src.mt5 import MT5Connection
from src.telegram import TelegramService
from src.advisor import MarketAdvisor
from src.orchestrator import BotOrchestrator
from src.risk import RiskManager


class VirtusSystem:
    """
    Sistema principal VIRTUS.
    
    Coordena inicialização e execução de todos os componentes.
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.logger = VirtusLogger.get_logger("virtus")
        
        # Componentes
        self.config: Optional[Config] = None
        self.brain: Optional[BrainService] = None
        self.mt5: Optional[MT5Connection] = None
        self.telegram: Optional[TelegramService] = None
        self.advisor: Optional[MarketAdvisor] = None
        self.orchestrator: Optional[BotOrchestrator] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # Estado
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self) -> bool:
        """Inicializa todos os componentes do sistema."""
        try:
            self.logger.info("=" * 60)
            self.logger.info("🚀 VIRTUS Trading System v3.0")
            self.logger.info("=" * 60)
            self.logger.info(f"⏰ Iniciando: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 1. Carrega configuração
            self.logger.info("📋 Carregando configuração...")
            self.config = Config.from_yaml(self.config_path)
            self.logger.success("✅ Configuração carregada")
            
            # 2. Inicializa MT5
            self.logger.info("📊 Conectando ao MT5...")
            self.mt5 = await MT5Connection.get_instance()
            if not await self.mt5.connect(
                login=self.config.mt5.login,
                password=self.config.mt5.password,
                server=self.config.mt5.server,
            ):
                raise VirtusError("Falha ao conectar MT5")
            self.logger.success("✅ MT5 conectado")
            
            # 3. Inicializa Risk Manager
            self.logger.info("⚠️ Inicializando Risk Manager...")
            self.risk_manager = RiskManager(self.config.risk)
            
            # Obtém saldo da conta
            account_info = self.mt5.account_info
            if account_info:
                await self.risk_manager.update_account(
                    balance=account_info.get('balance', 0),
                    equity=account_info.get('equity', 0)
                )
            self.logger.success("✅ Risk Manager inicializado")
            
            # 4. Inicializa Brain
            self.logger.info("🧠 Inicializando Brain...")
            self.brain = await BrainService.get_instance()
            self.logger.success("✅ Brain inicializado")
            
            # 5. Inicializa Telegram (opcional)
            self.logger.info("📱 Inicializando Telegram...")
            try:
                if self.config.telegram.token and self.config.telegram.chat_id:
                    self.telegram = await TelegramService.get_instance()
                    if self.telegram._initialized:
                        await self.telegram.send_message(
                            "🟢 *VIRTUS iniciando...*\n\n"
                            f"📊 Símbolos: {', '.join([b.symbol for b in self.config.get_enabled_bots()])}\n"
                            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                        )
                    self.logger.success("✅ Telegram inicializado")
                else:
                    self.logger.warning("⚠️ Telegram não configurado - pulando")
            except Exception as e:
                self.logger.warning(f"⚠️ Telegram não disponível: {e}")
            
            # 6. Inicializa Advisor
            self.logger.info("📈 Inicializando Market Advisor...")
            self.advisor = await MarketAdvisor.get_instance()
            self.logger.success("✅ Market Advisor inicializado")
            
            # 7. Inicializa Orchestrator
            self.logger.info("🎭 Inicializando Orchestrator...")
            self.orchestrator = BotOrchestrator(self.config)
            if not await self.orchestrator.initialize():
                raise VirtusError("Falha ao inicializar Orchestrator")
            self.logger.success("✅ Orchestrator inicializado")
            
            self.logger.info("=" * 60)
            self.logger.success("✅ Sistema VIRTUS inicializado com sucesso!")
            self.logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na inicialização: {e}")
            return False
    
    async def start(self) -> None:
        """Inicia o sistema."""
        if not self.orchestrator:
            raise VirtusError("Sistema não inicializado")
        
        self._running = True
        
        # Inicia Advisor (briefings, alertas)
        await self.advisor.start()
        
        # Inicia Orchestrator (bots)
        await self.orchestrator.start()
        
        self.logger.info("▶️ Sistema VIRTUS em execução")
        
        # Notifica via Telegram (se disponível)
        if self.telegram and self.telegram._initialized:
            try:
                running_bots = len(self.orchestrator.registry.get_running())
                total_bots = self.orchestrator.registry.count()
                
                await self.telegram.send_message(
                    f"🟢 *VIRTUS Online*\n\n"
                    f"🤖 Bots ativos: {running_bots}/{total_bots}\n"
                    f"📊 Símbolos:\n"
                    + "\n".join([f"  • {b.symbol}" for b in self.orchestrator.registry.get_all()])
                    + f"\n\n⏰ {datetime.now().strftime('%H:%M:%S')}"
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Falha ao enviar notificação Telegram: {e}")
        
        # Aguarda shutdown
        await self._shutdown_event.wait()
    
    async def stop(self) -> None:
        """Para o sistema."""
        if not self._running:
            return
        
        self.logger.info("🛑 Parando sistema VIRTUS...")
        self._running = False
        
        # Para Advisor
        if self.advisor:
            await self.advisor.stop()
        
        # Para Orchestrator
        if self.orchestrator:
            await self.orchestrator.stop()
        
        # Desconecta MT5
        if self.mt5:
            await self.mt5.disconnect()
        
        # Notifica via Telegram
        if self.telegram and self.telegram._initialized:
            try:
                await self.telegram.send_message(
                    f"🔴 *VIRTUS Offline*\n\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Falha ao enviar notificação Telegram: {e}")
        
        self.logger.info("✅ Sistema VIRTUS parado")
        
        # Sinaliza shutdown
        self._shutdown_event.set()
    
    async def run_advisor_only(self) -> None:
        """Executa apenas o advisor (sem trading)."""
        if not await self.initialize():
            return
        
        self._running = True
        
        # Inicia apenas Advisor
        await self.advisor.start()
        
        self.logger.info("▶️ Modo Advisor ativo")
        
        if self.telegram and self.telegram._initialized:
            try:
                await self.telegram.send_message(
                    f"📈 *VIRTUS Advisor Online*\n\n"
                    f"Modo: Apenas assessoria\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Falha ao enviar notificação Telegram: {e}")
        
        # Aguarda shutdown
        await self._shutdown_event.wait()
    
    def get_status(self) -> dict:
        """Retorna status do sistema."""
        status = {
            'running': self._running,
            'timestamp': datetime.now().isoformat(),
        }
        
        if self.orchestrator:
            status['orchestrator'] = self.orchestrator.get_status()
        
        if self.risk_manager:
            status['risk'] = self.risk_manager.get_status()
        
        if self.brain:
            status['brain'] = {
                'budget_remaining': self.brain.budget_manager.get_remaining_budget(),
            }
        
        return status


# Instância global
_system: Optional[VirtusSystem] = None


def get_system() -> Optional[VirtusSystem]:
    """Obtém instância do sistema."""
    return _system


async def main(mode: str = "full", config_path: str = "config/config.yaml"):
    """Função principal."""
    global _system
    
    # Cria sistema
    _system = VirtusSystem(config_path)
    
    # Configura handlers de sinal
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(_system.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows não suporta add_signal_handler
            pass
    
    try:
        if mode == "advisor":
            await _system.run_advisor_only()
        elif mode == "full":
            if await _system.initialize():
                await _system.start()
        else:
            print(f"Modo desconhecido: {mode}")
            return
            
    except KeyboardInterrupt:
        pass
    finally:
        await _system.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VIRTUS Trading System")
    parser.add_argument(
        "--mode",
        choices=["full", "advisor", "backtest"],
        default="full",
        help="Modo de execução"
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Caminho do arquivo de configuração"
    )
    
    args = parser.parse_args()
    
    # Windows: necessário para asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main(args.mode, args.config))
