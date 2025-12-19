"""
VIRTUS - Busca Agentes de Imagem TESS
=====================================

Script para descobrir quais agentes de imagem podem ser usados
com input simples de texto (sem imagem de referência).
"""

import asyncio
import aiohttp
import yaml
from pathlib import Path


async def main():
    # Carrega configuração
    config_path = Path(__file__).parent.parent / "config" / "tess.yaml"
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    api_key = config['api_key']
    base_url = config['base_url']
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    
    print("=" * 70)
    print("🔍 Buscando agentes de imagem TEXT-TO-IMAGE (sem imagem obrigatória)")
    print("=" * 70)
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # Busca todos os agentes de imagem
        async with session.get(
            f"{base_url}/agents",
            params={"type": "image", "per_page": 100}
        ) as response:
            if response.status != 200:
                print(f"❌ Erro: {response.status}")
                return
            data = await response.json()
            agents = data.get('data', [])
        
        print(f"\n📋 Total de agentes de imagem: {len(agents)}\n")
        
        suitable_agents = []
        
        for i, agent in enumerate(agents):
            agent_id = agent['id']
            
            # Rate limit
            if i > 0 and i % 5 == 0:
                await asyncio.sleep(1)
            
            # Busca detalhes
            async with session.get(f"{base_url}/agents/{agent_id}") as detail_resp:
                if detail_resp.status != 200:
                    continue
                detail = await detail_resp.json()
                agent_data = detail.get('data', {})
                fields = agent_data.get('fields', [])
                
                # Verifica se tem campo de imagem obrigatório
                has_required_image = False
                text_inputs = []
                
                for f in fields:
                    key = f.get('key', '').lower()
                    required = f.get('required', False)
                    field_type = f.get('type', '').lower()
                    
                    # Detecta campos de imagem
                    if 'imagem' in key or 'image' in key or 'foto' in key or 'photo' in key:
                        if required:
                            has_required_image = True
                    
                    # Detecta campos de texto/descrição
                    if any(x in key for x in ['descri', 'prompt', 'comando', 'texto', 'ideia', 'tema']):
                        text_inputs.append(key)
                
                # Agentes sem imagem obrigatória são candidatos
                if not has_required_image and text_inputs:
                    suitable_agents.append({
                        'id': agent_id,
                        'title': agent_data.get('title', agent.get('title', 'N/A')),
                        'text_inputs': text_inputs,
                        'all_fields': [(f.get('key'), f.get('required'), f.get('type')) for f in fields]
                    })
                    print(f"✅ [{agent_id}] {agent_data.get('title', agent.get('title', 'N/A'))}")
                    print(f"   Inputs de texto: {text_inputs}")
        
        print("\n" + "=" * 70)
        print(f"🎯 AGENTES ADEQUADOS PARA TEXT-TO-IMAGE: {len(suitable_agents)}")
        print("=" * 70)
        
        if suitable_agents:
            print("\nAgentes que aceitam apenas descrição de texto:\n")
            for ag in suitable_agents:
                print(f"[{ag['id']}] {ag['title']}")
                print(f"   Campos de texto: {ag['text_inputs']}")
                print(f"   Todos campos: {[f[0] for f in ag['all_fields']]}")
                print()


if __name__ == "__main__":
    asyncio.run(main())
