import { useEffect, useState } from 'react'
import { systemAPI } from '../services/api'
import { getMarketSummary, MarketSummary } from '../services/brapiService'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  RefreshCw,
  Globe,
  Building2,
  Bitcoin,
  Landmark,
  BarChart3,
  Clock,
  Calendar,
  AlertCircle,
  CheckCircle,
  Sun,
  Moon,
} from 'lucide-react'
import { cn } from '../lib/utils'
import { SkeletonDashboard } from '../components/ui/Skeleton'
import NewsAudioPlayer from '../components/NewsAudioPlayer'

interface SystemHealth {
  api: boolean
  database: boolean
  websocket: boolean
  brapi: boolean
  eodhd: boolean
  tess: boolean
}

export default function DashboardPage() {
  const [marketData, setMarketData] = useState<MarketSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    api: true,
    database: true,
    websocket: true,
    brapi: true,
    eodhd: true,
    tess: true,
  })
  
  const loadData = async (showRefresh = false) => {
    if (showRefresh) setIsRefreshing(true)
    else setIsLoading(true)
    
    try {
      const [marketRes, statusRes] = await Promise.all([
        getMarketSummary(),
        systemAPI.getStatus().catch(() => null),
      ])
      
      setMarketData(marketRes)
      setLastUpdate(new Date())
      
      if (statusRes?.data) {
        setSystemHealth({
          api: statusRes.data.status === 'healthy',
          database: statusRes.data.components?.database === 'healthy',
          websocket: true,
          brapi: true,
          eodhd: true,
          tess: true,
        })
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }
  
  useEffect(() => {
    loadData()
    
    // Auto refresh every 60 seconds
    const interval = setInterval(() => {
      loadData(true)
    }, 60000)
    
    return () => clearInterval(interval)
  }, [])
  
  const getChangeColor = (value: number) => {
    if (value > 0) return 'text-virtus-accent-success'
    if (value < 0) return 'text-virtus-accent-danger'
    return 'text-virtus-text-muted'
  }
  
  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '0.00%'
    const sign = value >= 0 ? '+' : ''
    return `${sign}${value.toFixed(2)}%`
  }
  
  const formatNumber = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '0'
    return value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  
  // Get greeting based on time
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Bom dia'
    if (hour < 18) return 'Boa tarde'
    return 'Boa noite'
  }
  
  // Check if market is open (B3: 10:00 - 17:55 Brasília time)
  const isMarketOpen = () => {
    // Usar horário de Brasília (UTC-3)
    const now = new Date()
    const brasiliaTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }))
    const hour = brasiliaTime.getHours()
    const minute = brasiliaTime.getMinutes()
    const day = brasiliaTime.getDay()
    
    // Weekend
    if (day === 0 || day === 6) return false
    
    // Before 10:00 or after 17:55
    if (hour < 10 || (hour === 17 && minute > 55) || hour > 17) return false
    
    return true
  }
  
  if (isLoading) {
    return <SkeletonDashboard />
  }
  
  // Extract data from marketData
  const ibov = marketData?.ibovespa?.results?.[0]
  const currencies = marketData?.currencies?.currency || []
  const cryptos = marketData?.crypto?.coins || []
  const usd = currencies.find(c => c.fromCurrency === 'USD')
  const eur = currencies.find(c => c.fromCurrency === 'EUR')
  const btc = cryptos.find(c => c.coin === 'BTC')
  const topStocks = marketData?.topGainers?.stocks?.slice(0, 5) || []
  const topFiis = marketData?.topLosers?.stocks?.slice(0, 5) || []
  
  return (
    <div className="space-y-4 sm:space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold flex items-center gap-2">
            {getGreeting()}! 
            {new Date().getHours() < 18 ? (
              <Sun className="w-6 h-6 text-yellow-500" />
            ) : (
              <Moon className="w-6 h-6 text-blue-400" />
            )}
          </h1>
          <p className="text-sm sm:text-base text-virtus-text-muted flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            {new Date().toLocaleDateString('pt-BR', { 
              weekday: 'long', 
              day: 'numeric', 
              month: 'long', 
              year: 'numeric' 
            })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Market Status */}
          <div className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium',
            isMarketOpen() 
              ? 'bg-virtus-accent-success/20 text-virtus-accent-success' 
              : 'bg-virtus-accent-warning/20 text-virtus-accent-warning'
          )}>
            <span className={cn(
              'w-2 h-2 rounded-full',
              isMarketOpen() ? 'bg-virtus-accent-success animate-pulse' : 'bg-virtus-accent-warning'
            )} />
            {isMarketOpen() ? 'Mercado Aberto' : 'Mercado Fechado'}
          </div>
          
          <button
            onClick={() => loadData(true)}
            disabled={isRefreshing}
            className="btn-secondary flex items-center justify-center gap-2"
          >
            <RefreshCw className={cn('w-4 h-4', isRefreshing && 'animate-spin')} />
            <span className="hidden sm:inline">Atualizar</span>
          </button>
        </div>
      </div>
      
      {/* Main Market Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Ibovespa Card */}
        <div className="card bg-gradient-to-br from-blue-600/20 to-indigo-700/20 border-blue-500/30">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-blue-500" />
              </div>
              <span className="font-medium">Ibovespa</span>
            </div>
            {(ibov?.regularMarketChangePercent ?? 0) >= 0 ? (
              <TrendingUp className="w-5 h-5 text-virtus-accent-success" />
            ) : (
              <TrendingDown className="w-5 h-5 text-virtus-accent-danger" />
            )}
          </div>
          <p className="text-2xl font-bold">
            {formatNumber(ibov?.regularMarketPrice)}
          </p>
          <p className={cn('text-sm font-medium', getChangeColor(ibov?.regularMarketChangePercent ?? 0))}>
            {formatPercent(ibov?.regularMarketChangePercent)}
          </p>
        </div>
        
        {/* USD Card */}
        <div className="card bg-gradient-to-br from-green-600/20 to-emerald-700/20 border-green-500/30">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-green-500" />
              </div>
              <span className="font-medium">Dólar</span>
            </div>
            {parseFloat(usd?.percentageChange || '0') >= 0 ? (
              <TrendingUp className="w-5 h-5 text-virtus-accent-success" />
            ) : (
              <TrendingDown className="w-5 h-5 text-virtus-accent-danger" />
            )}
          </div>
          <p className="text-2xl font-bold">
            R$ {formatNumber(parseFloat(usd?.bidPrice || '0'))}
          </p>
          <p className={cn('text-sm font-medium', getChangeColor(parseFloat(usd?.percentageChange || '0')))}>
            {formatPercent(parseFloat(usd?.percentageChange || '0'))}
          </p>
        </div>
        
        {/* EUR Card */}
        <div className="card bg-gradient-to-br from-cyan-600/20 to-blue-700/20 border-cyan-500/30">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                <Globe className="w-5 h-5 text-cyan-500" />
              </div>
              <span className="font-medium">Euro</span>
            </div>
            {parseFloat(eur?.percentageChange || '0') >= 0 ? (
              <TrendingUp className="w-5 h-5 text-virtus-accent-success" />
            ) : (
              <TrendingDown className="w-5 h-5 text-virtus-accent-danger" />
            )}
          </div>
          <p className="text-2xl font-bold">
            R$ {formatNumber(parseFloat(eur?.bidPrice || '0'))}
          </p>
          <p className={cn('text-sm font-medium', getChangeColor(parseFloat(eur?.percentageChange || '0')))}>
            {formatPercent(parseFloat(eur?.percentageChange || '0'))}
          </p>
        </div>
        
        {/* Bitcoin Card */}
        <div className="card bg-gradient-to-br from-orange-600/20 to-amber-700/20 border-orange-500/30">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
                <Bitcoin className="w-5 h-5 text-orange-500" />
              </div>
              <span className="font-medium">Bitcoin</span>
            </div>
            {(btc?.regularMarketChangePercent ?? 0) >= 0 ? (
              <TrendingUp className="w-5 h-5 text-virtus-accent-success" />
            ) : (
              <TrendingDown className="w-5 h-5 text-virtus-accent-danger" />
            )}
          </div>
          <p className="text-2xl font-bold">
            R$ {btc?.regularMarketPrice ? (btc.regularMarketPrice / 1000).toFixed(1) + 'k' : '0'}
          </p>
          <p className={cn('text-sm font-medium', getChangeColor(btc?.regularMarketChangePercent ?? 0))}>
            {formatPercent(btc?.regularMarketChangePercent ?? 0)}
          </p>
        </div>
      </div>
      
      {/* Top Movers */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Ações - Maiores Altas */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-virtus-accent-success" />
              Maiores Altas
            </h3>
            <a href="/stocks" className="text-sm text-virtus-accent-primary hover:underline">
              Ver todas →
            </a>
          </div>
          <div className="space-y-3">
            {topStocks.length > 0 ? topStocks.map((stock: any, i: number) => (
              <div key={stock.symbol || i} className="flex items-center justify-between p-3 bg-virtus-bg-tertiary rounded-lg hover:bg-virtus-bg-hover transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-virtus-accent-success/20 flex items-center justify-center font-bold text-sm">
                    {(stock.symbol || '??').slice(0, 4)}
                  </div>
                  <div>
                    <p className="font-medium">{stock.symbol || 'N/A'}</p>
                    <p className="text-xs text-virtus-text-muted truncate max-w-[150px]">
                      {stock.shortName || stock.longName || 'Empresa'}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold">R$ {formatNumber(stock.regularMarketPrice)}</p>
                  <p className={cn('text-sm', getChangeColor(stock.regularMarketChangePercent || 0))}>
                    {formatPercent(stock.regularMarketChangePercent)}
                  </p>
                </div>
              </div>
            )) : (
              <p className="text-center text-virtus-text-muted py-8">
                Carregando ações...
              </p>
            )}
          </div>
        </div>
        
        {/* Top Ações - Maiores Baixas */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-virtus-accent-danger" />
              Maiores Baixas
            </h3>
            <a href="/stocks" className="text-sm text-virtus-accent-primary hover:underline">
              Ver todas →
            </a>
          </div>
          <div className="space-y-3">
            {topFiis.length > 0 ? topFiis.map((stock: any, i: number) => (
              <div key={stock.symbol || i} className="flex items-center justify-between p-3 bg-virtus-bg-tertiary rounded-lg hover:bg-virtus-bg-hover transition-colors">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-virtus-accent-danger/20 flex items-center justify-center font-bold text-sm">
                    {(stock.symbol || '??').slice(0, 4)}
                  </div>
                  <div>
                    <p className="font-medium">{stock.symbol || 'N/A'}</p>
                    <p className="text-xs text-virtus-text-muted truncate max-w-[150px]">
                      {stock.shortName || stock.longName || 'Empresa'}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold">R$ {formatNumber(stock.regularMarketPrice)}</p>
                  <p className={cn('text-sm', getChangeColor(stock.regularMarketChangePercent || 0))}>
                    {formatPercent(stock.regularMarketChangePercent)}
                  </p>
                </div>
              </div>
            )) : (
              <p className="text-center text-virtus-text-muted py-8">
                Carregando dados...
              </p>
            )}
          </div>
        </div>
      </div>
      
      {/* Quick Actions & System Status */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <div className="card lg:col-span-2">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-virtus-accent-primary" />
            Acesso Rápido
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <a href="/screener" className="p-4 bg-virtus-bg-tertiary rounded-lg hover:bg-virtus-bg-hover transition-all hover:scale-105 text-center">
              <BarChart3 className="w-8 h-8 mx-auto mb-2 text-blue-500" />
              <p className="text-sm font-medium">Screener</p>
            </a>
            <a href="/dividends" className="p-4 bg-virtus-bg-tertiary rounded-lg hover:bg-virtus-bg-hover transition-all hover:scale-105 text-center">
              <DollarSign className="w-8 h-8 mx-auto mb-2 text-green-500" />
              <p className="text-sm font-medium">Dividendos</p>
            </a>
            <a href="/forex" className="p-4 bg-virtus-bg-tertiary rounded-lg hover:bg-virtus-bg-hover transition-all hover:scale-105 text-center">
              <Globe className="w-8 h-8 mx-auto mb-2 text-purple-500" />
              <p className="text-sm font-medium">Forex Briefing</p>
            </a>
            <a href="/fii-portfolio" className="p-4 bg-virtus-bg-tertiary rounded-lg hover:bg-virtus-bg-hover transition-all hover:scale-105 text-center">
              <Landmark className="w-8 h-8 mx-auto mb-2 text-orange-500" />
              <p className="text-sm font-medium">Carteira FIIs</p>
            </a>
          </div>
        </div>
        
        {/* System Status */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-virtus-accent-primary" />
            Status do Sistema
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">API Backend</span>
              {systemHealth.api ? (
                <CheckCircle className="w-5 h-5 text-virtus-accent-success" />
              ) : (
                <AlertCircle className="w-5 h-5 text-virtus-accent-danger" />
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Database</span>
              {systemHealth.database ? (
                <CheckCircle className="w-5 h-5 text-virtus-accent-success" />
              ) : (
                <AlertCircle className="w-5 h-5 text-virtus-accent-danger" />
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Brapi</span>
              {systemHealth.brapi ? (
                <CheckCircle className="w-5 h-5 text-virtus-accent-success" />
              ) : (
                <AlertCircle className="w-5 h-5 text-virtus-accent-danger" />
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">EODHD</span>
              {systemHealth.eodhd ? (
                <CheckCircle className="w-5 h-5 text-virtus-accent-success" />
              ) : (
                <AlertCircle className="w-5 h-5 text-virtus-accent-danger" />
              )}
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-virtus-border">
            <p className="text-xs text-virtus-text-muted flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Última atualização: {lastUpdate.toLocaleTimeString('pt-BR')}
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
