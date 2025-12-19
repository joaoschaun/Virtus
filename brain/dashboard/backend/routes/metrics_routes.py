"""
VIRTUS - Routes para Métricas Prometheus
=========================================

Endpoint /metrics para coleta pelo Prometheus/Grafana.
"""

import sys
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

# Adiciona path do src
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

router = APIRouter(tags=["Monitoring"])

# Import do módulo de métricas
try:
    from src.monitoring.prometheus_metrics import registry, update_system_metrics
    METRICS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Prometheus Metrics module not available: {e}")
    METRICS_AVAILABLE = False


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    Endpoint Prometheus.
    
    Retorna métricas no formato Prometheus para scraping.
    Configure no prometheus.yml:
    
    scrape_configs:
      - job_name: 'virtus'
        static_configs:
          - targets: ['localhost:8000']
    """
    if not METRICS_AVAILABLE:
        return "# Prometheus metrics not available\n"
    
    try:
        # Atualiza métricas do sistema
        update_system_metrics()
        
        # Exporta todas as métricas (usa collect, não export)
        return registry.collect()
    except Exception as e:
        return f"# Error exporting metrics: {e}\n"


@router.get("/metrics/status")
async def metrics_status():
    """Retorna status do sistema de métricas."""
    if not METRICS_AVAILABLE:
        return {"available": False, "message": "Métricas Prometheus não disponíveis"}
    
    return {
        "available": True,
        "metrics_count": len(registry._metrics),
        "metrics": list(registry._metrics.keys()),
    }
