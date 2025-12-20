"""
MT4 File Watcher - Monitora arquivos JSON do MT4 e envia para o backend
"""
import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime

# Configurações
BACKEND_URL = "http://127.0.0.1:8000"
MT4_DATA_FOLDER = r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
CHECK_INTERVAL = 5  # segundos

def get_file_path(filename):
    """Retorna o caminho completo do arquivo"""
    return os.path.join(MT4_DATA_FOLDER, filename)

def read_json_file(filepath):
    """Lê arquivo JSON com tratamento de erros"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
    except Exception as e:
        print(f"⚠️ Erro ao ler {filepath}: {e}")
    return None

def sync_account_data():
    """Sincroniza dados da conta"""
    filepath = get_file_path("account.json")
    data = read_json_file(filepath)
    
    if data:
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/mt4-account/sync/account",
                json=data,
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ Conta sincronizada: {data.get('name')} - ${data.get('balance')}")
                return True
            else:
                print(f"❌ Erro ao sincronizar conta: {response.status_code}")
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
    return False

def sync_trades_data():
    """Sincroniza histórico de trades"""
    filepath = get_file_path("trades.json")
    data = read_json_file(filepath)
    
    if data and isinstance(data, list):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/mt4-account/sync/trades",
                json=data,
                timeout=10
            )
            if response.status_code == 200:
                print(f"✅ {len(data)} trades sincronizados")
                return True
        except Exception as e:
            print(f"❌ Erro ao sincronizar trades: {e}")
    return False

def sync_positions_data():
    """Sincroniza posições abertas"""
    filepath = get_file_path("positions.json")
    data = read_json_file(filepath)
    
    if data is not None and isinstance(data, list):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/mt4-account/sync/positions",
                json=data,
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ {len(data)} posições sincronizadas")
                return True
        except Exception as e:
            print(f"❌ Erro ao sincronizar posições: {e}")
    return False

def check_backend():
    """Verifica se o backend está online"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def main():
    print("=" * 50)
    print("🚀 MT4 File Watcher - Virtus Trading System")
    print("=" * 50)
    print(f"📁 Monitorando: {MT4_DATA_FOLDER}")
    print(f"🌐 Backend: {BACKEND_URL}")
    print(f"⏱️ Intervalo: {CHECK_INTERVAL}s")
    print("=" * 50)
    
    # Verificar backend
    if not check_backend():
        print("⚠️ Backend não está respondendo!")
        print("   Certifique-se que o backend está rodando na porta 8000")
    else:
        print("✅ Backend online!")
    
    # Verificar pasta
    if not os.path.exists(MT4_DATA_FOLDER):
        print(f"⚠️ Pasta não existe: {MT4_DATA_FOLDER}")
        print("   Criando pasta...")
        os.makedirs(MT4_DATA_FOLDER, exist_ok=True)
    
    last_account_mtime = 0
    last_trades_mtime = 0
    last_positions_mtime = 0
    
    print("\n🔄 Iniciando monitoramento...\n")
    
    while True:
        try:
            # Verificar arquivo de conta
            account_file = get_file_path("account.json")
            if os.path.exists(account_file):
                mtime = os.path.getmtime(account_file)
                if mtime > last_account_mtime:
                    last_account_mtime = mtime
                    sync_account_data()
            
            # Verificar arquivo de trades
            trades_file = get_file_path("trades.json")
            if os.path.exists(trades_file):
                mtime = os.path.getmtime(trades_file)
                if mtime > last_trades_mtime:
                    last_trades_mtime = mtime
                    sync_trades_data()
            
            # Verificar arquivo de posições
            positions_file = get_file_path("positions.json")
            if os.path.exists(positions_file):
                mtime = os.path.getmtime(positions_file)
                if mtime > last_positions_mtime:
                    last_positions_mtime = mtime
                    sync_positions_data()
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n❌ Monitoramento encerrado pelo usuário")
            break
        except Exception as e:
            print(f"❌ Erro: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
