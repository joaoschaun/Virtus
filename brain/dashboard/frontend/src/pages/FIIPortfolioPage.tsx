import { useState, useEffect } from 'react'
import {
  Building,
  Plus,
  Trash2,
  Edit3,
  DollarSign,
  TrendingUp,
  TrendingDown,
  PieChart,
  Calendar,
  Calculator,
  RefreshCw,
  X,
  Check,
  Target,
  Wallet,
  BarChart3,
  Lightbulb,
  ChevronRight,
  Info,
  Landmark,
} from 'lucide-react'

// Types
interface Position {
  ticker: string
  name: string
  quantity: number
  avg_price: number
  current_price: number
  invested: number
  current_value: number
  gain: number
  gain_percent: number
  monthly_income: number
  dy_12m: number
  logo: string
  category: string
  change_today: number
}

interface PortfolioSummary {
  total_invested: number
  current_value: number
  total_gain: number
  total_gain_percent: number
  monthly_income: number
  yearly_income: number
  avg_dy: number
  position_count: number
}

interface FIIQuote {
  ticker: string
  name: string
  price: number
  change: number
  changePercent: number
  volume: number
  dy: number | null
  pvp: number | null
  logo: string
}

interface Suggestion {
  ticker: string
  name: string
  price: number
  dy_12m: number
  pvp: number
  avg_monthly: number
  logo: string
  score: number
}

interface Payment {
  ticker: string
  date: string
  rate_per_share: number
  total: number
  quantity: number
}

const API_BASE = '/api'

const CATEGORIES = [
  { value: 'logistica', label: '📦 Logística', color: 'bg-blue-500' },
  { value: 'shoppings', label: '🛒 Shoppings', color: 'bg-pink-500' },
  { value: 'lajes', label: '🏢 Lajes Corporativas', color: 'bg-purple-500' },
  { value: 'papel', label: '📄 Papel (CRI/LCI)', color: 'bg-green-500' },
  { value: 'fof', label: '📊 Fundo de Fundos', color: 'bg-yellow-500' },
  { value: 'hibrido', label: '🔀 Híbrido', color: 'bg-orange-500' },
  { value: 'outros', label: '📁 Outros', color: 'bg-gray-500' },
]

export default function FIIPortfolioPage() {
  const [activeTab, setActiveTab] = useState<'portfolio' | 'explore' | 'calculator' | 'calendar'>('portfolio')
  const [positions, setPositions] = useState<Position[]>([])
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [byCategory, setByCategory] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingPosition, setEditingPosition] = useState<Position | null>(null)
  
  // Explore
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [allFiis, setAllFiis] = useState<FIIQuote[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  
  // Calculator
  const [targetMonthly, setTargetMonthly] = useState(3000)
  const [avgDy, setAvgDy] = useState(8)
  const [calcResult, setCalcResult] = useState<any>(null)
  
  // Calendar
  const [payments, setPayments] = useState<Payment[]>([])
  const [paymentsByMonth, setPaymentsByMonth] = useState<Record<string, any>>({})
  
  // Add Form
  const [newPosition, setNewPosition] = useState({
    ticker: '',
    quantity: 0,
    avg_price: 0,
    category: 'outros',
  })
  
  useEffect(() => {
    loadPortfolio()
  }, [])
  
  const loadPortfolio = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/fii-portfolio/portfolio`)
      const data = await res.json()
      setPositions(data.positions || [])
      setSummary(data.summary || null)
      setByCategory(data.by_category || {})
    } catch (err) {
      console.error('Erro ao carregar carteira:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const loadSuggestions = async () => {
    try {
      const res = await fetch(`${API_BASE}/fii-portfolio/suggestions?min_dy=6&max_pvp=1.1`)
      const data = await res.json()
      setSuggestions(data.suggestions || [])
    } catch (err) {
      console.error('Erro ao carregar sugestões:', err)
    }
  }
  
  const loadAllFiis = async () => {
    try {
      const res = await fetch(`${API_BASE}/fii-portfolio/fiis?limit=100`)
      const data = await res.json()
      setAllFiis(data.fiis || [])
    } catch (err) {
      console.error('Erro ao carregar FIIs:', err)
    }
  }
  
  const loadCalendar = async () => {
    try {
      const res = await fetch(`${API_BASE}/fii-portfolio/calendar`)
      const data = await res.json()
      setPayments(data.payments || [])
      setPaymentsByMonth(data.by_month || {})
    } catch (err) {
      console.error('Erro ao carregar calendário:', err)
    }
  }
  
  const calculateIncome = async () => {
    try {
      const res = await fetch(`${API_BASE}/fii-portfolio/calculator?target_monthly=${targetMonthly}&avg_dy=${avgDy}`)
      const data = await res.json()
      setCalcResult(data)
    } catch (err) {
      console.error('Erro ao calcular:', err)
    }
  }
  
  const addPosition = async () => {
    if (!newPosition.ticker || newPosition.quantity <= 0 || newPosition.avg_price <= 0) return
    
    try {
      const res = await fetch(`${API_BASE}/fii-portfolio/portfolio/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPosition),
      })
      
      if (res.ok) {
        setShowAddModal(false)
        setNewPosition({ ticker: '', quantity: 0, avg_price: 0, category: 'outros' })
        loadPortfolio()
      }
    } catch (err) {
      console.error('Erro ao adicionar posição:', err)
    }
  }
  
  const removePosition = async (ticker: string) => {
    if (!confirm(`Remover ${ticker} da carteira?`)) return
    
    try {
      await fetch(`${API_BASE}/fii-portfolio/portfolio/${ticker}`, { method: 'DELETE' })
      loadPortfolio()
    } catch (err) {
      console.error('Erro ao remover posição:', err)
    }
  }
  
  useEffect(() => {
    if (activeTab === 'explore') {
      loadSuggestions()
      loadAllFiis()
    } else if (activeTab === 'calendar') {
      loadCalendar()
    }
  }, [activeTab])
  
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value)
  }
  
  const getCategoryColor = (cat: string) => {
    return CATEGORIES.find(c => c.value === cat)?.color || 'bg-gray-500'
  }
  
  const filteredFiis = allFiis.filter(fii =>
    fii.ticker.toLowerCase().includes(searchTerm.toLowerCase()) ||
    fii.name?.toLowerCase().includes(searchTerm.toLowerCase())
  )
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-virtus-text-primary flex items-center gap-2">
            <Landmark className="w-7 h-7 text-virtus-purple" />
            Carteira de FIIs
          </h1>
          <p className="text-virtus-text-secondary mt-1">
            Gerencie sua carteira de Fundos Imobiliários e acompanhe sua renda passiva
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={loadPortfolio}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Adicionar FII
          </button>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="flex gap-2 border-b border-virtus-border pb-2">
        {[
          { id: 'portfolio', label: 'Minha Carteira', icon: Wallet },
          { id: 'explore', label: 'Explorar FIIs', icon: Lightbulb },
          { id: 'calculator', label: 'Calculadora', icon: Calculator },
          { id: 'calendar', label: 'Agenda', icon: Calendar },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              activeTab === tab.id
                ? 'bg-virtus-purple text-white'
                : 'text-virtus-text-secondary hover:text-white hover:bg-virtus-bg-secondary'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>
      
      {/* Portfolio Tab */}
      {activeTab === 'portfolio' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="card p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <Wallet className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-xs text-virtus-text-secondary">Patrimônio</p>
                    <p className="text-xl font-bold">{formatCurrency(summary.current_value)}</p>
                  </div>
                </div>
              </div>
              
              <div className="card p-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg ${summary.total_gain >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'} flex items-center justify-center`}>
                    {summary.total_gain >= 0 ? (
                      <TrendingUp className="w-5 h-5 text-green-400" />
                    ) : (
                      <TrendingDown className="w-5 h-5 text-red-400" />
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-virtus-text-secondary">Ganho/Perda</p>
                    <p className={`text-xl font-bold ${summary.total_gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(summary.total_gain)}
                    </p>
                    <p className={`text-xs ${summary.total_gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {summary.total_gain_percent >= 0 ? '+' : ''}{summary.total_gain_percent.toFixed(2)}%
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="card p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                    <DollarSign className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-xs text-virtus-text-secondary">Renda Mensal</p>
                    <p className="text-xl font-bold text-green-400">{formatCurrency(summary.monthly_income)}</p>
                    <p className="text-xs text-virtus-text-secondary">
                      {formatCurrency(summary.yearly_income)}/ano
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="card p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-xs text-virtus-text-secondary">DY Médio</p>
                    <p className="text-xl font-bold">{summary.avg_dy.toFixed(2)}%</p>
                    <p className="text-xs text-virtus-text-secondary">
                      {summary.position_count} FIIs
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Category Distribution */}
          {Object.keys(byCategory).length > 0 && (
            <div className="card p-4">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <PieChart className="w-5 h-5 text-virtus-purple" />
                Distribuição por Categoria
              </h3>
              <div className="flex flex-wrap gap-3">
                {Object.entries(byCategory).map(([cat, data]: [string, any]) => (
                  <div key={cat} className="flex items-center gap-2 bg-virtus-bg-secondary rounded-lg px-3 py-2">
                    <div className={`w-3 h-3 rounded-full ${getCategoryColor(cat)}`} />
                    <span className="text-sm font-medium capitalize">{cat}</span>
                    <span className="text-xs text-virtus-text-secondary">
                      {data.weight}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Positions Table */}
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-virtus-border">
              <h3 className="font-semibold">Minhas Posições</h3>
            </div>
            
            {loading ? (
              <div className="p-8 text-center">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto text-virtus-purple mb-2" />
                <p className="text-virtus-text-secondary">Carregando carteira...</p>
              </div>
            ) : positions.length === 0 ? (
              <div className="p-8 text-center">
                <Building className="w-12 h-12 mx-auto text-virtus-text-secondary mb-3" />
                <p className="text-virtus-text-secondary mb-4">Você ainda não tem FIIs na carteira</p>
                <button
                  onClick={() => setShowAddModal(true)}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Adicionar Primeiro FII
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-virtus-bg-secondary">
                    <tr>
                      <th className="text-left p-3 text-xs font-medium text-virtus-text-secondary">FII</th>
                      <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">Qtd</th>
                      <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">PM</th>
                      <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">Atual</th>
                      <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">Ganho</th>
                      <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">DY 12M</th>
                      <th className="text-right p-3 text-xs font-medium text-virtus-text-secondary">Renda/Mês</th>
                      <th className="text-center p-3 text-xs font-medium text-virtus-text-secondary">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map(pos => (
                      <tr key={pos.ticker} className="border-t border-virtus-border hover:bg-virtus-bg-secondary">
                        <td className="p-3">
                          <div className="flex items-center gap-3">
                            <div className={`w-1 h-10 rounded-full ${getCategoryColor(pos.category)}`} />
                            <div className="w-8 h-8 rounded-lg bg-virtus-bg-secondary flex items-center justify-center overflow-hidden">
                              {pos.logo ? (
                                <img src={pos.logo} alt="" className="w-6 h-6" />
                              ) : (
                                <Building className="w-4 h-4 text-virtus-text-secondary" />
                              )}
                            </div>
                            <div>
                              <p className="font-semibold">{pos.ticker}</p>
                              <p className="text-xs text-virtus-text-secondary truncate max-w-[120px]">
                                {pos.name}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="p-3 text-right font-mono">{pos.quantity}</td>
                        <td className="p-3 text-right font-mono text-sm">{formatCurrency(pos.avg_price)}</td>
                        <td className="p-3 text-right">
                          <p className="font-mono text-sm">{formatCurrency(pos.current_price)}</p>
                          <p className={`text-xs ${pos.change_today >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {pos.change_today >= 0 ? '+' : ''}{pos.change_today?.toFixed(2)}%
                          </p>
                        </td>
                        <td className="p-3 text-right">
                          <p className={`font-semibold ${pos.gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatCurrency(pos.gain)}
                          </p>
                          <p className={`text-xs ${pos.gain_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {pos.gain_percent >= 0 ? '+' : ''}{pos.gain_percent.toFixed(2)}%
                          </p>
                        </td>
                        <td className="p-3 text-right">
                          <span className="font-mono text-green-400">{pos.dy_12m.toFixed(2)}%</span>
                        </td>
                        <td className="p-3 text-right">
                          <span className="font-semibold text-green-400">{formatCurrency(pos.monthly_income)}</span>
                        </td>
                        <td className="p-3 text-center">
                          <button
                            onClick={() => removePosition(pos.ticker)}
                            className="p-1.5 hover:bg-red-500/20 rounded text-red-400"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Explore Tab */}
      {activeTab === 'explore' && (
        <div className="space-y-6">
          {/* Suggestions */}
          <div className="card p-4">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-yellow-400" />
              Sugestões de FIIs (DY &gt; 6%, P/VP &lt; 1.1)
            </h3>
            
            {suggestions.length === 0 ? (
              <div className="text-center py-4">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-virtus-purple" />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {suggestions.slice(0, 9).map(sug => (
                  <div key={sug.ticker} className="bg-virtus-bg-secondary rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded bg-virtus-bg-primary flex items-center justify-center overflow-hidden">
                          {sug.logo ? (
                            <img src={sug.logo} alt="" className="w-6 h-6" />
                          ) : (
                            <Building className="w-4 h-4 text-virtus-text-secondary" />
                          )}
                        </div>
                        <div>
                          <p className="font-bold">{sug.ticker}</p>
                          <p className="text-xs text-virtus-text-secondary truncate max-w-[100px]">
                            {sug.name}
                          </p>
                        </div>
                      </div>
                      <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded">
                        Score: {sug.score}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-2 text-center mb-3">
                      <div>
                        <p className="text-xs text-virtus-text-secondary">Preço</p>
                        <p className="font-semibold text-sm">{formatCurrency(sug.price)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-virtus-text-secondary">DY 12M</p>
                        <p className="font-semibold text-sm text-green-400">{sug.dy_12m.toFixed(1)}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-virtus-text-secondary">P/VP</p>
                        <p className="font-semibold text-sm">{sug.pvp.toFixed(2)}</p>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => {
                        setNewPosition({
                          ticker: sug.ticker,
                          quantity: 10,
                          avg_price: sug.price,
                          category: 'outros',
                        })
                        setShowAddModal(true)
                      }}
                      className="w-full btn-secondary text-sm flex items-center justify-center gap-2"
                    >
                      <Plus className="w-4 h-4" />
                      Adicionar à Carteira
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* All FIIs */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold">Todos os FIIs</h3>
              <input
                type="text"
                placeholder="Buscar FII..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="input-field w-48 text-sm"
              />
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 max-h-[400px] overflow-y-auto">
              {filteredFiis.map(fii => (
                <div
                  key={fii.ticker}
                  onClick={() => {
                    setNewPosition({
                      ticker: fii.ticker,
                      quantity: 10,
                      avg_price: fii.price,
                      category: 'outros',
                    })
                    setShowAddModal(true)
                  }}
                  className="bg-virtus-bg-secondary rounded-lg p-3 cursor-pointer hover:bg-virtus-bg-secondary/80 transition-colors"
                >
                  <p className="font-bold text-sm">{fii.ticker}</p>
                  <p className="text-sm font-mono">{formatCurrency(fii.price)}</p>
                  <p className={`text-xs ${fii.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {fii.change >= 0 ? '+' : ''}{fii.change?.toFixed(2)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      {/* Calculator Tab */}
      {activeTab === 'calculator' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Calculator className="w-5 h-5 text-virtus-purple" />
              Calculadora de Independência Financeira
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm text-virtus-text-secondary mb-1 block">
                  Renda Mensal Desejada
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-virtus-text-secondary">R$</span>
                  <input
                    type="number"
                    value={targetMonthly}
                    onChange={e => setTargetMonthly(Number(e.target.value))}
                    className="input-field pl-10 text-xl font-bold"
                  />
                </div>
              </div>
              
              <div>
                <label className="text-sm text-virtus-text-secondary mb-1 block">
                  Dividend Yield Médio Esperado (%)
                </label>
                <input
                  type="number"
                  value={avgDy}
                  onChange={e => setAvgDy(Number(e.target.value))}
                  className="input-field text-xl font-bold"
                  step="0.5"
                />
              </div>
              
              <button onClick={calculateIncome} className="btn-primary w-full py-3 text-lg">
                Calcular
              </button>
            </div>
          </div>
          
          {calcResult && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-green-400" />
                Resultado
              </h3>
              
              <div className="bg-gradient-to-br from-green-500/20 to-green-500/5 rounded-xl p-6 mb-6">
                <p className="text-sm text-virtus-text-secondary mb-2">Patrimônio Necessário</p>
                <p className="text-4xl font-bold text-green-400">
                  {formatCurrency(calcResult.required_capital)}
                </p>
                <p className="text-sm text-virtus-text-secondary mt-2">
                  Para receber {formatCurrency(calcResult.target_monthly)}/mês
                </p>
              </div>
              
              <h4 className="font-medium mb-3">Cenários com diferentes DYs</h4>
              <div className="space-y-2">
                {calcResult.scenarios?.map((sc: any) => (
                  <div key={sc.dy} className="flex items-center justify-between bg-virtus-bg-secondary rounded-lg p-3">
                    <span className="font-mono">DY {sc.dy}%</span>
                    <span className="font-bold">{formatCurrency(sc.required_capital)}</span>
                  </div>
                ))}
              </div>
              
              {calcResult.tips && (
                <div className="mt-4 bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                  <p className="text-sm font-medium text-blue-400 mb-2">💡 Dicas</p>
                  <ul className="text-xs text-blue-300 space-y-1">
                    {calcResult.tips.map((tip: string, i: number) => (
                      <li key={i}>• {tip}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Calendar Tab */}
      {activeTab === 'calendar' && (
        <div className="space-y-6">
          <div className="card p-4">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-virtus-purple" />
              Agenda de Pagamentos
            </h3>
            
            {payments.length === 0 ? (
              <div className="text-center py-8">
                <Calendar className="w-12 h-12 mx-auto text-virtus-text-secondary mb-3" />
                <p className="text-virtus-text-secondary">
                  Adicione FIIs à sua carteira para ver a agenda de pagamentos
                </p>
              </div>
            ) : (
              <>
                {/* By Month Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  {Object.entries(paymentsByMonth).slice(0, 4).map(([month, data]: [string, any]) => (
                    <div key={month} className="bg-virtus-bg-secondary rounded-lg p-4">
                      <p className="text-sm text-virtus-text-secondary">{month}</p>
                      <p className="text-xl font-bold text-green-400">{formatCurrency(data.total)}</p>
                      <p className="text-xs text-virtus-text-secondary">
                        {data.payments?.length} pagamentos
                      </p>
                    </div>
                  ))}
                </div>
                
                {/* Payments List */}
                <div className="space-y-2">
                  {payments.map((pay, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-virtus-bg-secondary rounded-lg p-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                          <DollarSign className="w-5 h-5 text-green-400" />
                        </div>
                        <div>
                          <p className="font-semibold">{pay.ticker}</p>
                          <p className="text-xs text-virtus-text-secondary">
                            {pay.quantity} cotas × {formatCurrency(pay.rate_per_share)}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-green-400">{formatCurrency(pay.total)}</p>
                        <p className="text-xs text-virtus-text-secondary">{pay.date}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
      
      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-virtus-bg-card rounded-xl max-w-md w-full animate-slideUp">
            <div className="p-6 border-b border-virtus-border flex items-center justify-between">
              <h2 className="text-xl font-bold">Adicionar FII</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-2 hover:bg-virtus-bg-secondary rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="text-sm text-virtus-text-secondary mb-1 block">Ticker</label>
                <input
                  type="text"
                  value={newPosition.ticker}
                  onChange={e => setNewPosition({...newPosition, ticker: e.target.value.toUpperCase()})}
                  placeholder="Ex: HGLG11"
                  className="input-field"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-virtus-text-secondary mb-1 block">Quantidade</label>
                  <input
                    type="number"
                    value={newPosition.quantity || ''}
                    onChange={e => setNewPosition({...newPosition, quantity: Number(e.target.value)})}
                    placeholder="0"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="text-sm text-virtus-text-secondary mb-1 block">Preço Médio</label>
                  <input
                    type="number"
                    value={newPosition.avg_price || ''}
                    onChange={e => setNewPosition({...newPosition, avg_price: Number(e.target.value)})}
                    placeholder="0.00"
                    step="0.01"
                    className="input-field"
                  />
                </div>
              </div>
              
              <div>
                <label className="text-sm text-virtus-text-secondary mb-1 block">Categoria</label>
                <select
                  value={newPosition.category}
                  onChange={e => setNewPosition({...newPosition, category: e.target.value})}
                  className="input-field"
                >
                  {CATEGORIES.map(cat => (
                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                  ))}
                </select>
              </div>
              
              {newPosition.quantity > 0 && newPosition.avg_price > 0 && (
                <div className="bg-virtus-bg-secondary rounded-lg p-3">
                  <p className="text-sm text-virtus-text-secondary">Total Investido</p>
                  <p className="text-xl font-bold">
                    {formatCurrency(newPosition.quantity * newPosition.avg_price)}
                  </p>
                </div>
              )}
            </div>
            
            <div className="p-6 border-t border-virtus-border flex gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="btn-secondary flex-1"
              >
                Cancelar
              </button>
              <button
                onClick={addPosition}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                <Check className="w-4 h-4" />
                Adicionar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
