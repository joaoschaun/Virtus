"""
Teste direto da API TESS para geração de imagem
"""

import asyncio
import aiohttp
import json


async def test_tess_image_direct():
    """Testa chamada direta à API TESS."""
    
    api_key = "337520|MzMxArNQnQAcO0XBz7CLbraeV4lA7L6ep9sHITpt59a4b449"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    print("=" * 60)
    print("🎨 TESTE DIRETO DA API TESS - GERAÇÃO DE IMAGEM")
    print("=" * 60)
    
    async with aiohttp.ClientSession(headers=headers) as session:
        
        # 1. Primeiro vamos ver os detalhes completos do agente 165
        print("\n📋 Buscando detalhes completos do agente 165...")
        async with session.get("https://tess.pareto.io/api/agents/165") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(json.dumps(data, indent=2))
            else:
                print(f"Erro: {resp.status}")
                text = await resp.text()
                print(text[:500])
        
        await asyncio.sleep(2)  # Aguardar para evitar rate limit
        
        # 2. Tentar executar com os parâmetros corretos
        print("\n\n🎨 Executando agente 165 (Unsplash style)...")
        
        payload = {
            "seu-comando": """Professional financial trading scene. Modern corporate office with 
            multiple monitors displaying forex charts and market data. Gold bars prominently 
            featured. Corporate blue and gold color scheme. Clean, modern, institutional, 
            premium quality photography style. High resolution, sharp focus.""",
            "image_size": "1024x1024",  # Square para Instagram
            "negativePrompt": "text, words, watermark, low quality, blurry, distorted, ugly",
            "seed": "42",
            "image_number_of_images": 1,
            "image_style": "realistic",
            "image_lighting": "studio",
            "image_mood": "bright",
            "waitExecution": "true"
        }
        
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            async with session.post(
                "https://tess.pareto.io/api/agents/165/execute",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                print(f"\nStatus: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    print("\n✅ Sucesso!")
                    print(json.dumps(data, indent=2))
                else:
                    text = await resp.text()
                    print(f"\n❌ Erro:")
                    print(text[:1000])
                    
        except Exception as e:
            print(f"\n❌ Exceção: {e}")


if __name__ == "__main__":
    asyncio.run(test_tess_image_direct())
