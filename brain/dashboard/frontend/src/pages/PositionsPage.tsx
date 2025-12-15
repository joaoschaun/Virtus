import { useEffect, useState } from 'react'
import { positionsAPI, ordersAPI } from '../services/api'
import { formatCurrency, cn, getTradeTypeColor, getPnLColor } from '../lib/utils'
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  XCircle,
  Clock,
  Target,
  AlertTriangle,
} from 'lucide-react'

interface Position {
  ticket: number
  symbol: string
  type: string
  volume: number
  entry_price: number
  current_price: number
  sl: number
  tp: number
  profit: number
  open_time: string
  swap: number
  commission: number
}

interface Order {
  ticket: number
  symbol: string
  type: string
  volume: number
  price: number
  sl: number
  tp: number
  expiration: string | null
}

export default function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [totalProfit, setTotalProfit] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'positions' | 'orders'>('positions')
  const [closingTicket, setClosingTicket] = useState<number | null>(null)
  
  const loadData = async () => {
    setIsLoading(true)
    try {
      const [posRes, ordRes] = await Promise.all([
        positionsAPI.list(),
        ordersAPI.list(),
      ])
      
      setPositions(posRes.data.positions)
      setTotalProfit(posRes.data.total_profit)
      setOrders(ordRes.data.orders)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  useEffect(() => {
    loadData()
    
    // Auto-refresh every 5 seconds
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])
  
  const handleClosePosition = async (ticket: number) => {
    if (!confirm('Deseja realmente fechar esta posição?')) return
    
    setClosingTicket(ticket)
    try {
      await positionsAPI.close(ticket)
      loadData()
    } catch (error) {
      console.error('Failed to close position:', error)
      alert('Erro ao fechar posição')
    } finally {
      setClosingTicket(null)
    }
  }
  
  const handleCancelOrder = async (ticket: number) => {
    if (!confirm('Deseja realmente cancelar esta ordem?')) return
    
    try {
      await ordersAPI.cancel(ticket)
      loadData()
    } catch (error) {
      console.error('Failed to cancel order:', error)
      alert('Erro ao cancelar ordem')
    }
  }
  
  const formatDuration = (openTime: string) => {
    const diff = Date.now() - new Date(openTime).getTime()
    const hours = Math.floor(diff / 3600000)
    const minutes = Math.floor((diff % 3600000) / 60000)
    return `${hours}h ${minutes}m`
  }
  
  return (
    <div className="space-y-4 sm:space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Posições & Ordens</h1>
          <p className="text-sm sm:text-base text-virtus-text-muted">Gerenciamento em tempo real</p>
        </div>
        <div className="flex items-center gap-2 sm:gap-4">
          <div className={cn(
            'px-3 sm:px-4 py-2 rounded-lg flex-1 sm:flex-none',
            totalProfit >= 0 ? 'bg-virtus-accent-success/20' : 'bg-virtus-accent-danger/20'
          )}>
            <p className="text-[10px] sm:text-xs text-virtus-text-muted">Lucro Total</p>
            <p className={cn('text-base sm:text-xl font-bold', getPnLColor(totalProfit))}>
              {totalProfit >= 0 ? '+' : ''}{formatCurrency(totalProfit)}
            </p>
          </div>
          <button onClick={loadData} className="btn-secondary flex items-center gap-2">
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
            <span className="hidden sm:inline">Atualizar</span>
          </button>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="tabs">
        <button
          onClick={() => setActiveTab('positions')}
          className={activeTab === 'positions' ? 'tab-active' : 'tab'}
        >
          Posições Abertas ({positions.length})
        </button>
        <button
          onClick={() => setActiveTab('orders')}
          className={activeTab === 'orders' ? 'tab-active' : 'tab'}
        >
          Ordens Pendentes ({orders.length})
        </button>
      </div>
      
      {/* Positions */}
      {activeTab === 'positions' && (
        <div className="space-y-4">
          {isLoading && positions.length === 0 ? (
            <div className="card flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-virtus-accent-primary" />
            </div>
          ) : positions.length === 0 ? (
            <div className="card flex flex-col items-center justify-center py-12">
              <Target className="w-12 h-12 text-virtus-text-muted mb-4" />
              <p className="text-virtus-text-muted">Nenhuma posição aberta</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {positions.map((position) => (
                <div key={position.ticket} className="card-hover">
                  <div className="flex items-center justify-between">
                    {/* Left: Symbol & Type */}
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        'w-12 h-12 rounded-lg flex items-center justify-center',
                        position.type === 'BUY' ? 'bg-virtus-accent-success/20' : 'bg-virtus-accent-danger/20'
                      )}>
                        {position.type === 'BUY' ? (
                          <TrendingUp className={cn('w-6 h-6', getTradeTypeColor(position.type))} />
                        ) : (
                          <TrendingDown className={cn('w-6 h-6', getTradeTypeColor(position.type))} />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold">{position.symbol}</span>
                          <span className={cn('badge', position.type === 'BUY' ? 'badge-success' : 'badge-danger')}>
                            {position.type}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-virtus-text-muted mt-1">
                          <span>Ticket: {position.ticket}</span>
                          <span>Volume: {position.volume}</span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            {formatDuration(position.open_time)}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Center: Prices */}
                    <div className="flex items-center gap-8">
                      <div className="text-center">
                        <p className="text-xs text-virtus-text-muted">Entrada</p>
                        <p className="font-mono">{position.entry_price.toFixed(5)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-virtus-text-muted">Atual</p>
                        <p className="font-mono">{position.current_price.toFixed(5)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-virtus-text-muted">SL</p>
                        <p className="font-mono text-virtus-accent-danger">
                          {position.sl > 0 ? position.sl.toFixed(5) : '-'}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-virtus-text-muted">TP</p>
                        <p className="font-mono text-virtus-accent-success">
                          {position.tp > 0 ? position.tp.toFixed(5) : '-'}
                        </p>
                      </div>
                    </div>
                    
                    {/* Right: Profit & Actions */}
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <p className="text-xs text-virtus-text-muted">P&L</p>
                        <p className={cn('text-2xl font-bold', getPnLColor(position.profit))}>
                          {position.profit >= 0 ? '+' : ''}{formatCurrency(position.profit)}
                        </p>
                      </div>
                      <button
                        onClick={() => handleClosePosition(position.ticket)}
                        disabled={closingTicket === position.ticket}
                        className="btn-danger flex items-center gap-2"
                      >
                        {closingTicket === position.ticket ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <XCircle className="w-4 h-4" />
                        )}
                        <span>Fechar</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Orders */}
      {activeTab === 'orders' && (
        <div className="space-y-4">
          {orders.length === 0 ? (
            <div className="card flex flex-col items-center justify-center py-12">
              <Clock className="w-12 h-12 text-virtus-text-muted mb-4" />
              <p className="text-virtus-text-muted">Nenhuma ordem pendente</p>
            </div>
          ) : (
            <div className="card p-0 overflow-hidden">
              <table className="table">
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Símbolo</th>
                    <th>Tipo</th>
                    <th>Volume</th>
                    <th>Preço</th>
                    <th>SL</th>
                    <th>TP</th>
                    <th>Expiração</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.ticket}>
                      <td className="font-mono text-xs">{order.ticket}</td>
                      <td className="font-medium">{order.symbol}</td>
                      <td>
                        <span className={cn('badge', order.type.includes('BUY') ? 'badge-success' : 'badge-danger')}>
                          {order.type}
                        </span>
                      </td>
                      <td>{order.volume}</td>
                      <td className="font-mono">{order.price.toFixed(5)}</td>
                      <td className="font-mono text-virtus-accent-danger">
                        {order.sl > 0 ? order.sl.toFixed(5) : '-'}
                      </td>
                      <td className="font-mono text-virtus-accent-success">
                        {order.tp > 0 ? order.tp.toFixed(5) : '-'}
                      </td>
                      <td className="text-xs text-virtus-text-muted">
                        {order.expiration || '-'}
                      </td>
                      <td>
                        <button
                          onClick={() => handleCancelOrder(order.ticket)}
                          className="btn-ghost text-virtus-accent-danger p-2"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
