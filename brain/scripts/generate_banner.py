"""
VIRTUS - Gerador de Banner usando TESS AI
==========================================

Script para gerar banner profissional para o portal VIRTUS
inspirado em sites como XP e Rico.
"""

import asyncio
import aiohttp
import yaml
import base64
from pathlib import Path
from datetime import datetime
import os


async def get_agent_fields(api_key: str, base_url: str, agent_id: int):
    """Busca campos necessários de um agente."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{base_url}/agents/{agent_id}") as response:
            if response.status != 200:
                return None
            data = await response.json()
            return data.get('data', {})


async def search_image_agents(api_key: str, base_url: str):
    """Busca agentes de geração de imagem."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # Busca agentes de imagem
        async with session.get(
            f"{base_url}/agents",
            params={"type": "image", "per_page": 50}
        ) as response:
            if response.status != 200:
                print(f"❌ Erro: {response.status}")
                return []
            data = await response.json()
            return data.get('data', [])


async def generate_image_with_agent(
    api_key: str, 
    base_url: str, 
    agent_id: int, 
    inputs: dict,
    output_path: str = None
):
    """
    Gera imagem usando um agente TESS.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        **inputs,
        "waitExecution": "true"
    }
    
    print(f"🎨 Gerando imagem com agente {agent_id}...")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(
            f"{base_url}/agents/{agent_id}/execute",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=180)
        ) as response:
            if response.status != 200:
                error = await response.text()
                print(f"❌ Erro {response.status}: {error[:200]}")
                return None
            
            data = await response.json()
            
            if data.get('responses') and len(data['responses']) > 0:
                result = data['responses'][0]
                output = result.get('output', '')
                credits = result.get('credits', 0)
                
                print(f"✅ Geração concluída! Créditos: {credits:.4f}")
                
                if output.startswith('http'):
                    print(f"🖼️ URL da imagem: {output}")
                    
                    if output_path:
                        async with session.get(output) as img_response:
                            if img_response.status == 200:
                                img_data = await img_response.read()
                                with open(output_path, 'wb') as f:
                                    f.write(img_data)
                                print(f"💾 Imagem salva em: {output_path}")
                    
                    return output
                else:
                    print(f"📝 Output: {output[:300]}...")
                    return output
            else:
                print(f"⚠️ Resposta sem output")
                return None


async def main():
    # Carrega configuração
    config_path = Path(__file__).parent.parent / "config" / "tess.yaml"
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    api_key = config['api_key']
    base_url = config['base_url']
    
    print("=" * 60)
    print("🎨 VIRTUS - Gerador de Banner")
    print("=" * 60)
    
    # Diretório para salvar
    output_dir = Path(__file__).parent.parent / "data" / "banners"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Verifica os campos necessários dos agentes
    print("\n📋 Verificando campos dos agentes de imagem...")
    
    agents_to_check = [165, 175, 2249, 2505, 2507, 358]
    
    for agent_id in agents_to_check:
        detail = await get_agent_fields(api_key, base_url, agent_id)
        if detail:
            print(f"\n[{agent_id}] {detail.get('title', 'N/A')}")
            fields = detail.get('fields', [])
            for f in fields:
                required = "OBRIGATÓRIO" if f.get('required') else "opcional"
                print(f"   - {f.get('key')}: {f.get('label', '')} [{required}]")
    
    # ============== GERAR COM AGENTE 165 (Unsplash) ==============
    print("\n" + "="*60)
    print("🎨 GERANDO COM AGENTE 165 (Imagens estilo Unsplash)...")
    print("="*60)
    
    prompt_165 = """
    Professional corporate portrait photo of confident Brazilian male executive, 
    40 years old, short dark hair, trimmed beard, wearing premium dark navy suit 
    with crisp white shirt and red tie. Standing in modern glass office with 
    city skyline view at sunset. Dramatic cinematic lighting, 
    warm golden hour tones mixed with cool shadows. Direct eye contact, 
    warm professional smile conveying trustworthiness and success.
    Premium corporate photography style, photorealistic, 8K ultra detailed.
    """
    
    output_path_165 = output_dir / f"virtus_banner_165_{timestamp}.png"
    
    result_165 = await generate_image_with_agent(
        api_key=api_key,
        base_url=base_url,
        agent_id=165,
        inputs={
            "seu-comando": prompt_165.strip(),
            "image_size": "landscape_16_9",
            "negativePrompt": "blurry, low quality, distorted, ugly, bad anatomy, text, watermark, logo",
            "seed": "42"
        },
        output_path=str(output_path_165)
    )
    
    # ============== GERAR COM AGENTE 2505 (DALL-E 2) ==============
    print("\n" + "="*60)
    print("🎨 GERANDO COM AGENTE 2505 (DALL-E 2)...")
    print("="*60)
    
    prompt_dalle = """
    Professional corporate banner image. Confident Brazilian male executive 
    in his late 30s, wearing an elegant dark suit with red tie, standing in 
    a modern luxury office with glass windows showing city skyline at dusk.
    Sophisticated dark background with subtle ascending financial chart graphics.
    Dramatic professional lighting. The image conveys authority, expertise, 
    success and trustworthiness. Corporate premium photography style, 
    photorealistic, high detail.
    """
    
    # Primeiro verifica campos do DALL-E
    dalle_detail = await get_agent_fields(api_key, base_url, 2505)
    if dalle_detail:
        print(f"   Campos do DALL-E 2:")
        for f in dalle_detail.get('fields', []):
            print(f"   - {f.get('key')}: [{f.get('required', False)}]")
    
    output_path_dalle = output_dir / f"virtus_banner_dalle_{timestamp}.png"
    
    result_dalle = await generate_image_with_agent(
        api_key=api_key,
        base_url=base_url,
        agent_id=2505,
        inputs={
            "descricao": prompt_dalle.strip(),
            "image_size": "1792x1024"  # Widescreen DALL-E
        },
        output_path=str(output_path_dalle)
    )
    
    # ============== GERAR COM AGENTE 2507 (OpenJourney) ==============
    print("\n" + "="*60)
    print("🎨 GERANDO COM AGENTE 2507 (OpenJourney/Midjourney style)...")
    print("="*60)
    
    prompt_openjourney = """
    mdjrny-v4 style, professional corporate portrait, confident male executive, 
    38 years old, Brazilian, dark suit, red tie, modern luxury office, 
    city skyline background, dramatic cinematic lighting, 
    dark sophisticated atmosphere, financial success, authority, 
    trustworthy, premium photography, 8k, detailed, photorealistic
    """
    
    oj_detail = await get_agent_fields(api_key, base_url, 2507)
    if oj_detail:
        print(f"   Campos do OpenJourney:")
        for f in oj_detail.get('fields', []):
            print(f"   - {f.get('key')}: [{f.get('required', False)}]")
    
    output_path_oj = output_dir / f"virtus_banner_openjourney_{timestamp}.png"
    
    result_oj = await generate_image_with_agent(
        api_key=api_key,
        base_url=base_url,
        agent_id=2507,
        inputs={
            "descricao": prompt_openjourney.strip()
        },
        output_path=str(output_path_oj)
    )
    
    # ============== RESULTADO ==============
    print("\n" + "=" * 60)
    print("✅ Processo concluído!")
    print("=" * 60)
    
    print(f"\n📁 Banners salvos em: {output_dir}")
    
    results = []
    if result_165:
        results.append(("Unsplash (165)", output_path_165, result_165))
    if result_dalle:
        results.append(("DALL-E 2 (2505)", output_path_dalle, result_dalle))
    if result_oj:
        results.append(("OpenJourney (2507)", output_path_oj, result_oj))
    
    if results:
        print("\n🎉 Imagens geradas com sucesso:")
        for name, path, url in results:
            print(f"   🖼️ {name}:")
            print(f"      URL: {url}")
            print(f"      Local: {path}")
    else:
        print("\n⚠️ Nenhuma imagem foi gerada. Verifique os erros acima.")


if __name__ == "__main__":
    asyncio.run(main())


async def generate_image_with_agent(
    api_key: str, 
    base_url: str, 
    agent_id: int, 
    inputs: dict,
    output_path: str = None
):
    """
    Gera imagem usando um agente TESS.
    
    Args:
        api_key: Chave da API
        base_url: URL base da API
        agent_id: ID do agente
        inputs: Inputs do agente
        output_path: Caminho para salvar a imagem
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        **inputs,
        "waitExecution": "true"
    }
    
    print(f"🎨 Gerando imagem com agente {agent_id}...")
    print(f"   Inputs: {inputs}")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(
            f"{base_url}/agents/{agent_id}/execute",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            if response.status != 200:
                error = await response.text()
                print(f"❌ Erro {response.status}: {error}")
                return None
            
            data = await response.json()
            
            # Verifica se há resposta
            if data.get('responses') and len(data['responses']) > 0:
                result = data['responses'][0]
                output = result.get('output', '')
                credits = result.get('credits', 0)
                
                print(f"✅ Geração concluída! Créditos: {credits:.4f}")
                
                # Se output é uma URL de imagem
                if output.startswith('http'):
                    print(f"🖼️ URL da imagem: {output}")
                    
                    if output_path:
                        # Baixa a imagem
                        async with session.get(output) as img_response:
                            if img_response.status == 200:
                                img_data = await img_response.read()
                                with open(output_path, 'wb') as f:
                                    f.write(img_data)
                                print(f"💾 Imagem salva em: {output_path}")
                    
                    return output
                else:
                    print(f"📝 Output: {output[:500]}...")
                    return output
            else:
                print(f"⚠️ Resposta sem output: {data}")
                return None


async def main():
    # Carrega configuração
    config_path = Path(__file__).parent.parent / "config" / "tess.yaml"
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    api_key = config['api_key']
    base_url = config['base_url']
    
    print("=" * 60)
    print("🎨 VIRTUS - Gerador de Banner")
    print("=" * 60)
    
    # Lista agentes de imagem disponíveis
    print("\n📋 Buscando agentes de imagem disponíveis...")
    agents = await search_image_agents(api_key, base_url)
    
    if agents:
        print(f"\n✅ Encontrados {len(agents)} agentes de imagem:\n")
        for agent in agents:
            print(f"   [{agent['id']}] {agent['title']}")
            if agent.get('description'):
                print(f"       {agent['description'][:80]}...")
            print()
    
    # Diretório para salvar
    output_dir = Path(__file__).parent.parent / "data" / "banners"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # =============== OPÇÃO 1: Agente 2249 - Imagens realistas para vídeos ===============
    print("\n🚀 OPÇÃO 1: Agente 2249 - Imagens realistas para redes sociais...")
    
    # Primeiro vamos ver os campos necessários deste agente
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # Verifica campos do agente 2249
        async with session.get(f"{base_url}/agents/2249") as resp:
            if resp.status == 200:
                detail = await resp.json()
                fields = detail.get('data', {}).get('fields', [])
                print(f"   Campos do agente 2249: {[(f.get('key'), f.get('label')) for f in fields]}")
        
        # Verifica campos do agente 165 (estilo Unsplash)
        print("\n🚀 OPÇÃO 2: Agente 165 - Imagens estilo Unsplash...")
        async with session.get(f"{base_url}/agents/165") as resp:
            if resp.status == 200:
                detail = await resp.json()
                fields = detail.get('data', {}).get('fields', [])
                print(f"   Campos do agente 165: {[(f.get('key'), f.get('label')) for f in fields]}")
        
        # Verifica campos do agente 175 - Ilustrações 2D de Profissionais
        print("\n🚀 OPÇÃO 3: Agente 175 - Ilustrações 2D de Profissionais...")
        async with session.get(f"{base_url}/agents/175") as resp:
            if resp.status == 200:
                detail = await resp.json()
                fields = detail.get('data', {}).get('fields', [])
                print(f"   Campos do agente 175: {[(f.get('key'), f.get('label')) for f in fields]}")
        
        # Verifica agente 358 - Ilustrações 2D Gerais
        print("\n🚀 OPÇÃO 4: Agente 358 - Ilustrações 2D Gerais para Web Design...")
        async with session.get(f"{base_url}/agents/358") as resp:
            if resp.status == 200:
                detail = await resp.json()
                fields = detail.get('data', {}).get('fields', [])
                print(f"   Campos do agente 358: {[(f.get('key'), f.get('label')) for f in fields]}")
    
    # =============== GERAR COM AGENTE 165 - Estilo Unsplash ===============
    print("\n" + "="*60)
    print("🎨 GERANDO BANNER COM AGENTE 165 (Estilo Unsplash)...")
    print("="*60)
    
    banner_prompt_unsplash = """
    Professional corporate banner for VIRTUS financial investment company.
    Confident male executive 35-45 years old, Brazilian appearance, dark premium suit, 
    red tie, standing in modern glass office with city skyline view.
    Dramatic cinematic lighting, dark sophisticated background with subtle ascending 
    financial charts and graphs. Red accent color (#E53935).
    Conveys authority, expertise, success, trust and security.
    Photorealistic, 8K quality, widescreen composition, corporate premium style.
    Similar to XP Investimentos and Rico broker websites aesthetic.
    """
    
    output_path_unsplash = output_dir / f"virtus_banner_unsplash_{timestamp}.png"
    
    result = await generate_image_with_agent(
        api_key=api_key,
        base_url=base_url,
        agent_id=165,
        inputs={
            "descricao": banner_prompt_unsplash.strip()
        },
        output_path=str(output_path_unsplash)
    )
    
    # =============== GERAR COM AGENTE 175 - Ilustração Profissional ===============
    print("\n" + "="*60)
    print("🎨 GERANDO BANNER COM AGENTE 175 (Ilustração Profissional)...")
    print("="*60)
    
    banner_prompt_illustration = """
    Financial advisor executive, confident businessman in dark suit with red tie,
    analyzing stock market data on computer screen, modern office environment,
    graphs showing upward trends, professional corporate atmosphere,
    dark elegant background, red accent colors
    """
    
    output_path_illustration = output_dir / f"virtus_banner_illustration_{timestamp}.png"
    
    result2 = await generate_image_with_agent(
        api_key=api_key,
        base_url=base_url,
        agent_id=175,
        inputs={
            "descricao": banner_prompt_illustration.strip()
        },
        output_path=str(output_path_illustration)
    )
    
    # =============== GERAR COM AGENTE 2249 - Realista para Vídeos ===============
    print("\n" + "="*60)
    print("🎨 GERANDO BANNER COM AGENTE 2249 (Realista)...")
    print("="*60)
    
    banner_prompt_realistic = """
    Handsome confident Brazilian male executive, 38 years old, short dark hair, 
    trimmed beard, wearing premium charcoal suit with crisp white shirt and red tie.
    Standing in luxurious modern financial office, dark elegant background.
    Professional cinematic lighting. Direct eye contact, warm confident smile.
    Radiates trustworthiness, expertise, success and authority.
    Premium corporate photography style, 8K ultra detailed, photorealistic.
    """
    
    output_path_realistic = output_dir / f"virtus_banner_realistic_{timestamp}.png"
    
    result3 = await generate_image_with_agent(
        api_key=api_key,
        base_url=base_url,
        agent_id=2249,
        inputs={
            "descricao": banner_prompt_realistic.strip()
        },
        output_path=str(output_path_realistic)
    )
    
    print("\n" + "=" * 60)
    print("✅ Processo concluído!")
    print("=" * 60)
    
    print(f"\n📁 Banners salvos em: {output_dir}")
    
    results = []
    if result:
        results.append(("Unsplash", output_path_unsplash, result))
    if result2:
        results.append(("Ilustração", output_path_illustration, result2))
    if result3:
        results.append(("Realista", output_path_realistic, result3))
    
    for name, path, url in results:
        print(f"   🖼️ {name}: {url}")


if __name__ == "__main__":
    asyncio.run(main())
