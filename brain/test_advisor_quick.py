"""
VIRTUS Market Advisor - Script de Teste e Uso Direto
=====================================================

Execute este script para:
1. Testar o Advisor
2. Enviar briefings ao Telegram
3. Consultar sentimento de ativos

Uso: python test_advisor_quick.py [comando]
Comandos: briefing, sentiment, news, test
"""
import asyncio
import sys
sys.path.insert(0, '.')

class AdvisorRunner:
    def __init__(self):
        self.telegram = None
        self.brain = None
        self.advisor = None
    
    async def initialize(self):
        """Inicializa todos os serviços"""
        print("🔄 Inicializando serviços...")
        
        from src.telegram import TelegramService
        from src.brain import BrainService
        from src.advisor import MarketAdvisor
        from src.advisor.market_advisor import AdvisorConfig
        from src.core.scheduler import Scheduler
        
        # Telegram
        self.telegram = TelegramService()
        await self.telegram.initialize()
        print("   ✅ Telegram OK")
        
        # Brain
        self.brain = BrainService()
        await self.brain.initialize()
        print("   ✅ Brain OK")
        
        # Advisor
        self.advisor = MarketAdvisor()
        self.advisor._brain = self.brain
        self.advisor._telegram = self.telegram
        self.advisor._scheduler = Scheduler()
        self.advisor._config = AdvisorConfig(symbols=['XAUUSD', 'EURUSD', 'GBPUSD'])
        self.advisor._initialized = True
        print("   ✅ Advisor OK")
    
    async def send_briefing(self):
        """Envia briefing matinal"""
        print("\n📋 Enviando briefing matinal...")
        await self.advisor.send_morning_briefing()
        print("✅ Briefing enviado! Verifique o Telegram.")
    
    async def send_sentiment(self, symbol: str = 'XAUUSD'):
        """Envia análise de sentimento"""
        print(f"\n📊 Analisando sentimento de {symbol}...")
        sentiment = await self.brain.get_sentiment(symbol)
        
        emoji = "🟢" if sentiment.overall_sentiment > 0.1 else "🔴" if sentiment.overall_sentiment < -0.1 else "🟡"
        
        text = f"""📊 *SENTIMENTO: {symbol}*

{emoji} *Nível:* {sentiment.sentiment_level.value}
📈 *Score:* {sentiment.overall_sentiment:+.2f}
📰 *Notícias analisadas:* {sentiment.news_count}

_{sentiment.explanation_pt}_

⏰ {sentiment.timestamp.strftime('%H:%M:%S')}"""
        
        await self.telegram.send_message(text)
        print("✅ Sentimento enviado! Verifique o Telegram.")
    
    async def send_news(self):
        """Envia notícias principais"""
        print("\n📰 Buscando notícias...")
        news = await self.brain.get_news(symbols=['XAUUSD', 'EURUSD', 'GBPUSD'], limit=5)
        
        lines = ["📰 *NOTÍCIAS DO MERCADO*", ""]
        for item in news[:5]:
            emoji = "🟢" if item.sentiment_score > 0.2 else "🔴" if item.sentiment_score < -0.2 else "🟡"
            lines.append(f"{emoji} *{item.source}*")
            lines.append(f"   {item.title[:80]}")
            lines.append("")
        
        await self.telegram.send_message("\n".join(lines))
        print("✅ Notícias enviadas! Verifique o Telegram.")
    
    async def test_connection(self):
        """Testa conexão com Telegram"""
        print("\n🧪 Testando conexão...")
        await self.telegram.send_message("🤖 *VIRTUS Advisor*\n\nConexão testada com sucesso! ✅")
        print("✅ Mensagem de teste enviada!")

async def main():
    runner = AdvisorRunner()
    
    try:
        await runner.initialize()
        
        # Pega comando da linha de comando
        command = sys.argv[1] if len(sys.argv) > 1 else 'briefing'
        symbol = sys.argv[2] if len(sys.argv) > 2 else 'XAUUSD'
        
        print(f"\n{'='*60}")
        print(f"🤖 VIRTUS MARKET ADVISOR")
        print(f"{'='*60}")
        
        if command == 'briefing':
            await runner.send_briefing()
        elif command == 'sentiment':
            await runner.send_sentiment(symbol)
        elif command == 'news':
            await runner.send_news()
        elif command == 'test':
            await runner.test_connection()
        elif command == 'all':
            await runner.send_briefing()
            await asyncio.sleep(1)
            await runner.send_news()
        else:
            print(f"❌ Comando desconhecido: {command}")
            print("\nComandos disponíveis:")
            print("  briefing  - Envia briefing matinal")
            print("  sentiment - Envia sentimento (ex: sentiment XAUUSD)")
            print("  news      - Envia notícias principais")
            print("  test      - Testa conexão")
            print("  all       - Envia tudo")
        
        print(f"\n{'='*60}")
        print("📱 Verifique: @OperadorVirtus_bot")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
