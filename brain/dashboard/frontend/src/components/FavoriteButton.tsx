import { Star } from 'lucide-react'
import { useFavoritesStore, FavoriteItem } from '../stores/favoritesStore'
import { cn } from '../lib/utils'

interface FavoriteButtonProps {
  symbol: string
  name: string
  type: FavoriteItem['type']
  size?: 'sm' | 'md' | 'lg'
  className?: string
  showLabel?: boolean
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6'
}

export default function FavoriteButton({ 
  symbol, 
  name, 
  type, 
  size = 'md', 
  className,
  showLabel = false 
}: FavoriteButtonProps) {
  const { isFavorite, toggleFavorite } = useFavoritesStore()
  const favorited = isFavorite(symbol)
  
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    toggleFavorite({ symbol, name, type })
  }
  
  return (
    <button
      onClick={handleClick}
      className={cn(
        'flex items-center gap-1 p-1.5 rounded-lg transition-all',
        'hover:bg-virtus-bg-tertiary',
        favorited 
          ? 'text-yellow-400 hover:text-yellow-500' 
          : 'text-virtus-text-muted hover:text-virtus-text-secondary',
        className
      )}
      title={favorited ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
    >
      <Star
        className={cn(
          sizeClasses[size],
          'transition-all',
          favorited && 'fill-yellow-400'
        )}
      />
      {showLabel && (
        <span className="text-xs">
          {favorited ? 'Favorito' : 'Favoritar'}
        </span>
      )}
    </button>
  )
}
