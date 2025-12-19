import { useEffect, useState } from 'react'
import { externalBotsAPI } from '../services/api'
import { cn } from '../lib/utils'
import {
  Bot,
  RefreshCw,
  CheckCircle,
  XCircle,
  Activity,
  Wifi,
  WifiOff,
  TrendingUp,
  TrendingDown,
  Clock,
  DollarSign,
  Target,
  Zap,
  ChevronDown,
  ChevronUp,
  BarChart3,
  AlertTriangle,
} from 'lucide-react'

interface ExternalBotStatus {
  is_running: boolean
  is_connected: boolean
  account_balance: number
  account_equity: number
  open_positions: number
  daily_profit: number
  daily_trades: number
  uptime_seconds: number
  last_trade_time: string
  errors: string[]
  updated_at: string
}

interface ExternalBotMetrics {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_profit: number
  total_profit_pips: number
  max_drawdown: number
  profit_factor: number
  average_win: number
  average_loss: number
  best_trade: number
  worst_trade: number
  period: string
  updated_at: string
}

interface ExternalBot {
  bot_id: string
  bot_name: string
  is_active: boolean
  created_at: string
  last_used: string | null
  status: ExternalBotStatus | null
  metrics: ExternalBotMetrics | null
}

export default function ExternalBotsSection() {
  const [bots, setBots] = useState<ExternalBot[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [expandedBot, setExpandedBot] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadBots = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await externalBotsAPI.list()
      setBots(response.data?.bots || [])
    } catch (err: any) {
      console.error('Failed to load external bots:', err)
      setError('Falha ao carregar bots externos')
      setBots([])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadBots()
    // Auto-refresh a cada 30 segundos
    const interval = setInterval(loadBots, 30000)
    return () => clearInterval(interval)
  }, [])

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }

  const formatDateTime = (isoString: string | null): string => {
    if (!isoString) return 'N/A'
    try {
      return new Date(isoString).toLocaleString('pt-BR')
    } catch {
      return isoString
    }
  }

  if (isLoading && bots.length === 0) {
    return (
      <div className="card flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-virtus-accent-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="card flex items-center justify-center py-12 text-virtus-accent-danger">
        <AlertTriangle className="w-6 h-6 mr-2" />
        <span>{error}</span>
      </div>
    )
  }

  if (bots.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center py-12 text-virtus-text-muted">
        <Bot className="w-12 h-12 mb-3 opacity-50" />
        <p>Nenhum bot externo integrado</p>
        <p className="text-sm">Bots externos aparecerão aqui quando conectados via API</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-virtus-accent-warning" />
          <h2 className="text-lg font-semibold">Bots Externos</h2>
          <span className="badge badge-primary">{bots.length}</span>
        </div>
        <button 
          onClick={loadBots} 
          className="btn-ghost p-2"
          title="Atualizar"
        >
          <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
        </button>
      </div>

      {/* Bots List */}
      <div className="space-y-3">
        {bots.map((bot) => (
          <div key={bot.bot_id} className="card-hover">
            {/* Bot Header */}
            <div 
              className="flex items-center justify-between cursor-pointer"
              onClick={() => setExpandedBot(expandedBot === bot.bot_id ? null : bot.bot_id)}
            >
              <div className="flex items-center gap-3">
                {/* Status Icon */}
                <div className={cn(
                  'w-10 h-10 rounded-lg flex items-center justify-center',
                  bot.status?.is_running 
                    ? 'bg-virtus-accent-success/20' 
                    : 'bg-virtus-accent-danger/20'
                )}>
                  {bot.status?.is_running ? (
                    <Activity className="w-5 h-5 text-virtus-accent-success animate-pulse" />
                  ) : (
                    <XCircle className="w-5 h-5 text-virtus-accent-danger" />
                  )}
                </div>

                {/* Bot Info */}
                <div>
                  <h3 className="font-semibold flex items-center gap-2">
                    {bot.bot_name}
                    {bot.status?.is_connected ? (
                      <Wifi className="w-4 h-4 text-virtus-accent-success" />
                    ) : (
                      <WifiOff className="w-4 h-4 text-virtus-accent-danger" />
                    )}
                  </h3>
                  <p className="text-sm text-virtus-text-muted">{bot.bot_id}</p>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="flex items-center gap-4">
                {bot.status && (
                  <>
                    {/* Daily Profit */}
                    <div className="hidden sm:flex items-center gap-1">
                      {bot.status.daily_profit >= 0 ? (
                        <TrendingUp className="w-4 h-4 text-virtus-accent-success" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-virtus-accent-danger" />
                      )}
                      <span className={cn(
                        'font-medium',
                        bot.status.daily_profit >= 0 
                          ? 'text-virtus-accent-success' 
                          : 'text-virtus-accent-danger'
                      )}>
                        ${bot.status.daily_profit.toFixed(2)}
                      </span>
                    </div>

                    {/* Balance */}
                    <div className="hidden md:flex items-center gap-1 text-virtus-text-muted">
                      <DollarSign className="w-4 h-4" />
                      <span>${bot.status.account_balance?.toLocaleString()}</span>
                    </div>
                  </>
                )}

                {/* Status Badge */}
                <span className={cn(
                  'badge',
                  bot.status?.is_running 
                    ? 'badge-success' 
                    : 'badge-danger'
                )}>
                  {bot.status?.is_running ? 'Online' : 'Offline'}
                </span>

                {/* Expand Icon */}
                {expandedBot === bot.bot_id ? (
                  <ChevronUp className="w-5 h-5 text-virtus-text-muted" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-virtus-text-muted" />
                )}
              </div>
            </div>

            {/* Expanded Details */}
            {expandedBot === bot.bot_id && (
              <div className="mt-4 pt-4 border-t border-virtus-secondary/30 animate-fadeIn">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  {/* Status Cards */}
                  {bot.status && (
                    <>
                      <div className="bg-virtus-secondary/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-virtus-text-muted text-sm mb-1">
                          <DollarSign className="w-4 h-4" />
                          <span>Balance</span>
                        </div>
                        <p className="text-lg font-semibold">
                          ${bot.status.account_balance?.toLocaleString()}
                        </p>
                      </div>

                      <div className="bg-virtus-secondary/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-virtus-text-muted text-sm mb-1">
                          <Target className="w-4 h-4" />
                          <span>Equity</span>
                        </div>
                        <p className="text-lg font-semibold">
                          ${bot.status.account_equity?.toLocaleString()}
                        </p>
                      </div>

                      <div className="bg-virtus-secondary/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-virtus-text-muted text-sm mb-1">
                          <Activity className="w-4 h-4" />
                          <span>Posições</span>
                        </div>
                        <p className="text-lg font-semibold">
                          {bot.status.open_positions}
                        </p>
                      </div>

                      <div className="bg-virtus-secondary/30 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-virtus-text-muted text-sm mb-1">
                          <Clock className="w-4 h-4" />
                          <span>Uptime</span>
                        </div>
                        <p className="text-lg font-semibold">
                          {formatUptime(bot.status.uptime_seconds)}
                        </p>
                      </div>
                    </>
                  )}
                </div>

                {/* Metrics */}
                {bot.metrics && (
                  <div className="mt-4">
                    <h4 className="text-sm font-semibold text-virtus-text-muted mb-3 flex items-center gap-2">
                      <BarChart3 className="w-4 h-4" />
                      Métricas ({bot.metrics.period})
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div className="text-center p-2 bg-virtus-secondary/20 rounded">
                        <p className="text-xs text-virtus-text-muted">Win Rate</p>
                        <p className={cn(
                          'text-lg font-bold',
                          bot.metrics.win_rate >= 0.5 
                            ? 'text-virtus-accent-success' 
                            : 'text-virtus-accent-danger'
                        )}>
                          {(bot.metrics.win_rate * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div className="text-center p-2 bg-virtus-secondary/20 rounded">
                        <p className="text-xs text-virtus-text-muted">Profit Factor</p>
                        <p className={cn(
                          'text-lg font-bold',
                          bot.metrics.profit_factor >= 1 
                            ? 'text-virtus-accent-success' 
                            : 'text-virtus-accent-danger'
                        )}>
                          {bot.metrics.profit_factor.toFixed(2)}
                        </p>
                      </div>
                      <div className="text-center p-2 bg-virtus-secondary/20 rounded">
                        <p className="text-xs text-virtus-text-muted">Total Profit</p>
                        <p className={cn(
                          'text-lg font-bold',
                          bot.metrics.total_profit >= 0 
                            ? 'text-virtus-accent-success' 
                            : 'text-virtus-accent-danger'
                        )}>
                          ${bot.metrics.total_profit.toFixed(2)}
                        </p>
                      </div>
                      <div className="text-center p-2 bg-virtus-secondary/20 rounded">
                        <p className="text-xs text-virtus-text-muted">Drawdown</p>
                        <p className="text-lg font-bold text-virtus-accent-warning">
                          ${bot.metrics.max_drawdown.toFixed(2)}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mt-3 text-sm">
                      <div className="text-center">
                        <p className="text-virtus-text-muted">Total</p>
                        <p className="font-medium">{bot.metrics.total_trades}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-virtus-text-muted">Wins</p>
                        <p className="font-medium text-virtus-accent-success">{bot.metrics.winning_trades}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-virtus-text-muted">Losses</p>
                        <p className="font-medium text-virtus-accent-danger">{bot.metrics.losing_trades}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-virtus-text-muted">Avg Win</p>
                        <p className="font-medium">${bot.metrics.average_win.toFixed(2)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-virtus-text-muted">Avg Loss</p>
                        <p className="font-medium">${bot.metrics.average_loss.toFixed(2)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-virtus-text-muted">Pips</p>
                        <p className="font-medium">{bot.metrics.total_profit_pips.toFixed(1)}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Footer Info */}
                <div className="mt-4 pt-3 border-t border-virtus-secondary/30 flex flex-wrap gap-4 text-xs text-virtus-text-muted">
                  <span>Criado: {formatDateTime(bot.created_at)}</span>
                  <span>Último uso: {formatDateTime(bot.last_used)}</span>
                  {bot.status && (
                    <span>Atualizado: {formatDateTime(bot.status.updated_at)}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
