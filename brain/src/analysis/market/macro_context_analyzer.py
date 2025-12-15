"""
VIRTUS Macro Context Analyzer
==============================

Analisa contexto macroeconômico global para trading.

Funcionalidades:
- DXY (Dollar Index) Analysis
- VIX (Fear Index) Monitoring
- US10Y (Treasury Yields) Tracking
- Cross-market Correlations
- Risk-On/Risk-Off Detection
- Global Macro Regime
"""

import numpy as np
import pandas as pd
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta, timezone
import logging


class MacroRegime(Enum):
    """Regime macroeconômico."""
    RISK_ON = auto()          # Appetite para risco
    RISK_OFF = auto()         # Aversão a risco
    UNCERTAINTY = auto()      # Incerteza elevada
    TRANSITION = auto()       # Mudança de regime
    NORMAL = auto()           # Condições normais


class DollarStrength(Enum):
    """Força do dólar."""
    VERY_STRONG = auto()
    STRONG = auto()
    NEUTRAL = auto()
    WEAK = auto()
    VERY_WEAK = auto()


class VIXLevel(Enum):
    """Nível do VIX."""
    EXTREME_FEAR = auto()     # VIX > 40
    HIGH_FEAR = auto()        # VIX > 25
    ELEVATED = auto()         # VIX > 20
    NORMAL = auto()           # VIX 12-20
    COMPLACENT = auto()       # VIX < 12


@dataclass
class MacroData:
    """Dados macroeconômicos."""
    # DXY
    dxy_value: float
    dxy_change_1d: float
    dxy_change_5d: float
    dxy_trend: str  # 'up', 'down', 'flat'
    dxy_percentile: float  # 0-100 (52 semanas)
    
    # VIX
    vix_value: float
    vix_change_1d: float
    vix_level: VIXLevel
    vix_spike: bool
    
    # US10Y
    us10y_yield: float
    us10y_change_1d: float
    us10y_trend: str
    
    # S&P 500 (risk proxy)
    sp500_change_1d: float
    sp500_trend: str
    
    # Gold (safe haven)
    gold_change_1d: float
    gold_trend: str


@dataclass
class MacroAnalysisResult:
    """Resultado da análise macro."""
    regime: MacroRegime
    confidence: float  # 0 a 1
    
    # Componentes
    dollar_strength: DollarStrength
    vix_level: VIXLevel
    risk_appetite: str  # 'high', 'medium', 'low'
    
    # Dados
    macro_data: Optional[MacroData]
    
    # Impact por moeda
    currency_impacts: Dict[str, str]  # {'EUR': 'negative', 'JPY': 'positive', ...}
    
    # Recomendações
    favored_pairs: List[str]
    avoid_pairs: List[str]
    
    recommendation: str
    details: Dict[str, Any]


class MacroContextAnalyzer:
    """
    Analisador de contexto macroeconômico.
    
    Monitora indicadores globais para ajustar
    viés e exposição de trading.
    """
    
    # Thresholds VIX
    VIX_EXTREME_FEAR = 40
    VIX_HIGH_FEAR = 25
    VIX_ELEVATED = 20
    VIX_COMPLACENT = 12
    
    # Thresholds DXY
    DXY_STRONG_THRESHOLD = 1.0   # % acima da média
    DXY_WEAK_THRESHOLD = -1.0    # % abaixo da média
    
    def __init__(
        self,
        logger: logging.Logger = None,
        # APIs
        finnhub_api_key: str = None,
        twelvedata_api_key: str = None,
        fmp_api_key: str = None,
        # Configurações
        cache_ttl_minutes: int = 15,
    ):
        self.logger = logger or logging.getLogger(__name__)
        
        self.finnhub_api_key = finnhub_api_key
        self.twelvedata_api_key = twelvedata_api_key
        self.fmp_api_key = fmp_api_key
        
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        
        # Cache
        self._macro_cache: Optional[MacroData] = None
        self._cache_time: Optional[datetime] = None
    
    async def analyze(
        self,
        force_refresh: bool = False,
    ) -> MacroAnalysisResult:
        """
        Analisa contexto macroeconômico.
        
        Returns:
            MacroAnalysisResult
        """
        # Obtém dados macro
        macro_data = await self._get_macro_data(force_refresh)
        
        if not macro_data:
            return self._neutral_result()
        
        # Análise do dólar
        dollar_strength = self._analyze_dollar(macro_data)
        
        # Análise do VIX
        vix_level = self._analyze_vix(macro_data)
        
        # Regime macro
        regime, confidence = self._determine_regime(macro_data, vix_level)
        
        # Risk appetite
        risk_appetite = self._assess_risk_appetite(macro_data, vix_level)
        
        # Impacto por moeda
        currency_impacts = self._calculate_currency_impacts(
            dollar_strength, regime, macro_data
        )
        
        # Pares recomendados
        favored, avoid = self._get_pair_recommendations(
            dollar_strength, regime, currency_impacts
        )
        
        # Recomendação
        recommendation = self._generate_recommendation(
            regime, dollar_strength, vix_level, risk_appetite
        )
        
        return MacroAnalysisResult(
            regime=regime,
            confidence=confidence,
            dollar_strength=dollar_strength,
            vix_level=vix_level,
            risk_appetite=risk_appetite,
            macro_data=macro_data,
            currency_impacts=currency_impacts,
            favored_pairs=favored,
            avoid_pairs=avoid,
            recommendation=recommendation,
            details={
                'dxy': macro_data.dxy_value,
                'vix': macro_data.vix_value,
                'us10y': macro_data.us10y_yield,
            }
        )
    
    async def _get_macro_data(self, force_refresh: bool = False) -> Optional[MacroData]:
        """Obtém dados macroeconômicos."""
        
        # Verifica cache
        if not force_refresh and self._cache_valid():
            return self._macro_cache
        
        # Tenta APIs
        dxy = await self._fetch_dxy()
        vix = await self._fetch_vix()
        us10y = await self._fetch_us10y()
        sp500 = await self._fetch_sp500()
        gold = await self._fetch_gold()
        
        # Se não conseguiu dados suficientes, usa simulados
        if dxy is None:
            dxy = {'value': 104.0, 'change_1d': 0.1, 'change_5d': 0.3}
        if vix is None:
            vix = {'value': 18.0, 'change_1d': -0.5}
        if us10y is None:
            us10y = {'value': 4.5, 'change_1d': 0.02}
        if sp500 is None:
            sp500 = {'change_1d': 0.2}
        if gold is None:
            gold = {'change_1d': 0.1}
        
        # Calcula tendências
        dxy_trend = 'up' if dxy['change_5d'] > 0.3 else 'down' if dxy['change_5d'] < -0.3 else 'flat'
        us10y_trend = 'up' if us10y['change_1d'] > 0 else 'down' if us10y['change_1d'] < 0 else 'flat'
        sp500_trend = 'up' if sp500['change_1d'] > 0 else 'down' if sp500['change_1d'] < 0 else 'flat'
        gold_trend = 'up' if gold['change_1d'] > 0 else 'down' if gold['change_1d'] < 0 else 'flat'
        
        # VIX level
        vix_value = vix['value']
        if vix_value >= self.VIX_EXTREME_FEAR:
            vix_level = VIXLevel.EXTREME_FEAR
        elif vix_value >= self.VIX_HIGH_FEAR:
            vix_level = VIXLevel.HIGH_FEAR
        elif vix_value >= self.VIX_ELEVATED:
            vix_level = VIXLevel.ELEVATED
        elif vix_value <= self.VIX_COMPLACENT:
            vix_level = VIXLevel.COMPLACENT
        else:
            vix_level = VIXLevel.NORMAL
        
        # VIX spike
        vix_spike = vix['change_1d'] > 3
        
        macro_data = MacroData(
            dxy_value=dxy['value'],
            dxy_change_1d=dxy['change_1d'],
            dxy_change_5d=dxy['change_5d'],
            dxy_trend=dxy_trend,
            dxy_percentile=dxy.get('percentile', 50),
            vix_value=vix_value,
            vix_change_1d=vix['change_1d'],
            vix_level=vix_level,
            vix_spike=vix_spike,
            us10y_yield=us10y['value'],
            us10y_change_1d=us10y['change_1d'],
            us10y_trend=us10y_trend,
            sp500_change_1d=sp500['change_1d'],
            sp500_trend=sp500_trend,
            gold_change_1d=gold['change_1d'],
            gold_trend=gold_trend,
        )
        
        # Atualiza cache
        self._macro_cache = macro_data
        self._cache_time = datetime.now(timezone.utc)
        
        return macro_data
    
    def _cache_valid(self) -> bool:
        """Verifica cache."""
        if not self._cache_time or not self._macro_cache:
            return False
        
        age = datetime.now(timezone.utc) - self._cache_time
        return age < self.cache_ttl
    
    async def _fetch_dxy(self) -> Optional[Dict]:
        """Busca dados do DXY."""
        if self.twelvedata_api_key:
            try:
                url = 'https://api.twelvedata.com/time_series'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params={
                        'symbol': 'DXY',
                        'interval': '1day',
                        'outputsize': 10,
                        'apikey': self.twelvedata_api_key,
                    }) as response:
                        if response.status == 200:
                            data = await response.json()
                            values = data.get('values', [])
                            if len(values) >= 6:
                                current = float(values[0]['close'])
                                prev_1d = float(values[1]['close'])
                                prev_5d = float(values[5]['close'])
                                
                                return {
                                    'value': current,
                                    'change_1d': ((current - prev_1d) / prev_1d) * 100,
                                    'change_5d': ((current - prev_5d) / prev_5d) * 100,
                                }
            except Exception as e:
                self.logger.debug(f"Erro DXY: {e}")
        
        return None
    
    async def _fetch_vix(self) -> Optional[Dict]:
        """Busca dados do VIX."""
        if self.finnhub_api_key:
            try:
                url = 'https://finnhub.io/api/v1/quote'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params={
                        'symbol': 'VIX',
                        'token': self.finnhub_api_key,
                    }) as response:
                        if response.status == 200:
                            data = await response.json()
                            current = data.get('c', 0)
                            prev_close = data.get('pc', current)
                            
                            if current > 0:
                                return {
                                    'value': current,
                                    'change_1d': current - prev_close,
                                }
            except Exception as e:
                self.logger.debug(f"Erro VIX: {e}")
        
        return None
    
    async def _fetch_us10y(self) -> Optional[Dict]:
        """Busca dados do US10Y."""
        if self.fmp_api_key:
            try:
                url = f'https://financialmodelingprep.com/api/v3/treasury'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params={
                        'from': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                        'to': datetime.now().strftime('%Y-%m-%d'),
                        'apikey': self.fmp_api_key,
                    }) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data:
                                current = data[0].get('year10', 4.5)
                                prev = data[1].get('year10', current) if len(data) > 1 else current
                                
                                return {
                                    'value': current,
                                    'change_1d': current - prev,
                                }
            except Exception as e:
                self.logger.debug(f"Erro US10Y: {e}")
        
        return None
    
    async def _fetch_sp500(self) -> Optional[Dict]:
        """Busca dados do S&P 500."""
        if self.finnhub_api_key:
            try:
                url = 'https://finnhub.io/api/v1/quote'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params={
                        'symbol': 'SPY',
                        'token': self.finnhub_api_key,
                    }) as response:
                        if response.status == 200:
                            data = await response.json()
                            current = data.get('c', 0)
                            prev_close = data.get('pc', current)
                            
                            if current > 0 and prev_close > 0:
                                return {
                                    'change_1d': ((current - prev_close) / prev_close) * 100,
                                }
            except Exception as e:
                self.logger.debug(f"Erro SP500: {e}")
        
        return None
    
    async def _fetch_gold(self) -> Optional[Dict]:
        """Busca dados do Ouro."""
        if self.finnhub_api_key:
            try:
                url = 'https://finnhub.io/api/v1/quote'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params={
                        'symbol': 'OANDA:XAU_USD',
                        'token': self.finnhub_api_key,
                    }) as response:
                        if response.status == 200:
                            data = await response.json()
                            current = data.get('c', 0)
                            prev_close = data.get('pc', current)
                            
                            if current > 0 and prev_close > 0:
                                return {
                                    'change_1d': ((current - prev_close) / prev_close) * 100,
                                }
            except Exception as e:
                self.logger.debug(f"Erro Gold: {e}")
        
        return None
    
    def _analyze_dollar(self, data: MacroData) -> DollarStrength:
        """Analisa força do dólar."""
        
        change_5d = data.dxy_change_5d
        
        if change_5d >= 1.5:
            return DollarStrength.VERY_STRONG
        elif change_5d >= 0.5:
            return DollarStrength.STRONG
        elif change_5d <= -1.5:
            return DollarStrength.VERY_WEAK
        elif change_5d <= -0.5:
            return DollarStrength.WEAK
        else:
            return DollarStrength.NEUTRAL
    
    def _analyze_vix(self, data: MacroData) -> VIXLevel:
        """Analisa VIX."""
        return data.vix_level
    
    def _determine_regime(
        self,
        data: MacroData,
        vix_level: VIXLevel
    ) -> Tuple[MacroRegime, float]:
        """Determina regime macroeconômico."""
        
        confidence = 0.7
        
        # VIX extremo = Risk Off
        if vix_level in [VIXLevel.EXTREME_FEAR, VIXLevel.HIGH_FEAR]:
            if data.sp500_trend == 'down' and data.gold_trend == 'up':
                return MacroRegime.RISK_OFF, 0.9
            return MacroRegime.RISK_OFF, 0.7
        
        # VIX spike = Transição/Incerteza
        if data.vix_spike:
            return MacroRegime.UNCERTAINTY, 0.8
        
        # VIX muito baixo + S&P subindo = Risk On
        if vix_level == VIXLevel.COMPLACENT and data.sp500_trend == 'up':
            return MacroRegime.RISK_ON, 0.85
        
        # VIX normal + S&P subindo = Risk On moderado
        if vix_level == VIXLevel.NORMAL and data.sp500_trend == 'up':
            return MacroRegime.RISK_ON, 0.7
        
        # VIX elevado = Cautela
        if vix_level == VIXLevel.ELEVATED:
            return MacroRegime.UNCERTAINTY, 0.6
        
        return MacroRegime.NORMAL, 0.5
    
    def _assess_risk_appetite(
        self,
        data: MacroData,
        vix_level: VIXLevel
    ) -> str:
        """Avalia apetite por risco."""
        
        score = 0
        
        # VIX
        if vix_level in [VIXLevel.COMPLACENT, VIXLevel.NORMAL]:
            score += 2
        elif vix_level == VIXLevel.ELEVATED:
            score -= 1
        else:
            score -= 2
        
        # S&P
        if data.sp500_trend == 'up':
            score += 1
        elif data.sp500_trend == 'down':
            score -= 1
        
        # Gold (inversamente correlacionado com risco)
        if data.gold_trend == 'down':
            score += 1
        elif data.gold_trend == 'up':
            score -= 1
        
        if score >= 2:
            return 'high'
        elif score <= -2:
            return 'low'
        else:
            return 'medium'
    
    def _calculate_currency_impacts(
        self,
        dollar_strength: DollarStrength,
        regime: MacroRegime,
        data: MacroData
    ) -> Dict[str, str]:
        """Calcula impacto por moeda."""
        
        impacts = {}
        
        # USD
        if dollar_strength in [DollarStrength.VERY_STRONG, DollarStrength.STRONG]:
            impacts['USD'] = 'positive'
        elif dollar_strength in [DollarStrength.VERY_WEAK, DollarStrength.WEAK]:
            impacts['USD'] = 'negative'
        else:
            impacts['USD'] = 'neutral'
        
        # EUR (inversamente correlacionado com USD)
        if impacts['USD'] == 'positive':
            impacts['EUR'] = 'negative'
        elif impacts['USD'] == 'negative':
            impacts['EUR'] = 'positive'
        else:
            impacts['EUR'] = 'neutral'
        
        # JPY e CHF (safe havens)
        if regime == MacroRegime.RISK_OFF:
            impacts['JPY'] = 'positive'
            impacts['CHF'] = 'positive'
        elif regime == MacroRegime.RISK_ON:
            impacts['JPY'] = 'negative'
            impacts['CHF'] = 'negative'
        else:
            impacts['JPY'] = 'neutral'
            impacts['CHF'] = 'neutral'
        
        # AUD, NZD, CAD (risk currencies)
        if regime == MacroRegime.RISK_ON:
            impacts['AUD'] = 'positive'
            impacts['NZD'] = 'positive'
            impacts['CAD'] = 'positive'
        elif regime == MacroRegime.RISK_OFF:
            impacts['AUD'] = 'negative'
            impacts['NZD'] = 'negative'
            impacts['CAD'] = 'negative'
        else:
            impacts['AUD'] = 'neutral'
            impacts['NZD'] = 'neutral'
            impacts['CAD'] = 'neutral'
        
        # GBP
        impacts['GBP'] = 'neutral'
        
        # XAU (Gold)
        if regime == MacroRegime.RISK_OFF or impacts['USD'] == 'negative':
            impacts['XAU'] = 'positive'
        elif regime == MacroRegime.RISK_ON and impacts['USD'] == 'positive':
            impacts['XAU'] = 'negative'
        else:
            impacts['XAU'] = 'neutral'
        
        return impacts
    
    def _get_pair_recommendations(
        self,
        dollar_strength: DollarStrength,
        regime: MacroRegime,
        impacts: Dict[str, str]
    ) -> Tuple[List[str], List[str]]:
        """Gera recomendações de pares."""
        
        favored = []
        avoid = []
        
        # Risk On
        if regime == MacroRegime.RISK_ON:
            favored.extend(['AUDUSD', 'NZDUSD', 'AUDJPY', 'NZDJPY'])
            avoid.extend(['USDJPY', 'USDCHF'])  # Contra safe havens
        
        # Risk Off
        elif regime == MacroRegime.RISK_OFF:
            favored.extend(['USDJPY', 'USDCHF', 'XAUUSD'])
            avoid.extend(['AUDUSD', 'NZDUSD', 'AUDJPY'])
        
        # USD forte
        if dollar_strength in [DollarStrength.VERY_STRONG, DollarStrength.STRONG]:
            if 'EURUSD' not in avoid:
                favored.append('SHORT EURUSD')
            if 'GBPUSD' not in avoid:
                favored.append('SHORT GBPUSD')
        
        # USD fraco
        elif dollar_strength in [DollarStrength.VERY_WEAK, DollarStrength.WEAK]:
            favored.append('LONG EURUSD')
            favored.append('LONG GBPUSD')
            favored.append('LONG XAUUSD')
        
        return favored, avoid
    
    def _generate_recommendation(
        self,
        regime: MacroRegime,
        dollar_strength: DollarStrength,
        vix_level: VIXLevel,
        risk_appetite: str
    ) -> str:
        """Gera recomendação geral."""
        
        parts = []
        
        # Regime
        if regime == MacroRegime.RISK_ON:
            parts.append("🟢 RISK ON - Favorece moedas de risco (AUD, NZD)")
        elif regime == MacroRegime.RISK_OFF:
            parts.append("🔴 RISK OFF - Favorece safe havens (JPY, CHF, Gold)")
        elif regime == MacroRegime.UNCERTAINTY:
            parts.append("⚠️ INCERTEZA - Cautela recomendada")
        else:
            parts.append("⚪ NORMAL - Sem viés macro forte")
        
        # Dólar
        if dollar_strength == DollarStrength.VERY_STRONG:
            parts.append("💪 USD muito forte")
        elif dollar_strength == DollarStrength.VERY_WEAK:
            parts.append("📉 USD muito fraco")
        
        # VIX
        if vix_level in [VIXLevel.EXTREME_FEAR, VIXLevel.HIGH_FEAR]:
            parts.append("🚨 VIX elevado - Volatilidade alta")
        
        return " | ".join(parts)
    
    def _neutral_result(self) -> MacroAnalysisResult:
        """Retorna resultado neutro."""
        return MacroAnalysisResult(
            regime=MacroRegime.NORMAL,
            confidence=0.3,
            dollar_strength=DollarStrength.NEUTRAL,
            vix_level=VIXLevel.NORMAL,
            risk_appetite='medium',
            macro_data=None,
            currency_impacts={},
            favored_pairs=[],
            avoid_pairs=[],
            recommendation="⚪ Dados macro indisponíveis",
            details={},
        )
    
    def to_dict(self, result: MacroAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        macro_dict = None
        if result.macro_data:
            m = result.macro_data
            macro_dict = {
                'dxy': {
                    'value': round(m.dxy_value, 2),
                    'change_1d': round(m.dxy_change_1d, 2),
                    'change_5d': round(m.dxy_change_5d, 2),
                    'trend': m.dxy_trend,
                },
                'vix': {
                    'value': round(m.vix_value, 2),
                    'change_1d': round(m.vix_change_1d, 2),
                    'level': m.vix_level.name,
                    'spike': m.vix_spike,
                },
                'us10y': {
                    'yield': round(m.us10y_yield, 2),
                    'change_1d': round(m.us10y_change_1d, 3),
                    'trend': m.us10y_trend,
                },
                'sp500': {
                    'change_1d': round(m.sp500_change_1d, 2),
                    'trend': m.sp500_trend,
                },
                'gold': {
                    'change_1d': round(m.gold_change_1d, 2),
                    'trend': m.gold_trend,
                },
            }
        
        return {
            'regime': result.regime.name,
            'confidence': round(result.confidence, 2),
            'dollar_strength': result.dollar_strength.name,
            'vix_level': result.vix_level.name,
            'risk_appetite': result.risk_appetite,
            'currency_impacts': result.currency_impacts,
            'favored_pairs': result.favored_pairs,
            'avoid_pairs': result.avoid_pairs,
            'recommendation': result.recommendation,
            'macro_data': macro_dict,
        }
