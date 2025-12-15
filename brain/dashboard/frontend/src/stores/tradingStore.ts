import { create } from 'zustand'

interface Metrics {
  balance: number
  equity: number
  margin: number
  freeMargin: number
  marginLevel: number
  profit: number
  dailyPnl: number
  weeklyPnl: number
  monthlyPnl: number
  totalTrades: number
  winningTrades: number
  losingTrades: number
  winRate: number
  profitFactor: number
  maxDrawdown: number
  currentDrawdown: number
  sharpeRatio: number
  activePositions: number
}

interface Position {
  ticket: number
  symbol: string
  type: 'BUY' | 'SELL'
  volume: number
  entryPrice: number
  currentPrice: number
  sl: number
  tp: number
  profit: number
  openTime: string
  swap: number
  commission: number
}

interface Order {
  ticket: number
  symbol: string
  type: string
  volume: number
  price: number
  sl: number
  tp: number
  expiration: string | null
}

interface TradingState {
  metrics: Metrics | null
  positions: Position[]
  orders: Order[]
  isConnected: boolean
  lastUpdate: Date | null
  
  updateMetrics: (metrics: Partial<Metrics>) => void
  setPositions: (positions: Position[]) => void
  setOrders: (orders: Order[]) => void
  setConnected: (connected: boolean) => void
}

const defaultMetrics: Metrics = {
  balance: 0,
  equity: 0,
  margin: 0,
  freeMargin: 0,
  marginLevel: 0,
  profit: 0,
  dailyPnl: 0,
  weeklyPnl: 0,
  monthlyPnl: 0,
  totalTrades: 0,
  winningTrades: 0,
  losingTrades: 0,
  winRate: 0,
  profitFactor: 0,
  maxDrawdown: 0,
  currentDrawdown: 0,
  sharpeRatio: 0,
  activePositions: 0,
}

export const useTradingStore = create<TradingState>((set) => ({
  metrics: defaultMetrics,
  positions: [],
  orders: [],
  isConnected: false,
  lastUpdate: null,
  
  updateMetrics: (newMetrics) => 
    set((state) => ({
      metrics: state.metrics ? { ...state.metrics, ...newMetrics } : { ...defaultMetrics, ...newMetrics },
      lastUpdate: new Date(),
    })),
  
  setPositions: (positions) => set({ positions, lastUpdate: new Date() }),
  
  setOrders: (orders) => set({ orders, lastUpdate: new Date() }),
  
  setConnected: (connected) => set({ isConnected: connected }),
}))
