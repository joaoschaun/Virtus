/**
 * Calculadora de Dividendos
 */

import { useState, useMemo } from 'react'
import { X, Calculator, TrendingUp, DollarSign, Percent, Calendar, RefreshCw } from 'lucide-react'
import { cn } from '../lib/utils'

interface DividendCalculatorProps {
  isOpen: boolean
  onClose: () => void
  initialSymbol?: string
  initialPrice?: number
  initialDY?: number
}

interface ProjectionYear {
  year: number
  shares: number
  value: number
  dividends: number
  totalInvested: number
  totalDividends: number
}

export default function DividendCalculator({ 
  isOpen, 
  onClose, 
  initialSymbol = '',
  initialPrice = 0,
  initialDY = 0
}: DividendCalculatorProps) {
  const [symbol, setSymbol] = useState(initialSymbol)
  const [investmentAmount, setInvestmentAmount] = useState<string>('10000')
  const [monthlyContribution, setMonthlyContribution] = useState<string>('500')
  const [currentPrice, setCurrentPrice] = useState<string>(initialPrice.toString())
  const [dividendYield, setDividendYield] = useState<string>(initialDY.toString())
  const [dyGrowth, setDyGrowth] = useState<string>('0')
  const [years, setYears] = useState<string>('10')
  const [reinvest, setReinvest] = useState(true)
  
  const projections = useMemo(() => {
    const initial = parseFloat(investmentAmount) || 0
    const monthly = parseFloat(monthlyContribution) || 0
    const price = parseFloat(currentPrice) || 1
    const dy = (parseFloat(dividendYield) || 0) / 100
    const growth = (parseFloat(dyGrowth) || 0) / 100
    const numYears = parseInt(years) || 10
    
    const results: ProjectionYear[] = []
    
    let currentShares = initial / price
    let totalInvested = initial
    let totalDividends = 0
    let currentDY = dy
    
    for (let year = 1; year <= numYears; year++) {
      // Monthly contributions
      const yearlyContribution = monthly * 12
      if (!reinvest) {
        currentShares += yearlyContribution / price
      }
      totalInvested += yearlyContribution
      
      // Calculate dividends
      const portfolioValue = currentShares * price
      const yearDividends = portfolioValue * currentDY
      totalDividends += yearDividends
      
      // Reinvest dividends
      if (reinvest) {
        currentShares += (yearDividends + yearlyContribution) / price
      }
      
      // DY growth
      currentDY *= (1 + growth)
      
      results.push({
        year,
        shares: currentShares,
        value: currentShares * price,
        dividends: yearDividends,
        totalInvested,
        totalDividends
      })
    }
    
    return results
  }, [investmentAmount, monthlyContribution, currentPrice, dividendYield, dyGrowth, years, reinvest])
  
  const lastYear = projections[projections.length - 1]
  const monthlyIncome = lastYear ? lastYear.dividends / 12 : 0
  const totalReturn = lastYear ? ((lastYear.value + lastYear.totalDividends - lastYear.totalInvested) / lastYear.totalInvested) * 100 : 0
  
  if (!isOpen) return null
  
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value)
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
            <Calculator className="w-5 h-5 text-virtus-accent-primary" />
            <h2 className="text-lg font-semibold text-virtus-text-primary">
              Calculadora de Dividendos
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Form */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-virtus-text-secondary mb-3">
                Parâmetros
              </h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-virtus-text-muted mb-1">
                    Investimento Inicial
                  </label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-virtus-text-muted" />
                    <input
                      type="number"
                      value={investmentAmount}
                      onChange={(e) => setInvestmentAmount(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 bg-virtus-bg-tertiary border border-virtus-border-primary rounded-lg text-virtus-text-primary focus:outline-none focus:border-virtus-accent-primary"
                      placeholder="10000"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-xs text-virtus-text-muted mb-1">
                    Aporte Mensal
                  </label>
                  <div className="relative">
                    <RefreshCw className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-virtus-text-muted" />
                    <input
                      type="number"
                      value={monthlyContribution}
                      onChange={(e) => setMonthlyContribution(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 bg-virtus-bg-tertiary border border-virtus-border-primary rounded-lg text-virtus-text-primary focus:outline-none focus:border-virtus-accent-primary"
                      placeholder="500"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-xs text-virtus-text-muted mb-1">
                    Preço do Ativo
                  </label>
                  <input
                    type="number"
                    value={currentPrice}
                    onChange={(e) => setCurrentPrice(e.target.value)}
                    className="w-full px-3 py-2 bg-virtus-bg-tertiary border border-virtus-border-primary rounded-lg text-virtus-text-primary focus:outline-none focus:border-virtus-accent-primary"
                    placeholder="30.00"
                    step="0.01"
                  />
                </div>
                
                <div>
                  <label className="block text-xs text-virtus-text-muted mb-1">
                    Dividend Yield (%)
                  </label>
                  <div className="relative">
                    <Percent className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-virtus-text-muted" />
                    <input
                      type="number"
                      value={dividendYield}
                      onChange={(e) => setDividendYield(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 bg-virtus-bg-tertiary border border-virtus-border-primary rounded-lg text-virtus-text-primary focus:outline-none focus:border-virtus-accent-primary"
                      placeholder="8"
                      step="0.1"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-xs text-virtus-text-muted mb-1">
                    Crescimento DY (%/ano)
                  </label>
                  <div className="relative">
                    <TrendingUp className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-virtus-text-muted" />
                    <input
                      type="number"
                      value={dyGrowth}
                      onChange={(e) => setDyGrowth(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 bg-virtus-bg-tertiary border border-virtus-border-primary rounded-lg text-virtus-text-primary focus:outline-none focus:border-virtus-accent-primary"
                      placeholder="0"
                      step="0.5"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-xs text-virtus-text-muted mb-1">
                    Período (anos)
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-virtus-text-muted" />
                    <input
                      type="number"
                      value={years}
                      onChange={(e) => setYears(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 bg-virtus-bg-tertiary border border-virtus-border-primary rounded-lg text-virtus-text-primary focus:outline-none focus:border-virtus-accent-primary"
                      placeholder="10"
                      min="1"
                      max="50"
                    />
                  </div>
                </div>
              </div>
              
              {/* Reinvest toggle */}
              <label className="flex items-center gap-3 cursor-pointer">
                <div 
                  className={cn(
                    'w-11 h-6 rounded-full transition-colors relative',
                    reinvest ? 'bg-virtus-accent-success' : 'bg-virtus-bg-tertiary'
                  )}
                  onClick={() => setReinvest(!reinvest)}
                >
                  <div 
                    className={cn(
                      'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                      reinvest ? 'translate-x-6' : 'translate-x-1'
                    )}
                  />
                </div>
                <span className="text-sm text-virtus-text-primary">
                  Reinvestir dividendos
                </span>
              </label>
              
              {/* Summary Cards */}
              <div className="grid grid-cols-2 gap-3 mt-6">
                <div className="p-4 rounded-lg bg-virtus-accent-success/10 border border-virtus-accent-success/30">
                  <p className="text-xs text-virtus-text-muted mb-1">Renda Mensal (Ano {years})</p>
                  <p className="text-xl font-bold text-virtus-accent-success">
                    {formatCurrency(monthlyIncome)}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-virtus-accent-primary/10 border border-virtus-accent-primary/30">
                  <p className="text-xs text-virtus-text-muted mb-1">Patrimônio Final</p>
                  <p className="text-xl font-bold text-virtus-accent-primary">
                    {formatCurrency(lastYear?.value || 0)}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-virtus-bg-tertiary border border-virtus-border-primary">
                  <p className="text-xs text-virtus-text-muted mb-1">Total Investido</p>
                  <p className="text-lg font-semibold text-virtus-text-primary">
                    {formatCurrency(lastYear?.totalInvested || 0)}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-virtus-bg-tertiary border border-virtus-border-primary">
                  <p className="text-xs text-virtus-text-muted mb-1">Retorno Total</p>
                  <p className={cn(
                    'text-lg font-semibold',
                    totalReturn >= 0 ? 'text-virtus-accent-success' : 'text-virtus-accent-danger'
                  )}>
                    {totalReturn.toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
            
            {/* Projections Table */}
            <div>
              <h3 className="text-sm font-semibold text-virtus-text-secondary mb-3">
                Projeção Anual
              </h3>
              
              <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-virtus-bg-card">
                    <tr className="border-b border-virtus-border-primary">
                      <th className="text-left py-2 px-2 text-virtus-text-muted font-medium">Ano</th>
                      <th className="text-right py-2 px-2 text-virtus-text-muted font-medium">Cotas</th>
                      <th className="text-right py-2 px-2 text-virtus-text-muted font-medium">Valor</th>
                      <th className="text-right py-2 px-2 text-virtus-text-muted font-medium">Dividendos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {projections.map((row) => (
                      <tr 
                        key={row.year}
                        className="border-b border-virtus-border-primary/30 hover:bg-virtus-bg-tertiary/30"
                      >
                        <td className="py-2 px-2 text-virtus-text-primary">{row.year}</td>
                        <td className="py-2 px-2 text-right text-virtus-text-secondary">
                          {row.shares.toFixed(0)}
                        </td>
                        <td className="py-2 px-2 text-right text-virtus-text-primary font-medium">
                          {formatCurrency(row.value)}
                        </td>
                        <td className="py-2 px-2 text-right text-virtus-accent-success">
                          {formatCurrency(row.dividends)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-virtus-border-primary bg-virtus-bg-tertiary/50">
          <p className="text-xs text-virtus-text-muted text-center">
            * Projeção simplificada. Resultados reais podem variar.
          </p>
        </div>
      </div>
    </div>
  )
}
