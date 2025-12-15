"""
VIRTUS Order Flow Analyzer
===========================

Análise de fluxo de ordens para detecção de atividade institucional.

Funcionalidades:
- Order Flow Analysis
- DOM (Depth of Market) Simulation
- Footprint Chart Emulation
- Absorption Detection
- Imbalance Detection
- Aggressive Order Detection
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
import logging


class OrderFlowType(Enum):
    """Tipo de fluxo detectado."""
    ABSORPTION = auto()        # Absorção de ordens
    IMBALANCE = auto()         # Desbalanceamento
    AGGRESSIVE_BUY = auto()    # Compra agressiva
    AGGRESSIVE_SELL = auto()   # Venda agressiva
    EXHAUSTION = auto()        # Exaustão de movimento
    NEUTRAL = auto()           # Neutro


class OrderFlowStrength(Enum):
    """Força do sinal de fluxo."""
    VERY_STRONG = auto()
    STRONG = auto()
    MODERATE = auto()
    WEAK = auto()


@dataclass
class FootprintBar:
    """Barra de footprint simulada."""
    timestamp: datetime
    open_price: float
    high: float
    low: float
    close: float
    
    # Volume por lado
    buy_volume: float
    sell_volume: float
    total_volume: float
    
    # Delta
    delta: float  # buy - sell
    cumulative_delta: float
    
    # Imbalances
    bid_imbalance: float  # volume no bid vs ask
    ask_imbalance: float
    
    # POC do bar
    poc_price: float


@dataclass
class OrderFlowSignal:
    """Sinal de order flow."""
    type: OrderFlowType
    strength: OrderFlowStrength
    price: float
    timestamp: datetime
    
    description: str
    confidence: float
    
    # Detalhes
    delta: float
    delta_pct: float
    imbalance_ratio: float
    
    direction: str  # 'bullish', 'bearish'
    recommendation: str


@dataclass 
class OrderFlowAnalysisResult:
    """Resultado da análise de order flow."""
    # Signals
    signals: List[OrderFlowSignal]
    dominant_signal: Optional[OrderFlowSignal]
    
    # Métricas
    cumulative_delta: float
    delta_trend: str  # 'rising', 'falling', 'flat'
    absorption_detected: bool
    imbalance_detected: bool
    
    # Bias
    flow_bias: str  # 'bullish', 'bearish', 'neutral'
    confidence: float
    
    # Footprint
    recent_footprints: List[FootprintBar]
    
    recommendation: str
    details: Dict[str, Any]


class OrderFlowAnalyzer:
    """
    Analisador de Order Flow.
    
    Simula análise de fluxo de ordens usando dados disponíveis
    (volume, preço, ticks) para detectar atividade institucional.
    """
    
    # Thresholds
    DELTA_THRESHOLD = 0.6       # 60% para considerar unilateral
    IMBALANCE_THRESHOLD = 2.0   # 2:1 ratio para imbalance
    ABSORPTION_VOL_MULT = 2.0   # Volume para absorção
    
    def __init__(
        self,
        logger: logging.Logger = None,
        delta_lookback: int = 20,
        imbalance_lookback: int = 10,
    ):
        self.logger = logger or logging.getLogger(__name__)
        
        self.delta_lookback = delta_lookback
        self.imbalance_lookback = imbalance_lookback
        
        # Histórico
        self.footprints: List[FootprintBar] = []
        self.cumulative_delta_history: List[float] = []
    
    def analyze(
        self,
        df: pd.DataFrame,
        tick_data: pd.DataFrame = None,
    ) -> OrderFlowAnalysisResult:
        """
        Analisa order flow.
        
        Args:
            df: DataFrame OHLCV
            tick_data: Dados de tick (opcional, para análise mais precisa)
            
        Returns:
            OrderFlowAnalysisResult
        """
        if df is None or len(df) < 10:
            return self._neutral_result()
        
        # Gera footprints simulados
        footprints = self._generate_footprints(df)
        
        if not footprints:
            return self._neutral_result()
        
        # Análise de delta
        delta_signals = self._analyze_delta(footprints)
        
        # Detecção de absorção
        absorption_signals = self._detect_absorption(footprints)
        
        # Detecção de imbalance
        imbalance_signals = self._detect_imbalance(footprints)
        
        # Detecção de exaustão
        exhaustion_signals = self._detect_exhaustion(footprints)
        
        # Combina todos os sinais
        all_signals = delta_signals + absorption_signals + imbalance_signals + exhaustion_signals
        
        # Ordena por confiança
        all_signals.sort(key=lambda s: -s.confidence)
        
        # Sinal dominante
        dominant = all_signals[0] if all_signals else None
        
        # Calcula métricas
        cum_delta = sum(f.delta for f in footprints[-self.delta_lookback:])
        delta_trend = self._get_delta_trend(footprints)
        
        # Bias
        flow_bias, confidence = self._calculate_bias(footprints, all_signals)
        
        # Absorção e imbalance flags
        absorption_detected = any(s.type == OrderFlowType.ABSORPTION for s in all_signals)
        imbalance_detected = any(s.type == OrderFlowType.IMBALANCE for s in all_signals)
        
        # Recomendação
        recommendation = self._generate_recommendation(
            dominant, flow_bias, delta_trend, absorption_detected
        )
        
        return OrderFlowAnalysisResult(
            signals=all_signals[:10],  # Top 10
            dominant_signal=dominant,
            cumulative_delta=cum_delta,
            delta_trend=delta_trend,
            absorption_detected=absorption_detected,
            imbalance_detected=imbalance_detected,
            flow_bias=flow_bias,
            confidence=confidence,
            recent_footprints=footprints[-10:],
            recommendation=recommendation,
            details={
                'total_signals': len(all_signals),
                'delta': cum_delta,
            }
        )
    
    def _generate_footprints(self, df: pd.DataFrame) -> List[FootprintBar]:
        """Gera footprints simulados a partir de OHLCV."""
        footprints = []
        cumulative_delta = 0.0
        
        vol_col = 'volume' if 'volume' in df.columns else 'tick_volume'
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            o = row['open']
            h = row['high']
            l = row['low']
            c = row['close']
            v = row[vol_col]
            
            # Estima buy/sell volume baseado na posição do close
            # Regra simples: se close > open, mais buy volume
            range_size = h - l if h > l else 0.0001
            close_position = (c - l) / range_size  # 0 a 1
            
            # Adiciona componente de wick
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l
            
            # Ajusta baseado em wicks (wicks indicam rejeição)
            if upper_wick > lower_wick:
                # Mais rejeição em cima = mais selling
                close_position *= 0.8
            elif lower_wick > upper_wick:
                # Mais rejeição embaixo = mais buying
                close_position = 0.2 + close_position * 0.8
            
            buy_vol = v * close_position
            sell_vol = v * (1 - close_position)
            
            delta = buy_vol - sell_vol
            cumulative_delta += delta
            
            # Calcula imbalances simples
            bid_imb = sell_vol / buy_vol if buy_vol > 0 else 1
            ask_imb = buy_vol / sell_vol if sell_vol > 0 else 1
            
            # POC é aproximadamente o preço médio
            poc = (h + l + c) / 3
            
            footprint = FootprintBar(
                timestamp=row.get('time', datetime.now()) if 'time' in row else datetime.now(),
                open_price=o,
                high=h,
                low=l,
                close=c,
                buy_volume=buy_vol,
                sell_volume=sell_vol,
                total_volume=v,
                delta=delta,
                cumulative_delta=cumulative_delta,
                bid_imbalance=bid_imb,
                ask_imbalance=ask_imb,
                poc_price=poc,
            )
            
            footprints.append(footprint)
        
        return footprints
    
    def _analyze_delta(self, footprints: List[FootprintBar]) -> List[OrderFlowSignal]:
        """Analisa delta para detectar fluxo direcional."""
        signals = []
        
        if len(footprints) < 5:
            return signals
        
        recent = footprints[-5:]
        
        # Delta acumulado recente
        total_delta = sum(f.delta for f in recent)
        total_volume = sum(f.total_volume for f in recent)
        
        if total_volume == 0:
            return signals
        
        delta_pct = total_delta / total_volume
        
        # Compra agressiva
        if delta_pct > self.DELTA_THRESHOLD:
            signals.append(OrderFlowSignal(
                type=OrderFlowType.AGGRESSIVE_BUY,
                strength=OrderFlowStrength.STRONG if delta_pct > 0.75 else OrderFlowStrength.MODERATE,
                price=recent[-1].close,
                timestamp=recent[-1].timestamp,
                description=f"Compra agressiva detectada - Delta {delta_pct:.0%}",
                confidence=min(delta_pct, 0.95),
                delta=total_delta,
                delta_pct=delta_pct,
                imbalance_ratio=0,
                direction='bullish',
                recommendation="Fluxo comprando - Favorece LONG",
            ))
        
        # Venda agressiva
        elif delta_pct < -self.DELTA_THRESHOLD:
            signals.append(OrderFlowSignal(
                type=OrderFlowType.AGGRESSIVE_SELL,
                strength=OrderFlowStrength.STRONG if delta_pct < -0.75 else OrderFlowStrength.MODERATE,
                price=recent[-1].close,
                timestamp=recent[-1].timestamp,
                description=f"Venda agressiva detectada - Delta {delta_pct:.0%}",
                confidence=min(abs(delta_pct), 0.95),
                delta=total_delta,
                delta_pct=delta_pct,
                imbalance_ratio=0,
                direction='bearish',
                recommendation="Fluxo vendendo - Favorece SHORT",
            ))
        
        return signals
    
    def _detect_absorption(self, footprints: List[FootprintBar]) -> List[OrderFlowSignal]:
        """Detecta absorção de ordens."""
        signals = []
        
        if len(footprints) < 3:
            return signals
        
        # Absorção: alto volume com pouco movimento de preço
        for i in range(2, len(footprints)):
            current = footprints[i]
            prev = footprints[i-1]
            
            # Calcula range e volume
            price_range = abs(current.high - current.low)
            avg_range = np.mean([abs(f.high - f.low) for f in footprints[max(0, i-10):i]])
            avg_volume = np.mean([f.total_volume for f in footprints[max(0, i-10):i]])
            
            # Absorção: volume alto + range pequeno
            if current.total_volume > avg_volume * self.ABSORPTION_VOL_MULT:
                if price_range < avg_range * 0.5:
                    # Determina direção baseado no delta
                    if current.delta > 0:
                        direction = 'bullish'
                        desc = "Absorção de venda detectada - Compradores absorvendo"
                    else:
                        direction = 'bearish'
                        desc = "Absorção de compra detectada - Vendedores absorvendo"
                    
                    signals.append(OrderFlowSignal(
                        type=OrderFlowType.ABSORPTION,
                        strength=OrderFlowStrength.STRONG,
                        price=current.close,
                        timestamp=current.timestamp,
                        description=desc,
                        confidence=0.75,
                        delta=current.delta,
                        delta_pct=current.delta / current.total_volume if current.total_volume > 0 else 0,
                        imbalance_ratio=0,
                        direction=direction,
                        recommendation=f"Absorção {direction} - Possível reversão",
                    ))
        
        return signals
    
    def _detect_imbalance(self, footprints: List[FootprintBar]) -> List[OrderFlowSignal]:
        """Detecta imbalance no fluxo."""
        signals = []
        
        if len(footprints) < 1:
            return signals
        
        current = footprints[-1]
        
        # Imbalance de compra
        if current.ask_imbalance > self.IMBALANCE_THRESHOLD:
            signals.append(OrderFlowSignal(
                type=OrderFlowType.IMBALANCE,
                strength=OrderFlowStrength.MODERATE,
                price=current.close,
                timestamp=current.timestamp,
                description=f"Imbalance de compra {current.ask_imbalance:.1f}:1",
                confidence=min(current.ask_imbalance / 4, 0.85),
                delta=current.delta,
                delta_pct=0,
                imbalance_ratio=current.ask_imbalance,
                direction='bullish',
                recommendation="Imbalance bullish - Pressão compradora",
            ))
        
        # Imbalance de venda
        elif current.bid_imbalance > self.IMBALANCE_THRESHOLD:
            signals.append(OrderFlowSignal(
                type=OrderFlowType.IMBALANCE,
                strength=OrderFlowStrength.MODERATE,
                price=current.close,
                timestamp=current.timestamp,
                description=f"Imbalance de venda {current.bid_imbalance:.1f}:1",
                confidence=min(current.bid_imbalance / 4, 0.85),
                delta=current.delta,
                delta_pct=0,
                imbalance_ratio=current.bid_imbalance,
                direction='bearish',
                recommendation="Imbalance bearish - Pressão vendedora",
            ))
        
        return signals
    
    def _detect_exhaustion(self, footprints: List[FootprintBar]) -> List[OrderFlowSignal]:
        """Detecta exaustão de movimento."""
        signals = []
        
        if len(footprints) < 10:
            return signals
        
        recent = footprints[-10:]
        
        # Trend de preço
        price_change = recent[-1].close - recent[0].close
        
        # Delta acumulado
        cum_delta = sum(f.delta for f in recent)
        
        # Exaustão: preço subindo mas delta diminuindo (divergência)
        if price_change > 0 and cum_delta < 0:
            signals.append(OrderFlowSignal(
                type=OrderFlowType.EXHAUSTION,
                strength=OrderFlowStrength.MODERATE,
                price=recent[-1].close,
                timestamp=recent[-1].timestamp,
                description="Exaustão de alta - Preço sobe mas fluxo é vendedor",
                confidence=0.7,
                delta=cum_delta,
                delta_pct=0,
                imbalance_ratio=0,
                direction='bearish',
                recommendation="Exaustão bullish - Possível topo",
            ))
        
        # Exaustão: preço caindo mas delta aumentando
        elif price_change < 0 and cum_delta > 0:
            signals.append(OrderFlowSignal(
                type=OrderFlowType.EXHAUSTION,
                strength=OrderFlowStrength.MODERATE,
                price=recent[-1].close,
                timestamp=recent[-1].timestamp,
                description="Exaustão de baixa - Preço cai mas fluxo é comprador",
                confidence=0.7,
                delta=cum_delta,
                delta_pct=0,
                imbalance_ratio=0,
                direction='bullish',
                recommendation="Exaustão bearish - Possível fundo",
            ))
        
        return signals
    
    def _get_delta_trend(self, footprints: List[FootprintBar]) -> str:
        """Calcula tendência do delta."""
        if len(footprints) < 10:
            return 'flat'
        
        recent = footprints[-10:]
        
        first_half = sum(f.delta for f in recent[:5])
        second_half = sum(f.delta for f in recent[5:])
        
        if second_half > first_half * 1.2:
            return 'rising'
        elif second_half < first_half * 0.8:
            return 'falling'
        else:
            return 'flat'
    
    def _calculate_bias(
        self,
        footprints: List[FootprintBar],
        signals: List[OrderFlowSignal]
    ) -> Tuple[str, float]:
        """Calcula bias do fluxo."""
        
        if not footprints:
            return 'neutral', 0.5
        
        # Baseado em delta recente
        recent_delta = sum(f.delta for f in footprints[-10:])
        recent_volume = sum(f.total_volume for f in footprints[-10:])
        
        if recent_volume == 0:
            return 'neutral', 0.5
        
        delta_pct = recent_delta / recent_volume
        
        # Ajusta baseado em sinais
        signal_score = 0
        for s in signals[:5]:
            if s.direction == 'bullish':
                signal_score += s.confidence
            else:
                signal_score -= s.confidence
        
        combined = delta_pct * 0.6 + (signal_score / 5) * 0.4 if signals else delta_pct
        
        if combined > 0.2:
            return 'bullish', min(abs(combined), 0.9)
        elif combined < -0.2:
            return 'bearish', min(abs(combined), 0.9)
        else:
            return 'neutral', 0.5 - abs(combined)
    
    def _generate_recommendation(
        self,
        dominant: Optional[OrderFlowSignal],
        bias: str,
        delta_trend: str,
        absorption: bool
    ) -> str:
        """Gera recomendação."""
        
        parts = []
        
        if dominant:
            parts.append(dominant.recommendation)
        
        if bias == 'bullish':
            parts.append("🟢 Fluxo favorece alta")
        elif bias == 'bearish':
            parts.append("🔴 Fluxo favorece baixa")
        
        if delta_trend == 'rising':
            parts.append("📈 Delta acelerando")
        elif delta_trend == 'falling':
            parts.append("📉 Delta desacelerando")
        
        if absorption:
            parts.append("⚡ Absorção detectada")
        
        if not parts:
            return "⚪ Fluxo neutro - Sem sinal claro"
        
        return " | ".join(parts)
    
    def _neutral_result(self) -> OrderFlowAnalysisResult:
        """Retorna resultado neutro."""
        return OrderFlowAnalysisResult(
            signals=[],
            dominant_signal=None,
            cumulative_delta=0,
            delta_trend='flat',
            absorption_detected=False,
            imbalance_detected=False,
            flow_bias='neutral',
            confidence=0.5,
            recent_footprints=[],
            recommendation="⚪ Dados insuficientes para análise de fluxo",
            details={},
        )
    
    def to_dict(self, result: OrderFlowAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        signals_list = []
        for s in result.signals[:5]:
            signals_list.append({
                'type': s.type.name,
                'strength': s.strength.name,
                'price': round(s.price, 5),
                'direction': s.direction,
                'confidence': round(s.confidence, 2),
                'description': s.description,
            })
        
        return {
            'flow_bias': result.flow_bias,
            'confidence': round(result.confidence, 2),
            'cumulative_delta': round(result.cumulative_delta, 0),
            'delta_trend': result.delta_trend,
            'absorption_detected': result.absorption_detected,
            'imbalance_detected': result.imbalance_detected,
            'dominant_signal': result.dominant_signal.type.name if result.dominant_signal else None,
            'signals': signals_list,
            'recommendation': result.recommendation,
        }
