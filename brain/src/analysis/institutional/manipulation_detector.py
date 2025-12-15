"""
VIRTUS Manipulation Detector
=============================

Detecta manipulação de mercado para proteção do capital.
Bloqueia trades quando manipulação é detectada.

Tipos detectados:
- Stop Hunt
- Fake Breakout
- Volume Spike
- Spread Manipulation
- Liquidity Grab
- Wyckoff Spring/Upthrust
- Liquidity Sweep
- Equal Highs/Lows Sweep
- Order Block Raid
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import deque
import logging


class ManipulationType(Enum):
    """Tipos de manipulação detectados."""
    STOP_HUNT = auto()
    FAKE_BREAKOUT = auto()
    VOLUME_SPIKE = auto()
    SPREAD_MANIPULATION = auto()
    LIQUIDITY_GRAB = auto()
    INSTITUTIONAL_ACCUMULATION = auto()
    INSTITUTIONAL_DISTRIBUTION = auto()
    WYCKOFF_SPRING = auto()
    WYCKOFF_UPTHRUST = auto()
    LIQUIDITY_SWEEP = auto()
    EQUAL_HIGHS_SWEEP = auto()
    EQUAL_LOWS_SWEEP = auto()
    ORDER_BLOCK_RAID = auto()


class ManipulationSeverity(Enum):
    """Severidade da manipulação."""
    LOW = auto()       # Alerta apenas
    MEDIUM = auto()    # Reduzir posição
    HIGH = auto()      # Evitar trades
    CRITICAL = auto()  # Bloquear completamente


@dataclass
class ManipulationEvent:
    """Um evento de manipulação detectado."""
    timestamp: datetime
    type: ManipulationType
    severity: ManipulationSeverity
    price: float
    description: str
    confidence: float  # 0 a 1
    recommended_action: str
    details: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None


@dataclass
class ManipulationAnalysisResult:
    """Resultado da análise de manipulação."""
    is_safe: bool
    active_events: List[ManipulationEvent]
    highest_severity: ManipulationSeverity
    blocking_reason: Optional[str]
    cooldown_remaining: int  # segundos
    risk_multiplier: float  # 1.0 = normal, 0.5 = reduzir, 0 = bloquear


class ManipulationDetector:
    """
    Detector de manipulação de mercado.
    
    Protege o capital identificando armadilhas institucionais
    e bloqueando trades em momentos perigosos.
    """
    
    # Cooldown após eventos (segundos)
    COOLDOWN_BY_SEVERITY = {
        ManipulationSeverity.LOW: 60,
        ManipulationSeverity.MEDIUM: 180,
        ManipulationSeverity.HIGH: 300,
        ManipulationSeverity.CRITICAL: 600,
    }
    
    def __init__(
        self,
        logger: logging.Logger = None,
        # Stop Hunt
        stop_hunt_wick_ratio: float = 2.5,
        stop_hunt_volume_mult: float = 1.5,
        # Fake Breakout
        fake_breakout_retrace_pct: float = 0.7,
        fake_breakout_bars: int = 5,
        # Volume Spike
        volume_spike_mult: float = 3.0,
        # Spread
        max_spread_mult: float = 3.0,
        # Equal Highs/Lows
        equal_tolerance_pct: float = 0.0002,
    ):
        self.logger = logger or logging.getLogger(__name__)
        
        self.stop_hunt_wick_ratio = stop_hunt_wick_ratio
        self.stop_hunt_volume_mult = stop_hunt_volume_mult
        self.fake_breakout_retrace_pct = fake_breakout_retrace_pct
        self.fake_breakout_bars = fake_breakout_bars
        self.volume_spike_mult = volume_spike_mult
        self.max_spread_mult = max_spread_mult
        self.equal_tolerance_pct = equal_tolerance_pct
        
        # Histórico de eventos
        self.events_history: deque = deque(maxlen=100)
        self.active_events: List[ManipulationEvent] = []
    
    def analyze(
        self,
        df: pd.DataFrame,
        current_spread: float = None,
        average_spread: float = None,
    ) -> ManipulationAnalysisResult:
        """
        Analisa manipulação no mercado.
        
        Args:
            df: DataFrame com OHLCV
            current_spread: Spread atual (opcional)
            average_spread: Spread médio (opcional)
            
        Returns:
            ManipulationAnalysisResult
        """
        if df is None or len(df) < 50:
            return self._safe_result()
        
        # Limpa eventos expirados
        self._cleanup_expired_events()
        
        new_events = []
        
        # 1. Stop Hunt Detection
        stop_hunt = self._detect_stop_hunt(df)
        if stop_hunt:
            new_events.append(stop_hunt)
        
        # 2. Fake Breakout Detection
        fake_breakout = self._detect_fake_breakout(df)
        if fake_breakout:
            new_events.append(fake_breakout)
        
        # 3. Volume Spike Detection
        volume_spike = self._detect_volume_spike(df)
        if volume_spike:
            new_events.append(volume_spike)
        
        # 4. Spread Manipulation
        if current_spread and average_spread:
            spread_manip = self._detect_spread_manipulation(current_spread, average_spread)
            if spread_manip:
                new_events.append(spread_manip)
        
        # 5. Liquidity Grab
        liquidity_grab = self._detect_liquidity_grab(df)
        if liquidity_grab:
            new_events.append(liquidity_grab)
        
        # 6. Wyckoff Spring/Upthrust
        wyckoff = self._detect_wyckoff_patterns(df)
        if wyckoff:
            new_events.extend(wyckoff)
        
        # 7. Liquidity Sweep
        sweep = self._detect_liquidity_sweep(df)
        if sweep:
            new_events.append(sweep)
        
        # 8. Equal Highs/Lows Sweep
        equal_sweep = self._detect_equal_levels_sweep(df)
        if equal_sweep:
            new_events.extend(equal_sweep)
        
        # Adiciona novos eventos ao histórico
        for event in new_events:
            self.events_history.append(event)
            self.active_events.append(event)
        
        # Determina resultado
        return self._evaluate_safety()
    
    def _detect_stop_hunt(self, df: pd.DataFrame) -> Optional[ManipulationEvent]:
        """Detecta Stop Hunt."""
        if len(df) < 10:
            return None
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        high = last['high']
        low = last['low']
        open_price = last['open']
        close = last['close']
        volume = last.get('volume', last.get('tick_volume', 0))
        
        body = abs(close - open_price)
        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low
        
        avg_volume = df['volume'].mean() if 'volume' in df.columns else df['tick_volume'].mean()
        
        # Stop Hunt para CIMA (bearish)
        if upper_wick > body * self.stop_hunt_wick_ratio:
            if volume > avg_volume * self.stop_hunt_volume_mult:
                if close < open_price:  # Candle bearish
                    return ManipulationEvent(
                        timestamp=datetime.now(),
                        type=ManipulationType.STOP_HUNT,
                        severity=ManipulationSeverity.HIGH,
                        price=high,
                        description="Stop Hunt detectado acima - possível reversão para baixo",
                        confidence=0.8,
                        recommended_action="Evitar LONG, considerar SHORT após confirmação",
                        details={
                            'wick_ratio': upper_wick / body if body > 0 else 999,
                            'volume_ratio': volume / avg_volume,
                            'direction': 'bearish',
                        },
                        expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                    )
        
        # Stop Hunt para BAIXO (bullish)
        if lower_wick > body * self.stop_hunt_wick_ratio:
            if volume > avg_volume * self.stop_hunt_volume_mult:
                if close > open_price:  # Candle bullish
                    return ManipulationEvent(
                        timestamp=datetime.now(),
                        type=ManipulationType.STOP_HUNT,
                        severity=ManipulationSeverity.HIGH,
                        price=low,
                        description="Stop Hunt detectado abaixo - possível reversão para cima",
                        confidence=0.8,
                        recommended_action="Evitar SHORT, considerar LONG após confirmação",
                        details={
                            'wick_ratio': lower_wick / body if body > 0 else 999,
                            'volume_ratio': volume / avg_volume,
                            'direction': 'bullish',
                        },
                        expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                    )
        
        return None
    
    def _detect_fake_breakout(self, df: pd.DataFrame) -> Optional[ManipulationEvent]:
        """Detecta Fake Breakout."""
        if len(df) < 20:
            return None
        
        lookback = 20
        recent = df.iloc[-lookback:-1]
        last = df.iloc[-1]
        
        resistance = recent['high'].max()
        support = recent['low'].min()
        
        high = last['high']
        low = last['low']
        close = last['close']
        
        # Fake breakout para CIMA
        if high > resistance:
            # Fechou abaixo da resistência?
            if close < resistance:
                retrace = (high - close) / (high - resistance) if high > resistance else 0
                
                if retrace >= self.fake_breakout_retrace_pct:
                    return ManipulationEvent(
                        timestamp=datetime.now(),
                        type=ManipulationType.FAKE_BREAKOUT,
                        severity=ManipulationSeverity.HIGH,
                        price=high,
                        description=f"Fake Breakout acima de {resistance:.5f} - armadilha de compra",
                        confidence=0.75,
                        recommended_action="Evitar LONG, possível queda iminente",
                        details={
                            'resistance': resistance,
                            'breakout_high': high,
                            'close': close,
                            'retrace_pct': retrace,
                        },
                        expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                    )
        
        # Fake breakout para BAIXO
        if low < support:
            if close > support:
                retrace = (close - low) / (support - low) if low < support else 0
                
                if retrace >= self.fake_breakout_retrace_pct:
                    return ManipulationEvent(
                        timestamp=datetime.now(),
                        type=ManipulationType.FAKE_BREAKOUT,
                        severity=ManipulationSeverity.HIGH,
                        price=low,
                        description=f"Fake Breakout abaixo de {support:.5f} - armadilha de venda",
                        confidence=0.75,
                        recommended_action="Evitar SHORT, possível alta iminente",
                        details={
                            'support': support,
                            'breakout_low': low,
                            'close': close,
                            'retrace_pct': retrace,
                        },
                        expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                    )
        
        return None
    
    def _detect_volume_spike(self, df: pd.DataFrame) -> Optional[ManipulationEvent]:
        """Detecta Volume Spike anormal."""
        if len(df) < 20:
            return None
        
        vol_col = 'volume' if 'volume' in df.columns else 'tick_volume'
        
        last_volume = df[vol_col].iloc[-1]
        avg_volume = df[vol_col].iloc[-20:-1].mean()
        
        if last_volume > avg_volume * self.volume_spike_mult:
            severity = ManipulationSeverity.MEDIUM
            if last_volume > avg_volume * 5:
                severity = ManipulationSeverity.HIGH
            
            return ManipulationEvent(
                timestamp=datetime.now(),
                type=ManipulationType.VOLUME_SPIKE,
                severity=severity,
                price=df['close'].iloc[-1],
                description=f"Volume spike {last_volume/avg_volume:.1f}x acima da média",
                confidence=0.7,
                recommended_action="Cautela - possível manipulação institucional",
                details={
                    'current_volume': last_volume,
                    'avg_volume': avg_volume,
                    'ratio': last_volume / avg_volume,
                },
                expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[severity]),
            )
        
        return None
    
    def _detect_spread_manipulation(
        self,
        current_spread: float,
        average_spread: float,
    ) -> Optional[ManipulationEvent]:
        """Detecta Spread anormalmente alto."""
        if average_spread <= 0:
            return None
        
        ratio = current_spread / average_spread
        
        if ratio > self.max_spread_mult:
            severity = ManipulationSeverity.MEDIUM
            if ratio > 5:
                severity = ManipulationSeverity.CRITICAL
            
            return ManipulationEvent(
                timestamp=datetime.now(),
                type=ManipulationType.SPREAD_MANIPULATION,
                severity=severity,
                price=0,  # Não específico
                description=f"Spread {ratio:.1f}x maior que a média - evitar trading",
                confidence=0.9,
                recommended_action="NÃO OPERAR até spread normalizar",
                details={
                    'current_spread': current_spread,
                    'avg_spread': average_spread,
                    'ratio': ratio,
                },
                expires_at=datetime.now() + timedelta(seconds=60),  # Curto prazo
            )
        
        return None
    
    def _detect_liquidity_grab(self, df: pd.DataFrame) -> Optional[ManipulationEvent]:
        """Detecta Liquidity Grab institucional."""
        if len(df) < 5:
            return None
        
        # Últimos 3 candles
        candles = df.iloc[-3:]
        
        # Verifica sequência: impulso forte → reversão
        impulse = candles.iloc[0]
        middle = candles.iloc[1]
        reversal = candles.iloc[2]
        
        impulse_move = abs(impulse['close'] - impulse['open'])
        reversal_move = abs(reversal['close'] - reversal['open'])
        
        # Impulso de alta seguido de reversão
        if impulse['close'] > impulse['open']:  # Candle de alta
            if reversal['close'] < reversal['open']:  # Candle de baixa
                if reversal['close'] < impulse['open']:  # Fechou abaixo do início
                    return ManipulationEvent(
                        timestamp=datetime.now(),
                        type=ManipulationType.LIQUIDITY_GRAB,
                        severity=ManipulationSeverity.HIGH,
                        price=candles['high'].max(),
                        description="Liquidity Grab bullish - instituições pegaram stops de shorts",
                        confidence=0.7,
                        recommended_action="Possível queda - evitar LONG",
                        details={
                            'grab_high': candles['high'].max(),
                            'reversal_close': reversal['close'],
                        },
                        expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                    )
        
        # Impulso de baixa seguido de reversão
        if impulse['close'] < impulse['open']:  # Candle de baixa
            if reversal['close'] > reversal['open']:  # Candle de alta
                if reversal['close'] > impulse['open']:  # Fechou acima do início
                    return ManipulationEvent(
                        timestamp=datetime.now(),
                        type=ManipulationType.LIQUIDITY_GRAB,
                        severity=ManipulationSeverity.HIGH,
                        price=candles['low'].min(),
                        description="Liquidity Grab bearish - instituições pegaram stops de longs",
                        confidence=0.7,
                        recommended_action="Possível alta - evitar SHORT",
                        details={
                            'grab_low': candles['low'].min(),
                            'reversal_close': reversal['close'],
                        },
                        expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                    )
        
        return None
    
    def _detect_wyckoff_patterns(self, df: pd.DataFrame) -> List[ManipulationEvent]:
        """Detecta Spring e Upthrust de Wyckoff."""
        events = []
        
        if len(df) < 30:
            return events
        
        recent = df.iloc[-30:]
        last = df.iloc[-1]
        
        # Encontra range de consolidação
        range_high = recent['high'].max()
        range_low = recent['low'].min()
        range_size = range_high - range_low
        
        # Spring (falso rompimento para baixo que reverte)
        if last['low'] < range_low:
            if last['close'] > range_low:  # Fechou dentro do range
                events.append(ManipulationEvent(
                    timestamp=datetime.now(),
                    type=ManipulationType.WYCKOFF_SPRING,
                    severity=ManipulationSeverity.MEDIUM,
                    price=last['low'],
                    description=f"Wyckoff Spring detectado em {last['low']:.5f}",
                    confidence=0.65,
                    recommended_action="Possível setup de COMPRA após confirmação",
                    details={
                        'range_low': range_low,
                        'spring_low': last['low'],
                        'penetration': range_low - last['low'],
                    },
                    expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.MEDIUM]),
                ))
        
        # Upthrust (falso rompimento para cima que reverte)
        if last['high'] > range_high:
            if last['close'] < range_high:  # Fechou dentro do range
                events.append(ManipulationEvent(
                    timestamp=datetime.now(),
                    type=ManipulationType.WYCKOFF_UPTHRUST,
                    severity=ManipulationSeverity.MEDIUM,
                    price=last['high'],
                    description=f"Wyckoff Upthrust detectado em {last['high']:.5f}",
                    confidence=0.65,
                    recommended_action="Possível setup de VENDA após confirmação",
                    details={
                        'range_high': range_high,
                        'upthrust_high': last['high'],
                        'penetration': last['high'] - range_high,
                    },
                    expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.MEDIUM]),
                ))
        
        return events
    
    def _detect_liquidity_sweep(self, df: pd.DataFrame) -> Optional[ManipulationEvent]:
        """Detecta Liquidity Sweep avançado."""
        if len(df) < 20:
            return None
        
        # Últimos candles
        recent = df.iloc[-10:]
        last = df.iloc[-1]
        
        # Encontra swing highs e lows recentes
        highs = []
        lows = []
        
        for i in range(1, len(recent) - 1):
            if recent['high'].iloc[i] > recent['high'].iloc[i-1] and \
               recent['high'].iloc[i] > recent['high'].iloc[i+1]:
                highs.append(recent['high'].iloc[i])
            
            if recent['low'].iloc[i] < recent['low'].iloc[i-1] and \
               recent['low'].iloc[i] < recent['low'].iloc[i+1]:
                lows.append(recent['low'].iloc[i])
        
        # Sweep de alta com reversão
        if highs and last['high'] > max(highs):
            if last['close'] < max(highs):
                return ManipulationEvent(
                    timestamp=datetime.now(),
                    type=ManipulationType.LIQUIDITY_SWEEP,
                    severity=ManipulationSeverity.HIGH,
                    price=last['high'],
                    description="Liquidity Sweep bullish - varreu stops e reverteu",
                    confidence=0.75,
                    recommended_action="Sinal bearish forte - considerar SHORT",
                    details={
                        'swept_level': max(highs),
                        'sweep_high': last['high'],
                        'direction': 'bearish',
                    },
                    expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                )
        
        # Sweep de baixa com reversão
        if lows and last['low'] < min(lows):
            if last['close'] > min(lows):
                return ManipulationEvent(
                    timestamp=datetime.now(),
                    type=ManipulationType.LIQUIDITY_SWEEP,
                    severity=ManipulationSeverity.HIGH,
                    price=last['low'],
                    description="Liquidity Sweep bearish - varreu stops e reverteu",
                    confidence=0.75,
                    recommended_action="Sinal bullish forte - considerar LONG",
                    details={
                        'swept_level': min(lows),
                        'sweep_low': last['low'],
                        'direction': 'bullish',
                    },
                    expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                )
        
        return None
    
    def _detect_equal_levels_sweep(self, df: pd.DataFrame) -> List[ManipulationEvent]:
        """Detecta sweep de Equal Highs / Equal Lows."""
        events = []
        
        if len(df) < 20:
            return events
        
        recent = df.iloc[-20:-1]
        last = df.iloc[-1]
        
        highs = recent['high'].values
        lows = recent['low'].values
        
        # Encontra equal highs (topos no mesmo nível)
        for i in range(len(highs) - 1):
            for j in range(i + 1, len(highs)):
                tolerance = highs[i] * self.equal_tolerance_pct
                if abs(highs[i] - highs[j]) < tolerance:
                    equal_high = max(highs[i], highs[j])
                    
                    # Sweep?
                    if last['high'] > equal_high and last['close'] < equal_high:
                        events.append(ManipulationEvent(
                            timestamp=datetime.now(),
                            type=ManipulationType.EQUAL_HIGHS_SWEEP,
                            severity=ManipulationSeverity.HIGH,
                            price=equal_high,
                            description=f"Equal Highs swept em {equal_high:.5f}",
                            confidence=0.8,
                            recommended_action="Possível reversão bearish - evitar LONG",
                            details={
                                'equal_level': equal_high,
                                'sweep_high': last['high'],
                            },
                            expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                        ))
                        break
            else:
                continue
            break
        
        # Encontra equal lows
        for i in range(len(lows) - 1):
            for j in range(i + 1, len(lows)):
                tolerance = lows[i] * self.equal_tolerance_pct
                if abs(lows[i] - lows[j]) < tolerance:
                    equal_low = min(lows[i], lows[j])
                    
                    # Sweep?
                    if last['low'] < equal_low and last['close'] > equal_low:
                        events.append(ManipulationEvent(
                            timestamp=datetime.now(),
                            type=ManipulationType.EQUAL_LOWS_SWEEP,
                            severity=ManipulationSeverity.HIGH,
                            price=equal_low,
                            description=f"Equal Lows swept em {equal_low:.5f}",
                            confidence=0.8,
                            recommended_action="Possível reversão bullish - evitar SHORT",
                            details={
                                'equal_level': equal_low,
                                'sweep_low': last['low'],
                            },
                            expires_at=datetime.now() + timedelta(seconds=self.COOLDOWN_BY_SEVERITY[ManipulationSeverity.HIGH]),
                        ))
                        break
            else:
                continue
            break
        
        return events
    
    def _cleanup_expired_events(self) -> None:
        """Remove eventos expirados."""
        now = datetime.now()
        self.active_events = [
            e for e in self.active_events
            if e.expires_at is None or e.expires_at > now
        ]
    
    def _evaluate_safety(self) -> ManipulationAnalysisResult:
        """Avalia se é seguro operar."""
        if not self.active_events:
            return self._safe_result()
        
        # Encontra maior severidade
        highest = max(e.severity for e in self.active_events)
        
        # Calcula cooldown restante
        max_cooldown = 0
        blocking_reason = None
        
        for event in self.active_events:
            if event.expires_at:
                remaining = (event.expires_at - datetime.now()).total_seconds()
                if remaining > max_cooldown:
                    max_cooldown = remaining
                    
                if event.severity in [ManipulationSeverity.HIGH, ManipulationSeverity.CRITICAL]:
                    blocking_reason = event.description
        
        # Determina se é seguro
        is_safe = highest not in [ManipulationSeverity.HIGH, ManipulationSeverity.CRITICAL]
        
        # Risk multiplier
        if highest == ManipulationSeverity.CRITICAL:
            risk_mult = 0.0
        elif highest == ManipulationSeverity.HIGH:
            risk_mult = 0.3
        elif highest == ManipulationSeverity.MEDIUM:
            risk_mult = 0.6
        else:
            risk_mult = 0.8
        
        return ManipulationAnalysisResult(
            is_safe=is_safe,
            active_events=self.active_events,
            highest_severity=highest,
            blocking_reason=blocking_reason,
            cooldown_remaining=int(max(0, max_cooldown)),
            risk_multiplier=risk_mult,
        )
    
    def _safe_result(self) -> ManipulationAnalysisResult:
        """Retorna resultado seguro."""
        return ManipulationAnalysisResult(
            is_safe=True,
            active_events=[],
            highest_severity=ManipulationSeverity.LOW,
            blocking_reason=None,
            cooldown_remaining=0,
            risk_multiplier=1.0,
        )
    
    def is_safe_to_trade(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Verifica rapidamente se é seguro operar.
        
        Returns:
            (is_safe, reason)
        """
        result = self.analyze(df)
        
        if result.is_safe:
            return True, "OK"
        else:
            return False, result.blocking_reason or "Manipulação detectada"
    
    def to_dict(self, result: ManipulationAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        events_list = []
        for e in result.active_events:
            events_list.append({
                'type': e.type.name,
                'severity': e.severity.name,
                'price': round(e.price, 5) if e.price else None,
                'description': e.description,
                'confidence': round(e.confidence, 2),
                'action': e.recommended_action,
                'expires_in': int((e.expires_at - datetime.now()).total_seconds()) if e.expires_at else None,
            })
        
        return {
            'is_safe': result.is_safe,
            'events': events_list,
            'highest_severity': result.highest_severity.name,
            'blocking_reason': result.blocking_reason,
            'cooldown_remaining': result.cooldown_remaining,
            'risk_multiplier': round(result.risk_multiplier, 2),
        }
