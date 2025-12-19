"""
Exemplo de Plugin de Estratégia VIRTUS
======================================

Este é um template para criar novas estratégias.
Copie este arquivo e modifique conforme necessário.
"""

from typing import Dict, Any, List, Optional
from brain.src.strategies.plugin_system import (
    StrategyPlugin,
    PluginInfo,
    Signal,
    SignalType,
)


class ExampleStrategy(StrategyPlugin):
    """
    Exemplo de estratégia customizada.
    
    Esta estratégia combina:
    - Cruzamento de EMAs
    - Confirmação de volume
    - Filtro de tendência
    """
    
    info = PluginInfo(
        name="ExampleStrategy",
        version="1.0.0",
        author="Seu Nome",
        description="Estratégia de exemplo com EMA + Volume",
        symbols=["XAUUSD", "EURUSD"],  # Símbolos suportados
        timeframes=["M15", "H1"],       # Timeframes suportados
    )
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Define os parâmetros configuráveis da estratégia.
        Estes podem ser alterados via API ou interface.
        """
        return {
            # EMAs
            "ema_fast": 9,
            "ema_slow": 21,
            "ema_trend": 50,
            
            # Volume
            "volume_threshold": 1.5,  # Volume atual > média * 1.5
            
            # Risk
            "sl_atr_multiplier": 1.5,
            "tp_atr_multiplier": 2.0,
            
            # Confidence
            "min_confidence": 60,
        }
    
    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        indicators: Dict[str, Any],
    ) -> Optional[Signal]:
        """
        Lógica principal da estratégia.
        
        Args:
            symbol: Par/símbolo sendo analisado
            timeframe: Timeframe atual
            candles: Lista de candles [{open, high, low, close, volume, time}, ...]
            indicators: Indicadores pré-calculados {ema_fast, ema_slow, atr, volume_ma, ...}
            
        Returns:
            Signal com a recomendação ou None
        """
        # Verifica dados suficientes
        if len(candles) < 50:
            return None
        
        # Extrai indicadores (assumindo que foram calculados)
        ema_fast = indicators.get("ema_fast", [])
        ema_slow = indicators.get("ema_slow", [])
        ema_trend = indicators.get("ema_trend", [])
        volume = indicators.get("volume", [])
        volume_ma = indicators.get("volume_ma", 0)
        atr = indicators.get("atr", 0)
        
        # Preço atual
        current_price = candles[-1].get("close", 0)
        current_volume = candles[-1].get("volume", 0)
        
        # Se indicadores não disponíveis, hold
        if not all([ema_fast, ema_slow, current_price]):
            return Signal(
                type=SignalType.HOLD,
                symbol=symbol,
                strategy=self.info.name,
                reason="Indicadores insuficientes"
            )
        
        # === REGRAS DA ESTRATÉGIA ===
        
        # 1. Verifica tendência geral (EMA trend)
        trend_bullish = current_price > ema_trend[-1] if ema_trend else True
        trend_bearish = current_price < ema_trend[-1] if ema_trend else True
        
        # 2. Verifica cruzamento de EMAs
        ema_cross_up = (
            ema_fast[-2] <= ema_slow[-2] and 
            ema_fast[-1] > ema_slow[-1]
        ) if len(ema_fast) > 1 and len(ema_slow) > 1 else False
        
        ema_cross_down = (
            ema_fast[-2] >= ema_slow[-2] and 
            ema_fast[-1] < ema_slow[-1]
        ) if len(ema_fast) > 1 and len(ema_slow) > 1 else False
        
        # 3. Verifica volume
        volume_ok = (
            current_volume > volume_ma * self._config["volume_threshold"]
        ) if volume_ma > 0 else True
        
        # 4. Calcula SL/TP baseado em ATR
        sl_distance = atr * self._config["sl_atr_multiplier"] if atr else None
        tp_distance = atr * self._config["tp_atr_multiplier"] if atr else None
        
        # === GERA SINAIS ===
        
        # BUY Signal
        if ema_cross_up and trend_bullish and volume_ok:
            confidence = self._calculate_confidence(
                trend=trend_bullish,
                volume=volume_ok,
                cross=True
            )
            
            if confidence >= self._config["min_confidence"]:
                return Signal(
                    type=SignalType.BUY,
                    symbol=symbol,
                    strategy=self.info.name,
                    confidence=confidence,
                    sl=current_price - sl_distance if sl_distance else None,
                    tp=current_price + tp_distance if tp_distance else None,
                    reason=f"EMA cross up + Tendência alta + Volume OK",
                    metadata={
                        "ema_fast": ema_fast[-1],
                        "ema_slow": ema_slow[-1],
                        "trend": "bullish",
                    }
                )
        
        # SELL Signal
        if ema_cross_down and trend_bearish and volume_ok:
            confidence = self._calculate_confidence(
                trend=trend_bearish,
                volume=volume_ok,
                cross=True
            )
            
            if confidence >= self._config["min_confidence"]:
                return Signal(
                    type=SignalType.SELL,
                    symbol=symbol,
                    strategy=self.info.name,
                    confidence=confidence,
                    sl=current_price + sl_distance if sl_distance else None,
                    tp=current_price - tp_distance if tp_distance else None,
                    reason=f"EMA cross down + Tendência baixa + Volume OK",
                    metadata={
                        "ema_fast": ema_fast[-1],
                        "ema_slow": ema_slow[-1],
                        "trend": "bearish",
                    }
                )
        
        # Sem sinal forte
        return Signal(
            type=SignalType.HOLD,
            symbol=symbol,
            strategy=self.info.name,
            reason="Condições não satisfeitas",
        )
    
    def _calculate_confidence(
        self,
        trend: bool,
        volume: bool,
        cross: bool
    ) -> float:
        """Calcula confiança baseada nas condições."""
        confidence = 50.0
        
        if cross:
            confidence += 20
        if trend:
            confidence += 15
        if volume:
            confidence += 15
        
        return min(confidence, 100.0)


# O plugin será carregado automaticamente pelo PluginManager
# quando colocado no diretório brain/src/strategies/plugins/
