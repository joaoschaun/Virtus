/**
 * Componente Sparkline - Mini gráfico de linha
 */

import { useMemo } from 'react'
import { cn } from '../../lib/utils'

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  color?: string
  strokeWidth?: number
  showArea?: boolean
  className?: string
}

export function Sparkline({ 
  data, 
  width = 80, 
  height = 24, 
  color,
  strokeWidth = 1.5,
  showArea = true,
  className 
}: SparklineProps) {
  
  const { path, areaPath, isPositive } = useMemo(() => {
    if (!data || data.length < 2) {
      return { path: '', areaPath: '', isPositive: true }
    }

    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1
    
    // Normalizar dados para o viewport
    const padding = 2
    const effectiveWidth = width - padding * 2
    const effectiveHeight = height - padding * 2
    
    const points = data.map((value, index) => ({
      x: padding + (index / (data.length - 1)) * effectiveWidth,
      y: padding + effectiveHeight - ((value - min) / range) * effectiveHeight
    }))
    
    // Criar path da linha
    const linePath = points.reduce((acc, point, i) => {
      if (i === 0) return `M ${point.x} ${point.y}`
      return `${acc} L ${point.x} ${point.y}`
    }, '')
    
    // Criar path da área (preenchimento)
    const area = `${linePath} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`
    
    // Determinar se é positivo (último valor > primeiro)
    const positive = data[data.length - 1] >= data[0]
    
    return { path: linePath, areaPath: area, isPositive: positive }
  }, [data, width, height])

  // Cor baseada na tendência
  const lineColor = color || (isPositive ? '#22c55e' : '#ef4444')
  const areaColor = isPositive ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)'

  if (!data || data.length < 2) {
    return (
      <div 
        className={cn('flex items-center justify-center', className)} 
        style={{ width, height }}
      >
        <span className="text-xs text-virtus-text-muted">—</span>
      </div>
    )
  }

  return (
    <svg 
      width={width} 
      height={height} 
      className={cn('overflow-visible', className)}
      viewBox={`0 0 ${width} ${height}`}
    >
      {/* Área de preenchimento */}
      {showArea && (
        <path
          d={areaPath}
          fill={areaColor}
        />
      )}
      
      {/* Linha principal */}
      <path
        d={path}
        fill="none"
        stroke={lineColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      
      {/* Ponto final */}
      <circle
        cx={width - 2}
        cy={path.split(' ').pop()}
        r={2}
        fill={lineColor}
      />
    </svg>
  )
}

// Sparkline com dados mockados para preview
export function SparklineDemo({ trend = 'up' }: { trend?: 'up' | 'down' | 'neutral' }) {
  const data = useMemo(() => {
    const base = 100
    const points = 20
    const result = []
    
    for (let i = 0; i < points; i++) {
      const noise = (Math.random() - 0.5) * 10
      const trendValue = trend === 'up' ? i * 0.5 : trend === 'down' ? -i * 0.5 : 0
      result.push(base + trendValue + noise)
    }
    
    return result
  }, [trend])

  return <Sparkline data={data} />
}

export default Sparkline
