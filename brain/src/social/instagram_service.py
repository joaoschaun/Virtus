"""
VIRTUS Social Media - Instagram Service
========================================

Serviço de integração com Instagram via Meta Graph API.
Gerencia publicação de posts com imagens.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio
import aiohttp
import logging
import json

logger = logging.getLogger(__name__)


class PublishStatus(Enum):
    """Status de publicação."""
    PENDING = "pending"
    UPLOADING = "uploading"
    PUBLISHED = "published"
    FAILED = "failed"
    SCHEDULED = "scheduled"


@dataclass
class InstagramConfig:
    """Configuração do Instagram."""
    access_token: str
    instagram_account_id: str
    page_id: str  # Facebook Page ID vinculada
    api_version: str = "v18.0"
    base_url: str = "https://graph.facebook.com"


@dataclass
class PostResult:
    """Resultado de uma publicação."""
    success: bool
    post_id: Optional[str] = None
    media_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class InstagramService:
    """
    Serviço de publicação no Instagram.
    
    Utiliza a Meta Graph API para publicar posts com imagens.
    Requer uma conta Business/Creator vinculada a uma Facebook Page.
    """
    
    def __init__(self, config: Optional[InstagramConfig] = None):
        """
        Inicializa o serviço.
        
        Args:
            config: Configuração do Instagram. Se None, tentará carregar do ambiente.
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._post_history: List[PostResult] = []
        
        # Rate limiting
        self._daily_posts = 0
        self._daily_limit = 25  # Limite conservador
        self._last_reset = datetime.now().date()
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtém ou cria sessão HTTP."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Fecha a sessão HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _check_rate_limit(self) -> bool:
        """Verifica se ainda pode postar (rate limiting)."""
        today = datetime.now().date()
        
        # Reset contador diário
        if today > self._last_reset:
            self._daily_posts = 0
            self._last_reset = today
        
        return self._daily_posts < self._daily_limit
    
    def _get_api_url(self, endpoint: str) -> str:
        """Monta URL da API."""
        return f"{self.config.base_url}/{self.config.api_version}/{endpoint}"
    
    async def verify_token(self) -> Dict[str, Any]:
        """
        Verifica se o token de acesso é válido.
        
        Returns:
            Informações do token ou erro
        """
        if not self.config:
            return {"valid": False, "error": "Configuração não definida"}
        
        session = await self._get_session()
        
        try:
            url = self._get_api_url("debug_token")
            params = {
                "input_token": self.config.access_token,
                "access_token": self.config.access_token,
            }
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if "error" in data:
                    return {"valid": False, "error": data["error"]["message"]}
                
                token_data = data.get("data", {})
                return {
                    "valid": token_data.get("is_valid", False),
                    "expires_at": token_data.get("expires_at"),
                    "scopes": token_data.get("scopes", []),
                }
                
        except Exception as e:
            logger.error(f"Erro ao verificar token: {e}")
            return {"valid": False, "error": str(e)}
    
    async def upload_image_url(
        self,
        image_url: str,
        caption: str,
    ) -> PostResult:
        """
        Publica imagem a partir de URL.
        
        Args:
            image_url: URL pública da imagem
            caption: Texto do post
            
        Returns:
            PostResult com status da publicação
        """
        if not self.config:
            return PostResult(success=False, error="Configuração não definida")
        
        if not self._check_rate_limit():
            return PostResult(
                success=False, 
                error="Limite diário de posts atingido"
            )
        
        session = await self._get_session()
        
        try:
            # Passo 1: Criar container de mídia
            container_url = self._get_api_url(
                f"{self.config.instagram_account_id}/media"
            )
            
            container_params = {
                "image_url": image_url,
                "caption": caption,
                "access_token": self.config.access_token,
            }
            
            async with session.post(container_url, data=container_params) as response:
                container_data = await response.json()
                
                if "error" in container_data:
                    return PostResult(
                        success=False,
                        error=container_data["error"]["message"]
                    )
                
                container_id = container_data.get("id")
            
            # Passo 2: Publicar a mídia
            publish_url = self._get_api_url(
                f"{self.config.instagram_account_id}/media_publish"
            )
            
            publish_params = {
                "creation_id": container_id,
                "access_token": self.config.access_token,
            }
            
            async with session.post(publish_url, data=publish_params) as response:
                publish_data = await response.json()
                
                if "error" in publish_data:
                    return PostResult(
                        success=False,
                        media_id=container_id,
                        error=publish_data["error"]["message"]
                    )
                
                post_id = publish_data.get("id")
            
            # Sucesso
            self._daily_posts += 1
            result = PostResult(
                success=True,
                post_id=post_id,
                media_id=container_id,
            )
            self._post_history.append(result)
            
            logger.info(f"Post publicado com sucesso: {post_id}")
            return result
            
        except Exception as e:
            logger.error(f"Erro ao publicar: {e}")
            return PostResult(success=False, error=str(e))
    
    async def upload_image_bytes(
        self,
        image_bytes: bytes,
        caption: str,
        upload_endpoint: str = None,
    ) -> PostResult:
        """
        Publica imagem a partir de bytes.
        
        Nota: A Graph API do Instagram não aceita upload direto.
        É necessário primeiro hospedar a imagem em uma URL pública.
        
        Esta função assume que você tem um endpoint para hospedar imagens.
        
        Args:
            image_bytes: Bytes da imagem
            caption: Texto do post
            upload_endpoint: Endpoint para upload temporário
            
        Returns:
            PostResult com status
        """
        if not upload_endpoint:
            return PostResult(
                success=False,
                error="Instagram Graph API requer URL pública. "
                      "Configure um endpoint de upload."
            )
        
        session = await self._get_session()
        
        try:
            # Upload para servidor temporário
            async with session.post(
                upload_endpoint,
                data={"image": image_bytes},
            ) as response:
                upload_data = await response.json()
                image_url = upload_data.get("url")
                
                if not image_url:
                    return PostResult(
                        success=False,
                        error="Falha ao obter URL da imagem uploadada"
                    )
            
            # Agora publica via URL
            return await self.upload_image_url(image_url, caption)
            
        except Exception as e:
            logger.error(f"Erro no upload: {e}")
            return PostResult(success=False, error=str(e))
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Obtém informações da conta do Instagram.
        
        Returns:
            Dados da conta
        """
        if not self.config:
            return {"error": "Configuração não definida"}
        
        session = await self._get_session()
        
        try:
            url = self._get_api_url(self.config.instagram_account_id)
            params = {
                "fields": "username,name,biography,followers_count,media_count",
                "access_token": self.config.access_token,
            }
            
            async with session.get(url, params=params) as response:
                return await response.json()
                
        except Exception as e:
            logger.error(f"Erro ao obter info da conta: {e}")
            return {"error": str(e)}
    
    async def get_recent_media(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém mídias recentes da conta.
        
        Args:
            limit: Número máximo de mídias
            
        Returns:
            Lista de mídias
        """
        if not self.config:
            return []
        
        session = await self._get_session()
        
        try:
            url = self._get_api_url(f"{self.config.instagram_account_id}/media")
            params = {
                "fields": "id,caption,media_type,timestamp,like_count,comments_count",
                "limit": limit,
                "access_token": self.config.access_token,
            }
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                return data.get("data", [])
                
        except Exception as e:
            logger.error(f"Erro ao obter mídias: {e}")
            return []
    
    def get_post_history(self) -> List[PostResult]:
        """Retorna histórico de publicações da sessão."""
        return self._post_history.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de uso."""
        successful = len([p for p in self._post_history if p.success])
        failed = len([p for p in self._post_history if not p.success])
        
        return {
            "daily_posts": self._daily_posts,
            "daily_limit": self._daily_limit,
            "remaining_today": self._daily_limit - self._daily_posts,
            "total_posts": len(self._post_history),
            "successful_posts": successful,
            "failed_posts": failed,
            "success_rate": successful / len(self._post_history) if self._post_history else 0,
        }


class MockInstagramService(InstagramService):
    """
    Versão mock do serviço para testes.
    
    Não faz chamadas reais à API.
    """
    
    def __init__(self):
        super().__init__(None)
        self._mock_posts: List[Dict[str, Any]] = []
    
    async def verify_token(self) -> Dict[str, Any]:
        return {
            "valid": True,
            "expires_at": None,
            "scopes": ["instagram_basic", "instagram_content_publish"],
        }
    
    async def upload_image_url(
        self,
        image_url: str,
        caption: str,
    ) -> PostResult:
        """Simula publicação."""
        import uuid
        
        post_id = f"mock_{uuid.uuid4().hex[:8]}"
        media_id = f"media_{uuid.uuid4().hex[:8]}"
        
        self._mock_posts.append({
            "id": post_id,
            "caption": caption,
            "image_url": image_url,
            "timestamp": datetime.now().isoformat(),
        })
        
        self._daily_posts += 1
        result = PostResult(
            success=True,
            post_id=post_id,
            media_id=media_id,
        )
        self._post_history.append(result)
        
        logger.info(f"[MOCK] Post simulado: {post_id}")
        return result
    
    async def upload_image_bytes(
        self,
        image_bytes: bytes,
        caption: str,
        upload_endpoint: str = None,
    ) -> PostResult:
        """Simula publicação de bytes."""
        # Simula URL da imagem
        fake_url = f"https://mock-images.example.com/{hash(image_bytes)}.jpg"
        return await self.upload_image_url(fake_url, caption)
    
    async def get_account_info(self) -> Dict[str, Any]:
        return {
            "id": "mock_account",
            "username": "virtusinvestimentos",
            "name": "Virtus Investimentos",
            "biography": "Trading inteligente com tecnologia de ponta.",
            "followers_count": 1000,
            "media_count": len(self._mock_posts),
        }
    
    async def get_recent_media(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._mock_posts[-limit:]


def create_instagram_service(
    access_token: Optional[str] = None,
    instagram_account_id: Optional[str] = None,
    page_id: Optional[str] = None,
    use_mock: bool = False,
) -> InstagramService:
    """
    Factory function para criar serviço do Instagram.
    
    Args:
        access_token: Token de acesso da Meta
        instagram_account_id: ID da conta do Instagram
        page_id: ID da Facebook Page
        use_mock: Se True, retorna versão mock para testes
        
    Returns:
        Instância do serviço
    """
    if use_mock:
        return MockInstagramService()
    
    if not all([access_token, instagram_account_id, page_id]):
        logger.warning(
            "Credenciais incompletas. "
            "Use MockInstagramService para testes ou configure as credenciais."
        )
        return MockInstagramService()
    
    config = InstagramConfig(
        access_token=access_token,
        instagram_account_id=instagram_account_id,
        page_id=page_id,
    )
    
    return InstagramService(config)
