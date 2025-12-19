import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFavoritesStore } from '../stores/favoritesStore'
import {
  Search,
  LayoutDashboard,
  Globe,
  Target,
  Building2,
  Landmark,
  Bitcoin,
  ArrowLeftRight,
  Percent,
  DollarSign,
  Wallet,
  Briefcase,
  Play,
  ListOrdered,
  LineChart,
  Bot,
  Zap,
  BarChart3,
  Activity,
  Instagram,
  Settings,
  TrendingUp,
  Star,
  Command,
  X,
  ArrowRight,
} from 'lucide-react'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

interface CommandItem {
  id: string
  name: string
  description?: string
  icon: React.ComponentType<{ className?: string }>
  type: 'page' | 'action' | 'asset'
  action: () => void
  keywords?: string[]
}

const pages: CommandItem[] = [
  { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard, type: 'page', action: () => {}, keywords: ['home', 'início'] },
  { id: 'forex', name: 'Forex Briefing', icon: TrendingUp, type: 'page', action: () => {}, keywords: ['cambio', 'dolar'] },
  { id: 'market-overview', name: 'Visão Geral', icon: Globe, type: 'page', action: () => {}, keywords: ['mercado', 'overview'] },
  { id: 'screener', name: 'Screener', icon: Target, type: 'page', action: () => {}, keywords: ['filtro', 'busca'] },
  { id: 'stocks', name: 'Ações', icon: Building2, type: 'page', action: () => {}, keywords: ['acoes', 'bovespa'] },
  { id: 'fiis', name: 'FIIs', icon: Landmark, type: 'page', action: () => {}, keywords: ['fundos', 'imobiliario'] },
  { id: 'crypto', name: 'Criptomoedas', icon: Bitcoin, type: 'page', action: () => {}, keywords: ['bitcoin', 'ethereum'] },
  { id: 'currency', name: 'Câmbio', icon: ArrowLeftRight, type: 'page', action: () => {}, keywords: ['dolar', 'euro'] },
  { id: 'indicators', name: 'Indicadores', icon: Percent, type: 'page', action: () => {}, keywords: ['selic', 'ipca'] },
  { id: 'dividends', name: 'Dividendos B3', icon: DollarSign, type: 'page', action: () => {}, keywords: ['proventos'] },
  { id: 'carteira-dividendos', name: 'Carteira Dividendos', icon: Wallet, type: 'page', action: () => {}, keywords: ['portfolio'] },
  { id: 'fii-portfolio', name: 'Carteira FIIs', icon: Briefcase, type: 'page', action: () => {}, keywords: ['portfolio'] },
  { id: 'paper-trading', name: 'Paper Trading', icon: Play, type: 'page', action: () => {}, keywords: ['simulacao'] },
  { id: 'positions', name: 'Posições', icon: ListOrdered, type: 'page', action: () => {}, keywords: ['operacoes'] },
  { id: 'trades', name: 'Histórico', icon: LineChart, type: 'page', action: () => {}, keywords: ['trades'] },
  { id: 'bots', name: 'Bots', icon: Bot, type: 'page', action: () => {}, keywords: ['automatico'] },
  { id: 'strategies', name: 'Estratégias', icon: Zap, type: 'page', action: () => {}, keywords: ['trading'] },
  { id: 'analysis', name: 'Análise', icon: BarChart3, type: 'page', action: () => {}, keywords: ['grafico'] },
  { id: 'monitoring', name: 'Monitoramento', icon: Activity, type: 'page', action: () => {}, keywords: ['sistema'] },
  { id: 'social', name: 'Social Media', icon: Instagram, type: 'page', action: () => {}, keywords: ['instagram'] },
  { id: 'settings', name: 'Configurações', icon: Settings, type: 'page', action: () => {}, keywords: ['config'] },
]

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const navigate = useNavigate()
  const { favorites } = useFavoritesStore()

  // Build command items with navigation actions
  const commandItems = useMemo(() => {
    const items: CommandItem[] = pages.map(page => ({
      ...page,
      action: () => {
        navigate(`/${page.id}`)
        onClose()
      }
    }))

    // Add favorite assets
    favorites.forEach(fav => {
      items.push({
        id: `fav-${fav.symbol}`,
        name: fav.symbol,
        description: `${fav.type.toUpperCase()} - Favorito`,
        icon: Star,
        type: 'asset',
        action: () => {
          // Navigate to the appropriate page based on type
          const typeRoutes: Record<string, string> = {
            stock: '/stocks',
            fii: '/fiis',
            crypto: '/crypto',
          }
          navigate(typeRoutes[fav.type] || '/market-overview')
          onClose()
        },
        keywords: [fav.type, 'favorito']
      })
    })

    return items
  }, [navigate, onClose, favorites])

  // Filter items based on query
  const filteredItems = useMemo(() => {
    if (!query.trim()) return commandItems.slice(0, 10)

    const lowerQuery = query.toLowerCase()
    return commandItems.filter(item => {
      const nameMatch = item.name.toLowerCase().includes(lowerQuery)
      const descMatch = item.description?.toLowerCase().includes(lowerQuery)
      const keywordMatch = item.keywords?.some(k => k.toLowerCase().includes(lowerQuery))
      return nameMatch || descMatch || keywordMatch
    })
  }, [query, commandItems])

  // Reset selection when filtered items change
  useEffect(() => {
    setSelectedIndex(0)
  }, [filteredItems])

  // Reset query when modal opens
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
    }
  }, [isOpen])

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => Math.min(prev + 1, filteredItems.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => Math.max(prev - 1, 0))
        break
      case 'Enter':
        e.preventDefault()
        if (filteredItems[selectedIndex]) {
          filteredItems[selectedIndex].action()
        }
        break
      case 'Escape':
        e.preventDefault()
        onClose()
        break
    }
  }, [filteredItems, selectedIndex, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-virtus-bg-card border border-virtus-border-primary rounded-xl shadow-2xl overflow-hidden animate-slideDown">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-virtus-border-primary">
          <Search className="w-5 h-5 text-virtus-text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar páginas, ativos, ações..."
            className="flex-1 bg-transparent text-virtus-text-primary placeholder-virtus-text-muted focus:outline-none"
            autoFocus
          />
          <kbd className="flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-virtus-bg-tertiary text-xs text-virtus-text-muted">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto py-2">
          {filteredItems.length === 0 ? (
            <div className="px-4 py-8 text-center text-virtus-text-muted">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Nenhum resultado encontrado</p>
            </div>
          ) : (
            filteredItems.map((item, index) => (
              <button
                key={item.id}
                onClick={item.action}
                onMouseEnter={() => setSelectedIndex(index)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 transition-colors ${
                  index === selectedIndex 
                    ? 'bg-virtus-accent-primary/10 text-virtus-accent-primary' 
                    : 'text-virtus-text-primary hover:bg-virtus-bg-tertiary'
                }`}
              >
                <item.icon className={`w-5 h-5 ${
                  index === selectedIndex ? 'text-virtus-accent-primary' : 'text-virtus-text-muted'
                }`} />
                <div className="flex-1 text-left">
                  <p className="font-medium">{item.name}</p>
                  {item.description && (
                    <p className="text-xs text-virtus-text-muted">{item.description}</p>
                  )}
                </div>
                {index === selectedIndex && (
                  <ArrowRight className="w-4 h-4" />
                )}
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-virtus-border-primary bg-virtus-bg-tertiary/50 text-xs text-virtus-text-muted">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-virtus-bg-tertiary">↑↓</kbd>
              navegar
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-virtus-bg-tertiary">↵</kbd>
              selecionar
            </span>
          </div>
          <span className="flex items-center gap-1">
            <kbd className="px-1 py-0.5 rounded bg-virtus-bg-tertiary">ESC</kbd>
            fechar
          </span>
        </div>
      </div>
    </div>
  )
}
