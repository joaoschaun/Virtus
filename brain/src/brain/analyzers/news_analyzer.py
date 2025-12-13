"""
BRAIN - News Analyzer
Analisador de notícias
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from ...core.types import NewsItem, NewsImpact, SignalDirection
from ...core.logger import get_logger

logger = get_logger("brain.analyzer.news")


class NewsAnalyzer:
    """
    Analisador de notícias financeiras
    
    Responsabilidades:
    - Filtrar notícias relevantes
    - Agrupar por tema/símbolo
    - Identificar narrativas dominantes
    - Estimar impacto no mercado
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        
        # Palavras-chave por categoria
        self._keywords = {
            "bullish": [
                "rally", "surge", "jump", "soar", "gain", "rise", "up",
                "bullish", "optimistic", "growth", "strong", "beat", "exceed",
                "hawkish", "recovery", "boom", "record high"
            ],
            "bearish": [
                "drop", "fall", "plunge", "crash", "decline", "down",
                "bearish", "pessimistic", "weak", "miss", "disappoint",
                "dovish", "recession", "crisis", "concern", "fear"
            ],
            "gold_bullish": [
                "safe haven", "uncertainty", "geopolitical", "inflation",
                "fear", "risk off", "dollar weakness", "rate cut"
            ],
            "gold_bearish": [
                "risk on", "dollar strength", "rate hike", "taper",
                "strong economy", "yield rise"
            ]
        }
    
    def analyze(
        self,
        news_list: List[NewsItem],
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analisa lista de notícias
        
        Args:
            news_list: Lista de notícias
            symbol: Símbolo para análise específica
            
        Returns:
            Dict com análise completa
        """
        if not news_list:
            return self._empty_analysis()
        
        # Filtrar por símbolo se especificado
        if symbol:
            news_list = [
                n for n in news_list
                if symbol in n.symbols or not n.symbols
            ]
        
        # Análise básica
        analysis = {
            "total_news": len(news_list),
            "high_impact": len([n for n in news_list if n.impact == NewsImpact.HIGH]),
            "medium_impact": len([n for n in news_list if n.impact == NewsImpact.MEDIUM]),
            "low_impact": len([n for n in news_list if n.impact == NewsImpact.LOW]),
            "timestamp": datetime.now().isoformat()
        }
        
        # Análise de sentimento agregado
        sentiment_score, sentiment_direction = self._analyze_sentiment(news_list, symbol)
        analysis["sentiment_score"] = sentiment_score
        analysis["sentiment_direction"] = sentiment_direction.value if sentiment_direction else "neutral"
        
        # Narrativas dominantes
        analysis["dominant_themes"] = self._extract_themes(news_list)
        
        # Notícias mais importantes
        analysis["top_news"] = self._get_top_news(news_list, limit=5)
        
        # Resumo textual
        analysis["summary"] = self._generate_summary(news_list, symbol)
        
        # Bias de trading
        analysis["trading_bias"] = self._calculate_trading_bias(
            sentiment_score,
            analysis["high_impact"]
        )
        
        return analysis
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Retorna análise vazia"""
        return {
            "total_news": 0,
            "high_impact": 0,
            "medium_impact": 0,
            "low_impact": 0,
            "sentiment_score": 0.0,
            "sentiment_direction": "neutral",
            "dominant_themes": [],
            "top_news": [],
            "summary": "Sem notícias relevantes no momento.",
            "trading_bias": "neutral",
            "timestamp": datetime.now().isoformat()
        }
    
    def _analyze_sentiment(
        self,
        news_list: List[NewsItem],
        symbol: Optional[str]
    ) -> Tuple[float, Optional[SignalDirection]]:
        """
        Calcula sentimento agregado
        
        Returns:
            Tuple de (score -1 a 1, direção)
        """
        if not news_list:
            return 0.0, None
        
        # Usar sentimento já calculado ou analisar texto
        scores = []
        
        for news in news_list:
            if news.sentiment != 0.0:
                # Peso pelo impacto
                weight = self._impact_weight(news.impact)
                scores.append(news.sentiment * weight)
            else:
                # Análise por palavras-chave
                text_score = self._analyze_text_sentiment(
                    news.title + " " + news.summary,
                    symbol
                )
                weight = self._impact_weight(news.impact)
                scores.append(text_score * weight)
        
        if not scores:
            return 0.0, None
        
        avg_score = sum(scores) / len(scores)
        
        # Determinar direção
        if avg_score > 0.2:
            direction = SignalDirection.BUY
        elif avg_score < -0.2:
            direction = SignalDirection.SELL
        else:
            direction = None
        
        return round(avg_score, 3), direction
    
    def _impact_weight(self, impact: NewsImpact) -> float:
        """Peso baseado no impacto"""
        weights = {
            NewsImpact.HIGH: 2.0,
            NewsImpact.MEDIUM: 1.0,
            NewsImpact.LOW: 0.5
        }
        return weights.get(impact, 1.0)
    
    def _analyze_text_sentiment(
        self,
        text: str,
        symbol: Optional[str]
    ) -> float:
        """Análise simples de sentimento por palavras-chave"""
        text_lower = text.lower()
        
        # Contar palavras bullish/bearish
        bullish_count = sum(1 for kw in self._keywords["bullish"] if kw in text_lower)
        bearish_count = sum(1 for kw in self._keywords["bearish"] if kw in text_lower)
        
        # Para gold, usar keywords específicos
        if symbol and "XAU" in symbol.upper():
            bullish_count += sum(1 for kw in self._keywords["gold_bullish"] if kw in text_lower)
            bearish_count += sum(1 for kw in self._keywords["gold_bearish"] if kw in text_lower)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0
        
        return (bullish_count - bearish_count) / total
    
    def _extract_themes(self, news_list: List[NewsItem]) -> List[str]:
        """Extrai temas dominantes das notícias"""
        theme_keywords = {
            "Inflação": ["inflation", "cpi", "pce", "prices"],
            "Taxa de Juros": ["rate", "fed", "fomc", "ecb", "boe", "monetary"],
            "Emprego": ["jobs", "employment", "payroll", "unemployment", "labor"],
            "Geopolítica": ["war", "conflict", "tension", "sanctions", "geopolitical"],
            "Commodities": ["oil", "gold", "silver", "commodity", "crude"],
            "Dólar": ["dollar", "usd", "dxy", "greenback"],
            "Recessão": ["recession", "slowdown", "contraction", "gdp"],
            "Tech/Ações": ["stocks", "equity", "nasdaq", "sp500", "tech"]
        }
        
        theme_counts = Counter()
        
        for news in news_list:
            text = (news.title + " " + news.summary).lower()
            for theme, keywords in theme_keywords.items():
                if any(kw in text for kw in keywords):
                    theme_counts[theme] += 1
        
        # Top 3 temas
        return [theme for theme, _ in theme_counts.most_common(3)]
    
    def _get_top_news(
        self,
        news_list: List[NewsItem],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Obtém notícias mais importantes"""
        # Ordenar por impacto e data
        sorted_news = sorted(
            news_list,
            key=lambda n: (
                -self._impact_weight(n.impact),
                -n.published_at.timestamp()
            )
        )
        
        return [
            {
                "title": n.title,
                "source": n.source,
                "impact": n.impact.value,
                "published": n.published_at.isoformat()
            }
            for n in sorted_news[:limit]
        ]
    
    def _generate_summary(
        self,
        news_list: List[NewsItem],
        symbol: Optional[str]
    ) -> str:
        """Gera resumo em português"""
        if not news_list:
            return "Sem notícias relevantes."
        
        high_impact = [n for n in news_list if n.impact == NewsImpact.HIGH]
        
        symbol_name = self._symbol_to_name(symbol) if symbol else "o mercado"
        
        summary_parts = []
        
        # Contagem
        summary_parts.append(
            f"Foram encontradas {len(news_list)} notícias relevantes para {symbol_name}"
        )
        
        if high_impact:
            summary_parts.append(
                f", sendo {len(high_impact)} de alto impacto"
            )
        
        summary_parts.append(". ")
        
        # Temas
        themes = self._extract_themes(news_list)
        if themes:
            summary_parts.append(
                f"Os principais temas são: {', '.join(themes)}. "
            )
        
        return "".join(summary_parts)
    
    def _symbol_to_name(self, symbol: str) -> str:
        """Converte símbolo para nome legível"""
        names = {
            "XAUUSD": "Ouro (XAU/USD)",
            "EURUSD": "Euro/Dólar (EUR/USD)",
            "GBPUSD": "Libra/Dólar (GBP/USD)",
            "USDJPY": "Dólar/Iene (USD/JPY)"
        }
        return names.get(symbol.upper(), symbol)
    
    def _calculate_trading_bias(
        self,
        sentiment_score: float,
        high_impact_count: int
    ) -> str:
        """Calcula bias para trading"""
        # Se há muitas notícias de alto impacto, cautela
        if high_impact_count >= 3:
            return "cautious"
        
        if sentiment_score > 0.3:
            return "bullish"
        elif sentiment_score < -0.3:
            return "bearish"
        else:
            return "neutral"
