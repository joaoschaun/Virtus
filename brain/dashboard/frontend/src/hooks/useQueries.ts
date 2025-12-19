/**
 * React Query hooks para gerenciamento de dados
 * Fornece cache automático, revalidação e estados de loading
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dashboardAPI, botsAPI, systemAPI, mt5API } from '../services/api'
import brapiService from '../services/brapiService'

// Query Keys - centralizados para consistência
export const queryKeys = {
  // Dashboard
  dashboardOverview: ['dashboard', 'overview'] as const,
  dashboardMetrics: ['dashboard', 'metrics'] as const,
  equityHistory: (days: number) => ['dashboard', 'equity', days] as const,
  
  // Bots
  bots: ['bots'] as const,
  bot: (id: string) => ['bots', id] as const,
  
  // System
  systemStatus: ['system', 'status'] as const,
  systemLogs: (level?: string) => ['system', 'logs', level] as const,
  
  // MT5
  mt5Status: ['mt5', 'status'] as const,
  mt5Account: ['mt5', 'account'] as const,
  mt5Positions: ['mt5', 'positions'] as const,
  
  // Market (Brapi)
  ibovespa: ['market', 'ibovespa'] as const,
  currency: ['market', 'currency'] as const,
  crypto: (coins: string[]) => ['market', 'crypto', coins] as const,
  stocks: (symbols: string[]) => ['market', 'stocks', symbols] as const,
  fiis: ['market', 'fiis'] as const,
  topGainers: ['market', 'topGainers'] as const,
  topLosers: ['market', 'topLosers'] as const,
}

// ========================
// Dashboard Hooks
// ========================

export function useDashboardOverview() {
  return useQuery({
    queryKey: queryKeys.dashboardOverview,
    queryFn: async () => {
      const response = await dashboardAPI.getOverview()
      return response.data
    },
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  })
}

export function useDashboardMetrics() {
  return useQuery({
    queryKey: queryKeys.dashboardMetrics,
    queryFn: async () => {
      const response = await dashboardAPI.getMetrics()
      return response.data
    },
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  })
}

export function useEquityHistory(days = 30) {
  return useQuery({
    queryKey: queryKeys.equityHistory(days),
    queryFn: async () => {
      const response = await dashboardAPI.getEquityHistory(days)
      return response.data
    },
    staleTime: 5 * 60 * 1000, // 5 minutos
  })
}

// ========================
// Bots Hooks
// ========================

export function useBots() {
  return useQuery({
    queryKey: queryKeys.bots,
    queryFn: async () => {
      const response = await botsAPI.list()
      return response.data
    },
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
  })
}

export function useBot(id: string) {
  return useQuery({
    queryKey: queryKeys.bot(id),
    queryFn: async () => {
      const response = await botsAPI.get(id)
      return response.data
    },
    staleTime: 5 * 1000,
    enabled: !!id,
  })
}

export function useBotControl() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ botId, action }: { botId: string; action: string }) => {
      const response = await botsAPI.control(botId, action)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.bots })
    },
  })
}

// ========================
// System Hooks
// ========================

export function useSystemStatus() {
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: async () => {
      const response = await systemAPI.getStatus()
      return response.data
    },
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
  })
}

export function useSystemLogs(level = 'all', limit = 100) {
  return useQuery({
    queryKey: queryKeys.systemLogs(level),
    queryFn: async () => {
      const response = await systemAPI.getLogs(level, limit)
      return response.data
    },
    staleTime: 5 * 1000,
  })
}

// ========================
// MT5 Hooks
// ========================

export function useMT5Status() {
  return useQuery({
    queryKey: queryKeys.mt5Status,
    queryFn: async () => {
      const response = await mt5API.getStatus()
      return response.data
    },
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
  })
}

export function useMT5Account() {
  return useQuery({
    queryKey: queryKeys.mt5Account,
    queryFn: async () => {
      const response = await mt5API.getAccount()
      return response.data
    },
    staleTime: 30 * 1000,
  })
}

export function useMT5Positions() {
  return useQuery({
    queryKey: queryKeys.mt5Positions,
    queryFn: async () => {
      const response = await mt5API.getPositions()
      return response.data
    },
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
  })
}

// ========================
// Market Hooks (Brapi)
// ========================

export function useIbovespa() {
  return useQuery({
    queryKey: queryKeys.ibovespa,
    queryFn: () => brapiService.getIbovespa(),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  })
}

export function useCurrency(pairs = ['USD-BRL', 'EUR-BRL']) {
  return useQuery({
    queryKey: queryKeys.currency,
    queryFn: () => brapiService.getCurrencyQuote(pairs),
    staleTime: 60 * 1000,
    refetchInterval: 120 * 1000,
  })
}

export function useCrypto(coins = ['BTC', 'ETH']) {
  return useQuery({
    queryKey: queryKeys.crypto(coins),
    queryFn: () => brapiService.getCryptoQuote(coins),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  })
}

export function useStockQuotes(symbols: string[]) {
  return useQuery({
    queryKey: queryKeys.stocks(symbols),
    queryFn: () => brapiService.getQuote(symbols),
    staleTime: 30 * 1000,
    enabled: symbols.length > 0,
  })
}

export function useFIIs() {
  return useQuery({
    queryKey: queryKeys.fiis,
    queryFn: () => brapiService.searchFIIs(),
    staleTime: 5 * 60 * 1000, // 5 minutos
  })
}

export function useTopGainers() {
  return useQuery({
    queryKey: queryKeys.topGainers,
    queryFn: () => brapiService.getTopGainers(),
    staleTime: 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
  })
}

export function useTopLosers() {
  return useQuery({
    queryKey: queryKeys.topLosers,
    queryFn: () => brapiService.getTopLosers(),
    staleTime: 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
  })
}

// ========================
// Utility Hooks
// ========================

/**
 * Hook para invalidar cache manualmente
 */
export function useInvalidateQueries() {
  const queryClient = useQueryClient()
  
  return {
    invalidateAll: () => queryClient.invalidateQueries(),
    invalidateDashboard: () => queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
    invalidateBots: () => queryClient.invalidateQueries({ queryKey: ['bots'] }),
    invalidateMarket: () => queryClient.invalidateQueries({ queryKey: ['market'] }),
    invalidateSystem: () => queryClient.invalidateQueries({ queryKey: ['system'] }),
    invalidateMT5: () => queryClient.invalidateQueries({ queryKey: ['mt5'] }),
  }
}

/**
 * Hook para prefetch de dados
 */
export function usePrefetchData() {
  const queryClient = useQueryClient()
  
  return {
    prefetchDashboard: () => {
      queryClient.prefetchQuery({
        queryKey: queryKeys.dashboardOverview,
        queryFn: async () => {
          const response = await dashboardAPI.getOverview()
          return response.data
        },
      })
    },
    prefetchMarket: () => {
      queryClient.prefetchQuery({
        queryKey: queryKeys.ibovespa,
        queryFn: () => brapiService.getIbovespa(),
      })
    },
  }
}
