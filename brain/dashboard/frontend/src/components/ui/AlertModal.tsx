/**
 * Modal de Alerta de Preço
 */

import { useState } from 'react'
import { X, Bell, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react'
import { useAlertsStore, AlertCondition, alertConditionLabels } from '../../stores/alertsStore'
import { cn } from '../../lib/utils'
import { useToast } from './Toast'

interface CreateAlertModalProps {
  isOpen: boolean
  onClose: () => void
  symbol?: string
  name?: string
  currentPrice?: number
}

export function CreateAlertModal({ isOpen, onClose, symbol = '', name = '', currentPrice }: CreateAlertModalProps) {
  const [alertSymbol, setAlertSymbol] = useState(symbol)
  const [alertName, setAlertName] = useState(name)
  const [condition, setCondition] = useState<AlertCondition>('above')
  const [targetPrice, setTargetPrice] = useState(currentPrice?.toString() || '')
  
  const { addAlert } = useAlertsStore()
  const toast = useToast()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!alertSymbol || !targetPrice) {
      toast.error('Preencha todos os campos')
      return
    }

    addAlert({
      symbol: alertSymbol.toUpperCase(),
      name: alertName || alertSymbol.toUpperCase(),
      condition,
      targetPrice: parseFloat(targetPrice),
      currentPrice,
    })

    toast.success(`Alerta criado para ${alertSymbol.toUpperCase()}`)
    onClose()
    
    // Reset form
    setAlertSymbol('')
    setAlertName('')
    setTargetPrice('')
    setCondition('above')
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-md bg-virtus-bg-secondary border border-virtus-border rounded-xl shadow-2xl animate-fadeIn">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-virtus-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/20 rounded-lg">
              <Bell className="w-5 h-5 text-amber-500" />
            </div>
            <h2 className="text-lg font-semibold">Criar Alerta de Preço</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-virtus-bg-tertiary rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Símbolo */}
          <div>
            <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
              Símbolo do Ativo
            </label>
            <input
              type="text"
              value={alertSymbol}
              onChange={(e) => setAlertSymbol(e.target.value.toUpperCase())}
              placeholder="Ex: PETR4, VALE3, BTC"
              className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
            />
          </div>
          
          {/* Nome (opcional) */}
          <div>
            <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
              Nome (opcional)
            </label>
            <input
              type="text"
              value={alertName}
              onChange={(e) => setAlertName(e.target.value)}
              placeholder="Ex: Petrobras PN"
              className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
            />
          </div>
          
          {/* Condição */}
          <div>
            <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
              Condição
            </label>
            <div className="grid grid-cols-2 gap-2">
              {(Object.keys(alertConditionLabels) as AlertCondition[]).map((cond) => (
                <button
                  key={cond}
                  type="button"
                  onClick={() => setCondition(cond)}
                  className={cn(
                    'flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border transition-all',
                    condition === cond
                      ? 'bg-virtus-primary/20 border-virtus-primary text-virtus-primary'
                      : 'bg-virtus-bg-tertiary border-virtus-border hover:border-virtus-primary/50'
                  )}
                >
                  {cond === 'above' || cond === 'change_up' ? (
                    <TrendingUp className="w-4 h-4" />
                  ) : (
                    <TrendingDown className="w-4 h-4" />
                  )}
                  <span className="text-sm">{alertConditionLabels[cond]}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Preço/Percentual Alvo */}
          <div>
            <label className="block text-sm font-medium text-virtus-text-secondary mb-1.5">
              {condition.includes('change') ? 'Variação (%)' : 'Preço Alvo (R$)'}
            </label>
            <input
              type="number"
              step="0.01"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
              placeholder={condition.includes('change') ? 'Ex: 5' : 'Ex: 35.50'}
              className="w-full px-4 py-2.5 bg-virtus-bg-tertiary border border-virtus-border rounded-lg focus:outline-none focus:ring-2 focus:ring-virtus-primary/50"
            />
          </div>
          
          {/* Info */}
          {currentPrice && (
            <div className="flex items-center gap-2 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <AlertCircle className="w-4 h-4 text-blue-500" />
              <span className="text-sm text-blue-400">
                Preço atual: R$ {currentPrice.toFixed(2)}
              </span>
            </div>
          )}
          
          {/* Submit */}
          <button
            type="submit"
            className="w-full py-3 bg-virtus-primary hover:bg-virtus-primary/80 text-white font-medium rounded-lg transition-colors"
          >
            Criar Alerta
          </button>
        </form>
      </div>
    </div>
  )
}

// Lista de alertas ativos
interface AlertsListProps {
  className?: string
}

export function AlertsList({ className }: AlertsListProps) {
  const { alerts, removeAlert, toggleAlert } = useAlertsStore()
  
  if (alerts.length === 0) {
    return (
      <div className={cn('text-center py-8', className)}>
        <Bell className="w-12 h-12 mx-auto mb-3 text-virtus-text-muted opacity-50" />
        <p className="text-virtus-text-muted">Nenhum alerta configurado</p>
        <p className="text-sm text-virtus-text-muted mt-1">
          Crie alertas para ser notificado quando ativos atingirem determinados preços
        </p>
      </div>
    )
  }
  
  return (
    <div className={cn('space-y-2', className)}>
      {alerts.map((alert) => (
        <div 
          key={alert.id}
          className={cn(
            'flex items-center justify-between p-3 rounded-lg border transition-colors',
            alert.isActive 
              ? 'bg-virtus-bg-tertiary border-virtus-border' 
              : 'bg-virtus-bg-tertiary/50 border-virtus-border/50 opacity-60'
          )}
        >
          <div className="flex items-center gap-3">
            <div className={cn(
              'p-2 rounded-lg',
              alert.condition === 'above' || alert.condition === 'change_up'
                ? 'bg-green-500/20'
                : 'bg-red-500/20'
            )}>
              {alert.condition === 'above' || alert.condition === 'change_up' ? (
                <TrendingUp className="w-4 h-4 text-green-500" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500" />
              )}
            </div>
            <div>
              <p className="font-medium">{alert.symbol}</p>
              <p className="text-xs text-virtus-text-muted">
                {alertConditionLabels[alert.condition]} {' '}
                {alert.condition.includes('change') ? `${alert.targetPrice}%` : `R$ ${alert.targetPrice.toFixed(2)}`}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => toggleAlert(alert.id)}
              className={cn(
                'px-3 py-1 text-xs rounded-full transition-colors',
                alert.isActive 
                  ? 'bg-green-500/20 text-green-500' 
                  : 'bg-gray-500/20 text-gray-500'
              )}
            >
              {alert.isActive ? 'Ativo' : 'Pausado'}
            </button>
            <button
              onClick={() => removeAlert(alert.id)}
              className="p-1.5 hover:bg-red-500/20 hover:text-red-500 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export default CreateAlertModal
