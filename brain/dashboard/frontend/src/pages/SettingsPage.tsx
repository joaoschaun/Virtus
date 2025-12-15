import { useEffect, useState } from 'react'
import { settingsAPI, mt5API, systemAPI, authAPI } from '../services/api'
import { useAuthStore } from '../stores/authStore'
import { cn } from '../lib/utils'
import {
  Settings,
  Shield,
  Bell,
  Clock,
  RefreshCw,
  Save,
  Wifi,
  WifiOff,
  Database,
  Server,
  CheckCircle,
  XCircle,
  ToggleLeft,
  ToggleRight,
  User,
  Lock,
  Eye,
  EyeOff,
} from 'lucide-react'

interface RiskSettings {
  max_daily_loss_percent: number
  max_position_size: number
  max_open_positions: number
  use_trailing_stop: boolean
}

interface TradingSettings {
  auto_trade: boolean
  trading_hours: { start: string; end: string }
  news_filter: boolean
  spread_filter: boolean
}

interface NotificationSettings {
  telegram_enabled: boolean
  email_enabled: boolean
  trade_alerts: boolean
  daily_report: boolean
}

interface SystemStatus {
  api: string
  mt5: string
  database: string
  websocket: string
  uptime: string
  version: string
  server_time: string
}

export default function SettingsPage() {
  const [risk, setRisk] = useState<RiskSettings>({
    max_daily_loss_percent: 5.0,
    max_position_size: 1.0,
    max_open_positions: 5,
    use_trailing_stop: true,
  })
  const [trading, setTrading] = useState<TradingSettings>({
    auto_trade: true,
    trading_hours: { start: '08:00', end: '22:00' },
    news_filter: true,
    spread_filter: true,
  })
  const [notifications, setNotifications] = useState<NotificationSettings>({
    telegram_enabled: true,
    email_enabled: false,
    trade_alerts: true,
    daily_report: true,
  })
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [mt5Status, setMt5Status] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<'risk' | 'trading' | 'notifications' | 'system' | 'account'>('risk')
  
  // Password change state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')
  
  const { user } = useAuthStore()
  
  const loadSettings = async () => {
    setIsLoading(true)
    try {
      const [settingsRes, statusRes, mt5Res] = await Promise.all([
        settingsAPI.get(),
        systemAPI.getStatus(),
        mt5API.getStatus(),
      ])
      
      setRisk(settingsRes.data.risk)
      setTrading(settingsRes.data.trading)
      setNotifications(settingsRes.data.notifications)
      setSystemStatus(statusRes.data)
      setMt5Status(mt5Res.data)
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  useEffect(() => {
    loadSettings()
  }, [])
  
  const handleSave = async () => {
    setIsSaving(true)
    try {
      await settingsAPI.update({
        risk,
        trading,
        notifications,
      })
      alert('Configurações salvas com sucesso!')
    } catch (error) {
      console.error('Failed to save settings:', error)
      alert('Erro ao salvar configurações')
    } finally {
      setIsSaving(false)
    }
  }
  
  const handleMt5Sync = async () => {
    try {
      const result = await mt5API.sync(30)
      alert(`Sincronizado ${result.data.synced} registros`)
      loadSettings()
    } catch (error) {
      console.error('Failed to sync MT5:', error)
      alert('Erro ao sincronizar MT5')
    }
  }
  
  const handleChangePassword = async () => {
    setPasswordError('')
    setPasswordSuccess('')
    
    // Validações
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError('Preencha todos os campos')
      return
    }
    
    if (newPassword.length < 6) {
      setPasswordError('Nova senha deve ter no mínimo 6 caracteres')
      return
    }
    
    if (newPassword !== confirmPassword) {
      setPasswordError('Confirmação de senha não confere')
      return
    }
    
    setIsChangingPassword(true)
    try {
      await authAPI.changePassword(currentPassword, newPassword, confirmPassword)
      setPasswordSuccess('Senha alterada com sucesso!')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Erro ao alterar senha'
      setPasswordError(message)
    } finally {
      setIsChangingPassword(false)
    }
  }
  
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Configurações</h1>
          <p className="text-virtus-text-muted">Gerencie as configurações do sistema</p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary flex items-center gap-2"
        >
          {isSaving ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          <span>Salvar Alterações</span>
        </button>
      </div>
      
      {/* Tabs */}
      <div className="tabs">
        <button
          onClick={() => setActiveTab('risk')}
          className={activeTab === 'risk' ? 'tab-active' : 'tab'}
        >
          <Shield className="w-4 h-4 mr-2 inline" />
          Risco
        </button>
        <button
          onClick={() => setActiveTab('trading')}
          className={activeTab === 'trading' ? 'tab-active' : 'tab'}
        >
          <Clock className="w-4 h-4 mr-2 inline" />
          Trading
        </button>
        <button
          onClick={() => setActiveTab('notifications')}
          className={activeTab === 'notifications' ? 'tab-active' : 'tab'}
        >
          <Bell className="w-4 h-4 mr-2 inline" />
          Notificações
        </button>
        <button
          onClick={() => setActiveTab('system')}
          className={activeTab === 'system' ? 'tab-active' : 'tab'}
        >
          <Server className="w-4 h-4 mr-2 inline" />
          Sistema
        </button>
        <button
          onClick={() => setActiveTab('account')}
          className={activeTab === 'account' ? 'tab-active' : 'tab'}
        >
          <User className="w-4 h-4 mr-2 inline" />
          Conta
        </button>
      </div>
      
      {isLoading ? (
        <div className="card flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-virtus-accent-primary" />
        </div>
      ) : (
        <>
          {/* Risk Settings */}
          {activeTab === 'risk' && (
            <div className="card space-y-6">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Shield className="w-5 h-5 text-virtus-accent-primary" />
                Configurações de Risco
              </h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="label">Máximo Loss Diário (%)</label>
                  <input
                    type="number"
                    value={risk.max_daily_loss_percent}
                    onChange={(e) => setRisk({
                      ...risk,
                      max_daily_loss_percent: parseFloat(e.target.value)
                    })}
                    className="input"
                    min="1"
                    max="20"
                    step="0.5"
                  />
                  <p className="text-xs text-virtus-text-muted mt-1">
                    Limite de perda diária antes de parar o trading
                  </p>
                </div>
                
                <div>
                  <label className="label">Tamanho Máximo de Posição (lotes)</label>
                  <input
                    type="number"
                    value={risk.max_position_size}
                    onChange={(e) => setRisk({
                      ...risk,
                      max_position_size: parseFloat(e.target.value)
                    })}
                    className="input"
                    min="0.01"
                    max="10"
                    step="0.01"
                  />
                </div>
                
                <div>
                  <label className="label">Máximo de Posições Abertas</label>
                  <input
                    type="number"
                    value={risk.max_open_positions}
                    onChange={(e) => setRisk({
                      ...risk,
                      max_open_positions: parseInt(e.target.value)
                    })}
                    className="input"
                    min="1"
                    max="20"
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Trailing Stop</p>
                    <p className="text-sm text-virtus-text-muted">
                      Ativar trailing stop automático
                    </p>
                  </div>
                  <button
                    onClick={() => setRisk({
                      ...risk,
                      use_trailing_stop: !risk.use_trailing_stop
                    })}
                  >
                    {risk.use_trailing_stop ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Trading Settings */}
          {activeTab === 'trading' && (
            <div className="card space-y-6">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Clock className="w-5 h-5 text-virtus-accent-primary" />
                Configurações de Trading
              </h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Auto Trade</p>
                    <p className="text-sm text-virtus-text-muted">
                      Executar trades automaticamente
                    </p>
                  </div>
                  <button
                    onClick={() => setTrading({
                      ...trading,
                      auto_trade: !trading.auto_trade
                    })}
                  >
                    {trading.auto_trade ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Filtro de Notícias</p>
                    <p className="text-sm text-virtus-text-muted">
                      Evitar trading em eventos de alto impacto
                    </p>
                  </div>
                  <button
                    onClick={() => setTrading({
                      ...trading,
                      news_filter: !trading.news_filter
                    })}
                  >
                    {trading.news_filter ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Filtro de Spread</p>
                    <p className="text-sm text-virtus-text-muted">
                      Evitar trading quando spread está alto
                    </p>
                  </div>
                  <button
                    onClick={() => setTrading({
                      ...trading,
                      spread_filter: !trading.spread_filter
                    })}
                  >
                    {trading.spread_filter ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
                
                <div>
                  <label className="label">Horário de Trading</label>
                  <div className="flex gap-3">
                    <input
                      type="time"
                      value={trading.trading_hours.start}
                      onChange={(e) => setTrading({
                        ...trading,
                        trading_hours: { ...trading.trading_hours, start: e.target.value }
                      })}
                      className="input flex-1"
                    />
                    <span className="self-center text-virtus-text-muted">até</span>
                    <input
                      type="time"
                      value={trading.trading_hours.end}
                      onChange={(e) => setTrading({
                        ...trading,
                        trading_hours: { ...trading.trading_hours, end: e.target.value }
                      })}
                      className="input flex-1"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Notification Settings */}
          {activeTab === 'notifications' && (
            <div className="card space-y-6">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Bell className="w-5 h-5 text-virtus-accent-primary" />
                Configurações de Notificações
              </h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Telegram</p>
                    <p className="text-sm text-virtus-text-muted">
                      Receber notificações via Telegram
                    </p>
                  </div>
                  <button
                    onClick={() => setNotifications({
                      ...notifications,
                      telegram_enabled: !notifications.telegram_enabled
                    })}
                  >
                    {notifications.telegram_enabled ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Email</p>
                    <p className="text-sm text-virtus-text-muted">
                      Receber notificações via Email
                    </p>
                  </div>
                  <button
                    onClick={() => setNotifications({
                      ...notifications,
                      email_enabled: !notifications.email_enabled
                    })}
                  >
                    {notifications.email_enabled ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Alertas de Trade</p>
                    <p className="text-sm text-virtus-text-muted">
                      Notificar a cada operação executada
                    </p>
                  </div>
                  <button
                    onClick={() => setNotifications({
                      ...notifications,
                      trade_alerts: !notifications.trade_alerts
                    })}
                  >
                    {notifications.trade_alerts ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Relatório Diário</p>
                    <p className="text-sm text-virtus-text-muted">
                      Enviar resumo diário de performance
                    </p>
                  </div>
                  <button
                    onClick={() => setNotifications({
                      ...notifications,
                      daily_report: !notifications.daily_report
                    })}
                  >
                    {notifications.daily_report ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* System Settings */}
          {activeTab === 'system' && (
            <div className="space-y-6">
              {/* Status Cards */}
              <div className="grid md:grid-cols-4 gap-4">
                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <Server className="w-5 h-5 text-virtus-accent-primary" />
                    <div>
                      <p className="text-xs text-virtus-text-muted">API</p>
                      <p className="font-semibold text-virtus-accent-success">
                        {systemStatus?.api || 'N/A'}
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    {mt5Status?.connected ? (
                      <Wifi className="w-5 h-5 text-virtus-accent-success" />
                    ) : (
                      <WifiOff className="w-5 h-5 text-virtus-accent-danger" />
                    )}
                    <div>
                      <p className="text-xs text-virtus-text-muted">MT5</p>
                      <p className={cn(
                        'font-semibold',
                        mt5Status?.connected ? 'text-virtus-accent-success' : 'text-virtus-accent-danger'
                      )}>
                        {mt5Status?.connected ? 'Conectado' : 'Desconectado'}
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <Database className="w-5 h-5 text-virtus-accent-primary" />
                    <div>
                      <p className="text-xs text-virtus-text-muted">Database</p>
                      <p className="font-semibold text-virtus-accent-success">
                        {systemStatus?.database || 'N/A'}
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <Clock className="w-5 h-5 text-virtus-accent-primary" />
                    <div>
                      <p className="text-xs text-virtus-text-muted">Uptime</p>
                      <p className="font-semibold">{systemStatus?.uptime || 'N/A'}</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* MT5 Details */}
              {mt5Status?.connected && mt5Status?.account && (
                <div className="card">
                  <h3 className="text-lg font-semibold mb-4">Conta MT5</h3>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="p-4 bg-virtus-bg-tertiary rounded-lg">
                      <p className="text-xs text-virtus-text-muted">Login</p>
                      <p className="font-semibold">{mt5Status.account.login}</p>
                    </div>
                    <div className="p-4 bg-virtus-bg-tertiary rounded-lg">
                      <p className="text-xs text-virtus-text-muted">Server</p>
                      <p className="font-semibold">{mt5Status.account.server}</p>
                    </div>
                    <div className="p-4 bg-virtus-bg-tertiary rounded-lg">
                      <p className="text-xs text-virtus-text-muted">Saldo</p>
                      <p className="font-semibold">
                        ${mt5Status.account.balance?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                  </div>
                  
                  <div className="mt-4">
                    <button onClick={handleMt5Sync} className="btn-secondary flex items-center gap-2">
                      <RefreshCw className="w-4 h-4" />
                      <span>Sincronizar Histórico MT5</span>
                    </button>
                  </div>
                </div>
              )}
              
              {/* Version Info */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Informações do Sistema</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-virtus-text-muted">Versão</span>
                    <span className="font-mono">{systemStatus?.version || '1.0.0'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-virtus-text-muted">Hora do Servidor</span>
                    <span className="font-mono">
                      {systemStatus?.server_time 
                        ? new Date(systemStatus.server_time).toLocaleString('pt-BR')
                        : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-virtus-text-muted">WebSocket Connections</span>
                    <span>{systemStatus?.websocket || 'N/A'}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Account Settings */}
          {activeTab === 'account' && (
            <div className="space-y-6">
              {/* User Info */}
              <div className="card">
                <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                  <User className="w-5 h-5 text-virtus-accent-primary" />
                  Informações da Conta
                </h3>
                
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="p-4 bg-virtus-bg-tertiary rounded-lg">
                    <p className="text-xs text-virtus-text-muted">Usuário</p>
                    <p className="font-semibold">{user?.username || 'N/A'}</p>
                  </div>
                  <div className="p-4 bg-virtus-bg-tertiary rounded-lg">
                    <p className="text-xs text-virtus-text-muted">Nome</p>
                    <p className="font-semibold">{user?.name || 'N/A'}</p>
                  </div>
                  <div className="p-4 bg-virtus-bg-tertiary rounded-lg">
                    <p className="text-xs text-virtus-text-muted">Perfil</p>
                    <p className="font-semibold capitalize">{user?.role || 'N/A'}</p>
                  </div>
                </div>
              </div>
              
              {/* Change Password */}
              <div className="card">
                <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
                  <Lock className="w-5 h-5 text-virtus-accent-primary" />
                  Alterar Senha
                </h3>
                
                <div className="space-y-4 max-w-md">
                  {/* Current Password */}
                  <div>
                    <label className="label">Senha Atual</label>
                    <div className="relative">
                      <input
                        type={showCurrentPassword ? 'text' : 'password'}
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        className="input pr-12"
                        placeholder="Digite sua senha atual"
                      />
                      <button
                        type="button"
                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-virtus-text-muted hover:text-virtus-text-primary transition-colors"
                      >
                        {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                      </button>
                    </div>
                  </div>
                  
                  {/* New Password */}
                  <div>
                    <label className="label">Nova Senha</label>
                    <div className="relative">
                      <input
                        type={showNewPassword ? 'text' : 'password'}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="input pr-12"
                        placeholder="Digite a nova senha (mín. 6 caracteres)"
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-virtus-text-muted hover:text-virtus-text-primary transition-colors"
                      >
                        {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                      </button>
                    </div>
                  </div>
                  
                  {/* Confirm Password */}
                  <div>
                    <label className="label">Confirmar Nova Senha</label>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="input"
                      placeholder="Confirme a nova senha"
                    />
                  </div>
                  
                  {/* Error Message */}
                  {passwordError && (
                    <div className="p-3 bg-virtus-accent-danger/10 border border-virtus-accent-danger/30 rounded-lg">
                      <p className="text-sm text-virtus-accent-danger">{passwordError}</p>
                    </div>
                  )}
                  
                  {/* Success Message */}
                  {passwordSuccess && (
                    <div className="p-3 bg-virtus-accent-success/10 border border-virtus-accent-success/30 rounded-lg">
                      <p className="text-sm text-virtus-accent-success">{passwordSuccess}</p>
                    </div>
                  )}
                  
                  {/* Submit Button */}
                  <button
                    onClick={handleChangePassword}
                    disabled={isChangingPassword || !currentPassword || !newPassword || !confirmPassword}
                    className="btn-primary flex items-center gap-2"
                  >
                    {isChangingPassword ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Lock className="w-4 h-4" />
                    )}
                    <span>{isChangingPassword ? 'Alterando...' : 'Alterar Senha'}</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
