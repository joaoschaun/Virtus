"""
VIRTUS Telegram Bot - Bot Interativo com Polling
=================================================

Este script inicia o bot do Telegram em modo polling,
permitindo receber e responder comandos dos usuários.

Comandos disponíveis:
- /start - Inicia o bot
- /briefing - Briefing diário completo
- /sentimento [XAUUSD|EURUSD|GBPUSD] - Sentimento do ativo
- /noticias - Notícias principais
- /calendario - Eventos econômicos
- /ajuda - Lista de comandos

Execute: python run_telegram_bot.py
"""
import asyncio
import sys
import signal
import aiohttp
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, '.')


class VirtusTelegramBot:
    """Bot interativo do Telegram com polling."""
    
    def __init__(self):
        self.telegram = None
        self.brain = None
        self.running = False
        self.last_update_id = 0
        self._token = None
        self._chat_id = None
        self._session = None
    
    async def initialize(self):
        """Inicializa serviços."""
        print("🤖 Inicializando VIRTUS Telegram Bot...")
        
        from src.core.config import get_config
        from src.telegram import TelegramService
        from src.brain import BrainService
        import aiohttp
        import ssl
        
        config = get_config()
        self._token = config.telegram.token
        self._chat_id = str(config.telegram.chat_id)
        
        # Session para polling
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self._session = aiohttp.ClientSession(connector=connector)
        
        # Serviços
        self.telegram = TelegramService()
        await self.telegram.initialize()
        print("   ✅ Telegram Service OK")
        
        self.brain = BrainService()
        await self.brain.initialize()
        print("   ✅ Brain Service OK")
        
        print("✅ Bot inicializado!")
    
    async def _api_call(self, method: str, data: dict = None, timeout: int = 60) -> dict:
        """Faz chamada à API do Telegram."""
        url = f"https://api.telegram.org/bot{self._token}/{method}"
        try:
            async with self._session.post(
                url, 
                json=data or {}, 
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                result = await resp.json()
                return result
        except asyncio.TimeoutError:
            return {'ok': False, 'error': 'timeout'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}
    
    async def get_updates(self, offset: int = 0) -> list:
        """Busca atualizações (mensagens novas)."""
        data = {
            'offset': offset,
            'timeout': 30,
            'allowed_updates': ['message']
        }
        result = await self._api_call('getUpdates', data, timeout=35)
        if result.get('ok'):
            return result.get('result', [])
        return []
    
    async def send_reply(self, chat_id: str, text: str):
        """Envia resposta."""
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        await self._api_call('sendMessage', data)
    
    async def send_typing(self, chat_id: str):
        """Mostra indicador de digitação."""
        await self._api_call('sendChatAction', {'chat_id': chat_id, 'action': 'typing'})
    
    # =========================================================================
    # HANDLERS DE COMANDOS
    # =========================================================================
    
    async def handle_start(self, chat_id: str, user_name: str):
        """Handler do /start."""
        text = f"""🤖 *Olá {user_name}!*

Sou o *VIRTUS Consultor de Mercado*, seu assistente de análise!

*📊 Análises de Mercado:*
/briefing - Resumo diário completo
/sentimento XAUUSD - Sentimento do ativo
/noticias - Notícias principais
/calendario - Eventos econômicos

*🤖 Monitoramento de Bots:*
/bots - Status dos bots de trading
/posicoes - Posições abertas
/conta - Informações da conta MT5
/lucro - P&L do dia

/ajuda - Ver todos os comandos"""
        await self.send_reply(chat_id, text)
    
    async def handle_help(self, chat_id: str):
        """Handler do /help."""
        text = """📚 *COMANDOS DISPONÍVEIS*

*📊 Análises de Mercado:*
/briefing - Resumo diário completo
/sentimento XAUUSD - Análise de sentimento
/noticias - Últimas notícias do mercado
/calendario - Eventos econômicos

*🤖 Monitoramento de Bots:*
/bots - Status de todos os bots
/posicoes - Posições abertas no MT5
/conta - Saldo e info da conta
/lucro - P&L diário

*Símbolos suportados:*
🥇 XAUUSD (Ouro)
💶 EURUSD (Euro)
💷 GBPUSD (Libra)

*Exemplos:*
`/sentimento ouro`
`/bots`
`/posicoes`"""
        await self.send_reply(chat_id, text)
    
    async def handle_briefing(self, chat_id: str):
        """Handler do /briefing."""
        await self.send_typing(chat_id)
        
        try:
            # Gera briefing
            briefing = await self.brain.generate_daily_briefing(['XAUUSD', 'EURUSD', 'GBPUSD'])
            
            # Formata
            lines = [
                "☀️ *BOM DIA! BRIEFING DO MERCADO*",
                f"📅 {briefing.date.strftime('%d/%m/%Y %H:%M')}",
                ""
            ]
            
            # Sentimentos
            if briefing.sentiments:
                lines.append("📊 *SENTIMENTO POR ATIVO:*")
                for symbol, sentiment in briefing.sentiments.items():
                    emoji = "🟢" if sentiment.overall_sentiment > 0.1 else "🔴" if sentiment.overall_sentiment < -0.1 else "🟡"
                    lines.append(f"  {emoji} {symbol}: {sentiment.sentiment_level.value} ({sentiment.overall_sentiment:+.2f})")
                lines.append("")
            
            # Notícias
            if briefing.top_news:
                lines.append("📰 *PRINCIPAIS NOTÍCIAS:*")
                for news in briefing.top_news[:3]:
                    emoji = "🟢" if news.sentiment_score > 0.2 else "🔴" if news.sentiment_score < -0.2 else "🟡"
                    lines.append(f"  {emoji} {news.title[:70]}...")
                lines.append("")
            
            lines.append(f"⏰ Gerado às {datetime.now().strftime('%H:%M')}")
            
            await self.send_reply(chat_id, "\n".join(lines))
            
        except Exception as e:
            await self.send_reply(chat_id, f"❌ Erro ao gerar briefing: {str(e)[:100]}")
    
    async def handle_sentiment(self, chat_id: str, symbol: str):
        """Handler do /sentiment."""
        await self.send_typing(chat_id)
        
        # Resolve aliases
        aliases = {
            'gold': 'XAUUSD', 'ouro': 'XAUUSD', 'xau': 'XAUUSD',
            'euro': 'EURUSD', 'eur': 'EURUSD',
            'libra': 'GBPUSD', 'gbp': 'GBPUSD', 'cable': 'GBPUSD'
        }
        symbol = aliases.get(symbol.lower(), symbol.upper())
        
        if symbol not in ['XAUUSD', 'EURUSD', 'GBPUSD']:
            await self.send_reply(chat_id, f"❌ Símbolo não suportado: {symbol}\n\nUse: XAUUSD, EURUSD ou GBPUSD")
            return
        
        try:
            sentiment = await self.brain.get_sentiment(symbol)
            
            emoji = "🟢" if sentiment.overall_sentiment > 0.1 else "🔴" if sentiment.overall_sentiment < -0.1 else "🟡"
            
            # Traduz o nível de sentimento
            niveis = {
                'BULLISH': 'ALTISTA', 'BEARISH': 'BAIXISTA', 'NEUTRAL': 'NEUTRO',
                'VERY_BULLISH': 'MUITO ALTISTA', 'VERY_BEARISH': 'MUITO BAIXISTA'
            }
            nivel = niveis.get(sentiment.sentiment_level.value, sentiment.sentiment_level.value)
            
            text = f"""📊 *SENTIMENTO: {symbol}*

{emoji} *Nível:* {nivel}
📈 *Score:* {sentiment.overall_sentiment:+.2f}
📰 *Notícias analisadas:* {sentiment.news_count}

_{sentiment.explanation_pt}_

⏰ {sentiment.timestamp.strftime('%H:%M:%S')}"""
            
            await self.send_reply(chat_id, text)
            
        except Exception as e:
            await self.send_reply(chat_id, f"❌ Erro ao analisar {symbol}: {str(e)[:100]}")
    
    async def handle_news(self, chat_id: str):
        """Handler do /noticias."""
        await self.send_typing(chat_id)
        
        try:
            news = await self.brain.get_news(symbols=['XAUUSD', 'EURUSD', 'GBPUSD'], limit=5)
            
            lines = ["📰 *NOTÍCIAS DO MERCADO*", ""]
            for item in news[:5]:
                emoji = "🟢" if item.sentiment_score > 0.2 else "🔴" if item.sentiment_score < -0.2 else "🟡"
                # Usa título em português se disponível
                titulo = item.title_pt if item.title_pt else self._traduzir_titulo(item.title)
                lines.append(f"{emoji} *{item.source}*")
                lines.append(f"   {titulo[:70]}")
                lines.append("")
            
            lines.append(f"⏰ {datetime.now().strftime('%H:%M')}")
            
            await self.send_reply(chat_id, "\n".join(lines))
            
        except Exception as e:
            await self.send_reply(chat_id, f"❌ Erro ao buscar notícias: {str(e)[:100]}")
    
    def _traduzir_titulo(self, titulo: str) -> str:
        """Traduz termos comuns do mercado para português."""
        traducoes = {
            'Gold': 'Ouro', 'gold': 'ouro',
            'Silver': 'Prata', 'silver': 'prata',
            'rises': 'sobe', 'falls': 'cai', 'drops': 'cai',
            'gains': 'ganha', 'loses': 'perde',
            'steady': 'estável', 'stable': 'estável',
            'higher': 'mais alto', 'lower': 'mais baixo',
            'bullish': 'altista', 'bearish': 'baixista',
            'rally': 'alta', 'decline': 'queda',
            'forecast': 'previsão', 'outlook': 'perspectiva',
            'traders': 'traders', 'investors': 'investidores',
            'market': 'mercado', 'markets': 'mercados',
            'prices': 'preços', 'price': 'preço',
            'support': 'suporte', 'resistance': 'resistência',
            'breakout': 'rompimento', 'breakdown': 'rompimento de baixa',
            'Dollar': 'Dólar', 'dollar': 'dólar',
            'Euro': 'Euro', 'Pound': 'Libra',
            'Fed': 'Fed', 'ECB': 'BCE',
            'rate': 'taxa', 'rates': 'taxas',
            'inflation': 'inflação', 'employment': 'emprego',
            'data': 'dados', 'report': 'relatório',
            'weekly': 'semanal', 'daily': 'diário', 'monthly': 'mensal',
            'ahead': 'antes de', 'after': 'após',
            'as': 'enquanto', 'amid': 'em meio a',
            'News': 'Notícias', 'news': 'notícias',
            'Update': 'Atualização', 'Analysis': 'Análise',
            'Forecast': 'Previsão', 'Price': 'Preço',
            'holds': 'mantém', 'hold': 'manter',
            'near': 'próximo de', 'above': 'acima de', 'below': 'abaixo de',
            'high': 'alta', 'low': 'baixa', 'record': 'recorde',
            'ATH': 'máxima histórica', 'ATL': 'mínima histórica',
        }
        resultado = titulo
        for en, pt in traducoes.items():
            resultado = resultado.replace(en, pt)
        return resultado
    
    async def handle_calendar(self, chat_id: str):
        """Handler do /calendario."""
        await self.send_typing(chat_id)
        
        try:
            events = await self.brain.get_economic_calendar()
            
            lines = ["📅 *EVENTOS ECONÔMICOS*", ""]
            
            impact_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}
            
            today_events = [e for e in events if e.timestamp.date() == datetime.now().date()]
            
            if today_events:
                for event in today_events[:10]:
                    emoji = impact_emoji.get(event.impact.value if hasattr(event.impact, 'value') else event.impact, '⚪')
                    time_str = event.timestamp.strftime('%H:%M')
                    name = event.name_pt or event.name
                    lines.append(f"{emoji} {time_str} - {name[:40]} ({event.currency})")
            else:
                lines.append("_Nenhum evento importante hoje_")
            
            lines.append(f"\n⏰ {datetime.now().strftime('%H:%M')}")
            
            await self.send_reply(chat_id, "\n".join(lines))
            
        except Exception as e:
            await self.send_reply(chat_id, f"❌ Erro ao buscar calendário: {str(e)[:100]}")
    
    # =========================================================================
    # HANDLERS DE MONITORAMENTO DOS BOTS
    # =========================================================================
    
    async def handle_bots(self, chat_id: str):
        """Handler do /bots - Status dos bots de trading."""
        await self.send_typing(chat_id)
        
        try:
            # Lê estado dos bots
            import json
            state_file = Path(__file__).parent / 'data' / 'bot_state.json'
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
            else:
                state = {}
            
            lines = ["🤖 *STATUS DOS BOTS DE TRADING*", ""]
            
            # Status do sistema
            system_status = state.get('system_status', 'offline')
            emoji_status = "🟢" if system_status == 'online' else "🔴"
            lines.append(f"{emoji_status} *Sistema:* {system_status.upper()}")
            
            # MT5
            mt5_connected = state.get('mt5_connected', False)
            emoji_mt5 = "🟢" if mt5_connected else "🔴"
            lines.append(f"{emoji_mt5} *MT5:* {'Conectado' if mt5_connected else 'Desconectado'}")
            lines.append("")
            
            # Bots configurados
            bot_configs = ['gold', 'euro', 'gbp']
            lines.append("📊 *BOTS CONFIGURADOS:*")
            
            bots_data = state.get('bots', [])
            if bots_data:
                for bot in bots_data:
                    symbol = bot.get('symbol', 'N/A')
                    status = bot.get('status', 'stopped')
                    trades = bot.get('trades_today', 0)
                    profit = bot.get('profit_today', 0)
                    
                    emoji = "🟢" if status == 'running' else "🟡" if status == 'paused' else "🔴"
                    profit_emoji = "📈" if profit >= 0 else "📉"
                    
                    lines.append(f"  {emoji} *{symbol}*")
                    lines.append(f"      Status: {status}")
                    lines.append(f"      Trades: {trades} | {profit_emoji} ${profit:.2f}")
            else:
                # Mostra configs disponíveis
                for bot_id in bot_configs:
                    config_file = Path(__file__).parent / 'config' / 'bots' / f'{bot_id}.yaml'
                    if config_file.exists():
                        import yaml
                        with open(config_file, 'r') as f:
                            cfg = yaml.safe_load(f)
                        
                        bot_cfg = cfg.get('bot', {})
                        name = bot_cfg.get('name', bot_id)
                        symbol = bot_cfg.get('symbol', 'N/A')
                        enabled = bot_cfg.get('enabled', False)
                        
                        emoji = "🟡" if enabled else "⚫"
                        lines.append(f"  {emoji} *{name}*")
                        lines.append(f"      Símbolo: {symbol}")
                        lines.append(f"      Config: {'Habilitado' if enabled else 'Desabilitado'}")
            
            lines.append("")
            lines.append(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
            lines.append("\n💡 _Use /posicoes para ver trades abertos_")
            
            await self.send_reply(chat_id, "\n".join(lines))
            
        except Exception as e:
            await self.send_reply(chat_id, f"❌ Erro ao buscar status dos bots: {str(e)[:100]}")
    
    async def handle_positions(self, chat_id: str):
        """Handler do /posicoes - Posições abertas no MT5."""
        await self.send_typing(chat_id)
        
        try:
            import MetaTrader5 as mt5
            
            if not mt5.initialize():
                await self.send_reply(chat_id, "❌ MT5 não está conectado.\n\nInicie o sistema principal primeiro.")
                return
            
            positions = mt5.positions_get()
            
            lines = ["📊 *POSIÇÕES ABERTAS*", ""]
            
            if positions:
                total_profit = 0
                for p in positions:
                    tipo = "🟢 COMPRA" if p.type == 0 else "🔴 VENDA"
                    profit_emoji = "📈" if p.profit >= 0 else "📉"
                    total_profit += p.profit
                    
                    lines.append(f"*{p.symbol}* - {tipo}")
                    lines.append(f"  📦 Volume: {p.volume}")
                    lines.append(f"  💰 Entrada: {p.price_open:.5f}")
                    lines.append(f"  📍 Atual: {p.price_current:.5f}")
                    lines.append(f"  {profit_emoji} Lucro: ${p.profit:.2f}")
                    if p.sl > 0:
                        lines.append(f"  🛑 SL: {p.sl:.5f}")
                    if p.tp > 0:
                        lines.append(f"  🎯 TP: {p.tp:.5f}")
                    lines.append("")
                
                total_emoji = "📈" if total_profit >= 0 else "📉"
                lines.append(f"*{total_emoji} TOTAL: ${total_profit:.2f}*")
            else:
                lines.append("_Nenhuma posição aberta no momento_")
            
            lines.append(f"\n⏰ {datetime.now().strftime('%H:%M:%S')}")
            
            await self.send_reply(chat_id, "\n".join(lines))
            
        except Exception as e:
            await self.send_reply(chat_id, f"❌ Erro ao buscar posições: {str(e)[:100]}")
    
    async def handle_account(self, chat_id: str):
        """Handler do /conta - Informações da conta MT5."""
        await self.send_typing(chat_id)
        
        try:
            import MetaTrader5 as mt5
            
            if not mt5.initialize():
                await self.send_reply(chat_id, "❌ MT5 não está conectado.\n\nInicie o sistema principal primeiro.")
                return
            
            account = mt5.account_info()
            
            if not account:
                await self.send_reply(chat_id, "❌ Não foi possível obter informações da conta.")
                return
            
            # Calcula lucro/perda do dia
            equity_change = account.equity - account.balance
            change_emoji = "📈" if equity_change >= 0 else "📉"
            
            text = f"""💳 *INFORMAÇÕES DA CONTA*

👤 *Nome:* {account.name}
🏦 *Corretora:* {account.company}
🖥️ *Servidor:* {account.server}

💰 *SALDO E CAPITAL:*
  💵 Saldo: ${account.balance:.2f}
  📊 Equity: ${account.equity:.2f}
  {change_emoji} Flutuante: ${equity_change:+.2f}

📈 *MARGEM:*
  🔒 Usada: ${account.margin:.2f}
  ✅ Livre: ${account.margin_free:.2f}
  📊 Nível: {account.margin_level:.1f}%

⚙️ *CONFIGURAÇÕES:*
  🔧 Alavancagem: 1:{account.leverage}
  💱 Moeda: {account.currency}

⏰ {datetime.now().strftime('%H:%M:%S')}"""
            
            await self.send_reply(chat_id, text)
            
        except Exception as e:
            await self.send_reply(chat_id, f"❌ Erro ao buscar conta: {str(e)[:100]}")
    
    async def handle_profit(self, chat_id: str):
        """Handler do /lucro - P&L diário."""
        await self.send_typing(chat_id)
        
        try:
            import MetaTrader5 as mt5
            from datetime import timedelta
            
            if not mt5.initialize():
                await self.send_reply(chat_id, "❌ MT5 não está conectado.")
                return
            
            # Trades de hoje
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            deals = mt5.history_deals_get(today, datetime.now())
            
            # Posições abertas
            positions = mt5.positions_get()
            floating = sum(p.profit for p in positions) if positions else 0
            
            # Calcula P&L realizado
            realized = 0
            trades_today = 0
            wins = 0
            losses = 0
            
            if deals:
                for deal in deals:
                    if deal.profit != 0:  # Ignora depósitos/saques
                        realized += deal.profit
                        trades_today += 1
                        if deal.profit > 0:
                            wins += 1
                        else:
                            losses += 1
            
            total_pnl = realized + floating
            pnl_emoji = "📈" if total_pnl >= 0 else "📉"
            realized_emoji = "✅" if realized >= 0 else "❌"
            floating_emoji = "🟢" if floating >= 0 else "🔴"
            
            win_rate = (wins / trades_today * 100) if trades_today > 0 else 0
            
            text = f"""💰 *P&L DO DIA*

{pnl_emoji} *TOTAL: ${total_pnl:+.2f}*

📊 *DETALHAMENTO:*
  {realized_emoji} Realizado: ${realized:+.2f}
  {floating_emoji} Flutuante: ${floating:+.2f}

📈 *ESTATÍSTICAS:*
  🔢 Trades: {trades_today}
  ✅ Ganhos: {wins}
  ❌ Perdas: {losses}
  🎯 Win Rate: {win_rate:.1f}%

⏰ {datetime.now().strftime('%H:%M:%S')}"""
            
            await self.send_reply(chat_id, text)
            
        except Exception as e:
            await self.send_reply(chat_id, f"❌ Erro ao calcular P&L: {str(e)[:100]}")
    
    async def handle_unknown(self, chat_id: str, text: str):
        """Handler para comandos desconhecidos."""
        await self.send_reply(chat_id, f"❓ Comando não reconhecido.\n\nDigite /ajuda para ver os comandos disponíveis.")
    
    # =========================================================================
    # POLLING LOOP
    # =========================================================================
    
    async def process_message(self, message: dict):
        """Processa uma mensagem recebida."""
        chat_id = str(message.get('chat', {}).get('id', ''))
        text = message.get('text', '').strip()
        user = message.get('from', {})
        user_name = user.get('first_name', 'Trader')
        
        if not text or not chat_id:
            return
        
        print(f"📩 [{datetime.now().strftime('%H:%M:%S')}] {user_name}: {text}")
        
        # Processa comandos
        if text.startswith('/'):
            parts = text.split()
            command = parts[0].lower().replace('@operadorvirtus_bot', '')
            args = parts[1:] if len(parts) > 1 else []
            
            if command in ['/start', '/iniciar']:
                await self.handle_start(chat_id, user_name)
            elif command in ['/help', '/ajuda']:
                await self.handle_help(chat_id)
            elif command in ['/briefing', '/resumo']:
                await self.handle_briefing(chat_id)
            elif command in ['/sentiment', '/sentimento']:
                symbol = args[0] if args else 'XAUUSD'
                await self.handle_sentiment(chat_id, symbol)
            elif command in ['/news', '/noticias', '/notícias']:
                await self.handle_news(chat_id)
            elif command in ['/calendar', '/calendario', '/calendário']:
                await self.handle_calendar(chat_id)
            # Comandos de monitoramento de bots
            elif command in ['/bots', '/robos']:
                await self.handle_bots(chat_id)
            elif command in ['/positions', '/posicoes', '/posições']:
                await self.handle_positions(chat_id)
            elif command in ['/account', '/conta']:
                await self.handle_account(chat_id)
            elif command in ['/profit', '/lucro', '/pnl']:
                await self.handle_profit(chat_id)
            else:
                await self.handle_unknown(chat_id, text)
    
    async def polling_loop(self):
        """Loop de polling para receber mensagens."""
        print("\n" + "="*60)
        print("🤖 VIRTUS BOT INICIADO - Aguardando mensagens...")
        print("="*60)
        print("📱 Bot: @OperadorVirtus_bot")
        print("💡 Pressione Ctrl+C para parar")
        print("="*60 + "\n")
        
        self.running = True
        
        while self.running:
            try:
                updates = await self.get_updates(self.last_update_id + 1)
                
                for update in updates:
                    self.last_update_id = update.get('update_id', 0)
                    
                    if 'message' in update:
                        await self.process_message(update['message'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Erro no polling: {e}")
                await asyncio.sleep(5)
        
        print("\n🛑 Bot encerrado.")
    
    async def stop(self):
        """Para o bot."""
        self.running = False
        if self._session:
            await self._session.close()
    
    async def run(self):
        """Executa o bot."""
        await self.initialize()
        
        # Envia mensagem de início
        await self.telegram.send_message(
            "🤖 *VIRTUS Advisor Online!*\n\n"
            "Pronto para receber comandos.\n"
            "Digite /help para ver os comandos disponíveis."
        )
        
        await self.polling_loop()


async def main():
    bot = VirtusTelegramBot()
    
    # Handler para Ctrl+C
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        print("\n\n⚠️ Interrupção recebida. Encerrando...")
        asyncio.create_task(bot.stop())
    
    try:
        # Tenta adicionar handler de sinal (não funciona em todos os ambientes)
        loop.add_signal_handler(signal.SIGINT, signal_handler)
    except:
        pass
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ Ctrl+C detectado. Encerrando...")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
