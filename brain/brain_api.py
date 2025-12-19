"""
VIRTUS Brain API
=================

API REST que expõe os dados do sistema de trading.
Roda independente do Dashboard, na porta 8001.

Endpoints:
- /api/status - Status geral
- /api/account - Informações da conta MT5
- /api/positions - Posições abertas
- /api/bots - Status dos bots
- /api/analysis/{symbol} - Análise de mercado
- /api/signals - Sinais ativos
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Adiciona path do src
BRAIN_PATH = Path(__file__).parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

# Imports do VIRTUS
try:
    from src.core.config import Config
    from src.core.logger import VirtusLogger
    from src.mt5.mt5_connection import MT5Connection
    from src.brain.brain_service import BrainService
    VIRTUS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: VIRTUS modules not available: {e}")
    VIRTUS_AVAILABLE = False

# ==================== ESTADO GLOBAL ====================

class BrainState:
    """Estado compartilhado do Brain."""
    def __init__(self):
        self.mt5: Optional[MT5Connection] = None
        self.brain: Optional[BrainService] = None
        self.config: Optional[Config] = None
        self.bots: Dict[str, Any] = {}
        self.signals: List[Dict] = []
        self.started_at: datetime = datetime.now()
        self.is_trading: bool = False
        
state = BrainState()

# ==================== MODELOS ====================

class StatusResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    mt5_connected: bool
    trading_active: bool
    bots_running: int
    timestamp: str

class AccountResponse(BaseModel):
    login: int
    server: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: Optional[float]
    profit: float
    currency: str

class PositionResponse(BaseModel):
    ticket: int
    symbol: str
    type: str
    volume: float
    price_open: float
    price_current: float
    sl: float
    tp: float
    profit: float
    swap: float
    time: str
    comment: str

class BotStatusResponse(BaseModel):
    id: str
    symbol: str
    name: str
    enabled: bool
    running: bool
    trades_today: int
    profit_today: float
    last_signal: Optional[str]

class SignalResponse(BaseModel):
    id: str
    symbol: str
    direction: str
    entry: float
    sl: float
    tp: float
    confidence: float
    strategy: str
    timestamp: str

class TradeRequest(BaseModel):
    symbol: str
    direction: str  # "buy" or "sell"
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: str = "Manual trade"

class AnalysisResponse(BaseModel):
    symbol: str
    timestamp: str
    trend: str
    rsi: float
    score: float
    bias: str
    support: float
    resistance: float
    recommendation: str

# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa e finaliza recursos."""
    print("🚀 Brain API iniciando...")
    
    if VIRTUS_AVAILABLE:
        try:
            # Carrega config
            config_path = BRAIN_PATH / "config" / "config.yaml"
            state.config = Config.from_yaml(str(config_path))
            print("✅ Config carregado")
            
            # Conecta MT5
            state.mt5 = await MT5Connection.get_instance()
            if state.mt5:
                await state.mt5.connect()
                print("✅ MT5 conectado")
        except Exception as e:
            print(f"⚠️ Erro na inicialização: {e}")
    
    yield
    
    # Cleanup
    print("🛑 Brain API parando...")
    if state.mt5:
        await state.mt5.disconnect()

# ==================== APP ====================

app = FastAPI(
    title="VIRTUS Brain API",
    description="API do sistema de trading VIRTUS",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - permite conexões do Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ENDPOINTS ====================

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Retorna status geral do sistema."""
    uptime = (datetime.now() - state.started_at).total_seconds()
    mt5_connected = state.mt5.is_connected if state.mt5 else False
    
    return StatusResponse(
        status="online",
        version="3.0.0",
        uptime_seconds=uptime,
        mt5_connected=mt5_connected,
        trading_active=state.is_trading,
        bots_running=len([b for b in state.bots.values() if b.get('running')]),
        timestamp=datetime.now().isoformat(),
    )

@app.get("/api/health")
async def health_check():
    """Health check simples."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/account", response_model=AccountResponse)
async def get_account():
    """Retorna informações da conta MT5."""
    if not state.mt5 or not state.mt5.is_connected:
        raise HTTPException(status_code=503, detail="MT5 não conectado")
    
    try:
        import MetaTrader5 as mt5
        account = mt5.account_info()
        if not account:
            raise HTTPException(status_code=500, detail="Erro ao obter conta")
        
        return AccountResponse(
            login=account.login,
            server=account.server,
            balance=account.balance,
            equity=account.equity,
            margin=account.margin,
            free_margin=account.margin_free,
            margin_level=account.margin_level if account.margin_level else None,
            profit=account.profit,
            currency=account.currency,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/positions", response_model=List[PositionResponse])
async def get_positions():
    """Retorna posições abertas."""
    if not state.mt5 or not state.mt5.is_connected:
        raise HTTPException(status_code=503, detail="MT5 não conectado")
    
    try:
        import MetaTrader5 as mt5
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        result = []
        for pos in positions:
            result.append(PositionResponse(
                ticket=pos.ticket,
                symbol=pos.symbol,
                type="buy" if pos.type == 0 else "sell",
                volume=pos.volume,
                price_open=pos.price_open,
                price_current=pos.price_current,
                sl=pos.sl,
                tp=pos.tp,
                profit=pos.profit,
                swap=pos.swap,
                time=datetime.fromtimestamp(pos.time).isoformat(),
                comment=pos.comment or "",
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bots", response_model=List[BotStatusResponse])
async def get_bots():
    """Retorna status dos bots."""
    if not state.config:
        return []
    
    result = []
    for bot_config in state.config.bots:
        bot_state = state.bots.get(bot_config.id, {})
        result.append(BotStatusResponse(
            id=bot_config.id,
            symbol=bot_config.symbol,
            name=bot_config.name,
            enabled=bot_config.enabled,
            running=bot_state.get('running', False),
            trades_today=bot_state.get('trades_today', 0),
            profit_today=bot_state.get('profit_today', 0.0),
            last_signal=bot_state.get('last_signal'),
        ))
    return result

@app.post("/api/bots/{bot_id}/start")
async def start_bot(bot_id: str):
    """Inicia um bot específico."""
    if bot_id not in state.bots:
        state.bots[bot_id] = {'running': False}
    
    state.bots[bot_id]['running'] = True
    return {"status": "started", "bot_id": bot_id}

@app.post("/api/bots/{bot_id}/stop")
async def stop_bot(bot_id: str):
    """Para um bot específico."""
    if bot_id in state.bots:
        state.bots[bot_id]['running'] = False
    return {"status": "stopped", "bot_id": bot_id}

@app.get("/api/signals", response_model=List[SignalResponse])
async def get_signals():
    """Retorna sinais ativos."""
    return [SignalResponse(**s) for s in state.signals]

@app.get("/api/analysis/{symbol}", response_model=AnalysisResponse)
async def get_analysis(symbol: str):
    """Retorna análise de um símbolo."""
    if not state.mt5 or not state.mt5.is_connected:
        raise HTTPException(status_code=503, detail="MT5 não conectado")
    
    try:
        import MetaTrader5 as mt5
        import numpy as np
        
        # Obtém candles
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
        if rates is None or len(rates) < 50:
            raise HTTPException(status_code=404, detail=f"Dados não disponíveis para {symbol}")
        
        closes = np.array([r[4] for r in rates])
        highs = np.array([r[2] for r in rates])
        lows = np.array([r[3] for r in rates])
        
        # RSI
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-14:])
        avg_loss = np.mean(losses[-14:])
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 100
        
        # Trend
        ema9 = np.mean(closes[-9:])
        ema21 = np.mean(closes[-21:])
        trend = "bullish" if ema9 > ema21 else "bearish"
        
        # Support/Resistance
        support = min(lows[-20:])
        resistance = max(highs[-20:])
        
        # Score e recomendação
        score = 0.5
        if rsi < 30:
            score += 0.3
            recommendation = "BUY - RSI Oversold"
        elif rsi > 70:
            score -= 0.3
            recommendation = "SELL - RSI Overbought"
        else:
            recommendation = f"HOLD - {trend.upper()}"
        
        if trend == "bullish":
            score += 0.2
        else:
            score -= 0.2
        
        return AnalysisResponse(
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
            trend=trend,
            rsi=round(rsi, 1),
            score=round(score, 2),
            bias=trend,
            support=round(support, 5),
            resistance=round(resistance, 5),
            recommendation=recommendation,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trade")
async def execute_trade(trade: TradeRequest):
    """Executa um trade manual."""
    if not state.mt5 or not state.mt5.is_connected:
        raise HTTPException(status_code=503, detail="MT5 não conectado")
    
    try:
        import MetaTrader5 as mt5
        
        # Obtém preço atual
        tick = mt5.symbol_info_tick(trade.symbol)
        if not tick:
            raise HTTPException(status_code=400, detail=f"Símbolo {trade.symbol} não encontrado")
        
        price = tick.ask if trade.direction == "buy" else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if trade.direction == "buy" else mt5.ORDER_TYPE_SELL
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": trade.symbol,
            "volume": trade.volume,
            "type": order_type,
            "price": price,
            "sl": trade.sl or 0.0,
            "tp": trade.tp or 0.0,
            "deviation": 20,
            "magic": 123456,
            "comment": trade.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise HTTPException(status_code=400, detail=f"Erro: {result.comment}")
        
        return {
            "status": "success",
            "ticket": result.order,
            "symbol": trade.symbol,
            "direction": trade.direction,
            "volume": trade.volume,
            "price": result.price,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/position/{ticket}")
async def close_position(ticket: int):
    """Fecha uma posição pelo ticket."""
    if not state.mt5 or not state.mt5.is_connected:
        raise HTTPException(status_code=503, detail="MT5 não conectado")
    
    try:
        import MetaTrader5 as mt5
        
        # Encontra a posição
        position = mt5.positions_get(ticket=ticket)
        if not position:
            raise HTTPException(status_code=404, detail=f"Posição {ticket} não encontrada")
        
        pos = position[0]
        
        # Prepara ordem de fechamento
        tick = mt5.symbol_info_tick(pos.symbol)
        close_price = tick.bid if pos.type == 0 else tick.ask
        close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": close_price,
            "deviation": 20,
            "magic": 123456,
            "comment": "Close via API",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise HTTPException(status_code=400, detail=f"Erro: {result.comment}")
        
        return {
            "status": "closed",
            "ticket": ticket,
            "close_price": result.price,
            "profit": pos.profit,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history(days: int = 7):
    """Retorna histórico de trades."""
    if not state.mt5 or not state.mt5.is_connected:
        raise HTTPException(status_code=503, detail="MT5 não conectado")
    
    try:
        import MetaTrader5 as mt5
        from datetime import timedelta
        
        # Define período
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        # Obtém histórico
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            return []
        
        result = []
        for deal in deals:
            if deal.entry == 1:  # Apenas fechamentos
                result.append({
                    "ticket": deal.ticket,
                    "order": deal.order,
                    "symbol": deal.symbol,
                    "type": "buy" if deal.type == 0 else "sell",
                    "volume": deal.volume,
                    "price": deal.price,
                    "profit": deal.profit,
                    "commission": deal.commission,
                    "swap": deal.swap,
                    "time": datetime.fromtimestamp(deal.time).isoformat(),
                    "comment": deal.comment,
                })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CALLBACKS PARA ATUALIZAR ESTADO ====================

def update_bot_state(bot_id: str, **kwargs):
    """Atualiza estado de um bot (chamado pelo main.py)."""
    if bot_id not in state.bots:
        state.bots[bot_id] = {}
    state.bots[bot_id].update(kwargs)

def add_signal(signal: Dict):
    """Adiciona um sinal (chamado pelo trading engine)."""
    state.signals.append(signal)
    # Mantém apenas últimos 50 sinais
    if len(state.signals) > 50:
        state.signals = state.signals[-50:]

def set_trading_active(active: bool):
    """Define se trading está ativo."""
    state.is_trading = active

# ==================== MAIN ====================

def run_brain_api(host: str = "0.0.0.0", port: int = 8001):
    """Inicia a Brain API."""
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    print("=" * 60)
    print("🧠 VIRTUS Brain API")
    print("=" * 60)
    print(f"📡 Iniciando servidor em http://localhost:8001")
    print("=" * 60)
    run_brain_api()
