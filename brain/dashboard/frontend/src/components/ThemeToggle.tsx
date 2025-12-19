import { Sun, Moon } from 'lucide-react'
import { useThemeStore } from '../stores/themeStore'

export default function ThemeToggle() {
  const { theme, toggleTheme } = useThemeStore()
  
  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg bg-virtus-bg-tertiary border border-virtus-border-primary hover:border-virtus-text-muted transition-all group"
      title={theme === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
    >
      {theme === 'dark' ? (
        <Sun className="w-5 h-5 text-virtus-text-muted group-hover:text-yellow-400 transition-colors" />
      ) : (
        <Moon className="w-5 h-5 text-virtus-text-muted group-hover:text-blue-400 transition-colors" />
      )}
    </button>
  )
}
