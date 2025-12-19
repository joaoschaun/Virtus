import { useMemo } from 'react'

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  strokeColor?: string
  fillColor?: string
  strokeWidth?: number
  showArea?: boolean
  className?: string
  showDots?: boolean
  autoColor?: boolean
}

export default function Sparkline({
  data,
  width = 100,
  height = 30,
  strokeColor = '#E53935',
  fillColor,
  strokeWidth = 1.5,
  showArea = true,
  className = '',
  showDots = false,
  autoColor = true
}: SparklineProps) {
  const { path, areaPath, color, dots, viewBox } = useMemo(() => {
    if (!data || data.length < 2) {
      return { path: '', areaPath: '', color: strokeColor, dots: [], viewBox: `0 0 ${width} ${height}` }
    }
    
    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1
    
    // Calculate trend color
    const trendColor = autoColor 
      ? (data[data.length - 1] >= data[0] ? '#10b981' : '#ef4444')
      : strokeColor
    
    // Padding
    const padding = 2
    const effectiveWidth = width - padding * 2
    const effectiveHeight = height - padding * 2
    
    // Generate points
    const points: { x: number; y: number }[] = data.map((value, index) => ({
      x: padding + (index / (data.length - 1)) * effectiveWidth,
      y: padding + effectiveHeight - ((value - min) / range) * effectiveHeight
    }))
    
    // Create smooth path using line segments
    let d = `M ${points[0].x} ${points[0].y}`
    for (let i = 1; i < points.length; i++) {
      d += ` L ${points[i].x} ${points[i].y}`
    }
    
    // Create area path
    const lastPoint = points[points.length - 1]
    const firstPoint = points[0]
    const area = `${d} L ${lastPoint.x} ${height - padding} L ${firstPoint.x} ${height - padding} Z`
    
    return {
      path: d,
      areaPath: area,
      color: trendColor,
      dots: showDots ? points : [],
      viewBox: `0 0 ${width} ${height}`
    }
  }, [data, width, height, strokeColor, autoColor, showDots])
  
  if (!data || data.length < 2) {
    return (
      <svg 
        width={width} 
        height={height}
        className={className}
        viewBox={`0 0 ${width} ${height}`}
      >
        <line 
          x1="0" 
          y1={height / 2} 
          x2={width} 
          y2={height / 2}
          stroke="currentColor"
          strokeWidth={1}
          opacity={0.2}
          strokeDasharray="4 2"
        />
      </svg>
    )
  }
  
  return (
    <svg 
      width={width} 
      height={height}
      viewBox={viewBox}
      className={className}
      preserveAspectRatio="none"
    >
      {/* Area fill */}
      {showArea && (
        <path
          d={areaPath}
          fill={fillColor || color}
          opacity={0.15}
        />
      )}
      
      {/* Line */}
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      
      {/* Dots */}
      {dots.length > 0 && dots.map((point, idx) => (
        <circle
          key={idx}
          cx={point.x}
          cy={point.y}
          r={2}
          fill={color}
        />
      ))}
      
      {/* End dot */}
      {data.length > 0 && (
        <circle
          cx={width - 2}
          cy={dots[dots.length - 1]?.y || height / 2}
          r={2.5}
          fill={color}
        />
      )}
    </svg>
  )
}
