import { useEffect, useState } from 'react'
import { tradesAPI } from '../services/api'
import { formatCurrency, formatDate, cn, getTradeTypeColor, getPnLColor } from '../lib/utils'
import {
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Download,
  Calendar,
} from 'lucide-react'

interface Trade {
  ticket: number
  symbol: string
  type: string
  volume: number
  entry_price: number
  exit_price: number
  sl: number
  tp: number
  entry_time: string
  exit_time: string
  pnl: number
  commission: number
  swap: number
  profit: number
  strategy: string
  setup: string
  bot_id: string
  comment: string
}

interface TradeStats {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  gross_profit: number
  gross_loss: number
  profit_factor: number
  avg_win: number
  avg_loss: number
  largest_win: number
  largest_loss: number
}

interface Pagination {
  page: number
  per_page: number
  total: number
  pages: number
}

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [stats, setStats] = useState<TradeStats | null>(null)
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    per_page: 50,
    total: 0,
    pages: 0,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [filters, setFilters] = useState({
    symbol: '',
    strategy: '',
    startDate: '',
    endDate: '',
  })
  const [showFilters, setShowFilters] = useState(false)
  
  const loadTrades = async (page: number = 1) => {
    setIsLoading(true)
    try {
      const params: any = { page, per_page: 50 }
      if (filters.symbol) params.symbol = filters.symbol
      if (filters.strategy) params.strategy = filters.strategy
      if (filters.startDate) params.start_date = filters.startDate
      if (filters.endDate) params.end_date = filters.endDate
      
      const response = await tradesAPI.list(params)
      setTrades(response.data.trades)
      setPagination(response.data.pagination)
    } catch (error) {
      console.error('Failed to load trades:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  const loadStats = async () => {
    try {
      const response = await tradesAPI.getStats(30)
      setStats(response.data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }
  
  useEffect(() => {
    loadTrades()
    loadStats()
  }, [])
  
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pagination.pages) {
      loadTrades(newPage)
    }
  }
  
  const handleApplyFilters = () => {
    loadTrades(1)
    setShowFilters(false)
  }
  
  const handleResetFilters = () => {
    setFilters({ symbol: '', strategy: '', startDate: '', endDate: '' })
    loadTrades(1)
  }
  
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Histórico de Trades</h1>
          <p className="text-virtus-text-muted">Todos os trades executados</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn-secondary flex items-center gap-2"
          >
            <Filter className="w-4 h-4" />
            <span>Filtros</span>
          </button>
          <button
            onClick={() => { loadTrades(); loadStats(); }}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Atualizar</span>
          </button>
        </div>
      </div>
      
      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div className="card p-4">
            <p className="text-xs text-virtus-text-muted uppercase">Total Trades</p>
            <p className="text-xl font-bold mt-1">{stats.total_trades}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-virtus-text-muted uppercase">Win Rate</p>
            <p className="text-xl font-bold mt-1 text-virtus-accent-success">{stats.win_rate.toFixed(1)}%</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-virtus-text-muted uppercase">P&L Total</p>
            <p className={cn('text-xl font-bold mt-1', getPnLColor(stats.total_pnl))}>
              {formatCurrency(stats.total_pnl)}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-virtus-text-muted uppercase">Profit Factor</p>
            <p className="text-xl font-bold mt-1">{stats.profit_factor.toFixed(2)}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-virtus-text-muted uppercase">Avg Win</p>
            <p className="text-xl font-bold mt-1 text-virtus-accent-success">{formatCurrency(stats.avg_win)}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-virtus-text-muted uppercase">Avg Loss</p>
            <p className="text-xl font-bold mt-1 text-virtus-accent-danger">{formatCurrency(stats.avg_loss)}</p>
          </div>
        </div>
      )}
      
      {/* Filters Panel */}
      {showFilters && (
        <div className="card animate-slideDown">
          <h3 className="text-lg font-semibold mb-4">Filtros</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="label">Símbolo</label>
              <select
                value={filters.symbol}
                onChange={(e) => setFilters({ ...filters, symbol: e.target.value })}
                className="select"
              >
                <option value="">Todos</option>
                <option value="EURUSD">EURUSD</option>
                <option value="GBPUSD">GBPUSD</option>
                <option value="XAUUSD">XAUUSD</option>
              </select>
            </div>
            <div>
              <label className="label">Estratégia</label>
              <select
                value={filters.strategy}
                onChange={(e) => setFilters({ ...filters, strategy: e.target.value })}
                className="select"
              >
                <option value="">Todas</option>
                <option value="ScalpingStrategy">Scalping</option>
                <option value="TrendStrategy">Trend</option>
                <option value="ReversalStrategy">Reversal</option>
              </select>
            </div>
            <div>
              <label className="label">Data Início</label>
              <input
                type="date"
                value={filters.startDate}
                onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="label">Data Fim</label>
              <input
                type="date"
                value={filters.endDate}
                onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
                className="input"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-4">
            <button onClick={handleResetFilters} className="btn-ghost">
              Limpar
            </button>
            <button onClick={handleApplyFilters} className="btn-primary">
              Aplicar
            </button>
          </div>
        </div>
      )}
      
      {/* Trades Table */}
      <div className="card p-0 overflow-hidden">
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Símbolo</th>
                <th>Tipo</th>
                <th>Volume</th>
                <th>Entrada</th>
                <th>Saída</th>
                <th>P&L</th>
                <th>Estratégia</th>
                <th>Setup</th>
                <th>Data</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={10} className="text-center py-8">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-virtus-accent-primary" />
                  </td>
                </tr>
              ) : trades.length === 0 ? (
                <tr>
                  <td colSpan={10} className="text-center py-8 text-virtus-text-muted">
                    Nenhum trade encontrado
                  </td>
                </tr>
              ) : (
                trades.map((trade) => (
                  <tr key={trade.ticket}>
                    <td className="font-mono text-xs">{trade.ticket}</td>
                    <td className="font-medium">{trade.symbol}</td>
                    <td>
                      <span className={cn('flex items-center gap-1', getTradeTypeColor(trade.type))}>
                        {trade.type.includes('BUY') ? (
                          <TrendingUp className="w-4 h-4" />
                        ) : (
                          <TrendingDown className="w-4 h-4" />
                        )}
                        {trade.type}
                      </span>
                    </td>
                    <td>{trade.volume.toFixed(2)}</td>
                    <td className="font-mono text-xs">{trade.entry_price.toFixed(5)}</td>
                    <td className="font-mono text-xs">{trade.exit_price.toFixed(5)}</td>
                    <td className={cn('font-semibold', getPnLColor(trade.profit))}>
                      {trade.profit >= 0 ? '+' : ''}{formatCurrency(trade.profit)}
                    </td>
                    <td>
                      <span className="badge badge-info">{trade.strategy.replace('Strategy', '')}</span>
                    </td>
                    <td>
                      <span className="text-xs text-virtus-text-muted">{trade.setup}</span>
                    </td>
                    <td className="text-xs text-virtus-text-muted">
                      {formatDate(trade.exit_time)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        {pagination.pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-virtus-border-primary">
            <p className="text-sm text-virtus-text-muted">
              Mostrando {((pagination.page - 1) * pagination.per_page) + 1} a {Math.min(pagination.page * pagination.per_page, pagination.total)} de {pagination.total}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
                className="btn-ghost p-2"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="text-sm">
                Página {pagination.page} de {pagination.pages}
              </span>
              <button
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page === pagination.pages}
                className="btn-ghost p-2"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
