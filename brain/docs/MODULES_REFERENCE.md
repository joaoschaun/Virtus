# VIRTUS - Arquitetura de Módulos

## 📦 Módulos do Sistema

### Core (`src/core/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `config.py` | `Config` | Carregamento e validação de configuração |
| `logger.py` | `LoggerSetup` | Sistema de logging centralizado |
| `performance_tracker.py` | `PerformanceTracker` | Tracking de métricas de performance |

---

### Brain (`src/brain/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `brain_service.py` | `BrainService` | Serviço central de dados |
| `brain_aggregator.py` | `BrainAggregator` | Agregação de múltiplas fontes |
| `data_providers/` | `ForexNewsProvider`, `CFTCProvider` | Providers de dados externos |

**Singleton Pattern:** `BrainService.get_instance()`

---

### MT5 (`src/mt5/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `connection.py` | `MT5Connection` | Conexão com MetaTrader 5 |
| `data_service.py` | `MT5DataService` | Coleta de dados de mercado |
| `order_manager.py` | `MT5OrderManager` | Execução de ordens |
| `symbol_info.py` | `SymbolInfo` | Informações de símbolos |

---

### Analysis (`src/analysis/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `master_analyzer.py` | `MasterTechnicalAnalyzer` | Análise técnica completa |
| `market_structure.py` | `MarketStructureAnalyzer` | BOS, CHoCH, Swings |
| `smart_money.py` | `SmartMoneyAnalyzer` | Order Blocks, FVG, Liquidity |
| `volume_analyzer.py` | `VolumeAnalyzer` | Profile, VSA, Delta |
| `mtf_analyzer.py` | `MultiTimeframeAnalyzer` | Análise multi-timeframe |
| `divergence_detector.py` | `DivergenceDetector` | Divergências |
| `fibonacci.py` | `FibonacciAnalyzer` | Níveis de Fibonacci |
| `harmonics.py` | `HarmonicPatternDetector` | Padrões harmônicos |
| `indicators.py` | `AdvancedIndicators` | Indicadores avançados |
| `correlation.py` | `CorrelationAnalyzer` | Correlação entre pares |

---

### Strategies (`src/strategies/`)

| Arquivo | Classes Principais | Setups |
|---------|-------------------|--------|
| `scalping.py` | `ScalpingStrategy` | 9 setups para scalping |
| `trend.py` | `TrendStrategy` | 7 setups para tendência |
| `reversal.py` | `ReversalStrategy` | 8 setups para reversão |
| `event.py` | `EventStrategy` | 5 setups para eventos |
| `factory.py` | `StrategyFactory` | Criação de estratégias |
| `validator.py` | `SetupValidator` | Validação de setups |

---

### ML (`src/ml/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `models/prediction_engine.py` | `PredictionService` | Serviço de predição ensemble |
| `models/lstm/` | `VirtusLSTMModel` | Modelo LSTM |
| `models/knn/` | `KNNPatternRecognizer` | Reconhecimento de padrões |
| `models/vision/` | `VirtusVisionAnalyzer` | Análise visual de gráficos |
| `features/` | `FeatureEngineer` | Engenharia de features |

---

### Risk (`src/risk/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `risk_manager.py` | `RiskManager` | Gestão central de risco |
| `advanced_risk.py` | `AdvancedRiskManager` | Kelly, VaR, Monte Carlo |
| `position_sizer.py` | `PositionSizer` | Cálculo de tamanho de posição |
| `exposure.py` | `ExposureManager` | Controle de exposição |
| `correlation_risk.py` | `CorrelationRiskManager` | Risco correlacionado |

---

### Bot (`src/bot/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `trading_bot.py` | `TradingBot` | Bot principal |
| `core/trading_engine.py` | `TradingEngine` | Motor de trading |
| `core/decision_maker.py` | `DecisionMaker` | Tomada de decisão |
| `core/exit_manager.py` | `ExitManager` | Gestão de saídas |

---

### Orchestrator (`src/orchestrator/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `bot_orchestrator.py` | `BotOrchestrator` | Orquestração multi-bot |
| `session_manager.py` | `SessionManager` | Gestão de sessões |

---

### Positions (`src/positions/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `position_manager.py` | `PositionManager` | Gestão de posições |
| `position_supervisor.py` | `PositionSupervisor` | Supervisão de posições |
| `trailing_stop.py` | `TrailingStopManager` | Gestão de trailing stop |

---

### Database (`src/database/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `models.py` | SQLAlchemy Models | Modelos de dados |
| `repositories.py` | `TradeRepository`, etc | Acesso a dados |
| `database.py` | `Database` | Conexão SQLite |

---

### Integrations (`src/integrations/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `tess/tess_client.py` | `TessClient` | Cliente TESS API |
| `tess/tess_agents.py` | `TessAgents` | Agentes de IA |
| `tess/market_analyzer.py` | `TessMarketAnalyzer` | Análise de mercado via IA |
| `tess/caption_service.py` | `TessCaptionService` | Geração de captions |

---

### Telegram (`src/telegram/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `telegram_service.py` | `TelegramService` | Serviço de notificações |
| `command_handler.py` | `CommandHandler` | Comandos do bot |

---

### Advisor (`src/advisor/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `market_advisor.py` | `MarketAdvisor` | Conselhos de mercado |

---

### Social (`src/social/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `auto_post_generator.py` | `AutoPostGenerator` | Geração automática de posts |
| `linkedin.py` | `LinkedInService` | Integração LinkedIn |
| `instagram.py` | `InstagramService` | Integração Instagram |

---

### Monitoring (`src/monitoring/`)

| Arquivo | Classe Principal | Responsabilidade |
|---------|-----------------|------------------|
| `system_monitor.py` | `SystemMonitor` | Monitoramento do sistema |
| `prometheus_metrics.py` | `PrometheusExporter` | Métricas Prometheus |

---

## 🔗 Diagrama de Dependências

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────┐       ┌───────────┐       ┌───────────┐
│Orchestrator│       │  Advisor  │       │  Brain    │
└─────┬─────┘       └───────────┘       └─────┬─────┘
      │                                       │
      ▼                                       ▼
┌───────────┐                           ┌───────────┐
│TradingBot │                           │   Data    │
└─────┬─────┘                           │ Providers │
      │                                 └───────────┘
      ▼
┌───────────┐
│  Trading  │
│  Engine   │
└─────┬─────┘
      │
      ├─────────────────────┬─────────────────────┐
      │                     │                     │
      ▼                     ▼                     ▼
┌───────────┐       ┌───────────┐       ┌───────────┐
│  Master   │       │Strategies │       │    ML     │
│ Analyzer  │       │           │       │ Prediction│
└───────────┘       └───────────┘       └─────┬─────┘
                                              │
                                    ┌─────────┼─────────┐
                                    │         │         │
                                    ▼         ▼         ▼
                              ┌──────┐  ┌──────┐  ┌──────┐
                              │ LSTM │  │ KNN  │  │Vision│
                              └──────┘  └──────┘  └──────┘
```

---

## 🔄 Padrões de Design Utilizados

| Padrão | Onde | Propósito |
|--------|------|-----------|
| **Singleton** | MT5Connection, BrainService | Instância única global |
| **Factory** | StrategyFactory | Criação de estratégias |
| **Observer** | Event handlers | Notificações de eventos |
| **Strategy** | Strategies | Algoritmos intercambiáveis |
| **Repository** | Database repos | Acesso a dados |
| **Facade** | TradingEngine | Interface simplificada |
| **Adapter** | MT5 Adapters | Compatibilidade MT5 |

---

*Documentação de módulos - VIRTUS v3.0*
