# VIRTUS - Integração EODHD Financial APIs

## Visão Geral

O sistema VIRTUS integra a API **EODHD** (End of Day Historical Data) para fornecer dados financeiros completos, incluindo:

- 📊 **Market Data**: Preços EOD, intraday e real-time
- 📋 **Dados Fundamentais**: Perfil de empresas, balanços, métricas
- 📅 **Calendário Econômico**: Eventos, earnings, IPOs
- 📰 **Notícias**: Artigos financeiros e análise de sentimento
- 📈 **Indicadores Técnicos**: SMA, EMA, RSI, MACD, Bollinger Bands
- 🌍 **Dados Macro**: PIB, inflação, desemprego por país

## Configuração

### API Key

A API key está configurada em `brain/config/config.yaml`:

```yaml
api_keys:
  eodhd: "694154fa05aa82.59300876"
```

### Limites de Budget

Configuração em `brain/config/brain.yaml`:

```yaml
budget:
  providers:
    eodhd:
      monthly_limit: 100000
      daily_limit: 10000
      min_interval_ms: 500
      priority: 1
```

## Arquitetura

### Provider

`brain/src/brain/providers/eodhd_provider.py`

Implementa a classe `EODHDProvider` que herda de `BaseProvider` e fornece:

```python
# Inicialização
provider = EODHDProvider(api_key="sua_key")

# Market Data
await provider.get_eod_data("AAPL.US")
await provider.get_live_price("EURUSD.FOREX")
await provider.get_intraday_data("BTC-USD.CC")

# Fundamentals
await provider.get_fundamentals("AAPL.US")
await provider.get_company_profile("MSFT.US")

# Economic Calendar
await provider.get_economic_events()
await provider.get_earnings_calendar()
await provider.get_ipos_calendar()

# News & Sentiment
await provider.get_news(symbols=["AAPL.US"])
await provider.get_sentiment("AAPL.US")

# Technical Indicators
await provider.get_rsi("EURUSD.FOREX")
await provider.get_macd("XAUUSD.FOREX")
await provider.get_bbands("GBPUSD.FOREX")

# Macro Data
await provider.get_gdp_growth("USA")
await provider.get_inflation("BRA")
```

### Data Service

`brain/src/brain/eodhd_service.py`

Serviço de alto nível com métodos agregados:

```python
service = EODHDDataService(api_key)
await service.initialize()

# Market Overview (Forex, Índices, Crypto)
overview = await service.get_market_overview()

# Economic Calendar completo
calendar = await service.get_economic_overview()

# News & Sentiment
sentiment = await service.get_sentiment_overview()

# Technical Analysis completa
analysis = await service.get_technical_analysis("EURUSD", "FOREX")
```

### Brain Service Integration

`brain/src/brain/brain_service.py`

O EODHD é integrado como provider principal:

```python
brain = await BrainService.get_instance()

# Dados de mercado
data = await brain.get_market_data("XAUUSD", "eod")

# Indicadores técnicos
indicators = await brain.get_technical_indicators("EURUSD")

# Calendário econômico
calendar = await brain.get_economic_calendar_enhanced()

# Dados fundamentais
fundamentals = await brain.get_fundamentals("AAPL")

# Dados macro
macro = await brain.get_macro_data("USA")

# Forex
forex = await brain.get_forex_data("EURUSD", "live")

# Crypto
crypto = await brain.get_crypto_data("BTC-USD")
```

## API REST (Dashboard)

### Endpoints Disponíveis

Base URL: `/api/eodhd`

#### Market Data

```
GET /market/overview           - Visão geral do mercado
GET /market/quote/{symbol}     - Cotação de símbolo
GET /market/historical/{symbol} - Dados históricos
```

#### Economic Calendar

```
GET /calendar/events           - Eventos econômicos
GET /calendar/earnings         - Calendário de earnings
GET /calendar/today            - Eventos de hoje
```

#### News

```
GET /news                      - Notícias gerais
GET /news/forex                - Notícias de Forex
GET /news/crypto               - Notícias de Crypto
```

#### Technical Analysis

```
GET /technical/{symbol}        - Indicadores técnicos
GET /technical/analysis/{symbol} - Análise técnica completa
```

#### Fundamental Data

```
GET /fundamentals/{symbol}     - Dados fundamentais
```

#### Macro Data

```
GET /macro/{country}           - Dados macro de país
GET /macro/overview            - Visão geral macro
```

#### Search

```
GET /search?query={term}       - Busca de símbolos
```

#### Health

```
GET /health                    - Status da integração
```

## Frontend (React)

### Componente EODHDSection

`brain/dashboard/frontend/src/components/EODHDSection.tsx`

Componente React que exibe:

1. **Market Overview**: Cards com cotações de Forex, Índices e Crypto
2. **Calendário Econômico**: Lista de eventos com impacto e valores
3. **Notícias**: Artigos com sentimento e símbolos relacionados

### Uso

```tsx
import EODHDSection from './components/EODHDSection';

// No App.tsx ou Dashboard.tsx
<EODHDSection apiUrl="/api" />
```

## Formato de Símbolos

O EODHD usa formato `SYMBOL.EXCHANGE`:

| Tipo | Formato | Exemplo |
|------|---------|---------|
| Ações US | SYMBOL.US | AAPL.US |
| Forex | PAIR.FOREX | EURUSD.FOREX |
| Crypto | SYMBOL.CC | BTC-USD.CC |
| Índices | SYMBOL.INDX | GSPC.INDX |
| Brasil B3 | SYMBOL.SA | PETR4.SA |

## Mapeamento de Símbolos Virtus

O sistema mapeia automaticamente:

```yaml
# Em brain.yaml
symbol_mapping:
  XAUUSD: "XAUUSD.FOREX"
  EURUSD: "EURUSD.FOREX"
  BTCUSD: "BTC-USD.CC"
  SPX: "GSPC.INDX"
```

## Planos EODHD

| Recurso | Free | Basic | All World |
|---------|------|-------|-----------|
| EOD Data | ❌ | ✅ | ✅ |
| Real-time | ❌ | 15min delay | ✅ |
| Fundamentals | ✅ | ✅ | ✅ |
| News | ✅ | ✅ | ✅ |
| Calendar | ✅ | ✅ | ✅ |
| Technical | ❌ | ✅ | ✅ |
| Macro | ✅ | ✅ | ✅ |

## Testes

Execute o teste de integração:

```bash
cd brain
python test_eodhd.py
```

## Troubleshooting

### Erro 403 Forbidden

Alguns endpoints requerem plano pago. Use endpoints gratuitos:
- `/news`
- `/economic-events`
- `/fundamentals`
- `/macro-indicator`
- `/search`

### Rate Limiting

O sistema implementa controle de budget automático. Ajuste em `brain.yaml`:

```yaml
budget:
  providers:
    eodhd:
      daily_limit: 10000
      min_interval_ms: 500
```

### Cache

TTLs configurados em `brain.yaml`:

```yaml
cache:
  ttl:
    eodhd_eod: 3600       # 1 hora
    eodhd_intraday: 300   # 5 minutos
    eodhd_live: 60        # 1 minuto
    eodhd_fundamentals: 86400  # 24 horas
    eodhd_news: 900       # 15 minutos
```

## Links

- [EODHD Documentation](https://eodhd.com/financial-apis/)
- [API Reference](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes/)
- [Pricing](https://eodhd.com/pricing)

## Changelog

### v1.0.0 (2024-12-16)
- Integração inicial com EODHD
- Provider completo com todos os endpoints
- Serviço de dados de alto nível
- Rotas REST para dashboard
- Componente React para exibição
- Documentação completa
