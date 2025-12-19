"""
Script para gerar API Key para o Bot Thanos
============================================

Execute este script UMA VEZ para gerar a API Key.
A key só é mostrada uma vez, então guarde em local seguro!
"""

import sys
import json
from pathlib import Path

# Adiciona o path do backend
sys.path.insert(0, str(Path(__file__).parent))

from routes.external_bots_routes import api_key_storage

def generate_thanos_key():
    """Gera API Key para o Bot Thanos."""
    
    # Informações do bot
    BOT_NAME = "Thanos Bot"
    BOT_ID = "thanos_bot_2024"
    PERMISSIONS = ["read", "write", "trade", "metrics"]
    
    print("=" * 60)
    print("🔑 GERADOR DE API KEY - VIRTUS DASHBOARD")
    print("=" * 60)
    print()
    print(f"📦 Bot: {BOT_NAME}")
    print(f"🆔 ID: {BOT_ID}")
    print(f"🔐 Permissões: {', '.join(PERMISSIONS)}")
    print()
    
    # Verifica se já existe
    existing_keys = api_key_storage.get_all_keys()
    for key in existing_keys:
        if key.bot_id == BOT_ID and key.is_active:
            print("⚠️  ATENÇÃO: Já existe uma API Key ativa para este bot!")
            print(f"   Key ID: {key.key_id}")
            print(f"   Criada em: {key.created_at}")
            print()
            confirm = input("Deseja gerar uma NOVA key? (s/n): ").strip().lower()
            if confirm != 's':
                print("❌ Operação cancelada.")
                return
    
    # Gera a key
    api_key, key_info = api_key_storage.generate_key(
        bot_name=BOT_NAME,
        bot_id=BOT_ID,
        permissions=PERMISSIONS
    )
    
    print()
    print("✅ API KEY GERADA COM SUCESSO!")
    print()
    print("=" * 60)
    print("⚠️  IMPORTANTE: COPIE E GUARDE ESTA KEY!")
    print("    ELA NÃO SERÁ MOSTRADA NOVAMENTE!")
    print("=" * 60)
    print()
    print(f"🔑 API Key: {api_key}")
    print()
    print("=" * 60)
    print()
    print(f"📋 Key ID: {key_info.key_id}")
    print(f"📅 Criada: {key_info.created_at}")
    print(f"🚀 Status: {'Ativa' if key_info.is_active else 'Inativa'}")
    print()
    
    return api_key, key_info


if __name__ == "__main__":
    generate_thanos_key()
