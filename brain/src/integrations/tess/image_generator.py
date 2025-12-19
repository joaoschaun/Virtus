"""
VIRTUS - TESS AI Image Generator Service
==========================================

Serviço de geração de imagens profissionais usando TESS AI.
Combina imagens geradas por IA com overlay do template Virtus.

Features:
- Geração de imagens via Stable Diffusion (TESS AI)
- Overlay do template Virtus por cima das imagens
- Suporte a briefings, notícias e alertas de mercado
- Prompts contextuais baseados nos dados reais

Custo estimado: ~18 créditos por imagem
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import os
import io

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

logger = logging.getLogger(__name__)


# ==================== BRAND COLORS ====================

class BrandColors:
    """Cores da marca Virtus."""
    PRIMARY = "#E53935"        # Vermelho principal
    PRIMARY_LIGHT = "#FF5252"  # Vermelho claro
    PRIMARY_DARK = "#B71C1C"   # Vermelho escuro
    BACKGROUND_DARK = "#0D0D0D"
    BACKGROUND_CARD = "#1A1A1A"
    BACKGROUND_OVERLAY = (0, 0, 0, 180)  # RGBA para overlay
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B0B0B0"
    SUCCESS = "#4CAF50"
    DANGER = "#F44336"
    WARNING = "#FF9800"
    INFO = "#2196F3"
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Converte hex para RGB."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class ImageStyle(Enum):
    """Estilos de imagem disponíveis na TESS."""
    REALISTIC = "realistic"
    MODERN = "modern"
    MINIMALISM = "minimalism"
    CONTEMPORARY = "contemporary"
    CYBERPUNK = "cyberpunk"
    RENDER_3D = "3d_render"
    VECTOR = "vector"
    POP = "pop"


class ImageLighting(Enum):
    """Iluminação disponível."""
    STUDIO = "studio"
    CINEMATIC = "cinematic"
    NATURAL = "natural"
    GOLDEN_HOUR = "golden_hour"
    DRAMATIC = "dramatic"
    NEON = "neon"


class ImageMood(Enum):
    """Mood/humor da imagem."""
    BRIGHT = "bright"
    COLORFUL = "colorful"
    CALM = "calm"
    NEUTRAL = "neutral"
    DARK = "dark"
    CHEERFUL = "cheerful"


class ImageSize(Enum):
    """Tamanhos disponíveis."""
    SQUARE = "1024x1024"  # Instagram
    PORTRAIT = "576x1024"  # Stories
    LANDSCAPE = "1024x576"  # Twitter/Facebook
    VERTICAL = "576x768"


@dataclass
class TessImageConfig:
    """Configuração para geração de imagem."""
    prompt: str
    style: ImageStyle = ImageStyle.REALISTIC
    lighting: ImageLighting = ImageLighting.STUDIO
    mood: ImageMood = ImageMood.BRIGHT
    size: ImageSize = ImageSize.SQUARE
    negative_prompt: str = "text, words, letters, watermark, logo, low quality, blurry, distorted"
    seed: Optional[int] = None  # None = random


@dataclass
class BriefingData:
    """Dados do briefing para geração de imagem contextual."""
    date: datetime
    sentiment: str  # bullish, bearish, neutral
    sentiment_score: float  # 0.0 a 1.0
    main_symbols: List[str] = field(default_factory=list)
    top_news: List[str] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)
    signals: Dict[str, Dict] = field(default_factory=dict)
    highlight: Optional[str] = None


@dataclass 
class NewsData:
    """Dados de uma notícia para geração de imagem."""
    title: str
    summary: str
    sentiment: str  # positive, negative, neutral
    impact: str  # high, medium, low
    symbols: List[str] = field(default_factory=list)
    source: str = ""


class VirtusOverlay:
    """
    Aplica overlay do template Virtus sobre imagens.
    """
    
    def __init__(self, assets_dir: Optional[Path] = None):
        """
        Inicializa o overlay.
        
        Args:
            assets_dir: Diretório com assets (logo, fontes)
        """
        if not PIL_AVAILABLE:
            raise ImportError("Pillow não instalado")
        
        # Tentar múltiplos caminhos para os assets
        if assets_dir and assets_dir.exists():
            self.assets_dir = assets_dir
        else:
            # Caminhos possíveis (do brain ou do backend)
            possible_paths = [
                Path(__file__).parent.parent.parent.parent / "dashboard" / "frontend" / "public",
                Path(__file__).parent.parent.parent.parent.parent / "brain" / "dashboard" / "frontend" / "public",
                Path("C:/Users/Administrator/Desktop/Virtus/brain/dashboard/frontend/public"),
            ]
            
            self.assets_dir = None
            for path in possible_paths:
                if path.exists():
                    self.assets_dir = path
                    break
            
            if self.assets_dir is None:
                self.assets_dir = possible_paths[0]  # Fallback
                
        print(f"📂 Assets dir: {self.assets_dir} (exists: {self.assets_dir.exists()})")
        self._load_fonts()
        self._load_logo()
    
    def _load_fonts(self):
        """Carrega fontes."""
        self.fonts = {}
        
        # Tentar carregar fontes do sistema
        font_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        
        for size_name, size in [("title", 48), ("subtitle", 32), ("body", 24), ("small", 18), ("tiny", 14)]:
            font_loaded = False
            for path in font_paths:
                if os.path.exists(path):
                    try:
                        self.fonts[size_name] = ImageFont.truetype(path, size)
                        font_loaded = True
                        break
                    except:
                        continue
            
            if not font_loaded:
                self.fonts[size_name] = ImageFont.load_default()
    
    def _load_logo(self):
        """Carrega logo da Virtus."""
        self.logo = None
        # Prioriza a assinatura para posts
        logo_paths = [
            self.assets_dir / "virtus-assinatura.png",
            self.assets_dir / "virtus-primaria.png",
            self.assets_dir / "virtus-simbolo.png",
            self.assets_dir / "logo.png",
            self.assets_dir / "virtus-logo.png",
            self.assets_dir / "images" / "logo.png",
        ]
        
        for path in logo_paths:
            if path.exists():
                try:
                    self.logo = Image.open(path).convert("RGBA")
                    # Redimensionar para tamanho adequado (assinatura é mais larga)
                    self.logo.thumbnail((200, 80), Image.Resampling.LANCZOS)
                    print(f"✅ Logo carregada: {path.name}")
                    break
                except Exception as e:
                    print(f"⚠️ Erro ao carregar logo {path}: {e}")
                    continue
        
        if self.logo is None:
            print(f"⚠️ Logo não encontrada em: {[str(p) for p in logo_paths]}")
    
    def apply_briefing_overlay(
        self,
        base_image: Image.Image,
        data: BriefingData
    ) -> Image.Image:
        """
        Aplica overlay de briefing sobre a imagem.
        
        Args:
            base_image: Imagem base da TESS
            data: Dados do briefing
            
        Returns:
            Imagem com overlay aplicado
        """
        # Redimensionar para 1080x1080
        img = base_image.copy()
        img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
        
        # Criar overlay semi-transparente
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Header com gradiente escuro (top)
        self._draw_gradient_bar(draw, 0, 0, 1080, 200, top_alpha=220, bottom_alpha=0)
        
        # Footer com gradiente escuro (bottom)
        self._draw_gradient_bar(draw, 0, 880, 1080, 200, top_alpha=0, bottom_alpha=220)
        
        # Converter para RGBA e compor
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # === HEADER ===
        # Logo no canto superior esquerdo
        if self.logo:
            img.paste(self.logo, (30, 30), self.logo)
        
        # Título centralizado
        date_str = data.date.strftime("%d/%m/%Y")
        title_text = "BRIEFING FOREX"
        title_bbox = draw.textbbox((0, 0), title_text, font=self.fonts["title"])
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (1080 - title_width) // 2
        title_y = 50
        
        draw.text(
            (title_x, title_y),
            title_text,
            font=self.fonts["title"],
            fill=BrandColors.hex_to_rgb(BrandColors.TEXT_PRIMARY)
        )
        
        # Badges centralizados abaixo do título
        badges_y = title_y + 60
        total_badges_width = 160 + 20 + 120  # data badge + gap + sentiment badge
        badges_start_x = (1080 - total_badges_width) // 2
        
        # Data badge
        badge_color = BrandColors.hex_to_rgb(BrandColors.PRIMARY)
        draw.rounded_rectangle(
            [badges_start_x, badges_y, badges_start_x + 160, badges_y + 35],
            radius=15,
            fill=badge_color
        )
        draw.text(
            (badges_start_x + 15, badges_y + 5),
            date_str,
            font=self.fonts["small"],
            fill=(255, 255, 255)
        )
        
        # Sentiment badge
        sentiment_colors = {
            "bullish": BrandColors.SUCCESS,
            "bearish": BrandColors.DANGER,
            "neutral": BrandColors.INFO
        }
        sentiment_labels = {
            "bullish": "📈 ALTA",
            "bearish": "📉 BAIXA",
            "neutral": "➡️ NEUTRO"
        }
        
        sent_color = BrandColors.hex_to_rgb(sentiment_colors.get(data.sentiment, BrandColors.INFO))
        sent_label = sentiment_labels.get(data.sentiment, "NEUTRO")
        
        sent_badge_x = badges_start_x + 180
        draw.rounded_rectangle(
            [sent_badge_x, badges_y, sent_badge_x + 120, badges_y + 35],
            radius=15,
            fill=sent_color
        )
        draw.text(
            (sent_badge_x + 15, badges_y + 5),
            sent_label,
            font=self.fonts["small"],
            fill=(255, 255, 255)
        )
        
        # === CONTEÚDO CENTRAL (cards de símbolos) ===
        cards_y_start = badges_y + 60  # Abaixo dos badges
        if data.signals:
            self._draw_symbol_cards(draw, img, data.signals, y_start=cards_y_start)
        
        # === FOOTER ===
        # Linha vermelha decorativa
        draw.rectangle([0, 970, 1080, 975], fill=BrandColors.hex_to_rgb(BrandColors.PRIMARY))
        
        # Principais notícias (se houver)
        if data.top_news:
            news_text = " • ".join(data.top_news[:2])
            if len(news_text) > 80:
                news_text = news_text[:77] + "..."
            draw.text(
                (40, 985),
                f"📰 {news_text}",
                font=self.fonts["tiny"],
                fill=BrandColors.hex_to_rgb(BrandColors.TEXT_SECONDARY)
            )
        
        # Eventos (se houver)
        if data.key_events:
            events_text = " | ".join(data.key_events[:2])
            if len(events_text) > 60:
                events_text = events_text[:57] + "..."
            draw.text(
                (40, 1010),
                f"📅 {events_text}",
                font=self.fonts["tiny"],
                fill=BrandColors.hex_to_rgb(BrandColors.TEXT_SECONDARY)
            )
        
        # Hashtags
        draw.text(
            (40, 1040),
            "#Forex #Trading #XAUUSD #EURUSD #VirtusInvestimentos",
            font=self.fonts["tiny"],
            fill=BrandColors.hex_to_rgb(BrandColors.TEXT_SECONDARY)
        )
        
        # URL
        draw.text(
            (880, 1040),
            "virtus.aggreg8.io",
            font=self.fonts["tiny"],
            fill=BrandColors.hex_to_rgb(BrandColors.PRIMARY_LIGHT)
        )
        
        return img.convert('RGB')
    
    def apply_news_overlay(
        self,
        base_image: Image.Image,
        news: NewsData
    ) -> Image.Image:
        """
        Aplica overlay de notícia sobre a imagem.
        
        Args:
            base_image: Imagem base da TESS
            news: Dados da notícia
            
        Returns:
            Imagem com overlay aplicado
        """
        # Redimensionar para 1080x1080
        img = base_image.copy()
        img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
        
        # Aplicar escurecimento leve para melhor legibilidade
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.7)
        
        # Criar overlay
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Gradiente inferior forte para texto
        self._draw_gradient_bar(draw, 0, 500, 1080, 580, top_alpha=0, bottom_alpha=240)
        
        # Header pequeno
        self._draw_gradient_bar(draw, 0, 0, 1080, 100, top_alpha=200, bottom_alpha=0)
        
        # Compor
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # === HEADER ===
        # Logo
        if self.logo:
            img.paste(self.logo, (40, 20), self.logo)
        
        # Badge de impacto
        impact_colors = {
            "high": BrandColors.DANGER,
            "medium": BrandColors.WARNING,
            "low": BrandColors.INFO
        }
        impact_labels = {
            "high": "🔴 ALTO IMPACTO",
            "medium": "🟡 MÉDIO IMPACTO",
            "low": "🔵 BAIXO IMPACTO"
        }
        
        impact_color = BrandColors.hex_to_rgb(impact_colors.get(news.impact, BrandColors.INFO))
        impact_label = impact_labels.get(news.impact, "NOTÍCIA")
        
        draw.rounded_rectangle(
            [850, 30, 1040, 65],
            radius=15,
            fill=impact_color
        )
        draw.text(
            (865, 37),
            impact_label,
            font=self.fonts["tiny"],
            fill=(255, 255, 255)
        )
        
        # === CONTEÚDO ===
        # Sentiment icon
        sentiment_icons = {
            "positive": "📈",
            "negative": "📉",
            "neutral": "➡️"
        }
        sentiment_icon = sentiment_icons.get(news.sentiment, "📰")
        
        # Título (quebrar em linhas se necessário)
        title_lines = self._wrap_text(news.title, self.fonts["subtitle"], 950)
        y = 700
        for line in title_lines[:3]:
            draw.text(
                (40, y),
                line,
                font=self.fonts["subtitle"],
                fill=BrandColors.hex_to_rgb(BrandColors.TEXT_PRIMARY)
            )
            y += 45
        
        # Resumo
        if news.summary:
            summary_lines = self._wrap_text(news.summary, self.fonts["body"], 950)
            y += 20
            for line in summary_lines[:3]:
                draw.text(
                    (40, y),
                    line,
                    font=self.fonts["body"],
                    fill=BrandColors.hex_to_rgb(BrandColors.TEXT_SECONDARY)
                )
                y += 30
        
        # Símbolos afetados
        if news.symbols:
            symbols_text = f"Símbolos: {', '.join(news.symbols[:4])}"
            draw.text(
                (40, 950),
                symbols_text,
                font=self.fonts["small"],
                fill=BrandColors.hex_to_rgb(BrandColors.PRIMARY_LIGHT)
            )
        
        # Fonte
        if news.source:
            draw.text(
                (40, 1000),
                f"Fonte: {news.source}",
                font=self.fonts["tiny"],
                fill=BrandColors.hex_to_rgb(BrandColors.TEXT_SECONDARY)
            )
        
        # Linha decorativa
        draw.rectangle([0, 1040, 1080, 1045], fill=BrandColors.hex_to_rgb(BrandColors.PRIMARY))
        
        # Hashtags e URL
        draw.text(
            (40, 1050),
            "#Forex #News #Trading",
            font=self.fonts["tiny"],
            fill=BrandColors.hex_to_rgb(BrandColors.TEXT_SECONDARY)
        )
        draw.text(
            (880, 1050),
            "virtus.aggreg8.io",
            font=self.fonts["tiny"],
            fill=BrandColors.hex_to_rgb(BrandColors.PRIMARY_LIGHT)
        )
        
        return img.convert('RGB')
    
    def _draw_gradient_bar(
        self,
        draw: ImageDraw.Draw,
        x: int, y: int,
        width: int, height: int,
        top_alpha: int = 200,
        bottom_alpha: int = 0
    ):
        """Desenha barra com gradiente de transparência."""
        for i in range(height):
            alpha = int(top_alpha + (bottom_alpha - top_alpha) * i / height)
            draw.rectangle(
                [x, y + i, x + width, y + i + 1],
                fill=(0, 0, 0, alpha)
            )
    
    def _draw_symbol_cards(
        self,
        draw: ImageDraw.Draw,
        img: Image.Image,
        signals: Dict[str, Dict],
        y_start: int = 200
    ):
        """Desenha cards de símbolos."""
        symbol_names = {
            'XAUUSD': '🥇 Ouro',
            'EURUSD': '🇪🇺 EUR/USD',
            'GBPUSD': '🇬🇧 GBP/USD',
            'USDJPY': '🇯🇵 USD/JPY',
        }
        
        symbols = list(signals.keys())[:4]
        
        if not symbols:
            return
        
        # Grid 2x2 de cards semi-transparentes
        card_width = 480
        card_height = 180
        margin = 30
        
        positions = [
            (margin, y_start),
            (margin + card_width + 20, y_start),
            (margin, y_start + card_height + 20),
            (margin + card_width + 20, y_start + card_height + 20),
        ]
        
        for i, symbol in enumerate(symbols):
            if i >= 4:
                break
            
            x, y = positions[i]
            signal = signals.get(symbol, {})
            
            direction = signal.get('direction', 'neutral')
            strength = signal.get('strength', 0.5)
            
            # Cor do card baseada na direção
            if direction == 'bullish':
                card_color = (76, 175, 80, 180)  # Verde
            elif direction == 'bearish':
                card_color = (244, 67, 54, 180)  # Vermelho
            else:
                card_color = (33, 150, 243, 180)  # Azul
            
            # Desenhar card
            card_overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_overlay)
            card_draw.rounded_rectangle(
                [x, y, x + card_width, y + card_height],
                radius=15,
                fill=card_color
            )
            img.paste(Image.alpha_composite(img.convert('RGBA'), card_overlay), (0, 0))
            
            # Nome do símbolo
            name = symbol_names.get(symbol, symbol)
            draw.text(
                (x + 20, y + 20),
                name,
                font=self.fonts["subtitle"],
                fill=(255, 255, 255)
            )
            
            # Direção
            dir_labels = {
                'bullish': '📈 ALTA',
                'bearish': '📉 BAIXA',
                'neutral': '➡️ NEUTRO'
            }
            draw.text(
                (x + 20, y + 70),
                dir_labels.get(direction, 'NEUTRO'),
                font=self.fonts["body"],
                fill=(255, 255, 255)
            )
            
            # Barra de força
            bar_x = x + 20
            bar_y = y + 120
            bar_width = card_width - 40
            bar_height = 20
            
            # Fundo da barra
            draw.rounded_rectangle(
                [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                radius=10,
                fill=(0, 0, 0, 100)
            )
            
            # Preenchimento
            fill_width = int(bar_width * strength)
            if fill_width > 0:
                draw.rounded_rectangle(
                    [bar_x, bar_y, bar_x + fill_width, bar_y + bar_height],
                    radius=10,
                    fill=(255, 255, 255, 200)
                )
            
            # Percentual
            pct_text = f"{int(strength * 100)}%"
            draw.text(
                (x + card_width - 60, y + 115),
                pct_text,
                font=self.fonts["small"],
                fill=(255, 255, 255)
            )
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Quebra texto em linhas que cabem na largura."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            if bbox[2] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


class TessImageGenerator:
    """
    Gerador de imagens usando TESS AI (Stable Diffusion) + Overlay Virtus.
    
    Uso:
        generator = TessImageGenerator(api_key="...")
        
        # Briefing com overlay
        image = await generator.generate_briefing_with_overlay(briefing_data)
        image.save("briefing.png")
        
        # Notícia com overlay
        image = await generator.generate_news_with_overlay(news_data)
        image.save("news.png")
    """
    
    # Agent ID para geração de imagens estilo Unsplash
    AGENT_ID = 165
    
    def __init__(self, api_key: Optional[str] = None, assets_dir: Optional[Path] = None):
        """
        Inicializa o gerador.
        
        Args:
            api_key: Chave da API TESS
            assets_dir: Diretório com assets (logo, fontes)
        """
        self.api_key = api_key or os.environ.get("TESS_API_KEY")
        
        if not self.api_key:
            # Tentar carregar de config.yaml
            try:
                import yaml
                config_path = Path(__file__).parent.parent.parent.parent / "config" / "tess.yaml"
                if config_path.exists():
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                        self.api_key = config.get('api_key')
            except Exception:
                pass
        
        if not self.api_key:
            raise ValueError("TESS API key não configurada")
        
        self.base_url = "https://tess.pareto.io/api"
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Overlay Virtus
        self.overlay = VirtusOverlay(assets_dir) if PIL_AVAILABLE else None
    
    @property
    def headers(self) -> Dict[str, str]:
        """Headers para requisições."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna sessão HTTP."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=120)  # 2 minutos para geração
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        return self._session
    
    async def close(self):
        """Fecha a sessão."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    async def _generate_raw_image(self, config: TessImageConfig) -> str:
        """
        Gera uma imagem crua usando TESS AI.
        
        Returns:
            URL da imagem gerada
        """
        session = await self._get_session()
        
        payload = {
            "seu-comando": config.prompt,
            "image_size": config.size.value,
            "negativePrompt": config.negative_prompt,
            "seed": str(config.seed) if config.seed else str(hash(config.prompt) % 1000000),
            "image_number_of_images": 1,
            "image_style": config.style.value,
            "image_lighting": config.lighting.value,
            "image_mood": config.mood.value,
            "waitExecution": "true"
        }
        
        logger.info(f"Gerando imagem TESS: {config.prompt[:100]}...")
        
        try:
            async with session.post(
                f"{self.base_url}/agents/{self.AGENT_ID}/execute",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Erro na API TESS: {response.status} - {error_text}")
                
                data = await response.json()
                
                if data.get('responses') and len(data['responses']) > 0:
                    result = data['responses'][0]
                    
                    if result.get('status') != 'succeeded':
                        raise Exception(f"Geração falhou: {result.get('status')}")
                    
                    image_url = result.get('output')
                    credits_used = result.get('credits', 0)
                    
                    logger.info(f"✅ Imagem gerada: {image_url} (créditos: {credits_used})")
                    return image_url
                
                raise Exception("Resposta inválida da API TESS")
                
        except aiohttp.ClientError as e:
            logger.error(f"Erro de conexão com TESS: {e}")
            raise Exception(f"Erro de conexão: {e}")
    
    async def _download_image(self, url: str) -> Image.Image:
        """Baixa imagem de URL."""
        # Usar sessão separada sem headers de auth para CDN
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Erro ao baixar imagem: {response.status}")
                data = await response.read()
                return Image.open(io.BytesIO(data))
    
    def _build_briefing_prompt(self, data: BriefingData) -> str:
        """Constrói prompt contextual para briefing."""
        
        # Cores e mood baseados no sentimento
        sentiment_elements = {
            "bullish": {
                "colors": "vibrant green and gold tones",
                "charts": "upward trending charts showing gains",
                "mood": "optimistic, positive, dynamic energy",
                "elements": "rising arrows, growth indicators"
            },
            "bearish": {
                "colors": "deep red and dark blue tones",
                "charts": "downward trending charts showing decline",
                "mood": "cautious, analytical, focused",
                "elements": "descending patterns, risk indicators"
            },
            "neutral": {
                "colors": "balanced blue, silver and white tones",
                "charts": "sideways consolidating charts",
                "mood": "calm, professional, analytical",
                "elements": "balanced indicators, range patterns"
            }
        }
        
        elements = sentiment_elements.get(data.sentiment, sentiment_elements["neutral"])
        
        # Símbolos para adicionar ao prompt
        symbol_visuals = []
        for symbol in data.main_symbols[:3]:
            if "GOLD" in symbol.upper() or "XAU" in symbol.upper():
                symbol_visuals.append("gold bars and golden coins")
            elif "EUR" in symbol.upper():
                symbol_visuals.append("Euro currency symbols")
            elif "GBP" in symbol.upper():
                symbol_visuals.append("British Pound sterling elements")
            elif "JPY" in symbol.upper():
                symbol_visuals.append("Japanese Yen symbols")
            elif "USD" in symbol.upper():
                symbol_visuals.append("US Dollar bills")
        
        symbols_text = ", ".join(symbol_visuals) if symbol_visuals else "forex currency pairs"
        
        # Adicionar contexto de notícias se disponível
        news_context = ""
        if data.top_news:
            news_context = f"The scene should convey the mood of: {data.top_news[0][:50]}. "
        
        prompt = f"""Professional high-end financial trading room scene.
        Ultra modern corporate office with multiple curved 4K monitors displaying {elements['charts']}.
        {symbols_text} prominently featured.
        {elements['colors']}, {elements['mood']}.
        {news_context}
        Sleek glass desk, premium leather chair, ambient lighting.
        Photorealistic, cinematic quality, sharp focus, high detail.
        Professional institutional photography style.
        No text, no watermarks, no logos, no people visible."""
        
        return prompt
    
    def _build_news_prompt(self, news: NewsData) -> str:
        """Constrói prompt contextual para notícia."""
        
        # Tema visual baseado no sentimento
        sentiment_themes = {
            "positive": {
                "mood": "bright, optimistic, dynamic",
                "colors": "green and gold tones, warm lighting",
                "elements": "upward movement, growth symbolism"
            },
            "negative": {
                "mood": "serious, dramatic, intense",
                "colors": "red and dark tones, dramatic lighting",
                "elements": "tension, volatility symbolism"
            },
            "neutral": {
                "mood": "balanced, analytical, professional",
                "colors": "blue and silver tones, even lighting",
                "elements": "stability, analysis symbolism"
            }
        }
        
        theme = sentiment_themes.get(news.sentiment, sentiment_themes["neutral"])
        
        # Contexto baseado nos símbolos
        symbol_context = ""
        for symbol in news.symbols[:2]:
            if "GOLD" in symbol.upper() or "XAU" in symbol.upper():
                symbol_context += "gold bars, gold coins, precious metals, "
            elif "EUR" in symbol.upper():
                symbol_context += "Euro currency, European finance, "
            elif "GBP" in symbol.upper():
                symbol_context += "British Pound, UK financial district, "
            elif "OIL" in symbol.upper() or "WTI" in symbol.upper():
                symbol_context += "oil barrels, energy sector, "
            elif "USD" in symbol.upper():
                symbol_context += "US Dollar, American finance, "
        
        # Impacto define intensidade
        intensity = {
            "high": "highly dramatic, intense atmosphere, breaking news feel",
            "medium": "moderate intensity, important development feel",
            "low": "calm, informative atmosphere"
        }
        
        intensity_text = intensity.get(news.impact, intensity["medium"])
        
        prompt = f"""Financial news visualization scene.
        {theme['mood']} atmosphere with {theme['colors']}.
        {symbol_context if symbol_context else 'forex trading environment'}
        {theme['elements']}.
        {intensity_text}.
        Modern financial dashboard aesthetic, premium quality.
        Cinematic lighting, professional photography.
        Abstract representation of market movement.
        No text, no watermarks, no people, no logos."""
        
        return prompt
    
    async def generate_briefing_with_overlay(
        self,
        data: BriefingData,
        save_path: Optional[Path] = None
    ) -> Image.Image:
        """
        Gera imagem de briefing com overlay Virtus.
        
        Args:
            data: Dados do briefing
            save_path: Caminho para salvar (opcional)
            
        Returns:
            Imagem PIL com overlay aplicado
        """
        # 1. Construir prompt contextual
        prompt = self._build_briefing_prompt(data)
        
        # 2. Configurar geração
        mood = ImageMood.BRIGHT if data.sentiment == "bullish" else (
            ImageMood.DARK if data.sentiment == "bearish" else ImageMood.NEUTRAL
        )
        
        config = TessImageConfig(
            prompt=prompt,
            style=ImageStyle.REALISTIC,
            lighting=ImageLighting.CINEMATIC,
            mood=mood,
            size=ImageSize.SQUARE,
            negative_prompt="text, words, letters, numbers, watermark, logo, low quality, blurry, ugly, cartoon, anime, people, faces, hands"
        )
        
        # 3. Gerar imagem
        image_url = await self._generate_raw_image(config)
        
        # 4. Baixar imagem
        base_image = await self._download_image(image_url)
        
        # 5. Aplicar overlay
        if self.overlay:
            final_image = self.overlay.apply_briefing_overlay(base_image, data)
        else:
            final_image = base_image
        
        # 6. Salvar se solicitado
        if save_path:
            final_image.save(str(save_path), "PNG", quality=95)
            logger.info(f"💾 Imagem salva: {save_path}")
        
        return final_image
    
    async def generate_news_with_overlay(
        self,
        news: NewsData,
        save_path: Optional[Path] = None
    ) -> Image.Image:
        """
        Gera imagem de notícia com overlay Virtus.
        
        Args:
            news: Dados da notícia
            save_path: Caminho para salvar (opcional)
            
        Returns:
            Imagem PIL com overlay aplicado
        """
        # 1. Construir prompt contextual
        prompt = self._build_news_prompt(news)
        
        # 2. Configurar geração
        mood = ImageMood.COLORFUL if news.sentiment == "positive" else (
            ImageMood.DARK if news.sentiment == "negative" else ImageMood.NEUTRAL
        )
        
        config = TessImageConfig(
            prompt=prompt,
            style=ImageStyle.MODERN,
            lighting=ImageLighting.DRAMATIC if news.impact == "high" else ImageLighting.STUDIO,
            mood=mood,
            size=ImageSize.SQUARE,
            negative_prompt="text, words, letters, numbers, watermark, logo, low quality, blurry, ugly, cartoon, anime, people, faces"
        )
        
        # 3. Gerar imagem
        image_url = await self._generate_raw_image(config)
        
        # 4. Baixar imagem
        base_image = await self._download_image(image_url)
        
        # 5. Aplicar overlay
        if self.overlay:
            final_image = self.overlay.apply_news_overlay(base_image, news)
        else:
            final_image = base_image
        
        # 6. Salvar se solicitado
        if save_path:
            final_image.save(str(save_path), "PNG", quality=95)
            logger.info(f"💾 Imagem salva: {save_path}")
        
        return final_image
    
    # Métodos legados para compatibilidade
    async def generate(self, config: TessImageConfig) -> str:
        """Gera imagem sem overlay (retorna URL)."""
        return await self._generate_raw_image(config)
    
    async def generate_forex_briefing_image(
        self,
        sentiment: str,
        main_symbols: List[str],
        highlights: Optional[str] = None
    ) -> str:
        """Método legado - retorna URL da imagem."""
        data = BriefingData(
            date=datetime.now(),
            sentiment=sentiment,
            sentiment_score=0.5,
            main_symbols=main_symbols,
            highlight=highlights
        )
        prompt = self._build_briefing_prompt(data)
        
        config = TessImageConfig(
            prompt=prompt,
            style=ImageStyle.REALISTIC,
            lighting=ImageLighting.STUDIO,
            mood=ImageMood.BRIGHT if sentiment == "bullish" else ImageMood.NEUTRAL,
            size=ImageSize.SQUARE
        )
        
        return await self._generate_raw_image(config)


# Singleton
_generator: Optional[TessImageGenerator] = None


async def get_tess_image_generator() -> TessImageGenerator:
    """Retorna instância singleton do gerador."""
    global _generator
    if _generator is None:
        _generator = TessImageGenerator()
    return _generator


# ==================== TESTE ====================

if __name__ == "__main__":
    async def test():
        """Teste do gerador de imagens."""
        api_key = "337520|MzMxArNQnQAcO0XBz7CLbraeV4lA7L6ep9sHITpt59a4b449"
        
        async with TessImageGenerator(api_key=api_key) as generator:
            print("=" * 60)
            print("🎨 TESTE DE GERAÇÃO DE IMAGEM COM OVERLAY VIRTUS")
            print("=" * 60)
            
            # Dados de teste para briefing
            briefing_data = BriefingData(
                date=datetime.now(),
                sentiment="bullish",
                sentiment_score=0.72,
                main_symbols=["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"],
                top_news=["Ouro atinge máxima histórica após dados de inflação", "Fed sinaliza pausa nos juros"],
                key_events=["Core CPI (EUA)", "Decisão COPOM"],
                signals={
                    "XAUUSD": {"direction": "bullish", "strength": 0.8},
                    "EURUSD": {"direction": "bullish", "strength": 0.65},
                    "GBPUSD": {"direction": "neutral", "strength": 0.5},
                    "USDJPY": {"direction": "bearish", "strength": 0.45},
                }
            )
            
            print("\n📊 Gerando briefing com overlay...")
            save_path = Path(__file__).parent.parent.parent.parent / "data" / "social_media" / "images" / "test_briefing_overlay.png"
            
            image = await generator.generate_briefing_with_overlay(briefing_data, save_path)
            print(f"✅ Briefing gerado: {save_path}")
            
            # Dados de teste para notícia
            news_data = NewsData(
                title="Fed mantém juros e sinaliza corte em 2025",
                summary="O Federal Reserve decidiu manter a taxa de juros inalterada, mas indicou possíveis cortes para o próximo ano.",
                sentiment="positive",
                impact="high",
                symbols=["EURUSD", "XAUUSD"],
                source="Federal Reserve"
            )
            
            print("\n📰 Gerando notícia com overlay...")
            save_path = Path(__file__).parent.parent.parent.parent / "data" / "social_media" / "images" / "test_news_overlay.png"
            
            image = await generator.generate_news_with_overlay(news_data, save_path)
            print(f"✅ Notícia gerada: {save_path}")
    
    asyncio.run(test())
