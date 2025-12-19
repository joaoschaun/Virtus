"""
VIRTUS - Teste de Integração EODHD
===================================

Testa a integração com a API EODHD.
Execute: python test_eodhd.py
"""

import asyncio
import aiohttp
import os
from datetime import datetime, timedelta

# API Key EODHD
API_KEY = os.getenv("EODHD_API_KEY", "")
BASE_URL = "https://eodhd.com/api"


async def fetch(session: aiohttp.ClientSession, endpoint: str, params: dict = None):
    """Faz requisição à API EODHD"""
    params = params or {}
    params['api_token'] = API_KEY
    params['fmt'] = 'json'
    
    url = f"{BASE_URL}{endpoint}"
    
    async with session.get(url, params=params) as response:
        if response.status == 200:
            return await response.json()
        else:
            print(f"❌ Erro {response.status}: {await response.text()}")
            return None


async def test_live_price(session: aiohttp.ClientSession):
    """Testa obtenção de preço em tempo real"""
    print("\n" + "="*60)
    print("📊 TESTE: Preço em Tempo Real")
    print("="*60)
    
    symbols = ["AAPL.US", "EURUSD.FOREX", "BTC-USD.CC"]
    
    for symbol in symbols:
        data = await fetch(session, f"/real-time/{symbol}")
        if data:
            price = data.get('close', data.get('previousClose', 'N/A'))
            change = data.get('change_p', 0)
            print(f"✅ {symbol}: ${price} ({change:+.2f}%)")
        else:
            print(f"❌ {symbol}: Erro ao obter dados")


async def test_eod_data(session: aiohttp.ClientSession):
    """Testa dados históricos EOD"""
    print("\n" + "="*60)
    print("📈 TESTE: Dados Históricos EOD")
    print("="*60)
    
    from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    data = await fetch(session, "/eod/XAUUSD.FOREX", {'from': from_date})
    if data and isinstance(data, list):
        print(f"✅ XAUUSD.FOREX: {len(data)} candles obtidos")
        if data:
            latest = data[-1]
            print(f"   Último: {latest.get('date')} - Close: {latest.get('close')}")
    else:
        print("❌ Erro ao obter dados EOD")


async def test_economic_events(session: aiohttp.ClientSession):
    """Testa calendário econômico"""
    print("\n" + "="*60)
    print("📅 TESTE: Calendário Econômico")
    print("="*60)
    
    from_date = datetime.now().strftime('%Y-%m-%d')
    to_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    data = await fetch(session, "/economic-events", {
        'from': from_date,
        'to': to_date,
        'country': 'US'
    })
    
    if data and isinstance(data, list):
        print(f"✅ Eventos econômicos US: {len(data)} eventos")
        for event in data[:5]:
            print(f"   • {event.get('date', '')[:10]} - {event.get('event', 'N/A')}")
    else:
        print("❌ Erro ao obter eventos econômicos")


async def test_news(session: aiohttp.ClientSession):
    """Testa notícias"""
    print("\n" + "="*60)
    print("📰 TESTE: Notícias Financeiras")
    print("="*60)
    
    data = await fetch(session, "/news", {'limit': 10})
    
    if data and isinstance(data, list):
        print(f"✅ Notícias: {len(data)} artigos")
        for article in data[:5]:
            title = article.get('title', 'N/A')[:60]
            print(f"   • {title}...")
    else:
        print("❌ Erro ao obter notícias")


async def test_technical_indicator(session: aiohttp.ClientSession):
    """Testa indicadores técnicos"""
    print("\n" + "="*60)
    print("📊 TESTE: Indicadores Técnicos")
    print("="*60)
    
    indicators = [
        ('sma', 20),
        ('rsi', 14),
        ('macd', 12),
    ]
    
    for indicator, period in indicators:
        data = await fetch(session, "/technical/EURUSD.FOREX", {
            'function': indicator,
            'period': period
        })
        
        if data and isinstance(data, list) and len(data) > 0:
            latest = data[-1] if data else {}
            print(f"✅ {indicator.upper()}({period}): Último valor disponível")
        else:
            print(f"❌ {indicator.upper()}: Erro ao obter dados")


async def test_fundamentals(session: aiohttp.ClientSession):
    """Testa dados fundamentalistas"""
    print("\n" + "="*60)
    print("📋 TESTE: Dados Fundamentais")
    print("="*60)
    
    data = await fetch(session, "/fundamentals/AAPL.US", {'filter': 'General'})
    
    if data:
        general = data.get('General', data)
        name = general.get('Name', 'N/A')
        sector = general.get('Sector', 'N/A')
        industry = general.get('Industry', 'N/A')
        print(f"✅ AAPL: {name}")
        print(f"   Setor: {sector}")
        print(f"   Indústria: {industry}")
    else:
        print("❌ Erro ao obter dados fundamentais")


async def test_macro_data(session: aiohttp.ClientSession):
    """Testa dados macro"""
    print("\n" + "="*60)
    print("🌍 TESTE: Dados Macroeconômicos")
    print("="*60)
    
    data = await fetch(session, "/macro-indicator/USA", {
        'indicator': 'gdp_growth_annual'
    })
    
    if data and isinstance(data, list):
        print(f"✅ PIB USA: {len(data)} registros")
        if data:
            latest = data[-1]
            print(f"   Último: {latest.get('Date', 'N/A')} - {latest.get('Value', 'N/A')}%")
    else:
        print("❌ Erro ao obter dados macro")


async def test_search(session: aiohttp.ClientSession):
    """Testa busca de símbolos"""
    print("\n" + "="*60)
    print("🔍 TESTE: Busca de Símbolos")
    print("="*60)
    
    data = await fetch(session, "/search/Apple")
    
    if data and isinstance(data, list):
        print(f"✅ Busca 'Apple': {len(data)} resultados")
        for item in data[:5]:
            print(f"   • {item.get('Code', 'N/A')}.{item.get('Exchange', 'N/A')} - {item.get('Name', 'N/A')}")
    else:
        print("❌ Erro na busca")


async def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("🧪 VIRTUS - TESTE DE INTEGRAÇÃO EODHD")
    print("="*60)
    print(f"API Key: {API_KEY[:10]}...")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with aiohttp.ClientSession() as session:
        # Testes básicos
        await test_live_price(session)
        await test_eod_data(session)
        
        # Calendário e notícias
        await test_economic_events(session)
        await test_news(session)
        
        # Análises
        await test_technical_indicator(session)
        await test_fundamentals(session)
        await test_macro_data(session)
        
        # Busca
        await test_search(session)
    
    print("\n" + "="*60)
    print("✅ TESTES CONCLUÍDOS")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
