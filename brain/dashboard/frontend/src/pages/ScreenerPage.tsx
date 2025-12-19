import { useState, useEffect } from 'react'
import {
  Search,
  Filter,
  TrendingUp,
  TrendingDown,
  Star,
  BarChart3,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Building2,
  Percent,
  DollarSign,
  PieChart,
  Award,
  Target,
  Zap,
  X,
  Check,
  Info,
} from 'lucide-react'

// Types
interface StockData {
  ticker: string
  name: string
  sector: string
  sector_pt: string
  price: number
  change: number
  marketCap: number
  logo: string
  pl: number | null
  pvp: number | null
  roe: number | null
  dy: number | null
  divida_ebitda: number | null
  margem_liquida: number | null
  value_score: {
    total: number
    components: Record<string, number>
    grade: string
  }
}

interface Preset {
  id: string
  name: string
  description: string
  filters: Record<string, number>
}

const API_BASE = '/api'

export default function ScreenerPage() {
  const [stocks, setStocks] = useState<StockData[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedStock, setSelectedStock] = useState<StockData | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [presets, setPresets] = useState<Preset[]>([])
  const [activePreset, setActivePreset] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState('value_score')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  
  // Filtros
  const [filters, setFilters] = useState({
    max_pl: '',
    max_pvp: '',
    min_roe: '',
    min_dy: '',
    max_divida_ebitda: '',
    sector: '',
  })
  
  // Setores
  const [sectors] = useState([
    { value: '', label: 'Todos os Setores' },
    { value: 'Finance', label: 'Financeiro' },
    { value: 'Utilities', label: 'Utilidades' },
    { value: 'Energy Minerals', label: 'Energia' },
    { value: 'Non-Energy Minerals', label: 'Mineração' },
    { value: 'Retail Trade', label: 'Varejo' },
    { value: 'Consumer Services', label: 'Serviços' },
    { value: 'Health Services', label: 'Saúde' },
    { value: 'Technology Services', label: 'Tecnologia' },
  ])
  
  useEffect(() => {
    loadPresets()
    loadTopValue()
  }, [])
  
  const loadPresets = async () => {
    try {
      const res = await fetch(`${API_BASE}/screener/presets`)
      const data = await res.json()
      setPresets(data.presets || [])
    } catch (err) {
      console.error('Erro ao carregar presets:', err)
    }
  }
  
  const loadTopValue = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/screener/top-value?limit=30`)
      const data = await res.json()
      setStocks(data.results || [])
    } catch (err) {
      console.error('Erro ao carregar top value:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const loadTopDividends = async () => {
    setLoading(true)
    setActivePreset('dividends')
    try {
      const res = await fetch(`${API_BASE}/screener/top-dividends?limit=30`)
      const data = await res.json()
      setStocks(data.results || [])
    } catch (err) {
      console.error('Erro ao carregar dividendos:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const loadGrowth = async () => {
    setLoading(true)
    setActivePreset('growth')
    try {
      const res = await fetch(`${API_BASE}/screener/growth?limit=30`)
      const data = await res.json()
      setStocks(data.results || [])
    } catch (err) {
      console.error('Erro ao carregar growth:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const applyFilters = async () => {
    setLoading(true)
    setActivePreset(null)
    try {
      const params = new URLSearchParams()
      params.append('sort_by', sortBy)
      params.append('limit', '30')
      
      if (filters.max_pl) params.append('max_pl', filters.max_pl)
      if (filters.max_pvp) params.append('max_pvp', filters.max_pvp)
      if (filters.min_roe) params.append('min_roe', (parseFloat(filters.min_roe) / 100).toString())
      if (filters.min_dy) params.append('min_dy', (parseFloat(filters.min_dy) / 100).toString())
      if (filters.max_divida_ebitda) params.append('max_divida_ebitda', filters.max_divida_ebitda)
      if (filters.sector) params.append('sector', filters.sector)
      
      const res = await fetch(`${API_BASE}/screener/filter?${params}`)
      const data = await res.json()
      setStocks(data.results || [])
    } catch (err) {
      console.error('Erro ao aplicar filtros:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const applyPreset = async (preset: Preset) => {
    setActivePreset(preset.id)
    setFilters({
      max_pl: preset.filters.max_pl?.toString() || '',
      max_pvp: preset.filters.max_pvp?.toString() || '',
      min_roe: preset.filters.min_roe ? (preset.filters.min_roe * 100).toString() : '',
      min_dy: preset.filters.min_dy ? (preset.filters.min_dy * 100).toString() : '',
      max_divida_ebitda: preset.filters.max_divida_ebitda?.toString() || '',
      sector: '',
    })
    
    // Aplica o filtro
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.append('sort_by', 'value_score')
      params.append('limit', '30')
      
      Object.entries(preset.filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString())
        }
      })
      
      const res = await fetch(`${API_BASE}/screener/filter?${params}`)
      const data = await res.json()
      setStocks(data.results || [])
    } catch (err) {
      console.error('Erro ao aplicar preset:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const clearFilters = () => {
    setFilters({
      max_pl: '',
      max_pvp: '',
      min_roe: '',
      min_dy: '',
      max_divida_ebitda: '',
      sector: '',
    })
    setActivePreset(null)
    loadTopValue()
  }
  
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value)
  }
  
  const formatPercent = (value: number | null) => {
    if (value === null || value === undefined) return '-'
    const pct = value < 1 ? value * 100 : value
    return `${pct.toFixed(2)}%`
  }
  
  const formatMarketCap = (value: number) => {
    if (value >= 1e12) return `R$ ${(value / 1e12).toFixed(1)}T`
    if (value >= 1e9) return `R$ ${(value / 1e9).toFixed(1)}B`
    if (value >= 1e6) return `R$ ${(value / 1e6).toFixed(1)}M`
    return formatCurrency(value)
  }
  
  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A': return 'text-green-400 bg-green-400/20'
      case 'B': return 'text-blue-400 bg-blue-400/20'
      case 'C': return 'text-yellow-400 bg-yellow-400/20'
      case 'D': return 'text-orange-400 bg-orange-400/20'
      default: return 'text-red-400 bg-red-400/20'
    }
  }
  
  const getScoreBarColor = (score: number) => {
    if (score >= 70) return 'bg-green-500'
    if (score >= 50) return 'bg-yellow-500'
    if (score >= 30) return 'bg-orange-500'
    return 'bg-red-500'
  }
  
  // Filtra por busca
  const filteredStocks = stocks.filter(stock => 
    stock.ticker.toLowerCase().includes(searchTerm.toLowerCase()) ||
    stock.name.toLowerCase().includes(searchTerm.toLowerCase())
  )
  
  // Ordena
  const sortedStocks = [...filteredStocks].sort((a, b) => {
    let aVal, bVal
    
    switch (sortBy) {
      case 'value_score':
        aVal = a.value_score?.total || 0
        bVal = b.value_score?.total || 0
        break
      case 'dy':
        aVal = a.dy || 0
        bVal = b.dy || 0
        break
      case 'pl':
        aVal = a.pl || 999
        bVal = b.pl || 999
        break
      case 'pvp':
        aVal = a.pvp || 999
        bVal = b.pvp || 999
        break
      case 'roe':
        aVal = a.roe || 0
        bVal = b.roe || 0
        break
      default:
        aVal = a.value_score?.total || 0
        bVal = b.value_score?.total || 0
    }
    
    return sortOrder === 'desc' ? bVal - aVal : aVal - bVal
  })
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-virtus-text-primary flex items-center gap-2">
            <Target className="w-7 h-7 text-virtus-purple" />
            Screener Inteligente B3
          </h1>
          <p className="text-virtus-text-secondary mt-1">
            Encontre as melhores ações com base em indicadores fundamentalistas
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-secondary flex items-center gap-2 ${showFilters ? 'bg-virtus-purple/20' : ''}`}
          >
            <Filter className="w-4 h-4" />
            Filtros
            {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          <button onClick={loadTopValue} className="btn-primary flex items-center gap-2">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
      </div>
      
      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={loadTopValue}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
            activePreset === 'value' || (!activePreset && !loading)
              ? 'bg-virtus-purple text-white'
              : 'bg-virtus-bg-card border border-virtus-border text-virtus-text-secondary hover:text-white'
          }`}
        >
          <Award className="w-4 h-4" />
          Top Value
        </button>
        <button
          onClick={loadTopDividends}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
            activePreset === 'dividends'
              ? 'bg-green-600 text-white'
              : 'bg-virtus-bg-card border border-virtus-border text-virtus-text-secondary hover:text-white'
          }`}
        >
          <DollarSign className="w-4 h-4" />
          Dividendos
        </button>
        <button
          onClick={loadGrowth}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
            activePreset === 'growth'
              ? 'bg-blue-600 text-white'
              : 'bg-virtus-bg-card border border-virtus-border text-virtus-text-secondary hover:text-white'
          }`}
        >
          <Zap className="w-4 h-4" />
          Crescimento
        </button>
        
        {/* Presets */}
        {presets.slice(3).map(preset => (
          <button
            key={preset.id}
            onClick={() => applyPreset(preset)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activePreset === preset.id
                ? 'bg-virtus-purple text-white'
                : 'bg-virtus-bg-card border border-virtus-border text-virtus-text-secondary hover:text-white'
            }`}
          >
            {preset.name}
          </button>
        ))}
      </div>
      
      {/* Filters Panel */}
      {showFilters && (
        <div className="card p-4 animate-fadeIn">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div>
              <label className="text-xs text-virtus-text-secondary mb-1 block">P/L Máximo</label>
              <input
                type="number"
                value={filters.max_pl}
                onChange={e => setFilters({...filters, max_pl: e.target.value})}
                placeholder="Ex: 15"
                className="input-field text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-virtus-text-secondary mb-1 block">P/VP Máximo</label>
              <input
                type="number"
                value={filters.max_pvp}
                onChange={e => setFilters({...filters, max_pvp: e.target.value})}
                placeholder="Ex: 2"
                className="input-field text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-virtus-text-secondary mb-1 block">ROE Mínimo (%)</label>
              <input
                type="number"
                value={filters.min_roe}
                onChange={e => setFilters({...filters, min_roe: e.target.value})}
                placeholder="Ex: 15"
                className="input-field text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-virtus-text-secondary mb-1 block">DY Mínimo (%)</label>
              <input
                type="number"
                value={filters.min_dy}
                onChange={e => setFilters({...filters, min_dy: e.target.value})}
                placeholder="Ex: 5"
                className="input-field text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-virtus-text-secondary mb-1 block">Dív/EBITDA Máx</label>
              <input
                type="number"
                value={filters.max_divida_ebitda}
                onChange={e => setFilters({...filters, max_divida_ebitda: e.target.value})}
                placeholder="Ex: 3"
                className="input-field text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-virtus-text-secondary mb-1 block">Setor</label>
              <select
                value={filters.sector}
                onChange={e => setFilters({...filters, sector: e.target.value})}
                className="input-field text-sm"
              >
                {sectors.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="flex justify-end gap-2 mt-4">
            <button onClick={clearFilters} className="btn-secondary text-sm">
              Limpar
            </button>
            <button onClick={applyFilters} className="btn-primary text-sm flex items-center gap-2">
              <Check className="w-4 h-4" />
              Aplicar Filtros
            </button>
          </div>
        </div>
      )}
      
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-virtus-text-secondary" />
        <input
          type="text"
          placeholder="Buscar por ticker ou nome..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="input-field pl-10 w-full"
        />
      </div>
      
      {/* Results */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-virtus-border flex items-center justify-between">
          <span className="text-virtus-text-secondary">
            {sortedStocks.length} ações encontradas
          </span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-virtus-text-secondary">Ordenar por:</span>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="bg-virtus-bg-secondary border border-virtus-border rounded px-2 py-1 text-sm"
            >
              <option value="value_score">Score Value</option>
              <option value="dy">Dividend Yield</option>
              <option value="pl">P/L</option>
              <option value="pvp">P/VP</option>
              <option value="roe">ROE</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
              className="p-1 hover:bg-virtus-bg-secondary rounded"
            >
              {sortOrder === 'desc' ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </button>
          </div>
        </div>
        
        {loading ? (
          <div className="p-8 text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-virtus-purple mb-2" />
            <p className="text-virtus-text-secondary">Analisando ações...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-virtus-bg-secondary">
                <tr>
                  <th className="text-left p-3 text-xs font-medium text-virtus-text-secondary">Ação</th>
                  <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">Preço</th>
                  <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">P/L</th>
                  <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">P/VP</th>
                  <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">ROE</th>
                  <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">DY</th>
                  <th className="text-center p-3 text-xs font-medium text-virtus-text-secondary">Score</th>
                  <th className="text-center p-3 text-xs font-medium text-virtus-text-secondary">Nota</th>
                </tr>
              </thead>
              <tbody>
                {sortedStocks.map((stock, idx) => (
                  <tr
                    key={stock.ticker}
                    onClick={() => setSelectedStock(stock)}
                    className="border-t border-virtus-border hover:bg-virtus-bg-secondary cursor-pointer transition-colors"
                  >
                    <td className="p-3">
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-virtus-text-secondary w-5">{idx + 1}</span>
                        <div className="w-8 h-8 rounded-lg bg-virtus-bg-secondary flex items-center justify-center overflow-hidden">
                          {stock.logo ? (
                            <img src={stock.logo} alt="" className="w-6 h-6" />
                          ) : (
                            <Building2 className="w-4 h-4 text-virtus-text-secondary" />
                          )}
                        </div>
                        <div>
                          <p className="font-semibold text-virtus-text-primary">{stock.ticker}</p>
                          <p className="text-xs text-virtus-text-secondary truncate max-w-[150px]">
                            {stock.name}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-right">
                      <p className="font-medium">{formatCurrency(stock.price)}</p>
                      <p className={`text-xs ${stock.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {stock.change >= 0 ? '+' : ''}{stock.change?.toFixed(2)}%
                      </p>
                    </td>
                    <td className="p-3 text-right font-mono text-sm">
                      {stock.pl ? stock.pl.toFixed(1) : '-'}
                    </td>
                    <td className="p-3 text-right font-mono text-sm">
                      {stock.pvp ? stock.pvp.toFixed(2) : '-'}
                    </td>
                    <td className="p-3 text-right font-mono text-sm">
                      {formatPercent(stock.roe)}
                    </td>
                    <td className="p-3 text-right">
                      <span className={`font-mono text-sm ${(stock.dy || 0) >= 0.05 ? 'text-green-400' : ''}`}>
                        {formatPercent(stock.dy)}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 bg-virtus-bg-secondary rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${getScoreBarColor(stock.value_score?.total || 0)}`}
                            style={{ width: `${stock.value_score?.total || 0}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono w-8">{stock.value_score?.total || 0}</span>
                      </div>
                    </td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 rounded font-bold text-sm ${getGradeColor(stock.value_score?.grade || 'F')}`}>
                        {stock.value_score?.grade || '-'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* Stock Detail Modal */}
      {selectedStock && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-virtus-bg-card rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto animate-slideUp">
            <div className="p-6 border-b border-virtus-border flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-virtus-bg-secondary flex items-center justify-center overflow-hidden">
                  {selectedStock.logo ? (
                    <img src={selectedStock.logo} alt="" className="w-10 h-10" />
                  ) : (
                    <Building2 className="w-6 h-6 text-virtus-text-secondary" />
                  )}
                </div>
                <div>
                  <h2 className="text-xl font-bold">{selectedStock.ticker}</h2>
                  <p className="text-virtus-text-secondary text-sm">{selectedStock.name}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedStock(null)}
                className="p-2 hover:bg-virtus-bg-secondary rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              {/* Score Card */}
              <div className="bg-gradient-to-br from-virtus-purple/20 to-virtus-purple/5 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Star className="w-5 h-5 text-yellow-400" />
                    Score Value Investing
                  </h3>
                  <span className={`px-4 py-2 rounded-lg font-bold text-2xl ${getGradeColor(selectedStock.value_score?.grade || 'F')}`}>
                    {selectedStock.value_score?.grade || '-'}
                  </span>
                </div>
                
                <div className="flex items-center gap-4 mb-4">
                  <div className="flex-1 bg-virtus-bg-primary rounded-full h-4">
                    <div
                      className={`h-4 rounded-full ${getScoreBarColor(selectedStock.value_score?.total || 0)} transition-all`}
                      style={{ width: `${selectedStock.value_score?.total || 0}%` }}
                    />
                  </div>
                  <span className="text-2xl font-bold">{selectedStock.value_score?.total || 0}</span>
                </div>
                
                {/* Components */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {selectedStock.value_score?.components && Object.entries(selectedStock.value_score.components).map(([key, value]) => (
                    <div key={key} className="bg-virtus-bg-primary/50 rounded-lg p-3">
                      <p className="text-xs text-virtus-text-secondary uppercase">{key.replace('_', ' ')}</p>
                      <div className="flex items-center justify-between mt-1">
                        <div className="w-full bg-virtus-bg-secondary rounded-full h-1.5 mr-2">
                          <div
                            className={`h-1.5 rounded-full ${getScoreBarColor(value)}`}
                            style={{ width: `${value}%` }}
                          />
                        </div>
                        <span className="text-sm font-mono">{value}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Fundamentals Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-virtus-bg-secondary rounded-lg p-4">
                  <p className="text-xs text-virtus-text-secondary">Preço</p>
                  <p className="text-xl font-bold">{formatCurrency(selectedStock.price)}</p>
                  <p className={`text-sm ${selectedStock.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {selectedStock.change >= 0 ? '+' : ''}{selectedStock.change?.toFixed(2)}%
                  </p>
                </div>
                <div className="bg-virtus-bg-secondary rounded-lg p-4">
                  <p className="text-xs text-virtus-text-secondary">Market Cap</p>
                  <p className="text-xl font-bold">{formatMarketCap(selectedStock.marketCap)}</p>
                </div>
                <div className="bg-virtus-bg-secondary rounded-lg p-4">
                  <p className="text-xs text-virtus-text-secondary">Setor</p>
                  <p className="text-lg font-semibold">{selectedStock.sector_pt}</p>
                </div>
                <div className="bg-virtus-bg-secondary rounded-lg p-4">
                  <p className="text-xs text-virtus-text-secondary">Dividend Yield</p>
                  <p className="text-xl font-bold text-green-400">{formatPercent(selectedStock.dy)}</p>
                </div>
              </div>
              
              {/* Indicators */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="flex items-center gap-3 p-3 bg-virtus-bg-secondary rounded-lg">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-xs text-virtus-text-secondary">P/L</p>
                    <p className="font-bold">{selectedStock.pl ? selectedStock.pl.toFixed(1) : '-'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-virtus-bg-secondary rounded-lg">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <PieChart className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-xs text-virtus-text-secondary">P/VP</p>
                    <p className="font-bold">{selectedStock.pvp ? selectedStock.pvp.toFixed(2) : '-'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-virtus-bg-secondary rounded-lg">
                  <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                    <TrendingUp className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-xs text-virtus-text-secondary">ROE</p>
                    <p className="font-bold">{formatPercent(selectedStock.roe)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-virtus-bg-secondary rounded-lg">
                  <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                    <Percent className="w-5 h-5 text-yellow-400" />
                  </div>
                  <div>
                    <p className="text-xs text-virtus-text-secondary">Margem Líquida</p>
                    <p className="font-bold">{formatPercent(selectedStock.margem_liquida)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-virtus-bg-secondary rounded-lg">
                  <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
                    <TrendingDown className="w-5 h-5 text-red-400" />
                  </div>
                  <div>
                    <p className="text-xs text-virtus-text-secondary">Dív/EBITDA</p>
                    <p className="font-bold">{selectedStock.divida_ebitda?.toFixed(1) || '-'}</p>
                  </div>
                </div>
              </div>
              
              {/* Info */}
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 flex gap-3">
                <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-200">
                  <p className="font-medium mb-1">Como interpretar o Score:</p>
                  <ul className="text-xs space-y-1 text-blue-300">
                    <li>• <strong>A (80+):</strong> Excelente - Forte candidata a investimento</li>
                    <li>• <strong>B (65-79):</strong> Bom - Fundamentos sólidos</li>
                    <li>• <strong>C (50-64):</strong> Regular - Análise adicional recomendada</li>
                    <li>• <strong>D/F (&lt;50):</strong> Fraco - Cautela necessária</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
