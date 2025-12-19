/**
 * Botão de Favorito (estrela)
 */

import { Star } from 'lucide-react'
import { useFavoritesStore, FavoriteItem } from '../../stores/favoritesStore'
import { cn } from '../../lib/utils'

interface FavoriteButtonProps {
  symbol: string
  name: string
  type: FavoriteItem['type']
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
}

export function FavoriteButton({ symbol, name, type, className, size = 'md' }: FavoriteButtonProps) {
  const { isFavorite, toggleFavorite } = useFavoritesStore()
  const favorited = isFavorite(symbol)

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    toggleFavorite({ symbol, name, type })
  }

  return (
    <button
      onClick={handleClick}
      className={cn(
        'p-1.5 rounded-lg transition-all',
        'hover:bg-virtus-bg-tertiary',
        'focus:outline-none focus:ring-2 focus:ring-amber-500/50',
        className
      )}
      title={favorited ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
    >
      <Star 
        className={cn(
          sizeClasses[size],
          'transition-all duration-200',
          favorited 
            ? 'fill-amber-500 text-amber-500 scale-110' 
            : 'text-virtus-text-muted hover:text-amber-500'
        )} 
      />
    </button>
  )
}

export default FavoriteButton
