"""
VIRTUS Master Technical Analyzer
=================================

Motor central de análise técnica que integra todos os
módulos especializados em uma análise unificada.

Combina:
- Market Structure (BOS, CHoCH, Swing Points)
- Smart Money Concepts (Order Blocks, FVG, Liquidity)
- Volume Analysis (Profile, VSA, Delta)
- Multi-Timeframe Analysis
- Divergence Detection
- Fibonacci Analysis
- Harmonic Patterns
- Advanced Indicators (Ichimoku, VWAP, Pivots, Supertrend)
- Correlation Analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
import logging

from .technical.market_structure import MarketStructureAnalyzer
from .institutional.smart_money import SmartMoneyAnalyzer
from .volume.volume_analyzer import VolumeAnalyzer
from .market.mtf_analyzer import MultiTimeframeAnalyzer
from .technical.divergence_detector import DivergenceDetector
from .technical.fibonacci_analyzer import FibonacciAnalyzer
from .technical.harmonic_patterns import HarmonicPatternDetector
from .technical.advanced_indicators import AdvancedIndicators
from .correlation.correlation_analyzer import CorrelationAnalyzer

# ML Vision Analyzer (opcional - não bloqueia se não disponível)
try:
    from ..ml.models.vision import VirtusVisionAnalyzer
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    VirtusVisionAnalyzer = None


class MarketBias(Enum):
    """Viés de mercado."""
    STRONG_BULLISH = auto()
    BULLISH = auto()
    NEUTRAL = auto()
    BEARISH = auto()
    STRONG_BEARISH = auto()


class SignalQuality(Enum):
    """Qualidade do sinal."""
    A_PLUS = auto()   # Melhor setup possível
    A = auto()        # Excelente
    B = auto()        # Bom
    C = auto()        # Aceitável
    D = auto()        # Fraco
    INVALID = auto()  # Não operar


class TradeDirection(Enum):
    """Direção do trade."""
    LONG = auto()
    SHORT = auto()
    NONE = auto()


@dataclass
class KeyLevel:
    """Um nível chave identificado."""
    price: float
    type: str  # 'support', 'resistance', 'pivot', 'fib', 'ob', 'fvg', etc.
    strength: float  # 0 a 1
    source: str  # Módulo que identificou
    description: str


@dataclass
class TradeSetup:
    """Um setup de trade identificado."""
    direction: TradeDirection
    entry_zone: Tuple[float, float]  # (low, high)
    stop_loss: float
    target_1: float
    target_2: float
    target_3: float
    risk_reward: float
    quality: SignalQuality
    confidence: float
    reasons: List[str]
    confluences: int  # Número de confluências


@dataclass
class MasterAnalysisResult:
    """Resultado da análise master."""
    symbol: str
    timeframe: str
    timestamp: datetime
    current_price: float
    
    # Viés geral
    bias: MarketBias
    bias_score: float  # -1 a +1
    trend: str  # 'up', 'down', 'sideways'
    trend_strength: float  # 0 a 1
    
    # Níveis chave consolidados
    key_supports: List[KeyLevel]
    key_resistances: List[KeyLevel]
    
    # Setup atual (se houver)
    current_setup: Optional[TradeSetup]
    
    # Componentes individuais (para detalhes)
    market_structure: Dict[str, Any]
    smart_money: Dict[str, Any]
    volume: Dict[str, Any]
    mtf: Dict[str, Any]
    divergences: Dict[str, Any]
    fibonacci: Dict[str, Any]
    harmonics: Dict[str, Any]
    indicators: Dict[str, Any]
    correlations: Dict[str, Any]
    
    # Resumo textual
    summary: str
    alerts: List[str]


class MasterTechnicalAnalyzer:
    """
    Motor central de análise técnica.
    
    Integra todos os módulos especializados e produz
    uma análise unificada com recomendações acionáveis.
    """
    
    def __init__(self, logger: logging.Logger = None, use_vision: bool = True):
        self.logger = logger or logging.getLogger(__name__)
        
        # Inicializa todos os analisadores
        self.market_structure = MarketStructureAnalyzer()
        self.smart_money = SmartMoneyAnalyzer()
        self.volume = VolumeAnalyzer()
        self.mtf = MultiTimeframeAnalyzer()
        self.divergence = DivergenceDetector()
        self.fibonacci = FibonacciAnalyzer()
        self.harmonics = HarmonicPatternDetector()
        self.indicators = AdvancedIndicators()
        self.correlations = CorrelationAnalyzer()
        
        # Vision Analyzer (ML - análise visual de padrões)
        self.vision = None
        self.use_vision = use_vision and VISION_AVAILABLE
        if self.use_vision:
            try:
                self.vision = VirtusVisionAnalyzer(
                    use_tensorflow=False,  # Usar apenas sklearn por padrão
                    use_pytorch=False
                )
                self.logger.info("Vision Analyzer inicializado com sucesso")
            except Exception as e:
                self.logger.warning(f"Vision Analyzer não disponível: {e}")
                self.use_vision = False
    
    def _get_trend_from_structure(self, ms_result) -> str:
        """Converte StructureType para string de trend."""
        if not ms_result:
            return 'sideways'
        
        from src.analysis.technical.market_structure import StructureType
        
        structure_to_trend = {
            StructureType.BULLISH_TREND: 'bullish',
            StructureType.BEARISH_TREND: 'bearish',
            StructureType.RANGING: 'sideways',
            StructureType.CONSOLIDATION: 'sideways',
            StructureType.BREAKOUT: ms_result.bias if ms_result.bias != 'neutral' else 'sideways',
        }
        
        return structure_to_trend.get(ms_result.structure_type, 'sideways')

    def analyze(
        self,
        symbol: str,
        df: pd.DataFrame,
        timeframe: str = 'M15',
        mtf_data: Dict[str, pd.DataFrame] = None,
        correlated_data: Dict[str, pd.DataFrame] = None,
        dxy_data: pd.DataFrame = None,
    ) -> MasterAnalysisResult:
        """
        Executa análise completa.
        
        Args:
            symbol: Símbolo sendo analisado
            df: DataFrame principal com OHLCV
            timeframe: Timeframe do df principal
            mtf_data: Dicionário com DataFrames de outros timeframes
            correlated_data: Dicionário com DataFrames de pares correlacionados
            dxy_data: DataFrame do DXY (opcional)
            
        Returns:
            MasterAnalysisResult
        """
        if df is None or len(df) < 100:
            return self._empty_result(symbol, timeframe)
        
        current_price = df['close'].values[-1]
        timestamp = datetime.now()
        
        # 1. Market Structure (to_dict sem parâmetro - usa estado interno)
        ms_result = self.market_structure.analyze(df)
        ms_dict = self.market_structure.to_dict()
        
        # 2. Smart Money Concepts (to_dict sem parâmetro - usa estado interno)
        sm_result = self.smart_money.analyze(df)
        sm_dict = self.smart_money.to_dict()
        
        # 3. Volume Analysis (to_dict com resultado)
        vol_result = self.volume.analyze(df)
        vol_dict = self.volume.to_dict(vol_result)
        
        # 4. Multi-Timeframe (se disponível)
        mtf_dict = {}
        if mtf_data:
            mtf_data[timeframe] = df  # Inclui o timeframe atual
            mtf_result = self.mtf.analyze(mtf_data)
            mtf_dict = self.mtf.to_dict(mtf_result)
        
        # 5. Divergences (to_dict com resultado)
        div_result = self.divergence.analyze(df)
        div_dict = self.divergence.to_dict(div_result)
        
        # 6. Fibonacci (to_dict com resultado)
        fib_result = self.fibonacci.analyze(df)
        fib_dict = self.fibonacci.to_dict(fib_result)
        
        # 7. Harmonic Patterns (to_dict com resultado)
        harm_result = self.harmonics.analyze(df)
        harm_dict = self.harmonics.to_dict(harm_result)
        
        # 8. Advanced Indicators (to_dict com resultado)
        ind_result = self.indicators.analyze(df)
        ind_dict = self.indicators.to_dict(ind_result)
        
        # 9. Correlations (se disponível) (to_dict com resultado)
        corr_dict = {}
        if correlated_data or dxy_data:
            corr_result = self.correlations.analyze(
                symbol, df, correlated_data, dxy_data
            )
            corr_dict = self.correlations.to_dict(corr_result)
        
        # === INTEGRAÇÃO ===
        
        # Calcula viés geral
        bias, bias_score = self._calculate_overall_bias(
            ms_result, sm_result, vol_result, mtf_dict, div_result, ind_result
        )
        
        # Determina tendência a partir do structure_type
        trend = self._get_trend_from_structure(ms_result)
        trend_strength = ms_result.trend_strength if ms_result else 0.5
        
        # Consolida níveis chave
        key_supports, key_resistances = self._consolidate_levels(
            current_price, ms_result, sm_result, fib_result, ind_result, mtf_dict
        )
        
        # Identifica setup atual
        current_setup = self._identify_setup(
            symbol, current_price, bias, bias_score,
            ms_result, sm_result, vol_result, div_result,
            fib_result, harm_result, ind_result,
            key_supports, key_resistances
        )
        
        # Gera resumo textual
        summary, alerts = self._generate_summary(
            symbol, timeframe, current_price, bias, trend, trend_strength,
            ms_result, sm_result, vol_result, div_result, harm_result,
            current_setup
        )
        
        return MasterAnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            current_price=current_price,
            bias=bias,
            bias_score=bias_score,
            trend=trend,
            trend_strength=trend_strength,
            key_supports=key_supports,
            key_resistances=key_resistances,
            current_setup=current_setup,
            market_structure=ms_dict,
            smart_money=sm_dict,
            volume=vol_dict,
            mtf=mtf_dict,
            divergences=div_dict,
            fibonacci=fib_dict,
            harmonics=harm_dict,
            indicators=ind_dict,
            correlations=corr_dict,
            summary=summary,
            alerts=alerts,
        )
    
    def _calculate_overall_bias(
        self,
        ms_result,
        sm_result,
        vol_result,
        mtf_dict: Dict,
        div_result,
        ind_result,
    ) -> Tuple[MarketBias, float]:
        """Calcula o viés geral do mercado."""
        score = 0.0
        weights = 0.0
        
        # Market Structure (peso 0.25)
        if ms_result:
            # Usa structure_type e bias do MarketStructureState
            from src.analysis.technical.market_structure import StructureType
            if ms_result.structure_type == StructureType.BULLISH_TREND:
                score += 0.25 * ms_result.trend_strength
            elif ms_result.structure_type == StructureType.BEARISH_TREND:
                score -= 0.25 * ms_result.trend_strength
            # Reforça com bias
            if ms_result.bias == 'bullish':
                score += 0.05
            elif ms_result.bias == 'bearish':
                score -= 0.05
            weights += 0.25
        
        # Smart Money (peso 0.20) - sm_result é um Dict
        if sm_result and isinstance(sm_result, dict):
            sm_bias = sm_result.get('bias', '')
            if sm_bias and 'bullish' in str(sm_bias).lower():
                score += 0.20
            elif sm_bias and 'bearish' in str(sm_bias).lower():
                score -= 0.20
            weights += 0.20
        
        # Volume (peso 0.15) - vol_result é VolumeAnalysisResult
        if vol_result and hasattr(vol_result, 'accumulation_score'):
            if vol_result.accumulation_score > 0.3:
                score += 0.15 * vol_result.accumulation_score
            elif vol_result.accumulation_score < -0.3:
                score += 0.15 * vol_result.accumulation_score
            weights += 0.15
        
        # MTF (peso 0.20)
        if mtf_dict and 'confluence' in mtf_dict:
            conf = mtf_dict['confluence']
            if conf.get('overall_bias', '').upper() in ['STRONG_BULLISH', 'BULLISH']:
                score += 0.20 * conf.get('confluence_score', 0.5)
            elif conf.get('overall_bias', '').upper() in ['STRONG_BEARISH', 'BEARISH']:
                score -= 0.20 * conf.get('confluence_score', 0.5)
            weights += 0.20
        
        # Divergences (peso 0.10)
        if div_result:
            if div_result.bias == 'bullish':
                score += 0.10
            elif div_result.bias == 'bearish':
                score -= 0.10
            weights += 0.10
        
        # Indicators (peso 0.10)
        if ind_result:
            # Ichimoku
            if ind_result.ichimoku.momentum == 'bullish':
                score += 0.05
            elif ind_result.ichimoku.momentum == 'bearish':
                score -= 0.05
            
            # Supertrend
            if ind_result.supertrend.direction == 'up':
                score += 0.05
            else:
                score -= 0.05
            
            weights += 0.10
        
        # Normaliza
        if weights > 0:
            score /= weights
        
        # Converte para enum
        if score >= 0.6:
            bias = MarketBias.STRONG_BULLISH
        elif score >= 0.2:
            bias = MarketBias.BULLISH
        elif score <= -0.6:
            bias = MarketBias.STRONG_BEARISH
        elif score <= -0.2:
            bias = MarketBias.BEARISH
        else:
            bias = MarketBias.NEUTRAL
        
        return bias, score
    
    def _consolidate_levels(
        self,
        current_price: float,
        ms_result,
        sm_result,
        fib_result,
        ind_result,
        mtf_dict: Dict,
    ) -> Tuple[List[KeyLevel], List[KeyLevel]]:
        """Consolida todos os níveis chave."""
        all_levels = []
        
        # Market Structure - swing_highs e swing_lows
        if ms_result:
            # Swing Highs (potenciais resistências)
            for swing in ms_result.swing_highs[-3:]:
                all_levels.append(KeyLevel(
                    price=swing.price,
                    type='resistance' if swing.price > current_price else 'support',
                    strength=0.7 if swing.swing_type.value in ['HH', 'LL'] else 0.5,
                    source='market_structure',
                    description=f"Swing {swing.swing_type.value}",
                ))
            # Swing Lows (potenciais suportes)
            for swing in ms_result.swing_lows[-3:]:
                all_levels.append(KeyLevel(
                    price=swing.price,
                    type='support' if swing.price < current_price else 'resistance',
                    strength=0.7 if swing.swing_type.value in ['HH', 'LL'] else 0.5,
                    source='market_structure',
                    description=f"Swing {swing.swing_type.value}",
                ))
        
        # Smart Money - sm_result é um Dict, precisamos acessar via keys
        if sm_result and isinstance(sm_result, dict):
            # Order Blocks - do dicionário
            obs = sm_result.get('order_blocks', {})
            bullish_obs = obs.get('bullish', [])[:2]
            bearish_obs = obs.get('bearish', [])[:2]
            
            for ob in bullish_obs:
                zone = ob.get('zone', (current_price, current_price))
                all_levels.append(KeyLevel(
                    price=(zone[0] + zone[1]) / 2 if isinstance(zone, (list, tuple)) else zone,
                    type='support',
                    strength=ob.get('strength', 0.5),
                    source='smart_money',
                    description="Order Block Bullish",
                ))
            
            for ob in bearish_obs:
                zone = ob.get('zone', (current_price, current_price))
                all_levels.append(KeyLevel(
                    price=(zone[0] + zone[1]) / 2 if isinstance(zone, (list, tuple)) else zone,
                    type='resistance',
                    strength=ob.get('strength', 0.5),
                    source='smart_money',
                    description="Order Block Bearish",
                ))
            
            # FVGs - do dicionário
            fvgs = sm_result.get('fair_value_gaps', {})
            bullish_fvgs = fvgs.get('bullish', [])[:2]
            bearish_fvgs = fvgs.get('bearish', [])[:2]
            
            for fvg in bullish_fvgs:
                zone = fvg.get('zone', (current_price, current_price))
                all_levels.append(KeyLevel(
                    price=(zone[0] + zone[1]) / 2 if isinstance(zone, (list, tuple)) else zone,
                    type='support',
                    strength=0.6,
                    source='smart_money',
                    description="FVG Bullish",
                ))
            
            for fvg in bearish_fvgs:
                zone = fvg.get('zone', (current_price, current_price))
                all_levels.append(KeyLevel(
                    price=(zone[0] + zone[1]) / 2 if isinstance(zone, (list, tuple)) else zone,
                    type='resistance',
                    strength=0.6,
                    source='smart_money',
                    description="FVG Bearish",
                ))
        
        # Fibonacci
        if fib_result:
            if fib_result.nearest_support:
                all_levels.append(KeyLevel(
                    price=fib_result.nearest_support,
                    type='support',
                    strength=0.8,
                    source='fibonacci',
                    description="Fibonacci Support",
                ))
            
            if fib_result.nearest_resistance:
                all_levels.append(KeyLevel(
                    price=fib_result.nearest_resistance,
                    type='resistance',
                    strength=0.8,
                    source='fibonacci',
                    description="Fibonacci Resistance",
                ))
            
            # Golden Zone
            if fib_result.golden_zone:
                center = (fib_result.golden_zone[0] + fib_result.golden_zone[1]) / 2
                all_levels.append(KeyLevel(
                    price=center,
                    type='support' if center < current_price else 'resistance',
                    strength=0.9,
                    source='fibonacci',
                    description="Golden Zone (0.618-0.786)",
                ))
        
        # Indicators - Pivots
        if ind_result and ind_result.pivots:
            std_pivots = ind_result.pivots.get('standard')
            if std_pivots:
                all_levels.append(KeyLevel(
                    price=std_pivots.pivot,
                    type='pivot',
                    strength=0.75,
                    source='indicators',
                    description="Daily Pivot",
                ))
                
                if std_pivots.s1 < current_price:
                    all_levels.append(KeyLevel(
                        price=std_pivots.s1,
                        type='support',
                        strength=0.7,
                        source='indicators',
                        description="Pivot S1",
                    ))
                
                if std_pivots.r1 > current_price:
                    all_levels.append(KeyLevel(
                        price=std_pivots.r1,
                        type='resistance',
                        strength=0.7,
                        source='indicators',
                        description="Pivot R1",
                    ))
        
        # Indicators - Ichimoku Cloud
        if ind_result and ind_result.ichimoku:
            all_levels.append(KeyLevel(
                price=ind_result.ichimoku.cloud_top,
                type='resistance',
                strength=0.7,
                source='indicators',
                description="Ichimoku Cloud Top",
            ))
            all_levels.append(KeyLevel(
                price=ind_result.ichimoku.cloud_bottom,
                type='support',
                strength=0.7,
                source='indicators',
                description="Ichimoku Cloud Bottom",
            ))
        
        # VWAP
        if ind_result and ind_result.vwap:
            all_levels.append(KeyLevel(
                price=ind_result.vwap.vwap,
                type='pivot',
                strength=0.65,
                source='indicators',
                description="VWAP",
            ))
        
        # Separa suportes e resistências
        supports = [l for l in all_levels if l.type == 'support' and l.price < current_price]
        resistances = [l for l in all_levels if l.type == 'resistance' and l.price > current_price]
        
        # Ordena por proximidade e agrupa similares
        supports = sorted(supports, key=lambda x: current_price - x.price)[:5]
        resistances = sorted(resistances, key=lambda x: x.price - current_price)[:5]
        
        return supports, resistances
    
    def _identify_setup(
        self,
        symbol: str,
        current_price: float,
        bias: MarketBias,
        bias_score: float,
        ms_result,
        sm_result,
        vol_result,
        div_result,
        fib_result,
        harm_result,
        ind_result,
        supports: List[KeyLevel],
        resistances: List[KeyLevel],
    ) -> Optional[TradeSetup]:
        """Identifica setup de trade."""
        confluences = 0
        reasons = []
        
        # Determina direção base
        if bias in [MarketBias.STRONG_BULLISH, MarketBias.BULLISH]:
            direction = TradeDirection.LONG
        elif bias in [MarketBias.STRONG_BEARISH, MarketBias.BEARISH]:
            direction = TradeDirection.SHORT
        else:
            direction = TradeDirection.NONE
        
        if direction == TradeDirection.NONE:
            return None
        
        # Verifica confluências
        
        # 1. Market Structure
        if ms_result:
            ms_trend = self._get_trend_from_structure(ms_result)
            if direction == TradeDirection.LONG and ms_trend == 'bullish':
                confluences += 1
                reasons.append("Estrutura de mercado bullish")
            elif direction == TradeDirection.SHORT and ms_trend == 'bearish':
                confluences += 1
                reasons.append("Estrutura de mercado bearish")
        
        # 2. Smart Money - sm_result é um Dict
        if sm_result and isinstance(sm_result, dict):
            # Order Block próximo
            obs = sm_result.get('order_blocks', {})
            bullish_obs = obs.get('bullish', [])[:2]
            bearish_obs = obs.get('bearish', [])[:2]
            
            # Verifica OBs bullish para LONG
            if direction == TradeDirection.LONG:
                for ob in bullish_obs:
                    if not ob.get('mitigated', True):
                        confluences += 1
                        reasons.append("Order Block bullish próximo")
                        break
            # Verifica OBs bearish para SHORT
            elif direction == TradeDirection.SHORT:
                for ob in bearish_obs:
                    if not ob.get('mitigated', True):
                        confluences += 1
                        reasons.append("Order Block bearish próximo")
                        break
        
        # 3. Volume
        if vol_result:
            if vol_result.trend_confirmation:
                confluences += 1
                reasons.append("Volume confirma tendência")
            
            if vol_result.accumulation_score > 0.5 and direction == TradeDirection.LONG:
                confluences += 1
                reasons.append("Acumulação detectada")
            elif vol_result.accumulation_score < -0.5 and direction == TradeDirection.SHORT:
                confluences += 1
                reasons.append("Distribuição detectada")
        
        # 4. Divergences
        if div_result:
            if direction == TradeDirection.LONG and div_result.bias == 'bullish':
                confluences += 1
                reasons.append(f"Divergência bullish ({div_result.bullish_count} indicadores)")
            elif direction == TradeDirection.SHORT and div_result.bias == 'bearish':
                confluences += 1
                reasons.append(f"Divergência bearish ({div_result.bearish_count} indicadores)")
        
        # 5. Fibonacci
        if fib_result and fib_result.in_golden_zone:
            if direction == TradeDirection.LONG:
                confluences += 1
                reasons.append("Preço na Golden Zone (0.618-0.786)")
        
        # 6. Harmonic Patterns
        if harm_result and harm_result.best_pattern:
            bp = harm_result.best_pattern
            if direction == TradeDirection.LONG and bp.direction.name == 'BULLISH':
                confluences += 1
                reasons.append(f"Padrão harmônico {bp.type.name} bullish")
            elif direction == TradeDirection.SHORT and bp.direction.name == 'BEARISH':
                confluences += 1
                reasons.append(f"Padrão harmônico {bp.type.name} bearish")
        
        # 7. Ichimoku
        if ind_result:
            ich = ind_result.ichimoku
            if direction == TradeDirection.LONG:
                if ich.price_vs_cloud == 'above' and ich.tk_cross == 'bullish':
                    confluences += 1
                    reasons.append("Ichimoku bullish")
            elif direction == TradeDirection.SHORT:
                if ich.price_vs_cloud == 'below' and ich.tk_cross == 'bearish':
                    confluences += 1
                    reasons.append("Ichimoku bearish")
        
        # 8. Supertrend
        if ind_result:
            st = ind_result.supertrend
            if direction == TradeDirection.LONG and st.direction == 'up':
                if st.trend_changed:
                    confluences += 2
                    reasons.append("Supertrend virou para compra!")
                else:
                    confluences += 1
                    reasons.append("Supertrend bullish")
            elif direction == TradeDirection.SHORT and st.direction == 'down':
                if st.trend_changed:
                    confluences += 2
                    reasons.append("Supertrend virou para venda!")
                else:
                    confluences += 1
                    reasons.append("Supertrend bearish")
        
        # Se não há confluências suficientes
        if confluences < 3:
            return None
        
        # Calcula níveis de entrada/saída
        atr = ind_result.atr if ind_result else current_price * 0.001
        
        if direction == TradeDirection.LONG:
            entry_low = current_price - (atr * 0.5)
            entry_high = current_price + (atr * 0.3)
            
            # Stop no suporte mais próximo ou ATR
            if supports:
                stop_loss = supports[0].price - (atr * 0.5)
            else:
                stop_loss = current_price - (atr * 2)
            
            # Targets
            risk = current_price - stop_loss
            target_1 = current_price + (risk * 1.5)
            target_2 = current_price + (risk * 2.5)
            target_3 = current_price + (risk * 4)
            
            if resistances:
                target_1 = min(target_1, resistances[0].price)
        else:
            entry_low = current_price - (atr * 0.3)
            entry_high = current_price + (atr * 0.5)
            
            if resistances:
                stop_loss = resistances[0].price + (atr * 0.5)
            else:
                stop_loss = current_price + (atr * 2)
            
            risk = stop_loss - current_price
            target_1 = current_price - (risk * 1.5)
            target_2 = current_price - (risk * 2.5)
            target_3 = current_price - (risk * 4)
            
            if supports:
                target_1 = max(target_1, supports[0].price)
        
        # Risk/Reward
        risk_val = abs(current_price - stop_loss)
        reward = abs(target_2 - current_price)
        rr = reward / risk_val if risk_val > 0 else 0
        
        # Qualidade do setup
        if confluences >= 7 and rr >= 2.5:
            quality = SignalQuality.A_PLUS
            confidence = 0.9
        elif confluences >= 5 and rr >= 2:
            quality = SignalQuality.A
            confidence = 0.8
        elif confluences >= 4 and rr >= 1.5:
            quality = SignalQuality.B
            confidence = 0.7
        elif confluences >= 3:
            quality = SignalQuality.C
            confidence = 0.6
        else:
            quality = SignalQuality.D
            confidence = 0.5
        
        return TradeSetup(
            direction=direction,
            entry_zone=(entry_low, entry_high),
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            risk_reward=rr,
            quality=quality,
            confidence=confidence,
            reasons=reasons,
            confluences=confluences,
        )
    
    def _generate_summary(
        self,
        symbol: str,
        timeframe: str,
        current_price: float,
        bias: MarketBias,
        trend: str,
        trend_strength: float,
        ms_result,
        sm_result,
        vol_result,
        div_result,
        harm_result,
        setup: Optional[TradeSetup],
    ) -> Tuple[str, List[str]]:
        """Gera resumo textual da análise."""
        alerts = []
        
        # Bias text
        bias_text = {
            MarketBias.STRONG_BULLISH: "FORTEMENTE BULLISH 🟢🟢",
            MarketBias.BULLISH: "BULLISH 🟢",
            MarketBias.NEUTRAL: "NEUTRO ⚪",
            MarketBias.BEARISH: "BEARISH 🔴",
            MarketBias.STRONG_BEARISH: "FORTEMENTE BEARISH 🔴🔴",
        }
        
        # Trend text
        trend_text = {
            'bullish': 'alta',
            'bearish': 'baixa',
            'sideways': 'lateral',
        }
        
        lines = []
        lines.append(f"📊 **{symbol} ({timeframe})** @ {current_price:.5f}")
        lines.append(f"")
        lines.append(f"**Viés:** {bias_text.get(bias, 'INDEFINIDO')}")
        lines.append(f"**Tendência:** {trend_text.get(trend, trend).capitalize()} "
                    f"(força: {trend_strength*100:.0f}%)")
        
        # Market Structure highlights
        if ms_result:
            if ms_result.recent_breaks:
                sb = ms_result.recent_breaks[-1]
                lines.append(f"**Estrutura:** Último {sb.break_type.name} em {sb.break_price:.5f}")
        
        # Smart Money highlights - sm_result é Dict
        if sm_result and isinstance(sm_result, dict):
            obs = sm_result.get('order_blocks', {})
            bullish_obs = obs.get('bullish', [])
            bearish_obs = obs.get('bearish', [])
            if bullish_obs:
                ob = bullish_obs[0]
                zone = ob.get('zone', (0, 0))
                lines.append(f"**Order Block:** Bullish em {zone[0]:.2f}-{zone[1]:.2f}")
            elif bearish_obs:
                ob = bearish_obs[0]
                zone = ob.get('zone', (0, 0))
                lines.append(f"**Order Block:** Bearish em {zone[0]:.2f}-{zone[1]:.2f}")
        
        # Volume highlights
        if vol_result:
            if vol_result.volume_ratio > 1.5:
                lines.append(f"**Volume:** {vol_result.volume_ratio:.1f}x acima da média")
                alerts.append("⚠️ Volume alto detectado")
        
        # Divergence alerts
        if div_result and div_result.actionable:
            if div_result.strongest:
                alerts.append(
                    f"🔔 Divergência {div_result.strongest.type.name} "
                    f"({div_result.strongest.indicator})"
                )
        
        # Harmonic alerts
        if harm_result and harm_result.best_pattern:
            bp = harm_result.best_pattern
            alerts.append(
                f"📐 Padrão {bp.type.name} {bp.direction.name} "
                f"(confiança: {bp.confidence*100:.0f}%)"
            )
        
        # Setup
        lines.append("")
        if setup:
            dir_text = "COMPRA 🟢" if setup.direction == TradeDirection.LONG else "VENDA 🔴"
            lines.append(f"**SETUP {setup.quality.name}:** {dir_text}")
            lines.append(f"• Entrada: {setup.entry_zone[0]:.5f} - {setup.entry_zone[1]:.5f}")
            lines.append(f"• Stop: {setup.stop_loss:.5f}")
            lines.append(f"• TP1: {setup.target_1:.5f}")
            lines.append(f"• TP2: {setup.target_2:.5f}")
            lines.append(f"• R:R: 1:{setup.risk_reward:.1f}")
            lines.append(f"• Confluências: {setup.confluences}")
            lines.append("")
            lines.append("**Razões:**")
            for reason in setup.reasons[:5]:
                lines.append(f"  ✓ {reason}")
        else:
            lines.append("**SETUP:** Nenhum setup válido no momento")
            lines.append("Aguardar alinhamento de confluências")
        
        summary = "\n".join(lines)
        
        return summary, alerts
    
    def _empty_result(self, symbol: str, timeframe: str) -> MasterAnalysisResult:
        """Retorna resultado vazio."""
        return MasterAnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(),
            current_price=0,
            bias=MarketBias.NEUTRAL,
            bias_score=0,
            trend='sideways',
            trend_strength=0,
            key_supports=[],
            key_resistances=[],
            current_setup=None,
            market_structure={},
            smart_money={},
            volume={},
            mtf={},
            divergences={},
            fibonacci={},
            harmonics={},
            indicators={},
            correlations={},
            summary="Dados insuficientes para análise",
            alerts=["⚠️ Dados insuficientes"],
        )
    
    def to_dict(self, result: MasterAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        supports_list = [
            {
                'price': round(s.price, 5),
                'type': s.type,
                'strength': round(s.strength, 2),
                'source': s.source,
                'description': s.description,
            }
            for s in result.key_supports
        ]
        
        resistances_list = [
            {
                'price': round(r.price, 5),
                'type': r.type,
                'strength': round(r.strength, 2),
                'source': r.source,
                'description': r.description,
            }
            for r in result.key_resistances
        ]
        
        setup_dict = None
        if result.current_setup:
            s = result.current_setup
            setup_dict = {
                'direction': s.direction.name,
                'entry_zone': {
                    'low': round(s.entry_zone[0], 5),
                    'high': round(s.entry_zone[1], 5),
                },
                'stop_loss': round(s.stop_loss, 5),
                'target_1': round(s.target_1, 5),
                'target_2': round(s.target_2, 5),
                'target_3': round(s.target_3, 5),
                'risk_reward': round(s.risk_reward, 2),
                'quality': s.quality.name,
                'confidence': round(s.confidence, 2),
                'reasons': s.reasons,
                'confluences': s.confluences,
            }
        
        return {
            'symbol': result.symbol,
            'timeframe': result.timeframe,
            'timestamp': result.timestamp.isoformat(),
            'current_price': round(result.current_price, 5),
            'bias': result.bias.name,
            'bias_score': round(result.bias_score, 3),
            'trend': result.trend,
            'trend_strength': round(result.trend_strength, 3),
            'key_supports': supports_list,
            'key_resistances': resistances_list,
            'current_setup': setup_dict,
            'components': {
                'market_structure': result.market_structure,
                'smart_money': result.smart_money,
                'volume': result.volume,
                'mtf': result.mtf,
                'divergences': result.divergences,
                'fibonacci': result.fibonacci,
                'harmonics': result.harmonics,
                'indicators': result.indicators,
                'correlations': result.correlations,
            },
            'summary': result.summary,
            'alerts': result.alerts,
        }

    async def analyze_full(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Análise completa a partir de market_data dict.
        
        Adaptador para integração com TradingEngine.
        
        Args:
            market_data: Dict com candles e indicadores
                - candles_h1: DataFrame H1
                - candles_m15: DataFrame M15
                - indicators: Dict com indicadores
                - sentiment: Dict com sentimento
        
        Returns:
            Dict com análise completa e score
        """
        try:
            # Extrai DataFrames dos candles
            df_h1 = market_data.get('candles_h1')
            df_m15 = market_data.get('candles_m15')
            
            # Usa M15 como principal, H1 para MTF
            df = df_m15 if df_m15 is not None else df_h1
            
            if df is None or len(df) < 50:
                return {'score': 0, 'error': 'Dados insuficientes'}
            
            # Prepara MTF data
            mtf_data = {}
            if df_m15 is not None:
                mtf_data['M15'] = df_m15
            if df_h1 is not None:
                mtf_data['H1'] = df_h1
            
            # Detecta símbolo (se disponível)
            symbol = market_data.get('symbol', 'UNKNOWN')
            
            # Executa análise
            result = self.analyze(
                symbol=symbol,
                df=df,
                timeframe='M15' if df_m15 is not None else 'H1',
                mtf_data=mtf_data if mtf_data else None,
            )
            
            # Converte para dict
            analysis_dict = self.to_dict(result)
            
            # Adiciona score baseado em bias_score e trend_strength
            bias_score = result.bias_score
            trend_strength = result.trend_strength / 100  # Normaliza 0-1
            
            # Score final considera múltiplos fatores
            score = (bias_score * 0.4 + trend_strength * 0.3 + 0.3)  # Base 0.3
            
            # Ajusta por setup se houver
            if result.current_setup:
                score += result.current_setup.confidence * 0.2
            
            analysis_dict['score'] = min(1.0, score)
            
            # Adiciona regime do mercado
            analysis_dict['regime'] = {
                'type': 'trending' if trend_strength > 0.5 else 'ranging',
                'trend_strength': result.trend_strength,
            }
            
            # Adiciona volatilidade
            vol_data = result.volume or {}
            volatility_level = 'medium'
            if isinstance(vol_data, dict):
                vol_ratio = vol_data.get('volume_ratio', 1.0)
                if vol_ratio > 1.5:
                    volatility_level = 'high'
                elif vol_ratio < 0.7:
                    volatility_level = 'low'
            
            analysis_dict['volatility'] = {
                'level': volatility_level,
            }
            
            return analysis_dict
            
        except Exception as e:
            self.logger.error(f"Erro em analyze_full: {e}")
            return {'score': 0, 'error': str(e)}
