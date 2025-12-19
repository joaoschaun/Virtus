"""
Teste de geração de imagem com TESS AI
"""

import asyncio
import sys
sys.path.insert(0, 'C:/Users/Administrator/Desktop/Virtus/brain')

from src.integrations.tess.client import TessClient


async def test_image_generation():
    """Testa geração de imagem com TESS."""
    
    api_key = "337520|MzMxArNQnQAcO0XBz7CLbraeV4lA7L6ep9sHITpt59a4b449"
    
    async with TessClient(api_key=api_key) as client:
        print("=" * 60)
        print("🎨 TESTE DE GERAÇÃO DE IMAGEM - TESS AI")
        print("=" * 60)
        
        # 1. Primeiro, vamos ver os detalhes do agente de imagem 153
        print("\n📋 Buscando detalhes do agente 153 (Mockup Realista)...")
        try:
            agent_details = await client.get_agent(153)
            print(f"   Nome: {agent_details.get('title')}")
            print(f"   Tipo: {agent_details.get('type')}")
            print(f"   Inputs: {agent_details.get('inputs')}")
            print(f"   Modelos suportados: {agent_details.get('models')}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        
        # 2. Vamos também ver o agente 156 (Pixar Style)
        print("\n📋 Buscando detalhes do agente 156 (Pixar Style)...")
        try:
            agent_details = await client.get_agent(156)
            print(f"   Nome: {agent_details.get('title')}")
            print(f"   Tipo: {agent_details.get('type')}")
            print(f"   Inputs: {agent_details.get('inputs')}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        
        # 3. Buscar agentes de imagem disponíveis
        print("\n🔍 Buscando todos os agentes de imagem...")
        try:
            image_agents = await client.list_agents(type_filter="image", per_page=30)
            for agent in image_agents.get('data', []):
                print(f"   [{agent['id']}] {agent['title']}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        
        # 4. Testar vários agentes de imagem
        print("\n🎨 Testando agentes de imagem disponíveis...")
        
        # Lista de agentes para testar (do mais relevante ao menos)
        agents_to_test = [
            (165, "Imagens estilo Unsplash", "descreva-a-cena"),  # Fotos profissionais
            (157, "Fotos Incríveis de Paisagem", "descreva-a-cena"),
            (159, "Ícones 3D Modernos", "descricao"),
            (175, "Ilustrações 2D Profissionais", "descreva-a-cena"),
            (358, "Ilustrações 2D Gerais", "descreva-a-cena"),
        ]
        
        # Prompt para imagem de notícias financeiras
        prompt = """
        Professional financial trading scene.
        Modern office with multiple monitors displaying forex charts and market data.
        Gold bars and currency symbols EUR/USD visible.
        Corporate blue and gold color scheme.
        Clean, modern, institutional, premium style.
        High quality, professional photography.
        """
        
        for agent_id, agent_name, input_field in agents_to_test:
            print(f"\n   Testando [{agent_id}] {agent_name}...")
            
            try:
                # Primeiro buscar detalhes para ver inputs necessários
                agent_details = await client.get_agent(agent_id)
                print(f"      Inputs requeridos: {agent_details.get('inputs', 'N/A')}")
                
                # Tentar executar
                inputs = {
                    input_field: prompt,
                    "image_size": "square",
                    "num_inference_steps": "30",
                    "negative_prompt": "text, words, watermark, low quality"
                }
                
                result = await client.execute_agent(
                    agent_id=agent_id,
                    inputs=inputs
                )
                
                print(f"      ✅ Sucesso! Créditos: {result.get('credits', 'N/A')}")
                
                # Verificar output
                output = result.get('output', '')
                
                # Se for uma URL direta ou contém URL
                if output:
                    print(f"      Output: {str(output)[:200]}...")
                    
                    # Extrair URLs
                    import re
                    urls = re.findall(r'https?://[^\s<>"\']+', str(output))
                    if urls:
                        print(f"      🖼️ URL: {urls[0]}")
                        # Sucesso! Parar aqui
                        break
                            
            except Exception as e:
                print(f"      ❌ Erro: {str(e)[:100]}")


if __name__ == "__main__":
    asyncio.run(test_image_generation())
