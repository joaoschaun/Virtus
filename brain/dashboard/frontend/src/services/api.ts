import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../stores/authStore'

const API_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - adiciona token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - trata erros e refresh token
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    
    // Se erro 401 e não é retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      const refreshSuccess = await useAuthStore.getState().refreshAccessToken()
      
      if (refreshSuccess) {
        const newToken = useAuthStore.getState().accessToken
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
        }
        return api(originalRequest)
      }
    }
    
    return Promise.reject(error)
  }
)

// ==================== API ENDPOINTS ====================

export const authAPI = {
  login: (username: string, password: string) => 
    api.post('/api/auth/login', { username, password }),
  
  logout: () => api.post('/api/auth/logout'),
  
  me: () => api.get('/api/auth/me'),
  
  refresh: (refreshToken: string) => 
    api.post('/api/auth/refresh', { refresh_token: refreshToken }),
  
  changePassword: (currentPassword: string, newPassword: string, confirmPassword: string) =>
    api.post('/api/auth/change-password', { 
      current_password: currentPassword, 
      new_password: newPassword, 
      confirm_password: confirmPassword 
    }),
}

export const dashboardAPI = {
  getOverview: () => api.get('/api/dashboard/overview'),
  
  getMetrics: () => api.get('/api/dashboard/metrics'),
  
  getEquityHistory: (days: number = 30) => 
    api.get(`/api/dashboard/equity-history?days=${days}`),
}

export const botsAPI = {
  list: () => api.get('/api/bots'),
  
  get: (botId: string) => api.get(`/api/bots/${botId}`),
  
  control: (botId: string, action: string) => 
    api.post(`/api/bots/${botId}/control`, { bot_id: botId, action }),
  
  updateConfig: (botId: string, config: any) => 
    api.put(`/api/bots/${botId}/config`, config),
}

export const strategiesAPI = {
  list: () => api.get('/api/strategies'),
  
  toggle: (strategyName: string, enabled: boolean) => 
    api.post(`/api/strategies/${strategyName}/toggle`, { strategy_name: strategyName, enabled }),
}

export const symbolsAPI = {
  list: () => api.get('/api/symbols'),
  
  toggle: (symbol: string, enabled: boolean) => 
    api.post(`/api/symbols/${symbol}/toggle`, { symbol, enabled }),
  
  updateConfig: (symbol: string, config: any) => 
    api.put(`/api/symbols/${symbol}/config`, config),
}

export const positionsAPI = {
  list: () => api.get('/api/positions'),
  
  close: (ticket: number) => api.delete(`/api/positions/${ticket}`),
}

export const ordersAPI = {
  list: () => api.get('/api/orders'),
  
  cancel: (ticket: number) => api.delete(`/api/orders/${ticket}`),
}

export const tradesAPI = {
  list: (params?: {
    page?: number
    per_page?: number
    symbol?: string
    strategy?: string
    start_date?: string
    end_date?: string
  }) => api.get('/api/trades', { params }),
  
  getStats: (days: number = 30) => api.get(`/api/trades/stats?days=${days}`),
}

export const analysisAPI = {
  getPerformance: (period: string = 'month') => 
    api.get(`/api/analysis/performance?period=${period}`),
  
  getAttribution: () => api.get('/api/analysis/attribution'),
}

export const settingsAPI = {
  get: () => api.get('/api/settings'),
  
  update: (settings: any) => api.put('/api/settings', settings),
}

export const systemAPI = {
  getStatus: () => api.get('/api/system/status'),
  
  getLogs: (level: string = 'all', limit: number = 100) => 
    api.get(`/api/system/logs?level=${level}&limit=${limit}`),
}

export const mt5API = {
  getStatus: () => api.get('/api/mt5/status'),
  
  connect: (credentials?: { login: number; password: string; server: string }) => 
    api.post('/api/mt5/connect', credentials),
  
  disconnect: () => api.post('/api/mt5/disconnect'),
  
  getAccount: () => api.get('/api/mt5/account'),
  
  getPositions: () => api.get('/api/mt5/positions'),
  
  getOrders: () => api.get('/api/mt5/orders'),
  
  getHistory: (days: number = 30, symbol?: string) => {
    const params = new URLSearchParams({ days: days.toString() })
    if (symbol) params.append('symbol', symbol)
    return api.get(`/api/mt5/history?${params}`)
  },
  
  sync: (days: number = 30, symbol?: string) => 
    api.post('/api/mt5/sync', { days, symbol }),
  
  getSymbols: () => api.get('/api/mt5/symbols'),
  
  getSymbolInfo: (symbol: string) => api.get(`/api/mt5/symbol/${symbol}`),
}

export default api
