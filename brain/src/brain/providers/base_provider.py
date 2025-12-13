"""
BRAIN - Base Provider
Interface base para todos os providers de dados
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import aiohttp
import asyncio

from ...core.logger import get_logger
from ...core.exceptions import ProviderError, RateLimitError

logger = get_logger("brain.provider")


class BaseProvider(ABC):
    """
    Classe base para providers de dados
    
    Todos os providers devem herdar desta classe e implementar
    os métodos abstratos.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._api_key = config.get("api_key")
        self._base_url = config.get("base_url", "")
        self._timeout = config.get("timeout", 30)
        self._enabled = config.get("enabled", True)
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def name(self) -> str:
        """Nome do provider"""
        return self.__class__.__name__
    
    @property
    def is_enabled(self) -> bool:
        """Verifica se provider está habilitado"""
        return self._enabled
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtém ou cria sessão HTTP"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Faz requisição HTTP
        
        Args:
            method: GET, POST, etc.
            endpoint: Endpoint da API
            params: Query parameters
            headers: Headers HTTP
            data: Body da requisição
            
        Returns:
            Resposta JSON
            
        Raises:
            ProviderError: Em caso de erro
            RateLimitError: Se rate limit atingido
        """
        session = await self._get_session()
        url = f"{self._base_url}{endpoint}"
        
        default_headers = self._get_default_headers()
        if headers:
            default_headers.update(headers)
        
        try:
            async with session.request(
                method=method,
                url=url,
                params=params,
                headers=default_headers,
                json=data
            ) as response:
                
                # Rate limit
                if response.status == 429:
                    raise RateLimitError(
                        self.name,
                        "Rate limit atingido",
                        None
                    )
                
                # Erro
                if response.status >= 400:
                    error_text = await response.text()
                    raise ProviderError(
                        self.name,
                        f"HTTP {response.status}: {error_text}"
                    )
                
                return await response.json()
                
        except aiohttp.ClientError as e:
            raise ProviderError(self.name, f"Erro de conexão: {e}", e)
        except asyncio.TimeoutError:
            raise ProviderError(self.name, "Timeout na requisição")
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Headers padrão para requisições"""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        
        return headers
    
    async def close(self):
        """Fecha conexões"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verifica se o provider está funcionando
        
        Returns:
            True se saudável
        """
        pass
