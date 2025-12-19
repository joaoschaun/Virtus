import { X, Command, ArrowUp } from 'lucide-react'

interface KeyboardShortcutsHelpProps {
  isOpen: boolean
  onClose: () => void
}

const shortcuts = [
  {
    category: 'Geral',
    items: [
      { keys: ['Ctrl', 'K'], description: 'Abrir busca rápida' },
      { keys: ['Shift', '?'], description: 'Mostrar atalhos' },
      { keys: ['ESC'], description: 'Fechar modal' },
    ]
  },
  {
    category: 'Navegação (G + Letra)',
    items: [
      { keys: ['G', 'D'], description: 'Ir para Dashboard' },
      { keys: ['G', 'M'], description: 'Ir para Visão Geral' },
      { keys: ['G', 'A'], description: 'Ir para Ações' },
      { keys: ['G', 'F'], description: 'Ir para FIIs' },
      { keys: ['G', 'C'], description: 'Ir para Criptomoedas' },
      { keys: ['G', 'I'], description: 'Ir para Dividendos' },
      { keys: ['G', 'S'], description: 'Ir para Configurações' },
      { keys: ['G', 'B'], description: 'Ir para Bots' },
      { keys: ['G', 'P'], description: 'Ir para Posições' },
    ]
  },
  {
    category: 'Ações Rápidas',
    items: [
      { keys: ['N'], description: 'Nova operação (em breve)' },
      { keys: ['R'], description: 'Atualizar dados (em breve)' },
    ]
  }
]

export default function KeyboardShortcutsHelp({ isOpen, onClose }: KeyboardShortcutsHelpProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-virtus-bg-card border border-virtus-border-primary rounded-xl shadow-2xl overflow-hidden animate-slideDown">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-virtus-border-primary">
          <h2 className="text-lg font-semibold text-virtus-text-primary">
            Atalhos de Teclado
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-virtus-bg-tertiary transition-colors"
          >
            <X className="w-5 h-5 text-virtus-text-muted" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {shortcuts.map((section) => (
              <div key={section.category}>
                <h3 className="text-sm font-semibold text-virtus-text-secondary mb-3">
                  {section.category}
                </h3>
                <div className="space-y-2">
                  {section.items.map((shortcut, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between py-2 px-3 rounded-lg bg-virtus-bg-tertiary/50"
                    >
                      <span className="text-sm text-virtus-text-primary">
                        {shortcut.description}
                      </span>
                      <div className="flex items-center gap-1">
                        {shortcut.keys.map((key, keyIdx) => (
                          <span key={keyIdx}>
                            <kbd className="inline-flex items-center justify-center min-w-[24px] px-1.5 py-1 rounded bg-virtus-bg-secondary border border-virtus-border-primary text-xs font-medium text-virtus-text-muted">
                              {key === 'Ctrl' ? (
                                <Command className="w-3 h-3" />
                              ) : key === 'Shift' ? (
                                <ArrowUp className="w-3 h-3" />
                              ) : (
                                key
                              )}
                            </kbd>
                            {keyIdx < shortcut.keys.length - 1 && (
                              <span className="mx-0.5 text-virtus-text-muted">+</span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-virtus-border-primary bg-virtus-bg-tertiary/50">
          <p className="text-xs text-virtus-text-muted text-center">
            Pressione <kbd className="px-1 py-0.5 rounded bg-virtus-bg-secondary text-virtus-text-muted">ESC</kbd> para fechar
          </p>
        </div>
      </div>
    </div>
  )
}
