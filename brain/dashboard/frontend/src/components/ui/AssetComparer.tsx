/**
 * Comparador de Ativos
 */

import { useState } from 'react'
import { X, Plus, Trash2, BarChart3, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react'
import { cn } from '../../lib/utils'

interface Asset {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  dy?: number
  pe?: number
  pvp?: number
  marketCap?: number
}

interface AssetComparerProps {
  isOpen: boolean
  onClose: () => void
}

// Dados mockados - em produção viria da API
const mockAssets: Record<string, Asset> = {
  'PETR4': { symbol: 'PETR4', name: 'Petrobras PN', price: 35.42, change: 0.52, changePercent: 1.49, dy: 12.5, pe: 4.2, pvp: 1.1, marketCap: 470000000000 },
  'VALE3': { symbol: 'VALE3', name: 'Vale ON', price: 62.15, change: -1.23, changePercent: -1.94, dy: 8.3, pe: 5.8, pvp: 1.4, marketCap: 285000000000 },
  'ITUB4': { symbol: 'ITUB4', name: 'Itaú Unibanco PN', price: 32.80, change: 0.35, changePercent: 1.08, dy: 5.2, pe: 8.5, pvp: 1.8, marketCap: 320000000000 },
  'BBDC4': { symbol: 'BBDC4', name: 'Bradesco PN', price: 12.45, change: -0.18, changePercent: -1.42, dy: 4.8, pe: 6.2, pvp: 0.9, marketCap: 125000000000 },
  'MXRF11': { symbol: 'MXRF11', name: 'Maxi Renda FII', price: 9.85, change: 0.02, changePercent: 0.20, dy: 13.2, pvp: 0.92, marketCap: 3500000000 },
  'HGLG11': { symbol: 'HGLG11', name: 'CSHG Logística', price: 156.20, change: -0.80, changePercent: -0.51, dy: 8.1, pvp: 1.05, marketCap: 4200000000 },
  'BBAS3': { symbol: 'BBAS3', name: 'Banco do Brasil ON', price: 28.90, change: 0.42, changePercent: 1.47, dy: 9.1, pe: 4.5, pvp: 0.85, marketCap: 165000000000 },
  'WEGE3': { symbol: 'WEGE3', name: 'WEG ON', price: 42.30, change: 0.65, changePercent: 1.56, dy: 1.2, pe: 32.5, pvp: 8.2, marketCap: 178000000000 },
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

const formatPercent = (value: number) => {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

const formatMarketCap = (value: number) => {
  if (value >= 1e12) return `R$ ${(value / 1e12).toFixed(1)}T`
  if (value >= 1e9) return `R$ ${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `R$ ${(value / 1e6).toFixed(1)}M`
  return formatCurrency(value)
}

export function AssetComparer({ isOpen, onClose }: AssetComparerProps) {
  const [selectedAssets, setSelectedAssets] = useState<string[]>(['PETR4', 'VALE3'])
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearchOpen, setIsSearchOpen] = useState(false)

  const assets = selectedAssets.map(s => mockAssets[s]).filter(Boolean)

  const addAsset = (symbol: string) => {
    if (!selectedAssets.includes(symbol) && selectedAssets.length < 4) {
      setSelectedAssets([...selectedAssets, symbol])
    }
    setSearchQuery('')
    setIsSearchOpen(false)
  }

  const removeAsset = (symbol: string) => {
    setSelectedAssets(selectedAssets.filter(s => s !== symbol))
  }

  const filteredSymbols = Object.keys(mockAssets).filter(
    s => !selectedAssets.includes(s) && 
    (s.toLowerCase().includes(searchQuery.toLowerCase()) ||
     mockAssets[s].name.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const getMetricBar = (value: number, max: number, color: string) => {
    const width = (value / max) * 100
    return (
      <div className="h-2 bg-virtus-bg-tertiary rounded-full overflow-hidden">
        <div 
          className={cn('h-full rounded-full transition-all', color)}
          style={{ width: `${Math.min(width, 100)}%` }}
        />
      </div>
    )
  }

  if (!isOpen) return null

  const maxDY = Math.max(...assets.map(a => a.dy || 0), 1)
  const maxPE = Math.max(...assets.map(a => a.pe || 0), 1)
  const maxPVP = Math.max(...assets.map(a => a.pvp || 0), 1)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-4xl bg-virtus-bg-secondary border border-virtus-border rounded-xl shadow-2xl animate-fadeIn my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-virtus-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <BarChart3 className="w-5 h-5 text-blue-500" />
            </div>
            <h2 className="text-lg font-semibold">Comparador de Ativos</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-virtus-bg-tertiary rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6">
          {/* Add Asset */}
          <div className="mb-6 relative">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setIsSearchOpen(true)
                  }}
                  onFocus={() => setIsSearchOpen(true)}
                  placeholder="Adicionar ativo para comparar..."
                  className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
                  disabled={selectedAssets.length >= 4}
                />
                
                {/* Search Dropdown */}
                {isSearchOpen && searchQuery && filteredSymbols.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-virtus-bg-secondary border border-virtus-border rounded-lg shadow-xl z-10 max-h-48 overflow-y-auto">
                    {filteredSymbols.map(symbol => (
                      <button
                        key={symbol}
                        onClick={() => addAsset(symbol)}
                        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-virtus-bg-tertiary transition-colors"
                      >
                        <span className="font-medium">{symbol}</span>
                        <span className="text-sm text-virtus-text-muted">{mockAssets[symbol].name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              
              <button
                onClick={() => setSelectedAssets(['PETR4', 'VALE3'])}
                className="p-2.5 bg-virtus-bg-tertiary hover:bg-virtus-bg-tertiary/80 rounded-lg transition-colors"
                title="Resetar comparação"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
            </div>
            
            {selectedAssets.length >= 4 && (
              <p className="text-xs text-amber-500 mt-1">Máximo de 4 ativos para comparar</p>
            )}
          </div>
          
          {/* Comparison Table */}
          {assets.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-virtus-border">
                    <th className="pb-3 text-left text-sm font-medium text-virtus-text-muted">Métrica</th>
                    {assets.map(asset => (
                      <th key={asset.symbol} className="pb-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <span className="font-bold">{asset.symbol}</span>
                          <button
                            onClick={() => removeAsset(asset.symbol)}
                            className="p-1 hover:bg-red-500/20 hover:text-red-500 rounded transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <span className="text-xs text-virtus-text-muted font-normal">{asset.name}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-virtus-border/50">
                  {/* Preço */}
                  <tr>
                    <td className="py-3 text-sm text-virtus-text-secondary">Preço</td>
                    {assets.map(asset => (
                      <td key={asset.symbol} className="py-3 text-center font-medium">
                        {formatCurrency(asset.price)}
                      </td>
                    ))}
                  </tr>
                  
                  {/* Variação */}
                  <tr>
                    <td className="py-3 text-sm text-virtus-text-secondary">Variação</td>
                    {assets.map(asset => (
                      <td key={asset.symbol} className="py-3 text-center">
                        <span className={cn(
                          'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-sm font-medium',
                          asset.changePercent >= 0 
                            ? 'bg-green-500/20 text-green-500' 
                            : 'bg-red-500/20 text-red-500'
                        )}>
                          {asset.changePercent >= 0 
                            ? <TrendingUp className="w-3.5 h-3.5" /> 
                            : <TrendingDown className="w-3.5 h-3.5" />
                          }
                          {formatPercent(asset.changePercent)}
                        </span>
                      </td>
                    ))}
                  </tr>
                  
                  {/* Dividend Yield */}
                  <tr>
                    <td className="py-3 text-sm text-virtus-text-secondary">Dividend Yield</td>
                    {assets.map(asset => (
                      <td key={asset.symbol} className="py-3 text-center">
                        <div className="space-y-1">
                          <span className="font-medium text-emerald-500">
                            {asset.dy ? `${asset.dy.toFixed(1)}%` : '-'}
                          </span>
                          {asset.dy && getMetricBar(asset.dy, maxDY, 'bg-emerald-500')}
                        </div>
                      </td>
                    ))}
                  </tr>
                  
                  {/* P/L */}
                  <tr>
                    <td className="py-3 text-sm text-virtus-text-secondary">P/L</td>
                    {assets.map(asset => (
                      <td key={asset.symbol} className="py-3 text-center">
                        <div className="space-y-1">
                          <span className="font-medium">
                            {asset.pe ? asset.pe.toFixed(1) : '-'}
                          </span>
                          {asset.pe && getMetricBar(asset.pe, maxPE, 'bg-blue-500')}
                        </div>
                      </td>
                    ))}
                  </tr>
                  
                  {/* P/VP */}
                  <tr>
                    <td className="py-3 text-sm text-virtus-text-secondary">P/VP</td>
                    {assets.map(asset => (
                      <td key={asset.symbol} className="py-3 text-center">
                        <div className="space-y-1">
                          <span className="font-medium">
                            {asset.pvp ? asset.pvp.toFixed(2) : '-'}
                          </span>
                          {asset.pvp && getMetricBar(asset.pvp, maxPVP, 'bg-purple-500')}
                        </div>
                      </td>
                    ))}
                  </tr>
                  
                  {/* Market Cap */}
                  <tr>
                    <td className="py-3 text-sm text-virtus-text-secondary">Valor de Mercado</td>
                    {assets.map(asset => (
                      <td key={asset.symbol} className="py-3 text-center font-medium">
                        {asset.marketCap ? formatMarketCap(asset.marketCap) : '-'}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <BarChart3 className="w-12 h-12 mx-auto mb-3 text-virtus-text-muted opacity-50" />
              <p className="text-virtus-text-muted">Adicione ativos para começar a comparar</p>
            </div>
          )}
          
          {/* Legend */}
          {assets.length > 0 && (
            <div className="mt-6 pt-4 border-t border-virtus-border">
              <p className="text-xs text-virtus-text-muted">
                <strong>P/L:</strong> Preço/Lucro (quanto menor, mais "barato") • 
                <strong> P/VP:</strong> Preço/Valor Patrimonial (abaixo de 1 pode indicar desconto) • 
                <strong> DY:</strong> Dividend Yield (retorno em dividendos)
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AssetComparer
