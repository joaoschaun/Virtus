"""
VIRTUS ML - Feature Engineering
================================

Criação de features técnicas usando TA-Lib e features customizadas.
Integra com o sistema de análise técnica existente do VIRTUS.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

# Conditional TA-Lib import
try:
    import talib as ta
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False

logger = logging.getLogger(__name__)


class FeatureCategory(Enum):
    """Categorias de features."""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    PATTERN = "pattern"
    CUSTOM = "custom"


@dataclass
class FeatureConfig:
    """Configuração de feature engineering."""
    # Features técnicas
    sma_periods: List[int] = field(default_factory=lambda: [20, 50, 200])
    ema_periods: List[int] = field(default_factory=lambda: [12, 26, 50])
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    atr_period: int = 14
    adx_period: int = 14
    
    # Features customizadas
    include_patterns: bool = True
    include_custom: bool = True
    include_lagged: bool = True
    lag_periods: List[int] = field(default_factory=lambda: [1, 2, 3, 5, 10])
    
    # Normalização
    normalize: bool = True
    normalize_method: str = "minmax"  # minmax, zscore, robust


class TechnicalFeatureEngineer:
    """
    Cria features técnicas usando TA-Lib e features customizadas.
    
    Compatível com a análise técnica existente do VIRTUS.
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        self.feature_names: List[str] = []
        self.scalers: Dict[str, Tuple[float, float]] = {}
    
    def create_features(
        self,
        df: pd.DataFrame,
        include_ohlcv: bool = True
    ) -> pd.DataFrame:
        """
        Cria todas as features técnicas.
        
        Args:
            df: DataFrame com OHLCV
            include_ohlcv: Incluir colunas originais
            
        Returns:
            DataFrame com features adicionadas
        """
        df = df.copy()
        self.feature_names = []
        
        # OHLCV base
        if include_ohlcv:
            for col in ['open', 'high', 'low', 'close']:
                if col in df.columns:
                    self.feature_names.append(col)
            if 'volume' in df.columns or 'tick_volume' in df.columns:
                vol_col = 'volume' if 'volume' in df.columns else 'tick_volume'
                df['volume'] = df[vol_col]
                self.feature_names.append('volume')
        
        # Features de tendência
        df = self._add_trend_features(df)
        
        # Features de momentum
        df = self._add_momentum_features(df)
        
        # Features de volatilidade
        df = self._add_volatility_features(df)
        
        # Features de volume
        df = self._add_volume_features(df)
        
        # Padrões de candlestick
        if self.config.include_patterns:
            df = self._add_candlestick_patterns(df)
        
        # Features customizadas
        if self.config.include_custom:
            df = self._add_custom_features(df)
        
        # Features com lag
        if self.config.include_lagged:
            df = self._add_lagged_features(df)
        
        # Remove NaN
        df = df.fillna(method='ffill').fillna(0)
        
        return df
    
    def _add_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features de tendência."""
        close = df['close'].values
        
        # SMAs
        for period in self.config.sma_periods:
            col_name = f'sma_{period}'
            if HAS_TALIB:
                df[col_name] = ta.SMA(close, timeperiod=period)
            else:
                df[col_name] = df['close'].rolling(period).mean()
            self.feature_names.append(col_name)
        
        # EMAs
        for period in self.config.ema_periods:
            col_name = f'ema_{period}'
            if HAS_TALIB:
                df[col_name] = ta.EMA(close, timeperiod=period)
            else:
                df[col_name] = df['close'].ewm(span=period).mean()
            self.feature_names.append(col_name)
        
        # ADX
        if HAS_TALIB and 'high' in df.columns and 'low' in df.columns:
            df['adx'] = ta.ADX(
                df['high'].values, 
                df['low'].values, 
                close, 
                timeperiod=self.config.adx_period
            )
            df['plus_di'] = ta.PLUS_DI(
                df['high'].values, 
                df['low'].values, 
                close, 
                timeperiod=self.config.adx_period
            )
            df['minus_di'] = ta.MINUS_DI(
                df['high'].values, 
                df['low'].values, 
                close, 
                timeperiod=self.config.adx_period
            )
            self.feature_names.extend(['adx', 'plus_di', 'minus_di'])
        
        return df
    
    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features de momentum."""
        close = df['close'].values
        
        # RSI
        if HAS_TALIB:
            df['rsi'] = ta.RSI(close, timeperiod=self.config.rsi_period)
        else:
            df['rsi'] = self._calculate_rsi(close, self.config.rsi_period)
        self.feature_names.append('rsi')
        
        # MACD
        if HAS_TALIB:
            df['macd'], df['macd_signal'], df['macd_hist'] = ta.MACD(
                close,
                fastperiod=self.config.macd_fast,
                slowperiod=self.config.macd_slow,
                signalperiod=self.config.macd_signal
            )
        else:
            macd, signal, hist = self._calculate_macd(close)
            df['macd'] = macd
            df['macd_signal'] = signal
            df['macd_hist'] = hist
        self.feature_names.extend(['macd', 'macd_signal', 'macd_hist'])
        
        # Stochastic
        if HAS_TALIB and 'high' in df.columns and 'low' in df.columns:
            df['stoch_k'], df['stoch_d'] = ta.STOCH(
                df['high'].values,
                df['low'].values,
                close,
                fastk_period=14,
                slowk_period=3,
                slowd_period=3
            )
            self.feature_names.extend(['stoch_k', 'stoch_d'])
        
        # CCI
        if HAS_TALIB and 'high' in df.columns and 'low' in df.columns:
            df['cci'] = ta.CCI(
                df['high'].values,
                df['low'].values,
                close,
                timeperiod=20
            )
            self.feature_names.append('cci')
        
        # Williams %R
        if HAS_TALIB and 'high' in df.columns and 'low' in df.columns:
            df['willr'] = ta.WILLR(
                df['high'].values,
                df['low'].values,
                close,
                timeperiod=14
            )
            self.feature_names.append('willr')
        
        # ROC
        if HAS_TALIB:
            df['roc'] = ta.ROC(close, timeperiod=10)
        else:
            df['roc'] = df['close'].pct_change(10) * 100
        self.feature_names.append('roc')
        
        return df
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features de volatilidade."""
        close = df['close'].values
        high = df['high'].values if 'high' in df.columns else close
        low = df['low'].values if 'low' in df.columns else close
        
        # ATR
        if HAS_TALIB:
            df['atr'] = ta.ATR(high, low, close, timeperiod=self.config.atr_period)
        else:
            df['atr'] = self._calculate_atr(high, low, close, self.config.atr_period)
        self.feature_names.append('atr')
        
        # Bollinger Bands
        if HAS_TALIB:
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = ta.BBANDS(
                close,
                timeperiod=self.config.bb_period,
                nbdevup=self.config.bb_std,
                nbdevdn=self.config.bb_std
            )
        else:
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger(
                close, self.config.bb_period, self.config.bb_std
            )
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
        self.feature_names.extend(['bb_upper', 'bb_middle', 'bb_lower'])
        
        # Bollinger Band Width
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        self.feature_names.append('bb_width')
        
        # Bollinger %B
        df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10)
        self.feature_names.append('bb_pct')
        
        # Volatility (rolling std)
        df['volatility_5'] = df['close'].pct_change().rolling(5).std()
        df['volatility_20'] = df['close'].pct_change().rolling(20).std()
        self.feature_names.extend(['volatility_5', 'volatility_20'])
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features de volume."""
        if 'volume' not in df.columns:
            return df
        
        volume = df['volume'].values
        close = df['close'].values
        
        # Volume SMA
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / (df['volume_sma_20'] + 1e-10)
        self.feature_names.extend(['volume_sma_20', 'volume_ratio'])
        
        # OBV
        if HAS_TALIB:
            df['obv'] = ta.OBV(close, volume)
        else:
            df['obv'] = self._calculate_obv(close, volume)
        self.feature_names.append('obv')
        
        # Money Flow Index
        if HAS_TALIB and 'high' in df.columns and 'low' in df.columns:
            df['mfi'] = ta.MFI(
                df['high'].values,
                df['low'].values,
                close,
                volume,
                timeperiod=14
            )
            self.feature_names.append('mfi')
        
        # Volume Price Trend
        df['vpt'] = (df['close'].pct_change() * df['volume']).cumsum()
        self.feature_names.append('vpt')
        
        return df
    
    def _add_candlestick_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona padrões de candlestick do TA-Lib."""
        if not HAS_TALIB:
            return df
        
        o = df['open'].values
        h = df['high'].values
        l = df['low'].values
        c = df['close'].values
        
        # Padrões de alta
        patterns_bullish = {
            'pattern_hammer': ta.CDLHAMMER,
            'pattern_inverted_hammer': ta.CDLINVERTEDHAMMER,
            'pattern_morning_star': ta.CDLMORNINGSTAR,
            'pattern_three_white_soldiers': ta.CDL3WHITESOLDIERS,
            'pattern_engulfing_bullish': lambda o, h, l, c: np.where(
                ta.CDLENGULFING(o, h, l, c) > 0, 
                ta.CDLENGULFING(o, h, l, c), 
                0
            ),
            'pattern_piercing': ta.CDLPIERCING,
        }
        
        # Padrões de baixa
        patterns_bearish = {
            'pattern_shooting_star': ta.CDLSHOOTINGSTAR,
            'pattern_hanging_man': ta.CDLHANGINGMAN,
            'pattern_evening_star': ta.CDLEVENINGSTAR,
            'pattern_three_black_crows': ta.CDL3BLACKCROWS,
            'pattern_engulfing_bearish': lambda o, h, l, c: np.where(
                ta.CDLENGULFING(o, h, l, c) < 0, 
                ta.CDLENGULFING(o, h, l, c), 
                0
            ),
            'pattern_dark_cloud': ta.CDLDARKCLOUDCOVER,
        }
        
        # Padrões neutros
        patterns_neutral = {
            'pattern_doji': ta.CDLDOJI,
            'pattern_spinning_top': ta.CDLSPINNINGTOP,
            'pattern_harami': ta.CDLHARAMI,
        }
        
        # Aplica todos os padrões
        for name, func in {**patterns_bullish, **patterns_bearish, **patterns_neutral}.items():
            try:
                df[name] = func(o, h, l, c)
                self.feature_names.append(name)
            except Exception as e:
                logger.debug(f"Erro ao calcular padrão {name}: {e}")
        
        return df
    
    def _add_custom_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features customizadas."""
        
        # Body/Shadow ratios
        body_size = abs(df['close'] - df['open'])
        total_range = df['high'] - df['low'] + 1e-10
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        
        df['body_ratio'] = body_size / total_range
        df['upper_shadow_ratio'] = upper_shadow / total_range
        df['lower_shadow_ratio'] = lower_shadow / total_range
        df['body_shadow_ratio'] = body_size / (upper_shadow + lower_shadow + 1e-10)
        self.feature_names.extend([
            'body_ratio', 'upper_shadow_ratio', 
            'lower_shadow_ratio', 'body_shadow_ratio'
        ])
        
        # Price position
        df['price_position'] = (df['close'] - df['low']) / total_range
        self.feature_names.append('price_position')
        
        # Returns
        df['return_1'] = df['close'].pct_change(1)
        df['return_5'] = df['close'].pct_change(5)
        df['return_10'] = df['close'].pct_change(10)
        self.feature_names.extend(['return_1', 'return_5', 'return_10'])
        
        # Gap
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        self.feature_names.append('gap')
        
        # Range
        df['range_pct'] = (df['high'] - df['low']) / df['close']
        self.feature_names.append('range_pct')
        
        # Candle direction
        df['bullish'] = (df['close'] > df['open']).astype(int)
        self.feature_names.append('bullish')
        
        # Consecutive same direction
        df['same_direction'] = (
            df['bullish'] == df['bullish'].shift(1)
        ).astype(int).rolling(5).sum()
        self.feature_names.append('same_direction')
        
        return df
    
    def _add_lagged_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona features com lag temporal."""
        base_features = ['close', 'return_1', 'rsi', 'macd_hist']
        
        for feature in base_features:
            if feature not in df.columns:
                continue
            for lag in self.config.lag_periods:
                col_name = f'{feature}_lag_{lag}'
                df[col_name] = df[feature].shift(lag)
                self.feature_names.append(col_name)
        
        return df
    
    # =====================================================
    # Cálculos fallback (sem TA-Lib)
    # =====================================================
    
    def _calculate_rsi(self, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Calcula RSI sem TA-Lib."""
        delta = np.diff(close, prepend=close[0])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = pd.Series(gain).rolling(period).mean().values
        avg_loss = pd.Series(loss).rolling(period).mean().values
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(
        self, 
        close: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calcula MACD sem TA-Lib."""
        close_series = pd.Series(close)
        ema_fast = close_series.ewm(span=fast).mean()
        ema_slow = close_series.ewm(span=slow).mean()
        
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_hist = macd - macd_signal
        
        return macd.values, macd_signal.values, macd_hist.values
    
    def _calculate_atr(
        self, 
        high: np.ndarray, 
        low: np.ndarray, 
        close: np.ndarray, 
        period: int = 14
    ) -> np.ndarray:
        """Calcula ATR sem TA-Lib."""
        tr = np.zeros(len(high))
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(high)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        return pd.Series(tr).rolling(period).mean().values
    
    def _calculate_bollinger(
        self, 
        close: np.ndarray, 
        period: int = 20, 
        std: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calcula Bollinger Bands sem TA-Lib."""
        close_series = pd.Series(close)
        middle = close_series.rolling(period).mean()
        rolling_std = close_series.rolling(period).std()
        
        upper = middle + (rolling_std * std)
        lower = middle - (rolling_std * std)
        
        return upper.values, middle.values, lower.values
    
    def _calculate_obv(self, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Calcula OBV sem TA-Lib."""
        obv = np.zeros(len(close))
        
        for i in range(1, len(close)):
            if close[i] > close[i-1]:
                obv[i] = obv[i-1] + volume[i]
            elif close[i] < close[i-1]:
                obv[i] = obv[i-1] - volume[i]
            else:
                obv[i] = obv[i-1]
        
        return obv
    
    def get_feature_names(self) -> List[str]:
        """Retorna lista de nomes das features criadas."""
        return self.feature_names.copy()
    
    def get_feature_importance(
        self, 
        X: np.ndarray, 
        y: np.ndarray, 
        method: str = "mutual_info"
    ) -> Dict[str, float]:
        """
        Calcula importância das features.
        
        Args:
            X: Features
            y: Labels
            method: Método (mutual_info, correlation)
        """
        from sklearn.feature_selection import mutual_info_classif
        
        if method == "mutual_info":
            importance = mutual_info_classif(X, y, random_state=42)
        else:
            # Correlação
            importance = np.abs(np.corrcoef(X.T, y)[-1, :-1])
        
        return dict(zip(self.feature_names, importance))
