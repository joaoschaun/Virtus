import { useState, useEffect } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { 
  Home, 
  Newspaper, 
  Calendar, 
  TrendingUp, 
  Menu, 
  X,
  ChevronUp,
  ChevronDown,
  ExternalLink
} from 'lucide-react'

interface TickerItem {
  symbol: string
  name: string
  price: number
  change: number
  change_percent: number
  direction: string
}

const Layout = () => {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [tickerData, setTickerData] = useState<TickerItem[]>([])
  
  const navigation = [
    { name: 'Início', href: '/', icon: Home },
    { name: 'Notícias', href: '/noticias', icon: Newspaper },
    { name: 'Calendário', href: '/calendario', icon: Calendar },
    { name: 'Cotações', href: '/cotacoes', icon: TrendingUp },
  ]

  useEffect(() => {
    fetchTicker()
    const interval = setInterval(fetchTicker, 60000)
    return () => clearInterval(interval)
  }, [])

  const fetchTicker = async () => {
    try {
      const response = await fetch('/api/portal/ticker')
      const data = await response.json()
      if (data.success && data.items) {
        setTickerData(data.items)
      }
    } catch (error) {
      console.error('Erro ao buscar ticker:', error)
    }
  }

  const formatPrice = (price: number | string, symbol: string) => {
    const numPrice = typeof price === 'string' ? parseFloat(price) : price
    if (isNaN(numPrice)) return '---'
    if (symbol === 'bitcoin') return numPrice.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
    if (['dolar', 'euro'].includes(symbol)) return numPrice.toFixed(4)
    if (['ibovespa', 'sp500', 'nasdaq', 'dow_jones'].includes(symbol)) return numPrice.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
    return numPrice.toFixed(2)
  }

  const formatChangePercent = (value: number | string) => {
    const num = typeof value === 'string' ? parseFloat(value) : value
    if (isNaN(num)) return '0.00'
    return num.toFixed(2)
  }

  return (
    <div className="min-h-screen bg-virtus-bg-primary">
      {/* Ticker Bar */}
      <div className="bg-virtus-bg-secondary border-b border-virtus-border-primary overflow-hidden">
        <div className="ticker-wrapper py-2">
          <div className="ticker-content">
            {[...tickerData, ...tickerData].map((item, index) => (
              <div 
                key={`${item.symbol}-${index}`}
                className="flex items-center gap-2 px-6 whitespace-nowrap"
              >
                <span className="text-virtus-text-muted text-sm">{item.name}</span>
                <span className="text-virtus-text-primary font-medium">
                  {formatPrice(item.price, item.symbol)}
                </span>
                <span className={`flex items-center text-sm ${
                  item.direction === 'up' ? 'text-virtus-accent-success' : 'text-virtus-accent-danger'
                }`}>
                  {item.direction === 'up' ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                  {formatChangePercent(item.change_percent)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Header */}
      <header className="bg-virtus-bg-secondary/80 backdrop-blur-sm border-b border-virtus-border-primary sticky top-0 z-50">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            {/* Logo */}
            <Link to="/" className="flex items-center">
              <img 
                src="/virtus-logo.png" 
                alt="VIRTUS Investimentos" 
                className="h-12 md:h-14 w-auto"
              />
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-1">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-virtus-accent-primary/20 text-virtus-accent-primary'
                        : 'text-virtus-text-secondary hover:bg-virtus-bg-hover hover:text-virtus-text-primary'
                    }`}
                  >
                    <item.icon className="w-4 h-4" />
                    {item.name}
                  </Link>
                )
              })}
            </div>

            {/* Dashboard Link */}
            <div className="hidden md:flex items-center gap-4">
              <a
                href="https://dashboard.virtusinvestimentos.com.br"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 bg-gradient-virtus text-white font-semibold rounded-lg text-sm hover:shadow-glow transition-all"
              >
                Dashboard
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-virtus-text-muted hover:text-virtus-text-primary hover:bg-virtus-bg-hover"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <div className="md:hidden py-4 border-t border-virtus-border-primary">
              <div className="flex flex-col gap-2">
                {navigation.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                        isActive
                          ? 'bg-virtus-accent-primary/20 text-virtus-accent-primary'
                          : 'text-virtus-text-secondary hover:bg-virtus-bg-hover'
                      }`}
                    >
                      <item.icon className="w-5 h-5" />
                      {item.name}
                    </Link>
                  )
                })}
                <a
                  href="https://dashboard.virtusinvestimentos.com.br"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 px-4 py-3 mt-2 bg-gradient-virtus text-white font-semibold rounded-lg"
                >
                  <ExternalLink className="w-5 h-5" />
                  Acessar Dashboard
                </a>
              </div>
            </div>
          )}
        </nav>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-virtus-bg-secondary border-t border-virtus-border-primary mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Logo & Description */}
            <div className="col-span-1 md:col-span-2">
              <div className="flex items-center mb-4">
                <img 
                  src="/virtus-logo.png" 
                  alt="VIRTUS Investimentos" 
                  className="h-10 w-auto"
                />
              </div>
              <p className="text-virtus-text-muted text-sm leading-relaxed max-w-md">
                Acompanhe o mercado financeiro em tempo real. Cotações, notícias, calendário econômico 
                e análises para auxiliar suas decisões de investimento.
              </p>
            </div>

            {/* Links */}
            <div>
              <h4 className="text-virtus-text-primary font-semibold mb-4">Navegação</h4>
              <ul className="space-y-2">
                {navigation.map((item) => (
                  <li key={item.name}>
                    <Link 
                      to={item.href}
                      className="text-virtus-text-muted hover:text-virtus-accent-primary text-sm transition-colors"
                    >
                      {item.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            {/* Contact */}
            <div>
              <h4 className="text-virtus-text-primary font-semibold mb-4">Contato</h4>
              <ul className="space-y-2 text-sm text-virtus-text-muted">
                <li>contato@virtusinvestimentos.com.br</li>
                <li className="pt-4">
                  <a
                    href="https://dashboard.virtusinvestimentos.com.br"
                    className="inline-flex items-center gap-2 text-virtus-accent-primary hover:text-virtus-accent-secondary transition-colors"
                  >
                    Acessar Dashboard
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-virtus-border-primary mt-8 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-virtus-text-muted text-sm">
              © {new Date().getFullYear()} VIRTUS Investimentos. Todos os direitos reservados.
            </p>
            <p className="text-virtus-text-muted text-xs">
              As informações apresentadas têm caráter informativo. Consulte um profissional antes de investir.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default Layout
