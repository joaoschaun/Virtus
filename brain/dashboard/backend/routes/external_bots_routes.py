"""
VIRTUS Dashboard - Rotas para Bots Externos
=============================================

Sistema de integração para bots externos via API Key.
Permite que bots de terceiros enviem sinais, trades e métricas.

Bots Integrados:
- Thanos Bot (thanos_bot_2024)
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Header, Query, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# Path para dados
BRAIN_PATH = Path(__file__).parent.parent.parent.parent
DATA_PATH = BRAIN_PATH / "data"
EXTERNAL_BOTS_PATH = DATA_PATH / "external_bots"
API_KEYS_FILE = EXTERNAL_BOTS_PATH / "api_keys.json"

# Garante que o diretório existe
EXTERNAL_BOTS_PATH.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/external", tags=["External Bots Integration"])

# ==================== API KEY SYSTEM ====================

# Header para API Key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyInfo(BaseModel):
    """Informações de uma API Key."""
    key_id: str
    bot_name: str
    bot_id: str
    created_at: str
    last_used: Optional[str] = None
    is_active: bool = True
    permissions: List[str] = ["read", "write"]
    rate_limit: int = 100  # requests per minute
    metadata: Dict[str, Any] = {}


class APIKeyStorage:
    """Gerenciador de API Keys."""
    
    def __init__(self):
        self._keys: Dict[str, APIKeyInfo] = {}
        self._load_keys()
    
    def _load_keys(self):
        """Carrega keys do arquivo."""
        if API_KEYS_FILE.exists():
            try:
                with open(API_KEYS_FILE, 'r') as f:
                    data = json.load(f)
                    for key_hash, info in data.items():
                        self._keys[key_hash] = APIKeyInfo(**info)
            except Exception as e:
                print(f"Error loading API keys: {e}")
    
    def _save_keys(self):
        """Salva keys no arquivo."""
        try:
            data = {k: v.dict() for k, v in self._keys.items()}
            with open(API_KEYS_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving API keys: {e}")
    
    def generate_key(self, bot_name: str, bot_id: str, permissions: List[str] = None) -> tuple:
        """
        Gera uma nova API Key.
        
        Returns:
            (api_key, key_info) - A key só é retornada uma vez!
        """
        # Gera key aleatória
        api_key = f"vts_{secrets.token_urlsafe(32)}"
        
        # Hash para armazenamento
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Cria info
        info = APIKeyInfo(
            key_id=key_hash[:16],
            bot_name=bot_name,
            bot_id=bot_id,
            created_at=datetime.now().isoformat(),
            permissions=permissions or ["read", "write", "trade"],
            metadata={"created_by": "system"}
        )
        
        self._keys[key_hash] = info
        self._save_keys()
        
        return api_key, info
    
    def validate_key(self, api_key: str) -> Optional[APIKeyInfo]:
        """Valida uma API Key."""
        if not api_key:
            return None
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        info = self._keys.get(key_hash)
        
        if info and info.is_active:
            # Atualiza last_used
            info.last_used = datetime.now().isoformat()
            self._save_keys()
            return info
        
        return None
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoga uma API Key."""
        for key_hash, info in self._keys.items():
            if info.key_id == key_id:
                info.is_active = False
                self._save_keys()
                return True
        return False
    
    def get_all_keys(self) -> List[APIKeyInfo]:
        """Retorna todas as keys (sem o hash)."""
        return list(self._keys.values())


# Instância global
api_key_storage = APIKeyStorage()


async def verify_api_key(x_api_key: str = Depends(api_key_header)) -> APIKeyInfo:
    """Dependency para verificar API Key."""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API Key required. Use header: X-API-Key"
        )
    
    info = api_key_storage.validate_key(x_api_key)
    
    if not info:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API Key"
        )
    
    return info


# ==================== MODELS ====================

class SignalDirection(str, Enum):
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"


class TradeStatus(str, Enum):
    PENDING = "pending"
    OPENED = "opened"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    ERROR = "error"


class ExternalSignal(BaseModel):
    """Sinal enviado por bot externo."""
    symbol: str = Field(..., description="Símbolo do ativo (ex: XAUUSD)")
    direction: SignalDirection = Field(..., description="Direção do sinal")
    entry_price: Optional[float] = Field(None, description="Preço de entrada sugerido")
    stop_loss: Optional[float] = Field(None, description="Stop Loss")
    take_profit: Optional[float] = Field(None, description="Take Profit")
    confidence: float = Field(0.7, ge=0, le=1, description="Confiança do sinal (0-1)")
    timeframe: str = Field("M15", description="Timeframe da análise")
    strategy: str = Field("external", description="Nome da estratégia")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dados adicionais")


class ExternalTrade(BaseModel):
    """Trade reportado por bot externo."""
    external_id: str = Field(..., description="ID do trade no sistema externo")
    symbol: str = Field(..., description="Símbolo do ativo")
    direction: SignalDirection = Field(..., description="Direção")
    status: TradeStatus = Field(..., description="Status do trade")
    entry_price: float = Field(..., description="Preço de entrada")
    current_price: Optional[float] = Field(None, description="Preço atual")
    exit_price: Optional[float] = Field(None, description="Preço de saída")
    volume: float = Field(..., description="Volume/Lotes")
    stop_loss: Optional[float] = Field(None)
    take_profit: Optional[float] = Field(None)
    profit: float = Field(0, description="Lucro/Prejuízo")
    profit_pips: float = Field(0, description="Lucro em pips")
    open_time: str = Field(..., description="Data/hora abertura ISO")
    close_time: Optional[str] = Field(None, description="Data/hora fechamento ISO")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BotStatus(BaseModel):
    """Status do bot externo."""
    is_running: bool = Field(..., description="Bot está rodando")
    is_connected: bool = Field(..., description="Conectado ao broker/exchange")
    account_balance: Optional[float] = Field(None, description="Saldo da conta")
    account_equity: Optional[float] = Field(None, description="Equity")
    open_positions: int = Field(0, description="Posições abertas")
    daily_profit: float = Field(0, description="Lucro do dia")
    daily_trades: int = Field(0, description="Trades do dia")
    uptime_seconds: int = Field(0, description="Tempo online")
    last_trade_time: Optional[str] = Field(None, description="Último trade")
    errors: List[str] = Field(default_factory=list, description="Erros recentes")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BotMetrics(BaseModel):
    """Métricas do bot externo."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    total_profit_pips: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    period: str = "all_time"  # daily, weekly, monthly, all_time


class Position(BaseModel):
    """Posição aberta."""
    ticket: int = Field(..., description="Ticket da posição no MT5")
    symbol: str = Field(..., description="Símbolo do ativo")
    direction: SignalDirection = Field(..., description="BUY ou SELL")
    volume: float = Field(..., description="Volume em lotes")
    entry_price: float = Field(..., description="Preço de entrada")
    current_price: float = Field(..., description="Preço atual")
    stop_loss: Optional[float] = Field(None, description="Stop Loss")
    take_profit: Optional[float] = Field(None, description="Take Profit")
    profit: float = Field(0, description="Lucro/Prejuízo em $")
    profit_pips: float = Field(0, description="Lucro em pips")
    open_time: str = Field(..., description="Data/hora abertura ISO")
    swap: float = Field(0, description="Swap")
    commission: float = Field(0, description="Comissão")
    magic: int = Field(0, description="Magic number")
    comment: str = Field("", description="Comentário")


class FullUpdate(BaseModel):
    """Atualização completa do bot - envie a cada 30-60s."""
    # Status básico
    is_running: bool = Field(True, description="Bot está rodando")
    is_connected: bool = Field(True, description="Conectado ao broker")
    
    # Account info
    account_balance: float = Field(..., description="Saldo da conta")
    account_equity: float = Field(..., description="Equity atual")
    account_margin: float = Field(0, description="Margem utilizada")
    account_free_margin: float = Field(0, description="Margem livre")
    account_profit: float = Field(0, description="Lucro flutuante")
    
    # Posições abertas
    positions: List[Position] = Field(default_factory=list, description="Posições abertas")
    
    # Métricas do dia
    daily_profit: float = Field(0, description="Lucro do dia em $")
    daily_profit_pips: float = Field(0, description="Lucro do dia em pips")
    daily_trades: int = Field(0, description="Número de trades do dia")
    daily_wins: int = Field(0, description="Trades vencedores do dia")
    daily_losses: int = Field(0, description="Trades perdedores do dia")
    
    # Métricas gerais
    total_trades: int = Field(0, description="Total de trades histórico")
    total_profit: float = Field(0, description="Lucro total histórico")
    win_rate: float = Field(0, description="Win rate geral (0-100)")
    max_drawdown: float = Field(0, description="Drawdown máximo")
    
    # Info adicional
    uptime_seconds: int = Field(0, description="Tempo online em segundos")
    last_trade_time: Optional[str] = Field(None, description="Último trade ISO")
    bot_version: str = Field("1.0.0", description="Versão do bot")
    strategy_name: str = Field("", description="Nome da estratégia ativa")
    errors: List[str] = Field(default_factory=list, description="Últimos erros")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dados extras")


# ==================== DATA STORAGE ====================

class ExternalBotData:
    """Armazena dados dos bots externos."""
    
    def __init__(self, bot_id: str):
        self.bot_id = bot_id
        self.data_path = EXTERNAL_BOTS_PATH / bot_id
        self.data_path.mkdir(parents=True, exist_ok=True)
    
    def save_signal(self, signal: ExternalSignal, api_info: APIKeyInfo):
        """Salva sinal recebido."""
        signals_file = self.data_path / "signals.json"
        signals = []
        
        if signals_file.exists():
            with open(signals_file, 'r') as f:
                signals = json.load(f)
        
        signal_data = signal.dict()
        signal_data['received_at'] = datetime.now().isoformat()
        signal_data['bot_name'] = api_info.bot_name
        signal_data['signal_id'] = f"{self.bot_id}_{len(signals)+1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        signals.append(signal_data)
        
        # Mantém últimos 1000 sinais
        signals = signals[-1000:]
        
        with open(signals_file, 'w') as f:
            json.dump(signals, f, indent=2, default=str)
        
        return signal_data
    
    def save_trade(self, trade: ExternalTrade, api_info: APIKeyInfo):
        """Salva trade recebido."""
        trades_file = self.data_path / "trades.json"
        trades = []
        
        if trades_file.exists():
            with open(trades_file, 'r') as f:
                trades = json.load(f)
        
        trade_data = trade.dict()
        trade_data['received_at'] = datetime.now().isoformat()
        trade_data['bot_name'] = api_info.bot_name
        trade_data['internal_id'] = f"{self.bot_id}_trade_{trade.external_id}"
        
        # Atualiza se já existe
        existing_idx = None
        for i, t in enumerate(trades):
            if t.get('external_id') == trade.external_id:
                existing_idx = i
                break
        
        if existing_idx is not None:
            trades[existing_idx] = trade_data
        else:
            trades.append(trade_data)
        
        # Mantém últimos 5000 trades
        trades = trades[-5000:]
        
        with open(trades_file, 'w') as f:
            json.dump(trades, f, indent=2, default=str)
        
        return trade_data
    
    def save_status(self, status: BotStatus, api_info: APIKeyInfo):
        """Salva status do bot."""
        status_file = self.data_path / "status.json"
        
        status_data = status.dict()
        status_data['updated_at'] = datetime.now().isoformat()
        status_data['bot_name'] = api_info.bot_name
        status_data['bot_id'] = self.bot_id
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2, default=str)
        
        return status_data
    
    def save_metrics(self, metrics: BotMetrics, api_info: APIKeyInfo):
        """Salva métricas do bot."""
        metrics_file = self.data_path / "metrics.json"
        
        metrics_data = metrics.dict()
        metrics_data['updated_at'] = datetime.now().isoformat()
        metrics_data['bot_name'] = api_info.bot_name
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2, default=str)
        
        return metrics_data
    
    def get_signals(self, limit: int = 100) -> List[dict]:
        """Retorna sinais."""
        signals_file = self.data_path / "signals.json"
        if signals_file.exists():
            with open(signals_file, 'r') as f:
                signals = json.load(f)
                return signals[-limit:]
        return []
    
    def get_trades(self, limit: int = 100, status: str = None) -> List[dict]:
        """Retorna trades."""
        trades_file = self.data_path / "trades.json"
        if trades_file.exists():
            with open(trades_file, 'r') as f:
                trades = json.load(f)
                if status:
                    trades = [t for t in trades if t.get('status') == status]
                return trades[-limit:]
        return []
    
    def get_status(self) -> Optional[dict]:
        """Retorna status."""
        status_file = self.data_path / "status.json"
        if status_file.exists():
            with open(status_file, 'r') as f:
                return json.load(f)
        return None
    
    def get_metrics(self) -> Optional[dict]:
        """Retorna métricas."""
        metrics_file = self.data_path / "metrics.json"
        if metrics_file.exists():
            with open(metrics_file, 'r') as f:
                return json.load(f)
        return None


# ==================== ENDPOINTS ====================

@router.get("/info")
async def get_integration_info():
    """
    Informações sobre a API de integração.
    
    Retorna documentação básica para desenvolvedores.
    """
    return {
        "api_version": "1.0.0",
        "description": "VIRTUS External Bots Integration API",
        "authentication": {
            "method": "API Key",
            "header": "X-API-Key",
            "example": "X-API-Key: vts_xxxxxxxxxxxxx"
        },
        "endpoints": {
            "POST /api/external/signal": "Enviar sinal de trading",
            "POST /api/external/trade": "Reportar trade executado",
            "POST /api/external/status": "Atualizar status do bot",
            "POST /api/external/metrics": "Enviar métricas",
            "GET /api/external/signals": "Listar sinais enviados",
            "GET /api/external/trades": "Listar trades",
            "GET /api/external/bot-status": "Obter status atual",
        },
        "rate_limit": "100 requests/minute",
        "contact": "admin@virtusinvestimentos.com.br"
    }


@router.post("/signal")
async def submit_signal(
    signal: ExternalSignal,
    api_info: APIKeyInfo = Depends(verify_api_key)
):
    """
    Envia um sinal de trading.
    
    O sinal será processado pelo sistema VIRTUS e pode gerar
    uma operação se passar nos filtros de risco.
    """
    try:
        bot_data = ExternalBotData(api_info.bot_id)
        saved = bot_data.save_signal(signal, api_info)
        
        # TODO: Processar sinal no sistema VIRTUS
        # - Validar com risk manager
        # - Enviar para execution se aprovado
        
        return {
            "success": True,
            "signal_id": saved['signal_id'],
            "message": "Signal received and queued for processing",
            "received_at": saved['received_at']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trade")
async def submit_trade(
    trade: ExternalTrade,
    api_info: APIKeyInfo = Depends(verify_api_key)
):
    """
    Reporta um trade executado pelo bot externo.
    
    Use para manter o dashboard sincronizado com trades
    executados externamente.
    """
    try:
        bot_data = ExternalBotData(api_info.bot_id)
        saved = bot_data.save_trade(trade, api_info)
        
        return {
            "success": True,
            "internal_id": saved['internal_id'],
            "external_id": trade.external_id,
            "status": trade.status,
            "message": "Trade recorded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status")
async def update_status(
    status: BotStatus,
    api_info: APIKeyInfo = Depends(verify_api_key)
):
    """
    Atualiza status do bot.
    
    Envie periodicamente (a cada 30-60 segundos) para
    manter o dashboard atualizado.
    """
    try:
        bot_data = ExternalBotData(api_info.bot_id)
        saved = bot_data.save_status(status, api_info)
        
        return {
            "success": True,
            "bot_id": api_info.bot_id,
            "updated_at": saved['updated_at']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics")
async def update_metrics(
    metrics: BotMetrics,
    api_info: APIKeyInfo = Depends(verify_api_key)
):
    """
    Envia métricas de performance do bot.
    
    Recomendado enviar ao final de cada dia de trading
    ou quando houver mudanças significativas.
    """
    try:
        bot_data = ExternalBotData(api_info.bot_id)
        saved = bot_data.save_metrics(metrics, api_info)
        
        return {
            "success": True,
            "bot_id": api_info.bot_id,
            "period": metrics.period,
            "updated_at": saved['updated_at']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_signals(
    limit: int = Query(100, ge=1, le=1000),
    api_info: APIKeyInfo = Depends(verify_api_key)
):
    """Retorna sinais enviados pelo bot."""
    bot_data = ExternalBotData(api_info.bot_id)
    signals = bot_data.get_signals(limit)
    
    return {
        "bot_id": api_info.bot_id,
        "count": len(signals),
        "signals": signals
    }


@router.get("/trades")
async def get_trades(
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    api_info: APIKeyInfo = Depends(verify_api_key)
):
    """Retorna trades do bot."""
    bot_data = ExternalBotData(api_info.bot_id)
    trades = bot_data.get_trades(limit, status)
    
    return {
        "bot_id": api_info.bot_id,
        "count": len(trades),
        "trades": trades
    }


@router.get("/bot-status")
async def get_bot_status(api_info: APIKeyInfo = Depends(verify_api_key)):
    """Retorna último status do bot."""
    bot_data = ExternalBotData(api_info.bot_id)
    status = bot_data.get_status()
    
    return {
        "bot_id": api_info.bot_id,
        "status": status
    }


@router.get("/bot-metrics")
async def get_bot_metrics(api_info: APIKeyInfo = Depends(verify_api_key)):
    """Retorna métricas do bot."""
    bot_data = ExternalBotData(api_info.bot_id)
    metrics = bot_data.get_metrics()
    
    return {
        "bot_id": api_info.bot_id,
        "metrics": metrics
    }


# ==================== ADMIN ENDPOINTS (Dashboard only) ====================

@router.get("/admin/bots")
async def admin_list_external_bots():
    """
    Lista todos os bots externos registrados.
    (Endpoint para o dashboard, não requer API key do bot)
    """
    keys = api_key_storage.get_all_keys()
    
    bots = []
    for key_info in keys:
        bot_data = ExternalBotData(key_info.bot_id)
        status = bot_data.get_status()
        metrics = bot_data.get_metrics()
        
        bots.append({
            "bot_id": key_info.bot_id,
            "bot_name": key_info.bot_name,
            "is_active": key_info.is_active,
            "created_at": key_info.created_at,
            "last_used": key_info.last_used,
            "status": status,
            "metrics": metrics
        })
    
    return {"bots": bots, "total": len(bots)}


@router.get("/admin/bot/{bot_id}")
async def admin_get_bot_details(bot_id: str):
    """Detalhes de um bot externo específico."""
    bot_data = ExternalBotData(bot_id)
    
    return {
        "bot_id": bot_id,
        "status": bot_data.get_status(),
        "metrics": bot_data.get_metrics(),
        "recent_signals": bot_data.get_signals(20),
        "recent_trades": bot_data.get_trades(20)
    }


# ==================== FULL UPDATE ENDPOINT ====================

# Cache para dados em tempo real (em memória)
_realtime_data: Dict[str, Dict[str, Any]] = {}


@router.post("/update")
async def full_update(
    update: FullUpdate,
    api_info: APIKeyInfo = Depends(verify_api_key)
):
    """
    Atualização completa do bot - ENDPOINT PRINCIPAL.
    
    Envie a cada 30-60 segundos com todos os dados do bot:
    - Status (running, connected)
    - Account (balance, equity, margin)
    - Positions (todas as posições abertas)
    - Métricas do dia
    - Métricas gerais
    
    Este endpoint:
    1. Salva os dados em disco (persistência)
    2. Atualiza cache em memória (tempo real)
    3. Notifica clientes WebSocket (se disponível)
    """
    try:
        bot_id = api_info.bot_id
        bot_data = ExternalBotData(bot_id)
        now = datetime.now()
        
        # Prepara dados completos
        full_data = {
            "bot_id": bot_id,
            "bot_name": api_info.bot_name,
            "updated_at": now.isoformat(),
            
            # Status
            "is_running": update.is_running,
            "is_connected": update.is_connected,
            "uptime_seconds": update.uptime_seconds,
            "bot_version": update.bot_version,
            "strategy_name": update.strategy_name,
            
            # Account
            "account": {
                "balance": update.account_balance,
                "equity": update.account_equity,
                "margin": update.account_margin,
                "free_margin": update.account_free_margin,
                "profit": update.account_profit
            },
            
            # Positions
            "positions": [p.dict() for p in update.positions],
            "positions_count": len(update.positions),
            
            # Daily
            "daily": {
                "profit": update.daily_profit,
                "profit_pips": update.daily_profit_pips,
                "trades": update.daily_trades,
                "wins": update.daily_wins,
                "losses": update.daily_losses,
                "win_rate": (update.daily_wins / update.daily_trades * 100) if update.daily_trades > 0 else 0
            },
            
            # Overall metrics
            "metrics": {
                "total_trades": update.total_trades,
                "total_profit": update.total_profit,
                "win_rate": update.win_rate,
                "max_drawdown": update.max_drawdown
            },
            
            # Misc
            "last_trade_time": update.last_trade_time,
            "errors": update.errors[-10:],  # Últimos 10 erros
            "metadata": update.metadata
        }
        
        # 1. Salva em disco
        full_update_file = bot_data.data_path / "full_update.json"
        bot_data.data_path.mkdir(parents=True, exist_ok=True)
        with open(full_update_file, 'w') as f:
            json.dump(full_data, f, indent=2, default=str)
        
        # 2. Atualiza cache em memória
        _realtime_data[bot_id] = full_data
        
        # 3. Também salva status e métricas nos arquivos padrão
        status = BotStatus(
            is_running=update.is_running,
            is_connected=update.is_connected,
            account_balance=update.account_balance,
            account_equity=update.account_equity,
            open_positions=len(update.positions),
            daily_profit=update.daily_profit,
            daily_trades=update.daily_trades,
            uptime_seconds=update.uptime_seconds,
            last_trade_time=update.last_trade_time,
            errors=update.errors
        )
        bot_data.save_status(status, api_info)
        
        metrics = BotMetrics(
            total_trades=update.total_trades,
            winning_trades=update.daily_wins,
            losing_trades=update.daily_losses,
            win_rate=update.win_rate,
            total_profit=update.total_profit,
            max_drawdown=update.max_drawdown,
            period="daily"
        )
        bot_data.save_metrics(metrics, api_info)
        
        # 4. Tenta notificar WebSocket (se disponível)
        try:
            from websocket import ws_manager
            import asyncio
            asyncio.create_task(ws_manager.broadcast("external_bots", {
                "type": "bot_update",
                "data": full_data
            }))
        except Exception:
            pass  # WebSocket não disponível
        
        return {
            "success": True,
            "bot_id": bot_id,
            "received_at": now.isoformat(),
            "positions_count": len(update.positions),
            "message": "Full update received successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/realtime/{bot_id}")
async def admin_get_realtime_data(bot_id: str):
    """
    Retorna dados em tempo real de um bot específico.
    Usa cache em memória para resposta rápida.
    """
    # Primeiro tenta memória
    if bot_id in _realtime_data:
        return _realtime_data[bot_id]
    
    # Se não tem em memória, tenta disco
    bot_data = ExternalBotData(bot_id)
    full_update_file = bot_data.data_path / "full_update.json"
    
    if full_update_file.exists():
        try:
            with open(full_update_file, 'r') as f:
                data = json.load(f)
                _realtime_data[bot_id] = data  # Cache
                return data
        except:
            pass
    
    raise HTTPException(status_code=404, detail=f"No data found for bot {bot_id}")


@router.get("/admin/realtime")
async def admin_get_all_realtime_data():
    """
    Retorna dados em tempo real de TODOS os bots externos.
    Ideal para o dashboard exibir resumo geral.
    """
    all_data = {}
    
    # Primeiro, dados em memória
    all_data.update(_realtime_data)
    
    # Depois, checa bots que não estão em memória
    keys = api_key_storage.get_all_keys()
    for key_info in keys:
        if key_info.bot_id not in all_data:
            bot_data = ExternalBotData(key_info.bot_id)
            full_update_file = bot_data.data_path / "full_update.json"
            
            if full_update_file.exists():
                try:
                    with open(full_update_file, 'r') as f:
                        data = json.load(f)
                        all_data[key_info.bot_id] = data
                except:
                    pass
    
    # Calcula totais
    total_balance = sum(d.get('account', {}).get('balance', 0) for d in all_data.values())
    total_equity = sum(d.get('account', {}).get('equity', 0) for d in all_data.values())
    total_positions = sum(d.get('positions_count', 0) for d in all_data.values())
    total_daily_profit = sum(d.get('daily', {}).get('profit', 0) for d in all_data.values())
    
    return {
        "bots": all_data,
        "summary": {
            "total_bots": len(all_data),
            "active_bots": sum(1 for d in all_data.values() if d.get('is_running')),
            "total_balance": total_balance,
            "total_equity": total_equity,
            "total_positions": total_positions,
            "total_daily_profit": total_daily_profit
        }
    }


@router.get("/admin/positions")
async def admin_get_all_positions():
    """
    Retorna todas as posições abertas de todos os bots externos.
    """
    all_positions = []
    
    keys = api_key_storage.get_all_keys()
    for key_info in keys:
        bot_id = key_info.bot_id
        
        # Tenta memória primeiro
        if bot_id in _realtime_data:
            data = _realtime_data[bot_id]
        else:
            # Tenta disco
            bot_data = ExternalBotData(bot_id)
            full_update_file = bot_data.data_path / "full_update.json"
            if full_update_file.exists():
                try:
                    with open(full_update_file, 'r') as f:
                        data = json.load(f)
                except:
                    continue
            else:
                continue
        
        # Adiciona posições com info do bot
        for pos in data.get('positions', []):
            pos_with_bot = {**pos}
            pos_with_bot['bot_id'] = bot_id
            pos_with_bot['bot_name'] = key_info.bot_name
            all_positions.append(pos_with_bot)
    
    return {
        "positions": all_positions,
        "total": len(all_positions)
    }
