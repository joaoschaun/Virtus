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
from src.integrations.dashboard_bridge import DashboardBridge, get_dashboard_bridge


class VirtusSystem:
    """
    Sistema principal VIRTUS.
    
    Coordena inicialização e execução de todos os componentes.
    """
    
    def __init__(self, config_path: str = None):
        # Usa path absoluto baseado no diretório do script se não fornecido
        if config_path is None:
            script_dir = Path(__file__).resolve().parent  # resolve() garante caminho absoluto
            config_path = str(script_dir / "config" / "config.yaml")
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
        self.dashboard_bridge: Optional[DashboardBridge] = None
        
        # Estado
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._dashboard_task: Optional[asyncio.Task] = None
    
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
            
            # 8. Inicializa Dashboard Bridge
            self.logger.info("🔗 Inicializando Dashboard Bridge...")
            try:
                self.dashboard_bridge = await get_dashboard_bridge()
                await self.dashboard_bridge.update_system_status("initializing")
                await self.dashboard_bridge.update_mt5_status(True, account_info)
                self.logger.success("✅ Dashboard Bridge inicializado")
            except Exception as e:
                self.logger.warning(f"⚠️ Dashboard Bridge não disponível: {e}")
            
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
        
        # Atualiza Dashboard
        if self.dashboard_bridge:
            await self.dashboard_bridge.update_system_status("running")
            # Inicia task de atualização periódica do dashboard
            self._dashboard_task = asyncio.create_task(self._dashboard_update_loop())
        
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
        
        # Para task de dashboard
        if self._dashboard_task:
            self._dashboard_task.cancel()
        
        # Atualiza Dashboard
        if self.dashboard_bridge:
            await self.dashboard_bridge.update_system_status("offline")
            await self.dashboard_bridge.stop()
        
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
    
    async def _dashboard_update_loop(self):
        """Loop de atualização periódica do dashboard."""
        while self._running:
            try:
                if self.dashboard_bridge:
                    # Atualiza status dos bots
                    if self.orchestrator:
                        bots_data = []
                        for bot in self.orchestrator.registry.get_all():
                            bots_data.append({
                                "symbol": bot.symbol,
                                "status": "running" if bot.is_running else "stopped",
                                "trades_today": getattr(bot, 'trades_today', 0),
                                "profit_today": getattr(bot, 'profit_today', 0),
                            })
                        await self.dashboard_bridge.update_bots(bots_data)
                    
                    # Atualiza posições via MT5 diretamente
                    try:
                        import MetaTrader5 as mt5
                        positions_raw = mt5.positions_get()
                        positions_data = []
                        if positions_raw:
                            for p in positions_raw:
                                positions_data.append({
                                    "ticket": p.ticket,
                                    "symbol": p.symbol,
                                    "type": "BUY" if p.type == 0 else "SELL",
                                    "volume": p.volume,
                                    "profit": p.profit,
                                    "open_price": p.price_open,
                                    "current_price": p.price_current,
                                })
                        await self.dashboard_bridge.update_positions(positions_data)
                    except Exception:
                        pass
                    
                    # Atualiza métricas
                    if self.risk_manager:
                        risk_status = self.risk_manager.get_status()
                        metrics = {
                            "daily_pnl": risk_status.get('metrics', {}).get('daily_loss', 0),
                            "max_drawdown": risk_status.get('metrics', {}).get('max_drawdown', 0),
                            "exposure": risk_status.get('metrics', {}).get('total_exposure', 0),
                            "balance": risk_status.get('balance', 0),
                            "equity": risk_status.get('equity', 0),
                        }
                        await self.dashboard_bridge.update_metrics(metrics)
                    
                    # Atualiza conta MT5
                    if self.mt5 and self.mt5.account_info:
                        await self.dashboard_bridge.update_mt5_status(True, self.mt5.account_info)
                
            except Exception as e:
                self.logger.warning(f"⚠️ Erro ao atualizar dashboard: {e}")
            
            await asyncio.sleep(5)  # Atualiza a cada 5 segundos
    
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
    
    # Calcula path padrão baseado no diretório do script
    script_dir = Path(__file__).resolve().parent
    default_config = str(script_dir / "config" / "config.yaml")
    
    parser.add_argument(
        "--config",
        default=default_config,
        help="Caminho do arquivo de configuração"
    )
    
    args = parser.parse_args()
    
    # Windows: necessário para asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main(args.mode, args.config))
