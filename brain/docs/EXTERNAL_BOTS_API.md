# VIRTUS Dashboard - API para Bots Externos

## 📋 Visão Geral

A API de Bots Externos permite integrar bots de trading externos com o dashboard VIRTUS. Através desta API, seus bots podem:

- Enviar dados em tempo real (equity, posições, métricas)
- Reportar sinais de trading
- Registrar trades executados
- Manter histórico de performance

## 🔐 Autenticação

### Obtendo uma API Key

1. Acesse o dashboard VIRTUS
2. Vá em **Configurações > Bots Externos**
3. Clique em **"Gerar Nova API Key"**
4. **IMPORTANTE**: Copie a key imediatamente - ela só aparece uma vez!

### Usando a API Key

Inclua a key em todas as requisições no header:

```
X-API-Key: vts_sua_api_key_aqui
```

### Formato da API Key

```
vts_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🌐 Base URL

```
Desenvolvimento: http://localhost:8000/api/external
Produção: https://seu-servidor.com/api/external
```

---

## 📡 Endpoints

### 1. POST /update - Atualização Completa ⭐ PRINCIPAL

**Endpoint mais importante!** Envie a cada 30-60 segundos para manter o dashboard atualizado em tempo real.

```bash
POST /api/external/update
```

**Body (JSON):**

```json
{
  "is_running": true,
  "is_connected": true,
  
  "account_balance": 10000.00,
  "account_equity": 10150.00,
  "account_margin": 500.00,
  "account_free_margin": 9650.00,
  "account_profit": 150.00,
  
  "positions": [
    {
      "ticket": 123456,
      "symbol": "XAUUSD",
      "direction": "buy",
      "volume": 0.1,
      "entry_price": 2650.50,
      "current_price": 2655.00,
      "stop_loss": 2640.00,
      "take_profit": 2670.00,
      "profit": 45.00,
      "profit_pips": 45,
      "open_time": "2024-01-15T10:30:00",
      "swap": -1.20,
      "commission": -0.50,
      "magic": 12345,
      "comment": "Gold Strategy"
    }
  ],
  
  "daily_profit": 150.00,
  "daily_profit_pips": 120,
  "daily_trades": 5,
  "daily_wins": 3,
  "daily_losses": 2,
  
  "total_trades": 250,
  "total_profit": 3500.00,
  "win_rate": 62.5,
  "max_drawdown": 8.5,
  
  "uptime_seconds": 28800,
  "last_trade_time": "2024-01-15T14:45:00",
  "bot_version": "2.1.0",
  "strategy_name": "Multi-Symbol Strategy",
  "errors": [],
  "metadata": {}
}
```

**Resposta:**

```json
{
  "success": true,
  "bot_id": "gold_bot_2024",
  "received_at": "2024-01-15T15:30:00.123456",
  "positions_count": 1,
  "message": "Full update received successfully"
}
```

---

### 2. POST /signal - Enviar Sinal

Envia um sinal de trading para o dashboard.

```bash
POST /api/external/signal
```

**Body:**

```json
{
  "symbol": "XAUUSD",
  "direction": "buy",
  "entry_price": 2650.00,
  "stop_loss": 2640.00,
  "take_profit": 2670.00,
  "confidence": 0.85,
  "timeframe": "M15",
  "strategy": "Breakout Strategy",
  "metadata": {
    "indicator": "RSI",
    "value": 35
  }
}
```

**Campos:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| symbol | string | ✅ | Símbolo do ativo |
| direction | string | ✅ | "buy", "sell" ou "close" |
| entry_price | float | ❌ | Preço de entrada sugerido |
| stop_loss | float | ❌ | Stop loss |
| take_profit | float | ❌ | Take profit |
| confidence | float | ❌ | Confiança (0-1), default: 0.7 |
| timeframe | string | ❌ | Timeframe, default: "M15" |
| strategy | string | ❌ | Nome da estratégia |
| metadata | object | ❌ | Dados adicionais |

**Resposta:**

```json
{
  "success": true,
  "signal_id": "sig_abc123",
  "message": "Signal received and queued for processing",
  "received_at": "2024-01-15T15:30:00"
}
```

---

### 3. POST /trade - Reportar Trade

Reporta um trade executado externamente.

```bash
POST /api/external/trade
```

**Body:**

```json
{
  "external_id": "MT5_123456",
  "symbol": "EURUSD",
  "direction": "buy",
  "status": "closed",
  "entry_price": 1.0850,
  "exit_price": 1.0880,
  "volume": 0.1,
  "stop_loss": 1.0820,
  "take_profit": 1.0900,
  "profit": 30.00,
  "profit_pips": 30,
  "open_time": "2024-01-15T10:30:00",
  "close_time": "2024-01-15T14:45:00",
  "metadata": {}
}
```

**Campos status:**
- `pending` - Ordem pendente
- `opened` - Trade aberto
- `closed` - Trade fechado
- `cancelled` - Cancelado
- `error` - Erro

---

### 4. POST /status - Atualizar Status (Leve)

Atualização simplificada do status (sem posições detalhadas).

```bash
POST /api/external/status
```

**Body:**

```json
{
  "is_running": true,
  "is_connected": true,
  "account_balance": 10000.00,
  "account_equity": 10150.00,
  "open_positions": 2,
  "daily_profit": 150.00,
  "daily_trades": 5,
  "uptime_seconds": 28800,
  "last_trade_time": "2024-01-15T14:45:00",
  "errors": []
}
```

---

### 5. POST /metrics - Enviar Métricas

Envia métricas de performance (recomendado 1x ao dia).

```bash
POST /api/external/metrics
```

**Body:**

```json
{
  "total_trades": 250,
  "winning_trades": 156,
  "losing_trades": 94,
  "win_rate": 62.5,
  "total_profit": 3500.00,
  "total_profit_pips": 2800,
  "max_drawdown": 8.5,
  "profit_factor": 1.85,
  "average_win": 35.00,
  "average_loss": -22.00,
  "best_trade": 150.00,
  "worst_trade": -80.00,
  "period": "all_time"
}
```

---

### 6. GET /info - Info da API

Retorna informações sobre a API e seu bot.

```bash
GET /api/external/info
```

**Resposta:**

```json
{
  "version": "1.0.0",
  "bot_info": {
    "bot_id": "gold_bot_2024",
    "bot_name": "Gold Trading Bot",
    "is_active": true,
    "permissions": ["read", "write", "trade"],
    "created_at": "2024-01-01T00:00:00"
  },
  "rate_limit": "100 requests/minute"
}
```

---

### 7. GET /signals - Listar Sinais

Retorna sinais enviados pelo bot.

```bash
GET /api/external/signals?limit=100
```

---

### 8. GET /trades - Listar Trades

Retorna trades do bot.

```bash
GET /api/external/trades?limit=100&status=closed
```

---

### 9. GET /bot-status - Último Status

Retorna o último status enviado.

```bash
GET /api/external/bot-status
```

---

### 10. GET /bot-metrics - Métricas

Retorna as métricas do bot.

```bash
GET /api/external/bot-metrics
```

---

## 🎯 Endpoints Admin (Dashboard)

Endpoints usados pelo frontend do dashboard (não requerem API Key do bot):

| Endpoint | Descrição |
|----------|-----------|
| GET /admin/bots | Lista todos os bots externos |
| GET /admin/bot/{bot_id} | Detalhes de um bot específico |
| GET /admin/realtime | Dados tempo real de todos os bots |
| GET /admin/realtime/{bot_id} | Dados tempo real de um bot |
| GET /admin/positions | Todas as posições abertas |

---

## 🐍 Cliente Python

Use o cliente Python pronto em [external_bot_client.py](external_bot_client.py):

```python
from external_bot_client import VirtusDashboardClient, Position

# Inicializa
client = VirtusDashboardClient(
    api_key="vts_sua_api_key",
    base_url="http://localhost:8000"
)

# Testa conexão
if client.test_connection():
    print("Conectado!")

# Envia update completo
client.send_full_update(
    account_balance=10000.0,
    account_equity=10150.0,
    positions=[
        Position(
            ticket=123456,
            symbol="XAUUSD",
            direction="buy",
            volume=0.1,
            entry_price=2650.50,
            current_price=2655.00,
            profit=45.0,
            open_time="2024-01-15T10:30:00"
        )
    ],
    daily_profit=150.0,
    daily_trades=5
)
```

---

## 📊 Exemplo de Integração com MT5

```python
import MetaTrader5 as mt5
from external_bot_client import VirtusDashboardClient, Position
from datetime import datetime
import time

# Configuração
client = VirtusDashboardClient(
    api_key="vts_sua_api_key",
    base_url="http://localhost:8000"
)

def get_mt5_positions():
    """Converte posições MT5 para formato VIRTUS."""
    positions = []
    for pos in mt5.positions_get():
        positions.append(Position(
            ticket=pos.ticket,
            symbol=pos.symbol,
            direction="buy" if pos.type == 0 else "sell",
            volume=pos.volume,
            entry_price=pos.price_open,
            current_price=pos.price_current,
            stop_loss=pos.sl,
            take_profit=pos.tp,
            profit=pos.profit,
            swap=pos.swap,
            commission=pos.commission,
            magic=pos.magic,
            comment=pos.comment,
            open_time=datetime.fromtimestamp(pos.time).isoformat()
        ))
    return positions

def update_dashboard():
    """Envia atualização para o dashboard."""
    account = mt5.account_info()
    
    client.send_full_update(
        account_balance=account.balance,
        account_equity=account.equity,
        account_margin=account.margin,
        account_free_margin=account.margin_free,
        account_profit=account.profit,
        positions=get_mt5_positions(),
        is_running=True,
        is_connected=True
    )

# Loop principal
while True:
    try:
        update_dashboard()
        print(f"[{datetime.now()}] Update enviado")
    except Exception as e:
        print(f"Erro: {e}")
        client.add_error(str(e))
    
    time.sleep(30)  # Atualiza a cada 30 segundos
```

---

## ⚠️ Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 401 | API Key inválida ou não fornecida |
| 403 | Permissão negada |
| 429 | Rate limit excedido (max 100/min) |
| 500 | Erro interno do servidor |

---

## 🔄 Rate Limiting

- **Limite**: 100 requisições por minuto
- **Recomendado**: 
  - `/update`: 1x a cada 30-60 segundos
  - `/signal`: Quando houver sinal
  - `/trade`: Quando trade abrir/fechar
  - `/metrics`: 1x ao final do dia

---

## 📝 Notas Importantes

1. **API Key Segura**: Nunca compartilhe ou commite sua API Key
2. **ISO 8601**: Todas as datas devem estar no formato ISO 8601
3. **Retry**: Implemente retry em caso de falhas de rede
4. **Logs**: Mantenha logs locais das requisições
5. **Validação**: Valide dados antes de enviar

---

## 🆘 Suporte

Em caso de problemas:
1. Verifique se a API Key está correta
2. Confirme que o dashboard está rodando
3. Verifique os logs do backend
4. Teste com o endpoint `/info` primeiro
