/**
 * Utilitário para exportação de dados (PDF, Excel/CSV)
 */

// Exportar para CSV
export function exportToCSV(data: Record<string, unknown>[], filename: string, headers?: Record<string, string>) {
  if (!data || data.length === 0) {
    console.warn('No data to export')
    return
  }

  // Determinar colunas
  const columns = Object.keys(data[0])
  
  // Header row
  const headerRow = columns.map(col => headers?.[col] || col).join(',')
  
  // Data rows
  const dataRows = data.map(row => 
    columns.map(col => {
      const value = row[col]
      // Escapar strings com vírgulas ou aspas
      if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
        return `"${value.replace(/"/g, '""')}"`
      }
      return value ?? ''
    }).join(',')
  ).join('\n')
  
  const csv = `${headerRow}\n${dataRows}`
  
  // Download
  downloadFile(csv, `${filename}.csv`, 'text/csv;charset=utf-8;')
}

// Exportar para JSON
export function exportToJSON(data: unknown, filename: string) {
  const json = JSON.stringify(data, null, 2)
  downloadFile(json, `${filename}.json`, 'application/json')
}

// Exportar tabela HTML para PDF (usando window.print)
export function exportTableToPDF(
  title: string,
  headers: string[],
  rows: (string | number)[][],
  filename: string
) {
  const printWindow = window.open('', '_blank')
  if (!printWindow) {
    alert('Permita popups para exportar PDF')
    return
  }

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>${title}</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          padding: 20px;
          color: #1a1a1a;
        }
        h1 {
          font-size: 24px;
          margin-bottom: 8px;
          color: #8b5cf6;
        }
        .subtitle {
          color: #666;
          margin-bottom: 20px;
          font-size: 12px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }
        th, td {
          padding: 8px 12px;
          text-align: left;
          border-bottom: 1px solid #e5e5e5;
        }
        th {
          background: #f5f5f5;
          font-weight: 600;
          color: #333;
        }
        tr:nth-child(even) {
          background: #fafafa;
        }
        .positive { color: #22c55e; }
        .negative { color: #ef4444; }
        .footer {
          margin-top: 20px;
          padding-top: 10px;
          border-top: 1px solid #e5e5e5;
          font-size: 10px;
          color: #999;
        }
        @media print {
          body { padding: 0; }
          .no-print { display: none; }
        }
      </style>
    </head>
    <body>
      <h1>VIRTUS - ${title}</h1>
      <p class="subtitle">Exportado em ${new Date().toLocaleString('pt-BR')}</p>
      
      <table>
        <thead>
          <tr>
            ${headers.map(h => `<th>${h}</th>`).join('')}
          </tr>
        </thead>
        <tbody>
          ${rows.map(row => `
            <tr>
              ${row.map(cell => {
                const value = cell?.toString() || ''
                const isPositive = value.startsWith('+') || (parseFloat(value) > 0 && value.includes('%'))
                const isNegative = value.startsWith('-')
                const className = isPositive ? 'positive' : isNegative ? 'negative' : ''
                return `<td class="${className}">${value}</td>`
              }).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>
      
      <div class="footer">
        VIRTUS Trading Dashboard - ${window.location.origin}
      </div>
      
      <script>
        window.onload = () => {
          window.print()
          setTimeout(() => window.close(), 100)
        }
      </script>
    </body>
    </html>
  `

  printWindow.document.write(html)
  printWindow.document.close()
}

// Utilitário de download
function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
}

// Formatar dados para exportação
export function formatExportData(
  data: Record<string, unknown>[],
  formatters?: Record<string, (value: unknown) => string>
): Record<string, unknown>[] {
  return data.map(row => {
    const formatted: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(row)) {
      formatted[key] = formatters?.[key] ? formatters[key](value) : value
    }
    return formatted
  })
}

// Hook helper para exportação
export interface ExportOptions {
  filename: string
  title: string
  headers: string[]
  data: (string | number)[][]
}

export function createExportHandlers(options: ExportOptions) {
  return {
    exportCSV: () => {
      const csvData = options.data.map((row, i) => {
        const obj: Record<string, string | number> = {}
        options.headers.forEach((header, j) => {
          obj[header] = row[j]
        })
        return obj
      })
      exportToCSV(csvData, options.filename)
    },
    
    exportPDF: () => {
      exportTableToPDF(options.title, options.headers, options.data, options.filename)
    },
    
    exportJSON: () => {
      const jsonData = options.data.map((row, i) => {
        const obj: Record<string, string | number> = {}
        options.headers.forEach((header, j) => {
          obj[header] = row[j]
        })
        return obj
      })
      exportToJSON(jsonData, options.filename)
    }
  }
}
