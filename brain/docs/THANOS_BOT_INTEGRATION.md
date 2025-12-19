# 🤖 Documentação de Integração - Bot Thanos
## VIRTUS Dashboard External Bot API

---

## 📋 Informações da Integração

| Campo | Valor |
|-------|-------|
| **Bot Name** | Thanos Bot |
| **Bot ID** | `thanos_bot_2024` |
| **API Key** | `vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns` |
| **Key ID** | `ef40945cccc6634a` |
| **Permissões** | read, write, trade, metrics |
| **Base URL** | `https://api.virtusinvestimentos.com.br` |
| **Local/Dev** | `http://localhost:8000` |
| **Rate Limit** | 100 requests/minuto |

---

## 🔐 Autenticação

Todas as requisições devem incluir o header `X-API-Key`:

```
X-API-Key: vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns
```

### Exemplo cURL:
```bash
curl -X GET "http://localhost:8000/api/external/info" \
     -H "X-API-Key: vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns"
```

---

## 📡 Endpoints Disponíveis

### 1️⃣ GET `/api/external/info`
Informações sobre a API (não requer autenticação).

```bash
curl -X GET "http://localhost:8000/api/external/info"
```

---

### 2️⃣ POST `/api/external/signal`
**Enviar um sinal de trading.**

#### Request Body:
```json
{
    "symbol": "XAUUSD",
    "direction": "buy",
    "entry_price": 2650.50,
    "stop_loss": 2645.00,
    "take_profit": 2665.00,
    "confidence": 0.85,
    "timeframe": "M15",
    "strategy": "thanos_main",
    "metadata": {
        "reason": "Suporte testado com volume",
        "indicators": ["RSI", "MACD"]
    }
}
```

#### Campos:
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `symbol` | string | ✅ | Símbolo do ativo (XAUUSD, EURUSD, etc) |
| `direction` | string | ✅ | `buy`, `sell`, ou `close` |
| `entry_price` | float | ❌ | Preço de entrada sugerido |
| `stop_loss` | float | ❌ | Stop Loss |
| `take_profit` | float | ❌ | Take Profit |
| `confidence` | float | ❌ | Confiança 0-1 (default: 0.7) |
| `timeframe` | string | ❌ | Timeframe (default: M15) |
| `strategy` | string | ❌ | Nome da estratégia |
| `metadata` | object | ❌ | Dados adicionais |

#### Response:
```json
{
    "success": true,
    "signal_id": "thanos_bot_2024_1_20241216131500",
    "message": "Signal received and queued for processing",
    "received_at": "2024-12-16T13:15:00.123456"
}
```

#### Exemplo cURL:
```bash
curl -X POST "http://localhost:8000/api/external/signal" \
     -H "X-API-Key: vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns" \
     -H "Content-Type: application/json" \
     -d '{
         "symbol": "XAUUSD",
         "direction": "buy",
         "entry_price": 2650.50,
         "stop_loss": 2645.00,
         "take_profit": 2665.00,
         "confidence": 0.85,
         "timeframe": "M15",
         "strategy": "thanos_main"
     }'
```

---

### 3️⃣ POST `/api/external/trade`
**Reportar um trade executado.**

#### Request Body:
```json
{
    "external_id": "thanos_12345",
    "symbol": "XAUUSD",
    "direction": "buy",
    "status": "opened",
    "entry_price": 2650.50,
    "current_price": 2652.00,
    "volume": 0.10,
    "stop_loss": 2645.00,
    "take_profit": 2665.00,
    "profit": 15.00,
    "profit_pips": 15.0,
    "open_time": "2024-12-16T13:15:00",
    "metadata": {
        "ticket": 123456789
    }
}
```

#### Campos:
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `external_id` | string | ✅ | ID único do trade no seu sistema |
| `symbol` | string | ✅ | Símbolo |
| `direction` | string | ✅ | `buy`, `sell`, `close` |
| `status` | string | ✅ | `pending`, `opened`, `closed`, `cancelled`, `error` |
| `entry_price` | float | ✅ | Preço de entrada |
| `current_price` | float | ❌ | Preço atual (para trades abertos) |
| `exit_price` | float | ❌ | Preço de saída (para trades fechados) |
| `volume` | float | ✅ | Volume/Lotes |
| `stop_loss` | float | ❌ | Stop Loss |
| `take_profit` | float | ❌ | Take Profit |
| `profit` | float | ❌ | Lucro/Prejuízo em $ |
| `profit_pips` | float | ❌ | Lucro em pips |
| `open_time` | string | ✅ | Data/hora abertura ISO 8601 |
| `close_time` | string | ❌ | Data/hora fechamento ISO 8601 |
| `metadata` | object | ❌ | Dados adicionais |

#### Response:
```json
{
    "success": true,
    "internal_id": "thanos_bot_2024_trade_thanos_12345",
    "external_id": "thanos_12345",
    "status": "opened",
    "message": "Trade recorded successfully"
}
```

---

### 4️⃣ POST `/api/external/status`
**Atualizar status do bot.**

Envie a cada 30-60 segundos para manter o dashboard atualizado.

#### Request Body:
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
    "last_trade_time": "2024-12-16T12:30:00",
    "errors": [],
    "metadata": {
        "version": "1.0.5",
        "mode": "live"
    }
}
```

#### Response:
```json
{
    "success": true,
    "bot_id": "thanos_bot_2024",
    "updated_at": "2024-12-16T13:20:00.123456"
}
```

---

### 5️⃣ POST `/api/external/metrics`
**Enviar métricas de performance.**

Envie ao final de cada dia ou periodicamente.

#### Request Body:
```json
{
    "total_trades": 150,
    "winning_trades": 95,
    "losing_trades": 55,
    "win_rate": 0.633,
    "total_profit": 2500.00,
    "total_profit_pips": 850.5,
    "max_drawdown": 350.00,
    "profit_factor": 1.85,
    "average_win": 45.00,
    "average_loss": 25.00,
    "best_trade": 250.00,
    "worst_trade": -80.00,
    "period": "monthly"
}
```

#### Response:
```json
{
    "success": true,
    "bot_id": "thanos_bot_2024",
    "period": "monthly",
    "updated_at": "2024-12-16T23:59:00.123456"
}
```

---

### 6️⃣ GET `/api/external/signals`
**Listar sinais enviados.**

```bash
curl -X GET "http://localhost:8000/api/external/signals?limit=50" \
     -H "X-API-Key: vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns"
```

#### Query Parameters:
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `limit` | int | 100 | Máximo de sinais (1-1000) |

---

### 7️⃣ GET `/api/external/trades`
**Listar trades reportados.**

```bash
curl -X GET "http://localhost:8000/api/external/trades?limit=50&status=opened" \
     -H "X-API-Key: vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns"
```

#### Query Parameters:
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `limit` | int | 100 | Máximo de trades (1-1000) |
| `status` | string | null | Filtrar por status |

---

### 8️⃣ GET `/api/external/bot-status`
**Obter último status enviado.**

```bash
curl -X GET "http://localhost:8000/api/external/bot-status" \
     -H "X-API-Key: vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns"
```

---

### 9️⃣ GET `/api/external/bot-metrics`
**Obter métricas enviadas.**

```bash
curl -X GET "http://localhost:8000/api/external/bot-metrics" \
     -H "X-API-Key: vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns"
```

---

## 💻 Exemplos de Implementação

### Python
```python
import requests
from datetime import datetime

API_KEY = "vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns"
BASE_URL = "http://localhost:8000"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Enviar sinal
signal = {
    "symbol": "XAUUSD",
    "direction": "buy",
    "entry_price": 2650.50,
    "stop_loss": 2645.00,
    "take_profit": 2665.00,
    "confidence": 0.85,
    "strategy": "thanos_scalping"
}

response = requests.post(
    f"{BASE_URL}/api/external/signal",
    json=signal,
    headers=headers
)
print(response.json())

# Atualizar status
status = {
    "is_running": True,
    "is_connected": True,
    "account_balance": 10000.00,
    "open_positions": 1,
    "daily_profit": 50.00,
    "daily_trades": 3,
    "uptime_seconds": 3600
}

response = requests.post(
    f"{BASE_URL}/api/external/status",
    json=status,
    headers=headers
)
print(response.json())
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

const API_KEY = 'vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns';
const BASE_URL = 'http://localhost:8000';

const client = axios.create({
    baseURL: BASE_URL,
    headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
    }
});

// Enviar sinal
async function sendSignal(signal) {
    try {
        const response = await client.post('/api/external/signal', signal);
        console.log('Signal sent:', response.data);
        return response.data;
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

// Exemplo
sendSignal({
    symbol: 'XAUUSD',
    direction: 'buy',
    entry_price: 2650.50,
    stop_loss: 2645.00,
    take_profit: 2665.00,
    confidence: 0.85
});
```

### MQL5 (MetaTrader 5)
```mql5
#include <Web.mqh>

string API_KEY = "vts_KSyXDX97wJbI91q26nnfpSKf1fNeye42lfrgVfI9Yns";
string BASE_URL = "http://localhost:8000";

int SendSignal(string symbol, string direction, double entry, double sl, double tp)
{
    string headers = "X-API-Key: " + API_KEY + "\r\nContent-Type: application/json\r\n";
    string url = BASE_URL + "/api/external/signal";
    
    string json = StringFormat(
        "{\"symbol\":\"%s\",\"direction\":\"%s\",\"entry_price\":%.5f,\"stop_loss\":%.5f,\"take_profit\":%.5f}",
        symbol, direction, entry, sl, tp
    );
    
    char data[], result[];
    StringToCharArray(json, data, 0, StringLen(json));
    
    int res = WebRequest("POST", url, headers, 5000, data, result, headers);
    
    if(res == 200)
    {
        Print("Signal sent successfully: ", CharArrayToString(result));
        return 1;
    }
    else
    {
        Print("Error sending signal: ", res);
        return -1;
    }
}
```

---

## ⚠️ Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 400 | Bad Request - Dados inválidos |
| 401 | Unauthorized - API Key inválida ou ausente |
| 403 | Forbidden - Sem permissão |
| 429 | Rate Limit - Muitas requisições |
| 500 | Erro interno do servidor |

---

## 🔄 Fluxo Recomendado

1. **Inicialização do Bot**:
   - Envie status inicial com `is_running: true`
   
2. **Durante operação**:
   - Envie status a cada 30-60 segundos
   - Envie sinais quando detectar oportunidades
   - Reporte trades quando executados/atualizados
   
3. **Fim do dia**:
   - Envie métricas consolidadas

4. **Encerramento do Bot**:
   - Envie status final com `is_running: false`

---

## 📞 Suporte

- **Email**: admin@virtusinvestimentos.com.br
- **Dashboard**: https://dashboard.virtusinvestimentos.com.br

---

## 📝 Changelog

| Versão | Data | Alterações |
|--------|------|------------|
| 1.0.0 | 2024-12-16 | Versão inicial da API |

---

> ⚠️ **SEGURANÇA**: Mantenha sua API Key em segredo! Não compartilhe em repositórios públicos ou logs.
