import { useEffect, useState } from 'react'
import { strategiesAPI, symbolsAPI } from '../services/api'
import { cn } from '../lib/utils'
import {
  Zap,
  TrendingUp,
  RefreshCw,
  CheckCircle,
  XCircle,
  DollarSign,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react'

interface Strategy {
  name: string
  enabled: boolean
  setups: number
}

interface Symbol {
  symbol: string
  enabled: boolean
  lot_size: number
  max_spread: number
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [symbols, setSymbols] = useState<Symbol[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'strategies' | 'symbols'>('strategies')
  const [togglingItem, setTogglingItem] = useState<string | null>(null)
  
  const loadData = async () => {
    setIsLoading(true)
    try {
      const [stratRes, symRes] = await Promise.all([
        strategiesAPI.list(),
        symbolsAPI.list(),
      ])
      setStrategies(stratRes.data?.strategies || [])
      setSymbols(symRes.data?.symbols || [])
    } catch (error) {
      console.error('Failed to load data:', error)
      setStrategies([])
      setSymbols([])
    } finally {
      setIsLoading(false)
    }
  }
  
  useEffect(() => {
    loadData()
  }, [])
  
  const handleToggleStrategy = async (name: string, currentEnabled: boolean) => {
    setTogglingItem(name)
    try {
      await strategiesAPI.toggle(name, !currentEnabled)
      setStrategies(prev => prev.map(s => 
        s.name === name ? { ...s, enabled: !currentEnabled } : s
      ))
    } catch (error) {
      console.error('Failed to toggle strategy:', error)
    } finally {
      setTogglingItem(null)
    }
  }
  
  const handleToggleSymbol = async (symbol: string, currentEnabled: boolean) => {
    setTogglingItem(symbol)
    try {
      await symbolsAPI.toggle(symbol, !currentEnabled)
      setSymbols(prev => prev.map(s => 
        s.symbol === symbol ? { ...s, enabled: !currentEnabled } : s
      ))
    } catch (error) {
      console.error('Failed to toggle symbol:', error)
    } finally {
      setTogglingItem(null)
    }
  }
  
  const strategyIcons: Record<string, typeof Zap> = {
    ScalpingStrategy: Zap,
    TrendStrategy: TrendingUp,
    ReversalStrategy: RefreshCw,
    EventStrategy: DollarSign,
  }
  
  const strategyDescriptions: Record<string, string> = {
    ScalpingStrategy: 'Operações rápidas em timeframes baixos',
    TrendStrategy: 'Segue tendências em timeframes maiores',
    ReversalStrategy: 'Identifica reversões de tendência',
    EventStrategy: 'Opera em eventos de mercado',
  }
  
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Estratégias & Símbolos</h1>
          <p className="text-virtus-text-muted">Controle quais estratégias e ativos estão ativos</p>
        </div>
        <button onClick={loadData} className="btn-secondary flex items-center gap-2">
          <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          <span>Atualizar</span>
        </button>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-xs text-virtus-text-muted uppercase">Total Estratégias</p>
          <p className="text-2xl font-bold mt-1">{strategies.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-virtus-text-muted uppercase">Estratégias Ativas</p>
          <p className="text-2xl font-bold mt-1 text-virtus-accent-success">
            {strategies.filter(s => s.enabled).length}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-virtus-text-muted uppercase">Total Símbolos</p>
          <p className="text-2xl font-bold mt-1">{symbols.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-virtus-text-muted uppercase">Símbolos Ativos</p>
          <p className="text-2xl font-bold mt-1 text-virtus-accent-success">
            {symbols.filter(s => s.enabled).length}
          </p>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="tabs">
        <button
          onClick={() => setActiveTab('strategies')}
          className={activeTab === 'strategies' ? 'tab-active' : 'tab'}
        >
          Estratégias
        </button>
        <button
          onClick={() => setActiveTab('symbols')}
          className={activeTab === 'symbols' ? 'tab-active' : 'tab'}
        >
          Símbolos
        </button>
      </div>
      
      {/* Strategies */}
      {activeTab === 'strategies' && (
        <div className="grid md:grid-cols-2 gap-4">
          {strategies.map((strategy) => {
            const Icon = strategyIcons[strategy.name] || Zap
            return (
              <div key={strategy.name} className="card-hover">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      'w-12 h-12 rounded-lg flex items-center justify-center',
                      strategy.enabled ? 'bg-virtus-accent-primary/20' : 'bg-virtus-bg-tertiary'
                    )}>
                      <Icon className={cn(
                        'w-6 h-6',
                        strategy.enabled ? 'text-virtus-accent-primary' : 'text-virtus-text-muted'
                      )} />
                    </div>
                    <div>
                      <h3 className="font-semibold">{strategy.name.replace('Strategy', '')}</h3>
                      <p className="text-sm text-virtus-text-muted">
                        {strategyDescriptions[strategy.name] || 'Estratégia de trading'}
                      </p>
                      <p className="text-xs text-virtus-text-muted mt-1">
                        {strategy.setups} setups disponíveis
                      </p>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => handleToggleStrategy(strategy.name, strategy.enabled)}
                    disabled={togglingItem === strategy.name}
                    className="flex items-center gap-2"
                  >
                    {togglingItem === strategy.name ? (
                      <RefreshCw className="w-6 h-6 animate-spin text-virtus-accent-primary" />
                    ) : strategy.enabled ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
      
      {/* Symbols */}
      {activeTab === 'symbols' && (
        <div className="card p-0 overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>Símbolo</th>
                <th>Lot Size</th>
                <th>Max Spread</th>
                <th>Status</th>
                <th className="text-right">Ativo</th>
              </tr>
            </thead>
            <tbody>
              {symbols.map((symbol) => (
                <tr key={symbol.symbol}>
                  <td>
                    <span className="font-semibold">{symbol.symbol}</span>
                  </td>
                  <td>{symbol.lot_size}</td>
                  <td>{symbol.max_spread} pontos</td>
                  <td>
                    {symbol.enabled ? (
                      <span className="badge badge-success">Ativo</span>
                    ) : (
                      <span className="badge badge-danger">Inativo</span>
                    )}
                  </td>
                  <td className="text-right">
                    <button
                      onClick={() => handleToggleSymbol(symbol.symbol, symbol.enabled)}
                      disabled={togglingItem === symbol.symbol}
                    >
                      {togglingItem === symbol.symbol ? (
                        <RefreshCw className="w-6 h-6 animate-spin text-virtus-accent-primary" />
                      ) : symbol.enabled ? (
                        <ToggleRight className="w-8 h-8 text-virtus-accent-success" />
                      ) : (
                        <ToggleLeft className="w-8 h-8 text-virtus-text-muted" />
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
