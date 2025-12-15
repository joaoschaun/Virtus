"""
VIRTUS - TESS AI Client
========================

Cliente assíncrono para API da TESS AI (Pareto.io).
Permite acesso a +250 modelos de IA via uma única interface.

Endpoints principais:
- /agents: Lista agentes disponíveis
- /agents/{id}: Detalhes de um agente
- /agents/{id}/execute: Executa um agente

Documentação: https://tess.im/
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class TessConfig:
    """Configuração do cliente TESS."""
    api_key: str
    base_url: str = "https://tess.pareto.io/api"
    default_model: str = "gpt-4o-mini"
    default_language: str = "Portuguese (Brazil)"
    default_temperature: str = "0.5"
    timeout_seconds: int = 60


class TessError(Exception):
    """Erro base para operações TESS."""
    pass


class TessAuthError(TessError):
    """Erro de autenticação."""
    pass


class TessExecutionError(TessError):
    """Erro na execução de agente."""
    pass


class TessClient:
    """
    Cliente assíncrono para API da TESS AI.
    
    Uso básico:
        client = TessClient(api_key="sua_chave")
        result = await client.execute_agent(
            agent_id=131,
            inputs={"seu-objetivo": "Criar post sobre trading"}
        )
        print(result['output'])
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        config: Optional[TessConfig] = None
    ):
        """
        Inicializa cliente TESS.
        
        Args:
            api_key: Chave da API TESS
            config: Configuração completa (substitui api_key)
        """
        if config:
            self.config = config
        elif api_key:
            self.config = TessConfig(api_key=api_key)
        else:
            # Tenta carregar de variável de ambiente
            env_key = os.environ.get("TESS_API_KEY")
            if not env_key:
                raise TessAuthError("API key não fornecida. Configure TESS_API_KEY ou passe como parâmetro.")
            self.config = TessConfig(api_key=env_key)
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
    
    @property
    def headers(self) -> Dict[str, str]:
        """Headers padrão para requisições."""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna sessão HTTP, criando se necessário."""
        async with self._lock:
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                self._session = aiohttp.ClientSession(
                    headers=self.headers,
                    timeout=timeout
                )
            return self._session
    
    async def close(self):
        """Fecha a sessão HTTP."""
        async with self._lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    # ==================== AGENTES ====================
    
    async def list_agents(
        self, 
        search: Optional[str] = None,
        type_filter: Optional[str] = None,
        page: int = 1,
        per_page: int = 15
    ) -> Dict[str, Any]:
        """
        Lista agentes disponíveis.
        
        Args:
            search: Termo de busca
            type_filter: Filtro por tipo (text, image, etc)
            page: Página de resultados
            per_page: Resultados por página
            
        Returns:
            Dados paginados dos agentes
        """
        session = await self._get_session()
        
        params = {"page": page, "per_page": per_page}
        if search:
            params["search"] = search
        if type_filter:
            params["type"] = type_filter
        
        try:
            async with session.get(
                f"{self.config.base_url}/agents",
                params=params
            ) as response:
                if response.status == 401:
                    raise TessAuthError("Chave de API inválida")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Erro ao listar agentes: {e}")
            raise TessError(f"Erro na requisição: {e}")
    
    async def get_agent(self, agent_id: int) -> Dict[str, Any]:
        """
        Busca detalhes de um agente.
        
        Args:
            agent_id: ID do agente
            
        Returns:
            Detalhes do agente
        """
        session = await self._get_session()
        
        try:
            async with session.get(
                f"{self.config.base_url}/agents/{agent_id}"
            ) as response:
                if response.status == 404:
                    raise TessError(f"Agente {agent_id} não encontrado")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Erro ao buscar agente {agent_id}: {e}")
            raise TessError(f"Erro na requisição: {e}")
    
    async def execute_agent(
        self, 
        agent_id: int, 
        inputs: Dict[str, Any],
        wait: bool = True,
        model: Optional[str] = None,
        temperature: Optional[str] = None,
        max_length: Optional[int] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executa um agente TESS.
        
        Args:
            agent_id: ID do agente
            inputs: Parâmetros específicos do agente
            wait: Se True, aguarda execução completa
            model: Modelo a usar (sobrescreve default)
            temperature: Temperatura (0 a 1)
            max_length: Limite de palavras na resposta
            language: Idioma da resposta
            
        Returns:
            Resultado da execução incluindo 'output'
            
        Example:
            result = await client.execute_agent(
                agent_id=131,
                inputs={"seu-objetivo": "Criar post sobre ouro em alta"}
            )
            print(result['output'])  # Post gerado
        """
        session = await self._get_session()
        
        # Prepara payload com defaults
        payload = {**inputs}
        
        # Adiciona parâmetros padrão se não fornecidos
        if "model" not in payload:
            payload["model"] = model or self.config.default_model
        if "temperature" not in payload:
            payload["temperature"] = temperature or self.config.default_temperature
        if "language" not in payload:
            payload["language"] = language or self.config.default_language
        if max_length and "maxlength" not in payload:
            payload["maxlength"] = max_length
        
        # waitExecution para resposta síncrona
        if wait:
            payload["waitExecution"] = "true"
        
        logger.debug(f"Executando agente {agent_id} com inputs: {list(inputs.keys())}")
        
        try:
            async with session.post(
                f"{self.config.base_url}/agents/{agent_id}/execute",
                json=payload
            ) as response:
                if response.status == 401:
                    raise TessAuthError("Chave de API inválida")
                if response.status == 422:
                    error_data = await response.json()
                    raise TessExecutionError(f"Parâmetros inválidos: {error_data}")
                response.raise_for_status()
                
                data = await response.json()
                
                # Extrai resposta principal
                if data.get('responses') and len(data['responses']) > 0:
                    result = data['responses'][0]
                    
                    # Log de custos
                    credits = result.get('credits', 0)
                    logger.info(f"Agente {agent_id} executado. Créditos: {credits:.6f}")
                    
                    return result
                
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"Erro ao executar agente {agent_id}: {e}")
            raise TessExecutionError(f"Erro na execução: {e}")
    
    # ==================== MÉTODOS DE CONVENIÊNCIA ====================
    
    async def generate_instagram_caption(
        self, 
        objective: str,
        model: str = "gpt-4o-mini",
        max_length: int = 300
    ) -> str:
        """
        Gera caption para Instagram.
        
        Args:
            objective: Objetivo/contexto do post
            model: Modelo a usar
            max_length: Limite de palavras
            
        Returns:
            Caption gerada
        """
        result = await self.execute_agent(
            agent_id=131,  # Descrição para Post no Instagram
            inputs={"seu-objetivo": objective},
            model=model,
            max_length=max_length
        )
        return result.get('output', '')
    
    async def generate_linkedin_post(
        self, 
        content: str,
        model: str = "gpt-4o-mini",
        max_length: int = 400
    ) -> str:
        """
        Gera post para LinkedIn.
        
        Args:
            content: Conteúdo base para o post
            model: Modelo a usar
            max_length: Limite de palavras
            
        Returns:
            Post gerado
        """
        result = await self.execute_agent(
            agent_id=67,  # Transformar Texto em Post para LinkedIn
            inputs={"texto": content},
            model=model,
            max_length=max_length
        )
        return result.get('output', '')
    
    async def search_agents_by_type(self, agent_type: str) -> List[Dict]:
        """
        Busca agentes por tipo.
        
        Args:
            agent_type: Tipo do agente (text, image, video, audio)
            
        Returns:
            Lista de agentes
        """
        result = await self.list_agents(type_filter=agent_type, per_page=100)
        return result.get('data', [])
    
    # ==================== HEALTH CHECK ====================
    
    async def health_check(self) -> bool:
        """
        Verifica se a API está acessível.
        
        Returns:
            True se API está funcionando
        """
        try:
            await self.list_agents(per_page=1)
            return True
        except Exception as e:
            logger.warning(f"Health check falhou: {e}")
            return False


# ==================== SINGLETON ====================

_tess_client: Optional[TessClient] = None
_tess_lock = asyncio.Lock()


async def get_tess_client(api_key: Optional[str] = None) -> TessClient:
    """
    Retorna instância singleton do cliente TESS.
    
    Args:
        api_key: Chave da API (usa env var se não fornecida)
        
    Returns:
        Instância do TessClient
    """
    global _tess_client
    
    async with _tess_lock:
        if _tess_client is None:
            # Tenta várias fontes para a API key
            key = api_key or os.environ.get("TESS_API_KEY")
            
            # Tenta carregar de config.yaml se existir
            if not key:
                config_path = Path(__file__).parent.parent.parent.parent / "config" / "tess.yaml"
                if config_path.exists():
                    try:
                        import yaml
                        with open(config_path) as f:
                            config = yaml.safe_load(f)
                            key = config.get('api_key')
                    except Exception:
                        pass
            
            if not key:
                raise TessAuthError(
                    "TESS API key não encontrada. Configure via:\n"
                    "1. Parâmetro api_key\n"
                    "2. Variável de ambiente TESS_API_KEY\n"
                    "3. Arquivo config/tess.yaml"
                )
            
            _tess_client = TessClient(api_key=key)
        
        return _tess_client


# ==================== TESTE ====================

if __name__ == "__main__":
    async def test():
        """Teste básico do cliente."""
        import os
        
        # Configura API key para teste
        api_key = "337520|MzMxArNQnQAcO0XBz7CLbraeV4lA7L6ep9sHITpt59a4b449"
        
        async with TessClient(api_key=api_key) as client:
            # Health check
            print("🔍 Verificando conexão...")
            healthy = await client.health_check()
            print(f"   Status: {'✅ OK' if healthy else '❌ FALHOU'}")
            
            if healthy:
                # Lista alguns agentes
                print("\n📋 Listando agentes de texto...")
                agents = await client.list_agents(type_filter="text", per_page=5)
                for agent in agents.get('data', [])[:5]:
                    print(f"   - [{agent['id']}] {agent['title']}")
                
                # Gera caption de teste
                print("\n✍️ Gerando caption de teste...")
                caption = await client.generate_instagram_caption(
                    "Divulgar que o ouro subiu 2% hoje após dados de inflação dos EUA",
                    max_length=200
                )
                print(f"   Caption:\n{caption[:300]}...")
    
    asyncio.run(test())
