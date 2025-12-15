"""
Teste de Conexão Telegram
==========================
"""

import asyncio
import aiohttp
import ssl

TELEGRAM_TOKEN = "8334321679:AAHZI9cFlflEigDR4ZlkZ68YWiPNPIhoEdc"
TELEGRAM_CHAT_ID = "7005082427"

async def test_telegram():
    print("=" * 50)
    print("TESTE DE CONEXÃO TELEGRAM")
    print("=" * 50)
    
    # Mensagem de teste
    message = """
🤖 *VIRTUS Trading System*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ *Teste de Conexão*

O sistema VIRTUS está operacional!

📊 *Status:*
• MT5: ✅ Conectado
• Telegram: ✅ Funcionando
• Analysis: ✅ 20 módulos
• Strategies: ✅ 29 setups
• Risk: ✅ Kelly/VaR/Anti-Martingale
• ML: ✅ Ensemble Predictions

_Pronto para operar!_ 🚀
"""
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    print("\n🔄 Enviando mensagem de teste...")
    
    # SSL sem verificação (ambiente de teste)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(url, json=payload) as response:
            result = await response.json()
            
            if result.get("ok"):
                print("✅ Mensagem enviada com sucesso!")
                print(f"   Message ID: {result['result']['message_id']}")
            else:
                print(f"❌ Erro: {result.get('description', 'Unknown error')}")
                return False
    
    print("\n✅ Teste Telegram concluído!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    asyncio.run(test_telegram())
