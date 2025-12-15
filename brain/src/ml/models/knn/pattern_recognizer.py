"""
VIRTUS Pattern Recognition - k-NN para Candlestick Patterns
============================================================

Implementação de k-Nearest Neighbors otimizado para:
- Reconhecimento de padrões de candlestick
- Detecção de formações clássicas
- Classificação de setups de trading
- Pattern matching com confiança

Padrões Detectados:
- Reversal: Doji, Hammer, Engulfing, Morning/Evening Star, etc.
- Continuation: Three White Soldiers, Three Black Crows, etc.
- Indecision: Spinning Top, Marubozu, etc.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from collections import Counter
import json
from pathlib import Path


class PatternType(Enum):
    """Tipos de padrões de candlestick."""
    # Single Candle
    DOJI = "doji"
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    HANGING_MAN = "hanging_man"
    SHOOTING_STAR = "shooting_star"
    MARUBOZU_BULL = "marubozu_bull"
    MARUBOZU_BEAR = "marubozu_bear"
    SPINNING_TOP = "spinning_top"
    
    # Double Candle
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    PIERCING_LINE = "piercing_line"
    DARK_CLOUD = "dark_cloud"
    TWEEZER_TOP = "tweezer_top"
    TWEEZER_BOTTOM = "tweezer_bottom"
    HARAMI_BULL = "harami_bull"
    HARAMI_BEAR = "harami_bear"
    
    # Triple Candle
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    THREE_INSIDE_UP = "three_inside_up"
    THREE_INSIDE_DOWN = "three_inside_down"
    
    # Chart Patterns
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_SHOULDERS = "head_shoulders"
    INV_HEAD_SHOULDERS = "inv_head_shoulders"
    
    # Unknown
    UNKNOWN = "unknown"


class PatternSignal(Enum):
    """Sinal do padrão."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class PatternReliability(Enum):
    """Confiabilidade do padrão."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CandleFeatures:
    """Features extraídas de um candle."""
    body_size: float          # Tamanho do corpo (abs(close-open)/range)
    upper_shadow: float       # Sombra superior/range
    lower_shadow: float       # Sombra inferior/range
    is_bullish: bool          # Candle de alta
    range_vs_atr: float       # Range vs ATR
    body_position: float      # Posição do corpo no range (0-1)
    gap_up: bool              # Gap de alta
    gap_down: bool            # Gap de baixa
    volume_ratio: float       # Volume vs média
    
    def to_array(self) -> np.ndarray:
        """Converte para array numérico."""
        return np.array([
            self.body_size,
            self.upper_shadow,
            self.lower_shadow,
            float(self.is_bullish),
            self.range_vs_atr,
            self.body_position,
            float(self.gap_up),
            float(self.gap_down),
            self.volume_ratio,
        ], dtype=np.float32)


@dataclass
class PatternMatch:
    """Resultado de um match de padrão."""
    pattern_type: PatternType
    signal: PatternSignal
    confidence: float         # 0.0 - 1.0
    reliability: PatternReliability
    distance: float          # Distância k-NN
    candles_used: int        # Número de candles no padrão
    start_index: int         # Índice inicial do padrão
    features: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern': self.pattern_type.value,
            'signal': self.signal.value,
            'confidence': round(self.confidence, 4),
            'reliability': self.reliability.value,
            'distance': round(self.distance, 4),
            'candles_used': self.candles_used,
            'start_index': self.start_index,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class PatternTemplate:
    """Template de um padrão conhecido."""
    pattern_type: PatternType
    signal: PatternSignal
    reliability: PatternReliability
    features: np.ndarray      # Feature vector normalizado
    n_candles: int
    description: str


class CandleFeatureExtractor:
    """
    Extrai features de candlesticks para k-NN.
    """
    
    def __init__(self, atr_period: int = 14):
        self.atr_period = atr_period
    
    def extract_single(
        self,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: float = 0,
        prev_close: Optional[float] = None,
        atr: float = 0,
        avg_volume: float = 1
    ) -> CandleFeatures:
        """Extrai features de um único candle."""
        
        range_ = high - low
        if range_ == 0:
            range_ = 0.0001  # Evitar divisão por zero
        
        body = abs(close - open_)
        upper_shadow = high - max(open_, close)
        lower_shadow = min(open_, close) - low
        
        # Body position (0 = bottom, 1 = top)
        body_mid = (open_ + close) / 2
        body_position = (body_mid - low) / range_
        
        # Gaps
        gap_up = prev_close is not None and open_ > prev_close
        gap_down = prev_close is not None and open_ < prev_close
        
        return CandleFeatures(
            body_size=body / range_,
            upper_shadow=upper_shadow / range_,
            lower_shadow=lower_shadow / range_,
            is_bullish=close > open_,
            range_vs_atr=range_ / atr if atr > 0 else 1.0,
            body_position=body_position,
            gap_up=gap_up,
            gap_down=gap_down,
            volume_ratio=volume / avg_volume if avg_volume > 0 else 1.0,
        )
    
    def extract_sequence(
        self,
        df,  # DataFrame com OHLCV
        n_candles: int = 3
    ) -> np.ndarray:
        """
        Extrai features de uma sequência de candles.
        
        Args:
            df: DataFrame com open, high, low, close, volume
            n_candles: Número de candles a considerar
            
        Returns:
            Feature vector combinado
        """
        if len(df) < n_candles:
            return np.zeros(n_candles * 9)  # 9 features por candle
        
        # ATR
        atr = self._calculate_atr(df)
        avg_volume = df['volume'].mean() if 'volume' in df.columns else 1
        
        features = []
        
        for i in range(n_candles):
            idx = -(n_candles - i)
            row = df.iloc[idx]
            
            prev_close = df.iloc[idx - 1]['close'] if idx > -len(df) else None
            vol = row.get('volume', row.get('tick_volume', 0))
            
            candle_features = self.extract_single(
                row['open'], row['high'], row['low'], row['close'],
                vol, prev_close, atr, avg_volume
            )
            features.append(candle_features.to_array())
        
        return np.concatenate(features)
    
    def _calculate_atr(self, df, period: int = 14) -> float:
        """Calcula ATR simplificado."""
        if len(df) < period:
            return df['high'].iloc[-1] - df['low'].iloc[-1]
        
        tr = []
        for i in range(-period, 0):
            h = df['high'].iloc[i]
            l = df['low'].iloc[i]
            c_prev = df['close'].iloc[i - 1] if i > -len(df) else l
            tr.append(max(h - l, abs(h - c_prev), abs(l - c_prev)))
        
        return np.mean(tr)


class PatternDatabase:
    """
    Banco de dados de padrões conhecidos para k-NN.
    """
    
    def __init__(self):
        self.templates: List[PatternTemplate] = []
        self._build_default_templates()
    
    def _build_default_templates(self) -> None:
        """Constrói templates de padrões clássicos."""
        
        # === SINGLE CANDLE PATTERNS ===
        
        # Doji (corpo muito pequeno)
        self.templates.append(PatternTemplate(
            pattern_type=PatternType.DOJI,
            signal=PatternSignal.NEUTRAL,
            reliability=PatternReliability.MEDIUM,
            features=np.array([0.05, 0.45, 0.45, 0.5, 1.0, 0.5, 0, 0, 1.0]),
            n_candles=1,
            description="Corpo muito pequeno, indecisão"
        ))
        
        # Hammer (sombra inferior longa, corpo pequeno no topo)
        self.templates.append(PatternTemplate(
            pattern_type=PatternType.HAMMER,
            signal=PatternSignal.BULLISH,
            reliability=PatternReliability.HIGH,
            features=np.array([0.2, 0.1, 0.7, 1.0, 1.0, 0.8, 0, 0, 1.2]),
            n_candles=1,
            description="Sombra inferior longa, reversão de baixa"
        ))
        
        # Inverted Hammer
        self.templates.append(PatternTemplate(
            pattern_type=PatternType.INVERTED_HAMMER,
            signal=PatternSignal.BULLISH,
            reliability=PatternReliability.MEDIUM,
            features=np.array([0.2, 0.7, 0.1, 1.0, 1.0, 0.2, 0, 0, 1.2]),
            n_candles=1,
            description="Sombra superior longa, possível reversão"
        ))
        
        # Hanging Man (como hammer mas em topo)
        self.templates.append(PatternTemplate(
            pattern_type=PatternType.HANGING_MAN,
            signal=PatternSignal.BEARISH,
            reliability=PatternReliability.MEDIUM,
            features=np.array([0.2, 0.1, 0.7, 0.0, 1.0, 0.8, 0, 0, 1.2]),
            n_candles=1,
            description="Como hammer mas bearish"
        ))
        
        # Shooting Star
        self.templates.append(PatternTemplate(
            pattern_type=PatternType.SHOOTING_STAR,
            signal=PatternSignal.BEARISH,
            reliability=PatternReliability.HIGH,
            features=np.array([0.2, 0.7, 0.1, 0.0, 1.0, 0.2, 0, 0, 1.2]),
            n_candles=1,
            description="Sombra superior longa em topo"
        ))
        
        # Marubozu Bull (corpo grande, sem sombras)
        self.templates.append(PatternTemplate(
            pattern_type=PatternType.MARUBOZU_BULL,
            signal=PatternSignal.BULLISH,
            reliability=PatternReliability.HIGH,
            features=np.array([0.95, 0.02, 0.02, 1.0, 1.5, 0.5, 0, 0, 1.5]),
            n_candles=1,
            description="Candle grande de alta sem sombras"
        ))
        
        # Marubozu Bear
        self.templates.append(PatternTemplate(
            pattern_type=PatternType.MARUBOZU_BEAR,
            signal=PatternSignal.BEARISH,
            reliability=PatternReliability.HIGH,
            features=np.array([0.95, 0.02, 0.02, 0.0, 1.5, 0.5, 0, 0, 1.5]),
            n_candles=1,
            description="Candle grande de baixa sem sombras"
        ))
        
        # Spinning Top
        self.templates.append(PatternTemplate(
            pattern_type=PatternType.SPINNING_TOP,
            signal=PatternSignal.NEUTRAL,
            reliability=PatternReliability.LOW,
            features=np.array([0.15, 0.4, 0.4, 0.5, 0.8, 0.5, 0, 0, 0.8]),
            n_candles=1,
            description="Corpo pequeno, sombras médias"
        ))
        
        # === DOUBLE CANDLE PATTERNS ===
        
        # Bullish Engulfing
        self._add_multi_candle_pattern(
            PatternType.BULLISH_ENGULFING,
            PatternSignal.BULLISH,
            PatternReliability.HIGH,
            [
                [0.6, 0.2, 0.2, 0.0, 1.0, 0.5, 0, 0, 1.0],  # Bearish candle
                [0.8, 0.1, 0.1, 1.0, 1.2, 0.5, 0, 0, 1.3],  # Larger bullish
            ],
            "Candle de alta engolfa o de baixa"
        )
        
        # Bearish Engulfing
        self._add_multi_candle_pattern(
            PatternType.BEARISH_ENGULFING,
            PatternSignal.BEARISH,
            PatternReliability.HIGH,
            [
                [0.6, 0.2, 0.2, 1.0, 1.0, 0.5, 0, 0, 1.0],  # Bullish candle
                [0.8, 0.1, 0.1, 0.0, 1.2, 0.5, 0, 0, 1.3],  # Larger bearish
            ],
            "Candle de baixa engolfa o de alta"
        )
        
        # Piercing Line
        self._add_multi_candle_pattern(
            PatternType.PIERCING_LINE,
            PatternSignal.BULLISH,
            PatternReliability.MEDIUM,
            [
                [0.7, 0.15, 0.15, 0.0, 1.0, 0.5, 0, 0, 1.0],  # Bearish
                [0.6, 0.2, 0.2, 1.0, 1.0, 0.5, 0, 1, 1.2],    # Bullish com gap down
            ],
            "Candle de alta penetra 50%+ do anterior"
        )
        
        # Dark Cloud Cover
        self._add_multi_candle_pattern(
            PatternType.DARK_CLOUD,
            PatternSignal.BEARISH,
            PatternReliability.MEDIUM,
            [
                [0.7, 0.15, 0.15, 1.0, 1.0, 0.5, 0, 0, 1.0],  # Bullish
                [0.6, 0.2, 0.2, 0.0, 1.0, 0.5, 1, 0, 1.2],    # Bearish com gap up
            ],
            "Candle de baixa penetra 50%+ do anterior"
        )
        
        # Harami Bullish
        self._add_multi_candle_pattern(
            PatternType.HARAMI_BULL,
            PatternSignal.BULLISH,
            PatternReliability.MEDIUM,
            [
                [0.8, 0.1, 0.1, 0.0, 1.2, 0.5, 0, 0, 1.0],   # Large bearish
                [0.3, 0.3, 0.3, 1.0, 0.5, 0.5, 0, 0, 0.7],   # Small bullish inside
            ],
            "Candle pequeno dentro de candle grande"
        )
        
        # Harami Bearish
        self._add_multi_candle_pattern(
            PatternType.HARAMI_BEAR,
            PatternSignal.BEARISH,
            PatternReliability.MEDIUM,
            [
                [0.8, 0.1, 0.1, 1.0, 1.2, 0.5, 0, 0, 1.0],   # Large bullish
                [0.3, 0.3, 0.3, 0.0, 0.5, 0.5, 0, 0, 0.7],   # Small bearish inside
            ],
            "Candle pequeno dentro de candle grande"
        )
        
        # === TRIPLE CANDLE PATTERNS ===
        
        # Morning Star
        self._add_multi_candle_pattern(
            PatternType.MORNING_STAR,
            PatternSignal.BULLISH,
            PatternReliability.HIGH,
            [
                [0.7, 0.15, 0.15, 0.0, 1.0, 0.5, 0, 0, 1.0],  # Bearish
                [0.1, 0.4, 0.4, 0.5, 0.5, 0.5, 0, 1, 0.8],    # Small/Doji
                [0.7, 0.15, 0.15, 1.0, 1.0, 0.5, 1, 0, 1.2],  # Bullish
            ],
            "Estrela da manhã - reversão de baixa"
        )
        
        # Evening Star
        self._add_multi_candle_pattern(
            PatternType.EVENING_STAR,
            PatternSignal.BEARISH,
            PatternReliability.HIGH,
            [
                [0.7, 0.15, 0.15, 1.0, 1.0, 0.5, 0, 0, 1.0],  # Bullish
                [0.1, 0.4, 0.4, 0.5, 0.5, 0.5, 1, 0, 0.8],    # Small/Doji
                [0.7, 0.15, 0.15, 0.0, 1.0, 0.5, 0, 1, 1.2],  # Bearish
            ],
            "Estrela da tarde - reversão de alta"
        )
        
        # Three White Soldiers
        self._add_multi_candle_pattern(
            PatternType.THREE_WHITE_SOLDIERS,
            PatternSignal.BULLISH,
            PatternReliability.HIGH,
            [
                [0.7, 0.15, 0.15, 1.0, 1.0, 0.5, 0, 0, 1.1],
                [0.7, 0.15, 0.15, 1.0, 1.0, 0.5, 0, 0, 1.2],
                [0.7, 0.15, 0.15, 1.0, 1.0, 0.5, 0, 0, 1.3],
            ],
            "Três soldados brancos - forte alta"
        )
        
        # Three Black Crows
        self._add_multi_candle_pattern(
            PatternType.THREE_BLACK_CROWS,
            PatternSignal.BEARISH,
            PatternReliability.HIGH,
            [
                [0.7, 0.15, 0.15, 0.0, 1.0, 0.5, 0, 0, 1.1],
                [0.7, 0.15, 0.15, 0.0, 1.0, 0.5, 0, 0, 1.2],
                [0.7, 0.15, 0.15, 0.0, 1.0, 0.5, 0, 0, 1.3],
            ],
            "Três corvos negros - forte baixa"
        )
    
    def _add_multi_candle_pattern(
        self,
        pattern_type: PatternType,
        signal: PatternSignal,
        reliability: PatternReliability,
        candle_features: List[List[float]],
        description: str
    ) -> None:
        """Adiciona padrão de múltiplos candles."""
        features = np.concatenate([np.array(f) for f in candle_features])
        self.templates.append(PatternTemplate(
            pattern_type=pattern_type,
            signal=signal,
            reliability=reliability,
            features=features,
            n_candles=len(candle_features),
            description=description
        ))
    
    def add_custom_pattern(self, template: PatternTemplate) -> None:
        """Adiciona padrão customizado."""
        self.templates.append(template)
    
    def get_templates_by_candles(self, n_candles: int) -> List[PatternTemplate]:
        """Retorna templates com N candles."""
        return [t for t in self.templates if t.n_candles == n_candles]


class KNNPatternRecognizer:
    """
    Reconhecedor de padrões usando k-Nearest Neighbors.
    
    Features:
    - Reconhecimento de padrões clássicos
    - Distância ponderada
    - Múltiplos k para ensemble
    - Confiança baseada em distância
    - Histórico de detecções
    """
    
    def __init__(
        self,
        k: int = 3,
        distance_threshold: float = 0.5,
        min_confidence: float = 0.3,
    ):
        self.k = k
        self.distance_threshold = distance_threshold
        self.min_confidence = min_confidence
        
        self.feature_extractor = CandleFeatureExtractor()
        self.pattern_db = PatternDatabase()
        
        # Histórico
        self.detections_history: List[PatternMatch] = []
        
        # Métricas
        self.stats = {
            'total_scans': 0,
            'patterns_detected': 0,
            'by_type': Counter(),
            'by_signal': Counter(),
        }
    
    def _euclidean_distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calcula distância euclidiana."""
        return float(np.sqrt(np.sum((a - b) ** 2)))
    
    def _cosine_distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calcula distância de cosseno."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 1.0
        return 1 - (dot / (norm_a * norm_b))
    
    def _combined_distance(self, a: np.ndarray, b: np.ndarray) -> float:
        """Distância combinada (euclidiana + cosseno)."""
        euclid = self._euclidean_distance(a, b)
        cosine = self._cosine_distance(a, b)
        return 0.7 * euclid + 0.3 * cosine
    
    def recognize_pattern(
        self,
        df,  # DataFrame com OHLCV
        n_candles: int = 3
    ) -> List[PatternMatch]:
        """
        Reconhece padrões nos últimos N candles.
        
        Args:
            df: DataFrame com OHLCV
            n_candles: Número de candles a analisar
            
        Returns:
            Lista de padrões detectados ordenados por confiança
        """
        self.stats['total_scans'] += 1
        
        if len(df) < n_candles:
            return []
        
        # Extrai features
        features = self.feature_extractor.extract_sequence(df, n_candles)
        
        # Normaliza
        features_norm = features / (np.linalg.norm(features) + 1e-10)
        
        # Busca k vizinhos mais próximos para cada tamanho de padrão
        all_matches = []
        
        for candle_count in [1, 2, 3]:
            if candle_count > n_candles:
                continue
            
            templates = self.pattern_db.get_templates_by_candles(candle_count)
            
            for template in templates:
                # Ajusta features se necessário
                if candle_count < n_candles:
                    # Usa apenas os últimos N candles
                    template_features = template.features
                    start_idx = (n_candles - candle_count) * 9
                    compare_features = features[start_idx:]
                else:
                    template_features = template.features
                    compare_features = features
                
                # Normaliza template
                template_norm = template_features / (np.linalg.norm(template_features) + 1e-10)
                
                # Calcula distância
                if len(template_norm) != len(compare_features):
                    continue
                    
                distance = self._combined_distance(compare_features, template_norm)
                
                # Verifica threshold
                if distance < self.distance_threshold:
                    # Calcula confiança (inverso da distância)
                    confidence = max(0, 1 - distance)
                    
                    if confidence >= self.min_confidence:
                        match = PatternMatch(
                            pattern_type=template.pattern_type,
                            signal=template.signal,
                            confidence=confidence,
                            reliability=template.reliability,
                            distance=distance,
                            candles_used=candle_count,
                            start_index=len(df) - candle_count,
                            features={
                                'body_size': float(features[-9]),
                                'upper_shadow': float(features[-8]),
                                'lower_shadow': float(features[-7]),
                            }
                        )
                        all_matches.append(match)
        
        # Ordena por confiança e remove duplicatas
        all_matches.sort(key=lambda x: x.confidence, reverse=True)
        
        # Filtra padrões únicos (mantém o de maior confiança)
        seen_patterns = set()
        unique_matches = []
        for match in all_matches:
            if match.pattern_type not in seen_patterns:
                seen_patterns.add(match.pattern_type)
                unique_matches.append(match)
                
                # Atualiza estatísticas
                self.stats['patterns_detected'] += 1
                self.stats['by_type'][match.pattern_type.value] += 1
                self.stats['by_signal'][match.signal.value] += 1
        
        # Histórico
        self.detections_history.extend(unique_matches)
        
        return unique_matches
    
    def scan_all_patterns(self, df) -> Dict[str, List[PatternMatch]]:
        """
        Escaneia todos os padrões possíveis.
        
        Returns:
            Dict com padrões por sinal (bullish, bearish, neutral)
        """
        results = {
            'bullish': [],
            'bearish': [],
            'neutral': [],
        }
        
        # Escaneia com diferentes tamanhos
        for n in [1, 2, 3]:
            matches = self.recognize_pattern(df, n)
            for match in matches:
                results[match.signal.value].append(match)
        
        # Remove duplicatas entre diferentes scans
        for signal in results:
            seen = set()
            unique = []
            for m in results[signal]:
                if m.pattern_type not in seen:
                    seen.add(m.pattern_type)
                    unique.append(m)
            results[signal] = sorted(unique, key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def get_dominant_signal(self, df) -> Tuple[PatternSignal, float, List[PatternMatch]]:
        """
        Determina o sinal dominante baseado em todos os padrões.
        
        Returns:
            (signal, confidence, matches)
        """
        results = self.scan_all_patterns(df)
        
        # Pontuação ponderada
        bullish_score = sum(m.confidence for m in results['bullish'])
        bearish_score = sum(m.confidence for m in results['bearish'])
        neutral_score = sum(m.confidence for m in results['neutral'])
        
        total = bullish_score + bearish_score + neutral_score + 1e-10
        
        if bullish_score > bearish_score and bullish_score > neutral_score:
            return PatternSignal.BULLISH, bullish_score / total, results['bullish']
        elif bearish_score > bullish_score and bearish_score > neutral_score:
            return PatternSignal.BEARISH, bearish_score / total, results['bearish']
        else:
            return PatternSignal.NEUTRAL, neutral_score / total, results['neutral']
    
    def add_custom_template(
        self,
        pattern_name: str,
        signal: str,
        features: np.ndarray,
        reliability: str = "medium"
    ) -> None:
        """
        Adiciona template customizado ao banco de dados.
        
        Útil para online learning de novos padrões.
        """
        n_candles = len(features) // 9
        
        self.pattern_db.add_custom_pattern(PatternTemplate(
            pattern_type=PatternType.UNKNOWN,  # Custom
            signal=PatternSignal[signal.upper()],
            reliability=PatternReliability[reliability.upper()],
            features=features,
            n_candles=n_candles,
            description=f"Custom pattern: {pattern_name}"
        ))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do reconhecedor."""
        return {
            'total_scans': self.stats['total_scans'],
            'patterns_detected': self.stats['patterns_detected'],
            'by_type': dict(self.stats['by_type']),
            'by_signal': dict(self.stats['by_signal']),
            'templates_count': len(self.pattern_db.templates),
            'history_size': len(self.detections_history),
        }
