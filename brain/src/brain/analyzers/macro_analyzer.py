"""
BRAIN - Macro Analyzer
Analisador de contexto macroeconômico
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from ...core.types import (
    CalendarEvent, COTData, MarketRegime, TradingSession,
    NewsImpact, SignalDirection
)
from ...core.logger import get_logger

logger = get_logger("brain.analyzer.macro")


class EconomicCycle(Enum):
    """Fase do ciclo econômico"""
    EXPANSION = "expansion"
    PEAK = "peak"
    CONTRACTION = "contraction"
    TROUGH = "trough"


class MacroAnalyzer:
    """
    Analisador de contexto macroeconômico
    
    Avalia:
    - Calendário econômico
    - Política monetária
    - Posicionamento institucional (COT)
    - Correlações macro
    - Ciclo econômico
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        
        # Taxas de juros atuais (aproximadas)
        self._interest_rates = {
            "USD": 5.50,  # Fed
            "EUR": 4.50,  # ECB
            "GBP": 5.25,  # BOE
            "JPY": -0.10,  # BOJ
            "CHF": 1.75,  # SNB
            "AUD": 4.35,  # RBA
            "CAD": 5.00,  # BOC
            "NZD": 5.50   # RBNZ
        }
    
    def analyze_calendar(
        self,
        events: List[CalendarEvent],
        symbol: str
    ) -> Dict[str, Any]:
        """
        Analisa calendário econômico para um símbolo
        
        Args:
            events: Lista de eventos
            symbol: Símbolo para análise
            
        Returns:
            Análise do calendário
        """
        if not events:
            return {
                "risk_level": "low",
                "upcoming_events": [],
                "recommendation": "Sem eventos de alto impacto próximos.",
                "safe_to_trade": True
            }
        
        now = datetime.now()
        
        # Separar eventos por período
        next_24h = [e for e in events if e.datetime <= now + timedelta(hours=24)]
        high_impact_24h = [e for e in next_24h if e.impact == NewsImpact.HIGH]
        
        # Determinar nível de risco
        if len(high_impact_24h) >= 2:
            risk_level = "critical"
            safe_to_trade = False
        elif len(high_impact_24h) == 1:
            risk_level = "high"
            safe_to_trade = False
        elif len(next_24h) >= 3:
            risk_level = "medium"
            safe_to_trade = True
        else:
            risk_level = "low"
            safe_to_trade = True
        
        # Eventos próximos formatados
        upcoming = []
        for event in events[:5]:
            time_until = event.datetime - now
            hours_until = time_until.total_seconds() / 3600
            
            upcoming.append({
                "name": event.name_pt or event.name,
                "country": event.country,
                "impact": event.impact.value,
                "datetime": event.datetime.isoformat(),
                "hours_until": round(hours_until, 1)
            })
        
        # Recomendação
        recommendation = self._generate_calendar_recommendation(
            high_impact_24h, risk_level, symbol
        )
        
        return {
            "risk_level": risk_level,
            "safe_to_trade": safe_to_trade,
            "high_impact_next_24h": len(high_impact_24h),
            "total_events": len(events),
            "upcoming_events": upcoming,
            "recommendation": recommendation
        }
    
    def _generate_calendar_recommendation(
        self,
        high_impact_events: List[CalendarEvent],
        risk_level: str,
        symbol: str
    ) -> str:
        """Gera recomendação baseada no calendário"""
        if risk_level == "critical":
            events_str = ", ".join([e.name_pt or e.name for e in high_impact_events[:2]])
            return (
                f"⚠️ CAUTELA: Múltiplos eventos de alto impacto próximos ({events_str}). "
                f"Recomenda-se evitar novas posições em {symbol} até publicação dos dados."
            )
        elif risk_level == "high":
            event = high_impact_events[0]
            return (
                f"⚡ ATENÇÃO: {event.name_pt or event.name} em breve. "
                f"Considere reduzir exposição ou aguardar resultado."
            )
        elif risk_level == "medium":
            return (
                f"📊 Alguns eventos econômicos próximos. "
                f"Opere com stops adequados."
            )
        else:
            return f"✅ Calendário favorável para operações em {symbol}."
    
    def analyze_cot(self, cot_data: Optional[COTData]) -> Dict[str, Any]:
        """
        Analisa dados do COT Report
        
        Args:
            cot_data: Dados do COT
            
        Returns:
            Análise do posicionamento institucional
        """
        if not cot_data:
            return {
                "available": False,
                "analysis": "Dados COT não disponíveis."
            }
        
        # Posições líquidas
        commercial_net = cot_data.commercial_net
        non_commercial_net = cot_data.non_commercial_net
        
        # Determinar bias dos hedgers (commercials)
        if commercial_net > 0:
            commercial_bias = "long"
            commercial_bias_pt = "comprado"
        else:
            commercial_bias = "short"
            commercial_bias_pt = "vendido"
        
        # Determinar bias dos especuladores
        if non_commercial_net > 0:
            speculator_bias = "long"
            speculator_bias_pt = "comprado"
        else:
            speculator_bias = "short"
            speculator_bias_pt = "vendido"
        
        # Detectar divergência
        divergence = (commercial_net > 0) != (non_commercial_net > 0)
        
        # Mudança semanal
        comm_change = cot_data.commercial_net_change or 0
        spec_change = cot_data.non_commercial_net_change or 0
        
        # Gerar análise
        analysis_text = self._generate_cot_analysis(
            cot_data.symbol,
            commercial_bias_pt,
            speculator_bias_pt,
            comm_change,
            spec_change,
            divergence
        )
        
        return {
            "available": True,
            "report_date": cot_data.report_date.isoformat(),
            "commercial_net": commercial_net,
            "non_commercial_net": non_commercial_net,
            "commercial_bias": commercial_bias,
            "speculator_bias": speculator_bias,
            "divergence": divergence,
            "commercial_change": comm_change,
            "speculator_change": spec_change,
            "analysis": analysis_text
        }
    
    def _generate_cot_analysis(
        self,
        symbol: str,
        comm_bias: str,
        spec_bias: str,
        comm_change: int,
        spec_change: int,
        divergence: bool
    ) -> str:
        """Gera texto de análise do COT"""
        parts = []
        
        symbol_name = {
            "XAUUSD": "Ouro",
            "EURUSD": "Euro",
            "GBPUSD": "Libra"
        }.get(symbol, symbol)
        
        parts.append(f"📊 **Posicionamento em {symbol_name}:**")
        parts.append(f"- Hedgers (Commercials): {comm_bias}")
        parts.append(f"- Especuladores: {spec_bias}")
        
        if divergence:
            parts.append(
                "\n⚠️ Divergência entre hedgers e especuladores - "
                "possível reversão à vista."
            )
        
        # Mudanças
        if abs(comm_change) > 10000:
            direction = "aumentaram" if comm_change > 0 else "reduziram"
            parts.append(f"\n📈 Commercials {direction} posições significativamente.")
        
        return "\n".join(parts)
    
    def analyze_monetary_policy(
        self,
        base_currency: str,
        quote_currency: str
    ) -> Dict[str, Any]:
        """
        Analisa política monetária relativa
        
        Args:
            base_currency: Moeda base (ex: EUR)
            quote_currency: Moeda cotada (ex: USD)
            
        Returns:
            Análise de política monetária
        """
        base_rate = self._interest_rates.get(base_currency, 0)
        quote_rate = self._interest_rates.get(quote_currency, 0)
        
        rate_differential = base_rate - quote_rate
        
        # Determinar viés
        if rate_differential > 0.5:
            bias = "base_bullish"
            bias_text = f"{base_currency} favorecido pelo diferencial de juros"
        elif rate_differential < -0.5:
            bias = "quote_bullish"
            bias_text = f"{quote_currency} favorecido pelo diferencial de juros"
        else:
            bias = "neutral"
            bias_text = "Diferencial de juros neutro"
        
        return {
            "base_currency": base_currency,
            "quote_currency": quote_currency,
            "base_rate": base_rate,
            "quote_rate": quote_rate,
            "differential": round(rate_differential, 2),
            "bias": bias,
            "analysis": bias_text
        }
    
    def get_full_context(
        self,
        symbol: str,
        events: List[CalendarEvent],
        cot_data: Optional[COTData],
        sentiment_score: float
    ) -> Dict[str, Any]:
        """
        Obtém contexto macroeconômico completo
        
        Args:
            symbol: Símbolo
            events: Eventos do calendário
            cot_data: Dados COT
            sentiment_score: Score de sentimento
            
        Returns:
            Contexto macro completo
        """
        # Extrair moedas do símbolo
        if symbol.upper() == "XAUUSD":
            base = "XAU"
            quote = "USD"
        else:
            base = symbol[:3].upper()
            quote = symbol[3:6].upper()
        
        # Análises individuais
        calendar_analysis = self.analyze_calendar(events, symbol)
        cot_analysis = self.analyze_cot(cot_data)
        monetary_analysis = self.analyze_monetary_policy(base, quote)
        
        # Determinar bias geral
        overall_bias = self._determine_overall_bias(
            calendar_analysis,
            cot_analysis,
            monetary_analysis,
            sentiment_score
        )
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "calendar": calendar_analysis,
            "cot": cot_analysis,
            "monetary_policy": monetary_analysis,
            "sentiment_score": sentiment_score,
            "overall_bias": overall_bias,
            "trading_allowed": calendar_analysis["safe_to_trade"]
        }
    
    def _determine_overall_bias(
        self,
        calendar: Dict,
        cot: Dict,
        monetary: Dict,
        sentiment: float
    ) -> Dict[str, Any]:
        """Determina bias geral do contexto macro"""
        bullish_factors = 0
        bearish_factors = 0
        
        # Sentimento
        if sentiment > 0.2:
            bullish_factors += 1
        elif sentiment < -0.2:
            bearish_factors += 1
        
        # COT
        if cot.get("available"):
            if cot.get("speculator_bias") == "long":
                bullish_factors += 1
            else:
                bearish_factors += 1
        
        # Política monetária
        if monetary.get("bias") == "base_bullish":
            bullish_factors += 1
        elif monetary.get("bias") == "quote_bullish":
            bearish_factors += 1
        
        # Determinar direção
        if bullish_factors > bearish_factors:
            direction = "bullish"
            direction_pt = "Alta"
        elif bearish_factors > bullish_factors:
            direction = "bearish"
            direction_pt = "Baixa"
        else:
            direction = "neutral"
            direction_pt = "Neutro"
        
        strength = abs(bullish_factors - bearish_factors)
        
        return {
            "direction": direction,
            "direction_pt": direction_pt,
            "strength": strength,
            "bullish_factors": bullish_factors,
            "bearish_factors": bearish_factors
        }
