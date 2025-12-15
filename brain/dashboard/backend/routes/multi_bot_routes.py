"""
VIRTUS Dashboard - Rotas Multi-Bot
===================================

Endpoints para gerenciamento de múltiplos tipos de bot.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import sys
from pathlib import Path

# Adiciona path do src
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

# Tenta importar sistema multi-bot
bot_registry = None
BotConfig = None
BotType = None
BotStatus = None
MarketType = None

try:
    from src.bot.base import BotConfig, BotType, BotStatus, MarketType
    from src.bot.registry import bot_registry
    from src.bot.types import register_all_bot_types
    MULTI_BOT_AVAILABLE = True
    # Registra todos os tipos ao importar
    register_all_bot_types()
except ImportError as e:
    print(f"Warning: Could not import multi-bot system: {e}")
    MULTI_BOT_AVAILABLE = False

# Fallback - dados em memória quando sistema completo não disponível
_mock_bots: Dict[str, Dict] = {}

router = APIRouter(prefix="/bots/v2", tags=["Multi-Bot System"])

# ==================== MODELOS ====================

class BotTypeEnum(str, Enum):
    """Tipos de bot disponíveis."""
    FOREX = "forex"
    ARBITRAGE = "arbitrage"
    CRYPTO = "crypto"
    STOCKS = "stocks"
    FUTURES = "futures"
    OPTIONS = "options"
    CUSTOM = "custom"


class MarketTypeEnum(str, Enum):
    """Mercados/Exchanges disponíveis."""
    MT5 = "mt5"
    BINANCE = "binance"
    BYBIT = "bybit"
    FTX = "ftx"
    KRAKEN = "kraken"
    B3 = "b3"
    NYSE = "nyse"
    CUSTOM = "custom"


class CreateBotRequest(BaseModel):
    """Request para criar novo bot."""
    bot_id: Optional[str] = Field(None, description="ID único do bot (gerado se não fornecido)")
    name: str = Field(..., description="Nome do bot")
    bot_type: BotTypeEnum = Field(..., description="Tipo do bot")
    market: MarketTypeEnum = Field(..., description="Mercado/Exchange")
    symbols: List[str] = Field(default_factory=list, description="Símbolos para operar")
    strategies: List[str] = Field(default_factory=list, description="Estratégias a usar")
    
    # Risco
    max_position_size: float = Field(0.1, description="Tamanho máximo de posição")
    max_daily_loss: float = Field(100.0, description="Perda máxima diária")
    max_drawdown: float = Field(10.0, description="Drawdown máximo permitido")
    risk_per_trade: float = Field(1.0, description="Risco por operação (%)")
    
    # Operacional
    enabled: bool = Field(True, description="Bot habilitado")
    auto_start: bool = Field(False, description="Iniciar automaticamente")
    
    # Configurações específicas do tipo
    extra: Dict[str, Any] = Field(default_factory=dict, description="Config extra por tipo")


class BotResponse(BaseModel):
    """Resposta com dados de um bot."""
    id: str
    name: str
    type: str
    status: str
    market: str
    symbols: List[str]
    strategies: List[str]
    metrics: Dict[str, Any]
    positions: List[Dict[str, Any]]
    config: Dict[str, Any]


class BotControlRequest(BaseModel):
    """Request para controlar bot."""
    action: str = Field(..., description="Ação: start, stop, pause, resume")


class AggregatedMetricsResponse(BaseModel):
    """Métricas agregadas de todos os bots."""
    total_bots: int
    running_bots: int
    paused_bots: int
    stopped_bots: int
    error_bots: int
    total_trades: int
    total_profit: float
    total_win_rate: float
    by_type: Dict[str, Dict[str, Any]]
    by_market: Dict[str, Dict[str, Any]]
    last_update: str


# ==================== ENDPOINTS ====================

@router.get("/types")
async def get_available_types():
    """
    Lista tipos de bot disponíveis.
    
    Retorna todos os tipos que podem ser criados.
    """
    types_list = [
        {
            "id": "forex",
            "name": "Forex (MT5)",
            "description": "Trading de pares de moedas via MetaTrader 5",
            "markets": ["mt5"],
            "example_symbols": ["EURUSD", "GBPUSD", "XAUUSD"],
        },
        {
            "id": "arbitrage",
            "name": "Arbitragem",
            "description": "Arbitragem entre exchanges ou triangular",
            "markets": ["binance", "bybit", "kraken"],
            "example_symbols": ["BTC/USDT", "ETH/USDT"],
            "subtypes": ["cross_exchange", "triangular", "statistical"],
        },
        {
            "id": "crypto",
            "name": "Crypto Trading",
            "description": "Trading de criptomoedas em exchanges",
            "markets": ["binance", "bybit", "kraken"],
            "example_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        },
        {
            "id": "stocks",
            "name": "Ações",
            "description": "Trading de ações na B3/NYSE",
            "markets": ["b3", "nyse"],
            "example_symbols": ["PETR4.SA", "VALE3.SA", "AAPL"],
        },
    ]
    
    registered = []
    if MULTI_BOT_AVAILABLE and bot_registry:
        registered = bot_registry.get_registered_types()
    else:
        registered = ["forex", "arbitrage", "crypto", "stocks"]
    
    return {
        "types": types_list,
        "registered": registered,
        "system_available": MULTI_BOT_AVAILABLE,
    }


@router.get("/markets")
async def get_available_markets():
    """
    Lista mercados/exchanges disponíveis.
    """
    return {
        "markets": [
            {"id": "mt5", "name": "MetaTrader 5", "type": "forex"},
            {"id": "binance", "name": "Binance", "type": "crypto"},
            {"id": "bybit", "name": "Bybit", "type": "crypto"},
            {"id": "kraken", "name": "Kraken", "type": "crypto"},
            {"id": "b3", "name": "B3 (Brasil)", "type": "stocks"},
            {"id": "nyse", "name": "NYSE", "type": "stocks"},
        ]
    }


@router.post("", response_model=BotResponse)
async def create_bot(request: CreateBotRequest):
    """
    Cria um novo bot.
    
    O bot é criado mas não iniciado automaticamente
    (a menos que auto_start=True).
    """
    if not MULTI_BOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Multi-bot system not available")
    
    try:
        import uuid
        
        config = BotConfig(
            bot_id=request.bot_id or str(uuid.uuid4())[:8],
            name=request.name,
            bot_type=BotType(request.bot_type.value),
            market=MarketType(request.market.value),
            symbols=request.symbols,
            strategies=request.strategies,
            max_position_size=request.max_position_size,
            max_daily_loss=request.max_daily_loss,
            max_drawdown=request.max_drawdown,
            risk_per_trade=request.risk_per_trade,
            enabled=request.enabled,
            auto_start=request.auto_start,
            extra=request.extra,
        )
        
        bot = bot_registry.add_bot(config)
        
        if not bot:
            raise HTTPException(
                status_code=400, 
                detail="Could not create bot. Check if type is registered."
            )
        
        return BotResponse(**bot.get_state())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[BotResponse])
async def list_bots(
    bot_type: Optional[BotTypeEnum] = Query(None, description="Filtrar por tipo"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    market: Optional[MarketTypeEnum] = Query(None, description="Filtrar por mercado"),
):
    """
    Lista todos os bots com filtros opcionais.
    """
    if not MULTI_BOT_AVAILABLE:
        return []
    
    bots = bot_registry.get_all_bots()
    
    # Aplica filtros
    if bot_type:
        bots = [b for b in bots if b.bot_type.value == bot_type.value]
    
    if status:
        bots = [b for b in bots if b.status.value == status]
    
    if market:
        bots = [b for b in bots if b.config.market.value == market.value]
    
    return [BotResponse(**b.get_state()) for b in bots]


@router.get("/metrics", response_model=AggregatedMetricsResponse)
async def get_aggregated_metrics():
    """
    Retorna métricas agregadas de todos os bots.
    
    Útil para visualização consolidada no dashboard.
    """
    if not MULTI_BOT_AVAILABLE:
        return AggregatedMetricsResponse(
            total_bots=0,
            running_bots=0,
            paused_bots=0,
            stopped_bots=0,
            error_bots=0,
            total_trades=0,
            total_profit=0.0,
            total_win_rate=0.0,
            by_type={},
            by_market={},
            last_update=datetime.now().isoformat(),
        )
    
    agg = bot_registry.get_aggregated_metrics()
    return AggregatedMetricsResponse(**agg.to_dict())


@router.get("/dashboard")
async def get_dashboard_state():
    """
    Retorna estado completo para o dashboard.
    
    Inclui todos os bots, métricas agregadas e resumo.
    """
    if not MULTI_BOT_AVAILABLE:
        return {
            "bots": [],
            "aggregated": {},
            "registered_types": [],
            "summary": {"total": 0, "running": 0, "by_type": {}},
        }
    
    return bot_registry.get_dashboard_state()


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: str):
    """
    Obtém detalhes de um bot específico.
    """
    if not MULTI_BOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Multi-bot system not available")
    
    bot = bot_registry.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return BotResponse(**bot.get_state())


@router.post("/{bot_id}/control")
async def control_bot(bot_id: str, request: BotControlRequest):
    """
    Controla um bot (start/stop/pause/resume).
    """
    if not MULTI_BOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Multi-bot system not available")
    
    bot = bot_registry.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    valid_actions = ["start", "stop", "pause", "resume"]
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid action. Must be one of: {valid_actions}"
        )
    
    try:
        if request.action == "start":
            success = await bot.start()
        elif request.action == "stop":
            success = await bot.stop()
        elif request.action == "pause":
            success = await bot.pause()
        elif request.action == "resume":
            success = await bot.resume()
        else:
            success = False
        
        return {
            "success": success,
            "bot_id": bot_id,
            "action": request.action,
            "new_status": bot.status.value,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{bot_id}/config")
async def update_bot_config(bot_id: str, config_updates: Dict[str, Any]):
    """
    Atualiza configuração de um bot.
    
    O bot deve estar parado para atualizar algumas configs.
    """
    if not MULTI_BOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Multi-bot system not available")
    
    bot = bot_registry.get_bot(bot_id)
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Atualiza campos permitidos
    allowed_fields = [
        "name", "symbols", "strategies", "max_position_size",
        "max_daily_loss", "max_drawdown", "risk_per_trade",
        "enabled", "auto_start", "extra"
    ]
    
    for field, value in config_updates.items():
        if field in allowed_fields and hasattr(bot.config, field):
            setattr(bot.config, field, value)
    
    return {"success": True, "config": bot.config.to_dict()}


@router.delete("/{bot_id}")
async def delete_bot(bot_id: str):
    """
    Remove um bot do sistema.
    
    O bot será parado automaticamente se estiver rodando.
    """
    if not MULTI_BOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Multi-bot system not available")
    
    success = bot_registry.remove_bot(bot_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return {"success": True, "message": f"Bot {bot_id} removed"}


@router.post("/batch/start")
async def start_all_bots(bot_type: Optional[BotTypeEnum] = None):
    """
    Inicia múltiplos bots.
    
    Se bot_type for especificado, inicia apenas bots desse tipo.
    """
    if not MULTI_BOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Multi-bot system not available")
    
    if bot_type:
        results = await bot_registry.start_by_type(BotType(bot_type.value))
    else:
        results = await bot_registry.start_all()
    
    return {
        "success": True,
        "results": results,
        "started": sum(1 for v in results.values() if v),
    }


@router.post("/batch/stop")
async def stop_all_bots(bot_type: Optional[BotTypeEnum] = None):
    """
    Para múltiplos bots.
    
    Se bot_type for especificado, para apenas bots desse tipo.
    """
    if not MULTI_BOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Multi-bot system not available")
    
    if bot_type:
        results = await bot_registry.stop_by_type(BotType(bot_type.value))
    else:
        results = await bot_registry.stop_all()
    
    return {
        "success": True,
        "results": results,
        "stopped": sum(1 for v in results.values() if v),
    }
