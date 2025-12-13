"""
BRAIN - Breakout Strategy
Estratégia de rompimento
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np

from ..base_strategy import BaseStrategy, StrategyConfig, StrategyState


class BreakoutStrategy(BaseStrategy):
    """
    Estratégia de Breakout (Rompimento)
    
    Lógica:
    - Identifica zonas de consolidação
    - Aguarda rompimento com volume
    - Entra na direção do rompimento
    - Usa reteste como confirmação
    
    Configurações recomendadas:
    - Timeframe: M15, M30, H1
    - Símbolos: Todos (especialmente XAUUSD)
    - Mercado: Após consolidação
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Parâmetros de consolidação
        self._lookback = config.parameters.get("lookback", 20)
        self._consolidation_threshold = config.parameters.get("consolidation_threshold", 0.003)  # 0.3%
        self._min_consolidation_bars = config.parameters.get("min_consolidation_bars", 10)
        
        # Parâmetros de breakout
        self._breakout_threshold = config.parameters.get("breakout_threshold", 0.0015)  # 0.15%
        self._volume_multiplier = config.parameters.get("volume_multiplier", 1.5)
        
        # ATR para SL/TP
        self._atr_period = config.parameters.get("atr_period", 14)
        self._sl_atr_mult = config.parameters.get("sl_atr_mult", 1.5)
        self._tp_atr_mult = config.parameters.get("tp_atr_mult", 3.0)
        
        # Support/Resistance
        self._sr_lookback = config.parameters.get("sr_lookback", 50)
    
    @property
    def name(self) -> str:
        return "breakout"
    
    @property
    def description(self) -> str:
        return "Estratégia de rompimento de zonas de consolidação"
    
    # ==========================================================================
    # CÁLCULOS
    # ==========================================================================
    
    def _find_consolidation_zone(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> Optional[Dict[str, float]]:
        """
        Identifica zona de consolidação recente
        
        Returns:
            Dict com high, low da zona ou None
        """
        if len(closes) < self._lookback:
            return None
        
        # Últimas N barras
        recent_highs = highs[-self._lookback:]
        recent_lows = lows[-self._lookback:]
        
        zone_high = np.max(recent_highs)
        zone_low = np.min(recent_lows)
        
        # Verificar se está consolidando (range < threshold)
        range_pct = (zone_high - zone_low) / zone_low
        
        if range_pct > self._consolidation_threshold:
            return None  # Range muito amplo
        
        # Contar barras dentro da zona
        bars_in_zone = 0
        for i in range(-self._lookback, 0):
            if lows[i] >= zone_low * 0.998 and highs[i] <= zone_high * 1.002:
                bars_in_zone += 1
        
        if bars_in_zone < self._min_consolidation_bars:
            return None
        
        return {
            "high": zone_high,
            "low": zone_low,
            "range": zone_high - zone_low,
            "bars": bars_in_zone
        }
    
    def _detect_breakout(
        self,
        closes: np.ndarray,
        zone: Dict[str, float],
        volumes: Optional[np.ndarray] = None
    ) -> Optional[str]:
        """
        Detecta rompimento da zona
        
        Returns:
            "up", "down" ou None
        """
        current_close = closes[-1]
        prev_close = closes[-2]
        
        zone_high = zone["high"]
        zone_low = zone["low"]
        
        # Threshold para considerar breakout
        breakout_margin = zone["range"] * 0.1
        
        # Verificar volume se disponível
        volume_confirmed = True
        if volumes is not None and len(volumes) >= 20:
            avg_volume = np.mean(volumes[-20:-1])
            current_volume = volumes[-1]
            volume_confirmed = current_volume > avg_volume * self._volume_multiplier
        
        # Breakout para cima
        if (current_close > zone_high + breakout_margin and
            prev_close <= zone_high and
            volume_confirmed):
            return "up"
        
        # Breakout para baixo
        if (current_close < zone_low - breakout_margin and
            prev_close >= zone_low and
            volume_confirmed):
            return "down"
        
        return None
    
    def _calculate_atr(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> float:
        """Calcula ATR atual"""
        tr = []
        
        for i in range(1, len(closes)):
            tr.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            ))
        
        if len(tr) < self._atr_period:
            return 0
        
        return np.mean(tr[-self._atr_period:])
    
    def _find_support_resistance(
        self,
        highs: np.ndarray,
        lows: np.ndarray
    ) -> tuple[List[float], List[float]]:
        """Encontra níveis de suporte e resistência"""
        supports = []
        resistances = []
        
        lookback = min(self._sr_lookback, len(highs) - 2)
        
        for i in range(2, lookback):
            # Pivot High (resistência)
            if (highs[-i] > highs[-i-1] and 
                highs[-i] > highs[-i+1] and
                highs[-i] > highs[-i-2] and
                highs[-i] > highs[-i+2] if i > 2 else True):
                resistances.append(highs[-i])
            
            # Pivot Low (suporte)
            if (lows[-i] < lows[-i-1] and 
                lows[-i] < lows[-i+1] and
                lows[-i] < lows[-i-2] and
                lows[-i] < lows[-i+2] if i > 2 else True):
                supports.append(lows[-i])
        
        return supports, resistances
    
    def _get_nearest_sr(
        self,
        price: float,
        levels: List[float],
        direction: str
    ) -> Optional[float]:
        """Encontra S/R mais próximo"""
        if not levels:
            return None
        
        if direction == "above":
            above = [l for l in levels if l > price]
            return min(above) if above else None
        else:
            below = [l for l in levels if l < price]
            return max(below) if below else None
    
    # ==========================================================================
    # SINAIS
    # ==========================================================================
    
    async def generate_signal(
        self,
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Gera sinal de breakout
        
        Condições:
        1. Identificar zona de consolidação
        2. Detectar rompimento com volume
        3. Calcular entrada, SL e TP
        """
        if self._state != StrategyState.ACTIVE:
            return None
        
        rates = market_data.get("rates", [])
        if len(rates) < self._sr_lookback:
            return None
        
        # Extrair OHLCV
        opens = np.array([r["open"] for r in rates])
        highs = np.array([r["high"] for r in rates])
        lows = np.array([r["low"] for r in rates])
        closes = np.array([r["close"] for r in rates])
        volumes = np.array([r.get("tick_volume", r.get("volume", 0)) for r in rates])
        
        # Encontrar zona de consolidação
        zone = self._find_consolidation_zone(highs, lows, closes)
        
        if not zone:
            return None
        
        # Detectar breakout
        breakout = self._detect_breakout(closes, zone, volumes)
        
        if not breakout:
            return None
        
        # Calcular indicadores
        atr = self._calculate_atr(highs, lows, closes)
        supports, resistances = self._find_support_resistance(highs, lows)
        
        current_close = closes[-1]
        signal = None
        
        # ===== BREAKOUT PARA CIMA (BUY) =====
        if breakout == "up":
            entry = current_close
            sl = zone["low"] - atr * self._sl_atr_mult
            
            # TP no próximo nível de resistência ou ATR
            next_resistance = self._get_nearest_sr(current_close, resistances, "above")
            
            if next_resistance and next_resistance > current_close:
                tp = next_resistance
            else:
                tp = entry + atr * self._tp_atr_mult
            
            confidence = self._calculate_breakout_confidence(zone, volumes)
            
            signal = {
                "symbol": self._config.symbol,
                "direction": "buy",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "confidence": confidence,
                "strategy": self.name,
                "reason": f"Breakout UP - Zone: {zone['low']:.5f}-{zone['high']:.5f}",
                "metadata": {
                    "zone_high": zone["high"],
                    "zone_low": zone["low"],
                    "zone_bars": zone["bars"],
                    "atr": atr,
                    "breakout_type": "up"
                }
            }
        
        # ===== BREAKOUT PARA BAIXO (SELL) =====
        elif breakout == "down":
            entry = current_close
            sl = zone["high"] + atr * self._sl_atr_mult
            
            # TP no próximo suporte ou ATR
            next_support = self._get_nearest_sr(current_close, supports, "below")
            
            if next_support and next_support < current_close:
                tp = next_support
            else:
                tp = entry - atr * self._tp_atr_mult
            
            confidence = self._calculate_breakout_confidence(zone, volumes)
            
            signal = {
                "symbol": self._config.symbol,
                "direction": "sell",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "confidence": confidence,
                "strategy": self.name,
                "reason": f"Breakout DOWN - Zone: {zone['low']:.5f}-{zone['high']:.5f}",
                "metadata": {
                    "zone_high": zone["high"],
                    "zone_low": zone["low"],
                    "zone_bars": zone["bars"],
                    "atr": atr,
                    "breakout_type": "down"
                }
            }
        
        if signal and self.validate_signal(signal):
            self._stats.signals_generated += 1
            return signal
        
        return None
    
    def _calculate_breakout_confidence(
        self,
        zone: Dict[str, float],
        volumes: np.ndarray
    ) -> float:
        """Calcula confiança do breakout"""
        confidence = 0.5
        
        # Mais barras na consolidação = mais confiável
        bars_score = min(zone["bars"] / 20, 0.2)
        confidence += bars_score
        
        # Volume acima da média = mais confiável
        if len(volumes) >= 20:
            avg_vol = np.mean(volumes[-20:-1])
            current_vol = volumes[-1]
            if current_vol > avg_vol * 2:
                confidence += 0.2
            elif current_vol > avg_vol * 1.5:
                confidence += 0.1
        
        return round(min(confidence, 0.9), 2)
    
    # ==========================================================================
    # VALIDAÇÃO E SL/TP
    # ==========================================================================
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Valida sinal de breakout"""
        if not signal:
            return False
        
        entry = signal.get("entry_price", 0)
        sl = signal.get("stop_loss", 0)
        tp = signal.get("take_profit", 0)
        
        if not all([entry, sl, tp]):
            return False
        
        # R:R mínimo 1.5:1
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        
        if risk == 0 or reward / risk < 1.5:
            return False
        
        # Confiança mínima
        if signal.get("confidence", 0) < self._config.min_confidence:
            return False
        
        return True
    
    def calculate_sl_tp(
        self,
        entry_price: float,
        direction: str,
        market_data: Dict[str, Any]
    ) -> tuple[float, float]:
        """Calcula SL/TP baseado em ATR"""
        rates = market_data.get("rates", [])
        
        if len(rates) < self._atr_period:
            atr = entry_price * 0.002
        else:
            highs = np.array([r["high"] for r in rates])
            lows = np.array([r["low"] for r in rates])
            closes = np.array([r["close"] for r in rates])
            atr = self._calculate_atr(highs, lows, closes)
        
        if direction == "buy":
            sl = entry_price - atr * self._sl_atr_mult
            tp = entry_price + atr * self._tp_atr_mult
        else:
            sl = entry_price + atr * self._sl_atr_mult
            tp = entry_price - atr * self._tp_atr_mult
        
        return sl, tp


# Registrar na factory
from ..base_strategy import StrategyFactory
StrategyFactory.register("breakout", BreakoutStrategy)
