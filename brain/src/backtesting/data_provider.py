"""
VIRTUS Data Provider
====================

Provedor de dados históricos para backtesting.
Suporta MT5, arquivos CSV e dados em memória.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import pandas as pd
import numpy as np

try:
    from ..core import VirtusLogger
except ImportError:
    # Fallback - usa logging padrão
    import logging
    class VirtusLogger:
        @staticmethod
        def get_logger(name):
            logging.basicConfig(level=logging.INFO)
            return logging.getLogger(name)


class Timeframe:
    """Timeframes disponíveis."""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"
    
    @staticmethod
    def to_minutes(tf: str) -> int:
        """Converte timeframe para minutos."""
        mapping = {
            "M1": 1, "M5": 5, "M15": 15, "M30": 30,
            "H1": 60, "H4": 240, "D1": 1440,
            "W1": 10080, "MN1": 43200,
        }
        return mapping.get(tf, 60)
    
    @staticmethod
    def to_mt5(tf: str) -> int:
        """Converte para constante MT5."""
        mapping = {
            "M1": 1, "M5": 5, "M15": 15, "M30": 30,
            "H1": 16385, "H4": 16388, "D1": 16408,
            "W1": 32769, "MN1": 49153,
        }
        return mapping.get(tf, 16385)


class DataProvider:
    """
    Provedor de dados históricos.
    
    Fontes suportadas:
    - MetaTrader 5
    - Arquivos CSV
    - DataFrames em memória
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.logger = VirtusLogger.get_logger("data_provider")
        
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._cache: Dict[str, pd.DataFrame] = {}
        self._mt5_available = self._check_mt5()
    
    def _check_mt5(self) -> bool:
        """Verifica se MT5 está disponível."""
        try:
            import MetaTrader5
            return True
        except ImportError:
            return False
    
    # ============================================================
    # MT5
    # ============================================================
    
    def get_mt5_data(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: Optional[datetime] = None,
        bars: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Obtém dados do MetaTrader 5.
        
        Args:
            symbol: Símbolo (ex: "XAUUSD")
            timeframe: Timeframe (ex: "H1")
            start: Data inicial
            end: Data final (opcional)
            bars: Número de barras (alternativa a end)
        
        Returns:
            DataFrame com OHLCV
        """
        if not self._mt5_available:
            raise RuntimeError("MetaTrader5 não disponível")
        
        import MetaTrader5 as mt5
        
        # Inicializa MT5 se necessário
        if not mt5.initialize():
            raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
        
        try:
            tf = Timeframe.to_mt5(timeframe)
            
            if bars:
                rates = mt5.copy_rates_from(symbol, tf, start, bars)
            elif end:
                rates = mt5.copy_rates_range(symbol, tf, start, end)
            else:
                rates = mt5.copy_rates_from(symbol, tf, start, 1000)
            
            if rates is None or len(rates) == 0:
                self.logger.warning(f"No data for {symbol} {timeframe}")
                return pd.DataFrame()
            
            # Converte para DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume',
            }, inplace=True)
            
            # Remove colunas desnecessárias
            cols_to_keep = ['open', 'high', 'low', 'close', 'volume']
            df = df[[c for c in cols_to_keep if c in df.columns]]
            
            self.logger.info(f"Loaded {len(df)} bars for {symbol} {timeframe}")
            
            return df
            
        finally:
            # Não desliga MT5 - pode estar sendo usado por outros processos
            pass
    
    # ============================================================
    # CSV
    # ============================================================
    
    def load_csv(
        self,
        filepath: str,
        datetime_col: str = 'time',
        datetime_format: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Carrega dados de arquivo CSV.
        
        Args:
            filepath: Caminho do arquivo
            datetime_col: Nome da coluna de datetime
            datetime_format: Formato da data (auto-detect se None)
        
        Returns:
            DataFrame com OHLCV
        """
        df = pd.read_csv(filepath)
        
        # Converte datetime
        if datetime_col in df.columns:
            if datetime_format:
                df[datetime_col] = pd.to_datetime(df[datetime_col], format=datetime_format)
            else:
                df[datetime_col] = pd.to_datetime(df[datetime_col])
            df.set_index(datetime_col, inplace=True)
        
        # Normaliza nomes das colunas
        df.columns = df.columns.str.lower()
        
        # Renomeia colunas comuns
        renames = {
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'close_price': 'close',
            'tick_volume': 'volume',
            'vol': 'volume',
        }
        df.rename(columns=renames, inplace=True)
        
        self.logger.info(f"Loaded {len(df)} bars from {filepath}")
        
        return df
    
    def save_csv(
        self,
        data: pd.DataFrame,
        filepath: str,
    ) -> None:
        """Salva dados em CSV."""
        data.to_csv(filepath)
        self.logger.info(f"Saved {len(data)} bars to {filepath}")
    
    # ============================================================
    # CACHE
    # ============================================================
    
    def get_cached(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> Optional[pd.DataFrame]:
        """Busca dados do cache."""
        key = f"{symbol}_{timeframe}"
        
        if key in self._cache:
            df = self._cache[key]
            return df[(df.index >= start) & (df.index <= end)]
        
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.parquet"
            if cache_file.exists():
                df = pd.read_parquet(cache_file)
                self._cache[key] = df
                return df[(df.index >= start) & (df.index <= end)]
        
        return None
    
    def cache_data(
        self,
        data: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> None:
        """Adiciona dados ao cache."""
        key = f"{symbol}_{timeframe}"
        
        if key in self._cache:
            # Merge com dados existentes
            existing = self._cache[key]
            combined = pd.concat([existing, data])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined.sort_index(inplace=True)
            self._cache[key] = combined
        else:
            self._cache[key] = data.copy()
        
        # Salva em disco se cache_dir configurado
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.parquet"
            self._cache[key].to_parquet(cache_file)
    
    def clear_cache(self) -> None:
        """Limpa cache em memória."""
        self._cache.clear()
    
    # ============================================================
    # DADOS SINTÉTICOS
    # ============================================================
    
    def generate_random_walk(
        self,
        start_price: float = 100.0,
        bars: int = 1000,
        volatility: float = 0.02,
        trend: float = 0.0,
        start_date: Optional[datetime] = None,
        timeframe: str = "H1",
    ) -> pd.DataFrame:
        """
        Gera dados de random walk para testes.
        
        Args:
            start_price: Preço inicial
            bars: Número de barras
            volatility: Volatilidade (std dev dos retornos)
            trend: Drift (tendência)
            start_date: Data inicial
            timeframe: Timeframe para timestamps
        
        Returns:
            DataFrame com OHLCV
        """
        np.random.seed(42)  # Reprodutibilidade
        
        # Gera retornos
        returns = np.random.normal(trend, volatility, bars)
        
        # Calcula preços de fechamento
        close = start_price * np.exp(np.cumsum(returns))
        
        # Gera OHLC
        high = close * (1 + np.abs(np.random.normal(0, volatility/2, bars)))
        low = close * (1 - np.abs(np.random.normal(0, volatility/2, bars)))
        open_ = np.roll(close, 1)
        open_[0] = start_price
        
        # Ajusta high/low para serem consistentes
        high = np.maximum(high, np.maximum(open_, close))
        low = np.minimum(low, np.minimum(open_, close))
        
        # Gera volume
        volume = np.random.lognormal(10, 1, bars).astype(int)
        
        # Gera timestamps
        if start_date is None:
            start_date = datetime.now() - timedelta(days=bars)
        
        minutes = Timeframe.to_minutes(timeframe)
        timestamps = pd.date_range(start=start_date, periods=bars, freq=f'{minutes}min')
        
        df = pd.DataFrame({
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        }, index=timestamps)
        
        self.logger.info(f"Generated {bars} bars of random walk data")
        
        return df
    
    def generate_trending(
        self,
        start_price: float = 100.0,
        bars: int = 1000,
        trend_strength: float = 0.001,
        noise: float = 0.01,
        start_date: Optional[datetime] = None,
        timeframe: str = "H1",
    ) -> pd.DataFrame:
        """
        Gera dados com tendência clara para testes.
        """
        return self.generate_random_walk(
            start_price=start_price,
            bars=bars,
            volatility=noise,
            trend=trend_strength,
            start_date=start_date,
            timeframe=timeframe,
        )
    
    def generate_ranging(
        self,
        center_price: float = 100.0,
        bars: int = 1000,
        range_size: float = 0.05,
        start_date: Optional[datetime] = None,
        timeframe: str = "H1",
    ) -> pd.DataFrame:
        """
        Gera dados de mercado lateral para testes.
        """
        np.random.seed(42)
        
        # Gera preço oscilando em range
        t = np.linspace(0, 10 * np.pi, bars)
        base = center_price + center_price * range_size * np.sin(t)
        noise = np.random.normal(0, center_price * 0.005, bars)
        close = base + noise
        
        high = close * (1 + np.abs(np.random.normal(0, 0.005, bars)))
        low = close * (1 - np.abs(np.random.normal(0, 0.005, bars)))
        open_ = np.roll(close, 1)
        open_[0] = center_price
        
        high = np.maximum(high, np.maximum(open_, close))
        low = np.minimum(low, np.minimum(open_, close))
        
        volume = np.random.lognormal(10, 1, bars).astype(int)
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=bars)
        
        minutes = Timeframe.to_minutes(timeframe)
        timestamps = pd.date_range(start=start_date, periods=bars, freq=f'{minutes}min')
        
        df = pd.DataFrame({
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        }, index=timestamps)
        
        self.logger.info(f"Generated {bars} bars of ranging data")
        
        return df
    
    # ============================================================
    # INDICADORES
    # ============================================================
    
    @staticmethod
    def add_sma(df: pd.DataFrame, period: int, column: str = 'close') -> pd.DataFrame:
        """Adiciona SMA ao DataFrame."""
        df[f'sma_{period}'] = df[column].rolling(window=period).mean()
        return df
    
    @staticmethod
    def add_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.DataFrame:
        """Adiciona EMA ao DataFrame."""
        df[f'ema_{period}'] = df[column].ewm(span=period, adjust=False).mean()
        return df
    
    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.DataFrame:
        """Adiciona RSI ao DataFrame."""
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df
    
    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Adiciona ATR ao DataFrame."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=period).mean()
        return df
    
    @staticmethod
    def add_bollinger(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
        """Adiciona Bollinger Bands ao DataFrame."""
        sma = df['close'].rolling(window=period).mean()
        rolling_std = df['close'].rolling(window=period).std()
        df['bb_middle'] = sma
        df['bb_upper'] = sma + (rolling_std * std)
        df['bb_lower'] = sma - (rolling_std * std)
        return df
    
    @staticmethod
    def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Adiciona MACD ao DataFrame."""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        return df
