/**
 * Componente de busca global com Command Palette
 * Atalho: Ctrl+K ou Cmd+K
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Search, 
  X, 
  TrendingUp, 
  Building2, 
  Bitcoin, 
  DollarSign,
  LayoutDashboard,
  LineChart,
  Settings,
  Wallet,
  BarChart3,
  ArrowRight,
  Star,
  Clock
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { useFavoritesStore } from '../../stores/favoritesStore'

interface SearchResult {
  id: string
  title: string
  subtitle?: string
  type: 'page' | 'stock' | 'fii' | 'crypto' | 'currency' | 'action'
  icon: React.ReactNode
  action: () => void
}

// Páginas disponíveis para navegação
const pages: SearchResult[] = [
  { id: 'dashboard', title: 'Dashboard', subtitle: 'Visão geral', type: 'page', icon: <LayoutDashboard className="w-4 h-4" />, action: () => {} },
  { id: 'market', title: 'Visão do Mercado', subtitle: 'Ibovespa, índices', type: 'page', icon: <TrendingUp className="w-4 h-4" />, action: () => {} },
  { id: 'stocks', title: 'Ações', subtitle: 'B3, cotações', type: 'page', icon: <LineChart className="w-4 h-4" />, action: () => {} },
  { id: 'fiis', title: 'FIIs', subtitle: 'Fundos imobiliários', type: 'page', icon: <Building2 className="w-4 h-4" />, action: () => {} },
  { id: 'crypto', title: 'Criptomoedas', subtitle: 'Bitcoin, Ethereum', type: 'page', icon: <Bitcoin className="w-4 h-4" />, action: () => {} },
  { id: 'currency', title: 'Moedas', subtitle: 'Câmbio', type: 'page', icon: <DollarSign className="w-4 h-4" />, action: () => {} },
  { id: 'dividends', title: 'Dividendos', subtitle: 'Proventos', type: 'page', icon: <Wallet className="w-4 h-4" />, action: () => {} },
  { id: 'screener', title: 'Screener', subtitle: 'Filtros avançados', type: 'page', icon: <BarChart3 className="w-4 h-4" />, action: () => {} },
  { id: 'settings', title: 'Configurações', subtitle: 'Preferências', type: 'page', icon: <Settings className="w-4 h-4" />, action: () => {} },
]

// Ações rápidas
const quickActions: SearchResult[] = [
  { id: 'compare', title: 'Comparar Ativos', subtitle: 'Análise comparativa', type: 'action', icon: <BarChart3 className="w-4 h-4" />, action: () => {} },
  { id: 'calculator', title: 'Calculadora de Dividendos', subtitle: 'Projetar rendimentos', type: 'action', icon: <Wallet className="w-4 h-4" />, action: () => {} },
]

// Ativos populares para busca rápida
const popularAssets: SearchResult[] = [
  { id: 'PETR4', title: 'PETR4', subtitle: 'Petrobras PN', type: 'stock', icon: <TrendingUp className="w-4 h-4 text-blue-500" />, action: () => {} },
  { id: 'VALE3', title: 'VALE3', subtitle: 'Vale ON', type: 'stock', icon: <TrendingUp className="w-4 h-4 text-blue-500" />, action: () => {} },
  { id: 'ITUB4', title: 'ITUB4', subtitle: 'Itaú Unibanco PN', type: 'stock', icon: <TrendingUp className="w-4 h-4 text-blue-500" />, action: () => {} },
  { id: 'BBDC4', title: 'BBDC4', subtitle: 'Bradesco PN', type: 'stock', icon: <TrendingUp className="w-4 h-4 text-blue-500" />, action: () => {} },
  { id: 'MXRF11', title: 'MXRF11', subtitle: 'Maxi Renda FII', type: 'fii', icon: <Building2 className="w-4 h-4 text-emerald-500" />, action: () => {} },
  { id: 'HGLG11', title: 'HGLG11', subtitle: 'CSHG Logística', type: 'fii', icon: <Building2 className="w-4 h-4 text-emerald-500" />, action: () => {} },
  { id: 'BTC', title: 'Bitcoin', subtitle: 'BTC', type: 'crypto', icon: <Bitcoin className="w-4 h-4 text-orange-500" />, action: () => {} },
  { id: 'ETH', title: 'Ethereum', subtitle: 'ETH', type: 'crypto', icon: <Bitcoin className="w-4 h-4 text-purple-500" />, action: () => {} },
]

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  onOpenCompare?: () => void
  onOpenCalculator?: () => void
}

export function CommandPalette({ isOpen, onClose, onOpenCompare, onOpenCalculator }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const favorites = useFavoritesStore(state => state.favorites)

  // Filtrar resultados
  const getResults = useCallback((): SearchResult[] => {
    const q = query.toLowerCase().trim()
    
    if (!q) {
      // Mostrar favoritos + páginas
      const favResults: SearchResult[] = favorites.slice(0, 3).map(f => ({
        id: f.symbol,
        title: f.symbol,
        subtitle: f.name,
        type: f.type,
        icon: f.type === 'fii' ? <Building2 className="w-4 h-4 text-emerald-500" /> :
              f.type === 'crypto' ? <Bitcoin className="w-4 h-4 text-orange-500" /> :
              <TrendingUp className="w-4 h-4 text-blue-500" />,
        action: () => navigate(`/stocks?symbol=${f.symbol}`)
      }))
      
      return [...favResults, ...pages.slice(0, 5)]
    }
    
    // Buscar em páginas
    const pageResults = pages.filter(p => 
      p.title.toLowerCase().includes(q) || 
      p.subtitle?.toLowerCase().includes(q)
    )
    
    // Buscar em ativos populares
    const assetResults = popularAssets.filter(a =>
      a.title.toLowerCase().includes(q) ||
      a.subtitle?.toLowerCase().includes(q)
    )
    
    // Buscar em ações rápidas
    const actionResults = quickActions.filter(a =>
      a.title.toLowerCase().includes(q) ||
      a.subtitle?.toLowerCase().includes(q)
    )
    
    return [...pageResults, ...assetResults, ...actionResults].slice(0, 10)
  }, [query, favorites, navigate])

  const results = getResults()

  // Reset ao abrir
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isOpen])

  // Navegação por teclado
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return
      
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex(i => Math.min(i + 1, results.length - 1))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex(i => Math.max(i - 1, 0))
          break
        case 'Enter':
          e.preventDefault()
          if (results[selectedIndex]) {
            handleSelect(results[selectedIndex])
          }
          break
        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, results, selectedIndex, onClose])

  const handleSelect = (result: SearchResult) => {
    switch (result.type) {
      case 'page':
        navigate(`/${result.id}`)
        break
      case 'stock':
      case 'fii':
        navigate(`/stocks?symbol=${result.id}`)
        break
      case 'crypto':
        navigate(`/crypto?coin=${result.id}`)
        break
      case 'action':
        if (result.id === 'compare' && onOpenCompare) {
          onOpenCompare()
        } else if (result.id === 'calculator' && onOpenCalculator) {
          onOpenCalculator()
        }
        break
    }
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-xl bg-virtus-bg-secondary border border-virtus-border rounded-xl shadow-2xl overflow-hidden animate-fadeIn">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-virtus-border">
          <Search className="w-5 h-5 text-virtus-text-muted" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
            placeholder="Buscar páginas, ativos, ações..."
            className="flex-1 bg-transparent text-virtus-text-primary placeholder-virtus-text-muted outline-none"
          />
          <kbd className="hidden sm:flex items-center gap-1 px-2 py-1 text-xs text-virtus-text-muted bg-virtus-bg-tertiary rounded">
            ESC
          </kbd>
          <button onClick={onClose} className="p-1 hover:bg-virtus-bg-tertiary rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
        
        {/* Results */}
        <div className="max-h-80 overflow-y-auto">
          {results.length === 0 ? (
            <div className="px-4 py-8 text-center text-virtus-text-muted">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Nenhum resultado para "{query}"</p>
            </div>
          ) : (
            <div className="py-2">
              {!query && favorites.length > 0 && (
                <div className="px-3 py-1.5 text-xs font-medium text-virtus-text-muted flex items-center gap-1">
                  <Star className="w-3 h-3" /> Favoritos
                </div>
              )}
              {!query && favorites.length === 0 && (
                <div className="px-3 py-1.5 text-xs font-medium text-virtus-text-muted flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Sugestões
                </div>
              )}
              
              {results.map((result, index) => (
                <button
                  key={result.id}
                  onClick={() => handleSelect(result)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                    index === selectedIndex 
                      ? 'bg-virtus-primary/20 text-virtus-text-primary' 
                      : 'hover:bg-virtus-bg-tertiary text-virtus-text-secondary'
                  )}
                >
                  <div className={cn(
                    'p-2 rounded-lg',
                    index === selectedIndex ? 'bg-virtus-primary/30' : 'bg-virtus-bg-tertiary'
                  )}>
                    {result.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{result.title}</p>
                    {result.subtitle && (
                      <p className="text-xs text-virtus-text-muted truncate">{result.subtitle}</p>
                    )}
                  </div>
                  <ArrowRight className={cn(
                    'w-4 h-4 transition-opacity',
                    index === selectedIndex ? 'opacity-100' : 'opacity-0'
                  )} />
                </button>
              ))}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="px-4 py-2 border-t border-virtus-border bg-virtus-bg-tertiary/50">
          <div className="flex items-center justify-between text-xs text-virtus-text-muted">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-virtus-bg-tertiary rounded">↑↓</kbd> navegar
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-virtus-bg-tertiary rounded">↵</kbd> selecionar
              </span>
            </div>
            <span>VIRTUS Search</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// Hook para abrir/fechar o Command Palette
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false)
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+K ou Cmd+K
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setIsOpen(true)
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])
  
  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
  }
}

export default CommandPalette
