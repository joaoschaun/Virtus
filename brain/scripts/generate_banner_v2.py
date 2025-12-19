"""
VIRTUS - Gerador de Banner usando TESS AI
==========================================

Script para gerar banner profissional para o portal VIRTUS
inspirado em sites como XP e Rico.

Usa modelos de geração de imagem via texto (text-to-image).
"""

import asyncio
import aiohttp
import yaml
from pathlib import Path
from datetime import datetime


async def get_agent_details(api_key: str, base_url: str, agent_id: int):
    """Busca detalhes completos de um agente."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{base_url}/agents/{agent_id}") as response:
            if response.status == 200:
                return await response.json()
            return None


async def generate_image(api_key: str, base_url: str, agent_id: int, inputs: dict, output_path: str = None):
    """Gera imagem usando um agente TESS."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {**inputs, "waitExecution": "true"}
    
    print(f"   🎨 Enviando requisição...")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(
            f"{base_url}/agents/{agent_id}/execute",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300)
        ) as response:
            if response.status != 200:
                error = await response.text()
                print(f"   ❌ Erro {response.status}: {error[:300]}")
                return None
            
            data = await response.json()
            
            if data.get('responses') and len(data['responses']) > 0:
                result = data['responses'][0]
                output = result.get('output', '')
                credits = result.get('credits', 0)
                
                print(f"   ✅ Sucesso! Créditos: {credits:.4f}")
                
                if output.startswith('http'):
                    print(f"   🖼️ URL: {output}")
                    
                    if output_path:
                        async with session.get(output) as img_response:
                            if img_response.status == 200:
                                img_data = await img_response.read()
                                with open(output_path, 'wb') as f:
                                    f.write(img_data)
                                print(f"   💾 Salvo: {output_path}")
                    
                    return output
                    
            return None


async def main():
    # Carrega configuração
    config_path = Path(__file__).parent.parent / "config" / "tess.yaml"
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    api_key = config['api_key']
    base_url = config['base_url']
    
    print("=" * 70)
    print("🎨 VIRTUS - Gerador de Banner Profissional")
    print("   Inspirado em XP Investimentos e Rico")
    print("=" * 70)
    
    # Diretório para salvar
    output_dir = Path(__file__).parent.parent / "data" / "banners"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Prompt principal inspirado em XP/Rico
    main_prompt = """
    Professional corporate portrait photograph of a confident successful Brazilian male executive,
    age 38, short dark hair neatly styled, well-trimmed beard, wearing an impeccable dark charcoal 
    premium suit with a crisp white dress shirt and a bold red silk tie (#E53935).
    
    He stands confidently in a luxurious modern financial office with floor-to-ceiling glass windows 
    showing a stunning city skyline at dusk with warm golden hour lighting. The background features 
    subtle digital elements: ascending stock charts and financial data visualizations in red accents.
    
    The lighting is dramatic and cinematic - key light from the side creating depth and authority.
    His expression conveys trustworthiness, expertise, success, and calm confidence with direct 
    eye contact and a subtle professional smile.
    
    Style: Premium corporate photography, photorealistic, 8K ultra high definition, 
    widescreen 16:9 composition, inspired by XP Investimentos and Rico broker websites aesthetic.
    Colors: Dark sophisticated background (#0c0c10 to #1a1a2e), red accents (#E53935).
    """
    
    # Aguarda um pouco antes de começar (rate limit)
    print("\n⏳ Aguardando 3 segundos antes de iniciar (rate limit)...")
    await asyncio.sleep(3)
    
    results = []
    
    # ============== TENTATIVA 1: Agente 2506 (Tess Fantasy Dream) ==============
    print("\n" + "="*70)
    print("🎨 TENTATIVA 1: Agente 2506 (Tess AI Fantasy Dream)")
    print("="*70)
    
    # Verifica campos
    detail = await get_agent_details(api_key, base_url, 2506)
    if detail:
        agent_data = detail.get('data', {})
        print(f"   Agente: {agent_data.get('title')}")
        fields = agent_data.get('fields', [])
        print(f"   Campos:")
        for f in fields:
            req = "✓" if f.get('required') else " "
            print(f"      [{req}] {f.get('key')}: {f.get('label', '')[:50]}")
    
    await asyncio.sleep(2)
    
    output_2506 = output_dir / f"virtus_banner_fantasy_{timestamp}.png"
    
    result = await generate_image(
        api_key, base_url, 2506,
        {
            "descricao": main_prompt.strip()
        },
        str(output_2506)
    )
    
    if result:
        results.append(("Fantasy Dream", output_2506, result))
    
    await asyncio.sleep(3)
    
    # ============== TENTATIVA 2: Agente 1889 (Pinturas Futuristas) ==============
    print("\n" + "="*70)
    print("🎨 TENTATIVA 2: Agente 1889 (Pinturas Digitais Futuristas)")
    print("="*70)
    
    detail = await get_agent_details(api_key, base_url, 1889)
    if detail:
        agent_data = detail.get('data', {})
        print(f"   Agente: {agent_data.get('title')}")
        fields = agent_data.get('fields', [])
        print(f"   Campos:")
        for f in fields:
            req = "✓" if f.get('required') else " "
            print(f"      [{req}] {f.get('key')}: {f.get('label', '')[:50]}")
    
    await asyncio.sleep(2)
    
    futuristic_prompt = """
    Confident successful male executive businessman, 38 years old, Brazilian, 
    short dark hair, trimmed beard, wearing elegant dark suit with red tie,
    standing in futuristic high-tech office, holographic financial charts,
    city skyline background, cinematic dramatic lighting, professional photography,
    conveying authority, success, trustworthiness, expertise
    """
    
    output_1889 = output_dir / f"virtus_banner_futuristic_{timestamp}.png"
    
    result2 = await generate_image(
        api_key, base_url, 1889,
        {
            "descricao": futuristic_prompt.strip()
        },
        str(output_1889)
    )
    
    if result2:
        results.append(("Futuristic", output_1889, result2))
    
    await asyncio.sleep(3)
    
    # ============== TENTATIVA 3: Agente 2063 (Cenários Futuristas) ==============
    print("\n" + "="*70)
    print("🎨 TENTATIVA 3: Agente 2063 (Cenários e Objetos Futuristas)")
    print("="*70)
    
    detail = await get_agent_details(api_key, base_url, 2063)
    if detail:
        agent_data = detail.get('data', {})
        print(f"   Agente: {agent_data.get('title')}")
        fields = agent_data.get('fields', [])
        print(f"   Campos:")
        for f in fields:
            req = "✓" if f.get('required') else " "
            print(f"      [{req}] {f.get('key')}: {f.get('label', '')[:50]}")
    
    await asyncio.sleep(2)
    
    office_prompt = """
    Luxurious modern financial trading office interior, dark sophisticated atmosphere,
    floor-to-ceiling windows with city skyline at dusk, multiple screens showing 
    ascending stock charts with red accent color (#E53935), elegant dark furniture,
    dramatic cinematic lighting, premium corporate aesthetic, 8K ultra detailed,
    inspired by investment bank headquarters, conveying success and authority
    """
    
    output_2063 = output_dir / f"virtus_banner_office_{timestamp}.png"
    
    result3 = await generate_image(
        api_key, base_url, 2063,
        {
            "descricao": office_prompt.strip()
        },
        str(output_2063)
    )
    
    if result3:
        results.append(("Office", output_2063, result3))
    
    # ============== RESULTADO FINAL ==============
    print("\n" + "=" * 70)
    print("📊 RESULTADO FINAL")
    print("=" * 70)
    
    if results:
        print(f"\n✅ {len(results)} imagem(ns) gerada(s) com sucesso!")
        print(f"📁 Pasta: {output_dir}\n")
        
        for name, path, url in results:
            print(f"🖼️  {name}:")
            print(f"    URL: {url}")
            print(f"    Arquivo: {path.name}")
            print()
        
        # Sugestão de uso
        print("=" * 70)
        print("💡 PRÓXIMOS PASSOS:")
        print("=" * 70)
        print(f"""
1. Abra a pasta: {output_dir}
2. Escolha a melhor imagem
3. Copie para o portal:
   
   Copy-Item "{results[0][1]}" "C:\\nginx\\portal\\banner.png"
   
4. Atualize o HomePage.tsx para usar o banner
5. Rebuild e deploy do portal
        """)
    else:
        print("\n⚠️ Nenhuma imagem foi gerada.")
        print("   Possíveis causas:")
        print("   - Rate limit da API (aguarde alguns minutos)")
        print("   - Campos obrigatórios não preenchidos")
        print("   - Créditos insuficientes na conta TESS")


if __name__ == "__main__":
    asyncio.run(main())
