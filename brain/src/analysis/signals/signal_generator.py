"""
VIRTUS Signal Generator
========================

Gerador de sinais de trading baseado em múltiplas análises.

Features:
- Combinação ponderada de múltiplas fontes
- Detecção de conflitos entre fontes
- Score de qualidade do sinal
- Filtros por sessão de mercado
- Tracking histórico de sinais
- Pesos adaptativos baseados em performance

Classes:
- SignalGenerator: Gerador principal
- SignalComponent: Componente individual de sinal
- SignalQuality: Métricas de qualidade
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque
import asyncio

from ...core import Signal, SignalType, VirtusLogger
from ..technical.technical_analyzer import TechnicalAnalyzer, TrendDirection


class SignalSource(Enum):
    """Fonte do sinal."""
    TECHNICAL = auto()
    INSTITUTIONAL = auto()
    SENTIMENT = auto()
    ML_PREDICTION = auto()
    COMBINED = auto()


class SignalQualityLevel(Enum):
    """Nível de qualidade do sinal."""
    EXCELLENT = "excellent"  # >85%
    GOOD = "good"            # 70-85%
    MODERATE = "moderate"    # 55-70%
    LOW = "low"              # 40-55%
    POOR = "poor"            # <40%


class MarketSession(Enum):
    """Sessão de mercado."""
    ASIA = "asia"
    EUROPE = "europe"
    US = "us"
    OVERLAP = "overlap"
    CLOSED = "closed"


@dataclass
class SignalComponent:
    """Componente individual de um sinal."""
    source: SignalSource
    direction: SignalType
    strength: float  # 0-1
    confidence: float  # 0-1
    weight: float  # Peso na combinação
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def weighted_score(self) -> float:
        """Score ponderado do componente."""
        return self.strength * self.confidence * self.weight


@dataclass
class SignalQuality:
    """Métricas de qualidade de um sinal."""
    overall_score: float  # 0-100
    level: SignalQualityLevel
    agreement_ratio: float  # % de fontes concordando
    conflict_score: float  # 0-1 (0 = sem conflito)
    confidence_spread: float  # Variação na confiança das fontes
    session_quality: float  # Qualidade da sessão para o ativo
    time_quality: float  # Qualidade do horário
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_score': round(self.overall_score, 2),
            'level': self.level.value,
            'agreement_ratio': round(self.agreement_ratio, 2),
            'conflict_score': round(self.conflict_score, 2),
            'confidence_spread': round(self.confidence_spread, 2),
            'session_quality': round(self.session_quality, 2),
            'time_quality': round(self.time_quality, 2),
        }


@dataclass
class SignalHistoryEntry:
    """Entrada no histórico de sinais."""
    signal: Signal
    quality: SignalQuality
    components: List[SignalComponent]
    outcome: Optional[str] = None  # 'win', 'loss', 'breakeven', None
    pnl: Optional[float] = None


class SignalGenerator:
    """
    Gerador de sinais de trading.
    
    Combina múltiplas fontes de análise para gerar sinais.
    Inclui detecção de conflitos, scoring de qualidade e
    tracking histórico.
    
    Uso:
        generator = SignalGenerator("EURUSD")
        signal = await generator.generate(candles, sentiment=sent_data)
        if signal:
            quality = generator.get_signal_quality()
            print(f"Signal: {signal.type}, Quality: {quality.level}")
    """
    
    # Qualidade de sessão por símbolo e sessão
    SESSION_QUALITY = {
        'EURUSD': {MarketSession.EUROPE: 1.0, MarketSession.US: 0.9, MarketSession.OVERLAP: 1.0, MarketSession.ASIA: 0.5},
        'GBPUSD': {MarketSession.EUROPE: 1.0, MarketSession.US: 0.9, MarketSession.OVERLAP: 1.0, MarketSession.ASIA: 0.4},
        'XAUUSD': {MarketSession.EUROPE: 0.8, MarketSession.US: 1.0, MarketSession.OVERLAP: 1.0, MarketSession.ASIA: 0.6},
        'USDJPY': {MarketSession.EUROPE: 0.7, MarketSession.US: 0.9, MarketSession.OVERLAP: 0.9, MarketSession.ASIA: 1.0},
    }
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.logger = VirtusLogger.get_logger(f"signals.{symbol.lower()}")
        
        # Analisadores
        self.technical = TechnicalAnalyzer()
        
        # Pesos para cada fonte (adaptativos)
        self.weights = {
            SignalSource.TECHNICAL: 0.40,
            SignalSource.INSTITUTIONAL: 0.25,
            SignalSource.SENTIMENT: 0.20,
            SignalSource.ML_PREDICTION: 0.15,
        }
        
        # Pesos adaptativos baseados em performance
        self._adaptive_weights = self.weights.copy()
        self._source_performance: Dict[SignalSource, List[bool]] = {
            s: [] for s in SignalSource if s != SignalSource.COMBINED
        }
        
        # Thresholds
        self.min_confidence = 0.60
        self.min_strength = 0.50
        self.min_agreement = 2  # Mínimo de fontes concordando
        self.min_quality_score = 50  # Score mínimo de qualidade
        
        # Cache de componentes
        self._components: List[SignalComponent] = []
        
        # Última qualidade calculada
        self._last_quality: Optional[SignalQuality] = None
        
        # Histórico de sinais (últimos 100)
        self._signal_history: deque = deque(maxlen=100)
        
        # Filtros de sessão
        self._session_filter_enabled = True
        self._min_session_quality = 0.5
    
    def _get_current_session(self) -> MarketSession:
        """Determina sessão atual baseada no horário UTC."""
        utc_hour = datetime.utcnow().hour
        
        if 0 <= utc_hour < 7:
            return MarketSession.ASIA
        elif 7 <= utc_hour < 12:
            return MarketSession.EUROPE
        elif 12 <= utc_hour < 16:
            return MarketSession.OVERLAP
        elif 16 <= utc_hour < 21:
            return MarketSession.US
        else:
            return MarketSession.CLOSED
    
    def _get_session_quality(self) -> float:
        """Retorna qualidade da sessão atual para o símbolo."""
        session = self._get_current_session()
        
        if session == MarketSession.CLOSED:
            return 0.2  # Sessão fechada = baixa qualidade
        
        symbol_sessions = self.SESSION_QUALITY.get(self.symbol, {})
        return symbol_sessions.get(session, 0.7)  # Default 0.7
    
    def _get_time_quality(self) -> float:
        """Retorna qualidade do horário (evita primeiros/últimos minutos)."""
        now = datetime.utcnow()
        minute = now.minute
        
        # Evita primeiros 5 minutos de cada hora (spreads maiores)
        if minute < 5:
            return 0.6
        # Evita últimos 5 minutos de cada hora
        elif minute > 55:
            return 0.7
        
        return 1.0
    
    async def generate(
        self,
        candles: Any,
        sentiment: Optional[Dict] = None,
        institutional: Optional[Dict] = None,
        ml_prediction: Optional[Dict] = None,
    ) -> Optional[Signal]:
        """
        Gera sinal combinando múltiplas fontes.
        
        Args:
            candles: DataFrame com OHLCV
            sentiment: Dados de sentimento
            institutional: Dados institucionais (COT, etc)
            ml_prediction: Predição do modelo ML
            
        Returns:
            Signal se condições atendidas, None caso contrário
        """
        self._components = []
        self._last_quality = None
        
        # Verifica sessão se filtro ativo
        if self._session_filter_enabled:
            session_quality = self._get_session_quality()
            if session_quality < self._min_session_quality:
                self.logger.debug(f"Sessão com qualidade baixa ({session_quality}), ignorando")
                return None
        
        # 1. Análise técnica
        tech_component = await self._analyze_technical(candles)
        if tech_component:
            self._components.append(tech_component)
        
        # 2. Análise de sentimento
        if sentiment:
            sent_component = await self._analyze_sentiment(sentiment)
            if sent_component:
                self._components.append(sent_component)
        
        # 3. Análise institucional
        if institutional:
            inst_component = await self._analyze_institutional(institutional)
            if inst_component:
                self._components.append(inst_component)
        
        # 4. Predição ML
        if ml_prediction:
            ml_component = await self._analyze_ml(ml_prediction)
            if ml_component:
                self._components.append(ml_component)
        
        # 5. Calcula qualidade
        quality = self._calculate_quality()
        self._last_quality = quality
        
        # 6. Verifica se qualidade mínima atendida
        if quality.overall_score < self.min_quality_score:
            self.logger.debug(f"Qualidade insuficiente: {quality.overall_score:.1f}")
            return None
        
        # 7. Combina componentes
        signal = self._combine_signals(quality)
        
        # 8. Registra no histórico
        if signal:
            self._signal_history.append(SignalHistoryEntry(
                signal=signal,
                quality=quality,
                components=self._components.copy(),
            ))
        
        return signal
    
    def _calculate_quality(self) -> SignalQuality:
        """Calcula qualidade do potencial sinal."""
        if not self._components:
            return SignalQuality(
                overall_score=0,
                level=SignalQualityLevel.POOR,
                agreement_ratio=0,
                conflict_score=1,
                confidence_spread=0,
                session_quality=0,
                time_quality=0,
            )
        
        # 1. Agreement ratio
        buy_count = sum(1 for c in self._components if c.direction == SignalType.BUY)
        sell_count = len(self._components) - buy_count
        max_count = max(buy_count, sell_count)
        agreement_ratio = max_count / len(self._components)
        
        # 2. Conflict score (0 = sem conflito, 1 = conflito total)
        conflict_score = 1 - agreement_ratio
        
        # 3. Confidence spread (menor = mais consistente)
        confidences = [c.confidence for c in self._components]
        confidence_spread = max(confidences) - min(confidences) if confidences else 0
        
        # 4. Qualidades de sessão e tempo
        session_quality = self._get_session_quality()
        time_quality = self._get_time_quality()
        
        # 5. Score geral
        # Ponderação: agreement (40%), confidence média (25%), session (20%), time (15%)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        overall_score = (
            agreement_ratio * 40 +
            avg_confidence * 25 +
            session_quality * 20 +
            time_quality * 15 -
            conflict_score * 20 -  # Penalidade por conflito
            confidence_spread * 10  # Penalidade por inconsistência
        )
        overall_score = max(0, min(100, overall_score))
        
        # Determina nível
        if overall_score >= 85:
            level = SignalQualityLevel.EXCELLENT
        elif overall_score >= 70:
            level = SignalQualityLevel.GOOD
        elif overall_score >= 55:
            level = SignalQualityLevel.MODERATE
        elif overall_score >= 40:
            level = SignalQualityLevel.LOW
        else:
            level = SignalQualityLevel.POOR
        
        return SignalQuality(
            overall_score=overall_score,
            level=level,
            agreement_ratio=agreement_ratio,
            conflict_score=conflict_score,
            confidence_spread=confidence_spread,
            session_quality=session_quality,
            time_quality=time_quality,
        )
    
    async def _analyze_technical(self, candles: Any) -> Optional[SignalComponent]:
        """Analisa componente técnico."""
        if candles is None or len(candles) < 50:
            return None
        
        analysis = self.technical.analyze(candles)
        
        if not analysis:
            return None
        
        score = analysis.get('score', 0)
        
        # trend pode ser string ou dict
        trend_data = analysis.get('trend', {})
        if isinstance(trend_data, dict):
            trend = trend_data.get('direction', TrendDirection.NEUTRAL)
        else:
            # trend é string ('bullish'/'bearish'), converte
            if trend_data == 'bullish':
                trend = TrendDirection.UP
            elif trend_data == 'bearish':
                trend = TrendDirection.DOWN
            else:
                trend = TrendDirection.NEUTRAL
        
        signals = analysis.get('signals', [])
        
        # Determina direção
        if score > 20:
            direction = SignalType.BUY
        elif score < -20:
            direction = SignalType.SELL
        else:
            return None  # Sem sinal claro
        
        # Calcula força baseado no score
        strength = min(abs(score) / 100, 1.0)
        
        # Calcula confiança baseado na quantidade de sinais concordando
        concordant = sum(
            1 for s in signals 
            if (s.signal_type == 'buy' and direction == SignalType.BUY) or
               (s.signal_type == 'sell' and direction == SignalType.SELL)
        )
        confidence = min(concordant / max(len(signals), 1) + 0.3, 1.0)
        
        return SignalComponent(
            source=SignalSource.TECHNICAL,
            direction=direction,
            strength=strength,
            confidence=confidence,
            weight=self.weights[SignalSource.TECHNICAL],
            metadata={
                'score': score,
                'trend': trend.name if hasattr(trend, 'name') else str(trend),
                'signals_count': len(signals),
                'rsi': analysis.get('momentum', {}).get('rsi') if isinstance(analysis.get('momentum'), dict) else None,
                'macd_hist': None,  # Evita acesso aninhado que pode falhar
            }
        )
    
    async def _analyze_sentiment(self, sentiment: Dict) -> Optional[SignalComponent]:
        """Analisa componente de sentimento."""
        score = sentiment.get('score', 0)  # -1 a +1
        confidence = sentiment.get('confidence', 0.5)
        
        if abs(score) < 0.2:
            return None  # Sentimento neutro
        
        direction = SignalType.BUY if score > 0 else SignalType.SELL
        strength = abs(score)
        
        return SignalComponent(
            source=SignalSource.SENTIMENT,
            direction=direction,
            strength=strength,
            confidence=confidence,
            weight=self.weights[SignalSource.SENTIMENT],
            metadata=sentiment
        )
    
    async def _analyze_institutional(self, institutional: Dict) -> Optional[SignalComponent]:
        """Analisa componente institucional (COT, etc)."""
        # COT positioning
        cot = institutional.get('cot', {})
        net_position = cot.get('net_position', 0)
        change = cot.get('change', 0)
        
        if abs(net_position) < 1000:
            return None
        
        # Direção baseada na posição líquida
        direction = SignalType.BUY if net_position > 0 else SignalType.SELL
        
        # Força baseada na magnitude
        strength = min(abs(net_position) / 100000, 1.0)
        
        # Confiança maior se posição está aumentando na direção
        confidence = 0.5
        if (net_position > 0 and change > 0) or (net_position < 0 and change < 0):
            confidence = 0.7
        
        return SignalComponent(
            source=SignalSource.INSTITUTIONAL,
            direction=direction,
            strength=strength,
            confidence=confidence,
            weight=self.weights[SignalSource.INSTITUTIONAL],
            metadata={'cot': cot}
        )
    
    async def _analyze_ml(self, prediction: Dict) -> Optional[SignalComponent]:
        """Analisa componente de ML."""
        pred_direction = prediction.get('direction')
        probability = prediction.get('probability', 0.5)
        
        if not pred_direction or probability < 0.6:
            return None
        
        direction = SignalType.BUY if pred_direction == 'up' else SignalType.SELL
        
        return SignalComponent(
            source=SignalSource.ML_PREDICTION,
            direction=direction,
            strength=probability,
            confidence=probability,
            weight=self.weights[SignalSource.ML_PREDICTION],
            metadata=prediction
        )
    
    def _combine_signals(self, quality: SignalQuality) -> Optional[Signal]:
        """Combina componentes em sinal final."""
        if not self._components:
            return None
        
        # Conta direções usando pesos adaptativos
        buy_score = 0.0
        sell_score = 0.0
        buy_count = 0
        sell_count = 0
        
        for comp in self._components:
            adaptive_weight = self._adaptive_weights.get(comp.source, comp.weight)
            weighted_score = comp.strength * comp.confidence * adaptive_weight
            
            if comp.direction == SignalType.BUY:
                buy_score += weighted_score
                buy_count += 1
            else:
                sell_score += weighted_score
                sell_count += 1
        
        # Determina direção final
        if buy_score > sell_score and buy_count >= self.min_agreement:
            direction = SignalType.BUY
            total_score = buy_score
            agreement = buy_count
        elif sell_score > buy_score and sell_count >= self.min_agreement:
            direction = SignalType.SELL
            total_score = sell_score
            agreement = sell_count
        else:
            return None  # Sem consenso suficiente
        
        # Calcula força e confiança finais
        strength = min(total_score * 2, 1.0)  # Normaliza
        
        # Confiança ajustada pela qualidade
        base_confidence = (agreement / len(self._components)) * min(total_score + 0.3, 1.0)
        confidence = base_confidence * (quality.overall_score / 100)
        
        # Verifica thresholds
        if strength < self.min_strength or confidence < self.min_confidence:
            return None
        
        # Cria sinal
        return Signal(
            symbol=self.symbol,
            type=direction,
            strength=strength,
            confidence=confidence,
            source="combined",
            timestamp=datetime.now(),
            metadata={
                'components': [
                    {
                        'source': c.source.name,
                        'direction': c.direction.name,
                        'strength': round(c.strength, 3),
                        'confidence': round(c.confidence, 3),
                    }
                    for c in self._components
                ],
                'agreement': agreement,
                'total_sources': len(self._components),
                'quality': quality.to_dict(),
                'session': self._get_current_session().value,
            }
        )
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Retorna resumo da última análise."""
        return {
            'symbol': self.symbol,
            'components': [
                {
                    'source': c.source.name,
                    'direction': c.direction.name,
                    'strength': round(c.strength, 3),
                    'confidence': round(c.confidence, 3),
                    'metadata': c.metadata,
                }
                for c in self._components
            ],
            'quality': self._last_quality.to_dict() if self._last_quality else None,
            'session': self._get_current_session().value,
            'timestamp': datetime.now().isoformat(),
        }
    
    def get_signal_quality(self) -> Optional[SignalQuality]:
        """Retorna qualidade do último sinal calculado."""
        return self._last_quality
    
    # ========================================================================
    # ADAPTIVE WEIGHTS
    # ========================================================================
    
    def record_outcome(self, signal_id: str, outcome: str, pnl: float = 0) -> None:
        """
        Registra resultado de um sinal para ajuste adaptativo.
        
        Args:
            signal_id: ID do sinal (timestamp)
            outcome: 'win', 'loss', 'breakeven'
            pnl: P&L do trade
        """
        # Encontra entrada no histórico
        for entry in self._signal_history:
            if entry.signal.timestamp.isoformat() == signal_id:
                entry.outcome = outcome
                entry.pnl = pnl
                
                # Registra performance por fonte
                is_win = outcome == 'win'
                for comp in entry.components:
                    self._source_performance[comp.source].append(is_win)
                    # Mantém últimos 50 registros
                    if len(self._source_performance[comp.source]) > 50:
                        self._source_performance[comp.source].pop(0)
                
                # Atualiza pesos
                self._update_adaptive_weights()
                break
    
    def _update_adaptive_weights(self) -> None:
        """Atualiza pesos adaptativos baseado em performance."""
        total_score = 0
        scores = {}
        
        for source, outcomes in self._source_performance.items():
            if len(outcomes) < 10:
                # Pouco histórico, usa peso original
                scores[source] = self.weights.get(source, 0.25)
            else:
                # Win rate como score
                win_rate = sum(outcomes) / len(outcomes)
                scores[source] = win_rate * self.weights.get(source, 0.25)
            
            total_score += scores[source]
        
        # Normaliza para somar 1
        if total_score > 0:
            for source in scores:
                self._adaptive_weights[source] = scores[source] / total_score
    
    def get_adaptive_weights(self) -> Dict[str, float]:
        """Retorna pesos adaptativos atuais."""
        return {s.name: round(w, 3) for s, w in self._adaptive_weights.items()}
    
    # ========================================================================
    # HISTÓRICO E ESTATÍSTICAS
    # ========================================================================
    
    def get_signal_history(
        self, 
        limit: int = 20,
        outcome_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna histórico de sinais.
        
        Args:
            limit: Número máximo de entradas
            outcome_filter: Filtrar por outcome ('win', 'loss', None)
        """
        history = list(self._signal_history)
        
        if outcome_filter:
            history = [e for e in history if e.outcome == outcome_filter]
        
        return [
            {
                'timestamp': e.signal.timestamp.isoformat(),
                'direction': e.signal.type.name,
                'strength': round(e.signal.strength, 3),
                'confidence': round(e.signal.confidence, 3),
                'quality': e.quality.level.value,
                'quality_score': round(e.quality.overall_score, 1),
                'outcome': e.outcome,
                'pnl': e.pnl,
            }
            for e in list(history)[-limit:]
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de sinais."""
        completed = [e for e in self._signal_history if e.outcome is not None]
        
        if not completed:
            return {
                'total_signals': len(self._signal_history),
                'completed_signals': 0,
                'win_rate': 0,
                'avg_quality': 0,
                'by_source': {},
            }
        
        wins = sum(1 for e in completed if e.outcome == 'win')
        total_pnl = sum(e.pnl or 0 for e in completed)
        avg_quality = sum(e.quality.overall_score for e in completed) / len(completed)
        
        # Performance por nível de qualidade
        by_quality = {}
        for level in SignalQualityLevel:
            level_signals = [e for e in completed if e.quality.level == level]
            if level_signals:
                level_wins = sum(1 for e in level_signals if e.outcome == 'win')
                by_quality[level.value] = {
                    'count': len(level_signals),
                    'win_rate': round(level_wins / len(level_signals), 2),
                }
        
        return {
            'total_signals': len(self._signal_history),
            'completed_signals': len(completed),
            'win_rate': round(wins / len(completed), 2) if completed else 0,
            'total_pnl': round(total_pnl, 2),
            'avg_quality': round(avg_quality, 1),
            'adaptive_weights': self.get_adaptive_weights(),
            'by_quality': by_quality,
        }
    
    # ========================================================================
    # CONFIGURAÇÃO
    # ========================================================================
    
    def set_session_filter(self, enabled: bool, min_quality: float = 0.5) -> None:
        """
        Configura filtro de sessão.
        
        Args:
            enabled: Ativar/desativar filtro
            min_quality: Qualidade mínima de sessão (0-1)
        """
        self._session_filter_enabled = enabled
        self._min_session_quality = min_quality
    
    def set_thresholds(
        self,
        min_confidence: Optional[float] = None,
        min_strength: Optional[float] = None,
        min_agreement: Optional[int] = None,
        min_quality: Optional[int] = None,
    ) -> None:
        """
        Configura thresholds do gerador.
        
        Args:
            min_confidence: Confiança mínima (0-1)
            min_strength: Força mínima (0-1)
            min_agreement: Mínimo de fontes concordando
            min_quality: Score de qualidade mínimo (0-100)
        """
        if min_confidence is not None:
            self.min_confidence = max(0, min(1, min_confidence))
        if min_strength is not None:
            self.min_strength = max(0, min(1, min_strength))
        if min_agreement is not None:
            self.min_agreement = max(1, min_agreement)
        if min_quality is not None:
            self.min_quality_score = max(0, min(100, min_quality))
