"""
Teste do Sistema de Social Media
================================

Gera posts de exemplo para visualização.
"""

import sys
from pathlib import Path

# Setup paths
BRAIN_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(BRAIN_PATH))

from src.social import (
    ContentGenerator,
    ImageGenerator,
    ImageConfig,
    PostType,
)


def test_image_generation():
    """Testa geração de imagens."""
    print("=" * 50)
    print("TESTE DE GERAÇÃO DE IMAGENS")
    print("=" * 50)
    
    # Cria diretório de output
    output_dir = BRAIN_PATH / "data" / "social_media" / "test_images"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Inicializa gerador
    assets_dir = BRAIN_PATH / "dashboard" / "frontend" / "public"
    generator = ImageGenerator(assets_dir=assets_dir)
    
    # 1. Market Alert - Alta
    print("\n1. Gerando Market Alert (Alta)...")
    config = ImageConfig(
        title="ALERTA | XAUUSD",
        symbol="XAUUSD",
        trend="bullish",
        price=2650.50,
        support=2620.00,
        resistance=2680.00,
        hashtags=["VirtusInvestimentos", "Gold", "Trading"],
    )
    image = generator.generate_market_alert(config)
    path = output_dir / "market_alert_bullish.png"
    generator.save(image, path)
    print(f"   ✓ Salvo em: {path}")
    
    # 2. Market Alert - Baixa
    print("\n2. Gerando Market Alert (Baixa)...")
    config = ImageConfig(
        title="ALERTA | EURUSD",
        symbol="EURUSD",
        trend="bearish",
        price=1.0842,
        support=1.0800,
        resistance=1.0900,
        hashtags=["VirtusInvestimentos", "Forex", "Trading"],
    )
    image = generator.generate_market_alert(config)
    path = output_dir / "market_alert_bearish.png"
    generator.save(image, path)
    print(f"   ✓ Salvo em: {path}")
    
    # 3. News Highlight
    print("\n3. Gerando News Highlight...")
    config = ImageConfig(
        title="Fed Mantém Taxa de Juros",
        body="O Federal Reserve decidiu manter as taxas de juros inalteradas, "
             "sinalizando cautela com a inflação. Mercados reagem positivamente.",
        trend="bullish",
    )
    image = generator.generate_news_highlight(config)
    path = output_dir / "news_highlight.png"
    generator.save(image, path)
    print(f"   ✓ Salvo em: {path}")
    
    # 4. Daily Summary
    print("\n4. Gerando Daily Summary...")
    config = ImageConfig(
        title="Resumo do Dia",
        body="""📈 XAUUSD: +1.25%
📉 EURUSD: -0.45%
📈 GBPUSD: +0.32%

🟢 Mercado com viés positivo""",
    )
    image = generator.generate_daily_summary(config)
    path = output_dir / "daily_summary.png"
    generator.save(image, path)
    print(f"   ✓ Salvo em: {path}")
    
    # 5. Quote/Tip
    print("\n5. Gerando Trading Tip...")
    config = ImageConfig(
        title="Dica do Dia",
        body="Nunca arrisque mais de 2% do seu capital em uma única operação. "
             "A gestão de risco é o que separa traders profissionais de amadores.",
    )
    image = generator.generate_quote(config)
    path = output_dir / "trading_tip.png"
    generator.save(image, path)
    print(f"   ✓ Salvo em: {path}")
    
    print("\n" + "=" * 50)
    print(f"✓ Todas as imagens geradas em: {output_dir}")
    print("=" * 50)


def test_content_generation():
    """Testa geração de conteúdo."""
    print("\n" + "=" * 50)
    print("TESTE DE GERAÇÃO DE CONTEÚDO")
    print("=" * 50)
    
    generator = ContentGenerator()
    
    # 1. Market Alert
    print("\n1. Market Alert:")
    content = generator.generate_market_alert(
        symbol="XAUUSD",
        trend="bullish",
        price=2650.50,
        support=2620.00,
        resistance=2680.00,
    )
    print(f"   Título: {content.title}")
    print(f"   Tipo: {content.post_type.value}")
    print(f"   Prioridade: {content.priority}")
    print(f"   Hashtags: {len(content.hashtags)} tags")
    
    # 2. News Post
    print("\n2. News Post:")
    content = generator.generate_news_post(
        title="Fed Mantém Taxa de Juros",
        summary="O Federal Reserve decidiu manter as taxas de juros inalteradas.",
        sentiment="bullish",
        related_symbols=["XAUUSD", "EURUSD"],
    )
    print(f"   Título: {content.title}")
    print(f"   Sentimento: {content.sentiment}")
    
    # 3. Daily Summary
    print("\n3. Daily Summary:")
    content = generator.generate_daily_summary(
        highlights=[
            {"symbol": "XAUUSD", "change": 1.25},
            {"symbol": "EURUSD", "change": -0.45},
            {"symbol": "GBPUSD", "change": 0.32},
        ],
        market_sentiment="bullish",
    )
    print(f"   Título: {content.title}")
    
    # 4. Trading Tip
    print("\n4. Trading Tip:")
    content = generator.generate_trading_tip()
    print(f"   Título: {content.title}")
    print(f"   Body: {content.body[:80]}...")
    
    # 5. Educational
    print("\n5. Educational:")
    content = generator.generate_educational()
    print(f"   Título: {content.title}")
    print(f"   Body: {content.body[:80]}...")
    
    print("\n" + "=" * 50)
    print("✓ Todos os conteúdos gerados com sucesso!")
    print("=" * 50)


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 60)
    print("     VIRTUS - TESTE DO SISTEMA DE SOCIAL MEDIA")
    print("=" * 60)
    
    try:
        test_content_generation()
    except Exception as e:
        print(f"\n❌ Erro na geração de conteúdo: {e}")
    
    try:
        test_image_generation()
    except Exception as e:
        print(f"\n❌ Erro na geração de imagens: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("     TESTES CONCLUÍDOS")
    print("=" * 60)


if __name__ == "__main__":
    main()
