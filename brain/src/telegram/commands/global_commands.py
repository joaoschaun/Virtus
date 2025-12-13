"""
BRAIN - Global Telegram Commands
Comandos globais do sistema
"""

from datetime import datetime
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes

from ...core.logger import get_logger
from ...orchestrator.bot_orchestrator import get_orchestrator
from ...brain.brain_service import get_brain
from ...risk.risk_manager import get_risk_manager

logger = get_logger("telegram.commands")


class GlobalCommands:
    """
    Comandos globais do Telegram
    
    Comandos disponíveis:
    - /start - Iniciar bot
    - /help - Ajuda
    - /status - Status geral do sistema
    - /positions - Todas as posições abertas
    - /risk - Relatório de risco
    - /stop_all - Parar todos os bots
    - /start_all - Iniciar todos os bots
    """
    
    def __init__(self, authorized_users: list = None):
        self._authorized = authorized_users or []
        self._orchestrator = None
        self._brain = None
    
    async def _check_auth(self, update: Update) -> bool:
        """Verifica se usuário está autorizado"""
        user_id = update.effective_user.id
        if self._authorized and user_id not in self._authorized:
            await update.message.reply_text("⛔ Acesso não autorizado.")
            return False
        return True
    
    def _get_orchestrator(self):
        """Obtém instância do orchestrator"""
        if self._orchestrator is None:
            self._orchestrator = get_orchestrator()
        return self._orchestrator
    
    def _get_brain(self):
        """Obtém instância do brain"""
        if self._brain is None:
            self._brain = get_brain()
        return self._brain
    
    # ==========================================================================
    # COMANDOS
    # ==========================================================================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /start"""
        user = update.effective_user
        
        message = (
            f"👋 Olá {user.first_name}!\n\n"
            "🧠 **BRAIN Trading System**\n"
            "Sistema Multi-Bot de Trading Automatizado\n\n"
            "📋 Comandos disponíveis:\n"
            "/status - Status do sistema\n"
            "/positions - Posições abertas\n"
            "/risk - Relatório de risco\n"
            "/briefing - Análise do dia\n"
            "/help - Ajuda completa"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /help"""
        message = (
            "📚 **Comandos Disponíveis**\n\n"
            "**Sistema:**\n"
            "/status - Status geral\n"
            "/health - Saúde dos componentes\n"
            "/risk - Relatório de risco\n\n"
            "**Trading:**\n"
            "/positions - Posições abertas\n"
            "/today - Trades do dia\n"
            "/performance - Performance\n\n"
            "**Bots:**\n"
            "/bots - Lista de bots\n"
            "/gold - Status bot GOLD\n"
            "/euro - Status bot EURO\n"
            "/gbp - Status bot GBP\n\n"
            "**Controle:**\n"
            "/pause [bot] - Pausar\n"
            "/resume [bot] - Retomar\n"
            "/stop_all - Parar todos\n\n"
            "**Advisor:**\n"
            "/briefing - Análise diária\n"
            "/news - Últimas notícias\n"
            "/calendar - Calendário"
        )
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /status - Status geral do sistema"""
        if not await self._check_auth(update):
            return
        
        try:
            orchestrator = self._get_orchestrator()
            brain = self._get_brain()
            risk = get_risk_manager()
            
            # Status dos bots
            bots_status = orchestrator.get_status() if orchestrator else {}
            
            # Status do brain
            brain_status = await brain.get_status() if brain else {}
            
            # Risk report
            risk_report = risk.get_risk_report() if risk else {}
            
            # Formatar mensagem
            running_bots = sum(1 for b in bots_status.get("bots", {}).values() 
                             if b.get("state") == "running")
            total_bots = len(bots_status.get("bots", {}))
            
            total_positions = risk_report.get("total_positions", 0)
            total_risk = risk_report.get("total_risk_percent", 0)
            daily_pnl = risk_report.get("daily_pnl", 0)
            risk_level = risk_report.get("risk_level", "unknown")
            
            # Emoji por nível de risco
            risk_emoji = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🟠",
                "critical": "🔴"
            }.get(risk_level, "⚪")
            
            message = (
                "📊 **Status do Sistema**\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"🤖 **Bots:** {running_bots}/{total_bots} ativos\n"
                f"📈 **Posições:** {total_positions}\n"
                f"💰 **P&L Diário:** ${daily_pnl:+.2f}\n"
                f"{risk_emoji} **Risco:** {risk_level.upper()} ({total_risk:.1f}%)\n\n"
                f"🧠 **Brain:** {'✅ Ativo' if brain_status.get('running') else '❌ Inativo'}\n"
                f"📡 **Cache:** {brain_status.get('cache_type', 'N/A')}\n"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Erro no comando status: {e}")
            await update.message.reply_text(f"❌ Erro ao obter status: {e}")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /positions - Lista posições abertas"""
        if not await self._check_auth(update):
            return
        
        try:
            orchestrator = self._get_orchestrator()
            
            if not orchestrator:
                await update.message.reply_text("❌ Orchestrator não disponível")
                return
            
            positions = await orchestrator.get_all_positions()
            
            if not positions:
                await update.message.reply_text("📭 Nenhuma posição aberta.")
                return
            
            message = "📊 **Posições Abertas**\n\n"
            total_profit = 0
            
            for pos in positions:
                direction = "🟢" if pos.get("direction") == "buy" else "🔴"
                profit = pos.get("profit", 0)
                total_profit += profit
                
                message += (
                    f"{direction} **{pos.get('symbol')}**\n"
                    f"   Vol: {pos.get('volume')} | "
                    f"P&L: ${profit:+.2f}\n"
                )
            
            message += f"\n💰 **Total:** ${total_profit:+.2f}"
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Erro no comando positions: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")
    
    async def cmd_risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /risk - Relatório de risco"""
        if not await self._check_auth(update):
            return
        
        try:
            risk = get_risk_manager()
            report = risk.get_risk_report()
            
            limits = report.get("limits", {})
            
            message = (
                "⚠️ **Relatório de Risco**\n\n"
                f"🎚️ **Nível:** {report.get('risk_level', 'N/A').upper()}\n"
                f"📊 **Risco Total:** {report.get('total_risk_percent', 0):.1f}%\n"
                f"📉 **Drawdown:** {report.get('current_drawdown', 0):.1f}%\n\n"
                f"📈 **Posições:** {report.get('total_positions', 0)}/{limits.get('max_positions', 0)}\n"
                f"🔄 **Trades Hoje:** {report.get('daily_trades', 0)}/{limits.get('max_daily_trades', 0)}\n"
                f"💰 **P&L Diário:** ${report.get('daily_pnl', 0):+.2f}\n\n"
                f"🚦 **Pode operar:** {'✅ Sim' if report.get('can_trade') else '❌ Não'}"
            )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Erro no comando risk: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")
    
    async def cmd_bots(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /bots - Lista bots"""
        if not await self._check_auth(update):
            return
        
        try:
            orchestrator = self._get_orchestrator()
            
            if not orchestrator:
                await update.message.reply_text("❌ Orchestrator não disponível")
                return
            
            status = orchestrator.get_status()
            bots = status.get("bots", {})
            
            if not bots:
                await update.message.reply_text("📭 Nenhum bot registrado.")
                return
            
            message = "🤖 **Bots Registrados**\n\n"
            
            for bot_id, info in bots.items():
                state = info.get("state", "unknown")
                state_emoji = {
                    "running": "🟢",
                    "paused": "🟡",
                    "stopped": "🔴",
                    "error": "❌"
                }.get(state, "⚪")
                
                symbol = info.get("symbol", "N/A")
                trades = info.get("trades_today", 0)
                pnl = info.get("daily_pnl", 0)
                
                message += (
                    f"{state_emoji} **{bot_id}** ({symbol})\n"
                    f"   Status: {state} | Trades: {trades} | P&L: ${pnl:+.2f}\n\n"
                )
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Erro no comando bots: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")
    
    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /pause [bot_id] - Pausar bot"""
        if not await self._check_auth(update):
            return
        
        try:
            orchestrator = self._get_orchestrator()
            
            if not orchestrator:
                await update.message.reply_text("❌ Orchestrator não disponível")
                return
            
            args = context.args
            
            if args:
                # Pausar bot específico
                bot_id = args[0]
                success = await orchestrator.pause_bot(bot_id)
                
                if success:
                    await update.message.reply_text(f"⏸️ Bot **{bot_id}** pausado.", parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"❌ Falha ao pausar {bot_id}")
            else:
                # Pausar todos
                await orchestrator.pause_all()
                await update.message.reply_text("⏸️ **Todos os bots pausados.**", parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Erro no comando pause: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")
    
    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /resume [bot_id] - Retomar bot"""
        if not await self._check_auth(update):
            return
        
        try:
            orchestrator = self._get_orchestrator()
            
            if not orchestrator:
                await update.message.reply_text("❌ Orchestrator não disponível")
                return
            
            args = context.args
            
            if args:
                bot_id = args[0]
                success = await orchestrator.resume_bot(bot_id)
                
                if success:
                    await update.message.reply_text(f"▶️ Bot **{bot_id}** retomado.", parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"❌ Falha ao retomar {bot_id}")
            else:
                await orchestrator.resume_all()
                await update.message.reply_text("▶️ **Todos os bots retomados.**", parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Erro no comando resume: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")
    
    async def cmd_stop_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para /stop_all - Parar todos os bots"""
        if not await self._check_auth(update):
            return
        
        try:
            orchestrator = self._get_orchestrator()
            
            if orchestrator:
                await orchestrator.stop_all()
                await update.message.reply_text(
                    "🛑 **Todos os bots foram parados.**\n"
                    "Use /start_all para reiniciar.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Orchestrator não disponível")
                
        except Exception as e:
            logger.error(f"Erro no comando stop_all: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")
