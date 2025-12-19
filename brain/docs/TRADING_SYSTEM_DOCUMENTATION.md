# VIRTUS Trading System - Documentação Completa

## 📋 Índice

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Componentes Principais](#2-componentes-principais)
3. [MasterAnalyzer - Motor de Análise](#3-masteranalyzer---motor-de-análise)
4. [TradingEngine - Motor de Decisões](#4-tradingengine---motor-de-decisões)
5. [Estratégias de Trading](#5-estratégias-de-trading)
6. [Risk Manager](#6-risk-manager)
7. [MT5 Integration](#7-mt5-integration)
8. [Fluxo de Execução](#8-fluxo-de-execução)
9. [Estruturas de Dados](#9-estruturas-de-dados)
10. [API Endpoints](#10-api-endpoints-para-bots-externos)
11. [Bugs Conhecidos e Soluções](#11-bugs-conhecidos-e-soluções)

---

## 1. Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                      VIRTUS TRADING SYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐   │
│  │  TradingBot  │───▶│  TradingEngine  │───▶│  MT5 Orders  │   │
│  │  (por símbolo)│    │  (decisões)     │    │  (execução)  │   │
│  └──────────────┘    └────────┬────────┘    └──────────────┘   │
│                               │                                  │
│         ┌─────────────────────┼─────────────────────┐           │
│         │                     │                     │           │
│         ▼                     ▼                     ▼           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │MasterAnalyzer│    │  Strategies  │    │ RiskManager  │      │
│  │(20 módulos)  │    │ (4 tipos)    │    │(Kelly,VaR)   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo Principal
1. **TradingBot** executa loop a cada 5 segundos
2. **TradingEngine** coordena análise e decisão
3. **MasterAnalyzer** analisa mercado (20 módulos)
4. **Strategies** geram sinais de trade
5. **RiskManager** valida tamanho e risco
6. **MT5 Orders** executa as ordens

---

## 2. Componentes Principais

### Arquivos Chave

| Arquivo | Localização | Função |
|---------|-------------|--------|
| `trading_bot.py` | `src/bot/core/` | Bot principal por símbolo |
| `trading_engine.py` | `src/bot/core/` | Motor de decisões |
| `master_analyzer.py` | `src/analysis/` | Análise técnica completa |
| `risk_manager.py` | `src/risk/` | Gestão de risco |
| `mt5_connection.py` | `src/mt5/` | Conexão MT5 |
| `mt5_orders.py` | `src/mt5/` | Execução de ordens |
| `scalping_strategy.py` | `src/strategies/scalping/` | Estratégia scalping |
| `trend_strategy.py` | `src/strategies/trend/` | Estratégia tendência |
| `reversal_strategy.py` | `src/strategies/reversal/` | Estratégia reversão |

---

## 3. MasterAnalyzer - Motor de Análise

### Localização
`brain/src/analysis/master_analyzer.py`

### Módulos Integrados (20 analisadores)

```python
class MasterTechnicalAnalyzer:
    """
    Integra todos os módulos:
    - Market Structure (BOS, CHoCH, Swing Points)
    - Smart Money Concepts (Order Blocks, FVG, Liquidity)
    - Volume Analysis (Profile, VSA, Delta)
    - Multi-Timeframe Analysis
    - Divergence Detection
    - Fibonacci Analysis
    - Harmonic Patterns
    - Advanced Indicators (Ichimoku, VWAP, Pivots, Supertrend)
    - Correlation Analysis
    - Vision Analyzer (ML opcional)
    """
```

### Método Principal: `analyze()`

```python
def analyze(
    self,
    symbol: str,
    df: pd.DataFrame,           # OHLCV principal (mínimo 100 candles)
    timeframe: str = 'M15',
    mtf_data: Dict[str, pd.DataFrame] = None,  # Outros timeframes
    correlated_data: Dict[str, pd.DataFrame] = None,  # Pares correlacionados
    dxy_data: pd.DataFrame = None,  # DXY (USD Index)
) -> MasterAnalysisResult:
```

### Estrutura do Resultado

```python
@dataclass
class MasterAnalysisResult:
    symbol: str
    timeframe: str
    timestamp: datetime
    current_price: float
    
    # Viés geral
    bias: MarketBias          # STRONG_BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG_BEARISH
    bias_score: float         # -1 a +1
    trend: str                # 'bullish', 'bearish', 'sideways'
    trend_strength: float     # 0 a 1
    
    # Níveis
    key_supports: List[KeyLevel]
    key_resistances: List[KeyLevel]
    
    # Setup (se houver)
    current_setup: Optional[TradeSetup]
    
    # Componentes detalhados (dicts)
    market_structure: Dict[str, Any]
    smart_money: Dict[str, Any]
    volume: Dict[str, Any]
    mtf: Dict[str, Any]
    divergences: Dict[str, Any]
    fibonacci: Dict[str, Any]
    harmonics: Dict[str, Any]
    indicators: Dict[str, Any]
    correlations: Dict[str, Any]
    
    summary: str
    alerts: List[str]
```

### Método `to_dict()` para serialização

```python
def to_dict(self) -> Dict[str, Any]:
    """Converte resultado para dicionário."""
    return {
        'symbol': self.symbol,
        'timeframe': self.timeframe,
        'timestamp': self.timestamp.isoformat(),
        'price': self.current_price,
        'bias': self.bias.name,
        'bias_score': self.bias_score,
        'trend': self.trend,  # ⚠️ ATENÇÃO: é STRING, não dict!
        'trend_strength': self.trend_strength,
        'supports': [lvl.__dict__ for lvl in self.key_supports],
        'resistances': [lvl.__dict__ for lvl in self.key_resistances],
        'setup': self.current_setup.to_dict() if self.current_setup else None,
        'structure': self.market_structure,
        'smc': self.smart_money,
        'volume': self.volume,
        'mtf': self.mtf,
        'divergences': self.divergences,
        'fibonacci': self.fibonacci,
        'harmonics': self.harmonics,
        'indicators': self.indicators,
        'correlations': self.correlations,
        'summary': self.summary,
        'alerts': self.alerts,
    }
```

---

## 4. TradingEngine - Motor de Decisões

### Localização
`brain/src/bot/core/trading_engine.py`

### Modos de Operação

```python
class TradingMode(Enum):
    SCALPING = "scalping"          # Scalping agressivo
    TREND_FOLLOWING = "trend"      # Seguir tendência
    REVERSAL = "reversal"          # Reversões
    EVENT_DRIVEN = "event"         # Baseado em eventos
    ADAPTIVE = "adaptive"          # Auto-seleção (padrão)
    CONSERVATIVE = "conservative"  # Conservador
```

### Inicialização

```python
engine = TradingEngine(
    symbol="EURUSD",
    mode=TradingMode.ADAPTIVE,
    execution_mode=ExecutionMode.NORMAL,
    risk_per_trade=0.01,  # 1%
    enabled_strategies=['scalping', 'trend', 'reversal'],
    bot_config={...}  # Config do YAML
)
await engine.initialize(account_balance=10000.0)
```

### Método Principal: `analyze_and_decide()`

```python
async def analyze_and_decide(
    self,
    market_data: Dict[str, Any],
    current_price: float,
) -> TradeDecision:
    """
    Fluxo:
    1. Análise completa (MasterAnalyzer)
    2. Seleção de estratégia (se ADAPTIVE)
    3. Geração de sinais
    4. Validação ML (se ativo)
    5. Validação de risco
    6. Cálculo de posição
    7. Validação de confluência
    8. Decisão final
    """
```

### Estrutura da Decisão

```python
@dataclass
class TradeDecision:
    should_trade: bool
    direction: str              # "buy", "sell", "none"
    confidence: float           # 0 a 1
    
    strategy_used: str          # Nome da estratégia
    setup_name: str             # Nome do setup
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float        # Volume em lotes
    
    risk_reward: float
    kelly_fraction: float
    var_impact: float
    
    ml_prediction: Optional[EnsemblePrediction]
    analysis_score: float
    confirmations: List[str]
    rejections: List[str]
    
    timestamp: datetime
    execution_mode: ExecutionMode
```

### Thresholds Configuráveis

```python
# No __init__ do TradingEngine
self._min_confluence = 0.45    # Mínimo de confluência para operar
self._min_ml_confidence = 0.50 # Mínimo de confiança ML
self._min_risk_reward = 1.2    # Mínimo risk:reward
```

---

## 5. Estratégias de Trading

### 5.1 Scalping Strategy

**Localização:** `src/strategies/scalping/scalping_strategy.py`

**Setups:**
- `SPREAD_COMPRESSION` - Entry quando spread contrai
- `LIQUIDITY_GRAB` - Após sweep de liquidez
- `MOMENTUM_BURST` - Movimento rápido com volume
- `ABSORPTION` - Grande volume absorvido
- `DELTA_DIVERGENCE` - Divergência delta vs preço
- `VWAP_BOUNCE` - Reversão no VWAP
- `MICROSTRUCTURE_REVERSAL` - Padrões micro
- `ORDER_BLOCK_TAP` - Toque em OB
- `FVG_FILL` - Preenchimento de FVG

**Configuração:**
```python
@dataclass
class ScalpingConfig:
    primary_tf: str = "M1"
    confirmation_tf: str = "M5"
    max_spread_pips: float = 1.5
    min_liquidity_score: float = 0.6
    max_risk_pips: float = 10.0
    min_risk_reward: float = 1.5
    target_pips: float = 8.0
    max_hold_seconds: int = 300  # 5 minutos
```

**Interface:**
```python
async def find_setups(
    self,
    market_data: Dict[str, Any],
    analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Retorna lista de setups:
    [{
        'name': 'scalping_spread_compression',
        'direction': 'buy' | 'sell',
        'entry': float,
        'sl': float,
        'tp': float,
        'score': float,  # 0 a 1
        'risk_reward': float,
    }]
    """
```

### 5.2 Trend Strategy

**Localização:** `src/strategies/trend/trend_strategy.py`

**Setups:**
- `BOS_CONTINUATION` - Após Break of Structure
- `ORDER_BLOCK_PULLBACK` - Pullback para OB
- `FVG_RETEST` - Reteste de FVG
- `FIBONACCI_PULLBACK` - Zona 61.8-78.6%
- `MTF_ALIGNMENT` - TFs alinhados
- `STRUCTURE_SHIFT` - Mudança de estrutura
- `LIQUIDITY_SWEEP_CONTINUATION` - Sweep e continuação

**Configuração:**
```python
@dataclass
class TrendConfig:
    entry_tf: str = "M15"
    structure_tf: str = "H1"
    bias_tf: str = "H4"
    min_confluences: int = 3
    min_risk_reward: float = 2.0
    tp1_r: float = 1.5  # Take profit 1 em R
    tp2_r: float = 2.5
    tp3_r: float = 4.0
```

### 5.3 Reversal Strategy

**Localização:** `src/strategies/reversal/reversal_strategy.py`

**Setups:**
- Divergências RSI/MACD
- Exaustão em níveis extremos
- Padrões de candle de reversão
- Smart Money Reversals

### 5.4 Event Strategy

**Localização:** `src/strategies/event/event_strategy.py`

**Setups:**
- Trading em notícias
- Eventos econômicos
- Aberturas de sessão

---

## 6. Risk Manager

### Localização
`brain/src/risk/risk_manager.py`

### Métricas de Risco

```python
@dataclass
class RiskMetrics:
    current_drawdown: float     # Drawdown atual %
    max_drawdown: float         # Máximo drawdown %
    daily_loss: float           # Perda do dia
    weekly_loss: float          # Perda da semana
    open_positions: int         # Posições abertas
    total_exposure: float       # Exposição total
    exposure_by_symbol: Dict[str, float]
    correlation_exposure: float
    var_95: float               # Value at Risk 95%
    risk_level: RiskLevel       # LOW, MEDIUM, HIGH, CRITICAL
```

### Position Sizing

```python
@dataclass
class PositionSizing:
    volume: float           # Volume calculado
    risk_amount: float      # Valor em $ arriscado
    risk_percent: float     # % da conta
    stop_loss_pips: float   # Distância do SL
    max_loss: float         # Perda máxima possível
    allowed: bool           # Se permitido
    reason: str             # Motivo se negado
```

### Métodos Principais

```python
class RiskManager:
    async def update_account(self, balance: float, equity: float) -> None:
        """Atualiza informações da conta."""
    
    async def calculate_position_size(
        self,
        symbol: str,
        stop_loss_pips: float,
        risk_percent: Optional[float] = None
    ) -> PositionSizing:
        """Calcula tamanho da posição."""
    
    async def can_open_position(
        self,
        symbol: str,
        direction: str,
        volume: float
    ) -> Tuple[bool, str]:
        """Verifica se pode abrir posição."""
    
    async def check_circuit_breaker(self) -> bool:
        """Verifica se circuit breaker está ativo."""
```

### Limites Configuráveis (via YAML)

```yaml
risk:
  risk_per_trade: 0.01        # 1% por trade
  max_daily_loss_pct: 5.0     # 5% max perda diária
  max_weekly_loss_pct: 10.0   # 10% max perda semanal
  max_total_exposure: 0.10    # 10% exposição total
  max_symbol_exposure: 0.05   # 5% por símbolo
  max_correlated_exposure: 0.08
  max_positions: 3
```

---

## 7. MT5 Integration

### 7.1 MT5Connection

**Localização:** `src/mt5/mt5_connection.py`

```python
class MT5Connection:
    """Singleton de conexão."""
    
    @classmethod
    async def get_instance(cls) -> 'MT5Connection':
        """Retorna instância singleton."""
    
    async def connect(
        self,
        login: int = None,
        password: str = None,
        server: str = None,
        path: str = None
    ) -> bool:
        """Conecta ao MT5."""
    
    @property
    def is_connected(self) -> bool:
        """Verifica conexão."""
    
    @property
    def account_info(self) -> Dict[str, Any]:
        """Retorna info da conta."""
```

### 7.2 MT5OrderManager

**Localização:** `src/mt5/mt5_orders.py`

```python
class MT5OrderManager:
    async def send_market_order(
        self,
        symbol: str,
        order_type: OrderType,  # BUY, SELL
        volume: float,
        stop_loss: float = None,
        take_profit: float = None,
        magic: int = 0,
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        Retorna:
        {
            'success': True,
            'ticket': int,
            'deal': int,
            'volume': float,
            'price': float,
            'symbol': str,
            'order_type': str,
        }
        """
    
    async def send_pending_order(
        self,
        symbol: str,
        order_type: OrderType,  # BUY_LIMIT, SELL_LIMIT, etc
        volume: float,
        price: float,
        stop_loss: float = None,
        take_profit: float = None,
        expiration: datetime = None
    ) -> Dict[str, Any]:
        """Envia ordem pendente."""
    
    async def modify_position(
        self,
        ticket: int,
        stop_loss: float = None,
        take_profit: float = None
    ) -> bool:
        """Modifica SL/TP."""
    
    async def close_position(
        self,
        ticket: int,
        volume: float = None  # Parcial se especificado
    ) -> bool:
        """Fecha posição."""
    
    async def get_positions(
        self,
        symbol: str = None
    ) -> List[Dict]:
        """Lista posições abertas."""
```

### 7.3 MT5DataService

**Localização:** `src/mt5/mt5_data.py`

```python
class MT5DataService:
    async def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        count: int = 100
    ) -> pd.DataFrame:
        """Retorna DataFrame OHLCV."""
    
    async def get_price(self, symbol: str) -> Dict:
        """Retorna {'bid': x, 'ask': y, 'time': t}."""
    
    async def get_tick(self, symbol: str) -> Dict:
        """Retorna último tick."""
```

---

## 8. Fluxo de Execução

### Loop Principal do Bot

```python
# Em TradingBot.run()
while self._running:
    try:
        # 1. Verifica condições básicas
        if not await self._check_basic_conditions():
            continue
        
        # 2. Obtém dados de mercado
        market_data = await self._get_market_data()
        
        # 3. Análise e decisão (via TradingEngine)
        decision = await self.engine.analyze_and_decide(
            market_data, 
            current_price
        )
        
        # 4. Executa se aprovado
        if decision.should_trade:
            await self._execute_trade(decision)
        
        # 5. Monitora posições abertas
        await self._monitor_positions()
        
    except Exception as e:
        self.logger.error(f"Erro no loop: {e}")
    
    await asyncio.sleep(self._analysis_interval)  # 5 segundos
```

### Diagrama de Sequência

```
TradingBot          TradingEngine         MasterAnalyzer        Strategies
    │                    │                      │                    │
    │─get_market_data()──│                      │                    │
    │                    │                      │                    │
    │─analyze_and_decide()─▶│                   │                    │
    │                    │──analyze_full()──────▶│                   │
    │                    │◀──analysis_dict───────│                   │
    │                    │                      │                    │
    │                    │──select_strategy()───┼────────────────────│
    │                    │                      │                    │
    │                    │──find_setups()───────┼───────────────────▶│
    │                    │◀──setups_list────────┼────────────────────│
    │                    │                      │                    │
    │                    │──validate_risk()─────│                    │
    │                    │                      │                    │
    │◀──TradeDecision────│                      │                    │
    │                    │                      │                    │
    │─execute_trade()────▶│                     │                    │
```

---

## 9. Estruturas de Dados

### Market Data (entrada)

```python
market_data = {
    'symbol': 'EURUSD',
    'candles': {
        'M1': pd.DataFrame,   # OHLCV
        'M5': pd.DataFrame,
        'M15': pd.DataFrame,
        'H1': pd.DataFrame,
    },
    'tick': {
        'bid': 1.04500,
        'ask': 1.04502,
        'time': datetime,
        'volume': int,
    },
    'spread': 0.00002,
}
```

### Analysis Dict (saída do MasterAnalyzer)

```python
analysis = {
    'symbol': 'EURUSD',
    'price': 1.04500,
    'score': 0.75,           # Score geral 0-1
    
    'trend': 'bullish',      # ⚠️ STRING, não dict!
    'trend_strength': 0.7,   # 0-1
    
    'bias': 'BULLISH',       # Enum name
    'bias_score': 0.6,       # -1 a +1
    
    'regime': {
        'type': 'trending',   # 'trending', 'ranging', 'volatile'
        'strength': 0.8,
    },
    
    'volatility': {
        'level': 'medium',    # 'low', 'medium', 'high'
        'atr': 0.0015,
    },
    
    'indicators': {
        'rsi': 55,
        'macd': {...},
        'bollinger': {...},
        'atr': 0.0015,
    },
    
    'zones': {
        'at_support': False,
        'at_resistance': True,
        'support_levels': [...],
        'resistance_levels': [...],
    },
    
    'divergence': {
        'detected': False,
        'type': None,
    },
    
    'structure': {...},  # Market structure
    'smc': {...},        # Smart Money Concepts
    'volume': {...},     # Volume analysis
    # ... outros módulos
}
```

### Setup Signal (saída das estratégias)

```python
setup = {
    'name': 'scalping_vwap_bounce',
    'direction': 'buy',       # 'buy' ou 'sell'
    'entry': 1.04500,
    'sl': 1.04450,           # Stop Loss
    'tp': 1.04600,           # Take Profit
    'score': 0.75,           # Confiança 0-1
    'risk_reward': 2.0,
    'metadata': {
        'setup_type': 'vwap_bounce',
        'confluences': ['rsi_oversold', 'at_support'],
    }
}
```

---

## 10. API Endpoints para Bots Externos

### Schema para Receber Dados de Bots Externos

Para integrar bots externos com o dashboard, use este schema:

```python
# POST /api/bots/update
{
    "bot_id": "unique_bot_identifier",
    "account": {
        "login": 61444598,
        "server": "Pepperstone-Demo",
        "balance": 5000.00,
        "equity": 5150.00,
        "margin": 100.00,
        "free_margin": 5050.00,
        "profit": 150.00,
        "leverage": 100
    },
    "positions": [
        {
            "ticket": 12345678,
            "symbol": "EURUSD",
            "type": "buy",
            "volume": 0.1,
            "open_price": 1.04500,
            "current_price": 1.04650,
            "sl": 1.04400,
            "tp": 1.04800,
            "profit": 15.00,
            "swap": -0.50,
            "open_time": "2025-12-17T10:30:00Z"
        }
    ],
    "orders": [
        {
            "ticket": 12345679,
            "symbol": "XAUUSD",
            "type": "buy_limit",
            "volume": 0.05,
            "price": 2600.00,
            "sl": 2590.00,
            "tp": 2630.00,
            "status": "pending"
        }
    ],
    "statistics": {
        "total_trades": 150,
        "winning_trades": 90,
        "losing_trades": 60,
        "win_rate": 0.60,
        "profit_factor": 1.8,
        "daily_profit": 75.00,
        "weekly_profit": 320.00,
        "monthly_profit": 1200.00,
        "max_drawdown": 5.2
    },
    "status": {
        "state": "running",       # running, paused, error, stopped
        "last_analysis": "2025-12-17T14:30:00Z",
        "current_strategy": "trend_following",
        "alerts": ["Spread alto em EURUSD"]
    },
    "timestamp": "2025-12-17T14:30:05Z"
}
```

---

## 11. Bugs Conhecidos e Soluções

### Bug 1: `'str' object has no attribute 'get'`

**Causa:** `analysis.get('trend', {}).get('strength')` falha porque `trend` é STRING, não dict.

**Solução:**
```python
# Em trading_engine.py - método _select_strategy()
trend_data = analysis.get('trend', {})
if isinstance(trend_data, dict):
    trend_strength = trend_data.get('strength', 50)
else:
    # trend é string ('bullish', 'bearish', 'sideways')
    trend_strength = analysis.get('trend_strength', 50)
```

### Bug 2: Config Singleton retorna 0 bots

**Causa:** `from_yaml()` não chama `reload()` após criar instância.

**Solução:**
```python
# Em config.py - método from_yaml()
@classmethod
def from_yaml(cls, config_path: str) -> 'Config':
    if cls._instance is None:
        cls._instance = cls(config_path)
    elif cls._instance.config_path != config_path:
        cls._instance = cls(config_path)
    
    cls._instance.reload()  # ← IMPORTANTE: força recarga
    return cls._instance
```

### Bug 3: Spread check muito restritivo

**Sintoma:** EURUSD frequentemente rejeitado por spread.

**Solução:** Aumentar `max_spread` no YAML do bot:
```yaml
filters:
  max_spread: 0.00035  # Era 0.00030
```

---

## Próximos Passos para Reconstrução

1. **Criar bot externo simples** que:
   - Conecta ao MT5 diretamente
   - Executa estratégia específica
   - Envia dados para dashboard via API

2. **Simplificar lógica de decisão**:
   - Remover dependências complexas
   - Usar indicadores diretos (RSI, BB, ATR)
   - Validação de risco simples

3. **Dashboard recebe dados**:
   - Endpoint `/api/bots/update`
   - Armazena em banco/arquivo
   - Exibe em tempo real via WebSocket

---

*Documentação gerada em: 17 de dezembro de 2025*
*Versão do VIRTUS: 3.0*
