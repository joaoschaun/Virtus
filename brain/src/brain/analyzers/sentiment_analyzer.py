"""
VIRTUS Sentiment Analyzer
==========================

Analisa sentimento de mercado agregando múltiplas fontes.
Gera score consolidado por símbolo e período.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
from collections import defaultdict

try:
    from ...core import VirtusLogger
except ImportError:
    from core import VirtusLogger


class SentimentSource(Enum):
    """Fontes de sentimento."""
    NEWS = "news"
    SOCIAL = "social"
    TECHNICAL = "technical"
    COT = "cot"                  # Commitment of Traders
    OPTIONS = "options"
    POSITIONING = "positioning"


class MarketMood(Enum):
    """Humor geral do mercado."""
    EXTREME_FEAR = -2
    FEAR = -1
    NEUTRAL = 0
    GREED = 1
    EXTREME_GREED = 2


@dataclass
class SentimentReading:
    """Leitura de sentimento individual."""
    source: SentimentSource
    symbol: str
    timestamp: datetime
    
    # Score normalizado (-100 a +100)
    score: float
    
    # Confiança (0 a 1)
    confidence: float = 0.5
    
    # Dados da fonte
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source': self.source.value,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'score': round(self.score, 2),
            'confidence': round(self.confidence, 3),
        }


@dataclass
class CompositeSentiment:
    """Sentimento composto de múltiplas fontes."""
    symbol: str
    timestamp: datetime
    
    # Score agregado (-100 a +100)
    composite_score: float = 0.0
    
    # Interpretação
    mood: MarketMood = MarketMood.NEUTRAL
    bias: str = "neutral"  # bullish, bearish, neutral
    
    # Confiança agregada
    confidence: float = 0.5
    
    # Por fonte
    source_scores: Dict[str, float] = field(default_factory=dict)
    
    # Mudanças
    change_1h: float = 0.0
    change_24h: float = 0.0
    
    # Divergências
    divergences: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'composite_score': round(self.composite_score, 2),
            'mood': self.mood.name,
            'bias': self.bias,
            'confidence': round(self.confidence, 3),
            'source_scores': {k: round(v, 2) for k, v in self.source_scores.items()},
            'change_1h': round(self.change_1h, 2),
            'change_24h': round(self.change_24h, 2),
            'divergences': self.divergences,
        }


@dataclass
class SentimentConfig:
    """Configuração do analisador."""
    # Pesos por fonte
    source_weights: Dict[SentimentSource, float] = field(default_factory=lambda: {
        SentimentSource.NEWS: 0.25,
        SentimentSource.TECHNICAL: 0.30,
        SentimentSource.COT: 0.20,
        SentimentSource.POSITIONING: 0.15,
        SentimentSource.SOCIAL: 0.10,
    })
    
    # Thresholds
    extreme_threshold: float = 70.0
    strong_threshold: float = 50.0
    
    # Cache
    cache_duration_minutes: int = 15


class SentimentAnalyzer:
    """
    Analisador de sentimento de mercado.
    
    Agrega sentimento de múltiplas fontes:
    - Notícias (via NewsAnalyzer)
    - Análise técnica
    - Dados de posicionamento
    - Social media
    """
    
    def __init__(self, config: Optional[SentimentConfig] = None):
        self.config = config or SentimentConfig()
        self.logger = VirtusLogger.get_logger("sentiment_analyzer")
        
        # Histórico de leituras
        self._readings: Dict[str, List[SentimentReading]] = defaultdict(list)
        
        # Cache de compostos
        self._composite_cache: Dict[str, CompositeSentiment] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        
        # Histórico para mudanças
        self._history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
    
    # ========================================================================
    # LEITURAS INDIVIDUAIS
    # ========================================================================
    
    async def add_news_sentiment(
        self,
        symbol: str,
        score: float,
        confidence: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Adiciona sentimento de notícias.
        
        Args:
            symbol: Símbolo
            score: Score (-100 a +100)
            confidence: Confiança (0 a 1)
        """
        reading = SentimentReading(
            source=SentimentSource.NEWS,
            symbol=symbol,
            timestamp=datetime.now(),
            score=self._normalize_score(score),
            confidence=confidence,
            metadata=metadata or {},
        )
        
        self._readings[symbol].append(reading)
        self._invalidate_cache(symbol)
        
        self.logger.debug(
            f"News sentiment {symbol}: {reading.score:.1f} ({confidence:.2f})"
        )
    
    async def add_technical_sentiment(
        self,
        symbol: str,
        indicators: Dict[str, float],
        confidence: float = 0.7
    ) -> None:
        """
        Adiciona sentimento de indicadores técnicos.
        
        Args:
            symbol: Símbolo
            indicators: Dict com indicadores e seus valores
                Ex: {'rsi': 75, 'macd_signal': 1, 'trend_strength': 0.8}
        """
        # Calcula score agregado dos indicadores
        score = self._calculate_technical_score(indicators)
        
        reading = SentimentReading(
            source=SentimentSource.TECHNICAL,
            symbol=symbol,
            timestamp=datetime.now(),
            score=score,
            confidence=confidence,
            metadata=indicators,
        )
        
        self._readings[symbol].append(reading)
        self._invalidate_cache(symbol)
    
    def _calculate_technical_score(self, indicators: Dict[str, float]) -> float:
        """Calcula score de indicadores técnicos."""
        score = 0.0
        count = 0
        
        # RSI (0-100 -> -100 a +100)
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            # RSI > 70 = overbought (-), < 30 = oversold (+)
            rsi_score = (50 - rsi) * 2
            score += rsi_score
            count += 1
        
        # MACD Signal (-1 a +1 -> -100 a +100)
        if 'macd_signal' in indicators:
            score += indicators['macd_signal'] * 100
            count += 1
        
        # Trend Strength (-1 a +1)
        if 'trend_strength' in indicators:
            score += indicators['trend_strength'] * 100
            count += 1
        
        # Moving Average Position
        if 'ma_position' in indicators:
            # 1 = preço acima, -1 = preço abaixo
            score += indicators['ma_position'] * 50
            count += 1
        
        # ADX (força da tendência)
        if 'adx' in indicators and 'trend_direction' in indicators:
            adx = indicators['adx']
            direction = indicators['trend_direction']  # 1 ou -1
            if adx > 25:
                score += direction * min(adx, 50)
                count += 1
        
        return self._normalize_score(score / max(1, count))
    
    async def add_cot_sentiment(
        self,
        symbol: str,
        commercial_net: float,
        non_commercial_net: float,
        change_weekly: float = 0.0
    ) -> None:
        """
        Adiciona sentimento de Commitment of Traders.
        
        Args:
            symbol: Símbolo
            commercial_net: Posição líquida dos comerciais
            non_commercial_net: Posição líquida dos especuladores
            change_weekly: Mudança semanal
        """
        # Comerciais são contrarians, especuladores seguem tendência
        # Score baseado principalmente em especuladores
        score = self._normalize_score(non_commercial_net / 1000)  # Normaliza
        
        # Ajusta se há divergência com comerciais
        if commercial_net * non_commercial_net < 0:
            # Divergência - reduz confiança
            confidence = 0.4
        else:
            confidence = 0.6
        
        reading = SentimentReading(
            source=SentimentSource.COT,
            symbol=symbol,
            timestamp=datetime.now(),
            score=score,
            confidence=confidence,
            metadata={
                'commercial_net': commercial_net,
                'non_commercial_net': non_commercial_net,
                'weekly_change': change_weekly,
            },
        )
        
        self._readings[symbol].append(reading)
        self._invalidate_cache(symbol)
    
    async def add_positioning_sentiment(
        self,
        symbol: str,
        long_percent: float,
        short_percent: float,
        source_name: str = "broker"
    ) -> None:
        """
        Adiciona sentimento de posicionamento de traders.
        
        Args:
            symbol: Símbolo
            long_percent: % de posições long
            short_percent: % de posições short
        """
        # Ratio como indicador contrarian
        # Muitos longs = sentimento extremo = possível reversão bearish
        ratio = long_percent / max(1, short_percent)
        
        # Contrarian: extremos indicam reversão
        if ratio > 2.0:  # >66% long
            score = -50 * (ratio - 1)
        elif ratio < 0.5:  # >66% short
            score = 50 * (1/ratio - 1)
        else:
            score = (long_percent - 50) * 2  # Próximo de 50/50
        
        reading = SentimentReading(
            source=SentimentSource.POSITIONING,
            symbol=symbol,
            timestamp=datetime.now(),
            score=self._normalize_score(score),
            confidence=0.5,
            metadata={
                'long_percent': long_percent,
                'short_percent': short_percent,
                'ratio': round(ratio, 2),
                'source': source_name,
            },
        )
        
        self._readings[symbol].append(reading)
        self._invalidate_cache(symbol)
    
    # ========================================================================
    # ANÁLISE COMPOSTA
    # ========================================================================
    
    async def get_composite_sentiment(
        self,
        symbol: str,
        use_cache: bool = True
    ) -> CompositeSentiment:
        """
        Obtém sentimento composto para um símbolo.
        
        Args:
            symbol: Símbolo
            use_cache: Se deve usar cache
            
        Returns:
            CompositeSentiment agregado
        """
        # Verifica cache
        if use_cache and symbol in self._composite_cache:
            expiry = self._cache_expiry.get(symbol, datetime.min)
            if datetime.now() < expiry:
                return self._composite_cache[symbol]
        
        # Obtém leituras recentes
        recent_readings = self._get_recent_readings(symbol, hours=24)
        
        if not recent_readings:
            return CompositeSentiment(
                symbol=symbol,
                timestamp=datetime.now(),
            )
        
        # Agrupa por fonte e pega mais recente de cada
        by_source: Dict[SentimentSource, SentimentReading] = {}
        for reading in recent_readings:
            if reading.source not in by_source or \
               reading.timestamp > by_source[reading.source].timestamp:
                by_source[reading.source] = reading
        
        # Calcula score composto ponderado
        weighted_sum = 0.0
        total_weight = 0.0
        source_scores = {}
        
        for source, reading in by_source.items():
            weight = self.config.source_weights.get(source, 0.1)
            weight *= reading.confidence  # Ajusta por confiança
            
            weighted_sum += reading.score * weight
            total_weight += weight
            source_scores[source.value] = reading.score
        
        composite_score = weighted_sum / max(0.01, total_weight)
        
        # Determina mood e bias
        mood = self._determine_mood(composite_score)
        bias = self._determine_bias(composite_score)
        
        # Detecta divergências
        divergences = self._detect_divergences(by_source)
        
        # Calcula confiança
        confidence = self._calculate_confidence(by_source, divergences)
        
        # Calcula mudanças
        change_1h = self._calculate_change(symbol, hours=1, current=composite_score)
        change_24h = self._calculate_change(symbol, hours=24, current=composite_score)
        
        composite = CompositeSentiment(
            symbol=symbol,
            timestamp=datetime.now(),
            composite_score=composite_score,
            mood=mood,
            bias=bias,
            confidence=confidence,
            source_scores=source_scores,
            change_1h=change_1h,
            change_24h=change_24h,
            divergences=divergences,
        )
        
        # Atualiza cache e histórico
        self._composite_cache[symbol] = composite
        self._cache_expiry[symbol] = datetime.now() + timedelta(
            minutes=self.config.cache_duration_minutes
        )
        self._history[symbol].append((datetime.now(), composite_score))
        
        return composite
    
    def _get_recent_readings(
        self, symbol: str, hours: int = 24
    ) -> List[SentimentReading]:
        """Obtém leituras recentes."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            r for r in self._readings.get(symbol, [])
            if r.timestamp >= cutoff
        ]
    
    def _determine_mood(self, score: float) -> MarketMood:
        """Determina humor do mercado."""
        if score >= self.config.extreme_threshold:
            return MarketMood.EXTREME_GREED
        elif score >= self.config.strong_threshold:
            return MarketMood.GREED
        elif score <= -self.config.extreme_threshold:
            return MarketMood.EXTREME_FEAR
        elif score <= -self.config.strong_threshold:
            return MarketMood.FEAR
        else:
            return MarketMood.NEUTRAL
    
    def _determine_bias(self, score: float) -> str:
        """Determina viés direcional."""
        if score > 20:
            return "bullish"
        elif score < -20:
            return "bearish"
        return "neutral"
    
    def _detect_divergences(
        self,
        by_source: Dict[SentimentSource, SentimentReading]
    ) -> List[str]:
        """Detecta divergências entre fontes."""
        divergences = []
        sources = list(by_source.items())
        
        for i, (source1, reading1) in enumerate(sources):
            for source2, reading2 in sources[i+1:]:
                # Divergência significativa
                if reading1.score * reading2.score < 0:  # Sinais opostos
                    diff = abs(reading1.score - reading2.score)
                    if diff > 50:
                        divergences.append(
                            f"{source1.value} vs {source2.value}: "
                            f"{reading1.score:.0f} vs {reading2.score:.0f}"
                        )
        
        return divergences
    
    def _calculate_confidence(
        self,
        by_source: Dict[SentimentSource, SentimentReading],
        divergences: List[str]
    ) -> float:
        """Calcula confiança no sentimento composto."""
        if not by_source:
            return 0.1
        
        # Base: média de confiança das fontes
        base_confidence = sum(r.confidence for r in by_source.values()) / len(by_source)
        
        # Penaliza por divergências
        divergence_penalty = len(divergences) * 0.1
        
        # Bonus por múltiplas fontes concordando
        scores = [r.score for r in by_source.values()]
        same_direction = all(s > 0 for s in scores) or all(s < 0 for s in scores)
        direction_bonus = 0.1 if same_direction else 0.0
        
        # Bonus por número de fontes
        sources_bonus = min(0.2, len(by_source) * 0.05)
        
        confidence = base_confidence - divergence_penalty + direction_bonus + sources_bonus
        
        return max(0.1, min(1.0, confidence))
    
    def _calculate_change(
        self,
        symbol: str,
        hours: int,
        current: float
    ) -> float:
        """Calcula mudança de sentimento."""
        history = self._history.get(symbol, [])
        if not history:
            return 0.0
        
        cutoff = datetime.now() - timedelta(hours=hours)
        old_readings = [score for ts, score in history if ts <= cutoff]
        
        if not old_readings:
            return 0.0
        
        old_score = old_readings[-1]  # Mais recente antes do cutoff
        return current - old_score
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _normalize_score(self, score: float) -> float:
        """Normaliza score para range -100 a +100."""
        return max(-100.0, min(100.0, score))
    
    def _invalidate_cache(self, symbol: str) -> None:
        """Invalida cache de um símbolo."""
        self._cache_expiry[symbol] = datetime.min
    
    async def get_all_sentiments(
        self,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, CompositeSentiment]:
        """Obtém sentimento para múltiplos símbolos."""
        symbols = symbols or ['XAUUSD', 'EURUSD', 'GBPUSD']
        
        results = {}
        for symbol in symbols:
            results[symbol] = await self.get_composite_sentiment(symbol)
        
        return results
    
    def get_extremes(self) -> Dict[str, Any]:
        """Identifica símbolos em extremos de sentimento."""
        extremes = {
            'extreme_greed': [],
            'extreme_fear': [],
            'divergent': [],
        }
        
        for symbol, composite in self._composite_cache.items():
            if composite.mood == MarketMood.EXTREME_GREED:
                extremes['extreme_greed'].append(symbol)
            elif composite.mood == MarketMood.EXTREME_FEAR:
                extremes['extreme_fear'].append(symbol)
            if composite.divergences:
                extremes['divergent'].append({
                    'symbol': symbol,
                    'divergences': composite.divergences,
                })
        
        return extremes
    
    def clear_history(self, older_than_hours: int = 48) -> int:
        """Limpa histórico antigo."""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        count = 0
        
        for symbol in list(self._readings.keys()):
            old_count = len(self._readings[symbol])
            self._readings[symbol] = [
                r for r in self._readings[symbol]
                if r.timestamp >= cutoff
            ]
            count += old_count - len(self._readings[symbol])
        
        for symbol in list(self._history.keys()):
            self._history[symbol] = [
                (ts, score) for ts, score in self._history[symbol]
                if ts >= cutoff
            ]
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do analisador."""
        total_readings = sum(len(r) for r in self._readings.values())
        
        return {
            'total_readings': total_readings,
            'symbols_tracked': len(self._readings),
            'cached_composites': len(self._composite_cache),
            'readings_by_symbol': {
                s: len(r) for s, r in self._readings.items()
            },
        }
