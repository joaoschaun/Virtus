import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useTradingStore } from '../stores/tradingStore'
import { useWebSocket } from '../services/websocket'
import NotificationDropdown from './NotificationDropdown'
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
  Menu,
  X,
  Instagram,
} from 'lucide-react'
import { useState, useEffect } from 'react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Posições', href: '/positions', icon: ListOrdered },
  { name: 'Histórico', href: '/trades', icon: LineChart },
  { name: 'Bots', href: '/bots', icon: Bot },
  { name: 'Estratégias', href: '/strategies', icon: Zap },
  { name: 'Análise', href: '/analysis', icon: BarChart3 },
  { name: 'Social Media', href: '/social', icon: Instagram },
  { name: 'Configurações', href: '/settings', icon: Settings },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const { isConnected, metrics } = useTradingStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  
  // Initialize WebSocket
  useWebSocket()
  
  // Close mobile menu on route change
  useEffect(() => {
    setShowMobileMenu(false)
  }, [location.pathname])
  
  const handleLogout = () => {
    logout()
    navigate('/login')
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
            <div className="flex items-center gap-3">
              <img 
                src="/virtus-primaria.png" 
                alt="Virtus Investimentos" 
                className="h-10 w-auto"
              />
            </div>
            {/* Close button for mobile */}
            <button 
              onClick={() => setShowMobileMenu(false)}
              className="lg:hidden p-2 rounded-lg hover:bg-virtus-bg-hover transition-colors"
            >
              <X className="w-5 h-5 text-virtus-text-secondary" />
            </button>
          </div>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          <ul className="space-y-1">
            {navigation.map((item) => (
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
        {navigation.slice(0, 5).map((item) => (
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
    </div>
  )
}
