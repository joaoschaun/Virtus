import { useEffect, useRef, useCallback } from 'react'
import { useTradingStore } from '../stores/tradingStore'
import { useAuthStore } from '../stores/authStore'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5
  
  const { updateMetrics, setPositions, setConnected } = useTradingStore()
  const { isAuthenticated, accessToken } = useAuthStore()
  
  const connect = useCallback(() => {
    if (!isAuthenticated || ws.current?.readyState === WebSocket.OPEN) {
      return
    }
    
    try {
      ws.current = new WebSocket(`${WS_URL}?token=${accessToken}`)
      
      ws.current.onopen = () => {
        console.log('WebSocket connected')
        setConnected(true)
        reconnectAttempts.current = 0
        
        // Subscribe to channels
        ws.current?.send(JSON.stringify({
          type: 'subscribe',
          channels: ['metrics', 'positions', 'orders', 'alerts'],
        }))
      }
      
      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
      ws.current.onclose = () => {
        console.log('WebSocket disconnected')
        setConnected(false)
        
        // Attempt reconnect
        if (reconnectAttempts.current < maxReconnectAttempts && isAuthenticated) {
          reconnectAttempts.current++
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`)
          
          reconnectTimeout.current = setTimeout(connect, delay)
        }
      }
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
    }
  }, [isAuthenticated, accessToken, setConnected])
  
  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current)
    }
    
    if (ws.current) {
      ws.current.close()
      ws.current = null
    }
    
    setConnected(false)
  }, [setConnected])
  
  const handleMessage = (message: any) => {
    switch (message.type) {
      case 'metrics_update':
        updateMetrics({
          equity: message.data.equity,
          balance: message.data.balance,
          profit: message.data.profit,
          dailyPnl: message.data.daily_pnl,
          marginLevel: message.data.margin_level,
        })
        break
      
      case 'positions_update':
        setPositions(message.data)
        break
      
      case 'connected':
        console.log('WebSocket authenticated:', message)
        break
      
      case 'subscribed':
        console.log('Subscribed to channels:', message.channels)
        break
      
      case 'heartbeat':
        ws.current?.send(JSON.stringify({ type: 'ping' }))
        break
      
      case 'alert':
        // Handle alerts (could show toast notification)
        console.log('Alert received:', message.data)
        break
      
      default:
        console.log('Unknown message type:', message.type)
    }
  }
  
  const send = useCallback((data: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])
  
  // Auto connect/disconnect based on auth state
  useEffect(() => {
    if (isAuthenticated) {
      connect()
    } else {
      disconnect()
    }
    
    return () => {
      disconnect()
    }
  }, [isAuthenticated, connect, disconnect])
  
  return { connect, disconnect, send }
}

export default useWebSocket
