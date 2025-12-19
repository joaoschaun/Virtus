"""
VIRTUS Social Media - Image Generator
======================================

Gerador de imagens profissionais com identidade visual Virtus.

Brand Guidelines:
- Cor Primária: #E53935 (Vermelho Virtus)
- Cor Secundária: #FF5252 (Vermelho claro)
- Fundo Escuro: #0D0D0D / #1A1A1A
- Texto: #FFFFFF / #B0B0B0
- Fonte: Arial/Helvetica (clean, profissional)
"""

import io
import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None  # Type hint placeholder
    ImageDraw = None
    ImageFont = None
    ImageFilter = None
    print("Warning: Pillow not installed. Run: pip install Pillow")


# ==================== BRAND CONSTANTS ====================

class BrandColors:
    """Cores da marca Virtus."""
    PRIMARY = "#E53935"        # Vermelho principal
    PRIMARY_LIGHT = "#FF5252"  # Vermelho claro
    PRIMARY_DARK = "#B71C1C"   # Vermelho escuro
    
    BACKGROUND_DARK = "#0D0D0D"   # Fundo principal
    BACKGROUND_CARD = "#1A1A1A"   # Fundo de cards
    BACKGROUND_LIGHT = "#2D2D2D"  # Fundo secundário
    
    TEXT_PRIMARY = "#FFFFFF"      # Texto principal
    TEXT_SECONDARY = "#B0B0B0"    # Texto secundário
    TEXT_MUTED = "#666666"        # Texto discreto
    
    SUCCESS = "#4CAF50"   # Verde (alta/positivo)
    DANGER = "#F44336"    # Vermelho (baixa/negativo)
    WARNING = "#FF9800"   # Laranja (alerta)
    INFO = "#2196F3"      # Azul (informação)
    
    # Gradientes
    GRADIENT_START = "#E53935"
    GRADIENT_END = "#FF5252"


class ImageTemplate(Enum):
    """Templates de imagem disponíveis."""
    MARKET_ALERT = "market_alert"       # Alerta de mercado
    DAILY_SUMMARY = "daily_summary"     # Resumo diário
    NEWS_HIGHLIGHT = "news_highlight"   # Destaque de notícia
    TECHNICAL_ANALYSIS = "technical"    # Análise técnica
    WEEKLY_OUTLOOK = "weekly_outlook"   # Previsão semanal
    QUOTE = "quote"                     # Citação/Dica
    EDUCATIONAL = "educational"         # Conteúdo educacional


@dataclass
class ImageConfig:
    """Configuração de imagem."""
    width: int = 1080
    height: int = 1080
    template: ImageTemplate = ImageTemplate.MARKET_ALERT
    
    # Conteúdo
    title: str = ""
    subtitle: str = ""
    body: str = ""
    footer: str = ""
    
    # Dados específicos (para templates de mercado)
    symbol: Optional[str] = None
    trend: Optional[str] = None  # "bullish", "bearish", "neutral"
    price: Optional[float] = None
    change_pct: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    sentiment_score: Optional[float] = None
    
    # Hashtags
    hashtags: List[str] = None
    
    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = [
                "Forex", "Trading", "Investimentos",
                "MercadoFinanceiro", "VirtusInvestimentos"
            ]


class ImageGenerator:
    """
    Gerador de imagens profissionais para redes sociais.
    
    Utiliza templates pré-definidos com a identidade visual Virtus.
    """
    
    def __init__(self, assets_dir: Optional[Path] = None):
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required. Install with: pip install Pillow")
        
        # Diretório de assets
        if assets_dir:
            self.assets_dir = Path(assets_dir)
        else:
            self.assets_dir = Path(__file__).parent.parent.parent.parent / "dashboard" / "frontend" / "public"
        
        # Carrega logos
        self._load_brand_assets()
        
        # Diretório de saída
        self.output_dir = Path(__file__).parent.parent.parent.parent / "data" / "social_posts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Fontes (usa padrão do sistema se não encontrar)
        self._load_fonts()
    
    def _load_brand_assets(self):
        """Carrega assets da marca."""
        self.logo_symbol = None
        self.logo_signature = None
        self.logo_primary = None
        
        try:
            symbol_path = self.assets_dir / "virtus-simbolo.png"
            if symbol_path.exists():
                self.logo_symbol = Image.open(symbol_path).convert("RGBA")
            
            signature_path = self.assets_dir / "virtus-assinatura.png"
            if signature_path.exists():
                self.logo_signature = Image.open(signature_path).convert("RGBA")
            
            primary_path = self.assets_dir / "virtus-primaria.png"
            if primary_path.exists():
                self.logo_primary = Image.open(primary_path).convert("RGBA")
                
        except Exception as e:
            print(f"Warning: Could not load brand assets: {e}")
    
    def _load_fonts(self):
        """Carrega fontes."""
        self.fonts = {}
        
        # Tenta carregar fontes do sistema
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        
        try:
            # Tenta Arial primeiro (mais comum no Windows)
            if os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
                self.fonts["title"] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 72)
                self.fonts["subtitle"] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 48)
                self.fonts["body"] = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
                self.fonts["small"] = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
                self.fonts["tiny"] = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
                self.fonts["huge"] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 96)
            else:
                # Fallback para fonte padrão
                self.fonts["title"] = ImageFont.load_default()
                self.fonts["subtitle"] = ImageFont.load_default()
                self.fonts["body"] = ImageFont.load_default()
                self.fonts["small"] = ImageFont.load_default()
                self.fonts["tiny"] = ImageFont.load_default()
                self.fonts["huge"] = ImageFont.load_default()
        except Exception as e:
            print(f"Warning: Could not load fonts: {e}")
            # Usa fonte padrão
            for key in ["title", "subtitle", "body", "small", "tiny", "huge"]:
                self.fonts[key] = ImageFont.load_default()
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Converte cor hex para RGB."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _create_gradient_background(
        self,
        width: int,
        height: int,
        color1: str = BrandColors.BACKGROUND_DARK,
        color2: str = BrandColors.BACKGROUND_CARD
    ) -> "Image.Image":
        """Cria fundo com gradiente sutil."""
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        
        r1, g1, b1 = self._hex_to_rgb(color1)
        r2, g2, b2 = self._hex_to_rgb(color2)
        
        for y in range(height):
            ratio = y / height
            r = int(r1 + (r2 - r1) * ratio * 0.3)  # Gradiente sutil
            g = int(g1 + (g2 - g1) * ratio * 0.3)
            b = int(b1 + (b2 - b1) * ratio * 0.3)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        return img
    
    def _add_logo(self, img: "Image.Image", position: str = "top-left") -> "Image.Image":
        """Adiciona logo na imagem."""
        if not self.logo_signature:
            return img
        
        # Redimensiona logo
        logo = self.logo_signature.copy()
        logo_width = int(img.width * 0.35)
        logo_height = int(logo.height * (logo_width / logo.width))
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        # Posição
        padding = 40
        if position == "top-left":
            pos = (padding, padding)
        elif position == "top-right":
            pos = (img.width - logo_width - padding, padding)
        elif position == "bottom-left":
            pos = (padding, img.height - logo_height - padding)
        elif position == "bottom-right":
            pos = (img.width - logo_width - padding, img.height - logo_height - padding)
        elif position == "center-top":
            pos = ((img.width - logo_width) // 2, padding)
        else:
            pos = (padding, padding)
        
        img.paste(logo, pos, logo)
        return img
    
    def _add_accent_line(self, draw: ImageDraw.Draw, y: int, width: int):
        """Adiciona linha de destaque da marca."""
        line_width = int(width * 0.15)
        draw.rectangle(
            [(40, y), (40 + line_width, y + 4)],
            fill=self._hex_to_rgb(BrandColors.PRIMARY)
        )
    
    def _draw_rounded_rect(
        self,
        draw: ImageDraw.Draw,
        coords: Tuple[int, int, int, int],
        radius: int,
        fill: str
    ):
        """Desenha retângulo com bordas arredondadas."""
        x1, y1, x2, y2 = coords
        color = self._hex_to_rgb(fill)
        
        # Retângulos
        draw.rectangle([(x1 + radius, y1), (x2 - radius, y2)], fill=color)
        draw.rectangle([(x1, y1 + radius), (x2, y2 - radius)], fill=color)
        
        # Cantos
        draw.ellipse([(x1, y1), (x1 + radius * 2, y1 + radius * 2)], fill=color)
        draw.ellipse([(x2 - radius * 2, y1), (x2, y1 + radius * 2)], fill=color)
        draw.ellipse([(x1, y2 - radius * 2), (x1 + radius * 2, y2)], fill=color)
        draw.ellipse([(x2 - radius * 2, y2 - radius * 2), (x2, y2)], fill=color)
    
    def generate_market_alert(self, config: ImageConfig) -> "Image.Image":
        """
        Gera imagem de alerta de mercado.
        
        Layout:
        - Logo no topo
        - Título "ALERTA DE MERCADO"
        - Símbolo grande
        - Dados (preço, variação, suporte/resistência)
        - Sentimento
        - Hashtags no rodapé
        """
        img = self._create_gradient_background(config.width, config.height)
        draw = ImageDraw.Draw(img)
        
        # Logo
        img = self._add_logo(img, "top-left")
        
        # Badge "ALERTA" no canto superior direito
        badge_text = "ALERTA"
        badge_width = 180
        badge_height = 50
        badge_x = config.width - badge_width - 40
        badge_y = 50
        self._draw_rounded_rect(
            draw,
            (badge_x, badge_y, badge_x + badge_width, badge_y + badge_height),
            radius=25,
            fill=BrandColors.PRIMARY
        )
        draw.text(
            (badge_x + badge_width // 2, badge_y + badge_height // 2),
            badge_text,
            font=self.fonts["body"],
            fill=self._hex_to_rgb(BrandColors.TEXT_PRIMARY),
            anchor="mm"
        )
        
        # Título secundário
        y_pos = 160
        draw.text(
            (40, y_pos),
            "MERCADO FINANCEIRO",
            font=self.fonts["small"],
            fill=self._hex_to_rgb(BrandColors.TEXT_SECONDARY)
        )
        
        # Linha de destaque
        y_pos += 50
        self._add_accent_line(draw, y_pos, config.width)
        
        # Símbolo (grande)
        y_pos += 40
        symbol_text = config.symbol or "XAUUSD"
        draw.text(
            (40, y_pos),
            symbol_text,
            font=self.fonts["huge"],
            fill=self._hex_to_rgb(BrandColors.TEXT_PRIMARY)
        )
        
        # Nome do ativo
        y_pos += 110
        asset_names = {
            "XAUUSD": "Ouro / Dólar",
            "EURUSD": "Euro / Dólar",
            "GBPUSD": "Libra / Dólar",
            "USDJPY": "Dólar / Iene",
        }
        asset_name = asset_names.get(symbol_text, "Par de Moedas")
        draw.text(
            (40, y_pos),
            asset_name,
            font=self.fonts["body"],
            fill=self._hex_to_rgb(BrandColors.TEXT_SECONDARY)
        )
        
        # Card de dados
        y_pos += 80
        card_height = 280
        self._draw_rounded_rect(
            draw,
            (40, y_pos, config.width - 40, y_pos + card_height),
            radius=20,
            fill=BrandColors.BACKGROUND_CARD
        )
        
        # Dados dentro do card
        card_padding = 30
        data_y = y_pos + card_padding
        
        # Preço
        if config.price:
            draw.text(
                (40 + card_padding, data_y),
                "PREÇO ATUAL",
                font=self.fonts["tiny"],
                fill=self._hex_to_rgb(BrandColors.TEXT_MUTED)
            )
            data_y += 25
            draw.text(
                (40 + card_padding, data_y),
                f"${config.price:,.2f}",
                font=self.fonts["subtitle"],
                fill=self._hex_to_rgb(BrandColors.TEXT_PRIMARY)
            )
            
            # Variação ao lado
            if config.change_pct is not None:
                change_color = BrandColors.SUCCESS if config.change_pct >= 0 else BrandColors.DANGER
                change_text = f"+{config.change_pct:.2f}%" if config.change_pct >= 0 else f"{config.change_pct:.2f}%"
                draw.text(
                    (350, data_y + 10),
                    change_text,
                    font=self.fonts["body"],
                    fill=self._hex_to_rgb(change_color)
                )
        
        # Suporte e Resistência
        data_y += 80
        if config.support:
            draw.text(
                (40 + card_padding, data_y),
                "SUPORTE",
                font=self.fonts["tiny"],
                fill=self._hex_to_rgb(BrandColors.TEXT_MUTED)
            )
            draw.text(
                (40 + card_padding, data_y + 25),
                f"${config.support:,.2f}",
                font=self.fonts["body"],
                fill=self._hex_to_rgb(BrandColors.SUCCESS)
            )
        
        if config.resistance:
            draw.text(
                (config.width // 2, data_y),
                "RESISTÊNCIA",
                font=self.fonts["tiny"],
                fill=self._hex_to_rgb(BrandColors.TEXT_MUTED)
            )
            draw.text(
                (config.width // 2, data_y + 25),
                f"${config.resistance:,.2f}",
                font=self.fonts["body"],
                fill=self._hex_to_rgb(BrandColors.DANGER)
            )
        
        # Tendência
        data_y += 80
        if config.trend:
            trend_text = {
                "bullish": "📈 TENDÊNCIA DE ALTA",
                "bearish": "📉 TENDÊNCIA DE BAIXA",
                "neutral": "➡️ MERCADO LATERAL"
            }.get(config.trend, "ANALISANDO...")
            
            trend_color = {
                "bullish": BrandColors.SUCCESS,
                "bearish": BrandColors.DANGER,
                "neutral": BrandColors.WARNING
            }.get(config.trend, BrandColors.TEXT_SECONDARY)
            
            draw.text(
                (40 + card_padding, data_y),
                trend_text,
                font=self.fonts["body"],
                fill=self._hex_to_rgb(trend_color)
            )
        
        # Texto principal (análise)
        y_pos = y_pos + card_height + 30
        if config.body:
            # Quebra texto em linhas
            words = config.body.split()
            lines = []
            current_line = []
            for word in words:
                current_line.append(word)
                test_line = " ".join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=self.fonts["body"])
                if bbox[2] > config.width - 80:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
            
            for line in lines[:3]:  # Máximo 3 linhas
                draw.text(
                    (40, y_pos),
                    line,
                    font=self.fonts["body"],
                    fill=self._hex_to_rgb(BrandColors.TEXT_SECONDARY)
                )
                y_pos += 45
        
        # Hashtags no rodapé
        if config.hashtags:
            hashtags_text = " ".join([f"#{tag}" for tag in config.hashtags[:6]])
            draw.text(
                (40, config.height - 80),
                hashtags_text,
                font=self.fonts["tiny"],
                fill=self._hex_to_rgb(BrandColors.PRIMARY)
            )
        
        # Timestamp discreto
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        draw.text(
            (config.width - 200, config.height - 40),
            timestamp,
            font=self.fonts["tiny"],
            fill=self._hex_to_rgb(BrandColors.TEXT_MUTED)
        )
        
        return img
    
    def generate_daily_summary(self, config: ImageConfig) -> "Image.Image":
        """
        Gera imagem de resumo diário INSTITUCIONAL.
        
        Layout profissional com:
        - Fundo com gradiente premium
        - Cards com efeito glassmorphism
        - Grid de sinais por símbolo
        - Indicador visual de sentimento
        """
        img = self._create_premium_background(config.width, config.height)
        draw = ImageDraw.Draw(img)
        
        # Header com logo e data
        self._draw_premium_header(img, draw, config)
        
        # Card principal de sentimento (glassmorphism)
        y_pos = 180
        sentiment_card_height = 160
        self._draw_glass_card(draw, 40, y_pos, config.width - 80, sentiment_card_height)
        
        # Título do sentimento
        mood = config.trend or "neutral"
        mood_emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️", "mixed": "🔄"}.get(mood, "📊")
        mood_text = {"bullish": "MERCADO OTIMISTA", "bearish": "MERCADO CAUTELOSO", 
                     "neutral": "MERCADO NEUTRO", "mixed": "MERCADO VOLÁTIL"}.get(mood, "ANALISANDO")
        mood_color = {"bullish": BrandColors.SUCCESS, "bearish": BrandColors.DANGER,
                      "neutral": BrandColors.WARNING, "mixed": BrandColors.INFO}.get(mood, BrandColors.TEXT_PRIMARY)
        
        draw.text(
            (config.width // 2, y_pos + 45),
            f"{mood_emoji} {mood_text}",
            font=self.fonts["subtitle"],
            fill=self._hex_to_rgb(mood_color),
            anchor="mm"
        )
        
        # Barra de sentimento visual
        bar_y = y_pos + 90
        bar_width = config.width - 160
        bar_height = 12
        bar_x = 80
        
        # Fundo da barra
        self._draw_rounded_rect(draw, (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), 6, BrandColors.BACKGROUND_LIGHT)
        
        # Preenchimento baseado no sentimento
        fill_pct = {"bullish": 0.8, "bearish": 0.2, "neutral": 0.5, "mixed": 0.5}.get(mood, 0.5)
        fill_width = int(bar_width * fill_pct)
        if fill_width > 12:
            self._draw_rounded_rect(draw, (bar_x, bar_y, bar_x + fill_width, bar_y + bar_height), 6, mood_color)
        
        # Labels da barra
        draw.text((bar_x, bar_y + 20), "BEARISH", font=self.fonts["tiny"], fill=self._hex_to_rgb(BrandColors.TEXT_MUTED))
        draw.text((bar_x + bar_width, bar_y + 20), "BULLISH", font=self.fonts["tiny"], 
                  fill=self._hex_to_rgb(BrandColors.TEXT_MUTED), anchor="ra")
        
        # Grid de sinais (4 símbolos)
        y_pos = y_pos + sentiment_card_height + 30
        card_width = (config.width - 100) // 2
        card_height = 200
        
        symbols_data = self._get_symbols_for_display(config)
        
        for i, (symbol, data) in enumerate(symbols_data.items()):
            row = i // 2
            col = i % 2
            card_x = 40 + col * (card_width + 20)
            card_y = y_pos + row * (card_height + 15)
            
            self._draw_symbol_card(draw, card_x, card_y, card_width, card_height, symbol, data)
        
        # Footer com logo e hashtags
        self._draw_premium_footer(img, draw, config)
        
        return img
    
    def _create_premium_background(self, width: int, height: int) -> "Image.Image":
        """Cria fundo premium com gradiente diagonal."""
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        
        # Gradiente diagonal escuro
        for y in range(height):
            for x in range(width):
                # Calcula distância do canto superior esquerdo
                ratio = (x + y) / (width + height)
                
                r1, g1, b1 = self._hex_to_rgb("#0A0A0A")
                r2, g2, b2 = self._hex_to_rgb("#1A1A2E")
                
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                
                img.putpixel((x, y), (r, g, b))
        
        # Adiciona padrão sutil de grid
        for i in range(0, width, 60):
            draw.line([(i, 0), (i, height)], fill=(30, 30, 40), width=1)
        for i in range(0, height, 60):
            draw.line([(0, i), (width, i)], fill=(30, 30, 40), width=1)
        
        return img
    
    def _draw_glass_card(self, draw: ImageDraw.Draw, x: int, y: int, w: int, h: int, opacity: int = 40):
        """Desenha card com efeito glassmorphism."""
        # Fundo semi-transparente
        glass_color = (255, 255, 255, opacity)
        
        # Como PIL não suporta alpha diretamente no draw, simulamos
        # Usa cor mais clara que o fundo
        self._draw_rounded_rect(draw, (x, y, x + w, y + h), 16, "#1E1E2E")
        
        # Borda superior luminosa (efeito de luz)
        draw.line([(x + 16, y + 1), (x + w - 16, y + 1)], fill=self._hex_to_rgb("#333344"), width=1)
        
        # Borda completa
        r = 16
        # Top
        draw.line([(x + r, y), (x + w - r, y)], fill=self._hex_to_rgb("#2A2A3A"), width=1)
        # Bottom
        draw.line([(x + r, y + h), (x + w - r, y + h)], fill=self._hex_to_rgb("#2A2A3A"), width=1)
        # Left
        draw.line([(x, y + r), (x, y + h - r)], fill=self._hex_to_rgb("#2A2A3A"), width=1)
        # Right
        draw.line([(x + w, y + r), (x + w, y + h - r)], fill=self._hex_to_rgb("#2A2A3A"), width=1)
    
    def _draw_premium_header(self, img: "Image.Image", draw: ImageDraw.Draw, config: ImageConfig):
        """Desenha header premium com logo e data."""
        # Logo no canto esquerdo
        if self.logo_signature:
            logo = self.logo_signature.copy()
            logo_width = int(config.width * 0.3)
            logo_height = int(logo.height * (logo_width / logo.width))
            logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            img.paste(logo, (40, 35), logo)
        
        # Badge de data no canto direito
        date_text = config.title.split(" - ")[-1] if " - " in config.title else datetime.now().strftime("%d/%m/%Y")
        
        # Fundo do badge
        badge_w = 160
        badge_h = 40
        badge_x = config.width - badge_w - 40
        badge_y = 45
        self._draw_rounded_rect(draw, (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h), 20, BrandColors.PRIMARY)
        
        draw.text(
            (badge_x + badge_w // 2, badge_y + badge_h // 2),
            date_text,
            font=self.fonts["small"],
            fill=self._hex_to_rgb(BrandColors.TEXT_PRIMARY),
            anchor="mm"
        )
        
        # Título centralizado abaixo
        draw.text(
            (config.width // 2, 130),
            "BRIEFING FOREX",
            font=self.fonts["title"],
            fill=self._hex_to_rgb(BrandColors.TEXT_PRIMARY),
            anchor="mm"
        )
    
    def _draw_symbol_card(self, draw: ImageDraw.Draw, x: int, y: int, w: int, h: int, 
                          symbol: str, data: Dict[str, Any]):
        """Desenha card de símbolo individual."""
        # Card background
        self._draw_glass_card(draw, x, y, w, h)
        
        # Ícone/emoji do símbolo
        symbol_icons = {
            "XAUUSD": "🥇",
            "EURUSD": "🇪🇺",
            "GBPUSD": "🇬🇧",
            "USDJPY": "🇯🇵"
        }
        icon = symbol_icons.get(symbol, "💱")
        
        # Nome do símbolo
        draw.text((x + 20, y + 20), icon, font=self.fonts["subtitle"], fill=self._hex_to_rgb(BrandColors.TEXT_PRIMARY))
        draw.text((x + 60, y + 25), symbol, font=self.fonts["body"], fill=self._hex_to_rgb(BrandColors.TEXT_PRIMARY))
        
        # Direção com cor
        direction = data.get("direction", "neutral")
        direction_color = {"bullish": BrandColors.SUCCESS, "bearish": BrandColors.DANGER}.get(direction, BrandColors.WARNING)
        direction_emoji = {"bullish": "▲", "bearish": "▼"}.get(direction, "●")
        direction_text = {"bullish": "ALTA", "bearish": "BAIXA"}.get(direction, "NEUTRO")
        
        draw.text(
            (x + 20, y + 70),
            f"{direction_emoji} {direction_text}",
            font=self.fonts["body"],
            fill=self._hex_to_rgb(direction_color)
        )
        
        # Força do sinal (barra)
        strength = data.get("strength", 0.5)
        bar_x = x + 20
        bar_y = y + 120
        bar_w = w - 40
        bar_h = 8
        
        # Fundo da barra
        self._draw_rounded_rect(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), 4, BrandColors.BACKGROUND_LIGHT)
        
        # Preenchimento
        fill_w = int(bar_w * strength)
        if fill_w > 8:
            self._draw_rounded_rect(draw, (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), 4, direction_color)
        
        # Percentual
        pct_text = f"{int(strength * 100)}%"
        draw.text(
            (x + w - 20, y + 115),
            pct_text,
            font=self.fonts["small"],
            fill=self._hex_to_rgb(direction_color),
            anchor="ra"
        )
        
        # Resumo curto
        summary = data.get("summary", "")[:40]
        if summary:
            draw.text(
                (x + 20, y + 150),
                summary,
                font=self.fonts["tiny"],
                fill=self._hex_to_rgb(BrandColors.TEXT_MUTED)
            )
    
    def _draw_premium_footer(self, img: "Image.Image", draw: ImageDraw.Draw, config: ImageConfig):
        """Desenha footer premium."""
        footer_y = config.height - 100
        
        # Linha separadora
        draw.line(
            [(40, footer_y), (config.width - 40, footer_y)],
            fill=self._hex_to_rgb(BrandColors.PRIMARY),
            width=2
        )
        
        # Hashtags
        hashtags = ["Forex", "Trading", "XAUUSD", "EURUSD", "VirtusInvestimentos"]
        hashtags_text = " ".join([f"#{tag}" for tag in hashtags])
        draw.text(
            (config.width // 2, footer_y + 30),
            hashtags_text,
            font=self.fonts["tiny"],
            fill=self._hex_to_rgb(BrandColors.TEXT_MUTED),
            anchor="mm"
        )
        
        # Timestamp discreto
        draw.text(
            (config.width - 40, footer_y + 55),
            "virtusinvestimentos.com.br",
            font=self.fonts["tiny"],
            fill=self._hex_to_rgb(BrandColors.TEXT_MUTED),
            anchor="ra"
        )
    
    def _get_symbols_for_display(self, config: ImageConfig) -> Dict[str, Dict]:
        """Extrai dados dos símbolos do config ou gera padrão."""
        symbols = {}
        
        # Tenta extrair do body ou usa padrão
        default_symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        
        for symbol in default_symbols:
            # Dados padrão baseados no trend geral
            base_direction = config.trend or "neutral"
            symbols[symbol] = {
                "direction": base_direction,
                "strength": 0.65,
                "summary": "Aguardando sinais"
            }
        
        return symbols
    
    def generate_news_highlight(self, config: ImageConfig) -> "Image.Image":
        """Gera imagem para destaque de notícia."""
        img = self._create_gradient_background(config.width, config.height)
        draw = ImageDraw.Draw(img)
        
        # Logo
        img = self._add_logo(img, "top-left")
        
        # Badge "NOTÍCIA"
        badge_text = "📰 NOTÍCIA"
        draw.text(
            (config.width - 200, 60),
            badge_text,
            font=self.fonts["body"],
            fill=self._hex_to_rgb(BrandColors.PRIMARY)
        )
        
        # Título da notícia
        y_pos = 200
        self._add_accent_line(draw, y_pos, config.width)
        y_pos += 30
        
        if config.title:
            # Quebra título em linhas
            words = config.title.split()
            lines = []
            current_line = []
            for word in words:
                current_line.append(word)
                test_line = " ".join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=self.fonts["title"])
                if bbox[2] > config.width - 80:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
            
            for line in lines[:3]:
                draw.text(
                    (40, y_pos),
                    line,
                    font=self.fonts["title"],
                    fill=self._hex_to_rgb(BrandColors.TEXT_PRIMARY)
                )
                y_pos += 90
        
        # Corpo da notícia
        y_pos += 40
        if config.body:
            words = config.body.split()
            lines = []
            current_line = []
            for word in words:
                current_line.append(word)
                test_line = " ".join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=self.fonts["body"])
                if bbox[2] > config.width - 80:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
            
            for line in lines[:5]:
                draw.text(
                    (40, y_pos),
                    line,
                    font=self.fonts["body"],
                    fill=self._hex_to_rgb(BrandColors.TEXT_SECONDARY)
                )
                y_pos += 45
        
        # Sentimento (se disponível)
        if config.trend:
            y_pos += 40
            sentiment_text = {
                "bullish": "💚 Impacto Positivo no Mercado",
                "bearish": "❤️ Impacto Negativo no Mercado",
                "neutral": "⚪ Impacto Neutro"
            }.get(config.trend, "")
            
            sentiment_color = {
                "bullish": BrandColors.SUCCESS,
                "bearish": BrandColors.DANGER,
                "neutral": BrandColors.TEXT_SECONDARY
            }.get(config.trend, BrandColors.TEXT_SECONDARY)
            
            draw.text(
                (40, y_pos),
                sentiment_text,
                font=self.fonts["body"],
                fill=self._hex_to_rgb(sentiment_color)
            )
        
        # Hashtags
        if config.hashtags:
            hashtags_text = " ".join([f"#{tag}" for tag in config.hashtags[:6]])
            draw.text(
                (40, config.height - 80),
                hashtags_text,
                font=self.fonts["tiny"],
                fill=self._hex_to_rgb(BrandColors.PRIMARY)
            )
        
        return img
    
    def generate_quote(self, config: ImageConfig) -> "Image.Image":
        """Gera imagem de citação/dica."""
        img = self._create_gradient_background(config.width, config.height)
        draw = ImageDraw.Draw(img)
        
        # Aspas grandes decorativas
        draw.text(
            (40, 150),
            """,
            font=self.fonts["huge"],
            fill=self._hex_to_rgb(BrandColors.PRIMARY)
        )
        
        # Citação
        y_pos = 350
        if config.body:
            words = config.body.split()
            lines = []
            current_line = []
            for word in words:
                current_line.append(word)
                test_line = " ".join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=self.fonts["subtitle"])
                if bbox[2] > config.width - 120:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))
            
            for line in lines[:5]:
                draw.text(
                    (config.width // 2, y_pos),
                    line,
                    font=self.fonts["subtitle"],
                    fill=self._hex_to_rgb(BrandColors.TEXT_PRIMARY),
                    anchor="mm"
                )
                y_pos += 65
        
        # Aspas finais
        draw.text(
            (config.width - 100, y_pos),
            """,
            font=self.fonts["huge"],
            fill=self._hex_to_rgb(BrandColors.PRIMARY)
        )
        
        # Logo
        img = self._add_logo(img, "bottom-left")
        
        # Hashtags
        if config.hashtags:
            hashtags_text = " ".join([f"#{tag}" for tag in config.hashtags[:4]])
            draw.text(
                (config.width - 40, config.height - 60),
                hashtags_text,
                font=self.fonts["tiny"],
                fill=self._hex_to_rgb(BrandColors.PRIMARY),
                anchor="rm"
            )
        
        return img
    
    def generate(self, config: ImageConfig) -> "Image.Image":
        """
        Gera imagem baseada no template configurado.
        
        Args:
            config: Configuração da imagem
            
        Returns:
            Imagem PIL
        """
        generators = {
            ImageTemplate.MARKET_ALERT: self.generate_market_alert,
            ImageTemplate.DAILY_SUMMARY: self.generate_daily_summary,
            ImageTemplate.NEWS_HIGHLIGHT: self.generate_news_highlight,
            ImageTemplate.QUOTE: self.generate_quote,
        }
        
        generator = generators.get(config.template, self.generate_market_alert)
        return generator(config)
    
    def save(
        self,
        image: Image.Image,
        filename: Optional[str] = None,
        format: str = "PNG"
    ) -> Path:
        """
        Salva imagem em arquivo.
        
        Args:
            image: Imagem PIL
            filename: Nome do arquivo (opcional)
            format: Formato (PNG, JPEG)
            
        Returns:
            Path do arquivo salvo
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"post_{timestamp}.{format.lower()}"
        
        filepath = self.output_dir / filename
        image.save(filepath, format=format, quality=95)
        
        return filepath
    
    def to_bytes(self, image: Image.Image, format: str = "PNG") -> bytes:
        """
        Converte imagem para bytes.
        
        Args:
            image: Imagem PIL
            format: Formato
            
        Returns:
            Bytes da imagem
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format, quality=95)
        buffer.seek(0)
        return buffer.getvalue()
