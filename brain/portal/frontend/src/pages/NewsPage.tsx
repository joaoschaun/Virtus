import { useState, useEffect } from 'react'
import { Newspaper, RefreshCw, ExternalLink, Filter } from 'lucide-react'

interface NewsItem {
  id: string
  title: string
  summary: string
  content?: string
  source: string
  category: string
  sentiment: string
  published_at: string
  image_url?: string
  url?: string
}

const NewsPage = () => {
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    fetchNews()
  }, [filter])

  const fetchNews = async () => {
    setLoading(true)
    try {
      const category = filter !== 'all' ? `&category=${filter}` : ''
      const response = await fetch(`/api/portal/news?limit=30${category}`)
      const data = await response.json()
      if (data.success) {
        setNews(data.data)
      }
    } catch (error) {
      console.error('Erro ao buscar notícias:', error)
    } finally {
      setLoading(false)
    }
  }

  const categories = [
    { value: 'all', label: 'Todas' },
    { value: 'forex', label: 'Forex' },
    { value: 'stocks_br', label: 'Ações Brasil' },
    { value: 'commodities', label: 'Commodities' },
  ]

  const getSentimentBadge = (sentiment: string) => {
    if (sentiment === 'bullish') return { color: 'bg-virtus-accent-success/20 text-virtus-accent-success', label: 'Alta' }
    if (sentiment === 'bearish') return { color: 'bg-virtus-accent-danger/20 text-virtus-accent-danger', label: 'Baixa' }
    return { color: 'bg-virtus-bg-tertiary text-virtus-text-muted', label: 'Neutro' }
  }

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('pt-BR', { 
        day: '2-digit', 
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-virtus-text-primary flex items-center gap-3">
            <Newspaper className="w-8 h-8 text-virtus-accent-primary" />
            Notícias do Mercado
          </h1>
          <p className="text-virtus-text-secondary mt-2">
            Últimas notícias de forex, ações e economia
          </p>
        </div>

        <button
          onClick={fetchNews}
          className="flex items-center gap-2 px-4 py-2 bg-virtus-accent-primary/10 text-virtus-accent-primary rounded-lg hover:bg-virtus-accent-primary/20 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="w-4 h-4 text-virtus-text-muted" />
        {categories.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setFilter(cat.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filter === cat.value
                ? 'bg-virtus-accent-primary text-white'
                : 'bg-virtus-bg-card text-virtus-text-secondary hover:bg-virtus-bg-hover'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* News Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-8 h-8 text-virtus-accent-primary animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {news.map((item) => {
            const sentiment = getSentimentBadge(item.sentiment)
            return (
              <a
                key={item.id}
                href={item.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="news-card rounded-xl overflow-hidden card-hover group"
              >
                {item.image_url && (
                  <div className="aspect-video overflow-hidden">
                    <img
                      src={item.image_url}
                      alt=""
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      onError={(e) => (e.currentTarget.parentElement!.style.display = 'none')}
                    />
                  </div>
                )}
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${sentiment.color}`}>
                      {sentiment.label}
                    </span>
                    <span className="text-virtus-text-muted text-xs">{item.source}</span>
                  </div>
                  
                  <h3 className="text-virtus-text-primary font-medium line-clamp-2 group-hover:text-virtus-accent-primary transition-colors mb-2">
                    {item.title}
                  </h3>
                  
                  <p className="text-virtus-text-secondary text-sm line-clamp-3 mb-4">
                    {item.summary}
                  </p>
                  
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-virtus-text-muted">{formatDate(item.published_at)}</span>
                    <ExternalLink className="w-4 h-4 text-virtus-text-muted group-hover:text-virtus-accent-primary transition-colors" />
                  </div>
                </div>
              </a>
            )
          })}
        </div>
      )}

      {!loading && news.length === 0 && (
        <div className="text-center py-20">
          <Newspaper className="w-12 h-12 text-virtus-text-muted mx-auto mb-4" />
          <p className="text-virtus-text-secondary">Nenhuma notícia encontrada</p>
        </div>
      )}
    </div>
  )
}

export default NewsPage
