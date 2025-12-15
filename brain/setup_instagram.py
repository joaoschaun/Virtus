"""
VIRTUS - Assistente de Configuração do Instagram
=================================================

Este script te ajuda a configurar a API do Instagram.
Execute e siga as instruções!
"""

import asyncio
import aiohttp
import json
from pathlib import Path


class InstagramSetupAssistant:
    """Assistente para configurar Instagram API."""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self):
        self.app_id = None
        self.app_secret = None
        self.access_token = None
        self.page_id = None
        self.instagram_account_id = None
    
    async def verify_token(self, token: str) -> dict:
        """Verifica se o token é válido."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/debug_token"
            params = {
                "input_token": token,
                "access_token": token,
            }
            async with session.get(url, params=params) as resp:
                return await resp.json()
    
    async def get_user_pages(self, token: str) -> dict:
        """Obtém páginas do Facebook do usuário."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/me/accounts"
            params = {"access_token": token}
            async with session.get(url, params=params) as resp:
                return await resp.json()
    
    async def get_instagram_account(self, page_id: str, token: str) -> dict:
        """Obtém conta do Instagram vinculada à página."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/{page_id}"
            params = {
                "fields": "instagram_business_account",
                "access_token": token,
            }
            async with session.get(url, params=params) as resp:
                return await resp.json()
    
    async def get_instagram_info(self, ig_id: str, token: str) -> dict:
        """Obtém informações da conta do Instagram."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/{ig_id}"
            params = {
                "fields": "username,name,biography,followers_count,media_count",
                "access_token": token,
            }
            async with session.get(url, params=params) as resp:
                return await resp.json()
    
    async def get_long_lived_token(self, short_token: str, app_id: str, app_secret: str) -> dict:
        """Converte token curto em token de longa duração."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            }
            async with session.get(url, params=params) as resp:
                return await resp.json()
    
    def save_config(self, config: dict):
        """Salva configuração no arquivo YAML."""
        config_path = Path(__file__).parent / "config" / "social.yaml"
        
        # Atualiza apenas as credenciais
        import yaml
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                current = yaml.safe_load(f) or {}
        else:
            current = {}
        
        # Atualiza
        if 'social_media' not in current:
            current['social_media'] = {}
        if 'instagram' not in current['social_media']:
            current['social_media']['instagram'] = {}
        
        current['social_media']['instagram']['access_token'] = config['access_token']
        current['social_media']['instagram']['account_id'] = config['instagram_account_id']
        current['social_media']['instagram']['page_id'] = config['page_id']
        current['social_media']['use_mock'] = False
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(current, f, allow_unicode=True, default_flow_style=False)
        
        print(f"\n✅ Configuração salva em: {config_path}")


async def main():
    print("=" * 60)
    print("   VIRTUS - Assistente de Configuração do Instagram")
    print("=" * 60)
    
    assistant = InstagramSetupAssistant()
    
    # Passo 1: App ID e Secret
    print("\n📱 PASSO 1: Informações do App")
    print("-" * 40)
    
    app_id = input("App ID (1390535695900407): ").strip() or "1390535695900407"
    app_secret = input("App Secret: ").strip()
    
    if not app_secret:
        print("\n⚠️  App Secret é necessário para gerar token de longa duração.")
        print("   Você pode continuar sem ele, mas o token vai expirar em 1 hora.")
    
    # Passo 2: Token de Acesso
    print("\n🔑 PASSO 2: Token de Acesso")
    print("-" * 40)
    print("Obtenha o token em: https://developers.facebook.com/tools/explorer/")
    print("Selecione seu app e gere um 'Token de Acesso do Usuário'")
    print("Permissões necessárias: pages_show_list, instagram_basic, instagram_content_publish")
    
    token = input("\nCole o Token de Acesso: ").strip()
    
    if not token:
        print("\n❌ Token é obrigatório!")
        return
    
    # Verificar token
    print("\n🔍 Verificando token...")
    result = await assistant.verify_token(token)
    
    if "error" in result:
        print(f"\n❌ Erro: {result['error'].get('message', 'Token inválido')}")
        return
    
    token_data = result.get("data", {})
    if not token_data.get("is_valid"):
        print("\n❌ Token inválido ou expirado!")
        return
    
    print("✅ Token válido!")
    print(f"   Escopos: {', '.join(token_data.get('scopes', []))}")
    
    # Verificar permissões do Instagram
    scopes = token_data.get('scopes', [])
    if 'instagram_basic' not in scopes:
        print("\n⚠️  ATENÇÃO: Permissão 'instagram_basic' não encontrada!")
        print("   Adicione o produto Instagram ao seu app e gere novo token.")
        
        cont = input("\nDeseja continuar mesmo assim? (s/n): ").strip().lower()
        if cont != 's':
            return
    
    # Passo 3: Obter Páginas
    print("\n📄 PASSO 3: Selecionando Página do Facebook")
    print("-" * 40)
    
    pages_result = await assistant.get_user_pages(token)
    
    if "error" in pages_result:
        print(f"\n❌ Erro ao buscar páginas: {pages_result['error'].get('message')}")
        return
    
    pages = pages_result.get("data", [])
    
    if not pages:
        print("\n❌ Nenhuma página encontrada!")
        print("   Certifique-se de que você administra uma Página do Facebook")
        print("   e que o Instagram está vinculado a ela.")
        return
    
    print(f"\n📋 Páginas encontradas ({len(pages)}):")
    for i, page in enumerate(pages, 1):
        print(f"   {i}. {page['name']} (ID: {page['id']})")
    
    if len(pages) == 1:
        selected = pages[0]
        print(f"\n✅ Usando: {selected['name']}")
    else:
        choice = input("\nEscolha o número da página: ").strip()
        try:
            selected = pages[int(choice) - 1]
        except:
            print("❌ Escolha inválida!")
            return
    
    page_id = selected['id']
    page_token = selected.get('access_token', token)
    
    # Passo 4: Obter Instagram Business Account
    print("\n📸 PASSO 4: Buscando conta do Instagram")
    print("-" * 40)
    
    ig_result = await assistant.get_instagram_account(page_id, page_token)
    
    if "error" in ig_result:
        print(f"\n❌ Erro: {ig_result['error'].get('message')}")
        return
    
    ig_account = ig_result.get("instagram_business_account")
    
    if not ig_account:
        print("\n❌ Nenhuma conta do Instagram vinculada a esta página!")
        print("\n📋 Para vincular:")
        print("   1. Vá no app do Instagram")
        print("   2. Configurações → Conta → Mudar para conta profissional")
        print("   3. Vincule à sua Página do Facebook")
        return
    
    instagram_id = ig_account['id']
    
    # Obter info do Instagram
    ig_info = await assistant.get_instagram_info(instagram_id, page_token)
    
    print(f"\n✅ Instagram encontrado!")
    print(f"   Username: @{ig_info.get('username', 'N/A')}")
    print(f"   Nome: {ig_info.get('name', 'N/A')}")
    print(f"   Seguidores: {ig_info.get('followers_count', 'N/A')}")
    print(f"   Posts: {ig_info.get('media_count', 'N/A')}")
    print(f"   ID: {instagram_id}")
    
    # Passo 5: Token de longa duração
    final_token = page_token
    
    if app_secret:
        print("\n⏰ PASSO 5: Gerando token de longa duração")
        print("-" * 40)
        
        long_token_result = await assistant.get_long_lived_token(token, app_id, app_secret)
        
        if "access_token" in long_token_result:
            final_token = long_token_result['access_token']
            expires = long_token_result.get('expires_in', 0)
            days = expires // 86400
            print(f"✅ Token de longa duração gerado!")
            print(f"   Expira em: ~{days} dias")
        else:
            print(f"⚠️  Não foi possível gerar token longo: {long_token_result.get('error', {}).get('message', 'Erro')}")
            print("   Usando token original (expira em 1 hora)")
    
    # Resumo
    print("\n" + "=" * 60)
    print("   📋 RESUMO DA CONFIGURAÇÃO")
    print("=" * 60)
    print(f"\n   App ID: {app_id}")
    print(f"   Page ID: {page_id}")
    print(f"   Instagram ID: {instagram_id}")
    print(f"   Instagram: @{ig_info.get('username', 'N/A')}")
    print(f"   Token: {final_token[:20]}...{final_token[-10:]}")
    
    # Salvar?
    print("\n" + "-" * 60)
    save = input("\n💾 Salvar configuração? (s/n): ").strip().lower()
    
    if save == 's':
        config = {
            "app_id": app_id,
            "page_id": page_id,
            "instagram_account_id": instagram_id,
            "access_token": final_token,
        }
        
        # Salva em JSON também como backup
        backup_path = Path(__file__).parent / "data" / "instagram_config.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(backup_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Backup salvo em: {backup_path}")
        
        # Tenta salvar no YAML
        try:
            assistant.save_config(config)
        except Exception as e:
            print(f"⚠️  Não foi possível atualizar social.yaml: {e}")
            print(f"   Use os dados do backup JSON para configurar manualmente.")
    
    print("\n" + "=" * 60)
    print("   ✅ CONFIGURAÇÃO CONCLUÍDA!")
    print("=" * 60)
    print("\nAgora você pode usar o sistema de social media!")
    print("O modo mock será desativado automaticamente.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
