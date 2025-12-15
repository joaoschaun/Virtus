"""
VIRTUS - TESS Market Analyzer
==============================

Usa TESS AI para análise de mercado:
- Análise de sentimento de notícias
- Resumo de contexto macro
- Identificação de eventos de impacto
- Geração de alertas inteligentes
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import logging

from .client import TessClient, TessConfig, TessError

logger = logging.getLogger(__name__)


@dataclass
class MarketSentiment:
    """Resultado de análise de sentimento."""
    sentiment: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0 a 1
    impact: str  # "high", "medium", "low"
    summary: str
    key_points: List[str]
    affected_symbols: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sentiment': self.sentiment,
            'confidence': self.confidence,
            'impact': self.impact,
            'summary': self.summary,
            'key_points': self.key_points,
            'affected_symbols': self.affected_symbols,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class MarketAlert:
    """Alerta de mercado gerado pela TESS."""
    title: str
    message: str
    severity: str  # "critical", "warning", "info"
    symbols: List[str]
    action_suggested: str
    timestamp: datetime = field(default_factory=datetime.now)


class TessMarketAnalyzer:
    """
    Analisa mercado usando TESS AI.
    
    Funcionalidades:
    - Análise de sentimento de notícias
    - Resumo diário de mercado
    - Identificação de eventos de impacto
    - Geração de alertas inteligentes
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger("tess_market")
        
        # Carrega config
        self.config = self._load_config(config_path)
        self.client: Optional[TessClient] = None
        
        # Cache de análises (evita chamadas repetidas)
        self._sentiment_cache: Dict[str, MarketSentiment] = {}
        self._cache_ttl = timedelta(minutes=15)
        
        # Histórico
        self._analysis_history: List[MarketSentiment] = []
        
        self._initialized = False
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Carrega configuração da TESS."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "tess.yaml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"Config não encontrada: {e}")
            return {}
    
    async def initialize(self) -> bool:
        """Inicializa o analisador."""
        try:
            api_key = self.config.get('api_key')
            if not api_key:
                self.logger.warning("TESS API key não configurada")
                return False
            
            self.client = TessClient(
                config=TessConfig(
                    api_key=api_key,
                    base_url=self.config.get('base_url', 'https://tess.pareto.io/api'),
                    default_model=self.config.get('default_model', 'gpt-4o-mini'),
                    timeout_seconds=self.config.get('timeout_seconds', 60),
                )
            )
            
            self._initialized = True
            self.logger.info("✅ TESS Market Analyzer inicializado")
            return True
            
        except Exception as e:
            self.logger.error(f"Falha ao inicializar TESS: {e}")
            return False
    
    async def analyze_news_sentiment(
        self,
        news_items: List[Dict[str, Any]],
        symbol: Optional[str] = None
    ) -> Optional[MarketSentiment]:
        """
        Analisa sentimento de uma lista de notícias.
        
        Args:
            news_items: Lista de notícias com 'title', 'content', 'source'
            symbol: Símbolo específico para focar análise
            
        Returns:
            MarketSentiment com resultado da análise
        """
        if not self._initialized or not self.client:
            return None
        
        if not news_items:
            return None
        
        # Monta contexto das notícias
        news_context = "\n".join([
            f"- {item.get('title', '')}: {item.get('content', '')[:200]}"
            for item in news_items[:10]  # Limita a 10 notícias
        ])
        
        prompt = f"""Analise as seguintes notícias de mercado financeiro e determine:
1. Sentimento geral: BULLISH, BEARISH ou NEUTRAL
2. Nível de impacto: HIGH, MEDIUM ou LOW
3. Resumo em 2-3 frases
4. Principais pontos (máximo 5)
5. Símbolos/ativos mais afetados

{"Foco especial em: " + symbol if symbol else ""}

Notícias:
{news_context}

Responda em formato estruturado:
SENTIMENTO: [BULLISH/BEARISH/NEUTRAL]
IMPACTO: [HIGH/MEDIUM/LOW]
CONFIANÇA: [0-100]%
RESUMO: [seu resumo]
PONTOS:
- [ponto 1]
- [ponto 2]
SÍMBOLOS: [lista separada por vírgula]"""
        
        try:
            result = await self.client.execute_agent(
                agent_id=self.config.get('agents', {}).get('market_analysis', 1),
                inputs={
                    "prompt": prompt,
                    "modelo": self.config.get('default_model', 'gpt-4o-mini'),
                    "idioma": "Portuguese (Brazil)",
                    "temperatura": "0.3",  # Mais preciso
                }
            )
            
            response_text = result.get('output', '')
            return self._parse_sentiment_response(response_text, news_items)
            
        except TessError as e:
            self.logger.error(f"Erro na análise TESS: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Erro inesperado: {e}")
            return None
    
    def _parse_sentiment_response(
        self,
        response: str,
        news_items: List[Dict]
    ) -> MarketSentiment:
        """Parse da resposta da TESS."""
        lines = response.strip().split('\n')
        
        sentiment = "neutral"
        impact = "medium"
        confidence = 0.5
        summary = ""
        key_points = []
        symbols = []
        
        parsing_points = False
        
        for line in lines:
            line_upper = line.upper().strip()
            line_clean = line.strip()
            
            if 'SENTIMENTO:' in line_upper:
                if 'BULLISH' in line_upper:
                    sentiment = 'bullish'
                elif 'BEARISH' in line_upper:
                    sentiment = 'bearish'
                else:
                    sentiment = 'neutral'
                parsing_points = False
                    
            elif 'IMPACTO:' in line_upper:
                if 'HIGH' in line_upper or 'ALTO' in line_upper:
                    impact = 'high'
                elif 'LOW' in line_upper or 'BAIXO' in line_upper:
                    impact = 'low'
                else:
                    impact = 'medium'
                parsing_points = False
                    
            elif 'CONFIANÇA:' in line_upper or 'CONFIDENCE:' in line_upper:
                try:
                    # Extrai número
                    import re
                    numbers = re.findall(r'\d+', line_clean)
                    if numbers:
                        confidence = int(numbers[0]) / 100
                except:
                    pass
                parsing_points = False
                    
            elif 'RESUMO:' in line_upper:
                summary = line_clean.replace('RESUMO:', '').replace('Resumo:', '').strip()
                parsing_points = False
                
            elif 'PONTOS:' in line_upper or 'POINTS:' in line_upper:
                parsing_points = True
                
            elif 'SÍMBOLOS:' in line_upper or 'SIMBOLOS:' in line_upper or 'SYMBOLS:' in line_upper:
                symbols_text = line_clean.split(':', 1)[-1].strip()
                symbols = [s.strip().upper() for s in symbols_text.split(',') if s.strip()]
                parsing_points = False
                
            elif parsing_points and line_clean.startswith('-'):
                point = line_clean.lstrip('- ').strip()
                if point:
                    key_points.append(point)
        
        # Fallback para símbolos se não encontrados
        if not symbols:
            symbols = ['XAUUSD', 'EURUSD', 'GBPUSD']
        
        result = MarketSentiment(
            sentiment=sentiment,
            confidence=min(1.0, max(0.0, confidence)),
            impact=impact,
            summary=summary or "Análise de mercado baseada em notícias recentes.",
            key_points=key_points[:5],
            affected_symbols=symbols[:5],
        )
        
        self._analysis_history.append(result)
        return result
    
    async def generate_market_summary(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Gera resumo de mercado para um símbolo.
        
        Args:
            symbol: Símbolo do ativo
            market_data: Dados de mercado (preço, indicadores, etc.)
            
        Returns:
            String com resumo do mercado
        """
        if not self._initialized or not self.client:
            return None
        
        prompt = f"""Crie um resumo conciso (máximo 150 palavras) do mercado para {symbol}:

Dados atuais:
- Preço: {market_data.get('close', 'N/A')}
- RSI: {market_data.get('rsi', 'N/A')}
- Tendência: {market_data.get('trend', 'N/A')}
- Volatilidade: {market_data.get('volatility', 'N/A')}

Inclua:
1. Situação atual do mercado
2. Níveis importantes
3. Perspectiva de curto prazo

Seja objetivo e use linguagem profissional."""
        
        try:
            result = await self.client.execute_agent(
                agent_id=1,  # Agente genérico
                inputs={
                    "prompt": prompt,
                    "modelo": "gpt-4o-mini",
                    "temperatura": "0.4",
                }
            )
            
            return result.get('output', '')[:500]  # Limita tamanho
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo: {e}")
            return None
    
    async def generate_alert(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> Optional[MarketAlert]:
        """
        Gera alerta inteligente baseado em evento.
        
        Args:
            event_type: Tipo de evento ('news', 'price_move', 'indicator')
            data: Dados do evento
            
        Returns:
            MarketAlert com mensagem formatada
        """
        if not self._initialized or not self.client:
            return None
        
        prompt = f"""Crie um alerta de trading profissional e conciso para:

Tipo: {event_type}
Dados: {data}

O alerta deve ter:
1. Título (máximo 10 palavras)
2. Mensagem (máximo 50 palavras)
3. Severidade: CRITICAL, WARNING ou INFO
4. Ação sugerida (máximo 20 palavras)

Formato:
TÍTULO: [título]
MENSAGEM: [mensagem]
SEVERIDADE: [severidade]
AÇÃO: [ação]"""
        
        try:
            result = await self.client.execute_agent(
                agent_id=1,
                inputs={
                    "prompt": prompt,
                    "modelo": "gpt-4o-mini",
                    "temperatura": "0.3",
                }
            )
            
            return self._parse_alert_response(result.get('output', ''), data)
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar alerta: {e}")
            return None
    
    def _parse_alert_response(
        self,
        response: str,
        data: Dict[str, Any]
    ) -> MarketAlert:
        """Parse da resposta de alerta."""
        lines = response.strip().split('\n')
        
        title = "Alerta de Mercado"
        message = ""
        severity = "info"
        action = ""
        
        for line in lines:
            line_upper = line.upper().strip()
            line_clean = line.strip()
            
            if 'TÍTULO:' in line_upper or 'TITLE:' in line_upper:
                title = line_clean.split(':', 1)[-1].strip()
            elif 'MENSAGEM:' in line_upper or 'MESSAGE:' in line_upper:
                message = line_clean.split(':', 1)[-1].strip()
            elif 'SEVERIDADE:' in line_upper or 'SEVERITY:' in line_upper:
                if 'CRITICAL' in line_upper or 'CRÍTICO' in line_upper:
                    severity = 'critical'
                elif 'WARNING' in line_upper or 'AVISO' in line_upper:
                    severity = 'warning'
                else:
                    severity = 'info'
            elif 'AÇÃO:' in line_upper or 'ACTION:' in line_upper:
                action = line_clean.split(':', 1)[-1].strip()
        
        symbols = data.get('symbols', ['XAUUSD'])
        if isinstance(symbols, str):
            symbols = [symbols]
        
        return MarketAlert(
            title=title[:100],
            message=message[:300],
            severity=severity,
            symbols=symbols,
            action_suggested=action[:150],
        )
    
    def get_recent_sentiment(
        self,
        symbol: Optional[str] = None,
        hours: int = 24
    ) -> List[MarketSentiment]:
        """Retorna análises de sentimento recentes."""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        results = [
            s for s in self._analysis_history
            if s.timestamp > cutoff
        ]
        
        if symbol:
            results = [
                s for s in results
                if symbol in s.affected_symbols
            ]
        
        return results
    
    def get_consensus_sentiment(self) -> Optional[str]:
        """Retorna sentimento de consenso das últimas análises."""
        recent = self.get_recent_sentiment(hours=6)
        
        if not recent:
            return None
        
        bullish = sum(1 for s in recent if s.sentiment == 'bullish')
        bearish = sum(1 for s in recent if s.sentiment == 'bearish')
        
        if bullish > bearish and bullish >= len(recent) * 0.6:
            return 'bullish'
        elif bearish > bullish and bearish >= len(recent) * 0.6:
            return 'bearish'
        else:
            return 'neutral'


# Singleton
_market_analyzer: Optional[TessMarketAnalyzer] = None


async def get_tess_market_analyzer() -> Optional[TessMarketAnalyzer]:
    """Obtém instância singleton do analisador."""
    global _market_analyzer
    
    if _market_analyzer is None:
        _market_analyzer = TessMarketAnalyzer()
        await _market_analyzer.initialize()
    
    return _market_analyzer
