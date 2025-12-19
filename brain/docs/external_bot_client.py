"""
VIRTUS Dashboard - Cliente Python para Bots Externos
=====================================================

Este módulo fornece uma classe cliente completa para integrar
bots de trading externos com o dashboard VIRTUS.

Uso:
    from external_bot_client import VirtusDashboardClient
    
    client = VirtusDashboardClient(
        api_key="vts_sua_api_key_aqui",
        base_url="http://localhost:8000"  # URL do dashboard
    )
    
    # Enviar atualização completa
    client.send_full_update(
        account_balance=10000.0,
        account_equity=10150.0,
        positions=[...],
        daily_profit=150.0,
        ...
    )

Para obter uma API Key:
    1. Acesse o dashboard VIRTUS
    2. Vá em Configurações > Bots Externos
    3. Clique em "Gerar Nova API Key"
    4. Copie a key (ela só aparece uma vez!)
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import time
import threading

logger = logging.getLogger(__name__)


class Direction(str, Enum):
    """Direção do trade."""
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"


class TradeStatus(str, Enum):
    """Status do trade."""
    PENDING = "pending"
    OPENED = "opened"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class Position:
    """Representa uma posição aberta."""
    ticket: int
    symbol: str
    direction: str  # "buy" ou "sell"
    volume: float
    entry_price: float
    current_price: float
    profit: float
    open_time: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    profit_pips: float = 0.0
    swap: float = 0.0
    commission: float = 0.0
    magic: int = 0
    comment: str = ""


class VirtusDashboardClient:
    """
    Cliente para integração com o Dashboard VIRTUS.
    
    Features:
    - Autenticação via API Key
    - Retry automático em falhas de rede
    - Batching de updates
    - Thread-safe
    - Logging integrado
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Inicializa o cliente.
        
        Args:
            api_key: API Key gerada no dashboard VIRTUS
            base_url: URL base do dashboard (ex: http://localhost:8000)
            timeout: Timeout das requisições em segundos
            max_retries: Número máximo de tentativas em caso de falha
            retry_delay: Delay entre tentativas em segundos
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._session = requests.Session()
        self._session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        })
        
        self._lock = threading.Lock()
        self._last_update = None
        self._errors: List[str] = []
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Faz requisição HTTP com retry automático.
        """
        url = f"{self.base_url}/api/external{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise AuthenticationError("API Key inválida ou expirada")
                elif response.status_code == 429:
                    raise RateLimitError("Rate limit excedido, aguarde antes de tentar novamente")
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(f"Tentativa {attempt + 1}/{self.max_retries} falhou: {error_msg}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Tentativa {attempt + 1}/{self.max_retries} falhou: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))
        
        raise ConnectionError(f"Falha após {self.max_retries} tentativas")
    
    # ==================== MÉTODOS PRINCIPAIS ====================
    
    def send_full_update(
        self,
        account_balance: float,
        account_equity: float,
        positions: List[Position] = None,
        account_margin: float = 0.0,
        account_free_margin: float = 0.0,
        account_profit: float = 0.0,
        daily_profit: float = 0.0,
        daily_profit_pips: float = 0.0,
        daily_trades: int = 0,
        daily_wins: int = 0,
        daily_losses: int = 0,
        total_trades: int = 0,
        total_profit: float = 0.0,
        win_rate: float = 0.0,
        max_drawdown: float = 0.0,
        is_running: bool = True,
        is_connected: bool = True,
        uptime_seconds: int = 0,
        last_trade_time: str = None,
        bot_version: str = "1.0.0",
        strategy_name: str = "",
        errors: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict:
        """
        Envia atualização completa do bot para o dashboard.
        
        Este é o método PRINCIPAL - chame a cada 30-60 segundos
        para manter o dashboard atualizado em tempo real.
        
        Args:
            account_balance: Saldo da conta
            account_equity: Equity atual
            positions: Lista de posições abertas
            account_margin: Margem utilizada
            account_free_margin: Margem livre
            account_profit: Lucro flutuante total
            daily_profit: Lucro do dia em $
            daily_profit_pips: Lucro do dia em pips
            daily_trades: Número de trades do dia
            daily_wins: Trades vencedores do dia
            daily_losses: Trades perdedores do dia
            total_trades: Total histórico de trades
            total_profit: Lucro total histórico
            win_rate: Win rate (0-100)
            max_drawdown: Drawdown máximo (0-100)
            is_running: Bot está rodando
            is_connected: Conectado ao broker
            uptime_seconds: Tempo online
            last_trade_time: Último trade (ISO format)
            bot_version: Versão do bot
            strategy_name: Nome da estratégia ativa
            errors: Lista de erros recentes
            metadata: Dados adicionais
            
        Returns:
            Dict com resposta do servidor
        """
        with self._lock:
            # Converte positions para dicts
            positions_data = []
            if positions:
                for pos in positions:
                    if isinstance(pos, Position):
                        positions_data.append(asdict(pos))
                    elif isinstance(pos, dict):
                        positions_data.append(pos)
            
            data = {
                "is_running": is_running,
                "is_connected": is_connected,
                "account_balance": account_balance,
                "account_equity": account_equity,
                "account_margin": account_margin,
                "account_free_margin": account_free_margin,
                "account_profit": account_profit,
                "positions": positions_data,
                "daily_profit": daily_profit,
                "daily_profit_pips": daily_profit_pips,
                "daily_trades": daily_trades,
                "daily_wins": daily_wins,
                "daily_losses": daily_losses,
                "total_trades": total_trades,
                "total_profit": total_profit,
                "win_rate": win_rate,
                "max_drawdown": max_drawdown,
                "uptime_seconds": uptime_seconds,
                "last_trade_time": last_trade_time,
                "bot_version": bot_version,
                "strategy_name": strategy_name,
                "errors": errors or self._errors[-10:],
                "metadata": metadata or {}
            }
            
            result = self._request("POST", "/update", data=data)
            self._last_update = datetime.now()
            
            return result
    
    def send_signal(
        self,
        symbol: str,
        direction: str,
        entry_price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        confidence: float = 0.7,
        timeframe: str = "M15",
        strategy: str = "external",
        metadata: Dict = None
    ) -> Dict:
        """
        Envia um sinal de trading.
        
        Args:
            symbol: Símbolo (ex: "XAUUSD", "EURUSD")
            direction: "buy", "sell" ou "close"
            entry_price: Preço de entrada sugerido
            stop_loss: Stop loss
            take_profit: Take profit
            confidence: Confiança do sinal (0-1)
            timeframe: Timeframe da análise
            strategy: Nome da estratégia
            metadata: Dados adicionais
            
        Returns:
            Dict com signal_id e timestamp
        """
        data = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "timeframe": timeframe,
            "strategy": strategy,
            "metadata": metadata or {}
        }
        
        return self._request("POST", "/signal", data=data)
    
    def report_trade(
        self,
        external_id: str,
        symbol: str,
        direction: str,
        status: str,
        entry_price: float,
        volume: float,
        open_time: str,
        current_price: float = None,
        exit_price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        profit: float = 0.0,
        profit_pips: float = 0.0,
        close_time: str = None,
        metadata: Dict = None
    ) -> Dict:
        """
        Reporta um trade executado.
        
        Use para manter histórico de trades sincronizado com o dashboard.
        
        Args:
            external_id: ID único do trade no seu sistema
            symbol: Símbolo do ativo
            direction: "buy" ou "sell"
            status: "pending", "opened", "closed", "cancelled", "error"
            entry_price: Preço de entrada
            volume: Volume em lotes
            open_time: Data/hora abertura (ISO format)
            current_price: Preço atual (para trades abertos)
            exit_price: Preço de saída (para trades fechados)
            stop_loss: Stop loss
            take_profit: Take profit
            profit: Lucro/prejuízo em $
            profit_pips: Lucro em pips
            close_time: Data/hora fechamento (ISO format)
            metadata: Dados adicionais
            
        Returns:
            Dict com internal_id atribuído pelo dashboard
        """
        data = {
            "external_id": external_id,
            "symbol": symbol,
            "direction": direction,
            "status": status,
            "entry_price": entry_price,
            "volume": volume,
            "open_time": open_time,
            "current_price": current_price,
            "exit_price": exit_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "profit": profit,
            "profit_pips": profit_pips,
            "close_time": close_time,
            "metadata": metadata or {}
        }
        
        return self._request("POST", "/trade", data=data)
    
    def update_status(
        self,
        is_running: bool,
        is_connected: bool,
        account_balance: float = None,
        account_equity: float = None,
        open_positions: int = 0,
        daily_profit: float = 0.0,
        daily_trades: int = 0,
        uptime_seconds: int = 0,
        last_trade_time: str = None,
        errors: List[str] = None,
        metadata: Dict = None
    ) -> Dict:
        """
        Atualiza status básico do bot.
        
        Alternativa mais leve ao send_full_update quando não há
        necessidade de enviar todas as posições.
        """
        data = {
            "is_running": is_running,
            "is_connected": is_connected,
            "account_balance": account_balance,
            "account_equity": account_equity,
            "open_positions": open_positions,
            "daily_profit": daily_profit,
            "daily_trades": daily_trades,
            "uptime_seconds": uptime_seconds,
            "last_trade_time": last_trade_time,
            "errors": errors or [],
            "metadata": metadata or {}
        }
        
        return self._request("POST", "/status", data=data)
    
    def send_metrics(
        self,
        total_trades: int = 0,
        winning_trades: int = 0,
        losing_trades: int = 0,
        win_rate: float = 0.0,
        total_profit: float = 0.0,
        total_profit_pips: float = 0.0,
        max_drawdown: float = 0.0,
        profit_factor: float = 0.0,
        average_win: float = 0.0,
        average_loss: float = 0.0,
        best_trade: float = 0.0,
        worst_trade: float = 0.0,
        period: str = "all_time"
    ) -> Dict:
        """
        Envia métricas de performance.
        
        Recomendado enviar ao final de cada dia ou quando
        houver mudanças significativas.
        """
        data = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "total_profit_pips": total_profit_pips,
            "max_drawdown": max_drawdown,
            "profit_factor": profit_factor,
            "average_win": average_win,
            "average_loss": average_loss,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "period": period
        }
        
        return self._request("POST", "/metrics", data=data)
    
    # ==================== MÉTODOS AUXILIARES ====================
    
    def get_api_info(self) -> Dict:
        """Retorna informações da API e status da conexão."""
        return self._request("GET", "/info")
    
    def get_my_signals(self, limit: int = 100) -> Dict:
        """Retorna sinais enviados pelo bot."""
        return self._request("GET", "/signals", params={"limit": limit})
    
    def get_my_trades(self, limit: int = 100, status: str = None) -> Dict:
        """Retorna trades do bot."""
        params = {"limit": limit}
        if status:
            params["status"] = status
        return self._request("GET", "/trades", params=params)
    
    def get_my_status(self) -> Dict:
        """Retorna último status enviado."""
        return self._request("GET", "/bot-status")
    
    def get_my_metrics(self) -> Dict:
        """Retorna métricas do bot."""
        return self._request("GET", "/bot-metrics")
    
    def add_error(self, error: str):
        """Adiciona erro à lista para próximo update."""
        self._errors.append(f"[{datetime.now().isoformat()}] {error}")
        if len(self._errors) > 50:
            self._errors = self._errors[-50:]
    
    def test_connection(self) -> bool:
        """Testa conexão com o dashboard."""
        try:
            info = self.get_api_info()
            return info.get("bot_info") is not None
        except:
            return False


# ==================== EXCEÇÕES ====================

class VirtusClientError(Exception):
    """Erro base do cliente."""
    pass


class AuthenticationError(VirtusClientError):
    """Erro de autenticação (API Key inválida)."""
    pass


class RateLimitError(VirtusClientError):
    """Rate limit excedido."""
    pass


class ConnectionError(VirtusClientError):
    """Erro de conexão."""
    pass


# ==================== EXEMPLO DE USO ====================

if __name__ == "__main__":
    """
    Exemplo de integração de um bot com o dashboard VIRTUS.
    """
    
    # Configuração
    API_KEY = "vts_SUA_API_KEY_AQUI"  # Obtida no dashboard
    DASHBOARD_URL = "http://localhost:8000"
    
    # Inicializa cliente
    client = VirtusDashboardClient(
        api_key=API_KEY,
        base_url=DASHBOARD_URL
    )
    
    # Testa conexão
    if client.test_connection():
        print("✅ Conectado ao dashboard VIRTUS!")
    else:
        print("❌ Falha na conexão")
        exit(1)
    
    # Exemplo de posições abertas
    positions = [
        Position(
            ticket=123456,
            symbol="XAUUSD",
            direction="buy",
            volume=0.1,
            entry_price=2650.50,
            current_price=2655.00,
            profit=45.0,
            profit_pips=45,
            open_time=datetime.now().isoformat(),
            stop_loss=2640.00,
            take_profit=2670.00,
            magic=12345,
            comment="Gold Strategy"
        ),
        Position(
            ticket=123457,
            symbol="EURUSD",
            direction="sell",
            volume=0.05,
            entry_price=1.0850,
            current_price=1.0845,
            profit=2.50,
            profit_pips=5,
            open_time=datetime.now().isoformat(),
            stop_loss=1.0900,
            take_profit=1.0800
        )
    ]
    
    # Envia atualização completa
    result = client.send_full_update(
        # Account
        account_balance=10000.00,
        account_equity=10047.50,
        account_margin=500.00,
        account_free_margin=9547.50,
        account_profit=47.50,
        
        # Positions
        positions=positions,
        
        # Daily stats
        daily_profit=147.50,
        daily_profit_pips=50,
        daily_trades=5,
        daily_wins=3,
        daily_losses=2,
        
        # Overall stats
        total_trades=250,
        total_profit=3500.00,
        win_rate=62.5,
        max_drawdown=8.5,
        
        # Bot info
        is_running=True,
        is_connected=True,
        uptime_seconds=3600 * 8,  # 8 horas
        bot_version="2.1.0",
        strategy_name="Multi-Symbol Strategy"
    )
    
    print(f"✅ Update enviado: {result}")
    
    # Exemplo de envio de sinal
    signal_result = client.send_signal(
        symbol="GBPUSD",
        direction="buy",
        entry_price=1.2650,
        stop_loss=1.2620,
        take_profit=1.2700,
        confidence=0.85,
        strategy="Breakout Strategy",
        metadata={"indicator": "RSI", "value": 35}
    )
    
    print(f"✅ Sinal enviado: {signal_result}")
    
    # Exemplo de report de trade
    trade_result = client.report_trade(
        external_id="MT5_123458",
        symbol="USDJPY",
        direction="buy",
        status="closed",
        entry_price=149.50,
        exit_price=149.80,
        volume=0.1,
        profit=30.0,
        profit_pips=30,
        open_time="2024-01-15T10:30:00",
        close_time="2024-01-15T14:45:00"
    )
    
    print(f"✅ Trade reportado: {trade_result}")
