"""
Teste de geração de briefing com TESS AI
"""

import asyncio
import sys
sys.path.insert(0, 'C:/Users/Administrator/Desktop/Virtus/brain')
sys.path.insert(0, 'C:/Users/Administrator/Desktop/Virtus/brain/dashboard/backend')

from services.social_briefing_generator import SocialBriefingGenerator


async def test_briefing():
    """Testa geração de briefing."""
    print("=" * 60)
    print("🎨 TESTE DE GERAÇÃO DE BRIEFING COM TESS AI")
    print("=" * 60)
    
    gen = SocialBriefingGenerator()
    
    print("\n📋 Gerando briefing diário...")
    post = await gen.generate_daily_briefing_post()
    
    print("\n✅ POST GERADO!")
    print(f"   Title: {post['title']}")
    print(f"   Image: {post['image_file']}")
    print(f"   Mood: {post['market_mood']}")
    print(f"   Sources: {post['data_sources']}")
    
    print("\n📝 Caption:")
    print("-" * 40)
    caption = post['caption']
    # Mostrar primeiras 500 chars
    if len(caption) > 500:
        print(caption[:500] + "...")
    else:
        print(caption)


if __name__ == "__main__":
    asyncio.run(test_briefing())
