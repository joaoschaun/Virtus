"""
VIRTUS - Routes para Sistema de Plugins
========================================

Endpoints REST para gerenciamento de estratégias/plugins.
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

# Adiciona path do src
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

router = APIRouter(prefix="/plugins", tags=["Strategy Plugins"])

# Import do módulo de plugins
try:
    from src.strategies.plugin_system import plugin_manager
    PLUGINS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Plugin System module not available: {e}")
    PLUGINS_AVAILABLE = False


class PluginConfigRequest(BaseModel):
    config: Dict[str, Any]


@router.get("/status")
async def get_plugins_status():
    """Retorna status do sistema de plugins."""
    if not PLUGINS_AVAILABLE:
        return {"available": False, "message": "Sistema de Plugins não disponível"}
    
    return {
        "available": True,
        "plugins_count": len(plugin_manager.plugins),
        "plugins": [p["name"] for p in plugin_manager.list_plugins()],
    }


@router.get("/")
async def list_strategy_plugins():
    """Lista todas as estratégias disponíveis."""
    if not PLUGINS_AVAILABLE:
        raise HTTPException(503, "Sistema de Plugins não disponível")
    
    return plugin_manager.list_plugins()


@router.get("/{name}")
async def get_strategy_plugin(name: str):
    """Retorna detalhes de uma estratégia."""
    if not PLUGINS_AVAILABLE:
        raise HTTPException(503, "Sistema de Plugins não disponível")
    
    plugin = plugin_manager.get_plugin(name)
    if not plugin:
        raise HTTPException(404, "Plugin não encontrado")
    
    return {
        **plugin.info.to_dict(),
        "enabled": plugin.enabled,
        "config": plugin.config,
        "default_config": plugin.get_default_config(),
        "stats": plugin.get_stats(),
        "last_signal": plugin.last_signal.to_dict() if plugin.last_signal else None,
    }


@router.post("/{name}/enable")
async def enable_strategy_plugin(name: str):
    """Habilita uma estratégia."""
    if not PLUGINS_AVAILABLE:
        raise HTTPException(503, "Sistema de Plugins não disponível")
    
    if plugin_manager.enable_plugin(name):
        return {"message": f"Plugin {name} habilitado"}
    raise HTTPException(404, "Plugin não encontrado")


@router.post("/{name}/disable")
async def disable_strategy_plugin(name: str):
    """Desabilita uma estratégia."""
    if not PLUGINS_AVAILABLE:
        raise HTTPException(503, "Sistema de Plugins não disponível")
    
    if plugin_manager.disable_plugin(name):
        return {"message": f"Plugin {name} desabilitado"}
    raise HTTPException(404, "Plugin não encontrado")


@router.post("/{name}/configure")
async def configure_strategy_plugin(name: str, request: PluginConfigRequest):
    """Configura uma estratégia."""
    if not PLUGINS_AVAILABLE:
        raise HTTPException(503, "Sistema de Plugins não disponível")
    
    if plugin_manager.configure_plugin(name, request.config):
        return {"message": f"Plugin {name} configurado", "config": request.config}
    raise HTTPException(404, "Plugin não encontrado")


@router.post("/reload")
async def reload_plugins():
    """Recarrega todos os plugins do diretório."""
    if not PLUGINS_AVAILABLE:
        raise HTTPException(503, "Sistema de Plugins não disponível")
    
    count = plugin_manager.load_plugins()
    return {"message": f"{count} plugins carregados", "count": count}
