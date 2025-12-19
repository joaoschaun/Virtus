# VIRTUS - Código de Referência para Reconstrução de Bots

Este arquivo contém os trechos de código mais importantes para você reconstruir
bots de trading externos que se comunicam com o dashboard.

## 1. Conexão Básica com MT5

```python
"""
Exemplo mínimo de conexão com MT5.
"""
import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd

class SimpleMT5:
    def __init__(self, login: int, password: str, server: str):
        self.login = login
        self.password = password
        self.server = server
        self.connected = False
    
    def connect(self) -> bool:
        """Conecta ao MT5."""
        if not mt5.initialize():
            print(f"Erro ao inicializar MT5: {mt5.last_error()}")
            return False
        
        # Verifica se já está logado
        account = mt5.account_info()
        if account and account.login == self.login:
            self.connected = True
            return True
        
        # Faz login
        if mt5.login(self.login, self.password, self.server):
            self.connected = True
            return True
        
        print(f"Erro no login: {mt5.last_error()}")
        return False
    
    def disconnect(self):
        """Desconecta do MT5."""
        mt5.shutdown()
        self.connected = False
    
    def get_account_info(self) -> dict:
        """Retorna informações da conta."""
        info = mt5.account_info()
        if info:
            return {
                'login': info.login,
                'server': info.server,
                'balance': info.balance,
                'equity': info.equity,
                'margin': info.margin,
                'free_margin': info.margin_free,
                'profit': info.profit,
                'leverage': info.leverage,
            }
        return {}
    
    def get_candles(self, symbol: str, timeframe: int, count: int = 100) -> pd.DataFrame:
        """
        Obtém candles.
        
        Timeframes:
            mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15,
            mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4, mt5.TIMEFRAME_D1
        """
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            return pd.DataFrame()
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    
    def get_price(self, symbol: str) -> dict:
        """Retorna bid/ask atual."""
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            return {
                'bid': tick.bid,
                'ask': tick.ask,
                'spread': tick.ask - tick.bid,
                'time': datetime.fromtimestamp(tick.time),
            }
        return {}
    
    def send_order(
        self,
        symbol: str,
        order_type: str,  # 'buy' ou 'sell'
        volume: float,
        sl: float = None,
        tp: float = None,
        comment: str = ""
    ) -> dict:
        """Envia ordem a mercado."""
        # Seleciona símbolo
        if not mt5.symbol_select(symbol, True):
            return {'success': False, 'error': 'Símbolo não disponível'}
        
        # Obtém preço
        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if order_type == 'buy' else tick.bid
        
        # Prepara request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if order_type == 'buy' else mt5.ORDER_TYPE_SELL,
            "price": price,
            "deviation": 20,
            "magic": 123456,  # Seu magic number
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        if sl:
            request["sl"] = sl
        if tp:
            request["tp"] = tp
        
        # Envia
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                'success': False,
                'error': result.comment,
                'code': result.retcode
            }
        
        return {
            'success': True,
            'ticket': result.order,
            'price': result.price,
            'volume': result.volume,
        }
    
    def close_position(self, ticket: int) -> bool:
        """Fecha uma posição pelo ticket."""
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False
        
        pos = position[0]
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY,
            "position": ticket,
            "price": mt5.symbol_info_tick(pos.symbol).bid if pos.type == 0 else mt5.symbol_info_tick(pos.symbol).ask,
            "deviation": 20,
            "magic": 123456,
            "comment": "Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE
    
    def get_positions(self, symbol: str = None) -> list:
        """Lista posições abertas."""
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        if not positions:
            return []
        
        return [{
            'ticket': p.ticket,
            'symbol': p.symbol,
            'type': 'buy' if p.type == 0 else 'sell',
            'volume': p.volume,
            'open_price': p.price_open,
            'current_price': p.price_current,
            'sl': p.sl,
            'tp': p.tp,
            'profit': p.profit,
            'swap': p.swap,
            'open_time': datetime.fromtimestamp(p.time),
        } for p in positions]


# Exemplo de uso
if __name__ == "__main__":
    mt5_client = SimpleMT5(
        login=61444598,
        password="SuaSenha",
        server="Pepperstone-Demo"
    )
    
    if mt5_client.connect():
        print("Conectado!")
        print(mt5_client.get_account_info())
        
        # Obtém candles M15
        df = mt5_client.get_candles("EURUSD", mt5.TIMEFRAME_M15, 100)
        print(df.tail())
        
        mt5_client.disconnect()
```

---

## 2. Indicadores Técnicos Simples

```python
"""
Indicadores técnicos básicos usando pandas/numpy.
"""
import numpy as np
import pandas as pd


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcula RSI."""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0):
    """Calcula Bollinger Bands."""
    middle = df['close'].rolling(window=period).mean()
    std_dev = df['close'].rolling(window=period).std()
    
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    return {
        'middle': middle,
        'upper': upper,
        'lower': lower,
    }


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcula ATR (Average True Range)."""
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calcula EMA."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """Calcula MACD."""
    ema_fast = calculate_ema(df['close'], fast)
    ema_slow = calculate_ema(df['close'], slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram,
    }


def detect_trend(df: pd.DataFrame, ema_period: int = 50) -> str:
    """Detecta tendência simples."""
    ema = calculate_ema(df['close'], ema_period)
    current_price = df['close'].iloc[-1]
    ema_current = ema.iloc[-1]
    ema_prev = ema.iloc[-5]  # 5 candles atrás
    
    if current_price > ema_current and ema_current > ema_prev:
        return 'bullish'
    elif current_price < ema_current and ema_current < ema_prev:
        return 'bearish'
    else:
        return 'sideways'
```

---

## 3. Estratégia Simples de Trading

```python
"""
Estratégia simples: RSI + Bollinger Bands.
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class TradeSignal:
    direction: str          # 'buy', 'sell', 'none'
    entry: float
    sl: float
    tp: float
    reason: str
    confidence: float


class SimpleStrategy:
    def __init__(
        self,
        rsi_oversold: int = 30,
        rsi_overbought: int = 70,
        risk_reward: float = 2.0,
        atr_sl_multiplier: float = 1.5,
    ):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.risk_reward = risk_reward
        self.atr_sl_multiplier = atr_sl_multiplier
    
    def analyze(self, df: pd.DataFrame) -> Optional[TradeSignal]:
        """
        Analisa e gera sinal.
        
        Regras:
        - BUY: RSI < 30 e preço tocou BB inferior
        - SELL: RSI > 70 e preço tocou BB superior
        """
        if len(df) < 50:
            return None
        
        # Calcula indicadores
        rsi = calculate_rsi(df)
        bb = calculate_bollinger_bands(df)
        atr = calculate_atr(df)
        
        current_price = df['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1]
        bb_lower = bb['lower'].iloc[-1]
        bb_upper = bb['upper'].iloc[-1]
        
        # BUY Signal
        if current_rsi < self.rsi_oversold and current_price <= bb_lower * 1.002:
            sl_distance = current_atr * self.atr_sl_multiplier
            tp_distance = sl_distance * self.risk_reward
            
            return TradeSignal(
                direction='buy',
                entry=current_price,
                sl=current_price - sl_distance,
                tp=current_price + tp_distance,
                reason=f"RSI oversold ({current_rsi:.1f}) + BB lower touch",
                confidence=0.7 if current_rsi < 25 else 0.6,
            )
        
        # SELL Signal
        if current_rsi > self.rsi_overbought and current_price >= bb_upper * 0.998:
            sl_distance = current_atr * self.atr_sl_multiplier
            tp_distance = sl_distance * self.risk_reward
            
            return TradeSignal(
                direction='sell',
                entry=current_price,
                sl=current_price + sl_distance,
                tp=current_price - tp_distance,
                reason=f"RSI overbought ({current_rsi:.1f}) + BB upper touch",
                confidence=0.7 if current_rsi > 75 else 0.6,
            )
        
        return None
```

---

## 4. Risk Management Simples

```python
"""
Gestão de risco básica.
"""

class SimpleRiskManager:
    def __init__(
        self,
        risk_per_trade: float = 0.01,  # 1%
        max_daily_loss: float = 0.05,   # 5%
        max_positions: int = 3,
    ):
        self.risk_per_trade = risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_positions = max_positions
        
        self.daily_pnl = 0.0
        self.open_positions = 0
    
    def calculate_position_size(
        self,
        balance: float,
        entry: float,
        stop_loss: float,
        symbol: str
    ) -> float:
        """
        Calcula tamanho da posição em lotes.
        
        Fórmula:
        Volume = (Balance * Risk%) / (SL_pips * pip_value)
        """
        # Calcula distância do SL em pips
        sl_distance = abs(entry - stop_loss)
        
        # Pip value por símbolo (simplificado)
        if 'JPY' in symbol:
            pip = 0.01
        elif symbol == 'XAUUSD':
            pip = 0.1
        else:
            pip = 0.0001
        
        sl_pips = sl_distance / pip
        
        # Valor do pip por lote (aproximado)
        if 'JPY' in symbol:
            pip_value = 7.5  # USD
        elif symbol == 'XAUUSD':
            pip_value = 10.0  # USD por 0.1 lot
        else:
            pip_value = 10.0  # USD para majors
        
        # Calcula
        risk_amount = balance * self.risk_per_trade
        volume = risk_amount / (sl_pips * pip_value)
        
        # Arredonda para 2 casas
        volume = round(volume, 2)
        
        # Limites
        volume = max(0.01, min(volume, 10.0))
        
        return volume
    
    def can_trade(self, balance: float, equity: float) -> tuple:
        """Verifica se pode abrir trade."""
        # Daily loss check
        if self.daily_pnl <= -(balance * self.max_daily_loss):
            return False, "Daily loss limit reached"
        
        # Positions check
        if self.open_positions >= self.max_positions:
            return False, "Max positions reached"
        
        # Drawdown check
        drawdown = (balance - equity) / balance
        if drawdown > 0.10:  # 10%
            return False, "High drawdown"
        
        return True, "OK"
    
    def record_trade(self, profit: float):
        """Registra resultado do trade."""
        self.daily_pnl += profit
        if profit >= 0:
            self.open_positions = max(0, self.open_positions - 1)
        else:
            self.open_positions = max(0, self.open_positions - 1)
    
    def new_day(self):
        """Reset para novo dia."""
        self.daily_pnl = 0.0
```

---

## 5. Envio de Dados para Dashboard

```python
"""
Cliente para enviar dados do bot para o dashboard VIRTUS.
"""
import requests
from datetime import datetime
from typing import Dict, List, Any


class DashboardClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.bot_id = None
    
    def register_bot(self, bot_id: str, name: str, symbol: str) -> bool:
        """Registra bot no dashboard."""
        self.bot_id = bot_id
        try:
            response = requests.post(
                f"{self.base_url}/api/bots/register",
                json={
                    "bot_id": bot_id,
                    "name": name,
                    "symbol": symbol,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Erro ao registrar bot: {e}")
            return False
    
    def send_update(
        self,
        account: Dict[str, Any],
        positions: List[Dict],
        statistics: Dict[str, Any],
        status: str = "running"
    ) -> bool:
        """Envia atualização para o dashboard."""
        if not self.bot_id:
            return False
        
        try:
            data = {
                "bot_id": self.bot_id,
                "account": account,
                "positions": positions,
                "orders": [],
                "statistics": statistics,
                "status": {
                    "state": status,
                    "last_analysis": datetime.now().isoformat(),
                },
                "timestamp": datetime.now().isoformat(),
            }
            
            response = requests.post(
                f"{self.base_url}/api/bots/update",
                json=data,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Erro ao enviar update: {e}")
            return False
    
    def send_trade_result(
        self,
        symbol: str,
        direction: str,
        entry: float,
        exit_price: float,
        profit: float,
        pips: float
    ) -> bool:
        """Envia resultado de trade."""
        try:
            response = requests.post(
                f"{self.base_url}/api/bots/{self.bot_id}/trades",
                json={
                    "symbol": symbol,
                    "direction": direction,
                    "entry": entry,
                    "exit": exit_price,
                    "profit": profit,
                    "pips": pips,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Erro ao enviar trade: {e}")
            return False
```

---

## 6. Bot Completo de Exemplo

```python
"""
Bot de trading simples e completo.
"""
import asyncio
import MetaTrader5 as mt5
from datetime import datetime
import time


class SimpleBot:
    def __init__(
        self,
        login: int,
        password: str,
        server: str,
        symbol: str,
        dashboard_url: str = None
    ):
        self.mt5 = SimpleMT5(login, password, server)
        self.symbol = symbol
        self.strategy = SimpleStrategy()
        self.risk = SimpleRiskManager()
        self.dashboard = DashboardClient(dashboard_url) if dashboard_url else None
        
        self.running = False
        self.statistics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
        }
    
    def start(self):
        """Inicia o bot."""
        if not self.mt5.connect():
            print("Falha ao conectar MT5")
            return
        
        if self.dashboard:
            self.dashboard.register_bot(
                f"bot_{self.symbol.lower()}",
                f"Simple Bot {self.symbol}",
                self.symbol
            )
        
        self.running = True
        print(f"Bot iniciado para {self.symbol}")
        
        try:
            while self.running:
                self._run_cycle()
                time.sleep(5)  # 5 segundos
        except KeyboardInterrupt:
            print("Bot interrompido")
        finally:
            self.mt5.disconnect()
    
    def _run_cycle(self):
        """Executa um ciclo de análise."""
        # 1. Obtém dados
        df = self.mt5.get_candles(self.symbol, mt5.TIMEFRAME_M15, 100)
        if df.empty:
            return
        
        account = self.mt5.get_account_info()
        positions = self.mt5.get_positions(self.symbol)
        
        # 2. Verifica se pode operar
        can_trade, reason = self.risk.can_trade(
            account['balance'],
            account['equity']
        )
        
        # 3. Se não tem posição aberta, busca sinal
        if can_trade and not positions:
            signal = self.strategy.analyze(df)
            
            if signal and signal.confidence >= 0.6:
                volume = self.risk.calculate_position_size(
                    account['balance'],
                    signal.entry,
                    signal.sl,
                    self.symbol
                )
                
                result = self.mt5.send_order(
                    self.symbol,
                    signal.direction,
                    volume,
                    sl=signal.sl,
                    tp=signal.tp,
                    comment=signal.reason[:30]
                )
                
                if result['success']:
                    print(f"✅ Trade aberto: {signal.direction} {volume} @ {result['price']}")
                    self.risk.open_positions += 1
        
        # 4. Atualiza dashboard
        if self.dashboard:
            self.dashboard.send_update(
                account=account,
                positions=positions,
                statistics=self.statistics,
                status="running"
            )
    
    def stop(self):
        """Para o bot."""
        self.running = False


# Execução
if __name__ == "__main__":
    bot = SimpleBot(
        login=61444598,
        password="SuaSenha",
        server="Pepperstone-Demo",
        symbol="EURUSD",
        dashboard_url="http://localhost:8000"
    )
    bot.start()
```

---

## Notas Importantes

1. **Sempre teste em conta demo primeiro**
2. **Comece com volume mínimo (0.01)**
3. **Monitore os logs e erros**
4. **Implemente circuit breakers**
5. **Nunca arrisque mais de 1-2% por trade**

---

*Código de referência VIRTUS - Dezembro 2025*
