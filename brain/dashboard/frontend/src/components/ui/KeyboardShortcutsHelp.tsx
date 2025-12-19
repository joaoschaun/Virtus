/**
 * Modal de ajuda com atalhos de teclado
 */

import { useState, useEffect } from 'react'
import { X, Keyboard } from 'lucide-react'
import { keyboardShortcutsList } from '../../hooks/useKeyboardShortcuts'

interface KeyboardShortcutsHelpProps {
  isOpen: boolean
  onClose: () => void
}

export function KeyboardShortcutsHelp({ isOpen, onClose }: KeyboardShortcutsHelpProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-md bg-virtus-bg-secondary border border-virtus-border rounded-xl shadow-2xl animate-fadeIn">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-virtus-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-virtus-primary/20 rounded-lg">
              <Keyboard className="w-5 h-5 text-virtus-primary" />
            </div>
            <h2 className="text-lg font-semibold">Atalhos de Teclado</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-virtus-bg-tertiary rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          <div className="space-y-3">
            {keyboardShortcutsList.map((shortcut, index) => (
              <div 
                key={index}
                className="flex items-center justify-between py-2 border-b border-virtus-border/50 last:border-0"
              >
                <span className="text-sm text-virtus-text-secondary">
                  {shortcut.description}
                </span>
                <div className="flex items-center gap-1">
                  {shortcut.keys.map((key, i) => (
                    <span key={i}>
                      <kbd className="px-2 py-1 text-xs font-mono bg-virtus-bg-tertiary border border-virtus-border rounded">
                        {key}
                      </kbd>
                      {i < shortcut.keys.length - 1 && (
                        <span className="mx-1 text-virtus-text-muted">+</span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-6 p-3 bg-virtus-bg-tertiary rounded-lg">
            <p className="text-xs text-virtus-text-muted">
              <strong>Dica:</strong> Para navegação com G + letra, pressione G e depois a letra rapidamente (dentro de 1 segundo).
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// Hook para controlar o modal de atalhos
export function useShortcutsHelp() {
  const [isOpen, setIsOpen] = useState(false)
  
  useEffect(() => {
    const handleShowHelp = () => setIsOpen(true)
    window.addEventListener('show-shortcuts-help', handleShowHelp)
    return () => window.removeEventListener('show-shortcuts-help', handleShowHelp)
  }, [])
  
  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
  }
}

export default KeyboardShortcutsHelp
