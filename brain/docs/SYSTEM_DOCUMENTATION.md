# VIRTUS Trading System - Documentação Completa

> **Versão:** 3.0  
> **Última atualização:** 15/12/2024  
> **Autor:** Virtus Team

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Módulos Principais](#módulos-principais)
4. [Fluxo de Execução](#fluxo-de-execução)
5. [Configuração](#configuração)
6. [Componentes Detalhados](#componentes-detalhados)
7. [Machine Learning](#machine-learning)
8. [Risk Management](#risk-management)
9. [Integrações Externas](#integrações-externas)
10. [Dashboard](#dashboard)
11. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

O **VIRTUS** é um sistema de trading automatizado multi-símbolo desenvolvido em Python. Combina análise técnica avançada, inteligência artificial e gestão de risco sofisticada para operar no mercado Forex via MetaTrader 5.

### Características Principais

| Feature | Descrição |
|---------|-----------|
| **Multi-Símbolo** | Opera XAUUSD, EURUSD, GBPUSD simultaneamente |
| **Multi-Estratégia** | 29 setups (Scalping, Trend, Reversal, Event) |
| **ML Integrado** | LSTM, KNN, Vision CNN, Ensemble Learning |
| **Risk Avançado** | Kelly Criterion, VaR, Anti-Martingale |
| **Brain Central** | Agregação de dados de múltiplas fontes |
| **TESS AI** | Integração com IA para análise de mercado |

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         VIRTUS SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   main.py   │───▶│ Orchestrator│───▶│  TradingBot │        │
│  └─────────────┘    └─────────────┘    └──────┬──────┘        │
│                                               │                 │
│  ┌─────────────┐    ┌─────────────┐    ┌──────▼──────┐        │
│  │    Brain    │◀──▶│   Advisor   │    │TradingEngine│        │
│  │  (Dados)    │    │  (Telegram) │    └──────┬──────┘        │
│  └─────────────┘    └─────────────┘           │                 │
│                                               │                 │
│  ┌───────────────────────────────────────────▼───────────────┐ │
│  │                    ANALYSIS LAYER                          │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │ │
│  │  │ Master   │ │Strategies│ │   ML     │ │  Risk    │     │ │
│  │  │ Analyzer │ │ Factory  │ │Prediction│ │ Manager  │     │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                   EXECUTION LAYER                          │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │ │
│  │  │   MT5    │ │ Position │ │   Exit   │ │ Database │     │ │
│  │  │ Orders   │ │Supervisor│ │ Manager  │ │  SQLite  │     │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Módulos Principais

### Estrutura de Diretórios

```
brain/
├── main.py                 # Ponto de entrada principal
├── config/                 # Arquivos de configuração
│   ├── config.yaml         # Configuração geral
│   ├── brain.yaml          # Configuração do Brain
│   ├── social.yaml         # Redes sociais
│   ├── tess.yaml           # TESS AI
│   └── bots/               # Configuração por bot
│       ├── gold.yaml       # XAUUSD
│       ├── euro.yaml       # EURUSD
│       └── gbp.yaml        # GBPUSD
│
├── src/                    # Código fonte
│   ├── core/               # Fundação do sistema
│   ├── brain/              # Serviço central de dados
│   ├── mt5/                # Interface MetaTrader 5
│   ├── analysis/           # Análise técnica
│   ├── strategies/         # Estratégias de trading
│   ├── ml/                 # Machine Learning
│   ├── risk/               # Gestão de risco
│   ├── bot/                # Bot de trading
│   ├── orchestrator/       # Orquestrador de bots
│   ├── positions/          # Gestão de posições
│   ├── telegram/           # Notificações Telegram
│   ├── advisor/            # Market Advisor
│   ├── database/           # Persistência
│   ├── integrations/       # TESS AI, APIs externas
│   ├── social/             # Redes sociais
│   ├── monitoring/         # Métricas
│   ├── reporting/          # Relatórios
│   └── backtesting/        # Backtesting
│
├── dashboard/              # Interface web
│   ├── backend/            # API FastAPI
│   └── frontend/           # React + TypeScript
│
├── models/                 # Modelos ML treinados
├── data/                   # Dados persistentes
└── scripts/                # Scripts auxiliares
```

---

## 🔄 Fluxo de Execução

### 1. Inicialização (`main.py`)

```python
# Ordem de inicialização
1. Config.from_yaml()          # Carrega configuração
2. MT5Connection.connect()      # Conecta ao MetaTrader 5
3. RiskManager.initialize()     # Inicializa gestão de risco
4. BrainService.get_instance()  # Inicia serviço de dados
5. TelegramService.start()      # Conecta Telegram (opcional)
6. MarketAdvisor.start()        # Inicia advisor
7. BotOrchestrator.start()      # Inicia bots
```

### 2. Ciclo do TradingBot

```python
# Loop principal de cada bot
while running:
    # 1. Coleta dados
    market_data = await mt5_data.get_market_snapshot(symbol)
    
    # 2. Análise completa
    analysis = await engine.analyze(market_data)
    
    # 3. Decisão de trading
    decision = await engine.make_decision(analysis)
    
    # 4. Execução (se aprovado)
    if decision.should_trade:
        await execute_trade(decision)
    
    # 5. Monitora posições abertas
    await monitor_positions()
    
    await asyncio.sleep(analysis_interval)
```

### 3. Pipeline de Análise (TradingEngine)

```
Dados MT5 ──▶ MasterAnalyzer ──▶ Strategies ──▶ ML Prediction ──▶ Risk Check ──▶ Decision
     │              │                │                │               │
     │     20 analisadores    4 estratégias    Vision + LSTM    Kelly + VaR
     │              │                │                │               │
     └──────────────┴────────────────┴────────────────┴───────────────┘
                                     │
                              TradeDecision
```

---

## ⚙️ Configuração

### config.yaml (Principal)

```yaml
# Credenciais MT5
mt5:
  login: 12345678
  password: "sua_senha"
  server: "Broker-Server"

# Símbolos ativos
symbols:
  - XAUUSD
  - EURUSD
  - GBPUSD

# Telegram
telegram:
  token: "BOT_TOKEN"
  chat_id: "CHAT_ID"

# Risk Management
risk:
  max_risk_per_trade: 0.01      # 1% por trade
  max_daily_drawdown: 0.05     # 5% drawdown diário
  max_open_positions: 3
  max_correlation_exposure: 0.6
```

### brain.yaml (Serviço de Dados)

```yaml
# APIs de dados
apis:
  forex_news:
    enabled: true
    api_key: "KEY"
  cftc:
    enabled: true  # COT Reports (gratuito)
  
# Cache
cache:
  ttl_seconds: 300
  max_entries: 1000
```

### tess.yaml (IA)

```yaml
api_key: "TESS_API_KEY"
base_url: "https://tess.pareto.io/api"
default_model: "gpt-4o-mini"

agents:
  instagram_caption: 131
  market_analysis: 1
```

---

## 🔍 Componentes Detalhados

### 1. MasterTechnicalAnalyzer

**Localização:** `src/analysis/master_analyzer.py`

Integra 9 sub-analisadores:

| Analisador | Função |
|------------|--------|
| MarketStructureAnalyzer | BOS, CHoCH, Swing Points |
| SmartMoneyAnalyzer | Order Blocks, FVG, Liquidity |
| VolumeAnalyzer | Profile, VSA, Delta |
| MultiTimeframeAnalyzer | Confluência MTF |
| DivergenceDetector | RSI, MACD divergências |
| FibonacciAnalyzer | Retracementes e extensões |
| HarmonicPatternDetector | Gartley, Butterfly, etc |
| AdvancedIndicators | Ichimoku, VWAP, Pivots |
| CorrelationAnalyzer | Correlação entre pares |

### 2. Strategies

**Localização:** `src/strategies/`

| Categoria | Setups | Descrição |
|-----------|--------|-----------|
| **Scalping** | 9 | Microestrutura, momentum rápido |
| **Trend** | 7 | SMC, MTF confluence |
| **Reversal** | 8 | Divergências, exaustão |
| **Event** | 5 | Notícias, calendário econômico |

### 3. TradingEngine

**Localização:** `src/bot/core/trading_engine.py`

Modos de operação:

```python
class TradingMode(Enum):
    SCALPING = "scalping"        # M1-M5, RR 1.2+
    TREND_FOLLOWING = "trend"    # H1-H4, RR 2.0+
    REVERSAL = "reversal"        # M15-H1, RR 2.5+
    EVENT_DRIVEN = "event"       # M5-M15, RR 1.5+
    ADAPTIVE = "adaptive"        # Auto-seleção
    CONSERVATIVE = "conservative" # Múltiplas confirmações
```

---

## 🤖 Machine Learning

### Modelos Disponíveis

| Modelo | Localização | Função |
|--------|-------------|--------|
| **VirtusLSTMModel** | `src/ml/models/lstm/` | Previsão de sequência temporal |
| **KNNPatternRecognizer** | `src/ml/models/knn/` | Reconhecimento de padrões |
| **VirtusVisionAnalyzer** | `src/ml/models/vision/` | Análise visual CNN de gráficos |
| **PredictionEngine** | `src/ml/models/prediction_engine.py` | Ensemble de modelos |

### PredictionService

```python
# Inicialização automática
prediction_service = PredictionService()
await prediction_service.initialize()

# Predição com ensemble + vision
prediction = await prediction_service.predict(
    symbol="XAUUSD",
    market_data=market_data,
    ohlcv_df=candles_dataframe  # Para Vision Analyzer
)

# Resultado
print(prediction.direction)      # "up", "down", "neutral"
print(prediction.confidence)     # 0.0 - 1.0
print(prediction.contributing_models)  # ['DirectionModel', 'VirtusVisionAnalyzer']
```

### Treinamento de Modelos

```bash
# Coletar dados
python scripts/collect_historical_data.py

# Preparar features
python scripts/prepare_ml_data.py

# Treinar
python scripts/train_simple_model.py

# Walk-forward validation
python scripts/train_walkforward.py
```

---

## 🛡️ Risk Management

### Componentes

| Componente | Função |
|------------|--------|
| **RiskManager** | Gestão central de risco |
| **AdvancedRiskManager** | Kelly, VaR, Monte Carlo |
| **ExposureManager** | Controle de exposição total |
| **PositionSizer** | Cálculo de lote otimizado |
| **CorrelationRisk** | Risco entre pares correlacionados |

### Parâmetros Críticos

```python
# Position Sizing (Kelly Criterion)
kelly_fraction = 0.25  # Kelly reduzido
max_position_pct = 0.02  # 2% máximo

# Stop Loss
max_sl_pips = 50  # SL máximo
atr_multiplier = 1.5  # SL baseado em ATR

# Drawdown
max_daily_dd = 0.05  # 5% diário
max_weekly_dd = 0.10  # 10% semanal

# Circuit Breaker
max_consecutive_losses = 3
cooldown_after_loss = 300  # segundos
```

### Exit Manager (8 tipos de trailing)

```python
class TrailingType(Enum):
    FIXED = "fixed"           # Trailing fixo em pips
    ATR_BASED = "atr"         # Baseado em ATR
    PERCENTAGE = "percentage" # Percentual do lucro
    CHANDELIER = "chandelier" # Chandelier Exit
    PARABOLIC = "parabolic"   # SAR parabólico
    SWING_BASED = "swing"     # Baseado em swings
    STEP_TRAIL = "step"       # Trailing em degraus
    BREAKEVEN = "breakeven"   # Move para breakeven
```

---

## 🔌 Integrações Externas

### 1. MetaTrader 5

```python
# Conexão
mt5 = await MT5Connection.get_instance()
await mt5.connect(login, password, server)

# Dados
data_service = MT5DataService()
candles = await data_service.get_candles(symbol, timeframe, count)

# Ordens
order_manager = MT5OrderManager()
ticket = await order_manager.open_position(
    symbol, direction, volume, sl, tp
)
```

### 2. TESS AI

**Uso atual:**

| Componente | Função |
|------------|--------|
| **TessCaptionService** | Gera captions para Instagram/LinkedIn |
| **TessMarketAnalyzer** | Análise de sentimento de notícias |

```python
# Análise de sentimento
from src.integrations.tess import TessMarketAnalyzer

analyzer = TessMarketAnalyzer()
await analyzer.initialize()

sentiment = await analyzer.analyze_news_sentiment(news_list, symbol="XAUUSD")
# sentiment.sentiment = "bullish" | "bearish" | "neutral"
# sentiment.confidence = 0.85
# sentiment.impact = "high"
```

### 3. Telegram

```python
# Notificações
telegram = await TelegramService.get_instance()
await telegram.send_message("🟢 Trade aberto: XAUUSD BUY @ 2650.50")

# Comandos disponíveis
/status - Status do sistema
/positions - Posições abertas
/pnl - Profit/Loss do dia
/stop - Para todos os bots
```

### 4. Dados de Mercado (Brain)

| Provider | Dados |
|----------|-------|
| **ForexNews** | Notícias em tempo real |
| **CFTC** | COT Reports (posicionamento institucional) |
| **Finnhub** | Dados fundamentais |
| **TwelveData** | Dados históricos |

---

## 📊 Dashboard

### Backend (FastAPI)

```
http://localhost:8000

/api/health          - Status do sistema
/api/auth/login      - Autenticação
/api/dashboard/overview - Visão geral
/api/bots            - Lista de bots
/api/positions       - Posições abertas
/api/trades          - Histórico de trades
/api/news            - Notícias
/ws                  - WebSocket para real-time
```

### Iniciar Dashboard

```bash
# Backend
cd brain/dashboard/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
cd brain/dashboard/frontend
npm install
npm run dev
```

---

## 🔧 Troubleshooting

### Problemas Comuns

| Problema | Solução |
|----------|---------|
| MT5 não conecta | Verificar credenciais e servidor |
| Telegram não envia | Verificar token e chat_id |
| Brain sem dados | Verificar API keys dos providers |
| ML não prediz | Executar scripts de treinamento |
| Dashboard 404 | Instalar uvicorn e websockets |

### Logs

```
brain/data/logs/
├── virtus.log        # Log principal
├── trading.log       # Operações de trading
├── brain.log         # Serviço de dados
└── errors.log        # Apenas erros
```

### Comandos Úteis

```bash
# Verificar imports
python -c "from src.core import *; print('OK')"

# Testar MT5
python -c "from src.mt5 import MT5Connection; print('OK')"

# Verificar modelos ML
python -c "from src.ml.models import *; print('OK')"

# Status do sistema
python -c "from src.bot import TradingBot; print('OK')"
```

---

## 📈 Métricas de Performance

### KPIs Monitorados

- **Win Rate:** % de trades vencedores
- **Profit Factor:** Lucro bruto / Prejuízo bruto
- **Max Drawdown:** Maior queda do equity
- **Sharpe Ratio:** Retorno ajustado ao risco
- **Expectancy:** Expectativa matemática por trade

### Prometheus Metrics

```
# Métricas expostas
virtus_trades_total
virtus_profit_total
virtus_positions_open
virtus_equity_current
virtus_drawdown_current
```

---

## 📞 Suporte

- **Logs:** `brain/data/logs/`
- **Config:** `brain/config/`
- **Documentação:** `brain/docs/`

---

*Documentação gerada em 15/12/2024 - VIRTUS v3.0*
