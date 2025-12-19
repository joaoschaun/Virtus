# VIRTUS Trading System v3.0 - Novos Módulos de Infraestrutura

## Visão Geral

Este documento descreve os novos módulos de infraestrutura adicionados ao sistema VIRTUS para melhorar segurança, resiliência, observabilidade e manutenibilidade.

## Índice

1. [Configuração de Ambiente](#1-configuração-de-ambiente)
2. [Circuit Breaker](#2-circuit-breaker)
3. [Rate Limiter](#3-rate-limiter)
4. [Retry com Backoff](#4-retry-com-backoff)
5. [Cache de Análises](#5-cache-de-análises)
6. [Webhooks](#6-webhooks)
7. [Logging Estruturado](#7-logging-estruturado)
8. [Health Check](#8-health-check)
9. [Métricas](#9-métricas)
10. [Backup](#10-backup)

---

## 1. Configuração de Ambiente

### Localização
- `brain/.env.example` - Template de variáveis
- `brain/src/core/env_config.py` - Classe de configuração

### Como Usar

1. Copie o arquivo de exemplo:
```powershell
Copy-Item brain/.env.example brain/.env
```

2. Edite o `.env` com suas credenciais reais:
```env
MT5_LOGIN=61444598
MT5_PASSWORD=sua_senha_aqui
MT5_SERVER=Pepperstone-Demo
```

3. No código:
```python
from src.core.env_config import EnvConfig

# Configurações MT5
mt5_config = EnvConfig.mt5()
login = mt5_config['login']

# Configurações Telegram
telegram = EnvConfig.telegram()
bot_token = telegram['bot_token']
```

### Variáveis Suportadas

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| `MT5_LOGIN` | Login da conta MT5 | Sim |
| `MT5_PASSWORD` | Senha da conta MT5 | Sim |
| `MT5_SERVER` | Servidor MT5 | Sim |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram | Sim |
| `FINNHUB_API_KEY` | API key Finnhub | Não |
| `EODHD_API_KEY` | API key EODHD | Não |

---

## 2. Circuit Breaker

### Localização
`brain/src/core/circuit_breaker.py`

### O que é?
O Circuit Breaker protege contra falhas cascata. Quando um serviço está falhando repetidamente, o circuito "abre" e impede novas chamadas, dando tempo para o serviço se recuperar.

### Estados
- **CLOSED**: Normal, chamadas passam
- **OPEN**: Bloqueado, chamadas são rejeitadas imediatamente
- **HALF_OPEN**: Testando, permite uma chamada de teste

### Como Usar

```python
from src.core.circuit_breaker import circuit_breaker, circuit_breaker_manager

# Como decorador
@circuit_breaker("mt5_connection")
async def get_positions():
    return await mt5.get_positions()

# Verificando estado
cb = circuit_breaker_manager.get_breaker("mt5_connection")
if cb.can_execute():
    result = await get_positions()
```

### Configuração

```python
from src.core.circuit_breaker import CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,      # Falhas para abrir
    timeout_seconds=60,       # Tempo para tentar novamente
    success_threshold=2,      # Sucessos para fechar
)
```

---

## 3. Rate Limiter

### Localização
`brain/src/core/rate_limiter.py`

### O que é?
O Rate Limiter controla a frequência de requisições para evitar exceder limites de APIs externas.

### Algoritmo
Token Bucket - Tokens são adicionados a uma taxa constante, cada requisição consome um token.

### Como Usar

```python
from src.core.rate_limiter import rate_limiter, rate_limited

# Configurar API
rate_limiter.configure("minha_api", requests_per_second=2, burst_size=5)

# Uso manual
if await rate_limiter.acquire("minha_api"):
    result = await fetch_data()

# Como decorador
@rate_limited("finnhub")
async def get_news():
    return await finnhub.get_news()
```

### Configurações Padrão

| API | Requests/s | Burst |
|-----|------------|-------|
| finnhub | 1 | 5 |
| forexnews | 0.5 | 3 |
| mt5 | 10 | 20 |

---

## 4. Retry com Backoff

### Localização
`brain/src/core/retry.py`

### O que é?
Retenta operações automaticamente com espera exponencial entre tentativas (backoff).

### Como Usar

```python
from src.core.retry import retry_async, with_retry, API_RETRY_CONFIG

# Função com retry manual
result = await retry_async(unstable_function, config=API_RETRY_CONFIG)

# Como decorador
@with_retry(max_retries=3, base_delay=1.0)
async def get_market_data():
    return await api.get_data()
```

### Configurações Predefinidas

- `API_RETRY_CONFIG`: 3 tentativas, 1s base, jitter ativo
- `CRITICAL_RETRY_CONFIG`: 5 tentativas, 2s base, delay máximo 120s
- `DB_RETRY_CONFIG`: 2 tentativas, 0.5s base, sem jitter

---

## 5. Cache de Análises

### Localização
`brain/src/core/cache.py`

### O que é?
Cache em memória com TTL (Time To Live) para evitar recálculos desnecessários.

### Como Usar

```python
from src.core.cache import analysis_cache, cached, CacheKey

# Set/Get manual
await analysis_cache.set("market_data:XAUUSD", data)
result = await analysis_cache.get("market_data:XAUUSD")

# Como decorador
@cached(key="analysis:XAUUSD", ttl=30)
async def get_analysis():
    return heavy_calculation()

# Gerando chaves
key = CacheKey.analysis("XAUUSD", "trend")
```

### TTLs Padrão

| Tipo | TTL |
|------|-----|
| market_data | 5 segundos |
| analysis | 30 segundos |
| signals | 10 segundos |
| news | 300 segundos |
| positions | 2 segundos |

---

## 6. Webhooks

### Localização
`brain/src/core/webhooks.py`

### O que é?
Sistema de notificação para sistemas externos via HTTP callbacks.

### Como Usar

```python
from src.core.webhooks import webhook_manager, WebhookConfig, WebhookEvent

# Registrar webhook
webhook_manager.register(WebhookConfig(
    id="discord",
    name="Discord Alerts",
    url="https://discord.com/api/webhooks/xxx/yyy",
    events=[WebhookEvent.TRADE_OPENED, WebhookEvent.TRADE_CLOSED],
    secret="chave_hmac",
))

# Disparar evento
await webhook_manager.dispatch(
    WebhookEvent.TRADE_OPENED,
    {"symbol": "XAUUSD", "type": "BUY", "volume": 0.01}
)
```

### Eventos Disponíveis

| Evento | Descrição |
|--------|-----------|
| `TRADE_OPENED` | Nova posição aberta |
| `TRADE_CLOSED` | Posição fechada |
| `SIGNAL_GENERATED` | Novo sinal gerado |
| `ALERT_TRIGGERED` | Alerta disparado |
| `SYSTEM_ERROR` | Erro no sistema |
| `BOT_STATUS_CHANGE` | Bot iniciado/parado |

### Segurança

Webhooks são assinados com HMAC-SHA256. O header `X-Webhook-Signature` contém a assinatura.

Verificação no receptor:
```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## 7. Logging Estruturado

### Localização
`brain/src/core/structured_logging.py`

### O que é?
Logs em formato JSON para análise em ferramentas como ELK, Datadog, Splunk.

### Como Usar

```python
from src.core.structured_logging import setup_structured_logging, log_trade, log_error

# Setup
setup_structured_logging(level="INFO", log_file="brain/data/logs/app.json")

# Log de trade
log_trade(
    ticket=123456,
    action="open",
    symbol="XAUUSD",
    volume=0.01,
    price=2050.50,
)

# Log de erro
try:
    risky_operation()
except Exception as e:
    log_error(e, context={"symbol": "XAUUSD"})
```

### Formato de Saída

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "virtus",
  "message": "Trade opened",
  "context": {
    "ticket": 123456,
    "symbol": "XAUUSD",
    "volume": 0.01
  }
}
```

---

## 8. Health Check

### Localização
`brain/dashboard/backend/routes/health_routes.py`

### Endpoints

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/health` | Status completo de todos componentes |
| `GET /api/health/live` | Liveness probe (servidor ativo?) |
| `GET /api/health/ready` | Readiness probe (pronto para requests?) |
| `GET /api/health/{component}` | Status de um componente específico |

### Componentes Verificados

- **MT5**: Conexão com MetaTrader 5
- **Database**: Conexão com SQLite
- **Disk**: Espaço em disco disponível
- **Memory**: Uso de memória
- **CPU**: Uso de CPU
- **Brain API**: Conexão com API do Brain

### Exemplo de Resposta

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "3.0.0",
  "uptime_seconds": 3600,
  "components": {
    "mt5": {"status": "healthy", "connected": true},
    "database": {"status": "healthy", "response_time_ms": 5},
    "disk": {"status": "healthy", "free_percent": 75.5},
    "memory": {"status": "healthy", "used_percent": 45.2}
  }
}
```

---

## 9. Métricas

### Localização
`brain/src/monitoring/metrics.py`

### Como Usar

```python
from src.monitoring.metrics import metrics_collector

# Registrar trade
metrics_collector.record_trade(
    symbol="XAUUSD",
    profit=45.50,
    pips=20,
    duration_seconds=3600,
)

# Timer automático
with metrics_collector.timer("analysis"):
    result = await heavy_calculation()

# Obter resumo
summary = metrics_collector.get_summary()
```

### Métricas Coletadas

- **Trades**: Total, wins, losses, win rate, profit total
- **Operations**: Análises, conexões, erros por tipo
- **Timing**: Duração de operações
- **System**: CPU, memória, uptime

---

## 10. Backup

### Localização
`backup.ps1`

### Como Usar

```powershell
# Backup completo
.\backup.ps1

# Apenas banco de dados
.\backup.ps1 -Type db

# Apenas configurações
.\backup.ps1 -Type config
```

### O que é Salvo

| Tipo | Conteúdo |
|------|----------|
| `full` | Tudo abaixo |
| `db` | `brain/data/*.db`, `*.json` de estado |
| `config` | `brain/config/*.yaml` |
| `logs` | `brain/data/logs/*` |
| `state` | `brain/data/bot_state.json` |

### Retenção

Por padrão, backups com mais de 30 dias são removidos automaticamente.

---

## Integração

### Exemplo Completo

```python
from src.core.env_config import EnvConfig
from src.core.circuit_breaker import circuit_breaker
from src.core.rate_limiter import rate_limited
from src.core.retry import with_retry
from src.core.cache import cached
from src.core.webhooks import webhook_manager, WebhookEvent
from src.core.structured_logging import log_trade

class TradingService:
    @circuit_breaker("mt5")
    @rate_limited("mt5")
    @with_retry(max_retries=3)
    @cached(ttl=2)
    async def get_positions(self):
        return await self.mt5.get_positions()
    
    async def execute_trade(self, signal):
        trade = await self.mt5.open_position(signal)
        
        # Log estruturado
        log_trade(
            ticket=trade.ticket,
            action="open",
            symbol=trade.symbol,
            volume=trade.volume,
            price=trade.price,
        )
        
        # Notifica sistemas externos
        await webhook_manager.dispatch(
            WebhookEvent.TRADE_OPENED,
            trade.to_dict()
        )
        
        return trade
```

---

## Testes

### Rodando Testes

```powershell
cd brain
python -m pytest tests/test_core.py -v
```

### Cobertura

```powershell
python -m pytest tests/test_core.py --cov=src/core --cov-report=html
```

---

## Troubleshooting

### Circuit Breaker Aberto
```python
# Verificar estado
cb = circuit_breaker_manager.get_breaker("mt5")
print(f"Estado: {cb.state}")
print(f"Falhas: {cb._failure_count}")

# Resetar manualmente
cb.reset()
```

### Cache Não Funcionando
```python
# Verificar estatísticas
stats = analysis_cache.get_stats()
print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")

# Limpar cache
await analysis_cache.clear()
```

### Rate Limiter Bloqueando
```python
# Verificar configuração
stats = rate_limiter.get_stats()
print(stats)

# Ajustar limites
rate_limiter.configure("api", requests_per_second=5, burst_size=10)
```

---

## Próximos Passos Recomendados

1. **Configurar .env**: Copiar `.env.example` para `.env` e preencher credenciais
2. **Testar Health Check**: Acessar `http://localhost:8000/api/health`
3. **Configurar Webhooks**: Adicionar endpoints externos para notificações
4. **Agendar Backup**: Criar task no Windows para rodar `backup.ps1` diariamente

---

*Documentação gerada em: Janeiro 2025*
*VIRTUS Trading System v3.0*
