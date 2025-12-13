"""
BRAIN - Sentiment Analyzer
Analisador de sentimento usando NLP
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re

from ...core.types import NewsItem, NewsImpact, SignalDirection
from ...core.logger import get_logger

logger = get_logger("brain.analyzer.sentiment")


class SentimentAnalyzer:
    """
    Analisador de sentimento de mercado
    
    Utiliza:
    - Análise léxica (Loughran-McDonald)
    - FinBERT (quando disponível)
    - Indicadores de fear/greed
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._finbert_available = False
        
        # Dicionário financeiro Loughran-McDonald simplificado
        self._positive_words = {
            "achieve", "accomplished", "advantage", "beneficial", "best",
            "boost", "bullish", "buy", "confidence", "gain", "good",
            "great", "growth", "high", "improve", "increase", "optimistic",
            "outperform", "positive", "profit", "progress", "rally",
            "recovery", "rise", "strong", "success", "surge", "upward"
        }
        
        self._negative_words = {
            "adverse", "against", "bad", "bearish", "concern", "crisis",
            "decline", "deficit", "deteriorate", "difficult", "down",
            "drop", "fail", "fall", "fear", "loss", "low", "negative",
            "pessimistic", "plunge", "poor", "recession", "risk", "sell",
            "slump", "threat", "trouble", "uncertain", "weak", "worse"
        }
        
        self._uncertainty_words = {
            "almost", "apparent", "assume", "believe", "could", "depend",
            "doubt", "estimate", "expect", "hope", "may", "maybe",
            "might", "possible", "possibly", "predict", "probably",
            "seem", "suggest", "uncertain", "unclear", "unknown"
        }
        
        # Tentativa de carregar FinBERT
        self._try_load_finbert()
    
    def _try_load_finbert(self):
        """Tenta carregar modelo FinBERT"""
        try:
            # from transformers import AutoModelForSequenceClassification, AutoTokenizer
            # self._finbert_model = AutoModelForSequenceClassification.from_pretrained(
            #     "ProsusAI/finbert"
            # )
            # self._finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
            # self._finbert_available = True
            # logger.info("FinBERT carregado com sucesso")
            pass
        except Exception as e:
            logger.debug(f"FinBERT não disponível: {e}")
            self._finbert_available = False
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analisa sentimento de um texto
        
        Args:
            text: Texto para análise
            
        Returns:
            Dict com scores de sentimento
        """
        if not text:
            return {
                "score": 0.0,
                "direction": "neutral",
                "confidence": 0.0,
                "method": "none"
            }
        
        # Preprocessar
        text_clean = self._preprocess(text)
        words = text_clean.split()
        
        # Análise léxica
        lexical_result = self._lexical_analysis(words)
        
        # Se FinBERT disponível, fazer média
        if self._finbert_available:
            finbert_result = self._finbert_analysis(text)
            # Combinar resultados
            final_score = (lexical_result["score"] + finbert_result["score"]) / 2
            method = "lexical+finbert"
        else:
            final_score = lexical_result["score"]
            method = "lexical"
        
        # Determinar direção
        if final_score > 0.2:
            direction = "positive"
        elif final_score < -0.2:
            direction = "negative"
        else:
            direction = "neutral"
        
        return {
            "score": round(final_score, 3),
            "direction": direction,
            "confidence": lexical_result["confidence"],
            "uncertainty": lexical_result["uncertainty"],
            "method": method,
            "word_counts": lexical_result["counts"]
        }
    
    def _preprocess(self, text: str) -> str:
        """Preprocessa texto"""
        # Lowercase
        text = text.lower()
        # Remover URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)
        # Remover caracteres especiais
        text = re.sub(r'[^\w\s]', ' ', text)
        # Remover números
        text = re.sub(r'\d+', '', text)
        # Normalizar espaços
        text = ' '.join(text.split())
        return text
    
    def _lexical_analysis(self, words: List[str]) -> Dict[str, Any]:
        """Análise baseada em dicionário"""
        positive_count = sum(1 for w in words if w in self._positive_words)
        negative_count = sum(1 for w in words if w in self._negative_words)
        uncertainty_count = sum(1 for w in words if w in self._uncertainty_words)
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return {
                "score": 0.0,
                "confidence": 0.0,
                "uncertainty": 0.0,
                "counts": {
                    "positive": 0,
                    "negative": 0,
                    "uncertainty": 0,
                    "total_words": len(words)
                }
            }
        
        # Score de -1 a 1
        score = (positive_count - negative_count) / total_sentiment_words
        
        # Confiança baseada em quantidade de palavras encontradas
        confidence = min(total_sentiment_words / max(len(words), 1) * 5, 1.0)
        
        # Incerteza
        uncertainty_ratio = uncertainty_count / max(len(words), 1)
        
        return {
            "score": score,
            "confidence": round(confidence, 3),
            "uncertainty": round(uncertainty_ratio, 3),
            "counts": {
                "positive": positive_count,
                "negative": negative_count,
                "uncertainty": uncertainty_count,
                "total_words": len(words)
            }
        }
    
    def _finbert_analysis(self, text: str) -> Dict[str, Any]:
        """Análise usando FinBERT"""
        # TODO: Implementar quando FinBERT estiver disponível
        return {"score": 0.0, "confidence": 0.0}
    
    def analyze_news_list(
        self,
        news_list: List[NewsItem]
    ) -> Dict[str, Any]:
        """
        Analisa sentimento de lista de notícias
        
        Args:
            news_list: Lista de NewsItem
            
        Returns:
            Análise agregada de sentimento
        """
        if not news_list:
            return {
                "overall_score": 0.0,
                "overall_direction": "neutral",
                "news_analyzed": 0,
                "breakdown": {}
            }
        
        scores = []
        directions = {"positive": 0, "negative": 0, "neutral": 0}
        
        for news in news_list:
            # Combinar título e resumo
            text = f"{news.title} {news.summary}"
            result = self.analyze_text(text)
            
            # Peso pelo impacto
            weight = self._get_impact_weight(news.impact)
            scores.append(result["score"] * weight)
            directions[result["direction"]] += 1
            
            # Atualizar sentimento da notícia
            news.sentiment = result["score"]
        
        # Calcular média ponderada
        overall_score = sum(scores) / len(scores) if scores else 0.0
        
        # Determinar direção geral
        if overall_score > 0.15:
            overall_direction = "positive"
        elif overall_score < -0.15:
            overall_direction = "negative"
        else:
            overall_direction = "neutral"
        
        return {
            "overall_score": round(overall_score, 3),
            "overall_direction": overall_direction,
            "news_analyzed": len(news_list),
            "breakdown": directions,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_impact_weight(self, impact: NewsImpact) -> float:
        """Peso baseado no impacto da notícia"""
        weights = {
            NewsImpact.HIGH: 1.5,
            NewsImpact.MEDIUM: 1.0,
            NewsImpact.LOW: 0.7
        }
        return weights.get(impact, 1.0)
    
    def get_market_mood(
        self,
        sentiment_score: float,
        volatility: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Determina o "humor" do mercado
        
        Args:
            sentiment_score: Score de sentimento (-1 a 1)
            volatility: Volatilidade atual (opcional)
            
        Returns:
            Dict com mood e descrição
        """
        # Escala de Fear & Greed simplificada
        # Score: -1 (extreme fear) a 1 (extreme greed)
        
        if sentiment_score <= -0.6:
            mood = "extreme_fear"
            mood_pt = "Medo Extremo"
            emoji = "😱"
        elif sentiment_score <= -0.3:
            mood = "fear"
            mood_pt = "Medo"
            emoji = "😰"
        elif sentiment_score <= -0.1:
            mood = "worry"
            mood_pt = "Preocupação"
            emoji = "😟"
        elif sentiment_score <= 0.1:
            mood = "neutral"
            mood_pt = "Neutro"
            emoji = "😐"
        elif sentiment_score <= 0.3:
            mood = "optimism"
            mood_pt = "Otimismo"
            emoji = "🙂"
        elif sentiment_score <= 0.6:
            mood = "greed"
            mood_pt = "Ganância"
            emoji = "🤑"
        else:
            mood = "extreme_greed"
            mood_pt = "Ganância Extrema"
            emoji = "🚀"
        
        # Ajustar por volatilidade
        vol_comment = ""
        if volatility is not None:
            if volatility > 0.02:  # Alta volatilidade
                vol_comment = " (alta volatilidade aumenta incerteza)"
        
        return {
            "mood": mood,
            "mood_pt": mood_pt,
            "emoji": emoji,
            "score": round(sentiment_score, 2),
            "description": f"{emoji} {mood_pt}{vol_comment}"
        }
