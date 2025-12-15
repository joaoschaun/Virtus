"""
VIRTUS - Setup Automático do Instagram
======================================
Execute este script e siga as instruções!
"""

import asyncio
import aiohttp
import json
import webbrowser
from pathlib import Path

# SUAS CREDENCIAIS
APP_ID = "783040488084825"
APP_SECRET = "c324a0bb726be9a154ea65a7b1c2bd57"

BASE_URL = "https://graph.facebook.com/v18.0"


async def fazer_requisicao(url, params=None):
    """Faz requisição à API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def main():
    print("=" * 60)
    print("   VIRTUS - CONFIGURAÇÃO DO INSTAGRAM")
    print("=" * 60)
    print(f"\n   App ID: {APP_ID}")
    print("=" * 60)
    
    # Passo 1: Abrir Graph API Explorer
    print("\n📌 PASSO 1: Obter Token de Acesso")
    print("-" * 50)
    print("\nVou abrir o Graph API Explorer no navegador.")
    print("Lá você precisa:")
    print("  1. Selecionar o app '783040488084825' no dropdown")
    print("  2. Clicar em 'Gerar Token de Acesso'")
    print("  3. Autorizar quando pedir")
    print("  4. Copiar o token gerado")
    
    input("\n>>> Pressione ENTER para abrir o navegador...")
    
    # Abre o Explorer
    explorer_url = f"https://developers.facebook.com/tools/explorer/?app_id={APP_ID}"
    webbrowser.open(explorer_url)
    
    print("\n✅ Navegador aberto!")
    print("\nNa página que abriu:")
    print("  - No campo 'Aplicativo Meta', selecione seu app")
    print("  - Clique em 'Gerar Token de Acesso' (botão azul)")
    print("  - Se pedir permissões, aceite")
    print("  - Copie o TOKEN que aparecer na caixa de texto")
    
    # Passo 2: Receber o token
    print("\n" + "-" * 50)
    token = input("\n🔑 Cole o TOKEN aqui: ").strip()
    
    if not token:
        print("\n❌ Token é obrigatório!")
        return
    
    # Verificar token
    print("\n🔍 Verificando token...")
    
    result = await fazer_requisicao(
        f"{BASE_URL}/debug_token",
        {"input_token": token, "access_token": token}
    )
    
    if "error" in result:
        print(f"\n❌ Erro: {result['error'].get('message', 'Token inválido')}")
        print("\nPossíveis problemas:")
        print("  - Token copiado errado")
        print("  - App não selecionado corretamente")
        print("  - Precisa adicionar plataforma 'Site' nas configurações do app")
        return
    
    data = result.get("data", {})
    if not data.get("is_valid"):
        print("\n❌ Token inválido ou expirado!")
        return
    
    print("\n✅ Token válido!")
    scopes = data.get("scopes", [])
    print(f"   Permissões: {', '.join(scopes)}")
    
    # Verificar permissões Instagram
    tem_instagram = "instagram_basic" in scopes or "instagram_content_publish" in scopes
    
    if not tem_instagram:
        print("\n⚠️  ATENÇÃO: Permissões do Instagram não encontradas!")
        print("\nVocê precisa:")
        print("  1. Ir nas configurações do app")
        print("  2. Adicionar produto 'Instagram Graph API'")
        print("  3. Gerar novo token com as permissões")
        
        add_ig = input("\nDeseja continuar mesmo assim? (s/n): ").lower()
        if add_ig != 's':
            return
    
    # Passo 3: Buscar páginas
    print("\n📄 PASSO 2: Buscando suas Páginas...")
    print("-" * 50)
    
    pages_result = await fazer_requisicao(
        f"{BASE_URL}/me/accounts",
        {"access_token": token}
    )
    
    if "error" in pages_result:
        print(f"\n❌ Erro: {pages_result['error'].get('message')}")
        return
    
    pages = pages_result.get("data", [])
    
    if not pages:
        print("\n❌ Nenhuma página encontrada!")
        print("\nVocê precisa:")
        print("  1. Criar uma Página no Facebook")
        print("  2. Ou verificar se tem permissão 'pages_show_list'")
        return
    
    print(f"\n✅ {len(pages)} página(s) encontrada(s):\n")
    for i, page in enumerate(pages, 1):
        print(f"   {i}. {page['name']}")
    
    if len(pages) == 1:
        selected_page = pages[0]
    else:
        choice = input("\nEscolha o número da página: ").strip()
        try:
            selected_page = pages[int(choice) - 1]
        except:
            selected_page = pages[0]
    
    page_id = selected_page["id"]
    page_name = selected_page["name"]
    page_token = selected_page.get("access_token", token)
    
    print(f"\n✅ Página selecionada: {page_name}")
    
    # Passo 4: Buscar Instagram
    print("\n📸 PASSO 3: Buscando conta do Instagram...")
    print("-" * 50)
    
    ig_result = await fazer_requisicao(
        f"{BASE_URL}/{page_id}",
        {"fields": "instagram_business_account", "access_token": page_token}
    )
    
    if "error" in ig_result:
        print(f"\n❌ Erro: {ig_result['error'].get('message')}")
        return
    
    ig_account = ig_result.get("instagram_business_account")
    
    if not ig_account:
        print("\n❌ Nenhum Instagram vinculado a esta página!")
        print("\n📋 Para vincular:")
        print("   1. Abra o Instagram (app no celular)")
        print("   2. Vá em Configurações → Conta")
        print("   3. Mude para 'Conta Profissional' (Creator ou Business)")
        print("   4. Vincule à sua Página do Facebook")
        print("\n   Depois execute este script novamente!")
        return
    
    instagram_id = ig_account["id"]
    
    # Buscar info do Instagram
    ig_info = await fazer_requisicao(
        f"{BASE_URL}/{instagram_id}",
        {
            "fields": "username,name,followers_count,media_count",
            "access_token": page_token
        }
    )
    
    username = ig_info.get("username", "N/A")
    
    print(f"\n✅ Instagram encontrado!")
    print(f"   Username: @{username}")
    print(f"   Seguidores: {ig_info.get('followers_count', 'N/A')}")
    print(f"   Posts: {ig_info.get('media_count', 'N/A')}")
    
    # Passo 5: Gerar token de longa duração
    print("\n⏰ PASSO 4: Gerando token de longa duração...")
    print("-" * 50)
    
    long_token_result = await fazer_requisicao(
        f"{BASE_URL}/oauth/access_token",
        {
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": token
        }
    )
    
    if "access_token" in long_token_result:
        final_token = long_token_result["access_token"]
        expires = long_token_result.get("expires_in", 5184000)
        days = expires // 86400
        print(f"✅ Token de longa duração gerado! Expira em ~{days} dias")
    else:
        final_token = page_token
        print("⚠️  Usando token original (pode expirar em algumas horas)")
    
    # Resumo final
    print("\n" + "=" * 60)
    print("   📋 CONFIGURAÇÃO COMPLETA!")
    print("=" * 60)
    
    config = {
        "app_id": APP_ID,
        "page_id": page_id,
        "page_name": page_name,
        "instagram_account_id": instagram_id,
        "instagram_username": username,
        "access_token": final_token,
    }
    
    print(f"""
   App ID:       {APP_ID}
   Página:       {page_name} ({page_id})
   Instagram:    @{username} ({instagram_id})
   Token:        {final_token[:30]}...
""")
    
    # Salvar
    save_path = Path(__file__).parent / "data" / "instagram_config.json"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(save_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuração salva em: {save_path}")
    
    # Atualizar social.yaml
    yaml_path = Path(__file__).parent / "config" / "social.yaml"
    print(f"\n📝 Atualize o arquivo {yaml_path} com:")
    print(f"""
instagram:
  access_token: "{final_token}"
  account_id: "{instagram_id}"
  page_id: "{page_id}"
  
# Mude para false para publicar de verdade:
use_mock: false
""")
    
    print("=" * 60)
    print("   🎉 PRONTO! Sistema configurado!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nCancelado.")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
