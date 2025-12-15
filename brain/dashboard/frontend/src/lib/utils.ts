import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatNumber(value: number, decimals: number = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatPercent(value: number, decimals: number = 2): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`
}

export function formatDate(date: string | Date, format: 'short' | 'long' | 'time' = 'short'): string {
  const d = new Date(date)
  
  switch (format) {
    case 'short':
      return d.toLocaleDateString('pt-BR')
    case 'long':
      return d.toLocaleDateString('pt-BR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    case 'time':
      return d.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    default:
      return d.toLocaleDateString('pt-BR')
  }
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${minutes}m`
}

export function getTradeTypeColor(type: string): string {
  return type.toUpperCase().includes('BUY') 
    ? 'text-virtus-accent-success' 
    : 'text-virtus-accent-danger'
}

export function getPnLColor(value: number): string {
  if (value > 0) return 'text-virtus-accent-success'
  if (value < 0) return 'text-virtus-accent-danger'
  return 'text-virtus-text-secondary'
}

export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'running':
    case 'active':
    case 'online':
    case 'connected':
      return 'text-virtus-accent-success'
    case 'stopped':
    case 'inactive':
    case 'offline':
    case 'disconnected':
      return 'text-virtus-accent-danger'
    case 'paused':
    case 'pending':
      return 'text-virtus-accent-warning'
    default:
      return 'text-virtus-text-secondary'
  }
}

export function getStatusBadge(status: string): string {
  switch (status.toLowerCase()) {
    case 'running':
    case 'active':
    case 'online':
    case 'connected':
      return 'badge-success'
    case 'stopped':
    case 'inactive':
    case 'offline':
    case 'disconnected':
      return 'badge-danger'
    case 'paused':
    case 'pending':
      return 'badge-warning'
    default:
      return 'badge-info'
  }
}

export function calculateWinRate(wins: number, total: number): number {
  if (total === 0) return 0
  return (wins / total) * 100
}

export function calculateProfitFactor(grossProfit: number, grossLoss: number): number {
  if (grossLoss === 0) return grossProfit > 0 ? Infinity : 0
  return Math.abs(grossProfit / grossLoss)
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}
