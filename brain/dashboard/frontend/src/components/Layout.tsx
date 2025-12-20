import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useTradingStore } from '../stores/tradingStore'
import { useThemeStore } from '../stores/themeStore'
import { useWebSocket } from '../services/websocket'
import NotificationDropdown from './NotificationDropdown'
import DailyBriefingModal from './DailyBriefingModal'
import CommandPalette from './CommandPalette'
import ThemeToggle from './ThemeToggle'
import KeyboardShortcutsHelp from './KeyboardShortcutsHelp'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { OnlineStatus, UpdatePrompt, InstallButton } from '../hooks/usePWA'
import { 
  LayoutDashboard, 
  LineChart, 
  ListOrdered,
  Bot,
  Zap,
  BarChart3,
  Settings,
  LogOut,
  Wifi,
  WifiOff,
  User,
  ChevronDown,
  ChevronRight,
  Menu,
  X,
  Instagram,
  TrendingUp,
  DollarSign,
  Newspaper,
  Wallet,
  Play,
  Activity,
  Building2,
  Bitcoin,
  Landmark,
  ArrowLeftRight,
  Percent,
  Globe,
  Target,
  Briefcase,
  Search,
  Command,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { cn } from '../lib/utils'

// Navegação agrupada
const navigationGroups = [
  {
    name: 'Principal',
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'Forex Briefing', href: '/forex', icon: TrendingUp },
    ]
  },
  {
    name: 'Mercado B3',
    items: [
      { name: 'Visão Geral', href: '/market-overview', icon: Globe },
      { name: 'Screener', href: '/screener', icon: Target },
      { name: 'Ações', href: '/stocks', icon: Building2 },
      { name: 'FIIs', href: '/fiis', icon: Landmark },
      { name: 'Criptomoedas', href: '/crypto', icon: Bitcoin },
      { name: 'Câmbio', href: '/currency', icon: ArrowLeftRight },
      { name: 'Indicadores', href: '/indicators', icon: Percent },
    ]
  },
  {
    name: 'Patrimônio',
    items: [
      { name: 'Desenvolvimento', href: '/patrimonio', icon: TrendingUp },
      { name: 'Carteira', href: '/carteira', icon: Briefcase },
    ]
  },
  {
    name: 'Dividendos',
    items: [
      { name: 'Dividendos B3', href: '/dividends', icon: DollarSign },
      { name: 'Carteira Dividendos', href: '/carteira-dividendos', icon: Wallet },
    ]
  },
  {
    name: 'Portfólios',
    items: [
      { name: 'Carteira FIIs', href: '/fii-portfolio', icon: Briefcase },
      { name: 'Paper Trading', href: '/paper-trading', icon: Play },
    ]
  },
  {
    name: 'Trading',
    items: [
      { name: 'Posições', href: '/positions', icon: ListOrdered },
      { name: 'Histórico', href: '/trades', icon: LineChart },
      { name: 'MT4 Conta Real', href: '/mt4-account', icon: Wallet },
      { name: 'Bots', href: '/bots', icon: Bot },
      { name: 'Estratégias', href: '/strategies', icon: Zap },
      { name: 'Análise', href: '/analysis', icon: BarChart3 },
    ]
  },
  {
    name: 'Outros',
    items: [
      { name: 'Monitoramento', href: '/monitoring', icon: Activity },
      { name: 'Social Media', href: '/social', icon: Instagram },
      { name: 'Configurações', href: '/settings', icon: Settings },
    ]
  },
]

// Flat navigation for mobile
const flatNavigation = navigationGroups.flatMap(g => g.items)

export default function Layout() {
  const { user, logout } = useAuthStore()
  const { isConnected, metrics } = useTradingStore()
  const { theme } = useThemeStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const [showBriefing, setShowBriefing] = useState(false)
  const [showCommandPalette, setShowCommandPalette] = useState(false)
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false)
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({})
  
  // Initialize WebSocket
  useWebSocket()
  
  // Initialize keyboard shortcuts
  useKeyboardShortcuts({
    onOpenCommandPalette: () => setShowCommandPalette(true),
    onOpenShortcutsHelp: () => setShowShortcutsHelp(true)
  })
  
  // Close mobile menu on route change
  useEffect(() => {
    setShowMobileMenu(false)
  }, [location.pathname])
  
  // Mostra briefing ao entrar no dashboard (primeira vez do dia)
  useEffect(() => {
    const today = new Date().toDateString()
    const lastBriefingDate = localStorage.getItem('lastBriefingDate')
    
    // Mostra briefing se é um novo dia ou primeira visita
    if (lastBriefingDate !== today && location.pathname === '/dashboard') {
      // Pequeno delay para dar tempo da página carregar
      const timer = setTimeout(() => {
        setShowBriefing(true)
        localStorage.setItem('lastBriefingDate', today)
      }, 1000)
      
      return () => clearTimeout(timer)
    }
  }, [location.pathname])
  
  const handleLogout = () => {
    logout()
    navigate('/login')
  }
  
  const toggleGroup = (groupName: string) => {
    setCollapsedGroups(prev => ({
      ...prev,
      [groupName]: !prev[groupName]
    }))
  }
  
  // Check if any item in group is active
  const isGroupActive = (items: typeof flatNavigation) => {
    return items.some(item => location.pathname === item.href)
  }
  
  return (
    <div className="min-h-screen bg-virtus-bg-primary">
      {/* Mobile Menu Overlay */}
      {showMobileMenu && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setShowMobileMenu(false)}
        />
      )}
      
      {/* Sidebar - Desktop */}
      <aside className={`sidebar ${showMobileMenu ? 'sidebar-mobile-open' : ''}`}>
        {/* Logo */}
        <div className="p-4 lg:p-6 border-b border-virtus-border-primary">
          <div className="flex items-center justify-between">
            <div className="flex items-center justify-center w-full">
              <img 
                src="/virtus-primaria.png" 
                alt="Virtus Investimentos" 
                className="h-12 lg:h-14 w-auto max-w-[180px] object-contain"
              />
            </div>
            {/* Close button for mobile */}
            <button 
              onClick={() => setShowMobileMenu(false)}
              className="lg:hidden p-2 rounded-lg hover:bg-virtus-bg-hover transition-colors absolute right-4"
            >
              <X className="w-5 h-5 text-virtus-text-secondary" />
            </button>
          </div>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          {navigationGroups.map((group) => (
            <div key={group.name} className="mb-2">
              {/* Group Header */}
              <button
                onClick={() => toggleGroup(group.name)}
                className="w-full flex items-center justify-between px-4 py-2 text-xs font-semibold text-virtus-text-muted uppercase tracking-wider hover:text-virtus-text-secondary transition-colors"
              >
                <span>{group.name}</span>
                <ChevronRight 
                  className={cn(
                    'w-4 h-4 transition-transform',
                    !collapsedGroups[group.name] && 'rotate-90'
                  )} 
                />
              </button>
              
              {/* Group Items */}
              {!collapsedGroups[group.name] && (
                <ul className="space-y-0.5 mt-1">
                  {group.items.map((item) => (
                    <li key={item.name}>
                      <NavLink
                        to={item.href}
                        className={({ isActive }) =>
                          isActive ? 'sidebar-link-active' : 'sidebar-link'
                        }
                      >
                        <item.icon className="w-5 h-5" />
                        <span>{item.name}</span>
                      </NavLink>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </nav>
        
        {/* Connection Status */}
        <div className="p-4 border-t border-virtus-border-primary">
          <div className="flex items-center gap-2 text-sm">
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4 text-virtus-accent-success" />
                <span className="text-virtus-accent-success">Conectado</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-virtus-accent-danger" />
                <span className="text-virtus-accent-danger">Desconectado</span>
              </>
            )}
          </div>
        </div>
      </aside>
      
      {/* Header */}
      <header className="header">
        {/* Mobile Menu Button */}
        <button
          onClick={() => setShowMobileMenu(true)}
          className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-virtus-bg-hover transition-colors"
        >
          <Menu className="w-6 h-6 text-virtus-text-secondary" />
        </button>
        
        {/* Account Info */}
        <div className="flex items-center gap-2 sm:gap-6">
          <div className="flex items-center gap-2 sm:gap-4">
            <div>
              <p className="text-[10px] sm:text-xs text-virtus-text-muted">Patrimônio</p>
              <p className="text-sm sm:text-lg font-bold">
                ${metrics?.equity?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || '0.00'}
              </p>
            </div>
            <div className="hidden sm:block w-px h-8 bg-virtus-border-primary" />
            <div className="hidden sm:block">
              <p className="text-xs text-virtus-text-muted">Lucro Diário</p>
              <p className={`text-lg font-bold ${(metrics?.dailyPnl || 0) >= 0 ? 'profit' : 'loss'}`}>
                {(metrics?.dailyPnl || 0) >= 0 ? '+' : ''}${metrics?.dailyPnl?.toFixed(2) || '0.00'}
              </p>
            </div>
          </div>
        </div>
        
        {/* Right Side */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Search Button */}
          <button
            onClick={() => setShowCommandPalette(true)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-virtus-bg-tertiary border border-virtus-border-primary hover:border-virtus-text-muted transition-all group"
            title="Busca Rápida (Ctrl+K)"
          >
            <Search className="w-4 h-4 text-virtus-text-muted group-hover:text-virtus-text-primary transition-colors" />
            <span className="hidden md:inline text-sm text-virtus-text-muted">Buscar...</span>
            <kbd className="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-virtus-bg-secondary text-[10px] text-virtus-text-muted">
              <Command className="w-3 h-3" />K
            </kbd>
          </button>
          
          {/* Theme Toggle */}
          <ThemeToggle />
          
          {/* Briefing Button */}
          <button
            onClick={() => setShowBriefing(true)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gradient-to-r from-virtus-accent-primary/20 to-green-500/20 border border-virtus-accent-primary/30 hover:border-virtus-accent-primary/50 transition-all group"
            title="Briefing Diário"
          >
            <Newspaper className="w-4 h-4 text-virtus-accent-primary group-hover:scale-110 transition-transform" />
            <span className="hidden sm:inline text-sm font-medium text-virtus-accent-primary">Briefing</span>
          </button>
          
          {/* Notifications */}
          <NotificationDropdown />
          
          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 sm:gap-3 px-2 sm:px-3 py-2 rounded-lg hover:bg-virtus-bg-hover transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-virtus flex items-center justify-center">
                <User className="w-4 h-4 text-white" />
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-sm font-medium">{user?.name || 'Usuário'}</p>
                <p className="text-xs text-virtus-text-muted capitalize">{user?.role || 'trader'}</p>
              </div>
              <ChevronDown className="hidden sm:block w-4 h-4 text-virtus-text-muted" />
            </button>
            
            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-virtus-bg-card border border-virtus-border-primary rounded-lg shadow-virtus-lg py-2 animate-slideDown z-50">
                {/* Show user info on mobile */}
                <div className="sm:hidden px-4 py-2 border-b border-virtus-border-primary">
                  <p className="text-sm font-medium">{user?.name || 'Usuário'}</p>
                  <p className="text-xs text-virtus-text-muted capitalize">{user?.role || 'trader'}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-virtus-accent-danger hover:bg-virtus-bg-hover transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sair</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="main-content">
        <Outlet />
      </main>
      
      {/* Mobile Bottom Navigation */}
      <nav className="mobile-bottom-nav">
        {flatNavigation.slice(0, 5).map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `mobile-nav-item ${isActive ? 'mobile-nav-item-active' : ''}`
            }
          >
            <item.icon className="w-5 h-5" />
            <span className="text-[10px]">{item.name}</span>
          </NavLink>
        ))}
      </nav>
      
      {/* Daily Briefing Modal */}
      <DailyBriefingModal 
        isOpen={showBriefing} 
        onClose={() => setShowBriefing(false)} 
      />
      
      {/* Command Palette */}
      <CommandPalette
        isOpen={showCommandPalette}
        onClose={() => setShowCommandPalette(false)}
      />
      
      {/* Keyboard Shortcuts Help */}
      <KeyboardShortcutsHelp
        isOpen={showShortcutsHelp}
        onClose={() => setShowShortcutsHelp(false)}
      />
      
      {/* PWA Components */}
      <OnlineStatus />
      <UpdatePrompt />
    </div>
  )
}
