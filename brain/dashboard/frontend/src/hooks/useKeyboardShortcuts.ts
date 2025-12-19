/**
 * Hook para atalhos de teclado globais
 */

import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

interface KeyboardShortcut {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  action: () => void
  description: string
}

interface UseKeyboardShortcutsOptions {
  onOpenCommandPalette?: () => void
  onOpenShortcutsHelp?: () => void
  additionalShortcuts?: KeyboardShortcut[]
}

// Sequências de teclas (ex: G + D para Dashboard)
let keySequence: string[] = []
let sequenceTimeout: NodeJS.Timeout | null = null

export function useKeyboardShortcuts(options?: UseKeyboardShortcutsOptions) {
  const navigate = useNavigate()
  const { onOpenCommandPalette, onOpenShortcutsHelp, additionalShortcuts } = options || {}
  
  // Atalhos de navegação com sequência "G + letra"
  const handleKeySequence = useCallback((key: string) => {
    keySequence.push(key.toLowerCase())
    
    // Limpar sequência após 1 segundo
    if (sequenceTimeout) clearTimeout(sequenceTimeout)
    sequenceTimeout = setTimeout(() => {
      keySequence = []
    }, 1000)
    
    // Verificar sequências de 2 teclas
    if (keySequence.length >= 2) {
      const sequence = keySequence.slice(-2).join('')
      
      const sequences: Record<string, string> = {
        'gd': '/dashboard',      // G + D = Dashboard
        'gm': '/market-overview', // G + M = Mercado
        'ga': '/stocks',         // G + A = Ações
        'gf': '/fiis',           // G + F = FIIs
        'gc': '/crypto',         // G + C = Crypto
        'gv': '/dividends',      // G + V = Dividendos (V de Valor)
        'gi': '/dividends',      // G + I = Income/Dividendos
        'gs': '/settings',       // G + S = Settings
        'go': '/screener',       // G + O = Overview/Screener
        'gx': '/forex',          // G + X = Forex
        'gb': '/bots',           // G + B = Bots
        'gp': '/positions',      // G + P = Posições
      }
      
      if (sequences[sequence]) {
        navigate(sequences[sequence])
        keySequence = []
      }
    }
  }, [navigate])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignorar se estiver digitando em input/textarea
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return
      }
      
      // Ctrl+K para busca global
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        onOpenCommandPalette?.()
        return
      }
      
      // Atalho ? para mostrar ajuda
      if (e.key === '?' && e.shiftKey) {
        e.preventDefault()
        onOpenShortcutsHelp?.()
        return
      }
      
      // Sequências de navegação
      if (e.key.length === 1 && /[a-z]/i.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) {
        handleKeySequence(e.key)
      }
      
      // Atalhos adicionais
      additionalShortcuts?.forEach(shortcut => {
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase()
        const ctrlMatch = shortcut.ctrl ? (e.ctrlKey || e.metaKey) : !e.ctrlKey && !e.metaKey
        const shiftMatch = shortcut.shift ? e.shiftKey : !e.shiftKey
        const altMatch = shortcut.alt ? e.altKey : !e.altKey
        
        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          e.preventDefault()
          shortcut.action()
        }
      })
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeySequence, additionalShortcuts, onOpenCommandPalette, onOpenShortcutsHelp])
}

// Lista de todos os atalhos para exibição
export const keyboardShortcutsList = [
  { keys: ['Ctrl', 'K'], description: 'Abrir busca global' },
  { keys: ['?'], description: 'Mostrar atalhos de teclado' },
  { keys: ['G', 'D'], description: 'Ir para Dashboard' },
  { keys: ['G', 'M'], description: 'Ir para Mercado' },
  { keys: ['G', 'A'], description: 'Ir para Ações' },
  { keys: ['G', 'F'], description: 'Ir para FIIs' },
  { keys: ['G', 'C'], description: 'Ir para Crypto' },
  { keys: ['G', 'V'], description: 'Ir para Dividendos' },
  { keys: ['G', 'S'], description: 'Ir para Screener' },
  { keys: ['G', 'B'], description: 'Ir para Bots' },
  { keys: ['G', 'O'], description: 'Ir para Configurações' },
  { keys: ['Esc'], description: 'Fechar modal/dropdown' },
]

export default useKeyboardShortcuts
