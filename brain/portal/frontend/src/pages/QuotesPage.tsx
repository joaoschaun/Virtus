import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, RefreshCw, Search, BarChart3 } from 'lucide-react'

interface StockQuote {
  symbol: string
  name: string
  price: number
  change: number
  change_percent: number
  volume?: number
  market_cap?: number
  high?: number
  low?: number
}

interface MarketIndex {
  symbol: string
  name: string
  price: number
  change: number
  change_percent: number
}

const QuotesPage = () => {
  const [indices, setIndices] = useState<Record<string, MarketIndex>>({})
  const [stocks, setStocks] = useState<StockQuote[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [indicesRes, stocksRes] = await Promise.all([
        fetch('/api/portal/indices'),
        fetch('/api/portal/quotes/brazil')
      ])
      
      const indicesData = await indicesRes.json()
      const stocksData = await stocksRes.json()
      
      if (indicesData.success) setIndices(indicesData.data)
      if (stocksData.success) setStocks(stocksData.data)
    } catch (error) {
      console.error('Erro ao buscar cotações:', error)
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
    return `R$ ${numPrice.toFixed(2)}`
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

  const formatVolume = (volume?: number) => {
    if (!volume) return '---'
    if (volume >= 1e9) return `${(volume / 1e9).toFixed(2)}B`
    if (volume >= 1e6) return `${(volume / 1e6).toFixed(2)}M`
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(2)}K`
    return volume.toString()
  }

  const filteredStocks = stocks.filter(s => 
    s.symbol.toLowerCase().includes(search.toLowerCase()) ||
    s.name?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-virtus-text-primary flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-virtus-accent-primary" />
            Cotações em Tempo Real
          </h1>
          <p className="text-virtus-text-secondary mt-2">
            Acompanhe índices globais e ações brasileiras
          </p>
        </div>

        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-virtus-accent-primary/10 text-virtus-accent-primary rounded-lg hover:bg-virtus-accent-primary/20 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      {/* Global Indices */}
      <section>
        <h2 className="text-xl font-semibold text-virtus-text-primary mb-4">Índices Globais</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(indices).map(([key, index]) => (
            <div 
              key={key}
              className="bg-virtus-bg-card rounded-xl p-4 border border-virtus-border-primary card-hover"
            >
              <p className="text-virtus-text-muted text-sm mb-1">{index.name}</p>
              <p className="text-2xl font-bold text-virtus-text-primary">
                {formatPrice(index.price, key)}
              </p>
              <div className={`flex items-center gap-2 mt-2 ${
                isPositive(index.change_percent) ? 'text-virtus-accent-success' : 'text-virtus-accent-danger'
              }`}>
                {isPositive(index.change_percent) ? (
                  <TrendingUp className="w-4 h-4" />
                ) : (
                  <TrendingDown className="w-4 h-4" />
                )}
                <span className="font-medium">
                  {isPositive(index.change_percent) ? '+' : ''}{formatChangePercent(index.change_percent)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Brazil Stocks */}
      <section>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <h2 className="text-xl font-semibold text-virtus-text-primary">Ações Brasil (B3)</h2>
          
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-virtus-text-muted" />
            <input
              type="text"
              placeholder="Buscar ação..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 pr-4 py-2 bg-virtus-bg-card border border-virtus-border-primary rounded-lg text-virtus-text-primary placeholder-virtus-text-muted focus:outline-none focus:border-virtus-accent-primary/50"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 text-virtus-accent-primary animate-spin" />
          </div>
        ) : (
          <div className="bg-virtus-bg-card rounded-xl border border-virtus-border-primary overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-virtus-border-primary">
                    <th className="text-left text-virtus-text-muted text-xs font-medium p-4">Ativo</th>
                    <th className="text-right text-virtus-text-muted text-xs font-medium p-4">Preço</th>
                    <th className="text-right text-virtus-text-muted text-xs font-medium p-4">Variação</th>
                    <th className="text-right text-virtus-text-muted text-xs font-medium p-4 hidden md:table-cell">Volume</th>
                    <th className="text-right text-virtus-text-muted text-xs font-medium p-4 hidden lg:table-cell">Máx</th>
                    <th className="text-right text-virtus-text-muted text-xs font-medium p-4 hidden lg:table-cell">Mín</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-virtus-border-primary">
                  {filteredStocks.map((stock) => (
                    <tr key={stock.symbol} className="hover:bg-virtus-bg-hover transition-colors">
                      <td className="p-4">
                        <div>
                          <p className="text-virtus-text-primary font-medium">{stock.symbol}</p>
                          <p className="text-virtus-text-muted text-xs truncate max-w-[200px]">{stock.name}</p>
                        </div>
                      </td>
                      <td className="p-4 text-right">
                        <p className="text-virtus-text-primary font-mono">R$ {stock.price?.toFixed(2) || '---'}</p>
                      </td>
                      <td className="p-4 text-right">
                        <div className={`flex items-center justify-end gap-1 ${
                          isPositive(stock.change_percent) ? 'text-virtus-accent-success' : 'text-virtus-accent-danger'
                        }`}>
                          {isPositive(stock.change_percent) ? (
                            <TrendingUp className="w-4 h-4" />
                          ) : (
                            <TrendingDown className="w-4 h-4" />
                          )}
                          <span className="font-mono">
                            {isPositive(stock.change_percent) ? '+' : ''}{formatChangePercent(stock.change_percent)}%
                          </span>
                        </div>
                      </td>
                      <td className="p-4 text-right hidden md:table-cell">
                        <p className="text-virtus-text-secondary font-mono text-sm">{formatVolume(stock.volume)}</p>
                      </td>
                      <td className="p-4 text-right hidden lg:table-cell">
                        <p className="text-virtus-text-secondary font-mono text-sm">
                          {stock.high ? `R$ ${stock.high.toFixed(2)}` : '---'}
                        </p>
                      </td>
                      <td className="p-4 text-right hidden lg:table-cell">
                        <p className="text-gray-400 font-mono text-sm">
                          {stock.low ? `R$ ${stock.low.toFixed(2)}` : '---'}
                        </p>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loading && filteredStocks.length === 0 && (
          <div className="text-center py-10 bg-virtus-navy-light rounded-xl">
            <p className="text-gray-400">Nenhuma ação encontrada</p>
          </div>
        )}
      </section>
    </div>
  )
}

export default QuotesPage
