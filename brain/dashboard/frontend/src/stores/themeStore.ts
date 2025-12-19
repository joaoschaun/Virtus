/**
 * Store para gerenciamento de tema (Dark/Light)
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'dark' | 'light'

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      
      setTheme: (theme) => {
        set({ theme })
        applyTheme(theme)
      },
      
      toggleTheme: () => {
        const newTheme = get().theme === 'dark' ? 'light' : 'dark'
        set({ theme: newTheme })
        applyTheme(newTheme)
      },
    }),
    {
      name: 'virtus-theme',
      onRehydrateStorage: () => (state) => {
        if (state) {
          applyTheme(state.theme)
        }
      },
    }
  )
)

// Aplica o tema no documento
function applyTheme(theme: Theme) {
  const root = document.documentElement
  
  if (theme === 'dark') {
    root.classList.add('dark')
    root.classList.remove('light')
  } else {
    root.classList.add('light')
    root.classList.remove('dark')
  }
}

// Inicializa tema no carregamento
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('virtus-theme')
  if (stored) {
    try {
      const { state } = JSON.parse(stored)
      applyTheme(state.theme)
    } catch {
      applyTheme('dark')
    }
  }
}
