"""
VIRTUS - TESS AI Integration
==============================

Módulo de integração com a TESS AI (Pareto.io).
Agrega +250 modelos de IA em uma única API.

Componentes:
- TessClient: Cliente base para API
- TessAgents: Gerenciador de agentes
- TessCaptionService: Geração de captions para redes sociais
- TessMarketAnalyzer: Análise de mercado com IA
"""

from .client import TessClient, get_tess_client
from .agents import TessAgents
from .caption_service import TessCaptionService
from .market_analyzer import TessMarketAnalyzer, MarketSentiment, MarketAlert, get_tess_market_analyzer

__all__ = [
    'TessClient',
    'get_tess_client',
    'TessAgents',
    'TessCaptionService',
    'TessMarketAnalyzer',
    'MarketSentiment',
    'MarketAlert',
    'get_tess_market_analyzer',
]
