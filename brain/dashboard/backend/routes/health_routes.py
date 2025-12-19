"""
VIRTUS - Health Check Unificado
================================

Endpoint único que verifica saúde de todos os componentes.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
import psutil
import os

router = APIRouter(tags=["Health"])


class HealthStatus(str, Enum):
    """Status de saúde."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Verificador de saúde de componentes."""
    
    def __init__(self):
        self._checks: Dict[str, callable] = {}
    
    def register(self, name: str, check_func: callable):
        """Registra verificação de componente."""
        self._checks[name] = check_func
    
    async def check_all(self) -> Dict[str, Dict]:
        """Executa todas as verificações."""
        results = {}
        
        for name, check_func in self._checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                results[name] = result
            except Exception as e:
                results[name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "error": str(e)
                }
        
        return results


# Instância global
health_checker = ComponentHealth()


# ==================== VERIFICAÇÕES ====================

async def check_mt5() -> Dict:
    """Verifica conexão MT5."""
    try:
        import MetaTrader5 as mt5
        
        if not mt5.initialize():
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": "MT5 não inicializado",
                "connected": False
            }
        
        account = mt5.account_info()
        if account:
            return {
                "status": HealthStatus.HEALTHY,
                "connected": True,
                "account": account.login,
                "server": account.server,
                "balance": account.balance
            }
        else:
            return {
                "status": HealthStatus.DEGRADED,
                "connected": True,
                "error": "Sem info da conta"
            }
            
    except ImportError:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": "Módulo MT5 não instalado",
            "connected": False
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "connected": False
        }


def check_database() -> Dict:
    """Verifica banco de dados."""
    from pathlib import Path
    
    # Caminho base do projeto
    base_path = Path(__file__).parent.parent.parent.parent  # brain/
    
    db_paths = [
        base_path / "data" / "brain" / "virtus.db",
        base_path / "data" / "brain" / "brain.db",
        base_path / "data" / "virtus.db"
    ]
    
    for db_path in db_paths:
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            return {
                "status": HealthStatus.HEALTHY,
                "path": str(db_path),
                "size_mb": round(size_mb, 2),
                "writable": os.access(db_path, os.W_OK)
            }
    
    return {
        "status": HealthStatus.DEGRADED,
        "error": "Banco de dados não encontrado",
        "paths_checked": [str(p) for p in db_paths]
    }


def check_disk_space() -> Dict:
    """Verifica espaço em disco."""
    try:
        disk = psutil.disk_usage('/')
        free_gb = disk.free / (1024 ** 3)
        percent_used = disk.percent
        
        if free_gb < 1:
            status = HealthStatus.UNHEALTHY
        elif free_gb < 5:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        return {
            "status": status,
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(free_gb, 2),
            "percent_used": percent_used
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)
        }


def check_memory() -> Dict:
    """Verifica uso de memória."""
    try:
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024 ** 3)
        
        if memory.percent > 90:
            status = HealthStatus.UNHEALTHY
        elif memory.percent > 80:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        return {
            "status": status,
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(available_gb, 2),
            "percent_used": memory.percent
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)
        }


def check_cpu() -> Dict:
    """Verifica uso de CPU."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        if cpu_percent > 90:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        return {
            "status": status,
            "percent_used": cpu_percent,
            "cores": psutil.cpu_count()
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)
        }


async def check_brain_api() -> Dict:
    """Verifica Brain API."""
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:8001/api/health")
            
            if response.status_code == 200:
                return {
                    "status": HealthStatus.HEALTHY,
                    "url": "http://localhost:8001",
                    "response": response.json()
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "url": "http://localhost:8001",
                    "http_status": response.status_code
                }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "url": "http://localhost:8001",
            "error": str(e)
        }


def check_config() -> Dict:
    """Verifica configurações."""
    from pathlib import Path
    
    # Caminho base do projeto
    base_path = Path(__file__).parent.parent.parent.parent  # brain/
    
    config_files = [
        base_path / "config" / "config.yaml",
        base_path / "config" / "brain.yaml"
    ]
    
    missing = []
    found = []
    
    for config in config_files:
        if config.exists():
            found.append(str(config))
        else:
            missing.append(str(config))
    
    if missing and not found:
        status = HealthStatus.UNHEALTHY
    elif missing:
        status = HealthStatus.DEGRADED
    else:
        status = HealthStatus.HEALTHY
    
    return {
        "status": status,
        "found": found,
        "missing": missing
    }


# Registra verificações padrão
health_checker.register("mt5", check_mt5)
health_checker.register("database", check_database)
health_checker.register("disk", check_disk_space)
health_checker.register("memory", check_memory)
health_checker.register("cpu", check_cpu)
health_checker.register("brain_api", check_brain_api)
health_checker.register("config", check_config)


# ==================== ENDPOINTS ====================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check completo do sistema.
    
    Retorna status de todos os componentes.
    """
    components = await health_checker.check_all()
    
    # Determina status geral
    statuses = [c.get("status", HealthStatus.UNHEALTHY) for c in components.values()]
    
    if all(s == HealthStatus.HEALTHY for s in statuses):
        overall = HealthStatus.HEALTHY
    elif any(s == HealthStatus.UNHEALTHY for s in statuses):
        overall = HealthStatus.UNHEALTHY
    else:
        overall = HealthStatus.DEGRADED
    
    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0",
        "components": components
    }


@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe - verifica se o serviço está vivo.
    
    Usado por Kubernetes/Docker para verificar se o container está rodando.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness probe - verifica se o serviço está pronto para receber requisições.
    
    Usado por Kubernetes/Docker para verificar se pode receber tráfego.
    """
    # Verifica componentes críticos
    mt5_health = await check_mt5()
    db_health = check_database()
    
    is_ready = (
        mt5_health.get("status") != HealthStatus.UNHEALTHY and
        db_health.get("status") != HealthStatus.UNHEALTHY
    )
    
    if is_ready:
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "mt5": mt5_health,
                "database": db_health
            }
        )


@router.get("/health/{component}")
async def component_health(component: str):
    """
    Health check de um componente específico.
    """
    if component not in health_checker._checks:
        raise HTTPException(
            status_code=404,
            detail=f"Componente não encontrado: {component}. "
                   f"Disponíveis: {list(health_checker._checks.keys())}"
        )
    
    check_func = health_checker._checks[component]
    
    if asyncio.iscoroutinefunction(check_func):
        result = await check_func()
    else:
        result = check_func()
    
    return {
        "component": component,
        "timestamp": datetime.utcnow().isoformat(),
        **result
    }
