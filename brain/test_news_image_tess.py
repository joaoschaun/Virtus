"""
Teste da geração de imagens de notícias com TESS AI e overlay Virtus.
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o path do brain
BRAIN_PATH = Path(__file__).parent
sys.path.insert(0, str(BRAIN_PATH))

from src.integrations.tess.image_generator import (
    TessImageGenerator, NewsData, ImageSize
)

async def test_news_image():
    """Testa geração de imagem de notícia"""
    
    print("=" * 60)
    print("🧪 TESTE: Geração de Imagem de Notícia TESS + Overlay")
    print("=" * 60)
    
    # Simula uma notícia real
    news_data = NewsData(
        title="Fed mantém taxa de juros e sinaliza cortes em 2025",
        summary="O Federal Reserve decidiu manter a taxa de juros entre 4,25% e 4,50% na última reunião do ano. Jerome Powell indicou que o banco central está preparado para iniciar um ciclo de cortes graduais a partir do primeiro trimestre de 2025, dependendo dos dados de inflação.",
        sentiment="positive",
        impact="high",
        symbols=["EURUSD", "XAUUSD", "US30"],
        source="Reuters"
    )
    
    # Define caminho de saída
    save_path = BRAIN_PATH / "data" / "social_media" / "test_news_tess.png"
    
    print("\n📰 Dados da Notícia:")
    print(f"   Título: {news_data.title}")
    print(f"   Sentimento: {news_data.sentiment}")
    print(f"   Impacto: {news_data.impact}")
    print(f"   Símbolos: {news_data.symbols}")
    print(f"   Fonte: {news_data.source}")
    
    print("\n⏳ Gerando imagem com TESS AI...")
    
    async with TessImageGenerator() as generator:
        result = await generator.generate_news_with_overlay(
            news=news_data,
            save_path=save_path
        )
    
    if result:
        # Verifica o arquivo
        if save_path.exists():
            size_kb = save_path.stat().st_size / 1024
            print(f"\n✅ SUCESSO!")
            print(f"   Arquivo: {save_path.name}")
            print(f"   Tamanho: {size_kb:.2f} KB")
            print(f"   Path: {save_path}")
        else:
            print(f"\n❌ ERRO: Arquivo não encontrado")
    else:
        print(f"\n❌ ERRO: Geração retornou None")
    
    # Teste com notícia bearish
    print("\n" + "=" * 60)
    print("🧪 TESTE 2: Notícia Bearish")
    print("=" * 60)
    
    news_bearish = NewsData(
        title="Ouro dispara com tensões geopolíticas no Oriente Médio",
        summary="O preço do ouro atingiu nova máxima histórica acima de $2,100 por onça, impulsionado pelo aumento das tensões geopolíticas. Investidores buscam ativos de refúgio em meio à incerteza global.",
        sentiment="negative",
        impact="high",
        symbols=["XAUUSD", "USDJPY"],
        source="Bloomberg"
    )
    
    save_path_2 = BRAIN_PATH / "data" / "social_media" / "test_news_bearish.png"
    
    print("\n📰 Dados da Notícia:")
    print(f"   Título: {news_bearish.title}")
    print(f"   Sentimento: {news_bearish.sentiment}")
    print(f"   Impacto: {news_bearish.impact}")
    
    print("\n⏳ Gerando imagem...")
    
    async with TessImageGenerator() as generator:
        result = await generator.generate_news_with_overlay(
            news=news_bearish,
            save_path=save_path_2
        )
    
    if result and save_path_2.exists():
        size_kb = save_path_2.stat().st_size / 1024
        print(f"\n✅ SUCESSO!")
        print(f"   Arquivo: {save_path_2.name}")
        print(f"   Tamanho: {size_kb:.2f} KB")
    else:
        print(f"\n❌ ERRO na geração bearish")
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_news_image())
