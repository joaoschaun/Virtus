"""
VIRTUS ML - Candlestick Image Transformer
==========================================

Transforma dados OHLCV em imagens de candlestick para Vision AI.
Suporta múltiplos estilos de renderização.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import io
import base64
import logging

# Conditional imports
try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import mplfinance as mpf
    HAS_MPLFINANCE = True
except ImportError:
    HAS_MPLFINANCE = False

logger = logging.getLogger(__name__)


@dataclass
class ImageConfig:
    """Configuração para geração de imagens."""
    width: int = 224
    height: int = 224
    lookback: int = 50
    include_volume: bool = True
    style: str = "candlestick"  # candlestick, line, ohlc
    background_color: str = "black"
    bull_color: str = "#00FF00"
    bear_color: str = "#FF0000"
    volume_alpha: float = 0.5
    dpi: int = 100


class CandlestickImageGenerator:
    """
    Transforma dados OHLCV em imagens de candlestick para Vision AI.
    
    Suporta:
    - Renderização via matplotlib/mplfinance
    - Renderização via PIL (mais rápida)
    - Múltiplos estilos (candlestick, line, ohlc)
    """
    
    def __init__(self, config: Optional[ImageConfig] = None):
        self.config = config or ImageConfig()
        self._validate_dependencies()
    
    def _validate_dependencies(self) -> None:
        """Valida dependências disponíveis."""
        if not HAS_PIL and not HAS_MATPLOTLIB:
            logger.warning("Nem PIL nem matplotlib disponíveis. Usando renderização básica.")
    
    def generate_image(
        self,
        df: pd.DataFrame,
        save_path: Optional[str] = None
    ) -> np.ndarray:
        """
        Gera imagem de candlestick.
        
        Args:
            df: DataFrame com OHLCV
            save_path: Caminho para salvar (opcional)
            
        Returns:
            Array numpy da imagem (H, W, C)
        """
        # Pega os últimos N candles
        df_window = df.tail(self.config.lookback).copy()
        
        if len(df_window) < 5:
            # Retorna imagem em branco se dados insuficientes
            return np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)
        
        # Escolhe método de renderização
        if HAS_MPLFINANCE and self.config.style == "candlestick":
            img_array = self._render_mplfinance(df_window)
        elif HAS_MATPLOTLIB:
            img_array = self._render_matplotlib(df_window)
        elif HAS_PIL:
            img_array = self._render_pil(df_window)
        else:
            img_array = self._render_basic(df_window)
        
        # Salva se solicitado
        if save_path and HAS_PIL:
            img = Image.fromarray(img_array)
            img.save(save_path)
        
        return img_array
    
    def _render_mplfinance(self, df: pd.DataFrame) -> np.ndarray:
        """Renderiza usando mplfinance (alta qualidade)."""
        
        # Prepara DataFrame para mplfinance (precisa de índice datetime)
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='H')
        
        # Renomeia colunas se necessário
        df = df.rename(columns={
            'open': 'Open', 'high': 'High', 
            'low': 'Low', 'close': 'Close',
            'volume': 'Volume', 'tick_volume': 'Volume'
        })
        
        # Estilo customizado
        mc = mpf.make_marketcolors(
            up=self.config.bull_color,
            down=self.config.bear_color,
            edge='inherit',
            wick='inherit',
            volume={'up': self.config.bull_color, 'down': self.config.bear_color}
        )
        
        style = mpf.make_mpf_style(
            marketcolors=mc,
            base_mpf_style='nightclouds' if self.config.background_color == 'black' else 'charles',
            rc={'axes.edgecolor': 'white' if self.config.background_color == 'black' else 'black'}
        )
        
        # Cria figura
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=style,
            returnfig=True,
            volume=self.config.include_volume and 'Volume' in df.columns,
            show_nontrading=False,
            figsize=(self.config.width/self.config.dpi, self.config.height/self.config.dpi),
            tight_layout=True
        )
        
        # Converte para array
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.config.dpi, 
                    bbox_inches='tight', pad_inches=0,
                    facecolor=self.config.background_color)
        buf.seek(0)
        
        img = Image.open(buf)
        img = img.resize((self.config.width, self.config.height), Image.LANCZOS)
        img_array = np.array(img)
        
        plt.close(fig)
        
        # Garante 3 canais
        if len(img_array.shape) == 2:
            img_array = np.stack([img_array] * 3, axis=-1)
        elif img_array.shape[-1] == 4:
            img_array = img_array[:, :, :3]
        
        return img_array
    
    def _render_matplotlib(self, df: pd.DataFrame) -> np.ndarray:
        """Renderiza usando matplotlib padrão."""
        
        fig, ax = plt.subplots(
            figsize=(self.config.width/self.config.dpi, 
                    self.config.height/self.config.dpi),
            dpi=self.config.dpi
        )
        
        fig.patch.set_facecolor(self.config.background_color)
        ax.set_facecolor(self.config.background_color)
        
        # Normaliza preços para o plot
        prices = df[['open', 'high', 'low', 'close']].values
        min_price = prices.min()
        max_price = prices.max()
        price_range = max_price - min_price
        if price_range == 0:
            price_range = 1
        
        # Área do chart
        chart_height = self.config.height * (0.8 if self.config.include_volume else 1.0)
        
        # Desenha candlesticks
        candle_width = max(1, (self.config.width - 20) / len(df) * 0.8)
        
        for i, (_, row) in enumerate(df.iterrows()):
            x = 10 + i * (self.config.width - 20) / len(df)
            
            o = (row['open'] - min_price) / price_range * chart_height
            h = (row['high'] - min_price) / price_range * chart_height
            l = (row['low'] - min_price) / price_range * chart_height
            c = (row['close'] - min_price) / price_range * chart_height
            
            color = self.config.bull_color if row['close'] >= row['open'] else self.config.bear_color
            
            # Corpo
            body_bottom = min(o, c)
            body_height = max(abs(c - o), 1)
            
            from matplotlib.patches import Rectangle
            rect = Rectangle(
                (x - candle_width/2, body_bottom),
                candle_width, body_height,
                facecolor=color, edgecolor=color
            )
            ax.add_patch(rect)
            
            # Sombras
            ax.plot([x, x], [l, body_bottom], color=color, linewidth=1)
            ax.plot([x, x], [body_bottom + body_height, h], color=color, linewidth=1)
        
        ax.axis('off')
        ax.set_xlim(0, self.config.width)
        ax.set_ylim(0, chart_height)
        
        # Converte para array
        fig.canvas.draw()
        img_array = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        img_array = img_array.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        
        plt.close(fig)
        
        # Redimensiona se necessário
        if img_array.shape[0] != self.config.height or img_array.shape[1] != self.config.width:
            img = Image.fromarray(img_array)
            img = img.resize((self.config.width, self.config.height), Image.LANCZOS)
            img_array = np.array(img)
        
        return img_array
    
    def _render_pil(self, df: pd.DataFrame) -> np.ndarray:
        """Renderiza usando PIL (mais rápido)."""
        
        # Cria imagem
        bg_color = (0, 0, 0) if self.config.background_color == 'black' else (255, 255, 255)
        img = Image.new('RGB', (self.config.width, self.config.height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Normaliza preços
        prices = df[['open', 'high', 'low', 'close']].values
        min_price = prices.min()
        max_price = prices.max()
        price_range = max_price - min_price if max_price != min_price else 1
        
        chart_height = self.config.height * 0.9
        margin_top = self.config.height * 0.05
        
        candle_width = max(1, (self.config.width - 20) / len(df) * 0.7)
        
        bull_rgb = tuple(int(self.config.bull_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        bear_rgb = tuple(int(self.config.bear_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        for i, (_, row) in enumerate(df.iterrows()):
            x = 10 + i * (self.config.width - 20) / len(df)
            
            # Normaliza para coordenadas de imagem (y invertido)
            o = margin_top + chart_height * (1 - (row['open'] - min_price) / price_range)
            h = margin_top + chart_height * (1 - (row['high'] - min_price) / price_range)
            l = margin_top + chart_height * (1 - (row['low'] - min_price) / price_range)
            c = margin_top + chart_height * (1 - (row['close'] - min_price) / price_range)
            
            color = bull_rgb if row['close'] >= row['open'] else bear_rgb
            
            # Sombra
            draw.line([(x, h), (x, l)], fill=color, width=1)
            
            # Corpo
            body_top = min(o, c)
            body_bottom = max(o, c)
            draw.rectangle(
                [x - candle_width/2, body_top, x + candle_width/2, body_bottom],
                fill=color, outline=color
            )
        
        return np.array(img)
    
    def _render_basic(self, df: pd.DataFrame) -> np.ndarray:
        """Renderização básica sem dependências."""
        
        img = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)
        
        if self.config.background_color != 'black':
            img.fill(255)
        
        prices = df['close'].values
        min_p = prices.min()
        max_p = prices.max()
        range_p = max_p - min_p if max_p != min_p else 1
        
        # Desenha linha
        for i in range(len(prices) - 1):
            x1 = int(i * self.config.width / len(prices))
            x2 = int((i + 1) * self.config.width / len(prices))
            y1 = int((1 - (prices[i] - min_p) / range_p) * self.config.height * 0.9 + self.config.height * 0.05)
            y2 = int((1 - (prices[i+1] - min_p) / range_p) * self.config.height * 0.9 + self.config.height * 0.05)
            
            color = [0, 255, 0] if prices[i+1] >= prices[i] else [255, 0, 0]
            self._draw_line(img, x1, y1, x2, y2, color)
        
        return img
    
    def _draw_line(
        self, 
        img: np.ndarray, 
        x1: int, y1: int, 
        x2: int, y2: int, 
        color: List[int]
    ) -> None:
        """Desenha linha (algoritmo de Bresenham)."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            if 0 <= x1 < img.shape[1] and 0 <= y1 < img.shape[0]:
                img[y1, x1] = color
            
            if x1 == x2 and y1 == y2:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
    
    def generate_batch(
        self,
        df: pd.DataFrame,
        stride: int = 1
    ) -> np.ndarray:
        """
        Gera múltiplas imagens com janela deslizante.
        
        Args:
            df: DataFrame completo
            stride: Passo da janela
            
        Returns:
            Array (N, H, W, C)
        """
        images = []
        
        for i in range(self.config.lookback, len(df), stride):
            df_window = df.iloc[i - self.config.lookback:i]
            img = self.generate_image(df_window)
            images.append(img)
        
        return np.array(images)
    
    def to_base64(self, img_array: np.ndarray) -> str:
        """Converte imagem para base64."""
        if not HAS_PIL:
            return ""
        
        img = Image.fromarray(img_array)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode()
    
    def generate_with_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str] = ['sma_20', 'bb_upper', 'bb_lower']
    ) -> np.ndarray:
        """
        Gera imagem com indicadores sobrepostos.
        
        Args:
            df: DataFrame com OHLCV e indicadores
            indicators: Lista de indicadores para plotar
        """
        if not HAS_MATPLOTLIB:
            return self.generate_image(df)
        
        df_window = df.tail(self.config.lookback).copy()
        
        fig, ax = plt.subplots(
            figsize=(self.config.width/self.config.dpi, 
                    self.config.height/self.config.dpi),
            dpi=self.config.dpi
        )
        
        fig.patch.set_facecolor(self.config.background_color)
        ax.set_facecolor(self.config.background_color)
        
        # Plot candlesticks primeiro
        # (código similar ao _render_matplotlib)
        prices = df_window[['open', 'high', 'low', 'close']].values
        min_price = prices.min()
        max_price = prices.max()
        
        # Plot indicadores
        x_vals = np.arange(len(df_window))
        colors = ['yellow', 'cyan', 'magenta', 'white', 'orange']
        
        for i, indicator in enumerate(indicators):
            if indicator in df_window.columns:
                y_vals = (df_window[indicator].values - min_price) / (max_price - min_price + 1e-10)
                ax.plot(x_vals, y_vals, color=colors[i % len(colors)], 
                       linewidth=1, alpha=0.8, label=indicator)
        
        ax.axis('off')
        ax.legend(loc='upper left', fontsize=6)
        
        # Converte
        fig.canvas.draw()
        img_array = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        img_array = img_array.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        
        plt.close(fig)
        
        return img_array
