"""
VIRTUS Scalping Strategy
=========================

Estratégia de scalping avançada baseada em:
- Microestrutura de mercado
- Order Flow
- Spread analysis
- Liquidity detection
- Quick momentum
- Price action patterns
- Session-specific entries
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

try:
    from ...core import VirtusLogger
    from ...core.types import SignalDirection
except ImportError:
    from core import VirtusLogger
    from core.types import SignalDirection


class ScalpingSetup(Enum):
    """Tipos de setup de scalping."""
    SPREAD_COMPRESSION = "spread_compression"
    LIQUIDITY_GRAB = "liquidity_grab"
    MOMENTUM_BURST = "momentum_burst"
    ABSORPTION = "absorption"
    DELTA_DIVERGENCE = "delta_divergence"
    VWAP_BOUNCE = "vwap_bounce"
    MICROSTRUCTURE_REVERSAL = "microstructure_reversal"
    ORDER_BLOCK_TAP = "order_block_tap"
    FVG_FILL = "fvg_fill"


@dataclass
class ScalpingSignal:
    """Sinal de scalping."""
    setup: ScalpingSetup
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    expected_duration_seconds: int
    risk_reward: float
    filters_passed: List[str]
    filters_failed: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScalpingConfig:
    """Configuração da estratégia de scalping."""
    # Timeframes
    primary_tf: str = "M1"
    confirmation_tf: str = "M5"
    
    # Risk - AJUSTADO para funcionar sem bloqueios
    max_spread_pips: float = 50.0  # Spread liberado
    min_liquidity_score: float = 0.3  # Mais flexível
    max_risk_pips: float = 30.0  # Mais espaço para XAUUSD
    min_risk_reward: float = 1.2  # Aceita 1.2:1
    
    # Time filters
    trade_sessions: List[str] = field(default_factory=lambda: ["london", "new_york"])
    avoid_news_minutes: int = 15
    
    # Entry filters
    min_delta_threshold: float = 0.3
    min_absorption_ratio: float = 2.0
    min_momentum_score: float = 0.5
    
    # Targets
    target_pips: float = 8.0
    max_hold_seconds: int = 300  # 5 minutos


class ScalpingStrategy:
    """
    Estratégia de scalping profissional.
    
    Setups:
    1. Spread Compression - Entry quando spread contrai após expansão
    2. Liquidity Grab - Após sweep de liquidez em high/low
    3. Momentum Burst - Movimento rápido com volume
    4. Absorption - Grande volume absorvido sem movimento
    5. Delta Divergence - Divergência entre delta e preço
    6. VWAP Bounce - Reversão no VWAP
    7. Microstructure Reversal - Padrões de reversão microscópicos
    8. Order Block Tap - Toque em OB com reação
    9. FVG Fill - Preenchimento de Fair Value Gap
    """
    
    def __init__(self, config: Optional[ScalpingConfig] = None):
        self.config = config or ScalpingConfig()
        self.logger = VirtusLogger.get_logger("scalping_strategy")
        self.name = "Scalping Strategy"
        
        # Cache de dados
        self._spread_history: List[float] = []
        self._delta_history: List[float] = []
        self._volume_history: List[float] = []
    
    async def find_setups(
        self,
        market_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Interface para TradingEngine - encontra setups de scalping.
        
        Args:
            market_data: Dados de mercado (candles, tick, etc)
            analysis: Análise técnica completa
            
        Returns:
            Lista de setups encontrados com entry, sl, tp, score
        """
        setups = []
        
        try:
            # Extrai dados necessários
            symbol = market_data.get('symbol', '')
            tick = analysis.get('tick', {})
            current_price = tick.get('bid') or tick.get('last') or analysis.get('price', 0)
            bid = tick.get('bid', current_price)
            ask = tick.get('ask', current_price * 1.0001)
            
            self.logger.info(f"[{symbol}] find_setups START: price={current_price}, tick={tick}")
            
            if not current_price:
                self.logger.warning(f"[{symbol}] No current_price, skipping")
                return setups
            
            # Calcula spread
            spread = ask - bid
            point_value = 0.0001 if 'JPY' not in symbol and symbol != 'XAUUSD' else 0.01
            spread_pips = spread / point_value / 10 if symbol != 'XAUUSD' else spread / 0.1
            
            # Obtém indicadores da análise
            indicators = analysis.get('indicators', {})
            volatility = analysis.get('volatility', {})
            atr = volatility.get('atr', 0) or indicators.get('atr', 0)
            
            # Session
            from datetime import datetime
            hour = datetime.utcnow().hour
            if 7 <= hour < 12:
                session = "london"
            elif 12 <= hour < 17:
                session = "new_york"
            else:
                session = "asian"
            
            # RSI para direção simplificada
            rsi = indicators.get('rsi', 50)
            trend = analysis.get('trend', {})
            
            # trend pode ser string ou dict
            if isinstance(trend, str):
                trend_direction = trend
            else:
                trend_direction = trend.get('direction', 'neutral')
            
            self.logger.info(f"[{symbol}] find_setups: RSI={rsi:.1f}, trend={trend_direction}")
            
            # Tenta gerar sinal via evaluate
            signal = await self.evaluate(
                symbol=symbol,
                current_price=current_price,
                bid=bid,
                ask=ask,
                spread_pips=spread_pips,
                atr=atr,
                session=session,
                trend=trend_direction,
                liquidity_score=0.7,  # Default razoável
            )
            
            if signal:
                # Converte ScalpingSignal para dict
                setups.append({
                    'name': f"scalping_{signal.setup.value}",
                    'direction': 'buy' if signal.direction == SignalDirection.BUY else 'sell',
                    'entry': signal.entry_price,
                    'sl': signal.stop_loss,
                    'tp': signal.take_profit,
                    'score': signal.confidence,
                    'risk_reward': signal.risk_reward,
                    'metadata': {
                        'setup_type': signal.setup.value,
                        'filters_passed': signal.filters_passed,
                        'expected_duration': signal.expected_duration_seconds,
                    }
                })
            
            # Fallback: Gerar setup simples baseado em RSI/BB se não houver sinal complexo
            if not setups:
                bb = indicators.get('bollinger', {})
                bb_lower = bb.get('lower', 0)
                bb_upper = bb.get('upper', 0)
                bb_middle = bb.get('middle', 0)
                
                # Log para debug
                self.logger.info(f"[{symbol}] Fallback check: RSI={rsi:.1f}, price={current_price:.5f}, trend={trend_direction}")
                self.logger.info(f"[{symbol}] BB: lower={bb_lower:.5f}, middle={bb_middle:.5f}, upper={bb_upper:.5f}")
                
                # === SETUP 1: RSI extremo com preço em banda ===
                if rsi < 45 and current_price and bb_lower and current_price <= bb_lower * 1.005:
                    # RSI baixo + preço próximo ao suporte BB
                    sl_distance = atr * 1.5 if atr else current_price * 0.003
                    tp_distance = atr * 2.0 if atr else current_price * 0.004
                    
                    setups.append({
                        'name': 'scalping_rsi_bb_buy',
                        'direction': 'buy',
                        'entry': current_price,
                        'sl': current_price - sl_distance,
                        'tp': current_price + tp_distance,
                        'score': 0.55,
                        'risk_reward': tp_distance / sl_distance if sl_distance else 1.3,
                    })
                    
                elif rsi > 55 and current_price and bb_upper and current_price >= bb_upper * 0.995:
                    # RSI alto + preço próximo à resistência BB
                    sl_distance = atr * 1.5 if atr else current_price * 0.003
                    tp_distance = atr * 2.0 if atr else current_price * 0.004
                    
                    setups.append({
                        'name': 'scalping_rsi_bb_sell',
                        'direction': 'sell',
                        'entry': current_price,
                        'sl': current_price + sl_distance,
                        'tp': current_price - tp_distance,
                        'score': 0.55,
                        'risk_reward': tp_distance / sl_distance if sl_distance else 1.3,
                    })
                
                # === SETUP 2: TREND FOLLOWING - segue direção da tendência ===
                if not setups and trend_direction in ['bullish', 'bearish']:
                    sl_distance = atr * 2.0 if atr else current_price * 0.004
                    tp_distance = atr * 3.0 if atr else current_price * 0.006
                    
                    if trend_direction == 'bullish' and current_price:
                        # Compra em tendência de alta
                        setups.append({
                            'name': 'scalping_trend_buy',
                            'direction': 'buy',
                            'entry': current_price,
                            'sl': current_price - sl_distance,
                            'tp': current_price + tp_distance,
                            'score': 0.50,
                            'risk_reward': tp_distance / sl_distance if sl_distance else 1.5,
                        })
                        self.logger.info(f"[{symbol}] ✅ Setup TREND BUY gerado (trend={trend_direction})")
                    
                    elif trend_direction == 'bearish' and current_price:
                        # Vende em tendência de baixa
                        setups.append({
                            'name': 'scalping_trend_sell',
                            'direction': 'sell',
                            'entry': current_price,
                            'sl': current_price + sl_distance,
                            'tp': current_price - tp_distance,
                            'score': 0.50,
                            'risk_reward': tp_distance / sl_distance if sl_distance else 1.5,
                        })
                        self.logger.info(f"[{symbol}] ✅ Setup TREND SELL gerado (trend={trend_direction})")
                
                # === SETUP 3: MOMENTUM - RSI com direção clara ===
                if not setups:
                    sl_distance = atr * 1.5 if atr else current_price * 0.003
                    tp_distance = atr * 2.0 if atr else current_price * 0.004
                    
                    # RSI > 50 = momentum de alta, RSI < 50 = momentum de baixa
                    if rsi > 52:
                        setups.append({
                            'name': 'scalping_momentum_buy',
                            'direction': 'buy',
                            'entry': current_price,
                            'sl': current_price - sl_distance,
                            'tp': current_price + tp_distance,
                            'score': 0.45,  # Score menor para setup mais agressivo
                            'risk_reward': tp_distance / sl_distance if sl_distance else 1.3,
                        })
                        self.logger.info(f"[{symbol}] ✅ Setup MOMENTUM BUY gerado (RSI={rsi:.1f})")
                    
                    elif rsi < 48:
                        setups.append({
                            'name': 'scalping_momentum_sell',
                            'direction': 'sell',
                            'entry': current_price,
                            'sl': current_price + sl_distance,
                            'tp': current_price - tp_distance,
                            'score': 0.45,
                            'risk_reward': tp_distance / sl_distance if sl_distance else 1.3,
                        })
                        self.logger.info(f"[{symbol}] ✅ Setup MOMENTUM SELL gerado (RSI={rsi:.1f})")
                    
        except Exception as e:
            self.logger.error(f"Erro em find_setups: {e}")
        
        return setups
        
        # Estado
        self._last_signal_time: Optional[datetime] = None
        self._cooldown_seconds = 30
    
    async def evaluate(
        self,
        symbol: str,
        current_price: float,
        bid: float,
        ask: float,
        # Order Flow Data
        delta: float = 0,
        cumulative_delta: float = 0,
        buy_volume: float = 0,
        sell_volume: float = 0,
        absorption_detected: bool = False,
        absorption_side: Optional[str] = None,
        # Microstructure
        spread_pips: float = 0,
        liquidity_score: float = 0,
        market_quality: float = 0,
        # Technical
        vwap: float = 0,
        vwap_upper: float = 0,
        vwap_lower: float = 0,
        atr: float = 0,
        # SMC
        order_blocks: List[Dict] = None,
        fvg_zones: List[Dict] = None,
        liquidity_pools: List[Dict] = None,
        # Context
        session: str = "london",
        near_news: bool = False,
        trend: str = "neutral",
    ) -> Optional[ScalpingSignal]:
        """
        Avalia todos os setups de scalping.
        
        Returns:
            ScalpingSignal se encontrar setup válido
        """
        # === FILTROS GERAIS ===
        filters_passed = []
        filters_failed = []
        
        # Spread check
        if spread_pips <= self.config.max_spread_pips:
            filters_passed.append("spread_ok")
        else:
            filters_failed.append(f"spread_high_{spread_pips:.1f}")
            return None  # Deal breaker
        
        # Session check
        if session in self.config.trade_sessions:
            filters_passed.append(f"session_{session}")
        else:
            filters_failed.append(f"session_{session}")
            return None
        
        # News check
        if near_news and self.config.avoid_news_minutes > 0:
            filters_failed.append("near_news")
            return None
        filters_passed.append("no_news")
        
        # Liquidity check
        if liquidity_score >= self.config.min_liquidity_score:
            filters_passed.append("liquidity_ok")
        else:
            filters_failed.append("low_liquidity")
        
        # Cooldown check
        if self._last_signal_time:
            elapsed = (datetime.now() - self._last_signal_time).total_seconds()
            if elapsed < self._cooldown_seconds:
                return None
        
        # Atualiza históricos
        self._spread_history.append(spread_pips)
        self._delta_history.append(delta)
        self._volume_history.append(buy_volume + sell_volume)
        
        # Mantém últimos 100
        self._spread_history = self._spread_history[-100:]
        self._delta_history = self._delta_history[-100:]
        self._volume_history = self._volume_history[-100:]
        
        # === AVALIA CADA SETUP ===
        signals: List[ScalpingSignal] = []
        
        # 1. Spread Compression
        signal = self._check_spread_compression(
            current_price, spread_pips, atr, filters_passed.copy()
        )
        if signal:
            signals.append(signal)
        
        # 2. Liquidity Grab
        if liquidity_pools:
            signal = self._check_liquidity_grab(
                current_price, liquidity_pools, atr, filters_passed.copy()
            )
            if signal:
                signals.append(signal)
        
        # 3. Momentum Burst
        signal = self._check_momentum_burst(
            current_price, delta, buy_volume, sell_volume,
            atr, filters_passed.copy()
        )
        if signal:
            signals.append(signal)
        
        # 4. Absorption
        if absorption_detected:
            signal = self._check_absorption(
                current_price, absorption_side, delta,
                buy_volume, sell_volume, atr, filters_passed.copy()
            )
            if signal:
                signals.append(signal)
        
        # 5. Delta Divergence
        signal = self._check_delta_divergence(
            current_price, cumulative_delta, trend, atr, filters_passed.copy()
        )
        if signal:
            signals.append(signal)
        
        # 6. VWAP Bounce
        if vwap > 0:
            signal = self._check_vwap_bounce(
                current_price, vwap, vwap_upper, vwap_lower,
                atr, filters_passed.copy()
            )
            if signal:
                signals.append(signal)
        
        # 7. Order Block Tap
        if order_blocks:
            signal = self._check_order_block_tap(
                current_price, order_blocks, delta, atr, filters_passed.copy()
            )
            if signal:
                signals.append(signal)
        
        # 8. FVG Fill
        if fvg_zones:
            signal = self._check_fvg_fill(
                current_price, fvg_zones, atr, filters_passed.copy()
            )
            if signal:
                signals.append(signal)
        
        # Seleciona melhor sinal
        if signals:
            best_signal = max(signals, key=lambda s: s.confidence * s.risk_reward)
            
            # Valida RR mínimo
            if best_signal.risk_reward >= self.config.min_risk_reward:
                self._last_signal_time = datetime.now()
                
                self.logger.info(
                    f"🎯 Scalping signal: {best_signal.setup.value} "
                    f"{best_signal.direction.value} @ {best_signal.entry_price:.5f} "
                    f"SL: {best_signal.stop_loss:.5f} TP: {best_signal.take_profit:.5f} "
                    f"RR: {best_signal.risk_reward:.2f}"
                )
                
                return best_signal
        
        return None
    
    def _check_spread_compression(
        self,
        price: float,
        spread: float,
        atr: float,
        filters: List[str]
    ) -> Optional[ScalpingSignal]:
        """
        Detecta compressão de spread.
        
        Entry quando spread contrai significativamente após expansão.
        Indica potencial movimento direcional.
        """
        if len(self._spread_history) < 20:
            return None
        
        recent_spreads = self._spread_history[-20:]
        avg_spread = np.mean(recent_spreads)
        max_spread = max(recent_spreads[-10:])
        
        # Verifica se houve expansão recente seguida de compressão
        compression_ratio = spread / max_spread if max_spread > 0 else 1
        
        if compression_ratio > 0.5:  # Spread não comprimiu suficiente
            return None
        
        if spread >= avg_spread * 0.7:  # Ainda acima de 70% da média
            return None
        
        # Determina direção pelo delta recente
        if len(self._delta_history) < 5:
            return None
        
        recent_delta = sum(self._delta_history[-5:])
        
        if abs(recent_delta) < 0.1:  # Delta muito baixo
            return None
        
        direction = SignalDirection.BUY if recent_delta > 0 else SignalDirection.SELL
        
        # Calcula stops
        sl_distance = atr * 0.5 if atr > 0 else self._pips_to_price(price, 5)
        tp_distance = atr * 1.0 if atr > 0 else self._pips_to_price(price, 10)
        
        if direction == SignalDirection.BUY:
            sl = price - sl_distance
            tp = price + tp_distance
        else:
            sl = price + sl_distance
            tp = price - tp_distance
        
        rr = tp_distance / sl_distance if sl_distance > 0 else 0
        
        filters.append("spread_compression")
        
        return ScalpingSignal(
            setup=ScalpingSetup.SPREAD_COMPRESSION,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.65 + (1 - compression_ratio) * 0.2,
            expected_duration_seconds=120,
            risk_reward=rr,
            filters_passed=filters,
            filters_failed=[],
            metadata={
                'compression_ratio': compression_ratio,
                'avg_spread': avg_spread,
                'recent_delta': recent_delta,
            }
        )
    
    def _check_liquidity_grab(
        self,
        price: float,
        liquidity_pools: List[Dict],
        atr: float,
        filters: List[str]
    ) -> Optional[ScalpingSignal]:
        """
        Detecta liquidity grab seguido de reversão.
        
        Entry após sweep de liquidez (stop hunt).
        """
        # Procura pools próximos que foram varridos
        for pool in liquidity_pools:
            pool_level = pool.get('level', 0)
            pool_type = pool.get('type', '')  # 'high' ou 'low'
            swept = pool.get('swept', False)
            
            if not swept:
                continue
            
            distance = abs(price - pool_level)
            atr_distance = distance / atr if atr > 0 else float('inf')
            
            # Pool deve ter sido varrido e preço retornado
            if atr_distance > 1.0:  # Muito longe do sweep
                continue
            
            # Direção oposta ao sweep
            if pool_type == 'high':  # Sweep de highs = bearish reversal
                direction = SignalDirection.SELL
                sl = pool_level + atr * 0.3
                tp = price - atr * 1.5
            else:  # Sweep de lows = bullish reversal
                direction = SignalDirection.BUY
                sl = pool_level - atr * 0.3
                tp = price + atr * 1.5
            
            sl_distance = abs(price - sl)
            tp_distance = abs(tp - price)
            rr = tp_distance / sl_distance if sl_distance > 0 else 0
            
            if rr < self.config.min_risk_reward:
                continue
            
            filters.append("liquidity_grabbed")
            
            return ScalpingSignal(
                setup=ScalpingSetup.LIQUIDITY_GRAB,
                direction=direction,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                confidence=0.75,
                expected_duration_seconds=180,
                risk_reward=rr,
                filters_passed=filters,
                filters_failed=[],
                metadata={
                    'pool_level': pool_level,
                    'pool_type': pool_type,
                }
            )
        
        return None
    
    def _check_momentum_burst(
        self,
        price: float,
        delta: float,
        buy_vol: float,
        sell_vol: float,
        atr: float,
        filters: List[str]
    ) -> Optional[ScalpingSignal]:
        """
        Detecta burst de momentum.
        
        Entry em movimento rápido com volume confirmatório.
        """
        total_vol = buy_vol + sell_vol
        
        if total_vol == 0:
            return None
        
        # Volume deve ser acima da média
        if len(self._volume_history) < 10:
            return None
        
        avg_vol = np.mean(self._volume_history[-10:])
        vol_ratio = total_vol / avg_vol if avg_vol > 0 else 0
        
        if vol_ratio < 1.5:  # Volume não é significativo
            return None
        
        # Delta deve ser forte
        vol_delta = buy_vol - sell_vol
        delta_ratio = abs(vol_delta) / total_vol if total_vol > 0 else 0
        
        if delta_ratio < self.config.min_delta_threshold:
            return None
        
        # Direção pelo delta
        direction = SignalDirection.BUY if vol_delta > 0 else SignalDirection.SELL
        
        # Stops baseados em ATR (scalping = stops curtos)
        sl_distance = atr * 0.4 if atr > 0 else self._pips_to_price(price, 4)
        tp_distance = atr * 0.8 if atr > 0 else self._pips_to_price(price, 8)
        
        if direction == SignalDirection.BUY:
            sl = price - sl_distance
            tp = price + tp_distance
        else:
            sl = price + sl_distance
            tp = price - tp_distance
        
        rr = tp_distance / sl_distance if sl_distance > 0 else 0
        
        filters.append("momentum_burst")
        
        return ScalpingSignal(
            setup=ScalpingSetup.MOMENTUM_BURST,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.6 + min(vol_ratio * 0.1, 0.2),
            expected_duration_seconds=90,
            risk_reward=rr,
            filters_passed=filters,
            filters_failed=[],
            metadata={
                'volume_ratio': vol_ratio,
                'delta_ratio': delta_ratio,
            }
        )
    
    def _check_absorption(
        self,
        price: float,
        absorption_side: str,
        delta: float,
        buy_vol: float,
        sell_vol: float,
        atr: float,
        filters: List[str]
    ) -> Optional[ScalpingSignal]:
        """
        Detecta absorção de ordens.
        
        Grande volume sem movimento = acumulação institucional.
        """
        # Absorção de vendas = compradores absorvendo = bullish
        # Absorção de compras = vendedores absorvendo = bearish
        
        if absorption_side == "sell":
            direction = SignalDirection.BUY
        elif absorption_side == "buy":
            direction = SignalDirection.SELL
        else:
            return None
        
        # Calcula ratio de absorção
        total_vol = buy_vol + sell_vol
        if total_vol == 0:
            return None
        
        if absorption_side == "sell":
            absorption_ratio = sell_vol / buy_vol if buy_vol > 0 else 0
        else:
            absorption_ratio = buy_vol / sell_vol if sell_vol > 0 else 0
        
        if absorption_ratio < self.config.min_absorption_ratio:
            return None
        
        # Stops
        sl_distance = atr * 0.5 if atr > 0 else self._pips_to_price(price, 5)
        tp_distance = atr * 1.0 if atr > 0 else self._pips_to_price(price, 10)
        
        if direction == SignalDirection.BUY:
            sl = price - sl_distance
            tp = price + tp_distance
        else:
            sl = price + sl_distance
            tp = price - tp_distance
        
        rr = tp_distance / sl_distance if sl_distance > 0 else 0
        
        filters.append("absorption_detected")
        
        return ScalpingSignal(
            setup=ScalpingSetup.ABSORPTION,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.70 + min(absorption_ratio * 0.05, 0.15),
            expected_duration_seconds=150,
            risk_reward=rr,
            filters_passed=filters,
            filters_failed=[],
            metadata={
                'absorption_side': absorption_side,
                'absorption_ratio': absorption_ratio,
            }
        )
    
    def _check_delta_divergence(
        self,
        price: float,
        cumulative_delta: float,
        trend: str,
        atr: float,
        filters: List[str]
    ) -> Optional[ScalpingSignal]:
        """
        Detecta divergência de delta.
        
        Preço subindo mas delta caindo = fraqueza bullish
        Preço caindo mas delta subindo = fraqueza bearish
        """
        if len(self._delta_history) < 10:
            return None
        
        # Calcula tendência do delta
        delta_changes = [
            self._delta_history[i] - self._delta_history[i-1]
            for i in range(1, len(self._delta_history[-10:]))
        ]
        
        delta_trend = sum(delta_changes)
        
        # Divergência
        if trend == "bullish" and delta_trend < -0.5:
            direction = SignalDirection.SELL
        elif trend == "bearish" and delta_trend > 0.5:
            direction = SignalDirection.BUY
        else:
            return None
        
        # Stops
        sl_distance = atr * 0.6 if atr > 0 else self._pips_to_price(price, 6)
        tp_distance = atr * 1.2 if atr > 0 else self._pips_to_price(price, 12)
        
        if direction == SignalDirection.BUY:
            sl = price - sl_distance
            tp = price + tp_distance
        else:
            sl = price + sl_distance
            tp = price - tp_distance
        
        rr = tp_distance / sl_distance if sl_distance > 0 else 0
        
        filters.append("delta_divergence")
        
        return ScalpingSignal(
            setup=ScalpingSetup.DELTA_DIVERGENCE,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.65,
            expected_duration_seconds=200,
            risk_reward=rr,
            filters_passed=filters,
            filters_failed=[],
            metadata={
                'trend': trend,
                'delta_trend': delta_trend,
            }
        )
    
    def _check_vwap_bounce(
        self,
        price: float,
        vwap: float,
        vwap_upper: float,
        vwap_lower: float,
        atr: float,
        filters: List[str]
    ) -> Optional[ScalpingSignal]:
        """
        Detecta bounce no VWAP.
        
        VWAP age como suporte/resistência dinâmico.
        """
        # Distância do VWAP
        distance_from_vwap = abs(price - vwap) / vwap * 100 if vwap > 0 else float('inf')
        
        if distance_from_vwap > 0.1:  # Mais de 0.1% do VWAP
            return None
        
        # Determina se está acima ou abaixo
        if price < vwap:  # Abaixo = potencial bounce para cima
            direction = SignalDirection.BUY
            sl = vwap_lower - atr * 0.2 if vwap_lower else price - atr * 0.5
            tp = vwap + atr * 0.5
        else:  # Acima = potencial rejeição para baixo
            direction = SignalDirection.SELL
            sl = vwap_upper + atr * 0.2 if vwap_upper else price + atr * 0.5
            tp = vwap - atr * 0.5
        
        sl_distance = abs(price - sl)
        tp_distance = abs(tp - price)
        rr = tp_distance / sl_distance if sl_distance > 0 else 0
        
        filters.append("vwap_proximity")
        
        return ScalpingSignal(
            setup=ScalpingSetup.VWAP_BOUNCE,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            confidence=0.60,
            expected_duration_seconds=180,
            risk_reward=rr,
            filters_passed=filters,
            filters_failed=[],
            metadata={
                'vwap': vwap,
                'distance_pct': distance_from_vwap,
            }
        )
    
    def _check_order_block_tap(
        self,
        price: float,
        order_blocks: List[Dict],
        delta: float,
        atr: float,
        filters: List[str]
    ) -> Optional[ScalpingSignal]:
        """
        Detecta toque em Order Block com reação.
        """
        for ob in order_blocks:
            ob_high = ob.get('high', 0)
            ob_low = ob.get('low', 0)
            ob_type = ob.get('type', '')  # 'bullish' ou 'bearish'
            mitigated = ob.get('mitigated', False)
            
            if mitigated:
                continue
            
            # Verifica se preço está dentro do OB
            if not (ob_low <= price <= ob_high):
                continue
            
            # Bullish OB (suporte) = compra
            # Bearish OB (resistência) = venda
            if ob_type == 'bullish':
                direction = SignalDirection.BUY
                sl = ob_low - atr * 0.2
                tp = price + atr * 1.5
            else:
                direction = SignalDirection.SELL
                sl = ob_high + atr * 0.2
                tp = price - atr * 1.5
            
            # Confirma com delta
            delta_confirms = (
                (direction == SignalDirection.BUY and delta > 0) or
                (direction == SignalDirection.SELL and delta < 0)
            )
            
            if not delta_confirms:
                continue
            
            sl_distance = abs(price - sl)
            tp_distance = abs(tp - price)
            rr = tp_distance / sl_distance if sl_distance > 0 else 0
            
            if rr < self.config.min_risk_reward:
                continue
            
            filters.append("order_block_tap")
            
            return ScalpingSignal(
                setup=ScalpingSetup.ORDER_BLOCK_TAP,
                direction=direction,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                confidence=0.75,
                expected_duration_seconds=200,
                risk_reward=rr,
                filters_passed=filters,
                filters_failed=[],
                metadata={
                    'ob_type': ob_type,
                    'ob_high': ob_high,
                    'ob_low': ob_low,
                }
            )
        
        return None
    
    def _check_fvg_fill(
        self,
        price: float,
        fvg_zones: List[Dict],
        atr: float,
        filters: List[str]
    ) -> Optional[ScalpingSignal]:
        """
        Detecta preenchimento de Fair Value Gap.
        """
        for fvg in fvg_zones:
            fvg_high = fvg.get('high', 0)
            fvg_low = fvg.get('low', 0)
            fvg_type = fvg.get('type', '')  # 'bullish' ou 'bearish'
            filled = fvg.get('filled', False)
            
            if filled:
                continue
            
            # Verifica se preço está entrando no FVG
            in_fvg = fvg_low <= price <= fvg_high
            
            if not in_fvg:
                continue
            
            # FVG bullish (gap up) = preço corrige para baixo, depois sobe
            # FVG bearish (gap down) = preço corrige para cima, depois cai
            if fvg_type == 'bullish':
                direction = SignalDirection.BUY
                sl = fvg_low - atr * 0.3
                tp = fvg_high + atr * 1.0
            else:
                direction = SignalDirection.SELL
                sl = fvg_high + atr * 0.3
                tp = fvg_low - atr * 1.0
            
            sl_distance = abs(price - sl)
            tp_distance = abs(tp - price)
            rr = tp_distance / sl_distance if sl_distance > 0 else 0
            
            if rr < self.config.min_risk_reward:
                continue
            
            filters.append("fvg_fill")
            
            return ScalpingSignal(
                setup=ScalpingSetup.FVG_FILL,
                direction=direction,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                confidence=0.70,
                expected_duration_seconds=150,
                risk_reward=rr,
                filters_passed=filters,
                filters_failed=[],
                metadata={
                    'fvg_type': fvg_type,
                    'fvg_high': fvg_high,
                    'fvg_low': fvg_low,
                }
            )
        
        return None
    
    def _pips_to_price(self, price: float, pips: float) -> float:
        """Converte pips para valor de preço."""
        # Assume EURUSD-like (4 decimais)
        # Para outros pares, ajustar baseado no símbolo
        return pips / 10000
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna informações da estratégia."""
        return {
            'name': 'VIRTUS Scalping Strategy',
            'type': 'scalping',
            'timeframes': {
                'primary': self.config.primary_tf,
                'confirmation': self.config.confirmation_tf,
            },
            'setups': [s.value for s in ScalpingSetup],
            'config': {
                'max_spread_pips': self.config.max_spread_pips,
                'min_liquidity': self.config.min_liquidity_score,
                'max_risk_pips': self.config.max_risk_pips,
                'min_rr': self.config.min_risk_reward,
                'target_pips': self.config.target_pips,
                'max_hold_seconds': self.config.max_hold_seconds,
            },
            'active_sessions': self.config.trade_sessions,
        }
