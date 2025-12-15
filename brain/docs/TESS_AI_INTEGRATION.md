# 🤖 TESS AI - Análise de Integração para VIRTUS

## 📋 Resumo Executivo

A **TESS AI** (Pareto.io) é uma plataforma brasileira que agrega +250 modelos de IA em uma única API, incluindo GPT-4, Claude, Gemini, Stable Diffusion, entre outros. Com a API testada e funcionando, identificamos **7 oportunidades principais** de integração no projeto Virtus.

---

## 🔑 Credenciais da API

```
URL Base: https://tess.pareto.io/api
API Key: 337520|MzMxArNQnQAcO0XBz7CLbraeV4lA7L6ep9sHITpt59a4b449
```

### Endpoints Disponíveis

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/agents` | GET | Lista agentes disponíveis (998 agentes) |
| `/agents/{id}` | GET | Detalhes de um agente específico |
| `/agents/{id}/execute` | POST | Executa um agente |
| `/agents?search={termo}` | GET | Busca agentes |
| `/agents?type=image` | GET | Lista agentes de imagem |

### Modelos Disponíveis

| Categoria | Modelos |
|-----------|---------|
| **Texto** | gpt-4o, gpt-4o-mini, claude-3-5-haiku, deepseek-r1, gemini-2.0-flash, grok-2, llama-3.1-405b |
| **Imagem** | Stable Diffusion 3.5, Flux, Leonardo AI, Google Imagen 4, GPT-5 Image |
| **Vídeo** | Runway Gen4, Veo 3, Kling AI 2.1, Luma Labs Ray 2.0 |

---

## 🎯 Oportunidades de Integração

### 1. 📱 **Social Media - Geração de Captions (Alta Prioridade)**

**Arquivo atual:** `brain/src/social/content_generator.py`

**Situação Atual:**
- Usa templates estáticos para gerar captions
- Textos repetitivos e genéricos

**Com TESS AI:**
- Captions dinâmicas e únicas usando IA
- Agente recomendado: **ID 131 - "Descrição para Post no Instagram"**
- Personalização por tipo de notícia (forex, crypto, gold)

**Implementação:**
```python
# Exemplo de integração
async def generate_caption_with_ai(news_content: str) -> str:
    response = await tess_client.execute_agent(
        agent_id=131,
        inputs={
            "seu-objetivo": f"Criar post sobre trading: {news_content}",
            "temperature": "0.75",
            "model": "gpt-4o-mini",
            "maxlength": 300,
            "language": "Portuguese (Brazil)"
        }
    )
    return response['output']
```

**Custo estimado:** ~0.06 créditos por post

---

### 2. 📊 **Análise de Sentimento de Notícias (Alta Prioridade)**

**Arquivo atual:** `brain/src/brain/brain_service.py`

**Situação Atual:**
- Análise de sentimento básica ou inexistente
- Dependência de APIs de terceiros

**Com TESS AI:**
- Análise profunda de sentimento usando GPT-4 ou Claude
- Extração de entidades financeiras
- Scoring de impacto no mercado

**Implementação:**
```python
async def analyze_news_sentiment(news_text: str) -> dict:
    prompt = f"""Analise a seguinte notícia financeira:
    {news_text}
    
    Retorne em JSON:
    - sentiment: bullish/bearish/neutral
    - impact_score: 0-10
    - affected_assets: [lista de ativos]
    - key_events: [eventos importantes]
    """
    # Usar TESS Chat com modelo de raciocínio (deepseek-r1)
```

---

### 3. 🖼️ **Geração de Imagens para Posts (Média Prioridade)**

**Arquivo atual:** `brain/src/social/image_generator.py`

**Situação Atual:**
- Usa Pillow para criar imagens estáticas
- Design limitado, sem fotos profissionais

**Com TESS AI:**
- Geração de imagens profissionais com IA
- Agentes disponíveis:
  - ID 153 - "Modelos Realistas para Mockup"
  - ID 156 - "Ilustrações no Estilo Pixar"
  - ID 159 - "Ícones 3D Modernos"

**Casos de uso:**
- Banners para eventos econômicos (FOMC, NFP)
- Imagens temáticas (ouro, forex, crypto)
- Gráficos estilizados

---

### 4. 🤖 **Chatbot no Dashboard (Média Prioridade)**

**Arquivo atual:** Novo módulo a criar

**Proposta:**
- Assistente de IA integrado ao dashboard
- Responde dúvidas sobre trading
- Explica sinais e análises do bot
- Baseado no contexto do Virtus

**Implementação:**
- Criar agente personalizado na TESS
- Integrar via WebSocket no frontend
- Memória de contexto por sessão

---

### 5. 📈 **Resumos de Performance (Média Prioridade)**

**Arquivo atual:** `brain/src/reporting/`

**Situação Atual:**
- Relatórios técnicos com números

**Com TESS AI:**
- Narrativas humanizadas dos resultados
- "O bot Gold teve um excelente desempenho esta semana, capturando 3 operações lucrativas..."
- Insights automáticos sobre o que funcionou/não funcionou

---

### 6. 📹 **Roteiros para Lives/Reels (Baixa Prioridade)**

**Agentes disponíveis:**
- ID 75 - "Transformar ideia em roteiro para LIVE"
- ID 76 - "Roteiro Completo para Live Streaming"
- ID 183 - "Roteiro de Reels para Instagram"

**Uso:**
- Criar conteúdo para YouTube/Instagram
- Roteiros de análise semanal
- Vídeos educacionais sobre trading

---

### 7. 🎯 **Marketing - Google/YouTube Ads (Baixa Prioridade)**

**Agentes disponíveis:**
- ID 45 - "Anúncios de Texto no Google Ads"
- ID 68 - "Ideias de anúncios para YouTube Ads"
- ID 59 - "Palavras-chave para campanha"

**Uso:**
- Criar campanhas de captação de clientes
- Copy para anúncios

---

## 📁 Estrutura de Arquivos Proposta

```
brain/
├── src/
│   └── integrations/
│       └── tess/
│           ├── __init__.py
│           ├── client.py           # Cliente HTTP para API TESS
│           ├── agents.py           # Mapeamento de agentes usados
│           └── services/
│               ├── caption_service.py    # Geração de captions
│               ├── sentiment_service.py  # Análise de sentimento
│               ├── image_service.py      # Geração de imagens
│               └── chat_service.py       # Chatbot
└── config/
    └── tess.yaml                   # Configurações TESS
```

---

## 🔧 Implementação Sugerida: Cliente Base

```python
# brain/src/integrations/tess/client.py
"""
VIRTUS - TESS AI Integration Client
====================================
"""

import aiohttp
from typing import Dict, Any, Optional
import asyncio


class TessClient:
    """Cliente assíncrono para API da TESS AI."""
    
    BASE_URL = "https://tess.pareto.io/api"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
        return self._session
    
    async def execute_agent(
        self, 
        agent_id: int, 
        inputs: Dict[str, Any],
        wait: bool = True
    ) -> Dict[str, Any]:
        """
        Executa um agente TESS.
        
        Args:
            agent_id: ID do agente
            inputs: Parâmetros do agente
            wait: Se True, aguarda execução completa
            
        Returns:
            Resultado da execução
        """
        session = await self._get_session()
        
        # Adiciona waitExecution se necessário
        if wait:
            inputs["waitExecution"] = "true"
        
        async with session.post(
            f"{self.BASE_URL}/agents/{agent_id}/execute",
            json=inputs
        ) as response:
            response.raise_for_status()
            data = await response.json()
            
            if data.get('responses') and len(data['responses']) > 0:
                return data['responses'][0]
            return data
    
    async def get_agent(self, agent_id: int) -> Dict[str, Any]:
        """Busca detalhes de um agente."""
        session = await self._get_session()
        
        async with session.get(
            f"{self.BASE_URL}/agents/{agent_id}"
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    async def search_agents(self, query: str) -> list:
        """Busca agentes por termo."""
        session = await self._get_session()
        
        async with session.get(
            f"{self.BASE_URL}/agents",
            params={"search": query}
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get('data', [])
    
    async def close(self):
        """Fecha a sessão."""
        if self._session and not self._session.closed:
            await self._session.close()


# Instância global
_tess_client: Optional[TessClient] = None


def get_tess_client() -> TessClient:
    """Retorna instância do cliente TESS."""
    global _tess_client
    if _tess_client is None:
        from ..core.config import get_config
        config = get_config()
        _tess_client = TessClient(config.tess_api_key)
    return _tess_client
```

---

## 📊 Comparativo de Custos

| Operação | Créditos TESS | Equivalente USD |
|----------|---------------|-----------------|
| Caption Instagram (GPT-4o-mini) | ~0.06 | ~$0.002 |
| Caption Instagram (GPT-4o) | ~0.30 | ~$0.010 |
| Análise de Sentimento (GPT-4o-mini) | ~0.10 | ~$0.003 |
| Geração de Imagem (Stable Diffusion) | ~0.50 | ~$0.015 |

**Estimativa mensal (uso moderado):**
- 30 posts/mês: ~2-3 créditos
- 100 análises de sentimento: ~10 créditos
- 10 imagens: ~5 créditos
- **Total: ~20 créditos/mês**

---

## ⚡ Próximos Passos

### Fase 1 - Imediato (Esta Semana)
1. ✅ Validar API TESS funcionando
2. ⏳ Criar cliente base (`tess/client.py`)
3. ⏳ Integrar geração de captions no `auto_post_generator.py`

### Fase 2 - Curto Prazo (2 semanas)
4. Implementar análise de sentimento no Brain
5. Testar agentes de imagem

### Fase 3 - Médio Prazo (1 mês)
6. Chatbot no dashboard
7. Resumos de performance com IA

---

## 🔗 Agentes Recomendados para Virtus

| ID | Nome | Uso no Virtus |
|----|------|---------------|
| 131 | Descrição para Post no Instagram | Captions de posts |
| 67 | Post para LinkedIn | Posts para LinkedIn |
| 183 | Roteiro de Reels | Conteúdo em vídeo |
| 76 | Live Streaming Instagram | Análises ao vivo |
| 153 | Mockup Realista | Imagens de produtos |

---

## 📞 Referências

- **Site TESS:** https://tess.im/
- **API Base:** https://tess.pareto.io/api
- **Documentação:** Verificar no painel TESS após login

---

## ✅ Status de Implementação

| Módulo | Status | Detalhes |
|--------|--------|----------|
| `src/integrations/tess/client.py` | ✅ Implementado | Cliente HTTP assíncrono |
| `src/integrations/tess/agents.py` | ✅ Implementado | IDs de agentes e modelos |
| `src/integrations/tess/caption_service.py` | ✅ Implementado | Serviço de geração de captions |
| `config/tess.yaml` | ✅ Configurado | API key e parâmetros |
| `auto_post_generator.py` | ✅ Integrado | Usa TESS para captions |

### Testes Realizados (14/12/2024)

```
✅ TessCaptionService - Importação bem sucedida
✅ Geração de caption Instagram - Funcionando (modelo: gpt-4o-mini)
✅ Auto Post Generator - TESS_ENABLED = True
✅ Geração automática - Posts criados com AI_GENERATED = True
✅ Créditos: ~0.03 por caption
```

---

*Documento criado em: 14/12/2024*
*Última atualização: 14/12/2024*
