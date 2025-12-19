/**
 * Store para gerenciamento de favoritos
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface FavoriteItem {
  symbol: string
  name: string
  type: 'stock' | 'fii' | 'crypto' | 'currency'
  addedAt: string
}

interface FavoritesState {
  favorites: FavoriteItem[]
  addFavorite: (item: Omit<FavoriteItem, 'addedAt'>) => void
  removeFavorite: (symbol: string) => void
  isFavorite: (symbol: string) => boolean
  toggleFavorite: (item: Omit<FavoriteItem, 'addedAt'>) => void
  clearFavorites: () => void
}

export const useFavoritesStore = create<FavoritesState>()(
  persist(
    (set, get) => ({
      favorites: [],
      
      addFavorite: (item) => {
        const exists = get().favorites.some(f => f.symbol === item.symbol)
        if (!exists) {
          set({
            favorites: [
              ...get().favorites,
              { ...item, addedAt: new Date().toISOString() }
            ]
          })
        }
      },
      
      removeFavorite: (symbol) => {
        set({
          favorites: get().favorites.filter(f => f.symbol !== symbol)
        })
      },
      
      isFavorite: (symbol) => {
        return get().favorites.some(f => f.symbol === symbol)
      },
      
      toggleFavorite: (item) => {
        if (get().isFavorite(item.symbol)) {
          get().removeFavorite(item.symbol)
        } else {
          get().addFavorite(item)
        }
      },
      
      clearFavorites: () => {
        set({ favorites: [] })
      },
    }),
    {
      name: 'virtus-favorites',
    }
  )
)
