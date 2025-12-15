"""
VIRTUS Vision AI - Chart Pattern Analysis via Computer Vision
==============================================================

Sistema de Visão Computacional para análise de gráficos financeiros.

Features:
- Conversão de dados OHLC para imagens de gráficos
- CNN para reconhecimento de padrões visuais
- Transfer Learning com modelos pré-treinados
- Detecção de formações gráficas (H&S, Triangles, etc.)
- Análise de tendências visuais

Padrões Visuais Detectados:
- Head & Shoulders (H&S)
- Inverse Head & Shoulders
- Double Top / Double Bottom
- Triangles (Ascending, Descending, Symmetric)
- Wedges (Rising, Falling)
- Flags and Pennants
- Channels (Ascending, Descending)
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
import io
import base64
from collections import Counter
from typing import TYPE_CHECKING

# Conditional imports
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, Model
    from tensorflow.keras.applications import MobileNetV2, ResNet50V2
    from tensorflow.keras.preprocessing.image import img_to_array
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    # Dummy para type hints
    Model = object
    layers = None

try:
    import torch
    import torch.nn as nn
    import torchvision.models as models
    import torchvision.transforms as transforms
    HAS_PYTORCH = True
except ImportError:
    HAS_PYTORCH = False
    # Módulo dummy para evitar erros de type hints
    class _DummyNN:
        Module = object
    nn = _DummyNN()
    torch = None
    models = None
    transforms = None

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None


class ChartPatternType(Enum):
    """Tipos de padrões gráficos."""
    # Reversal Patterns
    HEAD_SHOULDERS = "head_shoulders"
    INV_HEAD_SHOULDERS = "inv_head_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIPLE_TOP = "triple_top"
    TRIPLE_BOTTOM = "triple_bottom"
    ROUNDING_TOP = "rounding_top"
    ROUNDING_BOTTOM = "rounding_bottom"
    
    # Continuation Patterns
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRIC_TRIANGLE = "symmetric_triangle"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    PENNANT = "pennant"
    
    # Channel Patterns
    ASCENDING_CHANNEL = "ascending_channel"
    DESCENDING_CHANNEL = "descending_channel"
    HORIZONTAL_CHANNEL = "horizontal_channel"
    
    # Trend Patterns
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"
    
    # Unknown
    UNKNOWN = "unknown"


class PatternBias(Enum):
    """Viés do padrão."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class ChartImage:
    """Representação de um gráfico como imagem."""
    data: np.ndarray              # Imagem como array (H, W, C)
    width: int
    height: int
    channels: int = 3
    symbol: str = ""
    timeframe: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_base64(self) -> str:
        """Converte para base64."""
        if not HAS_PIL:
            return ""
        img = Image.fromarray((self.data * 255).astype(np.uint8))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()


@dataclass
class PatternDetection:
    """Detecção de padrão visual."""
    pattern_type: ChartPatternType
    bias: PatternBias
    confidence: float             # 0.0 - 1.0
    bounding_box: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    probability_completion: float = 0.5
    time_to_completion: Optional[int] = None  # Candles estimados
    features: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern': self.pattern_type.value,
            'bias': self.bias.value,
            'confidence': round(self.confidence, 4),
            'bounding_box': self.bounding_box,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss,
            'probability': round(self.probability_completion, 4),
            'candles_to_completion': self.time_to_completion,
            'timestamp': self.timestamp.isoformat(),
        }


class ChartRenderer:
    """
    Renderiza dados OHLC como imagens de gráficos.
    """
    
    def __init__(
        self,
        width: int = 224,
        height: int = 224,
        style: str = 'candlestick',  # 'candlestick', 'line', 'ohlc'
        include_volume: bool = True,
        background_color: str = 'black',
    ):
        self.width = width
        self.height = height
        self.style = style
        self.include_volume = include_volume
        self.background_color = background_color
    
    def render_candlestick(
        self,
        df,  # DataFrame com OHLCV
        symbol: str = "",
        timeframe: str = "",
    ) -> ChartImage:
        """
        Renderiza gráfico de candlestick.
        
        Args:
            df: DataFrame com open, high, low, close, volume
            
        Returns:
            ChartImage com o gráfico renderizado
        """
        if not HAS_MATPLOTLIB:
            return self._render_simple(df, symbol, timeframe)
        
        # Configuração do gráfico
        fig, ax = plt.subplots(figsize=(self.width/72, self.height/72), dpi=72)
        fig.patch.set_facecolor(self.background_color)
        ax.set_facecolor(self.background_color)
        
        # Normaliza preços
        prices = df[['open', 'high', 'low', 'close']].values
        min_price = prices.min()
        max_price = prices.max()
        price_range = max_price - min_price
        if price_range == 0:
            price_range = 1
        
        # Área do gráfico
        chart_height = self.height * 0.8 if self.include_volume else self.height
        
        # Desenha candlesticks
        candle_width = max(1, (self.width - 20) / len(df) * 0.8)
        
        for i, (_, row) in enumerate(df.iterrows()):
            x = 10 + i * (self.width - 20) / len(df)
            
            o, h, l, c = row['open'], row['high'], row['low'], row['close']
            
            # Normaliza
            o_norm = (o - min_price) / price_range * chart_height
            h_norm = (h - min_price) / price_range * chart_height
            l_norm = (l - min_price) / price_range * chart_height
            c_norm = (c - min_price) / price_range * chart_height
            
            color = 'green' if c >= o else 'red'
            
            # Corpo
            body_bottom = min(o_norm, c_norm)
            body_height = max(abs(c_norm - o_norm), 1)
            rect = Rectangle((x - candle_width/2, body_bottom), 
                            candle_width, body_height, 
                            facecolor=color, edgecolor=color)
            ax.add_patch(rect)
            
            # Sombras
            ax.plot([x, x], [l_norm, body_bottom], color=color, linewidth=1)
            ax.plot([x, x], [body_bottom + body_height, h_norm], color=color, linewidth=1)
        
        # Volume (se habilitado)
        if self.include_volume and 'volume' in df.columns:
            vol_height = self.height * 0.15
            max_vol = df['volume'].max()
            if max_vol == 0:
                max_vol = 1
            
            for i, (_, row) in enumerate(df.iterrows()):
                x = 10 + i * (self.width - 20) / len(df)
                v = row['volume'] / max_vol * vol_height
                c = row['close']
                o = row['open']
                color = 'green' if c >= o else 'red'
                
                rect = Rectangle((x - candle_width/2, -vol_height), 
                                candle_width, v, 
                                facecolor=color, alpha=0.5)
                ax.add_patch(rect)
        
        ax.axis('off')
        ax.set_xlim(0, self.width)
        ax.set_ylim(-self.height * 0.2 if self.include_volume else 0, chart_height)
        
        # Converte para array
        fig.canvas.draw()
        img_array = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        img_array = img_array.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        
        plt.close(fig)
        
        # Normaliza para 0-1
        img_array = img_array.astype(np.float32) / 255.0
        
        # Redimensiona se necessário
        if img_array.shape[0] != self.height or img_array.shape[1] != self.width:
            img_array = self._resize_image(img_array)
        
        return ChartImage(
            data=img_array,
            width=self.width,
            height=self.height,
            symbol=symbol,
            timeframe=timeframe,
            start_time=df.index[0] if hasattr(df.index, '__iter__') else None,
            end_time=df.index[-1] if hasattr(df.index, '__iter__') else None,
        )
    
    def _render_simple(
        self,
        df,
        symbol: str = "",
        timeframe: str = "",
    ) -> ChartImage:
        """Renderização simples sem matplotlib."""
        
        img = np.zeros((self.height, self.width, 3), dtype=np.float32)
        
        if len(df) == 0:
            return ChartImage(
                data=img, width=self.width, height=self.height,
                symbol=symbol, timeframe=timeframe
            )
        
        prices = df['close'].values
        min_p = prices.min()
        max_p = prices.max()
        range_p = max_p - min_p if max_p != min_p else 1
        
        # Normaliza e desenha linha
        for i in range(len(prices) - 1):
            x1 = int(i * self.width / len(prices))
            x2 = int((i + 1) * self.width / len(prices))
            y1 = int((1 - (prices[i] - min_p) / range_p) * self.height * 0.9 + self.height * 0.05)
            y2 = int((1 - (prices[i+1] - min_p) / range_p) * self.height * 0.9 + self.height * 0.05)
            
            # Cor baseada na direção
            color = [0, 1, 0] if prices[i+1] >= prices[i] else [1, 0, 0]
            
            # Desenha linha (simples)
            self._draw_line(img, x1, y1, x2, y2, color)
        
        return ChartImage(
            data=img, width=self.width, height=self.height,
            symbol=symbol, timeframe=timeframe
        )
    
    def _draw_line(self, img: np.ndarray, x1: int, y1: int, x2: int, y2: int, color: List[float]) -> None:
        """Desenha linha simples (Bresenham)."""
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
    
    def _resize_image(self, img: np.ndarray) -> np.ndarray:
        """Redimensiona imagem."""
        if HAS_PIL:
            pil_img = Image.fromarray((img * 255).astype(np.uint8))
            pil_img = pil_img.resize((self.width, self.height), Image.LANCZOS)
            return np.array(pil_img).astype(np.float32) / 255.0
        
        # Resize simples sem PIL
        h, w = img.shape[:2]
        new_img = np.zeros((self.height, self.width, 3), dtype=np.float32)
        
        for y in range(self.height):
            for x in range(self.width):
                src_y = int(y * h / self.height)
                src_x = int(x * w / self.width)
                new_img[y, x] = img[src_y, src_x]
        
        return new_img


class TensorFlowVisionModel:
    """
    Modelo de visão computacional com TensorFlow/Keras.
    """
    
    def __init__(
        self,
        input_shape: Tuple[int, int, int] = (224, 224, 3),
        num_classes: int = len(ChartPatternType),
        backbone: str = 'mobilenet',  # 'mobilenet', 'resnet'
        pretrained: bool = True,
    ):
        if not HAS_TENSORFLOW:
            raise ImportError("TensorFlow não disponível")
        
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.backbone_name = backbone
        self.pretrained = pretrained
        
        self.model = None
        self.class_names = [p.value for p in ChartPatternType]
    
    def build_model(self) -> Model:
        """Constrói o modelo CNN."""
        
        # Backbone pré-treinado
        if self.backbone_name == 'mobilenet':
            base_model = MobileNetV2(
                input_shape=self.input_shape,
                include_top=False,
                weights='imagenet' if self.pretrained else None,
            )
        elif self.backbone_name == 'resnet':
            base_model = ResNet50V2(
                input_shape=self.input_shape,
                include_top=False,
                weights='imagenet' if self.pretrained else None,
            )
        else:
            # Custom CNN
            return self._build_custom_cnn()
        
        # Congela base inicialmente
        base_model.trainable = False
        
        # Cabeça de classificação
        inputs = keras.Input(shape=self.input_shape)
        x = base_model(inputs, training=False)
        x = layers.GlobalAveragePooling2D()(x)
        x = layers.Dropout(0.3)(x)
        x = layers.Dense(256, activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(0.3)(x)
        x = layers.Dense(128, activation='relu')(x)
        
        # Saídas múltiplas
        pattern_output = layers.Dense(
            self.num_classes, 
            activation='softmax', 
            name='pattern'
        )(x)
        
        bias_output = layers.Dense(
            3,  # bullish, bearish, neutral
            activation='softmax',
            name='bias'
        )(x)
        
        confidence_output = layers.Dense(
            1, 
            activation='sigmoid', 
            name='confidence'
        )(x)
        
        self.model = Model(
            inputs=inputs,
            outputs=[pattern_output, bias_output, confidence_output]
        )
        
        return self.model
    
    def _build_custom_cnn(self) -> Model:
        """Constrói CNN customizada."""
        
        inputs = keras.Input(shape=self.input_shape)
        
        # Bloco 1
        x = layers.Conv2D(32, 3, padding='same', activation='relu')(inputs)
        x = layers.BatchNormalization()(x)
        x = layers.Conv2D(32, 3, padding='same', activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D(2)(x)
        x = layers.Dropout(0.25)(x)
        
        # Bloco 2
        x = layers.Conv2D(64, 3, padding='same', activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Conv2D(64, 3, padding='same', activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D(2)(x)
        x = layers.Dropout(0.25)(x)
        
        # Bloco 3
        x = layers.Conv2D(128, 3, padding='same', activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Conv2D(128, 3, padding='same', activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D(2)(x)
        x = layers.Dropout(0.25)(x)
        
        # Bloco 4
        x = layers.Conv2D(256, 3, padding='same', activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.GlobalAveragePooling2D()(x)
        
        # Dense layers
        x = layers.Dense(256, activation='relu')(x)
        x = layers.Dropout(0.5)(x)
        x = layers.Dense(128, activation='relu')(x)
        x = layers.Dropout(0.3)(x)
        
        # Saídas
        pattern_output = layers.Dense(
            self.num_classes, 
            activation='softmax', 
            name='pattern'
        )(x)
        
        bias_output = layers.Dense(
            3, 
            activation='softmax', 
            name='bias'
        )(x)
        
        confidence_output = layers.Dense(
            1, 
            activation='sigmoid', 
            name='confidence'
        )(x)
        
        return Model(
            inputs=inputs,
            outputs=[pattern_output, bias_output, confidence_output]
        )
    
    def compile_model(
        self,
        learning_rate: float = 0.001,
    ) -> None:
        """Compila o modelo."""
        if self.model is None:
            self.build_model()
        
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss={
                'pattern': 'categorical_crossentropy',
                'bias': 'categorical_crossentropy',
                'confidence': 'binary_crossentropy',
            },
            loss_weights={
                'pattern': 1.0,
                'bias': 0.5,
                'confidence': 0.3,
            },
            metrics={
                'pattern': ['accuracy'],
                'bias': ['accuracy'],
            }
        )
    
    def predict(self, images: np.ndarray) -> List[Dict[str, Any]]:
        """
        Faz predição em imagens.
        
        Args:
            images: Array de imagens (N, H, W, C)
            
        Returns:
            Lista de predições
        """
        if self.model is None:
            self.build_model()
            self.compile_model()
        
        # Garante formato correto
        if len(images.shape) == 3:
            images = np.expand_dims(images, 0)
        
        # Predição
        pattern_probs, bias_probs, confidences = self.model.predict(images, verbose=0)
        
        results = []
        for i in range(len(images)):
            pattern_idx = np.argmax(pattern_probs[i])
            bias_idx = np.argmax(bias_probs[i])
            
            results.append({
                'pattern': self.class_names[pattern_idx],
                'pattern_confidence': float(pattern_probs[i][pattern_idx]),
                'bias': ['bullish', 'bearish', 'neutral'][bias_idx],
                'bias_confidence': float(bias_probs[i][bias_idx]),
                'overall_confidence': float(confidences[i][0]),
                'all_pattern_probs': {
                    self.class_names[j]: float(pattern_probs[i][j])
                    for j in range(len(self.class_names))
                }
            })
        
        return results


class PyTorchVisionModel:
    """
    Modelo de visão computacional com PyTorch.
    """
    
    def __init__(
        self,
        input_size: int = 224,
        num_classes: int = len(ChartPatternType),
        backbone: str = 'mobilenet',
        pretrained: bool = True,
    ):
        if not HAS_PYTORCH:
            raise ImportError("PyTorch não disponível")
        
        self.input_size = input_size
        self.num_classes = num_classes
        self.backbone_name = backbone
        self.pretrained = pretrained
        
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.class_names = [p.value for p in ChartPatternType]
        
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
        ])
    
    def build_model(self) -> nn.Module:
        """Constrói o modelo."""
        
        class ChartPatternNet(nn.Module):
            def __init__(self, backbone, num_classes, pretrained):
                super().__init__()
                
                # Backbone
                if backbone == 'mobilenet':
                    self.backbone = models.mobilenet_v2(pretrained=pretrained)
                    in_features = self.backbone.classifier[1].in_features
                    self.backbone.classifier = nn.Identity()
                elif backbone == 'resnet':
                    self.backbone = models.resnet50(pretrained=pretrained)
                    in_features = self.backbone.fc.in_features
                    self.backbone.fc = nn.Identity()
                else:
                    # Custom backbone
                    self.backbone = self._build_custom(num_classes)
                    return
                
                # Heads
                self.pattern_head = nn.Sequential(
                    nn.Linear(in_features, 256),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(256, num_classes),
                )
                
                self.bias_head = nn.Sequential(
                    nn.Linear(in_features, 64),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    nn.Linear(64, 3),
                )
                
                self.confidence_head = nn.Sequential(
                    nn.Linear(in_features, 32),
                    nn.ReLU(),
                    nn.Linear(32, 1),
                    nn.Sigmoid(),
                )
            
            def _build_custom(self, num_classes):
                return nn.Sequential(
                    nn.Conv2d(3, 32, 3, padding=1),
                    nn.BatchNorm2d(32),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.Conv2d(32, 64, 3, padding=1),
                    nn.BatchNorm2d(64),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.Conv2d(64, 128, 3, padding=1),
                    nn.BatchNorm2d(128),
                    nn.ReLU(),
                    nn.AdaptiveAvgPool2d(1),
                    nn.Flatten(),
                    nn.Linear(128, num_classes),
                )
            
            def forward(self, x):
                features = self.backbone(x)
                
                pattern = self.pattern_head(features)
                bias = self.bias_head(features)
                confidence = self.confidence_head(features)
                
                return pattern, bias, confidence
        
        self.model = ChartPatternNet(
            self.backbone_name, 
            self.num_classes, 
            self.pretrained
        ).to(self.device)
        
        return self.model
    
    def predict(self, images: np.ndarray) -> List[Dict[str, Any]]:
        """Faz predição."""
        if self.model is None:
            self.build_model()
        
        self.model.eval()
        
        # Prepara batch
        if len(images.shape) == 3:
            images = np.expand_dims(images, 0)
        
        batch = []
        for img in images:
            img_uint8 = (img * 255).astype(np.uint8)
            tensor = self.transform(img_uint8)
            batch.append(tensor)
        
        batch = torch.stack(batch).to(self.device)
        
        with torch.no_grad():
            pattern_logits, bias_logits, confidences = self.model(batch)
            
            pattern_probs = torch.softmax(pattern_logits, dim=1).cpu().numpy()
            bias_probs = torch.softmax(bias_logits, dim=1).cpu().numpy()
            confidences = confidences.cpu().numpy()
        
        results = []
        for i in range(len(images)):
            pattern_idx = np.argmax(pattern_probs[i])
            bias_idx = np.argmax(bias_probs[i])
            
            results.append({
                'pattern': self.class_names[pattern_idx],
                'pattern_confidence': float(pattern_probs[i][pattern_idx]),
                'bias': ['bullish', 'bearish', 'neutral'][bias_idx],
                'bias_confidence': float(bias_probs[i][bias_idx]),
                'overall_confidence': float(confidences[i][0]),
            })
        
        return results


class VirtusVisionAnalyzer:
    """
    Analisador principal de visão computacional para VIRTUS.
    
    Integra:
    - Renderização de gráficos
    - CNN para detecção de padrões
    - Análise de múltiplos timeframes
    - Ensemble de modelos
    """
    
    def __init__(
        self,
        image_size: int = 224,
        use_tensorflow: bool = True,
        use_pytorch: bool = False,
        backbone: str = 'mobilenet',
    ):
        self.image_size = image_size
        
        # Renderer
        self.renderer = ChartRenderer(
            width=image_size,
            height=image_size,
            include_volume=True,
        )
        
        # Modelos
        self.models = []
        
        if use_tensorflow and HAS_TENSORFLOW:
            tf_model = TensorFlowVisionModel(
                input_shape=(image_size, image_size, 3),
                backbone=backbone,
            )
            tf_model.build_model()
            tf_model.compile_model()
            self.models.append(('tensorflow', tf_model))
        
        if use_pytorch and HAS_PYTORCH:
            pt_model = PyTorchVisionModel(
                input_size=image_size,
                backbone=backbone,
            )
            pt_model.build_model()
            self.models.append(('pytorch', pt_model))
        
        # Histórico
        self.analysis_history: List[PatternDetection] = []
        
        # Estatísticas
        self.stats = {
            'total_analyses': 0,
            'patterns_detected': Counter(),
            'by_bias': Counter(),
        }
    
    def analyze_chart(
        self,
        df,  # DataFrame OHLCV
        symbol: str = "",
        timeframe: str = "",
        min_confidence: float = 0.3,
    ) -> List[PatternDetection]:
        """
        Analisa gráfico para detectar padrões.
        
        Args:
            df: DataFrame com OHLCV
            symbol: Símbolo do ativo
            timeframe: Timeframe dos dados
            min_confidence: Confiança mínima
            
        Returns:
            Lista de padrões detectados
        """
        self.stats['total_analyses'] += 1
        
        if len(df) < 10:
            return []
        
        # Renderiza gráfico
        chart_image = self.renderer.render_candlestick(df, symbol, timeframe)
        
        # Ensemble de predições
        all_predictions = []
        
        for name, model in self.models:
            try:
                predictions = model.predict(chart_image.data)
                all_predictions.append((name, predictions[0]))
            except Exception as e:
                print(f"Erro no modelo {name}: {e}")
        
        if not all_predictions:
            # Análise heurística se modelos falharem
            return self._heuristic_analysis(df, symbol)
        
        # Combina predições
        combined = self._combine_predictions(all_predictions)
        
        # Converte para detecções
        detections = []
        
        if combined['pattern_confidence'] >= min_confidence:
            pattern_type = ChartPatternType(combined['pattern'])
            bias = PatternBias(combined['bias'])
            
            # Calcula targets
            target, stop = self._calculate_targets(df, pattern_type, bias)
            
            detection = PatternDetection(
                pattern_type=pattern_type,
                bias=bias,
                confidence=combined['pattern_confidence'],
                bounding_box=(0, 0, self.image_size, self.image_size),
                target_price=target,
                stop_loss=stop,
                probability_completion=combined.get('overall_confidence', 0.5),
                features=combined.get('all_pattern_probs', {}),
            )
            
            detections.append(detection)
            
            # Atualiza stats
            self.stats['patterns_detected'][pattern_type.value] += 1
            self.stats['by_bias'][bias.value] += 1
        
        # Histórico
        self.analysis_history.extend(detections)
        
        return detections
    
    def _combine_predictions(
        self,
        predictions: List[Tuple[str, Dict]]
    ) -> Dict[str, Any]:
        """Combina predições de múltiplos modelos."""
        
        if len(predictions) == 1:
            return predictions[0][1]
        
        # Média ponderada
        pattern_votes = Counter()
        bias_votes = Counter()
        total_confidence = 0
        
        for name, pred in predictions:
            weight = 1.0  # Pode ser ajustado por modelo
            pattern_votes[pred['pattern']] += pred['pattern_confidence'] * weight
            bias_votes[pred['bias']] += pred['bias_confidence'] * weight
            total_confidence += pred.get('overall_confidence', 0.5) * weight
        
        top_pattern = pattern_votes.most_common(1)[0]
        top_bias = bias_votes.most_common(1)[0]
        
        return {
            'pattern': top_pattern[0],
            'pattern_confidence': top_pattern[1] / len(predictions),
            'bias': top_bias[0],
            'bias_confidence': top_bias[1] / len(predictions),
            'overall_confidence': total_confidence / len(predictions),
        }
    
    def _calculate_targets(
        self,
        df,
        pattern_type: ChartPatternType,
        bias: PatternBias,
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calcula target e stop loss baseado no padrão."""
        
        current_price = df['close'].iloc[-1]
        atr = (df['high'] - df['low']).tail(14).mean()
        
        if bias == PatternBias.BULLISH:
            target = current_price + 2 * atr
            stop = current_price - 1 * atr
        elif bias == PatternBias.BEARISH:
            target = current_price - 2 * atr
            stop = current_price + 1 * atr
        else:
            target = None
            stop = None
        
        return target, stop
    
    def _heuristic_analysis(
        self,
        df,
        symbol: str = "",
    ) -> List[PatternDetection]:
        """Análise heurística quando modelos não estão disponíveis."""
        
        if len(df) < 20:
            return []
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        
        # Tendência simples
        sma_short = np.mean(closes[-10:])
        sma_long = np.mean(closes[-20:])
        
        if sma_short > sma_long * 1.01:
            pattern = ChartPatternType.UPTREND
            bias = PatternBias.BULLISH
            confidence = 0.6
        elif sma_short < sma_long * 0.99:
            pattern = ChartPatternType.DOWNTREND
            bias = PatternBias.BEARISH
            confidence = 0.6
        else:
            pattern = ChartPatternType.SIDEWAYS
            bias = PatternBias.NEUTRAL
            confidence = 0.5
        
        return [PatternDetection(
            pattern_type=pattern,
            bias=bias,
            confidence=confidence,
            bounding_box=(0, 0, self.image_size, self.image_size),
        )]
    
    def analyze_multiple_timeframes(
        self,
        data_by_tf: Dict[str, Any],  # {timeframe: DataFrame}
        symbol: str = "",
    ) -> Dict[str, List[PatternDetection]]:
        """
        Analisa múltiplos timeframes.
        
        Returns:
            Dict com detecções por timeframe
        """
        results = {}
        
        for tf, df in data_by_tf.items():
            detections = self.analyze_chart(df, symbol, tf)
            results[tf] = detections
        
        return results
    
    def get_consensus(
        self,
        mtf_results: Dict[str, List[PatternDetection]]
    ) -> Tuple[PatternBias, float]:
        """
        Obtém consenso entre timeframes.
        
        Returns:
            (bias, confidence)
        """
        bias_scores = Counter()
        
        # Pesos por timeframe (maior = mais importante)
        tf_weights = {
            'M1': 0.5, 'M5': 0.7, 'M15': 0.9,
            'H1': 1.0, 'H4': 1.2, 'D1': 1.5,
        }
        
        for tf, detections in mtf_results.items():
            weight = tf_weights.get(tf, 1.0)
            
            for det in detections:
                bias_scores[det.bias] += det.confidence * weight
        
        if not bias_scores:
            return PatternBias.NEUTRAL, 0.0
        
        top_bias = bias_scores.most_common(1)[0]
        total = sum(bias_scores.values())
        
        return top_bias[0], top_bias[1] / total if total > 0 else 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas."""
        return {
            'total_analyses': self.stats['total_analyses'],
            'patterns_detected': dict(self.stats['patterns_detected']),
            'by_bias': dict(self.stats['by_bias']),
            'models_loaded': [name for name, _ in self.models],
            'history_size': len(self.analysis_history),
        }
