/**
 * Store para alertas de preço
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type AlertCondition = 'above' | 'below' | 'change_up' | 'change_down'

export interface PriceAlert {
  id: string
  symbol: string
  name: string
  condition: AlertCondition
  targetPrice: number
  currentPrice?: number
  isActive: boolean
  createdAt: string
  triggeredAt?: string
}

interface AlertsState {
  alerts: PriceAlert[]
  addAlert: (alert: Omit<PriceAlert, 'id' | 'createdAt' | 'isActive'>) => void
  removeAlert: (id: string) => void
  toggleAlert: (id: string) => void
  triggerAlert: (id: string) => void
  updateCurrentPrice: (symbol: string, price: number) => void
  getActiveAlerts: () => PriceAlert[]
  getAlertsBySymbol: (symbol: string) => PriceAlert[]
  clearTriggeredAlerts: () => void
}

export const useAlertsStore = create<AlertsState>()(
  persist(
    (set, get) => ({
      alerts: [],
      
      addAlert: (alert) => {
        const newAlert: PriceAlert = {
          ...alert,
          id: `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          createdAt: new Date().toISOString(),
          isActive: true,
        }
        set({ alerts: [...get().alerts, newAlert] })
      },
      
      removeAlert: (id) => {
        set({ alerts: get().alerts.filter(a => a.id !== id) })
      },
      
      toggleAlert: (id) => {
        set({
          alerts: get().alerts.map(a =>
            a.id === id ? { ...a, isActive: !a.isActive } : a
          )
        })
      },
      
      triggerAlert: (id) => {
        set({
          alerts: get().alerts.map(a =>
            a.id === id ? { ...a, isActive: false, triggeredAt: new Date().toISOString() } : a
          )
        })
      },
      
      updateCurrentPrice: (symbol, price) => {
        const alerts = get().alerts
        const updatedAlerts = alerts.map(a => {
          if (a.symbol === symbol) {
            return { ...a, currentPrice: price }
          }
          return a
        })
        set({ alerts: updatedAlerts })
      },
      
      getActiveAlerts: () => {
        return get().alerts.filter(a => a.isActive)
      },
      
      getAlertsBySymbol: (symbol) => {
        return get().alerts.filter(a => a.symbol === symbol)
      },
      
      clearTriggeredAlerts: () => {
        set({ alerts: get().alerts.filter(a => a.isActive) })
      },
    }),
    {
      name: 'virtus-alerts',
    }
  )
)

// Função para verificar se um alerta foi acionado
export function checkAlert(alert: PriceAlert, currentPrice: number): boolean {
  if (!alert.isActive) return false
  
  switch (alert.condition) {
    case 'above':
      return currentPrice >= alert.targetPrice
    case 'below':
      return currentPrice <= alert.targetPrice
    case 'change_up':
      // Variação percentual positiva
      if (alert.currentPrice) {
        const change = ((currentPrice - alert.currentPrice) / alert.currentPrice) * 100
        return change >= alert.targetPrice
      }
      return false
    case 'change_down':
      // Variação percentual negativa
      if (alert.currentPrice) {
        const change = ((currentPrice - alert.currentPrice) / alert.currentPrice) * 100
        return change <= -alert.targetPrice
      }
      return false
    default:
      return false
  }
}

// Labels para condições
export const alertConditionLabels: Record<AlertCondition, string> = {
  above: 'Acima de',
  below: 'Abaixo de',
  change_up: 'Subir %',
  change_down: 'Cair %',
}
