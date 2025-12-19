import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  TrendingUp,
  TrendingDown,
  Newspaper,
  AlertTriangle,
  Clock,
  ChevronRight,
  RefreshCw,
  Globe,
  BarChart3
} from 'lucide-react'

interface MarketIndex {
  symbol: string
  name: string
  price: number
  change: number
  change_percent: number
}

interface NewsItem {
  id: string
  title: string
  summary: string
  source: string
  category: string
  sentiment: string
  published_at: string
  image_url?: string
  url?: string
}

interface EconomicEvent {
  time: string
  time_brazil: string
  country: string
  event: string
  impact: string
  actual?: string
  forecast?: string
  previous?: string
}

interface HomeData {
  market: {
    indices: Record<string, MarketIndex>
    brazil_stocks: MarketIndex[]
  }
  news: {
    latest: NewsItem[]
  }
  calendar: {
    today: EconomicEvent[]
    high_impact: EconomicEvent[]
  }
  summary: {
    market_status: string
    sentiment: {
      overall: string
      bullish: number
      bearish: number
      neutral: number
    }
  }
}

const HomePage = () => {
  const [data, setData] = useState<HomeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 300000) // 5 minutos
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const response = await fetch('/api/portal/home')
      const result = await response.json()
      if (result.success) {
        setData(result)
        setLastUpdate(new Date())
      }
    } catch (error) {
      console.error('Erro ao buscar dados:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatPrice = (price: number | string, symbol: string) => {
    const numPrice = typeof price === 'string' ? parseFloat(price) : price
    if (!numPrice && numPrice !== 0) return '---'
    if (symbol === 'bitcoin') return `$${numPrice.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`
    if (['dolar', 'euro'].includes(symbol)) return `R$ ${numPrice.toFixed(4)}`
    if (['ibovespa', 'sp500', 'nasdaq', 'dow_jones'].includes(symbol)) return numPrice.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
    if (symbol === 'ouro') return `$${numPrice.toFixed(2)}`
    return numPrice.toFixed(2)
  }

  const formatChangePercent = (value: number | string) => {
    const num = typeof value === 'string' ? parseFloat(value) : value
    if (isNaN(num)) return '0.00'
    return num.toFixed(2)
  }

  const isPositive = (value: number | string) => {
    const num = typeof value === 'string' ? parseFloat(value) : value
    return num >= 0
  }

  const getCountryFlag = (country: string) => {
    const flags: Record<string, string> = {
      'US': '🇺🇸',
      'BR': '🇧🇷',
      'EU': '🇪🇺',
      'GB': '🇬🇧',
      'JP': '🇯🇵',
      'CN': '🇨🇳',
      'DE': '🇩🇪',
      'FR': '🇫🇷',
    }
    return flags[country] || '🌍'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-virtus-accent-primary animate-spin mx-auto mb-4" />
          <p className="text-virtus-text-muted">Carregando dados do mercado...</p>
        </div>
      </div>
    )
  }

  const indices = data?.market?.indices || {}
  const stocks = data?.market?.brazil_stocks || []
  const news = data?.news?.latest || []
  const highImpactEvents = data?.calendar?.high_impact || []
  const marketStatus = data?.summary?.market_status || 'Mercado fechado'
  const sentiment = data?.summary?.sentiment || { overall: 'neutral', bullish: 0, bearish: 0, neutral: 0 }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero Banner Section */}
      <div className="relative -mx-4 md:-mx-8 lg:-mx-16 -mt-8 overflow-hidden">
        {/* Background Image with Overlay */}
        <div 
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: 'url(/banner-hero.jpg)' }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-virtus-bg-primary/95 via-virtus-bg-primary/80 to-virtus-bg-primary/60" />
        <div className="absolute inset-0 bg-gradient-to-t from-virtus-bg-primary via-transparent to-transparent" />
        
        {/* Content */}
        <div className="relative z-10 py-16 md:py-24 px-4 md:px-8 lg:px-16">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-virtus-accent-primary/20 border border-virtus-accent-primary/30 rounded-full px-4 py-1.5 mb-6">
              <span className="w-2 h-2 bg-virtus-accent-primary rounded-full animate-pulse" />
              <span className="text-virtus-accent-primary text-sm font-medium">Dados em Tempo Real</span>
            </div>
            
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight">
              Inteligência para o
              <span className="text-gradient-red block">Mercado Financeiro</span>
            </h1>
            
            <p className="text-virtus-text-secondary text-lg md:text-xl max-w-2xl mb-8">
              Acompanhe cotações, notícias e eventos econômicos em tempo real. 
              Análises profissionais para decisões mais inteligentes.
            </p>
            
            <div className="flex flex-wrap gap-4">
              <a 
                href="https://dashboard.virtusinvestimentos.com.br" 
                className="inline-flex items-center gap-2 bg-virtus-accent-primary hover:bg-virtus-accent-primary-hover text-white px-6 py-3 rounded-xl font-semibold transition-all shadow-lg shadow-virtus-accent-primary/25 hover:shadow-virtus-accent-primary/40"
              >
                Acessar Dashboard
                <ChevronRight className="w-5 h-5" />
              </a>
              <a 
                href="#cotacoes" 
                className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white px-6 py-3 rounded-xl font-semibold transition-all border border-white/20"
              >
                Ver Cotações
                <TrendingUp className="w-5 h-5" />
              </a>
            </div>
          </div>
          
          {lastUpdate && (
            <p className="text-virtus-text-muted text-sm mt-8 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Última atualização: {lastUpdate.toLocaleTimeString('pt-BR')}
            </p>
          )}
        </div>
      </div>

      {/* Market Status Banner */}
      <div className={`p-4 rounded-xl border ${
        sentiment.overall === 'bullish' 
          ? 'bg-virtus-accent-success/10 border-virtus-accent-success/30' 
          : sentiment.overall === 'bearish'
          ? 'bg-virtus-accent-danger/10 border-virtus-accent-danger/30'
          : 'bg-virtus-accent-primary/10 border-virtus-accent-primary/30'
      }`}>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full pulse-live ${
              sentiment.overall === 'bullish' ? 'bg-virtus-accent-success' 
              : sentiment.overall === 'bearish' ? 'bg-virtus-accent-danger' 
              : 'bg-virtus-accent-primary'
            }`} />
            <span className="text-virtus-text-primary font-medium">{marketStatus}</span>
          </div>
          <div className="flex items-center gap-6 text-sm">
            <span className="text-virtus-accent-success">📈 {sentiment.bullish} alta</span>
            <span className="text-virtus-accent-danger">📉 {sentiment.bearish} baixa</span>
            <span className="text-virtus-text-muted">➡️ {sentiment.neutral} neutro</span>
          </div>
        </div>
      </div>

      {/* Indices Grid */}
      <section id="cotacoes">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-virtus-text-primary flex items-center gap-3">
            <Globe className="w-6 h-6 text-virtus-accent-primary" />
            Índices Globais
          </h2>
          <Link 
            to="/cotacoes" 
            className="text-virtus-accent-primary hover:text-virtus-accent-secondary text-sm flex items-center gap-1"
          >
            Ver todos <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(indices).slice(0, 8).map(([key, index]) => (
            <div 
              key={key}
              className="bg-virtus-bg-card rounded-xl p-4 border border-virtus-border-primary card-hover"
            >
              <p className="text-virtus-text-muted text-sm mb-1">{index.name}</p>
              <p className="text-xl font-bold text-virtus-text-primary">
                {formatPrice(index.price, key)}
              </p>
              <div className={`flex items-center gap-1 mt-2 text-sm ${
                isPositive(index.change_percent) ? 'text-virtus-accent-success' : 'text-virtus-accent-danger'
              }`}>
                {isPositive(index.change_percent) ? (
                  <TrendingUp className="w-4 h-4" />
                ) : (
                  <TrendingDown className="w-4 h-4" />
                )}
                <span>{isPositive(index.change_percent) ? '+' : ''}{formatChangePercent(index.change_percent)}%</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Main Grid - News & Calendar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* News Section */}
        <section className="lg:col-span-2">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-virtus-text-primary flex items-center gap-3">
              <Newspaper className="w-6 h-6 text-virtus-accent-primary" />
              Últimas Notícias
            </h2>
            <Link 
              to="/noticias" 
              className="text-virtus-accent-primary hover:text-virtus-accent-secondary text-sm flex items-center gap-1"
            >
              Ver todas <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="space-y-4">
            {news.slice(0, 5).map((item) => (
              <a
                key={item.id}
                href={item.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="block news-card rounded-xl p-4 card-hover"
              >
                <div className="flex gap-4">
                  {item.image_url && (
                    <img 
                      src={item.image_url} 
                      alt=""
                      className="w-24 h-24 rounded-lg object-cover flex-shrink-0"
                      onError={(e) => (e.currentTarget.style.display = 'none')}
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`w-2 h-2 rounded-full ${
                        item.sentiment === 'bullish' ? 'bg-virtus-accent-success' 
                        : item.sentiment === 'bearish' ? 'bg-virtus-accent-danger' 
                        : 'bg-virtus-text-muted'
                      }`} />
                      <span className="text-virtus-text-muted text-xs">{item.source}</span>
                      <span className="text-virtus-text-muted text-xs">•</span>
                      <span className="text-virtus-text-muted text-xs capitalize">{item.category}</span>
                    </div>
                    <h3 className="text-virtus-text-primary font-medium line-clamp-2 hover:text-virtus-accent-primary transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-virtus-text-secondary text-sm mt-2 line-clamp-2">
                      {item.summary}
                    </p>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </section>

        {/* Sidebar - Calendar & Stocks */}
        <aside className="space-y-8">
          {/* High Impact Events */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-virtus-text-primary flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-virtus-accent-danger" />
                Alto Impacto Hoje
              </h3>
              <Link 
                to="/calendario" 
                className="text-virtus-accent-primary text-sm hover:text-virtus-accent-secondary"
              >
                Ver mais
              </Link>
            </div>

            <div className="bg-virtus-bg-card rounded-xl border border-virtus-accent-danger/20 overflow-hidden">
              {highImpactEvents.length > 0 ? (
                <div className="divide-y divide-virtus-border-primary">
                  {highImpactEvents.slice(0, 5).map((event, index) => (
                    <div key={index} className="p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">{getCountryFlag(event.country)}</span>
                        <span className="text-virtus-accent-primary font-mono text-sm">
                          {event.time_brazil}
                        </span>
                      </div>
                      <p className="text-virtus-text-primary text-sm line-clamp-2">{event.event}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center text-virtus-text-muted text-sm">
                  Sem eventos de alto impacto hoje
                </div>
              )}
            </div>
          </div>

          {/* Brazil Stocks */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-virtus-text-primary flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-virtus-accent-primary" />
                Ações Brasil
              </h3>
              <Link 
                to="/cotacoes" 
                className="text-virtus-accent-primary text-sm hover:text-virtus-accent-secondary"
              >
                Ver mais
              </Link>
            </div>

            <div className="bg-virtus-bg-card rounded-xl border border-virtus-border-primary overflow-hidden">
              <div className="divide-y divide-virtus-border-primary">
                {stocks.slice(0, 6).map((stock) => (
                  <div key={stock.symbol} className="p-3 flex items-center justify-between">
                    <div>
                      <p className="text-virtus-text-primary font-medium">{stock.symbol}</p>
                      <p className="text-virtus-text-muted text-xs truncate max-w-[120px]">{stock.name}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-virtus-text-primary">R$ {stock.price?.toFixed(2) || '---'}</p>
                      <p className={`text-sm ${
                        stock.change_percent >= 0 ? 'text-virtus-accent-success' : 'text-virtus-accent-danger'
                      }`}>
                        {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent?.toFixed(2) || '0.00'}%
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default HomePage
