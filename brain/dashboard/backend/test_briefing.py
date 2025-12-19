"""Test briefing service."""
import asyncio
import sys
sys.path.insert(0, '.')

from services.daily_briefing_service import DailyBriefingService

async def test():
    print("Creating service...")
    s = DailyBriefingService()
    
    print("Generating briefing...")
    b = await s.generate_briefing()
    
    print("\n=== MARKET OVERVIEW ===")
    mo = b.market_overview
    print(f"Ibovespa: {mo.ibovespa.get('value', 'N/A')}")
    print(f"Dolar: {mo.dolar.get('value', 'N/A')}")
    print(f"SP500: {mo.sp500.get('value', 'N/A')}")
    
    print("\n=== DIVIDEND ALERTS ===")
    print(f"Total: {len(b.dividend_alerts)}")
    for d in b.dividend_alerts[:5]:
        print(f"  - {d.ticker}: buy until {d.buy_limit_date}")
    
    print("\nSuccess!")

if __name__ == "__main__":
    asyncio.run(test())
