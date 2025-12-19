"""
Teste da API de Bots Externos
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/external"

print("=" * 60)
print("TESTE DA API DE BOTS EXTERNOS - VIRTUS DASHBOARD")
print("=" * 60)

# 1. Teste sem API Key (deve retornar 401)
print("\n1. Teste /info sem API Key (esperado: 401)...")
try:
    r = requests.get(f"{BASE_URL}/info")
    print(f"   Status: {r.status_code}")
    print(f"   Resposta: {r.json()}")
except Exception as e:
    print(f"   Erro: {e}")

# 2. Teste endpoint admin (não precisa de API Key do bot)
print("\n2. Teste /admin/bots (lista bots registrados)...")
try:
    r = requests.get(f"{BASE_URL}/admin/bots")
    print(f"   Status: {r.status_code}")
    data = r.json()
    print(f"   Total bots: {data.get('total', 0)}")
    for bot in data.get('bots', []):
        print(f"   - {bot['bot_name']} ({bot['bot_id']})")
except Exception as e:
    print(f"   Erro: {e}")

# 3. Teste endpoint realtime (todos os bots)
print("\n3. Teste /admin/realtime (dados tempo real)...")
try:
    r = requests.get(f"{BASE_URL}/admin/realtime")
    print(f"   Status: {r.status_code}")
    data = r.json()
    print(f"   Summary: {json.dumps(data.get('summary', {}), indent=4)}")
except Exception as e:
    print(f"   Erro: {e}")

# 4. Teste endpoint positions
print("\n4. Teste /admin/positions (todas posições)...")
try:
    r = requests.get(f"{BASE_URL}/admin/positions")
    print(f"   Status: {r.status_code}")
    data = r.json()
    print(f"   Total positions: {data.get('total', 0)}")
except Exception as e:
    print(f"   Erro: {e}")

# 5. Verifica se há API Keys existentes
print("\n5. Verificando estrutura de dados...")
import os
from pathlib import Path

ext_bots_path = Path(r"C:\Users\Administrator\Desktop\Virtus\brain\data\external_bots")
if ext_bots_path.exists():
    print(f"   Pasta external_bots existe: {ext_bots_path}")
    for item in ext_bots_path.iterdir():
        print(f"   - {item.name}")
else:
    print(f"   Pasta external_bots NÃO existe")
    print(f"   Será criada automaticamente ao gerar primeira API Key")

print("\n" + "=" * 60)
print("TESTE CONCLUÍDO!")
print("=" * 60)
print("\nPróximos passos:")
print("1. Gere uma API Key no dashboard (Configurações > Bots Externos)")
print("2. Use o cliente Python (brain/docs/external_bot_client.py)")
print("3. Envie updates a cada 30-60 segundos")
