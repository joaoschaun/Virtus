# 📊 VIRTUS - Módulo de Análise Técnica Avançada

## Arquitetura do Sistema de Análise

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MASTER TECHNICAL ANALYZER                        │
│                  (Integrador Central de Análise)                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    ANÁLISE UNIFICADA                        │   │
│  │  • Viés de Mercado (STRONG_BULLISH → STRONG_BEARISH)       │   │
│  │  • Níveis Chave Consolidados (Suportes/Resistências)       │   │
│  │  • Setup de Trade (Entrada, Stop, Targets, R:R)            │   │
│  │  • Qualidade do Sinal (A+ → D)                              │   │
│  │  • Número de Confluências                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
       ▼                        ▼                        ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   MARKET     │    │   SMART MONEY    │    │     VOLUME       │
│  STRUCTURE   │    │    CONCEPTS      │    │    ANALYSIS      │
├──────────────┤    ├──────────────────┤    ├──────────────────┤
│ • Swing HH   │    │ • Order Blocks   │    │ • Volume Profile │
│ • Swing HL   │    │   (Bull/Bear)    │    │ • POC            │
│ • Swing LH   │    │ • Fair Value     │    │ • Value Area     │
│ • Swing LL   │    │   Gaps (FVG)     │    │ • Delta Volume   │
│ • BOS        │    │ • Liquidity      │    │ • VSA Signals    │
│ • CHoCH      │    │   Pools          │    │ • Accumulation/  │
│ • Premium/   │    │ • Mitigation     │    │   Distribution   │
│   Discount   │    │ • Sweep          │    │                  │
│   Zones      │    │   Detection      │    │                  │
└──────────────┘    └──────────────────┘    └──────────────────┘

       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
       ▼                        ▼                        ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ DIVERGENCE   │    │   FIBONACCI      │    │    HARMONIC      │
│  DETECTOR    │    │    ANALYSIS      │    │    PATTERNS      │
├──────────────┤    ├──────────────────┤    ├──────────────────┤
│ • Regular    │    │ • Retracements   │    │ • Gartley        │
│   Bullish    │    │ • Extensions     │    │ • Bat            │
│ • Regular    │    │ • Expansions     │    │ • Butterfly      │
│   Bearish    │    │ • Golden Zone    │    │ • Crab           │
│ • Hidden     │    │   (0.618-0.786)  │    │ • Shark          │
│   Bullish    │    │ • Clusters       │    │ • Cypher         │
│ • Hidden     │    │ • Auto-detect    │    │ • ABCD           │
│   Bearish    │    │   Swings         │    │ • Three Drives   │
│ • Multi-     │    │                  │    │                  │
│   Indicator  │    │                  │    │                  │
│   (RSI,MACD, │    │                  │    │                  │
│   Stoch,OBV, │    │                  │    │                  │
│   CCI)       │    │                  │    │                  │
└──────────────┘    └──────────────────┘    └──────────────────┘

       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
       ▼                        ▼                        ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  ADVANCED    │    │ MULTI-TIMEFRAME  │    │  CORRELATION     │
│ INDICATORS   │    │    ANALYSIS      │    │   ANALYSIS       │
├──────────────┤    ├──────────────────┤    ├──────────────────┤
│ • Ichimoku   │    │ • M5, M15, M30   │    │ • Par vs Par     │
│   Cloud      │    │ • H1, H4, D1     │    │ • Par vs DXY     │
│ • VWAP       │    │ • Confluência    │    │ • Rolling Corr   │
│   + Bandas   │    │ • Aligned TFs    │    │ • Regime         │
│ • Pivots     │    │ • Signal         │    │   Detection      │
│   (Standard, │    │   Strength       │    │ • Risk-On/Off    │
│   Fibonacci, │    │ • Entry          │    │ • Anomaly        │
│   Camarilla, │    │   Permission     │    │   Detection      │
│   Woodie)    │    │                  │    │                  │
│ • Supertrend │    │                  │    │                  │
│ • ATR        │    │                  │    │                  │
└──────────────┘    └──────────────────┘    └──────────────────┘
```

## Fluxo de Análise

```
1. COLETA DE DADOS
   MT5 → Candles OHLCV de múltiplos timeframes
   
2. ANÁLISE INDIVIDUAL
   Cada módulo analisa independentemente
   
3. INTEGRAÇÃO
   MasterAnalyzer consolida todos os resultados
   
4. SCORING
   Calcula bias_score (-1 a +1) baseado em todos os módulos
   
5. IDENTIFICAÇÃO DE NÍVEIS
   Consolida suportes/resistências de todas as fontes
   
6. DETECÇÃO DE SETUP
   Identifica confluências e gera setup se >= 3
   
7. QUALIFICAÇÃO
   Classifica qualidade (A+, A, B, C, D)
   
8. OUTPUT
   Resumo textual + dados estruturados para bot
```

## Qualidade do Setup (SignalQuality)

| Qualidade | Confluências | R:R Mínimo | Confiança |
|-----------|--------------|------------|-----------|
| A+        | >= 7         | >= 2.5     | 90%       |
| A         | >= 5         | >= 2.0     | 80%       |
| B         | >= 4         | >= 1.5     | 70%       |
| C         | >= 3         | >= 1.0     | 60%       |
| D         | < 3          | Qualquer   | 50%       |

## Fontes de Confluência

1. **Market Structure** - Tendência alinhada
2. **Smart Money** - Preço em Order Block / FVG
3. **Volume** - Confirmação de tendência
4. **Volume** - Acumulação/Distribuição
5. **Divergences** - Divergência favorável
6. **Fibonacci** - Preço em Golden Zone
7. **Harmonic Patterns** - Padrão identificado
8. **Ichimoku** - Momentum + Cloud + TK Cross
9. **Supertrend** - Direção + Mudança de tendência

## Níveis Chave (KeyLevel)

Cada nível identificado contém:
- `price` - Preço do nível
- `type` - support/resistance/pivot
- `strength` - Força 0-1
- `source` - Módulo que identificou
- `description` - Descrição textual

Fontes de níveis:
- Swing Points (HH, HL, LH, LL)
- Order Blocks
- Fair Value Gaps
- Fibonacci Levels
- Pivot Points
- Ichimoku Cloud
- VWAP

## Uso no Bot de Trading

```python
from src.analysis import MasterTechnicalAnalyzer

# Inicializa
analyzer = MasterTechnicalAnalyzer(logger)

# Analisa
result = analyzer.analyze(
    symbol='EURUSD',
    df=df_m15,
    timeframe='M15',
    mtf_data={'M5': df_m5, 'H1': df_h1, 'H4': df_h4},
    correlated_data={'GBPUSD': df_gbp},
    dxy_data=df_dxy,
)

# Usa resultado
if result.current_setup:
    if result.current_setup.quality in [SignalQuality.A_PLUS, SignalQuality.A]:
        # Trade de alta qualidade - pode entrar
        direction = result.current_setup.direction
        entry = result.current_setup.entry_zone
        stop = result.current_setup.stop_loss
        targets = [
            result.current_setup.target_1,
            result.current_setup.target_2,
            result.current_setup.target_3,
        ]
```

## Arquivos do Módulo

```
brain/src/analysis/
├── __init__.py                      # Exports centralizados
├── master_analyzer.py               # INTEGRADOR CENTRAL
│
├── technical/
│   ├── __init__.py
│   ├── technical_analyzer.py        # Indicadores básicos
│   ├── market_structure.py          # BOS, CHoCH, Swings
│   ├── divergence_detector.py       # Divergências multi-indicador
│   ├── fibonacci_analyzer.py        # Fib completo
│   ├── harmonic_patterns.py         # Gartley, Bat, etc.
│   └── advanced_indicators.py       # Ichimoku, VWAP, Pivots, Supertrend
│
├── institutional/
│   ├── __init__.py
│   └── smart_money.py               # Order Blocks, FVG, Liquidity
│
├── volume/
│   ├── __init__.py
│   └── volume_analyzer.py           # Profile, VSA, Delta
│
├── market/
│   ├── __init__.py
│   └── mtf_analyzer.py              # Multi-Timeframe
│
├── correlation/
│   ├── __init__.py
│   └── correlation_analyzer.py      # Correlações
│
└── signals/
    ├── __init__.py
    └── signal_generator.py          # Gerador de sinais
```

---

**Versão:** 1.0
**Última Atualização:** Módulo avançado de análise técnica implementado
