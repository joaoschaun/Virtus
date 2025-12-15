import { useEffect, useState } from 'react'
import { dashboardAPI, mt5API } from '../services/api'
import { useTradingStore } from '../stores/tradingStore'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  Activity,
  Percent,
  BarChart3,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react'
import { formatCurrency, formatPercent, cn } from '../lib/utils'
import NewsAudioPlayer from '../components/NewsAudioPlayer'

interface OverviewData {
  account: any
  metrics: any
  bots_status: { total: number; running: number; stopped: number }
  strategies_status: { total: number; enabled: number }
  symbols_status: { total: number; enabled: number }
  mt5_connected: boolean
}

interface EquityData {
  timestamp: string
  balance: number
  equity: number
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [equityHistory, setEquityHistory] = useState<EquityData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const { metrics, isConnected } = useTradingStore()
  
  const loadData = async (showRefresh = false) => {
    if (showRefresh) setIsRefreshing(true)
    else setIsLoading(true)
    
    try {
      const [overviewRes, equityRes] = await Promise.all([
        dashboardAPI.getOverview(),
        dashboardAPI.getEquityHistory(30),
      ])
      
      setOverview(overviewRes.data)
      setEquityHistory(equityRes.data.history)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }
  
  useEffect(() => {
    loadData()
  }, [])
  
  // Use real-time metrics if available, fallback to overview
  const currentMetrics = metrics || overview?.metrics
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-virtus-accent-primary" />
      </div>
    )
  }
  
  return (
    <div className="space-y-4 sm:space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Dashboard</h1>
          <p className="text-sm sm:text-base text-virtus-text-muted">Visão geral do sistema de trading</p>
        </div>
        <button
          onClick={() => loadData(true)}
          disabled={isRefreshing}
          className="btn-secondary flex items-center justify-center gap-2 w-full sm:w-auto"
        >
          <RefreshCw className={cn('w-4 h-4', isRefreshing && 'animate-spin')} />
          <span>Atualizar</span>
        </button>
      </div>
      
      {/* Status Cards */}
      <div className="grid grid-cols-2 gap-2 sm:gap-4 md:grid-cols-4">
        {/* MT5 Status */}
        <div className="card-hover">
          <div className="flex items-center justify-between">
            <span className="text-virtus-text-muted text-sm">MT5 Status</span>
            {overview?.mt5_connected ? (
              <CheckCircle className="w-5 h-5 text-virtus-accent-success" />
            ) : (
              <XCircle className="w-5 h-5 text-virtus-accent-danger" />
            )}
          </div>
          <p className={cn(
            'text-lg font-semibold mt-1',
            overview?.mt5_connected ? 'text-virtus-accent-success' : 'text-virtus-accent-danger'
          )}>
            {overview?.mt5_connected ? 'Conectado' : 'Desconectado'}
          </p>
        </div>
        
        {/* Bots Status */}
        <div className="card-hover">
          <div className="flex items-center justify-between">
            <span className="text-virtus-text-muted text-sm">Bots Ativos</span>
            <Activity className="w-5 h-5 text-virtus-accent-primary" />
          </div>
          <p className="text-lg font-semibold mt-1">
            {overview?.bots_status?.running ?? 0}/{overview?.bots_status?.total ?? 0}
          </p>
        </div>
        
        {/* Strategies */}
        <div className="card-hover">
          <div className="flex items-center justify-between">
            <span className="text-virtus-text-muted text-sm">Estratégias</span>
            <Target className="w-5 h-5 text-virtus-accent-secondary" />
          </div>
          <p className="text-lg font-semibold mt-1">
            {overview?.strategies_status?.enabled ?? 0}/{overview?.strategies_status?.total ?? 0}
          </p>
        </div>
        
        {/* Symbols */}
        <div className="card-hover">
          <div className="flex items-center justify-between">
            <span className="text-virtus-text-muted text-sm">Símbolos</span>
            <BarChart3 className="w-5 h-5 text-virtus-accent-info" />
          </div>
          <p className="text-lg font-semibold mt-1">
            {overview?.symbols_status?.enabled ?? 0}/{overview?.symbols_status?.total ?? 0}
          </p>
        </div>
      </div>
      
      {/* Main Metrics */}
      <div className="grid grid-cols-2 gap-2 sm:gap-4 lg:grid-cols-4">
        {/* Balance */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Saldo</span>
            <DollarSign className="w-5 h-5 text-virtus-accent-primary" />
          </div>
          <p className="stat-value">{formatCurrency(currentMetrics?.balance || 0)}</p>
        </div>
        
        {/* Equity */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Patrimônio</span>
            <TrendingUp className="w-5 h-5 text-virtus-accent-success" />
          </div>
          <p className="stat-value">{formatCurrency(currentMetrics?.equity || 0)}</p>
          <div className={cn(
            'stat-change flex items-center gap-1',
            (currentMetrics?.profit || 0) >= 0 ? 'stat-change-positive' : 'stat-change-negative'
          )}>
            {(currentMetrics?.profit || 0) >= 0 ? (
              <ArrowUpRight className="w-4 h-4" />
            ) : (
              <ArrowDownRight className="w-4 h-4" />
            )}
            <span>{formatCurrency(currentMetrics?.profit || 0)}</span>
          </div>
        </div>
        
        {/* Daily P&L */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">P&L Diário</span>
            <Clock className="w-5 h-5 text-virtus-accent-warning" />
          </div>
          <p className={cn(
            'stat-value',
            (currentMetrics?.daily_pnl || 0) >= 0 ? 'profit' : 'loss'
          )}>
            {(currentMetrics?.daily_pnl || 0) >= 0 ? '+' : ''}{formatCurrency(currentMetrics?.daily_pnl || 0)}
          </p>
        </div>
        
        {/* Win Rate */}
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Win Rate</span>
            <Percent className="w-5 h-5 text-virtus-accent-info" />
          </div>
          <p className="stat-value">{(currentMetrics?.win_rate || 0).toFixed(1)}%</p>
          <p className="text-xs text-virtus-text-muted mt-1">
            {currentMetrics?.winning_trades || 0}W / {currentMetrics?.losing_trades || 0}L
          </p>
        </div>
      </div>
      
      {/* Secondary Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-4">
        <div className="card p-4">
          <p className="text-xs text-virtus-text-muted uppercase">Profit Factor</p>
          <p className="text-xl font-bold mt-1">{(currentMetrics?.profit_factor || 0).toFixed(2)}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-virtus-text-muted uppercase">Sharpe Ratio</p>
          <p className="text-xl font-bold mt-1">{(currentMetrics?.sharpe_ratio || 0).toFixed(2)}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-virtus-text-muted uppercase">Max Drawdown</p>
          <p className="text-xl font-bold text-virtus-accent-danger mt-1">
            -{(currentMetrics?.max_drawdown || 0).toFixed(2)}%
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-virtus-text-muted uppercase">Current DD</p>
          <p className={cn(
            'text-xl font-bold mt-1',
            (currentMetrics?.current_drawdown || 0) > 3 ? 'text-virtus-accent-danger' : 'text-virtus-accent-warning'
          )}>
            -{(currentMetrics?.current_drawdown || 0).toFixed(2)}%
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-virtus-text-muted uppercase">Posições Abertas</p>
          <p className="text-xl font-bold mt-1">{currentMetrics?.active_positions || 0}</p>
        </div>
      </div>
      
      {/* Charts */}
      <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
        {/* Equity Curve */}
        <div className="card virtus-card-accent">
          <h3 className="text-lg font-semibold mb-4">Evolução do Patrimônio</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={(equityHistory || []).slice(-168)}>
                <defs>
                  <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#E53935" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#E53935" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a32" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(value) => new Date(value).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
                  stroke="#707078"
                  fontSize={11}
                />
                <YAxis 
                  stroke="#707078"
                  fontSize={11}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#16161b',
                    border: '1px solid #2a2a32',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number) => [formatCurrency(value), 'Patrimônio']}
                  labelFormatter={(label) => new Date(label).toLocaleString('pt-BR')}
                />
                <Area 
                  type="monotone" 
                  dataKey="equity" 
                  stroke="#E53935" 
                  fill="url(#equityGradient)" 
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        {/* Balance vs Equity */}
        <div className="card virtus-card-accent">
          <h3 className="text-lg font-semibold mb-4">Saldo vs Patrimônio</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={(equityHistory || []).slice(-168)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a32" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(value) => new Date(value).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
                  stroke="#707078"
                  fontSize={11}
                />
                <YAxis 
                  stroke="#707078"
                  fontSize={11}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#16161b',
                    border: '1px solid #2a2a32',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number, name: string) => [
                    formatCurrency(value), 
                    name === 'balance' ? 'Saldo' : 'Patrimônio'
                  ]}
                  labelFormatter={(label) => new Date(label).toLocaleString('pt-BR')}
                />
                <Line 
                  type="monotone" 
                  dataKey="balance" 
                  stroke="#FF5252" 
                  strokeWidth={2}
                  dot={false}
                />
                <Line 
                  type="monotone" 
                  dataKey="equity" 
                  stroke="#E53935" 
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      
      {/* P&L Summary */}
      <div className="card">
        <h3 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4">Resumo de Performance</h3>
        <div className="grid grid-cols-3 gap-2 sm:gap-6">
          <div className="text-center p-2 sm:p-4 bg-virtus-bg-tertiary rounded-lg">
            <p className="text-xs sm:text-sm text-virtus-text-muted">Diário</p>
            <p className={cn(
              'text-sm sm:text-2xl font-bold mt-1 sm:mt-2',
              (currentMetrics?.daily_pnl || 0) >= 0 ? 'profit' : 'loss'
            )}>
              {formatCurrency(currentMetrics?.daily_pnl || 0)}
            </p>
          </div>
          <div className="text-center p-2 sm:p-4 bg-virtus-bg-tertiary rounded-lg">
            <p className="text-xs sm:text-sm text-virtus-text-muted">Semanal</p>
            <p className={cn(
              'text-sm sm:text-2xl font-bold mt-1 sm:mt-2',
              (currentMetrics?.weekly_pnl || 0) >= 0 ? 'profit' : 'loss'
            )}>
              {formatCurrency(currentMetrics?.weekly_pnl || 0)}
            </p>
          </div>
          <div className="text-center p-2 sm:p-4 bg-virtus-bg-tertiary rounded-lg">
            <p className="text-xs sm:text-sm text-virtus-text-muted">Mensal</p>
            <p className={cn(
              'text-sm sm:text-2xl font-bold mt-1 sm:mt-2',
              (currentMetrics?.monthly_pnl || 0) >= 0 ? 'profit' : 'loss'
            )}>
              {formatCurrency(currentMetrics?.monthly_pnl || 0)}
            </p>
          </div>
        </div>
      </div>

      {/* News Audio Player */}
      <div className="card p-0 overflow-hidden">
        <NewsAudioPlayer />
      </div>
    </div>
  )
}
