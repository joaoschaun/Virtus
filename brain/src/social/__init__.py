"""
VIRTUS Social Media Automation
===============================

Sistema de automação de posts para redes sociais.
Gera conteúdo profissional baseado nos dados do Brain.

Componentes:
- ContentGenerator: Gera textos para posts
- ImageGenerator: Cria imagens com branding Virtus
- InstagramService: Integração com Meta Graph API
- SocialScheduler: Agendamento estratégico
- SocialMediaManager: Orquestrador principal
"""

from .content_generator import ContentGenerator, PostType, PostContent
from .image_generator import ImageGenerator, ImageTemplate, ImageConfig, BrandColors
from .instagram_service import (
    InstagramService, 
    InstagramConfig,
    PostResult,
    create_instagram_service,
    MockInstagramService,
)
from .scheduler import SocialScheduler, ScheduledPost, ScheduleType
from .manager import SocialMediaManager, SocialMediaConfig, create_social_routes

__all__ = [
    # Content
    "ContentGenerator",
    "PostType",
    "PostContent",
    
    # Image
    "ImageGenerator",
    "ImageTemplate",
    "ImageConfig",
    "BrandColors",
    
    # Instagram
    "InstagramService",
    "InstagramConfig",
    "PostResult",
    "create_instagram_service",
    "MockInstagramService",
    
    # Scheduler
    "SocialScheduler",
    "ScheduledPost",
    "ScheduleType",
    
    # Manager
    "SocialMediaManager",
    "SocialMediaConfig",
    "create_social_routes",
]
