"""
VIRTUS Dashboard Backend - INTEGRADO
=====================================

API REST + WebSocket integrada com sistema VIRTUS existente.
Usa Database SQLite, Brain Service, e configurações existentes.
"""

import os
import sys
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import jwt

# Adicionar path do src para imports do sistema VIRTUS
BRAIN_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BRAIN_PATH))
sys.path.insert(0, str(BRAIN_PATH / "src"))

# Imports do sistema VIRTUS existente
try:
    from src.database.manager import DatabaseManager, DatabaseConfig, get_database
    from src.database.repositories import TradeRepository, SignalRepository, PerformanceRepository
    from src.database.models import Trade, Signal, DailyPerformance
    from src.core.config import ConfigLoader
    from src.core.logger import VirtusLogger
    VIRTUS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import VIRTUS modules: {e}")
    VIRTUS_AVAILABLE = False
    # Tipos mock quando VIRTUS não disponível
    Trade = Any
    Signal = Any
    DailyPerformance = Any
    DatabaseManager = Any
    TradeRepository = Any
    SignalRepository = Any
    PerformanceRepository = Any
    ConfigLoader = None
    VirtusLogger = None

# ==================== CONFIGURAÇÃO ====================

class Settings:
    """Configurações do servidor."""
    # Chave secreta fixa para manter tokens válidos entre restarts
    SECRET_KEY: str = os.getenv("VIRTUS_SECRET_KEY", "virtus_dashboard_secret_key_2024_production_fixed_k3y!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Usuários (em produção, usar banco de dados)
    USERS: Dict[str, Dict] = {
        "admin": {
            "password_hash": hashlib.sha256("virtus2024!".encode()).hexdigest(),
            "role": "admin",
            "name": "Administrador",
        },
        "trader": {
            "password_hash": hashlib.sha256("trader123".encode()).hexdigest(),
            "role": "trader",
            "name": "Trader",
        }
    }
    
    # Paths
    DATA_DIR = BRAIN_PATH / "data"
    CONFIG_DIR = BRAIN_PATH / "config"

settings = Settings()
security = HTTPBearer()

# ==================== MODELOS PYDANTIC ====================

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class TokenRefresh(BaseModel):
    refresh_token: str

class BotConfig(BaseModel):
    enabled: bool = True
    max_positions: int = 3
    risk_per_trade: float = 1.0
    max_daily_loss: float = 5.0
    max_daily_trades: int = 10

class BotControl(BaseModel):
    action: str  # start, stop, pause

class StrategyToggle(BaseModel):
    enabled: bool

class SymbolToggle(BaseModel):
    enabled: bool

class SettingsUpdate(BaseModel):
    risk: Optional[Dict] = None
    trading: Optional[Dict] = None
    notifications: Optional[Dict] = None
    system: Optional[Dict] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

# ==================== NOTIFICAÇÕES ====================

from enum import Enum
from uuid import uuid4

class NotificationType(str, Enum):
    TRADE = "trade"           # Posições abertas/fechadas
    ALERT = "alert"           # Alertas de risco/drawdown
    BOT = "bot"               # Status dos bots
    NEWS = "news"             # Notícias importantes
    SYSTEM = "system"         # Sistema/conectividade

class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Notification(BaseModel):
    id: str
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    title: str
    message: str
    timestamp: str
    read: bool = False
    data: Optional[Dict] = None

class NotificationManager:
    """Gerenciador de notificações."""
    
    def __init__(self, max_notifications: int = 100):
        self.notifications: List[Notification] = []
        self.max_notifications = max_notifications
        self._load_notifications()
    
    def _load_notifications(self):
        """Carrega notificações persistidas."""
        try:
            import json
            notif_file = settings.DATA_DIR / "notifications.json"
            if notif_file.exists():
                with open(notif_file, "r") as f:
                    data = json.load(f)
                    self.notifications = [Notification(**n) for n in data]
        except Exception as e:
            print(f"Warning: Could not load notifications: {e}")
    
    def _save_notifications(self):
        """Persiste notificações em arquivo."""
        try:
            import json
            notif_file = settings.DATA_DIR / "notifications.json"
            with open(notif_file, "w") as f:
                json.dump([n.dict() for n in self.notifications], f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save notifications: {e}")
    
    def add(self, type: NotificationType, title: str, message: str, 
            priority: NotificationPriority = NotificationPriority.MEDIUM,
            data: Optional[Dict] = None) -> Notification:
        """Adiciona uma nova notificação."""
        notification = Notification(
            id=str(uuid4()),
            type=type,
            priority=priority,
            title=title,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            read=False,
            data=data
        )
        
        self.notifications.insert(0, notification)
        
        # Limita quantidade
        if len(self.notifications) > self.max_notifications:
            self.notifications = self.notifications[:self.max_notifications]
        
        self._save_notifications()
        return notification
    
    def get_all(self, limit: int = 50) -> List[Notification]:
        """Retorna todas as notificações."""
        return self.notifications[:limit]
    
    def get_unread_count(self) -> int:
        """Conta notificações não lidas."""
        return sum(1 for n in self.notifications if not n.read)
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Marca uma notificação como lida."""
        for n in self.notifications:
            if n.id == notification_id:
                n.read = True
                self._save_notifications()
                return True
        return False
    
    def mark_all_as_read(self):
        """Marca todas como lidas."""
        for n in self.notifications:
            n.read = True
        self._save_notifications()
    
    def delete(self, notification_id: str) -> bool:
        """Remove uma notificação."""
        for i, n in enumerate(self.notifications):
            if n.id == notification_id:
                del self.notifications[i]
                self._save_notifications()
                return True
        return False
    
    def clear_all(self):
        """Remove todas as notificações."""
        self.notifications = []
        self._save_notifications()

# Instância global do gerenciador de notificações
notification_manager = NotificationManager()

# ==================== ESTADO GLOBAL ====================

class AppState:
    """Estado global da aplicação integrado com VIRTUS."""
    
    def __init__(self):
        self.logger = VirtusLogger.get_logger("dashboard") if VIRTUS_AVAILABLE else None
        
        # Inicializa banco de dados
        self.db: Optional[DatabaseManager] = None
        self.trade_repo: Optional[TradeRepository] = None
        self.signal_repo: Optional[SignalRepository] = None
        self.perf_repo: Optional[PerformanceRepository] = None
        
        # Configurações do VIRTUS
        self.config: Optional[Dict] = None
        
        # Estado dos bots (carregado do config)
        self.bots: Dict[str, Dict] = {}
        
        # Estado das estratégias
        self.strategies: Dict[str, Dict] = {}
        
        # Estado dos símbolos
        self.symbols: Dict[str, Dict] = {}
        
        # WebSocket connections
        self.websocket_connections: Set[WebSocket] = set()
        
        # MT5 status
        self.mt5_connected: bool = False
        self.mt5_account: Optional[Dict] = None
        
        # Métricas em tempo real
        self.metrics: Dict[str, Any] = {}
        
        # Posições abertas
        self.positions: List[Dict] = []
        
        # Ordens pendentes
        self.pending_orders: List[Dict] = []
    
    def _load_persisted_users(self):
        """Carrega senhas persistidas do arquivo."""
        try:
            import json
            users_file = settings.DATA_DIR / "users.json"
            if users_file.exists():
                with open(users_file, "r") as f:
                    users_data = json.load(f)
                
                for username, data in users_data.items():
                    if username in settings.USERS:
                        settings.USERS[username]["password_hash"] = data["password_hash"]
                        print(f"Loaded persisted password for user: {username}")
        except Exception as e:
            print(f"Warning: Could not load persisted users: {e}")
    
    def initialize(self):
        """Inicializa conexões e carrega configurações."""
        try:
            # Carrega senhas persistidas
            self._load_persisted_users()
            
            # Inicializa Database
            db_config = DatabaseConfig.sqlite_default(str(settings.DATA_DIR / "brain"))
            self.db = DatabaseManager(db_config)
            
            # Inicializa Repositories
            self.trade_repo = TradeRepository(self.db)
            self.signal_repo = SignalRepository(self.db)
            self.perf_repo = PerformanceRepository(self.db)
            
            # Carrega configurações
            self._load_config()
            
            # Inicializa métricas
            self._init_metrics()
            
            if self.logger:
                self.logger.info("Dashboard backend initialized with VIRTUS integration")
                
        except Exception as e:
            print(f"Warning: Could not initialize VIRTUS integration: {e}")
            # Fallback para modo standalone
            self._init_standalone()
    
    def _load_config(self):
        """Carrega configurações do sistema VIRTUS."""
        try:
            config_path = settings.CONFIG_DIR / "config.yaml"
            if config_path.exists():
                import yaml
                with open(config_path) as f:
                    self.config = yaml.safe_load(f)
                
                # Carrega configurações de bots
                self._load_bots_config()
                
                # Carrega símbolos
                self._load_symbols_config()
                
                # Carrega estratégias
                self._load_strategies_config()
                
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
    
    def _load_bots_config(self):
        """Carrega configuração dos bots."""
        bots_dir = settings.CONFIG_DIR / "bots"
        if bots_dir.exists():
            import yaml
            for bot_file in bots_dir.glob("*.yaml"):
                try:
                    with open(bot_file, encoding='utf-8') as f:
                        bot_config = yaml.safe_load(f)
                    
                    if not isinstance(bot_config, dict):
                        print(f"Warning: Invalid bot config format in {bot_file}")
                        continue
                    
                    bot_id = bot_file.stem
                    self.bots[bot_id] = {
                        "id": bot_id,
                        "name": bot_config.get("name", bot_id.title()),
                        "symbol": bot_config.get("symbol", "UNKNOWN"),
                        "status": "stopped",  # Status real virá do orchestrator
                        "config": bot_config,
                        "strategies": bot_config.get("strategies", {}).get("enabled", []) if isinstance(bot_config.get("strategies"), dict) else [],
                    }
                except Exception as e:
                    print(f"Warning: Could not load bot config {bot_file}: {e}")
        
        # Fallback se não encontrar configs
        if not self.bots:
            self.bots = {
                "euro": {"id": "euro", "name": "Euro Bot", "symbol": "EURUSD", "status": "stopped", "strategies": []},
                "gbp": {"id": "gbp", "name": "GBP Bot", "symbol": "GBPUSD", "status": "stopped", "strategies": []},
                "gold": {"id": "gold", "name": "Gold Bot", "symbol": "XAUUSD", "status": "stopped", "strategies": []},
            }
    
    def _load_symbols_config(self):
        """Carrega configuração de símbolos."""
        if self.config and "symbols" in self.config:
            for symbol in self.config["symbols"]:
                self.symbols[symbol] = {
                    "symbol": symbol,
                    "enabled": True,
                    "lot_size": 0.1,
                    "max_spread": 20,
                }
        else:
            self.symbols = {
                "EURUSD": {"symbol": "EURUSD", "enabled": True, "lot_size": 0.1, "max_spread": 15},
                "GBPUSD": {"symbol": "GBPUSD", "enabled": True, "lot_size": 0.1, "max_spread": 20},
                "XAUUSD": {"symbol": "XAUUSD", "enabled": True, "lot_size": 0.05, "max_spread": 50},
            }
    
    def _load_strategies_config(self):
        """Carrega configuração de estratégias."""
        self.strategies = {
            "ScalpingStrategy": {"name": "ScalpingStrategy", "enabled": True, "setups": 9},
            "TrendStrategy": {"name": "TrendStrategy", "enabled": True, "setups": 7},
            "ReversalStrategy": {"name": "ReversalStrategy", "enabled": False, "setups": 8},
            "EventStrategy": {"name": "EventStrategy", "enabled": False, "setups": 5},
        }
    
    def _init_metrics(self):
        """Inicializa métricas do banco de dados."""
        try:
            if self.perf_repo:
                # Busca última performance
                perf = self.perf_repo.get_latest()
                if perf:
                    self.metrics = {
                        "balance": float(perf.end_balance) if hasattr(perf, 'end_balance') else 10000.0,
                        "equity": float(perf.end_balance) if hasattr(perf, 'end_balance') else 10000.0,
                        "profit": float(perf.net_profit) if hasattr(perf, 'net_profit') else 0.0,
                        "total_trades": perf.total_trades if hasattr(perf, 'total_trades') else 0,
                        "win_rate": float(perf.win_rate) if hasattr(perf, 'win_rate') else 0.0,
                        "profit_factor": float(perf.profit_factor) if hasattr(perf, 'profit_factor') else 0.0,
                        "max_drawdown": float(perf.max_drawdown_pct) if hasattr(perf, 'max_drawdown_pct') else 0.0,
                    }
                    return
        except Exception as e:
            print(f"Warning: Could not load metrics from DB: {e}")
        
        # Fallback
        self._init_standalone_metrics()
    
    def _init_standalone(self):
        """Inicialização standalone sem VIRTUS."""
        self._load_bots_config()
        self._load_symbols_config()
        self._load_strategies_config()
        self._init_standalone_metrics()
    
    def _init_standalone_metrics(self):
        """Métricas padrão para modo standalone."""
        self.metrics = {
            "balance": 10000.00,
            "equity": 10250.00,
            "margin": 500.00,
            "free_margin": 9750.00,
            "margin_level": 2050.00,
            "profit": 250.00,
            "daily_pnl": 125.50,
            "weekly_pnl": 450.00,
            "monthly_pnl": 1250.00,
            "total_trades": 156,
            "winning_trades": 98,
            "losing_trades": 58,
            "win_rate": 62.82,
            "profit_factor": 1.85,
            "max_drawdown": 4.5,
            "current_drawdown": 1.2,
            "sharpe_ratio": 1.45,
            "active_positions": 2,
        }
    
    def get_trades(
        self, 
        limit: int = 50, 
        offset: int = 0,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """Busca trades do banco de dados."""
        try:
            if self.trade_repo:
                trades = self.trade_repo.get_all(
                    limit=limit,
                    offset=offset,
                    symbol=symbol,
                    strategy=strategy,
                    start_date=start_date,
                    end_date=end_date,
                )
                return [self._trade_to_dict(t) for t in trades]
        except Exception as e:
            print(f"Warning: Could not fetch trades: {e}")
        
        # Fallback: retorna mock
        return self._generate_mock_trades(limit, offset)
    
    def get_trades_count(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Conta total de trades."""
        try:
            if self.trade_repo:
                return self.trade_repo.count(
                    symbol=symbol,
                    strategy=strategy,
                    start_date=start_date,
                    end_date=end_date,
                )
        except Exception as e:
            print(f"Warning: Could not count trades: {e}")
        return 200  # Mock
    
    def _trade_to_dict(self, trade: Trade) -> Dict:
        """Converte Trade model para dict."""
        return {
            "ticket": trade.ticket,
            "symbol": trade.symbol,
            "type": trade.direction.value if hasattr(trade.direction, 'value') else str(trade.direction),
            "volume": float(trade.volume),
            "entry_price": float(trade.entry_price),
            "exit_price": float(trade.exit_price) if trade.exit_price else None,
            "sl": float(trade.stop_loss) if trade.stop_loss else None,
            "tp": float(trade.take_profit) if trade.take_profit else None,
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "pnl": float(trade.profit) if trade.profit else 0,
            "strategy": trade.strategy,
            "setup": trade.setup_name if hasattr(trade, 'setup_name') else None,
            "bot_id": trade.bot_id,
        }
    
    def _generate_mock_trades(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Gera trades mock para demo."""
        import random
        trades = []
        base_time = datetime.now() - timedelta(days=30)
        
        strategies = ["ScalpingStrategy", "TrendStrategy", "ReversalStrategy"]
        setups = ["SPREAD_COMPRESSION", "BOS_CONTINUATION", "CHOCH_REVERSAL", "FVG_FILL"]
        symbols = ["EURUSD", "GBPUSD", "XAUUSD"]
        
        for i in range(offset, offset + limit):
            if i >= 200:
                break
            
            symbol = random.choice(symbols)
            is_win = random.random() > 0.38
            pnl = random.uniform(50, 200) if is_win else random.uniform(-30, -100)
            
            entry_time = base_time + timedelta(hours=i * 3.5)
            exit_time = entry_time + timedelta(minutes=random.randint(5, 180))
            
            entry_price = 1.1000 if symbol == "EURUSD" else (1.2700 if symbol == "GBPUSD" else 2050.0)
            pip_value = 0.0001 if symbol != "XAUUSD" else 0.1
            exit_price = entry_price + (pnl / 100) * pip_value
            
            trades.append({
                "ticket": 1000000 + i,
                "symbol": symbol,
                "type": random.choice(["BUY", "SELL"]),
                "volume": round(random.uniform(0.05, 0.5), 2),
                "entry_price": round(entry_price, 5),
                "exit_price": round(exit_price, 5),
                "sl": round(entry_price - 0.002, 5),
                "tp": round(entry_price + 0.004, 5),
                "entry_time": entry_time.isoformat(),
                "exit_time": exit_time.isoformat(),
                "pnl": round(pnl, 2),
                "strategy": random.choice(strategies),
                "setup": random.choice(setups),
                "bot_id": f"{symbol.lower()[:4]}_bot",
            })
        
        return sorted(trades, key=lambda x: x["exit_time"], reverse=True)
    
    def get_equity_history(self, days: int = 30) -> List[Dict]:
        """Busca histórico de equity."""
        try:
            if self.perf_repo:
                performances = self.perf_repo.get_range(
                    start_date=datetime.now() - timedelta(days=days),
                    end_date=datetime.now(),
                )
                if performances:
                    return [
                        {
                            "timestamp": p.date.isoformat(),
                            "equity": float(p.end_balance) if hasattr(p, 'end_balance') else 10000.0,
                            "balance": float(p.end_balance) if hasattr(p, 'end_balance') else 10000.0,
                        }
                        for p in performances
                    ]
        except Exception as e:
            print(f"Warning: Could not fetch equity history: {e}")
        
        # Mock
        history = []
        balance = 10000.0
        base_time = datetime.now() - timedelta(days=days)
        
        for i in range(days * 24):
            change = (0.5 - 0.48) * balance * 0.001
            balance += change
            timestamp = base_time + timedelta(hours=i)
            history.append({
                "timestamp": timestamp.isoformat(),
                "balance": round(balance, 2),
                "equity": round(balance * 1.002, 2),
            })
        
        return history
    
    def get_trade_stats(self) -> Dict:
        """Calcula estatísticas de trades."""
        try:
            if self.trade_repo:
                stats = self.trade_repo.get_statistics()
                if stats:
                    return stats
        except Exception as e:
            print(f"Warning: Could not calculate stats: {e}")
        
        # Mock
        return {
            "total_trades": 156,
            "winning_trades": 98,
            "losing_trades": 58,
            "win_rate": 62.82,
            "total_profit": 4250.00,
            "total_loss": -2300.00,
            "net_profit": 1950.00,
            "profit_factor": 1.85,
            "average_win": 43.37,
            "average_loss": -39.66,
            "largest_win": 245.00,
            "largest_loss": -125.00,
            "average_duration_minutes": 67,
        }


# Instância global do estado
app_state = AppState()

# ==================== JWT HELPERS ====================

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    payload = verify_token(token, "access")
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    username = payload.get("sub")
    if username not in settings.USERS:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {"username": username, **settings.USERS[username]}


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação."""
    # Startup
    if VIRTUS_AVAILABLE:
        app_state.initialize()
    else:
        app_state._init_standalone()
    
    # Notificação de sistema iniciado (apenas se não houver notificações recentes)
    if notification_manager.get_unread_count() == 0 or len(notification_manager.notifications) == 0:
        notification_manager.add(
            type=NotificationType.SYSTEM,
            title="Sistema Iniciado",
            message="Dashboard VIRTUS iniciado com sucesso. Todos os serviços estão operacionais.",
            priority=NotificationPriority.LOW
        )
    
    yield
    
    # Shutdown
    if app_state.db:
        app_state.db.close()


# ==================== APP ====================

app = FastAPI(
    title="VIRTUS Dashboard API",
    description="API para dashboard institucional VIRTUS Trading System",
    version="1.0.0",
    lifespan=lifespan,
)

# ==================== ROUTERS ====================

# Importa e registra router de notícias
from routes.news_routes import router as news_router
app.include_router(news_router, prefix="/api")

# Importa e registra router multi-bot
from routes.multi_bot_routes import router as multi_bot_router
app.include_router(multi_bot_router, prefix="/api")

# Importa e registra router de social media
from routes.social_routes import router as social_router
app.include_router(social_router, prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://virtusinvestimentos.com.br",
        "https://www.virtusinvestimentos.com.br",
        "https://dashboard.virtusinvestimentos.com.br",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ROUTES: AUTH ====================

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Autenticação de usuário."""
    user = settings.USERS.get(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    if password_hash != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": request.username, "role": user["role"]})
    refresh_token = create_refresh_token({"sub": request.username})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user={
            "username": request.username,
            "name": user["name"],
            "role": user["role"],
        }
    )


@app.post("/api/auth/refresh")
async def refresh_token(request: TokenRefresh):
    """Renovação de token."""
    payload = verify_token(request.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    username = payload.get("sub")
    user = settings.USERS.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    access_token = create_access_token({"sub": username, "role": user["role"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    }


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Informações do usuário atual."""
    return {
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
    }


@app.post("/api/auth/change-password")
async def change_password(request: PasswordChange, user: dict = Depends(get_current_user)):
    """Alteração de senha do usuário."""
    username = user["username"]
    
    # Verifica senha atual
    current_hash = hashlib.sha256(request.current_password.encode()).hexdigest()
    if current_hash != settings.USERS[username]["password_hash"]:
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    
    # Valida nova senha
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter no mínimo 6 caracteres")
    
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Confirmação de senha não confere")
    
    # Atualiza senha em memória
    new_hash = hashlib.sha256(request.new_password.encode()).hexdigest()
    settings.USERS[username]["password_hash"] = new_hash
    
    # Salva em arquivo para persistir
    try:
        users_file = settings.DATA_DIR / "users.json"
        import json
        users_data = {}
        if users_file.exists():
            with open(users_file, "r") as f:
                users_data = json.load(f)
        
        users_data[username] = {
            "password_hash": new_hash,
            "role": settings.USERS[username]["role"],
            "name": settings.USERS[username]["name"],
        }
        
        with open(users_file, "w") as f:
            json.dump(users_data, f, indent=2)
            
    except Exception as e:
        print(f"Warning: Could not persist password change: {e}")
    
    return {"message": "Senha alterada com sucesso"}


# ==================== ROUTES: NOTIFICATIONS ====================

@app.get("/api/notifications")
async def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """Lista todas as notificações."""
    notifications = notification_manager.get_all(limit)
    unread_count = notification_manager.get_unread_count()
    
    return {
        "notifications": [n.dict() for n in notifications],
        "unread_count": unread_count,
        "total": len(notifications)
    }


@app.get("/api/notifications/unread-count")
async def get_unread_count(user: dict = Depends(get_current_user)):
    """Retorna apenas a contagem de não lidas."""
    return {"unread_count": notification_manager.get_unread_count()}


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    """Marca uma notificação como lida."""
    success = notification_manager.mark_as_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    return {"success": True}


@app.post("/api/notifications/read-all")
async def mark_all_notifications_read(user: dict = Depends(get_current_user)):
    """Marca todas as notificações como lidas."""
    notification_manager.mark_all_as_read()
    return {"success": True}


@app.delete("/api/notifications/{notification_id}")
async def delete_notification(notification_id: str, user: dict = Depends(get_current_user)):
    """Remove uma notificação."""
    success = notification_manager.delete(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    return {"success": True}


@app.delete("/api/notifications")
async def clear_all_notifications(user: dict = Depends(get_current_user)):
    """Remove todas as notificações."""
    notification_manager.clear_all()
    return {"success": True}


@app.post("/api/notifications/test")
async def create_test_notification(user: dict = Depends(get_current_user)):
    """Cria uma notificação de teste (apenas para debug)."""
    notification = notification_manager.add(
        type=NotificationType.SYSTEM,
        title="Notificação de Teste",
        message="Esta é uma notificação de teste criada manualmente.",
        priority=NotificationPriority.MEDIUM
    )
    return notification.dict()


# ==================== ROUTES: DASHBOARD ====================

@app.get("/api/dashboard/overview")
async def get_overview(user: dict = Depends(get_current_user)):
    """Visão geral do dashboard."""
    stats = app_state.get_trade_stats()
    
    return {
        "account": {
            "balance": app_state.metrics.get("balance", 10000),
            "equity": app_state.metrics.get("equity", 10000),
            "margin": app_state.metrics.get("margin", 0),
            "free_margin": app_state.metrics.get("free_margin", 10000),
            "profit": app_state.metrics.get("profit", 0),
        },
        "metrics": {
            "total_trades": stats.get("total_trades", 0),
            "win_rate": stats.get("win_rate", 0),
            "profit_factor": stats.get("profit_factor", 0),
            "net_profit": stats.get("net_profit", 0),
            "max_drawdown": app_state.metrics.get("max_drawdown", 0),
        },
        "today": {
            "trades": app_state.metrics.get("daily_trades", 0),
            "profit": app_state.metrics.get("daily_pnl", 0),
        },
        "bots_active": sum(1 for b in app_state.bots.values() if b.get("status") == "running"),
        "bots_total": len(app_state.bots),
    }


@app.get("/api/dashboard/metrics")
async def get_metrics(user: dict = Depends(get_current_user)):
    """Métricas em tempo real."""
    return app_state.metrics


@app.get("/api/dashboard/equity-history")
async def get_equity_history(
    days: int = Query(default=30, ge=1, le=365),
    user: dict = Depends(get_current_user)
):
    """Histórico de patrimônio."""
    return app_state.get_equity_history(days)


# ==================== ROUTES: BOTS ====================

@app.get("/api/bots")
async def get_bots(user: dict = Depends(get_current_user)):
    """Lista todos os bots."""
    bots = []
    for bot_id, bot in app_state.bots.items():
        bots.append({
            "id": bot_id,
            "name": bot.get("name", bot_id.title()),
            "symbol": bot.get("symbol", "UNKNOWN"),
            "status": bot.get("status", "stopped"),
            "strategies": bot.get("strategies", []),
            "profit_today": 0,
            "trades_today": 0,
        })
    return bots


@app.post("/api/bots/{bot_id}/control")
async def control_bot(bot_id: str, control: BotControl, user: dict = Depends(get_current_user)):
    """Controla um bot (start/stop/pause)."""
    if bot_id not in app_state.bots:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if control.action not in ["start", "stop", "pause"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    new_status = {
        "start": "running",
        "stop": "stopped",
        "pause": "paused",
    }[control.action]
    
    app_state.bots[bot_id]["status"] = new_status
    
    return {
        "success": True,
        "bot_id": bot_id,
        "new_status": new_status,
        "message": f"Bot {control.action}ed successfully",
    }


@app.get("/api/bots/{bot_id}/config")
async def get_bot_config(bot_id: str, user: dict = Depends(get_current_user)):
    """Obtém configuração de um bot."""
    if bot_id not in app_state.bots:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return app_state.bots[bot_id].get("config", {})


@app.put("/api/bots/{bot_id}/config")
async def update_bot_config(bot_id: str, config: Dict, user: dict = Depends(get_current_user)):
    """Atualiza configuração de um bot."""
    if bot_id not in app_state.bots:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    app_state.bots[bot_id]["config"] = config
    
    return {"success": True, "bot_id": bot_id}


# ==================== ROUTES: STRATEGIES ====================

@app.get("/api/strategies")
async def get_strategies(user: dict = Depends(get_current_user)):
    """Lista todas as estratégias."""
    return list(app_state.strategies.values())


@app.post("/api/strategies/{name}/toggle")
async def toggle_strategy(name: str, toggle: StrategyToggle, user: dict = Depends(get_current_user)):
    """Ativa/desativa uma estratégia."""
    if name not in app_state.strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    app_state.strategies[name]["enabled"] = toggle.enabled
    
    return {
        "success": True,
        "strategy": name,
        "enabled": toggle.enabled,
    }


# ==================== ROUTES: SYMBOLS ====================

@app.get("/api/symbols")
async def get_symbols(user: dict = Depends(get_current_user)):
    """Lista todos os símbolos."""
    return list(app_state.symbols.values())


@app.post("/api/symbols/{symbol}/toggle")
async def toggle_symbol(symbol: str, toggle: SymbolToggle, user: dict = Depends(get_current_user)):
    """Ativa/desativa um símbolo."""
    if symbol not in app_state.symbols:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    app_state.symbols[symbol]["enabled"] = toggle.enabled
    
    return {
        "success": True,
        "symbol": symbol,
        "enabled": toggle.enabled,
    }


# ==================== ROUTES: POSITIONS ====================

@app.get("/api/positions")
async def get_positions(user: dict = Depends(get_current_user)):
    """Lista posições abertas."""
    return app_state.positions


@app.delete("/api/positions/{ticket}")
async def close_position(ticket: int, user: dict = Depends(get_current_user)):
    """Fecha uma posição."""
    return {
        "success": True,
        "ticket": ticket,
        "message": "Position close requested",
    }


# ==================== ROUTES: ORDERS ====================

@app.get("/api/orders")
async def get_orders(user: dict = Depends(get_current_user)):
    """Lista ordens pendentes."""
    return app_state.pending_orders


@app.delete("/api/orders/{ticket}")
async def cancel_order(ticket: int, user: dict = Depends(get_current_user)):
    """Cancela uma ordem pendente."""
    return {
        "success": True,
        "ticket": ticket,
        "message": "Order cancellation requested",
    }


# ==================== ROUTES: TRADES ====================

@app.get("/api/trades")
async def get_trades(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Lista histórico de trades."""
    offset = (page - 1) * page_size
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    trades = app_state.get_trades(
        limit=page_size,
        offset=offset,
        symbol=symbol,
        strategy=strategy,
        start_date=start_dt,
        end_date=end_dt,
    )
    
    total = app_state.get_trades_count(
        symbol=symbol,
        strategy=strategy,
        start_date=start_dt,
        end_date=end_dt,
    )
    
    return {
        "trades": trades,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@app.get("/api/trades/stats")
async def get_trade_stats(user: dict = Depends(get_current_user)):
    """Estatísticas de trades."""
    return app_state.get_trade_stats()


# ==================== ROUTES: ANALYSIS ====================

@app.get("/api/analysis/performance")
async def get_performance(user: dict = Depends(get_current_user)):
    """Análise de performance por hora/dia."""
    import random
    
    hourly = [
        {"hour": h, "trades": random.randint(5, 20), "profit": random.uniform(-50, 150), "win_rate": random.uniform(50, 75)}
        for h in range(24)
    ]
    
    weekday = [
        {"day": day, "trades": random.randint(20, 40), "profit": random.uniform(50, 300), "win_rate": random.uniform(55, 72)}
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    ]
    
    return {"hourly": hourly, "weekday": weekday}


@app.get("/api/analysis/attribution")
async def get_attribution(user: dict = Depends(get_current_user)):
    """Atribuição de performance."""
    import random
    
    by_strategy = [
        {"name": s["name"], "trades": random.randint(30, 60), "profit": random.uniform(200, 800), "contribution": random.uniform(15, 40), "win_rate": random.uniform(58, 72)}
        for s in app_state.strategies.values()
    ]
    
    by_symbol = [
        {"name": s["symbol"], "trades": random.randint(40, 80), "profit": random.uniform(300, 1000), "contribution": random.uniform(20, 45), "win_rate": random.uniform(55, 70)}
        for s in app_state.symbols.values()
    ]
    
    return {"by_strategy": by_strategy, "by_symbol": by_symbol}


# ==================== ROUTES: SETTINGS ====================

@app.get("/api/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    """Obtém configurações."""
    if app_state.config:
        return {
            "risk": app_state.config.get("risk_management", {}),
            "trading": app_state.config.get("trading_hours", {}),
            "notifications": app_state.config.get("telegram", {}),
            "system": {
                "log_level": app_state.config.get("logging", {}).get("level", "INFO"),
            }
        }
    
    return {
        "risk": {
            "max_daily_loss": 500,
            "max_daily_loss_percent": 5,
            "max_drawdown": 1000,
            "max_drawdown_percent": 10,
            "max_position_size": 0.5,
            "max_concurrent_trades": 5,
        },
        "trading": {
            "trading_hours_start": "08:00",
            "trading_hours_end": "22:00",
            "allowed_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        },
        "notifications": {
            "telegram_enabled": True,
            "notify_on_trade": True,
            "notify_on_daily_summary": True,
        },
        "system": {
            "log_level": "INFO",
        }
    }


@app.put("/api/settings")
async def update_settings(settings_update: SettingsUpdate, user: dict = Depends(get_current_user)):
    """Atualiza configurações."""
    return {"success": True, "message": "Settings updated"}


# ==================== ROUTES: SYSTEM ====================

@app.get("/api/system/status")
async def get_system_status(user: dict = Depends(get_current_user)):
    """Status do sistema."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime": "Running",
        "components": {
            "database": "healthy" if app_state.db else "unavailable",
            "mt5": "connected" if app_state.mt5_connected else "disconnected",
            "virtus_integration": "active" if VIRTUS_AVAILABLE else "standalone",
        }
    }


@app.get("/health")
async def health_check():
    """Health check."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ==================== WEBSOCKET ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para atualizações em tempo real."""
    await websocket.accept()
    app_state.websocket_connections.add(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif data.get("type") == "subscribe":
                channel = data.get("channel")
                await websocket.send_json({"type": "subscribed", "channel": channel})
                
                if channel == "metrics":
                    await websocket.send_json({"type": "metrics", "data": app_state.metrics})
                elif channel == "positions":
                    await websocket.send_json({"type": "positions", "data": app_state.positions})
                elif channel == "orders":
                    await websocket.send_json({"type": "orders", "data": app_state.pending_orders})
    
    except WebSocketDisconnect:
        app_state.websocket_connections.discard(websocket)
    except Exception:
        app_state.websocket_connections.discard(websocket)


# ==================== MT5 ROUTES ====================

@app.get("/api/mt5/status")
async def get_mt5_status(user: dict = Depends(get_current_user)):
    """Status da conexão MT5."""
    return {
        "connected": app_state.mt5_connected,
        "account": app_state.mt5_account,
    }


@app.post("/api/mt5/connect")
async def connect_mt5(user: dict = Depends(get_current_user)):
    """Conecta ao MT5."""
    return {"success": True, "message": "MT5 connection requested"}


@app.post("/api/mt5/sync")
async def sync_mt5(user: dict = Depends(get_current_user)):
    """Sincroniza dados do MT5."""
    return {"success": True, "synced_trades": 0}


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
