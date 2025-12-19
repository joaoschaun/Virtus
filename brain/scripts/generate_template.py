"""
VIRTUS - Gerador de Template PNG com Fundo Transparente
=======================================================

Gera template base para posts de redes sociais com fundo transparente.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

# Cores da marca
class BrandColors:
    PRIMARY = "#E53935"
    PRIMARY_LIGHT = "#FF5252"
    BACKGROUND_DARK = "#0D0D0D"
    BACKGROUND_CARD = "#1A1A1A"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B0B0B0"
    TEXT_MUTED = "#666666"
    SUCCESS = "#4CAF50"
    DANGER = "#F44336"
    WARNING = "#FF9800"


def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    """Converte cor hex para RGBA."""
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def draw_rounded_rect(draw, coords, radius, fill_color, alpha=255):
    """Desenha retângulo com cantos arredondados."""
    x1, y1, x2, y2 = coords
    color = hex_to_rgba(fill_color, alpha) if isinstance(fill_color, str) else fill_color
    
    # Retângulo principal
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=color)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=color)
    
    # Cantos arredondados
    draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=color)
    draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=color)
    draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=color)
    draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=color)


def load_fonts():
    """Carrega fontes."""
    fonts = {}
    try:
        if os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
            fonts["title"] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 72)
            fonts["subtitle"] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 48)
            fonts["body"] = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
            fonts["small"] = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
            fonts["tiny"] = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
            fonts["huge"] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 96)
        else:
            for key in ["title", "subtitle", "body", "small", "tiny", "huge"]:
                fonts[key] = ImageFont.load_default()
    except:
        for key in ["title", "subtitle", "body", "small", "tiny", "huge"]:
            fonts[key] = ImageFont.load_default()
    return fonts


def generate_news_template(output_path: Path, include_placeholders: bool = True):
    """
    Gera template de notícia com fundo transparente.
    
    Args:
        output_path: Caminho para salvar o template
        include_placeholders: Se True, inclui textos de exemplo
    """
    width, height = 1080, 1080
    
    # Imagem com canal alpha (transparente)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fonts = load_fonts()
    
    # ==================== ELEMENTOS DO TEMPLATE ====================
    
    # 1. Fundo semi-transparente (overlay escuro)
    overlay_alpha = 220  # 0-255 (220 = bem escuro mas não totalmente opaco)
    draw_rounded_rect(draw, (0, 0, width, height), 0, BrandColors.BACKGROUND_DARK, overlay_alpha)
    
    # 2. Linha decorativa superior (vermelha Virtus)
    draw.rectangle([0, 0, width, 6], fill=hex_to_rgba(BrandColors.PRIMARY))
    
    # 3. Área do logo (canto superior esquerdo) - apenas placeholder
    logo_area = (40, 30, 200, 90)
    draw.rectangle(logo_area, outline=hex_to_rgba(BrandColors.PRIMARY, 100), width=1)
    if include_placeholders:
        draw.text((45, 45), "LOGO", font=fonts["small"], fill=hex_to_rgba(BrandColors.TEXT_MUTED))
    
    # 4. Badge "NOTÍCIA" (canto superior direito)
    badge_text = "📰 NOTÍCIA DO MERCADO"
    badge_x = width - 380
    badge_y = 50
    badge_width = 340
    badge_height = 45
    draw_rounded_rect(draw, (badge_x, badge_y, badge_x + badge_width, badge_y + badge_height), 
                      20, BrandColors.PRIMARY)
    draw.text(
        (badge_x + badge_width // 2, badge_y + badge_height // 2),
        badge_text,
        font=fonts["small"],
        fill=hex_to_rgba(BrandColors.TEXT_PRIMARY),
        anchor="mm"
    )
    
    # 5. Linha de accent (abaixo do badge)
    accent_y = 130
    draw.rectangle([40, accent_y, 120, accent_y + 4], fill=hex_to_rgba(BrandColors.PRIMARY))
    
    # 6. Área do título
    title_y = 160
    if include_placeholders:
        draw.text(
            (40, title_y),
            "[TÍTULO DA NOTÍCIA]",
            font=fonts["title"],
            fill=hex_to_rgba(BrandColors.TEXT_PRIMARY)
        )
        draw.text(
            (40, title_y + 80),
            "[Segunda linha do título]",
            font=fonts["title"],
            fill=hex_to_rgba(BrandColors.TEXT_PRIMARY)
        )
    
    # 7. Área do corpo/resumo
    body_y = 380
    if include_placeholders:
        draw.text(
            (40, body_y),
            "[Resumo da notícia - linha 1]",
            font=fonts["body"],
            fill=hex_to_rgba(BrandColors.TEXT_SECONDARY)
        )
        draw.text(
            (40, body_y + 50),
            "[Resumo da notícia - linha 2]",
            font=fonts["body"],
            fill=hex_to_rgba(BrandColors.TEXT_SECONDARY)
        )
        draw.text(
            (40, body_y + 100),
            "[Resumo da notícia - linha 3]",
            font=fonts["body"],
            fill=hex_to_rgba(BrandColors.TEXT_SECONDARY)
        )
    
    # 8. Card de impacto/sentimento
    card_y = 580
    card_height = 120
    draw_rounded_rect(draw, (40, card_y, width - 40, card_y + card_height), 
                      15, BrandColors.BACKGROUND_CARD, 200)
    
    if include_placeholders:
        # Ícone de impacto
        draw.text(
            (80, card_y + 35),
            "⚡",
            font=fonts["subtitle"],
            fill=hex_to_rgba(BrandColors.WARNING)
        )
        draw.text(
            (140, card_y + 25),
            "IMPACTO NO MERCADO",
            font=fonts["tiny"],
            fill=hex_to_rgba(BrandColors.TEXT_MUTED)
        )
        draw.text(
            (140, card_y + 55),
            "[Positivo / Negativo / Neutro]",
            font=fonts["body"],
            fill=hex_to_rgba(BrandColors.WARNING)
        )
    
    # 9. Área de símbolos relacionados
    symbols_y = 730
    if include_placeholders:
        draw.text(
            (40, symbols_y),
            "Símbolos: XAUUSD • EURUSD • GBPUSD",
            font=fonts["small"],
            fill=hex_to_rgba(BrandColors.TEXT_MUTED)
        )
    
    # 10. Linha separadora do rodapé
    footer_line_y = 850
    draw.rectangle([40, footer_line_y, width - 40, footer_line_y + 2], 
                   fill=hex_to_rgba(BrandColors.PRIMARY, 150))
    
    # 11. Área de hashtags
    hashtags_y = 880
    if include_placeholders:
        draw.text(
            (40, hashtags_y),
            "#Forex #Trading #Notícias #VirtusInvestimentos",
            font=fonts["tiny"],
            fill=hex_to_rgba(BrandColors.PRIMARY, 200)
        )
    
    # 12. Call to action
    cta_y = 930
    if include_placeholders:
        draw.text(
            (40, cta_y),
            "🔔 Acompanhe a Virtus para análises em tempo real!",
            font=fonts["small"],
            fill=hex_to_rgba(BrandColors.TEXT_SECONDARY)
        )
    
    # 13. Website/timestamp (canto inferior direito)
    draw.text(
        (width - 50, height - 40),
        "virtusinvestimentos.com.br",
        font=fonts["tiny"],
        fill=hex_to_rgba(BrandColors.TEXT_MUTED),
        anchor="ra"
    )
    
    # Salva a imagem
    img.save(output_path, "PNG")
    print(f"✅ Template salvo em: {output_path}")
    return img


def generate_clean_template(output_path: Path):
    """Gera template limpo sem textos placeholder."""
    return generate_news_template(output_path, include_placeholders=False)


def generate_frame_only(output_path: Path):
    """
    Gera apenas o frame/moldura com fundo 100% transparente.
    Útil para overlay em outras imagens.
    """
    width, height = 1080, 1080
    
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fonts = load_fonts()
    
    # Apenas elementos decorativos (moldura)
    
    # Linha superior vermelha
    draw.rectangle([0, 0, width, 6], fill=hex_to_rgba(BrandColors.PRIMARY))
    
    # Linha inferior vermelha
    draw.rectangle([0, height - 6, width, height], fill=hex_to_rgba(BrandColors.PRIMARY))
    
    # Linha de accent
    draw.rectangle([40, 130, 120, 134], fill=hex_to_rgba(BrandColors.PRIMARY))
    
    # Linha separadora do rodapé
    draw.rectangle([40, 850, width - 40, 852], fill=hex_to_rgba(BrandColors.PRIMARY, 150))
    
    # Badge VIRTUS (canto superior esquerdo)
    badge_height = 50
    draw_rounded_rect(draw, (40, 30, 220, 30 + badge_height), 25, BrandColors.PRIMARY)
    draw.text(
        (130, 30 + badge_height // 2),
        "VIRTUS",
        font=fonts["subtitle"],
        fill=hex_to_rgba(BrandColors.TEXT_PRIMARY),
        anchor="mm"
    )
    
    # Website
    draw.text(
        (width - 50, height - 40),
        "virtusinvestimentos.com.br",
        font=fonts["tiny"],
        fill=hex_to_rgba(BrandColors.TEXT_MUTED),
        anchor="ra"
    )
    
    img.save(output_path, "PNG")
    print(f"✅ Frame salvo em: {output_path}")
    return img


if __name__ == "__main__":
    output_dir = Path(__file__).parent.parent / "data" / "templates"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Gera templates
    print("\n🎨 Gerando templates Virtus...\n")
    
    # 1. Template completo com placeholders
    generate_news_template(output_dir / "news_template_with_placeholders.png", include_placeholders=True)
    
    # 2. Template limpo (sem textos)
    generate_clean_template(output_dir / "news_template_clean.png")
    
    # 3. Apenas moldura (fundo 100% transparente)
    generate_frame_only(output_dir / "virtus_frame_overlay.png")
    
    print(f"\n✅ Templates salvos em: {output_dir}")
    print("\nArquivos gerados:")
    for f in output_dir.glob("*.png"):
        print(f"  - {f.name}")
