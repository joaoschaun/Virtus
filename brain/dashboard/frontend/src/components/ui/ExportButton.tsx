/**
 * Botão de exportação com dropdown
 */

import { useState, useRef, useEffect } from 'react'
import { Download, FileSpreadsheet, FileText, FileJson, ChevronDown } from 'lucide-react'
import { cn } from '../../lib/utils'

interface ExportButtonProps {
  onExportCSV: () => void
  onExportPDF: () => void
  onExportJSON?: () => void
  className?: string
  disabled?: boolean
}

export function ExportButton({ 
  onExportCSV, 
  onExportPDF, 
  onExportJSON,
  className,
  disabled 
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Fechar ao clicar fora
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleExport = (type: 'csv' | 'pdf' | 'json') => {
    switch (type) {
      case 'csv':
        onExportCSV()
        break
      case 'pdf':
        onExportPDF()
        break
      case 'json':
        onExportJSON?.()
        break
    }
    setIsOpen(false)
  }

  return (
    <div className={cn('relative', className)} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className={cn(
          'flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors',
          'bg-virtus-bg-tertiary hover:bg-virtus-bg-tertiary/80 border border-virtus-border',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <Download className="w-4 h-4" />
        <span>Exportar</span>
        <ChevronDown className={cn(
          'w-4 h-4 transition-transform',
          isOpen && 'rotate-180'
        )} />
      </button>
      
      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-virtus-bg-secondary border border-virtus-border rounded-lg shadow-xl z-50 overflow-hidden animate-fadeIn">
          <button
            onClick={() => handleExport('csv')}
            className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-virtus-bg-tertiary transition-colors"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-500" />
            <span className="text-sm">Exportar CSV</span>
          </button>
          
          <button
            onClick={() => handleExport('pdf')}
            className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-virtus-bg-tertiary transition-colors"
          >
            <FileText className="w-4 h-4 text-red-500" />
            <span className="text-sm">Exportar PDF</span>
          </button>
          
          {onExportJSON && (
            <button
              onClick={() => handleExport('json')}
              className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-virtus-bg-tertiary transition-colors"
            >
              <FileJson className="w-4 h-4 text-amber-500" />
              <span className="text-sm">Exportar JSON</span>
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default ExportButton
