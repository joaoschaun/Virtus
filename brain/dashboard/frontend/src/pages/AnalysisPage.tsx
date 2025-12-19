import { useEffect, useState } from 'react'
import { analysisAPI } from '../services/api'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { RefreshCw, Calendar, TrendingUp, Target, Clock } from 'lucide-react'
import { cn, formatCurrency, getPnLColor } from '../lib/utils'

interface HourlyData {
  hour: number
  trades: number
  pnl: number
}

interface WeekdayData {
  day: string
  trades: number
  pnl: number
}

interface Attribution {
  [key: string]: {
    trades: number
    pnl: number
    wins: number
    win_rate: number
  }
}

export default function AnalysisPage() {
  const [period, setPeriod] = useState<'day' | 'week' | 'month' | 'year'>('month')
  const [hourlyData, setHourlyData] = useState<HourlyData[]>([])
  const [weekdayData, setWeekdayData] = useState<WeekdayData[]>([])
  const [attribution, setAttribution] = useState<{
    by_strategy: Attribution
    by_setup: Attribution
    by_symbol: Attribution
  } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'time' | 'attribution'>('time')
  
  const loadData = async () => {
    setIsLoading(true)
    try {
      const [perfRes, attrRes] = await Promise.all([
        analysisAPI.getPerformance(period),
        analysisAPI.getAttribution(),
      ])
      
      setHourlyData(perfRes.data?.hourly_performance || [])
      setWeekdayData(perfRes.data?.weekday_performance || [])
      setAttribution(attrRes.data || null)
    } catch (error) {
      console.error('Failed to load analysis:', error)
      setHourlyData([])
      setWeekdayData([])
      setAttribution(null)
    } finally {
      setIsLoading(false)
    }
  }
  
  useEffect(() => {
    loadData()
  }, [period])
  
  const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']
  
  const formatAttributionForChart = (data: Attribution | undefined) => {
    if (!data) return []
    return Object.entries(data).map(([name, stats]) => ({
      name: name.replace('Strategy', ''),
      pnl: stats.pnl,
      trades: stats.trades,
      winRate: stats.win_rate,
    }))
  }
  
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Análise de Performance</h1>
          <p className="text-virtus-text-muted">Análise detalhada dos resultados de trading</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as any)}
            className="select w-40"
          >
            <option value="day">Hoje</option>
            <option value="week">Esta Semana</option>
            <option value="month">Este Mês</option>
            <option value="year">Este Ano</option>
          </select>
          <button onClick={loadData} className="btn-secondary flex items-center gap-2">
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
            <span>Atualizar</span>
          </button>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="tabs">
        <button
          onClick={() => setActiveTab('time')}
          className={activeTab === 'time' ? 'tab-active' : 'tab'}
        >
          <Clock className="w-4 h-4 mr-2 inline" />
          Análise Temporal
        </button>
        <button
          onClick={() => setActiveTab('attribution')}
          className={activeTab === 'attribution' ? 'tab-active' : 'tab'}
        >
          <Target className="w-4 h-4 mr-2 inline" />
          Atribuição
        </button>
      </div>
      
      {isLoading ? (
        <div className="card flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-virtus-accent-primary" />
        </div>
      ) : (
        <>
          {/* Time Analysis */}
          {activeTab === 'time' && (
            <div className="space-y-6">
              {/* Hourly Performance */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Performance por Hora</h3>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={hourlyData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                      <XAxis 
                        dataKey="hour" 
                        stroke="#6a6a7a"
                        tickFormatter={(h) => `${h}h`}
                      />
                      <YAxis stroke="#6a6a7a" />
                      <Tooltip 
                        contentStyle={{
                          backgroundColor: '#15151f',
                          border: '1px solid #2a2a3a',
                          borderRadius: '8px',
                        }}
                        formatter={(value: number, name: string) => [
                          name === 'pnl' ? formatCurrency(value) : value,
                          name === 'pnl' ? 'P&L' : 'Trades'
                        ]}
                        labelFormatter={(h) => `${h}:00 - ${h}:59`}
                      />
                      <Bar 
                        dataKey="pnl" 
                        fill="#3b82f6" 
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              
              {/* Weekday Performance */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Performance por Dia da Semana</h3>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={weekdayData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                      <XAxis type="number" stroke="#6a6a7a" />
                      <YAxis dataKey="day" type="category" stroke="#6a6a7a" width={40} />
                      <Tooltip 
                        contentStyle={{
                          backgroundColor: '#15151f',
                          border: '1px solid #2a2a3a',
                          borderRadius: '8px',
                        }}
                        formatter={(value: number, name: string) => [
                          name === 'pnl' ? formatCurrency(value) : value,
                          name === 'pnl' ? 'P&L' : 'Trades'
                        ]}
                      />
                      <Bar 
                        dataKey="pnl" 
                        fill="#8b5cf6" 
                        radius={[0, 4, 4, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              
              {/* Best/Worst Hours */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="card">
                  <h3 className="text-lg font-semibold mb-4 text-virtus-accent-success">
                    Melhores Horários
                  </h3>
                  <div className="space-y-3">
                    {hourlyData
                      .filter(h => h.pnl > 0)
                      .sort((a, b) => b.pnl - a.pnl)
                      .slice(0, 5)
                      .map((h) => (
                        <div key={h.hour} className="flex justify-between items-center p-3 bg-virtus-bg-tertiary rounded-lg">
                          <span className="font-medium">{h.hour}:00 - {h.hour}:59</span>
                          <div className="text-right">
                            <p className="font-semibold text-virtus-accent-success">
                              {formatCurrency(h.pnl)}
                            </p>
                            <p className="text-xs text-virtus-text-muted">{h.trades} trades</p>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
                
                <div className="card">
                  <h3 className="text-lg font-semibold mb-4 text-virtus-accent-danger">
                    Piores Horários
                  </h3>
                  <div className="space-y-3">
                    {hourlyData
                      .filter(h => h.pnl < 0)
                      .sort((a, b) => a.pnl - b.pnl)
                      .slice(0, 5)
                      .map((h) => (
                        <div key={h.hour} className="flex justify-between items-center p-3 bg-virtus-bg-tertiary rounded-lg">
                          <span className="font-medium">{h.hour}:00 - {h.hour}:59</span>
                          <div className="text-right">
                            <p className="font-semibold text-virtus-accent-danger">
                              {formatCurrency(h.pnl)}
                            </p>
                            <p className="text-xs text-virtus-text-muted">{h.trades} trades</p>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Attribution Analysis */}
          {activeTab === 'attribution' && attribution && (
            <div className="space-y-6">
              {/* Strategy Attribution */}
              <div className="grid lg:grid-cols-2 gap-6">
                <div className="card">
                  <h3 className="text-lg font-semibold mb-4">P&L por Estratégia</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={formatAttributionForChart(attribution.by_strategy)}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={100}
                          dataKey="pnl"
                          nameKey="name"
                          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        >
                          {formatAttributionForChart(attribution.by_strategy).map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip 
                          contentStyle={{
                            backgroundColor: '#15151f',
                            border: '1px solid #2a2a3a',
                            borderRadius: '8px',
                          }}
                          formatter={(value: number) => formatCurrency(value)}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                
                <div className="card">
                  <h3 className="text-lg font-semibold mb-4">Detalhes por Estratégia</h3>
                  <div className="space-y-3">
                    {Object.entries(attribution.by_strategy).map(([name, stats], i) => (
                      <div key={name} className="flex justify-between items-center p-3 bg-virtus-bg-tertiary rounded-lg">
                        <div className="flex items-center gap-3">
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: COLORS[i % COLORS.length] }}
                          />
                          <span className="font-medium">{name.replace('Strategy', '')}</span>
                        </div>
                        <div className="text-right">
                          <p className={cn('font-semibold', getPnLColor(stats.pnl))}>
                            {formatCurrency(stats.pnl)}
                          </p>
                          <p className="text-xs text-virtus-text-muted">
                            {stats.trades} trades • {stats.win_rate.toFixed(1)}% WR
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              
              {/* Symbol Attribution */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Performance por Símbolo</h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={formatAttributionForChart(attribution.by_symbol)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                      <XAxis dataKey="name" stroke="#6a6a7a" />
                      <YAxis stroke="#6a6a7a" />
                      <Tooltip 
                        contentStyle={{
                          backgroundColor: '#15151f',
                          border: '1px solid #2a2a3a',
                          borderRadius: '8px',
                        }}
                        formatter={(value: number, name: string) => [
                          name === 'pnl' ? formatCurrency(value) : `${value}%`,
                          name === 'pnl' ? 'P&L' : 'Win Rate'
                        ]}
                      />
                      <Bar dataKey="pnl" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              
              {/* Setup Attribution */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Performance por Setup</h3>
                <div className="table-container">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Setup</th>
                        <th className="text-right">Trades</th>
                        <th className="text-right">Win Rate</th>
                        <th className="text-right">P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(attribution.by_setup)
                        .sort((a, b) => b[1].pnl - a[1].pnl)
                        .map(([setup, stats]) => (
                          <tr key={setup}>
                            <td className="font-medium">{setup}</td>
                            <td className="text-right">{stats.trades}</td>
                            <td className="text-right">
                              <span className={cn(
                                stats.win_rate >= 50 ? 'text-virtus-accent-success' : 'text-virtus-accent-danger'
                              )}>
                                {stats.win_rate.toFixed(1)}%
                              </span>
                            </td>
                            <td className={cn('text-right font-semibold', getPnLColor(stats.pnl))}>
                              {formatCurrency(stats.pnl)}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
