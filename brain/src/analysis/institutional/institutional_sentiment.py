"""
VIRTUS Institutional Sentiment Analyzer
========================================

Analisa sentimento institucional através de:
- Dados COT (Commitment of Traders)
- Posições de grandes players
- Fluxo institucional
- Sinais contrários

Funcionalidades:
- COT Analysis (Large Speculators, Commercial, Small Traders)
- Net Position Change
- Extremes Detection
- Contrarian Signals
"""

import numpy as np
import pandas as pd
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta, timezone
import logging


class SentimentBias(Enum):
    """Viés do sentimento."""
    EXTREME_BULLISH = auto()
    BULLISH = auto()
    NEUTRAL = auto()
    BEARISH = auto()
    EXTREME_BEARISH = auto()


class TraderType(Enum):
    """Tipo de trader no COT."""
    COMMERCIAL = auto()        # Hedgers (geralmente contrários)
    LARGE_SPECULATORS = auto() # Fundos, instituições
    SMALL_TRADERS = auto()     # Retail


@dataclass
class COTData:
    """Dados do COT Report."""
    report_date: datetime
    symbol: str
    
    # Commercial (Hedgers)
    commercial_long: int
    commercial_short: int
    commercial_net: int
    
    # Large Speculators
    large_spec_long: int
    large_spec_short: int
    large_spec_net: int
    
    # Small Traders (Retail)
    small_traders_long: int
    small_traders_short: int
    small_traders_net: int
    
    # Open Interest
    open_interest: int
    oi_change: int
    
    # Calculados
    commercial_pct_long: float = 0.0
    large_spec_pct_long: float = 0.0
    small_traders_pct_long: float = 0.0


@dataclass
class SentimentAnalysisResult:
    """Resultado da análise de sentimento."""
    bias: SentimentBias
    confidence: float  # 0 a 1
    
    # COT
    cot_data: Optional[COTData]
    cot_signal: str  # 'LONG', 'SHORT', 'NEUTRAL'
    
    # Análise
    institutional_bias: str
    retail_bias: str
    contrarian_signal: Optional[str]  # Sinal contrário ao retail
    
    # Extremos
    is_extreme: bool
    extreme_type: Optional[str]  # 'overbought_retail', 'oversold_retail', etc.
    
    # Scores
    scores: Dict[str, float]
    recommendation: str
    details: Dict[str, Any]


# Mapeamento de símbolos para códigos COT
COT_SYMBOL_MAP = {
    'EURUSD': 'EUR',
    'GBPUSD': 'GBP', 
    'USDJPY': 'JPY',
    'AUDUSD': 'AUD',
    'USDCAD': 'CAD',
    'USDCHF': 'CHF',
    'NZDUSD': 'NZD',
    'XAUUSD': 'GOLD',
    'XAGUSD': 'SILVER',
}


class InstitutionalSentimentAnalyzer:
    """
    Analisador de sentimento institucional.
    
    Usa dados COT e outros indicadores para identificar
    posicionamento institucional e sinais contrários.
    """
    
    # Thresholds para extremos
    EXTREME_THRESHOLD = 0.8  # 80% em uma direção
    
    def __init__(
        self,
        logger: logging.Logger = None,
        # API
        quandl_api_key: str = None,
        # Configurações
        lookback_weeks: int = 52,
        extreme_percentile: float = 90,
    ):
        self.logger = logger or logging.getLogger(__name__)
        
        self.quandl_api_key = quandl_api_key
        self.lookback_weeks = lookback_weeks
        self.extreme_percentile = extreme_percentile
        
        # Cache de dados COT
        self._cot_cache: Dict[str, List[COTData]] = {}
        self._cache_time: Dict[str, datetime] = {}
    
    async def analyze(
        self,
        symbol: str,
        retail_sentiment: float = None,  # -1 a 1, de APIs externas
    ) -> SentimentAnalysisResult:
        """
        Analisa sentimento institucional.
        
        Args:
            symbol: Par de moedas
            retail_sentiment: Sentimento retail externo (opcional)
            
        Returns:
            SentimentAnalysisResult
        """
        # Obtém dados COT
        cot_data = await self._get_cot_data(symbol)
        
        scores = {}
        
        # Análise COT
        cot_signal, cot_score = self._analyze_cot(cot_data)
        scores['cot'] = cot_score
        
        # Bias institucional
        inst_bias, inst_score = self._analyze_institutional_bias(cot_data)
        scores['institutional'] = inst_score
        
        # Bias retail
        retail_bias, retail_score = self._analyze_retail_bias(
            cot_data, retail_sentiment
        )
        scores['retail'] = retail_score
        
        # Sinal contrário
        contrarian_signal, contrarian_score = self._get_contrarian_signal(
            cot_data, retail_sentiment
        )
        scores['contrarian'] = contrarian_score
        
        # Detecta extremos
        is_extreme, extreme_type = self._detect_extremes(cot_data, retail_sentiment)
        
        # Calcula bias geral
        overall_score = (
            cot_score * 0.4 +
            inst_score * 0.3 +
            contrarian_score * 0.3
        )
        
        bias = self._score_to_bias(overall_score)
        
        # Confidence
        confidence = abs(overall_score)
        
        # Recomendação
        recommendation = self._generate_recommendation(
            bias, cot_signal, contrarian_signal, is_extreme
        )
        
        return SentimentAnalysisResult(
            bias=bias,
            confidence=confidence,
            cot_data=cot_data,
            cot_signal=cot_signal,
            institutional_bias=inst_bias,
            retail_bias=retail_bias,
            contrarian_signal=contrarian_signal,
            is_extreme=is_extreme,
            extreme_type=extreme_type,
            scores=scores,
            recommendation=recommendation,
            details={
                'overall_score': round(overall_score, 2),
                'symbol': symbol,
            }
        )
    
    async def _get_cot_data(self, symbol: str) -> Optional[COTData]:
        """Obtém dados COT para o símbolo."""
        
        # Verifica cache
        if symbol in self._cot_cache:
            cache_age = datetime.now() - self._cache_time.get(symbol, datetime.min)
            if cache_age < timedelta(hours=24):
                data_list = self._cot_cache[symbol]
                return data_list[-1] if data_list else None
        
        # Tenta obter de API
        if self.quandl_api_key:
            try:
                cot_list = await self._fetch_cot_quandl(symbol)
                if cot_list:
                    self._cot_cache[symbol] = cot_list
                    self._cache_time[symbol] = datetime.now()
                    return cot_list[-1]
            except Exception as e:
                self.logger.warning(f"Erro buscando COT: {e}")
        
        # Retorna dados simulados para teste
        return self._generate_simulated_cot(symbol)
    
    async def _fetch_cot_quandl(self, symbol: str) -> List[COTData]:
        """Busca dados COT do Quandl/NASDAQ Data Link."""
        cot_symbol = COT_SYMBOL_MAP.get(symbol.upper(), symbol[:3])
        
        # URL do Quandl
        url = f"https://data.nasdaq.com/api/v3/datasets/CFTC/{cot_symbol}_F_L_ALL.json"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params={'api_key': self.quandl_api_key, 'rows': self.lookback_weeks}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_quandl_cot(data, symbol)
        
        return []
    
    def _parse_quandl_cot(self, data: Dict, symbol: str) -> List[COTData]:
        """Parse dados do Quandl."""
        cot_list = []
        
        dataset = data.get('dataset', {})
        columns = dataset.get('column_names', [])
        rows = dataset.get('data', [])
        
        for row in rows:
            try:
                row_dict = dict(zip(columns, row))
                
                cot = COTData(
                    report_date=datetime.strptime(row_dict.get('Date', ''), '%Y-%m-%d'),
                    symbol=symbol,
                    commercial_long=int(row_dict.get('Commercial Long', 0)),
                    commercial_short=int(row_dict.get('Commercial Short', 0)),
                    commercial_net=int(row_dict.get('Commercial Long', 0)) - int(row_dict.get('Commercial Short', 0)),
                    large_spec_long=int(row_dict.get('Non-Commercial Long', 0)),
                    large_spec_short=int(row_dict.get('Non-Commercial Short', 0)),
                    large_spec_net=int(row_dict.get('Non-Commercial Long', 0)) - int(row_dict.get('Non-Commercial Short', 0)),
                    small_traders_long=int(row_dict.get('Nonreportable Long', 0)),
                    small_traders_short=int(row_dict.get('Nonreportable Short', 0)),
                    small_traders_net=int(row_dict.get('Nonreportable Long', 0)) - int(row_dict.get('Nonreportable Short', 0)),
                    open_interest=int(row_dict.get('Open Interest', 0)),
                    oi_change=int(row_dict.get('Change in Open Interest', 0)),
                )
                
                # Calcula percentuais
                total_long = cot.commercial_long + cot.large_spec_long + cot.small_traders_long
                if total_long > 0:
                    cot.commercial_pct_long = cot.commercial_long / total_long
                    cot.large_spec_pct_long = cot.large_spec_long / total_long
                    cot.small_traders_pct_long = cot.small_traders_long / total_long
                
                cot_list.append(cot)
            except Exception as e:
                self.logger.debug(f"Erro parsing COT row: {e}")
        
        return cot_list
    
    def _generate_simulated_cot(self, symbol: str) -> COTData:
        """Gera dados COT simulados para teste."""
        import random
        
        # Simula dados realistas
        oi = random.randint(100000, 500000)
        
        # Large specs geralmente seguem tendência
        large_spec_long = int(oi * random.uniform(0.3, 0.5))
        large_spec_short = int(oi * random.uniform(0.2, 0.4))
        
        # Commercials são hedgers (geralmente contrários)
        commercial_long = int(oi * random.uniform(0.2, 0.35))
        commercial_short = int(oi * random.uniform(0.25, 0.4))
        
        # Retail
        small_long = int(oi * random.uniform(0.1, 0.2))
        small_short = int(oi * random.uniform(0.1, 0.2))
        
        return COTData(
            report_date=datetime.now(timezone.utc) - timedelta(days=3),
            symbol=symbol,
            commercial_long=commercial_long,
            commercial_short=commercial_short,
            commercial_net=commercial_long - commercial_short,
            large_spec_long=large_spec_long,
            large_spec_short=large_spec_short,
            large_spec_net=large_spec_long - large_spec_short,
            small_traders_long=small_long,
            small_traders_short=small_short,
            small_traders_net=small_long - small_short,
            open_interest=oi,
            oi_change=random.randint(-5000, 5000),
            commercial_pct_long=commercial_long / (commercial_long + commercial_short) if (commercial_long + commercial_short) > 0 else 0.5,
            large_spec_pct_long=large_spec_long / (large_spec_long + large_spec_short) if (large_spec_long + large_spec_short) > 0 else 0.5,
            small_traders_pct_long=small_long / (small_long + small_short) if (small_long + small_short) > 0 else 0.5,
        )
    
    def _analyze_cot(self, cot: Optional[COTData]) -> Tuple[str, float]:
        """Analisa dados COT."""
        if not cot:
            return 'NEUTRAL', 0.0
        
        # Large speculators são o principal indicador
        total = abs(cot.large_spec_long) + abs(cot.large_spec_short)
        if total == 0:
            return 'NEUTRAL', 0.0
        
        net_pct = cot.large_spec_net / total
        
        if net_pct > 0.3:
            return 'LONG', min(net_pct, 1.0)
        elif net_pct < -0.3:
            return 'SHORT', max(net_pct, -1.0)
        else:
            return 'NEUTRAL', net_pct
    
    def _analyze_institutional_bias(self, cot: Optional[COTData]) -> Tuple[str, float]:
        """Analisa viés institucional."""
        if not cot:
            return 'NEUTRAL', 0.0
        
        # Combina large specs e commercials
        large_spec_score = cot.large_spec_pct_long - 0.5  # -0.5 a 0.5
        
        # Commercials são contrários, então invertemos
        commercial_score = -(cot.commercial_pct_long - 0.5)
        
        # Peso maior para large specs
        combined = large_spec_score * 0.7 + commercial_score * 0.3
        
        if combined > 0.15:
            return 'BULLISH', combined * 2
        elif combined < -0.15:
            return 'BEARISH', combined * 2
        else:
            return 'NEUTRAL', combined * 2
    
    def _analyze_retail_bias(
        self,
        cot: Optional[COTData],
        external_sentiment: float = None
    ) -> Tuple[str, float]:
        """Analisa viés do retail."""
        
        scores = []
        
        # COT small traders
        if cot:
            small_score = cot.small_traders_pct_long - 0.5
            scores.append(small_score * 2)
        
        # Sentimento externo
        if external_sentiment is not None:
            scores.append(external_sentiment)
        
        if not scores:
            return 'NEUTRAL', 0.0
        
        avg_score = np.mean(scores)
        
        if avg_score > 0.2:
            return 'BULLISH', avg_score
        elif avg_score < -0.2:
            return 'BEARISH', avg_score
        else:
            return 'NEUTRAL', avg_score
    
    def _get_contrarian_signal(
        self,
        cot: Optional[COTData],
        retail_sentiment: float = None
    ) -> Tuple[Optional[str], float]:
        """Gera sinal contrário ao retail."""
        
        # Retail muito bullish = sinal SHORT
        # Retail muito bearish = sinal LONG
        
        retail_score = 0.0
        
        if cot:
            retail_score = cot.small_traders_pct_long - 0.5
        
        if retail_sentiment is not None:
            retail_score = (retail_score + retail_sentiment) / 2
        
        # Só gera sinal contrário em extremos
        if retail_score > self.EXTREME_THRESHOLD - 0.5:
            return 'SHORT', -retail_score
        elif retail_score < -(self.EXTREME_THRESHOLD - 0.5):
            return 'LONG', -retail_score
        
        return None, 0.0
    
    def _detect_extremes(
        self,
        cot: Optional[COTData],
        retail_sentiment: float = None
    ) -> Tuple[bool, Optional[str]]:
        """Detecta extremos de sentimento."""
        
        if not cot and retail_sentiment is None:
            return False, None
        
        # Retail em extremo
        if cot:
            if cot.small_traders_pct_long > self.EXTREME_THRESHOLD:
                return True, 'retail_extreme_bullish'
            elif cot.small_traders_pct_long < (1 - self.EXTREME_THRESHOLD):
                return True, 'retail_extreme_bearish'
        
        if retail_sentiment is not None:
            if retail_sentiment > 0.8:
                return True, 'external_extreme_bullish'
            elif retail_sentiment < -0.8:
                return True, 'external_extreme_bearish'
        
        # Large specs em extremo
        if cot:
            if cot.large_spec_pct_long > self.EXTREME_THRESHOLD:
                return True, 'institutional_extreme_bullish'
            elif cot.large_spec_pct_long < (1 - self.EXTREME_THRESHOLD):
                return True, 'institutional_extreme_bearish'
        
        return False, None
    
    def _score_to_bias(self, score: float) -> SentimentBias:
        """Converte score para bias."""
        if score >= 0.6:
            return SentimentBias.EXTREME_BULLISH
        elif score >= 0.2:
            return SentimentBias.BULLISH
        elif score <= -0.6:
            return SentimentBias.EXTREME_BEARISH
        elif score <= -0.2:
            return SentimentBias.BEARISH
        else:
            return SentimentBias.NEUTRAL
    
    def _generate_recommendation(
        self,
        bias: SentimentBias,
        cot_signal: str,
        contrarian_signal: Optional[str],
        is_extreme: bool
    ) -> str:
        """Gera recomendação baseada na análise."""
        
        if is_extreme and contrarian_signal:
            return f"⚠️ EXTREMO - Sinal contrário {contrarian_signal}"
        
        if bias == SentimentBias.EXTREME_BULLISH:
            return "🟢 Sentimento muito bullish - Cautela para longs tardios"
        elif bias == SentimentBias.EXTREME_BEARISH:
            return "🔴 Sentimento muito bearish - Cautela para shorts tardios"
        elif bias == SentimentBias.BULLISH:
            if cot_signal == 'LONG':
                return "🟢 Instituições e sentimento favorecem LONG"
            return "🟢 Sentimento favorece LONG"
        elif bias == SentimentBias.BEARISH:
            if cot_signal == 'SHORT':
                return "🔴 Instituições e sentimento favorecem SHORT"
            return "🔴 Sentimento favorece SHORT"
        else:
            return "⚪ Sentimento neutro - Sem viés claro"
    
    def to_dict(self, result: SentimentAnalysisResult) -> Dict[str, Any]:
        """Converte resultado para dicionário."""
        cot_dict = None
        if result.cot_data:
            cot = result.cot_data
            cot_dict = {
                'report_date': cot.report_date.isoformat(),
                'large_spec_net': cot.large_spec_net,
                'large_spec_pct_long': round(cot.large_spec_pct_long, 2),
                'commercial_net': cot.commercial_net,
                'commercial_pct_long': round(cot.commercial_pct_long, 2),
                'small_traders_net': cot.small_traders_net,
                'small_traders_pct_long': round(cot.small_traders_pct_long, 2),
                'open_interest': cot.open_interest,
            }
        
        return {
            'bias': result.bias.name,
            'confidence': round(result.confidence, 2),
            'cot_signal': result.cot_signal,
            'institutional_bias': result.institutional_bias,
            'retail_bias': result.retail_bias,
            'contrarian_signal': result.contrarian_signal,
            'is_extreme': result.is_extreme,
            'extreme_type': result.extreme_type,
            'recommendation': result.recommendation,
            'scores': {k: round(v, 2) for k, v in result.scores.items()},
            'cot_data': cot_dict,
        }
