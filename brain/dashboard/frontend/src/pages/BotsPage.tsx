import { useEffect, useState } from 'react'
import { botsAPI } from '../services/api'
import { cn, getStatusBadge } from '../lib/utils'
import {
  Bot,
  Play,
  Pause,
  Square,
  Settings,
  RefreshCw,
  CheckCircle,
  XCircle,
  Activity,
} from 'lucide-react'

interface BotConfig {
  enabled: boolean
  max_positions: number
  risk_per_trade: number
  max_daily_loss: number
  max_daily_trades: number
}

interface BotData {
  id: string
  symbol: string
  status: string
  config: BotConfig
}

export default function BotsPage() {
  const [bots, setBots] = useState<BotData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [editingBot, setEditingBot] = useState<BotData | null>(null)
  const [editConfig, setEditConfig] = useState<BotConfig | null>(null)
  
  const loadBots = async () => {
    setIsLoading(true)
    try {
      const response = await botsAPI.list()
      setBots(response.data.bots)
    } catch (error) {
      console.error('Failed to load bots:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  useEffect(() => {
    loadBots()
  }, [])
  
  const handleControl = async (botId: string, action: 'start' | 'stop' | 'pause') => {
    setActionLoading(botId)
    try {
      await botsAPI.control(botId, action)
      loadBots()
    } catch (error) {
      console.error('Failed to control bot:', error)
      alert('Erro ao controlar bot')
    } finally {
      setActionLoading(null)
    }
  }
  
  const handleSaveConfig = async () => {
    if (!editingBot || !editConfig) return
    
    try {
      await botsAPI.updateConfig(editingBot.id, editConfig)
      setEditingBot(null)
      setEditConfig(null)
      loadBots()
    } catch (error) {
      console.error('Failed to save config:', error)
      alert('Erro ao salvar configuração')
    }
  }
  
  const openEditModal = (bot: BotData) => {
    setEditingBot(bot)
    setEditConfig({ ...bot.config })
  }
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Activity className="w-5 h-5 text-virtus-accent-success animate-pulse" />
      case 'stopped':
        return <XCircle className="w-5 h-5 text-virtus-accent-danger" />
      case 'paused':
        return <Pause className="w-5 h-5 text-virtus-accent-warning" />
      default:
        return <Bot className="w-5 h-5" />
    }
  }
  
  return (
    <div className="space-y-4 sm:space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">Gerenciamento de Bots</h1>
          <p className="text-sm sm:text-base text-virtus-text-muted">Controle e configure seus robôs de trading</p>
        </div>
        <button onClick={loadBots} className="btn-secondary flex items-center justify-center gap-2 w-full sm:w-auto">
          <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          <span>Atualizar</span>
        </button>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 sm:gap-4">
        <div className="card p-3 sm:p-4 flex flex-col sm:flex-row items-center gap-2 sm:gap-4">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-virtus-accent-primary/20 flex items-center justify-center">
            <Bot className="w-5 h-5 sm:w-6 sm:h-6 text-virtus-accent-primary" />
          </div>
          <div className="text-center sm:text-left">
            <p className="text-[10px] sm:text-xs text-virtus-text-muted uppercase">Total</p>
            <p className="text-lg sm:text-2xl font-bold">{bots.length}</p>
          </div>
        </div>
        <div className="card p-3 sm:p-4 flex flex-col sm:flex-row items-center gap-2 sm:gap-4">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-virtus-accent-success/20 flex items-center justify-center">
            <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-virtus-accent-success" />
          </div>
          <div className="text-center sm:text-left">
            <p className="text-[10px] sm:text-xs text-virtus-text-muted uppercase">Ativos</p>
            <p className="text-lg sm:text-2xl font-bold text-virtus-accent-success">
              {bots.filter(b => b.status === 'running').length}
            </p>
          </div>
        </div>
        <div className="card p-3 sm:p-4 flex flex-col sm:flex-row items-center gap-2 sm:gap-4">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-virtus-accent-danger/20 flex items-center justify-center">
            <XCircle className="w-5 h-5 sm:w-6 sm:h-6 text-virtus-accent-danger" />
          </div>
          <div className="text-center sm:text-left">
            <p className="text-[10px] sm:text-xs text-virtus-text-muted uppercase">Parados</p>
            <p className="text-lg sm:text-2xl font-bold text-virtus-accent-danger">
              {bots.filter(b => b.status === 'stopped').length}
            </p>
          </div>
        </div>
      </div>
      
      {/* Bots Grid */}
      {isLoading ? (
        <div className="card flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-virtus-accent-primary" />
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {bots.map((bot) => (
            <div key={bot.id} className="card-hover">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  {getStatusIcon(bot.status)}
                  <div>
                    <h3 className="font-semibold">{bot.id.replace('_', ' ').toUpperCase()}</h3>
                    <p className="text-sm text-virtus-text-muted">{bot.symbol}</p>
                  </div>
                </div>
                <span className={cn('badge', getStatusBadge(bot.status))}>
                  {bot.status}
                </span>
              </div>
              
              {/* Config Info */}
              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-virtus-text-muted">Max Posições</span>
                  <span>{bot.config.max_positions}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-virtus-text-muted">Risco/Trade</span>
                  <span>{bot.config.risk_per_trade}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-virtus-text-muted">Max Loss Diário</span>
                  <span>{bot.config.max_daily_loss}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-virtus-text-muted">Max Trades/Dia</span>
                  <span>{bot.config.max_daily_trades}</span>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex gap-2">
                {bot.status === 'running' ? (
                  <>
                    <button
                      onClick={() => handleControl(bot.id, 'pause')}
                      disabled={actionLoading === bot.id}
                      className="btn-secondary flex-1 flex items-center justify-center gap-2"
                    >
                      <Pause className="w-4 h-4" />
                      <span>Pausar</span>
                    </button>
                    <button
                      onClick={() => handleControl(bot.id, 'stop')}
                      disabled={actionLoading === bot.id}
                      className="btn-danger flex-1 flex items-center justify-center gap-2"
                    >
                      <Square className="w-4 h-4" />
                      <span>Parar</span>
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => handleControl(bot.id, 'start')}
                    disabled={actionLoading === bot.id}
                    className="btn-success flex-1 flex items-center justify-center gap-2"
                  >
                    {actionLoading === bot.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    <span>Iniciar</span>
                  </button>
                )}
                <button
                  onClick={() => openEditModal(bot)}
                  className="btn-ghost p-2"
                >
                  <Settings className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Edit Modal */}
      {editingBot && editConfig && (
        <div className="modal-overlay" onClick={() => setEditingBot(null)}>
          <div className="modal animate-slideUp" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="text-lg font-semibold">
                Configurar {editingBot.id.replace('_', ' ').toUpperCase()}
              </h3>
              <button onClick={() => setEditingBot(null)} className="btn-ghost p-1">
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <div className="modal-body space-y-4">
              <div>
                <label className="label">Máximo de Posições</label>
                <input
                  type="number"
                  value={editConfig.max_positions}
                  onChange={(e) => setEditConfig({
                    ...editConfig,
                    max_positions: parseInt(e.target.value)
                  })}
                  className="input"
                  min="1"
                  max="10"
                />
              </div>
              <div>
                <label className="label">Risco por Trade (%)</label>
                <input
                  type="number"
                  value={editConfig.risk_per_trade}
                  onChange={(e) => setEditConfig({
                    ...editConfig,
                    risk_per_trade: parseFloat(e.target.value)
                  })}
                  className="input"
                  min="0.1"
                  max="5"
                  step="0.1"
                />
              </div>
              <div>
                <label className="label">Máximo Loss Diário (%)</label>
                <input
                  type="number"
                  value={editConfig.max_daily_loss}
                  onChange={(e) => setEditConfig({
                    ...editConfig,
                    max_daily_loss: parseFloat(e.target.value)
                  })}
                  className="input"
                  min="1"
                  max="20"
                  step="0.5"
                />
              </div>
              <div>
                <label className="label">Máximo Trades por Dia</label>
                <input
                  type="number"
                  value={editConfig.max_daily_trades}
                  onChange={(e) => setEditConfig({
                    ...editConfig,
                    max_daily_trades: parseInt(e.target.value)
                  })}
                  className="input"
                  min="1"
                  max="50"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={() => setEditingBot(null)} className="btn-secondary">
                Cancelar
              </button>
              <button onClick={handleSaveConfig} className="btn-primary">
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
