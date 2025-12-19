/**
 * Comparador de Ativos
 */

import { useState } from 'react'
import { X, Plus, Scale, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '../lib/utils'
import { formatCurrency, formatPercent } from '../services/brapiService'

interface AssetData {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  pe?: number
  pvp?: number
  dy?: number
  marketCap?: number
  volume?: number
}

interface AssetComparerProps {
  isOpen: boolean
  onClose: () => void
  initialAssets?: AssetData[]
}

const metrics = [
  { key: 'price', label: 'Preço', format: (v: number) => formatCurrency(v) },
  { key: 'changePercent', label: 'Variação %', format: (v: number) => formatPercent(v), colorize: true },
  { key: 'pe', label: 'P/L', format: (v: number) => v?.toFixed(2) || '-' },
  { key: 'pvp', label: 'P/VP', format: (v: number) => v?.toFixed(2) || '-' },
  { key: 'dy', label: 'DY', format: (v: number) => v ? `${v.toFixed(2)}%` : '-', highlight: true },
  { key: 'marketCap', label: 'Mkt Cap', format: (v: number) => formatMarketCap(v) },
  { key: 'volume', label: 'Volume', format: (v: number) => formatVolume(v) },
]

function formatMarketCap(value: number): string {
  if (!value) return '-'
  if (value >= 1e12) return `R$ ${(value / 1e12).toFixed(1)}T`
  if (value >= 1e9) return `R$ ${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `R$ ${(value / 1e6).toFixed(1)}M`
  return formatCurrency(value)
}

function formatVolume(value: number): string {
  if (!value) return '-'
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`
  return value.toString()
}

// Dados de exemplo
const sampleAssets: AssetData[] = [
  {
    symbol: 'PETR4',
    name: 'Petrobras PN',
    price: 37.85,
    change: 0.45,
    changePercent: 1.2,
    pe: 5.2,
    pvp: 1.1,
    dy: 12.5,
    marketCap: 495e9,
    volume: 85e6
  },
  {
    symbol: 'VALE3',
    name: 'Vale ON',
    price: 62.30,
    change: -0.80,
    changePercent: -1.3,
    pe: 5.8,
    pvp: 1.4,
    dy: 9.8,
    marketCap: 285e9,
    volume: 62e6
  },
  {
    symbol: 'ITUB4',
    name: 'Itaú Unibanco PN',
    price: 33.45,
    change: 0.15,
    changePercent: 0.45,
    pe: 8.2,
    pvp: 1.6,
    dy: 5.2,
    marketCap: 320e9,
    volume: 45e6
  }
]

export default function AssetComparer({ isOpen, onClose, initialAssets = sampleAssets }: AssetComparerProps) {
  const [assets, setAssets] = useState<AssetData[]>(initialAssets.slice(0, 4))
  const [searchTerm, setSearchTerm] = useState('')
  
  if (!isOpen) return null
  
  const removeAsset = (symbol: string) => {
    setAssets(prev => prev.filter(a => a.symbol !== symbol))
  }
  
  const getBestValue = (key: string): number => {
    const values = assets.map(a => (a as any)[key]).filter(v => v != null && !isNaN(v))
    if (values.length === 0) return 0
    
    // For DY, higher is better. For P/L and P/VP, lower is better
    if (key === 'dy' || key === 'changePercent') {
      return Math.max(...values)
    }
    if (key === 'pe' || key === 'pvp') {
      return Math.min(...values)
    }
    return Math.max(...values)
  }
  
  const isBest = (key: string, value: number): boolean => {
    if (value == null || isNaN(value)) return false
    const best = getBestValue(key)
    
    if (key === 'dy' || key === 'changePercent') {
      return value === best && value > 0
    }
    if (key === 'pe' || key === 'pvp') {
      return value === best && value > 0
    }
    return value === best
  }
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-4xl bg-virtus-bg-card border border-virtus-border-primary rounded-xl shadow-2xl overflow-hidden animate-slideDown">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-virtus-border-primary">
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-virtus-accent-primary" />
            <h2 className="text-lg font-semibold text-virtus-text-primary">
              Comparador de Ativos
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-virtus-bg-tertiary transition-colors"
          >
            <X className="w-5 h-5 text-virtus-text-muted" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {assets.length === 0 ? (
            <div className="text-center py-12">
              <Scale className="w-12 h-12 mx-auto mb-4 text-virtus-text-muted opacity-50" />
              <p className="text-virtus-text-muted">Adicione ativos para comparar</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-virtus-border-primary">
                    <th className="text-left py-3 px-4 text-sm font-medium text-virtus-text-muted">
                      Métrica
                    </th>
                    {assets.map(asset => (
                      <th key={asset.symbol} className="text-center py-3 px-4 min-w-[140px]">
                        <div className="flex flex-col items-center gap-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-virtus-text-primary">
                              {asset.symbol}
                            </span>
                            <button
                              onClick={() => removeAsset(asset.symbol)}
                              className="p-0.5 rounded hover:bg-virtus-bg-tertiary text-virtus-text-muted hover:text-virtus-accent-danger transition-colors"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                          <span className="text-xs text-virtus-text-muted truncate max-w-[120px]">
                            {asset.name}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {metrics.map(metric => (
                    <tr 
                      key={metric.key} 
                      className="border-b border-virtus-border-primary/50 hover:bg-virtus-bg-tertiary/30 transition-colors"
                    >
                      <td className="py-3 px-4 text-sm font-medium text-virtus-text-secondary">
                        {metric.label}
                      </td>
                      {assets.map(asset => {
                        const value = (asset as any)[metric.key]
                        const isTheBest = isBest(metric.key, value)
                        
                        return (
                          <td 
                            key={`${asset.symbol}-${metric.key}`}
                            className="py-3 px-4 text-center"
                          >
                            <span className={cn(
                              'inline-flex items-center gap-1 px-2 py-1 rounded text-sm font-medium',
                              isTheBest && 'bg-virtus-accent-success/20 text-virtus-accent-success',
                              metric.colorize && value > 0 && 'text-virtus-accent-success',
                              metric.colorize && value < 0 && 'text-virtus-accent-danger',
                              !isTheBest && !metric.colorize && 'text-virtus-text-primary'
                            )}>
                              {metric.colorize && value > 0 && <TrendingUp className="w-3 h-3" />}
                              {metric.colorize && value < 0 && <TrendingDown className="w-3 h-3" />}
                              {metric.colorize && value === 0 && <Minus className="w-3 h-3" />}
                              {metric.format(value)}
                            </span>
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          {/* Legend */}
          <div className="mt-4 flex items-center gap-4 text-xs text-virtus-text-muted">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-virtus-accent-success/20" />
              <span>Melhor valor</span>
            </div>
            <span className="text-virtus-text-muted/50">•</span>
            <span>P/L e P/VP: menor é melhor</span>
            <span className="text-virtus-text-muted/50">•</span>
            <span>DY: maior é melhor</span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-virtus-border-primary bg-virtus-bg-tertiary/50">
          <p className="text-xs text-virtus-text-muted text-center">
            Compare até 4 ativos simultaneamente
          </p>
        </div>
      </div>
    </div>
  )
}
