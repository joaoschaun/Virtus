/**
 * Calculadora de Dividendos
 */

import { useState, useMemo } from 'react'
import { X, Calculator, TrendingUp, Wallet, Calendar, PiggyBank } from 'lucide-react'
import { cn } from '../../lib/utils'

interface DividendCalculatorProps {
  isOpen: boolean
  onClose: () => void
  initialSymbol?: string
  initialPrice?: number
  initialDY?: number
}

export function DividendCalculator({ 
  isOpen, 
  onClose, 
  initialSymbol = '',
  initialPrice = 0,
  initialDY = 0
}: DividendCalculatorProps) {
  const [symbol, setSymbol] = useState(initialSymbol)
  const [currentPrice, setCurrentPrice] = useState(initialPrice.toString())
  const [dividendYield, setDividendYield] = useState(initialDY.toString())
  const [investmentAmount, setInvestmentAmount] = useState('10000')
  const [projectionYears, setProjectionYears] = useState('10')
  const [reinvest, setReinvest] = useState(true)
  const [dyGrowth, setDyGrowth] = useState('0') // Crescimento anual do DY

  const calculations = useMemo(() => {
    const price = parseFloat(currentPrice) || 0
    const dy = parseFloat(dividendYield) || 0
    const investment = parseFloat(investmentAmount) || 0
    const years = parseInt(projectionYears) || 1
    const growth = parseFloat(dyGrowth) || 0

    if (!price || !dy || !investment) {
      return null
    }

    const shares = Math.floor(investment / price)
    const actualInvestment = shares * price
    const monthlyDY = dy / 12

    // Projeção ano a ano
    const projection = []
    let currentShares = shares
    let totalDividends = 0
    let currentDY = dy

    for (let year = 1; year <= years; year++) {
      // Aplicar crescimento do DY
      if (year > 1 && growth > 0) {
        currentDY = currentDY * (1 + growth / 100)
      }

      const yearlyDividend = currentShares * price * (currentDY / 100)
      totalDividends += yearlyDividend

      // Reinvestir dividendos comprando mais ações
      if (reinvest) {
        const newShares = Math.floor(yearlyDividend / price)
        currentShares += newShares
      }

      projection.push({
        year,
        shares: currentShares,
        dividendYield: currentDY,
        yearlyDividend,
        totalDividends,
        portfolioValue: currentShares * price,
      })
    }

    const finalYear = projection[projection.length - 1]
    
    return {
      initialShares: shares,
      actualInvestment,
      monthlyDividend: shares * price * (dy / 100) / 12,
      yearlyDividend: shares * price * (dy / 100),
      projection,
      finalShares: finalYear?.shares || shares,
      finalPortfolioValue: finalYear?.portfolioValue || actualInvestment,
      totalDividendsReceived: finalYear?.totalDividends || 0,
      totalReturn: (finalYear?.portfolioValue || actualInvestment) + (finalYear?.totalDividends || 0) - actualInvestment,
      totalReturnPercent: (((finalYear?.portfolioValue || actualInvestment) + (finalYear?.totalDividends || 0)) / actualInvestment - 1) * 100,
    }
  }, [currentPrice, dividendYield, investmentAmount, projectionYears, reinvest, dyGrowth])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-virtus-bg-secondary border border-virtus-border rounded-xl shadow-2xl animate-fadeIn my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-virtus-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/20 rounded-lg">
              <Calculator className="w-5 h-5 text-emerald-500" />
            </div>
            <h2 className="text-lg font-semibold">Calculadora de Dividendos</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-virtus-bg-tertiary rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
                Símbolo (opcional)
              </label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="Ex: PETR4"
                className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
                Preço Atual (R$)
              </label>
              <input
                type="number"
                step="0.01"
                value={currentPrice}
                onChange={(e) => setCurrentPrice(e.target.value)}
                placeholder="35.50"
                className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
                Dividend Yield Anual (%)
              </label>
              <input
                type="number"
                step="0.1"
                value={dividendYield}
                onChange={(e) => setDividendYield(e.target.value)}
                placeholder="8.5"
                className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
                Valor a Investir (R$)
              </label>
              <input
                type="number"
                value={investmentAmount}
                onChange={(e) => setInvestmentAmount(e.target.value)}
                placeholder="10000"
                className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
                Projeção (anos)
              </label>
              <input
                type="number"
                min="1"
                max="30"
                value={projectionYears}
                onChange={(e) => setProjectionYears(e.target.value)}
                className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
                Crescimento DY Anual (%)
              </label>
              <input
                type="number"
                step="0.5"
                value={dyGrowth}
                onChange={(e) => setDyGrowth(e.target.value)}
                placeholder="0"
                className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
              />
            </div>
          </div>
          
          {/* Reinvestir */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setReinvest(!reinvest)}
              className={cn(
                'relative w-12 h-6 rounded-full transition-colors',
                reinvest ? 'bg-emerald-500' : 'bg-virtus-bg-tertiary'
              )}
            >
              <span className={cn(
                'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                reinvest ? 'translate-x-7' : 'translate-x-1'
              )} />
            </button>
            <span className="text-sm text-virtus-text-secondary">
              Reinvestir dividendos automaticamente
            </span>
          </div>
          
          {/* Results */}
          {calculations && (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-virtus-bg-tertiary rounded-lg">
                  <div className="flex items-center gap-2 text-virtus-text-muted mb-1">
                    <PiggyBank className="w-4 h-4" />
                    <span className="text-xs">Ações</span>
                  </div>
                  <p className="text-lg font-bold">{calculations.initialShares}</p>
                </div>
                
                <div className="p-3 bg-virtus-bg-tertiary rounded-lg">
                  <div className="flex items-center gap-2 text-virtus-text-muted mb-1">
                    <Wallet className="w-4 h-4" />
                    <span className="text-xs">Mensal</span>
                  </div>
                  <p className="text-lg font-bold text-emerald-500">
                    R$ {calculations.monthlyDividend.toFixed(2)}
                  </p>
                </div>
                
                <div className="p-3 bg-virtus-bg-tertiary rounded-lg">
                  <div className="flex items-center gap-2 text-virtus-text-muted mb-1">
                    <Calendar className="w-4 h-4" />
                    <span className="text-xs">Anual</span>
                  </div>
                  <p className="text-lg font-bold text-emerald-500">
                    R$ {calculations.yearlyDividend.toFixed(2)}
                  </p>
                </div>
                
                <div className="p-3 bg-virtus-bg-tertiary rounded-lg">
                  <div className="flex items-center gap-2 text-virtus-text-muted mb-1">
                    <TrendingUp className="w-4 h-4" />
                    <span className="text-xs">Retorno {projectionYears}a</span>
                  </div>
                  <p className={cn(
                    'text-lg font-bold',
                    calculations.totalReturnPercent >= 0 ? 'text-emerald-500' : 'text-red-500'
                  )}>
                    {calculations.totalReturnPercent.toFixed(1)}%
                  </p>
                </div>
              </div>
              
              {/* Projection Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-virtus-text-muted border-b border-virtus-border">
                      <th className="pb-2 font-medium">Ano</th>
                      <th className="pb-2 font-medium text-right">Ações</th>
                      <th className="pb-2 font-medium text-right">Dividendo/Ano</th>
                      <th className="pb-2 font-medium text-right">Total Recebido</th>
                      <th className="pb-2 font-medium text-right">Patrimônio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {calculations.projection.slice(0, 10).map((row) => (
                      <tr key={row.year} className="border-b border-virtus-border/50">
                        <td className="py-2">{row.year}</td>
                        <td className="py-2 text-right">{row.shares.toLocaleString('pt-BR')}</td>
                        <td className="py-2 text-right text-emerald-500">
                          R$ {row.yearlyDividend.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-2 text-right">
                          R$ {row.totalDividends.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-2 text-right font-medium">
                          R$ {row.portfolioValue.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Final Summary */}
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                <h4 className="font-medium text-emerald-400 mb-2">
                  Resumo após {projectionYears} anos
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-virtus-text-muted">Investimento inicial:</span>
                    <p className="font-medium">R$ {calculations.actualInvestment.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
                  </div>
                  <div>
                    <span className="text-virtus-text-muted">Total em dividendos:</span>
                    <p className="font-medium text-emerald-500">R$ {calculations.totalDividendsReceived.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
                  </div>
                  <div>
                    <span className="text-virtus-text-muted">Valor final do patrimônio:</span>
                    <p className="font-medium">R$ {calculations.finalPortfolioValue.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
                  </div>
                  <div>
                    <span className="text-virtus-text-muted">Retorno total:</span>
                    <p className="font-medium text-emerald-500">
                      R$ {calculations.totalReturn.toLocaleString('pt-BR', { minimumFractionDigits: 2 })} ({calculations.totalReturnPercent.toFixed(1)}%)
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default DividendCalculator
