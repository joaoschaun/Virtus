"""
VIRTUS - Gerador de Banner usando TESS AI
==========================================

Gera banner profissional usando agentes text-to-image da TESS.
"""

import asyncio
import aiohttp
import yaml
from pathlib import Path
from datetime import datetime


async def generate_image(api_key: str, base_url: str, agent_id: int, inputs: dict, output_path: str):
    """Gera imagem usando um agente TESS."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {**inputs, "waitExecution": "true"}
    
    print(f"   🎨 Gerando imagem...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/agents/{agent_id}/execute",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300)
        ) as response:
            if response.status != 200:
                error = await response.text()
                print(f"   ❌ Erro {response.status}: {error[:400]}")
                return None
            
            data = await response.json()
            
            if data.get('responses') and len(data['responses']) > 0:
                result = data['responses'][0]
                output = result.get('output', '')
                credits = result.get('credits', 0)
                
                print(f"   ✅ Sucesso! Créditos: {credits:.4f}")
                
                if output.startswith('http'):
                    print(f"   🖼️ URL: {output}")
                    
                    # Download da imagem IMEDIATAMENTE com mesma sessão autenticada
                    download_headers = {"Authorization": f"Bearer {api_key}"}
                    async with session.get(output, headers=download_headers) as img_response:
                        if img_response.status == 200:
                            img_data = await img_response.read()
                            with open(output_path, 'wb') as f:
                                f.write(img_data)
                            print(f"   💾 Salvo: {output_path} ({len(img_data)} bytes)")
                            return output
                        else:
                            # Tenta sem autenticação
                            async with session.get(output) as img_r2:
                                if img_r2.status == 200:
                                    img_data = await img_r2.read()
                                    with open(output_path, 'wb') as f:
                                        f.write(img_data)
                                    print(f"   💾 Salvo: {output_path} ({len(img_data)} bytes)")
                                    return output
                                else:
                                    print(f"   ⚠️ Não foi possível baixar a imagem")
                                    print(f"   📋 URL para download manual: {output}")
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
    print("=" * 70)
    
    # Diretório para salvar
    output_dir = Path(__file__).parent.parent / "data" / "banners"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    results = []
    
    # ============== BANNER 1: Estilo Pixar (Agente 156) ==============
    print("\n" + "="*70)
    print("🎬 BANNER 1: Ilustração Estilo Pixar (Agente 156)")
    print("="*70)
    
    pixar_prompt = """
    Confident successful Brazilian male businessman executive character,
    age 38, wearing elegant dark charcoal suit with bold red tie,
    standing in luxurious modern financial office with glass windows,
    city skyline at sunset in background, professional dramatic lighting,
    warm and trustworthy expression, sophisticated corporate atmosphere,
    ascending financial charts on screens, red accent colors
    """
    
    output_pixar = output_dir / f"virtus_banner_pixar_{timestamp}.png"
    
    result = await generate_image(
        api_key, base_url, 156,
        {
            "descreva-a-cena": pixar_prompt.strip(),
            "image_size": "1024x576",  # Widescreen
            "num_inference_steps": "50",
            "negative_prompt": "blurry, low quality, distorted, ugly, bad anatomy, watermark, text, logo",
            "image_number_of_images": 1
        },
        str(output_pixar)
    )
    
    if result:
        results.append(("Pixar Style", output_pixar, result))
    
    await asyncio.sleep(3)
    
    # ============== BANNER 2: Ilustração 3D (Agente 159) ==============
    print("\n" + "="*70)
    print("🎲 BANNER 2: Ícone 3D Moderno (Agente 159)")
    print("="*70)
    
    icon_prompt = """
    3D modern minimalist icon of confident successful businessman,
    wearing dark suit with red tie, holding briefcase,
    professional corporate executive, clean modern design,
    dark background with subtle red accents
    """
    
    output_icon = output_dir / f"virtus_icon_3d_{timestamp}.png"
    
    result2 = await generate_image(
        api_key, base_url, 159,
        {
            "descricao": icon_prompt.strip()
        },
        str(output_icon)
    )
    
    if result2:
        results.append(("3D Icon", output_icon, result2))
    
    await asyncio.sleep(3)
    
    # ============== BANNER 3: Segunda versão Pixar ==============
    print("\n" + "="*70)
    print("🎬 BANNER 3: Cena de Escritório Pixar (Agente 156)")
    print("="*70)
    
    office_prompt = """
    Elegant modern financial trading office interior scene,
    multiple screens showing ascending stock market charts with green arrows,
    floor to ceiling windows with city skyline at golden hour,
    sophisticated dark wood furniture, warm ambient lighting,
    premium corporate atmosphere, success and prosperity mood,
    red accent decorations, luxury executive office
    """
    
    output_office = output_dir / f"virtus_office_pixar_{timestamp}.png"
    
    result3 = await generate_image(
        api_key, base_url, 156,
        {
            "descreva-a-cena": office_prompt.strip(),
            "image_size": "1024x576",
            "num_inference_steps": "75",
            "negative_prompt": "blurry, ugly, distorted, watermark",
            "image_number_of_images": 1
        },
        str(output_office)
    )
    
    if result3:
        results.append(("Office Pixar", output_office, result3))
    
    # ============== RESULTADO ==============
    print("\n" + "=" * 70)
    print("📊 RESULTADO FINAL")
    print("=" * 70)
    
    if results:
        print(f"\n✅ {len(results)} imagem(ns) gerada(s)!")
        print(f"📁 Pasta: {output_dir}\n")
        
        for name, path, url in results:
            print(f"🖼️  {name}:")
            print(f"    {url}")
            print()
        
        print("=" * 70)
        print("💡 PARA USAR NO PORTAL:")
        print("=" * 70)
        print(f"""
Escolha uma imagem e copie para o portal:

   Copy-Item "{results[0][1]}" "C:\\nginx\\portal\\banner.png"
   Restart-Service NginxVirtus
        """)
    else:
        print("\n⚠️ Nenhuma imagem foi gerada. Verifique os erros acima.")


if __name__ == "__main__":
    asyncio.run(main())
