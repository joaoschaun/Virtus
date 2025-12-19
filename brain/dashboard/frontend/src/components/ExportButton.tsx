import { useState, useRef, useEffect } from 'react'
import { Download, FileJson, FileSpreadsheet, FileText, ChevronDown } from 'lucide-react'
import { cn } from '../lib/utils'

interface ExportButtonProps {
  data: any[]
  filename: string
  columns?: { key: string; label: string }[]
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const sizeClasses = {
  sm: 'px-2 py-1 text-xs',
  md: 'px-3 py-1.5 text-sm',
  lg: 'px-4 py-2 text-base'
}

export default function ExportButton({ 
  data, 
  filename, 
  columns,
  className,
  size = 'md'
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])
  
  const exportToCSV = () => {
    if (!data || data.length === 0) return
    
    const headers = columns 
      ? columns.map(c => c.label)
      : Object.keys(data[0])
    
    const keys = columns 
      ? columns.map(c => c.key)
      : Object.keys(data[0])
    
    const csvContent = [
      headers.join(','),
      ...data.map(row => 
        keys.map(key => {
          const value = row[key]
          // Escape values with commas or quotes
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`
          }
          return value ?? ''
        }).join(',')
      )
    ].join('\n')
    
    downloadFile(csvContent, `${filename}.csv`, 'text/csv')
    setIsOpen(false)
  }
  
  const exportToJSON = () => {
    if (!data || data.length === 0) return
    
    const jsonContent = JSON.stringify(data, null, 2)
    downloadFile(jsonContent, `${filename}.json`, 'application/json')
    setIsOpen(false)
  }
  
  const exportToTXT = () => {
    if (!data || data.length === 0) return
    
    const headers = columns 
      ? columns.map(c => c.label)
      : Object.keys(data[0])
    
    const keys = columns 
      ? columns.map(c => c.key)
      : Object.keys(data[0])
    
    const maxLengths = headers.map((h, i) => {
      const values = data.map(row => String(row[keys[i]] ?? '').length)
      return Math.max(h.length, ...values)
    })
    
    const separator = maxLengths.map(l => '-'.repeat(l + 2)).join('+')
    
    const txtContent = [
      separator,
      '| ' + headers.map((h, i) => h.padEnd(maxLengths[i])).join(' | ') + ' |',
      separator,
      ...data.map(row => 
        '| ' + keys.map((key, i) => 
          String(row[key] ?? '').padEnd(maxLengths[i])
        ).join(' | ') + ' |'
      ),
      separator
    ].join('\n')
    
    downloadFile(txtContent, `${filename}.txt`, 'text/plain')
    setIsOpen(false)
  }
  
  const downloadFile = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type: `${type};charset=utf-8;` })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }
  
  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-1.5 rounded-lg transition-all',
          'bg-virtus-bg-tertiary border border-virtus-border-primary',
          'hover:border-virtus-text-muted text-virtus-text-secondary',
          sizeClasses[size],
          className
        )}
      >
        <Download className="w-4 h-4" />
        <span>Exportar</span>
        <ChevronDown className={cn('w-3 h-3 transition-transform', isOpen && 'rotate-180')} />
      </button>
      
      {isOpen && (
        <div className="absolute right-0 mt-1 w-40 bg-virtus-bg-card border border-virtus-border-primary rounded-lg shadow-lg py-1 z-50 animate-slideDown">
          <button
            onClick={exportToCSV}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-virtus-text-primary hover:bg-virtus-bg-tertiary transition-colors"
          >
            <FileSpreadsheet className="w-4 h-4 text-green-500" />
            <span>CSV</span>
          </button>
          <button
            onClick={exportToJSON}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-virtus-text-primary hover:bg-virtus-bg-tertiary transition-colors"
          >
            <FileJson className="w-4 h-4 text-blue-500" />
            <span>JSON</span>
          </button>
          <button
            onClick={exportToTXT}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-virtus-text-primary hover:bg-virtus-bg-tertiary transition-colors"
          >
            <FileText className="w-4 h-4 text-gray-500" />
            <span>TXT</span>
          </button>
        </div>
      )}
    </div>
  )
}
