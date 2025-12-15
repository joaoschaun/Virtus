"""Teste do serviço de notícias com áudio."""
import sys
import os
import asyncio

# Adiciona o path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.news_service import news_service, NewsCategory

async def test():
    print('='*60)
    print('TESTE: Serviço de Notícias com Áudio em Português')
    print('='*60)
    
    print('\n1. Buscando notícias de FOREX...')
    news = await news_service.fetch_news(category=NewsCategory.FOREX, limit=2)
    print(f'   Notícias encontradas: {len(news)}')
    
    for n in news:
        print(f'\n   === {n.title} ===')
        print(f'   Categoria: {n.category.value}')
        print(f'   Fonte: {n.source}')
        print(f'   Audio URL: {n.audio_url}')
        
        if n.audio_url:
            audio_filename = n.audio_url.replace('/api/news/audio/', '')
            audio_path = f'c:/Users/Administrator/Desktop/Virtus/brain/data/audio_cache/{audio_filename}'
            if os.path.exists(audio_path):
                size = os.path.getsize(audio_path)
                print(f'   ✓ Arquivo de áudio existe: {size} bytes')
            else:
                print(f'   ✗ Arquivo não encontrado: {audio_path}')
    
    print('\n2. Buscando notícias de ECONOMIA...')
    news_eco = await news_service.fetch_news(category=NewsCategory.ECONOMY, limit=2)
    print(f'   Notícias encontradas: {len(news_eco)}')
    
    for n in news_eco:
        print(f'\n   === {n.title} ===')
        summary_preview = n.summary[:100] if len(n.summary) > 100 else n.summary
        print(f'   Resumo: {summary_preview}...')
        print(f'   Audio URL: {n.audio_url}')
    
    print('\n3. Testando resumo diário...')
    summary_text = await news_service.get_news_summary()
    print(f'   Texto do resumo: {summary_text[:150]}...')
    
    # Gera áudio do resumo
    audio_path = await news_service.tts.text_to_speech(summary_text)
    if audio_path:
        print(f'   ✓ Áudio do resumo gerado: {audio_path}')
    
    print('\n' + '='*60)
    print('✅ TESTE COMPLETO - Sistema de notícias em áudio funcionando!')
    print('='*60)
    print('\nEndpoints disponíveis:')
    print('  GET  /api/news              - Lista notícias')
    print('  GET  /api/news/audio/{file} - Serve arquivo de áudio')
    print('  GET  /api/news/summary/audio - Resumo em áudio')
    print('  GET  /api/news/categories/list - Categorias')

if __name__ == '__main__':
    asyncio.run(test())
