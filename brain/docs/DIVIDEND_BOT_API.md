# VIRTUS Dividend Capture Bot API

## 📋 Visão Geral

Bot gerenciador e analisador de ações com foco na estratégia **Dividend Capture**:

1. 🔍 Identificar ações com dividendos próximos
2. 📊 Analisar fundamentals e timing
3. 💰 Comprar antes da data ex-dividendo
4. 💵 Receber o dividendo
5. 📈 Vender após estabilização do preço

## 🌐 Base URL

```
http://localhost:8000/api/dividend-bot
```

---

## 📡 Endpoints

### Informações

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Info e status do bot |
| `/settings` | GET | Configurações atuais |
| `/settings` | PUT | Atualizar configurações |

### Calendário e Dividendos

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/calendar` | GET | Calendário de dividendos (ex-dates e pagamentos) |
| `/upcoming` | GET | Próximos dividendos com filtros |
| `/recommendations` | GET | Melhores oportunidades |

### Análise de Ações

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/analyze/{ticker}` | GET | Análise completa de uma ação |
| `/analyze` | POST | Análise com valor de investimento |
| `/analyze-batch` | POST | Análise de múltiplas ações |
| `/simulate` | POST | Simular operação de dividend capture |

### Operações

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/operations` | GET | Listar operações |
| `/operations` | POST | Criar nova operação |
| `/operations/{id}` | GET | Detalhes da operação |
| `/operations/{id}/trade` | POST | Registrar compra/venda |
| `/operations/{id}/dividend` | POST | Registrar dividendo recebido |
| `/operations/{id}` | DELETE | Cancelar operação |

### Portfólio

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/portfolio/summary` | GET | Resumo do portfólio |
| `/portfolio/history` | GET | Histórico de ações |
| `/watchlist` | GET | Lista de observação |
| `/watchlist` | POST | Adicionar à watchlist |
| `/watchlist/{ticker}` | DELETE | Remover da watchlist |

---

## 📊 Exemplos de Uso

### 1. Listar Próximos Dividendos

```bash
GET /api/dividend-bot/upcoming?min_yield=5&sort_by=yield
```

**Resposta:**
```json
{
  "dividends": [
    {
      "ticker": "TAEE11",
      "company_name": "Taesa Unit",
      "dividend_type": "dividend",
      "value_per_share": 1.20,
      "ex_date": "2025-12-20",
      "payment_date": "2026-01-01",
      "dividend_yield": 8.5
    }
  ],
  "total": 5
}
```

### 2. Analisar Ação

```bash
GET /api/dividend-bot/analyze/PETR4?investment=10000
```

**Resposta:**
```json
{
  "ticker": "PETR4",
  "company_name": "Petrobras PN",
  "current_price": 34.50,
  "next_dividend": {
    "value_per_share": 1.45,
    "ex_date": "2025-12-22",
    "dividend_yield": 4.2
  },
  "recommendation": "buy",
  "recommendation_reason": "Bom momento para entrada",
  "score": 78,
  "suggested_entry_price": 33.81,
  "suggested_exit_price": 34.15,
  "expected_return": 4.44,
  "risk_level": "high"
}
```

### 3. Simular Operação

```bash
POST /api/dividend-bot/simulate?ticker=TAEE11&investment=5000
```

**Resposta:**
```json
{
  "simulation": {
    "ticker": "TAEE11",
    "investment": 5000.0,
    "shares": 139,
    "entry_price": 35.98,
    "exit_price": 35.02,
    "total_dividends": 166.80,
    "net_profit": 33.50,
    "return_percentage": 0.67
  },
  "analysis": {
    "recommendation": "buy",
    "score": 85
  }
}
```

### 4. Criar Operação

```bash
POST /api/dividend-bot/operations
Content-Type: application/json

{
  "ticker": "TAEE11",
  "target_shares": 100,
  "max_entry_price": 36.00,
  "expected_dividend": 1.20,
  "ex_date": "2025-12-20",
  "payment_date": "2026-01-01"
}
```

### 5. Registrar Compra

```bash
POST /api/dividend-bot/operations/{op_id}/trade
Content-Type: application/json

{
  "operation_id": "abc123",
  "action": "buy",
  "shares": 100,
  "price": 35.50,
  "fees": 5.00
}
```

### 6. Registrar Dividendo Recebido

```bash
POST /api/dividend-bot/operations/{op_id}/dividend?amount=120.00
```

---

## 📈 Modelo de Análise

### Critérios de Score (0-100)

| Critério | Peso | Descrição |
|----------|------|-----------|
| Dividend Yield | 25% | Maior yield = maior score |
| Consistência | 20% | Histórico de pagamentos |
| P/L | 15% | Menor P/L = maior score |
| Volatilidade | 15% | Menor volatilidade = menor risco |
| Liquidez | 15% | Maior volume = melhor execução |
| Timing | 10% | Dias até ex-date |

### Recomendações

| Score | Recomendação | Descrição |
|-------|--------------|-----------|
| 80-100 | BUY | Excelente oportunidade |
| 60-79 | WAIT | Aguardar melhor momento |
| 40-59 | HOLD | Manter se já possui |
| 0-39 | AVOID | Evitar - risco alto |

---

## ⚙️ Configurações

```json
{
  "min_dividend_yield": 5.0,
  "max_pe_ratio": 20.0,
  "min_liquidity": 100000,
  "buy_days_before_ex": 5,
  "sell_days_after_ex": 3,
  "max_position_size": 10000,
  "auto_trade": false,
  "notifications": true
}
```

---

## 🔄 Fluxo de Operação

```
1. PLANNED        → Operação criada, aguardando execução
2. WAITING_ENTRY  → Aguardando preço de entrada
3. POSITION_OPEN  → Posição comprada
4. EX_DATE_PASSED → Data ex passou
5. DIVIDEND_RECEIVED → Dividendo creditado
6. CLOSED         → Posição vendida, operação finalizada
```

---

## 📝 Notas

- **Data Ex-Dividendo**: Quem compra ANTES dessa data recebe o dividendo
- **Queda Típica**: Preço geralmente cai ~valor do dividendo após a data ex
- **Custos**: Considere corretagem, emolumentos e IR (15% sobre JCP)
- **Risco**: Estratégia de curto prazo com risco de queda maior que o dividendo

---

## 🚀 Próximos Passos (TODO)

1. [ ] Integrar com API de dados reais (StatusInvest, Yahoo Finance)
2. [ ] Adicionar backtesting histórico
3. [ ] Implementar alertas por Telegram/Email
4. [ ] Auto-trading com broker (XP, Clear, etc.)
5. [ ] Dashboard visual para acompanhamento
