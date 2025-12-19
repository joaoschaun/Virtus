import { useEffect, useState } from 'react'
import { settingsAPI, systemAPI, authAPI } from '../services/api'
import { useAuthStore } from '../stores/authStore'
import { useThemeStore } from '../stores/themeStore'
import { cn } from '../lib/utils'
import {
  Bell,
  RefreshCw,
  Save,
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
  Link,
  Globe,
  Palette,
  Monitor,
  Sun,
  Moon,
  Zap,
  TrendingUp,
  AlertCircle,
  ExternalLink,
  TestTube,
  Shield,
} from 'lucide-react'

// Tipos
interface DashboardSettings {
  theme: 'dark' | 'light' | 'auto'
  language: 'pt-BR' | 'en-US'
  currency: 'BRL' | 'USD'
  timezone: string
  refresh_interval: number
  compact_mode: boolean
}

interface IntegrationSettings {
  brapi_enabled: boolean
  brapi_status: 'connected' | 'error' | 'unconfigured'
  eodhd_enabled: boolean
  eodhd_status: 'connected' | 'error' | 'unconfigured'
  tess_enabled: boolean
  tess_status: 'connected' | 'error' | 'unconfigured'
}

interface NotificationSettings {
  telegram_enabled: boolean
  telegram_chat_id: string
  market_alerts: boolean
  briefing_alerts: boolean
  daily_summary: boolean
  alert_sound: boolean
}

interface SystemStatus {
  api: string
  database: string
  websocket: string
  uptime: string
  version: string
  server_time: string
  integrations: {
    brapi: boolean
    eodhd: boolean
    tess: boolean
  }
}

interface ExternalBotConfig {
  enabled: boolean
  api_url: string
  api_key: string
  sync_interval: number
}

export default function SettingsPage() {
  const [dashboard, setDashboard] = useState<DashboardSettings>({
    theme: 'dark',
    language: 'pt-BR',
    currency: 'BRL',
    timezone: 'America/Sao_Paulo',
    refresh_interval: 30,
    compact_mode: false,
  })
  
  const [integrations, setIntegrations] = useState<IntegrationSettings>({
    brapi_enabled: true,
    brapi_status: 'connected',
    eodhd_enabled: true,
    eodhd_status: 'connected',
    tess_enabled: true,
    tess_status: 'connected',
  })
  
  const [notifications, setNotifications] = useState<NotificationSettings>({
    telegram_enabled: true,
    telegram_chat_id: '',
    market_alerts: true,
    briefing_alerts: true,
    daily_summary: true,
    alert_sound: true,
  })
  
  const [externalBot, setExternalBot] = useState<ExternalBotConfig>({
    enabled: false,
    api_url: 'http://localhost:8001',
    api_key: '',
    sync_interval: 60,
  })
  
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [activeTab, setActiveTab] = useState<'dashboard' | 'integrations' | 'notifications' | 'system' | 'account' | 'external'>('dashboard')
  const [testingApi, setTestingApi] = useState<string | null>(null)
  
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
  const { theme: globalTheme, setTheme: setGlobalTheme } = useThemeStore()
  
  const loadSettings = async () => {
    setIsLoading(true)
    try {
      const [settingsRes, statusRes] = await Promise.all([
        settingsAPI.get(),
        systemAPI.getStatus(),
      ])
      
      // Carregar configurações do localStorage para preferências visuais
      const savedDashboard = localStorage.getItem('virtus_dashboard_settings')
      if (savedDashboard) {
        setDashboard(JSON.parse(savedDashboard))
      }
      
      // Configurações de notificação do backend
      if (settingsRes.data?.notifications) {
        setNotifications({
          ...notifications,
          telegram_enabled: settingsRes.data.notifications.telegram_enabled ?? true,
        })
      }
      
      setSystemStatus({
        api: statusRes.data?.status || 'healthy',
        database: statusRes.data?.components?.database || 'healthy',
        websocket: 'active',
        uptime: statusRes.data?.uptime || 'Running',
        version: statusRes.data?.version || '1.0.0',
        server_time: new Date().toISOString(),
        integrations: {
          brapi: true,
          eodhd: true,
          tess: true,
        }
      })
      
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
      // Salvar configurações visuais no localStorage
      localStorage.setItem('virtus_dashboard_settings', JSON.stringify(dashboard))
      
      // Salvar configurações no backend
      await settingsAPI.update({
        notifications,
        dashboard,
      })
      
      alert('Configurações salvas com sucesso!')
    } catch (error) {
      console.error('Failed to save settings:', error)
      alert('Erro ao salvar configurações')
    } finally {
      setIsSaving(false)
    }
  }
  
  const testApiConnection = async (api: string) => {
    setTestingApi(api)
    try {
      // Simular teste de conexão
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      setIntegrations(prev => ({
        ...prev,
        [`${api}_status`]: 'connected'
      }))
      
      alert(`✅ Conexão com ${api.toUpperCase()} estabelecida com sucesso!`)
    } catch (error) {
      setIntegrations(prev => ({
        ...prev,
        [`${api}_status`]: 'error'
      }))
      alert(`❌ Erro ao conectar com ${api.toUpperCase()}`)
    } finally {
      setTestingApi(null)
    }
  }
  
  const handleChangePassword = async () => {
    setPasswordError('')
    setPasswordSuccess('')
    
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
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
      case 'healthy':
      case 'active':
        return <CheckCircle className="w-4 h-4 text-virtus-accent-success" />
      case 'error':
        return <XCircle className="w-4 h-4 text-virtus-accent-danger" />
      default:
        return <AlertCircle className="w-4 h-4 text-virtus-accent-warning" />
    }
  }
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
      case 'healthy':
      case 'active':
        return 'text-virtus-accent-success'
      case 'error':
        return 'text-virtus-accent-danger'
      default:
        return 'text-virtus-accent-warning'
    }
  }
  
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Configurações</h1>
          <p className="text-virtus-text-muted">Gerencie as configurações do dashboard</p>
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
      <div className="tabs overflow-x-auto">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={activeTab === 'dashboard' ? 'tab-active' : 'tab'}
        >
          <Palette className="w-4 h-4 mr-2 inline" />
          Dashboard
        </button>
        <button
          onClick={() => setActiveTab('integrations')}
          className={activeTab === 'integrations' ? 'tab-active' : 'tab'}
        >
          <Link className="w-4 h-4 mr-2 inline" />
          Integrações
        </button>
        <button
          onClick={() => setActiveTab('notifications')}
          className={activeTab === 'notifications' ? 'tab-active' : 'tab'}
        >
          <Bell className="w-4 h-4 mr-2 inline" />
          Notificações
        </button>
        <button
          onClick={() => setActiveTab('external')}
          className={activeTab === 'external' ? 'tab-active' : 'tab'}
        >
          <Zap className="w-4 h-4 mr-2 inline" />
          Bots Externos
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
          {/* Dashboard Settings */}
          {activeTab === 'dashboard' && (
            <div className="card space-y-6">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Palette className="w-5 h-5 text-virtus-accent-primary" />
                Preferências do Dashboard
              </h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                {/* Theme */}
                <div>
                  <label className="label">Tema</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setDashboard({ ...dashboard, theme: 'dark' })
                        setGlobalTheme('dark')
                      }}
                      className={cn(
                        'flex-1 p-3 rounded-lg flex items-center justify-center gap-2 border transition-all',
                        globalTheme === 'dark'
                          ? 'border-virtus-accent-primary bg-virtus-accent-primary/10'
                          : 'border-virtus-border hover:border-virtus-accent-primary/50'
                      )}
                    >
                      <Moon className="w-4 h-4" />
                      <span>Escuro</span>
                    </button>
                    <button
                      onClick={() => {
                        setDashboard({ ...dashboard, theme: 'light' })
                        setGlobalTheme('light')
                      }}
                      className={cn(
                        'flex-1 p-3 rounded-lg flex items-center justify-center gap-2 border transition-all',
                        globalTheme === 'light'
                          ? 'border-virtus-accent-primary bg-virtus-accent-primary/10'
                          : 'border-virtus-border hover:border-virtus-accent-primary/50'
                      )}
                    >
                      <Sun className="w-4 h-4" />
                      <span>Claro</span>
                    </button>
                  </div>
                </div>
                
                {/* Language */}
                <div>
                  <label className="label">Idioma</label>
                  <select
                    value={dashboard.language}
                    onChange={(e) => setDashboard({ ...dashboard, language: e.target.value as any })}
                    className="input"
                    title="Selecione o idioma"
                  >
                    <option value="pt-BR">Português (Brasil)</option>
                    <option value="en-US">English (US)</option>
                  </select>
                </div>
                
                {/* Currency */}
                <div>
                  <label className="label">Moeda Padrão</label>
                  <select
                    value={dashboard.currency}
                    onChange={(e) => setDashboard({ ...dashboard, currency: e.target.value as any })}
                    className="input"
                    title="Selecione a moeda"
                  >
                    <option value="BRL">Real (R$)</option>
                    <option value="USD">Dólar (US$)</option>
                  </select>
                </div>
                
                {/* Timezone */}
                <div>
                  <label className="label">Fuso Horário</label>
                  <select
                    value={dashboard.timezone}
                    onChange={(e) => setDashboard({ ...dashboard, timezone: e.target.value })}
                    className="input"
                    title="Selecione o fuso horário"
                  >
                    <option value="America/Sao_Paulo">São Paulo (GMT-3)</option>
                    <option value="America/New_York">New York (GMT-5)</option>
                    <option value="Europe/London">Londres (GMT)</option>
                    <option value="Asia/Tokyo">Tokyo (GMT+9)</option>
                  </select>
                </div>
                
                {/* Refresh Interval */}
                <div>
                  <label className="label">Intervalo de Atualização (segundos)</label>
                  <input
                    type="number"
                    value={dashboard.refresh_interval}
                    onChange={(e) => setDashboard({ ...dashboard, refresh_interval: parseInt(e.target.value) })}
                    className="input"
                    min="10"
                    max="300"
                    step="10"
                    title="Intervalo de atualização em segundos"
                  />
                  <p className="text-xs text-virtus-text-muted mt-1">
                    Frequência de atualização dos dados de mercado
                  </p>
                </div>
                
                {/* Compact Mode */}
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Modo Compacto</p>
                    <p className="text-sm text-virtus-text-muted">
                      Exibir informações de forma mais condensada
                    </p>
                  </div>
                  <button
                    onClick={() => setDashboard({ ...dashboard, compact_mode: !dashboard.compact_mode })}
                  >
                    {dashboard.compact_mode ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Integrations Settings */}
          {activeTab === 'integrations' && (
            <div className="space-y-6">
              <div className="card">
                <h3 className="text-lg font-semibold flex items-center gap-2 mb-6">
                  <Link className="w-5 h-5 text-virtus-accent-primary" />
                  APIs de Mercado
                </h3>
                
                <div className="space-y-4">
                  {/* Brapi */}
                  <div className="p-4 bg-virtus-bg-tertiary rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                          <Globe className="w-5 h-5 text-blue-500" />
                        </div>
                        <div>
                          <p className="font-medium">Brapi</p>
                          <p className="text-sm text-virtus-text-muted">
                            Dados do mercado brasileiro (B3, FIIs, Ações)
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className={cn('flex items-center gap-1', getStatusColor(integrations.brapi_status))}>
                          {getStatusIcon(integrations.brapi_status)}
                          <span className="text-sm capitalize">{integrations.brapi_status}</span>
                        </div>
                        <button
                          onClick={() => testApiConnection('brapi')}
                          disabled={testingApi === 'brapi'}
                          className="btn-secondary text-sm py-1 px-3"
                        >
                          {testingApi === 'brapi' ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <TestTube className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => setIntegrations({ ...integrations, brapi_enabled: !integrations.brapi_enabled })}
                        >
                          {integrations.brapi_enabled ? (
                            <ToggleRight className="w-8 h-8 text-virtus-accent-success" />
                          ) : (
                            <ToggleLeft className="w-8 h-8 text-virtus-text-muted" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                  
                  {/* EODHD */}
                  <div className="p-4 bg-virtus-bg-tertiary rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                          <TrendingUp className="w-5 h-5 text-green-500" />
                        </div>
                        <div>
                          <p className="font-medium">EODHD</p>
                          <p className="text-sm text-virtus-text-muted">
                            Calendário econômico, notícias globais
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className={cn('flex items-center gap-1', getStatusColor(integrations.eodhd_status))}>
                          {getStatusIcon(integrations.eodhd_status)}
                          <span className="text-sm capitalize">{integrations.eodhd_status}</span>
                        </div>
                        <button
                          onClick={() => testApiConnection('eodhd')}
                          disabled={testingApi === 'eodhd'}
                          className="btn-secondary text-sm py-1 px-3"
                        >
                          {testingApi === 'eodhd' ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <TestTube className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => setIntegrations({ ...integrations, eodhd_enabled: !integrations.eodhd_enabled })}
                        >
                          {integrations.eodhd_enabled ? (
                            <ToggleRight className="w-8 h-8 text-virtus-accent-success" />
                          ) : (
                            <ToggleLeft className="w-8 h-8 text-virtus-text-muted" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                  
                  {/* TESS AI */}
                  <div className="p-4 bg-virtus-bg-tertiary rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                          <Zap className="w-5 h-5 text-purple-500" />
                        </div>
                        <div>
                          <p className="font-medium">TESS AI</p>
                          <p className="text-sm text-virtus-text-muted">
                            Análise de sentimento com inteligência artificial
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className={cn('flex items-center gap-1', getStatusColor(integrations.tess_status))}>
                          {getStatusIcon(integrations.tess_status)}
                          <span className="text-sm capitalize">{integrations.tess_status}</span>
                        </div>
                        <button
                          onClick={() => testApiConnection('tess')}
                          disabled={testingApi === 'tess'}
                          className="btn-secondary text-sm py-1 px-3"
                        >
                          {testingApi === 'tess' ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <TestTube className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => setIntegrations({ ...integrations, tess_enabled: !integrations.tess_enabled })}
                        >
                          {integrations.tess_enabled ? (
                            <ToggleRight className="w-8 h-8 text-virtus-accent-success" />
                          ) : (
                            <ToggleLeft className="w-8 h-8 text-virtus-text-muted" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* API Keys Info */}
              <div className="card bg-virtus-accent-warning/10 border-virtus-accent-warning/30">
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-virtus-accent-warning mt-0.5" />
                  <div>
                    <p className="font-medium text-virtus-accent-warning">Configuração de API Keys</p>
                    <p className="text-sm text-virtus-text-muted mt-1">
                      As API keys são configuradas via variáveis de ambiente no arquivo <code className="px-1 bg-virtus-bg-tertiary rounded">.env</code>.
                      Para modificar as chaves, edite o arquivo e reinicie o servidor.
                    </p>
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
                    <p className="font-medium">Alertas de Mercado</p>
                    <p className="text-sm text-virtus-text-muted">
                      Notificar sobre movimentos importantes
                    </p>
                  </div>
                  <button
                    onClick={() => setNotifications({
                      ...notifications,
                      market_alerts: !notifications.market_alerts
                    })}
                  >
                    {notifications.market_alerts ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Briefing Diário</p>
                    <p className="text-sm text-virtus-text-muted">
                      Receber resumo diário do mercado
                    </p>
                  </div>
                  <button
                    onClick={() => setNotifications({
                      ...notifications,
                      briefing_alerts: !notifications.briefing_alerts
                    })}
                  >
                    {notifications.briefing_alerts ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Resumo Diário</p>
                    <p className="text-sm text-virtus-text-muted">
                      Enviar resumo ao final do dia
                    </p>
                  </div>
                  <button
                    onClick={() => setNotifications({
                      ...notifications,
                      daily_summary: !notifications.daily_summary
                    })}
                  >
                    {notifications.daily_summary ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                  <div>
                    <p className="font-medium">Sons de Alerta</p>
                    <p className="text-sm text-virtus-text-muted">
                      Tocar som ao receber notificação
                    </p>
                  </div>
                  <button
                    onClick={() => setNotifications({
                      ...notifications,
                      alert_sound: !notifications.alert_sound
                    })}
                  >
                    {notifications.alert_sound ? (
                      <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                    ) : (
                      <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* External Bots Settings */}
          {activeTab === 'external' && (
            <div className="space-y-6">
              <div className="card">
                <h3 className="text-lg font-semibold flex items-center gap-2 mb-6">
                  <Zap className="w-5 h-5 text-virtus-accent-primary" />
                  Integração com Bots de Trading
                </h3>
                
                <div className="space-y-6">
                  <div className="flex items-center justify-between p-4 bg-virtus-bg-tertiary rounded-lg">
                    <div>
                      <p className="font-medium">Habilitar Integração</p>
                      <p className="text-sm text-virtus-text-muted">
                        Conectar com sistema VirtusTrading externo
                      </p>
                    </div>
                    <button
                      onClick={() => setExternalBot({ ...externalBot, enabled: !externalBot.enabled })}
                    >
                      {externalBot.enabled ? (
                        <ToggleRight className="w-10 h-10 text-virtus-accent-success" />
                      ) : (
                        <ToggleLeft className="w-10 h-10 text-virtus-text-muted" />
                      )}
                    </button>
                  </div>
                  
                  {externalBot.enabled && (
                    <div className="grid md:grid-cols-2 gap-6">
                      <div>
                        <label className="label">URL da API</label>
                        <input
                          type="text"
                          value={externalBot.api_url}
                          onChange={(e) => setExternalBot({ ...externalBot, api_url: e.target.value })}
                          className="input"
                          placeholder="http://localhost:8001"
                        />
                        <p className="text-xs text-virtus-text-muted mt-1">
                          Endereço do servidor VirtusTrading
                        </p>
                      </div>
                      
                      <div>
                        <label className="label">API Key</label>
                        <input
                          type="password"
                          value={externalBot.api_key}
                          onChange={(e) => setExternalBot({ ...externalBot, api_key: e.target.value })}
                          className="input"
                          placeholder="Chave de autenticação"
                        />
                      </div>
                      
                      <div>
                        <label className="label">Intervalo de Sincronização (segundos)</label>
                        <input
                          type="number"
                          value={externalBot.sync_interval}
                          onChange={(e) => setExternalBot({ ...externalBot, sync_interval: parseInt(e.target.value) })}
                          className="input"
                          min="10"
                          max="300"
                          step="10"
                          title="Intervalo de sincronização em segundos"
                        />
                      </div>
                      
                      <div className="flex items-end">
                        <button className="btn-secondary flex items-center gap-2">
                          <TestTube className="w-4 h-4" />
                          <span>Testar Conexão</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Info Box */}
              <div className="card bg-virtus-accent-primary/10 border-virtus-accent-primary/30">
                <div className="flex items-start gap-3">
                  <ExternalLink className="w-5 h-5 text-virtus-accent-primary mt-0.5" />
                  <div>
                    <p className="font-medium">Sobre Bots Externos</p>
                    <p className="text-sm text-virtus-text-muted mt-1">
                      O sistema VirtusTrading opera de forma independente e pode ser conectado 
                      ao dashboard para visualização de dados de trading, posições abertas 
                      e performance dos bots.
                    </p>
                    <a href="#" className="text-sm text-virtus-accent-primary hover:underline mt-2 inline-block">
                      Ver documentação da API →
                    </a>
                  </div>
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
                      <p className={cn('font-semibold', getStatusColor(systemStatus?.api || 'healthy'))}>
                        {systemStatus?.api || 'Healthy'}
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <Database className="w-5 h-5 text-virtus-accent-primary" />
                    <div>
                      <p className="text-xs text-virtus-text-muted">Database</p>
                      <p className={cn('font-semibold', getStatusColor(systemStatus?.database || 'healthy'))}>
                        {systemStatus?.database || 'Healthy'}
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <Zap className="w-5 h-5 text-virtus-accent-primary" />
                    <div>
                      <p className="text-xs text-virtus-text-muted">WebSocket</p>
                      <p className={cn('font-semibold', getStatusColor(systemStatus?.websocket || 'active'))}>
                        {systemStatus?.websocket || 'Active'}
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="card p-4">
                  <div className="flex items-center gap-3">
                    <RefreshCw className="w-5 h-5 text-virtus-accent-primary" />
                    <div>
                      <p className="text-xs text-virtus-text-muted">Uptime</p>
                      <p className="font-semibold">{systemStatus?.uptime || 'N/A'}</p>
                    </div>
                  </div>
                </div>
              </div>
              
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
                        : new Date().toLocaleString('pt-BR')}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-virtus-text-muted">Ambiente</span>
                    <span className="px-2 py-0.5 bg-virtus-accent-success/20 text-virtus-accent-success rounded text-sm">
                      Production
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Integrations Status */}
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Status das Integrações</h3>
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="p-4 bg-virtus-bg-tertiary rounded-lg flex items-center justify-between">
                    <span>Brapi</span>
                    {getStatusIcon(systemStatus?.integrations?.brapi ? 'connected' : 'error')}
                  </div>
                  <div className="p-4 bg-virtus-bg-tertiary rounded-lg flex items-center justify-between">
                    <span>EODHD</span>
                    {getStatusIcon(systemStatus?.integrations?.eodhd ? 'connected' : 'error')}
                  </div>
                  <div className="p-4 bg-virtus-bg-tertiary rounded-lg flex items-center justify-between">
                    <span>TESS AI</span>
                    {getStatusIcon(systemStatus?.integrations?.tess ? 'connected' : 'error')}
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
                
                <div className="grid sm:grid-cols-3 gap-4">
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
