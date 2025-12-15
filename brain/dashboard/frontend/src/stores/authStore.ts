import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../services/api'

interface User {
  username: string
  name: string
  role: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  login: (username: string, password: string) => Promise<boolean>
  logout: () => void
  refreshAccessToken: () => Promise<boolean>
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      
      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        
        try {
          const response = await api.post('/api/auth/login', { username, password })
          const { access_token, refresh_token, user } = response.data
          
          set({
            user,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
          })
          
          return true
        } catch (error: any) {
          const message = error.response?.data?.detail || 'Falha ao fazer login'
          set({ error: message, isLoading: false })
          return false
        }
      },
      
      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        })
      },
      
      refreshAccessToken: async () => {
        const { refreshToken } = get()
        
        if (!refreshToken) {
          get().logout()
          return false
        }
        
        try {
          const response = await api.post('/api/auth/refresh', { refresh_token: refreshToken })
          const { access_token } = response.data
          
          set({ accessToken: access_token })
          return true
        } catch {
          get().logout()
          return false
        }
      },
      
      clearError: () => set({ error: null }),
    }),
    {
      name: 'virtus-auth',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
