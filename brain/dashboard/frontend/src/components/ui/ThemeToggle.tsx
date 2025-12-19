/**
 * Toggle de tema Dark/Light
 */

import { Moon, Sun } from 'lucide-react'
import { useThemeStore } from '../../stores/themeStore'
import { cn } from '../../lib/utils'

interface ThemeToggleProps {
  className?: string
  showLabel?: boolean
}

export function ThemeToggle({ className, showLabel = false }: ThemeToggleProps) {
  const { theme, toggleTheme } = useThemeStore()
  const isDark = theme === 'dark'

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        'relative flex items-center gap-2 p-2 rounded-lg transition-all',
        'hover:bg-virtus-bg-tertiary',
        'focus:outline-none focus:ring-2 focus:ring-virtus-primary/50',
        className
      )}
      title={isDark ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
    >
      <div className="relative w-5 h-5">
        <Sun 
          className={cn(
            'absolute inset-0 w-5 h-5 transition-all duration-300',
            isDark 
              ? 'opacity-0 rotate-90 scale-0' 
              : 'opacity-100 rotate-0 scale-100 text-amber-500'
          )} 
        />
        <Moon 
          className={cn(
            'absolute inset-0 w-5 h-5 transition-all duration-300',
            isDark 
              ? 'opacity-100 rotate-0 scale-100 text-blue-400' 
              : 'opacity-0 -rotate-90 scale-0'
          )} 
        />
      </div>
      {showLabel && (
        <span className="text-sm text-virtus-text-secondary">
          {isDark ? 'Dark' : 'Light'}
        </span>
      )}
    </button>
  )
}

export default ThemeToggle
