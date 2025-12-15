"""
VIRTUS Brain - Base Provider
============================

Classe base para todos os providers de dados externos.
"""

import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime

from ...core.logger import get_logger
from ...core.exceptions import (
    APIError, APIConnectionError, APIRateLimitError,
    APIAuthenticationError, APIResponseError
)
from ..cache import CacheManager, get_cache_manager
from ..budget import BudgetManager, get_budget_manager

logger = get_logger("provider")


class BaseProvider(ABC):
    """
    Classe base abstrata para providers de API.
    
    Implementa:
    - Conexão HTTP com retry
    - Integração com cache
    - Controle de budget
    - Tratamento de erros
    """
    
    # Nome do provider (sobrescrever na subclasse)
    PROVIDER_NAME = "base"
    
    # URL base da API
    BASE_URL = ""
    
    # Headers padrão
    DEFAULT_HEADERS = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    def __init__(
        self,
        api_key: str,
        cache_manager: Optional[CacheManager] = None,
        budget_manager: Optional[BudgetManager] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.api_key = api_key
        self.cache_manager = cache_manager or get_cache_manager()
        self.budget_manager = budget_manager or get_budget_manager()
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna sessão HTTP, criando se necessário"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self.DEFAULT_HEADERS
            )
        return self._session
    
    async def close(self):
        """Fecha sessão HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _build_url(self, endpoint: str) -> str:
        """Constrói URL completa"""
        return f"{self.BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Faz requisição HTTP com retry e tratamento de erros.
        
        Args:
            method: GET, POST, etc.
            endpoint: Endpoint da API
            params: Query parameters
            data: Body data
            headers: Headers adicionais
            
        Returns:
            Resposta JSON da API
            
        Raises:
            APIError: Erro de API
        """
        # Verifica budget
        if not await self.budget_manager.can_make_request(self.PROVIDER_NAME):
            raise APIRateLimitError(
                message=f"Budget excedido para {self.PROVIDER_NAME}",
                provider=self.PROVIDER_NAME
            )
        
        url = self._build_url(endpoint)
        session = await self._get_session()
        
        request_headers = {**self.DEFAULT_HEADERS}
        if headers:
            request_headers.update(headers)
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=request_headers
                ) as response:
                    # Rate limit
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        raise APIRateLimitError(
                            message="Rate limit excedido",
                            provider=self.PROVIDER_NAME,
                            retry_after=retry_after
                        )
                    
                    # Autenticação
                    if response.status in [401, 403]:
                        raise APIAuthenticationError(
                            message="Erro de autenticação",
                            provider=self.PROVIDER_NAME,
                            status_code=response.status
                        )
                    
                    # Erro de servidor
                    if response.status >= 500:
                        text = await response.text()
                        raise APIResponseError(
                            message=f"Erro de servidor: {response.status}",
                            provider=self.PROVIDER_NAME,
                            status_code=response.status,
                            details=text
                        )
                    
                    # Erro genérico
                    if response.status >= 400:
                        text = await response.text()
                        raise APIResponseError(
                            message=f"Erro na API: {response.status}",
                            provider=self.PROVIDER_NAME,
                            status_code=response.status,
                            details=text
                        )
                    
                    # Sucesso - registra no budget
                    await self.budget_manager.register_request(self.PROVIDER_NAME)
                    
                    # Retorna JSON
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                last_error = APIConnectionError(
                    message=f"Erro de conexão: {str(e)}",
                    provider=self.PROVIDER_NAME
                )
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Tentativa {attempt + 1} falhou para {self.PROVIDER_NAME}, "
                        f"aguardando {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                    
            except APIError:
                raise
                
            except Exception as e:
                last_error = APIError(
                    message=f"Erro inesperado: {str(e)}",
                    provider=self.PROVIDER_NAME
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
        
        raise last_error or APIError(
            message="Erro desconhecido",
            provider=self.PROVIDER_NAME
        )
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Faz requisição GET"""
        return await self._make_request("GET", endpoint, params=params, headers=headers)
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Faz requisição POST"""
        return await self._make_request("POST", endpoint, params=params, data=data, headers=headers)
    
    # ========================================================================
    # MÉTODOS ABSTRATOS (implementar na subclasse)
    # ========================================================================
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica se o provider está disponível"""
        pass
    
    @abstractmethod
    async def get_supported_symbols(self) -> List[str]:
        """Retorna símbolos suportados pelo provider"""
        pass


class NewsProvider(BaseProvider):
    """Base para providers de notícias"""
    
    @abstractmethod
    async def get_news(
        self,
        symbols: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Busca notícias para símbolos"""
        pass


class SentimentProvider(BaseProvider):
    """Base para providers de sentimento"""
    
    @abstractmethod
    async def get_sentiment(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """Busca sentimento para símbolo"""
        pass


class CalendarProvider(BaseProvider):
    """Base para providers de calendário econômico"""
    
    @abstractmethod
    async def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        currencies: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Busca eventos do calendário"""
        pass


class MarketDataProvider(BaseProvider):
    """Base para providers de dados de mercado"""
    
    @abstractmethod
    async def get_price(self, symbol: str) -> Dict[str, Any]:
        """Busca preço atual"""
        pass
    
    @abstractmethod
    async def get_historical(
        self,
        symbol: str,
        interval: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Busca dados históricos"""
        pass
