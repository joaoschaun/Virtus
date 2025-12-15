"""
VIRTUS - TESS AI Agents
========================

Mapeamento dos agentes TESS recomendados para o projeto Virtus.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List


class AgentCategory(Enum):
    """Categorias de agentes."""
    SOCIAL_MEDIA = "social_media"
    MARKETING = "marketing"
    IMAGE = "image"
    VIDEO = "video"
    ANALYSIS = "analysis"


@dataclass
class AgentInfo:
    """Informações de um agente TESS."""
    id: int
    name: str
    description: str
    category: AgentCategory
    required_inputs: List[str]
    optional_inputs: List[str]
    average_credits: float
    recommended_model: str = "gpt-4o-mini"


class TessAgents:
    """
    Catálogo de agentes TESS recomendados para Virtus.
    
    Uso:
        agent = TessAgents.INSTAGRAM_CAPTION
        result = await client.execute_agent(
            agent_id=agent.id,
            inputs={...}
        )
    """
    
    # ==================== SOCIAL MEDIA ====================
    
    INSTAGRAM_CAPTION = AgentInfo(
        id=131,
        name="Descrição para Post no Instagram",
        description="Cria captions otimizadas para posts no Instagram",
        category=AgentCategory.SOCIAL_MEDIA,
        required_inputs=["seu-objetivo"],
        optional_inputs=["temperature", "model", "maxlength", "language"],
        average_credits=0.06,
        recommended_model="gpt-4o-mini"
    )
    
    LINKEDIN_POST = AgentInfo(
        id=67,
        name="Transformar Texto em Post para LinkedIn",
        description="Converte texto em post profissional para LinkedIn",
        category=AgentCategory.SOCIAL_MEDIA,
        required_inputs=["texto"],
        optional_inputs=["temperature", "model", "maxlength", "language"],
        average_credits=0.07,
        recommended_model="gpt-4o-mini"
    )
    
    INSTAGRAM_LIVE_SCRIPT = AgentInfo(
        id=76,
        name="Roteiro Completo para Live Streaming no Instagram",
        description="Cria roteiro completo para lives no Instagram",
        category=AgentCategory.SOCIAL_MEDIA,
        required_inputs=["topico", "seu-instagram", "objetivo"],
        optional_inputs=["temperature", "model", "maxlength", "language"],
        average_credits=0.10,
        recommended_model="gpt-4o-mini"
    )
    
    INSTAGRAM_REELS_SCRIPT = AgentInfo(
        id=183,
        name="Roteiro de Reels para Instagram",
        description="Cria roteiro para Reels",
        category=AgentCategory.SOCIAL_MEDIA,
        required_inputs=["tema"],
        optional_inputs=["temperature", "model", "maxlength", "language"],
        average_credits=0.05,
        recommended_model="gpt-4o-mini"
    )
    
    LIVE_SCRIPT = AgentInfo(
        id=75,
        name="Transformar uma ideia em roteiro para LIVE",
        description="Converte ideias em roteiro para lives",
        category=AgentCategory.SOCIAL_MEDIA,
        required_inputs=["suas-ideias"],
        optional_inputs=["temperature", "model", "maxlength", "language"],
        average_credits=0.08,
        recommended_model="gpt-4o-mini"
    )
    
    # ==================== MARKETING ====================
    
    GOOGLE_ADS_TEXT = AgentInfo(
        id=45,
        name="Anúncios de Texto no Google Ads para a Marca",
        description="Cria anúncios de texto para Google Ads",
        category=AgentCategory.MARKETING,
        required_inputs=["nome-da-marca", "descricao-do-produto"],
        optional_inputs=["temperature", "model", "maxlength", "language"],
        average_credits=0.08,
        recommended_model="gpt-4o-mini"
    )
    
    YOUTUBE_ADS_IDEAS = AgentInfo(
        id=68,
        name="Ideias de anúncios para o YouTube Ads",
        description="Gera ideias para anúncios no YouTube",
        category=AgentCategory.MARKETING,
        required_inputs=[
            "area-de-atucao-da-empresa", 
            "publico-alvo", 
            "ocasiao-especial",
            "descreva-o-produto-ou-servico",
            "company-name"
        ],
        optional_inputs=["temperature", "model", "maxlength", "language"],
        average_credits=0.10,
        recommended_model="gpt-4o-mini"
    )
    
    KEYWORDS_CAMPAIGN = AgentInfo(
        id=60,
        name="Palavras-chave para campanha de produtos/serviços",
        description="Gera palavras-chave para campanhas Google Ads",
        category=AgentCategory.MARKETING,
        required_inputs=["nome-da-marca", "lista-de-produtos-ou-servios"],
        optional_inputs=["temperature", "model", "maxlength", "language"],
        average_credits=0.06,
        recommended_model="gpt-4o-mini"
    )
    
    EMAIL_SALES = AgentInfo(
        id=53,
        name="E-mail de Venda",
        description="Cria emails de vendas persuasivos",
        category=AgentCategory.MARKETING,
        required_inputs=["produto", "publico-alvo"],
        optional_inputs=["temperature", "model", "maxlength", "language"],
        average_credits=0.07,
        recommended_model="gpt-4o-mini"
    )
    
    # ==================== IMAGE ====================
    
    MOCKUP_REALISTIC = AgentInfo(
        id=153,
        name="Modelos Realistas para Mockup do seu Produto",
        description="Gera mockups realistas de produtos",
        category=AgentCategory.IMAGE,
        required_inputs=["descricao-do-produto"],
        optional_inputs=["estilo"],
        average_credits=0.50,
        recommended_model="stable-diffusion-3.5"
    )
    
    PIXAR_ILLUSTRATION = AgentInfo(
        id=156,
        name="Ilustrações no Estilo Pixar",
        description="Cria ilustrações no estilo Pixar",
        category=AgentCategory.IMAGE,
        required_inputs=["descricao"],
        optional_inputs=[],
        average_credits=0.45,
        recommended_model="stable-diffusion-3.5"
    )
    
    ICONS_3D = AgentInfo(
        id=159,
        name="Ícones 3D Modernos e Minimalistas",
        description="Gera ícones 3D modernos",
        category=AgentCategory.IMAGE,
        required_inputs=["descricao"],
        optional_inputs=[],
        average_credits=0.40,
        recommended_model="stable-diffusion-3.5"
    )
    
    LOGO_MINIMALIST = AgentInfo(
        id=155,
        name="Logos Minimalistas",
        description="Cria logos minimalistas",
        category=AgentCategory.IMAGE,
        required_inputs=["nome", "descricao"],
        optional_inputs=[],
        average_credits=0.50,
        recommended_model="stable-diffusion-3.5"
    )
    
    LANDSCAPE_PHOTO = AgentInfo(
        id=157,
        name="Fotos Incríveis de Paisagem",
        description="Gera fotos de paisagem",
        category=AgentCategory.IMAGE,
        required_inputs=["descricao"],
        optional_inputs=[],
        average_credits=0.45,
        recommended_model="stable-diffusion-3.5"
    )
    
    # ==================== MÉTODOS DE CLASSE ====================
    
    @classmethod
    def get_by_id(cls, agent_id: int) -> AgentInfo:
        """Busca agente por ID."""
        for name in dir(cls):
            attr = getattr(cls, name)
            if isinstance(attr, AgentInfo) and attr.id == agent_id:
                return attr
        raise ValueError(f"Agente {agent_id} não encontrado")
    
    @classmethod
    def get_by_category(cls, category: AgentCategory) -> List[AgentInfo]:
        """Busca agentes por categoria."""
        agents = []
        for name in dir(cls):
            attr = getattr(cls, name)
            if isinstance(attr, AgentInfo) and attr.category == category:
                agents.append(attr)
        return agents
    
    @classmethod
    def list_all(cls) -> List[AgentInfo]:
        """Lista todos os agentes catalogados."""
        agents = []
        for name in dir(cls):
            attr = getattr(cls, name)
            if isinstance(attr, AgentInfo):
                agents.append(attr)
        return agents
    
    @classmethod
    def get_social_media_agents(cls) -> List[AgentInfo]:
        """Retorna agentes de social media."""
        return cls.get_by_category(AgentCategory.SOCIAL_MEDIA)
    
    @classmethod
    def get_image_agents(cls) -> List[AgentInfo]:
        """Retorna agentes de imagem."""
        return cls.get_by_category(AgentCategory.IMAGE)


# ==================== MODELOS DISPONÍVEIS ====================

class TessModels:
    """Modelos disponíveis na TESS AI."""
    
    # Texto - Rápidos e baratos
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_35_TURBO = "gpt-3.5-turbo"
    TESS_AI_LIGHT = "tess-ai-light"
    GEMINI_FLASH = "gemini-2.0-flash"
    GEMINI_FLASH_LITE = "gemini-2.0-flash-lite"
    
    # Texto - Premium
    GPT_4O = "gpt-4o"
    GPT_4_TURBO = "gpt-4-turbo"
    CLAUDE_3_HAIKU = "claude-3-5-haiku-latest"
    TESS_AI_3 = "tess-ai-3"
    
    # Texto - Raciocínio avançado
    GPT_O3_MINI = "gpt-o3-mini"
    GPT_O3_MINI_HIGH = "gpt-o3-mini-high"
    DEEPSEEK_R1 = "deepseek-r1"
    DEEPSEEK_R1_SMALL = "deepseek-r1-small"
    DEEPSEEK_V3 = "deepseek-v3"
    
    # Texto - Open Source
    LLAMA_3_405B = "meta-llama-3.1-405b-instruct"
    LLAMA_3_70B = "meta-llama-3-70b-instruct"
    LLAMA_3_8B = "meta-llama-3-8b-instruct"
    GROK_2 = "grok-2"
    COHERE_COMMAND_R = "cohere-command-r"
    COHERE_COMMAND_R_PLUS = "cohere-command-r-plus"
    SNOWFLAKE_ARCTIC = "snowflake-arctic"
    
    @classmethod
    def list_fast_models(cls) -> List[str]:
        """Modelos rápidos e baratos."""
        return [
            cls.GPT_4O_MINI,
            cls.GPT_35_TURBO,
            cls.TESS_AI_LIGHT,
            cls.GEMINI_FLASH_LITE,
        ]
    
    @classmethod
    def list_premium_models(cls) -> List[str]:
        """Modelos premium."""
        return [
            cls.GPT_4O,
            cls.GPT_4_TURBO,
            cls.CLAUDE_3_HAIKU,
            cls.TESS_AI_3,
        ]
    
    @classmethod
    def list_reasoning_models(cls) -> List[str]:
        """Modelos com raciocínio avançado."""
        return [
            cls.DEEPSEEK_R1,
            cls.GPT_O3_MINI,
        ]


# ==================== HELPERS ====================

def build_agent_inputs(
    agent: AgentInfo,
    **kwargs
) -> Dict[str, Any]:
    """
    Constrói inputs para um agente.
    
    Args:
        agent: Info do agente
        **kwargs: Parâmetros do agente
        
    Returns:
        Dicionário de inputs formatado
    """
    inputs = {}
    
    # Adiciona inputs obrigatórios
    for required in agent.required_inputs:
        if required not in kwargs:
            raise ValueError(f"Input obrigatório faltando: {required}")
        inputs[required] = kwargs[required]
    
    # Adiciona inputs opcionais se fornecidos
    for optional in agent.optional_inputs:
        if optional in kwargs:
            inputs[optional] = kwargs[optional]
    
    # Adiciona modelo recomendado se não especificado
    if "model" not in inputs:
        inputs["model"] = agent.recommended_model
    
    return inputs
