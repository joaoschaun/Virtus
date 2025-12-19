"""
VIRTUS - Sistema de Auditoria
==============================

Log de todas as ações críticas do sistema para compliance e debugging.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import hashlib
import threading

logger = logging.getLogger("virtus.audit")


class AuditCategory(str, Enum):
    """Categorias de eventos de auditoria."""
    TRADE = "trade"
    CONFIG = "config"
    AUTH = "auth"
    SYSTEM = "system"
    RISK = "risk"
    BOT = "bot"
    API = "api"
    ERROR = "error"


class AuditAction(str, Enum):
    """Ações de auditoria."""
    # Trades
    TRADE_OPEN = "trade_open"
    TRADE_CLOSE = "trade_close"
    TRADE_MODIFY = "trade_modify"
    TRADE_CANCEL = "trade_cancel"
    
    # Configurações
    CONFIG_CHANGE = "config_change"
    CONFIG_LOAD = "config_load"
    
    # Autenticação
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    
    # Sistema
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"
    BACKUP_CREATED = "backup_created"
    
    # Risco
    DRAWDOWN_ALERT = "drawdown_alert"
    RISK_LIMIT_HIT = "risk_limit_hit"
    POSITION_LIMIT_HIT = "position_limit_hit"
    
    # Bots
    BOT_START = "bot_start"
    BOT_STOP = "bot_stop"
    BOT_CONFIG_CHANGE = "bot_config_change"
    BOT_ERROR = "bot_error"
    
    # API
    API_CALL = "api_call"
    API_ERROR = "api_error"
    WEBHOOK_SENT = "webhook_sent"


class AuditSeverity(str, Enum):
    """Severidade do evento."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Evento de auditoria."""
    id: Optional[int] = None
    timestamp: datetime = None
    category: AuditCategory = AuditCategory.SYSTEM
    action: AuditAction = AuditAction.SYSTEM_START
    severity: AuditSeverity = AuditSeverity.INFO
    user: Optional[str] = None
    ip_address: Optional[str] = None
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    details: Optional[Dict] = None
    hash: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.hash is None:
            self.hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Computa hash do evento para integridade."""
        data = f"{self.timestamp}|{self.category}|{self.action}|{self.user}|{self.resource}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "action": self.action.value if isinstance(self.action, Enum) else self.action,
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "user": self.user,
            "ip_address": self.ip_address,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "details": self.details,
            "hash": self.hash,
        }


class AuditLog:
    """
    Sistema de auditoria com persistência em SQLite.
    
    Uso:
        audit = AuditLog()
        audit.log_trade(action="open", symbol="XAUUSD", ...)
        audit.log_config_change(key="risk.max_positions", old=3, new=5)
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path(__file__).parent.parent.parent / "data" / "audit.db")
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Inicializa banco de dados."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user TEXT,
                    ip_address TEXT,
                    resource TEXT,
                    resource_id TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    details TEXT,
                    hash TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices para consultas rápidas
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_log(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource)")
            
            conn.commit()
    
    def log(self, event: AuditEvent) -> int:
        """Registra evento de auditoria."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO audit_log 
                    (timestamp, category, action, severity, user, ip_address, 
                     resource, resource_id, old_value, new_value, details, hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.timestamp.isoformat(),
                    event.category.value if isinstance(event.category, Enum) else event.category,
                    event.action.value if isinstance(event.action, Enum) else event.action,
                    event.severity.value if isinstance(event.severity, Enum) else event.severity,
                    event.user,
                    event.ip_address,
                    event.resource,
                    event.resource_id,
                    event.old_value,
                    event.new_value,
                    json.dumps(event.details) if event.details else None,
                    event.hash,
                ))
                conn.commit()
                
                event.id = cursor.lastrowid
                logger.debug(f"Audit logged: {event.action} by {event.user}")
                
                return event.id
    
    # =========================================================================
    # MÉTODOS HELPER PARA LOGGING
    # =========================================================================
    
    def log_trade(
        self,
        action: str,
        symbol: str,
        ticket: Optional[int] = None,
        volume: Optional[float] = None,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        profit: Optional[float] = None,
        user: Optional[str] = None,
        bot_id: Optional[str] = None,
        **kwargs
    ) -> int:
        """Log de operação de trade."""
        action_map = {
            "open": AuditAction.TRADE_OPEN,
            "close": AuditAction.TRADE_CLOSE,
            "modify": AuditAction.TRADE_MODIFY,
            "cancel": AuditAction.TRADE_CANCEL,
        }
        
        return self.log(AuditEvent(
            category=AuditCategory.TRADE,
            action=action_map.get(action, AuditAction.TRADE_OPEN),
            severity=AuditSeverity.INFO,
            user=user or bot_id or "system",
            resource="trade",
            resource_id=str(ticket) if ticket else None,
            details={
                "symbol": symbol,
                "ticket": ticket,
                "volume": volume,
                "price": price,
                "sl": sl,
                "tp": tp,
                "profit": profit,
                "bot_id": bot_id,
                **kwargs
            }
        ))
    
    def log_config_change(
        self,
        key: str,
        old_value: Any,
        new_value: Any,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> int:
        """Log de mudança de configuração."""
        return self.log(AuditEvent(
            category=AuditCategory.CONFIG,
            action=AuditAction.CONFIG_CHANGE,
            severity=AuditSeverity.WARNING,
            user=user or "admin",
            ip_address=ip_address,
            resource="config",
            resource_id=key,
            old_value=json.dumps(old_value) if not isinstance(old_value, str) else old_value,
            new_value=json.dumps(new_value) if not isinstance(new_value, str) else new_value,
        ))
    
    def log_login(
        self,
        username: str,
        success: bool,
        ip_address: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> int:
        """Log de tentativa de login."""
        return self.log(AuditEvent(
            category=AuditCategory.AUTH,
            action=AuditAction.LOGIN_SUCCESS if success else AuditAction.LOGIN_FAILED,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user=username,
            ip_address=ip_address,
            resource="auth",
            details={"reason": reason} if reason else None,
        ))
    
    def log_bot_action(
        self,
        action: str,
        bot_id: str,
        user: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> int:
        """Log de ação de bot."""
        action_map = {
            "start": AuditAction.BOT_START,
            "stop": AuditAction.BOT_STOP,
            "config": AuditAction.BOT_CONFIG_CHANGE,
            "error": AuditAction.BOT_ERROR,
        }
        
        return self.log(AuditEvent(
            category=AuditCategory.BOT,
            action=action_map.get(action, AuditAction.BOT_START),
            severity=AuditSeverity.ERROR if action == "error" else AuditSeverity.INFO,
            user=user or "system",
            resource="bot",
            resource_id=bot_id,
            details=details,
        ))
    
    def log_risk_alert(
        self,
        alert_type: str,
        value: float,
        threshold: float,
        action_taken: Optional[str] = None,
    ) -> int:
        """Log de alerta de risco."""
        action_map = {
            "drawdown": AuditAction.DRAWDOWN_ALERT,
            "risk_limit": AuditAction.RISK_LIMIT_HIT,
            "position_limit": AuditAction.POSITION_LIMIT_HIT,
        }
        
        return self.log(AuditEvent(
            category=AuditCategory.RISK,
            action=action_map.get(alert_type, AuditAction.DRAWDOWN_ALERT),
            severity=AuditSeverity.CRITICAL,
            user="system",
            resource="risk",
            details={
                "alert_type": alert_type,
                "value": value,
                "threshold": threshold,
                "action_taken": action_taken,
            }
        ))
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict] = None,
        user: Optional[str] = None,
    ) -> int:
        """Log de erro do sistema."""
        return self.log(AuditEvent(
            category=AuditCategory.ERROR,
            action=AuditAction.SYSTEM_ERROR,
            severity=AuditSeverity.ERROR,
            user=user or "system",
            resource="error",
            details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context,
            }
        ))
    
    def log_api_call(
        self,
        method: str,
        endpoint: str,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
    ) -> int:
        """Log de chamada à API."""
        return self.log(AuditEvent(
            category=AuditCategory.API,
            action=AuditAction.API_CALL,
            severity=AuditSeverity.DEBUG,
            user=user,
            ip_address=ip_address,
            resource="api",
            resource_id=endpoint,
            details={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }
        ))
    
    # =========================================================================
    # CONSULTAS
    # =========================================================================
    
    def query(
        self,
        category: Optional[AuditCategory] = None,
        action: Optional[AuditAction] = None,
        user: Optional[str] = None,
        resource: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """Consulta eventos de auditoria."""
        conditions = []
        params = []
        
        if category:
            conditions.append("category = ?")
            params.append(category.value if isinstance(category, Enum) else category)
        
        if action:
            conditions.append("action = ?")
            params.append(action.value if isinstance(action, Enum) else action)
        
        if user:
            conditions.append("user = ?")
            params.append(user)
        
        if resource:
            conditions.append("resource = ?")
            params.append(resource)
        
        if severity:
            conditions.append("severity = ?")
            params.append(severity.value if isinstance(severity, Enum) else severity)
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date.isoformat())
        
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date.isoformat())
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT id, timestamp, category, action, severity, user, ip_address,
                   resource, resource_id, old_value, new_value, details, hash
            FROM audit_log
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "category": row["category"],
                    "action": row["action"],
                    "severity": row["severity"],
                    "user": row["user"],
                    "ip_address": row["ip_address"],
                    "resource": row["resource"],
                    "resource_id": row["resource_id"],
                    "old_value": row["old_value"],
                    "new_value": row["new_value"],
                    "details": json.loads(row["details"]) if row["details"] else None,
                    "hash": row["hash"],
                })
            
            return results
    
    def get_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Retorna estatísticas de auditoria."""
        start_date = start_date or datetime.now() - timedelta(days=7)
        end_date = end_date or datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            # Total de eventos
            total = conn.execute("""
                SELECT COUNT(*) FROM audit_log
                WHERE timestamp BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat())).fetchone()[0]
            
            # Por categoria
            by_category = {}
            for row in conn.execute("""
                SELECT category, COUNT(*) as count FROM audit_log
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY category
            """, (start_date.isoformat(), end_date.isoformat())):
                by_category[row[0]] = row[1]
            
            # Por severidade
            by_severity = {}
            for row in conn.execute("""
                SELECT severity, COUNT(*) as count FROM audit_log
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY severity
            """, (start_date.isoformat(), end_date.isoformat())):
                by_severity[row[0]] = row[1]
            
            # Top usuários
            top_users = []
            for row in conn.execute("""
                SELECT user, COUNT(*) as count FROM audit_log
                WHERE timestamp BETWEEN ? AND ? AND user IS NOT NULL
                GROUP BY user
                ORDER BY count DESC
                LIMIT 10
            """, (start_date.isoformat(), end_date.isoformat())):
                top_users.append({"user": row[0], "count": row[1]})
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "total_events": total,
                "by_category": by_category,
                "by_severity": by_severity,
                "top_users": top_users,
            }
    
    def cleanup(self, days_to_keep: int = 90):
        """Remove eventos antigos."""
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                DELETE FROM audit_log WHERE timestamp < ?
            """, (cutoff.isoformat(),))
            
            deleted = result.rowcount
            conn.commit()
            
            logger.info(f"Audit cleanup: {deleted} eventos removidos")
            return deleted


# Instância global
audit_log = AuditLog()


# ============================================================================
# MIDDLEWARE FASTAPI PARA AUDITORIA AUTOMÁTICA
# ============================================================================

async def audit_middleware(request, call_next):
    """Middleware para auditoria automática de requests."""
    import time
    
    start_time = time.time()
    
    # Obtém informações do request
    user = getattr(request.state, "user", None)
    ip_address = request.client.host if request.client else None
    
    response = await call_next(request)
    
    # Calcula duração
    duration_ms = (time.time() - start_time) * 1000
    
    # Log apenas para endpoints importantes (não assets)
    if request.url.path.startswith("/api/"):
        audit_log.log_api_call(
            method=request.method,
            endpoint=request.url.path,
            user=user,
            ip_address=ip_address,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
    
    return response


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Teste básico
    audit = AuditLog()
    
    # Log de trade
    audit.log_trade(
        action="open",
        symbol="XAUUSD",
        ticket=123456,
        volume=0.01,
        price=2050.50,
        sl=2045.00,
        tp=2060.00,
        bot_id="XAUUSD_Scalper"
    )
    
    # Log de config
    audit.log_config_change(
        key="risk.max_positions",
        old_value=3,
        new_value=5,
        user="admin",
        ip_address="192.168.1.100"
    )
    
    # Log de login
    audit.log_login("admin", success=True, ip_address="192.168.1.100")
    audit.log_login("hacker", success=False, ip_address="1.2.3.4", reason="Invalid password")
    
    # Log de bot
    audit.log_bot_action("start", "XAUUSD_Scalper", user="admin")
    
    # Consulta
    events = audit.query(category=AuditCategory.TRADE, limit=10)
    print(f"Trades: {len(events)}")
    
    # Stats
    stats = audit.get_stats()
    print(f"Stats: {stats}")
