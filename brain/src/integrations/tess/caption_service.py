"""
VIRTUS - TESS Caption Service
==============================

Serviço de geração de captions para social media usando TESS AI.
Substitui os templates estáticos por conteúdo gerado por IA.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import yaml

from .client import TessClient, TessError
from .agents import TessAgents, TessModels

logger = logging.getLogger(__name__)


@dataclass
class CaptionResult:
    """Resultado da geração de caption."""
    text: str
    model_used: str
    credits_spent: float
    generation_time: float
    agent_id: int


class TessCaptionService:
    """
    Serviço de geração de captions usando TESS AI.
    
    Gera captions profissionais e únicas para:
    - Instagram posts
    - LinkedIn posts
    - Twitter/X posts
    
    Uso:
        service = TessCaptionService(api_key="...")
        caption = await service.generate_instagram_caption(
            topic="Ouro subiu 2% após dados de inflação",
            sentiment="bullish"
        )
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        config_path: Optional[Path] = None
    ):
        """
        Inicializa o serviço.
        
        Args:
            api_key: Chave da API TESS (opcional se configurado)
            config_path: Caminho para config/tess.yaml
        """
        self.config = self._load_config(config_path)
        self.api_key = api_key or self.config.get('api_key')
        self.client = TessClient(api_key=self.api_key)
        
        # Configurações
        self.default_model = self.config.get('default_model', 'gpt-4o-mini')
        self.caption_max_length = self.config.get('caption_max_length', 300)
        self.linkedin_max_length = self.config.get('linkedin_max_length', 400)
    
    def _load_config(self, config_path: Optional[Path] = None) -> Dict:
        """Carrega configuração do arquivo YAML."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "tess.yaml"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Erro ao carregar config: {e}")
        
        return {}
    
    async def close(self):
        """Fecha conexões."""
        await self.client.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    # ==================== INSTAGRAM ====================
    
    async def generate_instagram_caption(
        self,
        topic: str,
        sentiment: Optional[str] = None,
        symbol: Optional[str] = None,
        include_hashtags: bool = True,
        model: Optional[str] = None,
        max_length: Optional[int] = None
    ) -> CaptionResult:
        """
        Gera caption para Instagram.
        
        Args:
            topic: Tópico/notícia principal
            sentiment: bullish/bearish/neutral
            symbol: Símbolo relacionado (XAUUSD, EURUSD, etc)
            include_hashtags: Se deve incluir hashtags
            model: Modelo a usar
            max_length: Limite de palavras
            
        Returns:
            CaptionResult com a caption gerada
        """
        start_time = datetime.now()
        
        # Monta objetivo contextualizado
        objective = self._build_instagram_objective(
            topic, sentiment, symbol, include_hashtags
        )
        
        try:
            result = await self.client.execute_agent(
                agent_id=TessAgents.INSTAGRAM_CAPTION.id,
                inputs={"seu-objetivo": objective},
                model=model or self.default_model,
                max_length=max_length or self.caption_max_length
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return CaptionResult(
                text=result.get('output', ''),
                model_used=model or self.default_model,
                credits_spent=result.get('credits', 0),
                generation_time=generation_time,
                agent_id=TessAgents.INSTAGRAM_CAPTION.id
            )
            
        except TessError as e:
            logger.error(f"Erro ao gerar caption Instagram: {e}")
            raise
    
    def _build_instagram_objective(
        self,
        topic: str,
        sentiment: Optional[str],
        symbol: Optional[str],
        include_hashtags: bool
    ) -> str:
        """Constrói objetivo para o agente Instagram."""
        
        parts = [f"Criar post sobre trading/investimentos: {topic}"]
        
        if sentiment:
            sentiment_text = {
                "bullish": "com tom otimista e positivo",
                "bearish": "com tom cauteloso e de alerta",
                "neutral": "com tom neutro e informativo"
            }.get(sentiment, "")
            if sentiment_text:
                parts.append(sentiment_text)
        
        if symbol:
            symbol_name = {
                "XAUUSD": "Ouro",
                "EURUSD": "Euro/Dólar",
                "GBPUSD": "Libra/Dólar",
                "BTC": "Bitcoin",
                "ETH": "Ethereum"
            }.get(symbol, symbol)
            parts.append(f"relacionado a {symbol_name}")
        
        parts.append("para o perfil @VirtusInvestimentos")
        
        if include_hashtags:
            parts.append("Inclua hashtags relevantes como #Trading #Forex #Investimentos")
        else:
            parts.append("Sem hashtags")
        
        parts.append("Use emojis estratégicos")
        
        return ". ".join(parts)
    
    # ==================== LINKEDIN ====================
    
    async def generate_linkedin_post(
        self,
        content: str,
        tone: str = "professional",
        model: Optional[str] = None,
        max_length: Optional[int] = None
    ) -> CaptionResult:
        """
        Gera post para LinkedIn.
        
        Args:
            content: Conteúdo base
            tone: Tom do post (professional, casual, educational)
            model: Modelo a usar
            max_length: Limite de palavras
            
        Returns:
            CaptionResult com o post gerado
        """
        start_time = datetime.now()
        
        # Adiciona contexto para LinkedIn
        enhanced_content = f"""
        Contexto: Post para LinkedIn da Virtus Investimentos
        Tom: {tone}
        Conteúdo base: {content}
        
        Crie um post profissional que:
        - Gere engajamento e discussão
        - Seja relevante para investidores
        - Inclua call-to-action no final
        """
        
        try:
            result = await self.client.execute_agent(
                agent_id=TessAgents.LINKEDIN_POST.id,
                inputs={"texto": enhanced_content},
                model=model or self.default_model,
                max_length=max_length or self.linkedin_max_length
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return CaptionResult(
                text=result.get('output', ''),
                model_used=model or self.default_model,
                credits_spent=result.get('credits', 0),
                generation_time=generation_time,
                agent_id=TessAgents.LINKEDIN_POST.id
            )
            
        except TessError as e:
            logger.error(f"Erro ao gerar post LinkedIn: {e}")
            raise
    
    # ==================== NEWS TO CAPTION ====================
    
    async def news_to_instagram_caption(
        self,
        news_title: str,
        news_summary: str,
        news_sentiment: Optional[str] = None,
        related_symbols: Optional[List[str]] = None
    ) -> CaptionResult:
        """
        Converte notícia em caption para Instagram.
        
        Args:
            news_title: Título da notícia
            news_summary: Resumo da notícia
            news_sentiment: Sentimento da notícia
            related_symbols: Símbolos relacionados
            
        Returns:
            CaptionResult com a caption gerada
        """
        # Monta tópico a partir da notícia
        topic = f"{news_title}. {news_summary}"
        
        # Usa primeiro símbolo relacionado
        symbol = related_symbols[0] if related_symbols else None
        
        return await self.generate_instagram_caption(
            topic=topic,
            sentiment=news_sentiment,
            symbol=symbol,
            include_hashtags=True
        )
    
    # ==================== TRADING TIP ====================
    
    async def generate_trading_tip(
        self,
        category: str = "general",
        model: Optional[str] = None
    ) -> CaptionResult:
        """
        Gera dica de trading.
        
        Args:
            category: Categoria (risk, psychology, technical, general)
            model: Modelo a usar
            
        Returns:
            CaptionResult com a dica gerada
        """
        start_time = datetime.now()
        
        category_context = {
            "risk": "gestão de risco e preservação de capital",
            "psychology": "psicologia do trading e controle emocional",
            "technical": "análise técnica e leitura de gráficos",
            "general": "trading em geral"
        }.get(category, "trading em geral")
        
        objective = f"""
        Criar um post educativo sobre {category_context} para Instagram.
        
        Requisitos:
        - Dica prática e aplicável
        - Linguagem acessível
        - Para o perfil @VirtusInvestimentos
        - Inclua emojis e hashtags como #TradingTips #EducacaoFinanceira
        - Máximo 3 parágrafos
        """
        
        try:
            result = await self.client.execute_agent(
                agent_id=TessAgents.INSTAGRAM_CAPTION.id,
                inputs={"seu-objetivo": objective},
                model=model or self.default_model,
                max_length=250
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            return CaptionResult(
                text=result.get('output', ''),
                model_used=model or self.default_model,
                credits_spent=result.get('credits', 0),
                generation_time=generation_time,
                agent_id=TessAgents.INSTAGRAM_CAPTION.id
            )
            
        except TessError as e:
            logger.error(f"Erro ao gerar dica de trading: {e}")
            raise
    
    # ==================== BULK GENERATION ====================
    
    async def generate_multiple_captions(
        self,
        topics: List[Dict[str, Any]],
        platform: str = "instagram"
    ) -> List[CaptionResult]:
        """
        Gera múltiplas captions em batch.
        
        Args:
            topics: Lista de {topic, sentiment, symbol}
            platform: instagram ou linkedin
            
        Returns:
            Lista de CaptionResult
        """
        results = []
        
        for topic_data in topics:
            try:
                if platform == "instagram":
                    result = await self.generate_instagram_caption(
                        topic=topic_data.get('topic', ''),
                        sentiment=topic_data.get('sentiment'),
                        symbol=topic_data.get('symbol')
                    )
                else:
                    result = await self.generate_linkedin_post(
                        content=topic_data.get('topic', '')
                    )
                
                results.append(result)
                
                # Pequeno delay para não sobrecarregar
                await asyncio.sleep(0.5)
                
            except TessError as e:
                logger.error(f"Erro em topic {topic_data}: {e}")
                continue
        
        return results


# ==================== TESTE ====================

if __name__ == "__main__":
    async def test():
        """Teste do serviço de captions."""
        api_key = "337520|MzMxArNQnQAcO0XBz7CLbraeV4lA7L6ep9sHITpt59a4b449"
        
        async with TessCaptionService(api_key=api_key) as service:
            print("🔥 Testando geração de caption Instagram...")
            
            result = await service.generate_instagram_caption(
                topic="O ouro atingiu máxima histórica após dados de inflação dos EUA",
                sentiment="bullish",
                symbol="XAUUSD"
            )
            
            print(f"\n📱 Caption gerada:")
            print(f"   {result.text[:500]}...")
            print(f"\n📊 Estatísticas:")
            print(f"   - Modelo: {result.model_used}")
            print(f"   - Créditos: {result.credits_spent:.4f}")
            print(f"   - Tempo: {result.generation_time:.2f}s")
    
    asyncio.run(test())
